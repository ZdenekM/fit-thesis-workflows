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
from thesis_review_workflow.paths import is_safe_round_relative_path
from thesis_review_workflow.report_calibration import (
    REPORT_CALIBRATION_BASIS_REL,
    is_report_calibration_source_path,
)
from thesis_review_workflow.review_packets import (
    COMMON_BRIEFING_REL,
    build_common_briefing_payload,
    validate_common_briefing_artifact,
    write_common_briefing,
)
from thesis_review_workflow.structured_evidence import CURRENT_EVIDENCE_SNAPSHOT_REL
from thesis_review_workflow.submission_bundle import (
    SUBMISSION_BUNDLE_MATERIALIZATION_REL,
    SUBMISSION_BUNDLE_VISIBILITY_REFS,
)

REFRESHABLE_COMMON_BRIEFING_REFS = ("notes/", "work/reviews/")
REFRESHABLE_COMMON_BRIEFING_EXACT_REFS = (
    CURRENT_EVIDENCE_SNAPSHOT_REL,
    REPORT_CALIBRATION_BASIS_REL,
    *SUBMISSION_BUNDLE_VISIBILITY_REFS,
)
REFRESHABLE_COMMON_BRIEFING_JSON_PREFIXES = ("work/review_materiality/",)
MATERIALIZED_CODE_WORKSPACE_REFS = {
    "work/code_workspace.md",
    "work/serena_roots.json",
    "work/code/.prepare-code-workspace-manifest.json",
    "work/code_reproducibility.json",
}


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


def materialized_input_refs(round_dir: Path) -> set[str]:
    path = round_dir / SUBMISSION_BUNDLE_MATERIALIZATION_REL
    if not path.is_file():
        return set()
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    if not isinstance(loaded, dict) or not isinstance(loaded.get("materializations"), list):
        return set()
    refs: set[str] = set()
    for item in loaded["materializations"]:
        if not isinstance(item, dict):
            continue
        ref = item.get("materialized_ref")
        if isinstance(ref, str) and ref.startswith("inputs/") and is_safe_round_relative_path(ref):
            refs.add(ref)
    return refs


def code_workspace_uses_materialized_input(round_dir: Path) -> bool:
    materialized_refs = materialized_input_refs(round_dir)
    if not materialized_refs:
        return False
    path = round_dir / "work/code/.prepare-code-workspace-manifest.json"
    if not path.is_file():
        return False
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    sources = loaded.get("sources") if isinstance(loaded, dict) else None
    return isinstance(sources, dict) and bool(set(sources) & materialized_refs)


def is_refreshable_common_briefing_ref(ref: str, *, round_dir: Path | None = None) -> bool:
    notes_prefix, reviews_prefix = REFRESHABLE_COMMON_BRIEFING_REFS
    if ref in REFRESHABLE_COMMON_BRIEFING_EXACT_REFS:
        return True
    if is_report_calibration_source_path(ref):
        return True
    if round_dir is not None and ref in materialized_input_refs(round_dir):
        return True
    if (
        round_dir is not None
        and ref in MATERIALIZED_CODE_WORKSPACE_REFS
        and code_workspace_uses_materialized_input(round_dir)
    ):
        return True
    if ref.startswith(notes_prefix) or (ref.startswith(reviews_prefix) and ref.endswith(".json")):
        return True
    return any(ref.startswith(prefix) and ref.endswith(".json") for prefix in REFRESHABLE_COMMON_BRIEFING_JSON_PREFIXES)


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
        if not is_refreshable_common_briefing_ref(ref, round_dir=round_dir):
            blockers.append(
                f"{COMMON_BRIEFING_REL}: refusing to refresh hash for {ref}; "
                "refresh-round-hashes only refreshes notes/*, work/reviews/*.json, current evidence, "
                "materiality, report-calibration source refs, and submission-bundle visibility snapshots. "
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
