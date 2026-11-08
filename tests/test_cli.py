import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from yt_subtitle import cli


URL = "https://www.youtube.com/watch?v=example"


@pytest.fixture(autouse=True)
def mock_device_check(monkeypatch):
    monkeypatch.setattr(cli, "check_device", lambda device: None)


@pytest.fixture
def pipeline(monkeypatch):
    state = SimpleNamespace(directory=None, segments=[
        SimpleNamespace(start=1.25, end=3604.5, text="  Hello, 世界!  "),
        SimpleNamespace(start=3605, end=3606, text="  "),
    ])

    def download(url, directory):
        state.directory = directory
        audio = directory / "audio.webm"
        audio.write_bytes(b"mock audio")
        return "example", audio

    monkeypatch.setattr(cli, "download_audio", download)
    monkeypatch.setattr(cli, "transcribe", lambda *args: iter(state.segments))
    return state


def test_defaults():
    args = cli.build_parser().parse_args([URL])
    assert (args.output_dir, args.model, args.language) == (Path("transcripts"), "small", None)
    assert args.device == "cuda"


def test_outputs_and_cleanup(tmp_path, pipeline):
    plain, timed = cli.run(URL, tmp_path / "output", "small", None)
    assert plain.read_text(encoding="utf-8") == "Hello, 世界!\n"
    assert timed.read_text(encoding="utf-8") == "[00:00:01.250 --> 01:00:04.500] Hello, 世界!\n"
    assert not pipeline.directory.exists()
    assert len(list(plain.parent.iterdir())) == 2


@pytest.mark.parametrize("name", ["example.txt", "example.timestamped.txt"])
def test_existing_output_is_preserved(tmp_path, pipeline, name):
    existing = tmp_path / name
    existing.write_text("existing", encoding="utf-8")
    with pytest.raises(cli.TranscriptionError, match="already exists"):
        cli.run(URL, tmp_path, "small", None)
    assert existing.read_text(encoding="utf-8") == "existing"
    assert len(list(tmp_path.iterdir())) == 1
    assert not pipeline.directory.exists()


def test_no_speech(tmp_path, pipeline):
    pipeline.segments = []
    with pytest.raises(cli.TranscriptionError, match="No speech"):
        cli.run(URL, tmp_path, "small", None)
    assert not list(tmp_path.iterdir())
    assert not pipeline.directory.exists()


@pytest.mark.parametrize("error", [cli.TranscriptionError("decode failed"), KeyboardInterrupt()])
def test_failure_during_iteration_cleans_up(tmp_path, pipeline, monkeypatch, error):
    def fail(*args):
        yield pipeline.segments[0]
        raise error

    monkeypatch.setattr(cli, "transcribe", fail)
    with pytest.raises(type(error)):
        cli.run(URL, tmp_path, "small", None)
    assert not list(tmp_path.iterdir())
    assert not pipeline.directory.exists()


def test_publication_rolls_back_without_overwriting(tmp_path):
    sources = (tmp_path / "a", tmp_path / "b")
    for path in sources:
        path.write_text("new")
    destinations = (tmp_path / "plain", tmp_path / "timed")
    destinations[1].write_text("existing")
    with pytest.raises(FileExistsError):
        cli.publish(sources, destinations)
    assert not destinations[0].exists()
    assert destinations[1].read_text() == "existing"


@pytest.mark.parametrize("url", ["file:///audio", "https://youtube.com.evil.test/watch?v=x", "https://youtube.com/playlist?list=x"])
def test_invalid_urls(tmp_path, url):
    with pytest.raises(cli.TranscriptionError):
        cli.run(url, tmp_path, "small", None)


def test_model_load_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "resolve_model", lambda name: str(tmp_path))
    def fail(*args, **kwargs):
        raise RuntimeError("offline")

    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=fail))
    with pytest.raises(cli.TranscriptionError, match="Model loading failed"):
        list(cli.transcribe(tmp_path / "audio", "small", None))


def test_download_failure(monkeypatch, tmp_path):
    def fail(*args, **kwargs):
        raise RuntimeError("offline")

    monkeypatch.setitem(sys.modules, "yt_dlp", SimpleNamespace(YoutubeDL=fail))
    with pytest.raises(cli.TranscriptionError, match="Download failed"):
        cli.download_audio(URL, tmp_path)


def test_main_dependency_error(monkeypatch, capsys):
    def fail(*args):
        raise ImportError("missing dependency; run uv sync")

    monkeypatch.setattr(sys, "argv", ["yt-subtitle", URL])
    monkeypatch.setattr(cli, "run", fail)
    assert cli.main() == 1
    assert "missing dependency" in capsys.readouterr().err


def test_timestamp_rounding():
    assert cli.timestamp(59.9999) == "00:01:00.000"
    assert cli.timestamp(360000) == "100:00:00.000"
