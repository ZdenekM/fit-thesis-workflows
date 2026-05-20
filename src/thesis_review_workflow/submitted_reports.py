"""Submitted report capture and validation contracts."""

from __future__ import annotations

import hashlib
import importlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from thesis_review_workflow.artifact_validation import sha256_file
from thesis_review_workflow.markdown_utils import section_text
from thesis_review_workflow.paths import is_safe_round_relative_path
from thesis_review_workflow.report_calibration import (
    REPORT_CALIBRATION_BASIS_REL,
    report_calibration_expected_controls,
    validate_report_calibration_artifact,
)
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
REPORT_KIND_OPPONENT = "opponent_report"
SUPPORTED_REPORT_KINDS = {REPORT_KIND_SUPERVISOR, REPORT_KIND_OPPONENT}

OPPONENT_REPORT_CLEAN_REL = "outputs/oponent_posudek_navrh.md"
OPPONENT_REPORT_REVIEW_REL = "outputs/feedback_k_posudku.md"
OPPONENT_REPORT_APPROVAL_REL = "work/reviews/opponent_report_review.json"
OPPONENT_REPORT_TRACE_REL = "work/opponent_report_trace.json"
OPPONENT_REPORT_SUBMITTED_RECORD_REL = "work/submitted_reports/opponent_report.json"
OPPONENT_REPORT_SUBMITTED_PDF_REL = "work/submitted_reports/opponent_report.pdf"
OPPONENT_REPORT_SUBMITTED_TEXT_REL = "extracted/submitted_reports/opponent_report.txt"
OPPONENT_REPORT_DELTAS_REL = "work/submitted_reports/opponent_report_deltas.json"
OPPONENT_REPORT_PRIVATE_HEADING = "## Komentář pro studenta (neveřejná část)"
OPPONENT_REPORT_IS_FORM_HEADING = "## IS formulář (výběry a body)"
OPPONENT_REPORT_QUESTIONS_HEADING = "## 10. Otázky k obhajobě"
OPPONENT_REPORT_POINTS_HEADING = "## 11. Body a známka"
OPPONENT_REPORT_PRIVATE_MIN_NONSPACE_CHARS = 80
OPPONENT_SELECT_FIELDS = {
    "Náročnost zadání": {
        "jednoduché zadání",
        "méně obtížné zadání",
        "průměrně obtížné zadání",
        "obtížnější zadání",
        "značně obtížné zadání",
    },
    "Rozsah splnění požadavků zadání": {
        "zadání nesplněno",
        "zadání splněno pouze částečně",
        "zadání splněno pouze částečně s drobnými výhradami",
        "zadání splněno pouze částečně s vážnějšími výhradami",
        "zadání téměř splněno",
        "zadání téměř splněno s drobnými výhradami",
        "zadání téměř splněno s vážnějšími výhradami",
        "student se odůvodněně odchýlil od zadání",
        "student se odůvodněně odchýlil od zadání s drobnými výhradami",
        "student se odůvodněně odchýlil od zadání s vážnějšími výhradami",
        "zadání splněno",
        "zadání splněno s drobnými výhradami",
        "zadání splněno s vážnějšími výhradami",
        "zadání splněno a práce obsahuje podstatná rozšíření",
    },
    "Rozsah technické zprávy": {
        "nesplňuje minimální požadavky",
        "téměř splňuje minimální požadavky",
        "splňuje pouze minimální požadavky",
        "je v obvyklém rozmezí",
        "přesahuje obvyklé rozmezí",
    },
}
OPPONENT_POINT_FIELDS = (
    "Prezentační úroveň technické zprávy",
    "Formální úprava technické zprávy",
    "Práce s literaturou",
    "Realizační výstup",
)
OPPONENT_POINT_RE = re.compile(r"\b(?:Body|Bodové hodnocení|Bodove hodnoceni)\s*:\s*(\d{1,3})\b", re.IGNORECASE)
OPPONENT_GRADE_RE = re.compile(r"\b(?:Známka|Znamka|Navržená známka|Navrzena znamka)\s*:\s*([A-F])\b", re.IGNORECASE)
OPPONENT_PUBLIC_FORBIDDEN_PATTERNS = (
    r"(?<!\w)/(?:home|Users|tmp|var|workspace|mnt)/[^\s)\"']*",
    r"\bcases/",
    r"\brounds/",
    r"\bwork/",
    r"\bnotes/",
    r"\bprofiles/",
    r"\boutputs/",
    r"\binputs/",
    r"\bextracted/",
    r"\boponent_posudek_navrh\.md\b",
    r"\bfeedback_k_posudku\.md\b",
    r"\breview_manifest\.json\b",
    r"\bagent_coverage\.json\b",
    r"\boponent_podklady(?:_revidovane|_draft)?\.md\b",
    r"\boponent_posudek_draft\.md\b",
    r"\bgithub_code_intake\.md\b",
    r"\brevision_diff\.md\b",
    r"\breference_report_comparison\.md\b",
    r"\bopponent_reading_packet\.md\b",
    r"\bpr_contribution_review\.md\b",
    r"\bdemo_artifacts_review\.md\b",
    r"\bcode_consistency\.md\b",
    r"\bcode_quality_review\.md\b",
    r"\bfigure_media_review\.md\b",
    r"\btypography_formal_review\.md\b",
    r"\breport_calibration_basis\.json\b",
    r"\breport[-_ ]calibration[-_ ]basis(?:\b|_)",
    r"\breviewer profile\b",
    r"\bsource_report_calibration(?:\b|_)",
    r"\b[0-9a-f]{64}\b",
    r"\b(?:approval record|helper[- ]check|workflow profile|review basis|review manifest|agent coverage)\b",
)


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


def copy_submitted_pdf(
    source: Path,
    round_dir: Path,
    *,
    force: bool = False,
    target_rel: str = SUPERVISOR_REPORT_SUBMITTED_PDF_REL,
) -> str:
    if not source.is_file():
        raise ValueError(f"submitted PDF path is not a file: {source}")
    if source.suffix.casefold() != ".pdf":
        raise ValueError("--pdf must point to a .pdf file")
    target = round_dir / target_rel
    if target.exists() and not force:
        raise ValueError(f"refusing to overwrite existing submitted PDF without --force: {target_rel}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != target.resolve():
        shutil.copy2(source, target)
    return target_rel


def copy_or_extract_public_text(
    *,
    pdf_path: Path,
    round_dir: Path,
    public_text_file: Path | None,
    force: bool = False,
    pdftotext_command: str = "pdftotext",
    target_rel: str = SUPERVISOR_REPORT_SUBMITTED_TEXT_REL,
) -> str:
    target = round_dir / target_rel
    if target.exists() and not force:
        raise ValueError(f"refusing to overwrite existing submitted public text without --force: {target_rel}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if public_text_file is not None:
        if not public_text_file.is_file():
            raise ValueError(f"submitted public text path is not a file: {public_text_file}")
        shutil.copy2(public_text_file, target)
        return target_rel
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
    return target_rel


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


def parse_colon_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip("- \t")
        value = value.strip()
        if key and value:
            fields[key] = value
    return fields


def parse_opponent_point_value(value: str) -> int | None:
    match = re.fullmatch(r"(\d{1,3})(?:\s*(?:bod[uůy]?|b\.?))?", value.strip(), re.IGNORECASE)
    if not match:
        return None
    parsed = int(match.group(1))
    return parsed if 0 <= parsed <= 100 else None


def opponent_public_report_text(text: str) -> str:
    lines = text.splitlines()
    result: list[str] = []
    in_private = False
    for line in lines:
        if line.strip() == OPPONENT_REPORT_PRIVATE_HEADING:
            in_private = True
            continue
        if in_private and line.startswith("## "):
            in_private = False
        if not in_private:
            result.append(line)
    while result and not result[-1].strip():
        result.pop()
    return "\n".join(result).strip() + "\n"


def opponent_report_values(text: str, *, require_private_comment: bool = True) -> tuple[dict[str, Any], list[str]]:
    lines = text.splitlines()
    errors: list[str] = []
    is_form = section_text(lines, OPPONENT_REPORT_IS_FORM_HEADING, stop_pattern=r"^##\s+")
    fields = parse_colon_fields(is_form)
    select_values: dict[str, str] = {}
    point_values: dict[str, int] = {}
    for field, allowed in OPPONENT_SELECT_FIELDS.items():
        value = fields.get(field, "")
        if not value:
            errors.append(f"missing IS select field: {field}")
        elif value not in allowed:
            errors.append(f"invalid IS select field {field}: {value}")
        else:
            select_values[field] = value
    for field in OPPONENT_POINT_FIELDS:
        value = fields.get(field, "")
        parsed = parse_opponent_point_value(value)
        if parsed is None:
            errors.append(f"missing or invalid IS point field: {field}")
        else:
            point_values[field] = parsed

    points_section = section_text(lines, OPPONENT_REPORT_POINTS_HEADING, stop_pattern=r"^##\s+")
    points_match = OPPONENT_POINT_RE.search(points_section)
    grade_match = OPPONENT_GRADE_RE.search(points_section)
    overall_points = int(points_match.group(1)) if points_match else None
    grade = grade_match.group(1).upper() if grade_match else None
    if overall_points is None or not 0 <= overall_points <= 100:
        errors.append("missing or invalid overall point value")
    if grade is None:
        errors.append("missing grade value")

    questions_section = section_text(lines, OPPONENT_REPORT_QUESTIONS_HEADING, stop_pattern=r"^##\s+")
    questions = [
        re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line).strip() for line in questions_section.splitlines() if "?" in line
    ]
    if not questions:
        errors.append("missing submitted defense questions")
    questions_text = normalize_report_text(questions_section)

    private_comment = section_text(lines, OPPONENT_REPORT_PRIVATE_HEADING, stop_pattern=r"^##\s+")
    if (
        require_private_comment
        and len(re.sub(r"\s+", "", private_comment)) < OPPONENT_REPORT_PRIVATE_MIN_NONSPACE_CHARS
    ):
        errors.append("missing or too-short private student comment")

    return (
        {
            "select_fields": select_values,
            "point_fields": point_values,
            "overall_points": overall_points,
            "grade": grade,
            "defense_questions": questions,
            "defense_questions_text": questions_text,
            "private_student_comment": private_comment.strip(),
            "private_student_comment_present": bool(private_comment.strip()),
        },
        errors,
    )


def public_text_safety_errors(text: str, rel_path: str) -> list[str]:
    errors: list[str] = []
    for pattern in OPPONENT_PUBLIC_FORBIDDEN_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            errors.append(f"{rel_path}: submitted public text contains internal/workflow pattern {pattern}")
    if OPPONENT_REPORT_PRIVATE_HEADING in text.splitlines():
        errors.append(f"{rel_path}: submitted public text must not contain private student comment heading")
    return errors


def public_report_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current = "__document__"
    buffer: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            sections[current] = "\n".join(buffer).strip()
            current = line.strip()
            buffer = []
        else:
            buffer.append(line)
    sections[current] = "\n".join(buffer).strip()
    return {key: value for key, value in sections.items() if value.strip()}


def opponent_public_section_diffs(reviewed_public_text: str, submitted_public_text: str) -> list[dict[str, str]]:
    if normalize_report_text(reviewed_public_text) == normalize_report_text(submitted_public_text):
        return []
    before_sections = public_report_sections(reviewed_public_text)
    after_sections = public_report_sections(submitted_public_text)
    ordered_sections = list(before_sections)
    ordered_sections.extend(section for section in after_sections if section not in before_sections)
    diffs: list[dict[str, str]] = []
    for section in ordered_sections:
        before = normalize_report_text(before_sections.get(section, ""))
        after = normalize_report_text(after_sections.get(section, ""))
        if before == after:
            continue
        diffs.append(
            {
                "section": section,
                "normalized_before": before,
                "normalized_after": after,
                "before_sha256": sha256_text(before),
                "after_sha256": sha256_text(after),
            }
        )
    return diffs


def is_submitted_report_artifact(rel_path: str) -> bool:
    return rel_path in {SUPERVISOR_REPORT_SUBMITTED_RECORD_REL, OPPONENT_REPORT_SUBMITTED_RECORD_REL}


def load_opponent_approval(round_dir: Path) -> dict[str, Any]:
    approval = load_json_object(round_dir / OPPONENT_REPORT_APPROVAL_REL, OPPONENT_REPORT_APPROVAL_REL)
    if approval.get("workflow_profile") != "opponent_report_review":
        raise ValueError(f"{OPPONENT_REPORT_APPROVAL_REL}: workflow_profile must be opponent_report_review")
    if approval.get("reviewed_artifact_path") != OPPONENT_REPORT_REVIEW_REL:
        raise ValueError(f"{OPPONENT_REPORT_APPROVAL_REL}: reviewed_artifact_path must be {OPPONENT_REPORT_REVIEW_REL}")
    if approval.get("review_basis_path") != OPPONENT_REPORT_CLEAN_REL:
        raise ValueError(f"{OPPONENT_REPORT_APPROVAL_REL}: review_basis_path must be {OPPONENT_REPORT_CLEAN_REL}")
    if approval.get("reviewed_artifact_sha256") != sha256_file(round_dir / OPPONENT_REPORT_REVIEW_REL):
        raise ValueError(f"{OPPONENT_REPORT_APPROVAL_REL}: reviewed_artifact_sha256 is stale")
    if approval.get("review_basis_sha256") != sha256_file(round_dir / OPPONENT_REPORT_CLEAN_REL):
        raise ValueError(f"{OPPONENT_REPORT_APPROVAL_REL}: review_basis_sha256 is stale")
    return approval


def opponent_report_field_values_match(clean_values: dict[str, Any], submitted_values: dict[str, Any]) -> bool:
    return bool(
        clean_values["select_fields"] == submitted_values["select_fields"]
        and clean_values["point_fields"] == submitted_values["point_fields"]
        and clean_values["overall_points"] == submitted_values["overall_points"]
        and clean_values["grade"] == submitted_values["grade"]
        and clean_values["defense_questions"] == submitted_values["defense_questions"]
        and clean_values["defense_questions_text"] == submitted_values["defense_questions_text"]
        and submitted_values.get("private_student_comment_present") is False
    )


def opponent_report_calibration_drift(values: dict[str, Any], expected_controls: dict[str, Any]) -> list[str]:
    drift: list[str] = []
    is_select_values = expected_controls.get("is_select_values")
    if isinstance(is_select_values, dict):
        select_fields = values.get("select_fields")
        select_fields = select_fields if isinstance(select_fields, dict) else {}
        for field, expected in is_select_values.items():
            if isinstance(field, str) and isinstance(expected, str) and select_fields.get(field) != expected:
                drift.append(f"is_select_values.{field}")
    expected_grade = expected_controls.get("overall_grade")
    if isinstance(expected_grade, str) and values.get("grade") != expected_grade:
        drift.append("overall_grade")
    interval = expected_controls.get("overall_points_interval")
    if (
        isinstance(interval, list)
        and len(interval) == 2
        and all(isinstance(item, int) and not isinstance(item, bool) for item in interval)
    ):
        points = values.get("overall_points")
        if not isinstance(points, int) or points < interval[0] or points > interval[1]:
            drift.append("overall_points_interval")
    question_count = expected_controls.get("defense_question_count")
    if isinstance(question_count, dict):
        minimum = question_count.get("min")
        maximum = question_count.get("max")
        questions = values.get("defense_questions")
        count = len(questions) if isinstance(questions, list) else 0
        if isinstance(minimum, int) and not isinstance(minimum, bool) and count < minimum:
            drift.append("defense_question_count")
        if isinstance(maximum, int) and not isinstance(maximum, bool) and count > maximum:
            drift.append("defense_question_count")
    if (
        expected_controls.get("private_comment_required") is True
        and values.get("private_student_comment_present") is not True
    ):
        drift.append("private_comment_required")
    return sorted(dict.fromkeys(drift))


def _load_bound_opponent_report_calibration(
    round_dir: Path,
    *,
    case_id: str,
    round_id: str,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    trace_path = round_dir / OPPONENT_REPORT_TRACE_REL
    if not trace_path.is_file():
        return None, {}
    trace = load_json_object(trace_path, OPPONENT_REPORT_TRACE_REL)
    basis_path = trace.get("report_calibration_basis_path")
    basis_hash = trace.get("report_calibration_basis_sha256")
    if basis_path is None and basis_hash is None:
        return None, {}
    if basis_path != REPORT_CALIBRATION_BASIS_REL:
        raise ValueError(
            f"{OPPONENT_REPORT_TRACE_REL}: report_calibration_basis_path must be {REPORT_CALIBRATION_BASIS_REL}"
        )
    basis_file = round_dir / REPORT_CALIBRATION_BASIS_REL
    if not basis_file.is_file():
        raise ValueError(f"missing report calibration basis: {REPORT_CALIBRATION_BASIS_REL}")
    if not isinstance(basis_hash, str) or basis_hash != sha256_file(basis_file):
        raise ValueError(f"{OPPONENT_REPORT_TRACE_REL}: report_calibration_basis_sha256 is stale")
    errors = validate_report_calibration_artifact(
        round_dir,
        REPORT_CALIBRATION_BASIS_REL,
        case_id=case_id,
        round_id=round_id,
    )
    if errors:
        raise ValueError("; ".join(errors))
    basis = load_json_object(basis_file, REPORT_CALIBRATION_BASIS_REL)
    return basis, report_calibration_expected_controls(basis)


def opponent_report_calibration_snapshot(
    round_dir: Path,
    *,
    case_id: str,
    round_id: str,
    clean_values: dict[str, Any],
    submitted_values: dict[str, Any],
) -> dict[str, Any]:
    basis, expected_controls = _load_bound_opponent_report_calibration(
        round_dir,
        case_id=case_id,
        round_id=round_id,
    )
    if basis is None:
        return {}
    clean_drift = opponent_report_calibration_drift(clean_values, expected_controls)
    submitted_expected_controls = dict(expected_controls)
    submitted_expected_controls.pop("private_comment_required", None)
    submitted_drift = opponent_report_calibration_drift(submitted_values, submitted_expected_controls)
    return {
        "report_calibration_basis_path": REPORT_CALIBRATION_BASIS_REL,
        "report_calibration_basis_sha256": sha256_file(round_dir / REPORT_CALIBRATION_BASIS_REL),
        "report_calibration_expected_controls": expected_controls,
        "report_calibration_reviewed_drift": clean_drift,
        "report_calibration_submitted_drift": submitted_drift,
        "report_calibration_controls_match": not clean_drift and not submitted_drift,
    }


def build_opponent_submitted_report_payload(
    round_dir: Path,
    *,
    case_id: str,
    round_id: str,
    submitted_at: str,
    recorded_by: str,
    pdf_rel: str = OPPONENT_REPORT_SUBMITTED_PDF_REL,
    public_text_rel: str = OPPONENT_REPORT_SUBMITTED_TEXT_REL,
) -> dict[str, Any]:
    if not recorded_by.strip():
        raise ValueError("--recorded-by is required for submitted report records")
    clean_path = round_dir / OPPONENT_REPORT_CLEAN_REL
    review_path = round_dir / OPPONENT_REPORT_REVIEW_REL
    pdf_path = round_dir / pdf_rel
    public_text_path = round_dir / public_text_rel
    for label, path in (
        (OPPONENT_REPORT_CLEAN_REL, clean_path),
        (OPPONENT_REPORT_REVIEW_REL, review_path),
        (pdf_rel, pdf_path),
        (public_text_rel, public_text_path),
    ):
        if not path.is_file():
            raise ValueError(f"missing required artifact: {label}")
    approval = load_opponent_approval(round_dir)
    clean_text = clean_path.read_text(encoding="utf-8")
    submitted_text = public_text_path.read_text(encoding="utf-8")
    public_projection = opponent_public_report_text(clean_text)
    clean_values, clean_errors = opponent_report_values(clean_text, require_private_comment=True)
    submitted_values, submitted_errors = opponent_report_values(submitted_text, require_private_comment=False)
    if clean_errors:
        raise ValueError("; ".join(f"{OPPONENT_REPORT_CLEAN_REL}: {error}" for error in clean_errors))
    if submitted_errors:
        raise ValueError("; ".join(f"{public_text_rel}: {error}" for error in submitted_errors))
    normalized_projection = normalize_report_text(public_projection)
    normalized_submitted = normalize_report_text(submitted_text)
    compared_fields = opponent_report_field_values_match(clean_values, submitted_values)
    calibration_snapshot = opponent_report_calibration_snapshot(
        round_dir,
        case_id=case_id,
        round_id=round_id,
        clean_values=clean_values,
        submitted_values=submitted_values,
    )
    calibration_controls_match = calibration_snapshot.get("report_calibration_controls_match", True) is True
    public_match = normalized_projection == normalized_submitted
    payload = {
        "schema_version": SUBMITTED_REPORT_SCHEMA,
        "case_id": case_id,
        "round_id": round_id,
        "generated_at": submitted_at,
        "producer_type": "human",
        "producer_role": "record-submitted-opponent-report",
        "producer_agent": None,
        "recorded_by": recorded_by.strip(),
        "human_reviewer_note": "Operator recorded the submitted opponent report PDF and public text.",
        "report_kind": REPORT_KIND_OPPONENT,
        "supported_report_kinds": sorted(SUPPORTED_REPORT_KINDS),
        "source_refs": [
            OPPONENT_REPORT_CLEAN_REL,
            OPPONENT_REPORT_REVIEW_REL,
            OPPONENT_REPORT_APPROVAL_REL,
            pdf_rel,
            public_text_rel,
        ],
        "limitations": [],
        "submitted_pdf_path": pdf_rel,
        "submitted_pdf_sha256": sha256_file(pdf_path),
        "submitted_public_text_path": public_text_rel,
        "submitted_public_text_sha256": sha256_file(public_text_path),
        "submitted_public_text_normalized_sha256": sha256_text(normalized_submitted),
        "reviewed_report_path": OPPONENT_REPORT_CLEAN_REL,
        "reviewed_report_sha256": sha256_file(clean_path),
        "reviewed_public_text_sha256": sha256_text(public_projection),
        "reviewed_public_text_normalized_sha256": sha256_text(normalized_projection),
        "review_output_path": OPPONENT_REPORT_REVIEW_REL,
        "review_output_sha256": sha256_file(review_path),
        "approval_record_path": OPPONENT_REPORT_APPROVAL_REL,
        "approval_record_sha256": sha256_file(round_dir / OPPONENT_REPORT_APPROVAL_REL),
        "approval_reviewed_artifact_sha256": approval["reviewed_artifact_sha256"],
        "approval_review_basis_sha256": approval["review_basis_sha256"],
        "grade": submitted_values["grade"],
        "points": submitted_values["overall_points"],
        "reviewed_grade": clean_values["grade"],
        "reviewed_points": clean_values["overall_points"],
        "is_select_fields": submitted_values["select_fields"],
        "reviewed_is_select_fields": clean_values["select_fields"],
        "category_points": submitted_values["point_fields"],
        "reviewed_category_points": clean_values["point_fields"],
        "defense_questions": submitted_values["defense_questions"],
        "reviewed_defense_questions": clean_values["defense_questions"],
        "defense_questions_text": submitted_values["defense_questions_text"],
        "reviewed_defense_questions_text": clean_values["defense_questions_text"],
        "private_student_comment_path": OPPONENT_REPORT_CLEAN_REL,
        "private_student_comment_sha256": sha256_text(clean_values["private_student_comment"]),
        "submitted_public_private_comment_present": submitted_values["private_student_comment_present"],
        "reviewed_private_student_comment_present": clean_values["private_student_comment_present"],
        "public_text_projection_kind": "opponent-clean-markdown-public-v1",
        "public_text_section_diffs": opponent_public_section_diffs(public_projection, submitted_text),
        "submitted_report_deltas_path": OPPONENT_REPORT_DELTAS_REL,
        "public_text_normalized_match": public_match,
        "field_values_match": compared_fields,
        "ready_for_archive": public_match and compared_fields and calibration_controls_match,
    }
    payload["source_refs"].extend(
        ref
        for ref in (OPPONENT_REPORT_TRACE_REL, REPORT_CALIBRATION_BASIS_REL)
        if calibration_snapshot and (round_dir / ref).is_file()
    )
    payload.update(calibration_snapshot)
    return payload


def validate_submitted_report_record(
    loaded: Any,
    *,
    round_dir: Path,
    case_id: str | None = None,
    round_id: str | None = None,
    rel_path: str = SUPERVISOR_REPORT_SUBMITTED_RECORD_REL,
) -> list[str]:
    if isinstance(loaded, dict) and loaded.get("report_kind") == REPORT_KIND_OPPONENT:
        return validate_submitted_opponent_report_record(
            loaded,
            round_dir=round_dir,
            case_id=case_id,
            round_id=round_id,
            rel_path=rel_path,
        )
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


def validate_submitted_opponent_report_record(
    loaded: Any,
    *,
    round_dir: Path,
    case_id: str | None = None,
    round_id: str | None = None,
    rel_path: str = OPPONENT_REPORT_SUBMITTED_RECORD_REL,
    require_archive_ready: bool = True,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(loaded, dict):
        return [f"{rel_path}: submitted opponent report record must be an object"]
    if loaded.get("schema_version") != SUBMITTED_REPORT_SCHEMA:
        errors.append(f"{rel_path}: schema_version must be {SUBMITTED_REPORT_SCHEMA}")
    if case_id is not None and loaded.get("case_id") != case_id:
        errors.append(f"{rel_path}: case_id does not match requested case")
    if round_id is not None and loaded.get("round_id") != round_id:
        errors.append(f"{rel_path}: round_id does not match requested round")
    if loaded.get("report_kind") != REPORT_KIND_OPPONENT:
        errors.append(f"{rel_path}: report_kind must be {REPORT_KIND_OPPONENT}")
    submitted_pdf_path = _validate_hash_bound_path(
        loaded, rel_path, round_dir, "submitted_pdf_path", "submitted_pdf_sha256", errors
    )
    submitted_text_path = _validate_hash_bound_path(
        loaded, rel_path, round_dir, "submitted_public_text_path", "submitted_public_text_sha256", errors
    )
    reviewed_path = _validate_hash_bound_path(
        loaded, rel_path, round_dir, "reviewed_report_path", "reviewed_report_sha256", errors
    )
    review_output_path = _validate_hash_bound_path(
        loaded, rel_path, round_dir, "review_output_path", "review_output_sha256", errors
    )
    approval_path = _validate_hash_bound_path(
        loaded, rel_path, round_dir, "approval_record_path", "approval_record_sha256", errors
    )
    calibration_path = _validate_optional_hash_bound_path(
        loaded,
        rel_path,
        round_dir,
        "report_calibration_basis_path",
        "report_calibration_basis_sha256",
        errors,
    )
    if submitted_pdf_path is not None and submitted_pdf_path.suffix.casefold() != ".pdf":
        errors.append(f"{rel_path}: submitted_pdf_path must point to a PDF")
    if loaded.get("reviewed_report_path") != OPPONENT_REPORT_CLEAN_REL:
        errors.append(f"{rel_path}: reviewed_report_path must be {OPPONENT_REPORT_CLEAN_REL}")
    if loaded.get("review_output_path") != OPPONENT_REPORT_REVIEW_REL:
        errors.append(f"{rel_path}: review_output_path must be {OPPONENT_REPORT_REVIEW_REL}")
    if loaded.get("approval_record_path") != OPPONENT_REPORT_APPROVAL_REL:
        errors.append(f"{rel_path}: approval_record_path must be {OPPONENT_REPORT_APPROVAL_REL}")
    if calibration_path is not None and loaded.get("report_calibration_basis_path") != REPORT_CALIBRATION_BASIS_REL:
        errors.append(f"{rel_path}: report_calibration_basis_path must be {REPORT_CALIBRATION_BASIS_REL}")
    if not isinstance(loaded.get("recorded_by"), str) or not str(loaded.get("recorded_by")).strip():
        errors.append(f"{rel_path}: recorded_by must be a non-empty string")
    if submitted_text_path is not None:
        errors.extend(public_text_safety_errors(submitted_text_path.read_text(encoding="utf-8"), rel_path))
    if (
        submitted_text_path is not None
        and reviewed_path is not None
        and review_output_path is not None
        and approval_path
    ):
        _validate_recomputed_submitted_opponent_report_state(
            loaded,
            rel_path,
            round_dir=round_dir,
            submitted_text_path=submitted_text_path,
            reviewed_path=reviewed_path,
            review_output_path=review_output_path,
            approval_path=approval_path,
            case_id=case_id,
            round_id=round_id,
            errors=errors,
        )
    archive_ready_with_deltas = False
    if require_archive_ready and loaded.get("public_text_normalized_match") is not True:
        archive_ready_with_deltas = _accepted_opponent_delta_ready(
            round_dir,
            rel_path=rel_path,
            case_id=case_id,
            round_id=round_id,
            errors=errors,
            submitted_record=loaded,
        )
    if (
        require_archive_ready
        and loaded.get("public_text_normalized_match") is not True
        and not archive_ready_with_deltas
    ):
        errors.append(f"{rel_path}: submitted public text does not match reviewed public report projection")
    if require_archive_ready and loaded.get("field_values_match") is not True:
        errors.append(f"{rel_path}: submitted public text field values do not match reviewed report basis")
    if require_archive_ready and loaded.get("report_calibration_controls_match") is False:
        errors.append(f"{rel_path}: submitted report values drift from report calibration basis")
    if require_archive_ready and loaded.get("ready_for_archive") is not True and not archive_ready_with_deltas:
        errors.append(f"{rel_path}: ready_for_archive must be true")
    if require_archive_ready and loaded.get("grade") != loaded.get("reviewed_grade"):
        errors.append(f"{rel_path}: submitted and reviewed grades must match")
    if require_archive_ready and loaded.get("points") != loaded.get("reviewed_points"):
        errors.append(f"{rel_path}: submitted and reviewed points must match")
    return errors


def _accepted_opponent_delta_ready(
    round_dir: Path,
    *,
    rel_path: str,
    case_id: str | None,
    round_id: str | None,
    errors: list[str],
    submitted_record: dict[str, Any],
) -> bool:
    delta_module = importlib.import_module("thesis_review_workflow.submitted_report_deltas")

    try:
        deltas = delta_module.load_opponent_submitted_report_deltas(round_dir)
    except ValueError as exc:
        errors.append(f"{rel_path}: {exc}")
        return False
    delta_errors = delta_module.validate_opponent_submitted_report_deltas(
        deltas,
        round_dir=round_dir,
        case_id=case_id,
        round_id=round_id,
        submitted_record=submitted_record,
    )
    errors.extend(f"{rel_path}: {error}" for error in delta_errors)
    return not delta_errors and deltas.get("ready_for_archive_with_deltas") is True


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


def _validate_optional_hash_bound_path(
    loaded: dict[str, Any],
    rel_path: str,
    round_dir: Path,
    path_field: str,
    hash_field: str,
    errors: list[str],
) -> Path | None:
    if path_field not in loaded and hash_field not in loaded:
        return None
    if path_field not in loaded or hash_field not in loaded:
        errors.append(f"{rel_path}: {path_field} and {hash_field} must be recorded together")
        return None
    return _validate_hash_bound_path(loaded, rel_path, round_dir, path_field, hash_field, errors)


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


def _validate_recomputed_submitted_opponent_report_state(
    loaded: dict[str, Any],
    rel_path: str,
    *,
    round_dir: Path,
    submitted_text_path: Path,
    reviewed_path: Path,
    review_output_path: Path,
    approval_path: Path,
    case_id: str | None,
    round_id: str | None,
    errors: list[str],
) -> None:
    submitted_text = submitted_text_path.read_text(encoding="utf-8")
    reviewed_text = reviewed_path.read_text(encoding="utf-8")
    public_projection = opponent_public_report_text(reviewed_text)
    clean_values, clean_errors = opponent_report_values(reviewed_text, require_private_comment=True)
    submitted_values, submitted_errors = opponent_report_values(submitted_text, require_private_comment=False)
    errors.extend(f"{rel_path}: reviewed report {error}" for error in clean_errors)
    errors.extend(f"{rel_path}: submitted public text {error}" for error in submitted_errors)
    if clean_errors or submitted_errors:
        return
    try:
        approval = load_opponent_approval(round_dir)
    except ValueError as exc:
        errors.append(f"{rel_path}: {exc}")
        return
    normalized_submitted = normalize_report_text(submitted_text)
    normalized_projection = normalize_report_text(public_projection)
    field_values_match = opponent_report_field_values_match(clean_values, submitted_values)
    calibration_snapshot: dict[str, Any] = {}
    if case_id is not None and round_id is not None:
        try:
            calibration_snapshot = opponent_report_calibration_snapshot(
                round_dir,
                case_id=case_id,
                round_id=round_id,
                clean_values=clean_values,
                submitted_values=submitted_values,
            )
        except ValueError as exc:
            errors.append(f"{rel_path}: {exc}")
    if loaded.get("submitted_public_text_normalized_sha256") != sha256_text(normalized_submitted):
        errors.append(f"{rel_path}: submitted_public_text_normalized_sha256 is stale")
    if loaded.get("reviewed_public_text_normalized_sha256") != sha256_text(normalized_projection):
        errors.append(f"{rel_path}: reviewed_public_text_normalized_sha256 is stale")
    if loaded.get("reviewed_public_text_sha256") != sha256_text(public_projection):
        errors.append(f"{rel_path}: reviewed_public_text_sha256 is stale")
    if loaded.get("public_text_normalized_match") != (normalized_submitted == normalized_projection):
        errors.append(f"{rel_path}: public_text_normalized_match is stale")
    if loaded.get("field_values_match") != field_values_match:
        errors.append(f"{rel_path}: field_values_match is stale")
    calibration_controls_match = calibration_snapshot.get("report_calibration_controls_match", True) is True
    if loaded.get("ready_for_archive") != (
        normalized_submitted == normalized_projection and field_values_match and calibration_controls_match
    ):
        errors.append(f"{rel_path}: ready_for_archive is stale")
    expected_fields = {
        "grade": submitted_values["grade"],
        "points": submitted_values["overall_points"],
        "reviewed_grade": clean_values["grade"],
        "reviewed_points": clean_values["overall_points"],
        "is_select_fields": submitted_values["select_fields"],
        "reviewed_is_select_fields": clean_values["select_fields"],
        "category_points": submitted_values["point_fields"],
        "reviewed_category_points": clean_values["point_fields"],
        "defense_questions": submitted_values["defense_questions"],
        "reviewed_defense_questions": clean_values["defense_questions"],
        "defense_questions_text": submitted_values["defense_questions_text"],
        "reviewed_defense_questions_text": clean_values["defense_questions_text"],
        "private_student_comment_sha256": sha256_text(clean_values["private_student_comment"]),
        "submitted_public_private_comment_present": submitted_values["private_student_comment_present"],
        "reviewed_private_student_comment_present": clean_values["private_student_comment_present"],
        "public_text_section_diffs": opponent_public_section_diffs(public_projection, submitted_text),
        "approval_reviewed_artifact_sha256": approval["reviewed_artifact_sha256"],
        "approval_review_basis_sha256": approval["review_basis_sha256"],
    }
    expected_fields.update(calibration_snapshot)
    if not calibration_snapshot and (
        "report_calibration_basis_path" in loaded or "report_calibration_basis_sha256" in loaded
    ):
        errors.append(f"{rel_path}: report calibration basis binding is stale or no longer present")
    for field, expected in expected_fields.items():
        if loaded.get(field) != expected:
            errors.append(f"{rel_path}: {field} is stale")
    if loaded.get("review_output_sha256") != sha256_file(review_output_path):
        errors.append(f"{rel_path}: review_output_sha256 is stale")
    if loaded.get("approval_record_sha256") != sha256_file(approval_path):
        errors.append(f"{rel_path}: approval_record_sha256 is stale")
