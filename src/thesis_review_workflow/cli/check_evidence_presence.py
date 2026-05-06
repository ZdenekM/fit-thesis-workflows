"""Write advisory evidence-presence findings for opponent review."""

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
from thesis_review_workflow.evidence_presence import (
    MEDIA_PRESENCE_INVENTORY_REL,
    to_artifact,
    write_json,
    write_media_inventory,
)
from thesis_review_workflow.paths import rel_repo

ARTIFACT_REL = Path("work/evidence_presence.json")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/check-evidence-presence",
        description="Write advisory evidence-presence findings and a media inventory.",
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

    artifact, media_records = to_artifact(args.case_id, round_id, now_utc(), round_dir)
    artifact_path = round_dir / ARTIFACT_REL
    media_path = round_dir / MEDIA_PRESENCE_INVENTORY_REL
    write_json(artifact_path, artifact)
    write_media_inventory(media_path, media_records)

    findings = artifact.get("findings")
    count = len(findings) if isinstance(findings, list) else 0
    print(f"Wrote {rel_repo(root, artifact_path)}")
    print(f"Wrote {rel_repo(root, media_path)}")
    print(f"Evidence findings: {count}")
    return 0


def console_main() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(console_main())
