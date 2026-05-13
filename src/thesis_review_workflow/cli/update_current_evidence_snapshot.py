"""Create or refresh work/current_evidence_snapshot.json."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from thesis_review_workflow.cli.context import (
    repo_root,
    require_case_dir,
    require_round_dir,
    resolve_round,
    validate_id,
)
from thesis_review_workflow.paths import is_safe_round_relative_path, rel_repo
from thesis_review_workflow.structured_evidence import (
    ALLOWED_REF_PREFIXES,
    CURRENT_EVIDENCE_SNAPSHOT_REL,
    build_current_evidence_snapshot_payload,
    current_evidence_default_source_refs,
    validate_structured_evidence_artifact,
)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_existing_snapshot(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("existing current evidence snapshot must be a JSON object")
    return loaded


def allowed_ref(value: str) -> bool:
    return is_safe_round_relative_path(value) and value.startswith(ALLOWED_REF_PREFIXES)


def parse_path_values(values: list[str], *, field: str) -> list[str]:
    refs: list[str] = []
    for value in values:
        if not allowed_ref(value):
            raise ValueError(f"{field} must be a safe round-relative path under known round directories: {value}")
        refs.append(value)
    return refs


def parse_limitations(values: list[str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("--limitation must use PATH=TEXT")
        path, text = value.split("=", 1)
        if not allowed_ref(path):
            raise ValueError(f"--limitation path is not a safe round-relative ref: {path}")
        if not text:
            raise ValueError("--limitation text must not be empty")
        result.setdefault(path, []).append(text)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/update-current-evidence-snapshot",
        description="Write a hash-bound work/current_evidence_snapshot.json from explicit round-relative file refs.",
    )
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    parser.add_argument(
        "--source-ref",
        action="append",
        default=[],
        help="Additional round-relative file ref to record; missing explicit refs are recorded as missing.",
    )
    parser.add_argument(
        "--no-known",
        action="store_true",
        help="Record only --source-ref values instead of the standard known freshness-sensitive refs.",
    )
    parser.add_argument(
        "--include-missing-known",
        action="store_true",
        help="Also record missing standard known refs as missing/not_checked items.",
    )
    parser.add_argument(
        "--limitation",
        action="append",
        default=[],
        metavar="PATH=TEXT",
        help="Attach an explicit limitation to a snapshot item path.",
    )
    parser.add_argument(
        "--readiness-relevant",
        action="append",
        default=[],
        help="Mark a snapshot item path as readiness relevant.",
    )
    parser.add_argument(
        "--not-readiness-relevant",
        action="append",
        default=[],
        help="Mark a snapshot item path as not readiness relevant.",
    )
    parser.add_argument("--generated-at", default="")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv[1:])
    validate_id("CASE_ID", args.case_id)
    if args.round_id is not None:
        validate_id("ROUND_ID", args.round_id)

    try:
        explicit_refs = parse_path_values(args.source_ref, field="--source-ref")
        readiness_true = parse_path_values(args.readiness_relevant, field="--readiness-relevant")
        readiness_false = parse_path_values(args.not_readiness_relevant, field="--not-readiness-relevant")
        limitations = parse_limitations(args.limitation)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    root = repo_root()
    case_dir = require_case_dir(root, args.case_id)
    round_id = resolve_round(case_dir, args.round_id)
    round_dir = require_round_dir(case_dir, args.case_id, round_id)

    try:
        known_refs = (
            []
            if args.no_known
            else current_evidence_default_source_refs(
                round_dir,
                include_missing_known=args.include_missing_known,
            )
        )
        snapshot_path = round_dir / CURRENT_EVIDENCE_SNAPSHOT_REL
        existing = load_existing_snapshot(snapshot_path)
        existing_items = existing.get("items") if isinstance(existing, dict) else None
        existing_refs: list[str] = []
        if not args.no_known and isinstance(existing_items, list):
            for item in existing_items:
                if isinstance(item, dict) and isinstance(item.get("path"), str):
                    existing_refs.append(item["path"])
        source_refs = sorted(
            dict.fromkeys(
                [*known_refs, *existing_refs, *explicit_refs, *limitations, *readiness_true, *readiness_false]
            )
        )
        readiness = {ref: True for ref in readiness_true}
        readiness.update({ref: False for ref in readiness_false})
        generated_at = args.generated_at or now_utc()
        payload = build_current_evidence_snapshot_payload(
            round_dir,
            case_id=args.case_id,
            round_id=round_id,
            generated_at=generated_at,
            source_refs=source_refs,
            existing_payload=existing,
            limitations_by_path=limitations,
            readiness_relevant_by_path=readiness,
        )
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        errors = validate_structured_evidence_artifact(
            round_dir,
            CURRENT_EVIDENCE_SNAPSHOT_REL,
            case_id=args.case_id,
            round_id=round_id,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 1

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    present = sum(1 for item in payload["items"] if item.get("status") == "present")
    missing = sum(1 for item in payload["items"] if item.get("status") == "missing")
    print(f"Current evidence snapshot: {rel_repo(root, snapshot_path)}")
    print(f"Items: {len(payload['items'])} present={present} missing={missing}")
    print("Current evidence snapshot update passed")
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
