"""Validate readiness for drafting a formal supervisor report."""

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
from thesis_review_workflow.commands import run_step
from thesis_review_workflow.structured_evidence import (
    SUPERVISOR_REPORT_TRACE_REL,
    validate_structured_evidence_artifact,
)
from thesis_review_workflow.supervisor_report import check_supervisor_report_intake


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/check-supervisor-report-ready",
        description="Check readiness for formal supervisor-report drafting.",
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

    errors: list[str] = []
    warnings: list[str] = []
    base = run_step(root, "supervisor readiness", ["scripts/check-supervisor-ready", args.case_id, round_id])
    if base.output:
        print(base.output)
    if not base.ok:
        errors.append("base supervisor readiness failed")

    intake = check_supervisor_report_intake(round_dir)
    errors.extend(intake.errors)
    warnings.extend(intake.warnings)

    trace_path = round_dir / SUPERVISOR_REPORT_TRACE_REL
    if trace_path.is_file():
        errors.extend(
            validate_structured_evidence_artifact(
                round_dir,
                SUPERVISOR_REPORT_TRACE_REL,
                case_id=args.case_id,
                round_id=round_id,
            )
        )

    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Supervisor report readiness passed")
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
