"""SQLite-backed persistent store for the Yu Memory Kernel.

Design guarantees:
- Event is append-only: enforced by both the API (no update method)
  and SQLite triggers (no UPDATE/DELETE on the 'events' table).
- Memory supports Create / Read / Archive / Invalidate; archiving never deletes history.
- Every Memory carries provenance (source_type / source_role / source_event_id /
  confidence). User-facing writes go through MemoryWriteValidator.

分层：
- add_event / add_memory 是底层 DB primitive（迁移、内部、system 用）。
- write_memory / add_user_memory / add_system_fact / remember 是经过写入门
  （MemoryWriteValidator）的正式写入路径。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from .models import Event, Memory, utcnow_iso
from .provenance import (
    ASSISTANT_INFERENCE,
    SYSTEM_FACT,
    UNKNOWN,
    USER_EXPLICIT,
    confidence_for,
)
from .retrieval import retrieve as retrieve_memories
from .validator import MemoryWriteError, MemoryWriteValidator

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    type        TEXT NOT NULL,
    content     TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    role        TEXT NOT NULL DEFAULT 'user'
);

CREATE TABLE IF NOT EXISTS memories (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    type            TEXT NOT NULL,
    content         TEXT NOT NULL,
    importance      TEXT NOT NULL DEFAULT 'medium',
    status          TEXT NOT NULL DEFAULT 'active',
    source_event_id INTEGER,
    source_type     TEXT NOT NULL DEFAULT 'UNKNOWN',
    source_role     TEXT,
    confidence      REAL NOT NULL DEFAULT 0.5,
    created_at      TEXT NOT NULL,
    archived_at     TEXT,
    updated_at      TEXT,
    FOREIGN KEY (source_event_id) REFERENCES events(id)
);

CREATE TRIGGER IF NOT EXISTS events_no_update
BEFORE UPDATE ON events
BEGIN
    SELECT RAISE(ABORT, 'events are append-only: update is not allowed');
END;

CREATE TRIGGER IF NOT EXISTS events_no_delete
BEFORE DELETE ON events
BEGIN
    SELECT RAISE(ABORT, 'events are append-only: delete is not allowed');
END;
"""


class MemoryStore:
    """Persistent store for Events and Memories backed by a SQLite file."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        with self._conn:
            self._conn.executescript(_SCHEMA)
        self._migrate()
        self._validator = MemoryWriteValidator()

    def __enter__(self) -> "MemoryStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        self._conn.close()

    # ---------------------------------------------------------------- migration

    def _migrate(self) -> None:
        """为旧数据库补齐 provenance 列，并为用户来源的旧记忆回填 USER_EXPLICIT。"""
        with self._conn:
            mem_cols = {
                r["name"] for r in self._conn.execute("PRAGMA table_info(memories)").fetchall()
            }
            if "source_type" not in mem_cols:
                self._conn.execute(
                    "ALTER TABLE memories ADD COLUMN source_type TEXT NOT NULL DEFAULT 'UNKNOWN'"
                )
            if "source_role" not in mem_cols:
                self._conn.execute("ALTER TABLE memories ADD COLUMN source_role TEXT")
            if "confidence" not in mem_cols:
                self._conn.execute(
                    "ALTER TABLE memories ADD COLUMN confidence REAL NOT NULL DEFAULT 0.5"
                )
            if "updated_at" not in mem_cols:
                self._conn.execute("ALTER TABLE memories ADD COLUMN updated_at TEXT")
            self._conn.execute(
                "UPDATE memories SET updated_at = created_at WHERE updated_at IS NULL"
            )

            ev_cols = {
                r["name"] for r in self._conn.execute("PRAGMA table_info(events)").fetchall()
            }
            if "role" not in ev_cols:
                self._conn.execute(
                    "ALTER TABLE events ADD COLUMN role TEXT NOT NULL DEFAULT 'user'"
                )

            # 旧记忆：能找到真实 user 事件的，补 USER_EXPLICIT；否则保持 UNKNOWN（不伪造来源）。
            self._conn.execute(
                "UPDATE memories SET source_type = ?, source_role = 'user', confidence = 1.0 "
                "WHERE source_type = ? AND source_event_id IS NOT NULL "
                "AND source_event_id IN (SELECT id FROM events WHERE role = 'user')",
                (USER_EXPLICIT, UNKNOWN),
            )

    # ------------------------------------------------------------------ Events

    def add_event(self, type: str, content: str, role: str = "user") -> Event:
        created_at = utcnow_iso()
        with self._conn:
            cur = self._conn.execute(
                "INSERT INTO events (type, content, created_at, role) VALUES (?, ?, ?, ?)",
                (type, content, created_at, role),
            )
        return Event(id=cur.lastrowid, type=type, content=content, created_at=created_at, role=role)

    def list_events(self) -> list[Event]:
        rows = self._conn.execute(
            "SELECT id, type, content, created_at, role FROM events ORDER BY id"
        ).fetchall()
        return [self._row_to_event(r) for r in rows]

    def get_event(self, event_id: int) -> Optional[Event]:
        row = self._conn.execute(
            "SELECT id, type, content, created_at, role FROM events WHERE id = ?", (event_id,)
        ).fetchone()
        return self._row_to_event(row) if row else None

    # ----------------------------------------------------------------- Memories

    def add_memory(
        self,
        type: str,
        content: str,
        importance: str = "medium",
        source_event_id: Optional[int] = None,
        source_type: Optional[str] = None,
        source_role: Optional[str] = None,
        confidence: Optional[float] = None,
    ) -> Memory:
        """底层 DB primitive：写入一条记忆（不经过写入门）。

        用于迁移、内部 system 写入与测试；用户事实写入请使用 write_memory /
        add_user_memory / remember。
        """
        stype, srole, conf = self._resolve_provenance(source_event_id, source_type, source_role, confidence)
        return self._insert_memory(type, content, importance, source_event_id, stype, srole, conf)

    def write_memory(
        self,
        *,
        type: str,
        content: str,
        importance: str = "medium",
        source_event_id: Optional[int] = None,
        source_type: Optional[str] = None,
        source_role: Optional[str] = None,
        confidence: Optional[float] = None,
    ) -> Memory:
        """正式写入路径：先解析 provenance，再经 MemoryWriteValidator 校验。"""
        stype, srole, conf = self._resolve_provenance(source_event_id, source_type, source_role, confidence)
        decision = self._validator.validate(
            type=type,
            content=content,
            source_type=stype,
            source_role=srole,
            source_event_id=source_event_id,
            confidence=conf,
        )
        if not decision.allowed:
            raise MemoryWriteError(decision.reason, decision.code)
        return self._insert_memory(type, content, importance, source_event_id, stype, srole, conf)

    def add_user_memory(
        self,
        type: str,
        content: str,
        importance: str = "high",
        source_type: str = USER_EXPLICIT,
        event_type: str = "user_said",
    ) -> Memory:
        """记录一条用户明确表达的事实：先写 user Event（Primary Evidence），再写 Memory。"""
        event = self.add_event(type=event_type, content=content, role="user")
        return self.write_memory(
            type=type,
            content=content,
            importance=importance,
            source_event_id=event.id,
            source_type=source_type,
            source_role="user",
        )

    def add_system_fact(self, content: str, importance: str = "high") -> Memory:
        """写入一条 SYSTEM_FACT（系统真实状态，非用户历史）。"""
        return self.write_memory(
            type="system_fact",
            content=content,
            importance=importance,
            source_type=SYSTEM_FACT,
            source_role="system",
            source_event_id=None,
        )

    def remember(self, content: str) -> Memory:
        """Record a user statement as both an append-only Event and a Memory.

        This is the single entry point used by the CLI for "记住：xxx"。
        """
        event = self.add_event(type="user_said", content=f"记住：{content}", role="user")
        return self.write_memory(
            type="fact",
            content=content,
            importance="high",
            source_event_id=event.id,
            source_type=USER_EXPLICIT,
            source_role="user",
        )

    def get_memory(self, memory_id: int) -> Optional[Memory]:
        row = self._conn.execute(
            "SELECT id, type, content, importance, status, source_event_id, source_type, "
            "source_role, confidence, created_at, archived_at, updated_at "
            "FROM memories WHERE id = ?",
            (memory_id,),
        ).fetchone()
        return self._row_to_memory(row) if row else None

    def list_memories(self, include_archived: bool = False) -> list[Memory]:
        query = (
            "SELECT id, type, content, importance, status, source_event_id, source_type, "
            "source_role, confidence, created_at, archived_at, updated_at "
            "FROM memories"
        )
        if not include_archived:
            query += " WHERE status = 'active'"
        query += " ORDER BY id"
        rows = self._conn.execute(query).fetchall()
        return [self._row_to_memory(r) for r in rows]

    def list_verified_memories(self) -> list[Memory]:
        """仅返回可支撑强归因的 verified 记忆。"""
        return [m for m in self.list_memories() if m.verified]

    def retrieve(self, query: str, limit: int = 5) -> list[tuple[Memory, float]]:
        """检索与 query 最相关的活跃记忆（关键词 + importance + 时间排序）。"""
        return retrieve_memories(self.list_memories(), query, limit)

    def archive_memory(self, memory_id: int) -> Optional[Memory]:
        archived_at = utcnow_iso()
        with self._conn:
            cur = self._conn.execute(
                "UPDATE memories SET status = 'archived', archived_at = ? WHERE id = ?",
                (archived_at, memory_id),
            )
        if cur.rowcount == 0:
            return None
        return self.get_memory(memory_id)

    def invalidate_memory(self, memory_id: int) -> Optional[Memory]:
        """纠错：作废一条错误记忆（标记 invalidated，不删除历史）。"""
        archived_at = utcnow_iso()
        with self._conn:
            cur = self._conn.execute(
                "UPDATE memories SET status = 'invalidated', archived_at = ? WHERE id = ?",
                (archived_at, memory_id),
            )
        if cur.rowcount == 0:
            return None
        return self.get_memory(memory_id)

    def update_memory(self, memory_id: int, content: str) -> Optional[Memory]:
        """更新一条活跃记忆的内容；affected_rows=0 时返回 None（不存在或已归档）。"""
        updated_at = utcnow_iso()
        with self._conn:
            cur = self._conn.execute(
                "UPDATE memories SET content = ?, updated_at = ? WHERE id = ? AND status = 'active'",
                (content, updated_at, memory_id),
            )
        if cur.rowcount == 0:
            return None
        return self.get_memory(memory_id)

    # ------------------------------------------------------------------ helpers

    def _resolve_provenance(
        self,
        source_event_id: Optional[int],
        source_type: Optional[str],
        source_role: Optional[str],
        confidence: Optional[float],
    ) -> tuple[str, Optional[str], float]:
        """根据来源事件推导 source_type / source_role / confidence（未显式给出时）。"""
        event: Optional[Event] = self.get_event(source_event_id) if source_event_id is not None else None

        if source_type is None:
            if event is None:
                source_type = UNKNOWN
            elif event.role == "assistant":
                source_type = ASSISTANT_INFERENCE
            elif event.role == "system":
                source_type = SYSTEM_FACT
            else:
                source_type = USER_EXPLICIT

        if source_role is None:
            source_role = event.role if event is not None else None

        if confidence is None:
            confidence = confidence_for(source_type)

        return source_type, source_role, confidence

    def _insert_memory(
        self,
        type: str,
        content: str,
        importance: str,
        source_event_id: Optional[int],
        source_type: str,
        source_role: Optional[str],
        confidence: float,
    ) -> Memory:
        created_at = utcnow_iso()
        with self._conn:
            cur = self._conn.execute(
                "INSERT INTO memories "
                "(type, content, importance, status, source_event_id, source_type, source_role, confidence, created_at, updated_at) "
                "VALUES (?, ?, ?, 'active', ?, ?, ?, ?, ?, ?)",
                (type, content, importance, source_event_id, source_type, source_role, confidence, created_at, created_at),
            )
            memory_id = cur.lastrowid
        return Memory(
            id=memory_id,
            type=type,
            content=content,
            importance=importance,
            status="active",
            source_event_id=source_event_id,
            source_type=source_type,
            source_role=source_role,
            confidence=confidence,
            created_at=created_at,
            archived_at=None,
            updated_at=created_at,
        )

    @staticmethod
    def _row_to_event(r: sqlite3.Row) -> Event:
        return Event(
            id=r["id"],
            type=r["type"],
            content=r["content"],
            created_at=r["created_at"],
            role=r["role"],
        )

    @staticmethod
    def _row_to_memory(r: sqlite3.Row) -> Memory:
        return Memory(
            id=r["id"],
            type=r["type"],
            content=r["content"],
            importance=r["importance"],
            status=r["status"],
            source_event_id=r["source_event_id"],
            source_type=r["source_type"],
            source_role=r["source_role"],
            confidence=r["confidence"],
            created_at=r["created_at"],
            archived_at=r["archived_at"],
            updated_at=r["updated_at"],
        )