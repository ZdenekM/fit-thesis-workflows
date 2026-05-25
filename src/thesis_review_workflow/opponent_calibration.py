"""Structural contracts for private opponent calibration artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from thesis_review_workflow.artifact_validation import sha256_file, validate_common_artifact_fields
from thesis_review_workflow.ids import is_valid_id
from thesis_review_workflow.paths import is_safe_round_relative_path
from thesis_review_workflow.structured_evidence import (
    validate_structured_evidence_artifact,
    validate_structured_evidence_payload,
)

HISTORICAL_CASE_ANALYSIS_SCHEMA = "historical-opponent-case-analysis-v1"
REVIEWER_CALIBRATION_PROFILE_SCHEMA = "opponent-reviewer-calibration-profile-v1"
REVIEWER_CHECKLIST_SCHEMA = "opponent-reviewer-checklist-v1"
REVIEWER_PROFILE_HISTORY_SCHEMA = "opponent-reviewer-calibration-history-v1"
OPPONENT_CALIBRATION_USE_SCHEMA = "opponent-calibration-use-v1"
OPPONENT_CALIBRATION_ADVISORY_SCHEMA = "opponent-calibration-advisory-v1"
OPPONENT_REPORT_REVISION_REQUEST_SCHEMA = "opponent-report-revision-request-v1"
OPPONENT_CALIBRATION_REFRESH_ELIGIBILITY_SCHEMA = "opponent-calibration-refresh-eligibility-v1"

HISTORICAL_CASE_ANALYSIS_PREFIX = "work/calibration/historical_case_analyses/"
REVIEWER_CALIBRATION_PROFILE_REL = "work/calibration/reviewer_calibration_profile.json"
REVIEWER_CHECKLIST_REL = "work/calibration/reviewer_checklist.json"
REVIEWER_PROFILE_HISTORY_REL = "work/calibration/reviewer_calibration_profile_history.jsonl"
REVIEWER_CALIBRATION_PROFILE_MARKDOWN_REL = "outputs/reviewer_calibration_profile.md"
REVIEWER_CALIBRATION_PROFILE_SNAPSHOT_PREFIX = "work/calibration/profile_versions/"
REVIEWER_PROFILE_REVIEW_REL = "work/calibration/profile_review.md"
REVIEWER_PROFILE_CHANGE_LOG_REL = "work/calibration/reviewer_profile_change_log.md"
OPPONENT_CALIBRATION_USE_REL = "work/opponent_calibration_use.json"
OPPONENT_CALIBRATION_ADVISORY_REL = "work/opponent_calibration_advisory.json"
OPPONENT_REPORT_REVISION_REQUEST_REL = "work/opponent_report_revision_request.json"
OPPONENT_CALIBRATION_REFRESH_ELIGIBILITY_REL = "work/opponent_calibration_refresh_eligibility.json"
OPPONENT_OPERATOR_FEEDBACK_REL = "notes/opponent-report-operator-feedback.md"
OPPONENT_MATERIALS_REVIEWED_REL = "outputs/oponent_podklady_revidovane.md"
OPPONENT_REPORT_TRACE_REL = "work/opponent_report_trace.json"
OPPONENT_REPORT_DRAFT_REL = "work/oponent_posudek_draft.md"
OPPONENT_REPORT_REVIEW_REL = "outputs/feedback_k_posudku.md"
OPPONENT_REVISION_SOURCE_TRACE_REL = "work/opponent_report_revision_sources/opponent_report_trace.json"
OPPONENT_REVISION_SOURCE_DRAFT_REL = "work/opponent_report_revision_sources/oponent_posudek_draft.md"
OPPONENT_REFRESH_SOURCE_MANIFEST_REL = "work/opponent_calibration_refresh_sources/review_manifest.json"
REFERENCE_REPORT_COMPARISON_REL = "outputs/reference_report_comparison.md"
OPPONENT_READING_PACKET_REL = "outputs/opponent_reading_packet.md"

EXACT_CALIBRATION_ARTIFACT_SCHEMAS: dict[str, str] = {
    REVIEWER_CALIBRATION_PROFILE_REL: REVIEWER_CALIBRATION_PROFILE_SCHEMA,
    REVIEWER_CHECKLIST_REL: REVIEWER_CHECKLIST_SCHEMA,
    REVIEWER_PROFILE_HISTORY_REL: REVIEWER_PROFILE_HISTORY_SCHEMA,
    OPPONENT_CALIBRATION_USE_REL: OPPONENT_CALIBRATION_USE_SCHEMA,
    OPPONENT_CALIBRATION_ADVISORY_REL: OPPONENT_CALIBRATION_ADVISORY_SCHEMA,
    OPPONENT_REPORT_REVISION_REQUEST_REL: OPPONENT_REPORT_REVISION_REQUEST_SCHEMA,
    OPPONENT_CALIBRATION_REFRESH_ELIGIBILITY_REL: OPPONENT_CALIBRATION_REFRESH_ELIGIBILITY_SCHEMA,
}

ALLOWED_REF_PREFIXES = ("inputs/", "extracted/", "notes/", "work/", "outputs/")
CONFIDENCE_DIMENSIONS = {
    "style",
    "grading",
    "severity",
    "questions",
    "evidence_expectations",
    "checklist_coverage",
}
OWNERSHIP_BOUNDARY_FIELDS = {
    "baseline_workflow_owned",
    "methodology_pipeline_owned",
    "calibration_profile_owned",
    "do_not_duplicate",
}
NONEMPTY_OWNERSHIP_BOUNDARY_FIELDS = {"calibration_profile_owned", "do_not_duplicate"}
CHECKLIST_OWNERSHIP_SCOPES = {"calibration_profile"}
HISTORICAL_CASE_STRENGTHS = {"strong", "typical", "weak", "atypical", "unknown"}
CALIBRATION_APPLICABILITY_STATUSES = {"matching", "partial", "mismatch", "unknown"}
CALIBRATION_ADVISORY_REASONS = {
    "missing_profile",
    "operator_declined",
    "not_applicable",
    "not_approved",
    "stale_profile",
    "insufficient_corpus",
}
REVISION_FEEDBACK_CATEGORIES = {
    "evidence_request",
    "grading_calibration",
    "tone_style",
    "missing_check",
    "factual_correction",
    "wording_preference",
    "defense_question",
    "scope_limitation",
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REVIEWED_STATUSES = {"reviewed", "reviewed_with_notes"}


def calibration_schema_for_rel_path(rel_path: str) -> str | None:
    if rel_path in EXACT_CALIBRATION_ARTIFACT_SCHEMAS:
        return EXACT_CALIBRATION_ARTIFACT_SCHEMAS[rel_path]
    if historical_case_analysis_id(rel_path) is not None:
        return HISTORICAL_CASE_ANALYSIS_SCHEMA
    return None


def historical_case_analysis_id(rel_path: str) -> str | None:
    if not rel_path.startswith(HISTORICAL_CASE_ANALYSIS_PREFIX) or not rel_path.endswith(".json"):
        return None
    suffix = rel_path.removeprefix(HISTORICAL_CASE_ANALYSIS_PREFIX)
    if "/" in suffix:
        return None
    historical_case_id = suffix.removesuffix(".json")
    return historical_case_id if is_valid_id(historical_case_id) else None


def is_opponent_calibration_artifact(rel_path: str) -> bool:
    return calibration_schema_for_rel_path(rel_path) is not None


def calibration_profile_check_targets(round_dir: Path) -> list[str]:
    targets = [
        REVIEWER_CALIBRATION_PROFILE_MARKDOWN_REL,
        REVIEWER_CALIBRATION_PROFILE_REL,
        REVIEWER_CHECKLIST_REL,
        REVIEWER_PROFILE_HISTORY_REL,
        REVIEWER_PROFILE_CHANGE_LOG_REL,
        REVIEWER_PROFILE_REVIEW_REL,
    ]
    analyses_dir = round_dir / HISTORICAL_CASE_ANALYSIS_PREFIX
    if analyses_dir.is_dir():
        targets.extend(path.relative_to(round_dir).as_posix() for path in sorted(analyses_dir.rglob("*.json")))
    snapshots_dir = round_dir / REVIEWER_CALIBRATION_PROFILE_SNAPSHOT_PREFIX
    if snapshots_dir.is_dir():
        targets.extend(path.relative_to(round_dir).as_posix() for path in sorted(snapshots_dir.rglob("*.md")))
    return targets


def validate_opponent_calibration_artifact(
    round_dir: Path,
    rel_path: Path | str,
    *,
    case_id: str | None = None,
    round_id: str | None = None,
    require_existing_refs: bool = True,
    allow_stale_trace_binding: bool = False,
) -> list[str]:
    rel = rel_path.as_posix() if isinstance(rel_path, Path) else rel_path
    path_errors = validate_opponent_calibration_rel_path(rel)
    if path_errors:
        return path_errors
    path = round_dir / rel
    if rel == REVIEWER_PROFILE_HISTORY_REL:
        return validate_profile_history_artifact(
            path,
            rel,
            round_dir,
            case_id=case_id,
            round_id=round_id,
            require_existing_refs=require_existing_refs,
        )
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [f"{rel}: missing opponent calibration artifact"]
    except OSError as exc:
        detail = exc.strerror or exc.__class__.__name__
        return [f"{rel}: cannot read opponent calibration artifact: {detail}"]
    except json.JSONDecodeError as exc:
        return [f"{rel}: invalid JSON: {exc.msg}"]
    if not isinstance(loaded, dict):
        return [f"{rel}: JSON opponent calibration artifact must be an object"]
    return validate_opponent_calibration_payload(
        loaded,
        rel,
        round_dir=round_dir,
        case_id=case_id,
        round_id=round_id,
        require_existing_refs=require_existing_refs,
        allow_stale_trace_binding=allow_stale_trace_binding,
    )


def validate_opponent_calibration_rel_path(rel_path: str) -> list[str]:
    if not is_safe_round_relative_path(rel_path):
        return [f"{rel_path}: opponent calibration path must be relative inside the round"]
    if calibration_schema_for_rel_path(rel_path) is None:
        return [f"{rel_path}: unknown opponent calibration artifact path"]
    return []


def validate_opponent_calibration_payload(
    loaded: dict[str, Any],
    rel_path: str,
    *,
    round_dir: Path | None = None,
    case_id: str | None = None,
    round_id: str | None = None,
    require_existing_refs: bool = True,
    allow_stale_trace_binding: bool = False,
) -> list[str]:
    errors: list[str] = []
    path_errors = validate_opponent_calibration_rel_path(rel_path)
    if path_errors:
        return path_errors
    expected_schema = calibration_schema_for_rel_path(rel_path)
    if expected_schema is None:
        return [f"{rel_path}: unknown opponent calibration artifact path"]

    _validate_common_fields(loaded, rel_path, expected_schema, case_id, round_id, errors)
    if expected_schema == HISTORICAL_CASE_ANALYSIS_SCHEMA:
        _validate_historical_case_analysis(loaded, rel_path, errors)
    elif expected_schema == REVIEWER_CALIBRATION_PROFILE_SCHEMA:
        _validate_profile_manifest(loaded, rel_path, round_dir, require_existing_refs, errors)
    elif expected_schema == REVIEWER_CHECKLIST_SCHEMA:
        _validate_reviewer_checklist(loaded, rel_path, round_dir, require_existing_refs, errors)
    elif expected_schema == OPPONENT_CALIBRATION_USE_SCHEMA:
        _validate_opponent_calibration_use(
            loaded,
            rel_path,
            round_dir,
            case_id=case_id,
            round_id=round_id,
            errors=errors,
            allow_stale_trace_binding=allow_stale_trace_binding,
        )
    elif expected_schema == OPPONENT_CALIBRATION_ADVISORY_SCHEMA:
        _validate_opponent_calibration_advisory(
            loaded,
            rel_path,
            round_dir,
            case_id=case_id,
            round_id=round_id,
            errors=errors,
            allow_stale_trace_binding=allow_stale_trace_binding,
        )
    elif expected_schema == OPPONENT_REPORT_REVISION_REQUEST_SCHEMA:
        _validate_opponent_report_revision_request(
            loaded,
            rel_path,
            round_dir,
            case_id=case_id,
            round_id=round_id,
            errors=errors,
        )
    elif expected_schema == OPPONENT_CALIBRATION_REFRESH_ELIGIBILITY_SCHEMA:
        _validate_opponent_calibration_refresh_eligibility(
            loaded,
            rel_path,
            round_dir,
            case_id=case_id,
            round_id=round_id,
            errors=errors,
        )

    _validate_refs(
        loaded.get("source_refs"),
        f"{rel_path}: source_refs",
        round_dir=round_dir,
        require_existing_refs=require_existing_refs,
        errors=errors,
    )
    return errors


def validate_profile_history_artifact(
    path: Path,
    rel_path: str,
    round_dir: Path,
    *,
    case_id: str | None = None,
    round_id: str | None = None,
    require_existing_refs: bool = True,
) -> list[str]:
    errors: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return [f"{rel_path}: missing opponent calibration artifact"]
    except OSError as exc:
        detail = exc.strerror or exc.__class__.__name__
        return [f"{rel_path}: cannot read opponent calibration artifact: {detail}"]
    if not lines:
        return [f"{rel_path}: profile history must contain at least one JSONL entry"]
    for index, line in enumerate(lines, start=1):
        prefix = f"{rel_path}: line {index}"
        if not line.strip():
            errors.append(f"{prefix}: empty JSONL lines are not allowed")
            continue
        try:
            loaded = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{prefix}: invalid JSON: {exc.msg}")
            continue
        if not isinstance(loaded, dict):
            errors.append(f"{prefix}: JSONL entry must be an object")
            continue
        _validate_common_fields(loaded, prefix, REVIEWER_PROFILE_HISTORY_SCHEMA, case_id, round_id, errors)
        _require_int(loaded, "profile_version", prefix, errors)
        _require_sha_or_null(loaded, "previous_profile_markdown_sha256", prefix, errors)
        _require_sha(loaded, "profile_markdown_sha256", prefix, errors)
        _require_sha(loaded, "profile_manifest_sha256", prefix, errors)
        _require_nonempty_string(loaded, "change_summary", prefix, errors)
        _require_nonempty_string(loaded, "review_status", prefix, errors)
        _require_sha_or_null(loaded, "previous_history_entry_sha256", prefix, errors)
        _require_nonempty_string(loaded, "profile_snapshot_path", prefix, errors)
        snapshot_path = loaded.get("profile_snapshot_path")
        if isinstance(snapshot_path, str):
            _validate_profile_snapshot_path(
                snapshot_path, loaded.get("profile_version"), f"{prefix}: profile_snapshot_path", errors
            )
            _validate_ref(
                snapshot_path,
                f"{prefix}: profile_snapshot_path",
                round_dir=round_dir,
                require_existing_refs=require_existing_refs,
                errors=errors,
            )
        version = loaded.get("profile_version")
        if isinstance(version, int) and not isinstance(version, bool) and version > 1:
            _validate_operator_approval(loaded.get("operator_approval"), f"{prefix}: operator_approval", errors)
        elif "operator_approval" in loaded:
            _validate_operator_approval(loaded.get("operator_approval"), f"{prefix}: operator_approval", errors)
        _validate_refs(
            loaded.get("source_refs"),
            f"{prefix}: source_refs",
            round_dir=round_dir,
            require_existing_refs=require_existing_refs,
            errors=errors,
        )
        source_refs = _require_nonempty_list(loaded, "source_case_refs", prefix, errors)
        _validate_historical_analysis_refs(
            source_refs,
            f"{prefix}: source_case_refs",
            round_dir=round_dir,
            require_existing_refs=require_existing_refs,
            errors=errors,
        )
    return errors


def _validate_historical_analysis_refs(
    values: Any,
    label: str,
    *,
    round_dir: Path | None,
    require_existing_refs: bool,
    errors: list[str],
) -> None:
    if not isinstance(values, list):
        return
    for index, value in enumerate(values, start=1):
        item_label = f"{label} item {index}"
        _validate_ref(
            value,
            item_label,
            round_dir=round_dir,
            require_existing_refs=require_existing_refs,
            errors=errors,
        )
        if isinstance(value, str) and is_safe_round_relative_path(value) and historical_case_analysis_id(value) is None:
            errors.append(f"{item_label}: ref must be a historical case analysis artifact")


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
        required_string_fields=("reviewer_profile_id", "case_id", "round_id", "generated_at", "producer_role"),
    )


def _validate_historical_case_analysis(loaded: dict[str, Any], rel_path: str, errors: list[str]) -> None:
    path_case_id = historical_case_analysis_id(rel_path)
    historical_case_id = loaded.get("historical_case_id")
    if not isinstance(historical_case_id, str) or not historical_case_id:
        errors.append(f"{rel_path}: historical_case_id must be non-empty str")
    elif path_case_id != historical_case_id:
        errors.append(f"{rel_path}: historical_case_id must match the analysis filename")
    for field in ("work_type", "domain"):
        _require_nonempty_string(loaded, field, rel_path, errors)
    for field in (
        "artifact_availability",
        "code_availability",
        "report_shape",
        "judgment_calibration",
        "evidence_habits",
        "corpus_coverage",
    ):
        _require_dict(loaded, field, rel_path, errors)
    strength = loaded.get("case_strength")
    if strength not in HISTORICAL_CASE_STRENGTHS:
        values = ", ".join(sorted(HISTORICAL_CASE_STRENGTHS))
        errors.append(f"{rel_path}: case_strength must be one of: {values}")
    _validate_recurring_checks(loaded.get("recurring_checks"), rel_path, errors)
    source_refs = loaded.get("source_refs")
    if not isinstance(source_refs, list) or not source_refs:
        errors.append(f"{rel_path}: source_refs must not be empty")
    elif isinstance(historical_case_id, str):
        expected_prefix = f"inputs/historical_cases/{historical_case_id}/"
        mismatched = [
            ref
            for ref in source_refs
            if isinstance(ref, str)
            and ref.startswith("inputs/historical_cases/")
            and not ref.startswith(expected_prefix)
        ]
        if mismatched:
            errors.append(f"{rel_path}: source_refs must not point to a different historical case id")
        if not any(isinstance(ref, str) and ref.startswith(expected_prefix) for ref in source_refs):
            errors.append(f"{rel_path}: source_refs must include at least one ref under {expected_prefix}")


def _validate_profile_manifest(
    loaded: dict[str, Any],
    rel_path: str,
    round_dir: Path | None,
    require_existing_refs: bool,
    errors: list[str],
) -> None:
    _require_nonempty_string(loaded, "profile_markdown_path", rel_path, errors)
    _require_sha(loaded, "profile_markdown_sha256", rel_path, errors)
    _require_dict(loaded, "profile_applicability", rel_path, errors)
    _require_nonempty_list(loaded, "source_case_refs", rel_path, errors)
    _require_int(loaded, "profile_version", rel_path, errors)
    _require_sha_or_null(loaded, "profile_previous_sha256", rel_path, errors)
    _require_nonempty_string(loaded, "profile_change_summary", rel_path, errors)
    if "operator_approval" in loaded:
        _validate_operator_approval(loaded.get("operator_approval"), f"{rel_path}: operator_approval", errors)
    _validate_confidence_by_dimension(loaded.get("confidence_by_dimension"), rel_path, errors)
    _validate_ownership_boundaries(loaded.get("ownership_boundaries"), rel_path, errors)
    _require_list(loaded, "do_not_use_for", rel_path, errors)
    markdown_path = loaded.get("profile_markdown_path")
    if isinstance(markdown_path, str):
        if markdown_path != REVIEWER_CALIBRATION_PROFILE_MARKDOWN_REL:
            errors.append(f"{rel_path}: profile_markdown_path must be {REVIEWER_CALIBRATION_PROFILE_MARKDOWN_REL}")
        _validate_ref(
            markdown_path,
            f"{rel_path}: profile_markdown_path",
            round_dir=round_dir,
            require_existing_refs=True,
            errors=errors,
        )
        recorded_hash = loaded.get("profile_markdown_sha256")
        if round_dir is not None and isinstance(recorded_hash, str) and SHA256_RE.fullmatch(recorded_hash):
            path = round_dir / markdown_path
            if path.is_file() and sha256_file(path) != recorded_hash:
                errors.append(f"{rel_path}: profile_markdown_sha256 is stale")
    source_case_refs = loaded.get("source_case_refs")
    _validate_historical_analysis_refs(
        source_case_refs,
        f"{rel_path}: source_case_refs",
        round_dir=round_dir,
        require_existing_refs=require_existing_refs,
        errors=errors,
    )


def _validate_reviewer_checklist(
    loaded: dict[str, Any],
    rel_path: str,
    round_dir: Path | None,
    require_existing_refs: bool,
    errors: list[str],
) -> None:
    items = _require_nonempty_list(loaded, "checklist_items", rel_path, errors)
    if not isinstance(items, list):
        return
    seen_item_ids: set[str] = set()
    for index, item in enumerate(items, start=1):
        prefix = f"{rel_path}: checklist_items item {index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be object")
            continue
        _validate_id_field(item, "item_id", prefix, errors)
        for field in ("evidence_class", "prompt"):
            _require_nonempty_string(item, field, prefix, errors)
        item_id = item.get("item_id")
        if isinstance(item_id, str) and item_id:
            if item_id in seen_item_ids:
                errors.append(f"{prefix}: item_id must be unique")
            seen_item_ids.add(item_id)
        _require_enum(item, "ownership_scope", CHECKLIST_OWNERSHIP_SCOPES, prefix, errors)
        source_case_refs = _require_nonempty_list(item, "source_case_refs", prefix, errors)
        _validate_historical_analysis_refs(
            source_case_refs,
            f"{prefix}: source_case_refs",
            round_dir=round_dir,
            require_existing_refs=require_existing_refs,
            errors=errors,
        )
        _require_bool(item, "requires_current_case_evidence", prefix, errors)


def _validate_recurring_checks(value: Any, rel_path: str, errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append(f"{rel_path}: recurring_checks must be list")
        return
    seen_check_ids: set[str] = set()
    for index, item in enumerate(value, start=1):
        prefix = f"{rel_path}: recurring_checks item {index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be object")
            continue
        _validate_id_field(item, "check_id", prefix, errors)
        for field in ("evidence_class", "prompt"):
            _require_nonempty_string(item, field, prefix, errors)
        check_id = item.get("check_id")
        if isinstance(check_id, str) and check_id:
            if check_id in seen_check_ids:
                errors.append(f"{prefix}: check_id must be unique")
            seen_check_ids.add(check_id)


def _validate_ownership_boundaries(value: Any, rel_path: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{rel_path}: ownership_boundaries must be object")
        return
    unknown_fields = sorted(set(value) - OWNERSHIP_BOUNDARY_FIELDS)
    if unknown_fields:
        errors.append(
            f"{rel_path}: ownership_boundaries contains unknown field(s): {', '.join(unknown_fields)}"
        )
    for field in sorted(OWNERSHIP_BOUNDARY_FIELDS):
        items = _require_list(value, field, f"{rel_path}: ownership_boundaries", errors)
        if not isinstance(items, list):
            continue
        if field in NONEMPTY_OWNERSHIP_BOUNDARY_FIELDS and not items:
            errors.append(f"{rel_path}: ownership_boundaries: {field} must not be empty")
        for index, item in enumerate(items, start=1):
            if not isinstance(item, str) or not item:
                errors.append(f"{rel_path}: ownership_boundaries {field} item {index} must be non-empty str")


def _validate_opponent_calibration_use(
    loaded: dict[str, Any],
    rel_path: str,
    round_dir: Path | None,
    *,
    case_id: str | None,
    round_id: str | None,
    errors: list[str],
    allow_stale_trace_binding: bool = False,
) -> None:
    _validate_hash_binding(
        loaded,
        rel_path,
        "source_materials_path",
        "source_materials_sha256",
        OPPONENT_MATERIALS_REVIEWED_REL,
        round_dir,
        errors,
    )
    if not allow_stale_trace_binding:
        _validate_current_case_trace(OPPONENT_REPORT_TRACE_REL, round_dir, case_id, round_id, errors)
    _validate_hash_binding(
        loaded,
        rel_path,
        "opponent_report_trace_path",
        "opponent_report_trace_sha256",
        OPPONENT_REPORT_TRACE_REL,
        round_dir,
        errors,
        check_current=not allow_stale_trace_binding,
    )
    _validate_bound_calibration_artifact(REVIEWER_CALIBRATION_PROFILE_REL, round_dir, case_id, round_id, errors)
    _validate_hash_binding(
        loaded,
        rel_path,
        "profile_manifest_path",
        "profile_manifest_sha256",
        REVIEWER_CALIBRATION_PROFILE_REL,
        round_dir,
        errors,
    )
    _validate_hash_binding(
        loaded,
        rel_path,
        "checklist_path",
        "checklist_sha256",
        REVIEWER_CHECKLIST_REL,
        round_dir,
        errors,
    )
    _validate_bound_calibration_artifact(REVIEWER_CHECKLIST_REL, round_dir, case_id, round_id, errors)
    _require_int(loaded, "selected_profile_version", rel_path, errors)
    _validate_selected_profile_version(loaded, rel_path, round_dir, errors)
    _require_nonempty_string(loaded, "calibration_scope", rel_path, errors)
    _validate_applicability_dimensions(loaded.get("applicability_dimensions"), rel_path, errors)
    _validate_confidence_by_dimension(loaded.get("confidence_by_dimension"), rel_path, errors)
    _require_nonempty_list(loaded, "limitations", rel_path, errors)
    _validate_reviewer_profile_gate(loaded.get("reviewer_profile_gate"), rel_path, errors)
    _validate_current_case_approval(loaded.get("operator_approval"), rel_path, loaded, errors)


def _validate_opponent_calibration_advisory(
    loaded: dict[str, Any],
    rel_path: str,
    round_dir: Path | None,
    *,
    case_id: str | None,
    round_id: str | None,
    errors: list[str],
    allow_stale_trace_binding: bool = False,
) -> None:
    _validate_hash_binding(
        loaded,
        rel_path,
        "source_materials_path",
        "source_materials_sha256",
        OPPONENT_MATERIALS_REVIEWED_REL,
        round_dir,
        errors,
    )
    _validate_hash_binding(
        loaded,
        rel_path,
        "opponent_report_trace_path",
        "opponent_report_trace_sha256",
        OPPONENT_REPORT_TRACE_REL,
        round_dir,
        errors,
        check_current=not allow_stale_trace_binding,
    )
    if not allow_stale_trace_binding:
        _validate_current_case_trace(OPPONENT_REPORT_TRACE_REL, round_dir, case_id, round_id, errors)
    _require_enum(loaded, "no_profile_reason", CALIBRATION_ADVISORY_REASONS, rel_path, errors)
    if loaded.get("advisory_status") != "non_blocking":
        errors.append(f"{rel_path}: advisory_status must be non_blocking")
    if loaded.get("normal_workflow_continues") is not True:
        errors.append(f"{rel_path}: normal_workflow_continues must be true")
    _require_nonempty_string(loaded, "recommendation", rel_path, errors)
    _require_nonempty_list(loaded, "limitations", rel_path, errors)
    _validate_reviewer_profile_gate(loaded.get("reviewer_profile_gate"), rel_path, errors)


def _validate_opponent_report_revision_request(
    loaded: dict[str, Any],
    rel_path: str,
    round_dir: Path | None,
    *,
    case_id: str | None,
    round_id: str | None,
    errors: list[str],
) -> None:
    _validate_hash_binding(
        loaded,
        rel_path,
        "operator_feedback_path",
        "operator_feedback_sha256",
        OPPONENT_OPERATOR_FEEDBACK_REL,
        round_dir,
        errors,
    )
    _validate_hash_binding(
        loaded,
        rel_path,
        "source_materials_path",
        "source_materials_sha256",
        OPPONENT_MATERIALS_REVIEWED_REL,
        round_dir,
        errors,
    )
    _validate_hash_binding(
        loaded,
        rel_path,
        "opponent_report_trace_path",
        "opponent_report_trace_sha256",
        OPPONENT_REVISION_SOURCE_TRACE_REL,
        round_dir,
        errors,
    )
    _validate_trace_snapshot(
        loaded,
        rel_path,
        "opponent_report_trace_path",
        round_dir,
        case_id,
        round_id,
        errors,
    )
    _validate_hash_binding(
        loaded,
        rel_path,
        "opponent_report_draft_path",
        "opponent_report_draft_sha256",
        OPPONENT_REVISION_SOURCE_DRAFT_REL,
        round_dir,
        errors,
    )
    _validate_revision_calibration_context(loaded, rel_path, round_dir, case_id, round_id, errors)
    _validate_hash_binding(
        loaded,
        rel_path,
        "reference_report_comparison_path",
        "reference_report_comparison_sha256",
        REFERENCE_REPORT_COMPARISON_REL,
        round_dir,
        errors,
    )
    _validate_hash_binding(
        loaded,
        rel_path,
        "opponent_reading_packet_path",
        "opponent_reading_packet_sha256",
        OPPONENT_READING_PACKET_REL,
        round_dir,
        errors,
    )
    _validate_revision_feedback_items(loaded.get("feedback_items"), rel_path, "feedback_items", errors)
    _validate_revision_extra_checks(loaded.get("requested_extra_checks"), rel_path, errors)
    expected_refs = [
        OPPONENT_OPERATOR_FEEDBACK_REL,
        OPPONENT_MATERIALS_REVIEWED_REL,
        OPPONENT_REVISION_SOURCE_TRACE_REL,
        OPPONENT_REVISION_SOURCE_DRAFT_REL,
        REFERENCE_REPORT_COMPARISON_REL,
        OPPONENT_READING_PACKET_REL,
    ]
    calibration_ref = loaded.get("calibration_use_path") or loaded.get("calibration_advisory_path")
    if isinstance(calibration_ref, str):
        expected_refs.append(calibration_ref)
    _validate_source_refs_include(loaded, rel_path, expected_refs, errors)


def _validate_opponent_calibration_refresh_eligibility(
    loaded: dict[str, Any],
    rel_path: str,
    round_dir: Path | None,
    *,
    case_id: str | None,
    round_id: str | None,
    errors: list[str],
) -> None:
    _validate_hash_binding(
        loaded,
        rel_path,
        "source_materials_path",
        "source_materials_sha256",
        OPPONENT_MATERIALS_REVIEWED_REL,
        round_dir,
        errors,
    )
    _validate_hash_binding(
        loaded,
        rel_path,
        "opponent_report_trace_path",
        "opponent_report_trace_sha256",
        OPPONENT_REPORT_TRACE_REL,
        round_dir,
        errors,
    )
    _validate_current_case_trace(OPPONENT_REPORT_TRACE_REL, round_dir, case_id, round_id, errors)
    _validate_hash_binding(
        loaded,
        rel_path,
        "final_report_draft_path",
        "final_report_draft_sha256",
        OPPONENT_REPORT_DRAFT_REL,
        round_dir,
        errors,
    )
    _validate_hash_binding(
        loaded,
        rel_path,
        "final_report_review_path",
        "final_report_review_sha256",
        OPPONENT_REPORT_REVIEW_REL,
        round_dir,
        errors,
    )
    _validate_hash_binding(
        loaded,
        rel_path,
        "review_manifest_snapshot_path",
        "review_manifest_snapshot_sha256",
        OPPONENT_REFRESH_SOURCE_MANIFEST_REL,
        round_dir,
        errors,
    )
    _validate_refresh_manifest_snapshot(loaded, rel_path, round_dir, case_id, round_id, errors)
    if loaded.get("eligibility_status") != "operator_approved_for_calibration_refresh":
        errors.append(f"{rel_path}: eligibility_status must be operator_approved_for_calibration_refresh")
    if loaded.get("finalization_status") != "human_finalized_after_independent_report_review":
        errors.append(f"{rel_path}: finalization_status must be human_finalized_after_independent_report_review")
    if loaded.get("profile_update_status") != "not_started":
        errors.append(f"{rel_path}: profile_update_status must be not_started")
    if loaded.get("does_not_update_profile") is not True:
        errors.append(f"{rel_path}: does_not_update_profile must be true")
    _validate_refresh_copy_policy(loaded.get("copy_policy"), rel_path, errors)
    case_local_refs = _require_nonempty_list(loaded, "case_local_source_refs", rel_path, errors)
    _validate_refs(
        case_local_refs,
        f"{rel_path}: case_local_source_refs",
        round_dir=round_dir,
        require_existing_refs=True,
        errors=errors,
    )
    expected_refs = [
        OPPONENT_MATERIALS_REVIEWED_REL,
        OPPONENT_REPORT_TRACE_REL,
        OPPONENT_REPORT_DRAFT_REL,
        OPPONENT_REPORT_REVIEW_REL,
        OPPONENT_REFRESH_SOURCE_MANIFEST_REL,
    ]
    _validate_source_refs_include(loaded, rel_path, expected_refs, errors)
    if isinstance(case_local_refs, list):
        for expected_ref in expected_refs:
            if expected_ref not in case_local_refs:
                errors.append(f"{rel_path}: case_local_source_refs must include {expected_ref}")
    _validate_refresh_eligibility_approval(loaded.get("operator_approval"), rel_path, loaded, errors)


def _validate_refresh_copy_policy(value: Any, rel_path: str, errors: list[str]) -> None:
    label = f"{rel_path}: copy_policy"
    if not isinstance(value, dict):
        errors.append(f"{label} must be object")
        return
    if value.get("copy_scope") != "private_case_local_refs_only":
        errors.append(f"{label}: copy_scope must be private_case_local_refs_only")
    if value.get("target_workspace") != "ignored_calibration_case_workspace":
        errors.append(f"{label}: target_workspace must be ignored_calibration_case_workspace")
    if value.get("auto_copy_performed") is not False:
        errors.append(f"{label}: auto_copy_performed must be false")
    if value.get("profile_auto_update") is not False:
        errors.append(f"{label}: profile_auto_update must be false")
    if value.get("requires_explicit_profile_refresh_approval") is not True:
        errors.append(f"{label}: requires_explicit_profile_refresh_approval must be true")


def _validate_refresh_manifest_snapshot(
    loaded: dict[str, Any],
    rel_path: str,
    round_dir: Path | None,
    case_id: str | None,
    round_id: str | None,
    errors: list[str],
) -> None:
    if round_dir is None:
        return
    manifest = _load_json_object(
        round_dir / OPPONENT_REFRESH_SOURCE_MANIFEST_REL, OPPONENT_REFRESH_SOURCE_MANIFEST_REL, errors
    )
    if manifest is None:
        return
    label = f"{rel_path}: review_manifest_snapshot"
    if manifest.get("schema_version") != "review-manifest-v1":
        errors.append(f"{label}: schema_version must be review-manifest-v1")
    if case_id is not None and manifest.get("case_id") != case_id:
        errors.append(f"{label}: case_id does not match requested case")
    if round_id is not None and manifest.get("round_id") != round_id:
        errors.append(f"{label}: round_id does not match requested round")
    if _manifest_record_by_path(
        manifest.get("supporting_work_artifacts"), OPPONENT_CALIBRATION_REFRESH_ELIGIBILITY_REL
    ):
        errors.append(
            f"{label}: snapshot must be captured before {OPPONENT_CALIBRATION_REFRESH_ELIGIBILITY_REL} is collected"
        )

    _validate_manifest_work_artifact(
        manifest,
        OPPONENT_REPORT_TRACE_REL,
        loaded.get("opponent_report_trace_sha256"),
        label,
        errors,
    )
    _validate_manifest_work_artifact(
        manifest,
        OPPONENT_REPORT_DRAFT_REL,
        loaded.get("final_report_draft_sha256"),
        label,
        errors,
    )
    _validate_manifest_output_artifact(
        manifest,
        OPPONENT_MATERIALS_REVIEWED_REL,
        loaded.get("source_materials_sha256"),
        label,
        errors,
    )
    _validate_manifest_output_artifact(
        manifest,
        OPPONENT_REPORT_REVIEW_REL,
        loaded.get("final_report_review_sha256"),
        label,
        errors,
        review_basis_path=OPPONENT_REPORT_DRAFT_REL,
        review_basis_sha256=loaded.get("final_report_draft_sha256"),
    )
    _validate_manifest_helper_check(
        manifest,
        "check-opponent-materials",
        {OPPONENT_MATERIALS_REVIEWED_REL: loaded.get("source_materials_sha256")},
        label,
        errors,
    )
    _validate_manifest_helper_check(
        manifest,
        "check-opponent-report:canonical",
        {
            OPPONENT_MATERIALS_REVIEWED_REL: loaded.get("source_materials_sha256"),
            OPPONENT_REPORT_TRACE_REL: loaded.get("opponent_report_trace_sha256"),
            OPPONENT_REPORT_DRAFT_REL: loaded.get("final_report_draft_sha256"),
        },
        label,
        errors,
    )


def _validate_manifest_work_artifact(
    manifest: dict[str, Any],
    expected_path: str,
    expected_hash: Any,
    label: str,
    errors: list[str],
) -> None:
    record = _manifest_record_by_path(manifest.get("supporting_work_artifacts"), expected_path)
    if record is None:
        errors.append(f"{label}: supporting_work_artifacts must include {expected_path}")
        return
    if record.get("artifact_sha256") != expected_hash:
        errors.append(f"{label}: supporting_work_artifacts hash is stale for {expected_path}")


def _validate_manifest_output_artifact(
    manifest: dict[str, Any],
    expected_path: str,
    expected_hash: Any,
    label: str,
    errors: list[str],
    *,
    review_basis_path: str | None = None,
    review_basis_sha256: Any = None,
) -> None:
    record = _manifest_record_by_path(manifest.get("artifacts"), expected_path)
    if record is None:
        errors.append(f"{label}: artifacts must include {expected_path}")
        return
    if record.get("artifact_sha256") != expected_hash:
        errors.append(f"{label}: artifact hash is stale for {expected_path}")
    review = record.get("independent_review")
    review_label = f"{label}: {expected_path} independent_review"
    if not isinstance(review, dict):
        errors.append(f"{review_label} must be object")
        return
    if review.get("status") not in REVIEWED_STATUSES:
        errors.append(f"{review_label}.status must be reviewed or reviewed_with_notes")
    if review.get("reviewed_hash") != record.get("artifact_sha256"):
        errors.append(f"{review_label}.reviewed_hash is stale")
    for field in ("reviewer_role", "reviewer_agent", "reviewed_at"):
        _require_nonempty_string(review, field, review_label, errors)
    if review_basis_path is not None:
        if review.get("review_basis_path") != review_basis_path:
            errors.append(f"{review_label}.review_basis_path must be {review_basis_path}")
        if review.get("review_basis_sha256") != review_basis_sha256:
            errors.append(f"{review_label}.review_basis_sha256 is stale")


def _validate_manifest_helper_check(
    manifest: dict[str, Any],
    expected_check: str,
    expected_target_hashes: dict[str, Any],
    label: str,
    errors: list[str],
) -> None:
    record = _manifest_record_by_check(manifest.get("helper_checks"), expected_check)
    check_label = f"{label}: helper_checks {expected_check}"
    if record is None:
        errors.append(f"{label}: helper_checks must include {expected_check}")
        return
    if record.get("status") != "passed":
        errors.append(f"{check_label}: status must be passed")
    if record.get("exit_code") != 0:
        errors.append(f"{check_label}: exit_code must be 0")
    if not str(record.get("checked_at", "")).strip():
        errors.append(f"{check_label}: checked_at must be recorded")
    targets = record.get("target_artifacts")
    target_set = {target for target in targets if isinstance(target, str)} if isinstance(targets, list) else set()
    target_hashes = record.get("target_sha256")
    if not isinstance(target_hashes, dict):
        errors.append(f"{check_label}: target_sha256 must be object")
        target_hashes = {}
    for target, expected_hash in expected_target_hashes.items():
        if target not in target_set:
            errors.append(f"{check_label}: target_artifacts must include {target}")
        if target_hashes.get(target) != expected_hash:
            errors.append(f"{check_label}: target hash is stale for {target}")


def _manifest_record_by_path(records: Any, path: str) -> dict[str, Any] | None:
    if not isinstance(records, list):
        return None
    for record in records:
        if isinstance(record, dict) and record.get("path") == path:
            return record
    return None


def _manifest_record_by_check(records: Any, check: str) -> dict[str, Any] | None:
    if not isinstance(records, list):
        return None
    for record in records:
        if isinstance(record, dict) and record.get("check") == check:
            return record
    return None


def _validate_refresh_eligibility_approval(
    value: Any,
    rel_path: str,
    loaded: dict[str, Any],
    errors: list[str],
) -> None:
    label = f"{rel_path}: operator_approval"
    if not isinstance(value, dict):
        errors.append(f"{label} must be object")
        return
    if value.get("approved") is not True:
        errors.append(f"{label}: approved must be true")
    if value.get("approval_kind") != "calibration_refresh_eligibility":
        errors.append(f"{label}: approval_kind must be calibration_refresh_eligibility")
    expected_hashes = {
        "approved_source_materials_sha256": "source_materials_sha256",
        "approved_trace_sha256": "opponent_report_trace_sha256",
        "approved_final_report_draft_sha256": "final_report_draft_sha256",
        "approved_final_report_review_sha256": "final_report_review_sha256",
        "approved_review_manifest_snapshot_sha256": "review_manifest_snapshot_sha256",
    }
    for approval_field, payload_field in expected_hashes.items():
        if value.get(approval_field) != loaded.get(payload_field):
            errors.append(f"{label}: {approval_field} is stale")
    for field in ("approved_by", "approved_at", "approval_scope"):
        _require_nonempty_string(value, field, label, errors)


def _validate_revision_calibration_context(
    loaded: dict[str, Any],
    rel_path: str,
    round_dir: Path | None,
    case_id: str | None,
    round_id: str | None,
    errors: list[str],
) -> None:
    use_present = "calibration_use_path" in loaded or "calibration_use_sha256" in loaded
    advisory_present = "calibration_advisory_path" in loaded or "calibration_advisory_sha256" in loaded
    if use_present == advisory_present:
        errors.append(f"{rel_path}: exactly one of calibration_use or calibration_advisory binding is required")
        return
    if use_present:
        _validate_hash_binding(
            loaded,
            rel_path,
            "calibration_use_path",
            "calibration_use_sha256",
            OPPONENT_CALIBRATION_USE_REL,
            round_dir,
            errors,
        )
        _validate_bound_calibration_artifact(
            OPPONENT_CALIBRATION_USE_REL,
            round_dir,
            case_id,
            round_id,
            errors,
            allow_stale_trace_binding=True,
        )
    else:
        _validate_hash_binding(
            loaded,
            rel_path,
            "calibration_advisory_path",
            "calibration_advisory_sha256",
            OPPONENT_CALIBRATION_ADVISORY_REL,
            round_dir,
            errors,
        )
        _validate_bound_calibration_artifact(
            OPPONENT_CALIBRATION_ADVISORY_REL,
            round_dir,
            case_id,
            round_id,
            errors,
            allow_stale_trace_binding=True,
        )


def _validate_trace_snapshot(
    loaded: dict[str, Any],
    rel_path: str,
    path_field: str,
    round_dir: Path | None,
    case_id: str | None,
    round_id: str | None,
    errors: list[str],
) -> None:
    if round_dir is None:
        return
    path_value = loaded.get(path_field)
    if not isinstance(path_value, str):
        return
    snapshot_path = round_dir / path_value
    if not snapshot_path.is_file():
        return
    snapshot = _load_json_object(snapshot_path, path_value, errors)
    if snapshot is None:
        return
    snapshot_without_context = dict(snapshot)
    snapshot_without_context.pop("calibration_context", None)
    errors.extend(
        validate_structured_evidence_payload(
            snapshot_without_context,
            OPPONENT_REPORT_TRACE_REL,
            round_dir=round_dir,
            case_id=case_id,
            round_id=round_id,
            require_report_calibration=False,
        )
    )


def _validate_revision_feedback_items(
    value: Any,
    rel_path: str,
    field: str,
    errors: list[str],
) -> None:
    items = _require_nonempty_list({field: value}, field, rel_path, errors)
    if not isinstance(items, list):
        return
    seen: set[str] = set()
    for index, item in enumerate(items, start=1):
        prefix = f"{rel_path}: {field} item {index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be object")
            continue
        item_id = item.get("item_id")
        if not isinstance(item_id, str) or not item_id:
            errors.append(f"{prefix}: item_id must be non-empty str")
        elif item_id in seen:
            errors.append(f"{prefix}: duplicate item_id {item_id}")
        else:
            seen.add(item_id)
        _require_enum(item, "category", REVISION_FEEDBACK_CATEGORIES, prefix, errors)
        _require_nonempty_string(item, "summary", prefix, errors)
        _require_nonempty_string(item, "requested_action", prefix, errors)
        evidence_refs = _require_nonempty_list(item, "evidence_refs", prefix, errors)
        _validate_refs(
            evidence_refs,
            f"{prefix}: evidence_refs",
            round_dir=None,
            require_existing_refs=False,
            errors=errors,
        )


def _validate_revision_extra_checks(value: Any, rel_path: str, errors: list[str]) -> None:
    checks = _require_list({"requested_extra_checks": value}, "requested_extra_checks", rel_path, errors)
    if not isinstance(checks, list):
        return
    seen: set[str] = set()
    for index, item in enumerate(checks, start=1):
        prefix = f"{rel_path}: requested_extra_checks item {index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be object")
            continue
        check_id = item.get("check_id")
        if not isinstance(check_id, str) or not check_id:
            errors.append(f"{prefix}: check_id must be non-empty str")
        elif check_id in seen:
            errors.append(f"{prefix}: duplicate check_id {check_id}")
        else:
            seen.add(check_id)
        _require_enum(item, "category", REVISION_FEEDBACK_CATEGORIES, prefix, errors)
        _require_nonempty_string(item, "instruction", prefix, errors)
        evidence_refs = _require_list(item, "evidence_refs", prefix, errors)
        _validate_refs(
            evidence_refs,
            f"{prefix}: evidence_refs",
            round_dir=None,
            require_existing_refs=False,
            errors=errors,
        )


def _validate_source_refs_include(
    loaded: dict[str, Any],
    rel_path: str,
    expected_refs: list[str],
    errors: list[str],
) -> None:
    source_refs = loaded.get("source_refs")
    if not isinstance(source_refs, list):
        return
    for expected_ref in expected_refs:
        if expected_ref not in source_refs:
            errors.append(f"{rel_path}: source_refs must include {expected_ref}")


def _validate_confidence_by_dimension(value: Any, rel_path: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{rel_path}: confidence_by_dimension must be object")
        return
    missing = sorted(CONFIDENCE_DIMENSIONS.difference(value))
    if missing:
        errors.append(f"{rel_path}: confidence_by_dimension missing: {', '.join(missing)}")
    for key, item in value.items():
        if not isinstance(key, str):
            errors.append(f"{rel_path}: confidence_by_dimension keys must be strings")
            continue
        if not isinstance(item, dict):
            errors.append(f"{rel_path}: confidence_by_dimension.{key} must be object")
            continue
        _require_nonempty_string(item, "level", f"{rel_path}: confidence_by_dimension.{key}", errors)
        _require_nonempty_string(item, "rationale", f"{rel_path}: confidence_by_dimension.{key}", errors)


def _validate_hash_binding(
    loaded: dict[str, Any],
    rel_path: str,
    path_field: str,
    hash_field: str,
    expected_path: str,
    round_dir: Path | None,
    errors: list[str],
    *,
    check_current: bool = True,
) -> None:
    path_value = loaded.get(path_field)
    if path_value != expected_path:
        errors.append(f"{rel_path}: {path_field} must be {expected_path}")
    if isinstance(path_value, str):
        _validate_ref(
            path_value,
            f"{rel_path}: {path_field}",
            round_dir=round_dir,
            require_existing_refs=True,
            errors=errors,
        )
    hash_value = loaded.get(hash_field)
    if not isinstance(hash_value, str) or not SHA256_RE.fullmatch(hash_value):
        errors.append(f"{rel_path}: {hash_field} must be a 64-character hex string")
    elif check_current and round_dir is not None and isinstance(path_value, str):
        path = round_dir / path_value
        if path.is_file() and sha256_file(path) != hash_value:
            errors.append(f"{rel_path}: {hash_field} is stale")


def validate_round_hash_binding(
    loaded: dict[str, Any],
    rel_path: str,
    *,
    path_field: str,
    hash_field: str,
    expected_path: str,
    round_dir: Path | None,
    check_current: bool = True,
) -> list[str]:
    """Validate a path/SHA binding from another structured artifact."""

    errors: list[str] = []
    _validate_hash_binding(
        loaded,
        rel_path,
        path_field,
        hash_field,
        expected_path,
        round_dir,
        errors,
        check_current=check_current,
    )
    return errors


def _validate_current_case_trace(
    rel_path: str,
    round_dir: Path | None,
    case_id: str | None,
    round_id: str | None,
    errors: list[str],
) -> None:
    if round_dir is None:
        return
    errors.extend(
        validate_structured_evidence_artifact(
            round_dir,
            rel_path,
            case_id=case_id,
            round_id=round_id,
            require_report_calibration=False,
        )
    )


def _validate_bound_calibration_artifact(
    rel_path: str,
    round_dir: Path | None,
    case_id: str | None,
    round_id: str | None,
    errors: list[str],
    *,
    allow_stale_trace_binding: bool = False,
) -> None:
    if round_dir is None:
        return
    errors.extend(
        validate_opponent_calibration_artifact(
            round_dir,
            rel_path,
            case_id=case_id,
            round_id=round_id,
            allow_stale_trace_binding=allow_stale_trace_binding,
        )
    )


def _validate_selected_profile_version(
    loaded: dict[str, Any],
    rel_path: str,
    round_dir: Path | None,
    errors: list[str],
) -> None:
    if round_dir is None:
        return
    selected_version = loaded.get("selected_profile_version")
    if not isinstance(selected_version, int) or isinstance(selected_version, bool):
        return
    profile = _load_json_object(round_dir / REVIEWER_CALIBRATION_PROFILE_REL, REVIEWER_CALIBRATION_PROFILE_REL, errors)
    if profile is None:
        return
    profile_version = profile.get("profile_version")
    if (
        isinstance(profile_version, int)
        and not isinstance(profile_version, bool)
        and selected_version != profile_version
    ):
        errors.append(f"{rel_path}: selected_profile_version must match profile_manifest profile_version")


def _load_json_object(path: Path, rel_path: str, errors: list[str]) -> dict[str, Any] | None:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"{rel_path}: missing opponent calibration artifact")
        return None
    except OSError as exc:
        detail = exc.strerror or exc.__class__.__name__
        errors.append(f"{rel_path}: cannot read opponent calibration artifact: {detail}")
        return None
    except json.JSONDecodeError as exc:
        errors.append(f"{rel_path}: invalid JSON: {exc.msg}")
        return None
    if not isinstance(loaded, dict):
        errors.append(f"{rel_path}: JSON opponent calibration artifact must be an object")
        return None
    return loaded


def _validate_applicability_dimensions(value: Any, rel_path: str, errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append(f"{rel_path}: applicability_dimensions must be list")
        return
    if not value:
        errors.append(f"{rel_path}: applicability_dimensions must not be empty")
        return
    items = value
    if not isinstance(items, list):
        return
    seen: set[str] = set()
    for index, item in enumerate(items, start=1):
        prefix = f"{rel_path}: applicability_dimensions item {index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be object")
            continue
        dimension = item.get("dimension")
        if not isinstance(dimension, str) or not dimension:
            errors.append(f"{prefix}: dimension must be non-empty str")
        elif dimension in seen:
            errors.append(f"{prefix}: duplicate dimension {dimension}")
        else:
            seen.add(dimension)
        _require_enum(item, "status", CALIBRATION_APPLICABILITY_STATUSES, prefix, errors)
        _require_nonempty_string(item, "rationale", prefix, errors)


def _validate_reviewer_profile_gate(value: Any, rel_path: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{rel_path}: reviewer_profile_gate must be object")
        return
    if value.get("required") is not True:
        errors.append(f"{rel_path}: reviewer_profile_gate.required must be true")
    if value.get("satisfied_by_historical_calibration") is not False:
        errors.append(f"{rel_path}: reviewer_profile_gate.satisfied_by_historical_calibration must be false")


def _validate_current_case_approval(
    value: Any,
    rel_path: str,
    loaded: dict[str, Any],
    errors: list[str],
) -> None:
    if not isinstance(value, dict):
        errors.append(f"{rel_path}: operator_approval must be object")
        return
    if value.get("approved") is not True:
        errors.append(f"{rel_path}: operator_approval.approved must be true")
    if value.get("approval_kind") != "current_case_calibration_use":
        errors.append(f"{rel_path}: operator_approval.approval_kind must be current_case_calibration_use")
    if value.get("approved_profile_manifest_sha256") != loaded.get("profile_manifest_sha256"):
        errors.append(f"{rel_path}: operator_approval.approved_profile_manifest_sha256 is stale")
    if value.get("approved_checklist_sha256") != loaded.get("checklist_sha256"):
        errors.append(f"{rel_path}: operator_approval.approved_checklist_sha256 is stale")
    if value.get("approved_source_materials_sha256") != loaded.get("source_materials_sha256"):
        errors.append(f"{rel_path}: operator_approval.approved_source_materials_sha256 is stale")
    if value.get("approved_trace_sha256") != loaded.get("opponent_report_trace_sha256"):
        errors.append(f"{rel_path}: operator_approval.approved_trace_sha256 is stale")
    for field in ("approved_by", "approved_at"):
        _require_nonempty_string(value, field, f"{rel_path}: operator_approval", errors)


def _validate_operator_approval(value: Any, label: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{label} must be object")
        return
    if value.get("approved") is not True:
        errors.append(f"{label}: approved must be true")
    if value.get("approval_kind") != "default_profile_refresh":
        errors.append(f"{label}: approval_kind must be default_profile_refresh")
    _require_int(value, "approved_profile_version", label, errors)
    _require_sha(value, "approved_profile_markdown_sha256", label, errors)
    _require_sha(value, "approved_profile_manifest_sha256", label, errors)
    for field in ("approved_by", "approved_at", "approval_scope"):
        _require_nonempty_string(value, field, label, errors)


def _validate_profile_snapshot_path(value: str, version: Any, label: str, errors: list[str]) -> None:
    if not value.startswith(REVIEWER_CALIBRATION_PROFILE_SNAPSHOT_PREFIX) or not value.endswith(".md"):
        errors.append(f"{label}: path must be under {REVIEWER_CALIBRATION_PROFILE_SNAPSHOT_PREFIX} and end with .md")
        return
    if "/" in value.removeprefix(REVIEWER_CALIBRATION_PROFILE_SNAPSHOT_PREFIX):
        errors.append(f"{label}: snapshot path must not contain nested directories")
    if isinstance(version, int) and not isinstance(version, bool):
        expected = f"{REVIEWER_CALIBRATION_PROFILE_SNAPSHOT_PREFIX}v{version}.md"
        if value != expected:
            errors.append(f"{label}: path must be {expected}")


def _validate_refs(
    values: Any,
    label: str,
    *,
    round_dir: Path | None,
    require_existing_refs: bool,
    errors: list[str],
) -> None:
    if not isinstance(values, list):
        return
    for index, value in enumerate(values, start=1):
        _validate_ref(
            value,
            f"{label} item {index}",
            round_dir=round_dir,
            require_existing_refs=require_existing_refs,
            errors=errors,
        )


def _validate_ref(
    value: Any,
    label: str,
    *,
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
    if not value.startswith(ALLOWED_REF_PREFIXES):
        allowed = ", ".join(ALLOWED_REF_PREFIXES)
        errors.append(f"{label}: ref must start with one of: {allowed}")
        return
    if require_existing_refs and round_dir is not None and not (round_dir / value).exists():
        errors.append(f"{label}: ref does not exist: {value}")


def _validate_id_field(loaded: dict[str, Any], field: str, prefix: str, errors: list[str]) -> None:
    value = loaded.get(field)
    _require_nonempty_string(loaded, field, prefix, errors)
    if isinstance(value, str) and value and not is_valid_id(value):
        errors.append(
            f"{prefix}: {field} must use only letters, numbers, dot, underscore, and dash; "
            "dot-only ids are not allowed"
        )


def _require_nonempty_string(loaded: dict[str, Any], field: str, prefix: str, errors: list[str]) -> None:
    if not isinstance(loaded.get(field), str) or not loaded[field]:
        errors.append(f"{prefix}: {field} must be non-empty str")


def _require_list(loaded: dict[str, Any], field: str, prefix: str, errors: list[str]) -> Any:
    value = loaded.get(field)
    if not isinstance(value, list):
        errors.append(f"{prefix}: {field} must be list")
    return value


def _require_nonempty_list(loaded: dict[str, Any], field: str, prefix: str, errors: list[str]) -> Any:
    value = _require_list(loaded, field, prefix, errors)
    if isinstance(value, list) and not value:
        errors.append(f"{prefix}: {field} must not be empty")
    return value


def _require_dict(loaded: dict[str, Any], field: str, prefix: str, errors: list[str]) -> Any:
    value = loaded.get(field)
    if not isinstance(value, dict):
        errors.append(f"{prefix}: {field} must be object")
    return value


def _require_bool(loaded: dict[str, Any], field: str, prefix: str, errors: list[str]) -> None:
    if not isinstance(loaded.get(field), bool):
        errors.append(f"{prefix}: {field} must be bool")


def _require_enum(
    loaded: dict[str, Any],
    field: str,
    allowed: set[str],
    prefix: str,
    errors: list[str],
) -> None:
    value = loaded.get(field)
    if value not in allowed:
        errors.append(f"{prefix}: {field} must be one of: {', '.join(sorted(allowed))}")


def _require_int(loaded: dict[str, Any], field: str, prefix: str, errors: list[str]) -> None:
    value = loaded.get(field)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        errors.append(f"{prefix}: {field} must be positive int")


def _require_sha(loaded: dict[str, Any], field: str, prefix: str, errors: list[str]) -> None:
    value = loaded.get(field)
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        errors.append(f"{prefix}: {field} must be a 64-character hex string")


def _require_sha_or_null(loaded: dict[str, Any], field: str, prefix: str, errors: list[str]) -> None:
    value = loaded.get(field)
    if value is None:
        return
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        errors.append(f"{prefix}: {field} must be null or a 64-character hex string")
