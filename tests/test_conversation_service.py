import asyncio
import pytest


def test_concurrent_turns_are_serial_and_read_completed_history(tmp_path):
    from yu.conversation.service import ConversationService
    from yu.conversation.store import ConversationStore
    async def run():
        entered, release = asyncio.Event(), asyncio.Event()
        seen = []
        async def handler(message, history, refs):
            seen.append((message, history))
            if message == "甲":
                entered.set()
                await release.wait()
            return {"reply": message + "完成"}
        service = ConversationService(ConversationStore(str(tmp_path / "db")), handler)
        first = asyncio.create_task(service.submit("s", "r1", "web", "甲"))
        await entered.wait()
        second = asyncio.create_task(service.submit("s", "r2", "local_voice", "乙"))
        await asyncio.sleep(0.02)
        before = list(seen)
        release.set()
        await asyncio.gather(first, second)
        await service.close()
        assert before == [("甲", [])]
        assert seen[1][1][-1] == {"role": "assistant", "content": "甲完成"}
    asyncio.run(run())


def test_duplicate_request_executes_once(tmp_path):
    from yu.conversation.service import ConversationService
    from yu.conversation.store import ConversationStore
    calls = []
    async def handler(message, history, refs):
        calls.append(message)
        await asyncio.sleep(0.01)
        return {"reply": "完成", "allowed": True}
    async def run():
        service = ConversationService(ConversationStore(str(tmp_path / "db")), handler)
        args = ("s", "r1", "web", "打开微信")
        results = await asyncio.gather(service.submit(*args), service.submit(*args))
        await service.close()
        return results
    results = asyncio.run(run())
    assert calls == ["打开微信"]
    assert results[0]["reply"] == results[1]["reply"] == "完成"


def test_conflicting_payload_rejected(tmp_path):
    from yu.conversation.service import ConversationService, SessionConflict
    from yu.conversation.store import ConversationStore
    async def handler(*args): return {"reply": "完成"}
    async def run():
        service = ConversationService(ConversationStore(str(tmp_path / "db")), handler)
        await service.submit("s", "r1", "web", "甲")
        with pytest.raises(SessionConflict):
            await service.submit("s", "r1", "web", "乙")
        await service.close()
    asyncio.run(run())


def test_second_turn_reads_first_result(tmp_path):
    from yu.conversation.service import ConversationService
    from yu.conversation.store import ConversationStore
    histories = []
    async def handler(message, history, refs):
        histories.append(history)
        return {"reply": message + "完成"}
    async def run():
        service = ConversationService(ConversationStore(str(tmp_path / "db")), handler)
        await service.submit("s", "r1", "web", "甲")
        await service.submit("s", "r2", "local_voice", "乙")
        await service.close()
    asyncio.run(run())
    assert histories[1][-2:] == [{"role": "user", "content": "甲"}, {"role": "assistant", "content": "甲完成"}]
