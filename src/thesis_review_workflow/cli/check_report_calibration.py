"""Validate the applied opponent-report calibration basis."""

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
from thesis_review_workflow.report_calibration import (
    REPORT_CALIBRATION_APPLICABILITY_BOUND,
    REPORT_CALIBRATION_APPLICABILITY_NOT_APPLICABLE,
    REPORT_CALIBRATION_BASIS_REL,
    effective_reviewer_profile,
    report_calibration_applicability,
    validate_report_calibration_artifact,
)
from thesis_review_workflow.structured_evidence import OPPONENT_REPORT_TRACE_REL, validate_structured_evidence_artifact


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/check-report-calibration",
        description=__doc__,
    )
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    validate_id("CASE_ID", args.case_id)
    root = repo_root()
    case_dir = require_case_dir(root, args.case_id)
    round_id = resolve_round(case_dir, args.round_id)
    round_dir = require_round_dir(case_dir, args.case_id, round_id)
    reviewer_profile_id, profile_sources, profile_errors = effective_reviewer_profile(case_dir / "case.md", root)
    if profile_errors:
        for error in profile_errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    applicability = report_calibration_applicability(round_dir)
    if applicability == REPORT_CALIBRATION_APPLICABILITY_NOT_APPLICABLE:
        errors = validate_structured_evidence_artifact(
            round_dir,
            OPPONENT_REPORT_TRACE_REL,
            case_id=args.case_id,
            round_id=round_id,
        )
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1
        print(
            "Report calibration basis check not applicable: validated "
            "report_calibration_limitation in work/opponent_report_trace.json."
        )
        return 0
    if applicability != REPORT_CALIBRATION_APPLICABILITY_BOUND:
        print(
            "ERROR: report calibration basis is not bound; add work/report_calibration_basis.json "
            "or record a validated report_calibration_limitation in work/opponent_report_trace.json",
            file=sys.stderr,
        )
        return 1

    errors = validate_report_calibration_artifact(
        round_dir,
        REPORT_CALIBRATION_BASIS_REL,
        case_id=args.case_id,
        round_id=round_id,
        expected_reviewer_profile_id=reviewer_profile_id,
        expected_profile_source_paths=profile_sources,
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Report calibration basis check passed.")
    return 0


def console_main() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(console_main())
