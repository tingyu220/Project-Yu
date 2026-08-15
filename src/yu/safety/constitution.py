"""Safety Constitution — 独立规则文件，属于 Control Plane。

当前版本由程序读取；LLM / Planner / Agent 不得直接修改。
加载失败时 Fail Closed：is_valid() 为 False，Safety Kernel 将拒绝一切动作。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


@dataclass(frozen=True)
class SafetyRule:
    id: str
    rule: str


class SafetyConstitution:
    def __init__(self, config_path: str | Path):
        self.config_path = Path(config_path)
        self._rules: list[SafetyRule] = []
        self._load_error: Optional[str] = None
        self._load()

    def _load(self) -> None:
        try:
            if not self.config_path.exists():
                raise FileNotFoundError(f"宪法文件不存在: {self.config_path}")
            data = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("宪法格式错误：顶层应为映射")
            principles = data.get("principles")
            if not isinstance(principles, list) or not principles:
                raise ValueError("宪法缺少有效的 principles 列表")
            rules: list[SafetyRule] = []
            for item in principles:
                if not isinstance(item, dict):
                    raise ValueError("principle 项格式错误")
                rules.append(SafetyRule(id=str(item["id"]), rule=str(item["rule"])))
            self._rules = rules
        except Exception as e:  # noqa: BLE001 — Fail Closed，捕获并记录
            self._rules = []
            self._load_error = str(e)

    @property
    def is_valid(self) -> bool:
        return self._load_error is None

    @property
    def load_error(self) -> Optional[str]:
        return self._load_error

    @property
    def rules(self) -> list[SafetyRule]:
        return list(self._rules)

    def rule_ids(self) -> list[str]:
        return [r.id for r in self._rules]
