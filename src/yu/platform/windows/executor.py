"""Windows 确定性执行器。

这里只执行已经通过 Safety Kernel 的 ProposedAction，且不使用 shell=True。
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Callable
from threading import Lock

from ...actions.models import ActionResult, ProposedAction
from .paths import WindowsPathRegistry
from .registry import WindowsAppRegistry
from .activation import reuse_running_app


_app_open_lock = Lock()


def _expand_path(value: str) -> Path:
    return Path(os.path.expanduser(os.path.expandvars(value)))


def _default_open_target(target: Path) -> None:
    if hasattr(os, "startfile"):
        os.startfile(str(target))  # type: ignore[attr-defined]
        return
    subprocess.Popen(["explorer.exe", str(target)], shell=False)


class WindowsExecutor:
    def __init__(
        self,
        app_registry: WindowsAppRegistry,
        path_registry: WindowsPathRegistry,
        start_process: Callable[[str], object] | None = None,
        open_target: Callable[[Path], object] | None = None,
    ):
        self.app_registry = app_registry
        self.path_registry = path_registry
        self._start_process = start_process or self._start_executable
        self._open_target = open_target or _default_open_target

    @staticmethod
    def _start_executable(executable: str) -> object:
        return subprocess.Popen([executable], shell=False)

    def execute(self, action: ProposedAction) -> ActionResult:
        try:
            if action.action_type.startswith("media."):
                from .media import execute_media
                return execute_media(action)
            if action.action_type == "app.open":
                return self._open_app(action)
            if action.action_type == "path.open":
                return self._open_path(action, require_file=False)
            if action.action_type == "file.open":
                return self._open_path(action, require_file=True)
            return self._failure(action, "UNSUPPORTED_ACTION", "暂不支持这个动作。")
        except (OSError, ValueError, TypeError) as exc:
            return self._failure(action, "EXECUTION_FAILED", f"执行失败：{exc}")

    def _open_app(self, action: ProposedAction) -> ActionResult:
        app_id = str(action.parameters.get("app_id", ""))
        entry = self.app_registry.resolve(app_id)
        if entry is None:
            return self._failure(action, "APP_NOT_FOUND", f"没有找到应用“{app_id}”。", app_id)
        if not entry.executable.strip():
            return self._failure(action, "APP_NOT_CONFIGURED", f"{entry.display_name}尚未配置启动路径。", entry.app_id)
        executable = _expand_path(entry.executable)
        if not executable.is_file():
            return self._failure(action, "APP_NOT_CONFIGURED", f"{entry.display_name}启动路径不存在。", entry.app_id)
        # 检查和启动保持互斥，避免并发指令同时判定应用未运行。
        with _app_open_lock:
            reused = reuse_running_app(str(executable))
            if reused is True:
                return ActionResult(action.action_id, action.action_type, True, f"已恢复 {entry.display_name}窗口。", entry.app_id)
            if reused is False:
                return self._failure(action, "APP_ALREADY_RUNNING", f"{entry.display_name}已运行，但无法可靠恢复窗口（可能有多个窗口或系统限制）；未启动新实例，请从任务栏或托盘打开。", entry.app_id)
            self._start_process(str(executable))
        return ActionResult(action.action_id, action.action_type, True, f"已打开 {entry.display_name}。", entry.app_id)

    def _open_path(self, action: ProposedAction, require_file: bool) -> ActionResult:
        path_id = action.parameters.get("path_id")
        if path_id:
            entry = self.path_registry.resolve(str(path_id))
            if entry is None or not entry.path.strip():
                return self._failure(action, "PATH_NOT_FOUND", "没有找到已配置的路径。", str(path_id))
            target = _expand_path(entry.path)
            display_name = entry.display_name
        else:
            raw_path = str(action.parameters.get("path", ""))
            if not raw_path.strip():
                return self._failure(action, "PATH_NOT_FOUND", "未配置打开路径。")
            target = _expand_path(raw_path)
            display_name = str(target)

        if not target.is_absolute():
            return self._failure(action, "PATH_NOT_FOUND", "请提供绝对路径。", str(target))
        # 普通文件打开不允许绕过应用白名单执行脚本或快捷方式。
        if target.is_file() and target.suffix.casefold() not in {".pdf", ".txt", ".md", ".png", ".jpg", ".jpeg", ".gif", ".mp3", ".mp4", ".docx", ".xlsx", ".pptx", ".csv"}:
            return self._failure(action, "UNSUPPORTED_FILE_TYPE", "暂不支持打开此文件类型。", str(target))
        if require_file and not target.is_file():
            return self._failure(action, "FILE_NOT_FOUND", f"没有找到文件“{target}”。", str(target))
        if not require_file and not target.exists():
            return self._failure(action, "PATH_NOT_FOUND", f"没有找到路径“{target}”。", str(target))
        self._open_target(target)
        return ActionResult(action.action_id, action.action_type, True, f"已打开 {display_name}。", str(target))

    @staticmethod
    def _failure(action: ProposedAction, code: str, message: str, target: str | None = None) -> ActionResult:
        return ActionResult(action.action_id, action.action_type, False, message, target, code)
