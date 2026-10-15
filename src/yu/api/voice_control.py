"""本机语音控制路由；以同源与短期令牌保护写操作。"""

from __future__ import annotations

import os
import secrets
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Request

from ..voice.wake.control import VoiceControlState


def voice_control_router() -> APIRouter:
    router = APIRouter(prefix="/api/voice/control")
    state = VoiceControlState()
    token = os.environ.get("YU_CONTROL_TOKEN") or secrets.token_urlsafe(32)

    def validate(request: Request, write: bool = False):
        origin = request.headers.get("origin")
        expected = f"{request.url.scheme}://{request.headers.get('host', '')}"
        if request.url.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise HTTPException(403, "仅允许本机控制")
        if origin and origin != expected:
            raise HTTPException(403, "语音控制必须同源")
        if request.headers.get("sec-fetch-site") in {"cross-site", "same-site"}:
            raise HTTPException(403, "不允许跨站控制")
        if write and (origin != expected or not secrets.compare_digest(request.headers.get("x-yu-control-token", ""), token)):
            raise HTTPException(403, "控制令牌无效")

    @router.get("/token")
    async def get_token(request: Request):
        validate(request)
        return {"token": token}

    @router.get("/status")
    async def status(request: Request):
        validate(request)
        return state.snapshot()

    @router.post("/command")
    async def command(request: Request):
        validate(request, True)
        body = await request.json()
        try:
            state.enqueue(body.get("command", ""))
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return {"accepted": True}

    @router.post("/heartbeat")
    async def heartbeat(request: Request):
        validate(request, True)
        body = await request.json()
        state.publish(body.get("phase", "unknown"))
        return {"command": state.take()}

    return router
