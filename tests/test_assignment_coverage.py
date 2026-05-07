import json
from pathlib import Path

from thesis_review_workflow.cli import check_assignment_coverage


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def make_round(root: Path) -> Path:
    case_dir = root / "cases" / "case-a"
    round_dir = case_dir / "rounds" / "round-a"
    (round_dir / "notes").mkdir(parents=True)
    (round_dir / "work").mkdir()
    (case_dir / "case.md").write_text("Reviewer profile: default\n", encoding="utf-8")
    (case_dir / "current-round.txt").write_text("round-a\n", encoding="utf-8")
    (round_dir / "notes" / "assignment.md").write_text("# Assignment\n", encoding="utf-8")
    return round_dir


def assignment_artifact(case_id: str = "case-a") -> dict[str, object]:
    return {
        "schema_version": "assignment-coverage-agent-v1",
        "case_id": case_id,
        "round_id": "round-a",
        "generated_at": "2026-05-07T00:00:00Z",
        "producer_type": "agent",
        "producer_role": "assignment-coverage-reviewer",
        "producer_agent": "agent-a",
        "authorization_note": "Current request explicitly authorized agents.",
        "source_refs": ["notes/assignment.md"],
        "assignment_points": [
            {
                "point_id": "A1",
                "summary": "Requirement.",
                "source_refs": ["notes/assignment.md"],
                "coverage": {
                    "status": "covered",
                    "evidence_refs": ["notes/assignment.md"],
                    "limitations": [],
                    "requires_reviewer_verification": False,
                },
            },
            {
                "point_id": "A2",
                "summary": "Second requirement.",
                "source_refs": ["notes/assignment.md"],
                "coverage": {
                    "status": "not_verifiable",
                    "evidence_refs": [],
                    "limitations": ["Needs reviewer check."],
                    "requires_reviewer_verification": True,
                },
            },
        ],
        "limitations": [],
    }


def test_check_assignment_coverage_validates_structured_artifact(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    root = tmp_path / "repo"
    round_dir = make_round(root)
    write_json(round_dir / "work" / "assignment_coverage_agent.json", assignment_artifact())
    monkeypatch.setattr(check_assignment_coverage, "repo_root", lambda: root)

    assert check_assignment_coverage.main(["case-a", "round-a"]) == 0

    output = capsys.readouterr().out
    assert "Assignment coverage artifact: cases/case-a/rounds/round-a/work/assignment_coverage_agent.json" in output
    assert "Assignment points: 2" in output
    assert "Coverage statuses: covered=1, not_verifiable=1" in output
    assert "Reviewer verification required: 1" in output
    assert not (round_dir / "work" / "assignment_coverage_map.json").exists()


def test_check_assignment_coverage_requires_existing_structured_artifact(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    root = tmp_path / "repo"
    make_round(root)
    monkeypatch.setattr(check_assignment_coverage, "repo_root", lambda: root)

    assert check_assignment_coverage.main(["case-a", "round-a"]) == 1

    output = capsys.readouterr().out
    assert "missing structured evidence artifact" in output
    assert "Create `work/assignment_coverage_agent.json`" in output


def test_check_assignment_coverage_rejects_invalid_status(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    root = tmp_path / "repo"
    round_dir = make_round(root)
    payload = assignment_artifact()
    points = payload["assignment_points"]
    assert isinstance(points, list)
    coverage = points[0]["coverage"]
    assert isinstance(coverage, dict)
    coverage["status"] = "maybe"
    write_json(round_dir / "work" / "assignment_coverage_agent.json", payload)
    monkeypatch.setattr(check_assignment_coverage, "repo_root", lambda: root)

    assert check_assignment_coverage.main(["case-a", "round-a"]) == 1

    output = capsys.readouterr().out
    assert "status must be one of" in output
