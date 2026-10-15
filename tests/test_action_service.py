from yu.actions.models import ActionResult
from yu.actions.service import ActionService
from yu.audit.store import AuditStore
from yu.authority.owner import OwnerManager
from yu.platform.windows.paths import WindowsPathRegistry
from yu.platform.windows.registry import WindowsAppRegistry
from yu.safety.constitution import SafetyConstitution
from yu.safety.kernel import SafetyKernel
from yu.safety.permissions import PermissionEngine


class FakeExecutor:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def execute(self, action):
        self.calls.append(action)
        return self.result


def _service(tmp_path, executor):
    owner_path = tmp_path / "owner.yaml"
    owner_path.write_text(
        "owner_id: owner-1\ndisplay_name: Owner\nstatus: active\ncreated_at: now\n",
        encoding="utf-8",
    )
    audit = AuditStore(tmp_path / "audit.db")
    owner = OwnerManager(owner_path)
    permissions = PermissionEngine("owner-1", audit)
    kernel = SafetyKernel(
        SafetyConstitution("config/safety_constitution.yaml"),
        permissions,
        owner,
        audit,
    )
    app_config = tmp_path / "apps.yaml"
    app_config.write_text(
        "apps:\n"
        "  qq_music:\n"
        "    display_name: QQ音乐\n"
        "    aliases: [QQ音乐]\n"
        "    executable: ''\n",
        encoding="utf-8",
    )
    path_config = tmp_path / "paths.yaml"
    path_config.write_text("paths: {}\n", encoding="utf-8")
    service = ActionService(
        kernel,
        audit,
        WindowsAppRegistry(app_config),
        WindowsPathRegistry(path_config),
        executor,
    )
    return service, permissions, audit


def test_service_denies_without_process_permission(tmp_path):
    executor = FakeExecutor(ActionResult("a1", "app.open", True, "ok", "qq_music"))
    service, _, audit = _service(tmp_path, executor)

    result = service.handle("打开QQ音乐")

    assert result is not None
    assert result.success is False
    assert result.error_code == "ACTION_DENIED"
    assert executor.calls == []
    assert [event.event_type for event in reversed(audit.list_recent(10))] == [
        "ACTION_PROPOSED",
        "ACTION_DENIED",
    ]
    audit.close()


def test_service_executes_and_audits_allowed_action(tmp_path):
    executor = FakeExecutor(ActionResult("a1", "app.open", True, "已打开 QQ音乐。", "qq_music"))
    service, permissions, audit = _service(tmp_path, executor)
    permissions.grant("process.start")

    result = service.handle("打开QQ音乐")

    assert result.success is True
    assert len(executor.calls) == 1
    assert [event.event_type for event in reversed(audit.list_recent(10))][-3:] == [
        "ACTION_PROPOSED",
        "ACTION_ALLOWED",
        "ACTION_EXECUTED",
    ]
    audit.close()


def test_service_audits_executor_failure(tmp_path):
    executor = FakeExecutor(ActionResult("a1", "app.open", False, "没有找到应用。", "missing", "APP_NOT_FOUND"))
    service, permissions, audit = _service(tmp_path, executor)
    permissions.grant("process.start")

    result = service.handle("打开不存在的软件")

    assert result.success is False
    assert result.error_code == "APP_NOT_FOUND"
    assert any(event.event_type == "ACTION_FAILED" for event in audit.list_recent(10))
    audit.close()
