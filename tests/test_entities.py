"""Tests for structured entities (Goal / Task / Decision / Project) — Phase 4."""

import sqlite3

import pytest

from yu.entities.store import EntitiesStore


def _store(tmp_path):
    return EntitiesStore(tmp_path / "entities.db")


def test_goal_add_and_list(tmp_path):
    store = _store(tmp_path)
    g = store.add_goal("学习 AI")
    assert g.id >= 1
    assert g.status == "active"
    assert [x.title for x in store.list_goals()] == ["学习 AI"]
    store.close()


def test_goal_update_status(tmp_path):
    store = _store(tmp_path)
    g = store.add_goal("完成 Yu V0.1")
    updated = store.update_goal_status(g.id, "completed")
    assert updated.status == "completed"
    assert store.update_goal_status(999, "completed") is None
    store.close()


def test_goal_persistence(tmp_path):
    db = tmp_path / "g.db"
    store = EntitiesStore(db)
    store.add_goal("进入 AI 相关行业")
    store.close()

    store2 = EntitiesStore(db)
    assert [x.title for x in store2.list_goals()] == ["进入 AI 相关行业"]
    store2.close()


def test_task_add_and_list(tmp_path):
    store = _store(tmp_path)
    g = store.add_goal("学习 AI")
    t = store.add_task("完成 pytest 测试", related_goal=g.id)
    assert t.status == "todo"
    assert t.priority == "medium"
    assert t.related_goal == g.id
    tasks = store.list_tasks()
    assert len(tasks) == 1
    assert tasks[0].title == "完成 pytest 测试"
    store.close()


def test_task_update_status(tmp_path):
    store = _store(tmp_path)
    t = store.add_task("写测试")
    updated = store.update_task_status(t.id, "done")
    assert updated.status == "done"
    assert store.update_task_status(999, "done") is None
    store.close()


def test_task_foreign_key_constraint(tmp_path):
    store = _store(tmp_path)
    with pytest.raises(sqlite3.IntegrityError):
        store.add_task("无效任务", related_goal=999)
    store.close()


def test_project_add_list_update(tmp_path):
    store = _store(tmp_path)
    p = store.add_project("Yu", current_goal="完成 V0.1", next_step="实现 Phase 4")
    assert p.name == "Yu"
    assert p.status == "active"
    updated = store.update_project(p.id, status="paused", next_step="实现 Phase 5")
    assert updated.status == "paused"
    assert updated.next_step == "实现 Phase 5"
    assert len(store.list_projects()) == 1
    store.close()


def test_decision_add_and_list(tmp_path):
    store = _store(tmp_path)
    d = store.add_decision("Yu V0.1 暂时只开发 Windows PC", reason="减少开发成本和复杂度")
    assert d.decision.startswith("Yu V0.1")
    assert d.reason == "减少开发成本和复杂度"
    assert len(store.list_decisions()) == 1
    store.close()


def test_entities_coexist_with_memory_same_db(tmp_path):
    db = tmp_path / "shared.db"
    from yu.memory.store import MemoryStore

    mstore = MemoryStore(db)
    mstore.remember("用户正在开发 Yu。")
    estore = EntitiesStore(db)
    estore.add_goal("完成 Yu V0.1")

    assert len(mstore.list_memories()) == 1
    assert len(estore.list_goals()) == 1
    mstore.close()
    estore.close()
