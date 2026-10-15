from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    import yu.api.context as ctxmod

    monkeypatch.setattr(ctxmod, "DEFAULT_DB_PATH", str(tmp_path / "yu.db"))
    monkeypatch.setattr(ctxmod, "DEFAULT_AUDIT_DB", str(tmp_path / "audit.db"))

    from yu.api.app import create_app

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_chat_routes_clear_action_without_llm(client):
    response = client.post("/api/chat", json={"message": "打开不存在的软件", "history": []})

    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "action"
    assert body["type"] == "action"
    assert body["content"] == body["reply"]
    assert body["action"]["action_type"] == "app.open"
    assert body["action"]["success"] is False
    assert body["action"]["error_code"] == "ACTION_DENIED"
