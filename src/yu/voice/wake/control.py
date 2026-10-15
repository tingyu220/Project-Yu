"""监听状态与本机控制命令的无网络状态容器。"""

from __future__ import annotations

from time import monotonic


class VoiceControlState:
    _priority = {"pause_speech": 1, "end_session": 2, "stop_service": 3}

    def __init__(self, clock=monotonic):
        self.clock = clock
        self.phase = "waiting"
        self.heartbeat = 0.0
        self._commands: list[str] = []

    def publish(self, phase: str, heartbeat: float | None = None) -> None:
        self.phase = phase
        self.heartbeat = self.clock() if heartbeat is None else heartbeat

    def snapshot(self, now: float | None = None) -> dict[str, object]:
        now = self.clock() if now is None else now
        phase = self.phase if now - self.heartbeat <= 5 else "unknown"
        return {"phase": phase, "heartbeat": self.heartbeat}

    def enqueue(self, command: str) -> None:
        if command not in self._priority:
            raise ValueError("未知语音控制命令")
        if command not in self._commands:
            self._commands.append(command)
            self._commands.sort(key=self._priority.get, reverse=True)

    def take(self) -> str | None:
        return self._commands.pop(0) if self._commands else None
