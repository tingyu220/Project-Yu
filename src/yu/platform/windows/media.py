"""按应用绑定 Windows 媒体会话；只有状态变化得到验证才报告完成。"""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

from ...actions.models import ActionResult, ProposedAction

OPERATIONS = {"media.play": "try_play_async", "media.pause": "try_pause_async",
              "media.next": "try_skip_next_async", "media.previous": "try_skip_previous_async"}


def result(action, success, message, code=None):
    return ActionResult(action.action_id, action.action_type, success, message, "qq_music", code)


async def control_session(session, action):
    """读取前后歌曲和播放状态，不把请求已发送当作播放完成。"""
    before = await session.try_get_media_properties_async()
    accepted = await getattr(session, OPERATIONS[action.action_type])()
    if not accepted:
        return result(action, False, "QQ音乐未接受此操作，请检查播放列表或登录状态。", "MEDIA_REJECTED")
    for _ in range(12):
        after = await session.try_get_media_properties_async()
        # Windows 播放状态枚举：Playing=4、Paused=5。
        status = int(session.get_playback_info().playback_status)
        changed = (after.title, after.artist) != (before.title, before.artist)
        verified = ((action.action_type == "media.play" and status == 4)
                    or (action.action_type == "media.pause" and status == 5)
                    or (action.action_type in {"media.next", "media.previous"} and changed))
        if verified:
            label = {"media.play": "正在播放", "media.pause": "已暂停", "media.next": "已切换至", "media.previous": "已切换至"}[action.action_type]
            return result(action, True, f"{label}《{after.title or '当前歌曲'}》。")
        await asyncio.sleep(0.2)
    return result(action, False, "已发送控制请求，但未确认QQ音乐状态变化。", "MEDIA_NOT_VERIFIED")


async def control(action):
    from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager
    manager = await GlobalSystemMediaTransportControlsSessionManager.request_async()
    sessions = []
    # 刚打开播放器时媒体会话可能稍晚发布，短暂等待，避免立即误报失败。
    for _ in range(40):
        sessions = [s for s in manager.get_sessions() if s.source_app_user_model_id.casefold() == "qqmusic.exe"]
        if sessions:
            break
        await asyncio.sleep(0.2)
    if len(sessions) != 1:
        return result(action, False, "未找到唯一的QQ音乐媒体会话，请先打开QQ音乐并加载歌曲。", "MEDIA_SESSION_NOT_FOUND")
    return await control_session(sessions[0], action)


def execute_media(action: ProposedAction) -> ActionResult:
    if action.action_type not in OPERATIONS:
        return result(action, False, "目前支持播放、暂停、上一首和下一首，尚不支持按歌名搜索或选择歌单。", "UNSUPPORTED_ACTION")
    def run():
        return asyncio.run(asyncio.wait_for(control(action), timeout=12))
    try:
        # API 线程已有事件循环；在独立线程运行 WinRT，审计仍由调用线程负责。
        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(run).result()
    except ImportError:
        return result(action, False, "缺少 Windows 媒体依赖，请安装项目的 media 依赖。", "MEDIA_UNAVAILABLE")
    except (OSError, RuntimeError, TimeoutError):
        return result(action, False, "QQ音乐控制暂不可用，请重试。", "MEDIA_UNAVAILABLE")
