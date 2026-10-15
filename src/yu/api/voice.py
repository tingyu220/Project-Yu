"""语音接口：不落盘，不执行转写内容，不自动跨地域重试。"""
import asyncio

from fastapi import APIRouter, HTTPException, Request

from ..voice.provider import MAX_AUDIO_BYTES, QwenRecognizer, VoiceError, validate_wav
from ..voice.realtime import MODEL, MAX_SESSION_SECONDS
from .voice_live import live_router


def voice_router() -> APIRouter:
    router = APIRouter(prefix="/api/voice")
    router.include_router(live_router())
    lock = asyncio.Lock()

    @router.get("/status")
    async def status():
        provider = QwenRecognizer()
        return {"available": provider.available, "region": provider.region,
                "model": MODEL, "max_seconds": 30, "max_session_seconds": MAX_SESSION_SECONDS,
                "message": "开启后持续向阿里云发送语音并自动执行；单次最长 10 分钟，可随时结束。" if provider.available else "语音未配置：请设置北京地域 DASHSCOPE_API_KEY。"}

    @router.post("/transcribe")
    async def transcribe(request: Request):
        if request.headers.get("content-type", "").split(";")[0] != "audio/wav":
            raise HTTPException(415, "仅支持 WAV 录音。")
        if lock.locked():
            raise HTTPException(429, "正在识别上一段录音，请稍后重试。")
        async with lock:
            data = bytearray()
            async for chunk in request.stream():
                data.extend(chunk)
                if len(data) > MAX_AUDIO_BYTES:
                    raise HTTPException(413, "录音过大，请缩短录音。")
            try:
                validate_wav(bytes(data))
                text = await asyncio.to_thread(QwenRecognizer().transcribe, bytes(data))
            except VoiceError as exc:
                raise HTTPException(422, str(exc)) from exc
        return {"text": text}

    return router
