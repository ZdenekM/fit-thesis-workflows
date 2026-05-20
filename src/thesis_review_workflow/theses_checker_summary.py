"""Structural contract for operator-supplied FIT Theses Checker summaries."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

from thesis_review_workflow.artifact_validation import sha256_file
from thesis_review_workflow.paths import is_safe_round_relative_path

THESES_CHECKER_SUMMARY_REL = "work/theses_checker_summary.json"
THESES_CHECKER_SUMMARY_SCHEMA = "theses-checker-summary-v1"

SOURCE_KINDS = {"export", "screenshot", "copied_text", "operator_transcript", "other"}
SUMMARY_STATUSES = {
    "within_required_range",
    "below_required_minimum",
    "above_expected_range",
    "unknown_threshold",
    "not_applicable",
}
CHECKED_PDF_LIMITATION_TYPES = {
    "operator_did_not_bind_pdf",
    "source_does_not_identify_pdf",
    "legacy_checker_output",
    "other",
}
PRODUCER_TYPES = {"deterministic_helper", "agent", "human"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def round_uses_theses_checker_summary(round_dir: Path) -> bool:
    trace_path = round_dir / "work" / "opponent_report_trace.json"
    try:
        loaded = json.loads(trace_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(loaded, dict):
        return False
    basis = loaded.get("technical_report_scope_basis")
    return (
        isinstance(basis, dict)
        and basis.get("status") == "checker_summary"
        and basis.get("summary_path") == THESES_CHECKER_SUMMARY_REL
    )


def theses_checker_summary_dependency_files(round_dir: Path) -> list[tuple[str, Path]]:
    path = round_dir / THESES_CHECKER_SUMMARY_REL
    files: list[tuple[str, Path]] = [(f"round:{THESES_CHECKER_SUMMARY_REL}", path)]
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return files
    if not isinstance(loaded, dict):
        return files
    seen = {THESES_CHECKER_SUMMARY_REL}

    def add_ref(value: Any) -> None:
        if not isinstance(value, str) or value in seen or not _is_allowed_round_ref(value):
            return
        seen.add(value)
        files.append((f"round:{value}", round_dir / value))

    for ref in loaded.get("source_refs", []):
        add_ref(ref)
    source_artifact = loaded.get("source_artifact")
    if isinstance(source_artifact, dict):
        add_ref(source_artifact.get("path"))
    checked_pdf = loaded.get("checked_pdf")
    if isinstance(checked_pdf, dict):
        add_ref(checked_pdf.get("path"))
    return files


def validate_theses_checker_summary_artifact(
    round_dir: Path,
    rel_path: Path | str = THESES_CHECKER_SUMMARY_REL,
    *,
    case_id: str | None = None,
    round_id: str | None = None,
    require_existing_refs: bool = True,
) -> list[str]:
    rel = rel_path.as_posix() if isinstance(rel_path, Path) else rel_path
    if rel != THESES_CHECKER_SUMMARY_REL:
        return [f"{rel}: unknown theses checker summary artifact path"]
    path = round_dir / rel
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [f"{rel}: missing theses checker summary artifact"]
    except OSError as exc:
        detail = exc.strerror or exc.__class__.__name__
        return [f"{rel}: cannot read theses checker summary artifact: {detail}"]
    except json.JSONDecodeError as exc:
        return [f"{rel}: invalid JSON: {exc.msg}"]
    if not isinstance(loaded, dict):
        return [f"{rel}: JSON artifact must be an object"]
    return validate_theses_checker_summary_payload(
        loaded,
        rel,
        round_dir=round_dir,
        case_id=case_id,
        round_id=round_id,
        require_existing_refs=require_existing_refs,
    )


def validate_theses_checker_summary_payload(
    loaded: dict[str, Any],
    rel_path: str = THESES_CHECKER_SUMMARY_REL,
    *,
    round_dir: Path | None = None,
    case_id: str | None = None,
    round_id: str | None = None,
    require_existing_refs: bool = True,
) -> list[str]:
    errors: list[str] = []
    if loaded.get("schema_version") != THESES_CHECKER_SUMMARY_SCHEMA:
        errors.append(f"{rel_path}: schema_version must be {THESES_CHECKER_SUMMARY_SCHEMA}")
    if case_id is not None and loaded.get("case_id") != case_id:
        errors.append(f"{rel_path}: case_id does not match requested case")
    if round_id is not None and loaded.get("round_id") != round_id:
        errors.append(f"{rel_path}: round_id does not match requested round")
    for field in ("case_id", "round_id", "generated_at", "producer_role", "producer_agent", "captured_at"):
        _require_nonempty_string(loaded, field, rel_path, errors)
    producer_type = loaded.get("producer_type")
    if producer_type not in PRODUCER_TYPES:
        errors.append(f"{rel_path}: producer_type must be one of: {', '.join(sorted(PRODUCER_TYPES))}")
    if producer_type == "agent":
        _require_nonempty_string(loaded, "authorization_note", rel_path, errors)
    if producer_type == "human":
        _require_nonempty_string(loaded, "human_reviewer_note", rel_path, errors)
    if producer_type == "deterministic_helper":
        if loaded.get("producer_role") != "record-theses-checker-summary":
            errors.append(f"{rel_path}: deterministic producer_role must be record-theses-checker-summary")
        if loaded.get("producer_agent") != "record-theses-checker-summary":
            errors.append(f"{rel_path}: deterministic producer_agent must be record-theses-checker-summary")

    _validate_source_refs(loaded.get("source_refs"), rel_path, round_dir, require_existing_refs, errors)
    _validate_source_artifact(loaded.get("source_artifact"), rel_path, round_dir, require_existing_refs, errors)
    _validate_checked_pdf(
        loaded.get("checked_pdf"),
        loaded.get("checked_pdf_limitation"),
        rel_path,
        round_dir,
        require_existing_refs,
        errors,
    )
    normostrany = loaded.get("normostrany")
    _validate_positive_number(normostrany, f"{rel_path}: normostrany", errors)
    status = loaded.get("status")
    if status not in SUMMARY_STATUSES:
        errors.append(f"{rel_path}: status must be one of: {', '.join(sorted(SUMMARY_STATUSES))}")
    thresholds = loaded.get("thresholds")
    _validate_thresholds(thresholds, rel_path, errors)
    _validate_status_threshold_consistency(normostrany, status, thresholds, rel_path, errors)
    limitations = loaded.get("limitations")
    if not isinstance(limitations, list) or not all(isinstance(item, str) for item in limitations):
        errors.append(f"{rel_path}: limitations must be a list of strings")
    checker_timestamp = loaded.get("checker_timestamp")
    if checker_timestamp is not None and not isinstance(checker_timestamp, str):
        errors.append(f"{rel_path}: checker_timestamp must be string or null")
    return errors


def _validate_source_refs(
    value: Any,
    rel_path: str,
    round_dir: Path | None,
    require_existing_refs: bool,
    errors: list[str],
) -> None:
    if not isinstance(value, list) or not value:
        errors.append(f"{rel_path}: source_refs must be a non-empty list")
        return
    for index, ref in enumerate(value, start=1):
        prefix = f"{rel_path}: source_refs item {index}"
        if not isinstance(ref, str) or not ref:
            errors.append(f"{prefix} must be non-empty string")
            continue
        if not _is_allowed_round_ref(ref):
            errors.append(f"{prefix} must be relative under inputs/, extracted/, notes/, work/, or outputs/")
            continue
        if require_existing_refs and round_dir is not None and not (round_dir / ref).exists():
            errors.append(f"{prefix} does not exist: {ref}")


def _validate_source_artifact(
    value: Any,
    rel_path: str,
    round_dir: Path | None,
    require_existing_refs: bool,
    errors: list[str],
) -> None:
    prefix = f"{rel_path}: source_artifact"
    if not isinstance(value, dict):
        errors.append(f"{prefix} must be object")
        return
    path = value.get("path")
    _validate_hash_bound_ref(path, value.get("sha256"), prefix, round_dir, require_existing_refs, errors)
    if value.get("kind") not in SOURCE_KINDS:
        errors.append(f"{prefix}: kind must be one of: {', '.join(sorted(SOURCE_KINDS))}")


def _validate_checked_pdf(
    value: Any,
    limitation: Any,
    rel_path: str,
    round_dir: Path | None,
    require_existing_refs: bool,
    errors: list[str],
) -> None:
    if value is None:
        _validate_checked_pdf_limitation(limitation, rel_path, errors)
        return
    prefix = f"{rel_path}: checked_pdf"
    if not isinstance(value, dict):
        errors.append(f"{prefix} must be object or null")
        return
    path = value.get("path")
    _validate_hash_bound_ref(path, value.get("sha256"), prefix, round_dir, require_existing_refs, errors)
    if isinstance(path, str):
        normalized = Path(path).as_posix()
        if not normalized.startswith("inputs/") or Path(normalized).suffix.lower() != ".pdf":
            errors.append(f"{prefix}: path must be a rendered thesis PDF under inputs/")
    if limitation is not None:
        errors.append(f"{rel_path}: checked_pdf_limitation must be omitted when checked_pdf is recorded")


def _validate_checked_pdf_limitation(value: Any, rel_path: str, errors: list[str]) -> None:
    prefix = f"{rel_path}: checked_pdf_limitation"
    if not isinstance(value, dict):
        errors.append(f"{prefix} must be object when checked_pdf is null")
        return
    if value.get("type") not in CHECKED_PDF_LIMITATION_TYPES:
        errors.append(f"{prefix}: type must be one of: {', '.join(sorted(CHECKED_PDF_LIMITATION_TYPES))}")
    _require_nonempty_string(value, "description", prefix, errors)
    _require_nonempty_string(value, "accepted_by", prefix, errors)


def _validate_thresholds(value: Any, rel_path: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{rel_path}: thresholds must be object")
        return
    unknown = sorted(set(value) - {"minimum", "recommended_minimum", "maximum"})
    for key in unknown:
        errors.append(f"{rel_path}: thresholds has unknown key: {key}")
    for key in ("minimum", "recommended_minimum", "maximum"):
        if key in value:
            _validate_positive_number(value.get(key), f"{rel_path}: thresholds.{key}", errors)
    minimum = _finite_positive_number(value.get("minimum"))
    recommended = _finite_positive_number(value.get("recommended_minimum"))
    maximum = _finite_positive_number(value.get("maximum"))
    if minimum is not None and recommended is not None and recommended < minimum:
        errors.append(f"{rel_path}: thresholds.recommended_minimum must be >= thresholds.minimum")
    if minimum is not None and maximum is not None and maximum < minimum:
        errors.append(f"{rel_path}: thresholds.maximum must be >= thresholds.minimum")
    if recommended is not None and maximum is not None and maximum < recommended:
        errors.append(f"{rel_path}: thresholds.maximum must be >= thresholds.recommended_minimum")


def _validate_status_threshold_consistency(
    normostrany: Any,
    status: Any,
    thresholds: Any,
    rel_path: str,
    errors: list[str],
) -> None:
    if not _is_finite_positive(normostrany) or not isinstance(thresholds, dict):
        return
    minimum = thresholds.get("minimum")
    maximum = thresholds.get("maximum")
    if status == "within_required_range":
        if _is_finite_positive(minimum) and normostrany < minimum:
            errors.append(f"{rel_path}: status within_required_range conflicts with thresholds.minimum")
        if _is_finite_positive(maximum) and normostrany > maximum:
            errors.append(f"{rel_path}: status within_required_range conflicts with thresholds.maximum")
    elif status == "below_required_minimum":
        if not _is_finite_positive(minimum):
            errors.append(f"{rel_path}: status below_required_minimum requires thresholds.minimum")
        elif normostrany >= minimum:
            errors.append(f"{rel_path}: status below_required_minimum conflicts with thresholds.minimum")
    elif status == "above_expected_range":
        if not _is_finite_positive(maximum):
            errors.append(f"{rel_path}: status above_expected_range requires thresholds.maximum")
        elif normostrany <= maximum:
            errors.append(f"{rel_path}: status above_expected_range conflicts with thresholds.maximum")


def _validate_hash_bound_ref(
    path: Any,
    digest: Any,
    prefix: str,
    round_dir: Path | None,
    require_existing_refs: bool,
    errors: list[str],
) -> None:
    if not isinstance(path, str) or not path:
        errors.append(f"{prefix}: path must be non-empty string")
        return
    if not _is_allowed_round_ref(path):
        errors.append(f"{prefix}: path must be relative under inputs/, extracted/, notes/, work/, or outputs/")
        return
    if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
        errors.append(f"{prefix}: sha256 must be a 64-character hex string")
        return
    if require_existing_refs and round_dir is not None:
        target = round_dir / path
        if not target.is_file():
            errors.append(f"{prefix}: referenced file is missing: {path}")
        elif sha256_file(target) != digest:
            errors.append(f"{prefix}: sha256 is stale for {path}")


def _validate_positive_number(value: Any, label: str, errors: list[str]) -> None:
    if not _is_finite_positive(value):
        errors.append(f"{label} must be a positive number")


def _is_finite_positive(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def _finite_positive_number(value: Any) -> float | None:
    if not _is_finite_positive(value):
        return None
    return float(value)


def _require_nonempty_string(value: dict[str, Any], field: str, prefix: str, errors: list[str]) -> None:
    if not isinstance(value.get(field), str) or not value[field].strip():
        errors.append(f"{prefix}: {field} must be non-empty string")


def _is_allowed_round_ref(value: str) -> bool:
    return is_safe_round_relative_path(value) and value.startswith(
        ("inputs/", "extracted/", "notes/", "work/", "outputs/")
    )
