"""Memory Retrieval — 第一版：关键词 + importance + 时间的简单排序。

按计划，第一版不上向量库 / embedding；先用关键词 + Memory Type + 时间 + Importance
做简单排序，等有真实数据后再评估是否引入 embedding。
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


def build_context(matches: Sequence[tuple[Memory, float]]) -> str:
    """把检索结果拼成注入 LLM 的上下文文本；无结果返回空串。"""
    if not matches:
        return ""
    lines = ["以下是关于你（当前用户）的长期记忆。请只依据这些记忆回答，不要编造额外的信息："]
    lines.extend(f"- {m.content}" for m, _ in matches)
    return "\n".join(lines)
