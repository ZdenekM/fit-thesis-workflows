"""Diagnostic submitted-bundle inventory helper."""

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
from thesis_review_workflow.paths import rel_repo
from thesis_review_workflow.submission_bundle import (
    SUBMISSION_BUNDLE_PRODUCER,
    BundleInventoryLimits,
    build_and_write_submission_bundle_inventory,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/inventory-submission-bundle",
        description=(
            "Write a bounded diagnostic inventory for submitted parent bundles. "
            "Normal intake ownership remains scripts/review-round-start."
        ),
    )
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    parser.add_argument(
        "--bundle",
        action="append",
        required=True,
        metavar="ROUND_REL_PATH",
        help="Round-relative submitted bundle path, usually inputs/<bundle.zip>.",
    )
    parser.add_argument("--max-archive-bytes", type=int, default=BundleInventoryLimits.max_archive_bytes)
    parser.add_argument("--max-nested-archive-bytes", type=int, default=BundleInventoryLimits.max_nested_archive_bytes)
    parser.add_argument("--max-hash-bytes", type=int, default=BundleInventoryLimits.max_hash_bytes)
    parser.add_argument("--max-read-bytes", type=int, default=BundleInventoryLimits.max_read_bytes)
    parser.add_argument("--max-entries", type=int, default=BundleInventoryLimits.max_entries)
    parser.add_argument("--max-archive-depth", type=int, default=BundleInventoryLimits.max_archive_depth)
    parser.add_argument("--generated-at", default="", help=argparse.SUPPRESS)
    return parser


def positive_int(value: int, *, option: str) -> int:
    if value <= 0:
        raise ValueError(f"{option} must be greater than zero")
    return value


def limits_from_args(args: argparse.Namespace) -> BundleInventoryLimits:
    return BundleInventoryLimits(
        max_archive_bytes=positive_int(args.max_archive_bytes, option="--max-archive-bytes"),
        max_nested_archive_bytes=positive_int(
            args.max_nested_archive_bytes,
            option="--max-nested-archive-bytes",
        ),
        max_hash_bytes=positive_int(args.max_hash_bytes, option="--max-hash-bytes"),
        max_read_bytes=positive_int(args.max_read_bytes, option="--max-read-bytes"),
        max_entries=positive_int(args.max_entries, option="--max-entries"),
        max_archive_depth=positive_int(args.max_archive_depth, option="--max-archive-depth"),
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        validate_id("case_id", args.case_id, stderr=True)
        root = repo_root()
        case_dir = require_case_dir(root, args.case_id, stderr=True)
        round_id = resolve_round(case_dir, args.round_id, stderr=True)
        require_round_dir(case_dir, args.case_id, round_id, stderr=True)
        limits = limits_from_args(args)
        round_dir = case_dir / "rounds" / round_id
        payload, json_path, md_path = build_and_write_submission_bundle_inventory(
            case_id=args.case_id,
            round_id=round_id,
            round_dir=round_dir,
            bundle_refs=args.bundle,
            limits=limits,
            generated_at=args.generated_at or None,
            producer=SUBMISSION_BUNDLE_PRODUCER,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    summary = payload.get("summary", {})
    print(f"Wrote {rel_repo(root, json_path)}")
    print(f"Wrote {rel_repo(root, md_path)}")
    print(
        "Candidates: "
        f"{summary.get('candidate_count', 0)} "
        f"({summary.get('needs_operator_selection_count', 0)} need selection)"
    )
    return 0


def console_main() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(console_main())
