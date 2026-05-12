import hashlib
import json
from pathlib import Path

from thesis_review_workflow.cli.draft_supervisor_report import build_report
from thesis_review_workflow.supervisor_report import (
    SUPERVISOR_REPORT_DRAFT_REL,
    SUPERVISOR_REPORT_INPUT_REL,
    SUPERVISOR_REPORT_TRACE_REL,
    extract_markdown_grade_points,
    public_report_text,
    validate_draft_metadata,
    validate_report_markdown,
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def field(field_id: str, title: str, formulation: str, visibility: str = "official") -> dict[str, object]:
    return {
        "field_id": field_id,
        "title": title,
        "formulation": formulation,
        "visibility": visibility,
        "evidence_refs": [SUPERVISOR_REPORT_INPUT_REL],
        "supervisor_input_refs": [SUPERVISOR_REPORT_INPUT_REL],
        "prior_feedback_refs": [],
        "report_refs": [SUPERVISOR_REPORT_DRAFT_REL],
    }


def trace_payload(*, grade: str = "B", points: int | None = 82) -> dict[str, object]:
    return {
        "schema_version": "supervisor-report-trace-v1",
        "case_id": "case-a",
        "round_id": "round-a",
        "generated_at": "2026-05-12T00:00:00Z",
        "producer_type": "agent",
        "producer_role": "thesis-supervisor-report",
        "producer_agent": "agent-a",
        "authorization_note": "Synthetic test authorization.",
        "source_refs": [SUPERVISOR_REPORT_INPUT_REL],
        "limitations": [],
        "supervisor_input_path": SUPERVISOR_REPORT_INPUT_REL,
        "supervisor_input_sha256": "",
        "prior_feedback_status": "absent",
        "report_fields": [
            field("assignment_information", "Informace k zadání", "Zadání bylo splněno."),
            field("literature_work", "Práce s literaturou", "Student pracoval s literaturou."),
            field(
                "activity_during_solution",
                "Aktivita během řešení, konzultace, komunikace",
                "Student konzultoval průběžně.",
            ),
            field("completion_activity", "Aktivita při dokončování", "Definitivní obsah byl konzultován."),
            field("publication_activity", "Publikační činnost, ocenění", "Publikace nejsou."),
            field("overall_assessment", "Celkové hodnocení", "Práci doporučuji hodnotit jako velmi dobrou."),
            field("student_comment", "Komentář pro studenta", "Děkuji za práci.", "private_student_comment"),
        ],
        "grading": {
            "grade": grade,
            "points": points,
            "points_interval": None if points is not None else "80-85",
            "rationale": "Hodnocení odpovídá vstupu vedoucího.",
            "supervisor_input_refs": [SUPERVISOR_REPORT_INPUT_REL],
        },
        "uncertainty_items": [],
        "manual_checks": [],
    }


def write_trace_inputs(round_dir: Path, payload: dict[str, object]) -> tuple[str, str]:
    input_path = round_dir / SUPERVISOR_REPORT_INPUT_REL
    input_path.parent.mkdir(parents=True)
    input_path.write_text("# Intake\n", encoding="utf-8")
    payload["supervisor_input_sha256"] = sha256_file(input_path)
    trace_path = round_dir / SUPERVISOR_REPORT_TRACE_REL
    trace_path.parent.mkdir(parents=True)
    trace_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return sha256_file(trace_path), sha256_file(input_path)


def test_build_supervisor_report_draft_has_stable_is_shape_and_metadata(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = trace_payload()
    trace_hash, input_hash = write_trace_inputs(round_dir, payload)

    draft = build_report(payload, trace_hash=trace_hash, input_hash=input_hash)

    assert "## Informace k zadání" in draft
    assert "## Komentář pro studenta" in draft
    assert "Známka: B" in draft
    assert "Body: 82" in draft
    errors: list[str] = []
    validate_draft_metadata(draft, round_dir, errors)
    assert errors == []
    assert validate_report_markdown(draft, require_grade_points=False) == []
    assert extract_markdown_grade_points(draft, require=True).errors == ()


def test_build_supervisor_report_keeps_private_comment_out_of_public_text(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = trace_payload()
    trace_hash, input_hash = write_trace_inputs(round_dir, payload)

    draft = build_report(payload, trace_hash=trace_hash, input_hash=input_hash)

    public = public_report_text(draft)
    assert "Práci doporučuji hodnotit jako velmi dobrou." in public
    assert "Děkuji za práci." not in public


def test_build_supervisor_report_allows_undecided_grade_only_for_draft(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = trace_payload(grade="undecided", points=None)
    trace_hash, input_hash = write_trace_inputs(round_dir, payload)

    draft = build_report(payload, trace_hash=trace_hash, input_hash=input_hash)

    assert validate_report_markdown(draft, require_grade_points=False) == []
    reviewed_errors = validate_report_markdown(draft, require_grade_points=True)
    assert "concrete grade is required before supervisor report can pass" in reviewed_errors
    assert "concrete point value is required before supervisor report can pass" in reviewed_errors
