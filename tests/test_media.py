"""媒体命令必须实际控制并回读，不能落入 LLM 假报成功。"""
import asyncio
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from yu.actions.models import ProposedAction
from yu.actions.router import detect_action_intent
from yu.platform.windows.media import control_session, execute_media
from yu.platform.windows.registry import WindowsAppRegistry
from yu.platform.windows.paths import WindowsPathRegistry
from test_action_service import _service, FakeExecutor
from yu.actions.models import ActionResult


def action(kind):
    return ProposedAction("test-media", kind, "测试", "owner", "yu", "media.control", "测试")


@pytest.mark.parametrize("text,kind", [
    ("播放下一首歌。", "media.next"), ("暂停QQ音乐", "media.pause"),
    ("宇，播放QQ音乐。", "media.play"), ("上一首", "media.previous"),
    ("播放晴天", "media.unsupported"),
])
def test_media_routes_locally(tmp_path, text, kind):
    intent = detect_action_intent(text, WindowsAppRegistry(tmp_path / "apps"), WindowsPathRegistry(tmp_path / "paths"))
    assert intent.intent == kind


class Session:
    def __init__(self, accepted=True, changes=True):
        self.accepted, self.changes = accepted, changes
        self.title = "旧歌曲"
        self.status = 5

    async def try_get_media_properties_async(self):
        return SimpleNamespace(title=self.title, artist="歌手")

    def get_playback_info(self):
        return SimpleNamespace(playback_status=self.status)

    async def try_play_async(self):
        if self.changes: self.status = 4
        return self.accepted

    async def try_skip_next_async(self):
        if self.changes: self.title = "新歌曲"
        return self.accepted


def test_play_verified_by_playback_status():
    result = asyncio.run(control_session(Session(), action("media.play")))
    assert result.success
    assert "正在播放" in result.message


def test_next_verified_by_changed_title():
    result = asyncio.run(control_session(Session(), action("media.next")))
    assert result.success
    assert "新歌曲" in result.message


def test_rejected_request_cannot_claim_success():
    result = asyncio.run(control_session(Session(accepted=False), action("media.play")))
    assert result.error_code == "MEDIA_REJECTED"


def test_accepted_without_change_cannot_claim_success():
    async def no_wait(_): pass
    with patch("yu.platform.windows.media.asyncio.sleep", no_wait):
        result = asyncio.run(control_session(Session(changes=False), action("media.next")))
    assert not result.success
    assert result.error_code == "MEDIA_NOT_VERIFIED"


def test_unknown_song_request_is_not_executed():
    assert execute_media(action("media.unsupported")).error_code == "UNSUPPORTED_ACTION"


def test_media_requires_separate_permission(tmp_path):
    executor = FakeExecutor(ActionResult("a", "media.next", True, "切换成功", "qq_music"))
    service, permissions, audit = _service(tmp_path, executor)
    try:
        permissions.grant("process.start")
        assert service.handle("播放下一首歌。").error_code == "ACTION_DENIED"
        assert not executor.calls
        permissions.grant("media.control")
        assert service.handle("播放下一首歌。").success
        assert executor.calls[0].required_capability == "media.control"
        assert audit.list_recent(1)[0].event_type == "ACTION_EXECUTED"
    finally:
        audit.close()


def test_open_and_play_uses_both_permissions(tmp_path):
    executor = FakeExecutor(ActionResult("a", "app.open", True, "已打开", "qq_music"))
    service, permissions, audit = _service(tmp_path, executor)
    try:
        permissions.grant("process.start")
        assert service.handle("打开QQ音乐并播放").error_code == "ACTION_DENIED"
        assert [a.action_type for a in executor.calls] == ["app.open"]
        permissions.grant("media.control")
        executor.calls.clear()
        service.handle("打开QQ音乐并播放")
        assert [a.action_type for a in executor.calls] == ["app.open", "media.play"]
    finally:
        audit.close()
