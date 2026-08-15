"""DeepSeek Provider：通过 OpenAI 兼容的 chat/completions 接口调用。

使用标准库 urllib 完成 HTTP 请求，不引入额外 HTTP 依赖。
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .base import ChatMessage, LLMError, LLMProvider, LLMResponse

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_TEMPERATURE = 0.3


class DeepSeekProvider(LLMProvider):
    name = "deepseek"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 60.0,
        temperature: float | None = None,
    ):
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        self.base_url = (base_url or os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL)).rstrip("/")
        self.model = model or os.environ.get("DEEPSEEK_MODEL", DEFAULT_MODEL)
        self.timeout = timeout
        self.temperature = temperature if temperature is not None else float(
            os.environ.get("DEEPSEEK_TEMPERATURE", str(DEFAULT_TEMPERATURE))
        )
        if not self.api_key:
            raise LLMError("缺少 API Key：请设置环境变量 DEEPSEEK_API_KEY")

    def chat(self, messages: list[ChatMessage]) -> LLMResponse:
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "temperature": self.temperature,
        }
        data = json.dumps(payload).encode("utf-8")
        url = f"{self.base_url}/chat/completions"
        request = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            try:
                detail = e.read().decode("utf-8", errors="replace")
            except Exception:
                detail = ""
            raise LLMError(f"DeepSeek API HTTP {e.code}: {detail}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            raise LLMError(f"无法连接 DeepSeek API: {e}") from e

        try:
            result = json.loads(body)
        except json.JSONDecodeError as e:
            raise LLMError(f"DeepSeek API 返回非 JSON 响应: {body[:200]}") from e

        try:
            choices = result["choices"]
            content = choices[0]["message"]["content"]
            finish_reason = choices[0].get("finish_reason", "")
        except (KeyError, IndexError, TypeError) as e:
            raise LLMError(f"DeepSeek API 响应结构异常: {body[:400]}") from e

        return LLMResponse(
            content=content,
            model=result.get("model", self.model),
            finish_reason=finish_reason,
        )
