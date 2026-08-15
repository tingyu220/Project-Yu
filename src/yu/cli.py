"""Command-line interface for Yu (Phase 2: LLM Conversation + Memory).

Usage:
    python -m yu.cli

Commands:
    记住：<内容>   记录一条事实（同时创建 Event 与 Memory）
    记忆           列出所有有效记忆
    重置           清空当前对话
    exit           退出
    其他输入       作为对话发送给 LLM（多轮）
"""

from __future__ import annotations

import os

from . import __version__
from .llm import ChatMessage, Conversation, LLMError, create_provider
from .memory.store import MemoryStore

DEFAULT_DB_PATH = os.environ.get("YU_DB_PATH", "data/yu.db")
_PROMPT = "> "


def _print_banner() -> None:
    print(f"宇 Yu v{__version__}")


def main(argv: list[str] | None = None) -> int:
    del argv
    _print_banner()

    store = MemoryStore(DEFAULT_DB_PATH)
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
            if command == "exit":
                break
            if command == "记忆":
                _show_memories(store)
            elif command == "重置":
                conversation.clear()
                print("对话已重置。")
            elif command.startswith("记住："):
                _record(store, command[len("记住："):].strip())
            else:
                _chat(provider, conversation, command)
    finally:
        store.close()
    return 0


def _build_provider():
    try:
        return create_provider()
    except LLMError as e:
        print(f"[警告] {e}")
        print("未配置 LLM，本轮仅支持记忆命令（记住：/ 记忆 / 重置 / exit）。")
        return None


def _chat(provider, conversation: Conversation, text: str) -> None:
    if provider is None:
        print("未配置 LLM Provider（缺少 DEEPSEEK_API_KEY），无法对话。")
        return
    pending = conversation.as_messages() + [ChatMessage(role="user", content=text)]
    try:
        reply = provider.chat(pending)
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


if __name__ == "__main__":
    raise SystemExit(main())
