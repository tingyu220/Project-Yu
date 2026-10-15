"""Yu API 的 Pydantic 请求/响应模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Literal


class HistoryMessage(BaseModel):
    """一条多轮对话历史消息（role: system / user / assistant）。"""

    role: str
    content: str


class ChatRequest(BaseModel):
    """POST /api/chat 请求体。"""

    message: str = Field(min_length=1, max_length=4000)
    session_id: str | None = Field(default=None, max_length=128)
    request_id: str | None = Field(default=None, min_length=1, max_length=128)
    source: Literal["web", "local_voice"] = "web"
    history: list[HistoryMessage] = Field(default_factory=list)
    referenced_memory_ids: list[int] | None = None


class MemoryQueryRequest(BaseModel):
    """POST /api/memories/query 请求体。"""

    query: str
    limit: int = Field(default=8, ge=1, le=50)


class MemoryCreateRequest(BaseModel):
    """POST /api/memories 请求体。"""

    content: str
    type: str = "fact"
    importance: str = "high"


class MemoryUpdateRequest(BaseModel):
    """POST /api/memories/{id}/update 请求体。"""

    content: str
