#!/usr/bin/env python3
"""Deny bulk ``git add`` (``-A`` / ``--all`` / bare ``.``) in Bash tool calls.

This repository already requires staging explicit paths: private case material, reviewer profiles,
and local tool state live next to tracked files, and bulk staging is how local state reaches a
commit by accident. The concrete failure class is a re-dirtied ``.serena/project.yml`` committed as
part of an unrelated slice, which then blocked the Omen preflight and could not be undone by
restoring the file afterwards.

Reads the Claude Code PreToolUse JSON payload on stdin; exit 2 denies the call. Deliberately NOT
wired with ``|| exit 2``: unlike the privacy guard, whose failure mode is a data leak, a crash in a
staging guard must not block every Bash call in the session.
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any

SEGMENT_SPLIT = re.compile(r"&&|\|\||[;|&\n]")
GIT_ADD = re.compile(r"\bgit\s+(?:-[A-Za-z]\s+\S+\s+|--[\w-]+(?:=\S+)?\s+)*add\s+(?P<args>.*)$")
BULK_FLAG = re.compile(r"(?:^|\s)(?:-A|--all|--no-ignore-removal)(?:\s|$)")
BARE_DOT = re.compile(r"(?:^|\s)\.(?:\s|$)")


def bulk_add_segment(command: str) -> str | None:
    """Return the offending command segment, or None when the command is fine."""
    for segment in SEGMENT_SPLIT.split(command):
        match = GIT_ADD.search(segment)
        if match is None:
            continue
        args = match.group("args")
        if BULK_FLAG.search(args) or BARE_DOT.search(args):
            return segment.strip()
    return None


def main() -> int:
    try:
        payload: dict[str, Any] = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    command = str((payload.get("tool_input") or {}).get("command", ""))
    offending = bulk_add_segment(command)
    if offending is None:
        return 0
    sys.stderr.write(
        f"git-add guard blocked bulk staging: `{offending}`.\n"
        "Stage explicit paths (`git add <path>...`). Bulk staging has previously committed local "
        "tool state (.serena/project.yml) and is the accident path for private case material.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
