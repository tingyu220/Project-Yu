"""Security Audit Log — append-only SQLite 存储。

审计历史不能由普通业务逻辑 update / delete（数据库触发器强制）。
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import AuditEvent

_AUDIT_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL,
    event_type  TEXT NOT NULL,
    actor       TEXT NOT NULL,
    action_id   TEXT,
    risk_level  TEXT,
    decision    TEXT,
    reason      TEXT NOT NULL,
    metadata    TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS audit_no_update
BEFORE UPDATE ON audit_events
BEGIN
    SELECT RAISE(ABORT, 'audit log is append-only: update is not allowed');
END;

CREATE TRIGGER IF NOT EXISTS audit_no_delete
BEFORE DELETE ON audit_events
BEGIN
    SELECT RAISE(ABORT, 'audit log is append-only: delete is not allowed');
END;
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AuditStore:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        with self._conn:
            self._conn.executescript(_AUDIT_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def record(
        self,
        event_type: str,
        actor: str = "yu",
        reason: str = "",
        action_id: Optional[str] = None,
        risk_level: Optional[str] = None,
        decision: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> AuditEvent:
        ts = _now()
        meta = metadata or {}
        meta_json = json.dumps(meta, ensure_ascii=False)
        with self._conn:
            cur = self._conn.execute(
                "INSERT INTO audit_events "
                "(timestamp, event_type, actor, action_id, risk_level, decision, reason, metadata) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (ts, event_type, actor, action_id, risk_level, decision, reason, meta_json),
            )
        return AuditEvent(
            id=cur.lastrowid,
            timestamp=ts,
            event_type=event_type,
            actor=actor,
            action_id=action_id,
            risk_level=risk_level,
            decision=decision,
            reason=reason,
            metadata=meta,
        )

    def list_recent(self, limit: int = 20) -> list[AuditEvent]:
        rows = self._conn.execute(
            "SELECT id, timestamp, event_type, actor, action_id, risk_level, decision, reason, metadata "
            "FROM audit_events ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self._row_to_event(r) for r in rows]

    @staticmethod
    def _row_to_event(r: sqlite3.Row) -> AuditEvent:
        try:
            meta = json.loads(r["metadata"]) if r["metadata"] else {}
        except json.JSONDecodeError:
            meta = {}
        return AuditEvent(
            id=r["id"],
            timestamp=r["timestamp"],
            event_type=r["event_type"],
            actor=r["actor"],
            action_id=r["action_id"],
            risk_level=r["risk_level"],
            decision=r["decision"],
            reason=r["reason"],
            metadata=meta,
        )
