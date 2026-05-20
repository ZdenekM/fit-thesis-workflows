"""Submitted report public-form delta records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from thesis_review_workflow.artifact_validation import sha256_file
from thesis_review_workflow.paths import is_safe_round_relative_path
from thesis_review_workflow.submitted_reports import (
    OPPONENT_REPORT_APPROVAL_REL,
    OPPONENT_REPORT_CLEAN_REL,
    OPPONENT_REPORT_DELTAS_REL,
    OPPONENT_REPORT_SUBMITTED_PDF_REL,
    OPPONENT_REPORT_SUBMITTED_RECORD_REL,
    OPPONENT_REPORT_SUBMITTED_TEXT_REL,
    REPORT_KIND_OPPONENT,
    load_opponent_approval,
    normalize_report_text,
    opponent_public_report_text,
    opponent_public_section_diffs,
    opponent_report_field_values_match,
    opponent_report_values,
    sha256_text,
    validate_submitted_opponent_report_record,
)

SUBMITTED_REPORT_DELTAS_SCHEMA = "submitted-report-deltas-v1"
SUBMITTED_REPORT_DELTA_CLASSIFICATIONS = {
    "formatting_only",
    "is_renderer_wrapping",
    "operator_wording_non_material",
    "material_change",
}
NON_MATERIAL_SUBMITTED_REPORT_DELTA_CLASSIFICATIONS = {
    "formatting_only",
    "is_renderer_wrapping",
    "operator_wording_non_material",
}


def is_submitted_report_delta_artifact(rel_path: str) -> bool:
    return rel_path == OPPONENT_REPORT_DELTAS_REL


def _field_values_match(clean_text: str, submitted_text: str) -> tuple[bool, list[str]]:
    clean_values, clean_errors = opponent_report_values(clean_text, require_private_comment=True)
    submitted_values, submitted_errors = opponent_report_values(submitted_text, require_private_comment=False)
    errors = [f"reviewed report {error}" for error in clean_errors]
    errors.extend(f"submitted public text {error}" for error in submitted_errors)
    if errors:
        return False, errors
    return opponent_report_field_values_match(clean_values, submitted_values), []


def build_opponent_submitted_report_delta_payload(
    round_dir: Path,
    *,
    case_id: str,
    round_id: str,
    generated_at: str,
    recorded_by: str,
    sections: list[str],
    classification: str,
    rationale: str,
    pdf_rel: str = OPPONENT_REPORT_SUBMITTED_PDF_REL,
    public_text_rel: str = OPPONENT_REPORT_SUBMITTED_TEXT_REL,
) -> dict[str, Any]:
    if classification not in SUBMITTED_REPORT_DELTA_CLASSIFICATIONS:
        raise ValueError("--classification must be one of " + ", ".join(sorted(SUBMITTED_REPORT_DELTA_CLASSIFICATIONS)))
    if not recorded_by.strip():
        raise ValueError("--recorded-by is required for submitted-report deltas")
    if not rationale.strip():
        raise ValueError("--rationale is required for submitted-report deltas")
    requested_sections = [section.strip() for section in sections if section.strip()]
    if not requested_sections:
        raise ValueError("at least one --section is required")
    for rel_path in (
        OPPONENT_REPORT_CLEAN_REL,
        pdf_rel,
        public_text_rel,
        OPPONENT_REPORT_APPROVAL_REL,
        OPPONENT_REPORT_SUBMITTED_RECORD_REL,
    ):
        if not (round_dir / rel_path).is_file():
            raise ValueError(f"missing required artifact: {rel_path}")
    submitted_record_path = round_dir / OPPONENT_REPORT_SUBMITTED_RECORD_REL
    try:
        submitted_record = json.loads(submitted_record_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{OPPONENT_REPORT_SUBMITTED_RECORD_REL}: invalid JSON: {exc.msg}") from exc
    record_errors = validate_submitted_opponent_report_record(
        submitted_record,
        round_dir=round_dir,
        case_id=case_id,
        round_id=round_id,
        rel_path=OPPONENT_REPORT_SUBMITTED_RECORD_REL,
        require_archive_ready=False,
    )
    if record_errors:
        raise ValueError("; ".join(record_errors))
    approval = load_opponent_approval(round_dir)
    clean_path = round_dir / OPPONENT_REPORT_CLEAN_REL
    public_text_path = round_dir / public_text_rel
    clean_text = clean_path.read_text(encoding="utf-8")
    submitted_text = public_text_path.read_text(encoding="utf-8")
    reviewed_public = opponent_public_report_text(clean_text)
    current_diffs = opponent_public_section_diffs(reviewed_public, submitted_text)
    if not current_diffs:
        raise ValueError("submitted public text already matches the reviewed public projection")
    diffs_by_section = {str(diff["section"]): diff for diff in current_diffs}
    missing = [section for section in requested_sections if section not in diffs_by_section]
    if missing:
        raise ValueError("section has no current submitted-report diff: " + ", ".join(missing))
    field_values_match, field_errors = _field_values_match(clean_text, submitted_text)
    if field_errors:
        raise ValueError("; ".join(field_errors))
    materiality = (
        "non_material" if classification in NON_MATERIAL_SUBMITTED_REPORT_DELTA_CLASSIFICATIONS else "material"
    )
    selected_diffs = [
        {
            **diffs_by_section[section],
            "classification": classification,
            "materiality": materiality,
            "rationale": rationale.strip(),
            "accepted_by": recorded_by.strip(),
        }
        for section in requested_sections
    ]
    all_diffs_classified = set(diffs_by_section) == set(requested_sections)
    calibration_controls_match = submitted_record.get("report_calibration_controls_match", True) is True
    ready_with_deltas = (
        field_values_match and calibration_controls_match and all_diffs_classified and materiality == "non_material"
    )
    return {
        "schema_version": SUBMITTED_REPORT_DELTAS_SCHEMA,
        "case_id": case_id,
        "round_id": round_id,
        "generated_at": generated_at,
        "producer_type": "human",
        "producer_role": "record-submitted-report-delta",
        "producer_agent": None,
        "recorded_by": recorded_by.strip(),
        "human_reviewer_note": "Operator classified submitted opponent-report public-form differences.",
        "report_kind": REPORT_KIND_OPPONENT,
        "source_refs": [
            OPPONENT_REPORT_CLEAN_REL,
            pdf_rel,
            public_text_rel,
            OPPONENT_REPORT_APPROVAL_REL,
            OPPONENT_REPORT_SUBMITTED_RECORD_REL,
        ],
        "limitations": [],
        "submitted_record_path": OPPONENT_REPORT_SUBMITTED_RECORD_REL,
        "submitted_record_sha256": sha256_file(submitted_record_path),
        "reviewed_basis_path": OPPONENT_REPORT_CLEAN_REL,
        "reviewed_basis_sha256": sha256_file(clean_path),
        "reviewed_public_projection_sha256": sha256_text(reviewed_public),
        "submitted_pdf_path": pdf_rel,
        "submitted_pdf_sha256": sha256_file(round_dir / pdf_rel),
        "submitted_public_text_path": public_text_rel,
        "submitted_public_text_sha256": sha256_file(public_text_path),
        "submitted_public_text_normalized_sha256": sha256_text(normalize_report_text(submitted_text)),
        "approval_record_path": OPPONENT_REPORT_APPROVAL_REL,
        "approval_record_sha256": sha256_file(round_dir / OPPONENT_REPORT_APPROVAL_REL),
        "approval_reviewed_artifact_sha256": approval["reviewed_artifact_sha256"],
        "approval_review_basis_sha256": approval["review_basis_sha256"],
        "current_public_text_diffs": current_diffs,
        "deltas": selected_diffs,
        "delta_count": len(selected_diffs),
        "current_public_text_diff_count": len(current_diffs),
        "all_current_public_text_diffs_classified": all_diffs_classified,
        "field_values_match": field_values_match,
        "report_calibration_controls_match": calibration_controls_match,
        "ready_for_archive_with_deltas": ready_with_deltas,
    }


def validate_opponent_submitted_report_deltas(
    loaded: Any,
    *,
    round_dir: Path,
    case_id: str | None = None,
    round_id: str | None = None,
    rel_path: str = OPPONENT_REPORT_DELTAS_REL,
    submitted_record: dict[str, Any] | None = None,
    require_archive_ready: bool = True,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(loaded, dict):
        return [f"{rel_path}: submitted report deltas must be an object"]
    if loaded.get("schema_version") != SUBMITTED_REPORT_DELTAS_SCHEMA:
        errors.append(f"{rel_path}: schema_version must be {SUBMITTED_REPORT_DELTAS_SCHEMA}")
    if case_id is not None and loaded.get("case_id") != case_id:
        errors.append(f"{rel_path}: case_id does not match requested case")
    if round_id is not None and loaded.get("round_id") != round_id:
        errors.append(f"{rel_path}: round_id does not match requested round")
    if loaded.get("report_kind") != REPORT_KIND_OPPONENT:
        errors.append(f"{rel_path}: report_kind must be {REPORT_KIND_OPPONENT}")
    if not isinstance(loaded.get("recorded_by"), str) or not str(loaded.get("recorded_by")).strip():
        errors.append(f"{rel_path}: recorded_by must be a non-empty string")

    submitted_record_path = _validate_hash_bound_path(
        loaded, rel_path, round_dir, "submitted_record_path", "submitted_record_sha256", errors
    )
    clean_path = _validate_hash_bound_path(
        loaded, rel_path, round_dir, "reviewed_basis_path", "reviewed_basis_sha256", errors
    )
    submitted_text_path = _validate_hash_bound_path(
        loaded, rel_path, round_dir, "submitted_public_text_path", "submitted_public_text_sha256", errors
    )
    _validate_hash_bound_path(loaded, rel_path, round_dir, "submitted_pdf_path", "submitted_pdf_sha256", errors)
    approval_path = _validate_hash_bound_path(
        loaded, rel_path, round_dir, "approval_record_path", "approval_record_sha256", errors
    )
    if loaded.get("reviewed_basis_path") != OPPONENT_REPORT_CLEAN_REL:
        errors.append(f"{rel_path}: reviewed_basis_path must be {OPPONENT_REPORT_CLEAN_REL}")
    if loaded.get("submitted_record_path") != OPPONENT_REPORT_SUBMITTED_RECORD_REL:
        errors.append(f"{rel_path}: submitted_record_path must be {OPPONENT_REPORT_SUBMITTED_RECORD_REL}")
    if loaded.get("approval_record_path") != OPPONENT_REPORT_APPROVAL_REL:
        errors.append(f"{rel_path}: approval_record_path must be {OPPONENT_REPORT_APPROVAL_REL}")
    if (
        submitted_record_path is not None
        and clean_path is not None
        and submitted_text_path is not None
        and approval_path is not None
    ):
        _validate_recomputed_deltas(
            loaded,
            rel_path,
            round_dir=round_dir,
            submitted_record_path=submitted_record_path,
            clean_path=clean_path,
            submitted_text_path=submitted_text_path,
            approval_path=approval_path,
            errors=errors,
            case_id=case_id,
            round_id=round_id,
            submitted_record=submitted_record,
            require_archive_ready=require_archive_ready,
        )
    if require_archive_ready and loaded.get("ready_for_archive_with_deltas") is not True:
        errors.append(f"{rel_path}: ready_for_archive_with_deltas must be true")
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


def _validate_recomputed_deltas(
    loaded: dict[str, Any],
    rel_path: str,
    *,
    round_dir: Path,
    submitted_record_path: Path,
    clean_path: Path,
    submitted_text_path: Path,
    approval_path: Path,
    errors: list[str],
    case_id: str | None,
    round_id: str | None,
    submitted_record: dict[str, Any] | None,
    require_archive_ready: bool,
) -> None:
    if submitted_record is None:
        try:
            loaded_record = json.loads(submitted_record_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{rel_path}: submitted record invalid JSON: {exc.msg}")
            return
        if isinstance(loaded_record, dict):
            submitted_record = loaded_record
        else:
            errors.append(f"{rel_path}: submitted record must be an object")
            return
    record_errors = validate_submitted_opponent_report_record(
        submitted_record,
        round_dir=round_dir,
        case_id=case_id,
        round_id=round_id,
        rel_path=OPPONENT_REPORT_SUBMITTED_RECORD_REL,
        require_archive_ready=False,
    )
    errors.extend(f"{rel_path}: submitted record {error}" for error in record_errors)
    clean_text = clean_path.read_text(encoding="utf-8")
    submitted_text = submitted_text_path.read_text(encoding="utf-8")
    reviewed_public = opponent_public_report_text(clean_text)
    current_diffs = opponent_public_section_diffs(reviewed_public, submitted_text)
    field_values_match, field_errors = _field_values_match(clean_text, submitted_text)
    errors.extend(f"{rel_path}: {error}" for error in field_errors)
    try:
        approval = load_opponent_approval(round_dir)
    except ValueError as exc:
        errors.append(f"{rel_path}: {exc}")
        return

    expected_values = {
        "submitted_record_sha256": sha256_file(submitted_record_path),
        "reviewed_public_projection_sha256": sha256_text(reviewed_public),
        "submitted_public_text_normalized_sha256": sha256_text(normalize_report_text(submitted_text)),
        "approval_record_sha256": sha256_file(approval_path),
        "approval_reviewed_artifact_sha256": approval["reviewed_artifact_sha256"],
        "approval_review_basis_sha256": approval["review_basis_sha256"],
        "current_public_text_diffs": current_diffs,
        "current_public_text_diff_count": len(current_diffs),
        "field_values_match": field_values_match,
        "report_calibration_controls_match": submitted_record.get("report_calibration_controls_match", True) is True,
    }
    for field, expected in expected_values.items():
        if loaded.get(field) != expected:
            errors.append(f"{rel_path}: {field} is stale")
    submitted_record_bindings = {
        "submitted_pdf_path": submitted_record.get("submitted_pdf_path"),
        "submitted_pdf_sha256": submitted_record.get("submitted_pdf_sha256"),
        "submitted_public_text_path": submitted_record.get("submitted_public_text_path"),
        "submitted_public_text_sha256": submitted_record.get("submitted_public_text_sha256"),
        "reviewed_basis_path": submitted_record.get("reviewed_report_path"),
        "reviewed_basis_sha256": submitted_record.get("reviewed_report_sha256"),
        "approval_record_path": submitted_record.get("approval_record_path"),
        "approval_record_sha256": submitted_record.get("approval_record_sha256"),
        "current_public_text_diffs": submitted_record.get("public_text_section_diffs"),
        "field_values_match": submitted_record.get("field_values_match"),
    }
    for field, expected in submitted_record_bindings.items():
        if loaded.get(field) != expected:
            errors.append(f"{rel_path}: {field} is not bound to the submitted report record")

    deltas = loaded.get("deltas")
    if not isinstance(deltas, list) or not deltas:
        errors.append(f"{rel_path}: deltas must be a non-empty list")
        return
    current_by_section = {diff["section"]: diff for diff in current_diffs}
    selected_sections: list[str] = []
    material_delta = False
    for index, delta in enumerate(deltas, start=1):
        if not isinstance(delta, dict):
            errors.append(f"{rel_path}: deltas item {index} must be an object")
            continue
        section = delta.get("section")
        if not isinstance(section, str) or section not in current_by_section:
            errors.append(f"{rel_path}: deltas item {index} section must name a current public-text diff")
            continue
        selected_sections.append(section)
        current = current_by_section[section]
        for field in ("normalized_before", "normalized_after", "before_sha256", "after_sha256"):
            if delta.get(field) != current[field]:
                errors.append(f"{rel_path}: deltas item {index} {field} is stale")
        classification = delta.get("classification")
        if classification not in SUBMITTED_REPORT_DELTA_CLASSIFICATIONS:
            errors.append(
                f"{rel_path}: deltas item {index} classification must be one of "
                + ", ".join(sorted(SUBMITTED_REPORT_DELTA_CLASSIFICATIONS))
            )
        expected_materiality = (
            "non_material" if classification in NON_MATERIAL_SUBMITTED_REPORT_DELTA_CLASSIFICATIONS else "material"
        )
        if delta.get("materiality") != expected_materiality:
            errors.append(f"{rel_path}: deltas item {index} materiality is stale")
        if expected_materiality == "material":
            material_delta = True
        if not isinstance(delta.get("rationale"), str) or not str(delta.get("rationale")).strip():
            errors.append(f"{rel_path}: deltas item {index} rationale must be a non-empty string")
        if not isinstance(delta.get("accepted_by"), str) or not str(delta.get("accepted_by")).strip():
            errors.append(f"{rel_path}: deltas item {index} accepted_by must be a non-empty string")

    all_classified = set(selected_sections) == set(current_by_section)
    if loaded.get("delta_count") != len(deltas):
        errors.append(f"{rel_path}: delta_count is stale")
    if loaded.get("all_current_public_text_diffs_classified") != all_classified:
        errors.append(f"{rel_path}: all_current_public_text_diffs_classified is stale")
    calibration_controls_match = submitted_record.get("report_calibration_controls_match", True) is True
    expected_ready = field_values_match and calibration_controls_match and all_classified and not material_delta
    if loaded.get("ready_for_archive_with_deltas") != expected_ready:
        errors.append(f"{rel_path}: ready_for_archive_with_deltas is stale")
    if require_archive_ready and material_delta:
        errors.append(f"{rel_path}: material submitted-report delta reopens opponent report review")
    if require_archive_ready and not calibration_controls_match:
        errors.append(f"{rel_path}: report calibration drift reopens opponent report review")


def load_opponent_submitted_report_deltas(round_dir: Path) -> dict[str, Any]:
    path = round_dir / OPPONENT_REPORT_DELTAS_REL
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing submitted-report delta artifact: {OPPONENT_REPORT_DELTAS_REL}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"{OPPONENT_REPORT_DELTAS_REL}: invalid JSON: {exc.msg}") from exc
    if not isinstance(loaded, dict):
        raise ValueError(f"{OPPONENT_REPORT_DELTAS_REL}: submitted report deltas must be an object")
    return loaded
