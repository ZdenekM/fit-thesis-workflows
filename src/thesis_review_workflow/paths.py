"""Path formatting helpers shared by workflow scripts."""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath, PureWindowsPath


def rel_repo(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def rel_round(round_dir: Path, path: Path) -> str:
    try:
        return path.relative_to(round_dir).as_posix()
    except ValueError:
        return path.as_posix()


def strict_rel_round(round_dir: Path, path: Path) -> str:
    return path.relative_to(round_dir).as_posix()


def caller_cwd() -> Path:
    return Path(os.environ.get("THESIS_REVIEW_CALLER_CWD", Path.cwd())).expanduser()


def resolve_caller_path(value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return caller_cwd() / path


def is_safe_round_relative_path(value: str) -> bool:
    if not value or "\\" in value:
        return False
    if "//" in value:
        return False
    if value == "." or value.startswith("./") or "/./" in value or value.endswith("/."):
        return False
    posix_path = PurePosixPath(value)
    windows_path = PureWindowsPath(value)
    if posix_path.is_absolute() or windows_path.is_absolute() or windows_path.drive:
        return False
    return "" not in posix_path.parts and "." not in posix_path.parts and ".." not in posix_path.parts
