#!/usr/bin/env python3
"""Block accidental git staging of ignored thesis case data."""

from __future__ import annotations

import json
import shlex
import sys
from pathlib import PurePosixPath


DENY_REASON = (
    "Blocked staging private thesis case data. Keep cases/<case-id>/ contents ignored; "
    "only cases/README.md may be tracked."
)
SHELL_WRAPPERS = {"bash", "sh", "zsh"}
ENV_WRAPPERS = {"env"}


def _strip_wrappers(tokens: list[str]) -> list[str]:
    working = list(tokens)
    while working and "=" in working[0] and not working[0].startswith(("-", "/")):
        working = working[1:]
    if not working:
        return []

    executable = PurePosixPath(working[0]).name
    if executable in ENV_WRAPPERS:
        index = 1
        while index < len(working) and working[index].startswith("-") and working[index] != "--":
            index += 1
        if index < len(working) and working[index] == "--":
            index += 1
        return _strip_wrappers(working[index:])

    if executable in SHELL_WRAPPERS:
        for index, token in enumerate(working[1:], start=1):
            if token in {"-c", "-lc", "-cl"} and index + 1 < len(working):
                return _command_tokens(working[index + 1])
    return working


def _command_tokens(command: str) -> list[str]:
    try:
        return _strip_wrappers(shlex.split(command, posix=True))
    except ValueError:
        return []


def _normal_path(token: str) -> str:
    path = token
    while path.startswith("./"):
        path = path[2:]
    return path.rstrip("/")


def _is_private_case_path(token: str) -> bool:
    path = _normal_path(token)
    return path == "cases" or (path.startswith("cases/") and path != "cases/README.md")


def _is_force_add_of_cases(tokens: list[str]) -> bool:
    if len(tokens) < 3 or PurePosixPath(tokens[0]).name != "git" or tokens[1] not in {"add", "stage"}:
        return False
    return any(_is_private_case_path(token) for token in tokens[2:] if not token.startswith("-"))


def _deny() -> int:
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": DENY_REASON,
            }
        },
        sys.stdout,
    )
    return 0


def main() -> int:
    payload = json.load(sys.stdin)
    command = str(payload.get("tool_input", {}).get("command", ""))
    tokens = _command_tokens(command)
    if _is_force_add_of_cases(tokens):
        return _deny()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
