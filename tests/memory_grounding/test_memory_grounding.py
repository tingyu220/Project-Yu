"""Memory Grounding & Provenance 回归测试（Yu v0.0.7.2 方案 §49-59）。

覆盖方案中的 Test 001 - Test 010，以及 MemoryWriteValidator / Attribution Guard /
build_context provenance 分区 / Correction Flow。

全部测试使用 tmp_path，绝不触碰 data/ 下的真实数据库。
"""

from __future__ import annotations

import pytest

from yu.audit.store import AuditStore
from yu.memory.correction import MemoryCorrectionService, is_correction
from yu.memory.guard import MemoryAttributionGuard, detect_historical_claims, has_verified_support
from yu.memory.models import Memory
from yu.memory.provenance import (
    ASSISTANT_INFERENCE,
    AUDIT_MEMORY_CLAIM_UNSUPPORTED,
    AUDIT_MEMORY_CORRECTED,
    AUDIT_MEMORY_HALLUCINATION,
    AUDIT_MEMORY_INVALIDATED,
    NO_RELIABLE_MEMORY_REPLY,
    SUMMARY_DERIVED,
    UNKNOWN,
    USER_EXPLICIT,
    is_memory_probe,
)
from yu.memory.retrieval import build_context, retrieve
from yu.memory.store import MemoryStore
from yu.memory.validator import MemoryWriteError, MemoryWriteValidator


def _mem(content, source_type=UNKNOWN, source_role=None, confidence=0.5, mid=1, type_="fact"):
    return Memory(
        id=mid,
        type=type_,
        content=content,
        importance="high",
        status="active",
        source_event_id=None,
        created_at="",
        archived_at=None,
        source_type=source_type,
        source_role=source_role,
        confidence=confidence,
    )


# ------------------------------------------------------------------ Test 001

def test_001_valid_recall_is_verified_and_retrievable(tmp_path):
    """用户明确输入 -> USER_EXPLICIT + 证据；检索时按 verified 注入上下文。"""
    store = MemoryStore(tmp_path / "m.db")
    m = store.remember("我正在开发 Yu。")
    assert m.source_type == USER_EXPLICIT
    assert m.source_role == "user"
    assert m.confidence == 1.0
    assert m.source_event_id is not None
    assert m.verified is True

    matches = store.retrieve("Yu 开发", limit=5)
    assert matches
    ctx = build_context(matches)
    assert "[VERIFIED USER MEMORY]" in ctx
    assert "我正在开发 Yu。" in ctx
    assert "证据:" in ctx
    store.close()


# ------------------------------------------------------------------ Test 002

def test_002_false_knee_memory_is_blocked(tmp_path):
    """数据库无膝盖记忆 -> 「你之前提到膝盖疼」必须被归因守卫拦截。"""
    store = MemoryStore(tmp_path / "m.db")
    store.remember("我正在开发 Yu。")  # 只有一条无关的 verified 记忆

    # 允许：普通建议，不含历史归因。
    guard = MemoryAttributionGuard()
    ok = guard.check("建议注意膝盖负荷。", store.list_verified_memories())
    assert ok.has_claim is False
    assert ok.supported is True

    # 禁止：无证据的历史归因。
    bad = guard.check("你之前提到膝盖偶尔会不舒服。", store.list_verified_memories())
    assert bad.has_claim is True
    assert bad.supported is False
    assert bad.needs_block is True

    # 检索爬山建议不应返回膝盖记忆（数据库里根本没有）。
    matches = store.retrieve("我要去爬山，给我建议。", limit=5)
    assert not any("膝盖" in m.content for m, _ in matches)
    store.close()


# ------------------------------------------------------------------ Test 003

def test_003_assistant_contamination_cannot_create_user_fact(tmp_path):
    """Round1 assistant 假设 -> 不得成为用户事实。"""
    store = MemoryStore(tmp_path / "m.db")
    ev = store.add_event(type="assistant_said", content="如果膝盖不舒服，可以带护膝。", role="assistant")

    # 从 assistant 事件派生的记忆必须是推断、非 verified。
    m = store.add_memory(type="fact", content="用户膝盖不舒服", source_event_id=ev.id)
    assert m.source_type == ASSISTANT_INFERENCE
    assert m.verified is False

    # 经写入门时，assistant 来源直接拒绝。
    with pytest.raises(MemoryWriteError) as exc:
        store.write_memory(
            type="fact", content="用户膝盖不舒服",
            source_event_id=ev.id, source_role="assistant",
        )
    assert exc.value.code == "ASSISTANT_CONTENT_CANNOT_CREATE_USER_FACT"

    # Round2：即使用户再问，也无法用 assistant 记忆做历史归因。
    guard = MemoryAttributionGuard()
    v = guard.check("你之前说膝盖不舒服。", [m])
    assert v.supported is False
    store.close()


# ------------------------------------------------------------------ Test 004

def test_004_summary_contamination_is_not_verified(tmp_path):
    """Daily Summary 派生内容不得成为 verified 用户事实。"""
    store = MemoryStore(tmp_path / "m.db")
    m = store.add_memory(
        type="fact", content="用户可能比较疲劳",
        source_type=SUMMARY_DERIVED, source_role=None, confidence=0.5,
    )
    assert m.verified is False

    guard = MemoryAttributionGuard()
    v = guard.check("你昨天说自己很累。", [m])
    assert v.supported is False
    assert v.needs_block is True

    # 写入门拒绝 SUMMARY_DERIVED 作为 verified 记忆。
    with pytest.raises(MemoryWriteError) as exc:
        store.write_memory(type="fact", content="用户可能比较疲劳", source_type=SUMMARY_DERIVED)
    assert exc.value.code == "SUMMARY_DERIVED_CANNOT_CREATE_USER_FACT"
    store.close()


# ------------------------------------------------------------------ Test 005

def test_005_unknown_memory_cannot_support_attribution(tmp_path):
    """source_type=UNKNOWN 的旧记忆不能支撑「你之前说过」。"""
    store = MemoryStore(tmp_path / "m.db")
    m = store.add_memory(
        type="fact", content="用户膝盖不好",
        source_type=UNKNOWN, confidence=0.5,
    )
    assert m.verified is False

    ctx = build_context([(m, 2.0)])
    assert "[UNVERIFIED OBSERVATION]" in ctx
    # 「用户曾明确表达：」前缀只出现在 verified 分区，未验证记忆不应出现该分区。
    assert "用户曾明确表达：" not in ctx

    guard = MemoryAttributionGuard()
    v = guard.check("你之前说膝盖不好。", [m])
    assert v.supported is False
    store.close()


# ------------------------------------------------------------------ Test 006

def test_006_user_explicit_can_support_attribution(tmp_path):
    """用户明确说「膝盖疼」-> USER_EXPLICIT -> 允许「你之前提到膝盖」。"""
    store = MemoryStore(tmp_path / "m.db")
    m = store.add_user_memory(type="fact", content="我最近膝盖确实有点疼", source_type=USER_EXPLICIT)
    assert m.verified is True

    guard = MemoryAttributionGuard()
    v = guard.check("你之前提到最近膝盖有些不舒服。", [m])
    assert v.has_claim is True
    assert v.supported is True
    assert v.needs_block is False
    store.close()


# ------------------------------------------------------------------ Test 007

def test_007_correction_flow_hallucination_and_invalidate(tmp_path):
    """用户纠正：有错记忆 -> invalidate；无记忆 -> MEMORY_HALLUCINATION。"""
    # A. 无对应记忆 -> generation hallucination
    store = MemoryStore(tmp_path / "m.db")
    audit = AuditStore(tmp_path / "a.db")
    service = MemoryCorrectionService(store, audit)
    r1 = service.handle_correction("我没说过。")
    assert r1.kind == "generation_hallucination"
    assert any(e.event_type == AUDIT_MEMORY_HALLUCINATION for e in audit.list_recent(50))
    store.close()
    audit.close()

    # B. 存在错误记忆 -> invalidate + 审计
    store2 = MemoryStore(tmp_path / "m2.db")
    audit2 = AuditStore(tmp_path / "a2.db")
    mem = store2.add_user_memory(type="fact", content="用户膝盖疼")
    service2 = MemoryCorrectionService(store2, audit2)
    r2 = service2.handle_correction("我没说过膝盖疼。")
    assert r2.kind == "invalidated"
    assert r2.target_memory_id == mem.id
    assert store2.get_memory(mem.id).status == "invalidated"
    types = {e.event_type for e in audit2.list_recent(50)}
    assert AUDIT_MEMORY_INVALIDATED in types
    assert AUDIT_MEMORY_CORRECTED in types
    store2.close()
    audit2.close()


# ------------------------------------------------------------------ Test 008

def test_008_no_evidence_question_has_no_reliable_memory(tmp_path):
    """「我以前说过 X 吗？」无记忆 -> 确定性回答「没有可靠记忆」。"""
    store = MemoryStore(tmp_path / "m.db")
    question = "我以前说过我膝盖疼吗？"
    assert is_memory_probe(question) is True
    assert has_verified_support(question, store.list_verified_memories()) is False
    assert NO_RELIABLE_MEMORY_REPLY == "我目前没有可靠记忆显示你之前提到过这个。"
    store.close()


# ------------------------------------------------------------------ Test 009

def test_009_assistant_memory_extraction_is_blocked(tmp_path):
    """Assistant「你可能喜欢安静的地方」不得提取为「用户喜欢安静的地方」。"""
    store = MemoryStore(tmp_path / "m.db")
    with pytest.raises(MemoryWriteError) as exc:
        store.write_memory(
            type="fact", content="用户喜欢安静的地方",
            source_role="assistant", source_type=ASSISTANT_INFERENCE,
        )
    assert exc.value.code in ("ASSISTANT_CONTENT_CANNOT_CREATE_USER_FACT", "INFERENCE_CANNOT_CREATE_USER_FACT")
    store.close()


# ------------------------------------------------------------------ Test 010

def test_010_summary_memory_extraction_is_blocked(tmp_path):
    """Summary「用户似乎喜欢旅行」不得生成 verified personal memory。"""
    store = MemoryStore(tmp_path / "m.db")
    with pytest.raises(MemoryWriteError) as exc:
        store.write_memory(
            type="fact", content="用户喜欢旅行",
            source_type=SUMMARY_DERIVED,
        )
    assert exc.value.code == "SUMMARY_DERIVED_CANNOT_CREATE_USER_FACT"
    store.close()


# ------------------------------------------------------------------ Validator 补充

def test_validator_rejects_ungrounded_personal_memory(tmp_path):
    store = MemoryStore(tmp_path / "m.db")
    with pytest.raises(MemoryWriteError) as exc:
        store.write_memory(type="fact", content="用户膝盖不好", source_type=USER_EXPLICIT, source_role="user", source_event_id=None)
    assert exc.value.code == "MEMORY_WRITE_REJECTED_UNGROUNDED"
    store.close()


def test_validator_allows_system_fact_without_event(tmp_path):
    store = MemoryStore(tmp_path / "m.db")
    m = store.add_system_fact("系统状态：SQLite 可用")
    assert m.source_type == "SYSTEM_FACT"
    assert m.verified is True
    store.close()


def test_detect_historical_claims():
    claims = detect_historical_claims("你之前提到膝盖疼，我记得你以前说过。")
    assert "你之前提到" in claims
    assert "我记得你" in claims


def test_is_correction():
    assert is_correction("我没说过这个。") is True
    assert is_correction("你好") is False