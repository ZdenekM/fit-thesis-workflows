"""Validate structured evidence requirements and write media inventory."""

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
from thesis_review_workflow.evidence_presence import (
    MEDIA_PRESENCE_INVENTORY_REL,
    build_media_inventory,
    write_media_inventory,
)
from thesis_review_workflow.paths import rel_repo
from thesis_review_workflow.structured_evidence import validate_structured_evidence_artifact

ARTIFACT_REL = Path("work/evidence_requirements.json")


def remove_stale_media_inventory(media_path: Path) -> None:
    if media_path.is_file() or media_path.is_symlink():
        media_path.unlink()


def load_artifact(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("evidence requirements artifact must be a JSON object")
    return loaded


def requirement_state_summary(requirements: list[Any]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for requirement in requirements:
        if not isinstance(requirement, dict):
            continue
        state = requirement.get("state")
        if isinstance(state, str):
            summary[state] = summary.get(state, 0) + 1
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/check-evidence-presence",
        description="Validate work/evidence_requirements.json and write structural media inventory.",
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
    media_path = round_dir / MEDIA_PRESENCE_INVENTORY_REL
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
            "Create `work/evidence_requirements.json` with an explicitly authorized "
            "evidence-requirements agent or human reviewer before running this check."
        )
        remove_stale_media_inventory(media_path)
        return 1

    artifact = load_artifact(artifact_path)
    media_records = build_media_inventory(round_dir)
    write_media_inventory(media_path, media_records)

    requirements = artifact.get("requirements")
    requirement_list = requirements if isinstance(requirements, list) else []
    state_summary = requirement_state_summary(requirement_list)
    count = len(requirement_list)
    print(f"Evidence requirements artifact: {rel_repo(root, artifact_path)}")
    print(f"Wrote {rel_repo(root, media_path)}")
    print(f"Evidence requirements: {count}")
    if state_summary:
        rendered = ", ".join(f"{key}={state_summary[key]}" for key in sorted(state_summary))
        print(f"Requirement states: {rendered}")
    print(f"Media inventory records: {len(media_records)}")
    print("Evidence requirements structured artifact check passed")
    return 0


def console_main() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(console_main())
