"""Windows 固定语法唤醒；音频仅通过本机管道，不写盘、不上传。"""
import json
import math
from pathlib import Path
from queue import Empty, Queue
import re
import shutil
import subprocess
from threading import Thread, Event

from .config import WakeConfig


def powershell() -> str:
    executable = shutil.which("pwsh.exe")
    if not executable:
        raise RuntimeError("未找到 PowerShell 7，请先安装或加入 PATH")
    return executable


def keyword_text(text: str) -> str:
    return re.sub(r"[\s，,。.!！?？、]", "", text)


class KeywordDetector:
    def __init__(self, config: WakeConfig):
        self.config = config
        self._process = None
        self._events: Queue[dict] = Queue(16)
        self._hit = False
        self._thread = None
        self._error = None
        self._write_timeout = 1.0
        self._writer = None

    def _reader(self):
        try:
            for line in self._process.stdout:
                event = json.loads(line.decode("utf-8-sig"))
                if not isinstance(event, dict):
                    raise ValueError("格式错误")
                self._events.put_nowait(event)
        except Exception:
            self._error = "本地唤醒结果异常或队列溢出"

    def __enter__(self):
        self._process = subprocess.Popen([
            powershell(), "-NoLogo", "-NoProfile", "-File",
            str(Path(__file__).with_name("native-wake.ps1")),
            "-Keyword", keyword_text(self.config.keyword),
        ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            bufsize=0, shell=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self._thread = Thread(target=self._reader, daemon=True)
        self._thread.start()
        try:
            event = self._events.get(timeout=15)
            if event.get("type") != "ready":
                raise RuntimeError("Windows 本地唤醒引擎无法启动")
        except BaseException:
            self.__exit__()
            raise
        return self

    def handle_event(self, event: dict) -> bool:
        confidence = event.get("confidence")
        if (self._hit or event.get("type") != "wake"
                or event.get("text") != keyword_text(self.config.keyword)
                or type(confidence) not in (int, float) or not math.isfinite(confidence)
                or not self.config.threshold <= confidence <= 1):
            return False
        self._hit = True
        return True

    def accept(self, pcm: bytes) -> bool:
        if not isinstance(pcm, bytes) or len(pcm) != 3200:
            raise ValueError("唤醒音频必须是 100 毫秒单声道 PCM16")
        if self._error:
            raise RuntimeError(self._error)
        if self._process is None or self._process.poll() is not None:
            raise RuntimeError("本地唤醒引擎已退出")
        completed = Event()
        process = self._process
        def write():
            try:
                view = memoryview(pcm)
                while view:
                    count = process.stdin.write(view)
                    if not count:
                        raise OSError("音频管道已关闭")
                    view = view[count:]
                process.stdin.flush()
            except Exception:
                self._error = "本地音频管道写入失败"
            finally:
                completed.set()
        self._writer = Thread(target=write, daemon=True)
        self._writer.start()
        if not completed.wait(self._write_timeout):
            self._error = "本地音频管道阻塞，停止监听"
            raise RuntimeError(self._error)
        if self._error:
            raise RuntimeError(self._error)
        while True:
            try:
                event = self._events.get_nowait()
            except Empty:
                return False
            if event.get("type") == "error":
                raise RuntimeError("Windows 本地识别失败：" + str(event.get("message", "未知原因")))
            if self.handle_event(event):
                return True

    def reset(self):
        self._hit = False
        while True:
            try:
                self._events.get_nowait()
            except Empty:
                break

    def __exit__(self, *_):
        if self._process is not None:
            if self._process.poll() is None:
                self._process.terminate()
            try:
                self._process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=3)
            for stream in (self._process.stdin, self._process.stdout):
                if stream:
                    stream.close()
            if self._thread:
                self._thread.join(timeout=1)
            if self._writer:
                self._writer.join(timeout=1)
            self._process = None


def check_native() -> None:
    result = subprocess.run([
        powershell(), "-NoLogo", "-NoProfile", "-File",
        str(Path(__file__).with_name("native-wake.ps1")), "-CheckOnly",
    ], capture_output=True, timeout=20, shell=False)
    if result.returncode or b'"ready"' not in result.stdout:
        raise RuntimeError("Windows 中文本地唤醒引擎不可用")
