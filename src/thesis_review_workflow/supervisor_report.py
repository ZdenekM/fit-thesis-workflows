"""Supervisor-report artifact contracts and deterministic text checks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

from thesis_review_workflow.artifact_validation import sha256_file
from thesis_review_workflow.markdown_utils import section_text

SUPERVISOR_REPORT_INPUT_REL = "notes/supervisor-report-operator-input.md"
SUPERVISOR_REPORT_FEEDBACK_HISTORY_REL = "work/supervisor_report_feedback_history.json"
SUPERVISOR_REPORT_TRACE_REL = "work/supervisor_report_trace.json"
SUPERVISOR_REPORT_DRAFT_REL = "work/vedouci_posudek_draft.md"
SUPERVISOR_REPORT_REVIEWED_REL = "outputs/vedouci_posudek_revidovany.md"
SUPERVISOR_REPORT_REVIEW_REL = "work/reviews/supervisor_report_review.json"
SUPERVISOR_REPORT_CONFIRMATION_REL = "work/supervisor_report_confirmation.json"

SUPERVISOR_REPORT_TITLE_HEADINGS = ("# Návrh posudku vedoucího", "# Posudek vedoucího")
SUPERVISOR_REPORT_SECTION_HEADINGS = (
    "## Informace k zadání",
    "## Práce s literaturou",
    "## Aktivita během řešení, konzultace, komunikace",
    "## Aktivita při dokončování",
    "## Publikační činnost, ocenění",
    "## Celkové hodnocení",
    "## Komentář pro studenta",
)

SUPERVISOR_REPORT_HEADINGS = (*SUPERVISOR_REPORT_TITLE_HEADINGS[:1], *SUPERVISOR_REPORT_SECTION_HEADINGS)
SUPERVISOR_REPORT_PUBLIC_HEADINGS = SUPERVISOR_REPORT_SECTION_HEADINGS[:-1]
SUPERVISOR_REPORT_PRIVATE_HEADING = SUPERVISOR_REPORT_SECTION_HEADINGS[-1]

PLACEHOLDER_PATTERNS = (
    r"\bTBD\b",
    r"\bTODO\b",
    r"\bFIXME\b",
    r"\blorem ipsum\b",
    r"\bYYYY-MM-DD\b",
    r"<[^>\n]+>",
)

INTERNAL_PATTERNS = (
    r"(?<!\w)/(?:home|Users|tmp|var|workspace|mnt)/[^\s)\"']*",
    r"\bcases/",
    r"\brounds/",
    r"\bwork/",
    r"\bnotes/",
    r"\bprofiles/",
    r"\boutputs/",
    r"\binputs/",
    r"\bextracted/",
    r"\breview_manifest\.json\b",
    r"\bagent_coverage\.json\b",
    r"\bfeedback_student(?:_draft)?\.md\b",
    r"\bvedouci_posudek_draft\.md\b",
    r"\bvedouci_posudek_revidovany\.md\b",
    r"\bsupervisor_report_(?:trace|feedback_history|confirmation)\.json\b",
    r"\bgithub_code_intake\.md\b",
    r"\brevision_diff\.md\b",
    r"\bcode_consistency\.md\b",
    r"\bcode_quality_review\.md\b",
    r"\bfigure_media_review\.md\b",
    r"\btypography_formal_review\.md\b",
)

TRACE_PATH_RE = re.compile(r"<!--\s*source_trace_path:\s*([^>]+?)\s*-->")
TRACE_SHA_RE = re.compile(r"<!--\s*source_trace_sha256:\s*([0-9a-f]{64})\s*-->")
INPUT_PATH_RE = re.compile(r"<!--\s*supervisor_input_path:\s*([^>]+?)\s*-->")
INPUT_SHA_RE = re.compile(r"<!--\s*supervisor_input_sha256:\s*([0-9a-f]{64})\s*-->")
GRADE_RE = re.compile(r"\b(?:Známka|Znamka)\s*:\s*([A-F])\b", re.IGNORECASE)
POINT_RE = re.compile(r"\b(?:Body|Bodové hodnocení|Bodove hodnoceni)\s*:\s*(\d{1,3})\b", re.IGNORECASE)

GRADE_VALUES = {"A", "B", "C", "D", "E", "F"}
UNDECIDED_MARKERS = {"", "nerozhodnuto", "nevim", "nevím", "unknown", "do not decide"}


@dataclass(frozen=True)
class IntakeCheckResult:
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


class GradePoints(NamedTuple):
    grade: str | None
    points: int | None
    errors: tuple[str, ...] = ()


def strip_metadata_comments(text: str) -> str:
    return re.sub(
        r"^<!--\s*(?:source_trace|supervisor_input)_(?:path|sha256):.*?-->\s*\n?",
        "",
        text,
        flags=re.MULTILINE,
    )


def public_report_text(text: str) -> str:
    lines = strip_metadata_comments(text).splitlines()
    result: list[str] = []
    in_private = False
    for line in lines:
        if line == SUPERVISOR_REPORT_PRIVATE_HEADING:
            in_private = True
            continue
        if in_private and line.startswith("## "):
            in_private = False
        if not in_private:
            result.append(line)
    return "\n".join(result)


def section_has_content(lines: list[str], heading: str) -> bool:
    body = section_text(lines, heading, stop_pattern=r"^##\s+")
    return bool(body and not re.fullmatch(r"[-\s]*", body))


def validate_report_markdown(text: str, *, require_grade_points: bool) -> list[str]:
    errors: list[str] = []
    lines = strip_metadata_comments(text).splitlines()
    title_indices = [index for index, line in enumerate(lines) if line in SUPERVISOR_REPORT_TITLE_HEADINGS]
    if not title_indices:
        choices = " or ".join(SUPERVISOR_REPORT_TITLE_HEADINGS)
        errors.append(f"missing required heading: {choices}")
    else:
        title_index = title_indices[0]
        if any(line.strip() for line in lines[:title_index]):
            errors.append("unexpected text before supervisor report title")
        first_section_index = next(
            (
                index
                for index, line in enumerate(lines[title_index + 1 :], start=title_index + 1)
                if line.startswith("## ")
            ),
            None,
        )
        if first_section_index is not None and any(
            line.strip() for line in lines[title_index + 1 : first_section_index]
        ):
            errors.append("unexpected text between supervisor report title and first section")
    for heading in SUPERVISOR_REPORT_SECTION_HEADINGS:
        if heading not in lines:
            errors.append(f"missing required heading: {heading}")
        elif heading.startswith("## ") and not section_has_content(lines, heading):
            errors.append(f"empty supervisor report section: {heading}")

    visible_text = strip_metadata_comments(text)
    public_text = public_report_text(text)
    for pattern in PLACEHOLDER_PATTERNS:
        if re.search(pattern, visible_text, re.IGNORECASE | re.MULTILINE):
            errors.append(f"placeholder remains in supervisor report: {pattern}")
    for pattern in INTERNAL_PATTERNS:
        if re.search(pattern, visible_text, re.IGNORECASE):
            errors.append(f"internal workflow path or artifact leaked into supervisor report: {pattern}")

    points = [int(match.group(1)) for match in POINT_RE.finditer(public_text)]
    grades = [match.group(1).upper() for match in GRADE_RE.finditer(public_text)]
    if require_grade_points:
        if not grades:
            errors.append("concrete grade is required before supervisor report can pass")
        if not points:
            errors.append("concrete point value is required before supervisor report can pass")
    for value in points:
        if value < 0 or value > 100:
            errors.append(f"point value outside 0-100 range: {value}")
    return errors


def extract_markdown_grade_points(text: str, *, require: bool = False) -> GradePoints:
    public_text = public_report_text(text)
    grades = [match.group(1).upper() for match in GRADE_RE.finditer(public_text)]
    points = [int(match.group(1)) for match in POINT_RE.finditer(public_text)]
    errors: list[str] = []
    unique_grades = sorted(set(grades))
    unique_points = sorted(set(points))
    if len(unique_grades) > 1:
        errors.append("supervisor report contains conflicting grade values")
    if len(unique_points) > 1:
        errors.append("supervisor report contains conflicting point values")
    if require and not unique_grades:
        errors.append("supervisor report is missing grade")
    if require and not unique_points:
        errors.append("supervisor report is missing points")
    return GradePoints(
        grade=unique_grades[0] if len(unique_grades) == 1 else None,
        points=unique_points[0] if len(unique_points) == 1 else None,
        errors=tuple(errors),
    )


def trace_grade_points(trace: dict[str, object]) -> GradePoints:
    grading = trace.get("grading")
    if not isinstance(grading, dict):
        return GradePoints(None, None, ("trace grading must be object",))
    grade = grading.get("grade")
    points = grading.get("points")
    normalized_grade = grade if isinstance(grade, str) and grade in GRADE_VALUES else None
    normalized_points = points if isinstance(points, int) else None
    return GradePoints(normalized_grade, normalized_points, ())


def confirmation_grade_points(confirmation: dict[str, object]) -> GradePoints:
    grade = confirmation.get("grade")
    points = confirmation.get("points")
    normalized_grade = grade if isinstance(grade, str) and grade in GRADE_VALUES else None
    normalized_points = points if isinstance(points, int) else None
    return GradePoints(normalized_grade, normalized_points, ())


def validate_draft_metadata(text: str, round_dir: Path, errors: list[str]) -> None:
    trace_path = round_dir / SUPERVISOR_REPORT_TRACE_REL
    input_path = round_dir / SUPERVISOR_REPORT_INPUT_REL
    _validate_metadata_pair(
        text,
        errors,
        path_re=TRACE_PATH_RE,
        sha_re=TRACE_SHA_RE,
        expected_rel=SUPERVISOR_REPORT_TRACE_REL,
        expected_path=trace_path,
        label="source trace",
    )
    _validate_metadata_pair(
        text,
        errors,
        path_re=INPUT_PATH_RE,
        sha_re=INPUT_SHA_RE,
        expected_rel=SUPERVISOR_REPORT_INPUT_REL,
        expected_path=input_path,
        label="supervisor input",
    )


def _validate_metadata_pair(
    text: str,
    errors: list[str],
    *,
    path_re: re.Pattern[str],
    sha_re: re.Pattern[str],
    expected_rel: str,
    expected_path: Path,
    label: str,
) -> None:
    path_match = path_re.search(text)
    sha_match = sha_re.search(text)
    if not path_match:
        errors.append(f"missing {label} path metadata comment")
    elif path_match.group(1).strip() != expected_rel:
        errors.append(f"{label} path metadata must be {expected_rel}, got {path_match.group(1).strip()}")
    if not sha_match:
        errors.append(f"missing {label} sha256 metadata comment")
    elif expected_path.is_file() and sha_match.group(1) != sha256_file(expected_path):
        errors.append(f"supervisor report draft is stale: {label} hash changed")


def check_supervisor_report_intake(round_dir: Path) -> IntakeCheckResult:
    path = round_dir / SUPERVISOR_REPORT_INPUT_REL
    errors: list[str] = []
    warnings: list[str] = []
    if not path.is_file():
        return IntakeCheckResult(
            errors=(
                f"missing supervisor report intake: {SUPERVISOR_REPORT_INPUT_REL}",
                "Create it from templates/supervisor-report-intake.md.",
            ),
            warnings=(),
        )
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    for section, labels in (
        (
            "## Informace k zadani",
            (
                "Narocnost prace",
                "Spokojenost s dosazenymi vysledky",
                "Splneni zadani",
            ),
        ),
        (
            "## Publikacni cinnost, oceneni",
            (
                "Publikace",
                "Open-source zverejneni softwaru",
                "Ohlasy",
                "Oceneni",
                "Pokud nic z toho neni, jak to formulovat",
            ),
        ),
        (
            "## Komentar pro studenta",
            (
                "Soukromy komentar viditelny studentovi v IS",
                "Motivace / rada do budoucna",
                "Co se nehodi do oficialni casti, ale chci studentovi rict",
            ),
        ),
    ):
        body = section_text(lines, section, stop_pattern=r"^##\s+")
        if not body:
            errors.append(f"{SUPERVISOR_REPORT_INPUT_REL}: missing section {section}")
            continue
        values = labeled_values(body)
        if not any(_explicit_value(values.get(label)) for label in labels):
            joined = ", ".join(labels)
            errors.append(f"{SUPERVISOR_REPORT_INPUT_REL}: section {section} must fill at least one of {joined}")
    for section, process_labels, unknown_label in (
        (
            "## Prace s literaturou",
            ("Aktivita studenta pri ziskavani materialu", "Jak student materialy vyuzival"),
            "Co je explicitne nezname / nehodnotit",
        ),
        (
            "## Aktivita behem reseni, konzultace, komunikace",
            (
                "Aktivita a samostatnost",
                "Dodrzovani dohodnutych terminu",
                "Prubezne konzultace",
                "Pripravenost na konzultace",
                "Komunikace",
            ),
            "Co je explicitne nezname / nehodnotit",
        ),
        (
            "## Aktivita pri dokoncovani",
            ("Dokonceni s predstihem", "Konzultace definitivniho obsahu", "Posledni faze prace"),
            "Co je explicitne nezname / nehodnotit",
        ),
    ):
        body = section_text(lines, section, stop_pattern=r"^##\s+")
        if not body:
            errors.append(f"{SUPERVISOR_REPORT_INPUT_REL}: missing section {section}")
            continue
        values = labeled_values(body)
        unknown = _explicit_value(values.get(unknown_label))
        missing = [label for label in process_labels if not _explicit_value(values.get(label))]
        if missing and not unknown:
            joined = ", ".join(missing)
            errors.append(f"{SUPERVISOR_REPORT_INPUT_REL}: section {section} must fill {joined} " f"or {unknown_label}")

    overall = section_text(lines, "## Celkove hodnoceni", stop_pattern=r"^##\s+")
    if not overall:
        errors.append(f"{SUPERVISOR_REPORT_INPUT_REL}: missing section ## Celkove hodnoceni")
    else:
        values = labeled_values(overall)
        errors.extend(validate_grade_text(values.get("Navrhovana znamka", ""), SUPERVISOR_REPORT_INPUT_REL))
        errors.extend(validate_points_text(values.get("Navrhovane body", ""), SUPERVISOR_REPORT_INPUT_REL))
    prior = section_text(lines, "## Vztah k predchozi zpetne vazbe", stop_pattern=r"^##\s+")
    if not prior:
        warnings.append(f"{SUPERVISOR_REPORT_INPUT_REL}: prior-feedback section is absent")
    return IntakeCheckResult(errors=tuple(errors), warnings=tuple(warnings))


def labeled_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    current_label: str | None = None
    current_lines: list[str] = []
    for line in text.splitlines():
        match = re.match(r"^([^:#\n][^:\n]{1,120}):\s*(.*)$", line)
        if match:
            if current_label is not None:
                values[current_label] = "\n".join(current_lines).strip()
            current_label = match.group(1).strip()
            current_lines = [match.group(2).strip()] if match.group(2).strip() else []
            continue
        if current_label is not None:
            stripped = line.strip()
            if stripped and not stripped.startswith("## "):
                current_lines.append(stripped)
    if current_label is not None:
        values[current_label] = "\n".join(current_lines).strip()
    return values


def _explicit_value(value: str | None) -> bool:
    return bool(value and value.strip() and value.strip() not in {"-", "TODO", "TODO:"})


def validate_grade_text(value: str, label: str) -> list[str]:
    normalized = value.strip()
    if normalized.casefold() in UNDECIDED_MARKERS:
        return []
    if normalized.upper() in GRADE_VALUES:
        return []
    return [f"{label}: Navrhovana znamka must be A-F or nerozhodnuto"]


def validate_points_text(value: str, label: str) -> list[str]:
    normalized = value.strip()
    if normalized.casefold() in UNDECIDED_MARKERS:
        return []
    numbers = [int(item) for item in re.findall(r"\b\d{1,3}\b", normalized)]
    if not numbers:
        return [f"{label}: Navrhovane body must be 0-100, interval, or nerozhodnuto"]
    if any(number < 0 or number > 100 for number in numbers):
        return [f"{label}: Navrhovane body contains value outside 0-100"]
    return []
