"""实时 ASR 协议适配：只输出识别事件，不执行命令，不保存音频。"""
from __future__ import annotations

import asyncio
import base64
import json
from time import monotonic
from uuid import uuid4

from .provider import VoiceError

MODEL = "qwen3-asr-flash-realtime"
MAX_SESSION_SECONDS = 600


def normalize_event(event: dict) -> dict | None:
    kind = event.get("type")
    if kind == "session.updated":
        return {"type": "ready"}
    if kind == "input_audio_buffer.speech_started":
        return {"type": "speech"}
    if kind in {"error", "conversation.item.input_audio_transcription.failed"}:
        return {"type": "error", "message": "实时识别失败，请核对模型权限、地域和额度后重新开启。"}
    if kind not in {"conversation.item.input_audio_transcription.text",
                    "conversation.item.input_audio_transcription.completed"}:
        return None
    final = kind.endswith(".completed")
    item_id = event.get("item_id")
    parts = [event.get("transcript", "")] if final else [event.get("text", ""), event.get("stash", "")]
    if not isinstance(item_id, str) or not item_id or len(item_id) > 256:
        raise VoiceError("实时识别结果缺少有效句子编号，请重新开启。")
    if not all(isinstance(part, str) for part in parts):
        raise VoiceError("实时识别返回格式异常，请重新开启。")
    text = "".join(parts).strip()
    if len(text) > 4000:
        raise VoiceError("单句过长，已结束语音，请缩短指令后重新开启。")
    return {"type": "final" if final else "partial", "id": item_id, "text": text}


def packet(kind: str, **fields) -> str:
    return json.dumps({"type": kind, "event_id": uuid4().hex, **fields})


async def run_with_disconnect(browser, connect_session) -> None:
    """握手开始即读取断连；有界缓冲将收包与供应商连接生命周期分开。"""
    inbound = asyncio.Queue(maxsize=8)

    class BufferedBrowser:
        async def receive(self):
            return await inbound.get()

        async def send_json(self, event):
            await browser.send_json(event)

    async def monitor():
        while True:
            message = await browser.receive()
            if message["type"] == "websocket.disconnect":
                return
            audio = message.get("bytes")
            if not isinstance(audio, bytes) or not 0 < len(audio) <= 6400 or len(audio) % 2:
                raise VoiceError("音频帧格式异常，语音已结束。")
            try:
                inbound.put_nowait(message)
            except asyncio.QueueFull as exc:
                raise VoiceError("音频转发拥堵，语音已结束。") from exc

    tasks = [asyncio.create_task(monitor()), asyncio.create_task(connect_session(BufferedBrowser()))]
    try:
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def relay(browser, provider) -> None:
    """任一方向结束即取消另一方向；取消时不补交未说完的句子。"""
    ready = asyncio.Event()
    seen: set[str] = set()
    await provider.send(packet("session.update", session={
        "input_audio_format": "pcm", "sample_rate": 16000,
        "input_audio_transcription": {"language": "zh"},
        "turn_detection": {"type": "server_vad", "threshold": 0.2, "silence_duration_ms": 800},
    }))

    async def upload():
        await asyncio.wait_for(ready.wait(), timeout=12)
        started, total = monotonic(), 0
        while True:
            message = await asyncio.wait_for(browser.receive(), timeout=15)
            if message["type"] == "websocket.disconnect":
                return
            audio = message.get("bytes")
            if not isinstance(audio, bytes) or not 0 < len(audio) <= 6400 or len(audio) % 2:
                raise VoiceError("音频帧格式异常，语音已结束。")
            total += len(audio)
            if total > (monotonic() - started) * 32000 + 64000:
                raise VoiceError("音频发送过快，语音已结束。")
            await provider.send(packet("input_audio_buffer.append", audio=base64.b64encode(audio).decode("ascii")))

    async def download():
        async for raw in provider:
            event = json.loads(raw)
            if not isinstance(event, dict):
                raise VoiceError("实时识别返回格式异常。")
            normalized = normalize_event(event)
            if normalized is None:
                continue
            if normalized["type"] == "ready":
                ready.set()
            if normalized["type"] == "final":
                if normalized["id"] in seen:
                    continue
                seen.add(normalized["id"])
                if len(seen) > 1000:
                    raise VoiceError("本次语音句数已达上限，请重新开启。")
            await browser.send_json(normalized)
            if normalized["type"] == "error":
                return

    tasks = [asyncio.create_task(upload()), asyncio.create_task(download())]
    try:
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
