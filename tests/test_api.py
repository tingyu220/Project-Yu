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


def test_chat_memory_injects_context_with_provider():
    """回归：修复 app.py 中 build_context 命名冲突（memory.retrieval vs context）。

    当 LLM Provider 存在时，_chat_memory 必须走完「检索记忆 -> 注入上下文」路径。
    """
    from yu.api import app as api_app
    from yu.api.context import build_context
    from yu.llm import LLMResponse

    class FakeProvider:
        name = "fake"

        def __init__(self):
            self.messages = None

        def chat(self, messages):
            self.messages = messages
            return LLMResponse(content="测试回复")

    ctx = build_context()
    fp = FakeProvider()
    ctx.provider = fp
    try:
        r = api_app._chat_memory(ctx, "你好", [])
    finally:
        ctx.close()

    assert r["kind"] == "chat"
    assert r["reply"] == "测试回复"
    assert isinstance(r["retrieved"], list)
    assert fp.messages is not None
    assert fp.messages[0].role == "system"


# ------------------------------------------------------------------ Memory Grounding (v0.0.7.2)


class _FakeCtx:
    def __init__(self, memory, audit, provider=None):
        self.memory = memory
        self.audit = audit
        self.provider = provider


def test_memory_serializer_has_provenance(client):
    """GET /api/memories 必须返回 source_type / source_role / confidence / verified。"""
    mem = client.get("/api/memories?limit=150")
    assert mem.status_code == 200
    body = mem.json()
    if body["memories"]:
        m = body["memories"][0]
        for key in ("source_type", "source_role", "confidence", "verified", "source_event_id"):
            assert key in m


def test_chat_memory_probe_no_evidence(tmp_path):
    """No-Evidence Question：无 verified 支撑时返回确定性回答。"""
    from yu.api import app as api_app
    from yu.audit.store import AuditStore
    from yu.memory.provenance import NO_RELIABLE_MEMORY_REPLY
    from yu.memory.store import MemoryStore

    ctx = _FakeCtx(MemoryStore(tmp_path / "m.db"), AuditStore(tmp_path / "a.db"), provider=None)
    try:
        r = api_app._chat_memory(ctx, "我以前说过我膝盖疼吗？", [])
    finally:
        ctx.memory.close()
        ctx.audit.close()

    assert r["kind"] == "chat"
    assert r["reply"] == NO_RELIABLE_MEMORY_REPLY
    assert r["memory_probe"] is True


def test_chat_memory_correction_flow(tmp_path):
    """用户纠正 -> MemoryCorrectionService 作废错误记忆。"""
    from yu.api import app as api_app
    from yu.audit.store import AuditStore
    from yu.memory.store import MemoryStore

    ctx = _FakeCtx(MemoryStore(tmp_path / "m.db"), AuditStore(tmp_path / "a.db"), provider=None)
    try:
        ctx.memory.add_user_memory("fact", "用户膝盖疼")
        r = api_app._chat_memory(ctx, "我没说过膝盖疼。", [])
    finally:
        ctx.memory.close()
        ctx.audit.close()

    assert r["memory_correction"] == "invalidated"


def test_chat_memory_guard_flags_unsupported_claim(tmp_path):
    """回复含无证据历史归因 -> 记录 MEMORY_CLAIM_UNSUPPORTED 审计。"""
    from yu.api import app as api_app
    from yu.audit.store import AuditStore
    from yu.llm import LLMResponse
    from yu.memory.provenance import AUDIT_MEMORY_CLAIM_UNSUPPORTED
    from yu.memory.store import MemoryStore

    class FakeProvider:
        name = "fake"

        def chat(self, messages):
            return LLMResponse(content="你之前提到膝盖偶尔会不舒服，建议注意。")

    ctx = _FakeCtx(MemoryStore(tmp_path / "m.db"), AuditStore(tmp_path / "a.db"), provider=FakeProvider())
    try:
        r = api_app._chat_memory(ctx, "我要去爬山，给我建议。", [])
        audit_events = ctx.audit.list_recent(50)
    finally:
        ctx.memory.close()
        ctx.audit.close()

    assert r["memory_claims"]
    assert any(not c["supported"] for c in r["memory_claims"])
    assert any(e.event_type == AUDIT_MEMORY_CLAIM_UNSUPPORTED for e in audit_events)