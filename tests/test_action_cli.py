from __future__ import annotations

from yu.actions.models import ActionResult
from yu import cli


class FakeActionService:
    def handle(self, text: str):
        if text == "打开QQ音乐":
            return ActionResult("a1", "app.open", False, "[拒绝] 未授权", "qq_music", "ACTION_DENIED")
        return None


def test_cli_routes_action_before_chat(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "DEFAULT_DB_PATH", str(tmp_path / "yu.db"))
    monkeypatch.setattr(cli, "DEFAULT_AUDIT_DB", str(tmp_path / "audit.db"))
    monkeypatch.setattr(cli, "build_action_service", lambda kernel, audit: FakeActionService())
    commands = iter(["打开QQ音乐", "exit"])
    monkeypatch.setattr("builtins.input", lambda _: next(commands))

    assert cli.main([]) == 0
    assert "[拒绝] 未授权" in capsys.readouterr().out
