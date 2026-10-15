import asyncio
import json

import pytest


class Socket:
    def __init__(self, events):
        self.events = list(events)
        self.sent = []
        self.closed = False
    async def recv(self):
        await asyncio.sleep(0.01)
        if self.events:
            return json.dumps(self.events.pop(0))
        while not self.events:
            await asyncio.sleep(0.01)
        return json.dumps(self.events.pop(0))
    async def send(self, data):
        self.sent.append(data)
    async def close(self):
        self.closed = True


class Capture:
    muted = False
    def read(self, timeout):
        import time
        time.sleep(0.005)
        return b"\0" * 3200
    def discard(self):
        pass


class Feedback:
    def cue(self):
        pass
    def speak(self, text):
        pass


def setup(events, monkeypatch):
    from yu.voice.wake import session
    from yu.voice.wake.config import WakeConfig
    from yu.voice.wake.state import WakeController
    socket = Socket(events)
    connections = []

    class Connection:
        async def __aenter__(self):
            connections.append(True)
            return socket
        async def __aexit__(self, *_):
            connections.append(False)

    monkeypatch.setattr(session, "connect", lambda *a, **k: Connection())
    return session.VoiceSession("http://127.0.0.1:8792"), WakeController(WakeConfig()), socket, connections


def test_waiting_never_connects(monkeypatch):
    s, c, socket, connections = setup([], monkeypatch)
    asyncio.run(s.run(Capture(), c, Feedback()))
    assert connections == []
    assert socket.sent == []


def test_service_stop_closes_session_without_chat(monkeypatch):
    s, c, socket, connections = setup([
        {"type": "ready"},
        {"type": "final", "id": "stop", "text": "停止本次服务"},
    ], monkeypatch)
    async def forbidden(*args):
        pytest.fail("停止服务不得交给聊天模型")
    monkeypatch.setattr(s, "submit", forbidden)
    c.wake()
    asyncio.run(asyncio.wait_for(s.run(Capture(), c, Feedback()), 1))
    assert c.state.value == "stopped"
    assert socket.closed
    assert connections == [True, False]


def test_error_before_ready_never_uploads(monkeypatch):
    s, c, socket, connections = setup([{"type": "error", "message": "忙"}], monkeypatch)
    c.wake()
    with pytest.raises(RuntimeError):
        asyncio.run(s.run(Capture(), c, Feedback()))
    assert socket.sent == []
    assert connections == [True, False]


def test_handshake_does_not_accumulate_microphone_audio(monkeypatch):
    from yu.voice.wake import session
    from yu.voice.wake.capture import AudioCapture
    from yu.voice.wake.config import WakeConfig
    from yu.voice.wake.state import WakeController
    capture = AudioCapture(WakeConfig())
    socket = Socket([{"type": "error", "message": "连接失败"}])
    class Connection:
        async def __aenter__(self):
            # 模拟连接耗时超过两秒；此时尚不能发送任何录音。
            for _ in range(25):
                capture._callback(bytes(3200), 1600, None, False)
            return socket
        async def __aexit__(self, *_):
            pass
    monkeypatch.setattr(session, "connect", lambda *a, **k: Connection())
    c = WakeController(WakeConfig())
    c.wake()
    with pytest.raises(RuntimeError, match="连接失败"):
        asyncio.run(session.VoiceSession("http://127.0.0.1:8792").run(capture, c, Feedback()))
    assert capture._error is None
    assert socket.sent == []
    assert not capture.muted


def test_duplicate_final_submits_once_and_stop_closes(monkeypatch):
    s, c, socket, connections = setup([
        {"type": "ready"},
        {"type": "final", "id": "1", "text": "打开微信"},
        {"type": "final", "id": "1", "text": "打开微信"},
        {"type": "final", "id": "2", "text": "结束"},
    ], monkeypatch)
    submitted = []
    async def submit(text, history):
        submitted.append(text)
        return {"reply": "已恢复微信窗口", "kind": "action", "allowed": True,
                "action": {"success": True}}
    monkeypatch.setattr(s, "submit", submit)
    c.wake()
    async def bounded():
        await asyncio.wait_for(s.run(Capture(), c, Feedback()), 2)
    asyncio.run(bounded())
    assert submitted == ["打开微信"]
    assert connections == [True, False]
    assert c.state.value == "waiting"


@pytest.mark.parametrize("url", ["http://example.com:8792", "http://127.0.0.1:8080", "http://evil@127.0.0.1:8792", "http://127.0.0.1:8792/path"])
def test_client_rejects_nonlocal_or_modified_endpoint(url):
    from yu.voice.wake.session import VoiceSession
    with pytest.raises(ValueError):
        VoiceSession(url)


def test_stop_closes_audio_and_cancels_pending_but_collects_inflight_result(monkeypatch):
    async def scenario():
        s, c, socket, connections = setup([
            {"type": "ready"},
            {"type": "final", "id": "1", "text": "打开微信"},
            {"type": "final", "id": "2", "text": "打开QQ音乐"},
            {"type": "final", "id": "3", "text": "结束"},
        ], monkeypatch)
        release = asyncio.Event()
        submitted = []
        async def submit(text, history):
            submitted.append(text)
            await release.wait()
            return {"reply": "已恢复微信", "allowed": True}
        monkeypatch.setattr(s, "submit", submit)
        c.wake()
        task = asyncio.create_task(s.run(Capture(), c, Feedback()))
        for _ in range(100):
            if socket.closed:
                break
            await asyncio.sleep(0.01)
        assert socket.closed
        assert not task.done()
        release.set()
        await asyncio.wait_for(task, 2)
        assert submitted == ["打开微信"]
    asyncio.run(scenario())


def test_business_failure_clears_pending_commands(monkeypatch):
    async def scenario():
        s, c, socket, _ = setup([
            {"type": "ready"},
            {"type": "final", "id": "1", "text": "打开微信"},
            {"type": "final", "id": "2", "text": "打开QQ音乐"},
            {"type": "final", "id": "3", "text": "结束"},
        ], monkeypatch)
        submitted = []
        async def submit(text, history):
            submitted.append(text)
            await asyncio.sleep(0.015)
            return {"reply": "未找到窗口", "allowed": True, "action": {"success": False}}
        monkeypatch.setattr(s, "submit", submit)
        c.wake()
        await s.run(Capture(), c, Feedback())
        assert submitted == ["打开微信"]
    asyncio.run(scenario())


def test_stop_before_worker_wakes_does_not_submit(monkeypatch):
    async def scenario():
        s, c, socket, _ = setup([], monkeypatch)
        events = [{"type": "ready"}, {"type": "final", "id": "1", "text": "打开微信"},
                  {"type": "final", "id": "2", "text": "结束"}]
        async def receive():
            if len(events) == 2:
                await asyncio.sleep(0)
            if events:
                return json.dumps(events.pop(0))
            await asyncio.Future()
        socket.recv = receive
        submitted = []
        async def submit(text, history):
            submitted.append(text)
            return {"reply": "不应执行"}
        monkeypatch.setattr(s, "submit", submit)
        c.wake()
        await asyncio.wait_for(s.run(Capture(), c, Feedback()), 2)
        assert submitted == []
    asyncio.run(scenario())


def test_disconnect_does_not_unmute_until_real_speech_finishes(monkeypatch):
    async def scenario():
        import threading
        s, c, socket, _ = setup([{"type": "ready"},
            {"type": "final", "id": "1", "text": "你好"}], monkeypatch)
        started, release = threading.Event(), threading.Event()
        class Speaking(Feedback):
            def speak(self, text):
                started.set()
                release.wait(2)
        async def submit(text, history):
            return {"reply": "嘿宇"}
        monkeypatch.setattr(s, "submit", submit)
        capture = Capture()
        c.wake()
        task = asyncio.create_task(s.run(capture, c, Speaking()))
        try:
            for _ in range(100):
                if started.is_set():
                    break
                await asyncio.sleep(0.01)
            assert started.is_set()
            socket.events.append({"type": "error", "message": "断连"})
            await asyncio.sleep(0.05)
            assert capture.muted
            assert not task.done()
        finally:
            release.set()
        with pytest.raises(RuntimeError):
            await asyncio.wait_for(task, 2)
        assert not capture.muted
    asyncio.run(scenario())


def test_three_pending_commands_limit_ends_session_without_replay(monkeypatch):
    async def scenario():
        s, c, socket, connections = setup([{"type": "ready"}] + [
            {"type": "final", "id": str(i), "text": "打开微信"} for i in range(5)
        ], monkeypatch)
        submitted = []
        async def submit(text, history):
            submitted.append(text)
            await asyncio.sleep(0.15)
            return {"reply": "真实回执"}
        monkeypatch.setattr(s, "submit", submit)
        c.wake()
        with pytest.raises(RuntimeError, match="队列"):
            await asyncio.wait_for(s.run(Capture(), c, Feedback()), 2)
        assert submitted == ["打开微信"]
        assert connections == [True, False]
    asyncio.run(scenario())


def test_slow_audio_send_is_cancelled_on_timeout_without_reconnect(monkeypatch):
    async def scenario():
        from yu.voice.wake.config import WakeConfig
        from yu.voice.wake.state import WakeController
        s, _, socket, connections = setup([{"type": "ready"}], monkeypatch)
        attempts = []
        async def send(data):
            attempts.append(data)
            await asyncio.Future()
        socket.send = send
        c = WakeController(WakeConfig(idle_seconds=0.2))
        c.wake()
        await asyncio.wait_for(s.run(Capture(), c, Feedback()), 2)
        assert len(attempts) == 1
        assert connections == [True, False]
    asyncio.run(scenario())
