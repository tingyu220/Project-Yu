"""Tests for Daily Summary (Phase 6)."""

import re

from yu.daily import DailyLogStore, build_daily_summary, gather_daily_data, today_date
from yu.entities.store import EntitiesStore
from yu.llm import LLMProvider, LLMResponse
from yu.memory.store import MemoryStore


class FakeProvider(LLMProvider):
    name = "fake"

    def __init__(self):
        self.calls = []

    def chat(self, messages):
        self.calls.append(messages)
        return LLMResponse(content="Daily Summary（测试）", model="fake")


def test_today_date_format():
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", today_date())


def test_gather_daily_data_includes_all(tmp_path):
    store = MemoryStore(tmp_path / "m.db")
    entities = EntitiesStore(tmp_path / "e.db")
    entities.add_goal("学习 AI")
    entities.add_task("完成 pytest 测试")
    entities.add_project("Yu")
    entities.add_decision("Yu V0.1 只开发 Windows PC")
    store.remember("用户正在开发 Yu。")
    ctx = gather_daily_data(store, entities)
    assert "学习 AI" in ctx
    assert "完成 pytest 测试" in ctx
    assert "Yu" in ctx
    assert "只开发 Windows PC" in ctx
    assert "用户正在开发 Yu" in ctx
    store.close()
    entities.close()


def test_gather_daily_data_empty(tmp_path):
    store = MemoryStore(tmp_path / "m.db")
    entities = EntitiesStore(tmp_path / "e.db")
    ctx = gather_daily_data(store, entities)
    assert "暂无数据" in ctx
    store.close()
    entities.close()


def test_build_daily_summary_calls_provider(tmp_path):
    store = MemoryStore(tmp_path / "m.db")
    entities = EntitiesStore(tmp_path / "e.db")
    entities.add_goal("学习 AI")
    fake = FakeProvider()
    s = build_daily_summary(store, entities, fake)
    assert s == "Daily Summary（测试）"
    assert len(fake.calls) == 1
    messages = fake.calls[0]
    assert messages[0].role == "system"
    assert "Daily Summary" in messages[0].content
    assert messages[1].role == "user"
    assert "学习 AI" in messages[1].content
    store.close()
    entities.close()


def test_daily_log_save_and_get(tmp_path):
    daily = DailyLogStore(tmp_path / "d.db")
    daily.save("2026-08-15", "Date: 2026-08-15 内容")
    log = daily.get("2026-08-15")
    assert log is not None
    assert log.date == "2026-08-15"
    assert "Date: 2026-08-15" in log.content
    daily.close()


def test_daily_log_upsert(tmp_path):
    daily = DailyLogStore(tmp_path / "d.db")
    daily.save("2026-08-15", "第一版")
    daily.save("2026-08-15", "第二版")
    logs = daily.list_logs()
    assert len(logs) == 1
    assert "第二版" in logs[0].content
    daily.close()


def test_daily_log_persistence(tmp_path):
    db = tmp_path / "d.db"
    daily = DailyLogStore(db)
    daily.save("2026-08-15", "内容A")
    daily.close()

    daily2 = DailyLogStore(db)
    assert daily2.get("2026-08-15").content == "内容A"
    daily2.close()
