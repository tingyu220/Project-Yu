"""SQLite 持久化的结构化实体存储（Goal / Task / Decision / Project）。

复用 data/yu.db（与 Memory 同一个数据库文件），新增独立表；不修改 events/memories。
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import Decision, Goal, Project, Task

_ENTITIES_SCHEMA = """
CREATE TABLE IF NOT EXISTS goals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'active',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'active',
    current_goal TEXT,
    next_step    TEXT,
    notes        TEXT,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    title            TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'todo',
    priority         TEXT NOT NULL DEFAULT 'medium',
    due_date         TEXT,
    related_goal     INTEGER,
    related_project  INTEGER,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL,
    FOREIGN KEY (related_goal) REFERENCES goals(id),
    FOREIGN KEY (related_project) REFERENCES projects(id)
);

CREATE TABLE IF NOT EXISTS decisions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    decision     TEXT NOT NULL,
    reason       TEXT,
    constraints  TEXT,
    alternatives TEXT,
    created_at   TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EntitiesStore:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        with self._conn:
            self._conn.executescript(_ENTITIES_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    # ------------------------------------------------------------------ Goals

    def add_goal(self, title: str, status: str = "active") -> Goal:
        ts = _now()
        with self._conn:
            cur = self._conn.execute(
                "INSERT INTO goals (title, status, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (title, status, ts, ts),
            )
        return Goal(id=cur.lastrowid, title=title, status=status, created_at=ts, updated_at=ts)

    def list_goals(self, include_archived: bool = False) -> list[Goal]:
        query = "SELECT id, title, status, created_at, updated_at FROM goals"
        if not include_archived:
            query += " WHERE status != 'archived'"
        query += " ORDER BY id"
        rows = self._conn.execute(query).fetchall()
        return [
            Goal(id=r["id"], title=r["title"], status=r["status"], created_at=r["created_at"], updated_at=r["updated_at"])
            for r in rows
        ]

    def update_goal_status(self, goal_id: int, status: str) -> Optional[Goal]:
        ts = _now()
        with self._conn:
            cur = self._conn.execute(
                "UPDATE goals SET status = ?, updated_at = ? WHERE id = ?", (status, ts, goal_id)
            )
        if cur.rowcount == 0:
            return None
        row = self._conn.execute(
            "SELECT id, title, status, created_at, updated_at FROM goals WHERE id = ?", (goal_id,)
        ).fetchone()
        return Goal(id=row["id"], title=row["title"], status=row["status"], created_at=row["created_at"], updated_at=row["updated_at"])

    # ------------------------------------------------------------------ Projects

    def add_project(
        self,
        name: str,
        status: str = "active",
        current_goal: Optional[str] = None,
        next_step: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Project:
        ts = _now()
        with self._conn:
            cur = self._conn.execute(
                "INSERT INTO projects (name, status, current_goal, next_step, notes, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (name, status, current_goal, next_step, notes, ts, ts),
            )
        return Project(id=cur.lastrowid, name=name, status=status, current_goal=current_goal, next_step=next_step, notes=notes, created_at=ts, updated_at=ts)

    def list_projects(self) -> list[Project]:
        rows = self._conn.execute(
            "SELECT id, name, status, current_goal, next_step, notes, created_at, updated_at FROM projects ORDER BY id"
        ).fetchall()
        return [self._row_to_project(r) for r in rows]

    def update_project(
        self,
        project_id: int,
        status: Optional[str] = None,
        current_goal: Optional[str] = None,
        next_step: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[Project]:
        ts = _now()
        fields: dict[str, object] = {"updated_at": ts}
        if status is not None:
            fields["status"] = status
        if current_goal is not None:
            fields["current_goal"] = current_goal
        if next_step is not None:
            fields["next_step"] = next_step
        if notes is not None:
            fields["notes"] = notes
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        with self._conn:
            cur = self._conn.execute(
                f"UPDATE projects SET {set_clause} WHERE id = ?", (*fields.values(), project_id)
            )
        if cur.rowcount == 0:
            return None
        row = self._conn.execute(
            "SELECT id, name, status, current_goal, next_step, notes, created_at, updated_at FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()
        return self._row_to_project(row)

    # ------------------------------------------------------------------ Tasks

    def add_task(
        self,
        title: str,
        status: str = "todo",
        priority: str = "medium",
        due_date: Optional[str] = None,
        related_goal: Optional[int] = None,
        related_project: Optional[int] = None,
    ) -> Task:
        ts = _now()
        with self._conn:
            cur = self._conn.execute(
                "INSERT INTO tasks (title, status, priority, due_date, related_goal, related_project, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (title, status, priority, due_date, related_goal, related_project, ts, ts),
            )
        return Task(id=cur.lastrowid, title=title, status=status, priority=priority, due_date=due_date, related_goal=related_goal, related_project=related_project, created_at=ts, updated_at=ts)

    def list_tasks(self, status: Optional[str] = None) -> list[Task]:
        query = "SELECT id, title, status, priority, due_date, related_goal, related_project, created_at, updated_at FROM tasks"
        params: tuple = ()
        if status is not None:
            query += " WHERE status = ?"
            params = (status,)
        query += " ORDER BY id"
        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_task(r) for r in rows]

    def update_task_status(self, task_id: int, status: str) -> Optional[Task]:
        ts = _now()
        with self._conn:
            cur = self._conn.execute(
                "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?", (status, ts, task_id)
            )
        if cur.rowcount == 0:
            return None
        row = self._conn.execute(
            "SELECT id, title, status, priority, due_date, related_goal, related_project, created_at, updated_at FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()
        return self._row_to_task(row)

    # ------------------------------------------------------------------ Decisions

    def add_decision(
        self,
        decision: str,
        reason: Optional[str] = None,
        constraints: Optional[str] = None,
        alternatives: Optional[str] = None,
    ) -> Decision:
        ts = _now()
        with self._conn:
            cur = self._conn.execute(
                "INSERT INTO decisions (decision, reason, constraints, alternatives, created_at) VALUES (?, ?, ?, ?, ?)",
                (decision, reason, constraints, alternatives, ts),
            )
        return Decision(id=cur.lastrowid, decision=decision, reason=reason, constraints=constraints, alternatives=alternatives, created_at=ts)

    def list_decisions(self) -> list[Decision]:
        rows = self._conn.execute(
            "SELECT id, decision, reason, constraints, alternatives, created_at FROM decisions ORDER BY id"
        ).fetchall()
        return [
            Decision(id=r["id"], decision=r["decision"], reason=r["reason"], constraints=r["constraints"], alternatives=r["alternatives"], created_at=r["created_at"])
            for r in rows
        ]

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _row_to_task(r: sqlite3.Row) -> Task:
        return Task(
            id=r["id"], title=r["title"], status=r["status"], priority=r["priority"],
            due_date=r["due_date"], related_goal=r["related_goal"], related_project=r["related_project"],
            created_at=r["created_at"], updated_at=r["updated_at"],
        )

    @staticmethod
    def _row_to_project(r: sqlite3.Row) -> Project:
        return Project(
            id=r["id"], name=r["name"], status=r["status"], current_goal=r["current_goal"],
            next_step=r["next_step"], notes=r["notes"], created_at=r["created_at"], updated_at=r["updated_at"],
        )
