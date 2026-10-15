"""慢执行不能阻塞实时语音循环，数据库仍在原线程使用。"""
import asyncio
import threading

from yu.api import app as api_app
from yu.api.context import build_context
from yu.llm import LLMResponse
from yu.actions.models import ActionResult
from test_action_service import _service


def test_llm_does_not_block_event_loop():
    release = threading.Event()
    observed = []

    class SlowProvider:
        def chat(self, messages):
            observed.append(release.wait(1))
            return LLMResponse(content="测试回复")

    async def scenario():
        ctx = build_context()
        ctx.provider = SlowProvider()
        async def tick():
            await asyncio.sleep(0.02)
            release.set()
        try:
            tick_task = asyncio.create_task(tick())
            result = await api_app._chat_memory(ctx, "你好", [])
            await tick_task
            assert result["reply"] == "测试回复"
            assert observed == [True]
        finally:
            ctx.close()
    asyncio.run(scenario())


def test_media_async_preserves_audit_and_event_loop(tmp_path):
    release = threading.Event()
    observed = []

    class SlowExecutor:
        def execute(self, action):
            observed.append(release.wait(1))
            return ActionResult(action.action_id, action.action_type, True, "已播放", "qq_music")

    async def scenario():
        service, permissions, audit = _service(tmp_path, SlowExecutor())
        permissions.grant("media.control")
        async def tick():
            await asyncio.sleep(0.02)
            release.set()
        try:
            tick_task = asyncio.create_task(tick())
            result = await service.handle_async("播放QQ音乐")
            await tick_task
            assert result.success
            assert observed == [True]
            assert audit.list_recent(1)[0].event_type == "ACTION_EXECUTED"
        finally:
            audit.close()
    asyncio.run(scenario())
