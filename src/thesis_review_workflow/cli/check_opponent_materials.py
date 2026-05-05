"""Validate reviewed opponent-materials output shape and hygiene."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")

REQUIRED_HEADINGS = (
    "# Revidovane podklady pro oponentsky posudek",
    "## 1. Rozsah kontroly",
    "## 2. Strucna mapa prace",
    "## 3. Splneni zadani",
    "## 4. Technicke jadro prace vysvetlene oponentovi",
    "## 5. Mapa textu, kodu a artefaktu",
    "## 6. Evidence ledger: hlavni tvrzeni a opora",
    "## 7. Silne stranky",
    "## 8. Hlavni rizika a nedostatky",
    "## 9. Pokryti polozek IS a navrhy formulaci",
    "## 10. Technicka spravnost a realizacni vystup",
    "## 11. Experimenty, vysledky a reprodukovatelnost",
    "## 12. Text, struktura, formalni stranka a literatura",
    "## 13. Orientacni kalibrace hodnoceni",
    "## 14. Navrhy otazek k obhajobe",
    "## 15. Rucni kontroly pred napsanim posudku",
)

SCOPE_TERMS = (
    "neover",
    "neověř",
    "nebyl",
    "nebyla",
    "nebylo",
    "nejsou",
    "nelze",
    "chybi",
    "chybí",
    "omezen",
    "limit",
    "manual",
    "rucni",
    "ruční",
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
    "bez omezeni",
    "bez omezení",
    "zadna omezeni",
    "žádná omezení",
)

CONFIDENCE_LABELS = {
    "[FAKT]",
    "[INTERPRETACE]",
    "[ODHAD]",
    "[NEOVERENO]",
    "[NEOVĚŘENO]",
    "[K RUCNI KONTROLE]",
    "[K RUČNÍ KONTROLE]",
}

PRIORITIES = {"P0", "P1", "P2", "P3"}

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

DRAFT_ARTIFACT_PATTERNS = (
    r"\boponent_podklady_draft\.md\b",
    r"\bfeedback_student_draft\.md\b",
    r"\bwork/oponent_podklady_draft\.md\b",
)

INTERNAL_WORKFLOW_PATTERNS = (
    r"\bfigure_media_review\.md\b",
    r"\bvisual_inventory\.jsonl\b",
    r"\bfeedback_student\.md\b",
    r"\bround-notes\.md\b",
    r"\bsupervisor-intake\.md\b",
    r"\bprevious-feedback-index\.md\b",
)

GENERIC_EVIDENCE = {
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
    "paper",
    "document",
    "whole document",
    "everywhere",
}

GENERIC_ITEMS = {
    "",
    "-",
    "todo",
    "tbd",
    "zkontrolovat",
    "upravit",
    "doplnit",
    "opravit",
    "review",
    "check",
    "manual check",
    "rucni kontrola",
    "ruční kontrola",
}

CONCRETE_ANCHORS = (
    "zadani",
    "zadání",
    "abstrakt",
    "zaver",
    "závěr",
    "kapitol",
    "cast",
    "část",
    "sekc",
    "tabulk",
    "obraz",
    "obrazek",
    "obráz",
    "readme",
    "kod",
    "kód",
    "soubor",
    "pdf",
    "video",
    "poster",
    "appendix",
    "priloha",
    "příloha",
    "dataset",
    "experiment",
    "vysled",
    "výsled",
    "metrik",
    "bibliograph",
    "bibliography",
    "literatur",
    "src",
    "assignment",
    "chapter",
    "section",
    "table",
    "figure",
    "code",
    "results",
)

REQUIRED_IS_AREAS = (
    "narocnost",
    "rozsah splneni",
    "rozsah technicke",
    "prezentacni",
    "formalni",
    "literatur",
    "realizacni",
    "vyuzitelnost",
    "celkove",
)


def usage() -> str:
    return "Usage: scripts/check-opponent-materials CASE_ID [ROUND_ID]"


def repo_root() -> Path:
    output = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True)
    return Path(output.strip())


def die_usage(message: str) -> None:
    print(message, file=sys.stderr)
    print(usage(), file=sys.stderr)
    raise SystemExit(2)


def validate_id(label: str, value: str) -> None:
    if not ID_RE.fullmatch(value):
        die_usage(f"Invalid {label}. Use only letters, numbers, dot, underscore, and dash.")


def resolve_round(case_dir: Path, round_id: str | None) -> str:
    if round_id:
        validate_id("ROUND_ID", round_id)
        return round_id

    current_round = case_dir / "current-round.txt"
    if not current_round.is_file():
        die_usage(f"Missing current round: {case_dir.relative_to(case_dir.parents[1])}/current-round.txt")
    resolved = current_round.read_text(encoding="utf-8").strip()
    validate_id("ROUND_ID", resolved)
    return resolved


def run_round_ready(root: Path, case_id: str, round_id: str, errors: list[str]) -> None:
    result = subprocess.run(
        [str(root / "scripts/check-round-ready"), case_id, round_id],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        detail = "\n".join(line for line in (result.stderr + result.stdout).splitlines() if line.strip())
        errors.append("round readiness check failed" + (f":\n{detail}" if detail else ""))


def normalized(value: str) -> str:
    value = re.sub(r"`([^`]*)`", r"\1", value)
    value = value.replace("ě", "e").replace("š", "s").replace("č", "c")
    value = value.replace("ř", "r").replace("ž", "z").replace("ý", "y")
    value = value.replace("á", "a").replace("í", "i").replace("é", "e")
    value = value.replace("ú", "u").replace("ů", "u").replace("ň", "n")
    value = value.replace("ť", "t").replace("ď", "d")
    value = re.sub(r"\s+", " ", value.strip().lower())
    return value.strip(" .;:-")


def section_body(lines: list[str], heading: str) -> list[str] | None:
    start = None
    for index, line in enumerate(lines):
        if line.strip() == heading:
            start = index + 1
            break
    if start is None:
        return None

    end = len(lines)
    for index in range(start, len(lines)):
        if re.match(r"^#{1,2}\s+", lines[index]):
            end = index
            break
    return lines[start:end]


def section_text(lines: list[str], heading: str) -> str:
    body = section_body(lines, heading)
    if body is None:
        return ""
    return "\n".join(body).strip()


def split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    in_code = False

    for char in stripped:
        if char == "\\" and not escaped:
            current.append(char)
            escaped = True
            continue
        if char == "`" and not escaped:
            in_code = not in_code
        if char == "|" and not escaped and not in_code:
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(char)
        escaped = False

    cells.append("".join(current).strip())
    if cells and cells[0] == "":
        cells = cells[1:]
    if cells and cells[-1] == "":
        cells = cells[:-1]
    return cells


def is_delimiter_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def extract_table(body: list[str]) -> tuple[list[str], list[list[str]], str | None]:
    table_lines = [line for line in body if line.strip().startswith("|")]
    if len(table_lines) < 3:
        return [], [], "missing Markdown table"

    rows = [split_table_row(line) for line in table_lines]
    header_index = None
    for index, cells in enumerate(rows):
        if index + 1 < len(rows) and is_delimiter_row(rows[index + 1]):
            header_index = index
            break
    if header_index is None:
        return [], [], "missing Markdown delimiter row"

    headers = [normalized(cell) for cell in rows[header_index]]
    data_rows = rows[header_index + 2 :]
    valid_rows = [row for row in data_rows if row and not is_delimiter_row(row)]
    return headers, valid_rows, None


def check_headings(lines: list[str], errors: list[str]) -> None:
    present = {line.strip() for line in lines if re.match(r"^#{1,2}\s+", line)}
    for heading in REQUIRED_HEADINGS:
        if heading not in present:
            errors.append(f"missing required heading: {heading}")

    ordered_positions: list[int] = []
    for heading in REQUIRED_HEADINGS:
        try:
            ordered_positions.append(next(i for i, line in enumerate(lines) if line.strip() == heading))
        except StopIteration:
            return
    if ordered_positions != sorted(ordered_positions):
        errors.append("required headings are not in the expected order")


def check_scope(lines: list[str], errors: list[str]) -> None:
    text = section_text(lines, "## 1. Rozsah kontroly")
    if not text:
        return
    compact = re.sub(r"\s+", " ", text)
    if len(compact) < 120:
        errors.append("scope section is too thin")
    lowered = normalized(compact)
    if not any(term in lowered for term in SCOPE_TERMS):
        errors.append("scope section must state limitations or explicitly say none")


def has_concrete_anchor(value: str) -> bool:
    lowered = normalized(value)
    if re.search(r"\d", value):
        return True
    if re.search(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value):
        return True
    if re.search(r"\b[A-Za-z0-9_-]+\.[A-Za-z0-9]{2,5}\b", value):
        return True
    return any(anchor in lowered for anchor in CONCRETE_ANCHORS)


def check_required_table(
    lines: list[str],
    heading: str,
    required_headers: tuple[str, ...],
    min_rows: int,
    errors: list[str],
) -> tuple[list[str], list[list[str]]]:
    body = section_body(lines, heading)
    if body is None:
        return [], []
    headers, rows, table_error = extract_table(body)
    if table_error:
        errors.append(f"{heading}: {table_error}")
        return [], []

    missing = [header for header in required_headers if header not in headers]
    if missing:
        errors.append(f"{heading}: missing table column(s): {', '.join(missing)}")
    if len(rows) < min_rows:
        errors.append(f"{heading}: expected at least {min_rows} data row(s), got {len(rows)}")

    for row_number, cells in enumerate(rows, start=1):
        if len(cells) != len(headers):
            errors.append(
                f"{heading}: malformed table row {row_number}: expected {len(headers)} cells, got {len(cells)}"
            )
    return headers, rows


def check_assignment_table(lines: list[str], errors: list[str], warnings: list[str]) -> None:
    headers, rows = check_required_table(
        lines,
        "## 3. Splneni zadani",
        ("bod zadani", "stav", "evidence"),
        3,
        errors,
    )
    if not headers:
        return
    evidence_index = headers.index("evidence") if "evidence" in headers else -1
    for row_number, cells in enumerate(rows, start=1):
        if evidence_index < 0 or evidence_index >= len(cells):
            continue
        evidence = cells[evidence_index]
        if normalized(evidence) in GENERIC_EVIDENCE or not has_concrete_anchor(evidence):
            warnings.append(f"assignment row {row_number} may lack concrete evidence")


def confidence_labels(value: str) -> list[str]:
    found = []
    for match in re.finditer(r"\[[^\]\n]+\]", value):
        label = match.group(0).upper()
        if label in CONFIDENCE_LABELS:
            found.append(label)
    return found


def check_evidence_ledger(lines: list[str], errors: list[str], warnings: list[str]) -> None:
    headers, rows = check_required_table(
        lines,
        "## 6. Evidence ledger: hlavni tvrzeni a opora",
        ("tvrzeni", "znacka jistoty", "opora"),
        3,
        errors,
    )
    if not headers:
        return

    label_index = headers.index("znacka jistoty") if "znacka jistoty" in headers else -1
    support_index = headers.index("opora") if "opora" in headers else -1
    use_index = next(
        (index for index, header in enumerate(headers) if header.startswith("pouzit do posudku")),
        -1,
    )
    positive_labels = 0
    for row_number, cells in enumerate(rows, start=1):
        if label_index < 0 or label_index >= len(cells):
            continue
        labels = confidence_labels(cells[label_index])
        if not labels:
            errors.append(f"evidence ledger row {row_number} is missing a known confidence label")
        else:
            positive_labels += 1
        used_in_report = True
        if use_index >= 0 and use_index < len(cells):
            used_in_report = normalized(cells[use_index]) not in {"ne", "no"}
        if used_in_report and support_index >= 0 and support_index < len(cells):
            support = cells[support_index]
            if normalized(support) in GENERIC_EVIDENCE or not has_concrete_anchor(support):
                warnings.append(f"evidence ledger row {row_number} may lack concrete support")

    if positive_labels < 3:
        errors.append("evidence ledger must contain at least three confidence-labeled claims")


def check_risk_table(lines: list[str], errors: list[str], warnings: list[str]) -> None:
    headers, rows = check_required_table(
        lines,
        "## 8. Hlavni rizika a nedostatky",
        ("priorita", "tvrzeni", "evidence", "dopad"),
        1,
        errors,
    )
    if not headers:
        return

    priority_index = headers.index("priorita") if "priorita" in headers else -1
    evidence_index = headers.index("evidence") if "evidence" in headers else -1
    high_priority_count = 0
    for row_number, cells in enumerate(rows, start=1):
        if priority_index < 0 or priority_index >= len(cells):
            continue
        priority = cells[priority_index].strip().upper()
        if priority not in PRIORITIES:
            errors.append(f"unknown priority label in risk row {row_number}: {cells[priority_index]}")
            continue
        if priority in {"P0", "P1"}:
            high_priority_count += 1
            evidence = cells[evidence_index] if 0 <= evidence_index < len(cells) else ""
            if normalized(evidence) in GENERIC_EVIDENCE or not has_concrete_anchor(evidence):
                errors.append(f"{priority} risk row {row_number} needs concrete evidence")

    if not rows:
        errors.append("risk table has no findings")
    if high_priority_count == 0:
        warnings.append("risk table contains no P0/P1 findings; verify this is intentional")
    if len(rows) > 8:
        errors.append(f"too many risk rows: {len(rows)}; maximum is 8")


def check_is_table(lines: list[str], errors: list[str], warnings: list[str]) -> None:
    headers, rows = check_required_table(
        lines,
        "## 9. Pokryti polozek IS a navrhy formulaci",
        ("polozka is", "stav", "evidence", "dopad"),
        6,
        errors,
    )
    if not headers:
        return

    area_index = headers.index("polozka is") if "polozka is" in headers else -1
    joined = " ".join(normalized(row[area_index]) for row in rows if 0 <= area_index < len(row))
    missing_areas = [area for area in REQUIRED_IS_AREAS if area not in joined]
    if missing_areas:
        warnings.append("IS coverage may miss expected area(s): " + ", ".join(missing_areas))


def check_grading_calibration(lines: list[str], errors: list[str], warnings: list[str]) -> None:
    text = section_text(lines, "## 13. Orientacni kalibrace hodnoceni")
    if not text:
        return

    normalized_text = normalized(text)
    intervals = re.findall(r"\b\d{1,3}\s*(?:-|az|až|to)\s*\d{1,3}\b", normalized_text)
    if len(intervals) < 2:
        errors.append("grading calibration must use defensible point intervals")

    text_without_intervals = re.sub(r"\b\d{1,3}\s*(?:-|az|až|to)\s*\d{1,3}\b", "", normalized_text)
    single_scores = re.findall(r"\b\d{2,3}\s*(?:bodu|bodů|points|pts)\b", text_without_intervals)
    if single_scores and not intervals:
        errors.append("grading calibration looks like a single false-precision point score")
    elif len(single_scores) > 2:
        warnings.append(
            "grading calibration mentions several single point scores; verify they are context, not verdict"
        )

    if not any(word in normalized_text for word in ("konzervativ", "standard", "mirnej", "mirnejsi", "mild")):
        warnings.append("grading calibration does not clearly separate conservative/standard/milder interpretations")


def list_items(body: list[str]) -> list[str]:
    items = []
    for line in body:
        match = re.match(r"^\s*(?:[-*]\s+|\d+\.\s+)(.+?)\s*$", line)
        if match:
            items.append(match.group(1).strip())
    return items


def check_questions(lines: list[str], errors: list[str], warnings: list[str]) -> None:
    body = section_body(lines, "## 14. Navrhy otazek k obhajobe")
    if body is None:
        return
    items = list_items(body)
    if len(items) < 3:
        errors.append("defense questions section must contain at least three questions")
        return
    question_like = sum(
        1
        for item in items
        if "?" in item or normalized(item).startswith(("co ", "jak ", "proc ", "proč ", "ktera ", "která "))
    )
    if question_like < 3:
        warnings.append("defense questions may not be phrased as answerable questions")


def check_manual_checks(lines: list[str], errors: list[str], warnings: list[str]) -> None:
    body = section_body(lines, "## 15. Rucni kontroly pred napsanim posudku")
    if body is None:
        return
    items = list_items(body)
    if len(items) < 2:
        errors.append("manual-check section must contain at least two concrete items")
        return
    for index, item in enumerate(items, start=1):
        key = normalized(item)
        if key in GENERIC_ITEMS or len(key) < 18:
            errors.append(f"manual-check item {index} is empty or generic")
        elif not has_concrete_anchor(item) and len(key) < 45:
            warnings.append(f"manual-check item {index} may be too generic")


def check_text_hygiene(text: str, case_id: str, round_id: str, errors: list[str], warnings: list[str]) -> None:
    lowered = text.lower()
    if case_id.lower() in lowered:
        errors.append(f"opponent materials leak the exact case id: {case_id}")
    if round_id.lower() in lowered:
        errors.append(f"opponent materials leak the exact round id: {round_id}")
    if re.search(r"\b20\d{6}-\d{6}-[A-Za-z0-9_.-]+\b", text):
        errors.append("opponent materials contain a timestamp-like round id")
    if re.search(r"(?<!\w)/(?:home|Users|tmp|var|workspace|mnt)/[^\s)]+", text):
        errors.append("opponent materials contain an absolute filesystem path")
    if re.search(r"\b[A-Za-z]:\\[^\s)]+", text):
        errors.append("opponent materials contain a Windows absolute path")

    for pattern in PLACEHOLDER_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE):
            errors.append(f"leftover placeholder/template text matching: {pattern}")
    for match in ANGLE_PLACEHOLDER_RE.finditer(text):
        value = match.group(1).strip()
        if not AUTOLINK_RE.fullmatch(value):
            errors.append("leftover angle-bracket placeholder/template text")
    for pattern in DRAFT_ARTIFACT_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            errors.append(f"opponent materials mention draft artifact filename matching: {pattern}")
    for pattern in INTERNAL_WORKFLOW_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            errors.append(f"opponent materials mention unrelated workflow detail matching: {pattern}")


def check_strengths(lines: list[str], errors: list[str], warnings: list[str]) -> None:
    body = section_body(lines, "## 7. Silne stranky")
    if body is None:
        return
    items = list_items(body)
    if len(items) < 2:
        errors.append("strengths section should contain at least two concrete strengths")
    for index, item in enumerate(items, start=1):
        if normalized(item) in GENERIC_ITEMS or len(normalized(item)) < 20:
            warnings.append(f"strength item {index} may be too generic")


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[1] in {"-h", "--help"}:
        print(usage())
        return 0
    if len(argv) not in {2, 3}:
        die_usage("Expected CASE_ID and optional ROUND_ID.")

    case_id = argv[1]
    validate_id("CASE_ID", case_id)
    root = repo_root()
    case_dir = root / "cases" / case_id
    if not case_dir.is_dir():
        print(f"ERROR: Case does not exist: cases/{case_id}", file=sys.stderr)
        return 2

    round_id = resolve_round(case_dir, argv[2] if len(argv) == 3 else None)
    round_dir = case_dir / "rounds" / round_id
    if not round_dir.is_dir():
        print(f"ERROR: Round does not exist: cases/{case_id}/rounds/{round_id}", file=sys.stderr)
        return 2

    output = round_dir / "outputs" / "oponent_podklady_revidovane.md"
    if not output.is_file():
        print(
            "ERROR: Missing reviewed opponent materials: "
            f"cases/{case_id}/rounds/{round_id}/outputs/oponent_podklady_revidovane.md",
            file=sys.stderr,
        )
        return 1

    errors: list[str] = []
    warnings: list[str] = []
    run_round_ready(root, case_id, round_id, errors)

    text = output.read_text(encoding="utf-8")
    lines = text.splitlines()
    check_headings(lines, errors)
    check_scope(lines, errors)
    check_assignment_table(lines, errors, warnings)
    check_evidence_ledger(lines, errors, warnings)
    check_strengths(lines, errors, warnings)
    check_risk_table(lines, errors, warnings)
    check_is_table(lines, errors, warnings)
    check_grading_calibration(lines, errors, warnings)
    check_questions(lines, errors, warnings)
    check_manual_checks(lines, errors, warnings)
    check_text_hygiene(text, case_id, round_id, errors, warnings)

    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("Opponent materials check passed")
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
