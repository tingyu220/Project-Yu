import sqlite3


def test_migration_automatically_backs_up_existing_database(tmp_path):
    from yu.conversation.store import ConversationStore
    path = tmp_path / "existing.db"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE memories(content TEXT)")
        conn.execute("INSERT INTO memories VALUES ('原记忆')")
    store = ConversationStore(str(path))
    backups = list(tmp_path.glob("existing.db.before-conversation-*.db"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as conn:
        assert conn.execute("SELECT content FROM memories").fetchone()[0] == "原记忆"
    store.close()


def test_recovery_revision_is_newer_than_all_previous_updates(tmp_path):
    from yu.conversation.store import ConversationStore
    path = str(tmp_path / "db")
    store = ConversationStore(path)
    s = store.default_session()
    unfinished = store.insert_turn(s, "a", "web", "未完成")
    other = store.insert_turn(s, "b", "web", "其他")
    store.set_state(other.seq, "completed", {"reply": "完成"})
    cursor = store.changes(0)["next_cursor"]
    store.close()
    store = ConversationStore(path)
    assert store.changes(cursor)["turns"][0]["request_id"] == "a"
    store.close()


def test_restart_keeps_completed_history(tmp_path):
    from yu.conversation.store import ConversationStore
    path = str(tmp_path / "conversation.db")
    store = ConversationStore(path)
    session = store.default_session()
    turn = store.insert_turn(session, "r1", "web", "你好")
    store.set_state(turn.seq, "completed", {"reply": "你好，我是宇"})
    store.close()

    reopened = ConversationStore(path)
    assert reopened.default_session() == session
    assert reopened.history(session) == [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好，我是宇"},
    ]
    reopened.close()


def test_running_becomes_unknown_without_replay(tmp_path):
    from yu.conversation.store import ConversationStore
    path = str(tmp_path / "conversation.db")
    store = ConversationStore(path)
    turn = store.insert_turn(store.default_session(), "r1", "local_voice", "打开微信")
    store.set_state(turn.seq, "running")
    store.close()
    reopened = ConversationStore(path)
    result = reopened.get_request(reopened.default_session(), "r1")
    assert result.state == "unknown"
    assert reopened.history(reopened.default_session()) == []


def test_updates_advance_cursor_and_duplicate_is_idempotent(tmp_path):
    from yu.conversation.store import ConversationStore
    store = ConversationStore(str(tmp_path / "conversation.db"))
    session = store.default_session()
    turn = store.insert_turn(session, "r1", "web", "你好")
    first_cursor = store.changes(0)["next_cursor"]
    store.set_state(turn.seq, "completed", {"reply": "好"})
    changes = store.changes(first_cursor)
    assert changes["turns"][0]["state"] == "completed"
    assert changes["next_cursor"] > first_cursor
    same = store.insert_turn(session, "r1", "web", "你好")
    assert same.seq == turn.seq
    store.close()


def test_backup_preserves_existing_memories(tmp_path):
    from yu.conversation.store import ConversationStore
    path = str(tmp_path / "conversation.db")
    store = ConversationStore(path)
    store._conn.execute("CREATE TABLE memories (content TEXT NOT NULL)")
    store._conn.execute("INSERT INTO memories VALUES (?)", ("保留的记忆",))
    store._conn.commit()
    backup = str(tmp_path / "backup.db")
    store.backup(backup)
    store.close()
    with sqlite3.connect(backup) as conn:
        assert conn.execute("SELECT content FROM memories").fetchone()[0] == "保留的记忆"
