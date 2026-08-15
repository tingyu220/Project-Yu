"""Provider 工厂：按名称选择 LLM Provider。"""

from __future__ import annotations

import os

from .base import LLMError, LLMProvider
from .deepseek import DeepSeekProvider

DEFAULT_PROVIDER = "deepseek"

_REGISTRY: dict[str, type[LLMProvider]] = {
    "deepseek": DeepSeekProvider,
}


def create_provider(name: str | None = None) -> LLMProvider:
    """按名称创建 Provider；默认取环境变量 YU_LLM_PROVIDER（缺省 deepseek）。"""
    provider_name = (name or os.environ.get("YU_LLM_PROVIDER", DEFAULT_PROVIDER)).lower()
    cls = _REGISTRY.get(provider_name)
    if cls is None:
        available = ", ".join(sorted(_REGISTRY))
        raise LLMError(f"未知的 LLM Provider: {provider_name}（可用: {available}）")
    return cls()
