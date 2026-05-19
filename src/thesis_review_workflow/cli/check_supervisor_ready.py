"""Validate supervisor-feedback readiness for a thesis case round."""

from __future__ import annotations

import argparse
import sys

from thesis_review_workflow.cases import MissingCurrentRound, repo_root
from thesis_review_workflow.cases import resolve_round as resolve_round_core
from thesis_review_workflow.commands import run_step
from thesis_review_workflow.submission_bundle import submission_bundle_visibility_lines


def usage() -> str:
    return (
        "Usage: scripts/check-supervisor-ready CASE_ID [ROUND_ID]\n\n"
        "Checks readiness for supervisor feedback: assignment context must be present and\n"
        "deadline context must be known for the case academic year/work type."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/check-supervisor-ready",
        description="Check supervisor feedback readiness for a thesis round.",
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
    command_args = [args.case_id, *([args.round_id] if args.round_id else [])]
    root = repo_root()
    case_dir = root / "cases" / args.case_id
    visibility_round_id: str | None = None
    try:
        visibility_round_id = resolve_round_core(case_dir, args.round_id)
    except (MissingCurrentRound, ValueError):
        pass
    if visibility_round_id is not None:
        bundle_lines = submission_bundle_visibility_lines(
            case_dir / "rounds" / visibility_round_id,
            include_absent=False,
        )
        if bundle_lines:
            print("Submission Bundle Inventory")
            for line in bundle_lines:
                print(line)
    for command in ("check-round-ready", "supervisor-deadline"):
        step = run_step(root, command, [f"scripts/{command}", *command_args])
        if step.output:
            print(step.output)
        if not step.ok:
            return step.returncode
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
