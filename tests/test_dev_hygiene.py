from pathlib import Path

from thesis_review_workflow.cli import dev_hygiene


def test_jscpd_command_uses_npx_without_shell(monkeypatch) -> None:
    monkeypatch.setattr(dev_hygiene.shutil, "which", lambda name: "/usr/bin/npx" if name == "npx" else None)

    command = dev_hygiene.jscpd_command()

    assert command[0] == "/usr/bin/npx"
    assert command[:3] == ["/usr/bin/npx", "--yes", "jscpd@4.0.9"]
    assert any("cases/**" in item for item in command)
    assert ".codex/hooks" in command
    assert "src" in command


def test_omen_commands_prefer_explicit_binary(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OMEN_BIN", str(tmp_path / "omen"))

    commands = dev_hygiene.omen_commands(tmp_path)

    assert [command[-1] for command in commands] == ["score", "hotspot", "deadcode"]
    assert all(command[:6] == [str(tmp_path / "omen"), "-c", "omen.toml", "-p", ".", "-f"] for command in commands)


def test_omen_binary_accepts_local_dev_tool(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("OMEN_BIN", raising=False)
    monkeypatch.setattr(dev_hygiene.shutil, "which", lambda name: None)
    local = tmp_path / ".pants.d" / "dev-tools" / "omen" / "bin" / "omen"
    local.parent.mkdir(parents=True)
    local.write_text("binary\n", encoding="utf-8")

    assert dev_hygiene.omen_binary(tmp_path) == str(local)
