"""Classify static code-review reproducibility without executing submitted code."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from thesis_review_workflow.cli.context import (
    repo_root,
    require_case_dir,
    require_round_dir,
    resolve_round,
    validate_id,
)
from thesis_review_workflow.code_reproducibility import classify, to_artifact, write_artifact
from thesis_review_workflow.paths import rel_repo

ARTIFACT_REL = Path("work/code_reproducibility.json")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/check-code-reproducibility",
        description="Write a static code reproducibility classification artifact.",
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

    summary = classify(round_dir)
    artifact = to_artifact(args.case_id, round_id, now_utc(), summary)
    artifact_path = round_dir / ARTIFACT_REL
    write_artifact(artifact_path, artifact)

    print(f"Wrote {rel_repo(root, artifact_path)}")
    print(f"Classification: {summary.classification}")
    print(summary.summary)
    for request in summary.evidence_requests:
        print(f"- {request}")
    return 0


def console_main() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(console_main())
