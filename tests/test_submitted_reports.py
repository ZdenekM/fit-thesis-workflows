import json
from pathlib import Path

from thesis_review_workflow.artifact_validation import sha256_file
from thesis_review_workflow.cli import record_submitted_supervisor_report
from thesis_review_workflow.structured_evidence import STRUCTURED_EVIDENCE_SCHEMAS
from thesis_review_workflow.submitted_reports import (
    SUPERVISOR_REPORT_SUBMITTED_PDF_REL,
    SUPERVISOR_REPORT_SUBMITTED_RECORD_REL,
    SUPERVISOR_REPORT_SUBMITTED_TEXT_REL,
    build_supervisor_submitted_report_payload,
    validate_submitted_report_record,
)
from thesis_review_workflow.supervisor_report import (
    SUPERVISOR_REPORT_CONFIRMATION_REL,
    SUPERVISOR_REPORT_REVIEWED_REL,
    public_report_text,
)


def reviewed_report_text(*, grade: str = "B", points: int = 82) -> str:
    return f"""# Posudek vedoucího

## Informace k zadání

Zadání bylo splněno.

## Práce s literaturou

Student pracoval s literaturou.

## Aktivita během řešení, konzultace, komunikace

Student konzultoval průběžně.

## Aktivita při dokončování

Definitivní obsah byl konzultován.

## Publikační činnost, ocenění

Publikace nejsou.

## Celkové hodnocení

Práci doporučuji hodnotit jako velmi dobrou.

Známka: {grade}
Body: {points}

## Komentář pro studenta

Děkuji za práci.
"""


def write_confirmation(round_dir: Path, *, grade: str = "B", points: int = 82) -> None:
    reviewed = round_dir / SUPERVISOR_REPORT_REVIEWED_REL
    confirmation = {
        "schema_version": STRUCTURED_EVIDENCE_SCHEMAS[SUPERVISOR_REPORT_CONFIRMATION_REL],
        "case_id": "case-a",
        "round_id": "round-a",
        "generated_at": "2026-05-13T00:00:00Z",
        "producer_type": "human",
        "producer_role": "supervisor",
        "producer_agent": None,
        "human_reviewer_note": "Confirmed.",
        "source_refs": [SUPERVISOR_REPORT_REVIEWED_REL],
        "limitations": [],
        "reviewed_report_path": SUPERVISOR_REPORT_REVIEWED_REL,
        "reviewed_report_sha256": sha256_file(reviewed),
        "grade": grade,
        "points": points,
        "official_text_confirmed": True,
        "student_comment_confirmed": True,
        "ready_for_is": True,
        "confirmed_by": "supervisor",
        "confirmed_at": "2026-05-13T00:00:00Z",
    }
    path = round_dir / SUPERVISOR_REPORT_CONFIRMATION_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(confirmation, indent=2) + "\n", encoding="utf-8")


def make_submitted_round(tmp_path: Path, *, submitted_text: str | None = None) -> Path:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    reviewed = round_dir / SUPERVISOR_REPORT_REVIEWED_REL
    reviewed.parent.mkdir(parents=True)
    reviewed.write_text(reviewed_report_text(), encoding="utf-8")
    write_confirmation(round_dir)
    pdf = round_dir / SUPERVISOR_REPORT_SUBMITTED_PDF_REL
    text = round_dir / SUPERVISOR_REPORT_SUBMITTED_TEXT_REL
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4\n% synthetic\n")
    text.write_text(
        submitted_text if submitted_text is not None else public_report_text(reviewed.read_text()), encoding="utf-8"
    )
    return round_dir


def test_submitted_supervisor_report_record_binds_pdf_text_reviewed_report_and_confirmation(tmp_path: Path) -> None:
    round_dir = make_submitted_round(tmp_path)

    payload = build_supervisor_submitted_report_payload(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        submitted_at="2026-05-13T00:00:00Z",
        recorded_by="operator",
    )

    assert payload["schema_version"] == "submitted-report-v1"
    assert payload["report_kind"] == "supervisor_report"
    assert payload["recorded_by"] == "operator"
    assert payload["ready_for_archive"] is True
    assert payload["public_text_normalized_match"] is True
    assert payload["grade"] == "B"
    assert payload["points"] == 82
    assert validate_submitted_report_record(payload, round_dir=round_dir, case_id="case-a", round_id="round-a") == []


def test_submitted_supervisor_report_rejects_public_text_mismatch(tmp_path: Path) -> None:
    round_dir = make_submitted_round(tmp_path, submitted_text="Známka: B\nBody: 82\nJiny verejny text.\n")

    payload = build_supervisor_submitted_report_payload(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        submitted_at="2026-05-13T00:00:00Z",
        recorded_by="operator",
    )

    errors = validate_submitted_report_record(
        payload,
        round_dir=round_dir,
        case_id="case-a",
        round_id="round-a",
        rel_path=SUPERVISOR_REPORT_SUBMITTED_RECORD_REL,
    )

    assert (
        f"{SUPERVISOR_REPORT_SUBMITTED_RECORD_REL}: submitted public text does not match reviewed public report text"
        in errors
    )


def test_submitted_supervisor_report_validation_recomputes_record_state(tmp_path: Path) -> None:
    round_dir = make_submitted_round(tmp_path)
    payload = build_supervisor_submitted_report_payload(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        submitted_at="2026-05-13T00:00:00Z",
        recorded_by="operator",
    )
    payload["reviewed_points"] = 83
    payload["public_text_normalized_match"] = False

    errors = validate_submitted_report_record(
        payload,
        round_dir=round_dir,
        case_id="case-a",
        round_id="round-a",
        rel_path=SUPERVISOR_REPORT_SUBMITTED_RECORD_REL,
    )

    assert f"{SUPERVISOR_REPORT_SUBMITTED_RECORD_REL}: reviewed_points is stale" in errors
    assert f"{SUPERVISOR_REPORT_SUBMITTED_RECORD_REL}: public_text_normalized_match is stale" in errors


def test_record_submitted_supervisor_report_rolls_back_copies_on_rejected_record(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    reviewed = round_dir / SUPERVISOR_REPORT_REVIEWED_REL
    reviewed.parent.mkdir(parents=True)
    reviewed.write_text(reviewed_report_text(), encoding="utf-8")
    write_confirmation(round_dir)
    (root / "cases" / "case-a" / "case.md").write_text(
        "Work type: BP\nAcademic year: 2025/2026\nReviewer profile: default\n",
        encoding="utf-8",
    )
    (root / "cases" / "case-a" / "current-round.txt").write_text("round-a\n", encoding="utf-8")
    submitted_pdf = tmp_path / "submitted.pdf"
    submitted_text = tmp_path / "submitted.txt"
    submitted_pdf.write_bytes(b"%PDF-1.4\n% synthetic\n")
    submitted_text.write_text("Známka: B\nBody: 82\nJiny verejny text.\n", encoding="utf-8")
    monkeypatch.setattr(record_submitted_supervisor_report, "repo_root", lambda: root)

    result = record_submitted_supervisor_report.main(
        [
            "case-a",
            "round-a",
            "--pdf",
            str(submitted_pdf),
            "--public-text-file",
            str(submitted_text),
            "--recorded-by",
            "operator",
        ]
    )

    assert result == 1
    assert not (round_dir / SUPERVISOR_REPORT_SUBMITTED_PDF_REL).exists()
    assert not (round_dir / SUPERVISOR_REPORT_SUBMITTED_TEXT_REL).exists()
    assert not (round_dir / SUPERVISOR_REPORT_SUBMITTED_RECORD_REL).exists()
