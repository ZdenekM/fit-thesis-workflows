"""Validate supervisor-report trace, draft, reviewed output, and confirmation."""

from __future__ import annotations

import argparse
import json
import sys

from thesis_review_workflow.amendments import validate_report_amendment_record
from thesis_review_workflow.cli.context import (
    repo_root,
    require_case_dir,
    require_round_dir,
    resolve_round,
    validate_id,
)
from thesis_review_workflow.commands import run_step
from thesis_review_workflow.paths import is_safe_round_relative_path
from thesis_review_workflow.structured_evidence import (
    SUPERVISOR_REPORT_CONFIRMATION_REL,
    SUPERVISOR_REPORT_FEEDBACK_HISTORY_REL,
    SUPERVISOR_REPORT_TRACE_REL,
    validate_structured_evidence_artifact,
)
from thesis_review_workflow.submitted_reports import validate_submitted_report_record
from thesis_review_workflow.supervisor_report import (
    SUPERVISOR_REPORT_AMENDMENTS_DIR_REL,
    SUPERVISOR_REPORT_DRAFT_REL,
    SUPERVISOR_REPORT_REVIEWED_REL,
    SUPERVISOR_REPORT_SUBMITTED_DIR_REL,
    SUPERVISOR_REPORT_SUBMITTED_RECORD_REL,
    confirmation_grade_points,
    extract_markdown_grade_points,
    require_concrete_grade_points,
    trace_grade_points,
    validate_draft_metadata,
    validate_report_markdown,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/check-supervisor-report",
        description="Check formal supervisor report structured artifacts and Markdown shape.",
    )
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    parser.add_argument("--path", default=SUPERVISOR_REPORT_DRAFT_REL, help="round-relative draft path")
    parser.add_argument(
        "--require-reviewed",
        action="store_true",
        help=f"require {SUPERVISOR_REPORT_REVIEWED_REL} to exist and pass Markdown checks",
    )
    parser.add_argument(
        "--require-confirmation",
        action="store_true",
        help=f"require {SUPERVISOR_REPORT_CONFIRMATION_REL} to exist and pass hash checks",
    )
    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv[1:])
    validate_id("CASE_ID", args.case_id, stderr=True)
    if not is_safe_round_relative_path(args.path):
        print("ERROR: --path must be relative inside the round", file=sys.stderr)
        return 2

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
    ready = run_step(
        root, "supervisor report readiness", ["scripts/check-supervisor-report-ready", args.case_id, round_id]
    )
    if not ready.ok:
        detail = f":\n{ready.output}" if ready.output else ""
        errors.append(f"supervisor report readiness failed{detail}")

    errors.extend(
        validate_structured_evidence_artifact(
            round_dir,
            SUPERVISOR_REPORT_TRACE_REL,
            case_id=args.case_id,
            round_id=round_id,
        )
    )
    trace_payload = load_json_object(round_dir / SUPERVISOR_REPORT_TRACE_REL, errors)
    trace_values = trace_grade_points(trace_payload) if trace_payload is not None else None
    feedback_history = round_dir / SUPERVISOR_REPORT_FEEDBACK_HISTORY_REL
    if feedback_history.is_file():
        errors.extend(
            validate_structured_evidence_artifact(
                round_dir,
                SUPERVISOR_REPORT_FEEDBACK_HISTORY_REL,
                case_id=args.case_id,
                round_id=round_id,
            )
        )

    draft_path = round_dir / args.path
    draft_exists = draft_path.is_file()
    if draft_exists:
        text = draft_path.read_text(encoding="utf-8")
        validate_draft_metadata(text, round_dir, errors)
        errors.extend(validate_report_markdown(text, require_grade_points=False))
    elif args.path != SUPERVISOR_REPORT_DRAFT_REL:
        errors.append(f"missing supervisor report draft: {args.path}")

    reviewed_path = round_dir / SUPERVISOR_REPORT_REVIEWED_REL
    reviewed_grade_points = None
    final_mode = reviewed_path.is_file() or args.require_reviewed or args.require_confirmation
    if final_mode and trace_values is not None:
        errors.extend(require_concrete_grade_points("supervisor report trace", trace_values))
    if reviewed_path.is_file():
        if not draft_exists:
            errors.append(f"reviewed supervisor report requires review-basis draft: {SUPERVISOR_REPORT_DRAFT_REL}")
        reviewed_text = reviewed_path.read_text(encoding="utf-8")
        errors.extend(validate_report_markdown(reviewed_text, require_grade_points=True))
        reviewed_grade_points = extract_markdown_grade_points(reviewed_text, require=True)
        errors.extend(reviewed_grade_points.errors)
        if trace_payload is not None:
            errors.extend(
                compare_grade_points(
                    "reviewed supervisor report",
                    reviewed_grade_points,
                    "supervisor report trace",
                    trace_values,
                )
            )
    elif args.require_reviewed or args.require_confirmation:
        errors.append(f"missing reviewed supervisor report: {SUPERVISOR_REPORT_REVIEWED_REL}")

    confirmation_path = round_dir / SUPERVISOR_REPORT_CONFIRMATION_REL
    if confirmation_path.is_file():
        errors.extend(
            validate_structured_evidence_artifact(
                round_dir,
                SUPERVISOR_REPORT_CONFIRMATION_REL,
                case_id=args.case_id,
                round_id=round_id,
            )
        )
        confirmation_payload = load_json_object(confirmation_path, errors)
        if confirmation_payload is not None:
            confirmation = confirmation_grade_points(confirmation_payload)
            if reviewed_grade_points is not None:
                errors.extend(
                    compare_grade_points(
                        "supervisor report confirmation",
                        confirmation,
                        "reviewed supervisor report",
                        reviewed_grade_points,
                    )
                )
            if trace_payload is not None:
                errors.extend(
                    compare_grade_points(
                        "supervisor report confirmation",
                        confirmation,
                        "supervisor report trace",
                        trace_values,
                    )
                )
    elif args.require_confirmation:
        errors.append(f"missing supervisor report confirmation: {SUPERVISOR_REPORT_CONFIRMATION_REL}")

    submitted_record_path = round_dir / SUPERVISOR_REPORT_SUBMITTED_RECORD_REL
    if submitted_record_path.is_file():
        submitted_record = load_json_object(submitted_record_path, errors)
        if submitted_record is not None:
            errors.extend(
                validate_submitted_report_record(
                    submitted_record,
                    round_dir=round_dir,
                    case_id=args.case_id,
                    round_id=round_id,
                    rel_path=SUPERVISOR_REPORT_SUBMITTED_RECORD_REL,
                )
            )
    else:
        submitted_dir = round_dir / SUPERVISOR_REPORT_SUBMITTED_DIR_REL
        if submitted_dir.is_dir() and any(path.is_file() for path in submitted_dir.iterdir()):
            errors.append(
                f"{SUPERVISOR_REPORT_SUBMITTED_DIR_REL}: submitted-report files require "
                f"{SUPERVISOR_REPORT_SUBMITTED_RECORD_REL}"
            )

    amendment_dir = round_dir / SUPERVISOR_REPORT_AMENDMENTS_DIR_REL
    if amendment_dir.is_dir():
        amendment_records: list[dict[str, object]] = []
        for amendment_path in sorted(amendment_dir.glob("*.json")):
            amendment_record = load_json_object(amendment_path, errors)
            if amendment_record is not None:
                amendment_records.append(amendment_record)
                errors.extend(
                    validate_report_amendment_record(
                        amendment_record,
                        round_dir=round_dir,
                        case_id=args.case_id,
                        round_id=round_id,
                        rel_path=amendment_path.relative_to(round_dir).as_posix(),
                    )
                )
        referenced_snapshots = {
            record.get("previous_snapshot_path")
            for record in amendment_records
            if isinstance(record.get("previous_snapshot_path"), str)
        }
        for snapshot_path in sorted(amendment_dir.glob("*-before.md")):
            snapshot_rel = snapshot_path.relative_to(round_dir).as_posix()
            if snapshot_rel not in referenced_snapshots:
                errors.append(f"{snapshot_rel}: amendment snapshot has no matching JSON record")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Supervisor report trace/draft check passed")
    return 0


def console_main() -> int:
    return main(sys.argv)


def load_json_object(path, errors: list[str]) -> dict[str, object] | None:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        errors.append(f"{path.name}: invalid JSON: {exc.msg}")
        return None
    if not isinstance(loaded, dict):
        errors.append(f"{path.name}: JSON must be an object")
        return None
    return loaded


def compare_grade_points(left_label, left, right_label, right) -> list[str]:
    errors: list[str] = []
    if left.grade and right.grade and left.grade != right.grade:
        errors.append(f"{left_label} grade {left.grade} does not match {right_label} grade {right.grade}")
    if left.points is not None and right.points is not None and left.points != right.points:
        errors.append(f"{left_label} points {left.points} do not match {right_label} points {right.points}")
    return errors


if __name__ == "__main__":
    raise SystemExit(console_main())
