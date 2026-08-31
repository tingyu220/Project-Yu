"""Daily Summary — 每天的状态快照（Phase 6）。

让 Yu 每一天都有一个清晰的状态快照，并持久化到 data/yu.db 的 daily_logs 表，
作为次日恢复 Context 的基础。Daily Summary 不替代原始 Event，原始事件仍永久保留。
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .entities.store import EntitiesStore
from .llm import ChatMessage, LLMProvider
from .memory.retrieval import format_memory_line
from .memory.store import MemoryStore

_DAILY_SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT NOT NULL UNIQUE,
    content     TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
"""

DAILY_SUMMARY_SYSTEM_PROMPT = (
    "你是 Yu 的每日总结器。根据提供的当天数据，生成一份简洁、诚实的 Daily Summary。\n"
    "严格只使用提供的数据，不要编造；某项没有数据就写「无」。\n"
    "输出格式：\n"
    "Date: <今天日期>\n"
    "今日计划：...\n"
    "实际完成：...\n"
    "未完成：...\n"
    "新增记忆：...\n"
    "重要决策：...\n"
    "遇到的问题：...\n"
    "当前项目状态：...\n"
    "明天建议：..."
    "Memory Grounding：只把 [USER_EXPLICIT]/[USER_CONFIRMED] 的记忆当作用户事实；"
    "标注为 SUMMARY_DERIVED / ASSISTANT_INFERENCE / UNKNOWN 的内容不得写进「用户说过/做过」；"
    "不要用「你昨天说过」等措辞归因到未经证实的记忆。没有证据就写「无」。"
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def today_date() -> str:
    """返回本地日期（YYYY-MM-DD）。"""
    return datetime.now().date().isoformat()


@dataclass(frozen=True)
class DailyLog:
    id: int
    date: str
    content: str
    created_at: str
    updated_at: str


class DailyLogStore:
    """持久化 Daily Summary（按日期唯一，重复保存会覆盖）。"""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        with self._conn:
            self._conn.executescript(_DAILY_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def save(self, date: str, content: str) -> DailyLog:
        ts = _now()
        with self._conn:
            self._conn.execute(
                "INSERT INTO daily_logs (date, content, created_at, updated_at) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(date) DO UPDATE SET content = excluded.content, updated_at = excluded.updated_at",
                (date, content, ts, ts),
            )
        row = self._conn.execute(
            "SELECT id, date, content, created_at, updated_at FROM daily_logs WHERE date = ?", (date,)
        ).fetchone()
        return self._row_to_log(row)

    def get(self, date: str) -> Optional[DailyLog]:
        row = self._conn.execute(
            "SELECT id, date, content, created_at, updated_at FROM daily_logs WHERE date = ?", (date,)
        ).fetchone()
        return self._row_to_log(row) if row else None

    def list_logs(self, limit: int = 20) -> list[DailyLog]:
        rows = self._conn.execute(
            "SELECT id, date, content, created_at, updated_at FROM daily_logs ORDER BY date DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self._row_to_log(r) for r in rows]

    @staticmethod
    def _row_to_log(r: sqlite3.Row) -> DailyLog:
        return DailyLog(
            id=r["id"], date=r["date"], content=r["content"],
            created_at=r["created_at"], updated_at=r["updated_at"],
        )


def gather_daily_data(store: MemoryStore, entities: EntitiesStore) -> str:
    """汇总当天目标 / 任务 / 项目 / 决策 / 记忆。"""
    parts: list[str] = []

    goals = entities.list_goals()
    if goals:
        parts.append("## 目标\n" + "\n".join(f"- ({g.status}) {g.title}" for g in goals))

    tasks = entities.list_tasks()
    open_tasks = [t for t in tasks if t.status != "done"]
    done_tasks = [t for t in tasks if t.status == "done"]
    if open_tasks:
        parts.append("## 未完成任务\n" + "\n".join(f"- ({t.status}/{t.priority}) {t.title}" for t in open_tasks))
    if done_tasks:
        parts.append("## 已完成任务\n" + "\n".join(f"- {t.title}" for t in done_tasks))

    projects = entities.list_projects()
    if projects:
        lines = []
        for p in projects:
            line = f"- ({p.status}) {p.name}"
            if p.next_step:
                line += f"，下一步：{p.next_step}"
            lines.append(line)
        parts.append("## 项目\n" + "\n".join(lines))

    decisions = entities.list_decisions()
    if decisions:
        parts.append("## 决策\n" + "\n".join(f"- {d.decision}" for d in decisions))

    memories = store.list_memories()[-10:]
    if memories:
        parts.append("## 记忆（带来源标签，仅 USER_EXPLICIT/USER_CONFIRMED 是用户事实）\n" + "\n".join(format_memory_line(m) for m in memories))

    if not parts:
        return "（当天暂无数据）"
    return "\n\n".join(parts)


def build_daily_summary(store: MemoryStore, entities: EntitiesStore, provider: LLMProvider) -> str:
    """生成当天 Daily Summary，返回 LLM 输出文本。"""
    data = gather_daily_data(store, entities)
    messages = [
        ChatMessage(role="system", content=DAILY_SUMMARY_SYSTEM_PROMPT),
        ChatMessage(role="user", content=f"今天是 {today_date()}。以下是当天数据：\n\n{data}"),
    ]
    return provider.chat(messages).content