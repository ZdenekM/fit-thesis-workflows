"""Validate expected outputs after a thesis-review agent wave."""

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
from thesis_review_workflow.paths import is_safe_round_relative_path
from thesis_review_workflow.review_wave_gate import builtin_wave_spec, load_wave_spec, validate_wave


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/check-review-wave",
        description="Check expected files, validators, approval records, and whitespace after an agent wave.",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--workflow", "--profile", dest="workflow")
    source.add_argument("--spec", help="round-relative JSON wave spec path")
    parser.add_argument("--wave", default="draft", help="wave name for --workflow")
    parser.add_argument("--require-handoffs", action="store_true")
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(sys.argv[1:] if argv is None else argv[1:])
    validate_id("CASE_ID", args.case_id, stderr=True)

    root = repo_root()
    try:
        case_dir = require_case_dir(root, args.case_id, error_prefix="ERROR: ", stderr=True)
        round_id = resolve_round(case_dir, args.round_id, stderr=True)
        validate_id("ROUND_ID", round_id, stderr=True)
        round_dir = require_round_dir(case_dir, args.case_id, round_id, error_prefix="ERROR: ", stderr=True)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2

    try:
        if args.spec:
            if not is_safe_round_relative_path(args.spec):
                print("ERROR: --spec must be a safe round-relative path", file=sys.stderr)
                return 2
            spec = load_wave_spec(round_dir / args.spec)
        else:
            spec = builtin_wave_spec(args.workflow, args.wave)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    result = validate_wave(
        root,
        round_dir,
        spec,
        case_id=args.case_id,
        round_id=round_id,
        require_handoffs=args.require_handoffs,
    )
    for item in result.passed:
        print(f"PASS: {item}")
    for item in result.warnings:
        print(f"WARNING: {item}", file=sys.stderr)
    if result.errors:
        for item in result.errors:
            print(f"ERROR: {item}", file=sys.stderr)
        return 1
    print(f"Review wave check passed: {spec.workflow}:{spec.wave}")
    return 0


def console_main() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(console_main())
