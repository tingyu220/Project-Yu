"""Risk Engine — 统一的 RiskLevel 分类（R0-R4）。

风险由 Capability 权威判定，而非信任提议者（LLM/Planner）自报的风险等级。
"""

from __future__ import annotations

from enum import Enum


class RiskLevel(str, Enum):
    R0 = "R0"
    R1 = "R1"
    R2 = "R2"
    R3 = "R3"
    R4 = "R4"

    @property
    def label(self) -> str:
        return _LABELS[self]

    @property
    def rank(self) -> int:
        return int(self.value[1:])


_LABELS = {
    RiskLevel.R0: "READ_ONLY",
    RiskLevel.R1: "LOW",
    RiskLevel.R2: "MODERATE",
    RiskLevel.R3: "HIGH",
    RiskLevel.R4: "CRITICAL",
}

# 已知 Capability -> 权威风险等级
CAPABILITY_RISK: dict[str, RiskLevel] = {
    "conversation.read": RiskLevel.R0,
    "memory.read": RiskLevel.R0,
    "memory.write": RiskLevel.R1,
    "system.status.read": RiskLevel.R0,
    "file.read": RiskLevel.R0,
    "file.write": RiskLevel.R2,
    "process.read": RiskLevel.R0,
    "process.start": RiskLevel.R2,
    "process.stop": RiskLevel.R2,
    "network.read": RiskLevel.R0,
    "network.request": RiskLevel.R3,
    "system.modify": RiskLevel.R3,
    "code.execute": RiskLevel.R3,
    # 受保护 / 高危能力
    "owner.modify": RiskLevel.R4,
    "owner.delete": RiskLevel.R4,
    "audit.disable": RiskLevel.R4,
    "audit.modify": RiskLevel.R4,
    "safety.modify": RiskLevel.R4,
    "safety.disable": RiskLevel.R4,
    "constitution.modify": RiskLevel.R4,
}

# 用于展示的已知能力列表（有序）
KNOWN_CAPABILITIES: list[str] = [
    "conversation.read",
    "memory.read",
    "memory.write",
    "system.status.read",
    "file.read",
    "file.write",
    "process.read",
    "process.start",
    "process.stop",
    "network.read",
    "network.request",
    "system.modify",
    "code.execute",
    "owner.modify",
    "audit.disable",
    "safety.modify",
]


def classify(capability: str) -> RiskLevel:
    """返回 capability 的权威风险等级；未知能力按 R4（CRITICAL）保守处理。"""
    return CAPABILITY_RISK.get(capability, RiskLevel.R4)
