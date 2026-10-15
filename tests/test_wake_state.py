import pytest


def controller():
    from yu.voice.wake.config import WakeConfig
    from yu.voice.wake.state import WakeController
    now = [0.0]
    return WakeController(WakeConfig(), lambda: now[0]), now


def test_no_command_before_wake_and_ready():
    c, _ = controller()
    assert c.final("1", "打开微信") is None
    assert c.wake()
    assert not c.wake()
    assert c.final("1", "打开微信") is None
    c.ready()
    assert c.final("1", "打开微信") == "打开微信"
    assert c.final("1", "打开微信") is None


@pytest.mark.parametrize("text", ["结束", "OK，结束。", "结束语音", "停止监听"])
def test_stop_returns_to_waiting_and_can_wake_again(text):
    from yu.voice.wake.state import WakeState
    c, now = controller()
    c.wake()
    c.ready()
    assert c.final("1", text) is None
    assert c.state == WakeState.WAITING
    assert not c.wake()
    now[0] = 1
    assert c.wake()
    c.ready()
    assert c.final("1", "结束会议后打开微信") == "结束会议后打开微信"


def test_idle_boundary_and_busy_pause():
    c, now = controller()
    c.wake()
    c.ready()
    now[0] = 29
    assert not c.expired()
    c.set_busy(True)
    now[0] = 100
    assert not c.expired()
    c.set_busy(False)
    now[0] = 129
    assert not c.expired()
    now[0] = 130
    assert c.expired()


def test_absolute_limit_includes_busy_and_handshake():
    c, now = controller()
    c.wake()
    now[0] = 600
    assert c.expired()
    c, now = controller()
    c.wake()
    c.ready()
    c.set_busy(True)
    now[0] = 600
    assert c.expired()


def test_permanent_stop_cannot_be_reawakened():
    c, now = controller()
    c.stop()
    c.end()
    now[0] = 10
    assert not c.wake()


@pytest.mark.parametrize("text", ["停止本次服务", "关闭语音服务。", "宇，停止本次服务。"])
def test_service_stop_is_permanent_not_a_chat_request(text):
    from yu.voice.wake.state import WakeState, is_stop_command
    c, _ = controller()
    c.wake()
    c.ready()
    assert is_stop_command(text)
    assert c.final("stop", text) is None
    assert c.state == WakeState.STOPPED
    c.end()
    assert not c.wake()


def test_discussing_service_stop_does_not_execute_it():
    c, _ = controller()
    c.wake()
    c.ready()
    assert c.final("1", "解释停止本次服务是什么意思") == "解释停止本次服务是什么意思"
