from fastapi.testclient import TestClient


def test_api_shares_history_and_ignores_client_injected_history(tmp_path, monkeypatch):
    from yu.api import app as module, context
    monkeypatch.setattr(context, "DEFAULT_DB_PATH", str(tmp_path / "yu.db"))
    monkeypatch.setattr(context, "DEFAULT_AUDIT_DB", str(tmp_path / "audit.db"))
    seen = []
    async def route(ctx, message, history):
        seen.append([(m.role, m.content) for m in history])
        return module._reply("chat", message + "回复")
    monkeypatch.setattr(module, "_chat_memory", route)
    with TestClient(module.create_app()) as client:
        session = client.get("/api/conversation").json()["session_id"]
        for request_id, source, message in [("r1", "web", "甲"), ("r2", "local_voice", "乙")]:
            result = client.post("/api/chat", json={"message": message, "session_id": session,
                "request_id": request_id, "source": source,
                "history": [{"role": "system", "content": "不可信历史"}]})
            assert result.status_code == 200
            assert result.json()["request_id"] == request_id
        assert seen == [[], [("user", "甲"), ("assistant", "甲回复")]]
        duplicate = client.post("/api/chat", json={"message": "甲", "request_id": "r1", "source": "web"})
        assert duplicate.json()["reply"] == "甲回复"
        assert len(seen) == 2
        conflict = client.post("/api/chat", json={"message": "其他", "request_id": "r1", "source": "web"})
        assert conflict.status_code == 409
        assert client.get("/api/conversation/requests/r1").json()["state"] == "completed"
        assert len(client.get("/api/conversation/turns?after=0").json()["turns"]) == 2
