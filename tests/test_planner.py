"""Tests for Daily Planner (Phase 5)."""

import pytest

from yu.entities.store import EntitiesStore
from yu.llm import ChatMessage, LLMProvider, LLMResponse
from yu.memory.store import MemoryStore
from yu.planner import PLANNER_SYSTEM_PROMPT, build_plan, gather_context, is_plan_request


class FakeProvider(LLMProvider):
    name = "fake"

    def __init__(self):
        self.calls = []

    def chat(self, messages):
        self.calls.append(messages)
        return LLMResponse(content="今日计划（测试）", model="fake")


def test_is_plan_request():
    assert is_plan_request("我今天应该干什么？") is True
    assert is_plan_request("今天做什么") is True
    assert is_plan_request("今天天气怎么样") is False
    assert is_plan_request("记住：我喜欢咖啡") is False


def test_gather_context_includes_all(tmp_path):
    store = MemoryStore(tmp_path / "m.db")
    entities = EntitiesStore(tmp_path / "e.db")
    entities.add_goal("学习 AI")
    entities.add_task("完成 pytest 测试")
    entities.add_project("Yu")
    store.remember("用户正在开发 Yu。")
    ctx = gather_context(store, entities)
    assert "学习 AI" in ctx
    assert "完成 pytest 测试" in ctx
    assert "Yu" in ctx
    assert "用户正在开发 Yu" in ctx
    store.close()
    entities.close()


def test_gather_context_empty(tmp_path):
    store = MemoryStore(tmp_path / "m.db")
    entities = EntitiesStore(tmp_path / "e.db")
    ctx = gather_context(store, entities)
    assert "没有目标" in ctx
    store.close()
    entities.close()


def test_build_plan_calls_provider_with_context(tmp_path):
    store = MemoryStore(tmp_path / "m.db")
    entities = EntitiesStore(tmp_path / "e.db")
    entities.add_goal("学习 AI")
    entities.add_task("完成 pytest 测试")
    store.remember("用户希望长期向 AI 相关职业方向发展。")

    fake = FakeProvider()
    plan = build_plan(store, entities, fake)

    assert plan == "今日计划（测试）"
    assert len(fake.calls) == 1
    messages = fake.calls[0]
    assert messages[0].role == "system"
    assert "优先级决策" in messages[0].content
    assert messages[1].role == "user"
    assert "学习 AI" in messages[1].content
    assert "完成 pytest 测试" in messages[1].content
    store.close()
    entities.close()


def test_planner_prompt_has_principles():
    assert "每天最多 3 个核心任务" in PLANNER_SYSTEM_PROMPT
    assert "今天不要做什么" in PLANNER_SYSTEM_PROMPT
    assert "说明安排理由" in PLANNER_SYSTEM_PROMPT
