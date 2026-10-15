import pytest


def test_native_event_requires_exact_keyword_and_confidence():
    from yu.voice.wake.detector import KeywordDetector
    from yu.voice.wake.config import WakeConfig
    detector = KeywordDetector(WakeConfig())
    assert not detector.handle_event({"type": "wake", "text": "别的内容", "confidence": 0.99})
    assert not detector.handle_event({"type": "wake", "text": "嘿宇", "confidence": 0.1})
    assert detector.handle_event({"type": "wake", "text": "嘿宇", "confidence": 0.9})
    assert not detector.handle_event({"type": "wake", "text": "嘿宇", "confidence": 0.9})
    detector.reset()
    assert detector.handle_event({"type": "wake", "text": "嘿宇", "confidence": 0.9})


def test_detector_rejects_corrupt_audio_before_process_io():
    from yu.voice.wake.detector import KeywordDetector
    from yu.voice.wake.config import WakeConfig
    with pytest.raises(ValueError, match="PCM"):
        KeywordDetector(WakeConfig()).accept(b"123")


def test_detector_rejects_malformed_native_result():
    from yu.voice.wake.detector import KeywordDetector
    from yu.voice.wake.config import WakeConfig
    detector = KeywordDetector(WakeConfig())
    for confidence in [None, "1", float("nan"), True]:
        assert not detector.handle_event({"type": "wake", "text": "嘿宇", "confidence": confidence})


def test_windows_native_accepts_pcm_pipe_without_microphone():
    import os
    if os.name != "nt":
        pytest.skip("仅 Windows 本地引擎集成验证")
    from yu.voice.wake.detector import KeywordDetector, check_native
    from yu.voice.wake.config import WakeConfig
    try:
        check_native()
    except RuntimeError:
        pytest.skip("未安装中文本地识别引擎")
    with KeywordDetector(WakeConfig()) as detector:
        import time
        for _ in range(10):
            assert detector.accept(bytes(3200)) is False
            time.sleep(0.1)


def test_windows_native_recognizes_keyword_from_memory_audio():
    import os
    import base64
    import subprocess
    import time
    from pathlib import Path
    if os.name != "nt":
        pytest.skip("仅 Windows 本地引擎集成验证")
    from yu.voice.wake.detector import KeywordDetector, check_native, powershell
    from yu.voice.wake.config import WakeConfig
    try:
        check_native()
    except RuntimeError:
        pytest.skip("未安装中文本地识别引擎")
    result = subprocess.run([powershell(), "-NoProfile", "-File",
        str(Path(__file__).with_name("native-wake-fixture.ps1"))], capture_output=True, timeout=20)
    if result.returncode == 2:
        pytest.skip("未安装中文音色")
    assert result.returncode == 0
    audio = bytes(16000) + base64.b64decode(result.stdout.strip()) + bytes(64000)
    audio += bytes((-len(audio)) % 3200)
    hit = False
    with KeywordDetector(WakeConfig()) as detector:
        for start in range(0, len(audio), 3200):
            hit = detector.accept(audio[start:start+3200]) or hit
            time.sleep(0.03)
    assert hit
