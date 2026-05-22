"""Expand submitted parent bundles into the ignored round workspace."""

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
    SUBMISSION_BUNDLE_EXPANSION_PRODUCER,
    BundleExpansionLimits,
    materialize_submission_bundles,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/materialize-submission-bundle",
        description=(
            "Expand submitted parent bundles into work/submission_bundle and record provenance. "
            "This is for review inspection; use materialize-submission-bundle-candidate when a nested "
            "artifact must become a direct inputs/ artifact."
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
    parser.add_argument("--max-expand-bytes", type=int, default=BundleExpansionLimits.max_total_bytes)
    parser.add_argument("--max-file-bytes", type=int, default=BundleExpansionLimits.max_file_bytes)
    parser.add_argument("--max-entries", type=int, default=BundleExpansionLimits.max_entries)
    parser.add_argument("--max-archive-depth", type=int, default=BundleExpansionLimits.max_archive_depth)
    parser.add_argument("--refresh", action="store_true", help="Rebuild existing expanded bundle directories.")
    parser.add_argument("--generated-at", default="", help=argparse.SUPPRESS)
    return parser


def positive_int(value: int, *, option: str) -> int:
    if value <= 0:
        raise ValueError(f"{option} must be greater than zero")
    return value


def limits_from_args(args: argparse.Namespace) -> BundleExpansionLimits:
    return BundleExpansionLimits(
        max_total_bytes=positive_int(args.max_expand_bytes, option="--max-expand-bytes"),
        max_file_bytes=positive_int(args.max_file_bytes, option="--max-file-bytes"),
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
        round_dir = require_round_dir(case_dir, args.case_id, round_id, stderr=True)
        limits = limits_from_args(args)
        payload, manifest_path = materialize_submission_bundles(
            case_id=args.case_id,
            round_id=round_id,
            round_dir=round_dir,
            bundle_refs=args.bundle,
            limits=limits,
            generated_at=args.generated_at or None,
            producer=SUBMISSION_BUNDLE_EXPANSION_PRODUCER,
            refresh=args.refresh,
        )
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"Wrote {rel_repo(root, manifest_path)}")
    for record in payload.get("expansions", []):
        if not isinstance(record, dict):
            continue
        print(
            "Expanded "
            f"{record.get('source_bundle_ref', '')} -> {record.get('target_ref', '')} "
            f"({record.get('files_written', 0)} files, "
            f"{record.get('archives_expanded', 0)} archive(s), "
            f"{record.get('skipped_entry_count', 0)} skipped)"
        )
    return 0


def console_main() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(console_main())
