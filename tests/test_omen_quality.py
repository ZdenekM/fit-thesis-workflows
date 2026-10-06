from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import pytest
from thesis_review_workflow.cli import omen_quality

REPO_ROOT = Path(__file__).resolve().parents[1]


def complexity_payload(*paths: str, cyclomatic: int = 3) -> dict[str, Any]:
    return {
        "files": [
            {"path": f"./{path}", "functions": [{"name": "f", "metrics": {"cyclomatic": cyclomatic, "cognitive": 2}}]}
            for path in paths
        ],
        "summary": {"total_files": len(paths), "max_cyclomatic": cyclomatic, "p90_cyclomatic": 2, "max_cognitive": 2},
    }


def test_omen_config_excludes_private_cases_with_the_key_omen_reads() -> None:
    config = tomllib.loads((REPO_ROOT / "omen.toml").read_text(encoding="utf-8"))

    assert "exclude_patterns" not in config  # omen 4.24.2 silently ignores this key
    assert "cases/**" in config["exclude"]
    assert "dist/**" in config["exclude"]


def test_omen_binary_prefers_explicit_binary(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    binary = tmp_path / "omen"
    binary.write_text("binary\n", encoding="utf-8")
    monkeypatch.setenv("OMEN_BIN", str(binary))

    assert omen_quality.omen_binary(tmp_path) == str(binary)


def test_omen_binary_accepts_local_dev_tool(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("OMEN_BIN", raising=False)
    monkeypatch.setattr(omen_quality.shutil, "which", lambda name: None)
    local = tmp_path / ".pants.d" / "dev-tools" / "omen" / "bin" / "omen"
    local.parent.mkdir(parents=True)
    local.write_text("binary\n", encoding="utf-8")

    assert omen_quality.omen_binary(tmp_path) == str(local)


def test_omen_binary_reports_a_missing_tool(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("OMEN_BIN", raising=False)
    monkeypatch.setattr(omen_quality.shutil, "which", lambda name: None)

    with pytest.raises(omen_quality.OmenRunError, match="omen not found"):
        omen_quality.omen_binary(tmp_path)


def test_scope_rejects_an_empty_file_level_payload() -> None:
    errors = omen_quality.scope_errors("complexity", {"files": [], "summary": {}})

    assert errors and "zero files analysed" in errors[0]


def test_scope_rejects_any_private_case_or_build_path() -> None:
    payload = {
        "clones": [{"file_a": "src/a.py", "file_b": "cases/x/rounds/r/work/code/b.py"}],
        "total_files_scanned": 2,
    }

    errors = omen_quality.scope_errors("clones", payload)

    assert errors == ["clones: analysed a private or build path: cases/x/rounds/r/work/code/b.py"]


def test_scope_accepts_workflow_code_and_a_pathless_score() -> None:
    assert omen_quality.scope_errors("complexity", complexity_payload("src/a.py", "tests/test_a.py")) == []
    assert omen_quality.scope_errors("score", {"overall_score": 90.0, "summary": {"files_analyzed": 218}}) == []


@pytest.mark.parametrize(
    ("analyzer", "payload"),
    [
        ("score", {"overall_score": 100.0, "summary": {"files_analyzed": 0}}),
        ("clones", {"clones": [], "summary": {"duplication_ratio": 0.0}, "total_files_scanned": 0}),
        ("tdg", {"files": [], "average_score": 100.0, "total_files": 0}),
    ],
)
def test_scope_rejects_a_zero_file_run_that_would_pass_its_ratchet(analyzer: str, payload: dict[str, Any]) -> None:
    errors = omen_quality.scope_errors(analyzer, payload)

    assert errors and "zero files analysed" in errors[-1]


def test_scope_allows_the_tracked_public_cases_readme_in_history() -> None:
    payload = {"files": [{"path": "./cases/README.md"}], "summary": {"hotspot_files": ["cases/x/notes.md"]}}

    assert omen_quality.scope_errors("churn", payload) == ["churn: analysed a private or build path: cases/x/notes.md"]


def test_an_empty_history_window_is_reported_not_failed(capsys: pytest.CaptureFixture[str]) -> None:
    assert omen_quality.scope_errors("hotspot", {"hotspots": [], "summary": {}}) == []

    omen_quality.print_sections({"hotspot": {"hotspots": []}}, {"hotspot": {}})

    assert "not a quality signal" in capsys.readouterr().out


def test_ratchets_fail_when_the_code_gets_worse() -> None:
    summaries = {
        "score": {"overall_score": 80.0},
        "complexity": {"max_cyclomatic": 81, "p90_cyclomatic": 8},
    }

    results = {threshold.describe(): ok for threshold, _, ok in omen_quality.evaluate_thresholds(summaries)}

    assert results == {
        "score.overall_score >= 88.0": False,
        "complexity.max_cyclomatic <= 85": True,
        "complexity.p90_cyclomatic <= 9": True,
    }


def test_a_missing_metric_fails_its_ratchet_instead_of_passing() -> None:
    [(_, value, ok)] = omen_quality.evaluate_thresholds({"tdg": {}})

    assert value is None and ok is False


def test_score_components_on_an_empty_import_graph_are_labelled() -> None:
    payload = {
        "components": {
            "coupling": {"details": "217 nodes, 0 cycles, avg degree: 0.0"},
            "smells": {"details": "0 smells"},
            "complexity": {"details": "Analyzed 217 files"},
        }
    }

    assert omen_quality.unmeasured_score_components(payload) == ["coupling", "smells"]
    assert omen_quality.unmeasured_score_components({"components": {"coupling": {"details": "avg degree: 2.1"}}}) == []


def test_focus_lists_functions_and_rejects_files_omen_did_not_analyse() -> None:
    lines, errors = omen_quality.focus_lines(
        complexity_payload("src/a.py"), ["src/a.py", ".codex/hooks/session_start_context.py"]
    )

    assert lines == ["  src/a.py", "      3 cyc   2 cog  f"]
    assert len(errors) == 1 and ".codex/hooks/session_start_context.py" in errors[0]


def fake_run(payloads: dict[str, dict[str, Any]]) -> Any:
    def run(binary: str, root: Path, analyzer: str) -> dict[str, Any]:
        return payloads[analyzer]

    return run


@pytest.fixture
def no_omen_needed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(omen_quality, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(omen_quality, "omen_binary", lambda root: "omen")


@pytest.mark.usefixtures("no_omen_needed")
def test_main_passes_and_reports_a_clean_scoped_run(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(omen_quality, "run_analyzer", fake_run({"complexity": complexity_payload("src/a.py")}))

    assert omen_quality.main(["omen", "--focus", "src/a.py", "complexity"]) == 0

    out = capsys.readouterr().out
    assert "## complexity" in out and "## focus" in out and "PASS complexity.max_cyclomatic" in out


@pytest.mark.usefixtures("no_omen_needed")
def test_main_refuses_to_report_untrustworthy_evidence(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(omen_quality, "run_analyzer", fake_run({"complexity": {"files": [], "summary": {}}}))

    assert omen_quality.main(["omen", "complexity"]) == 1

    captured = capsys.readouterr()
    assert "## complexity" not in captured.out
    assert "zero files analysed" in captured.err


@pytest.mark.usefixtures("no_omen_needed")
def test_main_fails_a_violated_ratchet(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = complexity_payload("src/a.py", cyclomatic=99)
    monkeypatch.setattr(omen_quality, "run_analyzer", fake_run({"complexity": payload}))

    assert omen_quality.main(["omen", "complexity"]) == 1


def test_main_rejects_an_unsupported_analyzer() -> None:
    with pytest.raises(SystemExit):
        omen_quality.main(["omen", "deadcode"])
