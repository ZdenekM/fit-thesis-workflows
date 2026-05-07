"""Validate historical opponent calibration case-analysis artifacts."""

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
from thesis_review_workflow.opponent_calibration import (
    HISTORICAL_CASE_ANALYSIS_PREFIX,
    historical_case_analysis_id,
    validate_opponent_calibration_artifact,
)
from thesis_review_workflow.paths import rel_repo


def load_json_object(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"historical case analysis must be a JSON object: {path}")
    return loaded


def analysis_paths(round_dir: Path) -> list[Path]:
    base = round_dir / HISTORICAL_CASE_ANALYSIS_PREFIX
    if not base.is_dir():
        return []
    return sorted(base.rglob("*.json"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/check-opponent-calibration-case",
        description="Validate historical opponent calibration case-analysis artifacts.",
    )
    parser.add_argument("calibration_case_id")
    parser.add_argument("round_id", nargs="?")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    validate_id("CALIBRATION_CASE_ID", args.calibration_case_id)
    root = repo_root()
    case_dir = require_case_dir(root, args.calibration_case_id)
    round_id = resolve_round(case_dir, args.round_id)
    round_dir = require_round_dir(case_dir, args.calibration_case_id, round_id)

    paths = analysis_paths(round_dir)
    if not paths:
        print(
            "ERROR: no historical case analyses found under "
            f"{HISTORICAL_CASE_ANALYSIS_PREFIX}<historical-case-id>.json"
        )
        print(
            "Create these artifacts with explicitly authorized historical-opponent-calibration agents "
            "or human reviewers before running this check."
        )
        return 1

    all_errors: list[str] = []
    summaries: list[dict[str, Any]] = []
    for path in paths:
        rel_path = path.relative_to(round_dir).as_posix()
        if historical_case_analysis_id(rel_path) is None:
            all_errors.append(f"{rel_path}: invalid historical case analysis artifact path")
            continue
        errors = validate_opponent_calibration_artifact(
            round_dir,
            rel_path,
            case_id=args.calibration_case_id,
            round_id=round_id,
        )
        if errors:
            all_errors.extend(errors)
            continue
        summaries.append(load_json_object(path))

    if all_errors:
        for error in all_errors:
            print(f"ERROR: {error}")
        return 1

    print(f"Historical calibration round: {rel_repo(root, round_dir)}")
    print(f"Historical case analyses: {len(paths)}")
    by_strength: dict[str, int] = {}
    for summary in summaries:
        strength = summary.get("case_strength")
        if isinstance(strength, str):
            by_strength[strength] = by_strength.get(strength, 0) + 1
    if by_strength:
        rendered = ", ".join(f"{key}={by_strength[key]}" for key in sorted(by_strength))
        print(f"Case strength mix: {rendered}")
    print("Historical opponent calibration case check passed")
    return 0


def console_main() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(console_main())
