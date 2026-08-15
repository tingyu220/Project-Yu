"""Tests for Computer Context (Phase 7)."""

from yu.computer import (
    build_computer_advice,
    format_status,
    is_computer_request,
    read_computer_status,
)
from yu.llm import LLMProvider, LLMResponse
from yu.safety.permissions import PermissionEngine


class FakeProvider(LLMProvider):
    name = "fake"

    def __init__(self):
        self.calls = []

    def chat(self, messages):
        self.calls.append(messages)
        return LLMResponse(content="电脑建议（测试）", model="fake")


def test_read_computer_status():
    s = read_computer_status()
    assert 0.0 <= s.cpu_percent <= 100.0
    assert 0.0 <= s.ram_percent <= 100.0
    assert 0.0 <= s.disk_percent <= 100.0
    assert s.ram_total_gb > 0
    assert s.disk_total_gb > 0
    assert isinstance(s.top_processes, list)


def test_format_status():
    s = read_computer_status()
    text = format_status(s)
    assert "CPU" in text
    assert "内存" in text
    assert "磁盘" in text


def test_is_computer_request():
    assert is_computer_request("我电脑为什么这么卡") is True
    assert is_computer_request("电脑状态怎么样") is True
    assert is_computer_request("今天天气怎么样") is False
    assert is_computer_request("记住：我喜欢咖啡") is False


def test_build_computer_advice_calls_provider():
    fake = FakeProvider()
    s = read_computer_status()
    advice = build_computer_advice(fake, s)
    assert advice == "电脑建议（测试）"
    assert len(fake.calls) == 1
    messages = fake.calls[0]
    assert messages[0].role == "system"
    assert "只读" in messages[0].content


def test_system_status_read_granted():
    p = PermissionEngine("owner-001")
    assert p.has_permission("system.status.read") is True
