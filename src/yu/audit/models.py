"""AuditEvent 数据模型。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AuditEvent:
    id: int
    timestamp: str
    event_type: str
    actor: str
    action_id: Optional[str]
    risk_level: Optional[str]
    decision: Optional[str]
    reason: str
    metadata: dict
