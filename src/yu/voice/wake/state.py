"""纯状态控制，不接触麦克风、网络和动作执行。"""
from enum import Enum
import re
from time import monotonic

from .config import WakeConfig


class WakeState(str, Enum):
    WAITING = "waiting"
    CONNECTING = "connecting"
    LISTENING = "listening"
    BUSY = "busy"
    STOPPED = "stopped"


def is_stop_command(text: str) -> bool:
    clean = re.sub(r"[\s，,。.!！?？、]", "", text.lower())
    return (is_service_stop_command(text)
            or re.fullmatch(r"(?:ok|okay|好的|好)?(?:结束|结束语音|停止监听|退出语音)", clean) is not None)


def is_service_stop_command(text: str) -> bool:
    """整句命令才关闭服务，讨论停止方式不触发操作。"""
    clean = re.sub(r"[\s，,。.!！?？、]", "", text.lower())
    return re.fullmatch(r"(?:宇)?(?:请|帮我)?(?:停止本次服务|关闭语音服务|停止语音服务|关闭本次服务)", clean) is not None


class WakeController:
    def __init__(self, config: WakeConfig, clock=monotonic):
        self.config, self.clock = config, clock
        self.state = WakeState.WAITING
        self._cooldown_until = clock()
        self._started = self._last_speech = clock()
        self._seen: set[str] = set()

    def wake(self) -> bool:
        if self.state != WakeState.WAITING or self.clock() < self._cooldown_until:
            return False
        self._started = self._last_speech = self.clock()
        self._seen.clear()
        self.state = WakeState.CONNECTING
        return True

    def ready(self):
        if self.state == WakeState.CONNECTING:
            self.state = WakeState.LISTENING
            self._last_speech = self.clock()

    def speech(self):
        if self.state in (WakeState.LISTENING, WakeState.BUSY):
            self._last_speech = self.clock()

    def set_busy(self, value: bool):
        if value and self.state == WakeState.LISTENING:
            self.state = WakeState.BUSY
        elif not value and self.state == WakeState.BUSY:
            self.state = WakeState.LISTENING
            self._last_speech = self.clock()

    def final(self, item_id: str, text: str) -> str | None:
        if self.state not in (WakeState.LISTENING, WakeState.BUSY):
            return None
        if not isinstance(item_id, str) or not item_id or len(item_id) > 256:
            raise ValueError("识别句子编号无效")
        if not isinstance(text, str) or len(text) > 4000:
            raise ValueError("识别文本格式异常")
        if item_id in self._seen:
            return None
        if len(self._seen) >= 1000:
            raise ValueError("单次识别句数超过上限")
        self._seen.add(item_id)
        text = text.strip()
        if is_service_stop_command(text):
            self.stop()
            return None
        if is_stop_command(text):
            self.end()
            return None
        self.speech()
        return text or None

    def expired(self) -> bool:
        if self.state in (WakeState.WAITING, WakeState.STOPPED):
            return False
        return (self.clock() - self._started >= self.config.max_session_seconds
                or (self.state == WakeState.LISTENING
                    and self.clock() - self._last_speech >= self.config.idle_seconds))

    def end(self):
        if self.state == WakeState.STOPPED:
            return
        self.state = WakeState.WAITING
        self._seen.clear()
        self._cooldown_until = self.clock() + self.config.cooldown_seconds

    def stop(self):
        self.state = WakeState.STOPPED
        self._seen.clear()
