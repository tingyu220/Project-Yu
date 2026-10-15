"""Windows 应用目录：精确别名匹配，支持显式开启安装登记发现。"""

from __future__ import annotations

from dataclasses import dataclass, replace
import os
from pathlib import Path
import yaml
from .discovery import find_installed_executable


def _key(value: str) -> str:
    return value.strip().casefold()


@dataclass(frozen=True)
class AppEntry:
    app_id: str
    display_name: str
    aliases: tuple[str, ...]
    executable: str
    auto_discover: bool = False


class WindowsAppRegistry:
    """从 YAML 加载应用，匹配仅允许精确别名。"""

    def __init__(self, config_path: str | Path):
        self.config_path = Path(config_path)
        self._apps = self._load()

    def _load(self) -> list[AppEntry]:
        if not self.config_path.exists():
            return []
        data = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
        raw_apps = data.get("apps", {}) if isinstance(data, dict) else {}
        if not isinstance(raw_apps, dict):
            return []
        apps: list[AppEntry] = []
        for app_id, raw in raw_apps.items():
            if not isinstance(raw, dict):
                continue
            aliases = raw.get("aliases", [])
            if not isinstance(aliases, list):
                aliases = []
            apps.append(
                AppEntry(
                    app_id=str(app_id),
                    display_name=str(raw.get("display_name", app_id)),
                    aliases=tuple(str(alias) for alias in aliases),
                    executable=str(raw.get("executable", "")),
                    auto_discover=raw.get("auto_discover") is True,
                )
            )
        return apps

    def resolve(self, name: str) -> AppEntry | None:
        wanted = _key(name)
        for app in self._apps:
            candidates = (app.app_id, app.display_name, *app.aliases)
            if any(_key(candidate) == wanted for candidate in candidates):
                return self._resolve_executable(app)
        return None

    def list_apps(self) -> list[AppEntry]:
        return [self._resolve_executable(app) for app in self._apps]

    @staticmethod
    def _resolve_executable(app: AppEntry) -> AppEntry:
        configured = Path(os.path.expanduser(os.path.expandvars(app.executable)))
        if not app.auto_discover or (app.executable.strip() and configured.is_file()):
            return app
        # 每次失效时重新查询；应用升级后无需重启 Yu 或写回版本目录。
        discovered = find_installed_executable(app.app_id)
        return replace(app, executable=discovered) if discovered else app
