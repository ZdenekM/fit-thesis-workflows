"""Validate one assignment variant's bundle and its approval before publication."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from thesis_review_workflow.assignment_bundle import (
    approval_rel,
    bundle_paths,
    validate_bundle_approval_payload,
)
from thesis_review_workflow.cli.check_assignment_draft import check_case
from thesis_review_workflow.cli.context import repo_root, require_case_dir, validate_id
from thesis_review_workflow.paths import rel_repo


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/check-assignment-bundle",
        description="Validate one variant's bundle, its approval record, and its hashes.",
    )
    parser.add_argument("case_id")
    parser.add_argument("variant")
    return parser


def check_bundle(case_dir: Path, case_id: str, variant: str) -> list[str]:
    # Structure first: an approval over a structurally broken bundle would be worse
    # than no approval, because it reads as a reviewed artifact.
    draft_findings, _ = check_case(case_dir, variant)
    if draft_findings:
        return [
            "the structural check must pass before an approval means anything; "
            "run scripts/check-assignment-draft",
            *draft_findings,
        ]

    rel_path = approval_rel(variant)
    path = case_dir / rel_path
    if not path.is_file():
        return [
            f"missing {rel_path}; an independent reviewer must approve this bundle before it is "
            "published to FIT IS or its brief is sent"
        ]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        return [f"{rel_path}: cannot be read as JSON: {error}"]

    return validate_bundle_approval_payload(payload, case_dir, case_id=case_id, variant=variant, rel_path=rel_path)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    validate_id("CASE_ID", args.case_id)
    root = repo_root()
    case_dir = require_case_dir(root, args.case_id)

    findings = check_bundle(case_dir, args.case_id, args.variant)
    print(f"Topic case: {rel_repo(root, case_dir)}")
    print(f"Variant: {args.variant}")
    if findings:
        for finding in findings:
            print(f"ERROR: {finding}")
        return 1
    print(f"Bundle files bound by the approval: {', '.join(bundle_paths(args.variant))}")
    print("Assignment bundle check passed")
    print(
        "This checks structure, binding and reviewer distinctness only. The operator reading named "
        "in the plan's acceptance contract is still required before publishing or sending."
    )
    return 0


def console_main() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(console_main())
