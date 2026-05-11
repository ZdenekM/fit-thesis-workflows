"""Validators for agent- or reviewer-authored structured evidence artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from thesis_review_workflow.artifact_validation import sha256_file, validate_common_artifact_fields
from thesis_review_workflow.paths import is_safe_round_relative_path

ASSIGNMENT_COVERAGE_REL = "work/assignment_coverage_agent.json"
EVIDENCE_REQUIREMENTS_REL = "work/evidence_requirements.json"
QUANTITATIVE_CLAIMS_REL = "work/quantitative_claims.json"
OPPONENT_REPORT_TRACE_REL = "work/opponent_report_trace.json"
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
    OPPONENT_REPORT_TRACE_REL: "opponent-report-trace-v1",
    CURRENT_EVIDENCE_SNAPSHOT_REL: "current-evidence-snapshot-v1",
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
CURRENT_EVIDENCE_ITEM_STATUSES = {"present", "missing", "invalid", "unavailable", "not_applicable"}
CURRENT_EVIDENCE_FRESHNESS_STATUSES = {"current", "stale", "not_checked", "not_applicable"}
CURRENT_EVIDENCE_DEFAULT_SOURCE_REFS = (
    "work/code_workspace.md",
    "work/serena_roots.json",
    "work/code_reproducibility.json",
    "work/review_manifest.json",
    "work/agent_coverage.json",
    "work/quantitative_claims.json",
    "outputs/github_code_intake.md",
    "outputs/feedback_student.md",
    "work/feedback_student_draft.md",
    "outputs/oponent_podklady.md",
    "outputs/oponent_podklady_revidovane.md",
    "work/oponent_podklady_draft.md",
    "work/opponent_report_trace.json",
    "work/oponent_posudek_draft.md",
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
    )


def validate_structured_evidence_payload(
    loaded: dict[str, Any],
    rel_path: str,
    *,
    round_dir: Path | None = None,
    case_id: str | None = None,
    round_id: str | None = None,
    require_existing_refs: bool = True,
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
        _validate_opponent_report_trace(loaded, rel_path, round_dir, case_id, round_id, errors)
    elif rel_path == CURRENT_EVIDENCE_SNAPSHOT_REL:
        _validate_current_evidence_snapshot(loaded, rel_path, round_dir, errors)

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
            if key.endswith("_refs") or key == "trace_generated_from":
                if not isinstance(nested, list):
                    errors.append(f"{nested_path} must be list")
                    continue
                for index, ref in enumerate(nested, start=1):
                    ref_must_exist = require_existing_refs and key != "report_refs"
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
