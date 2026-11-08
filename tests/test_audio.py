"""Exercise the real decoder without network access or a model download."""

import wave

import numpy as np
from faster_whisper.audio import decode_audio


def test_decode_pcm_audio(tmp_path):
    audio = tmp_path / "tone.wav"
    samples = (np.sin(2 * np.pi * 440 * np.arange(8000) / 8000) * 16000).astype("<i2")
    with wave.open(str(audio), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(8000)
        output.writeframes(samples.tobytes())

    decoded = decode_audio(str(audio), sampling_rate=16000)

    assert decoded.dtype == np.float32
    assert abs(len(decoded) - 16000) < 100
    assert np.isfinite(decoded).all()
    assert np.max(np.abs(decoded)) > 0.1
