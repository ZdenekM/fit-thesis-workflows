"""Supervisor-report wrapper around shared post-review delta records."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from thesis_review_workflow.artifact_validation import sha256_file
from thesis_review_workflow.paths import is_safe_round_relative_path
from thesis_review_workflow.review_approvals import validate_review_approval_with_manifest
from thesis_review_workflow.review_delta import REVIEW_DELTA_SCHEMA, build_review_delta_payload
from thesis_review_workflow.review_delta import copy_previous_snapshot as _copy_previous_snapshot
from thesis_review_workflow.review_delta import (
    review_delta_record_rel,
    review_delta_snapshot_rel,
    validate_review_delta_record,
)
from thesis_review_workflow.review_manifest import MANIFEST_REL, load_manifest
from thesis_review_workflow.supervisor_report import (
    SUPERVISOR_REPORT_CONFIRMATION_REL,
    SUPERVISOR_REPORT_REVIEW_REL,
    SUPERVISOR_REPORT_REVIEWED_REL,
    confirmation_grade_points,
    extract_markdown_grade_points,
    private_student_comment_text,
    public_report_text,
    strip_metadata_comments,
)

REPORT_AMENDMENT_SCHEMA = REVIEW_DELTA_SCHEMA
AMENDMENT_TYPES = {"style_only", "public_text_delta", "private_comment_delta", "material_claim_delta"}
NON_MATERIAL_AMENDMENT_TYPES = {"style_only", "public_text_delta", "private_comment_delta"}


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def amendment_record_rel(amended_at: str, amendment_type: str) -> str:
    return review_delta_record_rel(amended_at, amendment_type)


def amendment_snapshot_rel(amended_at: str, amendment_type: str) -> str:
    return review_delta_snapshot_rel(amended_at, amendment_type, suffix=".md")


def copy_previous_snapshot(source: Path, round_dir: Path, rel_path: str, *, force: bool = False) -> str:
    return _copy_previous_snapshot(source, round_dir, rel_path, force=force)


def report_delta_type(amendment_type: str) -> str:
    if amendment_type == "style_only":
        return "style_only"
    if amendment_type in {"public_text_delta", "private_comment_delta"}:
        return "operator_preference"
    if amendment_type == "material_claim_delta":
        return "material_claim_delta"
    raise ValueError(f"amendment_type must be one of {', '.join(sorted(AMENDMENT_TYPES))}")


def report_affected_sections(amendment_type: str) -> list[str]:
    if amendment_type == "private_comment_delta":
        return ["supervisor_report.private_student_comment"]
    if amendment_type == "public_text_delta":
        return ["supervisor_report.public_text"]
    if amendment_type == "style_only":
        return ["supervisor_report.visible_text"]
    return ["supervisor_report.material_claim"]


def build_report_amendment_payload(
    round_dir: Path,
    *,
    case_id: str,
    round_id: str,
    amendment_type: str,
    previous_snapshot_rel: str,
    current_artifact_rel: str = SUPERVISOR_REPORT_REVIEWED_REL,
    amended_at: str,
    approved_by: str,
    rationale: str,
) -> dict[str, Any]:
    delta_type = report_delta_type(amendment_type)
    if not approved_by.strip():
        raise ValueError("--approved-by is required for report amendment deltas")
    if not rationale.strip():
        raise ValueError("--rationale is required for report amendment deltas")
    payload = build_review_delta_payload(
        round_dir,
        case_id=case_id,
        round_id=round_id,
        profile_id="supervisor_report",
        delta_type=delta_type,
        previous_snapshot_rel=previous_snapshot_rel,
        current_artifact_rel=current_artifact_rel,
        generated_at=amended_at,
        rationale=rationale,
        affected_sections=report_affected_sections(amendment_type),
        approval_record_rel=SUPERVISOR_REPORT_REVIEW_REL,
        typed_exception_type="",
        typed_exception_rationale="",
        approved_by=approved_by,
    )
    payload.update(report_specific_fields(round_dir, payload, amendment_type=amendment_type, approved_by=approved_by))
    errors = validate_report_amendment_record(payload, round_dir=round_dir)
    if errors:
        raise ValueError("\n".join(errors))
    return payload


def report_specific_fields(
    round_dir: Path, payload: dict[str, Any], *, amendment_type: str, approved_by: str
) -> dict[str, Any]:
    previous_path = round_dir / str(payload["previous_artifact_path"])
    current_path = round_dir / str(payload["current_artifact_path"])
    previous_text = previous_path.read_text(encoding="utf-8")
    current_text = current_path.read_text(encoding="utf-8")
    previous_grade_points = extract_markdown_grade_points(previous_text, require=True)
    current_grade_points = extract_markdown_grade_points(current_text, require=True)
    previous_public = public_report_text(previous_text)
    current_public = public_report_text(current_text)
    previous_private = private_student_comment_text(previous_text)
    current_private = private_student_comment_text(current_text)
    previous_visible = strip_metadata_comments(previous_text)
    current_visible = strip_metadata_comments(current_text)
    confirmation = load_json_object(round_dir / SUPERVISOR_REPORT_CONFIRMATION_REL, SUPERVISOR_REPORT_CONFIRMATION_REL)
    source_refs = list(payload.get("source_refs", []))
    for ref in (SUPERVISOR_REPORT_CONFIRMATION_REL, SUPERVISOR_REPORT_REVIEW_REL):
        if (round_dir / ref).is_file() and ref not in source_refs:
            source_refs.append(ref)
    source_sha256 = dict(payload.get("source_sha256", {}))
    for ref in source_refs:
        path = round_dir / ref
        if path.is_file():
            source_sha256[ref] = sha256_file(path)
    return {
        "report_kind": "supervisor_report",
        "amendment_type": amendment_type,
        "approved_by": approved_by.strip(),
        "approved_at": payload["generated_at"],
        "requires_semantic_review": bool(payload.get("independent_review_reopened")),
        "supervisor_confirmation_path": SUPERVISOR_REPORT_CONFIRMATION_REL,
        "supervisor_confirmation_sha256": sha256_file(round_dir / SUPERVISOR_REPORT_CONFIRMATION_REL),
        "confirmed_grade": confirmation_grade_points(confirmation).grade,
        "confirmed_points": confirmation_grade_points(confirmation).points,
        "grade_changed": (previous_grade_points.grade, previous_grade_points.points)
        != (current_grade_points.grade, current_grade_points.points),
        "evidence_anchor_changed": _metadata_fingerprint(previous_text) != _metadata_fingerprint(current_text),
        "public_text_changed": normalize_text(previous_public) != normalize_text(current_public),
        "private_comment_changed": normalize_text(previous_private) != normalize_text(current_private),
        "normalized_visible_text_changed": normalize_text(previous_visible) != normalize_text(current_visible),
        "source_refs": source_refs,
        "source_sha256": source_sha256,
    }


def validate_report_amendment_record(
    loaded: Any,
    *,
    round_dir: Path,
    case_id: str | None = None,
    round_id: str | None = None,
    rel_path: str = "report amendment",
) -> list[str]:
    errors = validate_review_delta_record(
        loaded,
        round_dir=round_dir,
        case_id=case_id,
        round_id=round_id,
        profile_id="supervisor_report",
        rel_path=rel_path,
    )
    if not isinstance(loaded, dict):
        return errors
    if loaded.get("report_kind") != "supervisor_report":
        errors.append(f"{rel_path}: report_kind must be supervisor_report")
    amendment_type = loaded.get("amendment_type")
    if amendment_type not in AMENDMENT_TYPES:
        errors.append(f"{rel_path}: amendment_type must be one of {', '.join(sorted(AMENDMENT_TYPES))}")
    previous_path = _validate_hash_bound_path(
        loaded, rel_path, round_dir, "previous_artifact_path", "previous_artifact_sha256", errors
    )
    current_path = _validate_hash_bound_path(
        loaded, rel_path, round_dir, "current_artifact_path", "current_artifact_sha256", errors
    )
    confirmation_path = _validate_hash_bound_path(
        loaded, rel_path, round_dir, "supervisor_confirmation_path", "supervisor_confirmation_sha256", errors
    )
    approval_path = _validate_hash_bound_path(
        loaded, rel_path, round_dir, "approval_record_path", "approval_record_sha256", errors
    )
    if previous_path is not None and current_path is not None and isinstance(amendment_type, str):
        _validate_recomputed_report_state(
            loaded,
            rel_path,
            amendment_type=amendment_type,
            previous_path=previous_path,
            current_path=current_path,
            confirmation_path=confirmation_path,
            approval_path=approval_path,
            errors=errors,
        )
    if amendment_type in NON_MATERIAL_AMENDMENT_TYPES and loaded.get("requires_semantic_review") is not False:
        errors.append(f"{rel_path}: bounded report amendment must not require semantic review")
    if amendment_type == "material_claim_delta" and loaded.get("independent_review_reopened") is not True:
        errors.append(f"{rel_path}: material_claim_delta must reopen independent review")
    if loaded.get("supervisor_confirmation_path") != SUPERVISOR_REPORT_CONFIRMATION_REL:
        errors.append(f"{rel_path}: supervisor_confirmation_path must be {SUPERVISOR_REPORT_CONFIRMATION_REL}")
    if loaded.get("approval_record_path") != SUPERVISOR_REPORT_REVIEW_REL:
        errors.append(f"{rel_path}: approval_record_path must be {SUPERVISOR_REPORT_REVIEW_REL}")
    if not isinstance(loaded.get("approved_by"), str) or not str(loaded.get("approved_by")).strip():
        errors.append(f"{rel_path}: approved_by must be a non-empty string")
    if loaded.get("approval_record_path") == SUPERVISOR_REPORT_REVIEW_REL:
        approval_payload = None
        approval_file = round_dir / SUPERVISOR_REPORT_REVIEW_REL
        if approval_file.is_file():
            try:
                approval_payload = load_json_object(approval_file, SUPERVISOR_REPORT_REVIEW_REL)
            except ValueError as exc:
                errors.append(str(exc))
        manifest = _load_manifest(round_dir, rel_path, errors)
        if approval_payload is not None and manifest is not None:
            errors.extend(
                validate_review_approval_with_manifest(
                    approval_payload,
                    SUPERVISOR_REPORT_REVIEW_REL,
                    round_dir,
                    manifest=manifest,
                    case_id=case_id,
                    round_id=round_id,
                    reviewed_artifact_path=SUPERVISOR_REPORT_REVIEWED_REL,
                )
            )
    return errors


def _validate_hash_bound_path(
    loaded: dict[str, Any],
    rel_path: str,
    round_dir: Path,
    path_field: str,
    hash_field: str,
    errors: list[str],
) -> Path | None:
    path_value = loaded.get(path_field)
    if not isinstance(path_value, str) or not is_safe_round_relative_path(path_value):
        errors.append(f"{rel_path}: {path_field} must be a safe round-relative path")
        return None
    path = round_dir / path_value
    if not path.is_file():
        errors.append(f"{rel_path}: {path_field} points to a missing file: {path_value}")
        return None
    if loaded.get(hash_field) != sha256_file(path):
        errors.append(f"{rel_path}: {hash_field} is stale for {path_value}")
        return None
    return path


def _validate_recomputed_report_state(
    loaded: dict[str, Any],
    rel_path: str,
    *,
    amendment_type: str,
    previous_path: Path,
    current_path: Path,
    confirmation_path: Path | None,
    approval_path: Path | None,
    errors: list[str],
) -> None:
    previous_text = previous_path.read_text(encoding="utf-8")
    current_text = current_path.read_text(encoding="utf-8")
    previous_grade_points = extract_markdown_grade_points(previous_text, require=True)
    current_grade_points = extract_markdown_grade_points(current_text, require=True)
    previous_public = public_report_text(previous_text)
    current_public = public_report_text(current_text)
    previous_private = private_student_comment_text(previous_text)
    current_private = private_student_comment_text(current_text)
    previous_visible = strip_metadata_comments(previous_text)
    current_visible = strip_metadata_comments(current_text)
    confirmation: dict[str, Any] | None = None
    approval: dict[str, Any] | None = None
    if confirmation_path is not None:
        try:
            confirmation = load_json_object(confirmation_path, f"{rel_path}: supervisor confirmation")
        except ValueError as exc:
            errors.append(str(exc))
    if approval_path is not None:
        try:
            approval = load_json_object(approval_path, f"{rel_path}: review approval")
        except ValueError as exc:
            errors.append(str(exc))
    expected: dict[str, object] = {
        "grade_changed": (previous_grade_points.grade, previous_grade_points.points)
        != (current_grade_points.grade, current_grade_points.points),
        "evidence_anchor_changed": _metadata_fingerprint(previous_text) != _metadata_fingerprint(current_text),
        "public_text_changed": normalize_text(previous_public) != normalize_text(current_public),
        "private_comment_changed": normalize_text(previous_private) != normalize_text(current_private),
        "normalized_visible_text_changed": normalize_text(previous_visible) != normalize_text(current_visible),
    }
    if confirmation is not None:
        confirmation_values = confirmation_grade_points(confirmation)
        expected["confirmed_grade"] = confirmation_values.grade
        expected["confirmed_points"] = confirmation_values.points
        if confirmation.get("reviewed_report_path") != loaded.get("current_artifact_path"):
            errors.append(f"{rel_path}: supervisor confirmation must target current_artifact_path")
        if confirmation.get("reviewed_report_sha256") != sha256_file(current_path):
            errors.append(f"{rel_path}: supervisor confirmation is stale for current artifact")
    if approval is not None and approval.get("reviewed_artifact_path") != loaded.get("current_artifact_path"):
        errors.append(f"{rel_path}: review approval must target current_artifact_path")
    for field, expected_value in expected.items():
        if loaded.get(field) != expected_value:
            errors.append(f"{rel_path}: {field} is stale")
    if amendment_type in NON_MATERIAL_AMENDMENT_TYPES:
        if expected["grade_changed"] is True:
            errors.append(f"{rel_path}: grade or points changed; record material_claim_delta and rerun review")
        if expected["evidence_anchor_changed"] is True:
            errors.append(f"{rel_path}: evidence anchor metadata changed; record material_claim_delta and rerun review")
    if amendment_type == "style_only" and expected["normalized_visible_text_changed"] is True:
        errors.append(f"{rel_path}: style_only amendment cannot change normalized visible text")
    if amendment_type == "private_comment_delta" and expected["public_text_changed"] is True:
        errors.append(f"{rel_path}: private_comment_delta cannot change public report text")
    if amendment_type == "public_text_delta" and expected["public_text_changed"] is not True:
        errors.append(f"{rel_path}: public_text_delta must change public report text")


def _metadata_fingerprint(text: str) -> str:
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip().startswith("<!--")
        and any(token in line for token in ("source_trace_", "supervisor_input_", "source_materials_"))
    ]
    return "\n".join(lines)


def load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing required artifact: {label}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {label}: {exc.msg}") from exc
    if not isinstance(loaded, dict):
        raise ValueError(f"invalid JSON in {label}: expected object")
    return loaded


def _load_manifest(round_dir: Path, rel_path: str, errors: list[str]) -> dict[str, Any] | None:
    manifest_rel = MANIFEST_REL.as_posix()
    try:
        manifest = load_manifest(round_dir / MANIFEST_REL)
    except json.JSONDecodeError as exc:
        errors.append(f"{rel_path}: invalid JSON in {manifest_rel}: {exc.msg}")
        return None
    if not manifest:
        errors.append(f"{rel_path}: missing required review manifest: {manifest_rel}")
        return None
    return manifest
