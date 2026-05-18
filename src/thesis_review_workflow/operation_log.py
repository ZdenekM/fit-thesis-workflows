"""Round-local append-only operation log helpers."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

OPERATION_LOG_REL = Path("work/operation_log.jsonl")
OPERATION_LOG_SCHEMA = "operation-log-v1"

OPERATION_STATUSES = {
    "started",
    "passed",
    "failed",
    "blocked",
    "skipped",
    "corrected",
    "note",
}


def utc_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def append_operation(
    round_dir: Path,
    *,
    case_id: str,
    round_id: str,
    operation: str,
    status: str,
    actor: str,
    summary: str,
    command: str = "",
    artifacts: list[str] | None = None,
    checks: list[str] | None = None,
    details: dict[str, str] | None = None,
) -> dict[str, Any]:
    if status not in OPERATION_STATUSES:
        expected = ", ".join(sorted(OPERATION_STATUSES))
        raise ValueError(f"status must be one of: {expected}")
    record: dict[str, Any] = {
        "schema_version": OPERATION_LOG_SCHEMA,
        "case_id": case_id,
        "round_id": round_id,
        "recorded_at": utc_timestamp(),
        "operation": operation,
        "status": status,
        "actor": actor,
        "summary": summary,
    }
    if command:
        record["command"] = command
    if artifacts:
        record["artifacts"] = list(dict.fromkeys(artifacts))
    if checks:
        record["checks"] = list(dict.fromkeys(checks))
    if details:
        record["details"] = details

    path = round_dir / OPERATION_LOG_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return record


def load_operation_log(round_dir: Path) -> tuple[list[dict[str, Any]], list[str]]:
    path = round_dir / OPERATION_LOG_REL
    if not path.is_file():
        return [], []
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            loaded = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(f"{OPERATION_LOG_REL.as_posix()}:{line_no}: invalid JSON: {exc.msg}")
            continue
        if not isinstance(loaded, dict):
            errors.append(f"{OPERATION_LOG_REL.as_posix()}:{line_no}: record must be a JSON object")
            continue
        records.append(loaded)
    return records, errors


def validate_operation_log(round_dir: Path, *, case_id: str | None = None, round_id: str | None = None) -> list[str]:
    records, errors = load_operation_log(round_dir)
    for index, record in enumerate(records, start=1):
        prefix = f"{OPERATION_LOG_REL.as_posix()}:{index}"
        if record.get("schema_version") != OPERATION_LOG_SCHEMA:
            errors.append(f"{prefix}: schema_version must be {OPERATION_LOG_SCHEMA}")
        if case_id is not None and record.get("case_id") != case_id:
            errors.append(f"{prefix}: case_id does not match requested case")
        if round_id is not None and record.get("round_id") != round_id:
            errors.append(f"{prefix}: round_id does not match requested round")
        for field in ("recorded_at", "operation", "status", "actor", "summary"):
            if not isinstance(record.get(field), str) or not record[field].strip():
                errors.append(f"{prefix}: missing {field}")
        status = record.get("status")
        if isinstance(status, str) and status not in OPERATION_STATUSES:
            expected = ", ".join(sorted(OPERATION_STATUSES))
            errors.append(f"{prefix}: status must be one of: {expected}")
        for field in ("artifacts", "checks"):
            value = record.get(field)
            if value is not None and not (isinstance(value, list) and all(isinstance(item, str) for item in value)):
                errors.append(f"{prefix}: {field} must be a list of strings")
        details = record.get("details")
        if details is not None and not (
            isinstance(details, dict)
            and all(isinstance(key, str) and isinstance(value, str) for key, value in details.items())
        ):
            errors.append(f"{prefix}: details must be an object of string values")
    return errors


def operation_log_summary_lines(round_dir: Path, *, case_id: str, round_id: str, limit: int = 6) -> list[str]:
    path = round_dir / OPERATION_LOG_REL
    if not path.is_file():
        return [f"- operation log: missing ({OPERATION_LOG_REL.as_posix()})"]
    records, load_errors = load_operation_log(round_dir)
    validation_errors = validate_operation_log(round_dir, case_id=case_id, round_id=round_id)
    errors = load_errors + [error for error in validation_errors if error not in load_errors]
    if errors:
        return [f"- operation log: invalid ({len(errors)} error(s)); first: {errors[0]}"]
    if not records:
        return [f"- operation log: empty ({OPERATION_LOG_REL.as_posix()})"]
    lines = [f"- operation log: present ({len(records)} event(s)); latest first"]
    for record in reversed(records[-limit:]):
        command = record.get("command")
        command_suffix = f"; `{command}`" if isinstance(command, str) and command else ""
        lines.append(
            "- "
            + f"{record.get('recorded_at')}: {record.get('status')} {record.get('operation')}"
            + f" by {record.get('actor')}: {record.get('summary')}"
            + command_suffix
        )
    return lines
