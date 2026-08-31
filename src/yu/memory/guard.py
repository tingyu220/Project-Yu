"""MemoryAttributionGuard — 检测回答是否使用了「用户历史归因」并检查证据。

原理（方案 §24-28）：
- 识别「你之前说过 / 你之前提到 / 我记得你 …」等历史归因措辞。
- 每一个历史归因都必须在 context 中有 verified memory 支撑（内容层面重叠）。
- 无支撑的历史归因 → 标记 unsupported（供审计 MEMORY_CLAIM_UNSUPPORTED，并可 BLOCK/REWRITE）。

V0 不做复杂 NLP：用「归因短语命中 + 与 verified memory 的内容 token 重叠」做判断。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from .models import Memory
from .provenance import ATTRIBUTION_PHRASES, detect_phrases
from .retrieval import tokenize

# 归因短语前后抓取的字数，用于提取「被归因的主体」。
_CLAIM_WINDOW = 16


@dataclass(frozen=True)
class AttributionVerdict:
    has_claim: bool
    supported: bool
    claims: list[str] = field(default_factory=list)
    unsupported_claims: list[str] = field(default_factory=list)

    @property
    def needs_block(self) -> bool:
        """是否需要 BLOCK / REWRITE：存在归因但没有证据支撑。"""
        return self.has_claim and not self.supported


def detect_historical_claims(text: str) -> list[str]:
    """返回 text 中命中的所有历史归因短语。"""
    return detect_phrases(text, ATTRIBUTION_PHRASES)


def _claim_window(text: str, phrase: str, window: int = _CLAIM_WINDOW) -> str:
    idx = text.find(phrase)
    if idx < 0:
        return text
    start = max(0, idx - window)
    end = min(len(text), idx + len(phrase) + window)
    return text[start:end]


def has_verified_support(text: str, memories: Sequence[Memory]) -> bool:
    """判断 text 是否与任意 verified 记忆存在内容 token 重叠（No-Evidence 探询用）。"""
    terms = tokenize(text)
    if not terms:
        return True
    verified = [m for m in memories if m.verified]
    return any(terms & tokenize(m.content) for m in verified)


def _overlaps(claim_text: str, memory: Memory) -> bool:
    """claim 与 memory 内容是否存在 token 重叠（中文 bigram / ASCII 词）。"""
    terms = tokenize(claim_text)
    if not terms:
        return True  # 没有可提取的主体词时，不轻易判为「无证据」。
    mem_terms = tokenize(memory.content)
    return bool(terms & mem_terms)


class MemoryAttributionGuard:
    """判断一条 assistant 回答中的历史归因是否有 verified 证据支撑。"""

    def check(
        self,
        text: str,
        supporting_memories: Sequence[Memory],
    ) -> AttributionVerdict:
        claims = detect_historical_claims(text)
        if not claims:
            return AttributionVerdict(has_claim=False, supported=True)

        verified = [m for m in supporting_memories if m.verified]
        unsupported: list[str] = []
        for phrase in claims:
            window = _claim_window(text, phrase)
            if not any(_overlaps(window, m) for m in verified):
                unsupported.append(phrase)

        supported = not unsupported
        return AttributionVerdict(
            has_claim=True,
            supported=supported,
            claims=claims,
            unsupported_claims=unsupported,
        )