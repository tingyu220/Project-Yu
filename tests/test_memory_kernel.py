"""Tests for the Yu Memory Kernel (Phase 1).

All tests use pytest's tmp_path fixture so the real database under data/
is never touched — test and production storage are isolated.
"""

import sqlite3

import pytest

from yu.memory.store import MemoryStore


def _store(tmp_path):
    return MemoryStore(tmp_path / "yu_test.db")


def test_database_is_created_on_first_start(tmp_path):
    db = tmp_path / "first.db"
    assert not db.exists()
    store = MemoryStore(db)
    assert db.exists()
    names = {
        r["name"]
        for r in store._conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    assert {"events", "memories"} <= names
    store.close()


def test_event_can_be_written(tmp_path):
    store = _store(tmp_path)
    ev = store.add_event("user_said", "记住：我正在开发 Yu。")
    assert ev.id >= 1
    assert ev.type == "user_said"
    assert ev.created_at
    assert [e.content for e in store.list_events()] == ["记住：我正在开发 Yu。"]
    store.close()


def test_memory_can_be_written(tmp_path):
    store = _store(tmp_path)
    m = store.add_memory("fact", "用户正在开发 Yu 项目。", importance="high")
    assert m.id >= 1
    assert m.status == "active"
    assert m.importance == "high"
    store.close()


def test_memory_can_be_read(tmp_path):
    store = _store(tmp_path)
    m = store.add_memory("fact", "用户希望向 AI 方向发展。")
    got = store.get_memory(m.id)
    assert got is not None
    assert got.content == "用户希望向 AI 方向发展。"
    assert store.get_memory(9999) is None
    store.close()


def test_multiple_memories_are_saved_in_order(tmp_path):
    store = _store(tmp_path)
    store.add_memory("fact", "第一条")
    store.add_memory("fact", "第二条")
    store.add_memory("fact", "第三条")
    contents = [m.content for m in store.list_memories()]
    assert contents == ["第一条", "第二条", "第三条"]
    store.close()


def test_persistence_across_reopen(tmp_path):
    db = tmp_path / "persist.db"
    store = MemoryStore(db)
    store.remember("我正在开发属于自己的 Yu。")
    store.close()  # simulate closing the program

    store2 = MemoryStore(db)  # simulate reopening the program
    contents = [m.content for m in store2.list_memories()]
    assert "我正在开发属于自己的 Yu。" in contents
    store2.close()


def test_remember_creates_event_and_memory(tmp_path):
    store = _store(tmp_path)
    m = store.remember("我正在开发 Yu。")
    assert m.type == "fact"
    assert m.importance == "high"
    assert m.source_event_id is not None
    events = store.list_events()
    assert len(events) == 1
    assert events[0].type == "user_said"
    assert events[0].content == "记住：我正在开发 Yu。"
    assert events[0].id == m.source_event_id
    store.close()


def test_event_cannot_be_updated_via_api():
    assert not hasattr(MemoryStore, "update_event")
    assert not hasattr(MemoryStore, "delete_event")


def test_event_cannot_be_updated_at_db_level(tmp_path):
    db = tmp_path / "append_only.db"
    store = MemoryStore(db)
    ev = store.add_event("user_said", "原始历史内容")
    store.close()

    conn = sqlite3.connect(str(db))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE events SET content = '被篡改' WHERE id = ?", (ev.id,))
    conn.close()


def test_event_cannot_be_deleted_at_db_level(tmp_path):
    db = tmp_path / "append_only.db"
    store = MemoryStore(db)
    ev = store.add_event("user_said", "原始历史内容")
    store.close()

    conn = sqlite3.connect(str(db))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM events WHERE id = ?", (ev.id,))
    conn.close()


def test_archive_does_not_delete_history(tmp_path):
    store = _store(tmp_path)
    m = store.add_memory("fact", "要被归档的记忆")
    archived = store.archive_memory(m.id)
    assert archived is not None
    assert archived.status == "archived"
    assert archived.archived_at is not None

    # 从有效列表消失 ...
    assert [x.id for x in store.list_memories()] == []
    # ... 但原始记录仍存在，且未删除
    assert store.get_memory(m.id).content == "要被归档的记忆"
    assert [x.id for x in store.list_memories(include_archived=True)] == [m.id]
    store.close()


def test_invalid_foreign_key_raises_integrity_error(tmp_path):
    store = _store(tmp_path)
    with pytest.raises(sqlite3.IntegrityError):
        store.add_memory("fact", "引用不存在的事件", source_event_id=9999)
    # 错误处理后 store 仍可正常使用
    m = store.add_memory("fact", "后续仍然可以写入")
    assert m.id >= 1
    store.close()
