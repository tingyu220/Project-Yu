"""Data models for the Yu Memory Kernel.

Event  — 真正发生过的事情，append-only。
Memory — 从经历中保存下来的有效信息。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


def utcnow_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Event:
    """An append-only record of something that actually happened."""

    id: int
    type: str
    content: str
    created_at: str


@dataclass(frozen=True)
class Memory:
    """A piece of useful information Yu has saved from experience."""

    id: int
    type: str
    content: str
    importance: str
    status: str
    source_event_id: Optional[int]
    created_at: str
    archived_at: Optional[str]
