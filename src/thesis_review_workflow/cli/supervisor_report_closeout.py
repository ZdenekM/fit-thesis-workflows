"""Run closeout gates for a reviewed and confirmed supervisor report."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from thesis_review_workflow.cli.context import (
    repo_root,
    require_case_dir,
    require_round_dir,
    resolve_round,
    validate_id,
)
from thesis_review_workflow.commands import Step, print_step, run_step

COVERAGE_REL = Path("work/agent_coverage.json")
SUPERVISOR_REPORT_DRAFT_REL = Path("work/vedouci_posudek_draft.md")
SUPERVISOR_REPORT_REVIEWED_REL = Path("outputs/vedouci_posudek_revidovany.md")
SUPERVISOR_REPORT_CONFIRMATION_REL = Path("work/supervisor_report_confirmation.json")
SUPERVISOR_REPORT_REVIEW_REL = Path("work/reviews/supervisor_report_review.json")
SUPERVISOR_REPORT_TRACE_REL = Path("work/supervisor_report_trace.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/supervisor-report-closeout",
        description=(
            "Validate reviewed and confirmed supervisor report, final review approval, provenance, "
            "role coverage, and repo hygiene."
        ),
    )
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    parser.add_argument(
        "--skip-repo-hygiene",
        action="store_true",
        help="skip check-private, check-scripts, and git diff --check",
    )
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv[1:])
    validate_id("CASE_ID", args.case_id)
    if args.round_id is not None:
        validate_id("ROUND_ID", args.round_id)
    root = repo_root()
    case_dir = require_case_dir(root, args.case_id)
    round_id = resolve_round(case_dir, args.round_id)
    round_dir = require_round_dir(case_dir, args.case_id, round_id)

    print("Supervisor Report Closeout")
    print(f"Case: cases/{args.case_id}")
    print(f"Round: cases/{args.case_id}/rounds/{round_id}")

    steps: list[Step] = []
    steps.append(
        run_step(root, "Supervisor report readiness", ["scripts/check-supervisor-report-ready", args.case_id, round_id])
    )
    steps.append(
        run_step(
            root,
            "Reviewed and confirmed supervisor report",
            ["scripts/check-supervisor-report", "--require-reviewed", "--require-confirmation", args.case_id, round_id],
        )
    )
    steps.append(
        run_step(
            root,
            "Final supervisor report review wave",
            ["scripts/check-review-wave", "--workflow", "supervisor_report", "--wave", "final", args.case_id, round_id],
        )
    )
    steps.append(
        run_step(
            root,
            "Review manifest refresh",
            ["scripts/init-review-manifest", "--run-checks", args.case_id, round_id],
        )
    )
    if (round_dir / COVERAGE_REL).is_file():
        steps.append(run_step(root, "Agent role coverage", ["scripts/check-agent-coverage", args.case_id, round_id]))
    else:
        steps.append(
            Step(
                label="Agent role coverage",
                command=["scripts/check-agent-coverage", args.case_id, round_id],
                returncode=0,
                output="skipped: work/agent_coverage.json is not present after manifest refresh",
                required=True,
            )
        )
    steps.append(
        run_step(
            root,
            "Review manifest completeness",
            ["scripts/check-review-manifest", "--require-complete", args.case_id, round_id],
        )
    )
    if not args.skip_repo_hygiene:
        steps.append(run_step(root, "Private workspace hygiene", ["scripts/check-private"]))
        steps.append(run_step(root, "Script syntax", ["scripts/check-scripts"]))
        steps.append(run_step(root, "Whitespace/diff hygiene", ["git", "diff", "--check"]))

    for step in steps:
        print_step(step, output_limit=1000)

    print()
    print("## Supervisor Report Closeout Summary")
    for label, rel_path in (
        ("Trace", SUPERVISOR_REPORT_TRACE_REL),
        ("Draft", SUPERVISOR_REPORT_DRAFT_REL),
        ("Reviewed report", SUPERVISOR_REPORT_REVIEWED_REL),
        ("Review approval", SUPERVISOR_REPORT_REVIEW_REL),
        ("Supervisor confirmation", SUPERVISOR_REPORT_CONFIRMATION_REL),
    ):
        if (round_dir / rel_path).is_file():
            print(f"- {label} present: `{rel_path.as_posix()}`.")
        else:
            print(f"- {label} missing: `{rel_path.as_posix()}`.")
    print("- PASS means the report is reviewed, hash-bound to supervisor confirmation, and ready for IS transfer.")
    print("- FAIL means fix the named gate before relying on the report.")
    return 1 if any(not step.ok and step.required for step in steps) else 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
