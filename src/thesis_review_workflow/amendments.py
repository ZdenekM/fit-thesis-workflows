"""Bounded post-review report amendment records."""

from __future__ import annotations

import difflib
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

from thesis_review_workflow.artifact_validation import sha256_file
from thesis_review_workflow.paths import is_safe_round_relative_path
from thesis_review_workflow.review_approvals import validate_review_approval_with_manifest
from thesis_review_workflow.review_manifest import MANIFEST_REL, load_manifest
from thesis_review_workflow.supervisor_report import (
    SUPERVISOR_REPORT_AMENDMENTS_DIR_REL,
    SUPERVISOR_REPORT_CONFIRMATION_REL,
    SUPERVISOR_REPORT_REVIEW_REL,
    SUPERVISOR_REPORT_REVIEWED_REL,
    confirmation_grade_points,
    extract_markdown_grade_points,
    private_student_comment_text,
    public_report_text,
    strip_metadata_comments,
)

REPORT_AMENDMENT_SCHEMA = "report-amendment-v1"
AMENDMENT_TYPES = {"style_only", "public_text_delta", "private_comment_delta", "material_claim_delta"}
NON_MATERIAL_AMENDMENT_TYPES = {"style_only", "public_text_delta", "private_comment_delta"}
MAX_DIFF_LINES = 160


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def amendment_record_rel(amended_at: str, amendment_type: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", amended_at).strip("-") or "amendment"
    return f"{SUPERVISOR_REPORT_AMENDMENTS_DIR_REL}/{slug}-{amendment_type}.json"


def amendment_snapshot_rel(amended_at: str, amendment_type: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", amended_at).strip("-") or "amendment"
    return f"{SUPERVISOR_REPORT_AMENDMENTS_DIR_REL}/{slug}-{amendment_type}-before.md"


def copy_previous_snapshot(source: Path, round_dir: Path, rel_path: str, *, force: bool = False) -> str:
    if not source.is_file():
        raise ValueError(f"previous report snapshot is not a file: {source}")
    target = round_dir / rel_path
    if target.exists() and not force:
        raise ValueError(f"refusing to overwrite existing amendment snapshot without --force: {rel_path}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != target.resolve():
        shutil.copy2(source, target)
    return rel_path


def diff_lines(previous_text: str, current_text: str) -> list[str]:
    lines = list(
        difflib.unified_diff(
            previous_text.splitlines(),
            current_text.splitlines(),
            fromfile="previous",
            tofile="current",
            lineterm="",
        )
    )
    if len(lines) > MAX_DIFF_LINES:
        return [*lines[:MAX_DIFF_LINES], f"... truncated after {MAX_DIFF_LINES} diff lines"]
    return lines


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
    if amendment_type not in AMENDMENT_TYPES:
        raise ValueError(f"amendment_type must be one of {', '.join(sorted(AMENDMENT_TYPES))}")
    if amendment_type == "material_claim_delta":
        raise ValueError("material_claim_delta requires normal semantic review; do not record a bounded amendment")
    if not approved_by.strip():
        raise ValueError("--approved-by is required for bounded report amendments")
    if not rationale.strip():
        raise ValueError("--rationale is required for bounded report amendments")
    if not is_safe_round_relative_path(previous_snapshot_rel) or not is_safe_round_relative_path(current_artifact_rel):
        raise ValueError("amendment paths must be safe round-relative paths")
    previous_path = round_dir / previous_snapshot_rel
    current_path = round_dir / current_artifact_rel
    if not previous_path.is_file():
        raise ValueError(f"missing previous amendment snapshot: {previous_snapshot_rel}")
    if not current_path.is_file():
        raise ValueError(f"missing current report artifact: {current_artifact_rel}")
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
    approval = load_json_object(round_dir / SUPERVISOR_REPORT_REVIEW_REL, SUPERVISOR_REPORT_REVIEW_REL)
    payload = {
        "schema_version": REPORT_AMENDMENT_SCHEMA,
        "case_id": case_id,
        "round_id": round_id,
        "generated_at": amended_at,
        "producer_type": "human",
        "producer_role": "record-report-amendment",
        "producer_agent": None,
        "human_reviewer_note": rationale.strip(),
        "report_kind": "supervisor_report",
        "amendment_type": amendment_type,
        "approval_status": "delta_approved",
        "approved_by": approved_by.strip(),
        "approved_at": amended_at,
        "requires_semantic_review": False,
        "previous_snapshot_path": previous_snapshot_rel,
        "previous_snapshot_sha256": sha256_file(previous_path),
        "current_artifact_path": current_artifact_rel,
        "current_artifact_sha256": sha256_file(current_path),
        "supervisor_confirmation_path": SUPERVISOR_REPORT_CONFIRMATION_REL,
        "supervisor_confirmation_sha256": sha256_file(round_dir / SUPERVISOR_REPORT_CONFIRMATION_REL),
        "review_approval_path": SUPERVISOR_REPORT_REVIEW_REL,
        "review_approval_sha256": sha256_file(round_dir / SUPERVISOR_REPORT_REVIEW_REL),
        "review_approval_reviewed_artifact_sha256": approval.get("reviewed_artifact_sha256"),
        "fresh_approval_artifact_sha256": sha256_file(current_path),
        "source_refs": [
            previous_snapshot_rel,
            current_artifact_rel,
            SUPERVISOR_REPORT_CONFIRMATION_REL,
            SUPERVISOR_REPORT_REVIEW_REL,
        ],
        "limitations": [],
        "grade_changed": (previous_grade_points.grade, previous_grade_points.points)
        != (current_grade_points.grade, current_grade_points.points),
        "evidence_anchor_changed": _metadata_fingerprint(previous_text) != _metadata_fingerprint(current_text),
        "public_text_changed": normalize_text(previous_public) != normalize_text(current_public),
        "private_comment_changed": normalize_text(previous_private) != normalize_text(current_private),
        "normalized_visible_text_changed": normalize_text(previous_visible) != normalize_text(current_visible),
        "previous_public_text_normalized_sha256": sha256_text(normalize_text(previous_public)),
        "current_public_text_normalized_sha256": sha256_text(normalize_text(current_public)),
        "confirmed_grade": confirmation_grade_points(confirmation).grade,
        "confirmed_points": confirmation_grade_points(confirmation).points,
        "compact_diff": diff_lines(previous_text, current_text),
    }
    errors = validate_report_amendment_record(payload, round_dir=round_dir)
    if errors:
        raise ValueError("\n".join(errors))
    return payload


def validate_report_amendment_record(
    loaded: Any,
    *,
    round_dir: Path,
    case_id: str | None = None,
    round_id: str | None = None,
    rel_path: str = "report amendment",
) -> list[str]:
    errors: list[str] = []
    if not isinstance(loaded, dict):
        return [f"{rel_path}: report amendment record must be an object"]
    if loaded.get("schema_version") != REPORT_AMENDMENT_SCHEMA:
        errors.append(f"{rel_path}: schema_version must be {REPORT_AMENDMENT_SCHEMA}")
    if case_id is not None and loaded.get("case_id") != case_id:
        errors.append(f"{rel_path}: case_id does not match requested case")
    if round_id is not None and loaded.get("round_id") != round_id:
        errors.append(f"{rel_path}: round_id does not match requested round")
    amendment_type = loaded.get("amendment_type")
    if amendment_type not in NON_MATERIAL_AMENDMENT_TYPES:
        errors.append(f"{rel_path}: amendment_type must be a non-material bounded type")
    previous_path = _validate_hash_bound_path(
        loaded, rel_path, round_dir, "previous_snapshot_path", "previous_snapshot_sha256", errors
    )
    current_path = _validate_hash_bound_path(
        loaded, rel_path, round_dir, "current_artifact_path", "current_artifact_sha256", errors
    )
    confirmation_path = _validate_hash_bound_path(
        loaded, rel_path, round_dir, "supervisor_confirmation_path", "supervisor_confirmation_sha256", errors
    )
    approval_path = _validate_hash_bound_path(
        loaded, rel_path, round_dir, "review_approval_path", "review_approval_sha256", errors
    )
    if previous_path is not None and current_path is not None and isinstance(amendment_type, str):
        _validate_recomputed_amendment_state(
            loaded,
            rel_path,
            amendment_type=amendment_type,
            previous_path=previous_path,
            current_path=current_path,
            confirmation_path=confirmation_path,
            approval_path=approval_path,
            errors=errors,
        )
    if loaded.get("approval_status") != "delta_approved":
        errors.append(f"{rel_path}: approval_status must be delta_approved")
    if loaded.get("requires_semantic_review") is not False:
        errors.append(f"{rel_path}: bounded amendment must not require semantic review")
    if loaded.get("supervisor_confirmation_path") != SUPERVISOR_REPORT_CONFIRMATION_REL:
        errors.append(f"{rel_path}: supervisor_confirmation_path must be {SUPERVISOR_REPORT_CONFIRMATION_REL}")
    if loaded.get("review_approval_path") != SUPERVISOR_REPORT_REVIEW_REL:
        errors.append(f"{rel_path}: review_approval_path must be {SUPERVISOR_REPORT_REVIEW_REL}")
    if not isinstance(loaded.get("approved_by"), str) or not str(loaded.get("approved_by")).strip():
        errors.append(f"{rel_path}: approved_by must be a non-empty string")
    if loaded.get("review_approval_path") == SUPERVISOR_REPORT_REVIEW_REL:
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
    if loaded.get("grade_changed") is True:
        errors.append(f"{rel_path}: grade or points changed; run normal semantic review")
    if loaded.get("evidence_anchor_changed") is True:
        errors.append(f"{rel_path}: evidence anchor metadata changed; run normal semantic review")
    if amendment_type == "style_only" and loaded.get("normalized_visible_text_changed") is True:
        errors.append(f"{rel_path}: style_only amendment cannot change normalized visible text")
    if amendment_type == "private_comment_delta" and loaded.get("public_text_changed") is True:
        errors.append(f"{rel_path}: private_comment_delta cannot change public report text")
    if amendment_type == "public_text_delta" and loaded.get("public_text_changed") is not True:
        errors.append(f"{rel_path}: public_text_delta must change public report text")
    if not isinstance(loaded.get("compact_diff"), list) or not loaded.get("compact_diff"):
        errors.append(f"{rel_path}: compact_diff must be a non-empty list")
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


def _validate_recomputed_amendment_state(
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
    expected = {
        "grade_changed": (previous_grade_points.grade, previous_grade_points.points)
        != (current_grade_points.grade, current_grade_points.points),
        "evidence_anchor_changed": _metadata_fingerprint(previous_text) != _metadata_fingerprint(current_text),
        "public_text_changed": normalize_text(previous_public) != normalize_text(current_public),
        "private_comment_changed": normalize_text(previous_private) != normalize_text(current_private),
        "normalized_visible_text_changed": normalize_text(previous_visible) != normalize_text(current_visible),
        "previous_public_text_normalized_sha256": sha256_text(normalize_text(previous_public)),
        "current_public_text_normalized_sha256": sha256_text(normalize_text(current_public)),
        "fresh_approval_artifact_sha256": sha256_file(current_path),
        "compact_diff": diff_lines(previous_text, current_text),
    }
    if confirmation is not None:
        confirmation_values = confirmation_grade_points(confirmation)
        expected["confirmed_grade"] = confirmation_values.grade
        expected["confirmed_points"] = confirmation_values.points
        if confirmation.get("reviewed_report_path") != loaded.get("current_artifact_path"):
            errors.append(f"{rel_path}: supervisor confirmation must target current_artifact_path")
        if confirmation.get("reviewed_report_sha256") != sha256_file(current_path):
            errors.append(f"{rel_path}: supervisor confirmation is stale for current artifact")
    if approval is not None:
        expected["review_approval_reviewed_artifact_sha256"] = approval.get("reviewed_artifact_sha256")
        if approval.get("reviewed_artifact_path") != loaded.get("current_artifact_path"):
            errors.append(f"{rel_path}: review approval must target current_artifact_path")
        if approval.get("reviewed_artifact_sha256") != sha256_file(current_path):
            errors.append(f"{rel_path}: review approval is stale for current artifact")
    for field, expected_value in expected.items():
        if loaded.get(field) != expected_value:
            errors.append(f"{rel_path}: {field} is stale")
    if expected["grade_changed"] is True:
        errors.append(f"{rel_path}: grade or points changed; run normal semantic review")
    if expected["evidence_anchor_changed"] is True:
        errors.append(f"{rel_path}: evidence anchor metadata changed; run normal semantic review")
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
