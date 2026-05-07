"""Structural contracts for private opponent calibration artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from thesis_review_workflow.artifact_validation import sha256_file, validate_common_artifact_fields
from thesis_review_workflow.ids import is_valid_id
from thesis_review_workflow.paths import is_safe_round_relative_path

HISTORICAL_CASE_ANALYSIS_SCHEMA = "historical-opponent-case-analysis-v1"
REVIEWER_CALIBRATION_PROFILE_SCHEMA = "opponent-reviewer-calibration-profile-v1"
REVIEWER_CHECKLIST_SCHEMA = "opponent-reviewer-checklist-v1"
REVIEWER_PROFILE_HISTORY_SCHEMA = "opponent-reviewer-calibration-history-v1"

HISTORICAL_CASE_ANALYSIS_PREFIX = "work/calibration/historical_case_analyses/"
REVIEWER_CALIBRATION_PROFILE_REL = "work/calibration/reviewer_calibration_profile.json"
REVIEWER_CHECKLIST_REL = "work/calibration/reviewer_checklist.json"
REVIEWER_PROFILE_HISTORY_REL = "work/calibration/reviewer_calibration_profile_history.jsonl"
REVIEWER_CALIBRATION_PROFILE_MARKDOWN_REL = "outputs/reviewer_calibration_profile.md"
REVIEWER_PROFILE_REVIEW_REL = "work/calibration/profile_review.md"
REVIEWER_PROFILE_CHANGE_LOG_REL = "work/calibration/reviewer_profile_change_log.md"

EXACT_CALIBRATION_ARTIFACT_SCHEMAS: dict[str, str] = {
    REVIEWER_CALIBRATION_PROFILE_REL: REVIEWER_CALIBRATION_PROFILE_SCHEMA,
    REVIEWER_CHECKLIST_REL: REVIEWER_CHECKLIST_SCHEMA,
    REVIEWER_PROFILE_HISTORY_REL: REVIEWER_PROFILE_HISTORY_SCHEMA,
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
HISTORICAL_CASE_STRENGTHS = {"strong", "typical", "weak", "atypical", "unknown"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


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
    return targets


def validate_opponent_calibration_artifact(
    round_dir: Path,
    rel_path: Path | str,
    *,
    case_id: str | None = None,
    round_id: str | None = None,
    require_existing_refs: bool = True,
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
    _require_list(loaded, "recurring_checks", rel_path, errors)
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
    _validate_confidence_by_dimension(loaded.get("confidence_by_dimension"), rel_path, errors)
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
    for index, item in enumerate(items, start=1):
        prefix = f"{rel_path}: checklist_items item {index}"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be object")
            continue
        for field in ("item_id", "evidence_class", "prompt"):
            _require_nonempty_string(item, field, prefix, errors)
        source_case_refs = _require_nonempty_list(item, "source_case_refs", prefix, errors)
        _validate_historical_analysis_refs(
            source_case_refs,
            f"{prefix}: source_case_refs",
            round_dir=round_dir,
            require_existing_refs=require_existing_refs,
            errors=errors,
        )
        _require_bool(item, "requires_current_case_evidence", prefix, errors)


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
