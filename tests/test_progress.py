from types import SimpleNamespace

import huggingface_hub
import faster_whisper

from yt_subtitle import cli


def test_model_download_uses_visible_default_progress(monkeypatch):
    calls = []

    def download(**kwargs):
        calls.append(kwargs)
        return "cached-model"

    monkeypatch.setattr(huggingface_hub, "snapshot_download", download)
    assert cli.resolve_model("small") == "cached-model"
    assert calls[0]["repo_id"] == "Systran/faster-whisper-small"
    assert "model.bin" in calls[0]["allow_patterns"]
    assert "tqdm_class" not in calls[0]  # Do not use Whisper's disabled_tqdm.


def test_local_model_skips_download(monkeypatch, tmp_path):
    def unexpected(**kwargs):
        raise AssertionError("Local models must not download")

    monkeypatch.setattr(huggingface_hub, "snapshot_download", unexpected)
    assert cli.resolve_model(str(tmp_path)) == str(tmp_path)


def test_transcription_enables_progress_and_preserves_segments(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "check_device", lambda device: None)
    expected = [SimpleNamespace(start=0, end=3, text="Hello")]
    calls = []

    class Model:
        def __init__(self, path, **kwargs):
            assert path == "cached-model"
            assert kwargs == {"device": "cuda", "compute_type": "float16"}

        def transcribe(self, path, **kwargs):
            calls.append(kwargs)
            return iter(expected), SimpleNamespace(duration=3)

    monkeypatch.setattr(cli, "resolve_model", lambda name: "cached-model")
    monkeypatch.setattr(faster_whisper, "WhisperModel", Model)
    assert list(cli.transcribe(tmp_path / "audio", "small", "en")) == expected
    assert calls == [{"language": "en", "task": "transcribe", "log_progress": True}]
