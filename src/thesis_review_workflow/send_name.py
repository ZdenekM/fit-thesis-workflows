"""Student-facing file names for rendered PDFs.

`render-feedback` and `render-brief` write their PDF to a fixed workflow path, which the
gates, hashes and docs rely on. Next to it they place a copy under a name the student and
the supervisor can tell apart in a mailbox or a downloads folder:

    2026-10-13_Novak_BP_zpetna-vazba.pdf

The date leads so the files sort chronologically. The name part is the student's surname
from `case.md`, and the parts are ASCII without spaces so mail clients, Windows and
archives keep them intact. The copy is derived from the fixed PDF and is removed or
replaced together with it.
"""

from __future__ import annotations

import datetime
import re
import unicodedata
from pathlib import Path

from thesis_review_workflow import pdf_render
from thesis_review_workflow.assignment_draft import WORK_TYPE_BY_VARIANT

KIND_LABELS: dict[str, dict[str, str]] = {
    "feedback": {"cs": "zpetna-vazba", "en": "feedback"},
    "brief": {"cs": "podklad-k-tematu", "en": "topic-brief"},
}
"""The document kind as the last name part, in the student's feedback language."""

WORK_TYPES = frozenset(WORK_TYPE_BY_VARIANT.values())
"""Work types `work_type_part` lets into a feedback name; `unknown` or a template line is left out."""

NON_DECOMPOSING = str.maketrans({"Đ": "D", "đ": "d", "Ł": "L", "ł": "l", "Ø": "O", "ø": "o", "ß": "ss"})
"""Latin letters that Unicode decomposition does not reduce to an ASCII base letter."""


def ascii_slug(value: str) -> str:
    """`value` without diacritics, with every run of other characters turned into one dash."""
    decomposed = unicodedata.normalize("NFKD", value.translate(NON_DECOMPOSING))
    ascii_only = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^A-Za-z0-9]+", "-", ascii_only).strip("-")


def surname(student: str) -> str:
    """The last word of the `Student:` value; a cosmetic name part, never an identifier."""
    words = student.split()
    return words[-1] if words else ""


def work_type_part(work_type: str) -> str:
    """`Work type:` from `case.md` as a name part: BP or DP, otherwise nothing."""
    part = work_type.strip().upper()
    return part if part in WORK_TYPES else ""


def scope_part(scope: str) -> str:
    return ascii_slug(scope).upper()


def send_pdf_name(*, day: datetime.date, who: str, scope: str, kind: str, language: str) -> str:
    """`<date>_<who>_<scope>_<kind>.pdf`, leaving out a part that is empty.

    `scope` is the work type for feedback and the variant's work type for a brief.
    """
    parts = [day.isoformat(), ascii_slug(who), scope_part(scope), KIND_LABELS[kind][language]]
    return "_".join(part for part in parts if part) + ".pdf"


def is_send_copy(name: str, *, kind: str, scope: str = "") -> bool:
    """Whether `name` has exactly the shape `send_pdf_name` gives `kind` (and `scope`, when given).

    Anything else in the folder, such as an archived or annotated PDF with extra name
    parts or a date that does not exist, is not a copy and is never removed.
    """
    labels = "|".join(re.escape(label) for label in KIND_LABELS[kind].values())
    scope_re = f"_{re.escape(scope_part(scope))}" if scope else f"(?:_(?:{'|'.join(sorted(WORK_TYPES))}))?"
    match = re.fullmatch(rf"(\d{{4}}-\d{{2}}-\d{{2}})(?:_[A-Za-z0-9-]+)?{scope_re}_(?:{labels})\.pdf", name)
    if match is None:
        return False
    try:
        datetime.date.fromisoformat(match.group(1))
    except ValueError:
        return False
    return True


def remove_send_copies(output_dir: Path, *, kind: str, scope: str = "") -> bool:
    """Remove the named copies of `kind` in `output_dir`, naming each; False when one cannot be removed."""
    if not output_dir.is_dir():
        return True
    for path in sorted(output_dir.iterdir()):
        if path.is_file() and is_send_copy(path.name, kind=kind, scope=scope):
            if not pdf_render.remove_stale_pdf(output_dir, path.name, "it is the named copy of an earlier render"):
                return False
    return True


def install_send_copy(pdf: Path, name: str) -> Path:
    """Copy the rendered `pdf` to `name` beside it.

    Callers have already removed the earlier copies with the earlier PDF, in the approval
    gate that runs before every render.
    """
    target = pdf.with_name(name)
    pdf_render.install_pdf(pdf, target)
    return target
