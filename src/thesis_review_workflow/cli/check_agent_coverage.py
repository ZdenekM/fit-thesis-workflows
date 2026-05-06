"""Validate required agent-role coverage for a thesis review round."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from thesis_review_workflow.agent_coverage import COVERAGE_REL, load_json_object, validate_coverage
from thesis_review_workflow.cli.context import (
    load_json_manifest,
    repo_root,
    require_case_dir,
    require_round_dir,
    resolve_round,
    validate_id,
)

MANIFEST_REL = Path("work/review_manifest.json")


def load_manifest(path: Path) -> dict:
    return load_json_manifest(
        path,
        label=MANIFEST_REL.as_posix(),
        missing_message=f"ERROR: Missing review manifest: {MANIFEST_REL.as_posix()}",
        not_object_message=f"ERROR: Review manifest must be a JSON object: {MANIFEST_REL.as_posix()}",
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
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

    manifest = load_manifest(round_dir / MANIFEST_REL)
    try:
        coverage = load_json_object(round_dir / COVERAGE_REL)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: Invalid agent coverage {COVERAGE_REL.as_posix()}: {exc}", file=sys.stderr)
        return 1

    errors, warnings = validate_coverage(coverage, manifest, args.case_id, round_id, round_dir)
    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("Agent coverage check passed")
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
