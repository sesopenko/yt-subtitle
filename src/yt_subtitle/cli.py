"""Command-line entry point and transcription pipeline."""

import argparse
import re
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse


class TranscriptionError(Exception):
    """An actionable failure that can be displayed without a traceback."""


def timestamp(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    seconds, milliseconds = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}.{milliseconds:03}"


def download_audio(url: str, directory: Path) -> tuple[str, Path]:
    from yt_dlp import YoutubeDL

    options = {
        "format": "bestaudio",
        "noplaylist": True,
        "outtmpl": str(directory / "audio.%(ext)s"),
        "quiet": True,
        "js_runtimes": {"node": {}},
    }
    try:
        with YoutubeDL(options) as downloader:
            info = downloader.extract_info(url, download=True)
            if not info or info.get("_type") in {"playlist", "multi_video"}:
                raise TranscriptionError("Provide a single YouTube video URL, not a playlist.")
            video_id = info["id"]
            if not re.fullmatch(r"[A-Za-z0-9_-]+", video_id):
                raise TranscriptionError("The downloader returned an invalid video ID.")
            path = Path(downloader.prepare_filename(info))
            if not path.is_file():
                raise TranscriptionError("The downloaded audio file could not be found.")
            return video_id, path
    except TranscriptionError:
        raise
    except Exception as exc:
        raise TranscriptionError(
            f"Download failed: {exc}. Check the URL, network access, and Node.js 22+ on PATH; "
            "try updating yt-dlp with uv lock --upgrade-package yt-dlp and uv sync."
        ) from exc


def resolve_model(model_name: str) -> str:
    """Download with visible Hub progress, preserving Whisper's model aliases."""
    from faster_whisper.utils import _MODELS
    from huggingface_hub import snapshot_download

    if Path(model_name).is_dir():
        print(f"Using local model: {model_name}", file=sys.stderr)
        return model_name
    # Reuse the installed library's aliases (including large and distil models).
    repo_id = _MODELS.get(model_name, model_name if "/" in model_name else None)
    if repo_id is None:
        raise ValueError(f"Unknown model: {model_name}")
    print(f"Preparing model {model_name} (downloading missing files if needed)...", file=sys.stderr)
    return snapshot_download(
        repo_id=repo_id,
        allow_patterns=[
            "config.json", "preprocessor_config.json", "model.bin",
            "tokenizer.json", "vocabulary.*",
        ],
    )


def check_device(device: str) -> None:
    if device == "cuda":
        from yt_subtitle.gpu import prepare_cuda

        try:
            prepare_cuda()
        except Exception as exc:
            raise TranscriptionError(
                f"GPU initialization failed: {exc}. Run uv sync and check your NVIDIA driver. "
                "CUDA 12/cuDNN 9 libraries are required. CPU use requires explicit --device cpu."
            ) from exc


def transcribe(audio: Path, model_name: str, language: str | None, device: str = "cuda"):
    check_device(device)
    from faster_whisper import WhisperModel

    try:
        model_path = resolve_model(model_name)
        compute_type = "float16" if device == "cuda" else "int8"
        print(f"Loading model on {device.upper()} ({compute_type})...", file=sys.stderr)
        model = WhisperModel(model_path, device=device, compute_type=compute_type)
    except Exception as exc:
        raise TranscriptionError(
            f"Model loading failed: {exc}. Check the model name, available memory, "
            "and internet access for the first model download. For GPU errors, check "
            "the NVIDIA driver/runtime; close other GPU apps or use --model base for less VRAM."
        ) from exc
    try:
        print("Decoding audio and detecting language...", file=sys.stderr)
        segments, _ = model.transcribe(
            str(audio), language=language, task="transcribe", log_progress=True,
        )
        yield from segments
    except Exception as exc:
        raise TranscriptionError(
            f"Audio decoding or transcription failed: {exc}. Check the language code "
            "and audio file. For CUDA errors, run uv sync and check the NVIDIA runtime "
            "and available VRAM."
        ) from exc


def publish(staged: tuple[Path, Path], destinations: tuple[Path, Path]) -> None:
    """Create outputs exclusively and roll back our files if publication fails."""
    created = []
    try:
        for source, destination in zip(staged, destinations, strict=True):
            with destination.open("xb") as target:
                created.append(destination)
                with source.open("rb") as incoming:
                    import shutil

                    shutil.copyfileobj(incoming, target)
    except BaseException:
        for path in created:
            path.unlink(missing_ok=True)
        raise


def run(url: str, output_dir: Path, model: str, language: str | None, device: str = "cuda") -> tuple[Path, Path]:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or not (
        host == "youtu.be" or host == "youtube.com" or host.endswith(".youtube.com")
    ):
        raise TranscriptionError("Provide an http(s) YouTube video URL.")
    if parsed.path.rstrip("/") == "/playlist":
        raise TranscriptionError("Provide a single YouTube video URL, not a playlist.")

    check_device(device)
    with tempfile.TemporaryDirectory(prefix="yt-subtitle-") as temporary:
        directory = Path(temporary)
        print("Downloading audio...", file=sys.stderr)
        video_id, audio = download_audio(url, directory)
        destinations = (output_dir / f"{video_id}.txt", output_dir / f"{video_id}.timestamped.txt")
        if any(path.exists() for path in destinations):
            raise TranscriptionError("An output file already exists; choose another --output-dir.")
        staged = (directory / "plain.txt", directory / "timestamped.txt")
        count = 0
        with staged[0].open("w", encoding="utf-8", newline="\n") as plain, staged[1].open(
            "w", encoding="utf-8", newline="\n"
        ) as timed:
            for segment in transcribe(audio, model, language, device):
                text = segment.text.strip()
                if not text:
                    continue
                plain.write(text + "\n")
                timed.write(f"[{timestamp(segment.start)} --> {timestamp(segment.end)}] {text}\n")
                count += 1
        if not count:
            raise TranscriptionError("No speech detected; no transcripts were created.")
        output_dir.mkdir(parents=True, exist_ok=True)
        publish(staged, destinations)
        return destinations


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Transcribe a YouTube video locally into two text files.")
    parser.add_argument("url", help="Single YouTube video URL")
    parser.add_argument("--output-dir", type=Path, default=Path("transcripts"))
    parser.add_argument("--model", default="small", help="Whisper model name or local path (default: small)")
    parser.add_argument("--language", help="Spoken language code, e.g. en; defaults to automatic detection")
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda",
                        help="Inference device (default: cuda, float16; cpu uses int8)")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        paths = run(args.url, args.output_dir, args.model, args.language, args.device)
    except KeyboardInterrupt:
        print("Interrupted; temporary audio removed.", file=sys.stderr)
        return 130
    except (TranscriptionError, OSError, ImportError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    for path in paths:
        print(path.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
