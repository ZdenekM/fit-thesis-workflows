"""Structural contracts for private supervisor-report calibration artifacts."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from thesis_review_workflow.artifact_validation import sha256_file, validate_common_artifact_fields
from thesis_review_workflow.ids import is_valid_id
from thesis_review_workflow.paths import is_safe_round_relative_path

HISTORICAL_SUPERVISOR_CASE_ANALYSIS_SCHEMA = "historical-supervisor-report-case-analysis-v1"
SUPERVISOR_REPORT_CALIBRATION_PROFILE_SCHEMA = "supervisor-report-calibration-profile-v1"
SUPERVISOR_REPORT_CHECKLIST_SCHEMA = "supervisor-report-calibration-checklist-v1"
SUPERVISOR_REPORT_PROFILE_HISTORY_SCHEMA = "supervisor-report-calibration-history-v1"
SUPERVISOR_REPORT_CALIBRATION_USE_SCHEMA = "supervisor-report-calibration-use-v1"
SUPERVISOR_REPORT_CALIBRATION_ADVISORY_SCHEMA = "supervisor-report-calibration-advisory-v1"

SUPERVISOR_CALIBRATION_DIR = "work/calibration/supervisor_report"
HISTORICAL_CASE_ANALYSIS_PREFIX = f"{SUPERVISOR_CALIBRATION_DIR}/historical_case_analyses/"
SUPERVISOR_REPORT_CALIBRATION_PROFILE_REL = f"{SUPERVISOR_CALIBRATION_DIR}/profile.json"
SUPERVISOR_REPORT_CHECKLIST_REL = f"{SUPERVISOR_CALIBRATION_DIR}/checklist.json"
SUPERVISOR_REPORT_PROFILE_HISTORY_REL = f"{SUPERVISOR_CALIBRATION_DIR}/profile_history.jsonl"
SUPERVISOR_REPORT_PROFILE_REVIEW_REL = f"{SUPERVISOR_CALIBRATION_DIR}/profile_review.md"
SUPERVISOR_REPORT_PROFILE_CHANGE_LOG_REL = f"{SUPERVISOR_CALIBRATION_DIR}/profile_change_log.md"
SUPERVISOR_REPORT_CALIBRATION_PROFILE_MARKDOWN_REL = "outputs/supervisor_report_calibration_profile.md"
SUPERVISOR_REPORT_PROFILE_SNAPSHOT_PREFIX = f"{SUPERVISOR_CALIBRATION_DIR}/profile_versions/"
SUPERVISOR_REPORT_CALIBRATION_USE_REL = "work/supervisor_report_calibration_use.json"
SUPERVISOR_REPORT_CALIBRATION_ADVISORY_REL = "work/supervisor_report_calibration_advisory.json"
SUPERVISOR_REPORT_TRACE_REL = "work/supervisor_report_trace.json"

EXACT_SUPERVISOR_CALIBRATION_SCHEMAS: dict[str, str] = {
    SUPERVISOR_REPORT_CALIBRATION_PROFILE_REL: SUPERVISOR_REPORT_CALIBRATION_PROFILE_SCHEMA,
    SUPERVISOR_REPORT_CHECKLIST_REL: SUPERVISOR_REPORT_CHECKLIST_SCHEMA,
    SUPERVISOR_REPORT_PROFILE_HISTORY_REL: SUPERVISOR_REPORT_PROFILE_HISTORY_SCHEMA,
    SUPERVISOR_REPORT_CALIBRATION_USE_REL: SUPERVISOR_REPORT_CALIBRATION_USE_SCHEMA,
    SUPERVISOR_REPORT_CALIBRATION_ADVISORY_REL: SUPERVISOR_REPORT_CALIBRATION_ADVISORY_SCHEMA,
}

ALLOWED_REF_PREFIXES = ("inputs/", "extracted/", "notes/", "work/", "outputs/")
SUPERVISOR_REPORT_FIELD_IDS = {
    "assignment_information",
    "literature_work",
    "activity_during_solution",
    "completion_activity",
    "publication_activity",
    "overall_assessment",
    "student_comment",
}
CONFIDENCE_DIMENSIONS = {
    "tone",
    "length",
    "grading",
    "process_evidence",
    "student_comment",
    "publication_wording",
}
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
REVIEWED_STATUSES = {"reviewed", "reviewed_with_notes"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def supervisor_calibration_schema_for_rel_path(rel_path: str) -> str | None:
    if rel_path in EXACT_SUPERVISOR_CALIBRATION_SCHEMAS:
        return EXACT_SUPERVISOR_CALIBRATION_SCHEMAS[rel_path]
    if historical_case_analysis_id(rel_path) is not None:
        return HISTORICAL_SUPERVISOR_CASE_ANALYSIS_SCHEMA
    return None


def historical_case_analysis_id(rel_path: str) -> str | None:
    if not rel_path.startswith(HISTORICAL_CASE_ANALYSIS_PREFIX) or not rel_path.endswith(".json"):
        return None
    suffix = rel_path.removeprefix(HISTORICAL_CASE_ANALYSIS_PREFIX)
    if "/" in suffix:
        return None
    historical_case_id = suffix.removesuffix(".json")
    return historical_case_id if is_valid_id(historical_case_id) else None


def is_supervisor_report_calibration_artifact(rel_path: str) -> bool:
    return supervisor_calibration_schema_for_rel_path(rel_path) is not None


def supervisor_report_calibration_profile_check_targets(round_dir: Path) -> list[str]:
    targets = [
        SUPERVISOR_REPORT_CALIBRATION_PROFILE_MARKDOWN_REL,
        SUPERVISOR_REPORT_CALIBRATION_PROFILE_REL,
        SUPERVISOR_REPORT_CHECKLIST_REL,
        SUPERVISOR_REPORT_PROFILE_HISTORY_REL,
        SUPERVISOR_REPORT_PROFILE_CHANGE_LOG_REL,
        SUPERVISOR_REPORT_PROFILE_REVIEW_REL,
    ]
    analyses_dir = round_dir / HISTORICAL_CASE_ANALYSIS_PREFIX
    if analyses_dir.is_dir():
        targets.extend(path.relative_to(round_dir).as_posix() for path in sorted(analyses_dir.rglob("*.json")))
    snapshots_dir = round_dir / SUPERVISOR_REPORT_PROFILE_SNAPSHOT_PREFIX
    if snapshots_dir.is_dir():
        targets.extend(path.relative_to(round_dir).as_posix() for path in sorted(snapshots_dir.rglob("*.md")))
    return targets


def validate_supervisor_report_calibration_artifact(
    round_dir: Path,
    rel_path: Path | str,
    *,
    case_id: str | None = None,
    round_id: str | None = None,
    require_existing_refs: bool = True,
    allow_stale_trace_binding: bool = False,
) -> list[str]:
    rel = rel_path.as_posix() if isinstance(rel_path, Path) else rel_path
    path_errors = validate_supervisor_report_calibration_rel_path(rel)
    if path_errors:
        return path_errors
    if rel == SUPERVISOR_REPORT_PROFILE_HISTORY_REL:
        return validate_profile_history_artifact(
            round_dir / rel,
            rel,
            round_dir,
            case_id=case_id,
            round_id=round_id,
            require_existing_refs=require_existing_refs,
        )
    try:
        loaded = json.loads((round_dir / rel).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [f"{rel}: missing supervisor-report calibration artifact"]
    except OSError as exc:
        detail = exc.strerror or exc.__class__.__name__
        return [f"{rel}: cannot read supervisor-report calibration artifact: {detail}"]
    except json.JSONDecodeError as exc:
        return [f"{rel}: invalid JSON: {exc.msg}"]
    if not isinstance(loaded, dict):
        return [f"{rel}: JSON supervisor-report calibration artifact must be an object"]
    return validate_supervisor_report_calibration_payload(
        loaded,
        rel,
        round_dir=round_dir,
        case_id=case_id,
        round_id=round_id,
        require_existing_refs=require_existing_refs,
        allow_stale_trace_binding=allow_stale_trace_binding,
    )


def validate_supervisor_report_calibration_rel_path(rel_path: str) -> list[str]:
    if not is_safe_round_relative_path(rel_path):
        return [f"{rel_path}: supervisor-report calibration path must be relative inside the round"]
    if supervisor_calibration_schema_for_rel_path(rel_path) is None:
        return [f"{rel_path}: unknown supervisor-report calibration artifact path"]
    return []


def validate_supervisor_report_calibration_payload(
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
    path_errors = validate_supervisor_report_calibration_rel_path(rel_path)
    if path_errors:
        return path_errors
    expected_schema = supervisor_calibration_schema_for_rel_path(rel_path)
    if expected_schema is None:
        return [f"{rel_path}: unknown supervisor-report calibration artifact path"]
    validate_common_artifact_fields(
        loaded,
        rel_path,
        expected_schema,
        case_id,
        round_id,
        errors,
        required_string_fields=("case_id", "round_id", "generated_at", "producer_role"),
    )
    if expected_schema == HISTORICAL_SUPERVISOR_CASE_ANALYSIS_SCHEMA:
        _validate_historical_case_analysis(loaded, rel_path, errors)
    elif expected_schema == SUPERVISOR_REPORT_CALIBRATION_PROFILE_SCHEMA:
        _validate_profile_manifest(loaded, rel_path, round_dir, errors)
    elif expected_schema == SUPERVISOR_REPORT_CHECKLIST_SCHEMA:
        _validate_checklist(loaded, rel_path, errors)
    elif expected_schema == SUPERVISOR_REPORT_CALIBRATION_USE_SCHEMA:
        _validate_calibration_use(loaded, rel_path, round_dir, errors, allow_stale_trace_binding)
    elif expected_schema == SUPERVISOR_REPORT_CALIBRATION_ADVISORY_SCHEMA:
        _validate_calibration_advisory(loaded, rel_path, round_dir, errors, allow_stale_trace_binding)
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
        return [f"{rel_path}: missing supervisor-report calibration artifact"]
    previous_entry_hash: str | None = None
    expected_version = 1
    for index, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            loaded = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{rel_path}: line {index}: invalid JSON: {exc.msg}")
            continue
        if not isinstance(loaded, dict):
            errors.append(f"{rel_path}: line {index}: JSONL entry must be an object")
            continue
        errors.extend(
            validate_supervisor_report_calibration_payload(
                loaded,
                rel_path,
                round_dir=round_dir,
                case_id=case_id,
                round_id=round_id,
                require_existing_refs=require_existing_refs,
            )
        )
        version = loaded.get("profile_version")
        if version != expected_version:
            errors.append(f"{rel_path}: line {index}: profile_version must be {expected_version}")
        if loaded.get("previous_history_entry_sha256") != previous_entry_hash:
            errors.append(f"{rel_path}: line {index}: previous_history_entry_sha256 is stale")
        previous_entry_hash = _sha256_text(line)
        expected_version += 1
    if expected_version == 1:
        errors.append(f"{rel_path}: missing profile history entries")
    return errors


def _validate_historical_case_analysis(loaded: dict[str, Any], rel_path: str, errors: list[str]) -> None:
    expected_case_id = historical_case_analysis_id(rel_path)
    if loaded.get("historical_case_id") != expected_case_id:
        errors.append(f"{rel_path}: historical_case_id must match the artifact filename")
    _validate_historical_case_refs(
        loaded.get("source_refs"),
        f"{rel_path}: source_refs",
        expected_case_id,
        errors,
    )
    _require_nonempty_string(loaded, "work_type", rel_path, errors)
    _require_nonempty_string(loaded, "domain", rel_path, errors)
    _require_enum(loaded, "case_strength", HISTORICAL_CASE_STRENGTHS, rel_path, errors)
    _require_nonempty_list(loaded, "tone_observations", rel_path, errors)
    _require_nonempty_list(loaded, "length_observations", rel_path, errors)
    _require_nonempty_list(loaded, "grading_observations", rel_path, errors)
    field_patterns = _require_nonempty_list(loaded, "field_patterns", rel_path, errors)
    if isinstance(field_patterns, list):
        for index, item in enumerate(field_patterns, start=1):
            prefix = f"{rel_path}: field_patterns item {index}"
            if not isinstance(item, dict):
                errors.append(f"{prefix} must be object")
                continue
            _require_enum(item, "field_id", SUPERVISOR_REPORT_FIELD_IDS, prefix, errors)
            _require_nonempty_string(item, "summary", prefix, errors)
            evidence_refs = _require_nonempty_list(item, "evidence_refs", prefix, errors)
            _validate_historical_case_refs(evidence_refs, f"{prefix}: evidence_refs", expected_case_id, errors)
    _require_nonempty_list(loaded, "do_not_generalize", rel_path, errors)


def _validate_profile_manifest(
    loaded: dict[str, Any],
    rel_path: str,
    round_dir: Path | None,
    errors: list[str],
) -> None:
    _validate_hash_binding(
        loaded,
        rel_path,
        round_dir,
        path_field="profile_markdown_path",
        hash_field="profile_markdown_sha256",
        expected_path=SUPERVISOR_REPORT_CALIBRATION_PROFILE_MARKDOWN_REL,
        errors=errors,
    )
    version = loaded.get("profile_version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        errors.append(f"{rel_path}: profile_version must be positive int")
    if version == 1 and loaded.get("profile_previous_sha256") is not None:
        errors.append(f"{rel_path}: profile_previous_sha256 must be null for version 1")
    elif version != 1 and not _is_sha256(loaded.get("profile_previous_sha256")):
        errors.append(f"{rel_path}: profile_previous_sha256 must be a 64-character hex string")
    _require_nonempty_string(loaded, "profile_change_summary", rel_path, errors)
    _require_nonempty_list(loaded, "source_case_refs", rel_path, errors)
    if len(distinct_historical_analysis_refs(loaded.get("source_case_refs"))) < 2:
        errors.append(f"{rel_path}: source_case_refs must reference at least two historical case analyses")
    confidence = loaded.get("confidence_by_dimension")
    if not isinstance(confidence, dict):
        errors.append(f"{rel_path}: confidence_by_dimension must be object")
    else:
        missing = sorted(CONFIDENCE_DIMENSIONS.difference(confidence))
        for dimension in missing:
            errors.append(f"{rel_path}: confidence_by_dimension missing {dimension}")
    _require_nonempty_list(loaded, "do_not_use_for", rel_path, errors)


def _validate_checklist(loaded: dict[str, Any], rel_path: str, errors: list[str]) -> None:
    items = _require_nonempty_list(loaded, "checklist_items", rel_path, errors)
    if not isinstance(items, list):
        return
    seen: set[str] = set()
    for index, item in enumerate(items, start=1):
        prefix = f"{rel_path}: checklist_items item {index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be object")
            continue
        item_id = item.get("item_id")
        if isinstance(item_id, str):
            if item_id in seen:
                errors.append(f"{prefix}: duplicate item_id {item_id}")
            seen.add(item_id)
        _require_nonempty_string(item, "item_id", prefix, errors)
        _require_enum(item, "field_id", SUPERVISOR_REPORT_FIELD_IDS, prefix, errors)
        _require_nonempty_string(item, "prompt", prefix, errors)
        _require_nonempty_list(item, "source_case_refs", prefix, errors)
        if item.get("requires_current_case_evidence") is not True:
            errors.append(f"{prefix}: requires_current_case_evidence must be true")


def _validate_calibration_use(
    loaded: dict[str, Any],
    rel_path: str,
    round_dir: Path | None,
    errors: list[str],
    allow_stale_trace_binding: bool,
) -> None:
    _validate_hash_binding(
        loaded,
        rel_path,
        round_dir,
        path_field="selected_profile_path",
        hash_field="selected_profile_sha256",
        expected_path=SUPERVISOR_REPORT_CALIBRATION_PROFILE_REL,
        errors=errors,
    )
    _validate_hash_binding(
        loaded,
        rel_path,
        round_dir,
        path_field="selected_checklist_path",
        hash_field="selected_checklist_sha256",
        expected_path=SUPERVISOR_REPORT_CHECKLIST_REL,
        errors=errors,
    )
    _validate_hash_binding(
        loaded,
        rel_path,
        round_dir,
        path_field="target_report_trace_path",
        hash_field="target_report_trace_sha256",
        expected_path=SUPERVISOR_REPORT_TRACE_REL,
        errors=errors,
        allow_stale=allow_stale_trace_binding,
    )
    _require_enum(loaded, "applicability_status", CALIBRATION_APPLICABILITY_STATUSES, rel_path, errors)
    _require_source_refs_include(
        loaded,
        rel_path,
        (
            SUPERVISOR_REPORT_CALIBRATION_PROFILE_REL,
            SUPERVISOR_REPORT_CHECKLIST_REL,
            SUPERVISOR_REPORT_TRACE_REL,
        ),
        errors,
    )
    if loaded.get("anti_overfit_review_status") not in REVIEWED_STATUSES:
        errors.append(f"{rel_path}: anti_overfit_review_status must be reviewed or reviewed_with_notes")
    _require_nonempty_list(loaded, "current_case_evidence_boundaries", rel_path, errors)


def _validate_calibration_advisory(
    loaded: dict[str, Any],
    rel_path: str,
    round_dir: Path | None,
    errors: list[str],
    allow_stale_trace_binding: bool,
) -> None:
    _require_enum(loaded, "advisory_reason", CALIBRATION_ADVISORY_REASONS, rel_path, errors)
    _require_nonempty_string(loaded, "operator_message", rel_path, errors)
    _validate_hash_binding(
        loaded,
        rel_path,
        round_dir,
        path_field="target_report_trace_path",
        hash_field="target_report_trace_sha256",
        expected_path=SUPERVISOR_REPORT_TRACE_REL,
        errors=errors,
        allow_stale=allow_stale_trace_binding,
    )
    _require_source_refs_include(loaded, rel_path, (SUPERVISOR_REPORT_TRACE_REL,), errors)


def distinct_historical_analysis_refs(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted({item for item in value if isinstance(item, str) and historical_case_analysis_id(item) is not None})


def _validate_refs(
    refs: Any,
    prefix: str,
    *,
    round_dir: Path | None,
    require_existing_refs: bool,
    errors: list[str],
) -> None:
    if not isinstance(refs, list):
        errors.append(f"{prefix} must be list")
        return
    for index, ref in enumerate(refs, start=1):
        if not isinstance(ref, str) or not _is_allowed_round_ref(ref):
            errors.append(f"{prefix} item {index}: path must be under inputs/, extracted/, notes/, work/, or outputs/")
        elif require_existing_refs and round_dir is not None and not (round_dir / ref).exists():
            errors.append(f"{prefix} item {index}: missing referenced artifact {ref}")


def _validate_historical_case_refs(
    refs: Any,
    prefix: str,
    historical_case_id: str | None,
    errors: list[str],
) -> None:
    if historical_case_id is None:
        return
    expected_prefix = f"inputs/historical_cases/{historical_case_id}/"
    if not isinstance(refs, list):
        return
    matching_seen = False
    for index, ref in enumerate(refs, start=1):
        if not isinstance(ref, str):
            continue
        if is_safe_round_relative_path(ref) and ref.startswith(expected_prefix):
            matching_seen = True
            continue
        errors.append(f"{prefix} item {index}: historical analysis ref must stay under {expected_prefix}")
    if not matching_seen:
        errors.append(f"{prefix} must include at least one ref under {expected_prefix}")


def _require_source_refs_include(
    loaded: dict[str, Any],
    rel_path: str,
    required_refs: tuple[str, ...],
    errors: list[str],
) -> None:
    refs = loaded.get("source_refs")
    if not isinstance(refs, list):
        return
    present = {ref for ref in refs if isinstance(ref, str)}
    for required in required_refs:
        if required not in present:
            errors.append(f"{rel_path}: source_refs must include {required}")


def _validate_hash_binding(
    loaded: dict[str, Any],
    rel_path: str,
    round_dir: Path | None,
    *,
    path_field: str,
    hash_field: str,
    expected_path: str,
    errors: list[str],
    allow_stale: bool = False,
) -> None:
    path_value = loaded.get(path_field)
    hash_value = loaded.get(hash_field)
    if path_value != expected_path:
        errors.append(f"{rel_path}: {path_field} must be {expected_path}")
    if not _is_sha256(hash_value):
        errors.append(f"{rel_path}: {hash_field} must be a 64-character hex string")
        return
    if round_dir is not None and isinstance(path_value, str):
        path = round_dir / path_value
        if not path.is_file():
            errors.append(f"{rel_path}: missing bound artifact {path_value}")
        elif sha256_file(path) != hash_value and not allow_stale:
            errors.append(f"{rel_path}: {hash_field} is stale for {path_value}")


def _is_allowed_round_ref(value: str) -> bool:
    return is_safe_round_relative_path(value) and value.startswith(ALLOWED_REF_PREFIXES)


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _require_nonempty_string(value: dict[str, Any], field: str, prefix: str, errors: list[str]) -> None:
    if not isinstance(value.get(field), str) or not value[field]:
        errors.append(f"{prefix}: {field} must be non-empty str")


def _require_nonempty_list(value: dict[str, Any], field: str, prefix: str, errors: list[str]) -> Any:
    loaded = value.get(field)
    if not isinstance(loaded, list):
        errors.append(f"{prefix}: {field} must be list")
    elif not loaded:
        errors.append(f"{prefix}: {field} must not be empty")
    return loaded


def _require_enum(value: dict[str, Any], field: str, allowed: set[str], prefix: str, errors: list[str]) -> None:
    loaded = value.get(field)
    if loaded not in allowed:
        choices = ", ".join(sorted(allowed))
        errors.append(f"{prefix}: {field} must be one of {choices}")
