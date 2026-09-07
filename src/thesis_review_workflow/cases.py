"""Case and round path helpers shared by workflow scripts."""

from __future__ import annotations

import subprocess
from pathlib import Path

from thesis_review_workflow.ids import validate_id


class MissingCurrentRound(FileNotFoundError):
    """Raised when a case has no current-round.txt and no explicit round was provided."""

    def __init__(self, case_dir: Path) -> None:
        self.case_dir = case_dir
        super().__init__(f"Missing current round: {case_dir}/current-round.txt")


def repo_root() -> Path:
    output = subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return Path(output.strip())


def case_dir(root: Path, case_id: str) -> Path:
    validate_id("CASE_ID", case_id)
    return root / "cases" / case_id


def round_dir(case_dir_path: Path, round_id: str) -> Path:
    validate_id("ROUND_ID", round_id)
    return case_dir_path / "rounds" / round_id


def read_current_round(case_dir_path: Path) -> str | None:
    current = case_dir_path / "current-round.txt"
    if not current.is_file():
        return None
    return current.read_text(encoding="utf-8").strip()


def previous_round_ids(case_dir_path: Path, current_round_id: str) -> list[str]:
    """Round ids that precede `current_round_id`, newest first.

    Ordering is lexical over non-hidden round directories. Round ids created by
    `import-round` are timestamp-prefixed, so lexical order is chronological for them;
    `ids.py` permits any safe id, so a hand-made id may order differently from its real
    chronology. Callers that need chronology must say so as a limitation.
    """
    rounds_dir = case_dir_path / "rounds"
    if not rounds_dir.is_dir():
        return []
    names = sorted(path.name for path in rounds_dir.iterdir() if path.is_dir() and not path.name.startswith("."))
    if current_round_id in names:
        return list(reversed(names[: names.index(current_round_id)]))
    return list(reversed([name for name in names if name != current_round_id]))


def resolve_round(case_dir_path: Path, round_id: str | None) -> str:
    if round_id:
        validate_id("ROUND_ID", round_id)
        return round_id
    resolved = read_current_round(case_dir_path)
    if resolved is None:
        raise MissingCurrentRound(case_dir_path)
    validate_id("ROUND_ID", resolved)
    return resolved
