"""Capability-based Permission System — Default Deny。

没有显式授予的能力一律不允许。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from .risk import RiskLevel, classify

# v0.0.2.1 默认只开放这三项
DEFAULT_GRANTED = {
    "conversation.read",
    "memory.read",
    "memory.write",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Permission:
    capability: str
    status: str
    risk_level: RiskLevel
    granted_by: str
    created_at: str
    expires_at: Optional[str]
    scope: str


class PermissionEngine:
    def __init__(self, owner_id: str, audit=None):
        self.owner_id = owner_id
        self.audit = audit
        self._grants: dict[str, Permission] = {}
        self._seed_defaults()

    def _seed_defaults(self) -> None:
        for cap in sorted(DEFAULT_GRANTED):
            self._grants[cap] = Permission(
                capability=cap,
                status="granted",
                risk_level=classify(cap),
                granted_by="owner",
                created_at=_now(),
                expires_at=None,
                scope="local_machine",
            )

    def has_permission(self, capability: str) -> bool:
        p = self._grants.get(capability)
        return p is not None and p.status == "granted"

    def list(self) -> list[Permission]:
        return [self._grants[c] for c in sorted(self._grants)]

    def grant(self, capability: str, granted_by: str = "owner", scope: str = "local_machine") -> Permission:
        p = Permission(
            capability=capability,
            status="granted",
            risk_level=classify(capability),
            granted_by=granted_by,
            created_at=_now(),
            expires_at=None,
            scope=scope,
        )
        self._grants[capability] = p
        if self.audit is not None:
            self.audit.record(
                event_type="PERMISSION_GRANT",
                actor=granted_by,
                reason=f"grant capability: {capability}",
                metadata={"capability": capability, "scope": scope},
            )
        return p

    def revoke(self, capability: str, revoked_by: str = "owner") -> None:
        self._grants.pop(capability, None)
        if self.audit is not None:
            self.audit.record(
                event_type="PERMISSION_REVOKE",
                actor=revoked_by,
                reason=f"revoke capability: {capability}",
                metadata={"capability": capability},
            )
