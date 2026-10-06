from thesis_review_workflow.cli import dev_hygiene


def test_jscpd_command_uses_npx_without_shell(monkeypatch) -> None:
    monkeypatch.setattr(dev_hygiene.shutil, "which", lambda name: "/usr/bin/npx" if name == "npx" else None)

    command = dev_hygiene.jscpd_command()

    assert command[0] == "/usr/bin/npx"
    assert command[:3] == ["/usr/bin/npx", "--yes", "jscpd@4.0.9"]
    assert any("cases/**" in item for item in command)
    assert ".codex/hooks" in command
    assert "src" in command
