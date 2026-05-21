"""Validators for agent- or reviewer-authored structured evidence artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from thesis_review_workflow.artifact_validation import sha256_file, validate_common_artifact_fields
from thesis_review_workflow.paths import is_safe_round_relative_path
from thesis_review_workflow.report_calibration import (
    EXPECTED_REPORT_CONTROL_KEYS,
    REPORT_CALIBRATION_BASIS_REL,
    effective_reviewer_profile,
    report_calibration_applied_preference_ids,
    report_calibration_expected_control_keys,
    report_calibration_related_artifact_hashes,
    report_calibration_source_paths,
    validate_report_calibration_artifact,
)
from thesis_review_workflow.semantic_source_refs import validate_long_lived_semantic_source_refs
from thesis_review_workflow.submission_bundle import SUBMISSION_BUNDLE_VISIBILITY_REFS
from thesis_review_workflow.theses_checker_summary import (
    THESES_CHECKER_SUMMARY_REL,
    validate_theses_checker_summary_artifact,
)
from thesis_review_workflow.theses_similarity import (
    CURRENT_SUBMISSION_MATCH_STATUSES,
    SIMILARITY_CONFIDENCE_VALUES,
    SIMILARITY_JUDGMENT_CATEGORIES,
    SIMILARITY_SYNTHESIS_ACTIONS,
    SIMILARITY_UNRESOLVED_CATEGORIES,
    THESES_SIMILARITY_ASSESSMENT_REL,
    THESES_SIMILARITY_ASSESSMENT_SCHEMA,
)

ASSIGNMENT_COVERAGE_REL = "work/assignment_coverage_agent.json"
EVIDENCE_REQUIREMENTS_REL = "work/evidence_requirements.json"
QUANTITATIVE_CLAIMS_REL = "work/quantitative_claims.json"
OPPONENT_REPORT_TRACE_REL = "work/opponent_report_trace.json"
SUPERVISOR_REPORT_FEEDBACK_HISTORY_REL = "work/supervisor_report_feedback_history.json"
SUPERVISOR_REPORT_TRACE_REL = "work/supervisor_report_trace.json"
SUPERVISOR_REPORT_CONFIRMATION_REL = "work/supervisor_report_confirmation.json"
CURRENT_EVIDENCE_SNAPSHOT_REL = "work/current_evidence_snapshot.json"
OPPONENT_CALIBRATION_USE_REL = "work/opponent_calibration_use.json"
OPPONENT_CALIBRATION_ADVISORY_REL = "work/opponent_calibration_advisory.json"
OPPONENT_REPORT_REVISION_REQUEST_REL = "work/opponent_report_revision_request.json"
REFERENCE_REPORT_COMPARISON_REL = "outputs/reference_report_comparison.md"
OPPONENT_READING_PACKET_REL = "outputs/opponent_reading_packet.md"

STRUCTURED_EVIDENCE_SCHEMAS: dict[str, str] = {
    ASSIGNMENT_COVERAGE_REL: "assignment-coverage-agent-v1",
    EVIDENCE_REQUIREMENTS_REL: "evidence-requirements-v1",
    QUANTITATIVE_CLAIMS_REL: "quantitative-claims-v1",
    OPPONENT_REPORT_TRACE_REL: "opponent-report-trace-v2",
    SUPERVISOR_REPORT_FEEDBACK_HISTORY_REL: "supervisor-report-feedback-history-v1",
    SUPERVISOR_REPORT_TRACE_REL: "supervisor-report-trace-v1",
    SUPERVISOR_REPORT_CONFIRMATION_REL: "supervisor-report-confirmation-v1",
    CURRENT_EVIDENCE_SNAPSHOT_REL: "current-evidence-snapshot-v1",
    THESES_SIMILARITY_ASSESSMENT_REL: THESES_SIMILARITY_ASSESSMENT_SCHEMA,
}

ALLOWED_REF_PREFIXES = ("inputs/", "extracted/", "notes/", "work/", "outputs/")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

ASSIGNMENT_COVERAGE_STATUSES = {"covered", "partially_covered", "not_covered", "not_verifiable"}
EVIDENCE_REQUIREMENT_CATEGORIES = {
    "media",
    "evaluation_data",
    "evaluation_script",
    "code_reproducibility",
    "dataset",
    "method_description",
    "assignment_source",
    "other",
}
EVIDENCE_REQUIREMENT_STATES = {"present", "weak", "missing", "not_applicable", "not_verifiable"}
QUANTITATIVE_CLAIM_KINDS = {"metric", "experiment", "performance", "scale", "count", "statistic", "other"}
QUANTITATIVE_CLAIM_STATUSES = {"plausible", "needs_context", "unsupported", "inconsistent", "not_verifiable"}
BASELINE_STATUSES = {"stated", "missing", "not_applicable", "not_verifiable"}
PRACTICAL_CONTEXT_STATUSES = {"sufficient", "weak", "missing", "not_applicable", "not_verifiable"}
OVERCLAIM_RISK_STATUSES = {"low", "moderate", "high", "not_applicable", "not_verifiable"}
OPPONENT_TRACE_REVIEW_STATUSES = {"accepted"}
OPPONENT_TRACE_UNCERTAINTY_STATUSES = {"carried_to_report", "accepted_missing", "not_applicable"}
OPPONENT_TRACE_ANTI_OVERFIT_STATUSES = {"reviewed", "reviewed_with_notes", "not_applicable"}
OPPONENT_TRACE_CALIBRATION_TARGET_CONTROLS = EXPECTED_REPORT_CONTROL_KEYS
OPPONENT_TRACE_CALIBRATION_LIMITATION_TYPE = "no_applicable_profile_or_operator_calibration"
OPPONENT_TRACE_FULFILLMENT_STATES = {"fulfilled", "partially_fulfilled", "not_evidenced", "not_fulfilled"}
OPPONENT_TRACE_EVIDENCE_STRENGTHS = {"direct", "indirect", "not_documented", "not_checked", "not_available"}
OPPONENT_TRACE_WORDING_MODES = {"direct", "cautious_not_evidenced", "manual_check", "defense_question", "internal_only"}
OPPONENT_TRACE_EVIDENCE_CLASSES = {
    "assignment",
    "thesis_text",
    "submitted_code_static",
    "build_run_demo",
    "media_visual",
    "operator_notes",
    "literature_citation",
    "reproducibility",
    "licensing",
    "deployment",
    "third_party_authorship",
    "quantitative_evaluation",
    "reviewed_materials",
    "other",
}
OPPONENT_TRACE_SCOPE_STATUSES = {"checked", "sampled", "not_available", "not_checked", "manual_check"}
OPPONENT_TRACE_SUPPORT_MODES = {"supports", "partially_supports", "limits", "not_checked", "not_available"}
OPPONENT_TRACE_MEDIA_STATUSES = {
    "pdf_inspected",
    "source_asset_checked",
    "inventoried_only",
    "not_checked",
    "not_applicable",
}
OPPONENT_TRACE_SCOPE_BASIS_STATUSES = {"checker_summary", "operator_accepted_limitation"}
SUPERVISOR_FEEDBACK_HISTORY_STATUSES = {
    "absent",
    "present",
    "evidenced_response",
    "evidenced_partial_response",
    "evidenced_nonresponse",
    "no_comparable_revision",
    "inconclusive",
}
SUPERVISOR_EVIDENCE_BEARING_FEEDBACK_STATUSES = {
    "evidenced_response",
    "evidenced_partial_response",
    "evidenced_nonresponse",
}
REQUIRED_SUPERVISOR_REPORT_FIELD_IDS = {
    "assignment_information",
    "literature_work",
    "activity_during_solution",
    "completion_activity",
    "publication_activity",
    "overall_assessment",
    "student_comment",
}
SUPERVISOR_REPORT_FIELD_VISIBILITIES = {"official", "private_student_comment"}
SUPERVISOR_REPORT_GRADES = {"A", "B", "C", "D", "E", "F", "undecided"}
SUPERVISOR_REPORT_UNCERTAINTY_STATUSES = {"carried_to_report", "accepted_missing", "not_applicable"}
CURRENT_EVIDENCE_ITEM_STATUSES = {"present", "missing", "invalid", "unavailable", "not_applicable"}
CURRENT_EVIDENCE_FRESHNESS_STATUSES = {"current", "stale", "not_checked", "not_applicable"}
CURRENT_EVIDENCE_DEFAULT_SOURCE_REFS = (
    *SUBMISSION_BUNDLE_VISIBILITY_REFS,
    "work/code_workspace.md",
    "work/serena_roots.json",
    "work/code_reproducibility.json",
    "work/quantitative_claims.json",
    THESES_CHECKER_SUMMARY_REL,
    "outputs/github_code_intake.md",
    "outputs/feedback_student.md",
    "work/feedback_student_draft.md",
    "outputs/oponent_podklady.md",
    "outputs/oponent_podklady_revidovane.md",
    REPORT_CALIBRATION_BASIS_REL,
    "work/oponent_podklady_draft.md",
    "work/opponent_report_trace.json",
    "work/oponent_posudek_draft.md",
    "work/supervisor_report_feedback_history.json",
    "work/supervisor_report_trace.json",
    "work/vedouci_posudek_draft.md",
    "work/supervisor_report_confirmation.json",
    "work/supervisor_report_calibration_use.json",
    "work/supervisor_report_calibration_advisory.json",
    "outputs/vedouci_posudek_revidovany.md",
    "notes/operator-late-communications.md",
    "notes/late-communications.md",
    "notes/round-notes.md",
)
CURRENT_EVIDENCE_REVIEW_RECORD_GLOB = "work/reviews/*_review.json"
REQUIRED_OPPONENT_IS_ITEM_IDS = {
    "assignment_difficulty",
    "assignment_fulfillment",
    "technical_report_scope",
    "technical_report_presentation",
    "technical_report_formal_level",
    "literature_work",
    "implementation_output",
    "result_usability",
    "overall_assessment",
}


def current_evidence_default_source_refs(
    round_dir: Path,
    *,
    include_missing_known: bool = False,
) -> list[str]:
    refs: list[str] = []
    for rel_path in CURRENT_EVIDENCE_DEFAULT_SOURCE_REFS:
        if include_missing_known or (round_dir / rel_path).exists():
            refs.append(rel_path)
    review_dir = round_dir / "work" / "reviews"
    if review_dir.is_dir():
        refs.extend(
            path.relative_to(round_dir).as_posix()
            for path in sorted(review_dir.glob("*_review.json"))
            if path.is_file()
        )
    return sorted(dict.fromkeys(refs))


def build_current_evidence_snapshot_payload(
    round_dir: Path,
    *,
    case_id: str,
    round_id: str,
    generated_at: str,
    source_refs: list[str],
    producer_role: str = "update-current-evidence-snapshot",
    producer_agent: str = "update-current-evidence-snapshot",
    existing_payload: dict[str, Any] | None = None,
    limitations_by_path: dict[str, list[str]] | None = None,
    readiness_relevant_by_path: dict[str, bool] | None = None,
) -> dict[str, Any]:
    existing_items = existing_payload.get("items") if isinstance(existing_payload, dict) else None
    existing_by_path: dict[str, dict[str, Any]] = {}
    if isinstance(existing_items, list):
        for item in existing_items:
            if isinstance(item, dict) and isinstance(item.get("path"), str):
                existing_by_path[item["path"]] = item
    limitations_by_path = limitations_by_path or {}
    readiness_relevant_by_path = readiness_relevant_by_path or {}

    items: list[dict[str, Any]] = []
    source_refs_present: list[str] = []
    for rel_path in sorted(dict.fromkeys(source_refs)):
        if not _is_allowed_round_ref(rel_path):
            raise ValueError(f"current evidence source ref must be a safe round-relative ref: {rel_path}")
        item = _current_evidence_item(
            round_dir,
            rel_path,
            generated_at=generated_at,
            existing=existing_by_path.get(rel_path),
            limitations=limitations_by_path.get(rel_path),
            readiness_relevant=readiness_relevant_by_path.get(rel_path),
        )
        items.append(item)
        if item["status"] == "present":
            source_refs_present.append(rel_path)
    return {
        "schema_version": STRUCTURED_EVIDENCE_SCHEMAS[CURRENT_EVIDENCE_SNAPSHOT_REL],
        "case_id": case_id,
        "round_id": round_id,
        "generated_at": generated_at,
        "producer_type": "agent",
        "producer_role": producer_role,
        "producer_agent": producer_agent,
        "authorization_note": "Deterministic helper generated hash-bound current evidence state.",
        "source_refs": source_refs_present,
        "items": items,
        "limitations": [],
    }


def _current_evidence_item(
    round_dir: Path,
    rel_path: str,
    *,
    generated_at: str,
    existing: dict[str, Any] | None,
    limitations: list[str] | None,
    readiness_relevant: bool | None,
) -> dict[str, Any]:
    previous_limitations = existing.get("limitations") if isinstance(existing, dict) else None
    if limitations is not None:
        item_limitations = limitations
    elif isinstance(previous_limitations, list):
        item_limitations = [item for item in previous_limitations if isinstance(item, str)]
    else:
        item_limitations = []
    if (
        readiness_relevant is None
        and isinstance(existing, dict)
        and isinstance(existing.get("readiness_relevant"), bool)
    ):
        readiness_relevant = bool(existing["readiness_relevant"])
    path = round_dir / rel_path
    if path.is_file():
        status = "present"
        freshness = "current"
    elif path.exists():
        status = "invalid"
        freshness = "stale"
    else:
        status = "missing"
        freshness = "not_checked"
    item: dict[str, Any] = {
        "item_id": _current_evidence_item_id(rel_path),
        "path": rel_path,
        "status": status,
        "freshness": freshness,
        "recorded_at": generated_at,
        "readiness_relevant": True if readiness_relevant is None else readiness_relevant,
        "limitations": item_limitations,
    }
    if status == "present":
        item["sha256"] = sha256_file(path)
    return item


def _current_evidence_item_id(rel_path: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", rel_path).strip("-").lower()
    return f"current-evidence-{cleaned or 'item'}"


def validate_structured_evidence_artifact(
    round_dir: Path,
    rel_path: Path | str,
    *,
    case_id: str | None = None,
    round_id: str | None = None,
    require_existing_refs: bool = True,
    require_report_calibration: bool = True,
) -> list[str]:
    rel = rel_path.as_posix() if isinstance(rel_path, Path) else rel_path
    path_errors = validate_structured_evidence_rel_path(rel)
    if path_errors:
        return path_errors
    path = round_dir / rel
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [f"{rel}: missing structured evidence artifact"]
    except OSError as exc:
        detail = exc.strerror or exc.__class__.__name__
        return [f"{rel}: cannot read structured evidence artifact: {detail}"]
    except json.JSONDecodeError as exc:
        return [f"{rel}: invalid JSON: {exc.msg}"]
    if not isinstance(loaded, dict):
        return [f"{rel}: JSON structured evidence artifact must be an object"]
    return validate_structured_evidence_payload(
        loaded,
        rel,
        round_dir=round_dir,
        case_id=case_id,
        round_id=round_id,
        require_existing_refs=require_existing_refs,
        require_report_calibration=require_report_calibration,
    )


def validate_structured_evidence_payload(
    loaded: dict[str, Any],
    rel_path: str,
    *,
    round_dir: Path | None = None,
    case_id: str | None = None,
    round_id: str | None = None,
    require_existing_refs: bool = True,
    require_report_calibration: bool = True,
) -> list[str]:
    errors: list[str] = []
    path_errors = validate_structured_evidence_rel_path(rel_path)
    if path_errors:
        return path_errors
    expected_schema = STRUCTURED_EVIDENCE_SCHEMAS.get(rel_path)
    if expected_schema is None:
        return [f"{rel_path}: unknown structured evidence artifact path"]

    _validate_common_fields(loaded, rel_path, expected_schema, case_id, round_id, errors)
    if rel_path == ASSIGNMENT_COVERAGE_REL:
        _validate_assignment_coverage(loaded, rel_path, errors)
    elif rel_path == EVIDENCE_REQUIREMENTS_REL:
        _validate_evidence_requirements(loaded, rel_path, errors)
    elif rel_path == QUANTITATIVE_CLAIMS_REL:
        _validate_quantitative_claims(loaded, rel_path, errors)
    elif rel_path == OPPONENT_REPORT_TRACE_REL:
        _validate_opponent_report_trace(
            loaded,
            rel_path,
            round_dir,
            case_id,
            round_id,
            errors,
            require_report_calibration=require_report_calibration,
        )
    elif rel_path == SUPERVISOR_REPORT_FEEDBACK_HISTORY_REL:
        _validate_supervisor_report_feedback_history(loaded, rel_path, round_dir, errors)
    elif rel_path == SUPERVISOR_REPORT_TRACE_REL:
        _validate_supervisor_report_trace(loaded, rel_path, round_dir, case_id, round_id, errors)
    elif rel_path == SUPERVISOR_REPORT_CONFIRMATION_REL:
        _validate_supervisor_report_confirmation(loaded, rel_path, round_dir, errors)
    elif rel_path == CURRENT_EVIDENCE_SNAPSHOT_REL:
        _validate_current_evidence_snapshot(loaded, rel_path, round_dir, errors)
    elif rel_path == THESES_SIMILARITY_ASSESSMENT_REL:
        _validate_theses_similarity_assessment(loaded, rel_path, round_dir, errors)

    _validate_refs(
        loaded,
        rel_path,
        round_dir=round_dir,
        require_existing_refs=require_existing_refs,
        errors=errors,
    )
    return errors


def validate_structured_evidence_rel_path(rel_path: str) -> list[str]:
    if not is_safe_round_relative_path(rel_path):
        return [f"{rel_path}: structured evidence path must be relative inside the round"]
    if rel_path not in STRUCTURED_EVIDENCE_SCHEMAS:
        return [f"{rel_path}: unknown structured evidence artifact path"]
    return []


def _validate_common_fields(
    loaded: dict[str, Any],
    rel_path: str,
    expected_schema: str,
    case_id: str | None,
    round_id: str | None,
    errors: list[str],
) -> None:
    validate_common_artifact_fields(
        loaded,
        rel_path,
        expected_schema,
        case_id,
        round_id,
        errors,
        required_string_fields=("case_id", "round_id", "generated_at", "producer_role"),
    )


def _validate_assignment_coverage(loaded: dict[str, Any], rel_path: str, errors: list[str]) -> None:
    points = _require_list(loaded, "assignment_points", rel_path, errors)
    if not isinstance(points, list):
        return
    for index, item in enumerate(points, start=1):
        prefix = f"{rel_path}: assignment_points item {index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be object")
            continue
        _require_nonempty_string(item, "point_id", prefix, errors)
        _require_nonempty_string(item, "summary", prefix, errors)
        _require_list(item, "source_refs", prefix, errors)
        coverage = item.get("coverage")
        if not isinstance(coverage, dict):
            errors.append(f"{prefix}: coverage must be object")
            continue
        _require_enum(coverage, "status", ASSIGNMENT_COVERAGE_STATUSES, f"{prefix}: coverage", errors)
        _require_list(coverage, "evidence_refs", f"{prefix}: coverage", errors)
        _require_list(coverage, "limitations", f"{prefix}: coverage", errors)
        _require_bool(coverage, "requires_reviewer_verification", f"{prefix}: coverage", errors)


def _validate_evidence_requirements(loaded: dict[str, Any], rel_path: str, errors: list[str]) -> None:
    requirements = _require_list(loaded, "requirements", rel_path, errors)
    if not isinstance(requirements, list):
        return
    for index, item in enumerate(requirements, start=1):
        prefix = f"{rel_path}: requirements item {index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be object")
            continue
        _require_nonempty_string(item, "requirement_id", prefix, errors)
        _require_enum(item, "category", EVIDENCE_REQUIREMENT_CATEGORIES, prefix, errors)
        _require_enum(item, "state", EVIDENCE_REQUIREMENT_STATES, prefix, errors)
        _require_nonempty_string(item, "request", prefix, errors)
        _require_list(item, "evidence_refs", prefix, errors)
        _require_bool(item, "requires_reviewer_verification", prefix, errors)


def _validate_quantitative_claims(loaded: dict[str, Any], rel_path: str, errors: list[str]) -> None:
    claims = _require_list(loaded, "claims", rel_path, errors)
    if not isinstance(claims, list):
        return
    for index, item in enumerate(claims, start=1):
        prefix = f"{rel_path}: claims item {index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be object")
            continue
        _require_nonempty_string(item, "claim_id", prefix, errors)
        _require_nonempty_string(item, "summary", prefix, errors)
        _require_enum(item, "kind", QUANTITATIVE_CLAIM_KINDS, prefix, errors)
        _require_enum(item, "status", QUANTITATIVE_CLAIM_STATUSES, prefix, errors)
        _require_nonempty_string(item, "unit", prefix, errors)
        _require_enum(item, "baseline_status", BASELINE_STATUSES, prefix, errors)
        _require_enum(item, "practical_context", PRACTICAL_CONTEXT_STATUSES, prefix, errors)
        _require_nonempty_string(item, "scale_context", prefix, errors)
        _require_nonempty_string(item, "sample_context", prefix, errors)
        _require_nonempty_string(item, "practical_magnitude", prefix, errors)
        _require_enum(item, "overclaim_risk", OVERCLAIM_RISK_STATUSES, prefix, errors)
        _require_list(item, "reproducibility_refs", prefix, errors)
        _require_nonempty_list(item, "evidence_refs", prefix, errors)
        _require_bool(item, "requires_reviewer_verification", prefix, errors)


def _validate_opponent_report_trace(
    loaded: dict[str, Any],
    rel_path: str,
    round_dir: Path | None,
    case_id: str | None,
    round_id: str | None,
    errors: list[str],
    *,
    require_report_calibration: bool = True,
) -> None:
    _require_nonempty_string(loaded, "source_materials_path", rel_path, errors)
    if loaded.get("source_materials_path") != "outputs/oponent_podklady_revidovane.md":
        errors.append(f"{rel_path}: source_materials_path must be outputs/oponent_podklady_revidovane.md")
    source_hash = loaded.get("source_materials_sha256")
    if not isinstance(source_hash, str) or not SHA256_RE.fullmatch(source_hash):
        errors.append(f"{rel_path}: source_materials_sha256 must be a 64-character hex string")
    elif round_dir is not None:
        _validate_source_materials_hash(loaded, rel_path, round_dir, errors)
    _require_enum(loaded, "trace_review_status", OPPONENT_TRACE_REVIEW_STATUSES, rel_path, errors)
    _require_nonempty_string(loaded, "reviewer_role", rel_path, errors)
    _require_nonempty_string(loaded, "reviewed_at", rel_path, errors)
    _require_list(loaded, "trace_generated_from", rel_path, errors)

    item_ids: set[str] = set()
    is_items = _require_list(loaded, "is_items", rel_path, errors)
    if isinstance(is_items, list):
        for index, item in enumerate(is_items, start=1):
            prefix = f"{rel_path}: is_items item {index}"
            if not isinstance(item, dict):
                errors.append(f"{prefix} must be object")
                continue
            item_id = item.get("item_id")
            if isinstance(item_id, str):
                if item_id in item_ids:
                    errors.append(f"{prefix}: duplicate item_id {item_id}")
                item_ids.add(item_id)
            _require_enum(item, "item_id", REQUIRED_OPPONENT_IS_ITEM_IDS, prefix, errors)
            _require_nonempty_string(item, "title", prefix, errors)
            _require_nonempty_string(item, "formulation", prefix, errors)
            _require_nonempty_list(item, "evidence_refs", prefix, errors)
    missing_ids = sorted(REQUIRED_OPPONENT_IS_ITEM_IDS - item_ids)
    if missing_ids:
        errors.append(f"{rel_path}: missing required is_items: {', '.join(missing_ids)}")

    _validate_trace_questions(loaded, "defense_questions", "question_id", "question", rel_path, errors)
    _validate_trace_questions(loaded, "pre_submission_checks", "check_id", "instruction", rel_path, errors)
    _validate_opponent_trace_quality_controls(loaded, rel_path, round_dir, errors)
    uncertainty_items = _require_list(loaded, "uncertainty_items", rel_path, errors)
    if isinstance(uncertainty_items, list):
        for index, item in enumerate(uncertainty_items, start=1):
            prefix = f"{rel_path}: uncertainty_items item {index}"
            if not isinstance(item, dict):
                errors.append(f"{prefix} must be object")
                continue
            _require_nonempty_string(item, "claim_id", prefix, errors)
            _require_nonempty_string(item, "summary", prefix, errors)
            _require_nonempty_string(item, "handling_instruction", prefix, errors)
            _require_nonempty_list(item, "source_refs", prefix, errors)
            _require_nonempty_list(item, "target_section_ids", prefix, errors)
            target_ids = item.get("target_section_ids")
            if isinstance(target_ids, list):
                for target_index, target_id in enumerate(target_ids, start=1):
                    if target_id not in REQUIRED_OPPONENT_IS_ITEM_IDS:
                        errors.append(f"{prefix}: target_section_ids item {target_index} has unknown IS item id")
            _require_nonempty_list(item, "report_refs", prefix, errors)
            report_refs = item.get("report_refs")
            if isinstance(report_refs, list):
                for ref_index, ref in enumerate(report_refs, start=1):
                    if ref != "work/oponent_posudek_draft.md":
                        errors.append(f"{prefix}: report_refs item {ref_index} must be work/oponent_posudek_draft.md")
            _require_enum(item, "status", OPPONENT_TRACE_UNCERTAINTY_STATUSES, prefix, errors)
    if "calibration_context" in loaded:
        _validate_calibration_context(
            loaded.get("calibration_context"),
            rel_path,
            round_dir,
            case_id,
            round_id,
            errors,
        )
    if require_report_calibration and _report_calibration_basis_required(loaded, round_dir):
        if "report_calibration_limitation" in loaded:
            errors.append(
                f"{rel_path}: report_calibration_limitation cannot be recorded together with "
                "report_calibration_basis binding"
            )
        basis_payload = _validate_report_calibration_basis_binding(
            loaded,
            rel_path,
            round_dir,
            case_id,
            round_id,
            errors,
        )
        if isinstance(basis_payload, dict):
            _validate_trace_calibration_preferences(loaded, basis_payload, rel_path, errors)
            if "calibration_context" in loaded:
                _validate_calibration_context_basis_relationship(
                    loaded.get("calibration_context"),
                    basis_payload,
                    rel_path,
                    errors,
                )
                _validate_calibration_context_control_conflicts(
                    loaded.get("calibration_context"),
                    basis_payload,
                    rel_path,
                    round_dir,
                    errors,
                )
    elif require_report_calibration and "report_calibration_limitation" in loaded:
        _validate_report_calibration_limitation(
            loaded.get("report_calibration_limitation"), rel_path, round_dir, errors
        )


def _validate_opponent_trace_quality_controls(
    loaded: dict[str, Any],
    rel_path: str,
    round_dir: Path | None,
    errors: list[str],
) -> None:
    _validate_assignment_fulfillment_map(loaded.get("assignment_fulfillment_map"), rel_path, errors)
    _validate_rubric_alignment(loaded.get("rubric_alignment"), rel_path, errors)
    ledger_ids = _validate_report_claim_ledger(loaded.get("report_claim_ledger"), rel_path, errors)
    _validate_checked_scope(loaded.get("checked_scope"), rel_path, errors)
    _validate_evidence_source_matrix(loaded.get("evidence_source_matrix"), ledger_ids, rel_path, errors)
    _validate_technical_report_scope_basis(loaded.get("technical_report_scope_basis"), rel_path, round_dir, errors)
    _validate_strength_grade_tension(loaded.get("strength_grade_tension"), rel_path, errors)
    _validate_defense_question_strategy(
        loaded.get("defense_question_strategy"), _trace_question_ids(loaded), rel_path, errors
    )
    for field in (
        "evaluation_claim_review",
        "scaling_claim_review",
        "third_party_authorship_review",
        "contribution_boundary_review",
        "citation_support_review",
        "technical_difficulty_breakdown",
        "result_usability_level",
        "deployment_readiness",
    ):
        if field in loaded:
            _validate_materiality_bound_trace_ref(loaded.get(field), field, rel_path, errors)


def _validate_assignment_fulfillment_map(value: Any, rel_path: str, errors: list[str]) -> None:
    prefix = f"{rel_path}: assignment_fulfillment_map"
    if not isinstance(value, dict):
        errors.append(f"{prefix} must be object")
        return
    _require_nonempty_list(value, "source_refs", prefix, errors)
    points = value.get("points")
    limitation = value.get("typed_limitation")
    if not isinstance(points, list) and not isinstance(limitation, dict):
        errors.append(f"{prefix}: must contain points or typed_limitation")
    if isinstance(points, list):
        if not points:
            errors.append(f"{prefix}: points must not be empty when present")
        for index, item in enumerate(points, start=1):
            item_prefix = f"{prefix}: points item {index}"
            if not isinstance(item, dict):
                errors.append(f"{item_prefix} must be object")
                continue
            _require_nonempty_string(item, "point_id", item_prefix, errors)
            _require_nonempty_string(item, "summary", item_prefix, errors)
            _require_enum(item, "fulfillment_state", OPPONENT_TRACE_FULFILLMENT_STATES, item_prefix, errors)
            _require_enum(item, "evidence_strength", OPPONENT_TRACE_EVIDENCE_STRENGTHS, item_prefix, errors)
            _require_nonempty_list(item, "evidence_refs", item_prefix, errors)
            _require_nonempty_string(item, "report_impact", item_prefix, errors)
    if isinstance(limitation, dict):
        _require_nonempty_string(limitation, "type", f"{prefix}: typed_limitation", errors)
        _require_nonempty_string(limitation, "description", f"{prefix}: typed_limitation", errors)


def _validate_rubric_alignment(value: Any, rel_path: str, errors: list[str]) -> None:
    items = _require_nonempty_list({"rubric_alignment": value}, "rubric_alignment", rel_path, errors)
    if not isinstance(items, list):
        return
    seen: set[str] = set()
    for index, item in enumerate(items, start=1):
        prefix = f"{rel_path}: rubric_alignment item {index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be object")
            continue
        item_id = item.get("item_id")
        if isinstance(item_id, str):
            if item_id in seen:
                errors.append(f"{prefix}: duplicate item_id {item_id}")
            seen.add(item_id)
        _require_enum(item, "item_id", REQUIRED_OPPONENT_IS_ITEM_IDS, prefix, errors)
        _require_nonempty_string(item, "criterion_scope", prefix, errors)
        _require_nonempty_list(item, "evidence_refs", prefix, errors)
        _require_nonempty_list(item, "do_not_mix_with", prefix, errors)
        _require_nonempty_string(item, "wording_tone", prefix, errors)
    missing = sorted(REQUIRED_OPPONENT_IS_ITEM_IDS - seen)
    if missing:
        errors.append(f"{rel_path}: rubric_alignment missing required item ids: {', '.join(missing)}")


def _validate_report_claim_ledger(value: Any, rel_path: str, errors: list[str]) -> set[str]:
    ids: set[str] = set()
    items = _require_nonempty_list({"report_claim_ledger": value}, "report_claim_ledger", rel_path, errors)
    if not isinstance(items, list):
        return ids
    for index, item in enumerate(items, start=1):
        prefix = f"{rel_path}: report_claim_ledger item {index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be object")
            continue
        claim_id = item.get("claim_id")
        if isinstance(claim_id, str):
            if claim_id in ids:
                errors.append(f"{prefix}: duplicate claim_id {claim_id}")
            ids.add(claim_id)
        _require_nonempty_string(item, "claim_id", prefix, errors)
        _require_enum(item, "target_item_id", REQUIRED_OPPONENT_IS_ITEM_IDS, prefix, errors)
        _require_nonempty_string(item, "summary", prefix, errors)
        _require_enum(item, "evidence_class", OPPONENT_TRACE_EVIDENCE_CLASSES, prefix, errors)
        _require_enum(item, "evidence_strength", OPPONENT_TRACE_EVIDENCE_STRENGTHS, prefix, errors)
        _require_enum(item, "public_wording_mode", OPPONENT_TRACE_WORDING_MODES, prefix, errors)
        _require_nonempty_list(item, "evidence_refs", prefix, errors)
    return ids


def _validate_checked_scope(value: Any, rel_path: str, errors: list[str]) -> None:
    items = _require_nonempty_list({"checked_scope": value}, "checked_scope", rel_path, errors)
    if not isinstance(items, list):
        return
    for index, item in enumerate(items, start=1):
        prefix = f"{rel_path}: checked_scope item {index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be object")
            continue
        _require_enum(item, "evidence_class", OPPONENT_TRACE_EVIDENCE_CLASSES, prefix, errors)
        _require_enum(item, "status", OPPONENT_TRACE_SCOPE_STATUSES, prefix, errors)
        _require_nonempty_list(item, "source_refs", prefix, errors)
        limitations = item.get("limitations")
        if not isinstance(limitations, list) or not all(isinstance(limitation, str) for limitation in limitations):
            errors.append(f"{prefix}: limitations must be a list of strings")


def _validate_evidence_source_matrix(
    value: Any,
    ledger_ids: set[str],
    rel_path: str,
    errors: list[str],
) -> None:
    items = _require_nonempty_list({"evidence_source_matrix": value}, "evidence_source_matrix", rel_path, errors)
    if not isinstance(items, list):
        return
    for index, item in enumerate(items, start=1):
        prefix = f"{rel_path}: evidence_source_matrix item {index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be object")
            continue
        claim_id = item.get("claim_id")
        _require_nonempty_string(item, "claim_id", prefix, errors)
        if isinstance(claim_id, str) and ledger_ids and claim_id not in ledger_ids:
            errors.append(f"{prefix}: claim_id is not present in report_claim_ledger")
        _require_enum(item, "source_class", OPPONENT_TRACE_EVIDENCE_CLASSES, prefix, errors)
        _require_enum(item, "support_mode", OPPONENT_TRACE_SUPPORT_MODES, prefix, errors)
        _require_nonempty_list(item, "source_refs", prefix, errors)
        if item.get("source_class") == "media_visual" or "media_status" in item:
            _require_enum(item, "media_status", OPPONENT_TRACE_MEDIA_STATUSES, prefix, errors)


def _validate_technical_report_scope_basis(
    value: Any,
    rel_path: str,
    round_dir: Path | None,
    errors: list[str],
) -> None:
    prefix = f"{rel_path}: technical_report_scope_basis"
    if not isinstance(value, dict):
        errors.append(f"{prefix} must be object")
        return
    _require_enum(value, "status", OPPONENT_TRACE_SCOPE_BASIS_STATUSES, prefix, errors)
    _require_enum(value, "wording_mode", OPPONENT_TRACE_WORDING_MODES, prefix, errors)
    _require_nonempty_list(value, "evidence_refs", prefix, errors)
    if value.get("status") == "checker_summary":
        if value.get("summary_path") != THESES_CHECKER_SUMMARY_REL:
            errors.append(f"{prefix}: summary_path must be {THESES_CHECKER_SUMMARY_REL}")
        digest = value.get("summary_sha256")
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            errors.append(f"{prefix}: summary_sha256 must be a 64-character hex string")
        elif round_dir is not None:
            summary_path = round_dir / THESES_CHECKER_SUMMARY_REL
            if not summary_path.is_file():
                errors.append(f"{prefix}: referenced checker summary is missing")
            elif sha256_file(summary_path) != digest:
                errors.append(f"{prefix}: summary_sha256 is stale for {THESES_CHECKER_SUMMARY_REL}")
            else:
                summary_errors = validate_theses_checker_summary_artifact(round_dir, THESES_CHECKER_SUMMARY_REL)
                errors.extend(f"{prefix}: {error}" for error in summary_errors)
                if not summary_errors:
                    _validate_technical_report_scope_summary_wording(value, prefix, summary_path, errors)
    else:
        if "summary_path" in value or "summary_sha256" in value:
            errors.append(f"{prefix}: summary_path and summary_sha256 require status checker_summary")
        limitation = value.get("typed_limitation")
        if not isinstance(limitation, dict):
            errors.append(f"{prefix}: typed_limitation must be object when status is operator_accepted_limitation")
        else:
            _require_nonempty_string(limitation, "type", f"{prefix}: typed_limitation", errors)
            _require_nonempty_string(limitation, "description", f"{prefix}: typed_limitation", errors)
            _require_nonempty_string(limitation, "accepted_by", f"{prefix}: typed_limitation", errors)


def _validate_technical_report_scope_summary_wording(
    value: dict[str, Any],
    prefix: str,
    summary_path: Path,
    errors: list[str],
) -> None:
    if value.get("wording_mode") != "direct":
        return
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(summary, dict):
        return
    if not isinstance(summary.get("checked_pdf"), dict):
        errors.append(f"{prefix}: wording_mode direct requires checked_pdf in {THESES_CHECKER_SUMMARY_REL}")
    if summary.get("status") in {"unknown_threshold", "not_applicable"}:
        errors.append(f"{prefix}: wording_mode direct requires a categorical theses checker summary status")


def _validate_strength_grade_tension(value: Any, rel_path: str, errors: list[str]) -> None:
    prefix = f"{rel_path}: strength_grade_tension"
    if not isinstance(value, dict):
        errors.append(f"{prefix} must be object")
        return
    _require_nonempty_list(value, "strength_refs", prefix, errors)
    _require_nonempty_list(value, "limiting_factor_refs", prefix, errors)
    _require_nonempty_string(value, "grade_interval_rationale", prefix, errors)
    _require_nonempty_string(value, "private_comment_focus", prefix, errors)


def _validate_defense_question_strategy(
    value: Any,
    question_ids: set[str],
    rel_path: str,
    errors: list[str],
) -> None:
    items = _require_nonempty_list({"defense_question_strategy": value}, "defense_question_strategy", rel_path, errors)
    if not isinstance(items, list):
        return
    seen: set[str] = set()
    for index, item in enumerate(items, start=1):
        prefix = f"{rel_path}: defense_question_strategy item {index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be object")
            continue
        question_id = item.get("question_id")
        if isinstance(question_id, str):
            if question_id in seen:
                errors.append(f"{prefix}: duplicate question_id {question_id}")
            seen.add(question_id)
            if question_ids and question_id not in question_ids:
                errors.append(f"{prefix}: question_id is not present in defense_questions")
        _require_nonempty_string(item, "question_id", prefix, errors)
        _require_nonempty_string(item, "purpose", prefix, errors)
        _require_enum(item, "target_item_id", REQUIRED_OPPONENT_IS_ITEM_IDS, prefix, errors)
        _require_nonempty_string(item, "evidence_gap_or_tension", prefix, errors)
        _require_bool(item, "single_focus", prefix, errors)
    missing = sorted(question_ids - seen)
    if missing:
        errors.append(f"{rel_path}: defense_question_strategy missing question ids: {', '.join(missing)}")


def _validate_materiality_bound_trace_ref(value: Any, field: str, rel_path: str, errors: list[str]) -> None:
    prefix = f"{rel_path}: {field}"
    if not isinstance(value, dict):
        errors.append(f"{prefix} must be object")
        return
    _require_nonempty_string(value, "summary", prefix, errors)
    _require_nonempty_list(value, "evidence_refs", prefix, errors)
    _require_enum(value, "wording_mode", OPPONENT_TRACE_WORDING_MODES, prefix, errors)
    _require_nonempty_string(value, "materiality_reason", prefix, errors)
    limitations = value.get("limitations")
    if not isinstance(limitations, list) or not all(isinstance(limitation, str) for limitation in limitations):
        errors.append(f"{prefix}: limitations must be a list of strings")


def _validate_supervisor_report_feedback_history(
    loaded: dict[str, Any],
    rel_path: str,
    round_dir: Path | None,
    errors: list[str],
) -> None:
    _require_enum(loaded, "feedback_status", SUPERVISOR_FEEDBACK_HISTORY_STATUSES, rel_path, errors)
    _require_nonempty_string(loaded, "summary", rel_path, errors)
    _require_list(loaded, "feedback_round_refs", rel_path, errors)
    _require_list(loaded, "revision_evidence_refs", rel_path, errors)
    status = loaded.get("feedback_status")
    evidence_items = _require_list(loaded, "evidence_items", rel_path, errors)
    item_requires_hashes = any(
        isinstance(item, dict) and item.get("status") in SUPERVISOR_EVIDENCE_BEARING_FEEDBACK_STATUSES
        for item in evidence_items
        if isinstance(evidence_items, list)
    )
    if status in SUPERVISOR_EVIDENCE_BEARING_FEEDBACK_STATUSES:
        if isinstance(evidence_items, list) and not evidence_items:
            errors.append(f"{rel_path}: evidence_items must not be empty for feedback_status {status}")
    if status in SUPERVISOR_EVIDENCE_BEARING_FEEDBACK_STATUSES or item_requires_hashes:
        _validate_source_ref_hashes(
            loaded,
            f"{rel_path}: source_ref_hashes",
            refs=_collect_feedback_history_refs(loaded),
            round_dir=round_dir,
            errors=errors,
        )
    if isinstance(evidence_items, list):
        for index, item in enumerate(evidence_items, start=1):
            prefix = f"{rel_path}: evidence_items item {index}"
            if not isinstance(item, dict):
                errors.append(f"{prefix} must be object")
                continue
            _require_nonempty_string(item, "item_id", prefix, errors)
            _require_enum(item, "status", SUPERVISOR_FEEDBACK_HISTORY_STATUSES, prefix, errors)
            _require_nonempty_string(item, "summary", prefix, errors)
            _require_list(item, "feedback_refs", prefix, errors)
            _require_list(item, "revision_evidence_refs", prefix, errors)
            _require_list(item, "limitations", prefix, errors)
            item_status = item.get("status")
            if item_status in SUPERVISOR_EVIDENCE_BEARING_FEEDBACK_STATUSES:
                feedback_refs = item.get("feedback_refs")
                revision_refs = item.get("revision_evidence_refs")
                if isinstance(feedback_refs, list) and not feedback_refs:
                    errors.append(f"{prefix}: feedback_refs must not be empty for status {item_status}")
                if isinstance(revision_refs, list) and not revision_refs:
                    errors.append(f"{prefix}: revision_evidence_refs must not be empty for status {item_status}")


def _collect_feedback_history_refs(loaded: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for field in ("feedback_round_refs", "revision_evidence_refs"):
        values = loaded.get(field)
        if isinstance(values, list):
            refs.extend(value for value in values if isinstance(value, str))
    evidence_items = loaded.get("evidence_items")
    if isinstance(evidence_items, list):
        for item in evidence_items:
            if not isinstance(item, dict):
                continue
            for field in ("feedback_refs", "revision_evidence_refs"):
                values = item.get(field)
                if isinstance(values, list):
                    refs.extend(value for value in values if isinstance(value, str))
    return sorted(dict.fromkeys(refs))


def _validate_supervisor_report_trace(
    loaded: dict[str, Any],
    rel_path: str,
    round_dir: Path | None,
    case_id: str | None,
    round_id: str | None,
    errors: list[str],
) -> None:
    _validate_expected_hash_binding(
        loaded,
        rel_path,
        round_dir,
        errors,
        path_field="supervisor_input_path",
        hash_field="supervisor_input_sha256",
        expected_path="notes/supervisor-report-operator-input.md",
    )
    _require_enum(loaded, "prior_feedback_status", SUPERVISOR_FEEDBACK_HISTORY_STATUSES, rel_path, errors)
    prior_feedback_status = loaded.get("prior_feedback_status")
    feedback_history_binding_present = "feedback_history_path" in loaded or "feedback_history_sha256" in loaded
    if prior_feedback_status in SUPERVISOR_EVIDENCE_BEARING_FEEDBACK_STATUSES and not feedback_history_binding_present:
        errors.append(
            f"{rel_path}: feedback_history_path and feedback_history_sha256 are required for "
            f"prior_feedback_status {prior_feedback_status}"
        )
    if feedback_history_binding_present:
        _validate_expected_hash_binding(
            loaded,
            rel_path,
            round_dir,
            errors,
            path_field="feedback_history_path",
            hash_field="feedback_history_sha256",
            expected_path=SUPERVISOR_REPORT_FEEDBACK_HISTORY_REL,
        )
        if round_dir is not None and (round_dir / SUPERVISOR_REPORT_FEEDBACK_HISTORY_REL).is_file():
            errors.extend(
                validate_structured_evidence_artifact(
                    round_dir,
                    SUPERVISOR_REPORT_FEEDBACK_HISTORY_REL,
                    case_id=case_id,
                    round_id=round_id,
                )
            )
    item_ids: set[str] = set()
    prior_feedback_ref_seen = False
    report_fields = _require_list(loaded, "report_fields", rel_path, errors)
    if isinstance(report_fields, list):
        for index, item in enumerate(report_fields, start=1):
            prefix = f"{rel_path}: report_fields item {index}"
            if not isinstance(item, dict):
                errors.append(f"{prefix} must be object")
                continue
            field_id = item.get("field_id")
            if isinstance(field_id, str):
                if field_id in item_ids:
                    errors.append(f"{prefix}: duplicate field_id {field_id}")
                item_ids.add(field_id)
            _require_enum(item, "field_id", REQUIRED_SUPERVISOR_REPORT_FIELD_IDS, prefix, errors)
            _require_nonempty_string(item, "title", prefix, errors)
            _require_nonempty_string(item, "formulation", prefix, errors)
            _require_enum(item, "visibility", SUPERVISOR_REPORT_FIELD_VISIBILITIES, prefix, errors)
            _require_list(item, "evidence_refs", prefix, errors)
            _require_nonempty_list(item, "supervisor_input_refs", prefix, errors)
            _require_list(item, "prior_feedback_refs", prefix, errors)
            prior_feedback_refs = item.get("prior_feedback_refs")
            if isinstance(prior_feedback_refs, list) and prior_feedback_refs:
                prior_feedback_ref_seen = True
            _require_nonempty_list(item, "report_refs", prefix, errors)
            report_refs = item.get("report_refs")
            if isinstance(report_refs, list):
                for ref_index, ref in enumerate(report_refs, start=1):
                    if ref != "work/vedouci_posudek_draft.md":
                        errors.append(f"{prefix}: report_refs item {ref_index} must be work/vedouci_posudek_draft.md")
            if field_id == "student_comment" and item.get("visibility") != "private_student_comment":
                errors.append(f"{prefix}: student_comment must have private_student_comment visibility")
            if field_id != "student_comment" and item.get("visibility") == "private_student_comment":
                errors.append(f"{prefix}: only student_comment may have private_student_comment visibility")
    missing_ids = sorted(REQUIRED_SUPERVISOR_REPORT_FIELD_IDS - item_ids)
    if missing_ids:
        errors.append(f"{rel_path}: missing required report_fields: {', '.join(missing_ids)}")
    if prior_feedback_status in SUPERVISOR_EVIDENCE_BEARING_FEEDBACK_STATUSES and not prior_feedback_ref_seen:
        errors.append(
            f"{rel_path}: evidenced prior_feedback_status requires at least one report field prior_feedback_refs"
        )
    _validate_supervisor_grading(loaded.get("grading"), rel_path, errors)
    _validate_supervisor_uncertainty_items(loaded, rel_path, errors)
    _validate_supervisor_manual_checks(loaded, rel_path, errors)


def _validate_supervisor_grading(value: Any, rel_path: str, errors: list[str]) -> None:
    prefix = f"{rel_path}: grading"
    if not isinstance(value, dict):
        errors.append(f"{prefix} must be object")
        return
    _require_enum(value, "grade", SUPERVISOR_REPORT_GRADES, prefix, errors)
    points = value.get("points")
    if points is not None:
        if not isinstance(points, int):
            errors.append(f"{prefix}: points must be int or null")
        elif points < 0 or points > 100:
            errors.append(f"{prefix}: points must be between 0 and 100")
    interval = value.get("points_interval")
    if interval is not None and not isinstance(interval, str):
        errors.append(f"{prefix}: points_interval must be str or null")
    _require_nonempty_string(value, "rationale", prefix, errors)
    _require_nonempty_list(value, "supervisor_input_refs", prefix, errors)


def _validate_supervisor_uncertainty_items(loaded: dict[str, Any], rel_path: str, errors: list[str]) -> None:
    uncertainty_items = _require_list(loaded, "uncertainty_items", rel_path, errors)
    if not isinstance(uncertainty_items, list):
        return
    for index, item in enumerate(uncertainty_items, start=1):
        prefix = f"{rel_path}: uncertainty_items item {index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be object")
            continue
        _require_nonempty_string(item, "claim_id", prefix, errors)
        _require_nonempty_string(item, "summary", prefix, errors)
        _require_nonempty_string(item, "handling_instruction", prefix, errors)
        _require_nonempty_list(item, "source_refs", prefix, errors)
        _require_nonempty_list(item, "target_field_ids", prefix, errors)
        target_ids = item.get("target_field_ids")
        if isinstance(target_ids, list):
            for target_index, target_id in enumerate(target_ids, start=1):
                if target_id not in REQUIRED_SUPERVISOR_REPORT_FIELD_IDS:
                    errors.append(f"{prefix}: target_field_ids item {target_index} has unknown supervisor field id")
        _require_enum(item, "status", SUPERVISOR_REPORT_UNCERTAINTY_STATUSES, prefix, errors)


def _validate_supervisor_manual_checks(loaded: dict[str, Any], rel_path: str, errors: list[str]) -> None:
    manual_checks = _require_list(loaded, "manual_checks", rel_path, errors)
    if not isinstance(manual_checks, list):
        return
    for index, item in enumerate(manual_checks, start=1):
        prefix = f"{rel_path}: manual_checks item {index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be object")
            continue
        _require_nonempty_string(item, "check_id", prefix, errors)
        _require_nonempty_string(item, "instruction", prefix, errors)
        _require_list(item, "evidence_refs", prefix, errors)


def _validate_supervisor_report_confirmation(
    loaded: dict[str, Any],
    rel_path: str,
    round_dir: Path | None,
    errors: list[str],
) -> None:
    _validate_expected_hash_binding(
        loaded,
        rel_path,
        round_dir,
        errors,
        path_field="reviewed_report_path",
        hash_field="reviewed_report_sha256",
        expected_path="outputs/vedouci_posudek_revidovany.md",
    )
    _require_enum(loaded, "grade", {"A", "B", "C", "D", "E", "F"}, rel_path, errors)
    points = loaded.get("points")
    if not isinstance(points, int) or points < 0 or points > 100:
        errors.append(f"{rel_path}: points must be int between 0 and 100")
    for field in ("official_text_confirmed", "student_comment_confirmed"):
        _require_bool(loaded, field, rel_path, errors)
        if loaded.get(field) is not True:
            errors.append(f"{rel_path}: {field} must be true for confirmation")
    _require_bool(loaded, "ready_for_is", rel_path, errors)
    if loaded.get("ready_for_is") is not True:
        errors.append(f"{rel_path}: ready_for_is must be true for confirmation")
    _require_nonempty_string(loaded, "confirmed_by", rel_path, errors)
    _require_nonempty_string(loaded, "confirmed_at", rel_path, errors)


def _validate_current_evidence_snapshot(
    loaded: dict[str, Any],
    rel_path: str,
    round_dir: Path | None,
    errors: list[str],
) -> None:
    items = _require_list(loaded, "items", rel_path, errors)
    if not isinstance(items, list):
        return
    item_ids: set[str] = set()
    for index, item in enumerate(items, start=1):
        prefix = f"{rel_path}: items item {index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be object")
            continue
        item_id = item.get("item_id")
        if isinstance(item_id, str):
            if item_id in item_ids:
                errors.append(f"{prefix}: duplicate item_id {item_id}")
            item_ids.add(item_id)
        _require_nonempty_string(item, "item_id", prefix, errors)
        path = item.get("path")
        if not isinstance(path, str) or not path:
            errors.append(f"{prefix}: path must be non-empty str")
        elif not _is_allowed_round_ref(path):
            errors.append(f"{prefix}: path must be under inputs/, extracted/, notes/, work/, or outputs/")
        status = item.get("status")
        _require_enum(item, "status", CURRENT_EVIDENCE_ITEM_STATUSES, prefix, errors)
        _require_enum(item, "freshness", CURRENT_EVIDENCE_FRESHNESS_STATUSES, prefix, errors)
        _require_bool(item, "readiness_relevant", prefix, errors)
        _require_list(item, "limitations", prefix, errors)
        _require_nonempty_string(item, "recorded_at", prefix, errors)
        sha256 = item.get("sha256")
        target = (
            round_dir / path
            if round_dir is not None and isinstance(path, str) and _is_allowed_round_ref(path)
            else None
        )
        if status == "present":
            if not isinstance(sha256, str) or not SHA256_RE.fullmatch(sha256):
                errors.append(f"{prefix}: sha256 must be a 64-character hex string when status is present")
            elif target is not None:
                if target.is_file():
                    if sha256_file(target) != sha256:
                        errors.append(f"{prefix}: sha256 is stale for {path}")
                else:
                    errors.append(f"{prefix}: path marked present but file is missing or invalid: {path}")
        elif sha256 is not None:
            if not isinstance(sha256, str) or not SHA256_RE.fullmatch(sha256):
                errors.append(f"{prefix}: sha256 must be a 64-character hex string when recorded")
        if target is not None:
            if status == "missing" and target.exists():
                errors.append(f"{prefix}: path marked missing but file exists or is invalid: {path}")
            if status == "invalid" and target.is_file():
                errors.append(f"{prefix}: path marked invalid but file is present: {path}")
            if status == "invalid" and not target.exists():
                errors.append(f"{prefix}: path marked invalid but file is missing: {path}")


def _validate_theses_similarity_assessment(
    loaded: dict[str, Any],
    rel_path: str,
    round_dir: Path | None,
    errors: list[str],
) -> None:
    _require_enum(loaded, "current_submission_match", CURRENT_SUBMISSION_MATCH_STATUSES, rel_path, errors)
    _validate_hashes_for_refs(loaded, rel_path, "source_sha256", "source_refs", round_dir, errors)
    loaded_source_refs = loaded.get("source_refs")
    source_refs = loaded_source_refs if isinstance(loaded_source_refs, list) else []
    validate_long_lived_semantic_source_refs(rel_path, "source_refs", source_refs, errors)
    judgments = _require_list(loaded, "judgments", rel_path, errors)
    if not isinstance(judgments, list):
        return
    judgment_ids: set[str] = set()
    for index, item in enumerate(judgments, start=1):
        prefix = f"{rel_path}: judgments item {index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be object")
            continue
        judgment_id = item.get("judgment_id")
        if isinstance(judgment_id, str):
            if judgment_id in judgment_ids:
                errors.append(f"{prefix}: duplicate judgment_id {judgment_id}")
            judgment_ids.add(judgment_id)
        _require_nonempty_string(item, "judgment_id", prefix, errors)
        _require_nonempty_list(item, "source_ids", prefix, errors)
        source_ids = item.get("source_ids")
        if isinstance(source_ids, list):
            for source_index, source_id in enumerate(source_ids, start=1):
                if not isinstance(source_id, int) and not isinstance(source_id, str):
                    errors.append(f"{prefix}: source_ids item {source_index} must be int or str")
        _validate_theses_passage_refs(item, prefix, round_dir, errors)
        _require_nonempty_list(item, "basis_refs", prefix, errors)
        category = item.get("category")
        _require_enum(item, "category", SIMILARITY_JUDGMENT_CATEGORIES, prefix, errors)
        _require_nonempty_string(item, "rationale", prefix, errors)
        _require_enum(item, "confidence", SIMILARITY_CONFIDENCE_VALUES, prefix, errors)
        _require_nonempty_list(item, "evidence_refs", prefix, errors)
        synthesis_action = item.get("synthesis_action")
        _require_enum(item, "synthesis_action", SIMILARITY_SYNTHESIS_ACTIONS, prefix, errors)
        _require_bool(item, "requires_reviewer_verification", prefix, errors)
        _require_list(item, "limitations", prefix, errors)
        _validate_theses_judgment_source_binding(item, prefix, source_refs, errors)
        if category == "no_material_concern" and synthesis_action != "silent":
            errors.append(f"{prefix}: no_material_concern must use synthesis_action silent")
        if category in SIMILARITY_UNRESOLVED_CATEGORIES:
            if synthesis_action == "silent":
                errors.append(f"{prefix}: unresolved/material category must not use synthesis_action silent")
            if item.get("requires_reviewer_verification") is not True:
                errors.append(f"{prefix}: unresolved/material category requires reviewer verification")


def _validate_theses_passage_refs(
    item: dict[str, Any],
    prefix: str,
    round_dir: Path | None,
    errors: list[str],
) -> None:
    passage_refs = _require_nonempty_list(item, "passage_refs", prefix, errors)
    if not isinstance(passage_refs, list):
        return
    known_passages = _known_theses_passage_ids(round_dir)
    for index, value in enumerate(passage_refs, start=1):
        label = f"{prefix}: passage_refs item {index}"
        if not isinstance(value, str) or not value:
            errors.append(f"{label}: passage ref must be non-empty str")
            continue
        base, separator, passage_id = value.partition("#")
        if base != "work/theses_similarity/intake.json" or separator != "#" or not passage_id:
            errors.append(f"{label}: passage ref must be work/theses_similarity/intake.json#<passage-id>")
            continue
        if known_passages is not None and passage_id not in known_passages:
            errors.append(f"{label}: unknown matched passage id {passage_id}")


def _known_theses_passage_ids(round_dir: Path | None) -> set[str] | None:
    if round_dir is None:
        return None
    path = round_dir / "work/theses_similarity/intake.json"
    if not path.is_file():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(loaded, dict):
        return None
    passages = loaded.get("matched_passages")
    if not isinstance(passages, list):
        return None
    return {
        item["passage_id"] for item in passages if isinstance(item, dict) and isinstance(item.get("passage_id"), str)
    }


def _validate_theses_judgment_source_binding(
    item: dict[str, Any],
    prefix: str,
    source_refs: list[Any],
    errors: list[str],
) -> None:
    source_ref_set = {value for value in source_refs if isinstance(value, str)}
    supporting_refs: set[str] = set()
    for field in ("passage_refs", "basis_refs", "evidence_refs"):
        refs = item.get(field)
        if not isinstance(refs, list):
            continue
        for ref in refs:
            if isinstance(ref, str):
                supporting_refs.add(ref.split("#", 1)[0])
    missing = sorted(ref for ref in supporting_refs if ref not in source_ref_set)
    if missing:
        errors.append(f"{prefix}: supporting refs must be listed in top-level source_refs: {', '.join(missing)}")


def _validate_hashes_for_refs(
    loaded: dict[str, Any],
    rel_path: str,
    hash_field: str,
    refs_field: str,
    round_dir: Path | None,
    errors: list[str],
) -> None:
    hashes = loaded.get(hash_field)
    if not isinstance(hashes, dict):
        errors.append(f"{rel_path}: {hash_field} must be object")
        return
    refs = loaded.get(refs_field)
    if not isinstance(refs, list):
        return
    for ref in refs:
        if not isinstance(ref, str) or not _is_allowed_round_ref(ref):
            continue
        recorded = hashes.get(ref)
        if not isinstance(recorded, str) or not SHA256_RE.fullmatch(recorded):
            errors.append(f"{rel_path}: {hash_field} missing 64-character hash for {ref}")
            continue
        if round_dir is not None:
            path = round_dir / ref
            if path.is_file() and sha256_file(path) != recorded:
                errors.append(f"{rel_path}: {hash_field} hash is stale for {ref}")


def _validate_calibration_context(
    value: Any,
    rel_path: str,
    round_dir: Path | None,
    case_id: str | None,
    round_id: str | None,
    errors: list[str],
) -> None:
    from thesis_review_workflow.opponent_calibration import (
        validate_opponent_calibration_artifact,
        validate_round_hash_binding,
    )

    prefix = f"{rel_path}: calibration_context"
    if not isinstance(value, dict):
        errors.append(f"{prefix} must be object")
        return
    use_present = "calibration_use_path" in value or "calibration_use_sha256" in value
    advisory_present = "calibration_advisory_path" in value or "calibration_advisory_sha256" in value
    if use_present == advisory_present:
        errors.append(f"{prefix}: exactly one of calibration_use or calibration_advisory binding is required")
    elif use_present:
        errors.extend(
            validate_round_hash_binding(
                value,
                prefix,
                path_field="calibration_use_path",
                hash_field="calibration_use_sha256",
                expected_path=OPPONENT_CALIBRATION_USE_REL,
                round_dir=round_dir,
            )
        )
        if round_dir is not None:
            errors.extend(
                validate_opponent_calibration_artifact(
                    round_dir,
                    OPPONENT_CALIBRATION_USE_REL,
                    case_id=case_id,
                    round_id=round_id,
                    allow_stale_trace_binding=True,
                )
            )
    else:
        errors.extend(
            validate_round_hash_binding(
                value,
                prefix,
                path_field="calibration_advisory_path",
                hash_field="calibration_advisory_sha256",
                expected_path=OPPONENT_CALIBRATION_ADVISORY_REL,
                round_dir=round_dir,
            )
        )
        if round_dir is not None:
            errors.extend(
                validate_opponent_calibration_artifact(
                    round_dir,
                    OPPONENT_CALIBRATION_ADVISORY_REL,
                    case_id=case_id,
                    round_id=round_id,
                    allow_stale_trace_binding=True,
                )
            )
    required_bindings = (
        ("reference_report_comparison_path", "reference_report_comparison_sha256", REFERENCE_REPORT_COMPARISON_REL),
        ("opponent_reading_packet_path", "opponent_reading_packet_sha256", OPPONENT_READING_PACKET_REL),
    )
    for path_field, hash_field, expected_path in required_bindings:
        path_present = path_field in value
        hash_present = hash_field in value
        if not path_present or not hash_present:
            errors.append(f"{prefix}: {path_field} and {hash_field} are required")
        else:
            errors.extend(
                validate_round_hash_binding(
                    value,
                    prefix,
                    path_field=path_field,
                    hash_field=hash_field,
                    expected_path=expected_path,
                    round_dir=round_dir,
                )
            )
    _require_bool(value, "revision_applied", prefix, errors)
    revision_applied = value.get("revision_applied") is True
    revision_path_present = "revision_request_path" in value
    revision_hash_present = "revision_request_sha256" in value
    if revision_applied and (not revision_path_present or not revision_hash_present):
        errors.append(
            f"{prefix}: revision_request_path and revision_request_sha256 are required when revision_applied is true"
        )
    elif revision_path_present != revision_hash_present:
        errors.append(f"{prefix}: revision_request_path and revision_request_sha256 must be recorded together")
    elif revision_path_present:
        errors.extend(
            validate_round_hash_binding(
                value,
                prefix,
                path_field="revision_request_path",
                hash_field="revision_request_sha256",
                expected_path=OPPONENT_REPORT_REVISION_REQUEST_REL,
                round_dir=round_dir,
            )
        )
        if round_dir is not None:
            errors.extend(
                validate_opponent_calibration_artifact(
                    round_dir,
                    OPPONENT_REPORT_REVISION_REQUEST_REL,
                    case_id=case_id,
                    round_id=round_id,
                )
            )
    elif not revision_applied:
        revision_reason = value.get("revision_not_applicable_reason")
        if not isinstance(revision_reason, str) or not revision_reason:
            errors.append(f"{prefix}: revision_not_applicable_reason must be recorded when revision_applied is false")
    _require_enum(value, "anti_overfit_review_status", OPPONENT_TRACE_ANTI_OVERFIT_STATUSES, prefix, errors)
    if value.get("anti_overfit_review_status") in {"reviewed", "reviewed_with_notes"}:
        _require_nonempty_string(value, "anti_overfit_reviewer_role", prefix, errors)
        if not isinstance(value.get("anti_overfit_reviewer_agent"), str) and not isinstance(
            value.get("anti_overfit_human_note"), str
        ):
            errors.append(f"{prefix}: anti_overfit_reviewer_agent or anti_overfit_human_note must be recorded")
        _require_nonempty_string(value, "reviewed_at", prefix, errors)
    _require_list(value, "limitations", prefix, errors)


def _report_calibration_basis_required(loaded: dict[str, Any], round_dir: Path | None) -> bool:
    if (
        "report_calibration_basis_path" in loaded
        or "report_calibration_basis_sha256" in loaded
        or "calibration_preference_ids" in loaded
        or "calibration_preference_applications" in loaded
    ):
        return True
    if round_dir is None:
        return False
    if (round_dir / REPORT_CALIBRATION_BASIS_REL).is_file():
        return True
    if "report_calibration_limitation" in loaded:
        return False
    return _round_has_report_calibration_context(round_dir)


def _round_has_report_calibration_context(round_dir: Path) -> bool:
    _, profile_sources, _ = _effective_reviewer_profile_context(round_dir)
    return bool(profile_sources)


def _existing_report_calibration_source_paths(round_dir: Path) -> tuple[str, ...]:
    return tuple(
        rel_path for rel_path in report_calibration_source_paths(round_dir) if (round_dir / rel_path).is_file()
    )


def _effective_reviewer_profile_context(round_dir: Path) -> tuple[str | None, list[str] | None, list[str]]:
    if len(round_dir.parents) < 4:
        return None, None, []
    case_md = round_dir.parents[1] / "case.md"
    repo_root = round_dir.parents[3]
    if not case_md.is_file() or not (repo_root / "profiles").is_dir():
        return None, None, []
    profile_id, profile_sources, profile_errors = effective_reviewer_profile(case_md, repo_root)
    return profile_id, profile_sources, profile_errors


def _repo_root_from_round_context(round_dir: Path) -> Path | None:
    if len(round_dir.parents) >= 4:
        repo_root = round_dir.parents[3]
        if (repo_root / "profiles").is_dir():
            return repo_root
    return None


def _validate_report_calibration_basis_binding(
    loaded: dict[str, Any],
    rel_path: str,
    round_dir: Path | None,
    case_id: str | None,
    round_id: str | None,
    errors: list[str],
) -> dict[str, Any] | None:
    _validate_expected_hash_binding(
        loaded,
        rel_path,
        round_dir,
        errors,
        path_field="report_calibration_basis_path",
        hash_field="report_calibration_basis_sha256",
        expected_path=REPORT_CALIBRATION_BASIS_REL,
    )
    _require_source_ref_contains(loaded, "source_refs", REPORT_CALIBRATION_BASIS_REL, rel_path, errors)
    _require_source_ref_contains(loaded, "trace_generated_from", REPORT_CALIBRATION_BASIS_REL, rel_path, errors)
    if round_dir is None:
        return None
    expected_profile_id, expected_profile_sources, profile_errors = _effective_reviewer_profile_context(round_dir)
    errors.extend(f"{rel_path}: {error}" for error in profile_errors)
    errors.extend(
        validate_report_calibration_artifact(
            round_dir,
            REPORT_CALIBRATION_BASIS_REL,
            case_id=case_id,
            round_id=round_id,
            expected_reviewer_profile_id=expected_profile_id,
            expected_profile_source_paths=expected_profile_sources,
        )
    )
    path = round_dir / REPORT_CALIBRATION_BASIS_REL
    try:
        loaded_basis = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return loaded_basis if isinstance(loaded_basis, dict) else None


def _validate_report_calibration_limitation(
    value: Any,
    rel_path: str,
    round_dir: Path | None,
    errors: list[str],
) -> None:
    prefix = f"{rel_path}: report_calibration_limitation"
    if not isinstance(value, dict):
        errors.append(f"{prefix} must be object")
        return
    _require_enum(value, "type", {OPPONENT_TRACE_CALIBRATION_LIMITATION_TYPE}, prefix, errors)
    _require_enum(value, "calibration_scope", {"opponent_report"}, prefix, errors)
    _require_enum(value, "assessed_by", {"agent", "human"}, prefix, errors)
    _require_nonempty_string(value, "assessor_role", prefix, errors)
    _require_nonempty_string(value, "assessed_at", prefix, errors)
    _require_nonempty_string(value, "rationale", prefix, errors)
    expected_profile_id: str | None = None
    expected_profile_sources: list[str] | None = None
    if round_dir is not None:
        expected_profile_id, expected_profile_sources, profile_errors = _effective_reviewer_profile_context(round_dir)
        errors.extend(f"{prefix}: {error}" for error in profile_errors)
    if expected_profile_id is not None and value.get("reviewer_profile_id") != expected_profile_id:
        errors.append(f"{prefix}: reviewer_profile_id does not match case Reviewer profile")
    elif expected_profile_id is None:
        _require_nonempty_string(value, "reviewer_profile_id", prefix, errors)
    _validate_report_calibration_limitation_profile_sources(
        value.get("profile_sources"),
        prefix,
        round_dir,
        expected_profile_sources,
        errors,
    )
    _validate_report_calibration_limitation_operator_sources(
        value.get("operator_calibration_sources"),
        prefix,
        round_dir,
        errors,
    )


def _validate_report_calibration_limitation_profile_sources(
    value: Any,
    prefix: str,
    round_dir: Path | None,
    expected_profile_sources: list[str] | None,
    errors: list[str],
) -> None:
    sources = value
    if not isinstance(sources, list):
        errors.append(f"{prefix}: profile_sources must be list")
        return
    repo_root = _repo_root_from_round_context(round_dir) if round_dir is not None else None
    expected = set(expected_profile_sources or [])
    seen: dict[str, str] = {}
    for index, item in enumerate(sources, start=1):
        item_prefix = f"{prefix}: profile_sources item {index}"
        if not isinstance(item, dict):
            errors.append(f"{item_prefix} must be object")
            continue
        path = item.get("path")
        digest = item.get("sha256")
        if not isinstance(path, str) or not path:
            errors.append(f"{item_prefix}: path must be non-empty str")
            continue
        if expected and path not in expected:
            errors.append(f"{item_prefix}: path is not an effective reviewer profile source")
        if path in seen:
            errors.append(f"{item_prefix}: duplicate profile source {path}")
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            errors.append(f"{item_prefix}: sha256 must be a 64-character hex string")
        else:
            seen[path] = digest
            if repo_root is not None and path in expected:
                profile_path = repo_root / path
                if profile_path.is_file() and sha256_file(profile_path) != digest:
                    errors.append(f"{item_prefix}: sha256 is stale for {path}")
    for path in sorted(expected.difference(seen)):
        errors.append(f"{prefix}: profile_sources missing effective reviewer profile source {path}")


def _validate_report_calibration_limitation_operator_sources(
    value: Any,
    prefix: str,
    round_dir: Path | None,
    errors: list[str],
) -> None:
    sources = value
    if not isinstance(sources, list):
        errors.append(f"{prefix}: operator_calibration_sources must be list")
        return
    expected = set(_existing_report_calibration_source_paths(round_dir)) if round_dir is not None else set()
    seen: dict[str, str] = {}
    for index, item in enumerate(sources, start=1):
        item_prefix = f"{prefix}: operator_calibration_sources item {index}"
        if not isinstance(item, dict):
            errors.append(f"{item_prefix} must be object")
            continue
        path = item.get("path")
        digest = item.get("sha256")
        if not isinstance(path, str) or not path:
            errors.append(f"{item_prefix}: path must be non-empty str")
            continue
        if expected and path not in expected:
            errors.append(f"{item_prefix}: path is not a current registered operator calibration source")
        if path in seen:
            errors.append(f"{item_prefix}: duplicate operator calibration source {path}")
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            errors.append(f"{item_prefix}: sha256 must be a 64-character hex string")
        else:
            seen[path] = digest
            if round_dir is not None and path in expected:
                source_path = round_dir / path
                if source_path.is_file() and sha256_file(source_path) != digest:
                    errors.append(f"{item_prefix}: sha256 is stale for {path}")
    for path in sorted(expected.difference(seen)):
        errors.append(f"{prefix}: operator_calibration_sources missing current registered source {path}")


def _validate_trace_calibration_preferences(
    loaded: dict[str, Any],
    basis_payload: dict[str, Any],
    rel_path: str,
    errors: list[str],
) -> None:
    declared = _require_nonempty_string_list(loaded, "calibration_preference_ids", rel_path, errors)
    basis_ids = set(report_calibration_applied_preference_ids(basis_payload))
    for preference_id in declared:
        if preference_id not in basis_ids:
            errors.append(
                f"{rel_path}: calibration_preference_ids includes unknown or unapplied preference {preference_id}"
            )
    applications = loaded.get("calibration_preference_applications")
    if not isinstance(applications, list):
        errors.append(f"{rel_path}: calibration_preference_applications must be list")
        return
    if not applications:
        errors.append(f"{rel_path}: calibration_preference_applications must not be empty")
    question_ids = _trace_question_ids(loaded)
    applied_ids: set[str] = set()
    mapped_controls: set[str] = set()
    for index, item in enumerate(applications, start=1):
        prefix = f"{rel_path}: calibration_preference_applications item {index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be object")
            continue
        mapped_preference_id = item.get("preference_id")
        if not isinstance(mapped_preference_id, str) or not mapped_preference_id:
            errors.append(f"{prefix}: preference_id must be non-empty str")
        else:
            applied_ids.add(mapped_preference_id)
            if mapped_preference_id not in declared:
                errors.append(f"{prefix}: preference_id must be listed in calibration_preference_ids")
        target_is = _validate_trace_target_list(item, "target_is_item_ids", prefix, errors)
        target_questions = _validate_trace_target_list(item, "target_defense_question_ids", prefix, errors)
        target_controls = _validate_trace_target_list(item, "target_report_controls", prefix, errors)
        for target in target_is:
            if target not in REQUIRED_OPPONENT_IS_ITEM_IDS:
                errors.append(f"{prefix}: target_is_item_ids contains unknown IS item id {target}")
        for target in target_questions:
            if target not in question_ids:
                errors.append(f"{prefix}: target_defense_question_ids contains unknown question id {target}")
        for target in target_controls:
            if target not in OPPONENT_TRACE_CALIBRATION_TARGET_CONTROLS:
                errors.append(f"{prefix}: target_report_controls contains unknown control {target}")
            else:
                mapped_controls.add(target)
        if not target_is and not target_questions and not target_controls:
            errors.append(f"{prefix}: at least one trace target must be recorded")
        _require_nonempty_string(item, "rationale", prefix, errors)
    for preference_id in sorted(set(declared).difference(applied_ids)):
        errors.append(f"{rel_path}: calibration_preference_applications missing preference {preference_id}")
    required_controls = report_calibration_expected_control_keys(basis_payload)
    for control in sorted(required_controls.difference(mapped_controls)):
        errors.append(f"{rel_path}: calibration_preference_applications missing expected report control {control}")


def _validate_calibration_context_control_conflicts(
    value: Any,
    basis_payload: dict[str, Any],
    rel_path: str,
    round_dir: Path | None,
    errors: list[str],
) -> None:
    if not isinstance(value, dict) or round_dir is None:
        return
    basis_controls = basis_payload.get("expected_report_controls")
    if not isinstance(basis_controls, dict):
        return
    for source_path, controls in _calibration_context_expected_controls(value, round_dir):
        for key, expected_value in basis_controls.items():
            if key in controls and controls[key] != expected_value:
                errors.append(
                    f"{rel_path}: calibration_context {source_path} expected_report_controls.{key} "
                    "conflicts with report_calibration_basis"
                )


def _validate_calibration_context_basis_relationship(
    value: Any,
    basis_payload: dict[str, Any],
    rel_path: str,
    errors: list[str],
) -> None:
    if not isinstance(value, dict):
        return
    related_hashes = report_calibration_related_artifact_hashes(basis_payload)
    for path_field, hash_field, expected_path in (
        ("calibration_use_path", "calibration_use_sha256", OPPONENT_CALIBRATION_USE_REL),
        ("calibration_advisory_path", "calibration_advisory_sha256", OPPONENT_CALIBRATION_ADVISORY_REL),
    ):
        if value.get(path_field) != expected_path:
            continue
        context_hash = value.get(hash_field)
        basis_hash = related_hashes.get(expected_path)
        if basis_hash is None:
            errors.append(
                f"{rel_path}: report_calibration_basis related_calibration_artifacts must include "
                f"{expected_path} when calibration_context uses it"
            )
        elif isinstance(context_hash, str) and basis_hash != context_hash:
            errors.append(
                f"{rel_path}: report_calibration_basis related_calibration_artifacts hash for "
                f"{expected_path} must match calibration_context"
            )


def _calibration_context_expected_controls(value: dict[str, Any], round_dir: Path) -> list[tuple[str, dict[str, Any]]]:
    paths: list[str] = []
    for field in (
        "calibration_use_path",
        "calibration_advisory_path",
        "revision_request_path",
    ):
        candidate = value.get(field)
        if isinstance(candidate, str) and _is_allowed_round_ref(candidate):
            paths.append(candidate)
    controls_by_path: list[tuple[str, dict[str, Any]]] = []
    for rel_path in sorted(dict.fromkeys(paths)):
        path = round_dir / rel_path
        if not path.is_file():
            continue
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(loaded, dict):
            continue
        controls = loaded.get("expected_report_controls")
        if isinstance(controls, dict):
            controls_by_path.append((rel_path, controls))
    return controls_by_path


def _trace_question_ids(loaded: dict[str, Any]) -> set[str]:
    values = loaded.get("defense_questions")
    if not isinstance(values, list):
        return set()
    return {
        item["question_id"] for item in values if isinstance(item, dict) and isinstance(item.get("question_id"), str)
    }


def _validate_trace_target_list(
    value: dict[str, Any],
    field: str,
    prefix: str,
    errors: list[str],
) -> list[str]:
    items = value.get(field)
    if not isinstance(items, list):
        errors.append(f"{prefix}: {field} must be list")
        return []
    result: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(items, start=1):
        if not isinstance(item, str) or not item:
            errors.append(f"{prefix}: {field} item {index} must be non-empty str")
            continue
        if item in seen:
            errors.append(f"{prefix}: {field} item {index} duplicates {item}")
            continue
        seen.add(item)
        result.append(item)
    return result


def _require_source_ref_contains(
    loaded: dict[str, Any],
    field: str,
    expected: str,
    rel_path: str,
    errors: list[str],
) -> None:
    value = loaded.get(field)
    if not isinstance(value, list):
        return
    if expected not in value:
        errors.append(f"{rel_path}: {field} must include {expected}")


def _require_nonempty_string_list(
    loaded: dict[str, Any],
    field: str,
    rel_path: str,
    errors: list[str],
) -> list[str]:
    values = loaded.get(field)
    if not isinstance(values, list):
        errors.append(f"{rel_path}: {field} must be list")
        return []
    if not values:
        errors.append(f"{rel_path}: {field} must not be empty")
    result: list[str] = []
    seen: set[str] = set()
    for index, value in enumerate(values, start=1):
        if not isinstance(value, str) or not value:
            errors.append(f"{rel_path}: {field} item {index} must be non-empty str")
            continue
        if value in seen:
            errors.append(f"{rel_path}: {field} item {index} duplicates {value}")
            continue
        seen.add(value)
        result.append(value)
    return result


def _validate_expected_hash_binding(
    loaded: dict[str, Any],
    rel_path: str,
    round_dir: Path | None,
    errors: list[str],
    *,
    path_field: str,
    hash_field: str,
    expected_path: str,
) -> None:
    path_value = loaded.get(path_field)
    hash_value = loaded.get(hash_field)
    if path_value != expected_path:
        errors.append(f"{rel_path}: {path_field} must be {expected_path}")
    if not isinstance(hash_value, str) or not SHA256_RE.fullmatch(hash_value):
        errors.append(f"{rel_path}: {hash_field} must be a 64-character hex string")
        return
    if not isinstance(path_value, str) or not _is_allowed_round_ref(path_value):
        return
    if round_dir is not None:
        path = round_dir / path_value
        if path.is_file() and sha256_file(path) != hash_value:
            errors.append(f"{rel_path}: {hash_field} is stale for {path_value}")


def _validate_source_ref_hashes(
    loaded: dict[str, Any],
    prefix: str,
    *,
    refs: list[str],
    round_dir: Path | None,
    errors: list[str],
) -> None:
    source_ref_hashes = loaded.get("source_ref_hashes")
    if not isinstance(source_ref_hashes, dict):
        errors.append(f"{prefix} must be object")
        return
    for ref in refs:
        recorded = source_ref_hashes.get(ref)
        if not isinstance(recorded, str) or not SHA256_RE.fullmatch(recorded):
            errors.append(f"{prefix}: missing 64-character hash for {ref}")
            continue
        if round_dir is not None and _is_allowed_round_ref(ref):
            path = round_dir / ref
            if path.is_file() and sha256_file(path) != recorded:
                errors.append(f"{prefix}: hash is stale for {ref}")


def _validate_source_materials_hash(
    loaded: dict[str, Any],
    rel_path: str,
    round_dir: Path,
    errors: list[str],
) -> None:
    source_path = loaded.get("source_materials_path")
    source_hash = loaded.get("source_materials_sha256")
    if not isinstance(source_path, str) or not isinstance(source_hash, str):
        return
    if not _is_allowed_round_ref(source_path):
        return
    path = round_dir / source_path
    if path.is_file() and sha256_file(path) != source_hash:
        errors.append(f"{rel_path}: source_materials_sha256 is stale for {source_path}")


def _validate_trace_questions(
    loaded: dict[str, Any],
    field: str,
    id_field: str,
    text_field: str,
    rel_path: str,
    errors: list[str],
) -> None:
    items = _require_nonempty_list(loaded, field, rel_path, errors)
    if not isinstance(items, list):
        return
    for index, item in enumerate(items, start=1):
        prefix = f"{rel_path}: {field} item {index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be object")
            continue
        _require_nonempty_string(item, id_field, prefix, errors)
        _require_nonempty_string(item, text_field, prefix, errors)
        _require_nonempty_list(item, "evidence_refs", prefix, errors)


def _validate_refs(
    value: Any,
    path: str,
    *,
    round_dir: Path | None,
    require_existing_refs: bool,
    errors: list[str],
) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            nested_path = f"{path}.{key}"
            if key == "passage_refs":
                continue
            if key.endswith("_refs") or key == "trace_generated_from":
                if not isinstance(nested, list):
                    errors.append(f"{nested_path} must be list")
                    continue
                for index, ref in enumerate(nested, start=1):
                    ref_must_exist = require_existing_refs and key not in {"report_refs", "expected_future_refs"}
                    _validate_ref(ref, f"{nested_path} item {index}", round_dir, ref_must_exist, errors)
            elif key == "source_materials_path":
                _validate_ref(nested, nested_path, round_dir, require_existing_refs, errors)
            else:
                _validate_refs(
                    nested,
                    nested_path,
                    round_dir=round_dir,
                    require_existing_refs=require_existing_refs,
                    errors=errors,
                )
    elif isinstance(value, list):
        for index, item in enumerate(value, start=1):
            _validate_refs(
                item,
                f"{path} item {index}",
                round_dir=round_dir,
                require_existing_refs=require_existing_refs,
                errors=errors,
            )


def _validate_ref(
    value: Any,
    label: str,
    round_dir: Path | None,
    require_existing_refs: bool,
    errors: list[str],
) -> None:
    if not isinstance(value, str) or not value:
        errors.append(f"{label}: ref must be non-empty str")
        return
    if not is_safe_round_relative_path(value):
        errors.append(f"{label}: ref must be relative inside the round")
        return
    if not _is_allowed_round_ref(value):
        errors.append(f"{label}: ref must be under inputs/, extracted/, notes/, work/, or outputs/")
        return
    if round_dir is not None and require_existing_refs and not (round_dir / value).exists():
        errors.append(f"{label}: referenced file is missing: {value}")


def _is_allowed_round_ref(value: str) -> bool:
    return is_safe_round_relative_path(value) and value.startswith(ALLOWED_REF_PREFIXES)


def _require_nonempty_string(value: dict[str, Any], field: str, prefix: str, errors: list[str]) -> None:
    if not isinstance(value.get(field), str) or not value[field]:
        errors.append(f"{prefix}: {field} must be non-empty str")


def _require_list(value: dict[str, Any], field: str, prefix: str, errors: list[str]) -> Any:
    loaded = value.get(field)
    if not isinstance(loaded, list):
        errors.append(f"{prefix}: {field} must be list")
    return loaded


def _require_nonempty_list(value: dict[str, Any], field: str, prefix: str, errors: list[str]) -> Any:
    loaded = _require_list(value, field, prefix, errors)
    if isinstance(loaded, list) and not loaded:
        errors.append(f"{prefix}: {field} must not be empty")
    return loaded


def _require_bool(value: dict[str, Any], field: str, prefix: str, errors: list[str]) -> None:
    if not isinstance(value.get(field), bool):
        errors.append(f"{prefix}: {field} must be bool")


def _require_enum(value: dict[str, Any], field: str, allowed: set[str], prefix: str, errors: list[str]) -> None:
    loaded = value.get(field)
    if loaded not in allowed:
        choices = ", ".join(sorted(allowed))
        errors.append(f"{prefix}: {field} must be one of {choices}")
