"""Shared validation helpers for agent- or reviewer-authored artifacts."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_nonempty_string(loaded: dict[str, Any], field: str, prefix: str, errors: list[str]) -> None:
    if not isinstance(loaded.get(field), str) or not loaded[field]:
        errors.append(f"{prefix}: {field} must be non-empty str")


def validate_common_artifact_fields(
    loaded: dict[str, Any],
    rel_path: str,
    expected_schema: str,
    case_id: str | None,
    round_id: str | None,
    errors: list[str],
    *,
    required_string_fields: tuple[str, ...],
) -> None:
    if loaded.get("schema_version") != expected_schema:
        errors.append(f"{rel_path}: schema_version must be {expected_schema}")
    if case_id is not None and loaded.get("case_id") != case_id:
        errors.append(f"{rel_path}: case_id does not match requested case")
    if round_id is not None and loaded.get("round_id") != round_id:
        errors.append(f"{rel_path}: round_id does not match requested round")
    for field in required_string_fields:
        require_nonempty_string(loaded, field, rel_path, errors)
    _require_list(loaded, "source_refs", rel_path, errors)
    _require_list(loaded, "limitations", rel_path, errors)
    producer_type = loaded.get("producer_type")
    if producer_type not in {"agent", "human"}:
        errors.append(f"{rel_path}: producer_type must be agent or human")
    if "producer_agent" not in loaded:
        errors.append(f"{rel_path}: missing producer_agent")
    elif loaded["producer_agent"] is not None and not isinstance(loaded["producer_agent"], str):
        errors.append(f"{rel_path}: producer_agent must be str or null")
    if producer_type == "agent":
        require_nonempty_string(loaded, "authorization_note", rel_path, errors)
        require_nonempty_string(loaded, "producer_agent", rel_path, errors)
    elif producer_type == "human":
        require_nonempty_string(loaded, "human_reviewer_note", rel_path, errors)


def _require_list(loaded: dict[str, Any], field: str, prefix: str, errors: list[str]) -> None:
    if not isinstance(loaded.get(field), list):
        errors.append(f"{prefix}: {field} must be list")
