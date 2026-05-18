import json
from pathlib import Path

from thesis_review_workflow.artifact_validation import sha256_file
from thesis_review_workflow.review_delta import (
    REVIEW_DELTA_SCHEMA,
    build_review_delta_payload,
    review_delta_closeout_errors,
    review_delta_record_rel,
    validate_review_delta_record,
)


def assert_value_error_contains(expected: str, func, *args, **kwargs) -> None:
    try:
        func(*args, **kwargs)
    except ValueError as exc:
        assert expected in str(exc)
    else:
        raise AssertionError(f"expected ValueError containing {expected!r}")


def make_round(tmp_path: Path, *, current_text: str = "# Feedback\n\nCurrent.\n") -> Path:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    previous = round_dir / "work" / "review_deltas" / "before.md"
    current = round_dir / "outputs" / "feedback_student.md"
    previous.parent.mkdir(parents=True)
    current.parent.mkdir(parents=True)
    previous.write_text("# Feedback\n\nPrevious.\n", encoding="utf-8")
    current.write_text(current_text, encoding="utf-8")
    return round_dir


def write_approval(round_dir: Path, *, timestamp: str) -> None:
    current = round_dir / "outputs" / "feedback_student.md"
    approval = {
        "reviewed_artifact_path": "outputs/feedback_student.md",
        "reviewed_artifact_sha256": sha256_file(current),
        "timestamp": timestamp,
    }
    path = round_dir / "work" / "reviews" / "supervisor_feedback_review.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(approval, indent=2) + "\n", encoding="utf-8")


def test_material_delta_reopens_review_and_blocks_closeout_until_new_approval(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    write_approval(round_dir, timestamp="2026-05-15T10:00:00Z")

    payload = build_review_delta_payload(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_feedback",
        delta_type="material_claim_delta",
        previous_snapshot_rel="work/review_deltas/before.md",
        current_artifact_rel="outputs/feedback_student.md",
        generated_at="2026-05-15T12:00:00Z",
        rationale="Operator challenged a material claim after review.",
        affected_sections=["feedback.body"],
        approval_record_rel="work/reviews/supervisor_feedback_review.json",
    )
    record = round_dir / review_delta_record_rel("2026-05-15T12:00:00Z", "material_claim_delta")
    record.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    assert payload["schema_version"] == REVIEW_DELTA_SCHEMA
    assert payload["independent_review_reopened"] is True
    errors = review_delta_closeout_errors(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_feedback",
    )

    assert errors == [
        "work/review_deltas/2026-05-15T12-00-00Z-material_claim_delta.json: "
        "rerun profile independent review with `check-review-wave --workflow supervisor_feedback --wave final`, "
        "then `review-round-closeout --profile supervisor_feedback`"
    ]


def test_stale_approval_without_delta_blocks_closeout_with_delta_instruction(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    write_approval(round_dir, timestamp="2026-05-15T10:00:00Z")
    (round_dir / "outputs" / "feedback_student.md").write_text("# Feedback\n\nEdited after review.\n", encoding="utf-8")

    errors = review_delta_closeout_errors(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_feedback",
    )

    assert errors == [
        "outputs/feedback_student.md: post-review artifact hash differs from "
        "work/reviews/supervisor_feedback_review.json; record the edit with "
        "`record-review-delta --profile supervisor_feedback` or rerun the independent review"
    ]


def test_non_material_delta_requires_current_approval_or_typed_exception(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)

    assert_value_error_contains(
        "non-material delta requires current approval record or typed exception",
        build_review_delta_payload,
        round_dir,
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_feedback",
        delta_type="style_only",
        previous_snapshot_rel="work/review_deltas/before.md",
        current_artifact_rel="outputs/feedback_student.md",
        generated_at="2026-05-15T12:00:00Z",
        rationale="Whitespace-only correction.",
        affected_sections=["feedback.body"],
    )

    payload = build_review_delta_payload(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_feedback",
        delta_type="style_only",
        previous_snapshot_rel="work/review_deltas/before.md",
        current_artifact_rel="outputs/feedback_student.md",
        generated_at="2026-05-15T12:00:00Z",
        rationale="Whitespace-only correction.",
        affected_sections=["feedback.body"],
        typed_exception_type="style_only_no_visible_change",
        typed_exception_rationale="No approval record is needed for this smoke-scale fixture.",
        approved_by="operator",
    )

    assert payload["independent_review_reopened"] is False
    assert payload["typed_exception"]["type"] == "style_only_no_visible_change"


def test_general_workflow_lesson_requires_durable_promotion_target(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)

    assert_value_error_contains(
        "general_workflow_lesson requires a durable promotion_target",
        build_review_delta_payload,
        round_dir,
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_feedback",
        delta_type="general_workflow_lesson",
        previous_snapshot_rel="work/review_deltas/before.md",
        current_artifact_rel="outputs/feedback_student.md",
        generated_at="2026-05-15T12:00:00Z",
        rationale="Promote this review lesson.",
        affected_sections=["feedback.body"],
    )

    assert_value_error_contains(
        "general_workflow_lesson requires a durable promotion_target",
        build_review_delta_payload,
        round_dir,
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_feedback",
        delta_type="general_workflow_lesson",
        previous_snapshot_rel="work/review_deltas/before.md",
        current_artifact_rel="outputs/feedback_student.md",
        generated_at="2026-05-15T12:00:00Z",
        rationale="Promote this review lesson.",
        affected_sections=["feedback.body"],
        promotion_target="WORKFLOW_MEMORY.md",
    )

    payload = build_review_delta_payload(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_feedback",
        delta_type="general_workflow_lesson",
        previous_snapshot_rel="work/review_deltas/before.md",
        current_artifact_rel="outputs/feedback_student.md",
        generated_at="2026-05-15T12:00:00Z",
        rationale="Promote this review lesson.",
        affected_sections=["feedback.body"],
        promotion_target="TODO.md",
    )

    assert payload["promotion_target"] == "TODO.md"
    assert payload["independent_review_reopened"] is True


def test_evidence_challenge_requires_safe_evidence_anchor(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)

    assert_value_error_contains(
        "evidence_challenge requires at least one evidence_ref",
        build_review_delta_payload,
        round_dir,
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_feedback",
        delta_type="evidence_challenge",
        previous_snapshot_rel="work/review_deltas/before.md",
        current_artifact_rel="outputs/feedback_student.md",
        generated_at="2026-05-15T12:00:00Z",
        rationale="Operator challenged an evidence-backed claim.",
        affected_sections=["feedback.body"],
    )

    assert_value_error_contains(
        "evidence_refs must contain only safe round-relative paths",
        build_review_delta_payload,
        round_dir,
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_feedback",
        delta_type="evidence_challenge",
        previous_snapshot_rel="work/review_deltas/before.md",
        current_artifact_rel="outputs/feedback_student.md",
        generated_at="2026-05-15T12:00:00Z",
        rationale="Operator challenged an evidence-backed claim.",
        affected_sections=["feedback.body"],
        evidence_refs=["../private-note.md"],
    )

    evidence = round_dir / "work" / "evidence" / "claim.md"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text("Claim evidence.\n", encoding="utf-8")
    payload = build_review_delta_payload(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_feedback",
        delta_type="evidence_challenge",
        previous_snapshot_rel="work/review_deltas/before.md",
        current_artifact_rel="outputs/feedback_student.md",
        generated_at="2026-05-15T12:00:00Z",
        rationale="Operator challenged an evidence-backed claim.",
        affected_sections=["feedback.body"],
        evidence_refs=["work/evidence/claim.md"],
    )

    assert payload["evidence_refs"] == ["work/evidence/claim.md"]
    assert payload["independent_review_reopened"] is True


def test_review_delta_validates_canonical_closeout_guidance(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    payload = build_review_delta_payload(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_feedback",
        delta_type="style_only",
        previous_snapshot_rel="work/review_deltas/before.md",
        current_artifact_rel="outputs/feedback_student.md",
        generated_at="2026-05-15T12:00:00Z",
        rationale="Whitespace-only correction.",
        affected_sections=["feedback.body"],
        typed_exception_type="style_only_no_visible_change",
        typed_exception_rationale="No approval record is needed for this smoke-scale fixture.",
        approved_by="operator",
    )

    tampered_gates = dict(payload)
    tampered_gates["closeout_gates_to_rerun"] = ["wrong-gate"]
    assert validate_review_delta_record(tampered_gates, round_dir=round_dir) == [
        "review delta: closeout_gates_to_rerun must match canonical profile delta gates"
    ]

    tampered_action = dict(payload)
    tampered_action["next_action"] = "do something else"
    assert validate_review_delta_record(tampered_action, round_dir=round_dir) == [
        "review delta: next_action must match canonical profile delta action"
    ]
