"""Validators for agent- or reviewer-authored structured evidence artifacts."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from thesis_review_workflow.paths import is_safe_round_relative_path

ASSIGNMENT_COVERAGE_REL = "work/assignment_coverage_agent.json"
EVIDENCE_REQUIREMENTS_REL = "work/evidence_requirements.json"
QUANTITATIVE_CLAIMS_REL = "work/quantitative_claims.json"
OPPONENT_REPORT_TRACE_REL = "work/opponent_report_trace.json"

STRUCTURED_EVIDENCE_SCHEMAS: dict[str, str] = {
    ASSIGNMENT_COVERAGE_REL: "assignment-coverage-agent-v1",
    EVIDENCE_REQUIREMENTS_REL: "evidence-requirements-v1",
    QUANTITATIVE_CLAIMS_REL: "quantitative-claims-v1",
    OPPONENT_REPORT_TRACE_REL: "opponent-report-trace-v1",
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
OPPONENT_TRACE_REVIEW_STATUSES = {"accepted"}
OPPONENT_TRACE_UNCERTAINTY_STATUSES = {"carried_to_report", "accepted_missing", "not_applicable"}
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
        _validate_opponent_report_trace(loaded, rel_path, round_dir, errors)

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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_common_fields(
    loaded: dict[str, Any],
    rel_path: str,
    expected_schema: str,
    case_id: str | None,
    round_id: str | None,
    errors: list[str],
) -> None:
    if loaded.get("schema_version") != expected_schema:
        errors.append(f"{rel_path}: schema_version must be {expected_schema}")
    if case_id is not None and loaded.get("case_id") != case_id:
        errors.append(f"{rel_path}: case_id does not match requested case")
    if round_id is not None and loaded.get("round_id") != round_id:
        errors.append(f"{rel_path}: round_id does not match requested round")
    for field in ("case_id", "round_id", "generated_at", "producer_role"):
        _require_nonempty_string(loaded, field, rel_path, errors)
    _require_list(loaded, "source_refs", rel_path, errors)
    _require_list(loaded, "limitations", rel_path, errors)
    producer_type = loaded.get("producer_type")
    if producer_type not in {"agent", "human"}:
        errors.append(f"{rel_path}: producer_type must be agent or human")
    if "producer_agent" not in loaded:
        errors.append(f"{rel_path}: missing producer_agent")
    elif loaded["producer_agent"] is not None and not isinstance(loaded["producer_agent"], str):
        errors.append(f"{rel_path}: producer_agent must be str or null")
    if producer_type == "agent":
        _require_nonempty_string(loaded, "authorization_note", rel_path, errors)
        _require_nonempty_string(loaded, "producer_agent", rel_path, errors)
    elif producer_type == "human":
        _require_nonempty_string(loaded, "human_reviewer_note", rel_path, errors)


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
        _require_enum(item, "baseline_status", BASELINE_STATUSES, prefix, errors)
        _require_enum(item, "practical_context", PRACTICAL_CONTEXT_STATUSES, prefix, errors)
        if "unit" in item and not isinstance(item["unit"], str):
            errors.append(f"{prefix}: unit must be str")
        _require_list(item, "reproducibility_refs", prefix, errors)
        _require_list(item, "evidence_refs", prefix, errors)
        _require_bool(item, "requires_reviewer_verification", prefix, errors)


def _validate_opponent_report_trace(
    loaded: dict[str, Any],
    rel_path: str,
    round_dir: Path | None,
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
                item_ids.add(item_id)
            _require_enum(item, "item_id", REQUIRED_OPPONENT_IS_ITEM_IDS, prefix, errors)
            _require_nonempty_string(item, "title", prefix, errors)
            _require_nonempty_string(item, "formulation", prefix, errors)
            _require_list(item, "evidence_refs", prefix, errors)
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
            _require_list(item, "source_refs", prefix, errors)
            _require_list(item, "target_section_ids", prefix, errors)
            target_ids = item.get("target_section_ids")
            if isinstance(target_ids, list):
                for target_index, target_id in enumerate(target_ids, start=1):
                    if target_id not in REQUIRED_OPPONENT_IS_ITEM_IDS:
                        errors.append(f"{prefix}: target_section_ids item {target_index} has unknown IS item id")
            _require_list(item, "report_refs", prefix, errors)
            _require_enum(item, "status", OPPONENT_TRACE_UNCERTAINTY_STATUSES, prefix, errors)


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
    items = _require_list(loaded, field, rel_path, errors)
    if not isinstance(items, list):
        return
    for index, item in enumerate(items, start=1):
        prefix = f"{rel_path}: {field} item {index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be object")
            continue
        _require_nonempty_string(item, id_field, prefix, errors)
        _require_nonempty_string(item, text_field, prefix, errors)
        _require_list(item, "evidence_refs", prefix, errors)


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
                    _validate_ref(ref, f"{nested_path} item {index}", round_dir, require_existing_refs, errors)
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


def _require_bool(value: dict[str, Any], field: str, prefix: str, errors: list[str]) -> None:
    if not isinstance(value.get(field), bool):
        errors.append(f"{prefix}: {field} must be bool")


def _require_enum(value: dict[str, Any], field: str, allowed: set[str], prefix: str, errors: list[str]) -> None:
    loaded = value.get(field)
    if loaded not in allowed:
        choices = ", ".join(sorted(allowed))
        errors.append(f"{prefix}: {field} must be one of {choices}")
