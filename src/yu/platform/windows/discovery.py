"""从 Windows 安装登记定位指定应用；不遍历磁盘或执行注册表命令。"""
from __future__ import annotations

import os
import re
from pathlib import Path

# 发现范围独立于聊天内容，只允许已支持的应用身份与启动文件。
RULES = {
    "qq_music": ({"qq音乐", "qqmusic", "qq music"}, ("QQMusic.exe",)),
    "weixin": ({"微信", "weixin", "wechat"}, ("Weixin.exe", "WeChat.exe")),
}


def installation_records(executables: tuple[str, ...]) -> list[dict[str, str]]:
    try:
        import winreg
    except ImportError:
        return []
    records = []

    def read(key, name):
        try:
            value = winreg.QueryValueEx(key, name)[0]
            return value if isinstance(value, str) else ""
        except OSError:
            return ""

    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
            for executable in executables:
                try:
                    with winreg.OpenKey(hive, rf"Software\Microsoft\Windows\CurrentVersion\App Paths\{executable}", 0, winreg.KEY_READ | view) as key:
                        records.append({"Executable": read(key, "")})
                except OSError:
                    pass
            try:
                with winreg.OpenKey(hive, r"Software\Microsoft\Windows\CurrentVersion\Uninstall", 0, winreg.KEY_READ | view) as root:
                    for index in range(winreg.QueryInfoKey(root)[0]):
                        try:
                            with winreg.OpenKey(root, winreg.EnumKey(root, index)) as key:
                                records.append({name: read(key, name) for name in ("DisplayName", "DisplayIcon", "InstallLocation")})
                        except OSError:
                            continue
            except OSError:
                pass
    return records


def find_installed_executable(app_id: str) -> str | None:
    rule = RULES.get(app_id)
    if rule is None:
        return None
    names, filenames = rule
    matches: dict[str, str] = {}
    for record in installation_records(filenames):
        candidates = []
        if "Executable" in record:
            candidates.append(record["Executable"])
        elif record.get("DisplayName", "").strip().casefold() in names:
            icon = record.get("DisplayIcon", "").strip()
            parsed = re.fullmatch(r'"?(.+?\.exe)"?(?:,\s*-?\d+)?', icon, re.IGNORECASE)
            if parsed:
                candidates.append(parsed[1])
            location = record.get("InstallLocation", "").strip().strip('"')
            if location:
                candidates.extend(str(Path(location) / filename) for filename in filenames)
        for candidate in candidates:
            path = Path(os.path.expandvars(candidate.strip().strip('"')))
            if path.is_absolute() and path.name.casefold() in {name.casefold() for name in filenames} and path.is_file():
                resolved = str(path.resolve())
                matches[resolved.casefold()] = resolved
    # 多份有效安装不猜测默认版本；交由用户指定路径。
    return next(iter(matches.values())) if len(matches) == 1 else None
