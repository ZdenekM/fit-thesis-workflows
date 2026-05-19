"""Materialize one selected submitted-bundle inventory candidate."""

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
from thesis_review_workflow.submission_bundle import materialize_submission_bundle_candidate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/materialize-submission-bundle-candidate",
        description=(
            "Materialize one selected candidate from work/submission_bundle_inventory.json "
            "as a direct inputs/ artifact and record provenance. Re-run review-round-start "
            "after materialization so the existing round lifecycle owns downstream state."
        ),
    )
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--output", default="", metavar="ROUND_REL_INPUT_PATH")
    parser.add_argument("--allow-ambiguous", action="store_true")
    parser.add_argument("--allow-duplicate", action="store_true")
    parser.add_argument("--max-materialize-bytes", type=int, default=250 * 1024 * 1024)
    parser.add_argument("--generated-at", default="", help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.max_materialize_bytes <= 0:
        print("ERROR: --max-materialize-bytes must be greater than zero", file=sys.stderr)
        return 2
    try:
        validate_id("case_id", args.case_id, stderr=True)
        root = repo_root()
        case_dir = require_case_dir(root, args.case_id, stderr=True)
        round_id = resolve_round(case_dir, args.round_id, stderr=True)
        round_dir = require_round_dir(case_dir, args.case_id, round_id, stderr=True)
        result = materialize_submission_bundle_candidate(
            case_id=args.case_id,
            round_id=round_id,
            round_dir=round_dir,
            candidate_id=args.candidate_id,
            output_ref=args.output or None,
            allow_ambiguous=args.allow_ambiguous,
            allow_duplicate=args.allow_duplicate,
            max_materialize_bytes=args.max_materialize_bytes,
            generated_at=args.generated_at or None,
        )
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"{result.action}: {result.materialized_ref}")
    print(f"Manifest: {rel_repo(root, result.manifest_path)}")
    print("Next: rerun review-round-start with the materialized inputs/<...> ref.")
    print("Then run prepare-code-workspace and prepare-review-round.")
    return 0


def console_main() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(console_main())
