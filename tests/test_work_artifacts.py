import json
from pathlib import Path

from thesis_review_workflow.claim_review_basis import CLAIM_REVIEW_BASIS_REL, CLAIM_REVIEW_BASIS_SCHEMA
from thesis_review_workflow.evidence_capsules import EVIDENCE_CAPSULE_SCHEMA, EVIDENCE_CAPSULES_REL
from thesis_review_workflow.report_calibration import REPORT_CALIBRATION_BASIS_REL
from thesis_review_workflow.review_packets import COMMON_BRIEFING_REL, write_common_briefing
from thesis_review_workflow.review_pipeline_orchestration import (
    REVIEW_ROLE_PLAN_REL,
    REVIEW_ROLE_PLAN_SCHEMA,
    REVIEW_RUN_TRACE_REL,
    REVIEW_RUN_TRACE_SCHEMA,
)
from thesis_review_workflow.theses_checker_summary import THESES_CHECKER_SUMMARY_REL, THESES_CHECKER_SUMMARY_SCHEMA
from thesis_review_workflow.work_artifacts import (
    collect_supporting_work_artifacts,
    sha256_file,
    validate_supporting_work_artifacts,
)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def collect_hash(path: Path) -> str:
    return sha256_file(path)


def report_calibration_payload(round_dir: Path) -> dict[str, object]:
    profile = round_dir.parents[3] / "profiles" / "default.md"
    operator = round_dir / "notes" / "opponent-report-operator-feedback.md"
    return {
        "schema_version": "report-calibration-basis-v1",
        "case_id": "case-a",
        "round_id": "round-a",
        "calibration_scope": "opponent_report",
        "reviewer_profile_id": "default",
        "workflow_profile": "opponent_review",
        "operator_surface": "opponent_materials",
        "wave_workflow": "opponent_report",
        "generated_at": "2026-05-20T00:00:00Z",
        "producer_type": "agent",
        "producer_role": "thesis-opponent-materials-reviewer",
        "producer_agent": "agent-a",
        "authorization_note": "Synthetic test authorization.",
        "source_refs": ["notes/opponent-report-operator-feedback.md"],
        "profile_sources": [
            {
                "path": "profiles/default.md",
                "sha256": sha256_file(profile),
                "sections_used": ["Opponent Report Style"],
            }
        ],
        "operator_calibration_sources": [
            {
                "path": "notes/opponent-report-operator-feedback.md",
                "sha256": sha256_file(operator),
                "purpose": "report calibration",
            }
        ],
        "related_calibration_artifacts": [],
        "applied_preferences": [
            {
                "preference_id": "opponent.assignment_difficulty.stack_not_enough",
                "source_keys": [
                    "profile:profiles/default.md",
                    "operator:notes/opponent-report-operator-feedback.md",
                ],
                "applies_to": ["assignment_difficulty"],
                "instruction": "Use the structured calibration basis.",
                "priority": "must",
                "status": "applied",
                "decision_reason": "Synthetic fixture.",
            }
        ],
        "expected_report_controls": {
            "is_select_values": {"Náročnost zadání": "průměrně obtížné zadání"},
            "overall_grade": "D",
            "overall_points_interval": [65, 74],
            "defense_question_count": {"min": 1, "max": 3},
            "public_report_length": "compact",
            "private_comment_required": True,
        },
        "limitations": [],
    }


def test_collect_supporting_work_artifacts_records_known_json_and_packet(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "src" / "thesis_review_workflow").mkdir(parents=True)
    (repo / "profiles").mkdir(parents=True)
    (repo / "profiles" / "default.md").write_text("# Default profile\n", encoding="utf-8")
    round_dir = repo / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "notes").mkdir(parents=True)
    (round_dir / "notes" / "assignment.md").write_text("# Assignment\n", encoding="utf-8")
    (round_dir / "notes" / "opponent-report-operator-feedback.md").write_text("# Operator feedback\n", encoding="utf-8")
    (round_dir / "extracted").mkdir(parents=True)
    (round_dir / "extracted" / "thesis.txt").write_text("Thesis text.\n", encoding="utf-8")
    (round_dir / "work" / "code").mkdir(parents=True)
    write_json(
        round_dir / "work" / "assignment_coverage_agent.json",
        {
            "schema_version": "assignment-coverage-agent-v1",
            "case_id": "case-a",
            "round_id": "round-a",
            "generated_at": "2026-05-06T00:00:00Z",
            "producer_type": "agent",
            "producer_role": "assignment-coverage-reviewer",
            "producer_agent": "agent-a",
            "authorization_note": "Authorized in current request.",
            "source_refs": ["notes/assignment.md", "extracted/thesis.txt"],
            "assignment_points": [
                {
                    "point_id": "A1",
                    "summary": "Requirement.",
                    "source_refs": ["notes/assignment.md"],
                    "coverage": {
                        "status": "covered",
                        "evidence_refs": ["extracted/thesis.txt"],
                        "limitations": [],
                        "requires_reviewer_verification": False,
                    },
                }
            ],
            "limitations": [],
        },
    )
    write_json(
        round_dir / "work" / "theses_similarity" / "intake.json",
        {
            "schema_version": "theses-similarity-intake-v1",
            "case_id": "case-a",
            "round_id": "round-a",
            "generated_at": "2026-05-12T00:00:00Z",
            "producer_type": "deterministic_helper",
            "producer_role": "import-theses-report",
            "producer_agent": "import-theses-report",
            "source_refs": ["inputs/theses_similarity/report.pdf", "extracted/theses_similarity/report.txt"],
            "limitations": [],
            "report_pdf": {"path": "inputs/theses_similarity/report.pdf", "sha256": "0" * 64, "page_count": 1},
            "extracted_text": {
                "path": "extracted/theses_similarity/report.txt",
                "sha256": "0" * 64,
                "extractor": "pdftotext -layout",
            },
            "current_submission_link": "unverified",
            "source_documents": [],
            "matched_passages": [],
        },
    )
    write_json(
        round_dir / "work" / "code_quality_omen.json",
        {
            "schema_version": "code-quality-omen-v1",
            "case_id": "case-a",
            "round_id": "round-a",
            "generated_at": "2026-05-18T12:00:00Z",
            "tool": "omen",
            "status": "available_with_findings",
            "reason": "Synthetic Omen advisory evidence.",
            "invocation": {
                "surface": "cli",
                "command": ["omen", "-p", ".", "-f", "json", "complexity"],
                "analyzed_root": "work/code",
            },
            "summary": {"total_files": 1, "total_functions": 1},
            "source_refs": ["work/code"],
            "non_empty_root_evidence": ["work/code"],
            "limitations": [],
        },
    )
    write_json(round_dir / REPORT_CALIBRATION_BASIS_REL, report_calibration_payload(round_dir))
    checker_source = round_dir / "notes" / "theses-checker-output.txt"
    checker_source.write_text("Normostrany: 42.5\n", encoding="utf-8")
    thesis_pdf = round_dir / "inputs" / "thesis.pdf"
    thesis_pdf.parent.mkdir(parents=True, exist_ok=True)
    thesis_pdf.write_text("Rendered thesis PDF fixture\n", encoding="utf-8")
    write_json(
        round_dir / THESES_CHECKER_SUMMARY_REL,
        {
            "schema_version": THESES_CHECKER_SUMMARY_SCHEMA,
            "case_id": "case-a",
            "round_id": "round-a",
            "generated_at": "2026-05-20T00:00:00Z",
            "producer_type": "deterministic_helper",
            "producer_role": "record-theses-checker-summary",
            "producer_agent": "record-theses-checker-summary",
            "source_refs": ["notes/theses-checker-output.txt", "inputs/thesis.pdf"],
            "source_artifact": {
                "path": "notes/theses-checker-output.txt",
                "sha256": sha256_file(checker_source),
                "kind": "copied_text",
            },
            "checked_pdf": {"path": "inputs/thesis.pdf", "sha256": sha256_file(thesis_pdf)},
            "checked_pdf_limitation": None,
            "normostrany": 42.5,
            "thresholds": {"minimum": 30},
            "status": "within_required_range",
            "checker_timestamp": None,
            "captured_at": "2026-05-20T00:00:00Z",
            "limitations": [],
        },
    )
    packet = round_dir / "work" / "opponent_packets" / "synthesis.md"
    packet.parent.mkdir(parents=True, exist_ok=True)
    packet.write_text("# Packet\n", encoding="utf-8")
    supervisor_packet = round_dir / "work" / "supervisor_packets" / "text_assignment.md"
    supervisor_packet.parent.mkdir(parents=True, exist_ok=True)
    supervisor_packet.write_text("# Supervisor Packet\n", encoding="utf-8")
    supervisor_report_packet = round_dir / "work" / "supervisor_report_packets" / "trace.md"
    supervisor_report_packet.parent.mkdir(parents=True, exist_ok=True)
    supervisor_report_packet.write_text("# Supervisor Report Packet\n", encoding="utf-8")

    records = collect_supporting_work_artifacts(round_dir)

    by_path = {record["path"]: record for record in records}
    assert by_path["work/assignment_coverage_agent.json"]["schema_version"] == "assignment-coverage-agent-v1"
    assert by_path["work/assignment_coverage_agent.json"]["producer_role"] == "assignment-coverage-reviewer"
    assert by_path["work/assignment_coverage_agent.json"]["producer_agent"] == "agent-a"
    assert by_path["work/assignment_coverage_agent.json"]["artifact_sha256"]
    assert by_path["work/theses_similarity/intake.json"]["schema_version"] == "theses-similarity-intake-v1"
    assert by_path["work/theses_similarity/intake.json"]["producer_role"] == "import-theses-report"
    assert by_path["work/code_quality_omen.json"]["kind"] == "structured_data"
    assert by_path[REPORT_CALIBRATION_BASIS_REL]["schema_version"] == "report-calibration-basis-v1"
    assert by_path[REPORT_CALIBRATION_BASIS_REL]["producer_role"] == "thesis-opponent-materials-reviewer"
    assert by_path[THESES_CHECKER_SUMMARY_REL]["schema_version"] == THESES_CHECKER_SUMMARY_SCHEMA
    assert by_path[THESES_CHECKER_SUMMARY_REL]["producer_role"] == "record-theses-checker-summary"
    assert by_path["work/opponent_packets/synthesis.md"]["kind"] == "text"
    assert by_path["work/supervisor_packets/text_assignment.md"]["kind"] == "text"
    assert by_path["work/supervisor_report_packets/trace.md"]["kind"] == "text"


def test_validate_supporting_work_artifacts_rejects_stale_hash_and_wrong_case(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    (round_dir / "notes").mkdir(parents=True)
    (round_dir / "notes" / "assignment.md").write_text("# Assignment\n", encoding="utf-8")
    write_json(
        round_dir / "work" / "evidence_requirements.json",
        {
            "schema_version": "evidence-requirements-v1",
            "case_id": "other-case",
            "round_id": "round-a",
            "generated_at": "2026-05-06T00:00:00Z",
            "producer_type": "agent",
            "producer_role": "evidence-requirements-reviewer",
            "producer_agent": "agent-a",
            "authorization_note": "Authorized in current request.",
            "source_refs": ["notes/assignment.md"],
            "requirements": [],
            "limitations": [],
        },
    )

    errors = validate_supporting_work_artifacts(
        [
            {
                "path": "work/evidence_requirements.json",
                "kind": "structured_data",
                "artifact_sha256": "0" * 64,
            }
        ],
        round_dir,
        case_id="case-a",
        round_id="round-a",
    )

    assert any("artifact_sha256 is stale" in error for error in errors)
    assert any("case_id does not match requested case" in error for error in errors)


def test_github_snapshot_manifest_is_case_bound_supporting_work_artifact(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-a"
    write_json(
        round_dir / "work" / "github-intake" / "snapshot-manifest.json",
        {
            "schema_version": "github-snapshot-manifest-v1",
            "case_id": "case-a",
            "round_id": "round-a",
            "generated_at": "2026-05-13T12:00:00Z",
            "producer": "scripts/import-github-code",
            "repositories": [],
            "pull_requests": [],
            "changed_file_list": {"available": False},
            "checks": [],
            "checks_summary_sha256": "0" * 64,
            "checkout_paths": [],
        },
    )

    records = collect_supporting_work_artifacts(round_dir)
    by_path = {record["path"]: record for record in records}

    assert by_path["work/github-intake/snapshot-manifest.json"]["schema_version"] == "github-snapshot-manifest-v1"
    assert validate_supporting_work_artifacts(records, round_dir, case_id="case-a", round_id="round-a") == []


def test_reuse_index_is_case_bound_supporting_work_artifact(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-a"
    write_json(
        round_dir / "work" / "reuse" / "reuse_index.json",
        {
            "schema_version": "round-reuse-index-v1",
            "case_id": "case-a",
            "round_id": "round-a",
            "generated_at": "2026-05-13T12:00:00Z",
            "producer": "scripts/update-round-reuse-index",
            "current_source_fingerprints": [],
            "previous_round_candidates": [],
            "decisions": [],
            "limitations": [],
        },
    )

    records = collect_supporting_work_artifacts(round_dir)
    by_path = {record["path"]: record for record in records}

    assert by_path["work/reuse/reuse_index.json"]["schema_version"] == "round-reuse-index-v1"
    assert validate_supporting_work_artifacts(records, round_dir, case_id="case-a", round_id="round-a") == []


def test_review_run_trace_is_case_bound_supporting_work_artifact(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-a"
    write_json(
        round_dir / REVIEW_RUN_TRACE_REL,
        {
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
                    "phase": "start",
                    "status": "passed",
                    "source_refs": ["inputs/thesis.pdf"],
                    "output_refs": [REVIEW_RUN_TRACE_REL],
                    "source_sha256": {"inputs/thesis.pdf": "a" * 64},
                    "output_sha256": {REVIEW_RUN_TRACE_REL: "b" * 64},
                    "notes": [],
                }
            ],
        },
    )

    records = collect_supporting_work_artifacts(round_dir)
    by_path = {record["path"]: record for record in records}

    assert by_path[REVIEW_RUN_TRACE_REL]["schema_version"] == REVIEW_RUN_TRACE_SCHEMA
    assert validate_supporting_work_artifacts(records, round_dir, case_id="case-a", round_id="round-a") == []

    payload = json.loads((round_dir / REVIEW_RUN_TRACE_REL).read_text(encoding="utf-8"))
    payload["events"][0]["source_sha256"]["inputs/thesis.pdf"] = "not-hex"
    write_json(round_dir / REVIEW_RUN_TRACE_REL, payload)
    records = collect_supporting_work_artifacts(round_dir)
    errors = validate_supporting_work_artifacts(records, round_dir, case_id="case-a", round_id="round-a")

    assert any("source_sha256['inputs/thesis.pdf'] must be a sha256 hex string" in error for error in errors)


def test_review_role_plan_is_case_bound_supporting_work_artifact(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-a"
    write_json(
        round_dir / REVIEW_ROLE_PLAN_REL,
        {
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
            "common_briefing": COMMON_BRIEFING_REL,
            "source_contracts": [],
            "role_states": [
                {
                    "role": "text_assignment",
                    "title": "Text And Assignment Coverage",
                    "skill": "thesis-supervisor-feedback",
                    "state": "required_fresh",
                    "activation": "mandatory",
                    "expected_output": "work/supervisor_packets/text_assignment_findings.md",
                    "packet_path": "work/supervisor_packets/text_assignment.md",
                    "packet_status": "present",
                    "output_status": "missing_artifact",
                    "role_inputs": [],
                    "reuse_projection": {},
                    "agent_coverage_projection": {},
                    "materiality_projection": {},
                    "materiality_profile": "supervisor_feedback",
                    "open_full_artifact_triggers": ["missing_anchor"],
                }
            ],
            "wave_schedule": [{"wave_id": "evidence_1_1", "max_concurrent_agents": 2, "roles": ["text_assignment"]}],
            "code_bearing_contract": {
                "applies": True,
                "code_evidence_present": False,
                "source": "prepared_workspace_or_manifest_projection",
                "required_roles": [],
                "satisfied_roles": [],
                "status": "satisfied",
            },
            "materiality_next_actions": [],
            "materiality_errors": [],
            "advisory_static_analysis": {
                "tool": "omen",
                "state": "tool_unavailable",
                "reason": "not present",
            },
        },
    )

    records = collect_supporting_work_artifacts(round_dir)
    by_path = {record["path"]: record for record in records}

    assert by_path[REVIEW_ROLE_PLAN_REL]["schema_version"] == REVIEW_ROLE_PLAN_SCHEMA
    assert validate_supporting_work_artifacts(records, round_dir, case_id="case-a", round_id="round-a") == []


def test_context_handoff_artifacts_are_case_bound_supporting_work_artifacts(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-a"
    draft = round_dir / "work" / "feedback_student_draft.md"
    evidence = round_dir / "extracted" / "thesis.txt"
    draft.parent.mkdir(parents=True, exist_ok=True)
    evidence.parent.mkdir(parents=True, exist_ok=True)
    draft.write_text("Draft claim.\n", encoding="utf-8")
    evidence.write_text("Anchored source.\n", encoding="utf-8")
    evidence_hash = collect_hash(round_dir / "extracted" / "thesis.txt")
    write_json(
        round_dir / EVIDENCE_CAPSULES_REL,
        {
            "schema_version": EVIDENCE_CAPSULE_SCHEMA,
            "case_id": "case-a",
            "round_id": "round-a",
            "generated_at": "2026-05-13T12:00:00Z",
            "producer_type": "agent",
            "producer_role": "text-reader",
            "producer_agent": "agent-a",
            "source_refs": ["extracted/thesis.txt"],
            "source_sha256": {"extracted/thesis.txt": evidence_hash},
            "capsules": [
                {
                    "capsule_id": "cap-1",
                    "source_ref": "extracted/thesis.txt",
                    "source_sha256": evidence_hash,
                    "anchor_refs": [
                        {
                            "anchor_id": "a1",
                            "source_ref": "extracted/thesis.txt",
                            "anchor_type": "section",
                            "locator": "Section 1",
                        }
                    ],
                    "summary": "Anchored source summary.",
                    "extracted_facts": [],
                    "candidate_claims": [],
                    "uncertainties": [],
                    "limitations": [],
                    "open_raw_source_if": [],
                }
            ],
            "limitations": [],
        },
    )
    capsule_hash = collect_hash(round_dir / EVIDENCE_CAPSULES_REL)
    write_json(
        round_dir / CLAIM_REVIEW_BASIS_REL,
        {
            "schema_version": CLAIM_REVIEW_BASIS_SCHEMA,
            "case_id": "case-a",
            "round_id": "round-a",
            "generated_at": "2026-05-13T12:00:00Z",
            "producer_type": "agent",
            "producer_role": "synthesis-reviewer",
            "producer_agent": "agent-a",
            "draft_ref": "work/feedback_student_draft.md",
            "draft_sha256": collect_hash(draft),
            "capsule_refs": [EVIDENCE_CAPSULES_REL],
            "claims": [
                {
                    "claim_id": "p2-claim",
                    "claim_text": "Draft claim.",
                    "priority": "p2",
                    "grade_impact": False,
                    "evidence_refs": ["extracted/thesis.txt"],
                    "capsule_refs": [EVIDENCE_CAPSULES_REL],
                    "source_sha256": {
                        "extracted/thesis.txt": evidence_hash,
                        EVIDENCE_CAPSULES_REL: capsule_hash,
                    },
                    "verification_status": "verified_from_basis",
                    "raw_source_escalations": [],
                }
            ],
            "limitations": [],
        },
    )

    records = collect_supporting_work_artifacts(round_dir)
    by_path = {record["path"]: record for record in records}

    assert by_path[EVIDENCE_CAPSULES_REL]["schema_version"] == EVIDENCE_CAPSULE_SCHEMA
    assert by_path[CLAIM_REVIEW_BASIS_REL]["schema_version"] == CLAIM_REVIEW_BASIS_SCHEMA
    assert validate_supporting_work_artifacts(records, round_dir, case_id="case-a", round_id="round-a") == []


def test_common_briefing_is_deep_validated_supporting_work_artifact(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    round_dir = repo_root / "cases" / "case-a" / "rounds" / "round-a"
    (repo_root / "profiles").mkdir(parents=True)
    (repo_root / "profiles" / "default.md").write_text("# Default profile\n", encoding="utf-8")
    (round_dir.parents[1]).mkdir(parents=True)
    (round_dir.parents[1] / "case.md").write_text("Reviewer profile: default\n", encoding="utf-8")
    (round_dir / "notes").mkdir(parents=True)
    (round_dir / "notes" / "assignment.md").write_text("# Assignment\n", encoding="utf-8")
    write_common_briefing("case-a", "round-a", "2026-05-13T12:00:00Z", round_dir)

    records = collect_supporting_work_artifacts(round_dir)
    by_path = {record["path"]: record for record in records}

    assert by_path[COMMON_BRIEFING_REL]["schema_version"] == "common-briefing-v1"
    assert validate_supporting_work_artifacts(records, round_dir, case_id="case-a", round_id="round-a") == []

    payload = json.loads((round_dir / COMMON_BRIEFING_REL).read_text(encoding="utf-8"))
    payload["context_handoffs"][0]["path"] = "../private.txt"
    write_json(round_dir / COMMON_BRIEFING_REL, payload)

    records = collect_supporting_work_artifacts(round_dir)
    errors = validate_supporting_work_artifacts(records, round_dir, case_id="case-a", round_id="round-a")

    assert any("context_handoffs item 1: path must be a safe relative path" in error for error in errors)


def test_common_briefing_rejects_false_present_record_for_missing_file(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    round_dir = repo_root / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "notes").mkdir(parents=True)
    (round_dir / "notes" / "assignment.md").write_text("# Assignment\n", encoding="utf-8")
    write_common_briefing("case-a", "round-a", "2026-05-13T12:00:00Z", round_dir)
    payload = json.loads((round_dir / COMMON_BRIEFING_REL).read_text(encoding="utf-8"))
    payload["base_inputs"][0]["path"] = "notes/missing.md"
    payload["base_inputs"][0]["status"] = "present"
    payload["base_inputs"][0].pop("sha256", None)
    write_json(round_dir / COMMON_BRIEFING_REL, payload)

    records = collect_supporting_work_artifacts(round_dir)
    errors = validate_supporting_work_artifacts(records, round_dir, case_id="case-a", round_id="round-a")

    assert any("base_inputs item 1: present records must point to an existing file" in error for error in errors)


def test_collect_supporting_work_artifacts_records_human_producer_identity(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    (round_dir / "inputs").mkdir(parents=True)
    (round_dir / "inputs" / "results.csv").write_text("metric,value\nlatency,42\n", encoding="utf-8")
    write_json(
        round_dir / "work" / "quantitative_claims.json",
        {
            "schema_version": "quantitative-claims-v1",
            "case_id": "case-a",
            "round_id": "round-a",
            "generated_at": "2026-05-11T00:00:00Z",
            "producer_type": "human",
            "producer_role": "quantitative-claims-reviewer",
            "producer_agent": None,
            "human_reviewer_note": "Reviewed by operator.",
            "source_refs": ["inputs/results.csv"],
            "claims": [
                {
                    "claim_id": "Q1",
                    "summary": "Synthetic metric claim.",
                    "kind": "metric",
                    "status": "needs_context",
                    "unit": "ms",
                    "baseline_status": "missing",
                    "practical_context": "weak",
                    "scale_context": "Latency scale is a single synthetic value.",
                    "sample_context": "Synthetic result file is the sample context.",
                    "practical_magnitude": "Magnitude is not interpreted against a baseline.",
                    "overclaim_risk": "moderate",
                    "reproducibility_refs": ["inputs/results.csv"],
                    "evidence_refs": ["inputs/results.csv"],
                    "requires_reviewer_verification": True,
                }
            ],
            "limitations": [],
        },
    )

    records = collect_supporting_work_artifacts(round_dir)
    quantitative = {record["path"]: record for record in records}["work/quantitative_claims.json"]

    assert quantitative["producer_type"] == "human"
    assert quantitative["producer_role"] == "quantitative-claims-reviewer"
    assert quantitative["producer_agent"] == "human_reviewer"
    assert validate_supporting_work_artifacts(records, round_dir, case_id="case-a", round_id="round-a") == []


def test_validate_supporting_work_artifacts_requires_hash_and_payload_fields(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    write_json(
        round_dir / "work" / "assignment_coverage_agent.json",
        {
            "schema_version": "assignment-coverage-agent-v1",
            "case_id": "case-a",
            "round_id": "round-a",
            "generated_at": "2026-05-06T00:00:00Z",
            "producer_type": "agent",
            "producer_role": "assignment-coverage-reviewer",
            "producer_agent": "agent-a",
            "authorization_note": "Authorized in current request.",
            "source_refs": [],
            "limitations": [],
        },
    )
    write_json(
        round_dir / "work" / "code_reproducibility.json",
        {
            "schema_version": "code-reproducibility-v1",
            "case_id": "case-a",
            "round_id": "round-a",
            "generated_at": "2026-05-06T00:00:00Z",
        },
    )

    errors = validate_supporting_work_artifacts(
        [
            {"path": "work/assignment_coverage_agent.json", "kind": "structured_data"},
            {
                "path": "work/code_reproducibility.json",
                "kind": "structured_data",
                "artifact_sha256": "not-a-hash",
            },
        ],
        round_dir,
        case_id="case-a",
        round_id="round-a",
    )

    assert any("artifact_sha256 must be a 64-character hex string" in error for error in errors)
    assert any("assignment_points must be list" in error for error in errors)
    assert any("classification must be str" in error for error in errors)


def test_validate_supporting_work_artifacts_rejects_unsafe_path_before_hashing(tmp_path: Path) -> None:
    outside = tmp_path / "outside.json"
    outside.write_text("{}\n", encoding="utf-8")
    round_dir = tmp_path / "round"
    round_dir.mkdir()

    errors = validate_supporting_work_artifacts(
        [
            {
                "path": outside.as_posix(),
                "kind": "structured_data",
                "artifact_sha256": "0" * 64,
            }
        ],
        round_dir,
        case_id="case-a",
        round_id="round-a",
    )

    assert errors == ["supporting_work_artifacts item 1: path must be relative inside the round"]
