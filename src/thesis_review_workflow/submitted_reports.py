"""Submitted report capture and validation contracts."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from thesis_review_workflow.artifact_validation import sha256_file
from thesis_review_workflow.paths import is_safe_round_relative_path
from thesis_review_workflow.supervisor_report import (
    SUPERVISOR_REPORT_CONFIRMATION_REL,
    SUPERVISOR_REPORT_REVIEWED_REL,
    SUPERVISOR_REPORT_SUBMITTED_PDF_REL,
    SUPERVISOR_REPORT_SUBMITTED_RECORD_REL,
    SUPERVISOR_REPORT_SUBMITTED_TEXT_REL,
    confirmation_grade_points,
    extract_markdown_grade_points,
    public_report_text,
)

SUBMITTED_REPORT_SCHEMA = "submitted-report-v1"
REPORT_KIND_SUPERVISOR = "supervisor_report"
SUPPORTED_REPORT_KINDS = {REPORT_KIND_SUPERVISOR}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_report_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


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


def copy_submitted_pdf(source: Path, round_dir: Path, *, force: bool = False) -> str:
    if not source.is_file():
        raise ValueError(f"submitted PDF path is not a file: {source}")
    if source.suffix.casefold() != ".pdf":
        raise ValueError("--pdf must point to a .pdf file")
    target = round_dir / SUPERVISOR_REPORT_SUBMITTED_PDF_REL
    if target.exists() and not force:
        raise ValueError(
            f"refusing to overwrite existing submitted PDF without --force: {SUPERVISOR_REPORT_SUBMITTED_PDF_REL}"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != target.resolve():
        shutil.copy2(source, target)
    return SUPERVISOR_REPORT_SUBMITTED_PDF_REL


def copy_or_extract_public_text(
    *,
    pdf_path: Path,
    round_dir: Path,
    public_text_file: Path | None,
    force: bool = False,
    pdftotext_command: str = "pdftotext",
) -> str:
    target = round_dir / SUPERVISOR_REPORT_SUBMITTED_TEXT_REL
    if target.exists() and not force:
        raise ValueError(
            f"refusing to overwrite existing submitted public text without --force: "
            f"{SUPERVISOR_REPORT_SUBMITTED_TEXT_REL}"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    if public_text_file is not None:
        if not public_text_file.is_file():
            raise ValueError(f"submitted public text path is not a file: {public_text_file}")
        shutil.copy2(public_text_file, target)
        return SUPERVISOR_REPORT_SUBMITTED_TEXT_REL
    completed = subprocess.run(
        [pdftotext_command, "-layout", str(pdf_path), str(target)],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        target.unlink(missing_ok=True)
        detail = completed.stderr.strip() or completed.stdout.strip() or f"{pdftotext_command} failed"
        raise ValueError(
            "could not extract submitted PDF text; install pdftotext or pass --public-text-file. " f"Details: {detail}"
        )
    return SUPERVISOR_REPORT_SUBMITTED_TEXT_REL


def build_supervisor_submitted_report_payload(
    round_dir: Path,
    *,
    case_id: str,
    round_id: str,
    submitted_at: str,
    recorded_by: str,
    pdf_rel: str = SUPERVISOR_REPORT_SUBMITTED_PDF_REL,
    public_text_rel: str = SUPERVISOR_REPORT_SUBMITTED_TEXT_REL,
) -> dict[str, Any]:
    if not recorded_by.strip():
        raise ValueError("--recorded-by is required for submitted report records")
    reviewed_path = round_dir / SUPERVISOR_REPORT_REVIEWED_REL
    confirmation_path = round_dir / SUPERVISOR_REPORT_CONFIRMATION_REL
    pdf_path = round_dir / pdf_rel
    public_text_path = round_dir / public_text_rel
    if not reviewed_path.is_file():
        raise ValueError(f"missing reviewed supervisor report: {SUPERVISOR_REPORT_REVIEWED_REL}")
    if not confirmation_path.is_file():
        raise ValueError(f"missing supervisor confirmation: {SUPERVISOR_REPORT_CONFIRMATION_REL}")
    if not pdf_path.is_file():
        raise ValueError(f"missing submitted PDF copy: {pdf_rel}")
    if not public_text_path.is_file():
        raise ValueError(f"missing submitted public text: {public_text_rel}")

    reviewed_text = reviewed_path.read_text(encoding="utf-8")
    submitted_text = public_text_path.read_text(encoding="utf-8")
    reviewed_public = public_report_text(reviewed_text)
    reviewed_grade_points = extract_markdown_grade_points(reviewed_text, require=True)
    submitted_grade_points = extract_markdown_grade_points(submitted_text, require=True)
    confirmation = load_json_object(confirmation_path, SUPERVISOR_REPORT_CONFIRMATION_REL)
    confirmation_values = confirmation_grade_points(confirmation)
    normalized_reviewed = normalize_report_text(reviewed_public)
    normalized_submitted = normalize_report_text(submitted_text)
    return {
        "schema_version": SUBMITTED_REPORT_SCHEMA,
        "case_id": case_id,
        "round_id": round_id,
        "generated_at": submitted_at,
        "producer_type": "human",
        "producer_role": "record-submitted-supervisor-report",
        "producer_agent": None,
        "recorded_by": recorded_by.strip(),
        "human_reviewer_note": "Operator recorded the submitted supervisor report PDF and public text.",
        "report_kind": REPORT_KIND_SUPERVISOR,
        "supported_report_kinds": sorted(SUPPORTED_REPORT_KINDS),
        "source_refs": [
            SUPERVISOR_REPORT_REVIEWED_REL,
            SUPERVISOR_REPORT_CONFIRMATION_REL,
            pdf_rel,
            public_text_rel,
        ],
        "limitations": [],
        "submitted_pdf_path": pdf_rel,
        "submitted_pdf_sha256": sha256_file(pdf_path),
        "submitted_public_text_path": public_text_rel,
        "submitted_public_text_sha256": sha256_file(public_text_path),
        "submitted_public_text_normalized_sha256": sha256_text(normalized_submitted),
        "reviewed_report_path": SUPERVISOR_REPORT_REVIEWED_REL,
        "reviewed_report_sha256": sha256_file(reviewed_path),
        "reviewed_public_text_sha256": sha256_text(reviewed_public),
        "reviewed_public_text_normalized_sha256": sha256_text(normalized_reviewed),
        "supervisor_confirmation_path": SUPERVISOR_REPORT_CONFIRMATION_REL,
        "supervisor_confirmation_sha256": sha256_file(confirmation_path),
        "grade": submitted_grade_points.grade,
        "points": submitted_grade_points.points,
        "reviewed_grade": reviewed_grade_points.grade,
        "reviewed_points": reviewed_grade_points.points,
        "confirmed_grade": confirmation_values.grade,
        "confirmed_points": confirmation_values.points,
        "public_text_normalized_match": normalized_submitted == normalized_reviewed,
        "ready_for_archive": (
            normalized_submitted == normalized_reviewed
            and submitted_grade_points.grade == reviewed_grade_points.grade == confirmation_values.grade
            and submitted_grade_points.points == reviewed_grade_points.points == confirmation_values.points
        ),
    }


def validate_submitted_report_record(
    loaded: Any,
    *,
    round_dir: Path,
    case_id: str | None = None,
    round_id: str | None = None,
    rel_path: str = SUPERVISOR_REPORT_SUBMITTED_RECORD_REL,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(loaded, dict):
        return [f"{rel_path}: submitted report record must be an object"]
    if loaded.get("schema_version") != SUBMITTED_REPORT_SCHEMA:
        errors.append(f"{rel_path}: schema_version must be {SUBMITTED_REPORT_SCHEMA}")
    if case_id is not None and loaded.get("case_id") != case_id:
        errors.append(f"{rel_path}: case_id does not match requested case")
    if round_id is not None and loaded.get("round_id") != round_id:
        errors.append(f"{rel_path}: round_id does not match requested round")
    if loaded.get("report_kind") != REPORT_KIND_SUPERVISOR:
        errors.append(f"{rel_path}: report_kind must be {REPORT_KIND_SUPERVISOR}")
    submitted_pdf_path = _validate_hash_bound_path(
        loaded, rel_path, round_dir, "submitted_pdf_path", "submitted_pdf_sha256", errors
    )
    submitted_text_path = _validate_hash_bound_path(
        loaded, rel_path, round_dir, "submitted_public_text_path", "submitted_public_text_sha256", errors
    )
    reviewed_path = _validate_hash_bound_path(
        loaded, rel_path, round_dir, "reviewed_report_path", "reviewed_report_sha256", errors
    )
    confirmation_path = _validate_hash_bound_path(
        loaded, rel_path, round_dir, "supervisor_confirmation_path", "supervisor_confirmation_sha256", errors
    )
    if submitted_pdf_path is not None and submitted_pdf_path.suffix.casefold() != ".pdf":
        errors.append(f"{rel_path}: submitted_pdf_path must point to a PDF")
    if loaded.get("reviewed_report_path") != SUPERVISOR_REPORT_REVIEWED_REL:
        errors.append(f"{rel_path}: reviewed_report_path must be {SUPERVISOR_REPORT_REVIEWED_REL}")
    if loaded.get("supervisor_confirmation_path") != SUPERVISOR_REPORT_CONFIRMATION_REL:
        errors.append(f"{rel_path}: supervisor_confirmation_path must be {SUPERVISOR_REPORT_CONFIRMATION_REL}")
    if not isinstance(loaded.get("recorded_by"), str) or not str(loaded.get("recorded_by")).strip():
        errors.append(f"{rel_path}: recorded_by must be a non-empty string")
    if submitted_text_path is not None and reviewed_path is not None and confirmation_path is not None:
        _validate_recomputed_submitted_report_state(
            loaded,
            rel_path,
            submitted_text_path=submitted_text_path,
            reviewed_path=reviewed_path,
            confirmation_path=confirmation_path,
            errors=errors,
        )
    if loaded.get("public_text_normalized_match") is not True:
        errors.append(f"{rel_path}: submitted public text does not match reviewed public report text")
    if loaded.get("ready_for_archive") is not True:
        errors.append(f"{rel_path}: ready_for_archive must be true")
    if loaded.get("grade") != loaded.get("reviewed_grade") or loaded.get("grade") != loaded.get("confirmed_grade"):
        errors.append(f"{rel_path}: submitted, reviewed, and confirmed grades must match")
    if loaded.get("points") != loaded.get("reviewed_points") or loaded.get("points") != loaded.get("confirmed_points"):
        errors.append(f"{rel_path}: submitted, reviewed, and confirmed points must match")
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
    recorded = loaded.get(hash_field)
    if not isinstance(recorded, str) or recorded != sha256_file(path):
        errors.append(f"{rel_path}: {hash_field} is stale for {path_value}")
        return None
    return path


def _validate_recomputed_submitted_report_state(
    loaded: dict[str, Any],
    rel_path: str,
    *,
    submitted_text_path: Path,
    reviewed_path: Path,
    confirmation_path: Path,
    errors: list[str],
) -> None:
    submitted_text = submitted_text_path.read_text(encoding="utf-8")
    reviewed_text = reviewed_path.read_text(encoding="utf-8")
    try:
        confirmation = load_json_object(confirmation_path, f"{rel_path}: supervisor confirmation")
    except ValueError as exc:
        errors.append(str(exc))
        return
    reviewed_public = public_report_text(reviewed_text)
    normalized_submitted = normalize_report_text(submitted_text)
    normalized_reviewed = normalize_report_text(reviewed_public)
    submitted_grade_points = extract_markdown_grade_points(submitted_text, require=True)
    reviewed_grade_points = extract_markdown_grade_points(reviewed_text, require=True)
    confirmation_values = confirmation_grade_points(confirmation)
    errors.extend(f"{rel_path}: submitted public text {error}" for error in submitted_grade_points.errors)
    errors.extend(f"{rel_path}: reviewed report {error}" for error in reviewed_grade_points.errors)
    if loaded.get("submitted_public_text_normalized_sha256") != sha256_text(normalized_submitted):
        errors.append(f"{rel_path}: submitted_public_text_normalized_sha256 is stale")
    if loaded.get("reviewed_public_text_normalized_sha256") != sha256_text(normalized_reviewed):
        errors.append(f"{rel_path}: reviewed_public_text_normalized_sha256 is stale")
    if loaded.get("reviewed_public_text_sha256") != sha256_text(reviewed_public):
        errors.append(f"{rel_path}: reviewed_public_text_sha256 is stale")
    if loaded.get("public_text_normalized_match") != (normalized_submitted == normalized_reviewed):
        errors.append(f"{rel_path}: public_text_normalized_match is stale")
    expected_ready = (
        normalized_submitted == normalized_reviewed
        and submitted_grade_points.grade == reviewed_grade_points.grade == confirmation_values.grade
        and submitted_grade_points.points == reviewed_grade_points.points == confirmation_values.points
    )
    if loaded.get("ready_for_archive") != expected_ready:
        errors.append(f"{rel_path}: ready_for_archive is stale")
    for field, expected in (
        ("grade", submitted_grade_points.grade),
        ("points", submitted_grade_points.points),
        ("reviewed_grade", reviewed_grade_points.grade),
        ("reviewed_points", reviewed_grade_points.points),
        ("confirmed_grade", confirmation_values.grade),
        ("confirmed_points", confirmation_values.points),
    ):
        if loaded.get(field) != expected:
            errors.append(f"{rel_path}: {field} is stale")
