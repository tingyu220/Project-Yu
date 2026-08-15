"""Computer Context — 读取电脑状态（Phase 7）。

当前只允许读取（Read）、分析（Analyze）、建议（Recommend）；禁止任何操作：
删除文件、清理注册表、关闭软件、修改系统配置、安装/卸载软件、修改启动项、操作鼠标键盘。

所有读取动作应经 Safety Kernel 授权（capability: system.status.read）。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Optional

import psutil

from .llm import ChatMessage, LLMProvider


@dataclass
class ComputerStatus:
    cpu_percent: float
    ram_percent: float
    ram_total_gb: float
    ram_used_gb: float
    disk_percent: float
    disk_free_gb: float
    disk_total_gb: float
    battery_percent: Optional[float]
    uptime_hours: float
    top_processes: list[dict[str, Any]]


COMPUTER_ADVICE_SYSTEM_PROMPT = (
    "你是 Yu 的电脑状态分析器。根据提供的电脑状态数据，判断电脑是否卡顿、可能的原因，并给出建议。\n"
    "注意：Yu 当前只读，禁止任何操作。你只能读取、分析、建议，\n"
    "不要提出删除文件、关闭软件、修改系统配置等操作；建议应指向让用户自行处理。"
)


def read_computer_status() -> ComputerStatus:
    vm = psutil.virtual_memory()
    du = psutil.disk_usage("/")
    battery = psutil.sensors_battery()

    procs: list[dict[str, Any]] = []
    for p in psutil.process_iter(["name", "memory_info"]):
        try:
            info = p.info
            name = info["name"] or ""
            rss = info["memory_info"].rss if info["memory_info"] else 0
            procs.append({"name": name, "rss": rss})
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    procs.sort(key=lambda x: x["rss"], reverse=True)
    top = [
        {"name": p["name"], "memory_mb": round(p["rss"] / 1024 / 1024, 1)}
        for p in procs[:5]
    ]

    uptime = (datetime.now() - datetime.fromtimestamp(psutil.boot_time())).total_seconds() / 3600

    return ComputerStatus(
        cpu_percent=psutil.cpu_percent(interval=0.1),
        ram_percent=vm.percent,
        ram_total_gb=round(vm.total / 1024**3, 1),
        ram_used_gb=round(vm.used / 1024**3, 1),
        disk_percent=du.percent,
        disk_free_gb=round(du.free / 1024**3, 1),
        disk_total_gb=round(du.total / 1024**3, 1),
        battery_percent=battery.percent if battery else None,
        uptime_hours=round(uptime, 1),
        top_processes=top,
    )


def format_status(s: ComputerStatus) -> str:
    lines = [
        f"CPU 使用率：{s.cpu_percent}%",
        f"内存使用率：{s.ram_percent}%（{s.ram_used_gb}GB / {s.ram_total_gb}GB）",
        f"磁盘使用率：{s.disk_percent}%（剩余 {s.disk_free_gb}GB / 共 {s.disk_total_gb}GB）",
    ]
    if s.battery_percent is not None:
        lines.append(f"电池：{s.battery_percent}%")
    lines.append(f"系统已运行：{s.uptime_hours} 小时")
    if s.top_processes:
        lines.append("内存占用最高的进程：")
        for p in s.top_processes:
            lines.append(f"- {p['name']}（{p['memory_mb']} MB）")
    return "\n".join(lines)


def is_computer_request(text: str) -> bool:
    if "电脑" not in text and "系统" not in text:
        return False
    low = text.lower()
    return any(k in text or k in low for k in ("状态", "卡", "内存", "磁盘", "cpu", "为什么", "运行"))


def build_computer_advice(provider: LLMProvider, s: ComputerStatus) -> str:
    data = format_status(s)
    messages = [
        ChatMessage(role="system", content=COMPUTER_ADVICE_SYSTEM_PROMPT),
        ChatMessage(role="user", content=f"当前电脑状态：\n{data}\n\n请分析并给出建议。"),
    ]
    return provider.chat(messages).content
