"""Validate synthesized supervisor-report calibration profile artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
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
from thesis_review_workflow.paths import rel_repo
from thesis_review_workflow.review_manifest import MANIFEST_REL, load_manifest
from thesis_review_workflow.supervisor_report_calibration import (
    HISTORICAL_CASE_ANALYSIS_PREFIX,
    SUPERVISOR_REPORT_CALIBRATION_PROFILE_MARKDOWN_REL,
    SUPERVISOR_REPORT_CALIBRATION_PROFILE_REL,
    SUPERVISOR_REPORT_CHECKLIST_REL,
    SUPERVISOR_REPORT_PROFILE_CHANGE_LOG_REL,
    SUPERVISOR_REPORT_PROFILE_HISTORY_REL,
    SUPERVISOR_REPORT_PROFILE_REVIEW_REL,
    SUPERVISOR_REPORT_PROFILE_SNAPSHOT_PREFIX,
    distinct_historical_analysis_refs,
    historical_case_analysis_id,
    validate_supervisor_report_calibration_artifact,
)

PROFILE_MARKDOWN_REL = SUPERVISOR_REPORT_CALIBRATION_PROFILE_MARKDOWN_REL
PROFILE_REVIEW_REL = SUPERVISOR_REPORT_PROFILE_REVIEW_REL
PROFILE_CHANGE_LOG_REL = SUPERVISOR_REPORT_PROFILE_CHANGE_LOG_REL
REVIEWED_STATUSES = {"reviewed", "reviewed_with_notes"}


def analysis_rel_paths(round_dir: Path) -> list[str]:
    base = round_dir / HISTORICAL_CASE_ANALYSIS_PREFIX
    if not base.is_dir():
        return []
    rel_paths: list[str] = []
    for path in sorted(base.rglob("*.json")):
        rel_path = path.relative_to(round_dir).as_posix()
        if historical_case_analysis_id(rel_path) is not None:
            rel_paths.append(rel_path)
    return rel_paths


def invalid_analysis_rel_paths(round_dir: Path) -> list[str]:
    base = round_dir / HISTORICAL_CASE_ANALYSIS_PREFIX
    if not base.is_dir():
        return []
    invalid: list[str] = []
    for path in sorted(base.rglob("*.json")):
        rel_path = path.relative_to(round_dir).as_posix()
        if historical_case_analysis_id(rel_path) is None:
            invalid.append(rel_path)
    return invalid


def load_json_object(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"expected JSON object: {path}")
    return loaded


def load_history_entries(round_dir: Path) -> tuple[list[dict[str, Any]], list[str]]:
    path = round_dir / SUPERVISOR_REPORT_PROFILE_HISTORY_REL
    errors: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [], [f"{SUPERVISOR_REPORT_PROFILE_HISTORY_REL}: cannot read profile history: {exc}"]
    entries: list[dict[str, Any]] = []
    for index, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            loaded = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(loaded, dict):
            loaded = dict(loaded)
            loaded["_history_entry_sha256"] = hashlib.sha256(line.encode("utf-8")).hexdigest()
            entries.append(loaded)
        else:
            errors.append(f"{SUPERVISOR_REPORT_PROFILE_HISTORY_REL}: line {index}: JSONL entry must be an object")
    return entries, errors


def profile_snapshot_path(version: int) -> str:
    return f"{SUPERVISOR_REPORT_PROFILE_SNAPSHOT_PREFIX}v{version}.md"


def source_case_ref_errors(label: str, refs: list[str], valid_analyses: set[str]) -> list[str]:
    errors: list[str] = []
    if len(refs) < 2:
        errors.append(f"{label}: must reference at least two distinct historical case analyses")
    for ref in refs:
        if ref not in valid_analyses:
            errors.append(f"{label}: ref is not a validated historical case analysis: {ref}")
    return errors


def profile_binding_errors(round_dir: Path, profile: dict[str, Any], analyses: list[str]) -> list[str]:
    errors: list[str] = []
    current_profile_hash = sha256_file(round_dir / PROFILE_MARKDOWN_REL)
    current_manifest_hash = sha256_file(round_dir / SUPERVISOR_REPORT_CALIBRATION_PROFILE_REL)
    profile_version = profile.get("profile_version")
    if profile.get("profile_markdown_path") != PROFILE_MARKDOWN_REL:
        errors.append(
            f"{SUPERVISOR_REPORT_CALIBRATION_PROFILE_REL}: profile_markdown_path must be {PROFILE_MARKDOWN_REL}"
        )
    if profile.get("profile_markdown_sha256") != current_profile_hash:
        errors.append(f"{SUPERVISOR_REPORT_CALIBRATION_PROFILE_REL}: profile_markdown_sha256 is stale")
    profile_refs = distinct_historical_analysis_refs(profile.get("source_case_refs"))
    errors.extend(
        source_case_ref_errors(
            f"{SUPERVISOR_REPORT_CALIBRATION_PROFILE_REL}: source_case_refs",
            profile_refs,
            set(analyses),
        )
    )
    history_entries, history_errors = load_history_entries(round_dir)
    errors.extend(history_errors)
    if not history_entries:
        errors.append(f"{SUPERVISOR_REPORT_PROFILE_HISTORY_REL}: missing latest profile history entry")
        return errors
    versions = [entry.get("profile_version") for entry in history_entries]
    if isinstance(profile_version, int) and not isinstance(profile_version, bool):
        expected_versions = list(range(1, profile_version + 1))
        if versions != expected_versions:
            errors.append(
                f"{SUPERVISOR_REPORT_PROFILE_HISTORY_REL}: profile_version entries must be append-only sequence "
                f"{expected_versions}"
            )
    for entry in history_entries:
        version = entry.get("profile_version")
        if not isinstance(version, int) or isinstance(version, bool):
            continue
        expected_snapshot = profile_snapshot_path(version)
        if entry.get("profile_snapshot_path") != expected_snapshot:
            errors.append(f"{SUPERVISOR_REPORT_PROFILE_HISTORY_REL}: version {version} profile_snapshot_path is stale")
        snapshot = round_dir / expected_snapshot
        if snapshot.is_file() and sha256_file(snapshot) != entry.get("profile_markdown_sha256"):
            errors.append(f"{SUPERVISOR_REPORT_PROFILE_HISTORY_REL}: version {version} profile snapshot hash is stale")
        if version == 1:
            if entry.get("previous_profile_markdown_sha256") is not None:
                errors.append(
                    f"{SUPERVISOR_REPORT_PROFILE_HISTORY_REL}: version 1 previous_profile_markdown_sha256 must be null"
                )
        else:
            previous_entry = history_entries[version - 2] if len(history_entries) >= version - 1 else None
            previous_hash = previous_entry.get("profile_markdown_sha256") if isinstance(previous_entry, dict) else None
            if entry.get("previous_profile_markdown_sha256") != previous_hash:
                errors.append(
                    f"{SUPERVISOR_REPORT_PROFILE_HISTORY_REL}: version {version} "
                    "previous_profile_markdown_sha256 is stale"
                )
    latest = history_entries[-1]
    if latest.get("profile_version") != profile.get("profile_version"):
        errors.append(
            f"{SUPERVISOR_REPORT_PROFILE_HISTORY_REL}: latest profile_version does not match profile manifest"
        )
    if latest.get("profile_markdown_sha256") != current_profile_hash:
        errors.append(f"{SUPERVISOR_REPORT_PROFILE_HISTORY_REL}: latest profile_markdown_sha256 is stale")
    if latest.get("profile_manifest_sha256") != current_manifest_hash:
        errors.append(f"{SUPERVISOR_REPORT_PROFILE_HISTORY_REL}: latest profile_manifest_sha256 is stale")
    if isinstance(profile_version, int) and not isinstance(profile_version, bool):
        if profile_version == 1:
            if profile.get("profile_previous_sha256") is not None:
                errors.append(
                    f"{SUPERVISOR_REPORT_CALIBRATION_PROFILE_REL}: profile_previous_sha256 must be null for version 1"
                )
        elif len(history_entries) >= 2:
            previous_hash = history_entries[-2].get("profile_markdown_sha256")
            if profile.get("profile_previous_sha256") != previous_hash:
                errors.append(f"{SUPERVISOR_REPORT_CALIBRATION_PROFILE_REL}: profile_previous_sha256 is stale")
            if latest.get("previous_profile_markdown_sha256") != previous_hash:
                errors.append(
                    f"{SUPERVISOR_REPORT_PROFILE_HISTORY_REL}: latest previous_profile_markdown_sha256 is stale"
                )
    history_refs = distinct_historical_analysis_refs(latest.get("source_case_refs"))
    errors.extend(
        source_case_ref_errors(
            f"{SUPERVISOR_REPORT_PROFILE_HISTORY_REL}: latest source_case_refs",
            history_refs,
            set(analyses),
        )
    )
    if history_refs != profile_refs:
        errors.append(
            f"{SUPERVISOR_REPORT_PROFILE_HISTORY_REL}: latest source_case_refs must match profile source_case_refs"
        )
    if latest.get("review_status") not in REVIEWED_STATUSES:
        errors.append(
            f"{SUPERVISOR_REPORT_PROFILE_HISTORY_REL}: latest review_status must be reviewed or reviewed_with_notes"
        )
    return errors


def manifest_profile_errors(round_dir: Path, profile_refs: list[str]) -> list[str]:
    errors: list[str] = []
    manifest_path = round_dir / MANIFEST_REL
    if not manifest_path.is_file():
        return [f"missing review manifest: {MANIFEST_REL.as_posix()}"]
    try:
        manifest = load_manifest(manifest_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"cannot read review manifest: {exc}"]
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        return ["review manifest artifacts must be a list"]
    entry = next(
        (item for item in artifacts if isinstance(item, dict) and item.get("path") == PROFILE_MARKDOWN_REL),
        None,
    )
    if entry is None:
        return [f"review manifest missing artifact entry for {PROFILE_MARKDOWN_REL}"]
    current_hash = sha256_file(round_dir / PROFILE_MARKDOWN_REL)
    if entry.get("artifact_sha256") != current_hash:
        errors.append(f"{PROFILE_MARKDOWN_REL}: artifact_sha256 is stale in review manifest")
    if entry.get("artifact_type") != "supervisor_report_calibration_profile":
        errors.append(f"{PROFILE_MARKDOWN_REL}: artifact_type must be supervisor_report_calibration_profile")
    if entry.get("review_scope") != "internal_only":
        errors.append(f"{PROFILE_MARKDOWN_REL}: review_scope must be internal_only")
    skills = entry.get("skills")
    if not isinstance(skills, list) or "historical-supervisor-report-calibration" not in skills:
        errors.append(f"{PROFILE_MARKDOWN_REL}: skills must include historical-supervisor-report-calibration")
    generated = entry.get("generated_by")
    generator_agent = ""
    generator_role = ""
    if not isinstance(generated, list) or not any(
        isinstance(item, dict)
        and str(item.get("role", "")).strip() not in {"", "not_recorded"}
        and str(item.get("agent", "")).strip() not in {"", "not_recorded"}
        for item in generated
    ):
        errors.append(f"{PROFILE_MARKDOWN_REL}: generated_by must include a recorded generator role and agent")
    elif isinstance(generated, list):
        for item in generated:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role", "")).strip()
            agent = str(item.get("agent", "")).strip()
            if role not in {"", "not_recorded"} and agent not in {"", "not_recorded"}:
                generator_role = role
                generator_agent = agent
                break
    limitations = entry.get("limitations")
    if not isinstance(limitations, list) or not limitations:
        errors.append(f"{PROFILE_MARKDOWN_REL}: limitations must record profile corpus and use boundaries")
    evidence_refs = entry.get("evidence_refs")
    if not isinstance(evidence_refs, list):
        errors.append(f"{PROFILE_MARKDOWN_REL}: evidence_refs must be a list")
    else:
        required_refs = {
            SUPERVISOR_REPORT_CALIBRATION_PROFILE_REL,
            SUPERVISOR_REPORT_CHECKLIST_REL,
            SUPERVISOR_REPORT_PROFILE_HISTORY_REL,
            PROFILE_CHANGE_LOG_REL,
            PROFILE_REVIEW_REL,
            *profile_refs,
        }
        missing_refs = sorted(required_refs.difference({item for item in evidence_refs if isinstance(item, str)}))
        for missing_ref in missing_refs:
            errors.append(f"{PROFILE_MARKDOWN_REL}: evidence_refs missing {missing_ref}")
    review = entry.get("independent_review")
    if not isinstance(review, dict):
        errors.append(f"{PROFILE_MARKDOWN_REL}: independent_review must be an object")
        return errors
    if review.get("status") not in REVIEWED_STATUSES:
        errors.append(f"{PROFILE_MARKDOWN_REL}: independent review status must be reviewed or reviewed_with_notes")
    if review.get("reviewed_hash") != current_hash:
        errors.append(f"{PROFILE_MARKDOWN_REL}: independent review hash is stale or missing")
    for field in ("reviewer_role", "reviewer_agent", "reviewed_at"):
        value = str(review.get(field, "")).strip()
        if not value or value == "not_recorded":
            errors.append(f"{PROFILE_MARKDOWN_REL}: independent_review.{field} must be recorded")
    reviewer_agent = str(review.get("reviewer_agent", "")).strip()
    reviewer_role = str(review.get("reviewer_role", "")).strip()
    if generator_agent and reviewer_agent and generator_agent == reviewer_agent and generator_agent != "manual":
        errors.append(f"{PROFILE_MARKDOWN_REL}: generator and reviewer agent must be independent")
    if generator_role and reviewer_role and generator_role == reviewer_role:
        errors.append(f"{PROFILE_MARKDOWN_REL}: generator and reviewer role must be independent")
    if review.get("review_basis_path") != PROFILE_REVIEW_REL:
        errors.append(f"{PROFILE_MARKDOWN_REL}: independent_review.review_basis_path must be {PROFILE_REVIEW_REL}")
    review_basis_hash = review.get("review_basis_sha256")
    if not isinstance(review_basis_hash, str) or len(review_basis_hash) != 64:
        errors.append(f"{PROFILE_MARKDOWN_REL}: independent_review.review_basis_sha256 must be recorded")
    elif not (round_dir / PROFILE_REVIEW_REL).is_file() or review_basis_hash != sha256_file(
        round_dir / PROFILE_REVIEW_REL
    ):
        errors.append(f"{PROFILE_MARKDOWN_REL}: independent review basis hash is stale")
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/check-supervisor-report-calibration-profile",
        description="Validate synthesized supervisor-report calibration profile artifacts.",
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

    errors: list[str] = []
    for rel_path in invalid_analysis_rel_paths(round_dir):
        errors.append(f"{rel_path}: invalid historical case analysis path")
    analyses = analysis_rel_paths(round_dir)
    if len(analyses) < 2:
        errors.append("profile synthesis requires at least two historical supervisor report analyses")
    for rel_path in analyses:
        errors.extend(
            validate_supervisor_report_calibration_artifact(
                round_dir,
                rel_path,
                case_id=args.calibration_case_id,
                round_id=round_id,
            )
        )
    for rel_path in (
        SUPERVISOR_REPORT_CALIBRATION_PROFILE_REL,
        SUPERVISOR_REPORT_CHECKLIST_REL,
        SUPERVISOR_REPORT_PROFILE_HISTORY_REL,
    ):
        errors.extend(
            validate_supervisor_report_calibration_artifact(
                round_dir,
                rel_path,
                case_id=args.calibration_case_id,
                round_id=round_id,
            )
        )
    profile: dict[str, Any] | None = None
    profile_refs: list[str] = []
    markdown_present = (round_dir / PROFILE_MARKDOWN_REL).is_file()
    if not errors and markdown_present:
        profile = load_json_object(round_dir / SUPERVISOR_REPORT_CALIBRATION_PROFILE_REL)
        profile_refs = distinct_historical_analysis_refs(profile.get("source_case_refs"))
        errors.extend(profile_binding_errors(round_dir, profile, analyses))
    if not (round_dir / PROFILE_REVIEW_REL).is_file():
        errors.append(f"missing independent profile review artifact: {PROFILE_REVIEW_REL}")
    if not (round_dir / PROFILE_CHANGE_LOG_REL).is_file():
        errors.append(f"missing supervisor report profile change log: {PROFILE_CHANGE_LOG_REL}")
    if not (round_dir / PROFILE_MARKDOWN_REL).is_file():
        errors.append(f"missing supervisor report calibration profile Markdown: {PROFILE_MARKDOWN_REL}")
    else:
        errors.extend(manifest_profile_errors(round_dir, profile_refs))

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    profile = profile or load_json_object(round_dir / SUPERVISOR_REPORT_CALIBRATION_PROFILE_REL)
    checklist = load_json_object(round_dir / SUPERVISOR_REPORT_CHECKLIST_REL)
    checklist_items = checklist.get("checklist_items")
    item_count = len(checklist_items) if isinstance(checklist_items, list) else 0
    print(f"Supervisor report calibration profile: {rel_repo(root, round_dir / PROFILE_MARKDOWN_REL)}")
    print(f"Profile version: {profile.get('profile_version')}")
    print(f"Historical supervisor report analyses: {len(analyses)}")
    print(f"Checklist items: {item_count}")
    print("Supervisor report calibration profile check passed")
    return 0


def console_main() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(console_main())
