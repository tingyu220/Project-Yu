"""Memory Provenance — Yu v0.0.7.2 Memory Grounding 的核心常量与规则。

本模块是 Memory Grounding 的单一事实来源（Single Source of Truth）：
- source_type 枚举
- verified 判定
- confidence 上限
- personal memory 类型集合
- 归因短语 / 纠正短语 / 记忆探询短语
- 审计事件类型
- 调试开关

任何关于「用户过去说过什么」的陈述，都必须能追溯到这里的 verified 来源。
"""

from __future__ import annotations

import os

# ------------------------------------------------------------------ source types

USER_EXPLICIT = "USER_EXPLICIT"          # 用户明确说出
USER_CONFIRMED = "USER_CONFIRMED"        # 用户确认（Yu 提议，用户说「可以」）
SYSTEM_FACT = "SYSTEM_FACT"              # 系统真实状态（非用户历史）
ASSISTANT_INFERENCE = "ASSISTANT_INFERENCE"  # 模型推断（不得当作用户事实）
SUMMARY_DERIVED = "SUMMARY_DERIVED"      # 每日摘要派生（非原始证据）
UNKNOWN = "UNKNOWN"                      # 无来源（迁移的旧记忆）

SOURCE_TYPES = (
    USER_EXPLICIT,
    USER_CONFIRMED,
    SYSTEM_FACT,
    ASSISTANT_INFERENCE,
    SUMMARY_DERIVED,
    UNKNOWN,
)

# 只有这些来源可以支撑「你之前说过……」等强归因。
VERIFIED_SOURCE_TYPES = frozenset({USER_EXPLICIT, USER_CONFIRMED, SYSTEM_FACT})

# v0.0.7.2 允许长期保存的来源（推断 / 摘要暂不保存）。
WRITABLE_SOURCE_TYPES = frozenset({USER_EXPLICIT, USER_CONFIRMED, SYSTEM_FACT})

# ------------------------------------------------------------------ confidence

_CONFIDENCE_LIMIT = {
    USER_EXPLICIT: 1.0,
    USER_CONFIRMED: 1.0,
    SYSTEM_FACT: 1.0,
    SUMMARY_DERIVED: 0.6,
    ASSISTANT_INFERENCE: 0.5,
    UNKNOWN: 0.5,
}


def confidence_for(source_type: str | None) -> float:
    """返回某来源允许的默认 / 上限置信度。"""
    if source_type is None:
        return _CONFIDENCE_LIMIT[UNKNOWN]
    return _CONFIDENCE_LIMIT.get(source_type, _CONFIDENCE_LIMIT[UNKNOWN])


def is_verified_source(source_type: str | None) -> bool:
    return source_type in VERIFIED_SOURCE_TYPES


# ------------------------------------------------------------------ personal types

# 属于「用户个人事实 / 历史」的记忆类型；这些类型的写入必须满足最严格的来源要求。
PERSONAL_MEMORY_TYPES = frozenset({
    "fact",
    "personal_fact",
    "goal",
    "preference",
    "health",
    "relationship",
    "decision",
    "history",
})


def is_personal_type(type_: str | None) -> bool:
    return type_ in PERSONAL_MEMORY_TYPES


# ------------------------------------------------------------------ audit events

AUDIT_MEMORY_CLAIM_UNSUPPORTED = "MEMORY_CLAIM_UNSUPPORTED"
AUDIT_MEMORY_CORRECTED = "MEMORY_CORRECTED"
AUDIT_MEMORY_INVALIDATED = "MEMORY_INVALIDATED"
AUDIT_MEMORY_HALLUCINATION = "MEMORY_HALLUCINATION"
AUDIT_MEMORY_WRITE_REJECTED = "MEMORY_WRITE_REJECTED"
AUDIT_MEMORY_CREATED = "MEMORY_CREATED"
AUDIT_MEMORY_UPDATED = "MEMORY_UPDATED"
AUDIT_MEMORY_ARCHIVED = "MEMORY_ARCHIVED"

# ------------------------------------------------------------------ attribution phrases

# 一旦回答里出现这些短语，就是在做「用户历史归因」，必须有 verified memory 支撑。
ATTRIBUTION_PHRASES = (
    "你之前说过", "你之前说", "你之前提到", "你之前提过",
    "我记得你", "我们以前讨论过", "我们之前讨论过",
    "根据你过去", "根据你之前",
    "你过去", "你以前说过", "你以前说", "你曾经说过", "你曾经",
    "你说过", "你提到过", "你提过",
    "你昨天说", "你昨天提到", "你上次说", "你上次提到",
    "你告诉过我", "你跟我说过", "你曾说过", "你曾提到",
)

# 用户纠正 Yu 的错误记忆（触发 Correction Flow）。
CORRECTION_PHRASES = (
    "我没说过", "我没有说过", "我没这么说过", "我没有这么说过",
    "我没提过", "我没有提过", "我从来没", "我从未说过",
    "你记错了", "记错了", "这不是我说的", "不是这样的",
)

# 用户在「询问自己是否说过某件事」（No-Evidence Question，走确定性回答）。
PROBE_PHRASES = (
    "我以前说过", "我之前说过", "我之前提到过", "我之前跟你说过",
    "我有没有说过", "我有没有提到过", "我跟你提过", "我说过我",
    "我记得我好像", "我是不是说过", "我是不是提到过",
)


def detect_phrases(text: str, phrases: tuple[str, ...]) -> list[str]:
    """返回 text 中命中的所有短语（按长度降序，去重）。"""
    found: list[str] = []
    for p in phrases:
        if p in text:
            found.append(p)
    found.sort(key=len, reverse=True)
    return found


def is_memory_probe(text: str) -> bool:
    """判断用户是否在「询问自己是否说过某件事」（No-Evidence Question）。

    例如：「我以前说过我膝盖疼吗？」——命中 PROBE_PHRASES 且带疑问语气。
    """
    if not detect_phrases(text, PROBE_PHRASES):
        return False
    return ("吗" in text) or ("？" in text) or ("?" in text) or ("么" in text)
    """返回 text 中命中的所有短语（按长度降序，去重）。"""
    found: list[str] = []
    for p in phrases:
        if p in text:
            found.append(p)
    found.sort(key=len, reverse=True)
    return found


# ------------------------------------------------------------------ standard replies

NO_RELIABLE_MEMORY_REPLY = "我目前没有可靠记忆显示你之前提到过这个。"

# ------------------------------------------------------------------ debug

def memory_debug_enabled() -> bool:
    """开发模式记忆调试开关：YU_MEMORY_DEBUG=1。"""
    return os.environ.get("YU_MEMORY_DEBUG") == "1"


def memory_debug_emit(**fields: object) -> None:
    """YU_MEMORY_DEBUG=1 时把结构化字段打印到 stderr。

    只用于记忆溯源，调用方禁止传入 API Key / Secret / Token。
    """
    if not memory_debug_enabled():
        return
    import sys

    lines = ["YU_MEMORY_DEBUG:"]
    for key, value in fields.items():
        lines.append(f"  {key}: {value}")
    print("\n".join(lines), file=sys.stderr)