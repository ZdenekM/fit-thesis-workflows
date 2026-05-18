"""Validate literature/citation review output and targeted source acquisition."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from thesis_review_workflow.cli.context import (
    repo_root,
    require_case_dir,
    require_round_dir,
    resolve_round,
    validate_id,
)
from thesis_review_workflow.internal_evidence_validators import PROFILES, validate_artifact_path
from thesis_review_workflow.literature_source_acquisition import (
    SOURCE_ACQUISITION_REL,
    validate_source_acquisition_payload,
)
from thesis_review_workflow.paths import rel_repo


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/check-literature-citation-review",
        description="Validate literature/citation review and targeted source acquisition evidence.",
    )
    handoff = parser.add_mutually_exclusive_group()
    handoff.add_argument("--require-synthesis-handoff", action="store_true")
    handoff.add_argument("--warn-synthesis-handoff", action="store_true")
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    return parser


def validate_source_acquisition_file(path: Path, case_id: str, round_id: str, round_dir: Path) -> list[str]:
    if not path.is_file():
        return [
            "missing targeted literature source acquisition artifact: "
            f"{SOURCE_ACQUISITION_REL}; select key/suspicious citations and record legal source attempts"
        ]
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{SOURCE_ACQUISITION_REL}: invalid JSON: {exc.msg}"]
    return validate_source_acquisition_payload(
        loaded,
        SOURCE_ACQUISITION_REL,
        round_dir=round_dir,
        case_id=case_id,
        round_id=round_id,
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    validate_id("CASE_ID", args.case_id)
    root = repo_root()
    case_dir = require_case_dir(root, args.case_id)
    round_id = resolve_round(case_dir, args.round_id)
    round_dir = require_round_dir(case_dir, args.case_id, round_id)

    profile = PROFILES["literature_citation"]
    artifact_path = round_dir / profile.relative_path
    result = validate_artifact_path(
        artifact_path,
        profile,
        require_synthesis_handoff=args.require_synthesis_handoff,
        warn_synthesis_handoff=args.warn_synthesis_handoff,
    )
    errors = list(result.errors)
    warnings = list(result.warnings)
    errors.extend(
        validate_source_acquisition_file(
            round_dir / SOURCE_ACQUISITION_REL,
            args.case_id,
            round_id,
            round_dir,
        )
    )

    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"Validated {rel_repo(root, artifact_path)} and {SOURCE_ACQUISITION_REL}")
    return 0


def console_main() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(console_main())
