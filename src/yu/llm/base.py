"""LLM Provider 抽象层。

Yu 的业务层只依赖这个统一接口；具体模型（DeepSeek / OpenAI / ...）通过实现本接口接入。

原则：模型可以替换，Yu 不随模型一起更换。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class LLMError(Exception):
    """LLM 调用相关的错误基类。"""


@dataclass(frozen=True)
class ChatMessage:
    """一条对话消息。role 取值：system / user / assistant。"""

    role: str
    content: str


@dataclass
class LLMResponse:
    """一次 LLM 调用的结果。"""

    content: str
    model: str = ""
    finish_reason: str = ""


class LLMProvider(ABC):
    """统一的 LLM 调用接口。所有 Provider 必须实现 chat()。"""

    name: str = "base"

    @abstractmethod
    def chat(self, messages: list[ChatMessage]) -> LLMResponse:
        """根据当前对话消息列表，返回助手的回复。"""
        raise NotImplementedError
