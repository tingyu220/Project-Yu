"""真实打开前的配置与执行边界回归。"""
from yu.platform.windows.paths import WindowsPathRegistry
from yu.platform.windows.executor import WindowsExecutor
from yu.platform.windows.registry import WindowsAppRegistry
from yu.actions.models import ProposedAction


def test_blank_config_stays_blank(tmp_path):
    config = tmp_path / "paths.yaml"
    config.write_text("paths:\n  empty:\n    path: ''\n", encoding="utf-8")
    assert WindowsPathRegistry(config).resolve("empty").path == ""


def test_script_cannot_open_as_document(tmp_path):
    script = tmp_path / "danger.cmd"
    script.write_text("", encoding="utf-8")
    opened = []
    executor = WindowsExecutor(WindowsAppRegistry(tmp_path / "none"), WindowsPathRegistry(tmp_path / "none"), open_target=opened.append)
    action = ProposedAction("test", "file.open", "测试", "owner", "yu", "process.start", "测试", parameters={"path": str(script)})
    assert executor.execute(action).error_code == "UNSUPPORTED_FILE_TYPE"
    assert opened == []


def test_startup_grant_is_explicit(monkeypatch, tmp_path):
    from yu.api import context
    monkeypatch.setattr(context, "DEFAULT_DB_PATH", str(tmp_path / "yu.db"))
    monkeypatch.setattr(context, "DEFAULT_AUDIT_DB", str(tmp_path / "audit.db"))
    monkeypatch.delenv("YU_ALLOW_LOCAL_OPEN", raising=False)
    ctx = context.build_context()
    assert not ctx.permissions.has_permission("process.start")
    ctx.close()
    monkeypatch.setenv("YU_ALLOW_LOCAL_OPEN", "1")
    ctx = context.build_context()
    assert ctx.permissions.has_permission("process.start")
    assert any(e.event_type == "PERMISSION_GRANT" for e in ctx.audit.list_recent())
    ctx.close()
