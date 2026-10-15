def test_cleanup_stops_only_owned_processes():
    from yu.voice.wake.launcher import OwnedServices
    stopped = []
    class Process:
        def __init__(self, name):
            self.name = name
        def poll(self):
            return None
        def terminate(self):
            stopped.append(self.name)
        def wait(self, timeout):
            pass
    owned = OwnedServices()
    owned.children = [Process("api"), Process("wake")]
    unrelated = Process("unrelated")
    owned.close()
    assert stopped == ["wake", "api"]
    assert unrelated.name not in stopped


def test_normal_listener_exit_closes_api(monkeypatch):
    from yu.voice.wake import launcher
    closed = []
    class Guard:
        def __init__(self, name):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *_):
            pass
    class Process:
        def __init__(self, code):
            self.code = code
        def poll(self):
            return self.code
    class Owned:
        def start(self, module):
            return Process(0 if module == "yu.voice.wake" else None)
        def close(self):
            closed.append(True)
    monkeypatch.setattr(launcher, "SingleInstance", Guard)
    monkeypatch.setattr(launcher, "check_port", lambda: None)
    monkeypatch.setattr(launcher, "preflight", lambda _: None)
    monkeypatch.setattr(launcher, "wait_api", lambda _: None)
    monkeypatch.setattr(launcher, "OwnedServices", Owned)
    launcher.run_launcher()
    assert closed == [True]


def test_launcher_refuses_occupied_port_without_starting(monkeypatch):
    from yu.voice.wake import launcher
    import pytest
    calls = []
    class Guard:
        def __init__(self, name):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *_):
            pass
    monkeypatch.setattr(launcher, "SingleInstance", Guard)
    def occupied():
        raise RuntimeError("端口占用")
    monkeypatch.setattr(launcher, "check_port", occupied)
    monkeypatch.setattr(launcher.subprocess, "Popen", lambda *a, **k: calls.append(a))
    with pytest.raises(RuntimeError):
        launcher.run_launcher()
    assert calls == []


def test_windows_singleton_blocks_duplicate_and_releases():
    import os
    import uuid
    import pytest
    if os.name != "nt":
        pytest.skip("Windows 命名互斥测试")
    from yu.voice.wake.singleton import SingleInstance
    name = "Local\\YuWakeTest" + uuid.uuid4().hex
    with SingleInstance(name):
        with pytest.raises(RuntimeError, match="已在运行"):
            with SingleInstance(name):
                pass
    with SingleInstance(name):
        pass


def test_start_script_propagates_preflight_failure(tmp_path):
    import os
    import shutil
    import subprocess
    from pathlib import Path
    import pytest
    if os.name != "nt":
        pytest.skip("Windows 启动脚本测试")
    from yu.voice.wake.detector import powershell
    source = Path(__file__).resolve().parents[1] / "start-voice.ps1"
    target = tmp_path / "start-voice.ps1"
    shutil.copy2(source, target)
    # 空目录没有虚拟环境，应在读取 Key 或创建任何子进程前失败。
    result = subprocess.run([powershell(), "-NoProfile", "-File", str(target)],
                            capture_output=True, timeout=10)
    assert result.returncode != 0
