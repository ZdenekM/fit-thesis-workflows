import json
import zipfile
from pathlib import Path

from thesis_review_workflow.code_reproducibility import classify, to_artifact


def make_code_zip(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("project/README.md", "# Project\n")
        archive.writestr("project/pyproject.toml", "[project]\nname = 'demo'\n")
        archive.writestr("project/src/main.py", "print('demo')\n")
        archive.writestr("project/tests/test_smoke.py", "def test_smoke():\n    assert True\n")


def test_classify_no_code_evidence(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    summary = classify(round_dir)

    assert summary.classification == "no_code_evidence"
    assert summary.code_evidence == []
    assert summary.roots == []


def test_classify_unprepared_code_does_not_run_commands(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    make_code_zip(round_dir / "inputs" / "code.zip")

    summary = classify(round_dir)

    assert summary.classification == "not_attempted"
    assert summary.code_evidence == ["inputs/code.zip"]
    assert any("Prepare or manually unpack" in request for request in summary.evidence_requests)


def test_classify_prepared_workspace_uses_static_inventory(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    root = round_dir / "work" / "code" / "code" / "project"
    (root / "src").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "README.md").write_text("# Project\n", encoding="utf-8")
    (root / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (root / "src" / "main.py").write_text("print('demo')\n", encoding="utf-8")
    (root / "tests" / "test_smoke.py").write_text("def test_smoke():\n    assert True\n", encoding="utf-8")

    summary = classify(round_dir)
    artifact = to_artifact("case-a", "round-a", "2026-05-06T00:00:00Z", summary)

    assert summary.classification == "static_setup_present"
    assert summary.roots[0]["suggested_smoke_commands"] == ["python -m compileall .", "python -m pytest -q"]
    assert artifact["execution_policy"] == "static_only_no_submitted_code_executed"
    assert json.dumps(artifact)
