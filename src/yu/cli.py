"""Command-line interface for the Yu Memory Kernel (Phase 1).

Usage:
    python -m yu.cli

Commands:
    记住：<内容>   记录一条事实（同时创建 Event 与 Memory）
    记忆           列出所有有效记忆
    exit           退出
"""

from __future__ import annotations

import os

from . import __version__
from .memory.store import MemoryStore

DEFAULT_DB_PATH = os.environ.get("YU_DB_PATH", "data/yu.db")
_PROMPT = "> "


def _print_banner() -> None:
    print(f"宇 Yu v{__version__}")


def main(argv: list[str] | None = None) -> int:
    del argv  # Phase 1 CLI 没有命令行参数。
    _print_banner()

    store = MemoryStore(DEFAULT_DB_PATH)
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
            elif command.startswith("记住："):
                _record(store, command[len("记住："):].strip())
            else:
                print("未识别的命令。支持：记住：xxx / 记忆 / exit")
    finally:
        store.close()
    return 0


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
