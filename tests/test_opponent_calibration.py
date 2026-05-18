import hashlib
import json
from pathlib import Path

from thesis_review_workflow.cli import check_reviewer_profile, check_round_ready
from thesis_review_workflow.cli.check_opponent_calibration_profile import profile_binding_errors
from thesis_review_workflow.cli.draft_opponent_report import validate_current_case_calibration
from thesis_review_workflow.commands import Step
from thesis_review_workflow.opponent_calibration import validate_opponent_calibration_artifact
from thesis_review_workflow.structured_evidence import REQUIRED_OPPONENT_IS_ITEM_IDS
from thesis_review_workflow.work_artifacts import collect_supporting_work_artifacts, validate_supporting_work_artifacts


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def jsonl_entry_sha256(entry: dict[str, object]) -> str:
    return hashlib.sha256(json.dumps(entry).encode("utf-8")).hexdigest()


def write_profile_snapshot(round_dir: Path, version: int, content: str = "synthetic fixture\n") -> Path:
    path = round_dir / "work/calibration/profile_versions" / f"v{version}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def write_text_artifact(round_dir: Path, rel_path: str, content: str = "synthetic fixture\n") -> Path:
    path = round_dir / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def common_fields(schema_version: str) -> dict[str, object]:
    return {
        "schema_version": schema_version,
        "reviewer_profile_id": "zm-calibration",
        "case_id": "calibration-case",
        "round_id": "round-a",
        "generated_at": "2026-05-07T00:00:00Z",
        "producer_type": "agent",
        "producer_role": "opponent-calibration-reviewer",
        "producer_agent": "agent-a",
        "authorization_note": "Current request explicitly authorized agents.",
        "source_refs": ["inputs/historical_cases/case-001/opponent_report.md"],
        "limitations": [],
    }


def create_calibration_refs(round_dir: Path) -> None:
    for rel in (
        "inputs/historical_cases/case-001/opponent_report.md",
        "inputs/historical_cases/case-001/assignment.md",
        "inputs/historical_cases/case-002/opponent_report.md",
        "outputs/reviewer_calibration_profile.md",
    ):
        path = round_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic fixture\n", encoding="utf-8")


def historical_case_payload() -> dict[str, object]:
    return {
        **common_fields("historical-opponent-case-analysis-v1"),
        "historical_case_id": "case-001",
        "work_type": "diploma thesis",
        "domain": "synthetic software engineering",
        "case_strength": "typical",
        "artifact_availability": {"assignment": "present", "thesis": "present", "report": "present"},
        "code_availability": {"submitted_code": "present"},
        "report_shape": {"length_class": "medium"},
        "judgment_calibration": {"strictness": "medium"},
        "evidence_habits": {"relied_on": ["assignment", "thesis", "code"]},
        "corpus_coverage": {"work_type": "diploma thesis", "domain": "synthetic"},
        "recurring_checks": [
            {
                "check_id": "assignment-map",
                "evidence_class": "assignment_fulfillment",
                "prompt": "Map submitted work to assignment points.",
            }
        ],
    }


def historical_case_payload_for(historical_case_id: str) -> dict[str, object]:
    payload = historical_case_payload()
    payload["historical_case_id"] = historical_case_id
    payload["source_refs"] = [f"inputs/historical_cases/{historical_case_id}/opponent_report.md"]
    return payload


def confidence_by_dimension() -> dict[str, dict[str, str]]:
    return {
        "style": {"level": "medium", "rationale": "Two synthetic reports."},
        "grading": {"level": "low", "rationale": "Small corpus."},
        "severity": {"level": "medium", "rationale": "Repeated categories."},
        "questions": {"level": "medium", "rationale": "Stable question pattern."},
        "evidence_expectations": {"level": "medium", "rationale": "Repeated evidence demands."},
        "checklist_coverage": {"level": "medium", "rationale": "Several recurring checks."},
    }


def operator_approval(
    *,
    version: int = 2,
    profile_hash: str = "b" * 64,
    manifest_hash: str = "c" * 64,
) -> dict[str, object]:
    return {
        "approved": True,
        "approval_kind": "default_profile_refresh",
        "approved_profile_version": version,
        "approved_profile_markdown_sha256": profile_hash,
        "approved_profile_manifest_sha256": manifest_hash,
        "approved_by": "synthetic-operator",
        "approved_at": "2026-05-07T00:00:00Z",
        "approval_scope": "Make refreshed profile version default for future opponent cases.",
    }


def write_selected_calibration_artifacts(round_dir: Path, *, profile_version: int = 1) -> dict[str, str]:
    create_calibration_refs(round_dir)
    analysis_refs = [
        "work/calibration/historical_case_analyses/case-001.json",
        "work/calibration/historical_case_analyses/case-002.json",
    ]
    for rel_path in analysis_refs:
        historical_case_id = rel_path.rsplit("/", maxsplit=1)[1].removesuffix(".json")
        write_json(round_dir / rel_path, historical_case_payload_for(historical_case_id))

    profile_path = round_dir / "outputs/reviewer_calibration_profile.md"
    profile = {
        **common_fields("opponent-reviewer-calibration-profile-v1"),
        "source_refs": analysis_refs,
        "profile_markdown_path": "outputs/reviewer_calibration_profile.md",
        "profile_markdown_sha256": sha256_file(profile_path),
        "profile_applicability": {"confident": ["synthetic software engineering"]},
        "source_case_refs": analysis_refs,
        "profile_version": profile_version,
        "profile_previous_sha256": None,
        "profile_change_summary": "Initial synthetic profile.",
        "confidence_by_dimension": confidence_by_dimension(),
        "do_not_use_for": ["current-case conclusions without evidence"],
    }
    checklist = {
        **common_fields("opponent-reviewer-checklist-v1"),
        "source_refs": analysis_refs,
        "checklist_items": [
            {
                "item_id": "assignment-map",
                "evidence_class": "assignment_fulfillment",
                "prompt": "Map submitted work to assignment points.",
                "source_case_refs": analysis_refs,
                "requires_current_case_evidence": True,
            }
        ],
    }
    paths = {
        "profile": "work/calibration/reviewer_calibration_profile.json",
        "checklist": "work/calibration/reviewer_checklist.json",
    }
    write_json(round_dir / paths["profile"], profile)
    write_json(round_dir / paths["checklist"], checklist)
    return {key: sha256_file(round_dir / rel_path) for key, rel_path in paths.items()}


def current_case_hashes(round_dir: Path) -> dict[str, str]:
    materials = write_text_artifact(round_dir, "outputs/oponent_podklady_revidovane.md")
    write_json(
        round_dir / "work/opponent_report_trace.json",
        opponent_trace_payload(sha256_file(materials)),
    )
    hashes = write_selected_calibration_artifacts(round_dir)
    paths = {
        "source_materials": "outputs/oponent_podklady_revidovane.md",
        "trace": "work/opponent_report_trace.json",
    }
    hashes.update({key: sha256_file(round_dir / rel_path) for key, rel_path in paths.items()})
    return hashes


def refresh_current_case_approval(payload: dict[str, object], field: str, value: str) -> None:
    approval = dict(payload["operator_approval"]) if isinstance(payload["operator_approval"], dict) else {}
    approval[field] = value
    payload["operator_approval"] = approval


def reviewer_profile_gate() -> dict[str, object]:
    return {
        "required": True,
        "satisfied_by_historical_calibration": False,
    }


def opponent_trace_payload(source_hash: str) -> dict[str, object]:
    return {
        **common_fields("opponent-report-trace-v1"),
        "source_refs": ["outputs/oponent_podklady_revidovane.md"],
        "source_materials_path": "outputs/oponent_podklady_revidovane.md",
        "source_materials_sha256": source_hash,
        "trace_review_status": "accepted",
        "reviewer_role": "synthetic-trace-reviewer",
        "reviewed_at": "2026-05-07T00:00:00Z",
        "trace_generated_from": ["outputs/oponent_podklady_revidovane.md"],
        "is_items": [
            {
                "item_id": item_id,
                "title": item_id.replace("_", " "),
                "formulation": "Synthetic formulation.",
                "evidence_refs": ["outputs/oponent_podklady_revidovane.md"],
            }
            for item_id in sorted(REQUIRED_OPPONENT_IS_ITEM_IDS)
        ],
        "defense_questions": [
            {
                "question_id": "D1",
                "question": "Synthetic defense question?",
                "evidence_refs": ["outputs/oponent_podklady_revidovane.md"],
            }
        ],
        "pre_submission_checks": [
            {
                "check_id": "C1",
                "instruction": "Synthetic manual check.",
                "evidence_refs": ["outputs/oponent_podklady_revidovane.md"],
            }
        ],
        "uncertainty_items": [
            {
                "claim_id": "U1",
                "summary": "Synthetic uncertainty.",
                "handling_instruction": "Keep cautious wording.",
                "source_refs": ["outputs/oponent_podklady_revidovane.md"],
                "target_section_ids": ["overall_assessment"],
                "report_refs": ["work/oponent_posudek_draft.md"],
                "status": "carried_to_report",
            }
        ],
        "limitations": [],
    }


def current_case_approval(hashes: dict[str, str]) -> dict[str, object]:
    return {
        "approved": True,
        "approval_kind": "current_case_calibration_use",
        "approved_by": "synthetic-operator",
        "approved_at": "2026-05-07T00:00:00Z",
        "approved_profile_manifest_sha256": hashes["profile"],
        "approved_checklist_sha256": hashes["checklist"],
        "approved_source_materials_sha256": hashes["source_materials"],
        "approved_trace_sha256": hashes["trace"],
    }


def calibration_use_payload(round_dir: Path) -> dict[str, object]:
    hashes = current_case_hashes(round_dir)
    return {
        **common_fields("opponent-calibration-use-v1"),
        "source_refs": [
            "outputs/oponent_podklady_revidovane.md",
            "work/opponent_report_trace.json",
            "work/calibration/reviewer_calibration_profile.json",
            "work/calibration/reviewer_checklist.json",
        ],
        "limitations": ["Synthetic calibration profile; current case evidence remains authoritative."],
        "source_materials_path": "outputs/oponent_podklady_revidovane.md",
        "source_materials_sha256": hashes["source_materials"],
        "opponent_report_trace_path": "work/opponent_report_trace.json",
        "opponent_report_trace_sha256": hashes["trace"],
        "profile_manifest_path": "work/calibration/reviewer_calibration_profile.json",
        "profile_manifest_sha256": hashes["profile"],
        "checklist_path": "work/calibration/reviewer_checklist.json",
        "checklist_sha256": hashes["checklist"],
        "selected_profile_version": 1,
        "calibration_scope": "Style, evidence expectations, and checklist prompts only.",
        "applicability_dimensions": [
            {"dimension": "work_type", "status": "matching", "rationale": "Synthetic fixture."},
            {"dimension": "domain", "status": "partial", "rationale": "Synthetic fixture."},
        ],
        "confidence_by_dimension": confidence_by_dimension(),
        "reviewer_profile_gate": reviewer_profile_gate(),
        "operator_approval": current_case_approval(hashes),
    }


def calibration_advisory_payload(round_dir: Path) -> dict[str, object]:
    materials = write_text_artifact(round_dir, "outputs/oponent_podklady_revidovane.md")
    trace = round_dir / "work/opponent_report_trace.json"
    write_json(trace, opponent_trace_payload(sha256_file(materials)))
    return {
        **common_fields("opponent-calibration-advisory-v1"),
        "source_refs": ["outputs/oponent_podklady_revidovane.md", "work/opponent_report_trace.json"],
        "limitations": ["Historical calibration is optional and unavailable in this synthetic fixture."],
        "source_materials_path": "outputs/oponent_podklady_revidovane.md",
        "source_materials_sha256": sha256_file(materials),
        "opponent_report_trace_path": "work/opponent_report_trace.json",
        "opponent_report_trace_sha256": sha256_file(trace),
        "no_profile_reason": "missing_profile",
        "advisory_status": "non_blocking",
        "normal_workflow_continues": True,
        "recommendation": "Add historical opponent reports later for better style calibration.",
        "reviewer_profile_gate": reviewer_profile_gate(),
    }


def revision_request_payload(round_dir: Path, *, use_calibration: bool = True) -> dict[str, object]:
    if use_calibration:
        calibration_payload = calibration_use_payload(round_dir)
        calibration_rel = "work/opponent_calibration_use.json"
    else:
        calibration_payload = calibration_advisory_payload(round_dir)
        calibration_rel = "work/opponent_calibration_advisory.json"
    write_json(round_dir / calibration_rel, calibration_payload)
    feedback = write_text_artifact(
        round_dir,
        "notes/opponent-report-operator-feedback.md",
        "# Operator feedback\n\nPlease adjust grading and add one manual check.\n",
    )
    comparison = write_text_artifact(
        round_dir,
        "outputs/reference_report_comparison.md",
        "# Reference report comparison\n\nSynthetic comparison.\n",
    )
    packet = write_text_artifact(
        round_dir,
        "outputs/opponent_reading_packet.md",
        "# Opponent reading packet\n\nSynthetic reading packet.\n",
    )
    draft = write_text_artifact(
        round_dir,
        "work/oponent_posudek_draft.md",
        "# Oponentsky posudek\n\nSynthetic draft calibrated by the operator.\n",
    )
    trace_snapshot = write_text_artifact(
        round_dir,
        "work/opponent_report_revision_sources/opponent_report_trace.json",
        (round_dir / "work/opponent_report_trace.json").read_text(encoding="utf-8"),
    )
    draft_snapshot = write_text_artifact(
        round_dir,
        "work/opponent_report_revision_sources/oponent_posudek_draft.md",
        draft.read_text(encoding="utf-8"),
    )
    source_paths = [
        "notes/opponent-report-operator-feedback.md",
        "outputs/oponent_podklady_revidovane.md",
        "work/opponent_report_revision_sources/opponent_report_trace.json",
        "work/opponent_report_revision_sources/oponent_posudek_draft.md",
        calibration_rel,
        "outputs/reference_report_comparison.md",
        "outputs/opponent_reading_packet.md",
    ]
    payload = {
        **common_fields("opponent-report-revision-request-v1"),
        "source_refs": source_paths,
        "limitations": ["Synthetic operator feedback normalization."],
        "operator_feedback_path": "notes/opponent-report-operator-feedback.md",
        "operator_feedback_sha256": sha256_file(feedback),
        "source_materials_path": "outputs/oponent_podklady_revidovane.md",
        "source_materials_sha256": sha256_file(round_dir / "outputs/oponent_podklady_revidovane.md"),
        "opponent_report_trace_path": "work/opponent_report_revision_sources/opponent_report_trace.json",
        "opponent_report_trace_sha256": sha256_file(trace_snapshot),
        "opponent_report_draft_path": "work/opponent_report_revision_sources/oponent_posudek_draft.md",
        "opponent_report_draft_sha256": sha256_file(draft_snapshot),
        "reference_report_comparison_path": "outputs/reference_report_comparison.md",
        "reference_report_comparison_sha256": sha256_file(comparison),
        "opponent_reading_packet_path": "outputs/opponent_reading_packet.md",
        "opponent_reading_packet_sha256": sha256_file(packet),
        "feedback_items": [
            {
                "item_id": "F1",
                "category": "grading_calibration",
                "summary": "Operator wants a stricter point interval.",
                "requested_action": "Re-evaluate the point interval against current-case evidence.",
                "evidence_refs": [
                    "notes/opponent-report-operator-feedback.md",
                    "outputs/opponent_reading_packet.md",
                ],
            }
        ],
        "requested_extra_checks": [
            {
                "check_id": "C1",
                "category": "evidence_request",
                "instruction": "Check whether the reproducibility concern is still current.",
                "evidence_refs": ["outputs/oponent_podklady_revidovane.md"],
            }
        ],
    }
    if use_calibration:
        payload["calibration_use_path"] = calibration_rel
        payload["calibration_use_sha256"] = sha256_file(round_dir / calibration_rel)
    else:
        payload["calibration_advisory_path"] = calibration_rel
        payload["calibration_advisory_sha256"] = sha256_file(round_dir / calibration_rel)
    return payload


def calibration_refresh_eligibility_payload(round_dir: Path) -> dict[str, object]:
    materials = write_text_artifact(round_dir, "outputs/oponent_podklady_revidovane.md")
    trace_path = round_dir / "work/opponent_report_trace.json"
    write_json(trace_path, opponent_trace_payload(sha256_file(materials)))
    draft = write_text_artifact(
        round_dir,
        "work/oponent_posudek_draft.md",
        "# Návrh oponentského posudku\n\nSynthetic finalized draft.\n",
    )
    review = write_text_artifact(
        round_dir,
        "outputs/feedback_k_posudku.md",
        "# Review of opponent report\n\nIndependent reviewer accepted the finalized draft.\n",
    )
    hashes = {
        "materials": sha256_file(materials),
        "trace": sha256_file(trace_path),
        "draft": sha256_file(draft),
        "review": sha256_file(review),
    }
    manifest_snapshot = {
        "schema_version": "review-manifest-v1",
        "case_id": "calibration-case",
        "round_id": "round-a",
        "updated_at": "2026-05-07T00:00:00Z",
        "manifest_path": "work/review_manifest.json",
        "inputs": [],
        "extracted_artifacts": [],
        "notes": [],
        "supporting_work_artifacts": [
            {
                "path": "work/opponent_report_trace.json",
                "kind": "structured_data",
                "artifact_sha256": hashes["trace"],
                "schema_version": "opponent-report-trace-v1",
            },
            {
                "path": "work/oponent_posudek_draft.md",
                "kind": "text",
                "artifact_sha256": hashes["draft"],
            },
        ],
        "helper_checks": [
            {
                "check": "check-opponent-materials",
                "command": "scripts/check-opponent-materials calibration-case round-a",
                "target_artifacts": ["outputs/oponent_podklady_revidovane.md"],
                "target_sha256": {"outputs/oponent_podklady_revidovane.md": hashes["materials"]},
                "status": "passed",
                "checked_at": "2026-05-07T00:01:00Z",
                "exit_code": 0,
            },
            {
                "check": "check-opponent-report:canonical",
                "command": "scripts/check-opponent-report --mode canonical calibration-case round-a",
                "target_artifacts": [
                    "work/opponent_report_trace.json",
                    "outputs/oponent_podklady_revidovane.md",
                    "work/oponent_posudek_draft.md",
                ],
                "target_sha256": {
                    "work/opponent_report_trace.json": hashes["trace"],
                    "outputs/oponent_podklady_revidovane.md": hashes["materials"],
                    "work/oponent_posudek_draft.md": hashes["draft"],
                },
                "status": "passed",
                "checked_at": "2026-05-07T00:02:00Z",
                "exit_code": 0,
            },
        ],
        "workflow_limitations": [],
        "artifacts": [
            {
                "path": "outputs/oponent_podklady_revidovane.md",
                "kind": "text",
                "artifact_sha256": hashes["materials"],
                "review_scope": "standalone_final",
                "generated_by": [
                    {
                        "role": "thesis-opponent-materials",
                        "agent": "synthetic-materials-agent",
                        "contribution": "generation",
                        "notes": "Synthetic fixture.",
                    }
                ],
                "independent_review": {
                    "status": "reviewed",
                    "reviewer_role": "thesis-opponent-materials-review",
                    "reviewer_agent": "synthetic-materials-reviewer",
                    "reviewed_at": "2026-05-07T00:03:00Z",
                    "reviewed_hash": hashes["materials"],
                    "covered_by_artifact": "",
                    "used_findings": "",
                    "exception": "",
                    "notes": "Synthetic review passed.",
                },
                "limitations": ["Synthetic fixture."],
            },
            {
                "path": "outputs/feedback_k_posudku.md",
                "kind": "text",
                "artifact_sha256": hashes["review"],
                "review_scope": "standalone_final",
                "generated_by": [
                    {
                        "role": "thesis-opponent-report-review",
                        "agent": "synthetic-report-reviewer",
                        "contribution": "generation",
                        "notes": "Synthetic fixture.",
                    }
                ],
                "independent_review": {
                    "status": "reviewed",
                    "reviewer_role": "thesis-opponent-report-review",
                    "reviewer_agent": "synthetic-report-review-reviewer",
                    "reviewed_at": "2026-05-07T00:04:00Z",
                    "reviewed_hash": hashes["review"],
                    "covered_by_artifact": "",
                    "used_findings": "",
                    "exception": "",
                    "notes": "Synthetic report review accepted.",
                    "review_basis_path": "work/oponent_posudek_draft.md",
                    "review_basis_sha256": hashes["draft"],
                },
                "limitations": ["Synthetic fixture."],
            },
        ],
    }
    manifest_snapshot_path = round_dir / "work/opponent_calibration_refresh_sources/review_manifest.json"
    write_json(manifest_snapshot_path, manifest_snapshot)
    hashes["manifest_snapshot"] = sha256_file(manifest_snapshot_path)
    source_refs = [
        "outputs/oponent_podklady_revidovane.md",
        "work/opponent_report_trace.json",
        "work/oponent_posudek_draft.md",
        "outputs/feedback_k_posudku.md",
        "work/opponent_calibration_refresh_sources/review_manifest.json",
    ]
    return {
        **common_fields("opponent-calibration-refresh-eligibility-v1"),
        "source_refs": source_refs,
        "limitations": ["Synthetic eligibility marker; profile refresh is a separate authorized workflow."],
        "eligibility_status": "operator_approved_for_calibration_refresh",
        "finalization_status": "human_finalized_after_independent_report_review",
        "profile_update_status": "not_started",
        "does_not_update_profile": True,
        "source_materials_path": "outputs/oponent_podklady_revidovane.md",
        "source_materials_sha256": hashes["materials"],
        "opponent_report_trace_path": "work/opponent_report_trace.json",
        "opponent_report_trace_sha256": hashes["trace"],
        "final_report_draft_path": "work/oponent_posudek_draft.md",
        "final_report_draft_sha256": hashes["draft"],
        "final_report_review_path": "outputs/feedback_k_posudku.md",
        "final_report_review_sha256": hashes["review"],
        "review_manifest_snapshot_path": "work/opponent_calibration_refresh_sources/review_manifest.json",
        "review_manifest_snapshot_sha256": hashes["manifest_snapshot"],
        "case_local_source_refs": source_refs,
        "copy_policy": {
            "copy_scope": "private_case_local_refs_only",
            "target_workspace": "ignored_calibration_case_workspace",
            "auto_copy_performed": False,
            "profile_auto_update": False,
            "requires_explicit_profile_refresh_approval": True,
        },
        "operator_approval": {
            "approved": True,
            "approval_kind": "calibration_refresh_eligibility",
            "approved_by": "synthetic-operator",
            "approved_at": "2026-05-07T00:00:00Z",
            "approval_scope": "Allow this finalized case to be analyzed later for calibration refresh.",
            "approved_source_materials_sha256": hashes["materials"],
            "approved_trace_sha256": hashes["trace"],
            "approved_final_report_draft_sha256": hashes["draft"],
            "approved_final_report_review_sha256": hashes["review"],
            "approved_review_manifest_snapshot_sha256": hashes["manifest_snapshot"],
        },
    }


def test_validate_historical_case_analysis_accepts_path_classified_payload(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    write_json(round_dir / "work/calibration/historical_case_analyses/case-001.json", historical_case_payload())

    errors = validate_opponent_calibration_artifact(
        round_dir,
        "work/calibration/historical_case_analyses/case-001.json",
        case_id="calibration-case",
        round_id="round-a",
    )

    assert errors == []


def test_validate_historical_case_analysis_rejects_filename_mismatch(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    write_json(round_dir / "work/calibration/historical_case_analyses/case-002.json", historical_case_payload())

    errors = validate_opponent_calibration_artifact(
        round_dir, "work/calibration/historical_case_analyses/case-002.json"
    )

    assert any("historical_case_id must match the analysis filename" in error for error in errors)


def test_validate_historical_case_analysis_requires_matching_source_anchor(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    other_ref = round_dir / "inputs/historical_cases/case-002/opponent_report.md"
    other_ref.parent.mkdir(parents=True, exist_ok=True)
    other_ref.write_text("other synthetic fixture\n", encoding="utf-8")
    payload = {
        **historical_case_payload(),
        "source_refs": ["inputs/historical_cases/case-002/opponent_report.md"],
    }
    write_json(round_dir / "work/calibration/historical_case_analyses/case-001.json", payload)

    errors = validate_opponent_calibration_artifact(
        round_dir,
        "work/calibration/historical_case_analyses/case-001.json",
    )

    assert any("source_refs must not point to a different historical case id" in error for error in errors)
    assert any(
        "source_refs must include at least one ref under inputs/historical_cases/case-001/" in error for error in errors
    )


def test_validate_historical_case_analysis_requires_source_refs(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    payload = {
        **historical_case_payload(),
        "source_refs": [],
    }
    write_json(round_dir / "work/calibration/historical_case_analyses/case-001.json", payload)

    errors = validate_opponent_calibration_artifact(
        round_dir,
        "work/calibration/historical_case_analyses/case-001.json",
    )

    assert any("source_refs must not be empty" in error for error in errors)


def test_validate_profile_manifest_binds_markdown_hash(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    analysis_path = round_dir / "work/calibration/historical_case_analyses/case-001.json"
    write_json(analysis_path, historical_case_payload())
    profile_path = round_dir / "outputs/reviewer_calibration_profile.md"
    payload = {
        **common_fields("opponent-reviewer-calibration-profile-v1"),
        "source_refs": ["work/calibration/historical_case_analyses/case-001.json"],
        "profile_markdown_path": "outputs/reviewer_calibration_profile.md",
        "profile_markdown_sha256": sha256_file(profile_path),
        "profile_applicability": {"confident": ["synthetic software engineering"]},
        "source_case_refs": ["work/calibration/historical_case_analyses/case-001.json"],
        "profile_version": 1,
        "profile_previous_sha256": None,
        "profile_change_summary": "Initial synthetic profile.",
        "confidence_by_dimension": confidence_by_dimension(),
        "do_not_use_for": ["current-case conclusions without evidence"],
    }
    write_json(round_dir / "work/calibration/reviewer_calibration_profile.json", payload)

    errors = validate_opponent_calibration_artifact(
        round_dir,
        "work/calibration/reviewer_calibration_profile.json",
        case_id="calibration-case",
        round_id="round-a",
    )

    assert errors == []

    profile_path.write_text("changed\n", encoding="utf-8")
    stale_errors = validate_opponent_calibration_artifact(
        round_dir, "work/calibration/reviewer_calibration_profile.json"
    )
    assert any("profile_markdown_sha256 is stale" in error for error in stale_errors)


def test_validate_profile_manifest_reports_non_string_hash_without_crashing(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    write_json(round_dir / "work/calibration/historical_case_analyses/case-001.json", historical_case_payload())
    payload = {
        **common_fields("opponent-reviewer-calibration-profile-v1"),
        "source_refs": ["work/calibration/historical_case_analyses/case-001.json"],
        "profile_markdown_path": "outputs/reviewer_calibration_profile.md",
        "profile_markdown_sha256": 123,
        "profile_applicability": {"confident": ["synthetic software engineering"]},
        "source_case_refs": ["work/calibration/historical_case_analyses/case-001.json"],
        "profile_version": 1,
        "profile_previous_sha256": None,
        "profile_change_summary": "Initial synthetic profile.",
        "confidence_by_dimension": confidence_by_dimension(),
        "do_not_use_for": ["current-case conclusions without evidence"],
    }
    write_json(round_dir / "work/calibration/reviewer_calibration_profile.json", payload)

    errors = validate_opponent_calibration_artifact(round_dir, "work/calibration/reviewer_calibration_profile.json")

    assert any("profile_markdown_sha256 must be a 64-character hex string" in error for error in errors)


def test_validate_profile_manifest_rejects_wrong_markdown_path(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    write_json(round_dir / "work/calibration/historical_case_analyses/case-001.json", historical_case_payload())
    wrong_profile = round_dir / "outputs/other_profile.md"
    wrong_profile.write_text("synthetic wrong profile\n", encoding="utf-8")
    payload = {
        **common_fields("opponent-reviewer-calibration-profile-v1"),
        "source_refs": ["work/calibration/historical_case_analyses/case-001.json"],
        "profile_markdown_path": "outputs/other_profile.md",
        "profile_markdown_sha256": sha256_file(wrong_profile),
        "profile_applicability": {"confident": ["synthetic software engineering"]},
        "source_case_refs": ["work/calibration/historical_case_analyses/case-001.json"],
        "profile_version": 1,
        "profile_previous_sha256": None,
        "profile_change_summary": "Initial synthetic profile.",
        "confidence_by_dimension": confidence_by_dimension(),
        "do_not_use_for": ["current-case conclusions without evidence"],
    }
    write_json(round_dir / "work/calibration/reviewer_calibration_profile.json", payload)

    errors = validate_opponent_calibration_artifact(round_dir, "work/calibration/reviewer_calibration_profile.json")

    assert any("profile_markdown_path must be outputs/reviewer_calibration_profile.md" in error for error in errors)


def test_validate_profile_manifest_requires_existing_historical_case_refs(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    profile_path = round_dir / "outputs/reviewer_calibration_profile.md"
    payload = {
        **common_fields("opponent-reviewer-calibration-profile-v1"),
        "source_refs": ["inputs/historical_cases/case-001/opponent_report.md"],
        "profile_markdown_path": "outputs/reviewer_calibration_profile.md",
        "profile_markdown_sha256": sha256_file(profile_path),
        "profile_applicability": {"confident": ["synthetic software engineering"]},
        "source_case_refs": ["work/calibration/historical_case_analyses/missing.json"],
        "profile_version": 1,
        "profile_previous_sha256": None,
        "profile_change_summary": "Initial synthetic profile.",
        "confidence_by_dimension": confidence_by_dimension(),
        "do_not_use_for": ["current-case conclusions without evidence"],
    }
    write_json(round_dir / "work/calibration/reviewer_calibration_profile.json", payload)

    errors = validate_opponent_calibration_artifact(round_dir, "work/calibration/reviewer_calibration_profile.json")

    assert any(
        "ref does not exist: work/calibration/historical_case_analyses/missing.json" in error for error in errors
    )


def test_validate_profile_manifest_validates_optional_operator_approval(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    analysis_path = round_dir / "work/calibration/historical_case_analyses/case-001.json"
    write_json(analysis_path, historical_case_payload())
    profile_path = round_dir / "outputs/reviewer_calibration_profile.md"
    payload = {
        **common_fields("opponent-reviewer-calibration-profile-v1"),
        "source_refs": ["work/calibration/historical_case_analyses/case-001.json"],
        "profile_markdown_path": "outputs/reviewer_calibration_profile.md",
        "profile_markdown_sha256": sha256_file(profile_path),
        "profile_applicability": {"confident": ["synthetic software engineering"]},
        "source_case_refs": ["work/calibration/historical_case_analyses/case-001.json"],
        "profile_version": 2,
        "profile_previous_sha256": "a" * 64,
        "profile_change_summary": "Refreshed synthetic profile.",
        "confidence_by_dimension": confidence_by_dimension(),
        "do_not_use_for": ["current-case conclusions without evidence"],
    }
    write_json(round_dir / "work/calibration/reviewer_calibration_profile.json", payload)

    payload["operator_approval"] = {"approved": False}
    write_json(round_dir / "work/calibration/reviewer_calibration_profile.json", payload)
    rejected_errors = validate_opponent_calibration_artifact(
        round_dir, "work/calibration/reviewer_calibration_profile.json"
    )
    assert any("operator_approval: approved must be true" in error for error in rejected_errors)


def test_validate_reviewer_checklist_requires_evidence_class_entries(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    write_json(round_dir / "work/calibration/historical_case_analyses/case-001.json", historical_case_payload())
    payload = {
        **common_fields("opponent-reviewer-checklist-v1"),
        "checklist_items": [
            {
                "item_id": "assignment-map",
                "evidence_class": "assignment_fulfillment",
                "prompt": "Map submitted work to assignment points.",
                "source_case_refs": ["work/calibration/historical_case_analyses/case-001.json"],
                "requires_current_case_evidence": True,
            }
        ],
    }
    write_json(round_dir / "work/calibration/reviewer_checklist.json", payload)

    errors = validate_opponent_calibration_artifact(round_dir, "work/calibration/reviewer_checklist.json")

    assert errors == []


def test_validate_reviewer_checklist_rejects_unsafe_source_case_refs(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    payload = {
        **common_fields("opponent-reviewer-checklist-v1"),
        "checklist_items": [
            {
                "item_id": "assignment-map",
                "evidence_class": "assignment_fulfillment",
                "prompt": "Map submitted work to assignment points.",
                "source_case_refs": ["/tmp/private-case.json"],
                "requires_current_case_evidence": True,
            }
        ],
    }
    write_json(round_dir / "work/calibration/reviewer_checklist.json", payload)

    errors = validate_opponent_calibration_artifact(round_dir, "work/calibration/reviewer_checklist.json")

    assert any("ref must be relative inside the round" in error for error in errors)


def test_validate_profile_history_jsonl(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    analysis_path = round_dir / "work/calibration/historical_case_analyses/case-001.json"
    write_json(analysis_path, historical_case_payload())
    snapshot = write_profile_snapshot(round_dir, 1)
    entry = {
        **common_fields("opponent-reviewer-calibration-history-v1"),
        "source_refs": ["work/calibration/historical_case_analyses/case-001.json"],
        "schema_version": "opponent-reviewer-calibration-history-v1",
        "profile_version": 1,
        "previous_profile_markdown_sha256": None,
        "previous_history_entry_sha256": None,
        "profile_snapshot_path": "work/calibration/profile_versions/v1.md",
        "profile_markdown_sha256": "a" * 64,
        "profile_manifest_sha256": "b" * 64,
        "source_case_refs": ["work/calibration/historical_case_analyses/case-001.json"],
        "review_status": "accepted",
        "change_summary": "Initial synthetic profile.",
    }
    entry["profile_markdown_sha256"] = sha256_file(snapshot)
    history_path = round_dir / "work/calibration/reviewer_calibration_profile_history.jsonl"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(json.dumps(entry) + "\n", encoding="utf-8")

    errors = validate_opponent_calibration_artifact(
        round_dir,
        "work/calibration/reviewer_calibration_profile_history.jsonl",
        case_id="calibration-case",
        round_id="round-a",
    )

    assert errors == []


def test_validate_profile_history_requires_common_metadata(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    write_json(round_dir / "work/calibration/historical_case_analyses/case-001.json", historical_case_payload())
    entry = {
        "schema_version": "opponent-reviewer-calibration-history-v1",
        "profile_version": 1,
        "previous_profile_markdown_sha256": None,
        "profile_markdown_sha256": "a" * 64,
        "profile_manifest_sha256": "b" * 64,
        "source_case_refs": ["work/calibration/historical_case_analyses/case-001.json"],
        "review_status": "accepted",
        "change_summary": "Initial synthetic profile.",
    }
    history_path = round_dir / "work/calibration/reviewer_calibration_profile_history.jsonl"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(json.dumps(entry) + "\n", encoding="utf-8")

    errors = validate_opponent_calibration_artifact(
        round_dir,
        "work/calibration/reviewer_calibration_profile_history.jsonl",
        case_id="calibration-case",
        round_id="round-a",
    )

    assert any("case_id does not match requested case" in error for error in errors)
    assert any("producer_role must be non-empty str" in error for error in errors)
    assert any("producer_type must be agent or human" in error for error in errors)


def test_validate_history_rejects_empty_source_case_refs(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    entry = {
        **common_fields("opponent-reviewer-calibration-history-v1"),
        "profile_version": 1,
        "previous_profile_markdown_sha256": None,
        "profile_markdown_sha256": "a" * 64,
        "profile_manifest_sha256": "b" * 64,
        "source_case_refs": [],
        "review_status": "accepted",
        "change_summary": "Initial synthetic profile.",
    }
    history_path = round_dir / "work/calibration/reviewer_calibration_profile_history.jsonl"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(json.dumps(entry) + "\n", encoding="utf-8")

    errors = validate_opponent_calibration_artifact(
        round_dir, "work/calibration/reviewer_calibration_profile_history.jsonl"
    )

    assert any("source_case_refs must not be empty" in error for error in errors)


def test_validate_profile_history_requires_operator_approval_for_refresh(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    write_json(round_dir / "work/calibration/historical_case_analyses/case-001.json", historical_case_payload())
    write_profile_snapshot(round_dir, 2)
    entry = {
        **common_fields("opponent-reviewer-calibration-history-v1"),
        "profile_version": 2,
        "previous_profile_markdown_sha256": "a" * 64,
        "previous_history_entry_sha256": "d" * 64,
        "profile_snapshot_path": "work/calibration/profile_versions/v2.md",
        "profile_markdown_sha256": "b" * 64,
        "profile_manifest_sha256": "c" * 64,
        "source_case_refs": ["work/calibration/historical_case_analyses/case-001.json"],
        "review_status": "reviewed",
        "change_summary": "Refreshed synthetic profile.",
    }
    history_path = round_dir / "work/calibration/reviewer_calibration_profile_history.jsonl"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(json.dumps(entry) + "\n", encoding="utf-8")

    errors = validate_opponent_calibration_artifact(
        round_dir, "work/calibration/reviewer_calibration_profile_history.jsonl"
    )

    assert any("operator_approval must be object" in error for error in errors)


def test_profile_binding_requires_two_used_historical_analyses(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    analysis_refs = [
        "work/calibration/historical_case_analyses/case-001.json",
        "work/calibration/historical_case_analyses/case-002.json",
    ]
    for rel_path in analysis_refs:
        case_id = rel_path.rsplit("/", maxsplit=1)[1].removesuffix(".json")
        write_json(round_dir / rel_path, historical_case_payload_for(case_id))
    profile_path = round_dir / "outputs/reviewer_calibration_profile.md"
    write_profile_snapshot(round_dir, 1)
    profile = {
        **common_fields("opponent-reviewer-calibration-profile-v1"),
        "source_refs": analysis_refs[:1],
        "profile_markdown_path": "outputs/reviewer_calibration_profile.md",
        "profile_markdown_sha256": sha256_file(profile_path),
        "profile_applicability": {"confident": ["synthetic software engineering"]},
        "source_case_refs": analysis_refs[:1],
        "profile_version": 1,
        "profile_previous_sha256": None,
        "profile_change_summary": "Initial synthetic profile.",
        "confidence_by_dimension": confidence_by_dimension(),
        "do_not_use_for": ["current-case conclusions without evidence"],
    }
    profile_manifest = round_dir / "work/calibration/reviewer_calibration_profile.json"
    write_json(profile_manifest, profile)
    history = {
        **common_fields("opponent-reviewer-calibration-history-v1"),
        "source_refs": analysis_refs[:1],
        "profile_version": 1,
        "previous_profile_markdown_sha256": None,
        "previous_history_entry_sha256": None,
        "profile_snapshot_path": "work/calibration/profile_versions/v1.md",
        "profile_markdown_sha256": sha256_file(profile_path),
        "profile_manifest_sha256": sha256_file(profile_manifest),
        "source_case_refs": analysis_refs[:1],
        "review_status": "reviewed",
        "change_summary": "Initial synthetic profile.",
    }
    history_path = round_dir / "work/calibration/reviewer_calibration_profile_history.jsonl"
    history_path.write_text(json.dumps(history) + "\n", encoding="utf-8")

    errors = profile_binding_errors(round_dir, profile, analysis_refs)

    assert any(
        "source_case_refs: must reference at least two distinct historical case analyses" in error for error in errors
    )


def test_profile_binding_rejects_stale_latest_history(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    analysis_refs = [
        "work/calibration/historical_case_analyses/case-001.json",
        "work/calibration/historical_case_analyses/case-002.json",
    ]
    for rel_path in analysis_refs:
        case_id = rel_path.rsplit("/", maxsplit=1)[1].removesuffix(".json")
        write_json(round_dir / rel_path, historical_case_payload_for(case_id))
    profile_path = round_dir / "outputs/reviewer_calibration_profile.md"
    profile = {
        **common_fields("opponent-reviewer-calibration-profile-v1"),
        "source_refs": analysis_refs,
        "profile_markdown_path": "outputs/reviewer_calibration_profile.md",
        "profile_markdown_sha256": sha256_file(profile_path),
        "profile_applicability": {"confident": ["synthetic software engineering"]},
        "source_case_refs": analysis_refs,
        "profile_version": 2,
        "profile_previous_sha256": "a" * 64,
        "profile_change_summary": "Second synthetic profile.",
        "confidence_by_dimension": confidence_by_dimension(),
        "do_not_use_for": ["current-case conclusions without evidence"],
    }
    profile_manifest = round_dir / "work/calibration/reviewer_calibration_profile.json"
    write_json(profile_manifest, profile)
    history_entries = [
        {
            **common_fields("opponent-reviewer-calibration-history-v1"),
            "source_refs": analysis_refs,
            "profile_version": 2,
            "previous_profile_markdown_sha256": "a" * 64,
            "profile_markdown_sha256": "b" * 64,
            "profile_manifest_sha256": "c" * 64,
            "source_case_refs": analysis_refs,
            "review_status": "reviewed",
            "change_summary": "Second synthetic profile.",
        },
        {
            **common_fields("opponent-reviewer-calibration-history-v1"),
            "source_refs": analysis_refs,
            "profile_version": 1,
            "previous_profile_markdown_sha256": None,
            "profile_markdown_sha256": "d" * 64,
            "profile_manifest_sha256": "e" * 64,
            "source_case_refs": analysis_refs,
            "review_status": "reviewed",
            "change_summary": "Out-of-order stale entry.",
        },
    ]
    history_path = round_dir / "work/calibration/reviewer_calibration_profile_history.jsonl"
    history_path.write_text("\n".join(json.dumps(entry) for entry in history_entries) + "\n", encoding="utf-8")

    errors = profile_binding_errors(round_dir, profile, analysis_refs)

    assert any("profile_version entries must be append-only sequence [1, 2]" in error for error in errors)
    assert any("latest profile_version does not match profile manifest" in error for error in errors)
    assert any("latest profile_markdown_sha256 is stale" in error for error in errors)
    assert any("latest profile_manifest_sha256 is stale" in error for error in errors)


def test_profile_binding_rejects_refresh_source_drop_and_stale_previous_hash(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    case_003_input = round_dir / "inputs/historical_cases/case-003/opponent_report.md"
    case_003_input.parent.mkdir(parents=True, exist_ok=True)
    case_003_input.write_text("synthetic fixture\n", encoding="utf-8")
    initial_refs = [
        "work/calibration/historical_case_analyses/case-001.json",
        "work/calibration/historical_case_analyses/case-002.json",
    ]
    refreshed_refs = [
        "work/calibration/historical_case_analyses/case-002.json",
        "work/calibration/historical_case_analyses/case-003.json",
    ]
    all_refs = sorted(set(initial_refs + refreshed_refs))
    for rel_path in all_refs:
        case_id = rel_path.rsplit("/", maxsplit=1)[1].removesuffix(".json")
        write_json(round_dir / rel_path, historical_case_payload_for(case_id))
    profile_path = round_dir / "outputs/reviewer_calibration_profile.md"
    previous_snapshot = write_profile_snapshot(round_dir, 1, "previous synthetic profile\n")
    write_profile_snapshot(round_dir, 2)
    profile = {
        **common_fields("opponent-reviewer-calibration-profile-v1"),
        "source_refs": refreshed_refs,
        "profile_markdown_path": "outputs/reviewer_calibration_profile.md",
        "profile_markdown_sha256": sha256_file(profile_path),
        "profile_applicability": {"confident": ["synthetic software engineering"]},
        "source_case_refs": refreshed_refs,
        "profile_version": 2,
        "profile_previous_sha256": "f" * 64,
        "profile_change_summary": "Refreshed synthetic profile.",
        "operator_approval": operator_approval(),
        "confidence_by_dimension": confidence_by_dimension(),
        "do_not_use_for": ["current-case conclusions without evidence"],
    }
    profile_manifest = round_dir / "work/calibration/reviewer_calibration_profile.json"
    write_json(profile_manifest, profile)
    previous_hash = sha256_file(previous_snapshot)
    first_entry = {
        **common_fields("opponent-reviewer-calibration-history-v1"),
        "source_refs": initial_refs,
        "profile_version": 1,
        "previous_profile_markdown_sha256": None,
        "previous_history_entry_sha256": None,
        "profile_snapshot_path": "work/calibration/profile_versions/v1.md",
        "profile_markdown_sha256": previous_hash,
        "profile_manifest_sha256": "b" * 64,
        "source_case_refs": initial_refs,
        "review_status": "reviewed",
        "change_summary": "Initial synthetic profile.",
    }
    second_entry = {
        **common_fields("opponent-reviewer-calibration-history-v1"),
        "source_refs": refreshed_refs,
        "profile_version": 2,
        "previous_profile_markdown_sha256": "e" * 64,
        "previous_history_entry_sha256": jsonl_entry_sha256(first_entry),
        "profile_snapshot_path": "work/calibration/profile_versions/v2.md",
        "profile_markdown_sha256": sha256_file(profile_path),
        "profile_manifest_sha256": sha256_file(profile_manifest),
        "source_case_refs": refreshed_refs,
        "review_status": "reviewed",
        "change_summary": "Refreshed synthetic profile.",
        "operator_approval": operator_approval(),
    }
    history_entries = [first_entry, second_entry]
    history_path = round_dir / "work/calibration/reviewer_calibration_profile_history.jsonl"
    history_path.write_text("\n".join(json.dumps(entry) for entry in history_entries) + "\n", encoding="utf-8")

    errors = profile_binding_errors(round_dir, profile, all_refs)

    assert any(
        "refresh dropped source case ref work/calibration/historical_case_analyses/case-001.json" in error
        for error in errors
    )
    assert any("profile_previous_sha256 is stale" in error for error in errors)
    assert any("latest previous_profile_markdown_sha256 is stale" in error for error in errors)
    assert any("approved_profile_markdown_sha256 does not match current profile" in error for error in errors)


def test_profile_binding_rejects_stale_history_entry_chain(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    analysis_refs = [
        "work/calibration/historical_case_analyses/case-001.json",
        "work/calibration/historical_case_analyses/case-002.json",
    ]
    for rel_path in analysis_refs:
        case_id = rel_path.rsplit("/", maxsplit=1)[1].removesuffix(".json")
        write_json(round_dir / rel_path, historical_case_payload_for(case_id))
    profile_path = round_dir / "outputs/reviewer_calibration_profile.md"
    previous_snapshot = write_profile_snapshot(round_dir, 1, "previous synthetic profile\n")
    write_profile_snapshot(round_dir, 2)
    previous_hash = sha256_file(previous_snapshot)
    current_hash = sha256_file(profile_path)
    profile = {
        **common_fields("opponent-reviewer-calibration-profile-v1"),
        "source_refs": analysis_refs,
        "profile_markdown_path": "outputs/reviewer_calibration_profile.md",
        "profile_markdown_sha256": current_hash,
        "profile_applicability": {"confident": ["synthetic software engineering"]},
        "source_case_refs": analysis_refs,
        "profile_version": 2,
        "profile_previous_sha256": previous_hash,
        "profile_change_summary": "Refreshed synthetic profile.",
        "confidence_by_dimension": confidence_by_dimension(),
        "do_not_use_for": ["current-case conclusions without evidence"],
    }
    profile_manifest = round_dir / "work/calibration/reviewer_calibration_profile.json"
    write_json(profile_manifest, profile)
    manifest_hash = sha256_file(profile_manifest)
    first_entry = {
        **common_fields("opponent-reviewer-calibration-history-v1"),
        "source_refs": analysis_refs,
        "profile_version": 1,
        "previous_profile_markdown_sha256": None,
        "previous_history_entry_sha256": None,
        "profile_snapshot_path": "work/calibration/profile_versions/v1.md",
        "profile_markdown_sha256": previous_hash,
        "profile_manifest_sha256": "b" * 64,
        "source_case_refs": analysis_refs,
        "review_status": "reviewed",
        "change_summary": "Initial synthetic profile.",
    }
    second_entry = {
        **common_fields("opponent-reviewer-calibration-history-v1"),
        "source_refs": analysis_refs,
        "profile_version": 2,
        "previous_profile_markdown_sha256": previous_hash,
        "previous_history_entry_sha256": "f" * 64,
        "profile_snapshot_path": "work/calibration/profile_versions/v2.md",
        "profile_markdown_sha256": current_hash,
        "profile_manifest_sha256": manifest_hash,
        "source_case_refs": analysis_refs,
        "review_status": "reviewed",
        "change_summary": "Refreshed synthetic profile.",
        "operator_approval": operator_approval(
            version=2,
            profile_hash=current_hash,
            manifest_hash=manifest_hash,
        ),
    }
    history_path = round_dir / "work/calibration/reviewer_calibration_profile_history.jsonl"
    history_path.write_text(
        "\n".join(json.dumps(entry) for entry in (first_entry, second_entry)) + "\n", encoding="utf-8"
    )

    errors = profile_binding_errors(round_dir, profile, analysis_refs)

    assert any("previous_history_entry_sha256 is stale" in error for error in errors)


def test_profile_binding_rejects_dirty_genesis_history_entry(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    analysis_refs = [
        "work/calibration/historical_case_analyses/case-001.json",
        "work/calibration/historical_case_analyses/case-002.json",
    ]
    for rel_path in analysis_refs:
        case_id = rel_path.rsplit("/", maxsplit=1)[1].removesuffix(".json")
        write_json(round_dir / rel_path, historical_case_payload_for(case_id))
    profile_path = round_dir / "outputs/reviewer_calibration_profile.md"
    previous_snapshot = write_profile_snapshot(round_dir, 1, "previous synthetic profile\n")
    write_profile_snapshot(round_dir, 2)
    previous_hash = sha256_file(previous_snapshot)
    current_hash = sha256_file(profile_path)
    profile = {
        **common_fields("opponent-reviewer-calibration-profile-v1"),
        "source_refs": analysis_refs,
        "profile_markdown_path": "outputs/reviewer_calibration_profile.md",
        "profile_markdown_sha256": current_hash,
        "profile_applicability": {"confident": ["synthetic software engineering"]},
        "source_case_refs": analysis_refs,
        "profile_version": 2,
        "profile_previous_sha256": previous_hash,
        "profile_change_summary": "Refreshed synthetic profile.",
        "confidence_by_dimension": confidence_by_dimension(),
        "do_not_use_for": ["current-case conclusions without evidence"],
    }
    profile_manifest = round_dir / "work/calibration/reviewer_calibration_profile.json"
    write_json(profile_manifest, profile)
    manifest_hash = sha256_file(profile_manifest)
    first_entry = {
        **common_fields("opponent-reviewer-calibration-history-v1"),
        "source_refs": analysis_refs,
        "profile_version": 1,
        "previous_profile_markdown_sha256": "e" * 64,
        "previous_history_entry_sha256": "f" * 64,
        "profile_snapshot_path": "work/calibration/profile_versions/v1.md",
        "profile_markdown_sha256": previous_hash,
        "profile_manifest_sha256": "b" * 64,
        "source_case_refs": analysis_refs,
        "review_status": "reviewed",
        "change_summary": "Initial synthetic profile.",
    }
    second_entry = {
        **common_fields("opponent-reviewer-calibration-history-v1"),
        "source_refs": analysis_refs,
        "profile_version": 2,
        "previous_profile_markdown_sha256": previous_hash,
        "previous_history_entry_sha256": jsonl_entry_sha256(first_entry),
        "profile_snapshot_path": "work/calibration/profile_versions/v2.md",
        "profile_markdown_sha256": current_hash,
        "profile_manifest_sha256": manifest_hash,
        "source_case_refs": analysis_refs,
        "review_status": "reviewed",
        "change_summary": "Refreshed synthetic profile.",
        "operator_approval": operator_approval(
            version=2,
            profile_hash=current_hash,
            manifest_hash=manifest_hash,
        ),
    }
    history_path = round_dir / "work/calibration/reviewer_calibration_profile_history.jsonl"
    history_path.write_text(
        "\n".join(json.dumps(entry) for entry in (first_entry, second_entry)) + "\n", encoding="utf-8"
    )

    errors = profile_binding_errors(round_dir, profile, analysis_refs)

    assert any("genesis previous_profile_markdown_sha256 must be null" in error for error in errors)
    assert any("genesis previous_history_entry_sha256 must be null" in error for error in errors)


def test_profile_binding_rejects_dirty_intermediate_refresh_entry(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    case_003_input = round_dir / "inputs/historical_cases/case-003/opponent_report.md"
    case_003_input.parent.mkdir(parents=True, exist_ok=True)
    case_003_input.write_text("synthetic fixture\n", encoding="utf-8")
    analysis_refs = [
        "work/calibration/historical_case_analyses/case-001.json",
        "work/calibration/historical_case_analyses/case-002.json",
        "work/calibration/historical_case_analyses/case-003.json",
    ]
    for rel_path in analysis_refs:
        case_id = rel_path.rsplit("/", maxsplit=1)[1].removesuffix(".json")
        write_json(round_dir / rel_path, historical_case_payload_for(case_id))
    snapshot_1 = write_profile_snapshot(round_dir, 1, "profile v1\n")
    snapshot_2 = write_profile_snapshot(round_dir, 2, "profile v2\n")
    snapshot_3 = write_profile_snapshot(round_dir, 3)
    profile_path = round_dir / "outputs/reviewer_calibration_profile.md"
    current_hash = sha256_file(profile_path)
    profile = {
        **common_fields("opponent-reviewer-calibration-profile-v1"),
        "source_refs": analysis_refs,
        "profile_markdown_path": "outputs/reviewer_calibration_profile.md",
        "profile_markdown_sha256": current_hash,
        "profile_applicability": {"confident": ["synthetic software engineering"]},
        "source_case_refs": analysis_refs,
        "profile_version": 3,
        "profile_previous_sha256": sha256_file(snapshot_2),
        "profile_change_summary": "Third synthetic profile.",
        "confidence_by_dimension": confidence_by_dimension(),
        "do_not_use_for": ["current-case conclusions without evidence"],
    }
    profile_manifest = round_dir / "work/calibration/reviewer_calibration_profile.json"
    write_json(profile_manifest, profile)
    manifest_hash = sha256_file(profile_manifest)
    first_entry = {
        **common_fields("opponent-reviewer-calibration-history-v1"),
        "source_refs": analysis_refs[:2],
        "profile_version": 1,
        "previous_profile_markdown_sha256": None,
        "previous_history_entry_sha256": None,
        "profile_snapshot_path": "work/calibration/profile_versions/v1.md",
        "profile_markdown_sha256": sha256_file(snapshot_1),
        "profile_manifest_sha256": "a" * 64,
        "source_case_refs": analysis_refs[:2],
        "review_status": "reviewed",
        "change_summary": "Initial synthetic profile.",
    }
    second_entry = {
        **common_fields("opponent-reviewer-calibration-history-v1"),
        "source_refs": analysis_refs,
        "profile_version": 2,
        "previous_profile_markdown_sha256": "e" * 64,
        "previous_history_entry_sha256": jsonl_entry_sha256(first_entry),
        "profile_snapshot_path": "work/calibration/profile_versions/v2.md",
        "profile_markdown_sha256": sha256_file(snapshot_2),
        "profile_manifest_sha256": "b" * 64,
        "source_case_refs": analysis_refs,
        "review_status": "reviewed",
        "change_summary": "Second synthetic profile.",
        "operator_approval": operator_approval(
            version=99,
            profile_hash="f" * 64,
            manifest_hash="d" * 64,
        ),
    }
    third_entry = {
        **common_fields("opponent-reviewer-calibration-history-v1"),
        "source_refs": analysis_refs,
        "profile_version": 3,
        "previous_profile_markdown_sha256": sha256_file(snapshot_2),
        "previous_history_entry_sha256": jsonl_entry_sha256(second_entry),
        "profile_snapshot_path": "work/calibration/profile_versions/v3.md",
        "profile_markdown_sha256": sha256_file(snapshot_3),
        "profile_manifest_sha256": manifest_hash,
        "source_case_refs": analysis_refs,
        "review_status": "reviewed",
        "change_summary": "Third synthetic profile.",
        "operator_approval": operator_approval(
            version=3,
            profile_hash=current_hash,
            manifest_hash=manifest_hash,
        ),
    }
    history_path = round_dir / "work/calibration/reviewer_calibration_profile_history.jsonl"
    history_path.write_text(
        "\n".join(json.dumps(entry) for entry in (first_entry, second_entry, third_entry)) + "\n",
        encoding="utf-8",
    )

    errors = profile_binding_errors(round_dir, profile, analysis_refs)

    assert any("version 2 previous_profile_markdown_sha256 is stale" in error for error in errors)
    assert any("version 2 operator_approval: approved_profile_version does not match" in error for error in errors)
    assert any(
        "version 2 operator_approval: approved_profile_markdown_sha256 does not match" in error for error in errors
    )


def test_profile_binding_rejects_dropped_history_source_refs(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    case_003_input = round_dir / "inputs/historical_cases/case-003/opponent_report.md"
    case_003_input.parent.mkdir(parents=True, exist_ok=True)
    case_003_input.write_text("synthetic fixture\n", encoding="utf-8")
    analysis_refs = [
        "work/calibration/historical_case_analyses/case-001.json",
        "work/calibration/historical_case_analyses/case-002.json",
        "work/calibration/historical_case_analyses/case-003.json",
    ]
    for rel_path in analysis_refs:
        case_id = rel_path.rsplit("/", maxsplit=1)[1].removesuffix(".json")
        write_json(round_dir / rel_path, historical_case_payload_for(case_id))
    snapshot_1 = write_profile_snapshot(round_dir, 1, "profile v1\n")
    snapshot_2 = write_profile_snapshot(round_dir, 2)
    profile_path = round_dir / "outputs/reviewer_calibration_profile.md"
    current_hash = sha256_file(profile_path)
    profile = {
        **common_fields("opponent-reviewer-calibration-profile-v1"),
        "source_refs": analysis_refs,
        "profile_markdown_path": "outputs/reviewer_calibration_profile.md",
        "profile_markdown_sha256": current_hash,
        "profile_applicability": {"confident": ["synthetic software engineering"]},
        "source_case_refs": analysis_refs,
        "profile_version": 2,
        "profile_previous_sha256": sha256_file(snapshot_1),
        "profile_change_summary": "Refreshed synthetic profile.",
        "confidence_by_dimension": confidence_by_dimension(),
        "do_not_use_for": ["current-case conclusions without evidence"],
    }
    profile_manifest = round_dir / "work/calibration/reviewer_calibration_profile.json"
    write_json(profile_manifest, profile)
    manifest_hash = sha256_file(profile_manifest)
    first_entry = {
        **common_fields("opponent-reviewer-calibration-history-v1"),
        "source_refs": analysis_refs,
        "profile_version": 1,
        "previous_profile_markdown_sha256": None,
        "previous_history_entry_sha256": None,
        "profile_snapshot_path": "work/calibration/profile_versions/v1.md",
        "profile_markdown_sha256": sha256_file(snapshot_1),
        "profile_manifest_sha256": "a" * 64,
        "source_case_refs": analysis_refs,
        "review_status": "reviewed",
        "change_summary": "Initial synthetic profile.",
    }
    second_entry = {
        **common_fields("opponent-reviewer-calibration-history-v1"),
        "source_refs": analysis_refs[1:],
        "profile_version": 2,
        "previous_profile_markdown_sha256": sha256_file(snapshot_1),
        "previous_history_entry_sha256": jsonl_entry_sha256(first_entry),
        "profile_snapshot_path": "work/calibration/profile_versions/v2.md",
        "profile_markdown_sha256": sha256_file(snapshot_2),
        "profile_manifest_sha256": manifest_hash,
        "source_case_refs": analysis_refs,
        "review_status": "reviewed",
        "change_summary": "Refreshed synthetic profile.",
        "operator_approval": operator_approval(
            version=2,
            profile_hash=sha256_file(snapshot_2),
            manifest_hash=manifest_hash,
        ),
    }
    history_path = round_dir / "work/calibration/reviewer_calibration_profile_history.jsonl"
    history_path.write_text(
        "\n".join(json.dumps(entry) for entry in (first_entry, second_entry)) + "\n",
        encoding="utf-8",
    )

    errors = profile_binding_errors(round_dir, profile, analysis_refs)

    assert any(
        "refresh dropped source ref work/calibration/historical_case_analyses/case-001.json" in error
        for error in errors
    )


def test_validate_opponent_calibration_use_binds_current_case_artifacts(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = calibration_use_payload(round_dir)
    write_json(round_dir / "work/opponent_calibration_use.json", payload)

    errors = validate_opponent_calibration_artifact(
        round_dir,
        "work/opponent_calibration_use.json",
        case_id="calibration-case",
        round_id="round-a",
    )

    assert errors == []


def test_validate_opponent_calibration_use_rejects_stale_trace_and_approval(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = calibration_use_payload(round_dir)
    (round_dir / "work/opponent_report_trace.json").write_text("changed\n", encoding="utf-8")
    approval = dict(payload["operator_approval"]) if isinstance(payload["operator_approval"], dict) else {}
    approval["approved_trace_sha256"] = "0" * 64
    payload["operator_approval"] = approval
    write_json(round_dir / "work/opponent_calibration_use.json", payload)

    errors = validate_opponent_calibration_artifact(round_dir, "work/opponent_calibration_use.json")

    assert any("opponent_report_trace_sha256 is stale" in error for error in errors)
    assert any("operator_approval.approved_trace_sha256 is stale" in error for error in errors)


def test_validate_opponent_calibration_use_rejects_direct_stale_source_materials_hash(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = calibration_use_payload(round_dir)
    (round_dir / "outputs/oponent_podklady_revidovane.md").write_text("changed materials\n", encoding="utf-8")
    write_json(round_dir / "work/opponent_calibration_use.json", payload)

    errors = validate_opponent_calibration_artifact(round_dir, "work/opponent_calibration_use.json")

    assert any("work/opponent_calibration_use.json: source_materials_sha256 is stale" in error for error in errors)


def test_validate_opponent_calibration_use_rejects_direct_stale_profile_hash(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = calibration_use_payload(round_dir)
    profile_path = round_dir / "work/calibration/reviewer_calibration_profile.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    profile["profile_change_summary"] = "Changed synthetic profile."
    write_json(profile_path, profile)
    write_json(round_dir / "work/opponent_calibration_use.json", payload)

    errors = validate_opponent_calibration_artifact(round_dir, "work/opponent_calibration_use.json")

    assert any("profile_manifest_sha256 is stale" in error for error in errors)


def test_validate_opponent_calibration_use_rejects_direct_stale_checklist_hash(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = calibration_use_payload(round_dir)
    checklist_path = round_dir / "work/calibration/reviewer_checklist.json"
    checklist = json.loads(checklist_path.read_text(encoding="utf-8"))
    checklist["checklist_items"][0]["prompt"] = "Changed synthetic prompt."
    write_json(checklist_path, checklist)
    write_json(round_dir / "work/opponent_calibration_use.json", payload)

    errors = validate_opponent_calibration_artifact(round_dir, "work/opponent_calibration_use.json")

    assert any("checklist_sha256 is stale" in error for error in errors)


def test_validate_opponent_calibration_use_rejects_unaccepted_trace_with_matching_hash(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = calibration_use_payload(round_dir)
    trace_path = round_dir / "work/opponent_report_trace.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    trace["trace_review_status"] = "draft"
    write_json(trace_path, trace)
    trace_hash = sha256_file(trace_path)
    payload["opponent_report_trace_sha256"] = trace_hash
    refresh_current_case_approval(payload, "approved_trace_sha256", trace_hash)
    write_json(round_dir / "work/opponent_calibration_use.json", payload)

    errors = validate_opponent_calibration_artifact(round_dir, "work/opponent_calibration_use.json")

    assert not any("opponent_report_trace_sha256 is stale" in error for error in errors)
    assert any("trace_review_status must be one of accepted" in error for error in errors)


def test_validate_opponent_calibration_use_rejects_trace_with_stale_source_hash(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = calibration_use_payload(round_dir)
    materials_path = round_dir / "outputs/oponent_podklady_revidovane.md"
    materials_path.write_text("changed materials\n", encoding="utf-8")
    materials_hash = sha256_file(materials_path)
    payload["source_materials_sha256"] = materials_hash
    refresh_current_case_approval(payload, "approved_source_materials_sha256", materials_hash)
    write_json(round_dir / "work/opponent_calibration_use.json", payload)

    errors = validate_opponent_calibration_artifact(round_dir, "work/opponent_calibration_use.json")

    assert not any("work/opponent_calibration_use.json: source_materials_sha256 is stale" in error for error in errors)
    assert any("work/opponent_report_trace.json: source_materials_sha256 is stale" in error for error in errors)


def test_validate_opponent_calibration_use_rejects_invalid_selected_profile(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = calibration_use_payload(round_dir)
    profile_path = round_dir / "work/calibration/reviewer_calibration_profile.json"
    write_json(profile_path, {})
    profile_hash = sha256_file(profile_path)
    payload["profile_manifest_sha256"] = profile_hash
    refresh_current_case_approval(payload, "approved_profile_manifest_sha256", profile_hash)
    write_json(round_dir / "work/opponent_calibration_use.json", payload)

    errors = validate_opponent_calibration_artifact(round_dir, "work/opponent_calibration_use.json")

    assert not any("profile_manifest_sha256 is stale" in error for error in errors)
    assert any("schema_version must be opponent-reviewer-calibration-profile-v1" in error for error in errors)


def test_validate_opponent_calibration_use_rejects_invalid_selected_checklist(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = calibration_use_payload(round_dir)
    checklist_path = round_dir / "work/calibration/reviewer_checklist.json"
    write_json(checklist_path, {})
    checklist_hash = sha256_file(checklist_path)
    payload["checklist_sha256"] = checklist_hash
    refresh_current_case_approval(payload, "approved_checklist_sha256", checklist_hash)
    write_json(round_dir / "work/opponent_calibration_use.json", payload)

    errors = validate_opponent_calibration_artifact(round_dir, "work/opponent_calibration_use.json")

    assert not any("checklist_sha256 is stale" in error for error in errors)
    assert any("schema_version must be opponent-reviewer-checklist-v1" in error for error in errors)


def test_validate_opponent_calibration_use_requires_selected_profile_version_match(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = calibration_use_payload(round_dir)
    payload["selected_profile_version"] = 99
    write_json(round_dir / "work/opponent_calibration_use.json", payload)

    errors = validate_opponent_calibration_artifact(round_dir, "work/opponent_calibration_use.json")

    assert any("selected_profile_version must match profile_manifest profile_version" in error for error in errors)


def test_validate_opponent_calibration_use_keeps_reviewer_profile_gate_separate(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = calibration_use_payload(round_dir)
    payload["reviewer_profile_gate"] = {
        "required": False,
        "satisfied_by_historical_calibration": True,
    }
    write_json(round_dir / "work/opponent_calibration_use.json", payload)

    errors = validate_opponent_calibration_artifact(round_dir, "work/opponent_calibration_use.json")

    assert any("reviewer_profile_gate.required must be true" in error for error in errors)
    assert any("reviewer_profile_gate.satisfied_by_historical_calibration must be false" in error for error in errors)


def test_current_case_calibration_cannot_satisfy_reviewer_profile_readiness(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "repo"
    case_dir = root / "cases" / "calibration-case"
    round_dir = case_dir / "rounds" / "round-a"
    (root / "profiles").mkdir(parents=True)
    (root / "profiles" / "default.md").write_text("# Default profile\n", encoding="utf-8")
    case_dir.mkdir(parents=True)
    (case_dir / "case.md").write_text("Reviewer profile: local/missing\n", encoding="utf-8")
    (case_dir / "current-round.txt").write_text("round-a\n", encoding="utf-8")
    payload = calibration_use_payload(round_dir)
    write_json(round_dir / "work/opponent_calibration_use.json", payload)
    assert (
        validate_opponent_calibration_artifact(
            round_dir,
            "work/opponent_calibration_use.json",
            case_id="calibration-case",
            round_id="round-a",
        )
        == []
    )

    def run_reviewer_profile(root_path: Path, label: str, args: list[str], *, required: bool = True) -> Step:
        monkeypatch.setattr(check_reviewer_profile, "repo_root", lambda: root_path)
        return Step(label, args, check_reviewer_profile.main(args), "", required)

    monkeypatch.setattr(check_round_ready, "repo_root", lambda: root)
    monkeypatch.setattr(check_round_ready, "run_step", run_reviewer_profile)

    assert check_round_ready.main(["scripts/check-round-ready", "calibration-case", "round-a"]) == 1


def test_validate_opponent_calibration_advisory_is_non_blocking(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = calibration_advisory_payload(round_dir)
    write_json(round_dir / "work/opponent_calibration_advisory.json", payload)

    errors = validate_opponent_calibration_artifact(round_dir, "work/opponent_calibration_advisory.json")

    assert errors == []


def test_validate_opponent_calibration_advisory_rejects_unaccepted_trace_with_matching_hash(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = calibration_advisory_payload(round_dir)
    trace_path = round_dir / "work/opponent_report_trace.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    trace["trace_review_status"] = "draft"
    write_json(trace_path, trace)
    payload["opponent_report_trace_sha256"] = sha256_file(trace_path)
    write_json(round_dir / "work/opponent_calibration_advisory.json", payload)

    errors = validate_opponent_calibration_artifact(round_dir, "work/opponent_calibration_advisory.json")

    assert not any("opponent_report_trace_sha256 is stale" in error for error in errors)
    assert any("trace_review_status must be one of accepted" in error for error in errors)


def test_validate_opponent_calibration_advisory_rejects_gate_like_status(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = {
        **calibration_advisory_payload(round_dir),
        "advisory_status": "blocking",
        "normal_workflow_continues": False,
    }
    write_json(round_dir / "work/opponent_calibration_advisory.json", payload)

    errors = validate_opponent_calibration_artifact(round_dir, "work/opponent_calibration_advisory.json")

    assert any("advisory_status must be non_blocking" in error for error in errors)
    assert any("normal_workflow_continues must be true" in error for error in errors)


def test_validate_opponent_report_revision_request_binds_current_case_artifacts(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = revision_request_payload(round_dir, use_calibration=False)
    write_json(round_dir / "work/opponent_report_revision_request.json", payload)

    errors = validate_opponent_calibration_artifact(
        round_dir,
        "work/opponent_report_revision_request.json",
        case_id="calibration-case",
        round_id="round-a",
    )

    assert errors == []


def test_validate_opponent_report_revision_request_accepts_nonblocking_advisory(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = revision_request_payload(round_dir, use_calibration=False)
    write_json(round_dir / "work/opponent_report_revision_request.json", payload)

    errors = validate_opponent_calibration_artifact(round_dir, "work/opponent_report_revision_request.json")

    assert errors == []


def test_validate_opponent_report_revision_request_rejects_stale_feedback_and_packet(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = revision_request_payload(round_dir)
    (round_dir / "notes/opponent-report-operator-feedback.md").write_text("changed feedback\n", encoding="utf-8")
    (round_dir / "outputs/opponent_reading_packet.md").write_text("changed packet\n", encoding="utf-8")
    write_json(round_dir / "work/opponent_report_revision_request.json", payload)

    errors = validate_opponent_calibration_artifact(round_dir, "work/opponent_report_revision_request.json")

    assert any("operator_feedback_sha256 is stale" in error for error in errors)
    assert any("opponent_reading_packet_sha256 is stale" in error for error in errors)


def test_validate_opponent_report_revision_request_rejects_stale_pre_revision_report_draft(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = revision_request_payload(round_dir)
    (round_dir / "work/opponent_report_revision_sources/oponent_posudek_draft.md").write_text(
        "changed draft\n",
        encoding="utf-8",
    )
    write_json(round_dir / "work/opponent_report_revision_request.json", payload)

    errors = validate_opponent_calibration_artifact(round_dir, "work/opponent_report_revision_request.json")

    assert any("opponent_report_draft_sha256 is stale" in error for error in errors)


def test_validate_opponent_report_revision_request_survives_active_trace_and_draft_rewrite(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = revision_request_payload(round_dir)
    write_json(round_dir / "work/opponent_report_revision_request.json", payload)
    rewritten_trace = opponent_trace_payload(sha256_file(round_dir / "outputs/oponent_podklady_revidovane.md"))
    rewritten_trace["reviewed_at"] = "2026-05-07T00:02:00Z"
    write_json(
        round_dir / "work/opponent_report_trace.json",
        rewritten_trace,
    )
    (round_dir / "work/oponent_posudek_draft.md").write_text("revised draft\n", encoding="utf-8")

    errors = validate_opponent_calibration_artifact(round_dir, "work/opponent_report_revision_request.json")

    assert errors == []


def test_validate_opponent_report_revision_request_ignores_snapshot_calibration_context_cycle(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = revision_request_payload(round_dir, use_calibration=False)
    trace_snapshot_path = round_dir / "work/opponent_report_revision_sources/opponent_report_trace.json"
    trace_snapshot = json.loads(trace_snapshot_path.read_text(encoding="utf-8"))
    trace_snapshot["calibration_context"] = {
        "calibration_advisory_path": "work/opponent_calibration_advisory.json",
        "calibration_advisory_sha256": payload["calibration_advisory_sha256"],
        "reference_report_comparison_path": "outputs/reference_report_comparison.md",
        "reference_report_comparison_sha256": payload["reference_report_comparison_sha256"],
        "opponent_reading_packet_path": "outputs/opponent_reading_packet.md",
        "opponent_reading_packet_sha256": payload["opponent_reading_packet_sha256"],
        "revision_request_path": "work/opponent_report_revision_request.json",
        "revision_request_sha256": "0" * 64,
        "revision_applied": True,
        "anti_overfit_review_status": "reviewed",
        "anti_overfit_reviewer_role": "previous-reviewer",
        "anti_overfit_reviewer_agent": "previous-agent",
        "reviewed_at": "2026-05-07T00:02:00Z",
        "limitations": [],
    }
    write_json(trace_snapshot_path, trace_snapshot)
    payload["opponent_report_trace_sha256"] = sha256_file(trace_snapshot_path)
    write_json(round_dir / "work/opponent_report_revision_request.json", payload)

    errors = validate_opponent_calibration_artifact(round_dir, "work/opponent_report_revision_request.json")

    assert errors == []


def test_validate_opponent_report_revision_request_rejects_unknown_feedback_category(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = revision_request_payload(round_dir)
    feedback_items = payload["feedback_items"]
    assert isinstance(feedback_items, list)
    assert isinstance(feedback_items[0], dict)
    feedback_items[0]["category"] = "contains_word_bad"
    write_json(round_dir / "work/opponent_report_revision_request.json", payload)

    errors = validate_opponent_calibration_artifact(round_dir, "work/opponent_report_revision_request.json")

    assert any("category must be one of" in error for error in errors)
    assert any("grading_calibration" in error for error in errors)


def test_validate_opponent_report_revision_request_requires_one_calibration_context(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = revision_request_payload(round_dir)
    payload.pop("calibration_use_path")
    payload.pop("calibration_use_sha256")
    write_json(round_dir / "work/opponent_report_revision_request.json", payload)

    errors = validate_opponent_calibration_artifact(round_dir, "work/opponent_report_revision_request.json")

    assert any(
        "exactly one of calibration_use or calibration_advisory binding is required" in error for error in errors
    )

    payload = revision_request_payload(round_dir, use_calibration=False)
    use_payload = calibration_use_payload(round_dir)
    write_json(round_dir / "work/opponent_calibration_use.json", use_payload)
    payload["calibration_use_path"] = "work/opponent_calibration_use.json"
    payload["calibration_use_sha256"] = sha256_file(round_dir / "work/opponent_calibration_use.json")
    write_json(round_dir / "work/opponent_report_revision_request.json", payload)

    errors = validate_opponent_calibration_artifact(round_dir, "work/opponent_report_revision_request.json")

    assert any(
        "exactly one of calibration_use or calibration_advisory binding is required" in error for error in errors
    )


def test_validate_opponent_report_revision_request_requires_source_refs_for_bound_artifacts(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = revision_request_payload(round_dir)
    payload["source_refs"] = ["notes/opponent-report-operator-feedback.md"]
    write_json(round_dir / "work/opponent_report_revision_request.json", payload)

    errors = validate_opponent_calibration_artifact(round_dir, "work/opponent_report_revision_request.json")

    assert any("source_refs must include outputs/opponent_reading_packet.md" in error for error in errors)
    assert any("source_refs must include work/opponent_calibration_use.json" in error for error in errors)
    assert any(
        "source_refs must include work/opponent_report_revision_sources/oponent_posudek_draft.md" in error
        for error in errors
    )


def test_validate_calibration_refresh_eligibility_binds_finalized_case_artifacts(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = calibration_refresh_eligibility_payload(round_dir)
    write_json(round_dir / "work/opponent_calibration_refresh_eligibility.json", payload)

    errors = validate_opponent_calibration_artifact(
        round_dir,
        "work/opponent_calibration_refresh_eligibility.json",
        case_id="calibration-case",
        round_id="round-a",
    )

    assert errors == []
    assert not (round_dir / "work/calibration/reviewer_calibration_profile.json").exists()
    assert not (round_dir / "work/calibration/reviewer_calibration_profile_history.jsonl").exists()


def test_validate_calibration_refresh_eligibility_rejects_stale_final_report_review_and_approval(
    tmp_path: Path,
) -> None:
    round_dir = tmp_path / "round"
    payload = calibration_refresh_eligibility_payload(round_dir)
    (round_dir / "outputs/feedback_k_posudku.md").write_text("changed review\n", encoding="utf-8")
    approval = dict(payload["operator_approval"]) if isinstance(payload["operator_approval"], dict) else {}
    approval["approved_final_report_review_sha256"] = "0" * 64
    payload["operator_approval"] = approval
    write_json(round_dir / "work/opponent_calibration_refresh_eligibility.json", payload)

    errors = validate_opponent_calibration_artifact(
        round_dir,
        "work/opponent_calibration_refresh_eligibility.json",
    )

    assert any("final_report_review_sha256 is stale" in error for error in errors)
    assert any("operator_approval: approved_final_report_review_sha256 is stale" in error for error in errors)


def test_validate_calibration_refresh_eligibility_requires_manifest_review_and_helper_evidence(
    tmp_path: Path,
) -> None:
    round_dir = tmp_path / "round"
    payload = calibration_refresh_eligibility_payload(round_dir)
    manifest_path = round_dir / "work/opponent_calibration_refresh_sources/review_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"] = [
        artifact for artifact in manifest["artifacts"] if artifact["path"] != "outputs/feedback_k_posudku.md"
    ]
    for check in manifest["helper_checks"]:
        if check["check"] == "check-opponent-report:canonical":
            check["status"] = "failed"
            check["exit_code"] = 1
    write_json(manifest_path, manifest)
    manifest_hash = sha256_file(manifest_path)
    payload["review_manifest_snapshot_sha256"] = manifest_hash
    approval = dict(payload["operator_approval"]) if isinstance(payload["operator_approval"], dict) else {}
    approval["approved_review_manifest_snapshot_sha256"] = manifest_hash
    payload["operator_approval"] = approval
    write_json(round_dir / "work/opponent_calibration_refresh_eligibility.json", payload)

    errors = validate_opponent_calibration_artifact(
        round_dir,
        "work/opponent_calibration_refresh_eligibility.json",
    )

    assert any("artifacts must include outputs/feedback_k_posudku.md" in error for error in errors)
    assert any("helper_checks check-opponent-report:canonical: status must be passed" in error for error in errors)
    assert any("helper_checks check-opponent-report:canonical: exit_code must be 0" in error for error in errors)


def test_validate_calibration_refresh_eligibility_rejects_stale_manifest_check_target(
    tmp_path: Path,
) -> None:
    round_dir = tmp_path / "round"
    payload = calibration_refresh_eligibility_payload(round_dir)
    manifest_path = round_dir / "work/opponent_calibration_refresh_sources/review_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for check in manifest["helper_checks"]:
        if check["check"] == "check-opponent-report:canonical":
            check["target_sha256"]["work/oponent_posudek_draft.md"] = "0" * 64
    write_json(manifest_path, manifest)
    manifest_hash = sha256_file(manifest_path)
    payload["review_manifest_snapshot_sha256"] = manifest_hash
    approval = dict(payload["operator_approval"]) if isinstance(payload["operator_approval"], dict) else {}
    approval["approved_review_manifest_snapshot_sha256"] = manifest_hash
    payload["operator_approval"] = approval
    write_json(round_dir / "work/opponent_calibration_refresh_eligibility.json", payload)

    errors = validate_opponent_calibration_artifact(
        round_dir,
        "work/opponent_calibration_refresh_eligibility.json",
    )

    assert any(
        "helper_checks check-opponent-report:canonical: target hash is stale for work/oponent_posudek_draft.md" in error
        for error in errors
    )


def test_validate_calibration_refresh_eligibility_rejects_self_referential_manifest_snapshot(
    tmp_path: Path,
) -> None:
    round_dir = tmp_path / "round"
    payload = calibration_refresh_eligibility_payload(round_dir)
    marker_path = round_dir / "work/opponent_calibration_refresh_eligibility.json"
    write_json(marker_path, payload)
    marker_hash = sha256_file(marker_path)
    manifest_path = round_dir / "work/opponent_calibration_refresh_sources/review_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["supporting_work_artifacts"].append(
        {
            "path": "work/opponent_calibration_refresh_eligibility.json",
            "kind": "structured_data",
            "artifact_sha256": marker_hash,
            "schema_version": "opponent-calibration-refresh-eligibility-v1",
        }
    )
    write_json(manifest_path, manifest)
    manifest_hash = sha256_file(manifest_path)
    payload["review_manifest_snapshot_sha256"] = manifest_hash
    approval = dict(payload["operator_approval"]) if isinstance(payload["operator_approval"], dict) else {}
    approval["approved_review_manifest_snapshot_sha256"] = manifest_hash
    payload["operator_approval"] = approval
    write_json(marker_path, payload)

    errors = validate_opponent_calibration_artifact(
        round_dir,
        "work/opponent_calibration_refresh_eligibility.json",
    )

    assert any(
        "snapshot must be captured before work/opponent_calibration_refresh_eligibility.json is collected" in error
        for error in errors
    )


def test_validate_calibration_refresh_eligibility_rejects_profile_update_claims(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = calibration_refresh_eligibility_payload(round_dir)
    payload["profile_update_status"] = "updated"
    payload["does_not_update_profile"] = False
    copy_policy = dict(payload["copy_policy"]) if isinstance(payload["copy_policy"], dict) else {}
    copy_policy["profile_auto_update"] = True
    copy_policy["auto_copy_performed"] = True
    payload["copy_policy"] = copy_policy
    write_json(round_dir / "work/opponent_calibration_refresh_eligibility.json", payload)

    errors = validate_opponent_calibration_artifact(
        round_dir,
        "work/opponent_calibration_refresh_eligibility.json",
    )

    assert any("profile_update_status must be not_started" in error for error in errors)
    assert any("does_not_update_profile must be true" in error for error in errors)
    assert any("copy_policy: profile_auto_update must be false" in error for error in errors)
    assert any("copy_policy: auto_copy_performed must be false" in error for error in errors)


def test_validate_calibration_refresh_eligibility_rejects_unsafe_case_local_refs(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = calibration_refresh_eligibility_payload(round_dir)
    payload["case_local_source_refs"] = [
        "outputs/oponent_podklady_revidovane.md",
        "/tmp/private/feedback_k_posudku.md",
        "work\\oponent_posudek_draft.md",
        "../outside.md",
    ]
    write_json(round_dir / "work/opponent_calibration_refresh_eligibility.json", payload)

    errors = validate_opponent_calibration_artifact(
        round_dir,
        "work/opponent_calibration_refresh_eligibility.json",
    )

    assert any("case_local_source_refs item 2: ref must be relative inside the round" in error for error in errors)
    assert any("case_local_source_refs item 3: ref must be relative inside the round" in error for error in errors)
    assert any("case_local_source_refs item 4: ref must be relative inside the round" in error for error in errors)


def test_work_artifacts_collects_current_case_calibration_advisory(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    write_json(round_dir / "work/opponent_calibration_advisory.json", calibration_advisory_payload(round_dir))

    records = collect_supporting_work_artifacts(round_dir)
    by_path = {record["path"]: record for record in records}

    assert by_path["work/opponent_calibration_advisory.json"]["schema_version"] == "opponent-calibration-advisory-v1"
    assert validate_supporting_work_artifacts(records, round_dir, case_id="calibration-case", round_id="round-a") == []


def test_work_artifacts_collects_current_case_revision_request(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    write_json(round_dir / "work/opponent_report_revision_request.json", revision_request_payload(round_dir))

    records = collect_supporting_work_artifacts(round_dir)
    by_path = {record["path"]: record for record in records}

    assert (
        by_path["work/opponent_report_revision_request.json"]["schema_version"] == "opponent-report-revision-request-v1"
    )
    assert validate_supporting_work_artifacts(records, round_dir, case_id="calibration-case", round_id="round-a") == []


def test_work_artifacts_collects_current_case_calibration_refresh_eligibility(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    write_json(
        round_dir / "work/opponent_calibration_refresh_eligibility.json",
        calibration_refresh_eligibility_payload(round_dir),
    )

    records = collect_supporting_work_artifacts(round_dir)
    by_path = {record["path"]: record for record in records}

    assert (
        by_path["work/opponent_calibration_refresh_eligibility.json"]["schema_version"]
        == "opponent-calibration-refresh-eligibility-v1"
    )
    assert validate_supporting_work_artifacts(records, round_dir, case_id="calibration-case", round_id="round-a") == []
    stale_records = [dict(record) for record in records]
    for record in stale_records:
        if record["path"] == "work/opponent_calibration_refresh_eligibility.json":
            record["artifact_sha256"] = "0" * 64
    stale_errors = validate_supporting_work_artifacts(
        stale_records,
        round_dir,
        case_id="calibration-case",
        round_id="round-a",
    )
    assert any(
        "artifact_sha256 is stale for work/opponent_calibration_refresh_eligibility.json" in error
        for error in stale_errors
    )


def test_draft_gate_validates_current_case_calibration_use(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = calibration_use_payload(round_dir)
    write_json(round_dir / "work/opponent_calibration_use.json", payload)

    selected = validate_current_case_calibration(round_dir, "calibration-case", "round-a")

    assert selected == "work/opponent_calibration_use.json"


def test_draft_gate_rejects_stale_current_case_calibration_use(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    payload = calibration_use_payload(round_dir)
    write_json(round_dir / "work/opponent_calibration_use.json", payload)
    profile_path = round_dir / "work/calibration/reviewer_calibration_profile.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    profile["profile_change_summary"] = "Changed synthetic profile."
    write_json(profile_path, profile)

    try:
        validate_current_case_calibration(round_dir, "calibration-case", "round-a")
    except SystemExit as exc:
        assert "Invalid current-case opponent calibration artifact" in str(exc)
        assert "profile_manifest_sha256 is stale" in str(exc)
    else:
        raise AssertionError("Expected stale current-case calibration to fail")


def test_draft_gate_rejects_conflicting_current_case_calibration_artifacts(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    write_json(round_dir / "work/opponent_calibration_use.json", calibration_use_payload(round_dir))
    write_json(round_dir / "work/opponent_calibration_advisory.json", calibration_advisory_payload(round_dir))

    try:
        validate_current_case_calibration(round_dir, "calibration-case", "round-a")
    except SystemExit as exc:
        assert "Conflicting current-case opponent calibration artifacts" in str(exc)
    else:
        raise AssertionError("Expected conflicting current-case calibration artifacts to fail")


def test_validate_historical_case_analysis_rejects_dot_only_stem(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"

    errors = validate_opponent_calibration_artifact(round_dir, "work/calibration/historical_case_analyses/...json")

    assert errors == ["work/calibration/historical_case_analyses/...json: unknown opponent calibration artifact path"]


def test_work_artifacts_collects_and_validates_calibration_artifacts(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_calibration_refs(round_dir)
    write_json(round_dir / "work/calibration/historical_case_analyses/case-001.json", historical_case_payload())

    records = collect_supporting_work_artifacts(round_dir)
    by_path = {record["path"]: record for record in records}

    assert (
        by_path["work/calibration/historical_case_analyses/case-001.json"]["schema_version"]
        == "historical-opponent-case-analysis-v1"
    )
    assert validate_supporting_work_artifacts(records, round_dir, case_id="calibration-case", round_id="round-a") == []
