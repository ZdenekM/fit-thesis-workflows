import json
from pathlib import Path

from thesis_review_workflow.amendments import (
    amendment_record_rel,
    amendment_snapshot_rel,
    build_report_amendment_payload,
    validate_report_amendment_record,
)
from thesis_review_workflow.artifact_validation import sha256_file
from thesis_review_workflow.cli import record_report_amendment
from thesis_review_workflow.cli.check_supervisor_report import load_supervisor_report_delta_records
from thesis_review_workflow.review_approvals import REVIEW_APPROVAL_SCHEMA
from thesis_review_workflow.review_manifest import MANIFEST_REL
from thesis_review_workflow.structured_evidence import STRUCTURED_EVIDENCE_SCHEMAS
from thesis_review_workflow.supervisor_report import (
    SUPERVISOR_REPORT_CONFIRMATION_REL,
    SUPERVISOR_REPORT_DRAFT_REL,
    SUPERVISOR_REPORT_REVIEW_REL,
    SUPERVISOR_REPORT_REVIEWED_REL,
    extract_markdown_grade_points,
)


def assert_value_error_contains(expected: str, func, *args, **kwargs) -> None:
    try:
        func(*args, **kwargs)
    except ValueError as exc:
        assert expected in str(exc)
    else:
        raise AssertionError(f"expected ValueError containing {expected!r}")


def report_text(*, grade: str = "B", points: int = 82, public_extra: str = "", private: str = "Děkuji.") -> str:
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

Práci doporučuji hodnotit jako velmi dobrou.{public_extra}

Známka: {grade}
Body: {points}

## Komentář pro studenta

{private}
"""


def write_amendment_pair(tmp_path: Path, *, previous: str, current: str) -> tuple[Path, str]:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    snapshot_rel = amendment_snapshot_rel("2026-05-13T00:00:00Z", "private_comment_delta")
    snapshot = round_dir / snapshot_rel
    current_path = round_dir / SUPERVISOR_REPORT_REVIEWED_REL
    snapshot.parent.mkdir(parents=True)
    current_path.parent.mkdir(parents=True)
    snapshot.write_text(previous, encoding="utf-8")
    current_path.write_text(current, encoding="utf-8")
    draft = round_dir / SUPERVISOR_REPORT_DRAFT_REL
    draft.parent.mkdir(parents=True, exist_ok=True)
    draft.write_text(previous, encoding="utf-8")
    write_current_confirmation_and_approval(round_dir)
    return round_dir, snapshot_rel


def write_current_confirmation_and_approval(round_dir: Path) -> None:
    current_path = round_dir / SUPERVISOR_REPORT_REVIEWED_REL
    draft_path = round_dir / SUPERVISOR_REPORT_DRAFT_REL
    grade_points = extract_markdown_grade_points(current_path.read_text(encoding="utf-8"), require=True)
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
        "reviewed_report_sha256": sha256_file(current_path),
        "grade": grade_points.grade,
        "points": grade_points.points,
        "official_text_confirmed": True,
        "student_comment_confirmed": True,
        "ready_for_is": True,
        "confirmed_by": "supervisor",
        "confirmed_at": "2026-05-13T00:00:00Z",
    }
    confirmation_path = round_dir / SUPERVISOR_REPORT_CONFIRMATION_REL
    confirmation_path.parent.mkdir(parents=True, exist_ok=True)
    confirmation_path.write_text(json.dumps(confirmation, indent=2) + "\n", encoding="utf-8")
    approval = {
        "schema_version": REVIEW_APPROVAL_SCHEMA,
        "case_id": "case-a",
        "round_id": "round-a",
        "workflow_profile": "supervisor_report",
        "reviewer_role": "thesis-supervisor-report-review",
        "reviewer_agent": "reviewer-agent",
        "verdict": "approved",
        "blocking_findings_count": 0,
        "reviewed_artifact_path": SUPERVISOR_REPORT_REVIEWED_REL,
        "reviewed_artifact_sha256": sha256_file(current_path),
        "review_basis_path": SUPERVISOR_REPORT_DRAFT_REL,
        "review_basis_sha256": sha256_file(draft_path),
        "checks_observed": ["check-supervisor-report", "check-supervisor-report-ready"],
        "limitations": [],
        "timestamp": "2026-05-13T00:00:00Z",
    }
    approval_path = round_dir / SUPERVISOR_REPORT_REVIEW_REL
    approval_path.parent.mkdir(parents=True, exist_ok=True)
    approval_path.write_text(json.dumps(approval, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "review-manifest-v1",
        "case_id": "case-a",
        "round_id": "round-a",
        "artifacts": [],
        "helper_checks": [
            {
                "check": name,
                "status": "passed",
                "exit_code": 0,
                "checked_at": "2026-05-13T00:00:00Z",
                "target_artifacts": [SUPERVISOR_REPORT_REVIEWED_REL],
                "target_sha256": {SUPERVISOR_REPORT_REVIEWED_REL: sha256_file(current_path)},
            }
            for name in ("check-supervisor-report", "check-supervisor-report-ready")
        ],
    }
    manifest_path = round_dir / MANIFEST_REL
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def test_private_comment_amendment_records_fresh_approved_hash(tmp_path: Path) -> None:
    round_dir, snapshot_rel = write_amendment_pair(
        tmp_path,
        previous=report_text(private="Děkuji."),
        current=report_text(private="Děkuji a přeji hodně zdaru."),
    )

    payload = build_report_amendment_payload(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        amendment_type="private_comment_delta",
        previous_snapshot_rel=snapshot_rel,
        amended_at="2026-05-13T00:00:00Z",
        approved_by="supervisor",
        rationale="Private comment wording cleanup only.",
    )

    assert payload["schema_version"] == "review-delta-v1"
    assert payload["status"] == "bounded_delta"
    assert payload["approval_status"] == "current"
    assert payload["approval_record_path"] == SUPERVISOR_REPORT_REVIEW_REL
    assert payload["supervisor_confirmation_path"] == SUPERVISOR_REPORT_CONFIRMATION_REL
    assert payload["private_comment_changed"] is True
    assert payload["public_text_changed"] is False
    assert validate_report_amendment_record(payload, round_dir=round_dir, case_id="case-a", round_id="round-a") == []


def test_public_text_amendment_rejects_grade_change(tmp_path: Path) -> None:
    round_dir, snapshot_rel = write_amendment_pair(
        tmp_path,
        previous=report_text(grade="B", points=82),
        current=report_text(grade="A", points=90, public_extra=" Upraveno."),
    )

    assert_value_error_contains(
        "grade or points changed",
        build_report_amendment_payload,
        round_dir,
        case_id="case-a",
        round_id="round-a",
        amendment_type="public_text_delta",
        previous_snapshot_rel=snapshot_rel,
        amended_at="2026-05-13T00:00:00Z",
        approved_by="supervisor",
        rationale="Attempted grade change.",
    )


def test_material_claim_delta_reopens_profile_review(tmp_path: Path) -> None:
    round_dir, snapshot_rel = write_amendment_pair(
        tmp_path,
        previous=report_text(),
        current=report_text(public_extra=" Doplněna materiální formulace."),
    )

    payload = build_report_amendment_payload(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        amendment_type="material_claim_delta",
        previous_snapshot_rel=snapshot_rel,
        amended_at="2026-05-13T00:00:00Z",
        approved_by="supervisor",
        rationale="Material change.",
    )

    assert payload["delta_type"] == "material_claim_delta"
    assert payload["independent_review_reopened"] is True
    assert "check-review-wave --workflow supervisor_report --wave final" in payload["next_action"]


def test_supervisor_report_delta_scan_ignores_other_profiles_without_orphaning_snapshots(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    delta_dir = round_dir / "work" / "review_deltas"
    snapshot_rel = "work/review_deltas/2026-05-15T12-00-00Z-style_only-before.md"
    snapshot_path = round_dir / snapshot_rel
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text("previous feedback\n", encoding="utf-8")
    (delta_dir / "2026-05-15T12-00-00Z-style_only.json").write_text(
        json.dumps(
            {
                "profile_id": "supervisor_feedback",
                "previous_artifact_path": snapshot_rel,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    errors: list[str] = []

    referenced = load_supervisor_report_delta_records(
        delta_dir,
        round_dir,
        case_id="case-a",
        round_id="round-a",
        errors=errors,
    )

    assert errors == []
    assert referenced == {snapshot_rel}


def test_public_text_amendment_requires_current_review_approval(tmp_path: Path) -> None:
    round_dir, snapshot_rel = write_amendment_pair(
        tmp_path,
        previous=report_text(),
        current=report_text(public_extra=" Upraveno."),
    )
    current_path = round_dir / SUPERVISOR_REPORT_REVIEWED_REL
    current_path.write_text(report_text(public_extra=" Upraveno po schválení."), encoding="utf-8")

    assert_value_error_contains(
        "non-material delta requires current approval record",
        build_report_amendment_payload,
        round_dir,
        case_id="case-a",
        round_id="round-a",
        amendment_type="public_text_delta",
        previous_snapshot_rel=snapshot_rel,
        amended_at="2026-05-13T00:00:00Z",
        approved_by="supervisor",
        rationale="Public wording cleanup after approval should fail.",
    )


def test_record_report_amendment_rolls_back_snapshot_on_rejected_delta(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "repo"
    case_dir = root / "cases" / "case-a"
    round_dir = case_dir / "rounds" / "round-a"
    current_path = round_dir / SUPERVISOR_REPORT_REVIEWED_REL
    current_path.parent.mkdir(parents=True)
    current_path.write_text(report_text(grade="A", points=90), encoding="utf-8")
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "case.md").write_text(
        "Work type: BP\nAcademic year: 2025/2026\nReviewer profile: default\n",
        encoding="utf-8",
    )
    (case_dir / "current-round.txt").write_text("round-a\n", encoding="utf-8")
    previous = tmp_path / "previous.md"
    previous.write_text(report_text(grade="B", points=82), encoding="utf-8")
    monkeypatch.setattr(record_report_amendment, "repo_root", lambda: root)

    result = record_report_amendment.main(
        [
            "case-a",
            "round-a",
            "--type",
            "public_text_delta",
            "--previous-reviewed",
            str(previous),
            "--approved-by",
            "supervisor",
            "--rationale",
            "Attempted grade change.",
            "--amended-at",
            "2026-05-13T00:00:00Z",
        ]
    )

    assert result == 1
    assert not (round_dir / amendment_snapshot_rel("2026-05-13T00:00:00Z", "public_text_delta")).exists()
    assert not (round_dir / amendment_record_rel("2026-05-13T00:00:00Z", "public_text_delta")).exists()


def test_record_report_amendment_does_not_delete_existing_snapshot_on_refused_overwrite(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "repo"
    case_dir = root / "cases" / "case-a"
    round_dir = case_dir / "rounds" / "round-a"
    current_path = round_dir / SUPERVISOR_REPORT_REVIEWED_REL
    current_path.parent.mkdir(parents=True)
    current_path.write_text(report_text(), encoding="utf-8")
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "case.md").write_text(
        "Work type: BP\nAcademic year: 2025/2026\nReviewer profile: default\n",
        encoding="utf-8",
    )
    (case_dir / "current-round.txt").write_text("round-a\n", encoding="utf-8")
    previous = tmp_path / "previous.md"
    previous.write_text(report_text(), encoding="utf-8")
    existing_rel = amendment_snapshot_rel("2026-05-13T00:00:00Z", "private_comment_delta")
    existing_snapshot = round_dir / existing_rel
    existing_snapshot.parent.mkdir(parents=True, exist_ok=True)
    existing_snapshot.write_text("existing snapshot\n", encoding="utf-8")
    monkeypatch.setattr(record_report_amendment, "repo_root", lambda: root)

    result = record_report_amendment.main(
        [
            "case-a",
            "round-a",
            "--type",
            "private_comment_delta",
            "--previous-reviewed",
            str(previous),
            "--approved-by",
            "supervisor",
            "--rationale",
            "Duplicate timestamp.",
            "--amended-at",
            "2026-05-13T00:00:00Z",
        ]
    )

    assert result == 1
    assert existing_snapshot.read_text(encoding="utf-8") == "existing snapshot\n"
