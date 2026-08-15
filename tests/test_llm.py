"""Tests for the Yu LLM layer (Phase 2)."""

import io
import json
import urllib.error
import urllib.request

import pytest

from yu.llm import ChatMessage, Conversation, LLMError, LLMResponse, create_provider
from yu.llm.base import LLMProvider
from yu.llm.deepseek import DeepSeekProvider


# ---------------------------------------------------------------- models

def test_chat_message_model():
    m = ChatMessage(role="user", content="你好")
    assert m.role == "user"
    assert m.content == "你好"


def test_llm_response_defaults():
    r = LLMResponse(content="hi")
    assert r.content == "hi"
    assert r.model == ""
    assert r.finish_reason == ""


def test_llm_provider_is_abstract():
    with pytest.raises(TypeError):
        LLMProvider()


# ---------------------------------------------------------------- deepseek

def _make_response(body: bytes):
    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return body

    return FakeResp()


def _patch_urlopen(monkeypatch, body=b"", exc=None):
    captured = {}

    def fake_urlopen(request, timeout=None):
        captured["request"] = request
        captured["timeout"] = timeout
        if exc is not None:
            raise exc
        return _make_response(body)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return captured


def test_deepseek_requires_api_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(LLMError):
        DeepSeekProvider()


def test_deepseek_builds_request_and_parses_response(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-chat")
    body = json.dumps(
        {
            "choices": [
                {"message": {"role": "assistant", "content": "你好！"}, "finish_reason": "stop"}
            ],
            "model": "deepseek-chat",
        }
    ).encode("utf-8")
    captured = _patch_urlopen(monkeypatch, body=body)

    p = DeepSeekProvider()
    reply = p.chat([ChatMessage("system", "你是 Yu"), ChatMessage("user", "hi")])

    assert reply.content == "你好！"
    assert reply.model == "deepseek-chat"
    assert reply.finish_reason == "stop"

    req = captured["request"]
    assert req.full_url == "https://api.deepseek.com/chat/completions"
    headers = {k.lower(): v for k, v in req.headers.items()}
    assert headers["authorization"] == "Bearer sk-test"
    assert headers["content-type"] == "application/json"
    payload = json.loads(req.data.decode("utf-8"))
    assert payload["model"] == "deepseek-chat"
    assert payload["stream"] is False
    assert payload["temperature"] == 0.3
    assert payload["messages"] == [
        {"role": "system", "content": "你是 Yu"},
        {"role": "user", "content": "hi"},
    ]


def test_deepseek_http_error(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    err = urllib.error.HTTPError(
        "https://api.deepseek.com/chat/completions",
        401,
        "Unauthorized",
        None,
        io.BytesIO(b'{"error":"invalid api key"}'),
    )
    _patch_urlopen(monkeypatch, exc=err)
    p = DeepSeekProvider()
    with pytest.raises(LLMError) as ei:
        p.chat([ChatMessage("user", "hi")])
    assert "401" in str(ei.value)


def test_deepseek_urlerror(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    _patch_urlopen(monkeypatch, exc=urllib.error.URLError("connection refused"))
    p = DeepSeekProvider()
    with pytest.raises(LLMError):
        p.chat([ChatMessage("user", "hi")])


def test_deepseek_non_json_response(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    _patch_urlopen(monkeypatch, body=b"<html>not json</html>")
    p = DeepSeekProvider()
    with pytest.raises(LLMError) as ei:
        p.chat([ChatMessage("user", "hi")])
    assert "非 JSON" in str(ei.value)


def test_deepseek_malformed_response(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    _patch_urlopen(monkeypatch, body=json.dumps({"unexpected": True}).encode("utf-8"))
    p = DeepSeekProvider()
    with pytest.raises(LLMError) as ei:
        p.chat([ChatMessage("user", "hi")])
    assert "结构异常" in str(ei.value)


# ---------------------------------------------------------------- factory

def test_factory_returns_deepseek(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    p = create_provider("deepseek")
    assert isinstance(p, DeepSeekProvider)


def test_factory_default_is_deepseek(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.delenv("YU_LLM_PROVIDER", raising=False)
    p = create_provider()
    assert isinstance(p, DeepSeekProvider)


def test_factory_unknown_provider():
    with pytest.raises(LLMError):
        create_provider("not-implemented-provider")


# ---------------------------------------------------------------- conversation

def test_conversation_has_system_prompt_by_default():
    c = Conversation()
    first = c.as_messages()[0]
    assert first.role == "system"
    assert first.content


def test_conversation_accumulates_turns():
    c = Conversation()
    c.add_user("问题")
    c.add_assistant("回答")
    assert [m.role for m in c.as_messages()] == ["system", "user", "assistant"]
    assert len(c) == 3


def test_conversation_clear_keeps_system():
    c = Conversation()
    c.add_user("问题")
    c.add_assistant("回答")
    c.clear()
    assert [m.role for m in c.as_messages()] == ["system"]
