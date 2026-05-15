from __future__ import annotations

from thesis_review_workflow import review_approvals, review_materiality, review_profiles, review_wave_gate
from thesis_review_workflow.review_pipeline_orchestration import (
    REVIEW_RUN_TRACE_REL,
    REVIEW_RUN_TRACE_SCHEMA,
    ReviewRunTraceEvent,
    build_review_run_trace_payload,
    trace_profile_summary,
    validate_review_run_trace_payload,
)


def test_workflow_profile_registry_shape_and_approval_names() -> None:
    errors = review_profiles.validate_workflow_profile_registry()
    assert errors == []

    profiles = review_profiles.profiles_by_id()
    assert profiles["supervisor_feedback"].approval_record == "work/reviews/supervisor_feedback_review.json"
    assert profiles["supervisor_feedback"].final_artifact == "outputs/feedback_student.md"
    assert profiles["supervisor_feedback"].workflow_profile == "supervisor_feedback"
    assert profiles["supervisor_feedback"].effective_materiality_profile == "supervisor_feedback"


def test_workflow_profiles_do_not_extend_materiality_with_operator_surfaces() -> None:
    profiles = review_profiles.profiles_by_id()
    assert profiles["opponent_materials"].workflow_profile == "opponent_review"
    assert profiles["opponent_materials"].operator_surface == "opponent_materials"
    assert profiles["opponent_materials"].effective_materiality_profile == "opponent_review"
    assert profiles["opponent_materials"].effective_wave_workflow == "opponent_materials"
    assert "opponent_materials" not in review_materiality.WORKFLOW_PROFILES
    assert profiles["opponent_materials"].effective_materiality_profile in review_materiality.WORKFLOW_PROFILES


def test_workflow_profiles_preserve_code_bearing_role_contract() -> None:
    for profile in review_profiles.workflow_review_profiles():
        if profile.profile_id in {"supervisor_feedback", "supervisor_report", "opponent_review", "opponent_materials"}:
            assert profile.code_bearing_roles == ("code_consistency", "code_quality")


def test_workflow_profiles_align_with_approval_wave_and_materiality_registries() -> None:
    wave_by_profile = {
        "supervisor_feedback": ("supervisor_feedback", "final"),
        "supervisor_report": ("supervisor_report", "final"),
        "opponent_review": ("opponent_materials", "reviewed"),
        "opponent_materials": ("opponent_materials", "reviewed"),
        "opponent_report_review": ("opponent_report_review", "final"),
    }

    for profile in review_profiles.workflow_review_profiles():
        approval_profile = review_approvals.canonical_profile_for_artifact(profile.final_artifact)
        assert approval_profile is not None
        assert approval_profile.approval_path == profile.approval_record
        assert approval_profile.workflow_profile == profile.workflow_profile
        assert profile.effective_materiality_profile in review_materiality.WORKFLOW_PROFILES

        wave_profile, wave = wave_by_profile[profile.profile_id]
        wave_spec = review_wave_gate.builtin_wave_spec(wave_profile, wave)
        assert wave_spec.outputs[0].approval_record is not None
        assert wave_spec.outputs[0].approval_record.path == profile.approval_record


def test_trace_payload_is_profile_bound_and_path_oriented() -> None:
    payload = build_review_run_trace_payload(
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_feedback",
        generated_at="2026-05-15T12:00:00Z",
        events=(
            ReviewRunTraceEvent(
                phase="start",
                status="passed",
                command="review-round-start --profile supervisor_feedback case-a round-a",
                source_refs=("inputs/thesis.pdf",),
                output_refs=("work/review_run_trace.json",),
                source_sha256=(("inputs/thesis.pdf", "a" * 64),),
                output_sha256=(("work/review_run_trace.json", "b" * 64),),
            ),
        ),
    )

    assert payload["schema_version"] == REVIEW_RUN_TRACE_SCHEMA
    assert payload["trace_path"] == REVIEW_RUN_TRACE_REL
    assert payload["workflow_profile"] == "supervisor_feedback"
    assert payload["materiality_profile"] == "supervisor_feedback"
    assert validate_review_run_trace_payload(payload) == []


def test_trace_payload_rejects_private_or_absolute_paths() -> None:
    payload = {
        "schema_version": REVIEW_RUN_TRACE_SCHEMA,
        "case_id": "case-a",
        "round_id": "round-a",
        "profile_id": "supervisor_feedback",
        "workflow_profile": "supervisor_feedback",
        "materiality_profile": "supervisor_feedback",
        "operator_surface": "supervisor_feedback",
        "generated_at": "2026-05-15T12:00:00Z",
        "trace_path": REVIEW_RUN_TRACE_REL,
        "events": [
            {
                "phase": "import",
                "status": "blocked",
                "source_refs": ["/tmp/private.pdf", "../outside.zip"],
                "output_refs": ["work/review_run_trace.json"],
                "source_sha256": {"/tmp/private.pdf": "a" * 64},
                "output_sha256": {},
            }
        ],
    }

    errors = validate_review_run_trace_payload(payload)
    assert any("source_refs[1] must be a safe round-relative path" in error for error in errors)
    assert any("source_refs[2] must be a safe round-relative path" in error for error in errors)
    assert any("source_sha256 path must be a safe round-relative path" in error for error in errors)


def test_trace_profile_summary_distinguishes_surface_from_agent_profiles() -> None:
    summary = trace_profile_summary("opponent_materials")

    assert summary == {
        "profile_id": "opponent_materials",
        "workflow_profile": "opponent_review",
        "materiality_profile": "opponent_review",
        "operator_surface": "opponent_materials",
        "final_artifact": "outputs/oponent_podklady_revidovane.md",
        "approval_record": "work/reviews/opponent_materials_review.json",
        "wave_workflow": "opponent_materials",
    }


def test_unknown_workflow_profile_is_rejected() -> None:
    try:
        review_profiles.get_workflow_review_profile("legacy")
    except ValueError as exc:
        assert "unknown workflow review profile" in str(exc)
    else:
        raise AssertionError("unknown workflow review profile was accepted")
