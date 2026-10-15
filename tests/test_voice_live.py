"""实时识别边界：字幕不执行、最终结果去重、拒绝跨站及无效音频。"""
import asyncio
import json
import base64

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from yu.api.voice import voice_router


def test_partial_and_final_are_distinct():
    from yu.voice.realtime import normalize_event
    assert normalize_event({"type": "conversation.item.input_audio_transcription.text",
                            "item_id": "a", "text": "打开", "stash": "QQ音乐"}) == {
        "type": "partial", "id": "a", "text": "打开QQ音乐"}
    assert normalize_event({"type": "conversation.item.input_audio_transcription.completed",
                            "item_id": "a", "transcript": "打开QQ音乐"}) == {
        "type": "final", "id": "a", "text": "打开QQ音乐"}
    assert normalize_event({"type": "conversation.item.created"}) is None


def test_provider_error_is_sanitized():
    from yu.voice.realtime import normalize_event
    result = normalize_event({"type": "error", "error": {"message": "secret-key"}})
    assert result["type"] == "error"
    assert "secret-key" not in json.dumps(result)


def test_origin_rejects_cross_site_before_connecting():
    app = FastAPI()
    app.include_router(voice_router())
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect("/api/voice/live", headers={"origin": "https://evil.example"}):
                pass
        assert exc.value.code == 1008


def test_live_missing_key_returns_actionable_error(monkeypatch):
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    app = FastAPI()
    app.include_router(voice_router())
    with TestClient(app, base_url="http://localhost") as client:
        with client.websocket_connect("ws://localhost/api/voice/live", headers={"origin": "http://localhost"}) as ws:
            event = ws.receive_json()
            assert event["type"] == "error"
            assert "配置" in event["message"]


def test_relay_configures_vad_and_deduplicates_finals():
    from yu.voice.realtime import relay

    async def scenario():
        class Browser:
            def __init__(self):
                self.output = []
            async def receive(self):
                await asyncio.Future()
            async def send_json(self, event):
                self.output.append(event)

        class Provider:
            def __init__(self):
                self.sent = []
            async def send(self, message):
                self.sent.append(json.loads(message))
            def __aiter__(self):
                return self.events()
            async def events(self):
                for event in [
                    {"type": "session.updated"},
                    {"type": "conversation.item.input_audio_transcription.completed", "item_id": "1", "transcript": "下一首"},
                    {"type": "conversation.item.input_audio_transcription.completed", "item_id": "1", "transcript": "下一首"},
                    {"type": "conversation.item.input_audio_transcription.completed", "item_id": "2", "transcript": "暂停"},
                ]:
                    yield json.dumps(event)

        browser, provider = Browser(), Provider()
        await relay(browser, provider)
        assert provider.sent[0]["session"]["input_audio_format"] == "pcm"
        assert provider.sent[0]["session"]["sample_rate"] == 16000
        assert provider.sent[0]["session"]["turn_detection"]["type"] == "server_vad"
        assert [e["text"] for e in browser.output if e["type"] == "final"] == ["下一首", "暂停"]
        assert browser.output[0]["type"] == "ready"
    asyncio.run(scenario())


def test_websocket_endpoint_streams_pcm_and_releases_provider(monkeypatch):
    """只替代外部供应商连接，保留本机 WebSocket 及协议转发。"""
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-only-key")
    monkeypatch.setenv("YU_VOICE_REGION", "cn-beijing")
    packets, connections, closed = [], [], []

    class Provider:
        async def __aenter__(self):
            self.events = asyncio.Queue()
            return self
        async def __aexit__(self, *args):
            closed.append(True)
        async def send(self, raw):
            event = json.loads(raw)
            packets.append(event)
            if event["type"] == "session.update":
                await self.events.put({"type": "session.updated"})
            else:
                assert base64.b64decode(event["audio"]) == b"\x00\x00" * 1600
                await self.events.put({"type": "conversation.item.input_audio_transcription.text",
                                       "item_id": "a", "text": "下一", "stash": "首"})
                await self.events.put({"type": "conversation.item.input_audio_transcription.completed",
                                       "item_id": "a", "transcript": "下一首"})
        def __aiter__(self):
            return self
        async def __anext__(self):
            return json.dumps(await self.events.get())

    def connect(url, **kwargs):
        connections.append((url, kwargs))
        return Provider()
    monkeypatch.setattr("websockets.asyncio.client.connect", connect)
    app = FastAPI()
    app.include_router(voice_router())
    with TestClient(app) as client:
        with client.websocket_connect("ws://localhost/api/voice/live", headers={"origin": "http://localhost"}) as ws:
            assert ws.receive_json() == {"type": "ready"}
            ws.send_bytes(b"\x00\x00" * 1600)
            assert ws.receive_json() == {"type": "partial", "id": "a", "text": "下一首"}
            assert ws.receive_json() == {"type": "final", "id": "a", "text": "下一首"}
    assert closed == [True]
    assert connections[0][0] == "wss://dashscope.aliyuncs.com/api-ws/v1/realtime?model=qwen3-asr-flash-realtime"
    assert connections[0][1]["additional_headers"] == {"Authorization": "Bearer test-only-key"}
    assert [p["type"] for p in packets] == ["session.update", "input_audio_buffer.append"]


def test_disconnect_cancels_pending_provider_handshake():
    from yu.voice.realtime import run_with_disconnect

    async def scenario():
        started = asyncio.Event()
        cancelled = []
        class Browser:
            async def receive(self):
                await started.wait()
                return {"type": "websocket.disconnect"}
        async def connecting(browser):
            started.set()
            try:
                await asyncio.Future()
            finally:
                cancelled.append(True)
        await asyncio.wait_for(run_with_disconnect(Browser(), connecting), timeout=0.5)
        assert cancelled == [True]
    asyncio.run(scenario())


@pytest.mark.parametrize("frame", [b"x", b"", b"x" * 6402], ids=["odd-pcm", "empty", "oversized"])
def test_relay_rejects_bad_pcm_and_cancels_reader(frame):
    from yu.voice.realtime import relay
    from yu.voice.provider import VoiceError

    async def scenario():
        closed = []
        class Browser:
            async def receive(self):
                return {"type": "websocket.receive", "bytes": frame}
            async def send_json(self, event):
                pass
        class Provider:
            async def send(self, packet):
                pass
            def __aiter__(self):
                return self.events()
            async def events(self):
                try:
                    yield json.dumps({"type": "session.updated"})
                    await asyncio.Future()
                finally:
                    closed.append(True)
        with pytest.raises(VoiceError, match="音频帧"):
            await relay(Browser(), Provider())
        assert closed == [True]
    asyncio.run(scenario())
