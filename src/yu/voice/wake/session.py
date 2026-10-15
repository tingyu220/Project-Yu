"""一次唤醒后的实时会话；不自行重连，不重放旧音频和指令。"""
import asyncio
import json
from urllib.parse import urlsplit
import urllib.request
import uuid
from time import monotonic

from websockets.asyncio.client import connect

from .state import WakeState, is_stop_command


class VoiceSession:
    def __init__(self, base_url: str):
        parts = urlsplit(base_url)
        if (parts.scheme != "http" or parts.hostname not in {"127.0.0.1", "localhost"}
                or parts.port != 8792 or parts.username or parts.password
                or parts.path not in {"", "/"} or parts.query or parts.fragment):
            raise ValueError("语音客户端只允许本机 8792 服务")
        self.base_url = base_url.rstrip("/")
        self.session_id: str | None = None

    async def submit(self, text: str, history: list[dict[str, str]] | None = None) -> dict:
        if self.session_id is None:
            with urllib.request.urlopen(self.base_url + "/api/conversation", timeout=5) as response:
                self.session_id = json.loads(response.read())['session_id']
        request_id = "voice-" + uuid.uuid4().hex
        payload = json.dumps({"message": text, "session_id": self.session_id,
                              "request_id": request_id, "source": "local_voice"}, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(self.base_url + "/api/chat", data=payload,
                                         headers={"Content-Type": "application/json"}, method="POST")
        def send():
            # 明确禁用环境代理，避免本机指令流出到代理服务器。
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(request, timeout=45) as response:
                data = response.read(1024 * 1024 + 1)
            if len(data) > 1024 * 1024:
                raise RuntimeError("本机回复过大")
            result = json.loads(data)
            if not isinstance(result, dict) or not isinstance(result.get("reply"), str):
                raise RuntimeError("本机回复格式异常")
            return result
        return await asyncio.to_thread(send)

    async def run(self, capture, controller, feedback) -> None:
        if controller.state != WakeState.CONNECTING:
            return
        ready, done = asyncio.Event(), asyncio.Event()
        pending: asyncio.Queue[str] = asyncio.Queue(maxsize=3)
        tasks = []
        # 握手没有音频消费者；禁止积压录音，ready 提示完成后才恢复采集。
        capture.muted = True
        capture.discard()
        try:
            async with connect(self.base_url.replace("http://", "ws://", 1) + "/api/voice/live",
                               origin=self.base_url, proxy=None, open_timeout=12,
                               close_timeout=2, max_size=65536, max_queue=8) as socket:

                async def upload():
                    await asyncio.wait_for(ready.wait(), timeout=12)
                    while not done.is_set():
                        started = monotonic()
                        try:
                            audio = await asyncio.to_thread(capture.read, 0.1)
                        except TimeoutError:
                            audio = b"\0" * 3200
                        if capture.muted:
                            audio = b"\0" * 3200
                        await asyncio.wait_for(socket.send(audio), timeout=3)
                        # 真实采集本身每 100ms 产帧，静音/缺帧时仍限制上传速率。
                        await asyncio.sleep(max(0, 0.1 - (monotonic() - started)))

                async def receive():
                    while not done.is_set():
                        event = json.loads(await socket.recv())
                        if not isinstance(event, dict):
                            raise RuntimeError("语音事件格式异常")
                        kind = event.get("type")
                        if kind == "error":
                            raise RuntimeError(str(event.get("message", "识别失败")))
                        if kind == "ready":
                            if ready.is_set():
                                continue
                            capture.muted = True
                            controller.ready()
                            await asyncio.to_thread(feedback.cue)
                            capture.discard()
                            capture.muted = False
                            print("云端对话：请说指令；说‘结束’回到待唤醒。", flush=True)
                            ready.set()
                        elif kind == "speech":
                            controller.speech()
                        elif kind == "partial":
                            if not capture.muted:
                                print("识别中：" + str(event.get("text", "")), flush=True)
                        elif kind == "final":
                            if capture.muted and not is_stop_command(str(event.get("text", ""))):
                                continue
                            text = controller.final(event.get("id"), event.get("text"))
                            if controller.state in (WakeState.WAITING, WakeState.STOPPED):
                                done.set()
                                return
                            if text:
                                try:
                                    pending.put_nowait(text)
                                except asyncio.QueueFull:
                                    raise RuntimeError("指令队列已满，本次语音已结束") from None

                async def work():
                    while not done.is_set():
                        text = await pending.get()
                        if done.is_set() or controller.state in (WakeState.WAITING, WakeState.STOPPED):
                            return
                        controller.set_busy(True)
                        print("你：" + text, flush=True)
                        # 第二参数保留测试与旧扩展点兼容；真实实现不再使用客户端历史。
                        request = asyncio.create_task(self.submit(text, None))
                        try:
                            result = await asyncio.shield(request)
                        except asyncio.CancelledError:
                            # 已交给 API 的动作不重发；收取真实结果后才能退出。
                            try:
                                result = await request
                                print("宇：" + result["reply"], flush=True)
                            except Exception:
                                print("已提交的指令未收到回执，不会自动重发。", flush=True)
                            raise
                        except Exception:
                            print("指令请求失败，不会自动重发。", flush=True)
                            clear_pending()
                            controller.set_busy(False)
                            continue
                        print("宇：" + result["reply"], flush=True)
                        if (result.get("allowed") is False or result.get("kind") == "error"
                                or (result.get("action") or {}).get("success") is False
                                or (result.get("memory_result") or {}).get("success") is False):
                            clear_pending()
                        if controller.state != WakeState.WAITING:
                            capture.muted = True
                            capture.discard()
                            speaking = asyncio.create_task(asyncio.to_thread(feedback.speak, result["reply"]))
                            try:
                                try:
                                    await asyncio.shield(speaking)
                                except asyncio.CancelledError:
                                    # 首版不支持打断朗读；等待声卡输出结束后才能重新待唤醒。
                                    await speaking
                                    raise
                                await asyncio.sleep(controller.config.cooldown_seconds)
                            finally:
                                capture.discard()
                                capture.muted = False
                                controller.set_busy(False)

                def clear_pending():
                    while not pending.empty():
                        pending.get_nowait()

                async def timeout():
                    while not done.is_set():
                        if controller.state in (WakeState.WAITING, WakeState.STOPPED):
                            done.set()
                            return
                        if controller.expired():
                            done.set()
                            return
                        await asyncio.sleep(0.1)

                tasks = [asyncio.create_task(upload()), asyncio.create_task(receive()),
                         asyncio.create_task(work()), asyncio.create_task(timeout()),
                         asyncio.create_task(done.wait())]
                finished, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for task in finished:
                    task.result()
                # 先关闭音频连接，再等待可能已发生的动作回执。
                if hasattr(socket, "close"):
                    await socket.close()
        finally:
            done.set()
            controller.end()
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            capture.muted = False
            capture.discard()
