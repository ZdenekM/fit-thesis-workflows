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

    assert_value_error_contains(
        "classification_reason is required when governance fields are present",
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
        promotion_target="TODO.md",
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
        classification_reason="General workflow lesson belongs in the durable TODO index.",
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


def test_review_delta_rejects_current_artifact_as_delta_evidence(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)

    assert_value_error_contains(
        "evidence_refs must not cite the current artifact being updated",
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
        evidence_refs=["outputs/feedback_student.md"],
    )


def test_review_delta_rejects_append_only_operator_note_evidence_refs(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    note = round_dir / "notes" / "opponent-report-operator-feedback.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text("Append-only operator note.\n", encoding="utf-8")

    assert_value_error_contains(
        "evidence_refs must not hash append-only operator notes directly",
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
        evidence_refs=["notes/opponent-report-operator-feedback.md"],
    )


def test_review_delta_validation_rejects_self_source_ref(tmp_path: Path) -> None:
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
    record_rel = review_delta_record_rel("2026-05-15T12:00:00Z", "style_only")
    payload["source_refs"].append(record_rel)
    payload["source_sha256"][record_rel] = "0" * 64

    errors = validate_review_delta_record(payload, round_dir=round_dir, rel_path=record_rel)

    assert any("source_refs must not cite the review delta record itself" in error for error in errors)


def test_review_delta_validation_rejects_append_only_operator_note_source_ref(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    note = round_dir / "notes" / "opponent-report-operator-feedback.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text("Append-only operator note.\n", encoding="utf-8")
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
    payload["source_refs"].append("notes/opponent-report-operator-feedback.md")
    payload["source_sha256"]["notes/opponent-report-operator-feedback.md"] = sha256_file(note)

    errors = validate_review_delta_record(
        payload,
        round_dir=round_dir,
        rel_path=review_delta_record_rel("2026-05-15T12:00:00Z", "style_only"),
    )

    assert any("source_refs must not hash append-only operator notes directly" in error for error in errors)


def test_review_delta_validation_rejects_record_to_record_source_cycle(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    first_rel = review_delta_record_rel("2026-05-15T12:00:00Z", "style_only")
    second_rel = review_delta_record_rel("2026-05-15T12:05:00Z", "style_only")
    first = build_review_delta_payload(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_feedback",
        delta_type="style_only",
        previous_snapshot_rel="work/review_deltas/before.md",
        current_artifact_rel="outputs/feedback_student.md",
        generated_at="2026-05-15T12:00:00Z",
        rationale="First style-only correction.",
        affected_sections=["feedback.body"],
        typed_exception_type="style_only_no_visible_change",
        typed_exception_rationale="No approval record is needed for this smoke-scale fixture.",
        approved_by="operator",
    )
    first_path = round_dir / first_rel
    first_path.write_text(json.dumps(first, indent=2) + "\n", encoding="utf-8")
    second = build_review_delta_payload(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_feedback",
        delta_type="style_only",
        previous_snapshot_rel="work/review_deltas/before.md",
        current_artifact_rel="outputs/feedback_student.md",
        generated_at="2026-05-15T12:05:00Z",
        rationale="Second style-only correction.",
        affected_sections=["feedback.body"],
        typed_exception_type="style_only_no_visible_change",
        typed_exception_rationale="No approval record is needed for this smoke-scale fixture.",
        approved_by="operator",
    )
    second["source_refs"].append(first_rel)
    second["source_sha256"][first_rel] = sha256_file(first_path)
    second_path = round_dir / second_rel
    second_path.write_text(json.dumps(second, indent=2) + "\n", encoding="utf-8")
    first["source_refs"].append(second_rel)
    first["source_sha256"][second_rel] = sha256_file(second_path)
    first_path.write_text(json.dumps(first, indent=2) + "\n", encoding="utf-8")

    errors = validate_review_delta_record(first, round_dir=round_dir, rel_path=first_rel)

    assert any("source_refs create review-delta provenance cycle" in error for error in errors)


def test_governance_fields_are_structural_and_hash_bound(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    proposal = round_dir / "work" / "profile_proposals" / "local-default.md"
    proposal.parent.mkdir(parents=True, exist_ok=True)
    proposal.write_text("Redacted preference proposal.\n", encoding="utf-8")

    assert_value_error_contains(
        "promotion_target must be a durable promotion target",
        build_review_delta_payload,
        round_dir,
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_feedback",
        delta_type="operator_preference",
        previous_snapshot_rel="work/review_deltas/before.md",
        current_artifact_rel="outputs/feedback_student.md",
        generated_at="2026-05-15T12:00:00Z",
        rationale="Operator preference should calibrate a private profile.",
        affected_sections=["feedback.body"],
        typed_exception_type="operator_explicit_exception",
        typed_exception_rationale="Operator accepted this bounded preference delta.",
        approved_by="operator",
        promotion_target="private-reviewer-profile:../secret",
        classification_reason="Rejected unsafe private-profile destination.",
        privacy_review="private_profile_not_copied",
    )

    assert_value_error_contains(
        "profile_proposal_ref requires a private-profile privacy_review",
        build_review_delta_payload,
        round_dir,
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_feedback",
        delta_type="operator_preference",
        previous_snapshot_rel="work/review_deltas/before.md",
        current_artifact_rel="outputs/feedback_student.md",
        generated_at="2026-05-15T12:00:00Z",
        rationale="Operator preference should calibrate a private profile.",
        affected_sections=["feedback.body"],
        typed_exception_type="operator_explicit_exception",
        typed_exception_rationale="Operator accepted this bounded preference delta.",
        approved_by="operator",
        profile_proposal_ref="work/profile_proposals/local-default.md",
        classification_reason="Redacted proposal stays in the ignored round workspace.",
    )

    assert_value_error_contains(
        "private reviewer profile promotion requires a private-profile privacy_review",
        build_review_delta_payload,
        round_dir,
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_feedback",
        delta_type="operator_preference",
        previous_snapshot_rel="work/review_deltas/before.md",
        current_artifact_rel="outputs/feedback_student.md",
        generated_at="2026-05-15T12:00:00Z",
        rationale="Operator preference should calibrate a private profile.",
        affected_sections=["feedback.body"],
        typed_exception_type="operator_explicit_exception",
        typed_exception_rationale="Operator accepted this bounded preference delta.",
        approved_by="operator",
        promotion_target="private-reviewer-profile:local/default",
        classification_reason="Private profile target cannot be classified as tracked workflow only.",
        privacy_review="tracked_workflow_only",
    )

    payload = build_review_delta_payload(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_feedback",
        delta_type="operator_preference",
        previous_snapshot_rel="work/review_deltas/before.md",
        current_artifact_rel="outputs/feedback_student.md",
        generated_at="2026-05-15T12:00:00Z",
        rationale="Operator preference should calibrate a private profile.",
        affected_sections=["feedback.body"],
        typed_exception_type="operator_explicit_exception",
        typed_exception_rationale="Operator accepted this bounded preference delta.",
        approved_by="operator",
        promotion_target="private-reviewer-profile:local/default",
        classification_reason="Durable personal preference belongs in a private profile, not tracked docs.",
        rejected_targets=["docs/workflow-command-surface.md"],
        privacy_review="redacted_promotion_candidate_only",
        profile_proposal_ref="work/profile_proposals/local-default.md",
    )

    assert payload["promotion_target"] == "private-reviewer-profile:local/default"
    assert (
        payload["classification_reason"]
        == "Durable personal preference belongs in a private profile, not tracked docs."
    )
    assert payload["rejected_targets"] == ["docs/workflow-command-surface.md"]
    assert payload["privacy_review"] == "redacted_promotion_candidate_only"
    assert payload["profile_proposal_sha256"] == {"work/profile_proposals/local-default.md": sha256_file(proposal)}


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
