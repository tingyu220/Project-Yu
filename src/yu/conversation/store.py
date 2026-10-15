"""共享会话的 SQLite 持久层；不调用模型，也不执行动作。"""

from __future__ import annotations

import json
import sqlite3
import uuid
from time import time_ns
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Turn:
    seq: int
    session_id: str
    request_id: str
    source: str
    message: str
    state: str
    created_at: str
    completed_at: str | None
    result: dict[str, Any] | None
    revision: int


class ConversationStore:
    """单默认会话的轮次、游标、幂等回执和安全备份。"""

    def __init__(self, db_path: str):
        database = Path(db_path)
        if database.exists() and database.stat().st_size:
            backup = database.with_name(f"{database.name}.before-conversation-{time_ns()}.db")
            with sqlite3.connect(str(backup)) as target, sqlite3.connect(str(database)) as source:
                source.backup(target)
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript("""
        CREATE TABLE IF NOT EXISTS yu_conversations (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            session_id TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS yu_conversation_turns (
            seq INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            request_id TEXT NOT NULL,
            source TEXT NOT NULL,
            message TEXT NOT NULL,
            state TEXT NOT NULL,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            result_json TEXT,
            revision INTEGER NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS yu_turn_request
            ON yu_conversation_turns(session_id, request_id);
        """)
        if self._conn.execute("SELECT 1 FROM yu_conversations WHERE id=1").fetchone() is None:
            self._conn.execute(
                "INSERT INTO yu_conversations VALUES (1, ?, ?)", (str(uuid.uuid4()), _now())
            )
        self._conn.commit()
        self._mark_unfinished_unknown()

    def _mark_unfinished_unknown(self) -> None:
        next_revision = self._conn.execute("SELECT COALESCE(MAX(revision), 0) FROM yu_conversation_turns").fetchone()[0]
        self._conn.execute(
            "UPDATE yu_conversation_turns SET state='unknown', revision=? "
            "WHERE state IN ('queued', 'running')"
            , (next_revision + 1,)
        )
        self._conn.commit()

    def default_session(self) -> str:
        return self._conn.execute("SELECT session_id FROM yu_conversations WHERE id=1").fetchone()[0]

    def _row(self, row: sqlite3.Row | None) -> Turn | None:
        if row is None:
            return None
        return Turn(row["seq"], row["session_id"], row["request_id"], row["source"], row["message"],
                    row["state"], row["created_at"], row["completed_at"],
                    json.loads(row["result_json"]) if row["result_json"] else None, row["revision"])

    def get_request(self, session_id: str, request_id: str) -> Turn | None:
        return self._row(self._conn.execute(
            "SELECT * FROM yu_conversation_turns WHERE session_id=? AND request_id=?",
            (session_id, request_id)).fetchone())

    def insert_turn(self, session_id: str, request_id: str, source: str, message: str) -> Turn:
        existing = self.get_request(session_id, request_id)
        if existing:
            if existing.message != message or existing.source != source:
                raise ValueError("request_id 已用于其他消息")
            return existing
        revision = self._conn.execute("SELECT COALESCE(MAX(revision), 0) + 1 FROM yu_conversation_turns").fetchone()[0]
        cursor = self._conn.execute(
            "INSERT INTO yu_conversation_turns(session_id,request_id,source,message,state,created_at,revision) "
            "VALUES(?,?,?,?,?,?,?)", (session_id, request_id, source, message, "queued", _now(), revision))
        self._conn.commit()
        return self._row(self._conn.execute("SELECT * FROM yu_conversation_turns WHERE seq=?", (cursor.lastrowid,)).fetchone())

    def set_state(self, seq: int, state: str, result: dict[str, Any] | None = None) -> Turn:
        revision = self._conn.execute("SELECT COALESCE(MAX(revision), 0) + 1 FROM yu_conversation_turns").fetchone()[0]
        completed = _now() if state in {"completed", "failed", "unknown"} else None
        self._conn.execute("UPDATE yu_conversation_turns SET state=?, completed_at=?, result_json=?, revision=? WHERE seq=?",
                           (state, completed, json.dumps(result, ensure_ascii=False) if result is not None else None, revision, seq))
        self._conn.commit()
        return self._row(self._conn.execute("SELECT * FROM yu_conversation_turns WHERE seq=?", (seq,)).fetchone())

    def history(self, session_id: str) -> list[dict[str, str]]:
        rows = self._conn.execute(
            "SELECT message,result_json FROM yu_conversation_turns WHERE session_id=? AND state='completed' ORDER BY seq DESC LIMIT 10",
            (session_id,)).fetchall()
        output: list[dict[str, str]] = []
        for row in reversed(rows):
            output.extend([{"role": "user", "content": row["message"]},
                           {"role": "assistant", "content": json.loads(row["result_json"] or "{}").get("reply", "")}])
        return output[-20:]

    def changes(self, after: int, limit: int = 100) -> dict[str, Any]:
        if not 1 <= limit <= 100:
            raise ValueError("limit 必须在 1 至 100 之间")
        rows = self._conn.execute("SELECT * FROM yu_conversation_turns WHERE revision>? ORDER BY revision LIMIT ?", (after, limit)).fetchall()
        turns = [self._serialize(self._row(row)) for row in rows]
        return {"turns": turns, "next_cursor": max([after] + [item["revision"] for item in turns]), "has_more": len(turns) == limit}

    @staticmethod
    def _serialize(turn: Turn) -> dict[str, Any]:
        return {"seq": turn.seq, "session_id": turn.session_id, "request_id": turn.request_id, "source": turn.source,
                "message": turn.message, "state": turn.state, "created_at": turn.created_at,
                "completed_at": turn.completed_at, "result": turn.result, "revision": turn.revision}

    def backup(self, destination: str) -> None:
        Path(destination).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(destination) as target:
            self._conn.backup(target)

    def close(self) -> None:
        self._conn.close()
