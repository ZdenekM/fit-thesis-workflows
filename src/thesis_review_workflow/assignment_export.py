"""Structural check of an assignment PDF exported from FIT IS.

The head of department approves an assignment as FIT IS prints it, and the
Markdown bundle cannot show how IS stores it: seven points pasted as plain text
`1. …` and the same points formatted as a numbered list read alike in the
bundle and differently in the export. This module reads the `pdftotext -layout`
text of the export, where a list keeps its geometry: every label of the form
opens a line at column 0, a list item is indented past that column, and the
item's continuation lines hang under its text. It decides that geometry, the
list markers, the page count, the header and whether a field has a value, never
what the text says (`AGENTS.md`); the labels come from
`assignment_draft.RENDERINGS`.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from thesis_review_workflow.assignment_draft import RENDERINGS, Rendering, form_labels

PAGE_BREAK = "\f"
"""`pdftotext` ends every page with a form feed."""
NUMBERED_ITEM_RE = re.compile(r"(\d+)\.(?=\s|$)")
BULLET_ITEM_RE = re.compile(r"•(?=\s|$)")
TYPED_POINT_RE = re.compile(r"\d+\.\s")
TYPED_BULLET_RE = re.compile(r"[-•*]\s")
"""A marker typed into the item's own text, which the list formatting then marks a second time."""
LABEL_COLUMN = 0
COLUMN_TOLERANCE = 1
"""`pdftotext -layout` rounds x positions to character columns, so one x can land a column apart."""
QUOTE_LIMIT = 60


@dataclass(frozen=True)
class ExportCheck:
    """One export: its rendering and variant when the header was recognised, findings, and notes."""

    rendering: Rendering | None
    variant: str | None
    pages: int
    findings: tuple[str, ...]
    notes: tuple[str, ...] = ()
    """What passed only because the operator said so, such as `--allow-empty-semestral`."""


@dataclass
class _Item:
    name: str
    number: int | None
    indent: int
    alone: bool
    """The marker stood on a line of its own, with the item's text below it."""
    doubled: bool
    """The item's text starts with a typed marker of its own."""
    text_column: int | None
    """Where the item's text starts, which its continuation lines hang under."""


@dataclass(frozen=True)
class _Field:
    rest: str
    """Text after the label on the label's own line."""
    body: tuple[str, ...]
    """The lines up to the next label of the form."""


def page_count(text: str) -> int:
    pages = text.split(PAGE_BREAK)
    if not pages[-1].strip():
        pages.pop()
    return len(pages)


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _quote(text: str) -> str:
    return f"`{text[:QUOTE_LIMIT]}`"


def recognised_header(lines: Sequence[str]) -> tuple[Rendering, str] | None:
    """The rendering and variant whose document title opens the export.

    Whitespace runs are collapsed and a typographic apostrophe read as `'`, so wider letter spacing
    or a `Bachelor’s` glyph does not hide the title; the assignment number may follow it.
    """

    first = next((line for line in lines if line.strip()), "")
    normalized = " ".join(first.replace("’", "'").split())
    for rendering in RENDERINGS.values():
        for variant, title in rendering.titles.items():
            if normalized == title or normalized.startswith(title + " "):
                return rendering, variant
    return None


def later_labels(rendering: Rendering, label: str) -> tuple[str, ...]:
    """The labels that may end `label`'s field: the form's labels after it, and the footer's opening line.

    Only LATER labels end a field, so plain text such as `Literature: points 1 and 2.` inside the
    semestral field is content, not the start of another field.
    """

    labels = form_labels(rendering)
    return (*labels[labels.index(label) + 1 :], rendering.guidelines)


def _opens_with(line: str, labels: Sequence[str]) -> bool:
    return _indent(line) == LABEL_COLUMN and any(line.startswith(label) for label in labels)


def read_field(lines: Sequence[str], label: str, boundaries: Sequence[str]) -> _Field | None:
    """The first field `label` opens, read up to the next of `boundaries`; None when absent."""

    for index, line in enumerate(lines):
        if _opens_with(line, (label,)):
            body: list[str] = []
            for following in lines[index + 1 :]:
                if _opens_with(following, boundaries):
                    break
                body.append(following)
            return _Field(line[len(label) :].strip(), tuple(body))
    return None


def _content(line: str) -> str:
    """The line's text without a leading list marker: a bullet with nothing after it is no value.

    Only an indented marker is a list marker; plain text at the label column that reads `1.` is content.
    """

    text = line.strip()
    if _indent(line) <= LABEL_COLUMN:
        return text
    match = NUMBERED_ITEM_RE.match(text) or BULLET_ITEM_RE.match(text)
    return text[match.end() :].strip() if match else text


def _has_value(field: _Field | None) -> bool:
    return field is not None and (bool(_content(field.rest)) or any(_content(line) for line in field.body))


def _hangs(indent: int, item: _Item | None) -> bool:
    return item is not None and item.text_column is not None and abs(indent - item.text_column) <= COLUMN_TOLERANCE


def _opens_item(indent: int, item: _Item | None) -> bool:
    """A marker opens a new item at or left of the previous marker's column plus the tolerance.

    Further right it sits under the previous item's text, as a wrapped `2. generace` does. Column 0
    stays a new item, which the label-column finding then reports.
    """

    return item is None or item.text_column is None or indent <= item.indent + COLUMN_TOLERANCE


def _names(names: Sequence[str]) -> str:
    return ", ".join(dict.fromkeys(names))


def _parse_list(body: Sequence[str], numbered: bool) -> tuple[list[_Item], list[tuple[str, str]], list[str]]:
    """Items, the lines after an item that do not hang under its text, and text before any item.

    A line under the current item's text continues it even when it starts with a number, so a
    point that wraps before `2. generace` stays one point. A sub-list is not modelled: a nested
    item under the text reads as part of the item, one indented deeper as a line that does not hang.
    """

    marker = NUMBERED_ITEM_RE if numbered else BULLET_ITEM_RE
    typed = TYPED_POINT_RE if numbered else TYPED_BULLET_RE
    items: list[_Item] = []
    misaligned: list[tuple[str, str]] = []
    stray: list[str] = []
    for line in body:
        text = line.strip()
        if not text:
            continue
        indent = _indent(line)
        current = items[-1] if items else None
        match = marker.match(text)
        if match and _opens_item(indent, current):
            after = text[match.end() :].lstrip()
            column = indent + len(text) - len(after) if after else None
            number = int(match.group(1)) if numbered else None
            name = str(number) if numbered else str(len(items) + 1)
            items.append(_Item(name, number, indent, column is None, bool(typed.match(after)), column))
        elif _hangs(indent, current):
            continue
        elif current is None:
            stray.append(text)
        elif current.text_column is None:
            # The text below a marker that stood alone; later lines hang under it.
            current.text_column = indent
            current.doubled = bool(typed.match(text))
        else:
            misaligned.append((current.name, text))
    return items, misaligned, stray


def list_findings(label: str, field: _Field | None, *, numbered: bool) -> list[str]:
    """Findings for a field FIT IS prints as a list: numbered points, or literature bullets."""

    if field is None or not _has_value(field):
        return [f"`{label}` is missing or empty"]
    if field.rest:
        # Everything below would be read relative to a list that starts on the label's line.
        return [f"`{label}` has text on the label's own line, outside the list: {_quote(field.rest)}"]
    kind = "point" if numbered else "entry"
    items, misaligned, stray = _parse_list(field.body, numbered)
    if not items:
        listed = "numbered list" if numbered else "bullet list"
        return [f"`{label}` is not a {listed}; its first line is {_quote(stray[0])}"]
    findings: list[str] = []
    if stray:
        findings.append(f"`{label}` has text before its first {kind}, outside the list: {_quote(stray[0])}")
    at_margin = [item.name for item in items if item.indent <= LABEL_COLUMN]
    if at_margin:
        findings.append(
            f"`{label}` {kind} {_names(at_margin)} starts at the label column, so it is typed text, not a list item"
        )
    alone = [item.name for item in items if item.alone]
    if alone:
        findings.append(f"`{label}` {kind} {_names(alone)} has its marker on a line of its own and the text below it")
    doubled = [item.name for item in items if item.doubled]
    if doubled:
        findings.append(
            f"`{label}` {kind} {_names(doubled)} carries a typed marker of its own inside the list item; "
            "paste the text without it"
        )
    if misaligned:
        names = _names([name for name, _ in misaligned])
        findings.append(
            f"`{label}` has lines after {kind} {names} that do not hang under its text, "
            f"first: {_quote(misaligned[0][1])}"
        )
    numbers = [item.number for item in items]
    if numbered and numbers != list(range(1, len(items) + 1)):
        findings.append(f"`{label}` points are numbered {', '.join(map(str, numbers))}, not consecutively from 1")
    return findings


def check_export(text: str, *, language: str | None = None, allow_empty_semestral: bool = False) -> ExportCheck:
    """Check the `pdftotext -layout` text of one assignment export.

    `language` is the rendering the export must be (`cs` or `en`), the CZ/EN switch at the end of
    the FIT IS form; None accepts either. `allow_empty_semestral` is for a student who passed the
    first semester in the previous academic year, the one exception to a filled semestral field;
    an empty field accepted under it is returned as a note, not dropped silently.
    """

    pages = page_count(text)
    if not text.strip():
        return ExportCheck(None, None, pages, ("no text could be extracted; export the assignment PDF from FIT IS",))
    findings: list[str] = []
    if pages > 1:
        findings.append(
            f"the export has {pages} pages; the assignment must fit on one, so shorten the points or the "
            "literature and put the full version into `Komentář k zadání (netiskne se)`"
        )
    lines = text.replace(PAGE_BREAK, "\n").splitlines()
    header = recognised_header(lines)
    if header is None:
        titles = ", ".join(f"`{title}`" for rendering in RENDERINGS.values() for title in rendering.titles.values())
        findings.append(f"the first line is not a FIT IS assignment header; expected one of {titles}")
        return ExportCheck(None, None, pages, tuple(findings))
    rendering, variant = header
    if language is not None and rendering.key != language:
        findings.append(
            f"the export is the `{rendering.key}` rendering, not `{language}`; set the CZ/EN switch at the end "
            "of the FIT IS form to the thesis language and fill that version"
        )

    def field(label: str) -> _Field | None:
        return read_field(lines, label, later_labels(rendering, label))

    title = field(rendering.title_label)
    if title is None or not title.rest:
        findings.append(f"`{rendering.title_label}` is missing or empty")
    findings.extend(list_findings(rendering.points_label, field(rendering.points_label), numbered=True))
    findings.extend(list_findings(rendering.literature_label, field(rendering.literature_label), numbered=False))
    notes: list[str] = []
    if not _has_value(field(rendering.semestral_label)):
        if allow_empty_semestral:
            notes.append(f"`{rendering.semestral_label}` is empty, accepted under `--allow-empty-semestral`")
        else:
            findings.append(
                f"`{rendering.semestral_label}` is missing or empty; leave it empty only for a student who passed "
                "the first semester in the previous academic year (`--allow-empty-semestral`)"
            )
    return ExportCheck(rendering, variant, pages, tuple(findings), tuple(notes))
