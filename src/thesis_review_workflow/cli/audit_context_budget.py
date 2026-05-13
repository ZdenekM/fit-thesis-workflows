"""Report advisory model-context budget for a thesis review round."""

from __future__ import annotations

import argparse
import json
import sys

from thesis_review_workflow.cli.context import (
    repo_root,
    require_case_dir,
    require_round_dir,
    resolve_round,
    validate_id,
)
from thesis_review_workflow.context_budget import (
    DEFAULT_MAX_COMMON_BRIEFING_TOKENS,
    DEFAULT_MAX_MANAGED_CONTEXT_TOKENS,
    DEFAULT_MAX_ROLE_PACKET_TOKENS,
    DEFAULT_RAW_TRANSFER_RATIO,
    build_context_budget_report,
    render_context_budget_report,
)


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def positive_ratio(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, prog="scripts/audit-context-budget")
    parser.add_argument("--json", action="store_true", help="print the advisory report as machine-readable JSON")
    parser.add_argument(
        "--max-common-briefing-tokens",
        type=positive_int,
        default=DEFAULT_MAX_COMMON_BRIEFING_TOKENS,
        help="warning threshold for work/common_briefing.json estimated tokens",
    )
    parser.add_argument(
        "--max-role-packet-tokens",
        type=positive_int,
        default=DEFAULT_MAX_ROLE_PACKET_TOKENS,
        help="warning threshold for each role packet estimated tokens",
    )
    parser.add_argument(
        "--max-managed-context-tokens",
        type=positive_int,
        default=DEFAULT_MAX_MANAGED_CONTEXT_TOKENS,
        help="warning threshold for all managed context surfaces combined",
    )
    parser.add_argument(
        "--raw-transfer-ratio",
        type=positive_ratio,
        default=DEFAULT_RAW_TRANSFER_RATIO,
        help="warning threshold for managed-context tokens divided by raw-source tokens",
    )
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv[1:])

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

    report = build_context_budget_report(
        args.case_id,
        round_id,
        round_dir,
        max_common_briefing_tokens=args.max_common_briefing_tokens,
        max_role_packet_tokens=args.max_role_packet_tokens,
        max_managed_context_tokens=args.max_managed_context_tokens,
        raw_transfer_ratio=args.raw_transfer_ratio,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        sys.stdout.write(render_context_budget_report(report))
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
