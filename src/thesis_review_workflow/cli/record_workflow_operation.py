"""Append a structured operation event to a round-local log."""

from __future__ import annotations

import argparse
import os
import sys

from thesis_review_workflow.cli.context import (
    repo_root,
    require_case_dir,
    require_round_dir,
    resolve_round,
    validate_id,
)
from thesis_review_workflow.operation_log import OPERATION_LOG_REL, OPERATION_STATUSES, append_operation
from thesis_review_workflow.paths import rel_repo


def parse_details(values: list[str]) -> dict[str, str]:
    details: dict[str, str] = {}
    for value in values:
        key, separator, item = value.partition("=")
        if not separator or not key.strip():
            raise argparse.ArgumentTypeError("--detail values must use key=value")
        details[key.strip()] = item.strip()
    return details


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/record-workflow-operation",
        description="Append an operation event to work/operation_log.jsonl for later reconstruction.",
    )
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    parser.add_argument("--operation", required=True, help="Short stable operation name, e.g. literature-source-audit.")
    parser.add_argument("--status", required=True, choices=sorted(OPERATION_STATUSES))
    parser.add_argument("--summary", required=True, help="One concise human-readable summary.")
    parser.add_argument("--actor", default=os.environ.get("USER", "operator"))
    parser.add_argument("--command", default="")
    parser.add_argument("--artifact", action="append", default=[])
    parser.add_argument("--check", action="append", default=[])
    parser.add_argument("--detail", action="append", default=[], metavar="KEY=VALUE")
    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv[1:])
    validate_id("CASE_ID", args.case_id)
    if args.round_id is not None:
        validate_id("ROUND_ID", args.round_id)

    try:
        details = parse_details(args.detail)
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))

    root = repo_root()
    case_dir = require_case_dir(root, args.case_id)
    round_id = resolve_round(case_dir, args.round_id)
    round_dir = require_round_dir(case_dir, args.case_id, round_id)

    append_operation(
        round_dir,
        case_id=args.case_id,
        round_id=round_id,
        operation=args.operation,
        status=args.status,
        actor=args.actor,
        summary=args.summary,
        command=args.command,
        artifacts=args.artifact,
        checks=args.check,
        details=details,
    )
    print(f"Recorded operation event: {rel_repo(root, round_dir / OPERATION_LOG_REL)}")
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
