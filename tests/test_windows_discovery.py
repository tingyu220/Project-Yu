from yu.platform.windows import discovery
from yu.platform.windows.registry import WindowsAppRegistry


def test_upgrade_is_resolved_without_recreating_registry(tmp_path, monkeypatch):
    first = tmp_path / "v1" / "QQMusic.exe"
    second = tmp_path / "v2" / "QQMusic.exe"
    first.parent.mkdir()
    second.parent.mkdir()
    first.touch()
    second.touch()
    record = {"DisplayName": "QQ音乐", "DisplayIcon": str(first)}
    monkeypatch.setattr(discovery, "installation_records", lambda _: [record])
    config = tmp_path / "apps.yaml"
    config.write_text("apps:\n  qq_music:\n    display_name: QQ音乐\n    auto_discover: true\n    executable: ''\n", encoding="utf-8")
    registry = WindowsAppRegistry(config)
    assert registry.resolve("QQ音乐").executable == str(first)
    record["DisplayIcon"] = str(second)
    assert registry.resolve("QQ音乐").executable == str(second)


def test_discovery_rejects_uninstaller_and_ambiguous_installations(tmp_path, monkeypatch):
    wrong = tmp_path / "Uninstall.exe"
    wrong.touch()
    monkeypatch.setattr(discovery, "installation_records", lambda _: [{"DisplayName": "微信", "DisplayIcon": str(wrong)}])
    assert discovery.find_installed_executable("weixin") is None
    paths = []
    for version in ("v1", "v2"):
        path = tmp_path / version / "Weixin.exe"
        path.parent.mkdir()
        path.touch()
        paths.append({"DisplayName": "微信", "DisplayIcon": str(path)})
    monkeypatch.setattr(discovery, "installation_records", lambda _: paths)
    assert discovery.find_installed_executable("weixin") is None


def test_discovery_requires_exact_identity_and_supports_quoted_icon(tmp_path, monkeypatch):
    path = tmp_path / "Weixin.exe"
    path.touch()
    record = {"DisplayName": "微信卸载工具", "DisplayIcon": f'"{path}",0'}
    monkeypatch.setattr(discovery, "installation_records", lambda _: [record])
    assert discovery.find_installed_executable("weixin") is None
    record["DisplayName"] = "微信"
    assert discovery.find_installed_executable("weixin") == str(path)
