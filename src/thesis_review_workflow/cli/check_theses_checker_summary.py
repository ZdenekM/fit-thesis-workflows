"""Validate an operator-supplied FIT Theses Checker summary."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from thesis_review_workflow.cli.context import (
    repo_root,
    require_case_dir,
    require_round_dir,
    resolve_round,
    validate_id,
)
from thesis_review_workflow.paths import rel_repo
from thesis_review_workflow.theses_checker_summary import (
    THESES_CHECKER_SUMMARY_REL,
    validate_theses_checker_summary_artifact,
)

ARTIFACT_REL = Path(THESES_CHECKER_SUMMARY_REL)


def load_artifact(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("Theses Checker summary artifact must be a JSON object")
    return loaded


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/check-theses-checker-summary",
        description="Validate work/theses_checker_summary.json for opponent technical-report-scope evidence.",
    )
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv[1:])
    validate_id("CASE_ID", args.case_id)
    if args.round_id is not None:
        validate_id("ROUND_ID", args.round_id)

    root = repo_root()
    case_dir = require_case_dir(root, args.case_id)
    round_id = resolve_round(case_dir, args.round_id)
    round_dir = require_round_dir(case_dir, args.case_id, round_id)

    artifact_path = round_dir / ARTIFACT_REL
    errors = validate_theses_checker_summary_artifact(
        round_dir,
        ARTIFACT_REL,
        case_id=args.case_id,
        round_id=round_id,
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(
            "Create `work/theses_checker_summary.json` with `scripts/record-theses-checker-summary` "
            "or an explicitly authorized human/agent handoff before making categorical normostrany claims."
        )
        return 1

    artifact = load_artifact(artifact_path)
    checked_pdf = artifact.get("checked_pdf")
    checked_pdf_status = "bound" if isinstance(checked_pdf, dict) else "typed limitation"
    print(f"Theses Checker summary artifact: {rel_repo(root, artifact_path)}")
    print(f"Normostrany: {artifact.get('normostrany')}")
    print(f"Status: {artifact.get('status')}")
    print(f"Checked rendered PDF: {checked_pdf_status}")
    print("Theses Checker summary structured artifact check passed")
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
