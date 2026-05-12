"""Write a hash-bound supervisor confirmation for a reviewed supervisor report."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from thesis_review_workflow.artifact_validation import sha256_file
from thesis_review_workflow.cli.context import (
    repo_root,
    require_case_dir,
    require_round_dir,
    resolve_round,
    validate_id,
)
from thesis_review_workflow.commands import command_display, run_step
from thesis_review_workflow.paths import rel_repo
from thesis_review_workflow.review_approvals import APPROVAL_PROFILES, validate_review_approval_with_manifest
from thesis_review_workflow.review_manifest import MANIFEST_REL, load_manifest
from thesis_review_workflow.structured_evidence import (
    STRUCTURED_EVIDENCE_SCHEMAS,
    SUPERVISOR_REPORT_CONFIRMATION_REL,
    SUPERVISOR_REPORT_TRACE_REL,
    validate_structured_evidence_artifact,
)
from thesis_review_workflow.supervisor_report import (
    SUPERVISOR_REPORT_DRAFT_REL,
    SUPERVISOR_REPORT_REVIEWED_REL,
    GradePoints,
    extract_markdown_grade_points,
    require_concrete_grade_points,
    trace_grade_points,
    validate_draft_metadata,
    validate_report_markdown,
)

APPROVAL_PROFILE = APPROVAL_PROFILES["supervisor-report"]


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/confirm-supervisor-report",
        description=(
            "Write work/supervisor_report_confirmation.json after the supervisor confirms the reviewed "
            "report text, private student comment, grade, and points."
        ),
    )
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    parser.add_argument(
        "--confirmed-by", required=True, help="human supervisor identifier recorded in the confirmation"
    )
    parser.add_argument("--confirmed-at", default="", help="ISO timestamp; defaults to current UTC time")
    parser.add_argument("--grade", choices=["A", "B", "C", "D", "E", "F"], default="")
    parser.add_argument("--points", type=int, default=None)
    parser.add_argument(
        "--force", action="store_true", help=f"overwrite an existing {SUPERVISOR_REPORT_CONFIRMATION_REL}"
    )
    return parser


def run_required(root: Path, label: str, command: list[str]) -> None:
    result = run_step(root, label, command)
    if not result.ok:
        detail = f"\n{result.output}" if result.output else ""
        raise ValueError(f"required command failed: {command_display(command)}{detail}")


def load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing required artifact: {label}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {label}: {exc.msg}") from exc
    if not isinstance(loaded, dict):
        raise ValueError(f"invalid JSON in {label}: expected object")
    return loaded


def compare_grade_points(left_label: str, left: GradePoints, right_label: str, right: GradePoints) -> list[str]:
    errors: list[str] = []
    if left.grade and right.grade and left.grade != right.grade:
        errors.append(f"{left_label} grade {left.grade} does not match {right_label} grade {right.grade}")
    if left.points is not None and right.points is not None and left.points != right.points:
        errors.append(f"{left_label} points {left.points} do not match {right_label} points {right.points}")
    return errors


def validate_reviewed_report(round_dir: Path, *, case_id: str, round_id: str) -> GradePoints:
    errors: list[str] = []
    errors.extend(
        validate_structured_evidence_artifact(
            round_dir,
            SUPERVISOR_REPORT_TRACE_REL,
            case_id=case_id,
            round_id=round_id,
        )
    )
    trace = load_json_object(round_dir / SUPERVISOR_REPORT_TRACE_REL, SUPERVISOR_REPORT_TRACE_REL)
    trace_values = trace_grade_points(trace)
    errors.extend(require_concrete_grade_points("supervisor report trace", trace_values))

    draft_path = round_dir / SUPERVISOR_REPORT_DRAFT_REL
    if not draft_path.is_file():
        errors.append(f"missing review-basis draft: {SUPERVISOR_REPORT_DRAFT_REL}")
    else:
        draft_text = draft_path.read_text(encoding="utf-8")
        validate_draft_metadata(draft_text, round_dir, errors)
        errors.extend(validate_report_markdown(draft_text, require_grade_points=False))

    reviewed_path = round_dir / SUPERVISOR_REPORT_REVIEWED_REL
    if not reviewed_path.is_file():
        errors.append(f"missing reviewed supervisor report: {SUPERVISOR_REPORT_REVIEWED_REL}")
        raise ValueError("\n".join(errors))
    reviewed_text = reviewed_path.read_text(encoding="utf-8")
    errors.extend(validate_report_markdown(reviewed_text, require_grade_points=True))
    reviewed_grade_points = extract_markdown_grade_points(reviewed_text, require=True)
    errors.extend(reviewed_grade_points.errors)
    errors.extend(
        compare_grade_points(
            "reviewed supervisor report",
            reviewed_grade_points,
            "supervisor report trace",
            trace_values,
        )
    )
    if errors:
        raise ValueError("\n".join(errors))
    return reviewed_grade_points


def require_current_review_approval(round_dir: Path, *, case_id: str, round_id: str) -> None:
    approval_rel = APPROVAL_PROFILE.approval_path
    manifest_rel = MANIFEST_REL.as_posix()
    approval = load_json_object(round_dir / approval_rel, approval_rel)
    try:
        manifest = load_manifest(round_dir / MANIFEST_REL)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {manifest_rel}: {exc.msg}") from exc
    if not manifest:
        raise ValueError(f"missing required review manifest: {manifest_rel}")
    errors = validate_review_approval_with_manifest(
        approval,
        approval_rel,
        round_dir,
        manifest=manifest,
        case_id=case_id,
        round_id=round_id,
        reviewed_artifact_path=SUPERVISOR_REPORT_REVIEWED_REL,
    )
    if errors:
        raise ValueError("\n".join(errors))


def build_confirmation_payload(
    round_dir: Path,
    *,
    case_id: str,
    round_id: str,
    confirmed_by: str,
    confirmed_at: str,
    grade_points: GradePoints,
) -> dict[str, Any]:
    if not grade_points.grade or grade_points.points is None:
        raise ValueError("reviewed supervisor report must contain a concrete grade and point value")
    return {
        "schema_version": STRUCTURED_EVIDENCE_SCHEMAS[SUPERVISOR_REPORT_CONFIRMATION_REL],
        "case_id": case_id,
        "round_id": round_id,
        "generated_at": confirmed_at,
        "producer_type": "human",
        "producer_role": "supervisor",
        "producer_agent": None,
        "human_reviewer_note": (
            "Supervisor confirmed the reviewed report text, private student comment, grade, and points."
        ),
        "source_refs": [SUPERVISOR_REPORT_REVIEWED_REL],
        "limitations": [],
        "reviewed_report_path": SUPERVISOR_REPORT_REVIEWED_REL,
        "reviewed_report_sha256": sha256_file(round_dir / SUPERVISOR_REPORT_REVIEWED_REL),
        "grade": grade_points.grade,
        "points": grade_points.points,
        "official_text_confirmed": True,
        "student_comment_confirmed": True,
        "ready_for_is": True,
        "confirmed_by": confirmed_by,
        "confirmed_at": confirmed_at,
    }


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv[1:])
    validate_id("CASE_ID", args.case_id)
    if args.round_id is not None:
        validate_id("ROUND_ID", args.round_id)
    if args.points is not None and (args.points < 0 or args.points > 100):
        print("ERROR: --points must be between 0 and 100", file=sys.stderr)
        return 1

    root = repo_root()
    try:
        case_dir = require_case_dir(root, args.case_id)
        round_id = resolve_round(case_dir, args.round_id)
        round_dir = require_round_dir(case_dir, args.case_id, round_id)
        run_required(
            root, "supervisor report readiness", ["scripts/check-supervisor-report-ready", args.case_id, round_id]
        )
        reviewed_grade_points = validate_reviewed_report(round_dir, case_id=args.case_id, round_id=round_id)
        require_current_review_approval(round_dir, case_id=args.case_id, round_id=round_id)
        expected = GradePoints(args.grade or reviewed_grade_points.grade, args.points, ())
        errors = compare_grade_points(
            "requested confirmation", expected, "reviewed supervisor report", reviewed_grade_points
        )
        if errors:
            raise ValueError("\n".join(errors))
        confirmation_path = round_dir / SUPERVISOR_REPORT_CONFIRMATION_REL
        if confirmation_path.exists() and not args.force:
            raise ValueError(
                f"refusing to overwrite existing confirmation without --force: {SUPERVISOR_REPORT_CONFIRMATION_REL}"
            )
        payload = build_confirmation_payload(
            round_dir,
            case_id=args.case_id,
            round_id=round_id,
            confirmed_by=args.confirmed_by,
            confirmed_at=args.confirmed_at or now_utc(),
            grade_points=reviewed_grade_points,
        )
        confirmation_path.parent.mkdir(parents=True, exist_ok=True)
        confirmation_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
        )
        run_required(
            root,
            "supervisor report confirmation",
            ["scripts/check-supervisor-report", "--require-reviewed", "--require-confirmation", args.case_id, round_id],
        )
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote {rel_repo(root, round_dir / SUPERVISOR_REPORT_CONFIRMATION_REL)}")
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
