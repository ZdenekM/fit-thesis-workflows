"""Path formatting helpers shared by workflow scripts."""

from __future__ import annotations

from pathlib import Path


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
