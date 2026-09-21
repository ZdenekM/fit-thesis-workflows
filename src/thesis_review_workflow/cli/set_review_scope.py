"""Declare which case (and round) a spawned Claude reviewer may write to.

`.claude/hooks/pre_tool_use_write_guard.py` confines a reviewer subagent to one
case. It reads `CLAUDE_REVIEW_CASE` / `CLAUDE_REVIEW_ROUND` first, but a Claude
Code session cannot change its own process environment, so a parent that did not
have them at launch had no way to grant a scope: the reviewer completed its whole
review and only then found it could not save its findings. This command writes the
declared-scope file the guard falls back to, which a parent CAN do mid-session.

It never widens the boundary. The file names exactly one case, the environment
still takes precedence, and a reviewer cannot write the file itself because every
role's owned writes live under `cases/` and this path does not.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from thesis_review_workflow.cases import repo_root
from thesis_review_workflow.ids import validate_id

SCOPE_REL = Path(".claude/hooks/review_scope.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/set-review-scope",
        description="Declare the active case/round for spawned Claude reviewer subagents.",
    )
    parser.add_argument("case_id", nargs="?", help="Case a reviewer may write under.")
    parser.add_argument("round_id", nargs="?", help="Round, for a round-scoped reviewer role.")
    parser.add_argument("--clear", action="store_true", help="Remove the declared scope.")
    parser.add_argument("--show", action="store_true", help="Print the declared scope and exit.")
    return parser


def _show(path: Path) -> int:
    if not path.is_file():
        print("No declared review scope. Reviewer writes fail closed unless CLAUDE_REVIEW_CASE is exported.")
        return 0
    print(path.read_text(encoding="utf-8").strip())
    return 0


def _clear(path: Path, case_id: str | None) -> int:
    if case_id:
        print("--clear takes no case id", file=sys.stderr)
        return 2
    if path.is_file():
        path.unlink()
        print(f"Cleared {SCOPE_REL.as_posix()}")
    else:
        print("No declared review scope to clear.")
    return 0


def _declare(root: Path, path: Path, case_id: str, round_id: str | None) -> int:
    try:
        validate_id("CASE_ID", case_id)
        if round_id:
            validate_id("ROUND_ID", round_id)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    # The scope may only name a case that exists: a typo would otherwise be discovered
    # as a reviewer denial at the END of a review, which is the failure this command
    # exists to remove.
    case_dir = root / "cases" / case_id
    if not case_dir.is_dir():
        print(f"No such case: cases/{case_id}", file=sys.stderr)
        return 1
    if round_id and not (case_dir / "rounds" / round_id).is_dir():
        print(f"No such round: cases/{case_id}/rounds/{round_id}", file=sys.stderr)
        return 1

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"case": case_id, "round": round_id or ""}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    scope = f"cases/{case_id}" + (f"/rounds/{round_id}" if round_id else "")
    print(f"Declared review scope: {scope}")
    print(f"Written to {SCOPE_REL.as_posix()}; clear it with `scripts/set-review-scope --clear` when the wave ends.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = repo_root()
    path = root / SCOPE_REL

    if args.show:
        return _show(path)
    if args.clear:
        return _clear(path, args.case_id)
    if not args.case_id:
        print("Give a case id, or --clear / --show.", file=sys.stderr)
        return 2
    return _declare(root, path, args.case_id, args.round_id)


def console_main() -> int:
    return main(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(console_main())
