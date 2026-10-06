"""Render reviewed student-facing supervisor feedback to a PDF with Quarto and Typst.

`outputs/feedback_student.md` stays the single source of truth; the PDF is a derived
presentation artifact. The Quarto defaults, Typst template partial, Lua filters and
vendored fonts are package resources under `render/feedback/`, copied next to the
Markdown in a temporary directory for each render, so the source file is never touched.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any

from thesis_review_workflow.cli.check_feedback_output import LANGUAGE, read_language
from thesis_review_workflow.metadata import read_fields
from thesis_review_workflow.operation_log import load_operation_log
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
MIN_QUARTO_VERSION = (1, 10, 18)
"""The version the template and filters were tested with (bundles Typst 0.15.1)."""

RENDER_TIMEOUT_SECONDS = 300
SOURCE_NAME = "feedback_student.md"
RENDER_VALUES_NAME = "feedback-render.json"
"""Read by `filters/feedback-blocks.lua`, which lets these values override front matter."""

LABELS: dict[str, dict[str, str]] = {
    "cs": {"kind": "Zpětná vazba vedoucího", "student": "Student", "topic": "Téma", "date": "Datum"},
    "en": {"kind": "Supervisor feedback", "student": "Student", "topic": "Topic", "date": "Date"},
}
DRAFT_STAMP = {"cs": "NÁVRH", "en": "DRAFT"}

AREA_HEADER = {"cs": "Oblast", "en": "Area"}
"""The priority-table column shown in a card title; the skill's table template fixes it."""

TIP_HEADINGS: dict[str, tuple[str, ...]] = {
    "cs": ("Co se od minulé verze posunulo", "Co je na práci už dobré"),
    "en": ("Progress Since Previous Feedback", "What Is Already Working Well"),
}
"""Sections rendered as a positive block. The scope and priority headings and the date
label come from `check_feedback_output.LANGUAGE`, the checker of the same contract."""


class RenderError(Exception):
    """A render-feedback failure with an operator-readable message."""


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
    """The values the layout filter assigns to the document metadata for the template."""
    language = LANGUAGE[case.language]
    feedback: dict[str, Any] = {
        "student": case.student,
        "topic": case.topic,
        "labels": LABELS[case.language],
        "sections": {
            "date_label": language["date_label"],
            "scope": strip_heading(language["scope_heading"]),
            "priority": strip_heading(language["priority_heading"]),
            "area_header": AREA_HEADER[case.language],
            "tips": list(TIP_HEADINGS[case.language]),
        },
    }
    if draft:
        feedback["draft"] = DRAFT_STAMP[case.language]
    return {"lang": case.language, "feedback": feedback}


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


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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
    found = shutil.which("quarto")
    if found is None:
        raise RenderError(
            "quarto is not installed or not on PATH; install Quarto "
            f"{format_version(MIN_QUARTO_VERSION)} or newer, or send {FEEDBACK_REL} as Markdown"
        )
    return Path(found)


def format_version(version: tuple[int, ...]) -> str:
    return ".".join(str(part) for part in version)


def parse_version(output: str) -> tuple[int, int, int] | None:
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", output)
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def quarto_version(quarto: Path) -> str:
    """The `quarto --version` string, refusing a version older than the tested one."""
    try:
        result = subprocess.run(
            [str(quarto), "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RenderError(f"cannot run {quarto} --version: {exc}") from exc
    text = result.stdout.strip()
    version = parse_version(text)
    if result.returncode != 0 or version is None:
        raise RenderError(f"cannot read the Quarto version from {quarto}: {text or result.stderr.strip()}")
    if version < MIN_QUARTO_VERSION:
        raise RenderError(
            f"Quarto {format_version(version)} is older than the tested {format_version(MIN_QUARTO_VERSION)}; "
            "update Quarto"
        )
    return format_version(version)


def resource_root() -> Traversable:
    return resources.files("thesis_review_workflow").joinpath("render", "feedback")


def copy_resources(source: Traversable, destination: Path) -> None:
    """Copy a resource tree through `importlib.resources`, so packaged PEX files work too."""
    destination.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        target = destination / item.name
        if item.is_dir():
            copy_resources(item, target)
        else:
            target.write_bytes(item.read_bytes())


def render_pdf(source: bytes, output_pdf: Path, metadata: dict[str, Any], quarto: Path) -> None:
    """Render the Markdown `source` bytes to `output_pdf` in a scratch directory."""
    # Quarto or Typst children may still hold files after a timeout, notably on Windows.
    with tempfile.TemporaryDirectory(prefix="render-feedback-", ignore_cleanup_errors=True) as scratch:
        work = Path(scratch)
        copy_resources(resource_root(), work)
        (work / SOURCE_NAME).write_bytes(source)
        values = json.dumps(metadata, ensure_ascii=False, indent=2) + "\n"
        (work / RENDER_VALUES_NAME).write_text(values, encoding="utf-8")
        try:
            result = subprocess.run(
                [str(quarto), "render", SOURCE_NAME, "--to", "typst"],
                cwd=work,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=RENDER_TIMEOUT_SECONDS,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RenderError(f"quarto render failed to run: {exc}") from exc
        rendered = work / Path(SOURCE_NAME).with_suffix(".pdf")
        if result.returncode != 0 or not rendered.is_file():
            tail = "\n".join((result.stdout + result.stderr).strip().splitlines()[-15:])
            raise RenderError(f"quarto render exited with {result.returncode}:\n{tail}")
        install_pdf(rendered, output_pdf)


def install_pdf(rendered: Path, output_pdf: Path) -> None:
    """Replace `output_pdf` atomically; a PDF open in a viewer on Windows cannot be replaced."""
    partial = output_pdf.with_name(output_pdf.name + ".partial")
    try:
        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(rendered, partial)
        partial.replace(output_pdf)
    except OSError as exc:
        partial.unlink(missing_ok=True)
        raise RenderError(f"cannot write {output_pdf.name} (close it if it is open in a viewer): {exc}") from exc
