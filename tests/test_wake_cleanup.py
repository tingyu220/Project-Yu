import asyncio
import threading

import pytest


def test_initialization_cancel_closes_completed_detector(monkeypatch):
    from yu.voice.wake import runtime
    async def scenario():
        started, release = threading.Event(), threading.Event()
        closed = []
        class Detector:
            def __enter__(self):
                started.set()
                release.wait(2)
                return self
            def __exit__(self, *_):
                closed.append(True)
        task = asyncio.create_task(runtime.open_detector(Detector()))
        for _ in range(100):
            if started.is_set():
                break
            await asyncio.sleep(0.01)
        task.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert closed == [True]
    asyncio.run(scenario())


def test_stopped_native_reader_times_out_instead_of_blocking():
    from yu.voice.wake.detector import KeywordDetector
    from yu.voice.wake.config import WakeConfig
    import time
    class Input:
        def write(self, data):
            time.sleep(0.3)
            return len(data)
        def flush(self):
            pass
    class Process:
        stdin = Input()
        def poll(self):
            return None
    detector = KeywordDetector(WakeConfig())
    detector._process = Process()
    detector._write_timeout = 0.03
    started = time.monotonic()
    with pytest.raises(RuntimeError, match="阻塞"):
        detector.accept(bytes(3200))
    assert time.monotonic() - started < 0.2


def test_capture_failure_does_not_restart_detector_or_claim_waiting(monkeypatch, tmp_path, capsys):
    from yu.voice.wake import runtime
    from yu.voice.wake.capture import CaptureError
    events = []
    class Detector:
        def __init__(self, config):
            pass
        def __enter__(self):
            events.append("enter")
            return self
        def __exit__(self, *_):
            events.append("exit")
        def accept(self, pcm):
            return True
    class Capture:
        muted = False
        def __init__(self, config):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *_):
            events.append("capture_closed")
        def read(self, timeout):
            return bytes(3200)
        def discard(self):
            pass
    class Session:
        def __init__(self, base_url):
            pass
        async def run(self, *args):
            raise CaptureError("麦克风断开")
    class Guard:
        def __init__(self, name):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *_):
            pass
    monkeypatch.setattr(runtime, "preflight", lambda _: None)
    monkeypatch.setattr(runtime, "KeywordDetector", Detector)
    monkeypatch.setattr(runtime, "AudioCapture", Capture)
    monkeypatch.setattr(runtime, "VoiceSession", Session)
    monkeypatch.setattr(runtime, "SingleInstance", Guard)
    config = tmp_path / "wake.yaml"
    config.write_text("{}", encoding="utf-8")
    with pytest.raises(CaptureError):
        asyncio.run(runtime.run_wake(config, "http://127.0.0.1:8792", 1))
    assert events == ["enter", "exit", "capture_closed"]
    assert "已回到本地待唤醒" not in capsys.readouterr().out
