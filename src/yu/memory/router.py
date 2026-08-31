"""Memory Intent Router — 确定性记忆命令识别（Explicit Intent > Inferred Routing）。

原则（方案 §20-25）：
- 用户明确表达的 Memory 命令（记住 / 修改 / 忘掉 / 纠正）必须先于 Tool Router 处理。
- 「提到某个能力 ≠ 请求该能力」：Declarative 语句不得误触发 Computer Context 等 Tool。
- 关键词路由（is_plan_request / is_computer_request）只能在 Memory Intent 判定为 None 之后运行。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .correction import is_correction

MEMORY_CREATE = "MEMORY_CREATE"
MEMORY_READ = "MEMORY_READ"
MEMORY_SEARCH = "MEMORY_SEARCH"
MEMORY_UPDATE = "MEMORY_UPDATE"
MEMORY_CORRECT = "MEMORY_CORRECT"
MEMORY_ARCHIVE = "MEMORY_ARCHIVE"

_CREATE_MARKERS = ("记住", "保存这段", "保存这条", "保存", "帮我记住", "记一下", "加入记忆")
_UPDATE_MARKERS = ("修改这条记忆", "更新这条记忆", "修改记忆", "更新记忆", "把刚刚那条改成", "改为", "改成", "更新这个", "修改这条")
_ARCHIVE_MARKERS = ("忘掉这个", "忘掉这条", "不再记住这个", "删除这条记忆", "别记这个")
_READ_MARKERS = ("显示记忆", "列出记忆", "查看记忆", "我的记忆", "记忆列表")
_SEARCH_MARKERS = ("搜索记忆", "查找记忆", "找一下记忆")

_LEAD_WORDS = ("以下内容", "这些", "这条", "这段")


@dataclass(frozen=True)
class MemoryIntent:
    intent: str
    payload: str
    memory_id: Optional[int] = None


def _strip_lead(text: str) -> str:
    s = text.strip()
    for lead in _LEAD_WORDS:
        if s.startswith(lead):
            s = s[len(lead):]
            break
    return s.lstrip("：: 　,，。. ").strip()


def _extract_create(text: str) -> str:
    s = text
    for m in _CREATE_MARKERS:
        idx = s.find(m)
        if idx >= 0:
            s = s[idx + len(m):]
            break
    return _strip_lead(s)


def _extract_update(text: str) -> str:
    s = text
    for m in _UPDATE_MARKERS:
        idx = s.find(m)
        if idx >= 0:
            s = s[idx + len(m):]
            break
    s = s.strip()
    for sep in ("改为", "改成", "为", "：", ":", "是"):
        if s.startswith(sep):
            s = s[len(sep):]
            break
    return _strip_lead(s)


def detect_memory_intent(text: str) -> Optional[MemoryIntent]:
    """识别 Memory 命令；不是 Memory 命令时返回 None（交给 General Router）。"""
    t = text.strip()
    if not t:
        return None

    # 纠正优先（「我没说过 / 这个记忆错了」）。
    if is_correction(t):
        return MemoryIntent(intent=MEMORY_CORRECT, payload=t)

    for m in _UPDATE_MARKERS:
        if m in t:
            return MemoryIntent(intent=MEMORY_UPDATE, payload=_extract_update(t))

    for m in _ARCHIVE_MARKERS:
        if m in t:
            return MemoryIntent(intent=MEMORY_ARCHIVE, payload=t)

    for m in _CREATE_MARKERS:
        if m in t:
            return MemoryIntent(intent=MEMORY_CREATE, payload=_extract_create(t))

    for m in _SEARCH_MARKERS:
        if m in t:
            return MemoryIntent(intent=MEMORY_SEARCH, payload=t)

    for m in _READ_MARKERS:
        if m in t:
            return MemoryIntent(intent=MEMORY_READ, payload=t)
    if t in ("记忆", "我的记忆"):
        return MemoryIntent(intent=MEMORY_READ, payload=t)

    return None
