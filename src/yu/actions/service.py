"""Action 编排器：Router -> ProposedAction -> Safety -> Executor -> Audit。"""

from __future__ import annotations

from pathlib import Path
import asyncio
import os
import re
from uuid import uuid4

from ..audit.store import AuditStore
from ..platform.windows.executor import WindowsExecutor
from ..platform.windows.paths import WindowsPathRegistry
from ..platform.windows.registry import WindowsAppRegistry
from ..safety.kernel import SafetyKernel
from .models import ActionResult, ProposedAction
from .router import detect_action_intent


class ActionService:
    def __init__(
        self,
        kernel: SafetyKernel,
        audit: AuditStore,
        app_registry: WindowsAppRegistry,
        path_registry: WindowsPathRegistry,
        executor: WindowsExecutor | None = None,
    ):
        self.kernel = kernel
        self.audit = audit
        self.app_registry = app_registry
        self.path_registry = path_registry
        self.executor = executor or WindowsExecutor(app_registry, path_registry)

    def handle(self, text: str) -> ActionResult | None:
        if self._is_compound(text):
            # 两步各自经过权限和审计；打开失败不继续播放。
            opened = self.handle("打开QQ音乐")
            if opened is None or not opened.success:
                return opened
            return self.handle("播放QQ音乐")
        prepared = self._prepare(text)
        if not isinstance(prepared, tuple):
            return prepared
        action, target = prepared
        return self._record(action, target, self._execute(action, target))

    async def handle_async(self, text: str) -> ActionResult | None:
        """API 专用：权限与审计留在原线程，系统 I/O 在工作线程执行。"""
        if self._is_compound(text):
            opened = await self.handle_async("打开QQ音乐")
            if opened is None or not opened.success:
                return opened
            return await self.handle_async("播放QQ音乐")
        prepared = self._prepare(text)
        if not isinstance(prepared, tuple):
            return prepared
        action, target = prepared
        task = asyncio.create_task(asyncio.to_thread(self._execute, action, target))
        try:
            result = await asyncio.shield(task)
        except asyncio.CancelledError:
            # 系统操作不能靠取消 HTTP 回滚；等待实际结果并完整记审计。
            result = await task
            self._record(action, target, result)
            raise
        return self._record(action, target, result)

    @staticmethod
    def _is_compound(text: str) -> bool:
        compound = re.sub(r"[\s，,。.!！]", "", text).casefold()
        return compound in {"打开qq音乐并播放", "打开并播放qq音乐", "打开qq音乐然后播放"}

    def _prepare(self, text: str) -> tuple[ProposedAction, str] | ActionResult | None:
        intent = detect_action_intent(text, self.app_registry, self.path_registry)
        if intent is None:
            return None

        action = ProposedAction(
            action_id=uuid4().hex,
            action_type=intent.intent,
            description=f"{intent.intent}: {intent.target}",
            requested_by="owner",
            proposed_by="yu",
            required_capability="media.control" if intent.intent.startswith("media.") else "process.start",
            reason=f"用户明确要求：{text.strip()}",
            parameters=intent.parameters,
        )
        decision = self.kernel.evaluate(action)
        if not decision.allowed:
            result = ActionResult(
                action.action_id,
                action.action_type,
                False,
                f"[拒绝] {decision.reason}",
                intent.target,
                "ACTION_DENIED",
            )
            return result
        return action, intent.target

    def _execute(self, action: ProposedAction, target: str) -> ActionResult:
        try:
            return self.executor.execute(action)
        except Exception:  # noqa: BLE001 — 对用户只返回稳定失败类型
            return ActionResult(
                action.action_id,
                action.action_type,
                False,
                "执行失败。",
                target,
                "EXECUTION_FAILED",
            )

    def _record(self, action: ProposedAction, target: str, result: ActionResult) -> ActionResult:
        self.audit.record(
            event_type="ACTION_EXECUTED" if result.success else "ACTION_FAILED",
            actor="yu",
            action_id=action.action_id,
            reason=result.message,
            metadata={
                "action_type": action.action_type,
                "target": result.target or target,
                "success": result.success,
                "error_code": result.error_code,
            },
        )
        return result


def build_action_service(kernel: SafetyKernel, audit: AuditStore, config_dir: str | Path = "config") -> ActionService:
    # 仅本机进程启动配置授权；聊天内容不能修改权限。
    if os.environ.get("YU_ALLOW_LOCAL_OPEN") == "1" and kernel.owner.is_active():
        kernel.permissions.grant("process.start", granted_by="owner")
    if os.environ.get("YU_ALLOW_MEDIA_CONTROL") == "1" and kernel.owner.is_active():
        kernel.permissions.grant("media.control", granted_by="owner")
    config_dir = os.environ.get("YU_ACTION_CONFIG_DIR", str(config_dir))
    config_root = Path(config_dir)
    apps = WindowsAppRegistry(config_root / "windows_apps.yaml")
    paths = WindowsPathRegistry(config_root / "windows_paths.yaml")
    return ActionService(kernel, audit, apps, paths)
