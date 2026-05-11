"""Shared CLI runner for internal evidence artifact validators."""

from __future__ import annotations

import argparse

from thesis_review_workflow.cli.context import (
    repo_root,
    require_case_dir,
    require_round_dir,
    resolve_round,
    validate_id,
)
from thesis_review_workflow.internal_evidence_validators import PROFILES, validate_artifact_path
from thesis_review_workflow.paths import rel_repo


def build_parser(prog: str, description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=prog, description=description)
    handoff = parser.add_mutually_exclusive_group()
    handoff.add_argument("--require-synthesis-handoff", action="store_true")
    handoff.add_argument("--warn-synthesis-handoff", action="store_true")
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    return parser


def run(profile_key: str, prog: str, description: str, argv: list[str] | None = None) -> int:
    args = build_parser(prog, description).parse_args(argv)
    validate_id("CASE_ID", args.case_id)
    root = repo_root()
    case_dir = require_case_dir(root, args.case_id)
    round_id = resolve_round(case_dir, args.round_id)
    round_dir = require_round_dir(case_dir, args.case_id, round_id)
    profile = PROFILES[profile_key]
    artifact_path = round_dir / profile.relative_path

    result = validate_artifact_path(
        artifact_path,
        profile,
        require_synthesis_handoff=args.require_synthesis_handoff,
        warn_synthesis_handoff=args.warn_synthesis_handoff,
    )
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    if not result.ok:
        for error in result.errors:
            print(f"ERROR: {error}")
        return 1
    print(f"Validated {rel_repo(root, artifact_path)}")
    return 0
