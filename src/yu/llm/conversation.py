"""多轮对话状态。"""

from __future__ import annotations

from .base import ChatMessage

DEFAULT_SYSTEM_PROMPT = (
    "你是「宇」（Yu），一个长期个人决策助手，"
    "帮助用户规划生活、学习和工作。"
    "你拥有关于用户的长期记忆；当上下文提供了相关记忆时，"
    "请优先基于这些记忆回答，不要要求用户重复已经告知的信息。"
    "只使用明确提供的记忆，不要编造或推测记忆中没有的事实。"
    "回答简洁、诚实、有帮助。\n"
    "\n"
    "Memory Grounding 规则（必须遵守）：\n"
    "1. 永远不要声称用户「之前说过 / 做过 / 喜欢 / 经历过 / 决定过」某件事，"
    "除非该声称有 [VERIFIED USER MEMORY] 或当前对话中的明确证据支撑。\n"
    "2. 不要把 assistant 自己生成的建议、假设或推断，转述成用户的历史或事实。\n"
    "3. 没有可靠证据时，明确说明「没有可靠记忆」，而不是编造用户过去说过或做过的事。\n"
    "4. 普通建议使用「如果……」或「基于当前请求……」的措辞，避免主动做历史归因。"
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
