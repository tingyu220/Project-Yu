"""Memory Reliability 回归测试（Yu v0.0.7.2 方案 §57-73）。

覆盖 Test 001 - Test 015 以及端到端生命周期（Create→Read→Update→Restart→Correct→Archive）。
所有测试使用 tmp_path，绝不触碰 data/ 下真实数据库。
"""

from __future__ import annotations

import pytest

from yu.audit.store import AuditStore
from yu.computer import is_computer_request
from yu.memory.guard import MemoryAttributionGuard, has_verified_support
from yu.memory.provenance import (
    ASSISTANT_INFERENCE,
    AUDIT_MEMORY_ARCHIVED,
    AUDIT_MEMORY_CREATED,
    AUDIT_MEMORY_HALLUCINATION,
    AUDIT_MEMORY_INVALIDATED,
    AUDIT_MEMORY_UPDATED,
    NO_RELIABLE_MEMORY_REPLY,
    SUMMARY_DERIVED,
    USER_EXPLICIT,
    is_memory_probe,
)
from yu.memory.router import (
    MEMORY_ARCHIVE,
    MEMORY_CREATE,
    MEMORY_UPDATE,
    detect_memory_intent,
)
from yu.memory.service import MemoryService
from yu.memory.store import MemoryStore


def _svc(tmp_path, name="m"):
    store = MemoryStore(tmp_path / (name + ".db"))
    audit = AuditStore(tmp_path / (name + "_audit.db"))
    return store, audit, MemoryService(store, audit)


# ------------------------------------------------------------------ Test 001

def test_001_create(tmp_path):
    store, audit, service = _svc(tmp_path)
    r = service.create("我正在开发 Yu。")
    assert r.success is True
    assert r.verified is True
    assert r.memory_id is not None

    m = store.get_memory(r.memory_id)
    assert m.source_type == USER_EXPLICIT
    assert m.verified is True
    assert m.source_event_id is not None  # DB 存在 + 有证据
    assert any(e.event_type == AUDIT_MEMORY_CREATED for e in audit.list_recent(50))
    store.close()
    audit.close()


# ------------------------------------------------------------------ Test 002

def test_002_restart_persistence(tmp_path):
    db = tmp_path / "persist.db"
    store = MemoryStore(db)
    audit = AuditStore(tmp_path / "a.db")
    MemoryService(store, audit).create("我正在开发 Yu。")
    store.close()

    store2 = MemoryStore(db)  # 重启
    assert any("我正在开发 Yu" in m.content for m in store2.list_memories())
    store2.close()
    audit.close()


# ------------------------------------------------------------------ Test 003

def test_003_explicit_routing_beats_tool_router():
    intent = detect_memory_intent("记住：我只有一台华硕轻薄本。")
    assert intent is not None
    assert intent.intent == MEMORY_CREATE
    assert intent.payload == "我只有一台华硕轻薄本。"

    # Declarative 陈述（提到电脑）不得触发 Computer Context。
    assert is_computer_request("我只有一台电脑。") is False


# ------------------------------------------------------------------ Test 004

def test_004_false_knee_memory(tmp_path):
    store, _, _ = _svc(tmp_path)
    guard = MemoryAttributionGuard()
    ok = guard.check("建议注意膝盖负担。", store.list_verified_memories())
    assert ok.has_claim is False
    bad = guard.check("你之前说过膝盖疼。", store.list_verified_memories())
    assert bad.needs_block is True
    store.close()


# ------------------------------------------------------------------ Test 005

def test_005_assistant_contamination(tmp_path):
    store, _, _ = _svc(tmp_path)
    ev = store.add_event(type="assistant_said", content="如果膝盖不舒服，可以戴护膝。", role="assistant")
    m = store.add_memory(type="fact", content="用户膝盖不舒服", source_event_id=ev.id)
    assert m.source_type == ASSISTANT_INFERENCE
    assert m.verified is False
    assert MemoryAttributionGuard().check("你以前说过膝盖不舒服。", [m]).needs_block is True
    store.close()


# ------------------------------------------------------------------ Test 006

def test_006_summary_contamination(tmp_path):
    store, _, _ = _svc(tmp_path)
    m = store.add_memory(type="fact", content="用户可能很累", source_type=SUMMARY_DERIVED, confidence=0.5)
    assert m.verified is False
    assert MemoryAttributionGuard().check("你昨天说自己很累。", [m]).needs_block is True
    store.close()


# ------------------------------------------------------------------ Test 007

def test_007_update_propagates(tmp_path):
    store, audit, service = _svc(tmp_path)
    mid = service.create("用户正在开发 Yu。").memory_id
    assert service.update(mid, "用户正在长期开发 Yu。").success is True

    assert store.get_memory(mid).content == "用户正在长期开发 Yu。"  # DB
    assert len(store.list_memories()) == 1  # count 不变
    matches = store.retrieve("开发 Yu", limit=5)  # Retrieval
    assert matches and matches[0][0].content == "用户正在长期开发 Yu。"
    assert any(e.event_type == AUDIT_MEMORY_UPDATED for e in audit.list_recent(50))
    store.close()
    audit.close()


# ------------------------------------------------------------------ Test 008

def test_008_fake_update_prevention(tmp_path):
    store, audit, service = _svc(tmp_path)
    r = service.update(9999, "B")
    assert r.success is False
    assert ("失败" in r.reason) or ("没有找到" in r.reason)

    mid = service.create("A").memory_id
    service.archive(mid)
    r2 = service.update(mid, "B")  # 已归档不可更新
    assert r2.success is False
    store.close()
    audit.close()


# ------------------------------------------------------------------ Test 009

def test_009_retrieval_no_stale_data(tmp_path):
    store, audit, service = _svc(tmp_path)
    mid = service.create("用户正在开发 Yu。").memory_id
    service.update(mid, "用户正在长期开发 Yu。")
    matches = store.retrieve("开发 Yu", limit=5)
    assert matches and matches[0][0].content == "用户正在长期开发 Yu。"
    assert all(m.content == "用户正在长期开发 Yu。" for m, _ in matches)
    store.close()
    audit.close()


# ------------------------------------------------------------------ Test 010

def test_010_conversation_chip_current_content(tmp_path):
    store, audit, service = _svc(tmp_path)
    mid = service.create("旧内容：学习 AI").memory_id
    service.update(mid, "新内容：学习 AI 与数学")
    matches = store.retrieve("学习 AI", limit=5)
    # Conversation Chip 显示 retrieved 的当前内容（API 返回的 server state）。
    assert matches[0][0].content == "新内容：学习 AI 与数学"
    store.close()
    audit.close()


# ------------------------------------------------------------------ Test 011

def test_011_memory_universe_current_content(tmp_path):
    store, audit, service = _svc(tmp_path)
    mid = service.create("旧内容：项目 Yu").memory_id
    service.update(mid, "新内容：项目 Yu 长期开发")
    # /api/memories 返回 current server state（Memory Universe 数据源）。
    contents = [m.content for m in store.list_memories()]
    assert "新内容：项目 Yu 长期开发" in contents
    store.close()
    audit.close()


# ------------------------------------------------------------------ Test 012

def test_012_correction(tmp_path):
    store, audit, service = _svc(tmp_path)
    r = service.correct("我没说过膝盖疼。")  # 无记忆 -> generation hallucination
    assert r.kind == "generation_hallucination"
    assert any(e.event_type == AUDIT_MEMORY_HALLUCINATION for e in audit.list_recent(50))

    m = store.add_user_memory("fact", "用户膝盖疼")
    r2 = service.correct("我没说过膝盖疼。")  # 有记忆 -> invalidate
    assert r2.kind == "invalidated"
    assert store.get_memory(m.id).status == "invalidated"
    assert any(e.event_type == AUDIT_MEMORY_INVALIDATED for e in audit.list_recent(50))
    store.close()
    audit.close()


# ------------------------------------------------------------------ Test 013

def test_013_archive(tmp_path):
    store, audit, service = _svc(tmp_path)
    mid = service.create("用户喜欢咖啡").memory_id
    assert service.archive(mid).success is True
    assert store.get_memory(mid).status == "archived"
    assert [x.id for x in store.list_memories()] == []  # active 列表不再包含
    assert store.retrieve("咖啡", limit=5) == []  # 检索不再返回
    assert any(e.event_type == AUDIT_MEMORY_ARCHIVED for e in audit.list_recent(50))
    store.close()
    audit.close()


# ------------------------------------------------------------------ Test 014

def test_014_ambiguous_reference(tmp_path):
    store, audit, service = _svc(tmp_path, name="amb")
    for c in ("记忆 A", "记忆 B", "记忆 C"):
        store.add_user_memory("fact", c)

    res = service.resolve_reference(None, store.list_memories())
    assert res.memory_id is None
    assert "哪一条" in res.reason

    res3 = service.resolve_reference([1, 2, 3], store.list_memories())
    assert res3.memory_id is None
    assert "哪一条" in res3.reason
    store.close()

    store2 = MemoryStore(tmp_path / "single.db")
    audit2 = AuditStore(tmp_path / "single_audit.db")
    service2 = MemoryService(store2, audit2)
    m = store2.add_user_memory("fact", "唯一记忆")
    res2 = service2.resolve_reference(None, store2.list_memories())
    assert res2.memory_id == m.id
    store2.close()
    audit2.close()
    audit.close()


# ------------------------------------------------------------------ Test 015

def test_015_no_evidence(tmp_path):
    store, _, _ = _svc(tmp_path)
    question = "我之前说过膝盖疼吗？"
    assert is_memory_probe(question) is True
    assert has_verified_support(question, store.list_verified_memories()) is False
    assert NO_RELIABLE_MEMORY_REPLY == "我目前没有可靠记忆显示你之前提到过这个。"
    store.close()


# ------------------------------------------------------------------ E2E

def test_e2e_full_lifecycle(tmp_path):
    db = tmp_path / "e2e.db"
    audit = AuditStore(tmp_path / "e2e_audit.db")

    store = MemoryStore(db)
    service = MemoryService(store, audit)
    # Create
    mid = service.create("用户正在开发 Yu。").memory_id
    assert store.get_memory(mid).content == "用户正在开发 Yu。"
    # Update
    assert service.update(mid, "用户正在长期开发 Yu。").success is True
    assert store.get_memory(mid).content == "用户正在长期开发 Yu。"
    # Restart
    store.close()
    store = MemoryStore(db)
    service = MemoryService(store, audit)
    assert store.get_memory(mid).content == "用户正在长期开发 Yu。"
    # Correct
    r = service.correct("我没说过我在开发 Yu。")
    assert r.kind == "invalidated"
    assert store.get_memory(mid).status == "invalidated"
    assert [x.id for x in store.list_memories()] == []
    # Archive
    m2 = service.create("用户喜欢咖啡").memory_id
    assert service.archive(m2).success is True
    assert store.get_memory(m2).status == "archived"
    store.close()
    audit.close()