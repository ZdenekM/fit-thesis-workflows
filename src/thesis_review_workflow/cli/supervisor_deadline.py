"""Print supervisor deadline context for a thesis case."""

from __future__ import annotations

import datetime as dt
import os
import re
import subprocess
import sys
from pathlib import Path


def usage() -> None:
    print(
        "Usage: scripts/supervisor-deadline CASE_ID [ROUND_ID]\n\n"
        "Reads case academic year/work type and prints supervisor deadline context.",
        file=sys.stderr,
    )


def repo_root() -> Path:
    output = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True)
    return Path(output.strip())


def parse_fields(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    if not path.exists():
        return fields
    for line in path.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip().lower()] = value.strip()
    return fields


def normalize_work_type(value: str) -> str:
    match = re.search(r"\b(BP|DP)\b", value.upper())
    return match.group(1) if match else ""


def normalize_academic_year(value: str) -> str:
    match = re.search(r"(20\d{2})\s*/\s*(20\d{2}|\d{2})", value)
    if not match:
        return ""
    start = match.group(1)
    end = match.group(2)
    if len(end) == 2:
        end = start[:2] + end
    return f"{start}/{end}"


def academic_year_from_assignment(round_dir: Path) -> str:
    assignment = round_dir / "notes" / "assignment.md"
    if not assignment.exists():
        return ""
    return normalize_academic_year(assignment.read_text(encoding="utf-8"))


def read_deadlines(config_path: Path) -> list[dict[str, str]]:
    lines = config_path.read_text(encoding="utf-8").splitlines()
    headers: list[str] | None = None
    rows: list[dict[str, str]] = []
    for line in lines:
        if not line.strip() or line.startswith("#"):
            if line.startswith("# academic_year"):
                headers = line[2:].split("\t")
            continue
        if headers is None:
            raise SystemExit(f"Missing header in {config_path}")
        values = line.split("\t")
        values.extend([""] * (len(headers) - len(values)))
        rows.append(dict(zip(headers, values, strict=False)))
    return rows


def parse_date(value: str) -> dt.date | None:
    if not value:
        return None
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        return None


def days_label(target: dt.date, today: dt.date) -> str:
    delta = (target - today).days
    if delta == 0:
        return "today"
    if delta > 0:
        return f"{delta} days left"
    return f"{abs(delta)} days after deadline"


def calibration(recommended: dt.date | None, official: dt.date | None, today: dt.date) -> str:
    anchor = recommended or official
    if anchor is None:
        return "unknown; confirm the deadline before phase calibration"
    days = (anchor - today).days
    if days < 0:
        return "after the recommended finish target; focus only on blockers and submission-critical fixes"
    if days <= 7:
        return "final week; prioritize blockers, assignment coverage, technical truth, and submission artifacts"
    if days <= 21:
        return "near-final stretch; keep feedback short and prioritize changes that can realistically be finished"
    return "normal supervision window; broader structural feedback can still be useful"


def main(argv: list[str]) -> int:
    if len(argv) not in {2, 3} or argv[1] in {"-h", "--help"}:
        usage()
        return 0 if len(argv) == 2 and argv[1] in {"-h", "--help"} else 2

    case_id = argv[1]
    root = repo_root()
    case_dir = root / "cases" / case_id
    if not case_dir.is_dir():
        print(f"Case does not exist: cases/{case_id}", file=sys.stderr)
        return 1

    if len(argv) == 3:
        round_id = argv[2]
    else:
        current_round = case_dir / "current-round.txt"
        if not current_round.exists():
            print(f"Missing current round: cases/{case_id}/current-round.txt", file=sys.stderr)
            return 1
        round_id = current_round.read_text(encoding="utf-8").strip()

    round_dir = case_dir / "rounds" / round_id
    if not round_dir.is_dir():
        print(f"Round does not exist: cases/{case_id}/rounds/{round_id}", file=sys.stderr)
        return 1

    case_fields = parse_fields(case_dir / "case.md")
    work_type = normalize_work_type(case_fields.get("work type", ""))
    academic_year = normalize_academic_year(case_fields.get("academic year", ""))
    if not academic_year:
        academic_year = academic_year_from_assignment(round_dir)

    if not work_type:
        print("Missing Work type in case.md. Expected BP or DP.", file=sys.stderr)
        return 1
    if not academic_year:
        print("Missing Academic year in case.md and notes/assignment.md.", file=sys.stderr)
        return 1

    rows = read_deadlines(root / "config" / "supervisor-deadlines.tsv")
    row = next(
        (
            item
            for item in rows
            if item.get("academic_year") == academic_year and item.get("work_type", "").upper() == work_type
        ),
        None,
    )
    if row is None:
        print(
            f"No supervisor deadline configured for academic year {academic_year}, work type {work_type}.",
            file=sys.stderr,
        )
        return 1

    deadline_mode = case_fields.get("deadline mode", "standard") or "standard"
    deadline_override = parse_date(case_fields.get("deadline override", ""))
    today = (
        parse_date(os.environ.get("THESIS_TODAY", ""))
        or parse_date(case_fields.get("review date", ""))
        or dt.date.today()
    )
    deadline_mode_normalized = deadline_mode.lower()
    missing_deferred_override = deadline_mode_normalized == "deferred" and not deadline_override
    official = deadline_override or parse_date(row.get("official_deadline", ""))
    recommended = None if deadline_override else parse_date(row.get("recommended_finish", ""))
    if missing_deferred_override:
        official = None
        recommended = None

    print("Supervisor deadline context")
    print(f"Case: {case_id}")
    print(f"Round: {round_id}")
    print(f"Academic year: {academic_year}")
    print(f"Work type: {work_type}")
    print(f"Deadline mode: {deadline_mode}")
    if official:
        label = "Deadline override" if deadline_override else "Official deadline"
        print(f"{label}: {official.isoformat()} ({days_label(official, today)})")
    if recommended:
        print(f"Recommended internal finish: {recommended.isoformat()} ({days_label(recommended, today)})")
    if missing_deferred_override:
        deferred_window = row.get("deferred_window", "")
        if deferred_window:
            print(f"Deferred window: {deferred_window}; exact deferred date is case-specific")
        print("Deferred mode requires a case-specific Deadline override before precise time calibration.")
    print(f"Calibration: {calibration(recommended, official, today)}")
    if row.get("notes"):
        print(f"Notes: {row['notes']}")
    return 1 if missing_deferred_override else 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
