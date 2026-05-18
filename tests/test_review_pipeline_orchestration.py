from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from thesis_review_workflow import review_approvals, review_materiality, review_profiles, review_wave_gate
from thesis_review_workflow.cli import prepare_review_round, review_round_start
from thesis_review_workflow.review_pipeline_orchestration import (
    REVIEW_ROLE_PLAN_REL,
    REVIEW_ROLE_PLAN_SCHEMA,
    REVIEW_RUN_TRACE_REL,
    REVIEW_RUN_TRACE_SCHEMA,
    ROUND_START_NEXT_COMMAND,
    ReviewRunTraceEvent,
    RoundMaterialDescriptor,
    RoundStartAction,
    advisory_static_analysis_state,
    artifact_next_action_state,
    build_review_role_plan_payload,
    build_review_run_trace_payload,
    closeout_wave_for_profile,
    coverage_role_for_packet_role,
    normalize_metadata_fields,
    plan_review_round_start,
    trace_profile_summary,
    validate_review_role_plan_payload,
    validate_review_run_trace_payload,
    validate_role_plan_for_closeout,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


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


def test_prepare_review_round_skips_legacy_round_ready_for_opponent_report_review() -> None:
    args = argparse.Namespace(
        skip_ready_check=False,
        skip_materiality_check=False,
        agents_authorized=False,
        authorization_note="authorized",
    )

    command = prepare_review_round.packet_command_args(
        args,
        profile_id="opponent_report_review",
        case_id="case-a",
        round_id="round-a",
    )

    assert command == ["prepare-opponent-packets", "case-a", "round-a", "--skip-ready-check"]


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


def test_round_start_planner_accepts_explicit_current_materials_and_stops_at_prepare_boundary() -> None:
    plan = plan_review_round_start(
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_feedback",
        fresh_materials_expected=True,
        materials=(
            RoundMaterialDescriptor("thesis_pdf", path="inputs/thesis.pdf", currentness="newer_than_previous"),
            RoundMaterialDescriptor("code_archive", path="inputs/code.zip", currentness="current"),
        ),
    )

    assert plan.ok
    assert plan.next_command == ROUND_START_NEXT_COMMAND
    assert plan.readiness_gates == ("check-supervisor-ready",)
    assert [action.action_id for action in plan.actions] == [
        "extract_pdf_text",
        "prepare_code_workspace",
        "update_current_evidence",
        "update_reuse_index",
        "run_readiness_gate",
        "prepare_role_plan",
    ]
    assert plan.actions[-1].command == "prepare-review-round <case-id> <round-id>"


def test_round_start_planner_blocks_when_fresh_materials_are_expected_but_only_stale_exist() -> None:
    plan = plan_review_round_start(
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_feedback",
        fresh_materials_expected=True,
        materials=(RoundMaterialDescriptor("thesis_pdf", path="inputs/thesis.pdf", currentness="stale"),),
    )

    assert not plan.ok
    assert plan.blockers[0].code == "fresh_materials_missing"
    assert plan.actions == ()


def test_round_start_planner_allows_typed_provisional_stale_review() -> None:
    plan = plan_review_round_start(
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_feedback",
        fresh_materials_expected=True,
        provisional_stale_review=True,
        materials=(RoundMaterialDescriptor("thesis_pdf", path="inputs/thesis.pdf", currentness="stale"),),
    )

    assert plan.ok
    assert any(diagnostic.code == "provisional_stale_review" for diagnostic in plan.diagnostics)
    assert any(action.action_id == "extract_pdf_text" for action in plan.actions)


def test_round_start_profile_gate_selection_is_profile_specific() -> None:
    expected = {
        "supervisor_feedback": ("check-supervisor-ready",),
        "supervisor_report": ("check-supervisor-report-ready",),
        "opponent_review": ("check-round-ready",),
        "opponent_materials": ("check-round-ready",),
        "opponent_report_review": (
            "check-opponent-report --mode canonical",
            "check-opponent-report --mode clean --path outputs/oponent_posudek_navrh.md",
        ),
    }

    for profile_id, gates in expected.items():
        plan = plan_review_round_start(
            case_id="case-a",
            round_id="round-a",
            profile_id=profile_id,
            materials=(RoundMaterialDescriptor("thesis_pdf", path="inputs/thesis.pdf"),),
        )
        assert plan.readiness_gates == gates
        assert [action.command for action in plan.actions if action.action_id == "run_readiness_gate"] == [
            f"{gate} <case-id> <round-id>" for gate in gates
        ]


def test_review_round_start_executes_option_bearing_readiness_gate(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[str, list[str]]] = []

    def fake_run_workflow_step(root: Path, label: str, args: list[str]) -> review_round_start.ExecutedAction:
        calls.append((label, args))
        return review_round_start.ExecutedAction("passed", " ".join(args), ())

    monkeypatch.setattr(review_round_start, "run_workflow_step", fake_run_workflow_step)
    action = RoundStartAction(
        "run_readiness_gate",
        "check-opponent-report --mode clean --path outputs/oponent_posudek_navrh.md <case-id> <round-id>",
        "profile readiness must pass before role-plan preparation",
        (),
        (),
    )

    result = review_round_start.execute_action(
        root=tmp_path,
        round_dir=tmp_path / "cases" / "case-a" / "rounds" / "round-a",
        case_id="case-a",
        round_id="round-a",
        action=action,
        materials=(),
    )

    assert result.status == "passed"
    assert calls == [
        (
            "Readiness gate: check-opponent-report",
            [
                "check-opponent-report",
                "--mode",
                "clean",
                "--path",
                "outputs/oponent_posudek_navrh.md",
                "case-a",
                "round-a",
            ],
        )
    ]


def test_round_start_planner_adds_supervisor_report_required_note_action() -> None:
    plan = plan_review_round_start(
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_report",
        materials=(RoundMaterialDescriptor("thesis_pdf", path="inputs/thesis.pdf"),),
    )

    assert any(
        action.action_id == "ensure_profile_note"
        and action.target_refs == ("notes/supervisor-report-operator-input.md",)
        for action in plan.actions
    )


def test_round_start_planner_classifies_parent_submission_bundles_without_code_discovery() -> None:
    plan = plan_review_round_start(
        case_id="case-a",
        round_id="round-a",
        profile_id="opponent_materials",
        materials=(
            RoundMaterialDescriptor(
                "submission_bundle",
                path="inputs/submission.zip",
                bundle_classification="container_bundle",
                decomposed_authoritative_refs=("inputs/thesis.pdf", "inputs/code.zip"),
            ),
            RoundMaterialDescriptor("code_archive", path="inputs/code.zip"),
        ),
    )

    assert plan.workflow_profile == "opponent_review"
    assert plan.materiality_profile == "opponent_review"
    assert plan.actions[0].action_id == "classify_bundle"
    assert plan.actions[0].material_refs == ("inputs/submission.zip",)
    assert plan.actions[0].target_refs == ("inputs/thesis.pdf", "inputs/code.zip")
    assert [action.action_id for action in plan.actions].count("prepare_code_workspace") == 1


def test_round_start_planner_rejects_unsafe_material_paths() -> None:
    plan = plan_review_round_start(
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_feedback",
        materials=(RoundMaterialDescriptor("thesis_pdf", path="../private.pdf"),),
    )

    assert not plan.ok
    assert any("path must be a safe round-relative path" in blocker.message for blocker in plan.blockers)


def test_metadata_newline_diagnostics_are_explicit_and_structural() -> None:
    normalized, diagnostics = normalize_metadata_fields(
        {"assignment_summary": "First line\\nSecond line", "short_note": "plain"}
    )

    assert normalized["assignment_summary"] == "First line\nSecond line"
    assert normalized["short_note"] == "plain"
    assert diagnostics[0].code == "literal_escaped_newline"


def test_review_role_plan_projects_packet_activation_and_code_contract(tmp_path: Path) -> None:
    round_dir = tmp_path / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "work").mkdir(parents=True)
    (round_dir / "inputs").mkdir()
    (round_dir / "outputs").mkdir()
    (round_dir / "work" / "code_workspace.md").write_text("Prepared code root.\n", encoding="utf-8")

    payload = build_review_role_plan_payload(
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_feedback",
        generated_at="2026-05-15T12:00:00Z",
        round_dir=round_dir,
    )

    roles = {item["role"]: item for item in payload["role_states"]}
    assert payload["schema_version"] == REVIEW_ROLE_PLAN_SCHEMA
    assert payload["role_plan_path"] == REVIEW_ROLE_PLAN_REL
    assert payload["packet_command"] == "prepare-supervisor-packets"
    assert roles["code_consistency"]["state"] == "required_fresh"
    assert roles["code_quality"]["state"] == "required_fresh"
    assert roles["figure_media"]["state"] == "not_material"
    assert roles["figure_media"]["packet_status"] == "not_generated_not_material"
    assert payload["code_bearing_contract"]["status"] == "satisfied"
    assert payload["code_bearing_contract"]["required_roles"] == ["code_consistency", "code_quality"]
    assert all(len(wave["roles"]) <= 2 for wave in payload["wave_schedule"])
    assert validate_review_role_plan_payload(payload, round_dir=round_dir) == []


def test_role_plan_uses_canonical_agent_coverage_roles_for_review_packets() -> None:
    from thesis_review_workflow import opponent_packets, supervisor_packets, supervisor_report_packets

    supervisor_profile = review_profiles.get_workflow_review_profile("supervisor_feedback")
    supervisor_final = next(role for role in supervisor_packets.PACKET_ROLES if role.key == "final_review")
    report_profile = review_profiles.get_workflow_review_profile("supervisor_report")
    report_final = next(role for role in supervisor_report_packets.PACKET_ROLES if role.key == "report_review")
    opponent_profile = review_profiles.get_workflow_review_profile("opponent_materials")
    materials_review = next(role for role in opponent_packets.PACKET_ROLES if role.key == "materials_review")

    assert coverage_role_for_packet_role(supervisor_profile, supervisor_final) == "supervisor_feedback_review"
    assert coverage_role_for_packet_role(report_profile, report_final) == "supervisor_report_review"
    assert coverage_role_for_packet_role(opponent_profile, materials_review) == "opponent_materials_review"


def minimal_closeout_role_plan(*, state: str = "required_fresh") -> dict[str, object]:
    return {
        "schema_version": REVIEW_ROLE_PLAN_SCHEMA,
        "case_id": "case-a",
        "round_id": "round-a",
        "profile_id": "supervisor_feedback",
        "workflow_profile": "supervisor_feedback",
        "materiality_profile": "supervisor_feedback",
        "operator_surface": "supervisor_feedback",
        "final_artifact": "outputs/feedback_student.md",
        "approval_record": "work/reviews/supervisor_feedback_review.json",
        "generated_at": "2026-05-15T12:00:00Z",
        "role_plan_path": REVIEW_ROLE_PLAN_REL,
        "packet_command": "prepare-supervisor-packets",
        "packet_dir": "work/supervisor_packets",
        "common_briefing": "work/common_briefing.json",
        "source_contracts": [],
        "role_states": [
            {
                "role": "final_review",
                "coverage_role": "supervisor_feedback_review",
                "title": "Final review",
                "skill": "thesis-supervisor-feedback-review",
                "state": state,
                "activation": "final review",
                "expected_output": "outputs/feedback_student.md",
                "registration_preset": "outputs/feedback_student.md",
                "packet_path": "work/supervisor_packets/final_review.md",
            }
        ],
        "wave_schedule": [],
        "code_bearing_contract": {"status": "satisfied"},
    }


def test_role_plan_closeout_requires_output_for_required_roles(tmp_path: Path) -> None:
    round_dir = tmp_path / "cases" / "case-a" / "rounds" / "round-a"
    payload = minimal_closeout_role_plan()

    errors = validate_role_plan_for_closeout(
        payload,
        round_dir=round_dir,
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_feedback",
    )

    assert any("final_review: role plan state required_fresh requires current output" in error for error in errors)

    output = round_dir / "outputs" / "feedback_student.md"
    output.parent.mkdir(parents=True)
    output.write_text("# Feedback\n", encoding="utf-8")

    errors = validate_role_plan_for_closeout(
        payload,
        round_dir=round_dir,
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_feedback",
    )

    assert any("final_review: role plan state required_fresh requires current output" in error for error in errors)

    manifest = round_dir / "work" / "review_manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "review-manifest-v1",
                "case_id": "case-a",
                "round_id": "round-a",
                "supporting_work_artifacts": [],
                "artifacts": [
                    {
                        "path": "outputs/feedback_student.md",
                        "artifact_sha256": review_materiality.sha256_file(output),
                        "generated_by": [{"role": "thesis-supervisor-feedback", "agent": "generator-a"}],
                        "independent_review": {
                            "status": "reviewed",
                            "reviewer_role": "thesis-supervisor-feedback-review",
                            "reviewer_agent": "reviewer-a",
                            "reviewed_hash": review_materiality.sha256_file(output),
                        },
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    errors = validate_role_plan_for_closeout(
        payload,
        round_dir=round_dir,
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_feedback",
    )

    assert errors == []


def test_role_plan_closeout_reusable_current_requires_coverage_record(tmp_path: Path) -> None:
    round_dir = tmp_path / "cases" / "case-a" / "rounds" / "round-a"
    payload = minimal_closeout_role_plan(state="reusable_current")

    errors = validate_role_plan_for_closeout(
        payload,
        round_dir=round_dir,
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_feedback",
    )

    assert errors == ["final_review: reusable_current requires current reviewed coverage in work/agent_coverage.json"]

    coverage = round_dir / "work" / "agent_coverage.json"
    coverage.parent.mkdir(parents=True)
    coverage.write_text(
        json.dumps(
            {
                "schema_version": "agent-coverage-v1",
                "case_id": "case-a",
                "round_id": "round-a",
                "coverage_path": "work/agent_coverage.json",
                "roles": [
                    {
                        "role": "supervisor_feedback_review",
                        "status": "required",
                        "coverage_satisfied_by": "current_reviewed_artifact",
                        "fresh_review_required": False,
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert (
        validate_role_plan_for_closeout(
            payload,
            round_dir=round_dir,
            case_id="case-a",
            round_id="round-a",
            profile_id="supervisor_feedback",
        )
        == []
    )


def test_role_plan_closeout_requires_registered_work_role_output(tmp_path: Path) -> None:
    round_dir = tmp_path / "cases" / "case-a" / "rounds" / "round-a"
    payload = minimal_closeout_role_plan()
    role = payload["role_states"][0]  # type: ignore[index]
    assert isinstance(role, dict)
    role.update(
        {
            "role": "text_assignment",
            "coverage_role": "text_assignment",
            "skill": "thesis-text-reviewer",
            "expected_output": "work/supervisor_packets/text_assignment_findings.md",
            "registration_preset": "work/supervisor_packets/text_assignment_findings.md",
            "packet_path": "work/supervisor_packets/text_assignment.md",
        }
    )
    output = round_dir / "work" / "supervisor_packets" / "text_assignment_findings.md"
    output.parent.mkdir(parents=True)
    output.write_text("# Findings\n", encoding="utf-8")

    errors = validate_role_plan_for_closeout(
        payload,
        round_dir=round_dir,
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_feedback",
    )

    assert any("text_assignment: role plan state required_fresh requires current output" in error for error in errors)

    manifest = round_dir / "work" / "review_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "review-manifest-v1",
                "case_id": "case-a",
                "round_id": "round-a",
                "supporting_work_artifacts": [
                    {
                        "path": "work/supervisor_packets/text_assignment_findings.md",
                        "artifact_sha256": review_materiality.sha256_file(output),
                        "generated_by": [{"role": "text_assignment", "agent": "text-agent"}],
                    }
                ],
                "artifacts": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert (
        validate_role_plan_for_closeout(
            payload,
            round_dir=round_dir,
            case_id="case-a",
            round_id="round-a",
            profile_id="supervisor_feedback",
        )
        == []
    )


def test_closeout_wave_maps_profile_operator_surfaces() -> None:
    assert closeout_wave_for_profile("supervisor_feedback") == ("supervisor_feedback", "final")
    assert closeout_wave_for_profile("supervisor_report") == ("supervisor_report", "final")
    assert closeout_wave_for_profile("opponent_materials") == ("opponent_materials", "reviewed")
    assert closeout_wave_for_profile("opponent_report_review") == ("opponent_report_review", "final")


def test_materiality_next_action_states_distinguish_present_artifact_gaps(tmp_path: Path) -> None:
    round_dir = tmp_path / "cases" / "case-a" / "rounds" / "round-a"
    output = round_dir / "outputs" / "theses_similarity_review.md"
    output.parent.mkdir(parents=True)
    output.write_text("# Review\n", encoding="utf-8")

    synthesis_state = artifact_next_action_state(
        round_dir,
        "outputs/theses_similarity_review.md",
        case_id="case-a",
        round_id="round-a",
        action={
            "reason": (
                "outputs/theses_similarity_review.md is present but not independently reviewed "
                "or covered by the current reviewed synthesis artifact."
            )
        },
    )
    standalone_state = artifact_next_action_state(
        round_dir,
        "outputs/theses_similarity_review.md",
        case_id="case-a",
        round_id="round-a",
        action={"reason": "Artifact exists but still needs standalone independent review."},
    )

    assert synthesis_state == "present_but_not_synthesis_covered"
    assert standalone_state == "present_but_not_standalone_reviewed"


def test_review_role_plan_crosswalks_reuse_states(tmp_path: Path) -> None:
    round_dir = tmp_path / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "work" / "reuse").mkdir(parents=True)
    (round_dir / "work").mkdir(exist_ok=True)
    (round_dir / "work" / "review_materiality" / "supervisor_feedback").mkdir(parents=True)
    (round_dir / "work" / "code_workspace.md").write_text("Prepared code root.\n", encoding="utf-8")
    (round_dir / "work" / "agent_coverage.json").write_text(
        json.dumps(
            {
                "schema_version": "agent-coverage-v1",
                "case_id": "case-a",
                "round_id": "round-a",
                "updated_at": "2026-05-15T12:00:00Z",
                "coverage_path": "work/agent_coverage.json",
                "roles": [
                    {
                        "role": "code_consistency",
                        "status": "required",
                        "coverage_required": True,
                        "fresh_review_required": False,
                        "coverage_satisfied_by": "current_reviewed_artifact",
                        "reuse_status": "unchanged_reusable",
                        "reuse_next_action": "reuse_existing_review",
                    },
                    {
                        "role": "figure_media",
                        "status": "required",
                        "coverage_required": True,
                        "fresh_review_required": False,
                        "coverage_satisfied_by": "current_reviewed_artifact",
                        "reuse_status": "unchanged_reusable",
                        "reuse_next_action": "reuse_existing_review",
                    },
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (round_dir / "work" / "review_materiality" / "supervisor_feedback" / "figure_media.json").write_text(
        json.dumps(
            {
                "schema_version": "review-materiality-decision-v1",
                "case_id": "case-a",
                "round_id": "round-a",
                "workflow_profile": "supervisor_feedback",
                "role": "figure_media",
                "recommendation": "material",
                "coverage_required": True,
                "fresh_review_required": True,
                "coverage_satisfied_by": "fresh_role_review",
                "coverage_state": "fresh_review_required",
                "scope": "explicit_request",
                "impact": "material visual evidence exists",
                "reason": "operator requested figure/media review for this round",
                "generated_at": "2026-05-15T12:00:00Z",
                "producer_role": "test",
                "source_refs": ["operator-request:figure_media"],
                "source_sha256": {},
                "limitations": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (round_dir / "work" / "reuse" / "reuse_index.json").write_text(
        json.dumps(
            {
                "schema_version": "round-reuse-index-v1",
                "case_id": "case-a",
                "round_id": "round-a",
                "generated_at": "2026-05-15T12:00:00Z",
                "producer": "test",
                "current_source_fingerprints": [],
                "decisions": [
                    {
                        "artifact_role": "code_consistency",
                        "status": "unchanged_reusable",
                        "fresh_semantic_review_required": False,
                        "coverage_satisfied_by": "current_reviewed_artifact",
                        "next_action": "reuse_existing_review",
                        "candidate_round_id": "round-prior",
                        "candidate_artifacts": [
                            {
                                "path": "outputs/code_consistency.md",
                                "sha256": "a" * 64,
                                "review_current": True,
                            }
                        ],
                        "source_sha256": {"work/code_workspace.md": "b" * 64},
                        "unchanged_refs": ["work/code_workspace.md"],
                        "changed_refs": [],
                        "added_refs": [],
                        "removed_refs": [],
                        "missing_current_refs": [],
                        "not_comparable_refs": [],
                        "missing_current_source_classes": [],
                        "missing_prior_source_classes": [],
                        "reasons": ["role-relevant sources unchanged and reviewed coverage is current"],
                    },
                    {
                        "artifact_role": "code_quality",
                        "status": "changed_delta_required",
                        "fresh_semantic_review_required": True,
                        "coverage_satisfied_by": "fresh_role_review",
                        "next_action": "delta_review",
                        "source_sha256": {"work/code_workspace.md": "b" * 64},
                    },
                    {
                        "artifact_role": "figure_media",
                        "status": "unchanged_reusable",
                        "fresh_semantic_review_required": False,
                        "coverage_satisfied_by": "current_reviewed_artifact",
                        "next_action": "reuse_existing_review",
                        "candidate_round_id": "round-prior",
                        "candidate_artifacts": [
                            {
                                "path": "outputs/figure_media_review.md",
                                "sha256": "c" * 64,
                                "review_current": True,
                            }
                        ],
                        "source_sha256": {"work/media_presence_inventory.jsonl": "d" * 64},
                        "unchanged_refs": ["work/media_presence_inventory.jsonl"],
                        "changed_refs": [],
                        "added_refs": [],
                        "removed_refs": [],
                        "missing_current_refs": [],
                        "not_comparable_refs": [],
                        "missing_current_source_classes": [],
                        "missing_prior_source_classes": [],
                        "reasons": ["role-relevant sources unchanged and reviewed coverage is current"],
                    },
                ],
                "limitations": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = build_review_role_plan_payload(
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_feedback",
        generated_at="2026-05-15T12:00:00Z",
        round_dir=round_dir,
    )

    roles = {item["role"]: item for item in payload["role_states"]}
    assert roles["code_consistency"]["state"] == "reusable_current"
    assert roles["code_consistency"]["reuse_projection"]["artifact_role"] == "code_consistency"
    assert roles["code_consistency"]["reuse_projection"]["candidate_round_id"] == "round-prior"
    assert roles["code_consistency"]["reuse_projection"]["source_sha256"] == {"work/code_workspace.md": "b" * 64}
    assert roles["code_quality"]["state"] == "delta_review"
    assert roles["figure_media"]["state"] == "reusable_current"
    assert roles["figure_media"]["reuse_projection"]["artifact_role"] == "figure_media"
    assert roles["figure_media"]["reuse_projection"]["candidate_artifacts"] == [
        {"path": "outputs/figure_media_review.md", "sha256": "c" * 64, "review_current": True}
    ]
    scheduled_roles = {role for wave in payload["wave_schedule"] for role in wave["roles"]}
    assert "code_consistency" not in scheduled_roles
    assert "code_quality" in scheduled_roles
    assert "figure_media" not in scheduled_roles


def test_review_role_plan_does_not_skip_from_reuse_index_without_agent_coverage(tmp_path: Path) -> None:
    round_dir = tmp_path / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "work" / "reuse").mkdir(parents=True)
    (round_dir / "work" / "code_workspace.md").write_text("Prepared code root.\n", encoding="utf-8")
    (round_dir / "work" / "reuse" / "reuse_index.json").write_text(
        json.dumps(
            {
                "schema_version": "round-reuse-index-v1",
                "case_id": "case-a",
                "round_id": "round-a",
                "generated_at": "2026-05-15T12:00:00Z",
                "producer": "test",
                "current_source_fingerprints": [],
                "decisions": [
                    {
                        "artifact_role": "code_consistency",
                        "status": "unchanged_reusable",
                        "fresh_semantic_review_required": False,
                        "coverage_satisfied_by": "current_reviewed_artifact",
                        "next_action": "reuse_existing_review",
                        "source_sha256": {"work/code_workspace.md": "b" * 64},
                        "changed_refs": [],
                        "added_refs": [],
                        "removed_refs": [],
                        "missing_current_refs": [],
                        "not_comparable_refs": [],
                    }
                ],
                "limitations": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = build_review_role_plan_payload(
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_feedback",
        generated_at="2026-05-15T12:00:00Z",
        round_dir=round_dir,
    )

    roles = {item["role"]: item for item in payload["role_states"]}
    assert roles["code_consistency"]["reuse_projection"]["reuse_status"] == "unchanged_reusable"
    assert roles["code_consistency"]["agent_coverage_projection"]["status"] == "missing"
    assert roles["code_consistency"]["state"] == "required_fresh"
    scheduled_roles = {role for wave in payload["wave_schedule"] for role in wave["roles"]}
    assert "code_consistency" in scheduled_roles


def test_review_role_plan_does_not_treat_omen_unavailable_as_code_quality_role_block(tmp_path: Path) -> None:
    round_dir = tmp_path / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "work").mkdir(parents=True)
    (round_dir / "work" / "code_workspace.md").write_text("Prepared code root.\n", encoding="utf-8")
    (round_dir / "work" / "agent_coverage.json").write_text(
        json.dumps(
            {
                "schema_version": "agent-coverage-v1",
                "case_id": "case-a",
                "round_id": "round-a",
                "updated_at": "2026-05-15T12:00:00Z",
                "coverage_path": "work/agent_coverage.json",
                "roles": [
                    {
                        "role": "code_quality",
                        "status": "blocked",
                        "coverage_satisfied_by": "typed_limitation",
                        "fresh_review_required": False,
                        "typed_limitation": {
                            "role": "code_quality",
                            "type": "unavailable_tool",
                            "tool": "omen",
                            "description": "Omen was unavailable in the operator environment.",
                        },
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = build_review_role_plan_payload(
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_feedback",
        generated_at="2026-05-15T12:00:00Z",
        round_dir=round_dir,
    )

    roles = {item["role"]: item for item in payload["role_states"]}
    assert roles["code_quality"]["state"] == "required_fresh"
    scheduled_roles = {role for wave in payload["wave_schedule"] for role in wave["roles"]}
    assert "code_quality" in scheduled_roles
    assert payload["code_bearing_contract"]["status"] == "satisfied"


def test_review_role_plan_requires_explicit_omen_tool_for_optional_tool_block(tmp_path: Path) -> None:
    round_dir = tmp_path / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "work").mkdir(parents=True)
    (round_dir / "work" / "code_workspace.md").write_text("Prepared code root.\n", encoding="utf-8")
    (round_dir / "work" / "agent_coverage.json").write_text(
        json.dumps(
            {
                "schema_version": "agent-coverage-v1",
                "case_id": "case-a",
                "round_id": "round-a",
                "updated_at": "2026-05-15T12:00:00Z",
                "coverage_path": "work/agent_coverage.json",
                "roles": [
                    {
                        "role": "code_quality",
                        "status": "blocked",
                        "coverage_satisfied_by": "typed_limitation",
                        "fresh_review_required": False,
                        "typed_limitation": {
                            "role": "code_quality",
                            "type": "unavailable_tool",
                            "description": "Omen appears in notes, but the blocker is missing submitted code evidence.",
                        },
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = build_review_role_plan_payload(
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_feedback",
        generated_at="2026-05-15T12:00:00Z",
        round_dir=round_dir,
    )

    roles = {item["role"]: item for item in payload["role_states"]}
    assert roles["code_quality"]["state"] == "blocked_with_typed_limitation"
    scheduled_roles = {role for wave in payload["wave_schedule"] for role in wave["roles"]}
    assert "code_quality" not in scheduled_roles


def test_advisory_static_analysis_state_reports_mcp_path_failure(tmp_path: Path) -> None:
    round_dir = tmp_path / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "work" / "code").mkdir(parents=True)
    (round_dir / "work" / "code_quality_omen.json").write_text(
        json.dumps(
            {
                "schema_version": "code-quality-omen-v1",
                "case_id": "case-a",
                "round_id": "round-a",
                "generated_at": "2026-05-18T12:00:00Z",
                "tool": "omen",
                "status": "mcp_path_failure",
                "reason": "MCP returned zero files for a non-empty prepared code root.",
                "invocation": {
                    "surface": "mcp",
                    "command": ["mcp", "omen", "complexity", "work/code"],
                    "analyzed_root": "work/code",
                },
                "summary": {"total_files": 0, "total_functions": 0},
                "source_refs": ["work/code"],
                "non_empty_root_evidence": ["work/code"],
                "limitations": ["MCP path handling failed; use CLI or rerun from the prepared root."],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert advisory_static_analysis_state(round_dir) == {
        "tool": "omen",
        "state": "mcp_path_failure",
        "reason": "MCP returned zero files for a non-empty prepared code root.",
    }


def test_advisory_static_analysis_state_accepts_legacy_cli_json(tmp_path: Path) -> None:
    round_dir = tmp_path / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "work").mkdir(parents=True)
    (round_dir / "work" / "code_quality_omen.json").write_text(
        json.dumps({"files": [{"path": "app.py"}], "summary": {"total_files": 1, "total_functions": 2}}) + "\n",
        encoding="utf-8",
    )

    state = advisory_static_analysis_state(round_dir)

    assert state["state"] == "available_with_findings"
    assert "legacy Omen JSON" in state["reason"]


def test_review_role_plan_blocks_code_archive_without_prepared_code_workspace(tmp_path: Path) -> None:
    round_dir = tmp_path / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "inputs").mkdir(parents=True)
    (round_dir / "inputs" / "code.zip").write_bytes(b"synthetic")

    try:
        build_review_role_plan_payload(
            case_id="case-a",
            round_id="round-a",
            profile_id="supervisor_feedback",
            generated_at="2026-05-15T12:00:00Z",
            round_dir=round_dir,
        )
    except ValueError as exc:
        assert "code_bearing_contract is blocked" in str(exc)
    else:
        raise AssertionError("raw code archive without prepared workspace did not block role-plan generation")


def test_review_round_start_cli_dry_run_writes_trace_without_role_plan(monkeypatch) -> None:
    case_id = "__review_round_start_pytest"
    round_id = "round-a"
    case_dir = REPO_ROOT / "cases" / case_id
    shutil.rmtree(case_dir, ignore_errors=True)
    monkeypatch.setattr(review_round_start, "repo_root", lambda: REPO_ROOT)
    monkeypatch.setattr(review_round_start, "git_ignored", lambda root, path: True)
    try:
        round_dir = case_dir / "rounds" / round_id
        for child in ("notes", "inputs", "extracted", "work", "outputs"):
            (round_dir / child).mkdir(parents=True, exist_ok=True)
        (case_dir / "case.md").write_text(
            "\n".join(
                [
                    "Work type: BP",
                    "Academic year: 2025/2026",
                    "Student feedback language: cs",
                    "Thesis language: auto",
                    "Reviewer profile: default",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (case_dir / "current-round.txt").write_text(f"{round_id}\n", encoding="utf-8")
        (round_dir / "inputs" / "thesis.pdf").write_text("%PDF synthetic\n", encoding="utf-8")

        result = review_round_start.run_round_start(
            [
                "review-round-start",
                case_id,
                round_id,
                "--profile",
                "supervisor_feedback",
                "--fresh-materials-expected",
                "--thesis-pdf",
                "inputs/thesis.pdf",
                "--metadata",
                "assignment=First line\\nSecond line",
                "--dry-run",
                "--generated-at",
                "2026-05-15T12:00:00Z",
            ]
        )

        assert result == 0
        assert not (round_dir / "work" / "review_role_plan.json").exists()
        trace = json.loads((round_dir / REVIEW_RUN_TRACE_REL).read_text(encoding="utf-8"))
        assert trace["schema_version"] == REVIEW_RUN_TRACE_SCHEMA
        assert trace["profile_id"] == "supervisor_feedback"
        assert trace["generated_at"] == "2026-05-15T12:00:00Z"
        assert any(event["phase"] == "extraction" and event["status"] == "skipped" for event in trace["events"])
        assert any(event["phase"] == "role_plan" and event["status"] == "planned" for event in trace["events"])
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)


def test_review_round_start_cli_blocks_unsafe_material_and_records_trace(monkeypatch) -> None:
    case_id = "__review_round_start_blocked_pytest"
    round_id = "round-a"
    case_dir = REPO_ROOT / "cases" / case_id
    shutil.rmtree(case_dir, ignore_errors=True)
    monkeypatch.setattr(review_round_start, "repo_root", lambda: REPO_ROOT)
    monkeypatch.setattr(review_round_start, "git_ignored", lambda root, path: True)
    try:
        round_dir = case_dir / "rounds" / round_id
        for child in ("notes", "inputs", "extracted", "work", "outputs"):
            (round_dir / child).mkdir(parents=True, exist_ok=True)
        (case_dir / "case.md").write_text("Work type: BP\nReviewer profile: default\n", encoding="utf-8")
        (case_dir / "current-round.txt").write_text(f"{round_id}\n", encoding="utf-8")

        result = review_round_start.run_round_start(
            [
                "review-round-start",
                case_id,
                round_id,
                "--profile",
                "supervisor_feedback",
                "--thesis-pdf",
                "../private.pdf",
                "--generated-at",
                "2026-05-15T12:00:00Z",
            ]
        )

        assert result == 1
        trace = json.loads((round_dir / REVIEW_RUN_TRACE_REL).read_text(encoding="utf-8"))
        assert any(event["phase"] == "start" and event["status"] == "blocked" for event in trace["events"])
        assert all("../private.pdf" not in event.get("source_refs", []) for event in trace["events"])
        assert "../private.pdf" not in json.dumps(trace)
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)


def test_review_round_start_metadata_file_reads_caller_path(tmp_path: Path) -> None:
    metadata_path = tmp_path / "assignment.txt"
    metadata_path.write_text("Line one\nLine two\n", encoding="utf-8")

    fields = review_round_start.metadata_fields([], [f"assignment={metadata_path}"])

    assert fields == {"assignment": "Line one\nLine two\n"}
