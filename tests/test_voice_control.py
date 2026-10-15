import time


def test_heartbeat_older_than_five_seconds_is_unknown():
    from yu.voice.wake.control import VoiceControlState
    state = VoiceControlState(clock=lambda: 10.0)
    state.publish("listening", 1.0)
    assert state.snapshot(10.0)["phase"] == "unknown"


def test_stop_command_has_priority():
    from yu.voice.wake.control import VoiceControlState
    state = VoiceControlState()
    state.enqueue("pause_speech")
    state.enqueue("stop_service")
    assert state.take() == "stop_service"


def test_control_status_is_local_and_explicit():
    from yu.voice.wake.control import VoiceControlState
    state = VoiceControlState()
    state.publish("waiting", time.monotonic())
    assert state.snapshot(time.monotonic())["phase"] == "waiting"
