import sys
from types import SimpleNamespace

import pytest

from yt_subtitle import cli, gpu


def test_gpu_failure_stops_before_download(monkeypatch, tmp_path):
    def fail():
        raise RuntimeError("Missing CUDA library")

    def unexpected(*args):
        raise AssertionError("Must fail before downloading audio")

    monkeypatch.setattr(gpu, "prepare_cuda", fail)
    monkeypatch.setattr(cli, "download_audio", unexpected)
    with pytest.raises(cli.TranscriptionError, match="GPU initialization failed"):
        cli.run("https://youtu.be/example", tmp_path, "small", None)


def test_explicit_cpu_uses_int8(monkeypatch, tmp_path):
    calls = []

    class Model:
        def __init__(self, path, **kwargs):
            calls.append(kwargs)

        def transcribe(self, *args, **kwargs):
            return iter([]), None

    def unexpected():
        raise AssertionError("CPU must not initialize CUDA")

    monkeypatch.setattr(gpu, "prepare_cuda", unexpected)
    monkeypatch.setattr(cli, "resolve_model", lambda name: str(tmp_path))
    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=Model))
    assert list(cli.transcribe(tmp_path / "audio", "small", "en", "cpu")) == []
    assert calls == [{"device": "cpu", "compute_type": "int8"}]


def test_no_gpu_has_actionable_error(monkeypatch):
    monkeypatch.setattr(gpu.sys, "platform", "linux")
    monkeypatch.setitem(sys.modules, "ctranslate2", SimpleNamespace(get_cuda_device_count=lambda: 0))
    with pytest.raises(RuntimeError, match="No CUDA GPU detected"):
        gpu.prepare_cuda()
