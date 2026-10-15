from yu.actions.models import ActionResult


def test_action_result_success():
    result = ActionResult(
        action_id="a1",
        action_type="app.open",
        success=True,
        message="已打开 QQ音乐。",
        target="qq_music",
    )

    assert result.success is True
    assert result.target == "qq_music"
    assert result.error_code is None
