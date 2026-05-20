"""Validate the applied opponent-report calibration basis."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from thesis_review_workflow.cli.context import (
    repo_root,
    require_case_dir,
    require_round_dir,
    resolve_round,
    validate_id,
)
from thesis_review_workflow.cli.check_reviewer_profile import profile_values
from thesis_review_workflow.report_calibration import (
    REPORT_CALIBRATION_BASIS_REL,
    validate_report_calibration_artifact,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/check-report-calibration",
        description=__doc__,
    )
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    return parser


def effective_reviewer_profile(case_md: Path, root: Path) -> tuple[str, list[str], list[str]]:
    errors: list[str] = []
    values = profile_values(case_md)
    if len(values) > 1:
        return "", [], [f"{case_md}: duplicate Reviewer profile fields"]
    configured = values[0] if values else "default"
    configured = configured or "default"
    relative_files = ["profiles/default.md"]
    if configured == "default":
        profile_id = "default"
        if (root / "profiles" / "local" / "default.md").is_file():
            relative_files.append("profiles/local/default.md")
    elif configured.startswith("local/"):
        profile_id = configured.removeprefix("local/")
        try:
            validate_id("profile-id", profile_id)
        except ValueError as exc:
            errors.append(str(exc))
        relative_files.append(f"profiles/local/{profile_id}.md")
    else:
        errors.append(f"{case_md}: Reviewer profile must be default or local/<profile-id>")
        profile_id = configured
    for rel_path in relative_files:
        if not (root / rel_path).is_file():
            errors.append(f"{case_md}: missing effective reviewer profile source {rel_path}")
    return profile_id, relative_files, errors


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    validate_id("CASE_ID", args.case_id)
    root = repo_root()
    case_dir = require_case_dir(root, args.case_id)
    round_id = resolve_round(case_dir, args.round_id)
    round_dir = require_round_dir(case_dir, args.case_id, round_id)
    reviewer_profile_id, profile_sources, profile_errors = effective_reviewer_profile(case_dir / "case.md", root)
    if profile_errors:
        for error in profile_errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    errors = validate_report_calibration_artifact(
        round_dir,
        REPORT_CALIBRATION_BASIS_REL,
        case_id=args.case_id,
        round_id=round_id,
        expected_reviewer_profile_id=reviewer_profile_id,
        expected_profile_source_paths=profile_sources,
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Report calibration basis check passed.")
    return 0


def console_main() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(console_main())
