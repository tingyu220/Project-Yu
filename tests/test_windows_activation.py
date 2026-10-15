from types import SimpleNamespace

from yu.platform.windows import activation


def test_tray_message_window_is_not_a_main_window():
    assert not activation.is_main_window("WxTrayIconMessageWindow", "Qt51514WxTrayIconMessageWindowClass", 0x04C00000, 0x100, 0)
    assert activation.is_main_window("微信", "Qt51514QWindowIcon", 0x86C70000, 0x100, 0)
    assert not activation.is_main_window("工具", "Tool", 0x00C00000, 0x80, 0)


def test_process_matching_uses_full_path_not_name(tmp_path, monkeypatch):
    target = str(tmp_path / "Weixin.exe")
    processes = [
        SimpleNamespace(info={"pid": 11, "name": "Weixin.exe", "exe": target}),
        SimpleNamespace(info={"pid": 12, "name": "Weixin.exe", "exe": str(tmp_path / "other" / "Weixin.exe")}),
    ]
    monkeypatch.setattr(activation.psutil, "process_iter", lambda _: processes)
    assert activation.running_app_pids(target) == ({11}, False)


def test_missing_process_path_blocks_duplicate_launch(tmp_path, monkeypatch):
    processes = [SimpleNamespace(info={"pid": 11, "name": "Weixin.exe", "exe": None})]
    monkeypatch.setattr(activation.psutil, "process_iter", lambda _: processes)
    assert activation.running_app_pids(str(tmp_path / "Weixin.exe")) == (set(), True)


def test_main_window_selection_excludes_helpers_and_multiple_instances():
    # 同一进程主窗口优先；另一进程是独立实例，不能默默选择账号。
    windows = [(11, False, 500000, 101), (11, False, 30000, 102), (12, True, 400000, 201)]
    assert activation.select_main_windows(windows) == [101, 201]


def test_multiple_instances_are_not_activated(monkeypatch):
    monkeypatch.setattr(activation, "running_app_pids", lambda _: ({11, 12}, False))
    monkeypatch.setattr(activation, "app_windows", lambda _: [101, 201])
    activated = []
    monkeypatch.setattr(activation, "activate_window", activated.append)
    assert activation.reuse_running_app("Weixin.exe") is False
    assert activated == []
