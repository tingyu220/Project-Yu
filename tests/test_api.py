"""Yu API Adapter 冒烟测试（Interface Layer）。

验证 apps/web 依赖的 HTTP 接口形态正确，且读取动作不绕过 Safety Kernel。
测试使用本地真实 data/yu.db（只读为主）；system.status.read 会追加审计事件，
与 CLI 行为一致（审计为 append-only，属预期副作用）。

需要：pip install -e ".[dev,api]"（httpx 供 TestClient 使用）。
"""

from __future__ import annotations

import os

import pytest

from fastapi.testclient import TestClient

from yu.api.app import create_app


@pytest.fixture(scope="module")
def client():
    """隔离 LLM：测试期间移除 DEEPSEEK_API_KEY，验证无 LLM 时的降级行为。"""
    saved = os.environ.get("DEEPSEEK_API_KEY")
    os.environ.pop("DEEPSEEK_API_KEY", None)
    app = create_app()
    try:
        with TestClient(app) as c:
            yield c
    finally:
        if saved is not None:
            os.environ["DEEPSEEK_API_KEY"] = saved


def test_status(client):
    r = client.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Yu"
    assert body["safety"]["safety_kernel"] == "ACTIVE"
    assert "llm" in body


def test_today_shape(client):
    r = client.get("/api/today")
    assert r.status_code == 200
    body = r.json()
    for key in ("date", "memory_count", "goals", "tasks", "projects", "top_priority"):
        assert key in body


def test_memories_and_stats(client):
    mem = client.get("/api/memories?limit=150")
    assert mem.status_code == 200
    assert "memories" in mem.json()

    stats = client.get("/api/memory/stats")
    assert stats.status_code == 200
    s = stats.json()
    assert "total" in s and "by_type" in s and "by_importance" in s


def test_system_status_through_kernel(client):
    r = client.get("/api/system/status")
    assert r.status_code == 200
    body = r.json()
    # 读取动作经 Safety Kernel 评估，返回其决策结果（allowed / reason）
    assert "allowed" in body
    if body["allowed"]:
        assert body["status"] is not None


def test_memory_query(client):
    r = client.post("/api/memories/query", json={"query": "记忆", "limit": 5})
    assert r.status_code == 200
    assert "matches" in r.json()


def test_chat_degrades_without_llm(client):
    r = client.post("/api/chat", json={"message": "你好", "history": []})
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] in ("chat", "plan", "computer", "error")
    assert isinstance(body["retrieved"], list)
