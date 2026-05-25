"""Validate external opponent-report postmortem learning artifacts."""

from __future__ import annotations

import argparse
import sys

from thesis_review_workflow.cli.context import (
    repo_root,
    require_case_dir,
    require_round_dir,
    resolve_round,
    validate_id,
)
from thesis_review_workflow.external_opponent_feedback import (
    external_opponent_feedback_evidence_present,
    validate_external_opponent_feedback_round,
)
from thesis_review_workflow.paths import rel_repo


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/check-external-opponent-feedback",
        description="Validate external opponent-report postmortem learning artifacts when present.",
    )
    parser.add_argument(
        "--require-analysis",
        action="store_true",
        help="Require the full findings, learning-candidates, analysis, and approval artifact set.",
    )
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    validate_id("CASE_ID", args.case_id, stderr=True)
    root = repo_root()
    try:
        case_dir = require_case_dir(root, args.case_id, error_prefix="ERROR: ", stderr=True)
        round_id = resolve_round(case_dir, args.round_id, stderr=True)
        round_dir = require_round_dir(case_dir, args.case_id, round_id, error_prefix="ERROR: ", stderr=True)
    except SystemExit as exc:
        if exc.code == 2:
            return 2
        raise

    errors = validate_external_opponent_feedback_round(
        round_dir,
        case_id=args.case_id,
        round_id=round_id,
        require_analysis=args.require_analysis,
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if external_opponent_feedback_evidence_present(round_dir):
        print(f"External opponent-feedback check passed: {rel_repo(root, round_dir)}")
    else:
        print(f"No external opponent-feedback evidence present: {rel_repo(root, round_dir)}")
    return 0


def console_main() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(console_main())
