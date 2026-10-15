"""Action 域模型：提议、决策与执行结果。

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


@dataclass(frozen=True)
class ActionResult:
    """跨平台统一的动作执行结果。"""

    action_id: str
    action_type: str
    success: bool
    message: str
    target: str | None = None
    error_code: str | None = None
