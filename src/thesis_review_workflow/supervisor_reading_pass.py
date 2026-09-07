"""Contract for the supervisor's own reading pass over a thesis artifact.

This module is the single owner of the reading-pass round path, its routing enum
and its structural parser. Every consumer - packets, current evidence, review
deltas, the leak checks and the validator CLI - reads them from here, so a new
consumer cannot quietly disagree about the path or the allowed routing values.

The parser is deliberately structural: it reads known labels and a fixed enum and
never interprets the operator's prose. Deciding what an observation means stays
with the authorized agent workflow that consumes it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from thesis_review_workflow.markdown_utils import normalized_text, section_body

SUPERVISOR_READING_PASS_REL = "notes/supervisor-reading-pass.md"
SUPERVISOR_READING_PASS_TEMPLATE = "templates/supervisor-reading-pass-intake.md"

OBSERVATIONS_HEADING = "## Poznamky"
OBSERVATION_LABELS = ("Pozorovani:", "Evidence:", "Routing:")

ROUTING_VALUES = ("student_feedback", "internal_only", "verify_first", "discard")
"""Allowed `Routing:` values, in the order the template documents them."""

ROUTING_ALLOWING_UNVERIFIED_EVIDENCE = ("verify_first", "discard")
UNVERIFIED_EVIDENCE_TOKEN = "neoverovano"

METADATA_LABELS = (
    "Cteny artefakt:",
    "Datum cteni:",
    "Forma zapisu:",
    "Rozsah cteni:",
    "Co jsem necetl:",
)
METADATA_LABELS_REQUIRING_VALUE = (
    "Cteny artefakt:",
    "Datum cteni:",
    "Rozsah cteni:",
)

# Deliberately separate from the opponent-materials evidence gate: that set guards a
# sendable artifact, this one guards an operator note, and the two are free to differ.
GENERIC_EVIDENCE_VALUES = frozenset(
    {
        "",
        "-",
        "n/a",
        "na",
        "todo",
        "tbd",
        "text",
        "prace",
        "práce",
        "cela prace",
        "celá práce",
        "cely dokument",
        "celý dokument",
        "dokument",
        "v textu",
        "text prace",
        "text práce",
        "thesis",
        "document",
        "whole document",
        "everywhere",
    }
)

OBSERVATION_HEADING_RE = re.compile(r"^#{3,}\s*(.*?)\s*$")


@dataclass(frozen=True)
class ReadingPassObservation:
    title: str
    line_number: int
    fields: dict[str, str] = field(default_factory=dict)
    duplicate_labels: list[str] = field(default_factory=list)


def reading_pass_path(round_dir: Path) -> Path:
    return round_dir / SUPERVISOR_READING_PASS_REL


def label_value(line: str, label: str) -> str | None:
    if not line.startswith(label):
        return None
    return line[len(label) :].strip()


def observations_section_bounds(lines: list[str]) -> tuple[int, int] | None:
    """Half-open line range of the observations section body, or None when it is absent."""

    body = section_body(lines, OBSERVATIONS_HEADING)
    if body is None:
        return None
    start = next(index for index, line in enumerate(lines) if line.strip() == OBSERVATIONS_HEADING) + 1
    return start, start + len(body)


def parse_observations(lines: list[str]) -> list[ReadingPassObservation]:
    """Observation blocks inside the observations section, in document order.

    A block runs from its heading of level three or deeper to the next heading of any
    level, so a `####` sub-heading starts its own block rather than having its fields
    silently merged into the parent. Labels are matched at line start, so prose
    mentioning a label mid-sentence is not a field.
    """

    bounds = observations_section_bounds(lines)
    if bounds is None:
        return []
    start, end = bounds

    observations: list[ReadingPassObservation] = []
    current: ReadingPassObservation | None = None
    for offset in range(start, end):
        line = lines[offset]
        heading = OBSERVATION_HEADING_RE.match(line)
        if heading:
            current = ReadingPassObservation(title=heading.group(1), line_number=offset + 1)
            observations.append(current)
            continue
        if current is None:
            continue
        for label in OBSERVATION_LABELS:
            value = label_value(line, label)
            if value is None:
                continue
            if label in current.fields:
                current.duplicate_labels.append(label)
            else:
                current.fields[label] = value
            break
    return observations


def stray_observation_content(lines: list[str]) -> list[str]:
    """Observation headings and labels outside the observations section.

    The section is the only place the consuming workflow reads, so content that looks
    like an observation but sits outside it must fail loudly rather than be skipped in
    silence: these files are long dictations, and a second `## ` heading is an easy way
    to lose half of one.
    """

    bounds = observations_section_bounds(lines)
    inside = range(*bounds) if bounds is not None else range(0)
    stray: list[str] = []
    for index, line in enumerate(lines):
        if index in inside:
            continue
        if OBSERVATION_HEADING_RE.match(line):
            stray.append(f"line {index + 1}: observation heading outside {OBSERVATIONS_HEADING}: {line.strip()}")
            continue
        for label in OBSERVATION_LABELS:
            if label_value(line, label) is not None:
                stray.append(f"line {index + 1}: {label} outside {OBSERVATIONS_HEADING}")
                break
    return stray


def validate_reading_pass_text(text: str) -> tuple[list[str], list[str]]:
    """Structural errors and warnings for a filled reading pass.

    The caller decides what an absent file means; this function assumes the file
    exists and was read.
    """

    errors: list[str] = []
    warnings: list[str] = []
    lines = text.splitlines()

    for label in METADATA_LABELS:
        matches = [line for line in lines if line.startswith(label)]
        if not matches:
            errors.append(f"missing metadata label: {label}")
            continue
        if label in METADATA_LABELS_REQUIRING_VALUE and not (label_value(matches[0], label) or ""):
            errors.append(f"metadata label has no value: {label}")

    if not any(line.strip() == OBSERVATIONS_HEADING for line in lines):
        errors.append(f"missing observations heading: {OBSERVATIONS_HEADING}")
        return errors, warnings

    errors.extend(stray_observation_content(lines))
    observations = parse_observations(lines)
    if not observations:
        errors.append(f"no observation blocks under {OBSERVATIONS_HEADING}; a reading pass needs at least one")
        return errors, warnings

    for observation in observations:
        prefix = f"line {observation.line_number} ({observation.title or 'untitled'})"
        if not observation.title:
            errors.append(f"{prefix}: observation heading has no title")
        for label in dict.fromkeys(observation.duplicate_labels):
            errors.append(
                f"{prefix}: {label} appears more than once; a dictated correction must replace the "
                "first value, not sit beside it"
            )
        missing = [label for label in OBSERVATION_LABELS if label not in observation.fields]
        if missing:
            errors.append(f"{prefix}: missing {', '.join(missing)}")
            continue
        if not observation.fields["Pozorovani:"]:
            errors.append(f"{prefix}: Pozorovani is empty")
        evidence = normalized_text(observation.fields["Evidence:"])
        routing = normalized_text(observation.fields["Routing:"])
        if evidence in GENERIC_EVIDENCE_VALUES:
            errors.append(
                f"{prefix}: Evidence is generic; name a chapter, section, page, file, figure or table, "
                f"or the token {UNVERIFIED_EVIDENCE_TOKEN}"
            )
        if routing not in ROUTING_VALUES:
            errors.append(f"{prefix}: Routing must be one of {', '.join(ROUTING_VALUES)}, got {routing or 'empty'}")
        elif evidence == UNVERIFIED_EVIDENCE_TOKEN and routing not in ROUTING_ALLOWING_UNVERIFIED_EVIDENCE:
            errors.append(
                f"{prefix}: unverified evidence must route to "
                f"{' or '.join(ROUTING_ALLOWING_UNVERIFIED_EVIDENCE)}, got {routing}"
            )

    unverified = sum(
        1
        for observation in observations
        if normalized_text(observation.fields.get("Evidence:", "")) == UNVERIFIED_EVIDENCE_TOKEN
    )
    if unverified == len(observations):
        warnings.append("every observation is unverified; nothing in this pass can reach student feedback as it stands")
    return errors, warnings


def routing_counts(text: str) -> dict[str, int]:
    """Observation count per routing value, for operator-facing summaries."""

    counts = dict.fromkeys(ROUTING_VALUES, 0)
    for observation in parse_observations(text.splitlines()):
        routing = normalized_text(observation.fields.get("Routing:", ""))
        if routing in counts:
            counts[routing] += 1
    return counts
