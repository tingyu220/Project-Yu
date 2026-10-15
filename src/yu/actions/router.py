"""本地确定性 Action Intent Router，不调用 LLM。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..platform.windows.paths import WindowsPathRegistry
from ..platform.windows.registry import WindowsAppRegistry


@dataclass(frozen=True)
class ActionIntent:
    intent: str
    target: str
    confidence: float
    parameters: dict[str, Any]


_COMMAND_RE = re.compile(r"^(?:请)?\s*(打开|启动|运行)\s*(.+?)\s*$", re.IGNORECASE)
_VAGUE_MARKERS = ("那个", "东西", "昨天", "之前", "最近", "经常")


def _clean_target(value: str) -> str:
    return value.strip().rstrip("。.!！？?").strip()


def detect_action_intent(
    text: str,
    app_registry: WindowsAppRegistry,
    path_registry: WindowsPathRegistry,
) -> ActionIntent | None:
    spoken = re.sub(r"^(?:宇|小宇|Yu)[，,、\s]+", "", text.strip(), flags=re.IGNORECASE)
    spoken = re.sub(r"^(?:请|帮我)+\s*", "", spoken)
    normalized = re.sub(r"\s+", "", _clean_target(spoken)).casefold()
    normalized = re.sub(r"^(?:请|帮我)", "", normalized)
    media_commands = {
        "播放下一首歌": "media.next", "播放下一首": "media.next", "下一首歌": "media.next", "下一首": "media.next", "切歌": "media.next",
        "播放上一首歌": "media.previous", "上一首": "media.previous", "上一首歌": "media.previous",
        "播放": "media.play", "播放音乐": "media.play", "继续播放": "media.play", "播放qq音乐": "media.play", "qq音乐播放": "media.play",
        "暂停": "media.pause", "暂停播放": "media.pause", "暂停音乐": "media.pause", "暂停qq音乐": "media.pause",
    }
    if normalized in media_commands:
        return ActionIntent(media_commands[normalized], "qq_music", 1.0, {"app_id": "qq_music"})
    if re.match(r"^(播放|暂停|切换|切到|换一首|来一首|放一首|上一首|下一首)", normalized):
        return ActionIntent("media.unsupported", "qq_music", 1.0, {"app_id": "qq_music"})
    match = _COMMAND_RE.match(spoken)
    if match is None:
        return None
    target = _clean_target(match.group(2))
    if not target:
        return None

    app = app_registry.resolve(target)
    if app is not None:
        return ActionIntent("app.open", app.app_id, 1.0, {"app_id": app.app_id})

    configured_path = path_registry.resolve(target)
    if configured_path is not None:
        return ActionIntent("path.open", configured_path.path_id, 1.0, {"path_id": configured_path.path_id})

    if re.match(r"^[A-Za-z]:[\\/]", target):
        path = Path(target)
        action_type = "file.open" if path.suffix else "path.open"
        return ActionIntent(action_type, target, 1.0, {"path": target})

    if any(marker in target for marker in _VAGUE_MARKERS):
        return None

    # 明确的“打开某个命名对象”进入 Executor，由它返回 APP_NOT_FOUND；不让 LLM 猜测。
    return ActionIntent("app.open", target, 1.0, {"app_id": target})
