"""Record a structured post-review delta for a reviewed workflow artifact."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from thesis_review_workflow.cli.context import (
    repo_root,
    require_case_dir,
    require_round_dir,
    resolve_round,
    validate_id,
)
from thesis_review_workflow.paths import rel_repo, resolve_caller_path
from thesis_review_workflow.review_delta import (
    DELTA_TYPES,
    TYPED_EXCEPTION_TYPES,
    build_review_delta_payload,
    copy_previous_snapshot,
    review_delta_record_rel,
    review_delta_snapshot_rel,
)
from thesis_review_workflow.review_profiles import get_workflow_review_profile, profiles_by_id


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/record-review-delta",
        description=(
            "Record a hash-bound operator delta after a reviewed artifact exists. "
            "Material claim and evidence-challenge deltas reopen profile-specific review."
        ),
    )
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    parser.add_argument("--profile", required=True, choices=sorted(profiles_by_id()))
    parser.add_argument("--type", required=True, choices=sorted(DELTA_TYPES), dest="delta_type")
    parser.add_argument("--previous-artifact", required=True, help="previous reviewed artifact snapshot")
    parser.add_argument(
        "--current-artifact", default="", help="round-relative current artifact; defaults to profile final"
    )
    parser.add_argument("--affected-section", action="append", default=[], help="repeat for each affected section")
    parser.add_argument("--evidence-ref", action="append", default=[], help="round-relative evidence anchor to verify")
    parser.add_argument("--rationale", required=True)
    parser.add_argument(
        "--approval-record", default="", help="round-relative approval record; defaults to profile approval"
    )
    parser.add_argument("--typed-exception-type", choices=sorted(TYPED_EXCEPTION_TYPES), default="")
    parser.add_argument("--typed-exception-rationale", default="")
    parser.add_argument("--approved-by", default="")
    parser.add_argument("--promotion-target", default="")
    parser.add_argument("--generated-at", default="", help="ISO timestamp; defaults to current UTC time")
    parser.add_argument("--force", action="store_true", help="overwrite existing delta record/snapshot")
    return parser


def previous_snapshot_suffix(path_value: str) -> str:
    suffix = Path(path_value).suffix
    return suffix if suffix else ".md"


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
        profile = get_workflow_review_profile(args.profile)
        generated_at = args.generated_at or now_utc()
        current_artifact = args.current_artifact or profile.final_artifact
        approval_record = args.approval_record or profile.approval_record
        snapshot_rel = review_delta_snapshot_rel(
            generated_at,
            args.delta_type,
            suffix=previous_snapshot_suffix(args.previous_artifact),
        )
        copy_previous_snapshot(resolve_caller_path(args.previous_artifact), round_dir, snapshot_rel, force=args.force)
        snapshot_copied = True
        payload = build_review_delta_payload(
            round_dir,
            case_id=args.case_id,
            round_id=round_id,
            profile_id=profile.profile_id,
            delta_type=args.delta_type,
            previous_snapshot_rel=snapshot_rel,
            current_artifact_rel=current_artifact,
            generated_at=generated_at,
            rationale=args.rationale,
            affected_sections=args.affected_section,
            evidence_refs=args.evidence_ref,
            approval_record_rel=approval_record,
            typed_exception_type=args.typed_exception_type,
            typed_exception_rationale=args.typed_exception_rationale,
            approved_by=args.approved_by,
            promotion_target=args.promotion_target,
        )
        record_rel = review_delta_record_rel(generated_at, args.delta_type)
        output = round_dir / record_rel
        if output.exists() and not args.force:
            raise ValueError(f"refusing to overwrite existing delta record without --force: {record_rel}")
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
