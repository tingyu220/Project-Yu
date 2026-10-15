from yu.platform.windows.paths import WindowsPathRegistry
from yu.platform.windows.registry import WindowsAppRegistry


def test_app_registry_resolves_alias_case_insensitively(tmp_path):
    config = tmp_path / "apps.yaml"
    config.write_text(
        "apps:\n"
        "  qq_music:\n"
        "    display_name: QQ音乐\n"
        "    aliases: [QQ音乐, QQ Music]\n"
        "    executable: C:/Apps/QQMusic.exe\n",
        encoding="utf-8",
    )

    registry = WindowsAppRegistry(config)

    entry = registry.resolve("qq music")

    assert entry is not None
    assert entry.app_id == "qq_music"
    assert registry.resolve("unknown") is None


def test_path_registry_expands_environment_variables(tmp_path, monkeypatch):
    target = tmp_path / "Downloads"
    target.mkdir()
    monkeypatch.setenv("YU_TEST_HOME", str(tmp_path))
    config = tmp_path / "paths.yaml"
    config.write_text(
        "paths:\n"
        "  downloads:\n"
        "    display_name: 下载文件夹\n"
        "    aliases: [下载, 下载文件夹]\n"
        "    path: $YU_TEST_HOME/Downloads\n",
        encoding="utf-8",
    )

    entry = WindowsPathRegistry(config).resolve("下载")

    assert entry is not None
    assert entry.path == str(target)
