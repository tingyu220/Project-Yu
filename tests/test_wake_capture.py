import pytest


def test_config_rejects_wrong_sample_rate(tmp_path):
    from yu.voice.wake.config import WakeConfig
    path = tmp_path / "wake.yaml"
    path.write_text("sample_rate: 48000\n", encoding="utf-8")
    with pytest.raises(ValueError, match="16000"):
        WakeConfig.load(path)


def test_capture_overflow_is_reported_not_silently_dropped():
    from yu.voice.wake.capture import AudioCapture
    from yu.voice.wake.config import WakeConfig
    capture = AudioCapture(WakeConfig())
    for _ in range(20):
        capture._callback(b"\0" * 3200, 1600, None, None)
    capture._callback(b"\0" * 3200, 1600, None, None)
    with pytest.raises(RuntimeError, match="溢出"):
        capture.read(0)


def test_capture_rejects_corrupt_frame():
    from yu.voice.wake.capture import AudioCapture
    from yu.voice.wake.config import WakeConfig
    capture = AudioCapture(WakeConfig())
    capture._callback(b"\0" * 3, 1600, None, None)
    with pytest.raises(RuntimeError, match="音频"):
        capture.read(0)


def test_capture_closes_input_stream_on_exception(monkeypatch):
    import sys
    from types import SimpleNamespace
    from yu.voice.wake.capture import AudioCapture
    from yu.voice.wake.config import WakeConfig
    events = []

    class Stream:
        active = True
        def __init__(self, **kwargs):
            assert kwargs["samplerate"] == 16000
            assert kwargs["channels"] == 1
            assert kwargs["dtype"] == "int16"
        def start(self):
            events.append("start")
        def stop(self):
            events.append("stop")
        def close(self):
            events.append("close")

    monkeypatch.setitem(sys.modules, "sounddevice", SimpleNamespace(
        check_input_settings=lambda **kwargs: None, RawInputStream=Stream))
    with pytest.raises(ValueError):
        with AudioCapture(WakeConfig()):
            raise ValueError("test")
    assert events == ["start", "stop", "close"]
