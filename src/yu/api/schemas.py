"""Yu API 的 Pydantic 请求/响应模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class HistoryMessage(BaseModel):
    """一条多轮对话历史消息（role: system / user / assistant）。"""

    role: str
    content: str


class ChatRequest(BaseModel):
    """POST /api/chat 请求体。"""

    message: str
    history: list[HistoryMessage] = Field(default_factory=list)


class MemoryQueryRequest(BaseModel):
    """POST /api/memories/query 请求体。"""

    query: str
    limit: int = Field(default=8, ge=1, le=50)
