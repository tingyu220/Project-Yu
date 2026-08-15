"""SQLite-backed persistent store for the Yu Memory Kernel.

Design guarantees:
- Event is append-only: enforced by both the API (no update method)
  and SQLite triggers (no UPDATE/DELETE on the 'events' table).
- Memory supports Create / Read / Archive; archiving never deletes history.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from .models import Event, Memory, utcnow_iso

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    type        TEXT NOT NULL,
    content     TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memories (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    type            TEXT NOT NULL,
    content         TEXT NOT NULL,
    importance      TEXT NOT NULL DEFAULT 'medium',
    status          TEXT NOT NULL DEFAULT 'active',
    source_event_id INTEGER,
    created_at      TEXT NOT NULL,
    archived_at     TEXT,
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

    def __enter__(self) -> "MemoryStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        self._conn.close()

    # ------------------------------------------------------------------ Events

    def add_event(self, type: str, content: str) -> Event:
        created_at = utcnow_iso()
        with self._conn:
            cur = self._conn.execute(
                "INSERT INTO events (type, content, created_at) VALUES (?, ?, ?)",
                (type, content, created_at),
            )
        return Event(id=cur.lastrowid, type=type, content=content, created_at=created_at)

    def list_events(self) -> list[Event]:
        rows = self._conn.execute(
            "SELECT id, type, content, created_at FROM events ORDER BY id"
        ).fetchall()
        return [
            Event(id=r["id"], type=r["type"], content=r["content"], created_at=r["created_at"])
            for r in rows
        ]

    # ----------------------------------------------------------------- Memories

    def add_memory(
        self,
        type: str,
        content: str,
        importance: str = "medium",
        source_event_id: Optional[int] = None,
    ) -> Memory:
        created_at = utcnow_iso()
        with self._conn:
            cur = self._conn.execute(
                "INSERT INTO memories (type, content, importance, status, source_event_id, created_at) "
                "VALUES (?, ?, ?, 'active', ?, ?)",
                (type, content, importance, source_event_id, created_at),
            )
            memory_id = cur.lastrowid
        return Memory(
            id=memory_id,
            type=type,
            content=content,
            importance=importance,
            status="active",
            source_event_id=source_event_id,
            created_at=created_at,
            archived_at=None,
        )

    def get_memory(self, memory_id: int) -> Optional[Memory]:
        row = self._conn.execute(
            "SELECT id, type, content, importance, status, source_event_id, created_at, archived_at "
            "FROM memories WHERE id = ?",
            (memory_id,),
        ).fetchone()
        return self._row_to_memory(row) if row else None

    def list_memories(self, include_archived: bool = False) -> list[Memory]:
        query = (
            "SELECT id, type, content, importance, status, source_event_id, created_at, archived_at "
            "FROM memories"
        )
        if not include_archived:
            query += " WHERE status = 'active'"
        query += " ORDER BY id"
        rows = self._conn.execute(query).fetchall()
        return [self._row_to_memory(r) for r in rows]

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

    def remember(self, content: str) -> Memory:
        """Record a user statement as both an append-only Event and a Memory.

        This is the single entry point used by the CLI for "记住：xxx".
        """
        event = self.add_event(type="user_said", content=f"记住：{content}")
        return self.add_memory(
            type="fact", content=content, importance="high", source_event_id=event.id
        )

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _row_to_memory(r: sqlite3.Row) -> Memory:
        return Memory(
            id=r["id"],
            type=r["type"],
            content=r["content"],
            importance=r["importance"],
            status=r["status"],
            source_event_id=r["source_event_id"],
            created_at=r["created_at"],
            archived_at=r["archived_at"],
        )
