"""MemoryService — 统一 Memory CRUD Service（方案 §26-35）。

所有 Memory 写操作必须经本 Service（禁止 LLM 直接操作 DB）：
- Create / Update / Archive 均执行 Read-After-Write 验证，只有验证通过才返回 success。
- 返回标准化 MemoryResult，LLM 只能依据该结果回复（禁止「我觉得已保存」）。
- 每次写操作记录审计（MEMORY_CREATED / MEMORY_UPDATED / MEMORY_ARCHIVED / ...）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .correction import MemoryCorrectionService
from .provenance import (
    AUDIT_MEMORY_ARCHIVED,
    AUDIT_MEMORY_CREATED,
    AUDIT_MEMORY_UPDATED,
    AUDIT_MEMORY_WRITE_REJECTED,
    USER_EXPLICIT,
    memory_debug_emit,
)
from .validator import MemoryWriteError


@dataclass(frozen=True)
class MemoryResult:
    operation: str
    success: bool
    verified: bool
    memory_id: Optional[int] = None
    before: Optional[str] = None
    after: Optional[str] = None
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "memory_id": self.memory_id,
            "success": self.success,
            "verified": self.verified,
            "before": self.before,
            "after": self.after,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ReferenceResolution:
    memory_id: Optional[int]
    reason: str


class MemoryService:
    """Memory CRUD + Read-After-Write + 审计；依赖 duck-typed store 与 audit。"""

    def __init__(self, store, audit):
        self._store = store
        self._audit = audit

    # ------------------------------------------------------------------ Create

    def create(self, content: str, type: str = "fact", importance: str = "high") -> MemoryResult:
        content = content.strip()
        if not content:
            return MemoryResult("create", False, False, reason="内容为空，未保存。")
        try:
            m = self._store.add_user_memory(
                type=type, content=content, importance=importance, source_type=USER_EXPLICIT
            )
        except MemoryWriteError as e:
            self._audit.record(
                event_type=AUDIT_MEMORY_WRITE_REJECTED,
                actor="yu",
                reason=e.reason,
                metadata={"code": e.code, "content": content},
            )
            return MemoryResult("create", False, False, reason=e.reason)

        got = self._store.get_memory(m.id)
        ok = got is not None and got.content == content
        memory_debug_emit(
            INPUT=content, INTENT="MEMORY_CREATE", MEMORY_COMMAND="create",
            DATABASE_RESULT="inserted", READ_AFTER_WRITE_RESULT=("verified" if ok else "MISMATCH"),
        )
        if not ok:
            return MemoryResult("create", False, False, memory_id=m.id, reason="写入后验证失败。")
        self._audit.record(
            event_type=AUDIT_MEMORY_CREATED,
            actor="yu",
            reason="创建记忆",
            metadata={"memory_id": m.id, "content": content, "type": type},
        )
        return MemoryResult("create", True, True, memory_id=m.id, after=content)

    # ------------------------------------------------------------------ Update

    def update(self, memory_id: int, new_content: str) -> MemoryResult:
        new_content = new_content.strip()
        if not new_content:
            return MemoryResult("update", False, False, memory_id=memory_id, reason="新内容为空。")

        old = self._store.get_memory(memory_id)
        if old is None:
            return MemoryResult("update", False, False, memory_id=memory_id, reason="更新失败，没有找到目标 Memory。")

        updated = self._store.update_memory(memory_id, new_content)
        if updated is None:
            # affected_rows = 0：目标不存在或已归档 —— 禁止假装成功。
            return MemoryResult(
                "update", False, False, memory_id=memory_id,
                before=old.content, reason="更新失败，没有找到目标 Memory。",
            )

        got = self._store.get_memory(memory_id)
        ok = got is not None and got.content == new_content
        memory_debug_emit(
            INPUT=new_content, INTENT="MEMORY_UPDATE", MEMORY_COMMAND="update",
            MEMORY_ID=memory_id, DATABASE_RESULT="updated",
            READ_AFTER_WRITE_RESULT=("verified" if ok else "MISMATCH"),
        )
        if not ok:
            return MemoryResult("update", False, False, memory_id=memory_id, before=old.content, reason="更新未通过读后验证。")
        self._audit.record(
            event_type=AUDIT_MEMORY_UPDATED,
            actor="yu",
            reason="更新记忆",
            metadata={"memory_id": memory_id, "before": old.content, "after": new_content, "requested_by": "owner"},
        )
        return MemoryResult("update", True, True, memory_id=memory_id, before=old.content, after=new_content)

    # ------------------------------------------------------------------ Archive

    def archive(self, memory_id: int) -> MemoryResult:
        old = self._store.get_memory(memory_id)
        if old is None:
            return MemoryResult("archive", False, False, memory_id=memory_id, reason="没有找到目标 Memory。")

        archived = self._store.archive_memory(memory_id)
        if archived is None:
            return MemoryResult("archive", False, False, memory_id=memory_id, reason="归档失败，没有找到目标 Memory。")

        got = self._store.get_memory(memory_id)
        ok = got is not None and got.status == "archived"
        memory_debug_emit(
            INTENT="MEMORY_ARCHIVE", MEMORY_COMMAND="archive", MEMORY_ID=memory_id,
            DATABASE_RESULT="archived", READ_AFTER_WRITE_RESULT=("verified" if ok else "MISMATCH"),
        )
        if not ok:
            return MemoryResult("archive", False, False, memory_id=memory_id, before=old.content, reason="归档未通过读后验证。")
        self._audit.record(
            event_type=AUDIT_MEMORY_ARCHIVED,
            actor="yu",
            reason="归档记忆",
            metadata={"memory_id": memory_id, "before": old.content, "requested_by": "owner"},
        )
        return MemoryResult("archive", True, True, memory_id=memory_id, before=old.content)

    # ------------------------------------------------------------------ Correct

    def correct(self, user_statement: str, target_memory_id: Optional[int] = None):
        """委托给 MemoryCorrectionService（invalidate 或 generation_hallucination）。"""
        return MemoryCorrectionService(self._store, self._audit).handle_correction(
            user_statement, target_memory_id=target_memory_id
        )

    # ------------------------------------------------------------------ Reference

    def resolve_reference(
        self,
        referenced_ids: Optional[list[int]],
        candidates,
    ) -> ReferenceResolution:
        """解析「这条记忆」指代：1 条直接绑定，多条必须询问，禁止猜测。"""
        ids = [i for i in (referenced_ids or []) if i is not None]
        if len(ids) == 1:
            return ReferenceResolution(memory_id=ids[0], reason="")
        if len(ids) > 1:
            return ReferenceResolution(
                memory_id=None,
                reason="你指的是哪一条？（可选 id：" + ", ".join(str(i) for i in ids) + "）",
            )

        cands = list(candidates)
        if len(cands) == 1:
            return ReferenceResolution(memory_id=cands[0].id, reason="")
        if not cands:
            return ReferenceResolution(memory_id=None, reason="当前没有可操作的有效记忆。")
        return ReferenceResolution(
            memory_id=None,
            reason="你指的是哪一条？（当前记忆 id：" + ", ".join(str(m.id) for m in cands) + "）",
        )
