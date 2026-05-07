"""Validate structured quantitative-claims evidence for review."""

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
from thesis_review_workflow.structured_evidence import validate_structured_evidence_artifact

ARTIFACT_REL = Path("work/quantitative_claims.json")


def load_artifact(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("quantitative claims artifact must be a JSON object")
    return loaded


def count_field_values(items: list[Any], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        value = item.get(field)
        if isinstance(value, str):
            counts[value] = counts.get(value, 0) + 1
    return counts


def render_counts(counts: dict[str, int]) -> str:
    return ", ".join(f"{key}={counts[key]}" for key in sorted(counts))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/check-evaluation-claims",
        description="Validate work/quantitative_claims.json created by an authorized quantitative-claims review.",
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
            "Create `work/quantitative_claims.json` with an explicitly authorized "
            "quantitative-claims agent or human reviewer before running this check."
        )
        return 1

    artifact = load_artifact(artifact_path)
    claims = artifact.get("claims")
    claim_list = claims if isinstance(claims, list) else []

    print(f"Quantitative claims artifact: {rel_repo(root, artifact_path)}")
    print(f"Quantitative claims: {len(claim_list)}")
    kind_counts = count_field_values(claim_list, "kind")
    if kind_counts:
        print(f"Claim kinds: {render_counts(kind_counts)}")
    status_counts = count_field_values(claim_list, "status")
    if status_counts:
        print(f"Claim statuses: {render_counts(status_counts)}")
    baseline_counts = count_field_values(claim_list, "baseline_status")
    if baseline_counts:
        print(f"Baseline statuses: {render_counts(baseline_counts)}")
    context_counts = count_field_values(claim_list, "practical_context")
    if context_counts:
        print(f"Practical-context statuses: {render_counts(context_counts)}")
    print("Quantitative claims structured artifact check passed")
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
