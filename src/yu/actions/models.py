"""Action 域模型：ProposedAction 与 ActionDecision。

LLM / Planner 只能输出 ProposedAction，不能直接执行。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from ..safety.risk import RiskLevel


@dataclass
class ProposedAction:
    action_id: str
    action_type: str
    description: str
    requested_by: str
    proposed_by: str
    required_capability: str
    reason: str
    risk_level: Optional[RiskLevel] = None
    parameters: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""


@dataclass(frozen=True)
class ActionDecision:
    allowed: bool
    action_id: str
    risk_level: RiskLevel
    reason: str
