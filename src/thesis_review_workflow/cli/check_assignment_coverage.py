"""Validate the structured assignment coverage artifact for opponent review."""

from __future__ import annotations

import argparse
import json
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
from thesis_review_workflow.structured_evidence import validate_structured_evidence_artifact

ARTIFACT_REL = Path("work/assignment_coverage_agent.json")


def load_artifact(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("assignment coverage artifact must be a JSON object")
    return loaded


def coverage_summary(points: list[Any]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for point in points:
        if not isinstance(point, dict):
            continue
        coverage = point.get("coverage")
        if not isinstance(coverage, dict):
            continue
        status = coverage.get("status")
        if isinstance(status, str):
            summary[status] = summary.get(status, 0) + 1
    return summary


def verification_count(points: list[Any]) -> int:
    count = 0
    for point in points:
        if not isinstance(point, dict):
            continue
        coverage = point.get("coverage")
        if isinstance(coverage, dict) and coverage.get("requires_reviewer_verification") is True:
            count += 1
    return count


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/check-assignment-coverage",
        description="Validate work/assignment_coverage_agent.json.",
    )
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    validate_id("CASE_ID", args.case_id)
    root = repo_root()
    case_dir = require_case_dir(root, args.case_id)
    round_id = resolve_round(case_dir, args.round_id)
    round_dir = require_round_dir(case_dir, args.case_id, round_id)

    artifact_path = round_dir / ARTIFACT_REL
    errors = validate_structured_evidence_artifact(
        round_dir,
        ARTIFACT_REL,
        case_id=args.case_id,
        round_id=round_id,
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(
            "Create `work/assignment_coverage_agent.json` with an explicitly authorized "
            "assignment-coverage agent or human reviewer before running this check."
        )
        return 1

    artifact = load_artifact(artifact_path)
    points = artifact.get("assignment_points")
    count = len(points) if isinstance(points, list) else 0
    point_list = points if isinstance(points, list) else []
    summary = coverage_summary(point_list)
    verification_required = verification_count(point_list)
    print(f"Assignment coverage artifact: {rel_repo(root, artifact_path)}")
    print(f"Assignment points: {count}")
    if summary:
        rendered = ", ".join(f"{key}={summary[key]}" for key in sorted(summary))
        print(f"Coverage statuses: {rendered}")
    print(f"Reviewer verification required: {verification_required}")
    print("Assignment coverage structured artifact check passed")
    return 0


def console_main() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(console_main())
