"""根据本机配置和权限生成能力说明，避免模型猜测产品能力。"""
import os
import re
from pathlib import Path


def is_capability_question(text: str) -> bool:
    clean = re.sub(r"[\s，,。.!！?？、]", "", text).casefold()
    return bool(re.fullmatch(r"(?:你好)?(?:你是谁(?:你能做什么)?|你能做什么|你有什么功能|你有哪些能力)", clean))


def describe_capabilities(ctx) -> str:
    lines = ["我是宇，你的个人助手。可以帮你规划、整理目标和任务，记录并检索你明确保存的信息。"]
    if ctx.permissions.has_permission("process.start"):
        apps = [app.display_name for app in ctx.action_service.app_registry.list_apps()
                if app.executable.strip() and Path(os.path.expandvars(os.path.expanduser(app.executable))).is_file()]
        if apps:
            lines.append("当前已配置并授权打开：" + "、".join(apps) + "。")
    else:
        lines.append("本次启动尚未授权打开本机应用。")
    if ctx.permissions.has_permission("media.control"):
        lines.append("支持QQ音乐播放、暂停、上一首和下一首；执行结果以实际播放器状态为准。")
    lines.append("语音会话支持持续接收和自动发送，结束时可说“结束语音”或“OK，结束”。")
    lines.append("当前尚未接入实时天气查询，也不会把建议说成已执行的动作。")
    return "\n".join(lines)
