"""Contracts for optional Omen advisory evidence in code-quality review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from thesis_review_workflow.paths import is_safe_round_relative_path

CODE_QUALITY_OMEN_REL = "work/code_quality_omen.json"
CODE_QUALITY_OMEN_SCHEMA = "code-quality-omen-v1"

KNOWN_STATUSES = {
    "available_with_findings",
    "available_no_findings",
    "mcp_path_failure",
    "tool_unavailable",
    "not_run",
    "unsupported_or_uninformative",
}
KNOWN_SURFACES = {"cli", "mcp", "unknown"}


def non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def int_field(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    return None


def validate_rel_refs(
    refs: Any,
    rel_path: str,
    label: str,
    round_dir: Path | None,
    errors: list[str],
) -> list[str]:
    if not isinstance(refs, list):
        errors.append(f"{rel_path}: {label} must be a list")
        return []
    values = [item for item in refs if isinstance(item, str) and item.strip()]
    for value in values:
        if not is_safe_round_relative_path(value):
            errors.append(f"{rel_path}: {label} contains an unsafe round-relative path: {value}")
        elif round_dir is not None and not (round_dir / value).exists():
            errors.append(f"{rel_path}: {label} referenced path is missing: {value}")
    return values


def omen_advisory_state_from_payload(loaded: dict[str, Any]) -> dict[str, str]:
    status = str(loaded.get("status", "")).strip()
    if status in KNOWN_STATUSES:
        reason = str(loaded.get("reason", "")).strip() or f"Omen advisory status: {status}"
        return {"tool": "omen", "state": status, "reason": reason}
    return {"tool": "omen", "state": "unsupported_or_uninformative", "reason": "Omen schema status is unknown"}


def omen_advisory_state_from_legacy_payload(loaded: dict[str, Any]) -> dict[str, str] | None:
    files = loaded.get("files")
    summary = loaded.get("summary")
    if not isinstance(summary, dict) and not isinstance(files, list):
        return None
    total_files = int_field(summary.get("total_files")) if isinstance(summary, dict) else None
    if total_files is None and isinstance(files, list):
        total_files = len(files)
    if total_files and total_files > 0:
        return {
            "tool": "omen",
            "state": "available_with_findings",
            "reason": "legacy Omen JSON output is present and includes analyzed files",
        }
    return {
        "tool": "omen",
        "state": "available_no_findings",
        "reason": "legacy Omen JSON output is present but includes zero analyzed files",
    }


def load_omen_advisory_state(path: Path) -> dict[str, str]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"tool": "omen", "state": "unsupported_or_uninformative", "reason": "Omen JSON is unreadable"}
    if not isinstance(loaded, dict):
        return {"tool": "omen", "state": "unsupported_or_uninformative", "reason": "Omen JSON is not an object"}
    if loaded.get("schema_version") == CODE_QUALITY_OMEN_SCHEMA:
        return omen_advisory_state_from_payload(loaded)
    legacy = omen_advisory_state_from_legacy_payload(loaded)
    if legacy is not None:
        return legacy
    return {"tool": "omen", "state": "unsupported_or_uninformative", "reason": "Omen JSON schema is unknown"}


def validate_code_quality_omen_payload(
    loaded: Any,
    rel_path: str = CODE_QUALITY_OMEN_REL,
    *,
    round_dir: Path | None = None,
    case_id: str | None = None,
    round_id: str | None = None,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(loaded, dict):
        return [f"{rel_path}: JSON work artifact must be an object"]
    if loaded.get("schema_version") != CODE_QUALITY_OMEN_SCHEMA:
        errors.append(f"{rel_path}: schema_version must be {CODE_QUALITY_OMEN_SCHEMA}")
    if case_id is not None and loaded.get("case_id") != case_id:
        errors.append(f"{rel_path}: case_id does not match requested case")
    if round_id is not None and loaded.get("round_id") != round_id:
        errors.append(f"{rel_path}: round_id does not match requested round")
    for field in ("generated_at", "tool", "status", "reason"):
        if not non_empty_string(loaded.get(field)):
            errors.append(f"{rel_path}: missing {field}")
    if loaded.get("tool") not in {None, "omen"}:
        errors.append(f"{rel_path}: tool must be omen")
    status = loaded.get("status")
    if status not in KNOWN_STATUSES:
        errors.append(f"{rel_path}: status must be one of {', '.join(sorted(KNOWN_STATUSES))}")

    invocation = loaded.get("invocation")
    if not isinstance(invocation, dict):
        errors.append(f"{rel_path}: invocation must be an object")
        invocation = {}
    surface = invocation.get("surface")
    if surface not in KNOWN_SURFACES:
        errors.append(f"{rel_path}: invocation.surface must be one of {', '.join(sorted(KNOWN_SURFACES))}")
    analyzed_root = invocation.get("analyzed_root")
    if not non_empty_string(analyzed_root):
        errors.append(f"{rel_path}: invocation.analyzed_root is required")
    elif not is_safe_round_relative_path(str(analyzed_root)):
        errors.append(f"{rel_path}: invocation.analyzed_root must be round-relative")
    elif round_dir is not None and not (round_dir / str(analyzed_root)).exists():
        errors.append(f"{rel_path}: invocation.analyzed_root is missing: {analyzed_root}")
    if not isinstance(invocation.get("command"), list):
        errors.append(f"{rel_path}: invocation.command must be a list")

    summary = loaded.get("summary")
    if not isinstance(summary, dict):
        errors.append(f"{rel_path}: summary must be an object")
        summary = {}
    total_files = int_field(summary.get("total_files"))
    total_functions = int_field(summary.get("total_functions"))
    if total_files is None:
        errors.append(f"{rel_path}: summary.total_files must be a non-negative integer")
    if total_functions is None:
        errors.append(f"{rel_path}: summary.total_functions must be a non-negative integer")
    if status == "available_with_findings" and total_files == 0:
        errors.append(f"{rel_path}: available_with_findings requires summary.total_files > 0")
    if status == "mcp_path_failure":
        if surface != "mcp":
            errors.append(f"{rel_path}: mcp_path_failure requires invocation.surface mcp")
        if total_files not in {0, None}:
            errors.append(f"{rel_path}: mcp_path_failure should record zero analyzed files")
        if not loaded.get("non_empty_root_evidence"):
            errors.append(f"{rel_path}: mcp_path_failure requires non_empty_root_evidence")

    validate_rel_refs(loaded.get("source_refs", []), rel_path, "source_refs", round_dir, errors)
    validate_rel_refs(
        loaded.get("non_empty_root_evidence", []),
        rel_path,
        "non_empty_root_evidence",
        round_dir,
        errors,
    )
    if not isinstance(loaded.get("limitations"), list):
        errors.append(f"{rel_path}: limitations must be a list")
    return errors
