"""Safety Kernel — Control Plane 的决策核心。

对每个 ProposedAction 执行：风险分类 -> 权限检查 -> 安全检查 -> ALLOW/DENY。
任何引擎异常都 Fail Closed（DENY）。所有判断写入 Audit Log。

核心要求：LLM 只能提出行动，不能直接获得执行权限。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..actions.models import ActionDecision, ProposedAction
from ..audit.store import AuditStore
from ..authority.owner import OwnerManager
from .constitution import SafetyConstitution
from .permissions import PermissionEngine
from .risk import RiskLevel, classify

ACTOR_YU = "yu"

# 永远不可授予的能力：即使存在 grant 也拒绝（受 Safety Constitution 保护）
NEVER_GRANTABLE = {
    "owner.modify",
    "owner.delete",
    "audit.disable",
    "audit.modify",
    "safety.modify",
    "safety.disable",
    "constitution.modify",
}


class SafetyKernel:
    def __init__(
        self,
        constitution: SafetyConstitution,
        permissions: PermissionEngine,
        owner: OwnerManager,
        audit: AuditStore,
    ):
        self.constitution = constitution
        self.permissions = permissions
        self.owner = owner
        self.audit = audit

    def status(self) -> dict:
        return {
            "safety_kernel": "ACTIVE",
            "owner": "ACTIVE" if self.owner.is_active() else "INACTIVE",
            "audit": "ACTIVE",
            "constitution": "VALID" if self.constitution.is_valid else "INVALID",
        }

    def evaluate(self, action: ProposedAction) -> ActionDecision:
        cap = action.required_capability

        # 权威风险分类（不信任提议者自报的风险）
        risk = classify(cap)

        self.audit.record(
            event_type="ACTION_PROPOSED",
            actor=action.proposed_by or ACTOR_YU,
            action_id=action.action_id,
            risk_level=risk.value,
            reason=action.reason,
            metadata={"action_type": action.action_type, "capability": cap},
        )

        # 1) Fail Closed：宪法无效
        if not self.constitution.is_valid:
            return self._deny(
                action, risk,
                "Safety Constitution 无效，Fail Closed（DENY）",
                event_type="SAFETY_KERNEL_ERROR",
            )

        # 2) Fail Closed：Owner 不活跃
        if not self.owner.is_active():
            return self._deny(
                action, risk,
                "Owner 状态异常，Fail Closed（DENY）",
                event_type="SAFETY_KERNEL_ERROR",
            )

        # 3) 受保护能力：永远拒绝（即使被错误授权）
        if cap in NEVER_GRANTABLE:
            return self._deny(
                action, risk,
                f"受保护能力 {cap} 永远拒绝（Safety Constitution）",
                event_type="SAFETY_RULE_VIOLATION",
            )

        # 4) 权限检查：Default Deny；异常时 Fail Closed
        try:
            granted = self.permissions.has_permission(cap)
        except Exception as e:  # noqa: BLE001
            return self._deny(
                action, risk,
                f"Permission Engine 异常：{e}（Fail Closed）",
                event_type="SAFETY_KERNEL_ERROR",
            )

        if not granted:
            return self._deny(
                action, risk,
                f"未授权 capability：{cap}（Default Deny）",
                event_type="ACTION_DENIED",
            )

        # 5) ALLOW
        self.audit.record(
            event_type="ACTION_ALLOWED",
            actor=ACTOR_YU,
            action_id=action.action_id,
            risk_level=risk.value,
            decision="ALLOW",
            reason=f"授权通过：{cap}",
            metadata={"capability": cap},
        )
        return ActionDecision(allowed=True, action_id=action.action_id, risk_level=risk, reason="ALLOW")

    def _deny(
        self,
        action: ProposedAction,
        risk: RiskLevel,
        reason: str,
        event_type: str = "ACTION_DENIED",
    ) -> ActionDecision:
        self.audit.record(
            event_type=event_type,
            actor=ACTOR_YU,
            action_id=action.action_id,
            risk_level=risk.value,
            decision="DENY",
            reason=reason,
            metadata={"capability": action.required_capability},
        )
        return ActionDecision(allowed=False, action_id=action.action_id, risk_level=risk, reason=reason)
