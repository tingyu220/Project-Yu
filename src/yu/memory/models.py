"""Data models for the Yu Memory Kernel.

Event  — 真正发生过的事情，append-only；每条事件带 role（user / assistant / system）。
Memory — 从经历中保存下来的有效信息；每条记忆带 provenance（来源 / 证据 / 置信度）。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from .provenance import VERIFIED_SOURCE_TYPES


def utcnow_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Event:
    """An append-only record of something that actually happened.

    role 区分说话人：user / assistant / system。Memory Extraction 只允许读取
    role == "user" 的事件，避免把 assistant 输出误当成用户历史。
    """

    id: int
    type: str
    content: str
    created_at: str
    role: str = "user"

    @property
    def event_id(self) -> str:
        """稳定的字符串事件引用（evt_00031），用于溯源与调试展示。"""
        return f"evt_{self.id:05d}"


@dataclass(frozen=True)
class Memory:
    """A piece of useful information Yu has saved from experience.

    Provenance 字段：
    - source_type   来源类型（USER_EXPLICIT / ... / UNKNOWN）
    - source_role   来源说话人角色（user / assistant / system / None）
    - source_event_id 支撑本记忆的原始 Event（Primary Evidence）
    - confidence    置信度（按 source_type 设定上限）

    只有 source_type 属于 verified 集合的记忆，才可以支撑「你之前说过……」这类
    用户历史归因。
    """

    id: int
    type: str
    content: str
    importance: str
    status: str
    source_event_id: Optional[int]
    created_at: str
    archived_at: Optional[str]
    updated_at: Optional[str] = None
    source_type: str = "UNKNOWN"
    source_role: Optional[str] = None
    confidence: float = 0.5

    @property
    def verified(self) -> bool:
        """是否可作为用户历史事实引用（强归因）。"""
        return self.source_type in VERIFIED_SOURCE_TYPES

    @property
    def memory_id(self) -> str:
        """稳定的字符串记忆引用（mem_00012），用于溯源与调试展示。"""
        return f"mem_{self.id:05d}"