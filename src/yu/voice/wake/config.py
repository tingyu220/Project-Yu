"""唤醒配置与固定音频协议校验。"""
from dataclasses import dataclass, fields
from pathlib import Path
import math

import yaml


@dataclass(frozen=True)
class WakeConfig:
    keyword: str = "嘿，宇"
    model_dir: str = "models/wake"
    device: int | str | None = None
    sample_rate: int = 16000
    channels: int = 1
    frame_ms: int = 100
    queue_frames: int = 20
    idle_seconds: float = 30
    max_session_seconds: float = 600
    cooldown_seconds: float = 1
    threshold: float = 0.25

    def __post_init__(self):
        if type(self.sample_rate) is not int or self.sample_rate != 16000:
            raise ValueError("采样率必须为 16000")
        if type(self.channels) is not int or self.channels != 1:
            raise ValueError("必须使用单声道")
        if type(self.frame_ms) is not int or self.frame_ms != 100:
            raise ValueError("音频帧必须为 100 毫秒")
        if type(self.queue_frames) is not int or not 1 <= self.queue_frames <= 20:
            raise ValueError("音频队列长度必须在 1 至 20 之间")
        for name in ("idle_seconds", "max_session_seconds", "cooldown_seconds", "threshold"):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} 必须为正有限数值")
        if self.max_session_seconds > 600 or self.threshold > 1:
            raise ValueError("会话时限不能超过 600 秒，阈值不能超过 1")
        if not isinstance(self.keyword, str) or not self.keyword.strip():
            raise ValueError("唤醒词不能为空")
        if not isinstance(self.model_dir, str) or not self.model_dir.strip():
            raise ValueError("模型目录不能为空")
        if self.device is not None and type(self.device) not in (int, str):
            raise ValueError("麦克风设备必须是编号或名称")

    @classmethod
    def load(cls, path: Path) -> "WakeConfig":
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("唤醒配置必须是映射")
        unknown = set(data) - {field.name for field in fields(cls)}
        if unknown:
            raise ValueError(f"未知配置项：{sorted(unknown, key=str)}")
        return cls(**data)
