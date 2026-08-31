"""Memory Retrieval — 关键词 + importance + 时间的简单排序。

按计划，第一版不上向量库 / embedding；先用关键词 + Memory Type + 时间 + Importance
做简单排序。

v0.0.7.2 Memory Grounding：
- retrieve 结果保留每条 Memory 的 provenance（source_type / source_event_id / confidence）。
- build_context 把记忆分为 [VERIFIED USER MEMORY] 与 [UNVERIFIED OBSERVATION]，
  只有 verified 记忆才允许支撑「你之前说过……」的强归因。
"""

from __future__ import annotations

import re
from typing import Sequence

from .models import Memory

_IMPORTANCE_WEIGHT = {"high": 1.0, "medium": 0.5, "low": 0.0}

# 常见停用词，避免通用词造成误匹配
_STOPWORDS = {"用户", "我们", "你们", "他们", "什么", "这个", "那个", "一个", "现在", "可能", "就是", "可以"}


def tokenize(text: str) -> set[str]:
    """提取检索关键词：ASCII 单词 + 中文二元组（bigram），过滤常见停用词。"""
    terms: set[str] = set(re.findall(r"[a-z0-9]+", text.lower()))
    for run in re.findall(r"[\u4e00-\u9fff]+", text):
        for i in range(len(run) - 1):
            terms.add(run[i:i + 2])
    return {t for t in terms if t not in _STOPWORDS}


def score(memory: Memory, query: str) -> float:
    """相关性评分：关键词重叠 * 2 + importance 权重；无重叠返回 0。"""
    qterms = tokenize(query)
    if not qterms:
        return 0.0
    content = memory.content.lower()
    overlap = sum(1 for t in qterms if t in content)
    if overlap == 0:
        return 0.0
    return overlap * 2.0 + _IMPORTANCE_WEIGHT.get(memory.importance, 0.0)


def retrieve(memories: Sequence[Memory], query: str, limit: int = 5) -> list[tuple[Memory, float]]:
    """返回按相关性降序的 (memory, score) 列表；分数相同按 id（新→旧）靠前。"""
    scored = [(m, score(m, query)) for m in memories]
    scored = [(m, s) for m, s in scored if s > 0.0]
    scored.sort(key=lambda x: (x[1], x[0].id), reverse=True)
    return scored[:limit]


def format_memory_line(memory: Memory) -> str:
    """单条记忆的可读来源标注行（用于 daily / planner 的输入，避免来源被抹平）。"""
    tag = memory.source_type or "UNKNOWN"
    return f"- [{tag}] {memory.content}"


def _section_verified(matches: Sequence[tuple[Memory, float]]) -> list[str]:
    lines = ["[VERIFIED USER MEMORY]", "以下内容有明确来源，可作为用户历史事实引用："]
    for m, _ in matches:
        lines.append(
            f"{m.memory_id} | 来源:{m.source_type} | 证据:{m.source_event_id} | 置信度:{m.confidence}"
        )
        lines.append(f"用户曾明确表达：{m.content}")
    return lines


def _section_unverified(matches: Sequence[tuple[Memory, float]]) -> list[str]:
    lines = [
        "[UNVERIFIED OBSERVATION]",
        "以下内容不是用户明确陈述的事实，仅供弱参考，禁止当作用户历史：",
    ]
    for m, _ in matches:
        lines.append(f"{m.memory_id} | 来源:{m.source_type} | 置信度:{m.confidence}")
        lines.append(m.content)
    return lines


_GROUNDING_RULE = (
    "归因规则：只有 [VERIFIED USER MEMORY] 中的内容可以用于「你之前说过 / 你之前提到 / "
    "我记得你 / 我们以前讨论过」等历史归因；禁止把观察、推断或你自己的建议当作用户历史。"
    "没有证据时，应明确说明「没有可靠记忆」，而不是编造用户过去说过或做过的事。"
)


def build_context(matches: Sequence[tuple[Memory, float]]) -> str:
    """把检索结果拼成注入 LLM 的上下文文本；无结果返回空串。

    按 provenance 分区，避免把 assistant/summary/推断内容混入「用户记忆」。
    """
    if not matches:
        return ""
    verified = [(m, s) for m, s in matches if m.verified]
    unverified = [(m, s) for m, s in matches if not m.verified]

    lines = ["以下是关于你（当前用户）的长期记忆。请只依据这些记忆回答，不要编造额外的信息："]
    if verified:
        lines.append("")
        lines.extend(_section_verified(verified))
    if unverified:
        lines.append("")
        lines.extend(_section_unverified(unverified))
    lines.append("")
    lines.append(_GROUNDING_RULE)
    return "\n".join(lines)


def memory_debug_trace(matches: Sequence[tuple[Memory, float]]) -> str:
    """开发模式调试信息（YU_MEMORY_DEBUG=1）：打印检索到的记忆 ID / 来源 / 置信度。

    只包含记忆字段，绝不包含 API Key / Secret。
    """
    if not matches:
        return "YU_MEMORY_DEBUG: 未检索到相关记忆"
    lines = ["YU_MEMORY_DEBUG: 检索到的记忆："]
    for m, s in matches:
        lines.append(
            f"- {m.memory_id} source_type={m.source_type} source_role={m.source_role} "
            f"source_event_id={m.source_event_id} confidence={m.confidence} "
            f"verified={m.verified} score={s}"
        )
        lines.append(f"  content: {m.content}")
    return "\n".join(lines)
