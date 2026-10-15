"""Windows 路径注册表：只使用用户显式绑定的路径。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml


def _key(value: str) -> str:
    return value.strip().casefold()


@dataclass(frozen=True)
class PathEntry:
    path_id: str
    display_name: str
    aliases: tuple[str, ...]
    path: str


class WindowsPathRegistry:
    def __init__(self, config_path: str | Path):
        self.config_path = Path(config_path)
        self._paths = self._load()

    def _load(self) -> list[PathEntry]:
        if not self.config_path.exists():
            return []
        data = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
        raw_paths = data.get("paths", {}) if isinstance(data, dict) else {}
        if not isinstance(raw_paths, dict):
            return []
        paths: list[PathEntry] = []
        for path_id, raw in raw_paths.items():
            if not isinstance(raw, dict):
                continue
            aliases = raw.get("aliases", [])
            if not isinstance(aliases, list):
                aliases = []
            configured_path = str(raw.get("path", ""))
            expanded_path = str(Path(os.path.expanduser(os.path.expandvars(configured_path)))) if configured_path.strip() else ""
            paths.append(
                PathEntry(
                    path_id=str(path_id),
                    display_name=str(raw.get("display_name", path_id)),
                    aliases=tuple(str(alias) for alias in aliases),
                    path=expanded_path,
                )
            )
        return paths

    def resolve(self, name: str) -> PathEntry | None:
        wanted = _key(name)
        for entry in self._paths:
            candidates = (entry.path_id, entry.display_name, *entry.aliases)
            if any(_key(candidate) == wanted for candidate in candidates):
                return entry
        return None

    def list_paths(self) -> list[PathEntry]:
        return list(self._paths)
