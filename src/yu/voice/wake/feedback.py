"""本机提示音和中文朗读，文本只通过 stdin 传递。"""
from pathlib import Path
import subprocess
import threading

from .detector import powershell


class Feedback:
    def __init__(self):
        self._process = None
        self._lock = threading.Lock()
        self.speaking = False

    def stop(self):
        """只终止本实例持有的朗读进程，不影响其他应用。"""
        with self._lock:
            process = self._process
            if process and process.poll() is None:
                process.terminate()

    def cue(self):
        import winsound
        winsound.Beep(880, 150)

    def speak(self, text: str):
        try:
            process = subprocess.Popen([
                powershell(), "-NoLogo", "-NoProfile", "-File",
                str(Path(__file__).with_name("native-speak.ps1")),
            ], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, shell=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            with self._lock:
                self._process = process
                self.speaking = True
            process.communicate(input=text[:600].encode("utf-8"), timeout=60)
            if process.returncode:
                print("本地朗读不可用，请查看文字回复（未切换云端朗读）。", flush=True)
        except (OSError, RuntimeError, subprocess.TimeoutExpired):
            self.stop()
            print("本地朗读失败，请查看文字回复。", flush=True)
        finally:
            with self._lock:
                self._process = None
                self.speaking = False
