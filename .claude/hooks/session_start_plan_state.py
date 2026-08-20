#!/usr/bin/env python3
"""Print the active plan's unreconciled state for a starting session.

The plan is the only carrier of state between sessions (`plans/README.md` `## Session Handoff`), so
the one thing a fresh session must know before touching it is whether the tree moved since the plan
was last written. Silent when there is nothing to say.

Intended as a Claude Code SessionStart hook wired in PERSONAL settings — on a shared checkout it
would narrate plan state to every developer — but runnable directly by any tool or human.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

MAX_LINES = 15


def _git(*args: str) -> str:
    probe = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    return probe.stdout.strip()


def _git_lines(*args: str) -> list[str]:
    """Like ``_git`` but keeps leading whitespace, which porcelain status uses as a status column."""
    probe = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    return probe.stdout.rstrip("\n").splitlines()


def _print_capped(lines: list[str]) -> None:
    for line in lines[:MAX_LINES]:
        print(f"    {line}")
    if len(lines) > MAX_LINES:
        print(f"    ... and {len(lines) - MAX_LINES} more")


def main() -> int:
    root_raw = _git("rev-parse", "--show-toplevel")
    if not root_raw:
        return 0
    root = Path(root_raw)
    plans_dir = root / "plans"
    if not plans_dir.is_dir():
        return 0
    active = [
        plan
        for plan in sorted(plans_dir.glob("*_plan.md"))
        if any(line.startswith("Status: in_progress") for line in plan.read_text(encoding="utf-8").splitlines()[:10])
    ]
    if len(active) > 1:
        print("Plans: MORE THAN ONE in_progress plan — resolve before any plan work:")
        for plan in active:
            print(f"    {plan.relative_to(root)}")
        return 0
    if not active:
        return 0
    plan = active[0]
    rel = plan.relative_to(root)
    last_touch = _git("log", "-1", "--format=%h", "--", str(rel))
    log = _git("log", "--oneline", f"{last_touch}..HEAD") if last_touch else ""
    dirty = [line for line in _git_lines("status", "--porcelain") if ".serena/" not in line]
    if not log and not dirty:
        return 0
    print(f"Active plan resume state ({rel}; plans/README.md `## Session Handoff`):")
    if log:
        print(
            f"- commits since the plan was last touched ({last_touch}) — reconcile them into"
            " `## Start Here` / `## Progress` before plan work:"
        )
        _print_capped(log.splitlines())
    if dirty:
        print("- uncommitted changes:")
        _print_capped(dirty)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
