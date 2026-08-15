"""Command-line interface for Yu (v0.0.3: Memory Retrieval).

Usage:
    python -m yu.cli

Commands:
    记住：<内容>   记录一条事实（同时创建 Event 与 Memory）
    记忆           列出所有有效记忆
    权限           查看当前 Permission
    安全状态       查看 Safety Kernel 状态
    审计           查看最近安全审计事件
    重置           清空当前对话
    exit           停止 Yu（受 Owner 停止权保护，不可被拒绝）
    其他输入       作为对话发送给 LLM（多轮）
"""

from __future__ import annotations

import os

from . import __version__
from .audit.store import AuditStore
from .authority.owner import OwnerManager
from .authority.shutdown import ShutdownController
from .llm import ChatMessage, Conversation, LLMError, create_provider
from .memory.retrieval import build_context
from .memory.store import MemoryStore
from .safety.constitution import SafetyConstitution
from .safety.kernel import SafetyKernel
from .safety.permissions import PermissionEngine
from .safety.risk import KNOWN_CAPABILITIES

DEFAULT_DB_PATH = os.environ.get("YU_DB_PATH", "data/yu.db")
DEFAULT_AUDIT_DB = os.environ.get("YU_AUDIT_DB", "data/audit.db")
DEFAULT_CONSTITUTION_PATH = os.environ.get("YU_CONSTITUTION_PATH", "config/safety_constitution.yaml")
DEFAULT_OWNER_PATH = os.environ.get("YU_OWNER_PATH", "config/owner.yaml")

_PROMPT = "> "

_SHUTDOWN_COMMANDS = {"exit", "quit", "shutdown", "关闭", "关闭yu", "关闭 yu"}


def _normalize_command(command: str) -> str:
    return command.strip().rstrip("。.!！？?").strip().lower()


def _print_banner() -> None:
    print(f"宇 Yu v{__version__}")


def main(argv: list[str] | None = None) -> int:
    del argv
    _print_banner()

    store = MemoryStore(DEFAULT_DB_PATH)
    audit = AuditStore(DEFAULT_AUDIT_DB)
    owner = OwnerManager(DEFAULT_OWNER_PATH)
    constitution = SafetyConstitution(DEFAULT_CONSTITUTION_PATH)
    owner_id = owner.owner.owner_id if owner.owner is not None else "unknown"
    permissions = PermissionEngine(owner_id, audit)
    kernel = SafetyKernel(constitution, permissions, owner, audit)
    shutdown = ShutdownController(audit)
    provider = _build_provider()
    conversation = Conversation()

    try:
        while True:
            try:
                line = input(_PROMPT)
            except EOFError:
                print()
                break
            command = line.strip()
            if not command:
                continue
            if _normalize_command(command) in _SHUTDOWN_COMMANDS:
                shutdown.request_shutdown("owner requested shutdown: " + command)
                break
            if command == "记忆":
                _show_memories(store)
            elif command == "重置":
                conversation.clear()
                print("对话已重置。")
            elif command == "权限":
                _show_permissions(permissions)
            elif command == "安全状态":
                _show_safety_status(kernel)
            elif command == "审计":
                _show_audit(audit)
            elif command.startswith("记住："):
                _record(store, command[len("记住："):].strip())
            else:
                _chat(store, provider, conversation, command)
    finally:
        store.close()
        audit.close()
    return 0


def _build_provider():
    try:
        return create_provider()
    except LLMError as e:
        print(f"[警告] {e}")
        print("未配置 LLM，本轮仅支持本地命令（记住：/ 记忆 / 权限 / 安全状态 / 审计 / 重置 / exit）。")
        return None


def _chat(store: MemoryStore, provider, conversation: Conversation, text: str) -> None:
    if provider is None:
        print("未配置 LLM Provider（缺少 DEEPSEEK_API_KEY），无法对话。")
        return
    context = build_context(store.retrieve(text, limit=5))
    base = conversation.as_messages()
    request = [base[0]]
    if context:
        request.append(ChatMessage(role="system", content=context))
    request.extend(base[1:])
    request.append(ChatMessage(role="user", content=text))
    try:
        reply = provider.chat(request)
    except LLMError as e:
        print(f"[错误] {e}")
        return
    conversation.add_user(text)
    conversation.add_assistant(reply.content)
    print(reply.content)


def _record(store: MemoryStore, content: str) -> None:
    if not content:
        print("内容为空，未记录。")
        return
    memory = store.remember(content)
    print("已记录。")
    print(f"Memory ID: {memory.id}")


def _show_memories(store: MemoryStore) -> None:
    memories = store.list_memories()
    if not memories:
        print("（暂无记忆）")
        return
    for m in memories:
        print(f"[{m.id}] {m.content}")


def _show_permissions(permissions: PermissionEngine) -> None:
    for cap in KNOWN_CAPABILITIES:
        status = "GRANTED" if permissions.has_permission(cap) else "DENIED"
        print(f"{cap:<20} {status}")


def _show_safety_status(kernel: SafetyKernel) -> None:
    s = kernel.status()
    print(f"Safety Kernel: {s['safety_kernel']}")
    print(f"Owner: {s['owner']}")
    print(f"Audit: {s['audit']}")
    print(f"Constitution: {s['constitution']}")


def _show_audit(audit: AuditStore, limit: int = 10) -> None:
    events = audit.list_recent(limit)
    if not events:
        print("（暂无审计记录）")
        return
    for e in events:
        risk = e.risk_level or "-"
        decision = e.decision or "-"
        print(f"[{e.id}] {e.timestamp} {e.event_type} actor={e.actor} risk={risk} decision={decision} reason={e.reason}")


if __name__ == "__main__":
    raise SystemExit(main())
