from types import SimpleNamespace
from yu.api.capabilities import describe_capabilities, is_capability_question


def test_capability_question_matches_real_test_but_not_quoted_intent():
    assert is_capability_question("你好，你是谁？你能做什么？")
    assert not is_capability_question("记住别人问你能做什么")


def test_capabilities_only_advertise_existing_apps_with_permission(tmp_path):
    app_path = tmp_path / "app.exe"
    app_path.touch()
    apps = [SimpleNamespace(display_name="微信", executable=str(app_path)),
            SimpleNamespace(display_name="未安装应用", executable=str(tmp_path / "missing.exe"))]
    ctx = SimpleNamespace(permissions=SimpleNamespace(has_permission=lambda cap: cap == "process.start"),
                          action_service=SimpleNamespace(app_registry=SimpleNamespace(list_apps=lambda: apps)))
    description = describe_capabilities(ctx)
    assert "微信" in description
    assert "未安装应用" not in description
    ctx.permissions.has_permission = lambda cap: False
    assert "微信" not in describe_capabilities(ctx)
