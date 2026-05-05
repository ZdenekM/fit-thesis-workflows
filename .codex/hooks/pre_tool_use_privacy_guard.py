#!/usr/bin/env python3
"""Block accidental git staging of ignored thesis case data and profiles."""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
from pathlib import Path, PurePosixPath

DENY_REASON = (
    "Blocked staging private thesis data. Keep cases/<case-id>/ contents and "
    "personal reviewer profiles ignored; only cases/README.md, "
    "profiles/README.md, and profiles/default.md may be tracked."
)
SHELL_WRAPPERS = {"bash", "sh", "zsh"}
ENV_WRAPPERS = {"env"}
COMMAND_SEPARATORS = {"&&", "||", ";"}
PUBLIC_PATHS = {"cases/README.md", "profiles/README.md", "profiles/default.md"}
PROTECTED_ROOTS = {"cases", "profiles"}


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


def _repo_root() -> Path:
    try:
        output = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.CalledProcessError):
        return Path.cwd().resolve()
    return Path(output.strip()).resolve()


def _normal_path(token: str, base_dir: Path, repo_root: Path) -> str:
    path = token
    if path == ":/":
        return "."
    if path.startswith(":/"):
        path = path[2:]
    if path.startswith(":(top)"):
        path = path[len(":(top)") :]

    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = base_dir / candidate

    try:
        normalized = candidate.resolve().relative_to(repo_root).as_posix()
    except ValueError:
        return candidate.resolve().as_posix().rstrip("/")

    if normalized == ".":
        return "."
    return normalized.rstrip("/")


def _is_broad_path(path: str) -> bool:
    return path in {"", "."}


def _is_public_path(path: str) -> bool:
    return path in PUBLIC_PATHS


def _is_protected_path(path: str) -> bool:
    return any(path == root or path.startswith(f"{root}/") for root in PROTECTED_ROOTS)


def _is_private_path(path: str) -> bool:
    if path == "profiles":
        return False
    return _is_protected_path(path) and not _is_public_path(path)


def _resolve_git_cwd(base_dir: Path, value: str) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = base_dir / candidate
    return candidate.resolve()


def _git_add_pathspecs(tokens: list[str], initial_base: Path) -> tuple[list[str], Path, bool, bool]:
    base_dir = initial_base
    force = False
    unknown_pathspecs = False
    if len(tokens) < 2 or PurePosixPath(tokens[0]).name != "git":
        return [], base_dir, force, unknown_pathspecs

    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            index += 1
            break
        if token == "-C":
            if index + 1 >= len(tokens):
                return [], base_dir, force, unknown_pathspecs
            base_dir = _resolve_git_cwd(base_dir, tokens[index + 1])
            index += 2
            continue
        if token.startswith("-C") and token != "-C":
            base_dir = _resolve_git_cwd(base_dir, token[2:])
            index += 1
            continue
        if token in {"-c", "--git-dir", "--work-tree", "--namespace", "--config-env"}:
            index += 2
            continue
        if token.startswith(("--git-dir=", "--work-tree=", "--namespace=", "--config-env=")):
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        break

    if index >= len(tokens) or tokens[index] not in {"add", "stage"}:
        return [], base_dir, force, unknown_pathspecs

    pathspecs: list[str] = []
    add_args = tokens[index + 1 :]
    arg_index = 0
    while arg_index < len(add_args):
        token = add_args[arg_index]
        if token == "--":
            pathspecs.extend(add_args[arg_index + 1 :])
            break
        if token in {"-f", "--force"}:
            force = True
        elif token in {"-A", "--all"}:
            if not pathspecs:
                pathspecs.append(".")
        elif token.startswith("--pathspec-from-file"):
            unknown_pathspecs = True
            if token == "--pathspec-from-file" and arg_index + 1 < len(add_args):
                arg_index += 1
        elif token.startswith("-") and not token.startswith(":"):
            if not token.startswith("--"):
                short_options = token[1:]
                if "f" in short_options:
                    force = True
                if "A" in short_options and not pathspecs:
                    pathspecs.append(".")
        else:
            pathspecs.append(token)
        arg_index += 1

    return pathspecs, base_dir, force, unknown_pathspecs


def _is_private_git_add(tokens: list[str], base_dir: Path, repo_root: Path) -> bool:
    pathspecs, git_base_dir, force, unknown_pathspecs = _git_add_pathspecs(tokens, base_dir)
    if unknown_pathspecs:
        return force
    if force and not pathspecs:
        return True

    for token in pathspecs:
        path = _normal_path(token, git_base_dir, repo_root)
        if force and (_is_broad_path(path) or _is_protected_path(path)):
            return True
        if _is_private_path(path):
            return True
    return False


def _command_segments(tokens: list[str]) -> list[list[str]]:
    segments: list[list[str]] = []
    segment: list[str] = []
    for token in tokens:
        if token in COMMAND_SEPARATORS:
            if segment:
                segments.append(segment)
                segment = []
        else:
            segment.append(token)
    if segment:
        segments.append(segment)
    return segments


def _is_cd_segment(tokens: list[str]) -> bool:
    return bool(tokens) and tokens[0] == "cd"


def _segment_cd_target(tokens: list[str]) -> str | None:
    for token in tokens[1:]:
        if not token.startswith("-"):
            return token
    return None


def _has_private_git_add(tokens: list[str]) -> bool:
    repo_root = _repo_root()
    base_dir = Path.cwd().resolve()
    for segment in _command_segments(tokens):
        if _is_cd_segment(segment):
            target = _segment_cd_target(segment)
            if target:
                base_dir = _resolve_git_cwd(base_dir, target)
            continue
        if _is_private_git_add(segment, base_dir, repo_root):
            return True
    return False


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
    if _has_private_git_add(tokens):
        return _deny()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
