"""本机实时语音入口：同源校验、单会话、凭据隔离及资源回收。"""
import asyncio
from urllib.parse import urlsplit

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..voice.provider import QwenRecognizer, VoiceError
from ..voice.realtime import MAX_SESSION_SECONDS, MODEL, relay, run_with_disconnect


def live_router() -> APIRouter:
    router = APIRouter()
    lock = asyncio.Lock()

    @router.websocket("/live")
    async def live(socket: WebSocket):
        origin = socket.headers.get("origin", "")
        expected = ("https" if socket.url.scheme == "wss" else "http") + "://" + socket.headers.get("host", "")
        # 开发代理保留浏览器 Origin；仅允许明确的本机开发端口。
        allowed = {expected, "http://127.0.0.1:5173", "http://localhost:5173"}
        if origin not in allowed or urlsplit(origin).hostname not in {"localhost", "127.0.0.1", "::1"}:
            await socket.close(code=1008)
            return
        await socket.accept()
        if lock.locked():
            await socket.send_json({"type": "error", "message": "另一个页面正在使用语音，请先结束该会话。"})
            await socket.close(code=1008)
            return
        try:
            async with lock:
                config = QwenRecognizer()
                if not config.available:
                    raise VoiceError("语音服务未配置，请在本机配置对应地域的 DASHSCOPE_API_KEY。")
                from websockets.asyncio.client import connect
                from websockets.exceptions import InvalidStatus

                async def connect_session(stream):
                    async with connect(
                        f"wss://{config.host}/api-ws/v1/realtime?model={MODEL}",
                        additional_headers={"Authorization": f"Bearer {config.key}"},
                        open_timeout=12, close_timeout=2, max_size=65536, max_queue=8,
                        proxy=None,
                    ) as provider:
                        await asyncio.wait_for(relay(stream, provider), timeout=MAX_SESSION_SECONDS)

                try:
                    await run_with_disconnect(socket, connect_session)
                except InvalidStatus as exc:
                    status = exc.response.status_code
                    messages = {401: "语音 Key 无效或地域不匹配。", 403: "实时语音模型未开通或没有权限。",
                                429: "实时语音额度不足或服务繁忙。"}
                    raise VoiceError(messages.get(status, "实时语音连接失败，请稍后重新开启。")) from exc
        except WebSocketDisconnect:
            return
        except Exception as exc:
            message = str(exc) if isinstance(exc, VoiceError) else "实时语音已结束或连接中断，请重新开启；不会重发旧指令。"
            try:
                await socket.send_json({"type": "error", "message": message})
            except (WebSocketDisconnect, RuntimeError, OSError):
                pass
        finally:
            try:
                await socket.close()
            except (WebSocketDisconnect, RuntimeError, OSError):
                pass

    return router
