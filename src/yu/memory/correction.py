"""MemoryCorrectionService — 用户纠正错误记忆时的 Correction Flow。

流程（方案 §30-32）：
    User Correction
    ↓
    Search relevant Memory
    ↓
    Memory exists?
       ├─ 是 → Invalidate Memory + 记录 MEMORY_CORRECTED / MEMORY_INVALIDATED 审计
       └─ 否 → Generation Hallucination + 记录 MEMORY_HALLUCINATION 审计

同时会在 append-only events 表写入一条 correction event，保留完整历史。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from .provenance import (
    AUDIT_MEMORY_CORRECTED,
    AUDIT_MEMORY_HALLUCINATION,
    AUDIT_MEMORY_INVALIDATED,
    CORRECTION_PHRASES,
    detect_phrases,
)


def is_correction(text: str) -> bool:
    """判断用户输入是否在纠正 Yu 的错误记忆（如「我没说过这个」）。"""
    return bool(detect_phrases(text, CORRECTION_PHRASES))


@dataclass(frozen=True)
class CorrectionResult:
    kind: str  # "invalidated" | "generation_hallucination"
    target_memory_id: Optional[int]
    reason: str


class MemoryCorrectionService:
    """执行 Correction Flow；依赖 duck-typed store（MemoryStore）与 audit（AuditStore）。"""

    def __init__(self, store, audit):
        self._store = store
        self._audit = audit

    def handle_correction(
        self,
        user_statement: str,
        target_memory_id: Optional[int] = None,
        query: Optional[str] = None,
    ) -> CorrectionResult:
        """处理一次用户纠正。返回结果并写入审计 + correction event。

        - target_memory_id 给出时直接查该记忆；
        - 否则用 query（或 user_statement 本身）检索最相关的记忆作为候选。
        """
        memory = None
        if target_memory_id is not None:
            memory = self._store.get_memory(target_memory_id)
        elif self._store.retrieve is not None:
            matches = self._store.retrieve(query or user_statement, limit=1)
            if matches:
                memory = matches[0][0]

        self._record_correction_event(user_statement, memory)

        if memory is not None:
            self._store.invalidate_memory(memory.id)
            self._audit.record(
                event_type=AUDIT_MEMORY_INVALIDATED,
                actor="yu",
                reason="用户指出该记忆错误，已作废",
                metadata={
                    "user_statement": user_statement,
                    "target_memory_id": memory.id,
                    "target_memory_content": memory.content,
                },
            )
            self._audit.record(
                event_type=AUDIT_MEMORY_CORRECTED,
                actor="yu",
                reason="用户纠正错误记忆",
                metadata={
                    "user_statement": user_statement,
                    "target_memory_id": memory.id,
                    "result": "invalidated",
                },
            )
            return CorrectionResult(
                kind="invalidated", target_memory_id=memory.id,
                reason="已作废该错误记忆",
            )

        self._audit.record(
            event_type=AUDIT_MEMORY_HALLUCINATION,
            actor="yu",
            reason="Yu 使用了无记忆支撑的历史归因，用户否认",
            metadata={
                "user_statement": user_statement,
                "target_memory": None,
                "result": "generation_hallucination",
            },
        )
        return CorrectionResult(
            kind="generation_hallucination", target_memory_id=None,
            reason="无对应记忆，判定为生成幻觉",
        )

    def _record_correction_event(self, user_statement: str, memory) -> None:
        """在 append-only events 表写入一条 correction event。"""
        payload = {
            "event_type": "MEMORY_CORRECTION",
            "user_statement": user_statement,
            "target_memory": memory.id if memory is not None else None,
            "result": "invalidated" if memory is not None else "generation_hallucination",
        }
        self._store.add_event(
            type="memory_correction",
            content=json.dumps(payload, ensure_ascii=False),
            role="system",
        )
