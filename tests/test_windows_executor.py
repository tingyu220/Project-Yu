from yu.actions.models import ProposedAction
from yu.platform.windows.executor import WindowsExecutor
from yu.platform.windows.paths import WindowsPathRegistry
from yu.platform.windows.registry import WindowsAppRegistry


def _action(action_type: str, parameters: dict) -> ProposedAction:
    return ProposedAction(
        action_id="a1",
        action_type=action_type,
        description="test",
        requested_by="owner",
        proposed_by="yu",
        required_capability="process.start",
        reason="test",
        parameters=parameters,
    )


def _registries(tmp_path, executable: str = "C:/Apps/QQMusic.exe"):
    app_config = tmp_path / "apps.yaml"
    app_config.write_text(
        "apps:\n"
        "  qq_music:\n"
        "    display_name: QQ音乐\n"
        "    aliases: [QQ音乐]\n"
        f"    executable: {executable}\n",
        encoding="utf-8",
    )
    path_config = tmp_path / "paths.yaml"
    path_config.write_text("paths: {}\n", encoding="utf-8")
    return WindowsAppRegistry(app_config), WindowsPathRegistry(path_config)


def test_executor_opens_configured_app(tmp_path):
    executable = tmp_path / "QQMusic.exe"
    executable.write_text("stub", encoding="utf-8")
    apps, paths = _registries(tmp_path, str(executable).replace("\\", "/"))
    started = []
    executor = WindowsExecutor(apps, paths, start_process=started.append)

    result = executor.execute(_action("app.open", {"app_id": "qq_music"}))

    assert result.success is True
    assert result.target == "qq_music"
    assert started == [str(executable)]


def test_executor_returns_app_not_found(tmp_path):
    apps, paths = _registries(tmp_path)
    executor = WindowsExecutor(apps, paths, start_process=lambda _: None)

    result = executor.execute(_action("app.open", {"app_id": "missing"}))

    assert result.success is False
    assert result.error_code == "APP_NOT_FOUND"


def test_executor_returns_app_not_configured(tmp_path):
    apps, paths = _registries(tmp_path, "")
    executor = WindowsExecutor(apps, paths, start_process=lambda _: None)

    result = executor.execute(_action("app.open", {"app_id": "qq_music"}))

    assert result.success is False
    assert result.error_code == "APP_NOT_CONFIGURED"


def test_executor_opens_existing_path(tmp_path):
    target = tmp_path / "folder"
    target.mkdir()
    apps, paths = _registries(tmp_path)
    opened = []
    executor = WindowsExecutor(apps, paths, open_target=opened.append)

    result = executor.execute(_action("path.open", {"path": str(target)}))

    assert result.success is True
    assert opened == [target]


def test_executor_returns_path_not_found(tmp_path):
    apps, paths = _registries(tmp_path)
    executor = WindowsExecutor(apps, paths, open_target=lambda _: None)

    result = executor.execute(_action("path.open", {"path": str(tmp_path / "missing")}))

    assert result.success is False
    assert result.error_code == "PATH_NOT_FOUND"


def test_executor_returns_file_not_found(tmp_path):
    apps, paths = _registries(tmp_path)
    executor = WindowsExecutor(apps, paths, open_target=lambda _: None)

    result = executor.execute(_action("file.open", {"path": str(tmp_path / "missing.pdf")}))

    assert result.success is False
    assert result.error_code == "FILE_NOT_FOUND"


def test_executor_rejects_unsupported_action(tmp_path):
    apps, paths = _registries(tmp_path)
    executor = WindowsExecutor(apps, paths)

    result = executor.execute(_action("system.shutdown", {}))

    assert result.success is False
    assert result.error_code == "UNSUPPORTED_ACTION"


def test_executor_reuses_running_app_without_starting(tmp_path, monkeypatch):
    executable = tmp_path / "QQMusic.exe"
    executable.write_text("stub", encoding="utf-8")
    apps, paths = _registries(tmp_path, str(executable))
    monkeypatch.setattr("yu.platform.windows.executor.reuse_running_app", lambda _: True, raising=False)
    started = []
    result = WindowsExecutor(apps, paths, start_process=started.append).execute(
        _action("app.open", {"app_id": "qq_music"})
    )
    assert result.success
    assert "恢复" in result.message
    assert started == []


def test_executor_does_not_launch_when_running_window_cannot_be_restored(tmp_path, monkeypatch):
    executable = tmp_path / "QQMusic.exe"
    executable.write_text("stub", encoding="utf-8")
    apps, paths = _registries(tmp_path, str(executable))
    monkeypatch.setattr("yu.platform.windows.executor.reuse_running_app", lambda _: False, raising=False)
    started = []
    result = WindowsExecutor(apps, paths, start_process=started.append).execute(
        _action("app.open", {"app_id": "qq_music"})
    )
    assert not result.success
    assert result.error_code == "APP_ALREADY_RUNNING"
    assert started == []
