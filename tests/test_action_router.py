from yu.actions.router import detect_action_intent
from yu.platform.windows.paths import WindowsPathRegistry
from yu.platform.windows.registry import WindowsAppRegistry


def _registries(tmp_path):
    app_config = tmp_path / "apps.yaml"
    app_config.write_text(
        "apps:\n"
        "  qq_music:\n"
        "    display_name: QQ音乐\n"
        "    aliases: [QQ音乐, QQ Music]\n"
        "    executable: ''\n",
        encoding="utf-8",
    )
    path_config = tmp_path / "paths.yaml"
    path_config.write_text(
        "paths:\n"
        "  downloads:\n"
        "    display_name: 下载文件夹\n"
        "    aliases: [下载, 下载文件夹]\n"
        "    path: $USERPROFILE/Downloads\n",
        encoding="utf-8",
    )
    return WindowsAppRegistry(app_config), WindowsPathRegistry(path_config)


def test_router_detects_app_open(tmp_path):
    apps, paths = _registries(tmp_path)

    intent = detect_action_intent("启动QQ音乐", apps, paths)

    assert intent is not None
    assert intent.intent == "app.open"
    assert intent.target == "qq_music"
    assert intent.parameters == {"app_id": "qq_music"}


def test_router_detects_configured_path(tmp_path):
    apps, paths = _registries(tmp_path)

    intent = detect_action_intent("打开下载文件夹", apps, paths)

    assert intent is not None
    assert intent.intent == "path.open"
    assert intent.parameters["path_id"] == "downloads"


def test_router_detects_explicit_file_path(tmp_path):
    apps, paths = _registries(tmp_path)

    intent = detect_action_intent(r"打开 C:\temp\report.pdf", apps, paths)

    assert intent is not None
    assert intent.intent == "file.open"
    assert intent.parameters["path"] == r"C:\temp\report.pdf"


def test_router_does_not_guess_ambiguous_or_chat_input(tmp_path):
    apps, paths = _registries(tmp_path)

    assert detect_action_intent("打开那个", apps, paths) is None
    assert detect_action_intent("今天天气怎么样", apps, paths) is None
