"""Tests for Memory Retrieval (Phase 3)."""

import pytest

from yu.memory.models import Memory
from yu.memory.retrieval import build_context, retrieve, score, tokenize
from yu.memory.store import MemoryStore


def _mem(mid, content, importance="high"):
    return Memory(
        id=mid,
        type="fact",
        content=content,
        importance=importance,
        status="active",
        source_event_id=None,
        created_at="",
        archived_at=None,
    )


def test_tokenize_ascii_and_cjk_bigrams():
    terms = tokenize("AI 相关职业方向")
    assert "ai" in terms
    assert "相关" in terms
    assert "方向" in terms
    assert "发展" in tokenize("我想往什么方向发展")


def test_tokenize_filters_stopwords():
    terms = tokenize("用户想往什么方向发展")
    assert "用户" not in terms
    assert "什么" not in terms
    assert "发展" in terms


def test_score_zero_when_no_overlap():
    m = _mem(1, "用户喜欢喝咖啡。")
    assert score(m, "我早餐想吃什么") == 0.0


def test_score_positive_with_importance():
    m_high = _mem(1, "用户希望长期向 AI 相关职业方向发展。", importance="high")
    m_low = _mem(2, "用户希望长期向 AI 相关职业方向发展。", importance="low")
    q = "我以后想往什么方向发展？"
    assert score(m_high, q) > 0.0
    assert score(m_high, q) > score(m_low, q)


def test_retrieve_returns_relevant_sorted():
    memories = [
        _mem(1, "用户喜欢喝咖啡。"),
        _mem(2, "用户希望长期向 AI 相关职业方向发展。"),
        _mem(3, "用户正在开发 Yu 项目。"),
    ]
    results = retrieve(memories, "我以后想往什么方向发展？")
    assert results
    assert results[0][0].id == 2


def test_retrieve_empty_when_no_match():
    memories = [_mem(1, "用户喜欢喝咖啡。")]
    assert retrieve(memories, "我早餐想吃什么") == []


def test_retrieve_limit():
    memories = [_mem(i, "AI 相关职业方向 " + str(i)) for i in range(1, 10)]
    results = retrieve(memories, "AI 相关职业方向", limit=3)
    assert len(results) == 3


def test_build_context_empty():
    assert build_context([]) == ""


def test_build_context_formats():
    matches = [(_mem(1, "用户喜欢喝咖啡。"), 2.0), (_mem(2, "用户正在开发 Yu。"), 1.0)]
    ctx = build_context(matches)
    assert "长期记忆" in ctx
    assert "用户喜欢喝咖啡。" in ctx
    assert "用户正在开发 Yu。" in ctx


def test_store_retrieve_integration(tmp_path):
    store = MemoryStore(tmp_path / "retr.db")
    store.remember("用户希望长期向 AI 相关职业方向发展。")
    store.remember("用户喜欢喝咖啡。")
    results = store.retrieve("我以后想往什么方向发展？", limit=5)
    assert results
    assert "AI 相关职业" in results[0][0].content
    store.close()


def test_store_retrieve_acceptance_scenario(tmp_path):
    """Phase 3 验收场景：先记住，再问方向，检索应命中该记忆。"""
    db = tmp_path / "acc.db"
    store = MemoryStore(db)
    store.remember("用户希望长期向 AI 相关职业方向发展。")
    store.close()

    store2 = MemoryStore(db)
    results = store2.retrieve("宇，我以后想往什么方向发展？", limit=3)
    store2.close()
    assert results
    assert any("AI 相关职业" in m.content for m, _ in results)
