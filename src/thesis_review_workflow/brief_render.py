"""Render an approved topic brief projection to a PDF the student can be handed.

`outputs/student_brief_<variant>.md` in a `topic-proposal` case stays the single source of
truth; the PDF is a derived presentation artifact. The engine is `pdf_render`; this module
owns the brief layout values (`render/brief/`) and the gate, which is the variant's bundle
approval — the same check `scripts/check-assignment-bundle` runs before a brief is sent.
Everything the PDF prints comes from files that approval binds: the projection, and the
official title from the variant's formal assignment.
"""

from __future__ import annotations

import datetime
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from thesis_review_workflow import pdf_render
from thesis_review_workflow.assignment_bundle import (
    approval_rel,
    assignment_formal_rel,
    brief_projection_rel,
    validate_bundle_approval_payload,
)
from thesis_review_workflow.assignment_draft import (
    WORK_TYPE_BY_VARIANT,
    BriefLanguage,
    brief_language,
    label_value,
    used_rendering,
)
from thesis_review_workflow.cli.check_assignment_bundle import check_bundle
from thesis_review_workflow.metadata import case_kind, read_fields
from thesis_review_workflow.pdf_render import DRAFT_STAMP, RenderError, sha256_bytes

RENDER_KIND = "brief"
SOURCE_NAME = "student_brief.md"
TOPIC_CASE_KIND = "topic-proposal"
RENDER_RECORD_SCHEMA = "brief-pdf-render-v1"

KIND: dict[str, dict[str, str]] = {
    "cs": {"BP": "Bakalářská práce", "DP": "Diplomová práce"},
    "en": {"BP": "Bachelor's thesis", "DP": "Master's thesis"},
}
"""The masthead line above the title, by the variant's FIT work type."""

LABELS: dict[str, dict[str, str]] = {
    "cs": {"topic": "Téma", "date": "Datum"},
    "en": {"topic": "Topic", "date": "Date"},
}

TITLE_LABEL = {"cs": "Název:", "en": "Title:"}
"""The official-title field of each FIT IS rendering in `assignment_draft.RENDERINGS`."""

EN_MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)  # fmt: skip
NBSP = " "


def pdf_rel(variant: str) -> str:
    return f"outputs/student_brief_{variant}.pdf"


def preview_pdf_rel(variant: str) -> str:
    """A `--draft` preview never lands in `outputs/`, so a PDF there means an approved render."""
    return f"work/student_brief_{variant}_preview.pdf"


def render_record_rel(variant: str) -> str:
    """Which approval the `outputs/` PDF was rendered under; a topic case has no operation log."""
    return f"work/student_brief_{variant}_pdf.json"


def exact_entry(path: Path) -> bool:
    """True when `path` exists under exactly this spelling.

    A case-insensitive filesystem (Windows, macOS) resolves `student_brief_BP.md` to
    `student_brief_bp.md`, so a mistyped variant would otherwise reach, and remove, the
    real variant's PDF.
    """
    try:
        return path.name in os.listdir(path.parent)
    except OSError:
        return False


@dataclass(frozen=True)
class BriefCase:
    language: BriefLanguage


def require_topic_case(case_dir: Path) -> dict[str, str]:
    """The `case.md` fields of a topic case; refuses any other case kind before anything is touched."""
    fields = read_fields(case_dir / "case.md")
    kind = case_kind(fields)
    if kind != TOPIC_CASE_KIND:
        raise RenderError(
            f"{case_dir.name}/case.md: `Case kind: {kind}` — a brief is rendered from a "
            f"`{TOPIC_CASE_KIND}` case; see docs/assignment-authoring.md"
        )
    return fields


def brief_case(fields: dict[str, str], case_name: str) -> BriefCase:
    """The brief language. Resolved after the gate, so a bad value still clears a stale PDF."""
    language = brief_language(fields)
    if language is None:
        raise RenderError(f"{case_name}/case.md: unsupported Student feedback language (expected cs or en)")
    return BriefCase(language=language)


def official_title(assignment: str) -> str:
    """The `Název:`/`Title:` value of the assignment's single rendering block, or empty."""
    rendering, _ = used_rendering(assignment)
    if rendering is None:
        return ""
    lines = assignment.splitlines()
    starts = [index for index, line in enumerate(lines) if line.strip() == rendering.heading]
    for line in lines[starts[0] + 1 :] if starts else []:
        value = label_value(line, TITLE_LABEL[rendering.key])
        if value is not None:
            return value
    return ""


def heading_text(markdown_heading: str) -> str:
    return markdown_heading.lstrip("#").strip()


def display_date(day: datetime.date, language: str) -> str:
    """`7. 10. 2026` or `7 October 2026`, joined by no-break spaces so it never wraps."""
    if language == "en":
        parts = [str(day.day), EN_MONTHS[day.month - 1], str(day.year)]
    else:
        parts = [f"{day.day}.", f"{day.month}.", str(day.year)]
    return NBSP.join(parts)


def render_values(case: BriefCase, variant: str, *, topic: str, today: datetime.date, draft: bool) -> dict[str, Any]:
    """The values `filters/brief-blocks.lua` assigns to the document metadata and maps."""
    key = case.language.key
    work_type = WORK_TYPE_BY_VARIANT.get(variant)
    masthead: dict[str, Any] = {
        "kind": KIND[key][work_type] if work_type else variant,
        "labels": LABELS[key],
        "topic": topic,
    }
    if draft:
        masthead["draft"] = DRAFT_STAMP[key]
    title = heading_text(case.language.title)
    delta = heading_text(case.language.delta_heading)
    return {
        "lang": key,
        "title": title,
        "date": display_date(today, key),
        "masthead": masthead,
        "headings": {
            "title": f"{title} - {variant}",
            "content": [heading_text(heading) for heading in case.language.content_headings],
            "delta": f"{delta} - {variant}",
            "delta_display": delta,
        },
    }


def read_bound(case_dir: Path, variant: str) -> dict[str, bytes]:
    """The bytes the PDF is built from, read once, so the gate and the render see the same."""
    read: dict[str, bytes] = {}
    for rel in (brief_projection_rel(variant), assignment_formal_rel(variant)):
        path = case_dir / rel
        read[rel] = path.read_bytes() if path.is_file() else b""
    return read


def approval_errors(case_dir: Path, *, case_id: str, variant: str, read: dict[str, bytes]) -> tuple[list[str], str]:
    """Every reason the variant's bundle approval does not cover the `read` bytes, and the
    hash of the approval record that does.

    `check_bundle` is the whole publication gate: structure first, then the approval record
    with every bound file's hash. The record is then read once more and those exact bytes are
    validated again, because they are what the returned hash and the render record vouch
    for: a record replaced between the two reads must not authorize the PDF. Each `read`
    entry is finally compared to the hash that record binds, so an edit after the check
    cannot slip into the PDF either.
    """
    errors = check_bundle(case_dir, case_id, variant)
    if errors:
        return errors, ""
    record_rel = approval_rel(variant)
    try:
        record = (case_dir / record_rel).read_bytes()
        payload = json.loads(record.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"{record_rel}: cannot be read as JSON: {exc}"], ""
    errors = validate_bundle_approval_payload(payload, case_dir, case_id=case_id, variant=variant, rel_path=record_rel)
    if errors:
        return errors, ""
    bound = {entry["path"]: entry["sha256"] for entry in payload["files"]}
    changed = [rel for rel, data in read.items() if bound.get(rel) != sha256_bytes(data)]
    if changed:
        return [f"{record_rel}: {rel} changed after it was read for rendering" for rel in changed], ""
    return [], sha256_bytes(record)


def write_render_record(case_dir: Path, *, case_id: str, variant: str, approval_sha256: str, version: str) -> None:
    record = {
        "schema_version": RENDER_RECORD_SCHEMA,
        "case_id": case_id,
        "variant": variant,
        "approval_sha256": approval_sha256,
        "pdf_sha256": sha256_bytes((case_dir / pdf_rel(variant)).read_bytes()),
        "quarto_version": version,
    }
    path = case_dir / render_record_rel(variant)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def pdf_rendered_from(case_dir: Path, variant: str, approval_sha256: str) -> bool:
    """True when the `outputs/` PDF is the one rendered under this exact approval record.

    The approval record binds every file the PDF prints, so its hash covers the brief and
    the title alike. An unreadable record proves nothing, so the PDF is treated as stale.
    """
    pdf = case_dir / pdf_rel(variant)
    if not pdf.is_file():
        return False
    try:
        record = json.loads((case_dir / render_record_rel(variant)).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    if not isinstance(record, dict) or record.get("schema_version") != RENDER_RECORD_SCHEMA:
        return False
    return bool(
        record.get("approval_sha256") == approval_sha256 and record.get("pdf_sha256") == sha256_bytes(pdf.read_bytes())
    )


def find_quarto(variant: str) -> Path:
    return pdf_render.find_quarto(brief_projection_rel(variant))


def render_pdf(source: bytes, output_pdf: Path, values: dict[str, Any], quarto: Path) -> None:
    """Render the brief Markdown `source` bytes to `output_pdf` in a scratch directory."""
    pdf_render.render_pdf(RENDER_KIND, SOURCE_NAME, source, output_pdf, values, quarto)
