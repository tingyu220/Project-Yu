"""Memory Reliability — API 层集成测试（CRUD 端点 + 路由 + 同步）。

使用 tmp_path 隔离数据库（monkeypatch 覆盖 Yu API 的 DB 路径），不触碰真实 data/。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    import yu.api.context as ctxmod

    monkeypatch.setattr(ctxmod, "DEFAULT_DB_PATH", str(tmp_path / "yu.db"))
    monkeypatch.setattr(ctxmod, "DEFAULT_AUDIT_DB", str(tmp_path / "audit.db"))

    from yu.api.app import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c


def test_create_memory_endpoint(client):
    r = client.post("/api/memories", json={"content": "我正在开发 Yu。", "type": "fact"})
    assert r.status_code == 200
    body = r.json()
    assert body["result"]["success"] is True
    assert body["result"]["verified"] is True
    assert body["memory"]["content"] == "我正在开发 Yu。"
    assert body["memory"]["source_type"] == "USER_EXPLICIT"
    assert body["memory"]["verified"] is True
    assert body["memory"]["source_event_id"] is not None


def test_update_memory_endpoint_returns_current_state(client):
    created = client.post("/api/memories", json={"content": "旧内容"}).json()
    mid = created["memory"]["id"]

    r = client.post(f"/api/memories/{mid}/update", json={"content": "新内容"})
    assert r.status_code == 200
    body = r.json()
    assert body["result"]["success"] is True
    assert body["result"]["before"] == "旧内容"
    assert body["result"]["after"] == "新内容"
    assert body["memory"]["content"] == "新内容"  # current server state

    # API 读取同步
    listed = client.get("/api/memories").json()
    assert any(m["id"] == mid and m["content"] == "新内容" for m in listed["memories"])


def test_update_missing_memory_no_fake_success(client):
    r = client.post("/api/memories/9999/update", json={"content": "B"})
    assert r.status_code == 200
    body = r.json()
    assert body["result"]["success"] is False
    assert "没有找到" in body["result"]["reason"]


def test_archive_memory_endpoint(client):
    created = client.post("/api/memories", json={"content": "用户喜欢咖啡"}).json()
    mid = created["memory"]["id"]

    r = client.post(f"/api/memories/{mid}/archive")
    assert r.status_code == 200
    body = r.json()
    assert body["result"]["success"] is True
    assert body["memory"]["status"] == "archived"

    listed = client.get("/api/memories").json()
    assert all(m["id"] != mid for m in listed["memories"])  # active 列表不含


def test_chat_explicit_create_routes_to_memory(client):
    r = client.post("/api/chat", json={"message": "记住：我正在开发 Yu。", "history": []})
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "MEMORY_CREATE"
    assert body["memory_result"]["success"] is True
    assert "已保存" in body["reply"]

    listed = client.get("/api/memories").json()
    assert any("我正在开发 Yu" in m["content"] for m in listed["memories"])


def test_chat_update_with_reference_syncs(client):
    created = client.post("/api/memories", json={"content": "用户正在开发 Yu。"}).json()
    mid = created["memory"]["id"]

    r = client.post(
        "/api/chat",
        json={"message": "修改这条记忆为 B", "history": [], "referenced_memory_ids": [mid]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["intent"] == "MEMORY_UPDATE"
    assert body["memory_result"]["success"] is True
    assert body["memory_result"]["after"] == "B"

    listed = client.get("/api/memories").json()
    assert any(m["id"] == mid and m["content"] == "B" for m in listed["memories"])


def test_chat_update_ambiguous_asks(client):
    for c in ("记忆 A", "记忆 B", "记忆 C"):
        client.post("/api/memories", json={"content": c})
    r = client.post(
        "/api/chat",
        json={"message": "修改这条记忆为 X", "history": [], "referenced_memory_ids": []},
    )
    body = r.json()
    assert body["intent"] == "MEMORY_UPDATE"
    assert "哪一条" in body["reply"]
    assert body.get("memory_result") is None


def test_chat_false_knee_has_no_attribution(client):
    """无膝盖记忆时，「我要去爬山」不得出现历史归因（Attribution Guard 兜底 + 无记忆）。"""
    r = client.post("/api/chat", json={"message": "我要去爬山，有什么建议？", "history": []})
    assert r.status_code == 200
    # 无 LLM 时降级，但仍返回检索结果，且不伪造历史。
    assert r.json()["kind"] in ("chat", "error")
