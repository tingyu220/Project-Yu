"""管理本次启动的 API 和监听进程，不附着不明服务、不关闭其他应用。"""
from pathlib import Path
import socket
import subprocess
import sys
import time
import os
import secrets
import urllib.request

from .config import WakeConfig
from .runtime import preflight
from .singleton import SingleInstance


def check_port():
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 8792)) == 0:
            raise RuntimeError("8792 已被占用；请先结束已启动的 Yu，不会重复启动或抢占服务")


def stop_native_helpers(parent):
    """仅清理该监听子进程拥有的两种明确脚本，不碰它打开的微信等应用。"""
    if not hasattr(parent, "pid"):
        return
    import psutil
    expected = {str(Path(__file__).with_name(name).resolve()).casefold()
                for name in ("native-wake.ps1", "native-speak.ps1")}
    try:
        children = psutil.Process(parent.pid).children()
    except psutil.Error:
        return
    for child in children:
        try:
            args = child.cmdline()
            if any(str(Path(arg).resolve()).casefold() in expected for arg in args):
                child.terminate()
                try:
                    child.wait(timeout=2)
                except psutil.TimeoutExpired:
                    child.kill()
        except (psutil.Error, OSError, ValueError):
            continue


class OwnedServices:
    def __init__(self):
        self.children = []

    def start(self, module: str):
        process = subprocess.Popen([sys.executable, "-u", "-m", module], shell=False,
                                   creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
        self.children.append(process)
        return process

    def close(self):
        for child in reversed(self.children):
            if child.poll() is None:
                stop_native_helpers(child)
                child.terminate()
                try:
                    child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=3)


def wait_api(process):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Yu API 启动失败")
        try:
            with opener.open("http://127.0.0.1:8792/api/status", timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            pass
        time.sleep(0.1)
    raise RuntimeError("等待本机 API 启动超时")


def run_launcher():
    with SingleInstance("Local\\YuVoiceLauncher"):
        check_port()
        preflight(WakeConfig.load(Path("config/voice_wake.yaml")))
        os.environ["YU_CONTROL_TOKEN"] = secrets.token_urlsafe(32)
        owned = OwnedServices()
        try:
            api = owned.start("yu.api")
            wait_api(api)
            listener = owned.start("yu.voice.wake")
            while True:
                if listener.poll() == 0:
                    print("语音监听正常结束，关闭本次 API 服务。", flush=True)
                    return
                if any(child.poll() is not None for child in owned.children):
                    raise RuntimeError("API 或监听进程退出，本次启动已停止")
                time.sleep(0.2)
        finally:
            owned.close()


if __name__ == "__main__":
    try:
        run_launcher()
    except KeyboardInterrupt:
        print("Yu 已停止，本次启动的监听和 API 已释放。", flush=True)
    except Exception as exc:
        print("启动未完成：" + str(exc), flush=True)
        raise SystemExit(1)
