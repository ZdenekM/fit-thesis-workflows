"""Render reviewed student-facing supervisor feedback to a PDF with Quarto and Typst.

`outputs/feedback_student.md` stays the single source of truth; the PDF is a derived
presentation artifact. The engine is `pdf_render`; this module owns the feedback layout
values (`render/feedback/`) and the review-approval gate.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from thesis_review_workflow import pdf_render
from thesis_review_workflow.cli.check_feedback_output import LANGUAGE, read_language
from thesis_review_workflow.metadata import read_fields
from thesis_review_workflow.operation_log import load_operation_log
from thesis_review_workflow.pdf_render import DRAFT_STAMP, RenderError, sha256_bytes
from thesis_review_workflow.review_approvals import (
    APPROVAL_PROFILES,
    load_review_approval,
    validate_review_approval_with_manifest,
)
from thesis_review_workflow.review_manifest import MANIFEST_REL, load_manifest

FEEDBACK_REL = "outputs/feedback_student.md"
PDF_REL = "outputs/feedback_student.pdf"
PREVIEW_PDF_REL = "work/feedback_student_preview.pdf"
"""A `--draft` preview never lands in `outputs/`, so a PDF there means an approved render."""

APPROVAL_PROFILE = APPROVAL_PROFILES["supervisor-feedback"]
RENDER_KIND = "feedback"
SOURCE_NAME = "feedback_student.md"

KIND = {"cs": "Zpětná vazba vedoucího", "en": "Supervisor feedback"}
LABELS: dict[str, dict[str, str]] = {
    "cs": {"student": "Student", "topic": "Téma", "date": "Datum"},
    "en": {"student": "Student", "topic": "Topic", "date": "Date"},
}

AREA_HEADER = {"cs": "Oblast", "en": "Area"}
"""The priority-table column shown in a card title; the skill's table template fixes it."""

TIP_HEADINGS: dict[str, tuple[str, ...]] = {
    "cs": ("Co se od minulé verze posunulo", "Co je na práci už dobré"),
    "en": ("Progress Since Previous Feedback", "What Is Already Working Well"),
}
"""Sections rendered as a positive block. The scope and priority headings and the date
label come from `check_feedback_output.LANGUAGE`, the checker of the same contract."""


@dataclass(frozen=True)
class FeedbackCaseMetadata:
    language: str
    student: str
    topic: str


def read_case_metadata(case_md: Path) -> FeedbackCaseMetadata:
    fields = read_fields(case_md)
    language = read_language(case_md) if case_md.is_file() else "cs"
    if language not in LANGUAGE:
        raise RenderError(f"{case_md.name}: unsupported Student feedback language: {language} (expected cs or en)")
    return FeedbackCaseMetadata(
        language=language,
        student=fields.get("student", ""),
        topic=fields.get("topic", ""),
    )


def strip_heading(markdown_heading: str) -> str:
    return markdown_heading.lstrip("#").strip()


def render_metadata(case: FeedbackCaseMetadata, *, draft: bool) -> dict[str, Any]:
    """The values `filters/feedback-blocks.lua` assigns to the document metadata and maps."""
    language = LANGUAGE[case.language]
    masthead: dict[str, Any] = {
        "kind": KIND[case.language],
        "labels": LABELS[case.language],
        "student": case.student,
        "topic": case.topic,
    }
    if draft:
        masthead["draft"] = DRAFT_STAMP[case.language]
    sections = {
        "date_label": language["date_label"],
        "scope": strip_heading(language["scope_heading"]),
        "priority": strip_heading(language["priority_heading"]),
        "area_header": AREA_HEADER[case.language],
        "tips": list(TIP_HEADINGS[case.language]),
    }
    return {"lang": case.language, "masthead": masthead, "sections": sections}


def approval_errors(round_dir: Path, *, case_id: str, round_id: str, source_sha256: str) -> list[str]:
    """Every reason the round's supervisor-feedback approval does not cover `source_sha256`.

    The same full contract `confirm-supervisor-report` enforces for its sendable artifact:
    profile, reviewer role, review basis, observed required checks backed by the review
    manifest, and reviewer independence, on top of verdict and both hashes. `source_sha256`
    is the hash of the bytes about to be rendered, so an edit after this check cannot slip
    into the PDF.
    """
    approval_rel = APPROVAL_PROFILE.approval_path
    payload, errors = load_review_approval(round_dir, approval_rel)
    if payload is None:
        return errors
    try:
        manifest = load_manifest(round_dir / MANIFEST_REL)
    except (ValueError, OSError) as exc:
        return [f"{MANIFEST_REL.as_posix()}: cannot read review manifest: {exc}"]
    if not manifest:
        return [f"missing required review manifest: {MANIFEST_REL.as_posix()}"]
    errors = validate_review_approval_with_manifest(
        payload,
        approval_rel,
        round_dir,
        manifest=manifest,
        case_id=case_id,
        round_id=round_id,
        reviewed_artifact_path=FEEDBACK_REL,
    )
    if payload.get("reviewed_artifact_sha256") != source_sha256:
        errors.append(f"{approval_rel}: {FEEDBACK_REL} changed after it was read for rendering")
    return errors


def pdf_rendered_from(round_dir: Path, source_sha256: str) -> bool:
    """True when `outputs/feedback_student.pdf` is the latest approved render of these bytes.

    Read from the round's operation log: the last non-draft `render-feedback` record must
    name `source_sha256` and the hash of the PDF now on disk.
    """
    pdf = round_dir / PDF_REL
    if not pdf.is_file():
        return False
    try:
        records, _ = load_operation_log(round_dir)
    except (OSError, UnicodeDecodeError):
        return False  # an unreadable log proves nothing, so the PDF is treated as stale
    renders = [
        record
        for record in records
        if record.get("operation") == "render-feedback"
        and record.get("status") == "passed"
        and isinstance(record.get("details"), dict)
        and record["details"].get("draft") == "false"
    ]
    if not renders:
        return False
    details: dict[str, Any] = renders[-1]["details"]
    pdf_sha256 = sha256_bytes(pdf.read_bytes())
    return bool(details.get("source_sha256") == source_sha256 and details.get("pdf_sha256") == pdf_sha256)


def find_quarto() -> Path:
    return pdf_render.find_quarto(FEEDBACK_REL)


def render_pdf(source: bytes, output_pdf: Path, metadata: dict[str, Any], quarto: Path) -> None:
    """Render the feedback Markdown `source` bytes to `output_pdf` in a scratch directory."""
    pdf_render.render_pdf(RENDER_KIND, SOURCE_NAME, source, output_pdf, metadata, quarto)
