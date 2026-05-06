"""CLI-facing case, round, and manifest helpers."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from thesis_review_workflow.cases import MissingCurrentRound
from thesis_review_workflow.cases import repo_root as repo_root_core
from thesis_review_workflow.cases import resolve_round as resolve_round_core
from thesis_review_workflow.ids import validate_id as validate_id_core


def repo_root() -> Path:
    return repo_root_core()


def validate_id(label: str, value: str, *, stderr: bool = False) -> None:
    try:
        validate_id_core(label, value)
    except ValueError as exc:
        if stderr:
            print(str(exc), file=sys.stderr)
            raise SystemExit(2) from exc
        raise SystemExit(str(exc)) from exc


def resolve_round(case_dir: Path, round_id: str | None, *, stderr: bool = False) -> str:
    try:
        return resolve_round_core(case_dir, round_id)
    except (MissingCurrentRound, ValueError) as exc:
        if stderr:
            print(str(exc), file=sys.stderr)
            raise SystemExit(2) from exc
        raise SystemExit(str(exc)) from exc


def require_case_dir(root: Path, case_id: str, *, error_prefix: str = "", stderr: bool = False) -> Path:
    case_dir = root / "cases" / case_id
    if case_dir.is_dir():
        return case_dir
    message = f"{error_prefix}Case does not exist: cases/{case_id}"
    if stderr:
        print(message, file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(message)


def require_round_dir(
    case_dir: Path,
    case_id: str,
    round_id: str,
    *,
    error_prefix: str = "",
    stderr: bool = False,
) -> Path:
    round_dir = case_dir / "rounds" / round_id
    if round_dir.is_dir():
        return round_dir
    message = f"{error_prefix}Round does not exist: cases/{case_id}/rounds/{round_id}"
    if stderr:
        print(message, file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(message)


def load_json_manifest(
    path: Path,
    *,
    label: str,
    missing_message: str,
    not_object_message: str,
) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(missing_message)
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: Invalid JSON in {label}: {exc.msg}") from exc
    if not isinstance(loaded, dict):
        raise SystemExit(not_object_message)
    return loaded
