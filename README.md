# yt-subtitle

Download a YouTube video's audio temporarily and transcribe it locally into plain
and timestamped UTF-8 text. Media is removed after completion or failure. The
multilingual Whisper `small` model runs on an NVIDIA GPU with CUDA and float16
processing by default. No API key is required.

## Setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and
[Node.js](https://nodejs.org/en/download/) version 22 or newer. Node must be
on `PATH` for yt-dlp's YouTube JavaScript challenges. The downloader explicitly
enables Node; Deno is not required. Node is installed separately from uv's Python
dependencies. Open a new terminal after installing it.

```powershell
uv python install 3.12
uv sync
node --version
nvidia-smi
```

Python 3.12 is pinned for dependency compatibility. Audio is downloaded without
conversion and decoded by PyAV (bundled with faster-whisper); this workflow does
not require a separate FFmpeg executable.
PyAV is constrained below version 19 because faster-whisper 1.2.1 uses a decoder
argument removed in PyAV 19. Keep this compatibility constraint until a released
faster-whisper version supports the newer API.

The first use downloads the selected
model from Hugging Face. Subsequent runs reuse its cache. Downloads need network
access. An NVIDIA GPU and a working NVIDIA driver are required for the default
device. On Windows, `uv sync` installs CUDA 12 cuBLAS and cuDNN 9 runtime libraries
in the virtual environment (about 1.3 GB of downloads). The application locates
their DLLs automatically; no system-wide CUDA Toolkit or PATH edits are needed.
On Linux, install CUDA 12/cuDNN 9 runtime libraries separately and make them
available to the dynamic linker.
Model downloads display Hugging Face progress bars and reuse already cached
files. Separate messages identify model loading and audio decoding, followed by
a transcription bar showing processed audio seconds and estimated time remaining.
Transcription updates arrive in chunks, so the bar can pause during computation.
Its counter measures seconds of audio, not iteration count.
Set `HF_HUB_DISABLE_PROGRESS_BARS=1` only if you want to hide model-download bars.

## Usage

```powershell
uv run yt-subtitle "https://www.youtube.com/watch?v=VIDEO_ID"
uv run yt-subtitle "https://youtu.be/VIDEO_ID" --output-dir results --model base --language en
uv run yt-subtitle "https://youtu.be/VIDEO_ID" --device cpu
uv run yt-subtitle --help
```

The default output directory is `transcripts/`. Successful runs print both paths:

- `<video-id>.txt`: one trimmed segment per line, without timestamps.
- `<video-id>.timestamped.txt`: `[00:00:01.250 --> 00:00:04.500] Spoken text`.

The default is `--device cuda` with float16 on GPU 0. GPU initialization is
checked before downloading audio, and GPU errors never silently fall back to
CPU. `--device cpu` explicitly selects the slower int8 CPU mode. If VRAM runs
out, close other GPU applications or select a smaller model with `--model base`.
The `small` model is retained by default to keep the same quality target.

Language is detected automatically unless `--language` is provided. Speech is
transcribed in its original language, not translated. Both files come from the
same transcription pass. Existing outputs are never overwritten; use another
output directory to rerun. No detected speech is reported as an error without
creating files. Temporary media is cleaned up on normal failure or Ctrl+C;
force-killing the process can prevent cleanup. Model cache files are retained.

Only one video is processed per invocation, including video links containing a
playlist parameter. Playlist-only links, authentication, and batch processing
are outside the initial scope. If downloads fail, check Node
and network access, then update the downloader:

```powershell
uv lock --upgrade-package yt-dlp
uv sync
```

## Development and verification

To start Codex with permissions for Git writes, uv caches and installations, and
network downloads, run from your own PowerShell terminal:

```powershell
.\scripts\codex.ps1
```

The launcher starts a fresh session in this repository with `danger-full-access`
and `on-request` approvals. Commands run with your Windows user's filesystem and
network access, outside the command sandbox. It does not change global Codex
settings or override managed policies. Additional CLI arguments are forwarded,
for example `.\scripts\codex.ps1 resume --last`.

Source lives in `src/yt_subtitle/`; offline tests live in `tests/`. Use four-space
Python indentation and descriptive snake_case names. No formatter or linter is
configured.

```powershell
uv run pytest
uv run yt-subtitle --help
uv build
```

For an end-to-end check, run the command against a short public YouTube video
with speech. Confirm both files contain matching text, timestamps follow the
audio, and no downloaded media remains in the output directory. Repeat with the
same output directory to confirm overwrite protection. Automated tests mock the
download and model boundaries and require neither network access nor model data.
A decoder regression test also exercises real PyAV decoding and resampling with
a generated WAV file to catch dependency incompatibilities.
