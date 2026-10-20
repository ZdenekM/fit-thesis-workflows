"""Tests for `scripts/set-review-scope`, which declares a reviewer scope per session."""

import json
import os
import time
from pathlib import Path

import pytest

from thesis_review_workflow.cli import set_review_scope


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "cases" / "demo" / "rounds" / "r1").mkdir(parents=True)
    monkeypatch.setattr(set_review_scope, "repo_root", lambda: tmp_path)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-1")
    return tmp_path


def _scope_dir(root: Path) -> Path:
    return root / ".claude" / "hooks" / "review_scopes"


def test_declares_the_scope_for_the_calling_session_only(root: Path) -> None:
    assert set_review_scope.main(["demo", "r1"]) == 0
    assert json.loads((_scope_dir(root) / "sess-1.json").read_text(encoding="utf-8")) == {
        "case": "demo",
        "round": "r1",
    }
    assert [p.name for p in _scope_dir(root).iterdir()] == ["sess-1.json"]


def test_clear_removes_only_the_calling_sessions_scope(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "other-session")
    assert set_review_scope.main(["demo", "r1"]) == 0
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-1")
    assert set_review_scope.main(["demo", "r1"]) == 0

    assert set_review_scope.main(["--clear"]) == 0
    assert sorted(p.name for p in _scope_dir(root).iterdir()) == ["other-session.json"]


def test_refuses_without_a_session_id(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for value in ("", "../escape"):
        monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", value)
        assert set_review_scope.main(["demo", "r1"]) == 2
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID")
    assert set_review_scope.main(["demo", "r1"]) == 2
    assert not _scope_dir(root).exists()


def test_refuses_a_case_or_round_that_does_not_exist(root: Path) -> None:
    assert set_review_scope.main(["nope", "r1"]) == 1
    assert set_review_scope.main(["demo", "r9"]) == 1


def test_declaring_prunes_scopes_left_by_long_ended_sessions(root: Path) -> None:
    _scope_dir(root).mkdir(parents=True)
    stale = _scope_dir(root) / "ended.json"
    recent = _scope_dir(root) / "parallel.json"
    for path in (stale, recent):
        path.write_text('{"case": "demo", "round": "r1"}', encoding="utf-8")
    old = time.time() - set_review_scope.STALE_AFTER_SECONDS - 60
    os.utime(stale, (old, old))

    assert set_review_scope.main(["demo", "r1"]) == 0
    assert sorted(p.name for p in _scope_dir(root).iterdir()) == ["parallel.json", "sess-1.json"]


def test_show_names_the_session(root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert set_review_scope.main(["--show"]) == 0
    assert "No declared review scope for session sess-1" in capsys.readouterr().out
    assert set_review_scope.main(["demo", "r1"]) == 0
    capsys.readouterr()
    assert set_review_scope.main(["--show"]) == 0
    out = capsys.readouterr().out
    assert "Session sess-1:" in out and '"case": "demo"' in out
    assert set_review_scope.main(["--clear"]) == 0
    assert set_review_scope.main(["--clear"]) == 0
    assert "No declared review scope to clear." in capsys.readouterr().out
