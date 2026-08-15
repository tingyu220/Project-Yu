"""多轮对话状态。"""

from __future__ import annotations

from .base import ChatMessage

DEFAULT_SYSTEM_PROMPT = (
    "你是「宇」（Yu），一个长期个人决策助手，"
    "帮助用户规划生活、学习和工作。回答简洁、诚实、有帮助。"
)


class Conversation:
    """维护一轮对话的消息历史（含 system 提示）。"""

    def __init__(self, system_prompt: str = DEFAULT_SYSTEM_PROMPT):
        self._messages: list[ChatMessage] = []
        if system_prompt:
            self._messages.append(ChatMessage(role="system", content=system_prompt))

    def add_user(self, content: str) -> None:
        self._messages.append(ChatMessage(role="user", content=content))

    def add_assistant(self, content: str) -> None:
        self._messages.append(ChatMessage(role="assistant", content=content))

    def clear(self) -> None:
        """清空对话，但保留 system 提示。"""
        self._messages = [m for m in self._messages if m.role == "system"]

    def as_messages(self) -> list[ChatMessage]:
        return list(self._messages)

    def __len__(self) -> int:
        return len(self._messages)
