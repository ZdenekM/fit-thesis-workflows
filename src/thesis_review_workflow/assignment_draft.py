"""Structural checks for an authored topic assignment bundle.

Everything here is decidable without judgment. Assessability, whether an open
point states a criterion, tone and topic quality belong to
`.agents/skills/thesis-assignment-review/SKILL.md`; this module exists so that
review round is not spent counting fields.

The FIT IS label sets live here rather than in the checker or the tests,
because `templates/assignment-formal.md`, the checker and
`tests/test_assignment_authoring.py` would otherwise each carry their own copy
and drift apart. See `docs/assignment-authoring.md`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from thesis_review_workflow.markdown_utils import section_body, section_text
from thesis_review_workflow.metadata import unresolved_values

VARIANTS_LABEL = "variants"
SUPPLEMENT_LABEL = "Supplement line:"
CITABLE_ARTIFACTS_HEADING = "## Citable Artifacts"
SHARED_BRIEF_HEADING = "## Shared Brief"
VARIANT_DELTA_HEADING = "## Variant Delta"

ASSIGNMENT_SECTIONS = (
    "### Header",
    "### Metadata",
    "### Assignment Points",
    "### Literature",
    "### Semestral Defence Requirement",
    "### Footer",
)

NUMBERED_POINT_RE = re.compile(r"^\s*\d+\.\s+\S")
# A variant is a path segment of `outputs/assignment_formal_<variant>.md`, so it is
# constrained here rather than trusted from the intake.
VARIANT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
BULLET_RE = re.compile(r"^\s*-\s+(\S.*)$")


@dataclass(frozen=True)
class Rendering:
    """One language rendering of the FIT IS assignment form."""

    key: str
    heading: str
    titles: dict[str, str]
    metadata: tuple[str, ...]
    optional_metadata: frozenset[str]
    points_label: str
    literature_label: str
    semestral_label: str
    footer: tuple[str, ...]


RENDERINGS: dict[str, Rendering] = {
    "cs": Rendering(
        key="cs",
        heading="## Czech Rendering",
        titles={"bp": "Zadání bakalářské práce", "dp": "Zadání diplomové práce"},
        metadata=("Ústav:", "Student:", "Program:", "Specializace:", "Název:", "Kategorie:", "Akademický rok:"),
        # `Specializace:` appears in a diplomová práce only.
        optional_metadata=frozenset({"Specializace:"}),
        points_label="Zadání:",
        literature_label="Literatura:",
        semestral_label="Při obhajobě semestrální části projektu je požadováno:",
        footer=("Vedoucí práce:", "Vedoucí ústavu:", "Datum zadání:", "Termín pro odevzdání:", "Datum schválení:"),
    ),
    "en": Rendering(
        key="en",
        heading="## English Rendering",
        titles={"bp": "Bachelor's Thesis Assignment", "dp": "Master's Thesis Assignment"},
        metadata=("Institut:", "Student:", "Programme:", "Specialization:", "Title:", "Category:", "Academic year:"),
        optional_metadata=frozenset({"Specialization:"}),
        points_label="Assignment:",
        literature_label="Literature:",
        semestral_label="Requirements for the semestral defence:",
        footer=("Supervisor:", "Head of Department:", "Beginning of work:", "Submission deadline:", "Approval date:"),
    ),
}


@dataclass(frozen=True)
class CitableArtifact:
    reference: str
    identifier: str


def _lines(text: str) -> list[str]:
    return text.splitlines()


def label_value(line: str, label: str) -> str | None:
    stripped = line.strip().removeprefix("- ").strip()
    if not stripped.startswith(label):
        return None
    return stripped[len(label) :].strip()


def declared_variants(intake: str) -> list[str]:
    """Variants the intake offers, from its `Variants:` field."""

    raw = read_fields_from_text(intake).get(VARIANTS_LABEL, "")
    return [part.strip() for part in raw.split("/") if part.strip()]


def read_fields_from_text(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip() and "\t" not in key:
            fields.setdefault(key.strip().lower(), value.strip())
    return fields


def citable_artifacts(intake: str) -> list[CitableArtifact]:
    """Entries authored under `## Citable Artifacts`, each a reference plus its identifier."""

    body = section_body(_lines(intake), CITABLE_ARTIFACTS_HEADING) or []
    artifacts: list[CitableArtifact] = []
    reference: str | None = None
    for line in body:
        found = label_value(line, "Reference:")
        if found is not None:
            if reference:
                artifacts.append(CitableArtifact(reference, ""))
            reference = found
            continue
        identifier = label_value(line, "Identifier:")
        if identifier is not None and reference is not None:
            artifacts.append(CitableArtifact(reference, identifier))
            reference = None
    if reference:
        artifacts.append(CitableArtifact(reference, ""))
    return [artifact for artifact in artifacts if artifact.reference]


def supplement_line(intake: str) -> str:
    body = section_body(_lines(intake), CITABLE_ARTIFACTS_HEADING) or []
    for line in body:
        value = label_value(line, SUPPLEMENT_LABEL)
        if value:
            return value
    return ""


def used_rendering(assignment: str) -> tuple[Rendering | None, list[str]]:
    """The single rendering block the author kept, or the reason there is not exactly one."""

    declared = read_fields_from_text(assignment).get("rendering", "")
    headings = [line.strip() for line in assignment.splitlines() if line.strip().startswith("## ")]
    by_heading = {rendering.heading: rendering for rendering in RENDERINGS.values()}
    # Count OCCURRENCES, not distinct languages: two Czech blocks are also not one block.
    present = [by_heading[heading] for heading in headings if heading in by_heading]
    if len(present) != 1:
        names = ", ".join(rendering.heading for rendering in present) or "none"
        return None, [
            f"expected exactly one rendering block, found {len(present)} ({names}); "
            "delete the rendering you are not using"
        ]
    rendering = present[0]
    findings: list[str] = []
    if declared not in RENDERINGS:
        findings.append(f"`Rendering:` is `{declared or '(empty)'}`; expected `cs` or `en`")
    elif declared != rendering.key:
        findings.append(f"`Rendering: {declared}` does not match the kept block `{rendering.heading}`")
    return rendering, findings


def form_labels(rendering: Rendering) -> tuple[str, ...]:
    """Every FIT IS label of one rendering, in form order.

    One sequence, used by the checker and by `tests/test_assignment_authoring.py`
    over `templates/assignment-formal.md`, so template and checker cannot drift.
    """

    return (
        *rendering.metadata,
        rendering.points_label,
        rendering.literature_label,
        rendering.semestral_label,
        *rendering.footer,
    )


def _ordered_labels_present(block: list[str], labels: tuple[str, ...]) -> list[str]:
    """The declared labels that open a line in `block`, in the order they appear."""

    wanted = set(labels)
    found: list[str] = []
    for line in block:
        for label in wanted:
            if line.strip().startswith(label):
                found.append(label)
                break
    return found


def assignment_findings(assignment: str, variant: str, artifacts: list[CitableArtifact], supplement: str) -> list[str]:
    findings: list[str] = []
    rendering, rendering_findings = used_rendering(assignment)
    findings.extend(rendering_findings)
    if rendering is None:
        return findings

    lines = _lines(assignment)
    block = section_body(lines, rendering.heading, stop_pattern=r"^#{1,2}\s+") or []

    positions = [assignment.find(section) for section in ASSIGNMENT_SECTIONS]
    if any(position < 0 for position in positions):
        missing = [section for section, position in zip(ASSIGNMENT_SECTIONS, positions) if position < 0]
        findings.append(f"missing section(s): {', '.join(missing)}")
    elif positions != sorted(positions):
        findings.append("sections are out of the FIT IS form order")

    expected_title = rendering.titles.get(variant)
    if expected_title and expected_title not in assignment:
        findings.append(f"header does not carry `{expected_title}` for variant `{variant}`")

    expected = form_labels(rendering)
    found = _ordered_labels_present(block, expected)
    for label in expected:
        if label not in rendering.optional_metadata and label not in found:
            findings.append(f"form label `{label}` is missing")
    in_form_order = [label for label in expected if label in found]
    if found != in_form_order:
        findings.append("form labels are not in the FIT IS field order")

    points_section = section_body(block, "### Assignment Points", stop_pattern=r"^#{1,3}\s+") or []
    if not any(NUMBERED_POINT_RE.match(line) for line in points_section):
        findings.append("no numbered assignment point under `### Assignment Points`")

    semestral = _section_after_label(block, rendering.semestral_label)
    if not semestral:
        findings.append(f"`{rendering.semestral_label}` is empty")

    findings.extend(_literature_findings(block, rendering, artifacts, supplement))
    return findings


def _section_after_label(block: list[str], label: str) -> str:
    for index, line in enumerate(block):
        if line.strip().startswith(label):
            inline = line.strip()[len(label) :].strip()
            if inline:
                return inline
            for candidate in block[index + 1 :]:
                if candidate.strip().startswith("#"):
                    break
                if candidate.strip():
                    return candidate.strip()
            return ""
    return ""


def _literature_findings(
    block: list[str], rendering: Rendering, artifacts: list[CitableArtifact], supplement: str
) -> list[str]:
    """Literature is checked by PROVENANCE, never by matching placeholder wording.

    `AGENTS.md` forbids a free-text heuristic as a gate, and the corpus
    placeholders are ordinary sentences. Structural provenance proves an entry
    came from the intake; it never proves the identifier resolves to a real work.

    The WHOLE `### Literature` section is consumed. Two narrower readings were
    tried and both leaked: scanning only `- ` bullets let a continuation or a
    plain line through, and stopping at the first `#` let a deeper heading hide
    unsourced citations behind it.
    """

    section = section_body(block, "### Literature", stop_pattern=r"^#{1,3}\s+")
    if section is None:
        return ["`### Literature` is missing"]

    findings: list[str] = []
    entries, stray = _literature_entries(section, rendering, findings)
    findings.extend(f"literature line is neither a bullet nor a continuation of one: {line}" for line in stray)

    references = {artifact.reference for artifact in artifacts}
    sourced = 0
    for entry in entries:
        if entry in references:
            sourced += 1
        elif supplement and entry == supplement:
            continue
        else:
            findings.append(f"literature entry is not authored in the intake's `{CITABLE_ARTIFACTS_HEADING}`: {entry}")
    if sourced == 0:
        findings.append(
            "no literature entry sourced from the intake; an empty or supplement-only literature block "
            "does not meet the generic base in `profiles/default.md`"
        )
    for artifact in artifacts:
        if artifact.reference in entries and not _resolved_identifier(artifact.identifier):
            findings.append(f"literature entry has no resolved identifier: {artifact.reference}")
    return findings


def _literature_entries(section: list[str], rendering: Rendering, findings: list[str]) -> tuple[list[str], list[str]]:
    """Bullets with their wrapped continuations joined, plus any line that is neither.

    Markdown wraps a long citation across indented lines, so a continuation is
    part of its entry rather than a separate one; anything else in the section is
    unaccounted text and is reported rather than ignored.
    """

    entries: list[str] = []
    stray: list[str] = []
    seen_label = False
    for line in section:
        stripped = line.strip()
        if not stripped:
            continue
        if not seen_label and stripped.startswith(rendering.literature_label):
            seen_label = True
            inline = stripped[len(rendering.literature_label) :].strip()
            if inline:
                findings.append(f"`{rendering.literature_label}` carries inline text; entries are bullets: {inline}")
            continue
        match = BULLET_RE.match(line)
        if match:
            entries.append(match.group(1).strip())
            continue
        if entries and line[:1].isspace():
            entries[-1] = f"{entries[-1]} {stripped}"
            continue
        stray.append(stripped)
    if not seen_label:
        findings.append(f"`{rendering.literature_label}` is missing")
    return entries, stray


def _resolved_identifier(identifier: str) -> bool:
    return bool(identifier.strip()) and not unresolved_values(f"Identifier: {identifier}")


def projection_delta_heading(variant: str) -> str:
    return f"## Variant Delta - {variant}"


def canonical_projection(shared: str, delta: str, variant: str) -> str:
    """The one shape `outputs/student_brief_<variant>.md` may have."""

    return "\n\n".join(
        [
            f"# Student Brief - {variant}",
            shared.strip(),
            projection_delta_heading(variant),
            delta.strip(),
        ]
    )


def brief_findings(source: str, projection: str, variant: str) -> list[str]:
    """A projection is compared WHOLE against the one canonical document.

    Comparing designated parts left the rest of the file unchecked: an
    obligation written into the title line passed. `docs/assignment-authoring.md`
    fixes the shape precisely so the comparison can be total.
    """

    shared = section_text(_lines(source), SHARED_BRIEF_HEADING, stop_pattern=r"^##\s+")
    if not shared:
        return [f"`{SHARED_BRIEF_HEADING}` is empty in the brief source"]
    own = _delta_body(source, variant)
    if not own:
        return [f"the brief source has no `### {variant}` delta"]

    expected = canonical_projection(shared, own, variant)
    if _normalized(projection) == _normalized(expected):
        return []
    return [
        "the projection is not exactly the shared brief body plus the "
        f"`### {variant}` delta in the canonical shape; see docs/assignment-authoring.md"
    ]


def _normalized(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if line.strip()).strip()


def _delta_body(source: str, variant: str) -> str:
    lines = _lines(source)
    delta = section_body(lines, VARIANT_DELTA_HEADING, stop_pattern=r"^##\s+")
    if delta is None:
        return ""
    return section_text(delta, f"### {variant}", stop_pattern=r"^#{1,3}\s+")


def unresolved_findings(label: str, text: str) -> list[str]:
    return [f"{label}:{number} unresolved value blocks publication: {description or '(unnamed)'}"
            for number, description in unresolved_values(text)]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""

