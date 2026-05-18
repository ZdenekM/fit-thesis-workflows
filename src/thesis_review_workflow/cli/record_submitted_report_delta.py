"""Record accepted public-form deltas for submitted reports."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from thesis_review_workflow.cli.context import (
    repo_root,
    require_case_dir,
    require_round_dir,
    resolve_round,
    validate_id,
)
from thesis_review_workflow.operation_log import append_operation
from thesis_review_workflow.paths import rel_repo
from thesis_review_workflow.submitted_report_deltas import (
    NON_MATERIAL_SUBMITTED_REPORT_DELTA_CLASSIFICATIONS,
    OPPONENT_REPORT_DELTAS_REL,
    SUBMITTED_REPORT_DELTA_CLASSIFICATIONS,
    build_opponent_submitted_report_delta_payload,
    validate_opponent_submitted_report_deltas,
)
from thesis_review_workflow.submitted_reports import OPPONENT_REPORT_SUBMITTED_RECORD_REL


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/record-submitted-report-delta",
        description=(
            "Classify current submitted opponent-report public-form differences. "
            "Only non-material classifications can unblock archive readiness."
        ),
    )
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    parser.add_argument(
        "--report-kind",
        default="opponent_report",
        choices=["opponent_report"],
        help="submitted report kind; currently only opponent_report is supported",
    )
    parser.add_argument(
        "--section",
        action="append",
        default=[],
        help="section heading to accept; repeat until every current public-text diff is classified",
    )
    parser.add_argument("--classification", required=True, choices=sorted(SUBMITTED_REPORT_DELTA_CLASSIFICATIONS))
    parser.add_argument("--rationale", required=True)
    parser.add_argument("--recorded-by", required=True, help="operator identity accepting the bounded delta")
    parser.add_argument("--recorded-at", default="", help="ISO timestamp; defaults to current UTC time")
    parser.add_argument("--force", action="store_true", help="overwrite the submitted-report delta artifact")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    validate_id("CASE_ID", args.case_id)
    if args.round_id is not None:
        validate_id("ROUND_ID", args.round_id)
    root = repo_root()
    try:
        case_dir = require_case_dir(root, args.case_id)
        round_id = resolve_round(case_dir, args.round_id)
        round_dir = require_round_dir(case_dir, args.case_id, round_id)
        payload = build_opponent_submitted_report_delta_payload(
            round_dir,
            case_id=args.case_id,
            round_id=round_id,
            generated_at=args.recorded_at or now_utc(),
            recorded_by=args.recorded_by,
            sections=args.section,
            classification=args.classification,
            rationale=args.rationale,
        )
        errors = validate_opponent_submitted_report_deltas(
            payload,
            round_dir=round_dir,
            case_id=args.case_id,
            round_id=round_id,
            rel_path=OPPONENT_REPORT_DELTAS_REL,
            require_archive_ready=args.classification in NON_MATERIAL_SUBMITTED_REPORT_DELTA_CLASSIFICATIONS,
        )
        if errors:
            raise ValueError("\n".join(errors))
        output = round_dir / OPPONENT_REPORT_DELTAS_REL
        if output.exists() and not args.force:
            raise ValueError(
                f"refusing to overwrite existing submitted-report deltas without --force: {OPPONENT_REPORT_DELTAS_REL}"
            )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        append_operation(
            round_dir,
            case_id=args.case_id,
            round_id=round_id,
            operation="submitted-report-delta-acceptance",
            status=(
                "passed" if args.classification in NON_MATERIAL_SUBMITTED_REPORT_DELTA_CLASSIFICATIONS else "blocked"
            ),
            actor=args.recorded_by,
            summary="Recorded submitted opponent report public-form delta classification.",
            command=f"record-submitted-report-delta {args.case_id} {round_id}",
            artifacts=[OPPONENT_REPORT_SUBMITTED_RECORD_REL, OPPONENT_REPORT_DELTAS_REL],
            checks=["check-opponent-report"],
        )
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote {rel_repo(root, output)}")
    return 0


def console_main() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(console_main())
