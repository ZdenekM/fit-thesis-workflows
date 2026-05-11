"""Validate final student-facing supervisor feedback output."""

from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import TypedDict

from thesis_review_workflow.commands import repo_command_environment, resolve_repo_command
from thesis_review_workflow.markdown_utils import is_delimiter_row, section_body, split_table_row
from thesis_review_workflow.paths import is_safe_round_relative_path

ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


class LanguageConfig(TypedDict):
    date_label: str
    scope_heading: str
    priority_heading: str
    checklist_heading: str
    priority_header: str
    evidence_header: str
    action_header: str
    scope_terms: tuple[str, ...]


LANGUAGE: dict[str, LanguageConfig] = {
    "cs": {
        "date_label": "Datum kontroly:",
        "scope_heading": "## Rozsah kontroly",
        "priority_heading": "## Nejvyšší priority pro aktuální iteraci",
        "checklist_heading": "## Checklist pro aktuální fázi",
        "priority_header": "priorita",
        "evidence_header": "kde se to projevuje",
        "action_header": "co udělat",
        "scope_terms": (
            "neověř",
            "neover",
            "nemohl",
            "nemohla",
            "nemohli",
            "neobsah",
            "omezen",
            "limit",
            "chyb",
            "nebyl",
            "nebyla",
            "nebylo",
            "bez omezení",
            "zadna omezeni",
            "žádná omezení",
        ),
    },
    "en": {
        "date_label": "Review date:",
        "scope_heading": "## Review Scope",
        "priority_heading": "## Highest Priorities for This Iteration",
        "checklist_heading": "## Checklist for the Current Phase",
        "priority_header": "priority",
        "evidence_header": "where it appears",
        "action_header": "what to do",
        "scope_terms": (
            "not checked",
            "not available",
            "unavailable",
            "limitation",
            "limited",
            "could not",
            "unable",
            "missing",
            "not provided",
            "no limitations",
            "without limitations",
        ),
    },
}

INTERNAL_PATTERNS = (
    r"\bcases/",
    r"\brounds/",
    r"\bfeedback_student\.md\b",
    r"\bcode_consistency\.md\b",
    r"\bcode_quality_review\.md\b",
    r"\bliterature_citation_review\.md\b",
    r"\bfigure_media_review\.md\b",
    r"\bvisual_inventory\.jsonl\b",
    r"\brevision_diff\.md\b",
    r"\bround-notes\.md\b",
    r"\bsupervisor-intake\.md\b",
    r"\bprevious-feedback-index\.md\b",
)

GENERIC_WORKFLOW_DIR_PATTERNS = (
    r"\bwork/",
    r"\boutputs/",
    r"\binputs/",
    r"\bextracted/",
)

PLACEHOLDER_PATTERNS = (
    r"\bYYYY-MM-DD\b",
    r"\bTBD\b",
    r"\blorem ipsum\b",
    r"^\s*(?:[-*]\s*)?TODO\s*:",
)
ANGLE_PLACEHOLDER_RE = re.compile(r"<([^>\n]+)>")
AUTOLINK_RE = re.compile(
    r"(?:https?://|mailto:)[^\s<>]+|[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+",
    re.IGNORECASE,
)

CONCRETE_ANCHORS = (
    "zadání",
    "zadani",
    "abstrakt",
    "závěr",
    "zaver",
    "kapitol",
    "část",
    "cast",
    "sekc",
    "tabulk",
    "obráz",
    "obraz",
    "readme",
    "kód",
    "kod",
    "soubor",
    "frontend",
    "backend",
    "package",
    "pdf",
    "video",
    "dotazník",
    "dotaznik",
    "sus",
    "assignment",
    "abstract",
    "conclusion",
    "chapter",
    "section",
    "table",
    "figure",
    "code",
    "appendix",
    "results",
    "experiment",
)

GENERIC_EVIDENCE = {
    "",
    "-",
    "n/a",
    "na",
    "todo",
    "tbd",
    "text",
    "práce",
    "prace",
    "celá práce",
    "cela prace",
    "celý dokument",
    "cely dokument",
    "dokument",
    "v textu",
    "text práce",
    "text prace",
    "thesis",
    "paper",
    "document",
    "whole document",
    "everywhere",
}

GENERIC_CHECKLIST = {
    "",
    "-",
    "todo",
    "tbd",
    "zkontrolovat",
    "upravit",
    "doplnit",
    "opravit",
    "zkontrolovat práci",
    "zkontrolovat praci",
    "upravit text",
    "doplnit text",
    "fix issues",
    "review",
    "revise text",
    "check thesis",
}


def usage() -> str:
    return "Usage: scripts/check-feedback-output [--artifact REL_PATH] CASE_ID [ROUND_ID]"


def repo_root() -> Path:
    output = subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return Path(output.strip())


def die_usage(message: str) -> None:
    print(message, file=sys.stderr)
    print(usage(), file=sys.stderr)
    raise SystemExit(2)


def validate_id(label: str, value: str) -> None:
    if not ID_RE.fullmatch(value):
        die_usage(f"Invalid {label}. Use only letters, numbers, dot, underscore, and dash.")


def read_language(case_md: Path) -> str:
    language = "cs"
    for line in case_md.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip().lower() == "student feedback language":
            language = value.strip().lower() or "cs"
            break
    return language


def run_language_check(root: Path, case_id: str, round_id: str, artifact: str, errors: list[str]) -> None:
    result = subprocess.run(
        resolve_repo_command(root, ["scripts/check-feedback-language", "--artifact", artifact, case_id, round_id]),
        cwd=root,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=repo_command_environment(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        detail = "\n".join(line for line in (result.stderr + result.stdout).splitlines() if line.strip())
        errors.append("language/heading check failed" + (f":\n{detail}" if detail else ""))


def run_supervisor_ready(root: Path, case_id: str, round_id: str, errors: list[str]) -> None:
    result = subprocess.run(
        resolve_repo_command(root, ["scripts/check-supervisor-ready", case_id, round_id]),
        cwd=root,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=repo_command_environment(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        detail = "\n".join(line for line in (result.stderr + result.stdout).splitlines() if line.strip())
        errors.append("supervisor readiness check failed" + (f":\n{detail}" if detail else ""))


def body_text(lines: list[str]) -> str:
    return "\n".join(line for line in lines if not re.match(r"^\s*#{1,6}\s+", line))


def normalized(value: str) -> str:
    value = re.sub(r"`([^`]*)`", r"\1", value)
    value = re.sub(r"\s+", " ", value.strip().lower())
    value = value.strip(" .;:-")
    return value


def find_review_date(text: str, lang: str, errors: list[str]) -> None:
    label = LANGUAGE[lang]["date_label"]
    pattern = re.compile(rf"^{re.escape(label)}\s*(.*)$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        errors.append(f"missing review date line: {label}")
        return

    value = match.group(1).strip()
    lowered = value.lower()
    if (
        not value
        or re.search(r"<[^>\n]+>", value)
        or "yyyy-mm-dd" in lowered
        or "current date" in lowered
        or "aktuální datum" in lowered
        or "aktualni datum" in lowered
        or re.fullmatch(r"(date|datum|tbd|todo)", lowered)
    ):
        errors.append(f"invalid placeholder review date: {value or '<empty>'}")
        return

    date_formats = (
        "%Y-%m-%d",
        "%d. %m. %Y",
        "%d.%m.%Y",
        "%B %d, %Y",
        "%b %d, %Y",
    )
    for date_format in date_formats:
        try:
            datetime.strptime(value, date_format)
            return
        except ValueError:
            pass

    errors.append(
        f"review date must be a real date in ISO YYYY-MM-DD, Czech D. M. YYYY, or English Month D, YYYY format: {value}"
    )


def check_scope(lines: list[str], lang: str, errors: list[str]) -> None:
    heading = LANGUAGE[lang]["scope_heading"]
    body = section_body(lines, heading)
    if body is None:
        errors.append(f"missing scope section: {heading}")
        return

    text = "\n".join(line.strip() for line in body).strip()
    compact = re.sub(r"\s+", " ", text)
    if len(compact) < 80:
        errors.append(f"scope section is too thin: {heading}")

    lowered = compact.lower()
    if not any(term in lowered for term in LANGUAGE[lang]["scope_terms"]):
        errors.append(f"scope section must state limitations or explicitly say none: {heading}")


def is_concrete_anchor(value: str) -> bool:
    lowered = normalized(value)
    if re.search(r"\d", value):
        return True
    if re.search(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value):
        return True
    if re.search(r"\b[A-Za-z0-9_-]+\.[A-Za-z0-9]{2,5}\b", value):
        return True
    return any(anchor in lowered for anchor in CONCRETE_ANCHORS)


def check_priority_table(lines: list[str], lang: str, errors: list[str], warnings: list[str]) -> None:
    heading = LANGUAGE[lang]["priority_heading"]
    body = section_body(lines, heading)
    if body is None:
        errors.append(f"missing priority section: {heading}")
        return

    table_lines = [line for line in body if line.strip().startswith("|")]
    if len(table_lines) < 3:
        errors.append("missing priority table in priority section")
        return

    rows = [split_table_row(line) for line in table_lines]
    header_index = None
    priority_header = LANGUAGE[lang]["priority_header"]
    for index, cells in enumerate(rows):
        if cells and normalized(cells[0]) == priority_header:
            header_index = index
            break
    if header_index is None:
        errors.append("priority table is missing the expected header row")
        return

    if header_index + 1 >= len(rows) or not is_delimiter_row(rows[header_index + 1]):
        errors.append("priority table is missing a Markdown delimiter row")
        return

    headers = [normalized(cell) for cell in rows[header_index]]
    evidence_header = LANGUAGE[lang]["evidence_header"]
    action_header = LANGUAGE[lang]["action_header"]
    required_headers = (priority_header, action_header, evidence_header)
    missing_headers = [header for header in required_headers if header not in headers]
    if missing_headers:
        errors.append("priority table is missing required column(s): " + ", ".join(missing_headers))
        return

    evidence_index = headers.index(evidence_header)
    action_index = headers.index(action_header)

    data_rows = rows[header_index + 2 :]
    priorities: list[tuple[str, list[str]]] = []
    for row_number, cells in enumerate(data_rows, start=1):
        if is_delimiter_row(cells):
            errors.append(f"priority table has an unexpected delimiter row at data row {row_number}")
            continue
        if len(cells) != len(headers):
            errors.append(f"malformed priority row {row_number}: expected {len(headers)} cells, got {len(cells)}")
            continue
        priority = cells[0].strip().upper()
        if priority not in {"P0", "P1", "P2"}:
            errors.append(f"unknown priority label in row {row_number}: {cells[0]}")
            continue
        priorities.append((priority, cells))

        if priority in {"P0", "P1"}:
            evidence = cells[evidence_index] if evidence_index < len(cells) else ""
            evidence_key = normalized(evidence)
            if evidence_key in GENERIC_EVIDENCE or not is_concrete_anchor(evidence):
                errors.append(f"{priority} row {row_number} needs concrete evidence in the evidence/location cell")

        action = normalized(cells[action_index])
        if action in GENERIC_CHECKLIST or len(action) < 20:
            warnings.append(f"priority row {row_number} may have a generic action")

    if not priorities:
        errors.append("priority table has no priority rows")
        return

    priority_count = len(priorities)
    if priority_count > 8:
        errors.append(f"too many priority rows: {priority_count}; maximum is 8")
    elif priority_count < 3 or priority_count > 6:
        warnings.append(f"priority row count is outside the ideal 3-6 range: {priority_count}")


def checklist_items(body: list[str]) -> list[str]:
    items = []
    for line in body:
        match = re.match(r"^\s*[-*]\s+(?:\[[ xX]\]\s+)?(.+?)\s*$", line)
        if match:
            items.append(match.group(1).strip())
    return items


def check_checklist(lines: list[str], lang: str, errors: list[str], warnings: list[str]) -> None:
    heading = LANGUAGE[lang]["checklist_heading"]
    body = section_body(lines, heading)
    if body is None:
        errors.append(f"missing checklist section: {heading}")
        return

    items = checklist_items(body)
    if len(items) < 3:
        errors.append("checklist section must contain at least three concrete items")
        return

    for index, item in enumerate(items, start=1):
        key = normalized(item)
        if key in GENERIC_CHECKLIST or len(key) < 15:
            errors.append(f"checklist item {index} is empty or generic")
        elif not is_concrete_anchor(item) and len(key) < 45:
            warnings.append(f"checklist item {index} may be too generic")


def check_internal_leaks(text: str, case_id: str, round_id: str, errors: list[str], warnings: list[str]) -> None:
    lowered = text.lower()
    if case_id.lower() in lowered:
        errors.append(f"student-facing feedback leaks the exact case id: {case_id}")
    if round_id.lower() in lowered:
        errors.append(f"student-facing feedback leaks the exact round id: {round_id}")

    if re.search(r"\b20\d{6}-\d{6}-[A-Za-z0-9_.-]+\b", text):
        errors.append("student-facing feedback contains a timestamp-like round id")
    if re.search(r"(?<!\w)/(?:home|Users|tmp|var|workspace|mnt)/[^\s)]+", text):
        errors.append("student-facing feedback contains an absolute filesystem path")
    if re.search(r"\b[A-Za-z]:\\[^\s)]+", text):
        errors.append("student-facing feedback contains a Windows absolute path")

    for pattern in INTERNAL_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            errors.append(f"student-facing feedback leaks internal workflow detail matching: {pattern}")

    for pattern in GENERIC_WORKFLOW_DIR_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            warnings.append(
                "feedback mentions a workflow-like directory name matching "
                f"{pattern}; verify it is a student project path, not local workflow detail"
            )


def check_placeholders(text: str, errors: list[str], warnings: list[str]) -> None:
    for match in ANGLE_PLACEHOLDER_RE.finditer(text):
        value = match.group(1).strip()
        if not AUTOLINK_RE.fullmatch(value):
            errors.append("leftover angle-bracket placeholder/template text")

    for pattern in PLACEHOLDER_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE):
            errors.append(f"leftover placeholder/template text matching: {pattern}")

    if re.search(r"\bTODO\b", text, flags=re.IGNORECASE):
        warnings.append("feedback mentions TODO; verify it is intentional student-facing wording")


def check_czech_diacritics(text: str, lines: list[str], errors: list[str], warnings: list[str]) -> None:
    plain = body_text(lines)
    letters = re.findall(r"[A-Za-zÁ-ž]", plain)
    if len(letters) < 300:
        return
    accents = re.findall(r"[áčďéěíňóřšťúůýžÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ]", plain)
    if not accents:
        errors.append("Czech feedback body contains no Czech diacritics")
        return
    ratio = len(accents) / max(len(letters), 1)
    if len(letters) > 800 and ratio < 0.003:
        warnings.append("Czech feedback body has unusually low Czech-diacritic density")


def main(argv: list[str]) -> int:
    args = argv[1:]
    if args == ["-h"] or args == ["--help"]:
        print(usage())
        return 0
    artifact = "outputs/feedback_student.md"
    if args[:1] == ["--artifact"]:
        if len(args) < 2:
            die_usage("--artifact requires a round-relative path.")
        artifact = args[1]
        args = args[2:]
    if len(args) not in {1, 2}:
        die_usage("Expected CASE_ID and optional ROUND_ID.")
    if not is_safe_round_relative_path(artifact):
        die_usage("--artifact must be a safe round-relative path.")

    case_id = args[0]
    validate_id("CASE_ID", case_id)
    root = repo_root()
    case_dir = root / "cases" / case_id
    if not case_dir.is_dir():
        print(f"ERROR: Case does not exist: cases/{case_id}", file=sys.stderr)
        return 1

    case_md = case_dir / "case.md"
    if not case_md.is_file():
        print(f"ERROR: Missing case metadata: cases/{case_id}/case.md", file=sys.stderr)
        return 1

    round_id = args[1] if len(args) == 2 else ""
    if round_id:
        validate_id("ROUND_ID", round_id)
    else:
        current_round = case_dir / "current-round.txt"
        if not current_round.is_file():
            print(f"ERROR: Missing current round: cases/{case_id}/current-round.txt", file=sys.stderr)
            return 1
        round_id = current_round.read_text(encoding="utf-8").strip()
        validate_id("ROUND_ID", round_id)

    lang = read_language(case_md)
    if lang not in LANGUAGE:
        print(
            f"ERROR: Unsupported Student feedback language in case.md: '{lang}'. Expected 'cs' or 'en'.",
            file=sys.stderr,
        )
        return 1

    round_dir = case_dir / "rounds" / round_id
    feedback = round_dir / artifact
    if not feedback.is_file():
        print(
            f"ERROR: Missing feedback output: cases/{case_id}/rounds/{round_id}/{artifact}",
            file=sys.stderr,
        )
        return 1

    errors: list[str] = []
    warnings: list[str] = []
    run_supervisor_ready(root, case_id, round_id, errors)
    run_language_check(root, case_id, round_id, artifact, errors)

    text = feedback.read_text(encoding="utf-8")
    lines = text.splitlines()
    find_review_date(text, lang, errors)
    check_scope(lines, lang, errors)
    check_priority_table(lines, lang, errors, warnings)
    check_checklist(lines, lang, errors, warnings)
    check_internal_leaks(text, case_id, round_id, errors, warnings)
    check_placeholders(text, errors, warnings)
    if lang == "cs":
        check_czech_diacritics(text, lines, errors, warnings)

    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"Feedback output check passed: {lang}")
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
