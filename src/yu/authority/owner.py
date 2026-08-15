"""Owner Identity — 独立数据模型，Single Owner。

Owner 拥有最高系统管理权限。Owner 身份不通过对话判断，只能通过
系统级配置 + 明确管理操作变更。加载失败时 Fail Closed（is_active() 为 False）。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


@dataclass(frozen=True)
class OwnerIdentity:
    owner_id: str
    display_name: str
    status: str
    created_at: str


class OwnerManager:
    def __init__(self, config_path: str | Path):
        self.config_path = Path(config_path)
        self._owner: Optional[OwnerIdentity] = None
        self._load_error: Optional[str] = None
        self._load()

    def _load(self) -> None:
        try:
            if not self.config_path.exists():
                raise FileNotFoundError(f"Owner 配置不存在: {self.config_path}")
            data = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("Owner 配置格式错误：顶层应为映射")
            self._owner = OwnerIdentity(
                owner_id=str(data["owner_id"]),
                display_name=str(data["display_name"]),
                status=str(data.get("status", "active")),
                created_at=str(data.get("created_at", "")),
            )
        except Exception as e:  # noqa: BLE001 — Fail Closed
            self._owner = None
            self._load_error = str(e)

    @property
    def owner(self) -> Optional[OwnerIdentity]:
        return self._owner

    @property
    def load_error(self) -> Optional[str]:
        return self._load_error

    def is_active(self) -> bool:
        return self._owner is not None and self._owner.status == "active"
