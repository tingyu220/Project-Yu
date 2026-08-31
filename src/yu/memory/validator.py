"""MemoryWriteValidator — 所有 Personal Memory 写入必经的写入门。

规则（见方案 §12 / §43-48）：
- Assistant 内容不能成为用户事实。
- 推断 / 摘要不能写入长期 Personal Memory（v0.0.7.2 暂不保存）。
- 无来源（source_event_id 为空）的 Personal Memory 禁止写入，除非 SYSTEM_FACT。
- Personal Memory 的 source_role 必须是 user，除非 SYSTEM_FACT。
- 置信度不得超过该 source_type 的上限。

验证失败会抛出 MemoryWriteError（附带错误码，用于审计 MEMORY_WRITE_REJECTED）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .provenance import (
    ASSISTANT_INFERENCE,
    SYSTEM_FACT,
    SUMMARY_DERIVED,
    UNKNOWN,
    WRITABLE_SOURCE_TYPES,
    confidence_for,
    is_personal_type,
)

# 错误码（供审计与测试断言）
ASSISTANT_CONTENT_CANNOT_CREATE_USER_FACT = "ASSISTANT_CONTENT_CANNOT_CREATE_USER_FACT"
INFERENCE_CANNOT_CREATE_USER_FACT = "INFERENCE_CANNOT_CREATE_USER_FACT"
SUMMARY_DERIVED_CANNOT_CREATE_USER_FACT = "SUMMARY_DERIVED_CANNOT_CREATE_USER_FACT"
PERSONAL_MEMORY_REQUIRES_USER_SOURCE = "PERSONAL_MEMORY_REQUIRES_USER_SOURCE"
MEMORY_WRITE_REJECTED_UNGROUNDED = "MEMORY_WRITE_REJECTED_UNGROUNDED"
UNKNOWN_SOURCE_NOT_WRITABLE = "UNKNOWN_SOURCE_NOT_WRITABLE"
CONFIDENCE_EXCEEDS_SOURCE_LIMIT = "CONFIDENCE_EXCEEDS_SOURCE_LIMIT"


class MemoryWriteError(Exception):
    """记忆写入被写入门拒绝。"""

    def __init__(self, reason: str, code: str = "MEMORY_WRITE_REJECTED"):
        super().__init__(reason)
        self.reason = reason
        self.code = code


@dataclass(frozen=True)
class WriteDecision:
    allowed: bool
    reason: str = ""
    code: str = ""

    @classmethod
    def ok(cls) -> "WriteDecision":
        return cls(allowed=True)

    @classmethod
    def deny(cls, reason: str, code: str) -> "WriteDecision":
        return cls(allowed=False, reason=reason, code=code)


class MemoryWriteValidator:
    """对一次记忆写入执行 Source → Role → Type → Confidence 检查。"""

    def validate(
        self,
        *,
        type: str,
        content: str,
        source_type: Optional[str],
        source_role: Optional[str],
        source_event_id: Optional[int],
        confidence: Optional[float] = None,
    ) -> WriteDecision:
        del content  # content 本身不参与来源校验，仅保留签名以便未来扩展

        if source_type is None:
            source_type = UNKNOWN

        # 1. Assistant 输出不能成为用户事实（最高优先级，先于 source_type 判定）。
        if source_role == "assistant":
            return WriteDecision.deny(
                "assistant 生成的内容不能成为用户事实", ASSISTANT_CONTENT_CANNOT_CREATE_USER_FACT
            )

        # 2. 本版本只允许长期保存 verified 来源；推断 / 摘要 / 未知来源一律拒绝。
        if source_type == ASSISTANT_INFERENCE:
            return WriteDecision.deny(
                "模型推断不能写入长期个人记忆", INFERENCE_CANNOT_CREATE_USER_FACT
            )
        if source_type == SUMMARY_DERIVED:
            return WriteDecision.deny(
                "每日摘要不能成为已验证的用户事实", SUMMARY_DERIVED_CANNOT_CREATE_USER_FACT
            )
        if source_type not in WRITABLE_SOURCE_TYPES:
            return WriteDecision.deny(
                f"来源 {source_type} 不允许写入长期记忆", UNKNOWN_SOURCE_NOT_WRITABLE
            )

        # 3. Personal Memory：source_role 必须是 user（除非 SYSTEM_FACT）。
        if is_personal_type(type) and source_type != SYSTEM_FACT:
            if source_role != "user":
                return WriteDecision.deny(
                    "个人记忆必须来自用户明确表达", PERSONAL_MEMORY_REQUIRES_USER_SOURCE
                )
            if source_event_id is None:
                return WriteDecision.deny(
                    "无来源的个人记忆禁止写入", MEMORY_WRITE_REJECTED_UNGROUNDED
                )

        # 4. 置信度不得超出来源上限。
        if confidence is not None:
            ceiling = confidence_for(source_type)
            if confidence > ceiling + 1e-9:
                return WriteDecision.deny(
                    f"{source_type} 的置信度不能超过 {ceiling}", CONFIDENCE_EXCEEDS_SOURCE_LIMIT
                )

        return WriteDecision.ok()