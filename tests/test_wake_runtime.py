import pytest


def test_feedback_text_is_stdin_not_shell_code(monkeypatch):
    from yu.voice.wake import feedback
    calls = []
    def run(command, **kwargs):
        calls.append((command, kwargs))
        class Process:
            returncode = 0
            def communicate(self, input, timeout):
                calls[0][1]["input"] = input
        return Process()
    monkeypatch.setattr(feedback.subprocess, "Popen", run)
    monkeypatch.setattr(feedback, "powershell", lambda: "pwsh.exe")
    text = '你好; Remove-Item C:\\anything'
    feedback.Feedback().speak(text)
    assert text not in " ".join(calls[0][0])
    assert calls[0][1]["input"] == text.encode("utf-8")
    assert calls[0][1]["shell"] is False


def test_capture_discards_audio_during_local_reply():
    from yu.voice.wake.capture import AudioCapture
    from yu.voice.wake.config import WakeConfig
    capture = AudioCapture(WakeConfig())
    capture.muted = True
    for _ in range(50):
        capture._callback(bytes(3200), 1600, None, None)
    with pytest.raises(TimeoutError):
        capture.read(0)
    capture.muted = False
    capture._callback(bytes(3200), 1600, None, None)
    assert capture.read(0) == bytes(3200)


def test_native_preflight_does_not_open_microphone(monkeypatch):
    from yu.voice.wake import runtime
    import sys
    from types import SimpleNamespace
    from yu.voice.wake.config import WakeConfig
    checks = []
    monkeypatch.setattr(runtime, "check_native", lambda: checks.append("native"))
    monkeypatch.setitem(sys.modules, "sounddevice", SimpleNamespace(
        check_input_settings=lambda **kwargs: checks.append("settings")))
    runtime.preflight(WakeConfig())
    assert checks == ["native", "settings"]


def test_failed_local_voice_falls_back_to_text_without_cloud(monkeypatch, capsys):
    from yu.voice.wake import feedback
    monkeypatch.setattr(feedback, "powershell", lambda: "pwsh.exe")
    class Process:
        returncode = 1
        def communicate(self, **kwargs):
            pass
    monkeypatch.setattr(feedback.subprocess, "Popen", lambda *a, **k: Process())
    feedback.Feedback().speak("文字回复")
    assert "未切换云端" in capsys.readouterr().out
