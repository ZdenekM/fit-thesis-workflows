"""Record a supervisor-report post-review amendment through the shared delta ledger."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from thesis_review_workflow.amendments import (
    amendment_record_rel,
    amendment_snapshot_rel,
    build_report_amendment_payload,
    copy_previous_snapshot,
)
from thesis_review_workflow.cli.context import (
    repo_root,
    require_case_dir,
    require_round_dir,
    resolve_round,
    validate_id,
)
from thesis_review_workflow.paths import rel_repo, resolve_caller_path
from thesis_review_workflow.supervisor_report import SUPERVISOR_REPORT_REVIEWED_REL


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/record-report-amendment",
        description=(
            "Profile-specific wrapper around record-review-delta for supervisor-report edits. "
            "The canonical record is written under work/review_deltas."
        ),
    )
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    parser.add_argument(
        "--type",
        required=True,
        choices=["style_only", "public_text_delta", "private_comment_delta", "material_claim_delta"],
        help="report amendment class; material_claim_delta reopens normal semantic review",
    )
    parser.add_argument("--previous-reviewed", required=True, help="previous reviewed Markdown snapshot")
    parser.add_argument("--current-artifact", default=SUPERVISOR_REPORT_REVIEWED_REL)
    parser.add_argument("--approved-by", required=True, help="human or reviewer identity approving the bounded delta")
    parser.add_argument("--rationale", required=True, help="why this delta is bounded, or why review must reopen")
    parser.add_argument("--amended-at", default="", help="ISO timestamp; defaults to current UTC time")
    parser.add_argument("--force", action="store_true", help="overwrite existing amendment record/snapshot")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    validate_id("CASE_ID", args.case_id)
    if args.round_id is not None:
        validate_id("ROUND_ID", args.round_id)
    root = repo_root()
    snapshot_rel = ""
    snapshot_copied = False
    try:
        case_dir = require_case_dir(root, args.case_id)
        round_id = resolve_round(case_dir, args.round_id)
        round_dir = require_round_dir(case_dir, args.case_id, round_id)
        amended_at = args.amended_at or now_utc()
        snapshot_rel = amendment_snapshot_rel(amended_at, args.type)
        copy_previous_snapshot(resolve_caller_path(args.previous_reviewed), round_dir, snapshot_rel, force=args.force)
        snapshot_copied = True
        payload = build_report_amendment_payload(
            round_dir,
            case_id=args.case_id,
            round_id=round_id,
            amendment_type=args.type,
            previous_snapshot_rel=snapshot_rel,
            current_artifact_rel=args.current_artifact,
            amended_at=amended_at,
            approved_by=args.approved_by,
            rationale=args.rationale,
        )
        record_rel = amendment_record_rel(amended_at, args.type)
        output = round_dir / record_rel
        if output.exists() and not args.force:
            raise ValueError(f"refusing to overwrite existing amendment record without --force: {record_rel}")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, ValueError) as exc:
        if "round_dir" in locals() and snapshot_rel and snapshot_copied and not args.force:
            (round_dir / snapshot_rel).unlink(missing_ok=True)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote {rel_repo(root, output)}")
    return 0


def console_main() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(console_main())
