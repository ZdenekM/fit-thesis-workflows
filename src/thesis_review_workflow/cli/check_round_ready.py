"""Validate round assignment context before review artifacts are generated."""

from __future__ import annotations

import argparse
import sys
import unicodedata
from pathlib import Path

from thesis_review_workflow.cases import MissingCurrentRound, repo_root, resolve_round
from thesis_review_workflow.commands import run_step
from thesis_review_workflow.ids import validate_id


def usage() -> str:
    return (
        "Usage: scripts/check-round-ready CASE_ID [ROUND_ID]\n\n"
        "Checks whether a round has the required assignment context before generating\n"
        "supervisor feedback or opponent materials."
    )


def folded(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char)).casefold()


def section_has_content(path: Path, heading: str) -> bool:
    in_section = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line == heading:
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        stripped = line.strip()
        if not in_section or not stripped or stripped == "-":
            continue
        if stripped.startswith("TODO:") or stripped.startswith("TODO "):
            continue
        return True
    return False


def has_matching_file(directory: Path, suffix: str) -> bool:
    if not directory.is_dir():
        return False
    dotted = "." + suffix.casefold().lstrip(".")
    for path in directory.iterdir():
        if not path.is_file() or path.suffix.casefold() != dotted:
            continue
        name = folded(path.name)
        if "zadani" in name or "assignment" in name:
            return True
    return False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/check-round-ready",
        description="Check whether a thesis round has required assignment context.",
    )
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    return parser


def main(argv: list[str]) -> int:
    if any(arg in {"-h", "--help"} for arg in argv[1:]):
        print(usage())
        return 0
    parser = build_parser()
    args = parser.parse_args(argv[1:])

    try:
        validate_id("CASE_ID", args.case_id)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    root = repo_root()
    case_dir = root / "cases" / args.case_id
    if not case_dir.is_dir():
        print(f"Case does not exist: cases/{args.case_id}", file=sys.stderr)
        return 1

    reviewer = run_step(root, "reviewer profile", ["scripts/check-reviewer-profile", args.case_id])
    if not reviewer.ok:
        if reviewer.output:
            print(reviewer.output, file=sys.stderr)
        return reviewer.returncode

    try:
        round_id = resolve_round(case_dir, args.round_id)
    except MissingCurrentRound:
        print(f"Missing current round: cases/{args.case_id}/current-round.txt", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    round_dir = case_dir / "rounds" / round_id
    if not round_dir.is_dir():
        print(f"Round does not exist: cases/{args.case_id}/rounds/{round_id}", file=sys.stderr)
        return 1

    assignment_notes = round_dir / "notes" / "assignment.md"
    if not assignment_notes.is_file():
        print(
            f"Missing required assignment context: cases/{args.case_id}/rounds/{round_id}/notes/assignment.md",
            file=sys.stderr,
        )
        print(
            "Create it from templates/assignment.md before generating feedback or opponent materials.", file=sys.stderr
        )
        return 1

    formal_source_ok = section_has_content(assignment_notes, "## Formal Assignment Artifacts") or has_matching_file(
        round_dir / "inputs", "pdf"
    )
    formal_readable_ok = section_has_content(
        assignment_notes, "## Formal Assignment Text Or Summary"
    ) or has_matching_file(round_dir / "extracted", "txt")
    private_notes_ok = section_has_content(assignment_notes, "## Private Assignment Notes For Student")

    failed = False
    if not formal_source_ok:
        print("Missing formal assignment artifact in notes/assignment.md or inputs/.", file=sys.stderr)
        failed = True
    if not formal_readable_ok:
        print(
            "Missing readable assignment text: add extracted assignment text or fill "
            "Formal Assignment Text Or Summary.",
            file=sys.stderr,
        )
        failed = True
    if not private_notes_ok:
        print("Missing private assignment notes for the student in notes/assignment.md.", file=sys.stderr)
        failed = True
    if failed:
        return 1

    print("Round ready: assignment context is present.")
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
