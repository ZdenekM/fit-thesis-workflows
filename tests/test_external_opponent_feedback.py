import json
from pathlib import Path

from thesis_review_workflow.cli import check_external_opponent_feedback
from thesis_review_workflow.external_opponent_feedback import (
    EXTERNAL_OPPONENT_FEEDBACK_ANALYSIS_REL,
    EXTERNAL_OPPONENT_FEEDBACK_FINDINGS_REL,
    EXTERNAL_OPPONENT_FEEDBACK_FINDINGS_SCHEMA,
    EXTERNAL_OPPONENT_FEEDBACK_REVIEW_REL,
    EXTERNAL_OPPONENT_REPORT_INTAKE_REL,
    EXTERNAL_OPPONENT_REPORT_INTAKE_SCHEMA,
    SUPERVISOR_LEARNING_CANDIDATES_REL,
    SUPERVISOR_LEARNING_CANDIDATES_SCHEMA,
    validate_external_opponent_feedback_payload,
    validate_external_opponent_feedback_round,
)
from thesis_review_workflow.work_artifacts import (
    collect_supporting_work_artifacts,
    sha256_file,
    validate_supporting_work_artifacts,
)

CASE_ID = "case-a"
ROUND_ID = "round-a"


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def hash_ref(round_dir: Path, rel_path: str) -> dict[str, str]:
    return {"path": rel_path, "sha256": sha256_file(round_dir / rel_path)}


def make_round(tmp_path: Path) -> Path:
    round_dir = tmp_path / "cases" / CASE_ID / "rounds" / ROUND_ID
    write_text(round_dir.parents[1] / "current-round.txt", ROUND_ID + "\n")
    write_text(round_dir / "notes" / "external-opponent-report-intake.md", "# Synthetic intake\n")
    write_text(round_dir / "inputs" / "external_opponent_report" / "opponent-report.txt", "Synthetic report.\n")
    write_text(round_dir / "outputs" / "feedback_student.md", "# Synthetic prior feedback\n")
    write_text(round_dir / "outputs" / "revision_diff.md", "# Synthetic revision diff\n")
    return round_dir


def intake_payload(
    round_dir: Path,
    *,
    permission: str = "allowed",
    source_status: str = "official_private_copy",
) -> dict[str, object]:
    report_rel = "inputs/external_opponent_report/opponent-report.txt"
    return {
        "schema_version": EXTERNAL_OPPONENT_REPORT_INTAKE_SCHEMA,
        "case_id": CASE_ID,
        "round_id": ROUND_ID,
        "generated_at": "2026-05-25T00:00:00Z",
        "producer_type": "human",
        "producer_role": "operator-intake",
        "producer_agent": None,
        "human_reviewer_note": "Synthetic operator intake.",
        "limitations": [],
        "source_status": source_status,
        "workflow_learning_permission": permission,
        "quote_permission": "none",
        "agent_report_reading_authorized": True,
        "intended_uses": ["supervisor_feedback_pipeline_learning"],
        "source_refs": [
            {
                "ref_id": "opponent_report_text",
                "kind": "report_text",
                "path": report_rel,
                "sha256": sha256_file(round_dir / report_rel),
            }
        ],
        "intake_note_ref": hash_ref(round_dir, "notes/external-opponent-report-intake.md"),
        "comparison_basis_refs": [hash_ref(round_dir, "outputs/feedback_student.md")],
        "operator_context_refs": [],
    }


def findings_payload(round_dir: Path) -> dict[str, object]:
    return {
        "schema_version": EXTERNAL_OPPONENT_FEEDBACK_FINDINGS_SCHEMA,
        "case_id": CASE_ID,
        "round_id": ROUND_ID,
        "generated_at": "2026-05-25T00:05:00Z",
        "producer_type": "agent",
        "producer_role": "thesis-supervisor-opponent-feedback-learning",
        "producer_agent": "agent-a",
        "authorization_note": "Synthetic current-request authorization.",
        "limitations": [],
        "intake_ref": hash_ref(round_dir, EXTERNAL_OPPONENT_REPORT_INTAKE_REL),
        "findings": [
            {
                "id": "finding-a",
                "classification": "missed_by_feedback",
                "summary": "Synthetic evidence-class concern.",
                "available_at_feedback_time": "available",
                "confidence": "medium",
                "promotion_route": "workflow_docs_or_skill",
                "opponent_report_refs": [
                    {
                        "source_ref_id": "opponent_report_text",
                        "locator": "synthetic section",
                    }
                ],
                "comparison_refs": [
                    {
                        **hash_ref(round_dir, "outputs/feedback_student.md"),
                        "locator": "synthetic prior-feedback section",
                    }
                ],
                "limitations": [],
            }
        ],
    }


def candidates_payload(round_dir: Path) -> dict[str, object]:
    return {
        "schema_version": SUPERVISOR_LEARNING_CANDIDATES_SCHEMA,
        "case_id": CASE_ID,
        "round_id": ROUND_ID,
        "generated_at": "2026-05-25T00:10:00Z",
        "producer_type": "agent",
        "producer_role": "thesis-supervisor-opponent-feedback-learning",
        "producer_agent": "agent-a",
        "authorization_note": "Synthetic current-request authorization.",
        "limitations": [],
        "findings_ref": hash_ref(round_dir, EXTERNAL_OPPONENT_FEEDBACK_FINDINGS_REL),
        "candidates": [
            {
                "id": "candidate-a",
                "source_finding_ids": ["finding-a"],
                "promotion_route": "workflow_docs_or_skill",
                "target_owner": "thesis-supervisor-feedback",
                "status": "proposed",
                "summary": "Synthetic workflow-learning candidate.",
                "generalized_lesson": "Check the synthetic evidence class before final feedback.",
                "target_refs": [".agents/skills/thesis-supervisor-feedback/SKILL.md"],
                "privacy_review": {
                    "contains_private_case_details": False,
                    "checked_for": ["student_identity", "topic", "metrics", "opponent_text"],
                },
                "limitations": [],
            }
        ],
    }


def write_valid_artifacts(round_dir: Path) -> None:
    write_json(round_dir / EXTERNAL_OPPONENT_REPORT_INTAKE_REL, intake_payload(round_dir))
    write_json(round_dir / EXTERNAL_OPPONENT_FEEDBACK_FINDINGS_REL, findings_payload(round_dir))
    write_json(round_dir / SUPERVISOR_LEARNING_CANDIDATES_REL, candidates_payload(round_dir))
    write_text(
        round_dir / EXTERNAL_OPPONENT_FEEDBACK_ANALYSIS_REL,
        "# External Opponent Feedback Analysis\n\nSynthetic case-local analysis.\n",
    )
    write_json(
        round_dir / EXTERNAL_OPPONENT_FEEDBACK_REVIEW_REL,
        {
            "schema_version": "review-approval-v1",
            "case_id": CASE_ID,
            "round_id": ROUND_ID,
            "workflow_profile": "external_opponent_feedback_learning",
            "reviewer_role": "thesis_evidence_calibrator",
            "reviewer_agent": "agent-reviewer",
            "timestamp": "2026-05-25T00:15:00Z",
            "verdict": "approved",
            "blocking_findings_count": 0,
            "reviewed_artifact_path": EXTERNAL_OPPONENT_FEEDBACK_ANALYSIS_REL,
            "reviewed_artifact_sha256": sha256_file(round_dir / EXTERNAL_OPPONENT_FEEDBACK_ANALYSIS_REL),
            "review_basis_path": SUPERVISOR_LEARNING_CANDIDATES_REL,
            "review_basis_sha256": sha256_file(round_dir / SUPERVISOR_LEARNING_CANDIDATES_REL),
            "checks_observed": ["check-external-opponent-feedback"],
            "limitations": [],
        },
    )


def test_external_opponent_feedback_round_and_work_artifacts_validate(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    write_valid_artifacts(round_dir)

    assert (
        validate_external_opponent_feedback_round(
            round_dir,
            case_id=CASE_ID,
            round_id=ROUND_ID,
            require_analysis=True,
        )
        == []
    )

    records = collect_supporting_work_artifacts(round_dir)
    by_path = {record["path"]: record for record in records}
    assert by_path[EXTERNAL_OPPONENT_REPORT_INTAKE_REL]["schema_version"] == EXTERNAL_OPPONENT_REPORT_INTAKE_SCHEMA
    assert (
        by_path[EXTERNAL_OPPONENT_FEEDBACK_FINDINGS_REL]["schema_version"] == EXTERNAL_OPPONENT_FEEDBACK_FINDINGS_SCHEMA
    )
    assert by_path[SUPERVISOR_LEARNING_CANDIDATES_REL]["schema_version"] == SUPERVISOR_LEARNING_CANDIDATES_SCHEMA
    assert validate_supporting_work_artifacts(records, round_dir, case_id=CASE_ID, round_id=ROUND_ID) == []


def test_source_refs_must_stay_under_external_opponent_report_inputs(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    payload = intake_payload(round_dir)
    payload["source_refs"][0]["path"] = "work/code/src/vendor-doc.md"  # type: ignore[index]

    errors = validate_external_opponent_feedback_payload(
        payload,
        EXTERNAL_OPPONENT_REPORT_INTAKE_REL,
        round_dir=round_dir,
        case_id=CASE_ID,
        round_id=ROUND_ID,
    )

    assert any("path must stay under inputs/external_opponent_report/" in error for error in errors)


def test_source_refs_are_hash_bound(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    payload = intake_payload(round_dir)
    payload["source_refs"][0]["sha256"] = "0" * 64  # type: ignore[index]

    errors = validate_external_opponent_feedback_payload(
        payload,
        EXTERNAL_OPPONENT_REPORT_INTAKE_REL,
        round_dir=round_dir,
        case_id=CASE_ID,
        round_id=ROUND_ID,
    )

    assert any("sha256 is stale" in error for error in errors)


def test_unknown_or_restricted_source_status_blocks_findings(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    write_json(
        round_dir / EXTERNAL_OPPONENT_REPORT_INTAKE_REL,
        intake_payload(round_dir, source_status="unknown_or_restricted"),
    )
    payload = findings_payload(round_dir)

    errors = validate_external_opponent_feedback_payload(
        payload,
        EXTERNAL_OPPONENT_FEEDBACK_FINDINGS_REL,
        round_dir=round_dir,
        case_id=CASE_ID,
        round_id=ROUND_ID,
    )

    assert any("findings require a usable source_status in intake" in error for error in errors)


def test_findings_reject_raw_opponent_report_text_fields(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    write_json(round_dir / EXTERNAL_OPPONENT_REPORT_INTAKE_REL, intake_payload(round_dir))
    payload = findings_payload(round_dir)
    payload["findings"][0]["opponent_text"] = "Synthetic quote field is not allowed."  # type: ignore[index]

    errors = validate_external_opponent_feedback_payload(
        payload,
        EXTERNAL_OPPONENT_FEEDBACK_FINDINGS_REL,
        round_dir=round_dir,
        case_id=CASE_ID,
        round_id=ROUND_ID,
    )

    assert any("raw opponent-report text field is not allowed" in error for error in errors)


def test_current_case_only_permission_blocks_general_promotion(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    write_json(
        round_dir / EXTERNAL_OPPONENT_REPORT_INTAKE_REL, intake_payload(round_dir, permission="current_case_only")
    )
    write_json(round_dir / EXTERNAL_OPPONENT_FEEDBACK_FINDINGS_REL, findings_payload(round_dir))
    payload = candidates_payload(round_dir)

    errors = validate_external_opponent_feedback_payload(
        payload,
        SUPERVISOR_LEARNING_CANDIDATES_REL,
        round_dir=round_dir,
        case_id=CASE_ID,
        round_id=ROUND_ID,
    )

    assert any("non-case-local promotion requires workflow_learning_permission allowed" in error for error in errors)


def test_require_analysis_fails_on_empty_round(tmp_path: Path) -> None:
    round_dir = tmp_path / "cases" / CASE_ID / "rounds" / ROUND_ID
    round_dir.mkdir(parents=True)

    errors = validate_external_opponent_feedback_round(
        round_dir,
        case_id=CASE_ID,
        round_id=ROUND_ID,
        require_analysis=True,
    )

    assert any("missing required external opponent-feedback analysis artifact" in error for error in errors)


def test_external_review_requires_required_check(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    write_valid_artifacts(round_dir)
    review_path = round_dir / EXTERNAL_OPPONENT_FEEDBACK_REVIEW_REL
    payload = json.loads(review_path.read_text(encoding="utf-8"))
    payload["checks_observed"] = []
    write_json(review_path, payload)

    errors = validate_external_opponent_feedback_round(
        round_dir,
        case_id=CASE_ID,
        round_id=ROUND_ID,
        require_analysis=True,
    )

    assert any("missing required observed check: check-external-opponent-feedback" in error for error in errors)


def test_cli_requires_intake_for_raw_external_report_source(tmp_path: Path, monkeypatch, capsys) -> None:
    round_dir = make_round(tmp_path)
    monkeypatch.setattr(check_external_opponent_feedback, "repo_root", lambda: tmp_path)

    result = check_external_opponent_feedback.main([CASE_ID, ROUND_ID])
    captured = capsys.readouterr()

    assert result == 1
    assert "missing required external opponent-report intake artifact" in captured.err
    assert str(round_dir) not in captured.err
