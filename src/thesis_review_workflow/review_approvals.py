"""Structured final-review approval records for generated review artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from thesis_review_workflow.paths import is_safe_round_relative_path

APPROVED_VERDICTS = {"approved", "pass"}
REVIEW_APPROVAL_GLOB = "work/reviews/*_review.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_review_approval_path(rel_path: str) -> bool:
    path = Path(rel_path)
    return (
        len(path.parts) == 3
        and path.parts[0] == "work"
        and path.parts[1] == "reviews"
        and path.name.endswith("_review.json")
    )


def require_review_approval_path(rel_path: str) -> None:
    if not is_review_approval_path(rel_path):
        raise ValueError(f"review approval path must match {REVIEW_APPROVAL_GLOB}: {rel_path}")


def load_review_approval(round_dir: Path, rel_path: str) -> tuple[dict[str, Any] | None, list[str]]:
    if not is_review_approval_path(rel_path):
        return None, [f"{rel_path}: unknown review approval path"]
    try:
        loaded = json.loads((round_dir / rel_path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, [f"{rel_path}: missing review approval record"]
    except OSError as exc:
        return None, [f"{rel_path}: cannot read review approval record: {exc}"]
    except json.JSONDecodeError as exc:
        return None, [f"{rel_path}: invalid JSON: {exc.msg}"]
    if not isinstance(loaded, dict):
        return None, [f"{rel_path}: review approval record must be a JSON object"]
    return loaded, []


def _require_string(payload: dict[str, Any], field: str, rel_path: str, errors: list[str]) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{rel_path}: {field} must be a non-empty string")
        return ""
    return value


def _require_hash_bound_path(
    payload: dict[str, Any],
    path_field: str,
    hash_field: str,
    rel_path: str,
    round_dir: Path,
    errors: list[str],
) -> str:
    path_value = _require_string(payload, path_field, rel_path, errors)
    if not path_value:
        return ""
    if not is_safe_round_relative_path(path_value):
        errors.append(f"{rel_path}: {path_field} must be relative inside the round")
        return ""
    path = round_dir / path_value
    if not path.is_file():
        errors.append(f"{rel_path}: {path_field} points to a missing file: {path_value}")
        return path_value
    recorded_hash = payload.get(hash_field)
    if not isinstance(recorded_hash, str) or not recorded_hash:
        errors.append(f"{rel_path}: {hash_field} must be a non-empty string")
    elif recorded_hash != sha256_file(path):
        errors.append(f"{rel_path}: {hash_field} is stale for {path_value}")
    return path_value


def validate_review_approval_payload(
    payload: dict[str, Any],
    rel_path: str,
    round_dir: Path,
    *,
    case_id: str | None = None,
    round_id: str | None = None,
    reviewed_artifact_path: str | None = None,
) -> list[str]:
    errors: list[str] = []
    _require_string(payload, "workflow_profile", rel_path, errors)
    _require_string(payload, "reviewer_role", rel_path, errors)
    _require_string(payload, "timestamp", rel_path, errors)
    blocking_findings_count = payload.get("blocking_findings_count")
    if not isinstance(blocking_findings_count, int) or blocking_findings_count < 0:
        errors.append(f"{rel_path}: blocking_findings_count must be a non-negative integer")
    elif blocking_findings_count != 0:
        errors.append(f"{rel_path}: approved/pass review must have blocking_findings_count 0")
    reviewer_agent = payload.get("reviewer_agent")
    if reviewer_agent is not None and not isinstance(reviewer_agent, str):
        errors.append(f"{rel_path}: reviewer_agent must be a string when present")
    notes = payload.get("notes")
    if notes is not None and not isinstance(notes, str):
        errors.append(f"{rel_path}: notes must be a string when present")
    if case_id is not None and payload.get("case_id") not in {None, case_id}:
        errors.append(f"{rel_path}: case_id does not match requested case")
    if round_id is not None and payload.get("round_id") not in {None, round_id}:
        errors.append(f"{rel_path}: round_id does not match requested round")

    verdict = payload.get("verdict")
    if not isinstance(verdict, str) or verdict.strip().lower() not in APPROVED_VERDICTS:
        errors.append(f"{rel_path}: verdict must be approved/pass")

    reviewed_path = _require_hash_bound_path(
        payload,
        "reviewed_artifact_path",
        "reviewed_artifact_sha256",
        rel_path,
        round_dir,
        errors,
    )
    if reviewed_artifact_path is not None and reviewed_path and reviewed_path != reviewed_artifact_path:
        errors.append(f"{rel_path}: reviewed_artifact_path must be {reviewed_artifact_path}")

    _require_hash_bound_path(
        payload,
        "review_basis_path",
        "review_basis_sha256",
        rel_path,
        round_dir,
        errors,
    )
    checks_observed = payload.get("checks_observed")
    if not isinstance(checks_observed, list):
        errors.append(f"{rel_path}: checks_observed must be a list")
    else:
        for index, item in enumerate(checks_observed, start=1):
            if not isinstance(item, str) or not item.strip():
                errors.append(f"{rel_path}: checks_observed item {index} must be a non-empty string")
    limitations = payload.get("limitations")
    if not isinstance(limitations, list):
        errors.append(f"{rel_path}: limitations must be a list")
    else:
        for index, item in enumerate(limitations, start=1):
            if not isinstance(item, str):
                errors.append(f"{rel_path}: limitations item {index} must be a string")
    return errors


def validate_review_approval_artifact(
    round_dir: Path,
    rel_path: str,
    *,
    case_id: str | None = None,
    round_id: str | None = None,
    reviewed_artifact_path: str | None = None,
) -> list[str]:
    payload, errors = load_review_approval(round_dir, rel_path)
    if errors:
        return errors
    assert payload is not None
    return validate_review_approval_payload(
        payload,
        rel_path,
        round_dir,
        case_id=case_id,
        round_id=round_id,
        reviewed_artifact_path=reviewed_artifact_path,
    )


def review_record_from_approval(payload: dict[str, Any], approval_path: str) -> dict[str, Any]:
    return {
        "status": "reviewed",
        "reviewer_role": str(payload.get("reviewer_role") or "not_recorded"),
        "reviewer_agent": str(payload.get("reviewer_agent") or "manual"),
        "reviewed_at": str(payload.get("timestamp") or ""),
        "reviewed_hash": str(payload.get("reviewed_artifact_sha256") or ""),
        "covered_by_artifact": "",
        "used_findings": str(payload.get("used_findings") or ""),
        "exception": "",
        "notes": f"Imported from structured approval record `{approval_path}`.",
        "review_basis_path": str(payload.get("review_basis_path") or ""),
        "review_basis_sha256": str(payload.get("review_basis_sha256") or ""),
        "approval_record_path": approval_path,
        "checks_observed": string_list(payload.get("checks_observed")),
        "blocking_findings_count": payload.get("blocking_findings_count", 0),
    }


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
