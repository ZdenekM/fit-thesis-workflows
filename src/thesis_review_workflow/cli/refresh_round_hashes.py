"""Refresh deterministic hash-bound helper artifacts for one review round."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from thesis_review_workflow.artifact_validation import sha256_file
from thesis_review_workflow.cli.context import (
    repo_root,
    require_case_dir,
    require_round_dir,
    resolve_round,
    validate_id,
)
from thesis_review_workflow.review_packets import (
    COMMON_BRIEFING_REL,
    build_common_briefing_payload,
    validate_common_briefing_artifact,
    write_common_briefing,
)

REFRESHABLE_COMMON_BRIEFING_REFS = ("notes/", "work/reviews/")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/refresh-round-hashes",
        description=(
            "Refresh deterministic hash-bound helper artifacts after operator-note or approval-record edits. "
            "This command does not change review approvals, review deltas, report text, grades, verdicts, or "
            "semantic findings."
        ),
    )
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    parser.add_argument("--generated-at", default="", help=argparse.SUPPRESS)
    return parser


def is_refreshable_common_briefing_ref(ref: str) -> bool:
    notes_prefix, reviews_prefix = REFRESHABLE_COMMON_BRIEFING_REFS
    return ref.startswith(notes_prefix) or (ref.startswith(reviews_prefix) and ref.endswith(".json"))


def collect_hash_records(value: Any) -> dict[str, str]:
    records: dict[str, str] = {}
    if isinstance(value, dict):
        path = value.get("path")
        digest = value.get("sha256")
        if isinstance(path, str) and isinstance(digest, str):
            records[path] = digest
        for child in value.values():
            records.update(collect_hash_records(child))
    elif isinstance(value, list):
        for child in value:
            records.update(collect_hash_records(child))
    return records


def common_briefing_refresh_blockers(round_dir: Path, *, case_id: str, round_id: str) -> list[str]:
    path = round_dir / COMMON_BRIEFING_REL
    if not path.is_file():
        return []
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{COMMON_BRIEFING_REL}: invalid JSON: {exc.msg}"]
    if not isinstance(existing, dict):
        return [f"{COMMON_BRIEFING_REL}: common briefing must be a JSON object"]

    current = build_common_briefing_payload(case_id, round_id, round_dir)
    existing_hashes = collect_hash_records(existing)
    current_hashes = collect_hash_records(current)
    blockers: list[str] = []
    changed_refs = sorted(
        ref for ref in set(existing_hashes) | set(current_hashes) if existing_hashes.get(ref) != current_hashes.get(ref)
    )
    for ref in changed_refs:
        if not is_refreshable_common_briefing_ref(ref):
            blockers.append(
                f"{COMMON_BRIEFING_REL}: refusing to refresh hash for {ref}; "
                "refresh-round-hashes only refreshes notes/* and work/reviews/*.json snapshots. "
                "For report text, review outputs, evidence artifacts, or materiality inputs, record a review delta "
                "or rerun the relevant review/check instead."
            )
    return blockers


def refresh_common_briefing(round_dir: Path, *, case_id: str, round_id: str, generated_at: str) -> tuple[str, str]:
    blockers = common_briefing_refresh_blockers(round_dir, case_id=case_id, round_id=round_id)
    if blockers:
        raise ValueError("\n".join(blockers))
    path = round_dir / COMMON_BRIEFING_REL
    before = sha256_file(path) if path.is_file() else ""
    write_common_briefing(case_id, round_id, generated_at, round_dir)
    errors = validate_common_briefing_artifact(round_dir, case_id=case_id, round_id=round_id)
    if errors:
        raise ValueError("\n".join(errors))
    after = sha256_file(path)
    status = "refreshed" if before != after else "already-current"
    return status, after


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    validate_id("CASE_ID", args.case_id)
    if args.round_id is not None:
        validate_id("ROUND_ID", args.round_id)

    root = repo_root()
    case_dir = require_case_dir(root, args.case_id)
    round_id = resolve_round(case_dir, args.round_id)
    round_dir = require_round_dir(case_dir, args.case_id, round_id)

    try:
        status, digest = refresh_common_briefing(
            round_dir,
            case_id=args.case_id,
            round_id=round_id,
            generated_at=args.generated_at or now_utc(),
        )
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"{COMMON_BRIEFING_REL}: {status} ({digest})")
    print("No approvals, review deltas, report text, grades, verdicts, or semantic findings were modified.")
    return 0


def console_main() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(console_main())
