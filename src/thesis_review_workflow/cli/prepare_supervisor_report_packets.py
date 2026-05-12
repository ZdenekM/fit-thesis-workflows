"""Generate role-specific packet files for formal supervisor-report agents."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

from thesis_review_workflow.cli.context import (
    repo_root,
    require_case_dir,
    require_round_dir,
    resolve_round,
    validate_id,
)
from thesis_review_workflow.commands import run_step
from thesis_review_workflow.paths import rel_repo
from thesis_review_workflow.supervisor_report_packets import generate_packets


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/prepare-supervisor-report-packets",
        description="Generate role-specific packets for formal supervisor-report agents.",
    )
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    parser.add_argument(
        "--skip-ready-check",
        action="store_true",
        help="generate packets without running check-supervisor-report-ready first",
    )
    parser.add_argument(
        "--skip-materiality-check",
        action="store_true",
        help="generate packets without refreshing supervisor_report materiality decisions first",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    validate_id("CASE_ID", args.case_id)
    root = repo_root()
    case_dir = require_case_dir(root, args.case_id)
    round_id = resolve_round(case_dir, args.round_id)
    round_dir = require_round_dir(case_dir, args.case_id, round_id)

    if not args.skip_ready_check:
        ready = run_step(
            root,
            "supervisor report readiness",
            ["scripts/check-supervisor-report-ready", args.case_id, round_id],
        )
        if ready.output:
            print(ready.output)
        if not ready.ok:
            return ready.returncode

    if not args.skip_materiality_check:
        materiality = run_step(
            root,
            "supervisor report materiality",
            [
                "scripts/check-review-materiality",
                "--workflow",
                "supervisor_report",
                "--phase",
                "final",
                args.case_id,
                round_id,
            ],
        )
        if materiality.output:
            print(materiality.output)
        if not materiality.ok:
            return materiality.returncode

    paths = generate_packets(args.case_id, round_id, now_utc(), round_dir)
    for path in paths:
        print(f"Wrote {rel_repo(root, path)}")
    print(f"Supervisor report packets: {len(paths)}")
    return 0


def console_main() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(console_main())
