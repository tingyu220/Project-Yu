"""免网页、免按钮的唤醒循环；一个采集流贯穿本地检测和云端对话。"""
import asyncio
import json
import os
import urllib.request
from pathlib import Path
from time import monotonic

from .capture import AudioCapture, CaptureError
from .config import WakeConfig
from .detector import KeywordDetector, check_native
from .feedback import Feedback
from .session import VoiceSession
from .singleton import SingleInstance
from .state import WakeController, WakeState


async def control_heartbeat(base_url, controller, feedback):
    """周期发布监听状态，控制命令不进入普通聊天队列。"""
    token = os.environ.get("YU_CONTROL_TOKEN")
    if not token:
        return
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    while controller.state != WakeState.STOPPED:
        def exchange():
            phase = "speaking" if getattr(feedback, "speaking", False) else controller.state.value
            request = urllib.request.Request(base_url + "/api/voice/control/heartbeat",
                data=json.dumps({"phase": phase}).encode(), method="POST",
                headers={"Content-Type": "application/json", "Origin": base_url, "X-Yu-Control-Token": token})
            with opener.open(request, timeout=2) as response:
                return json.loads(response.read()).get("command")
        try:
            command = await asyncio.to_thread(exchange)
            if command == "stop_service":
                feedback.stop()
                controller.stop()
            elif command == "end_session":
                feedback.stop()
                controller.end()
            elif command == "pause_speech":
                feedback.stop()
        except OSError:
            pass
        await asyncio.sleep(1)


def preflight(config: WakeConfig):
    check_native()
    import sounddevice as sd
    sd.check_input_settings(device=config.device, channels=1, dtype="int16", samplerate=16000)


async def open_detector(detector):
    """取消初始化时仍收回已启动的子进程，避免丢失其所有权。"""
    starting = asyncio.create_task(asyncio.to_thread(detector.__enter__))
    try:
        return await asyncio.shield(starting)
    except asyncio.CancelledError:
        try:
            await starting
        finally:
            await asyncio.to_thread(detector.__exit__)
        raise


async def run_wake(config_path: Path, base_url: str, listen_seconds: float | None = None):
    config = WakeConfig.load(config_path)
    preflight(config)
    controller, session, feedback = WakeController(config), VoiceSession(base_url), Feedback()
    deadline = monotonic() + listen_seconds if listen_seconds else float("inf")
    detector = None
    heartbeat_task = asyncio.create_task(control_heartbeat(base_url, controller, feedback))
    with SingleInstance("Local\\YuWakeListener"):
        # 启动识别引擎时不采集，避免加载耗时造成输入队列溢出。
        detector = await open_detector(KeywordDetector(config))
        try:
            with AudioCapture(config) as capture:
                print(f"本地待唤醒：说‘{config.keyword}’；麦克风已开启，音频不上传。Ctrl+C 退出。", flush=True)
                while monotonic() < deadline and controller.state != WakeState.STOPPED:
                    try:
                        pcm = await asyncio.to_thread(capture.read, 0.2)
                    except TimeoutError:
                        continue
                    if not await asyncio.to_thread(detector.accept, pcm):
                        continue
                    if not controller.wake():
                        continue
                    await asyncio.to_thread(detector.__exit__)
                    detector = None
                    capture.discard()
                    try:
                        print("已唤醒，正在连接识别；听到提示音后说指令。", flush=True)
                        await session.run(capture, controller, feedback)
                    except CaptureError:
                        raise
                    except Exception as exc:
                        print("本次语音结束：" + str(exc), flush=True)
                    if controller.state == WakeState.STOPPED:
                        print("已按指令停止语音服务，释放麦克风。", flush=True)
                        return
                    # 新建本地引擎清除旧识别状态；重建期间不缓存音频。
                    capture.muted = True
                    try:
                        detector = await open_detector(KeywordDetector(config))
                        await asyncio.sleep(config.cooldown_seconds)
                        capture.discard()
                    finally:
                        capture.muted = False
                    print("已回到本地待唤醒。", flush=True)
        finally:
            controller.stop()
            heartbeat_task.cancel()
            await asyncio.gather(heartbeat_task, return_exceptions=True)
            if detector:
                await asyncio.to_thread(detector.__exit__)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Yu Windows 免点击语音唤醒")
    parser.add_argument("--config", type=Path, default=Path("config/voice_wake.yaml"))
    parser.add_argument("--base-url", default="http://127.0.0.1:8792")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--listen-seconds", type=float, help="限时本地验证，结束后释放录音")
    args = parser.parse_args()
    try:
        if args.check:
            preflight(WakeConfig.load(args.config))
            print("预检通过：中文本地引擎和 16kHz 麦克风可用，未开始录音。")
        else:
            if args.listen_seconds is not None and not 0 < args.listen_seconds <= 600:
                raise ValueError("限时验证必须在 0 至 600 秒之间")
            asyncio.run(run_wake(args.config, args.base_url, args.listen_seconds))
    except KeyboardInterrupt:
        print("监听已结束，麦克风和连接已释放。")
    except Exception as exc:
        print("唤醒服务未完成：" + str(exc), flush=True)
        raise SystemExit(1)
