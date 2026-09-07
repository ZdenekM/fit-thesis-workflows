"""Validate the supervisor reading pass of a round when one is present."""

from __future__ import annotations

import argparse
import sys

from thesis_review_workflow.cases import MissingCurrentRound, repo_root, resolve_round
from thesis_review_workflow.ids import validate_id
from thesis_review_workflow.supervisor_reading_pass import (
    SUPERVISOR_READING_PASS_REL,
    SUPERVISOR_READING_PASS_TEMPLATE,
    reading_pass_path,
    routing_counts,
    validate_reading_pass_text,
)


def usage() -> str:
    return (
        "Usage: scripts/check-supervisor-reading-pass CASE_ID [ROUND_ID]\n\n"
        f"Validates {SUPERVISOR_READING_PASS_REL} when the round carries one.\n"
        "A round without a reading pass is valid and exits 0."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/check-supervisor-reading-pass",
        description="Validate the structure of a supervisor reading pass when the round has one.",
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

    path = reading_pass_path(round_dir)
    if not path.is_file():
        print(
            f"No supervisor reading pass in this round: {SUPERVISOR_READING_PASS_REL} is absent, which is valid. "
            f"Create it from {SUPERVISOR_READING_PASS_TEMPLATE} when the supervisor dictates a reading pass."
        )
        return 0

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"Could not read {SUPERVISOR_READING_PASS_REL}: {exc}", file=sys.stderr)
        return 1

    errors, warnings = validate_reading_pass_text(text)
    for warning in warnings:
        print(f"Warning: {warning}")
    if errors:
        print(f"Supervisor reading pass is not usable: {SUPERVISOR_READING_PASS_REL}", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        print(f"Shape and routing values are documented in {SUPERVISOR_READING_PASS_TEMPLATE}.", file=sys.stderr)
        return 1

    counts = routing_counts(text)
    print(f"Supervisor reading pass is usable: {SUPERVISOR_READING_PASS_REL}")
    print("Routing: " + ", ".join(f"{role} {count}" for role, count in counts.items()))
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
