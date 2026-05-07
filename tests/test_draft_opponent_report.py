import json
from pathlib import Path

from thesis_review_workflow.cli.draft_opponent_report import advisory_evidence_requirements_note


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def evidence_requirements(case_id: str = "case-a") -> dict[str, object]:
    return {
        "schema_version": "evidence-requirements-v1",
        "case_id": case_id,
        "round_id": "round-a",
        "generated_at": "2026-05-07T00:00:00Z",
        "producer_type": "agent",
        "producer_role": "evidence-requirements-reviewer",
        "producer_agent": "agent-a",
        "authorization_note": "Current request explicitly authorized agents.",
        "source_refs": ["notes/assignment.md"],
        "requirements": [
            {
                "requirement_id": "E1",
                "category": "evaluation_data",
                "state": "weak",
                "request": "Review result data.",
                "evidence_refs": [],
                "requires_reviewer_verification": True,
            }
        ],
        "limitations": [],
    }


def test_evidence_requirements_note_uses_valid_structured_artifact(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    (round_dir / "notes").mkdir(parents=True)
    (round_dir / "notes" / "assignment.md").write_text("# Assignment\n", encoding="utf-8")
    write_json(round_dir / "work" / "evidence_requirements.json", evidence_requirements())

    note = advisory_evidence_requirements_note(round_dir, "case-a", "round-a")

    assert note == "Zohlednit strukturované evidence requirements: evaluation_data:weak."


def test_evidence_requirements_note_rejects_stale_or_invalid_artifact(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    (round_dir / "notes").mkdir(parents=True)
    (round_dir / "notes" / "assignment.md").write_text("# Assignment\n", encoding="utf-8")
    write_json(round_dir / "work" / "evidence_requirements.json", evidence_requirements(case_id="other-case"))

    note = advisory_evidence_requirements_note(round_dir, "case-a", "round-a")

    assert note == "Zkontrolovat nevalidní strukturovaný artefakt evidence requirements."
