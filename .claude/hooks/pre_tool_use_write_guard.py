#!/usr/bin/env python3
"""Constrain spawned Claude reviewer subagents to their role-owned outputs.

Claude subagent frontmatter cannot path-scope Write/Edit, so this PreToolUse
hook enforces the boundary that Codex expresses through a role-scoped
``workspace-write`` sandbox. It is the authoritative reviewer sandbox for Claude:
even if a shadowing same-name adapter granted extra tools, this hook still
applies.

Behaviour:
- Acts only on **spawned subagents**, identified by the presence of ``agent_id``
  in the hook payload (``agent_type`` alone is unreliable: ``claude --agent X``
  gives the *main* session an ``agent_type``). The parent/main session is never
  constrained here, so ordinary development is not blocked.
- Applies only when the subagent's ``agent_type`` matches a reviewer role in
  ``.claude/hooks/reviewer_write_policy.json`` (kept in sync with the profile
  registry by a contract test). Non-reviewer subagents are not constrained.
- For a matched reviewer: allow Read/Grep/Glob; allow Write/Edit/NotebookEdit
  only when the resolved target is one of the role's owned round-relative writes
  under ``cases/<id>/rounds/<round>/``; deny every other tool (Bash, Task,
  WebFetch, ...) and every out-of-policy or path-less write.
- Fails closed: unparseable input, an unreadable policy file, or a write without
  a path all deny. The wiring adds ``|| exit 2`` so a crash blocks too.

The hook is wired as a catch-all (``matcher: "*"``) so every tool call from a
reviewer subagent is governed by the allowlist above — including ``Agent`` and
``mcp__*`` tools that an enumerated matcher would miss.
"""

from __future__ import annotations

import fnmatch
import json
import os
import subprocess
import sys
from pathlib import Path

WRITE_TOOLS = {"Write", "Edit", "NotebookEdit"}
READ_TOOLS = {"Read", "Grep", "Glob"}
POLICY_REL = ".claude/hooks/reviewer_write_policy.json"


def repo_root() -> Path:
    env_root = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_root:
        return Path(env_root).resolve()
    try:
        output = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return Path(output.strip()).resolve()
    except (OSError, subprocess.CalledProcessError):
        return Path.cwd().resolve()


def load_policy(root: Path) -> dict[str, list[str]] | None:
    """Return {reviewer-role: [allowed round-relative writes]} or None on error."""
    try:
        raw = json.loads((root / POLICY_REL).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    policy: dict[str, list[str]] = {}
    for role, writes in raw.items():
        if not isinstance(role, str) or not isinstance(writes, list):
            return None
        policy[role] = [w for w in writes if isinstance(w, str)]
    return policy


def normalize_agent_type(agent_type: str) -> str:
    # Plugin-namespaced types look like "plugin:name"; take the final segment.
    return agent_type.split(":")[-1].strip()


def target_path(tool_input: dict) -> str:
    return str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")


def owned_write(resolved: Path, root: Path, allowed: list[str]) -> bool:
    try:
        parts = resolved.relative_to(root).parts
    except ValueError:
        return False
    # cases/<id>/rounds/<round>/<tail...>
    if len(parts) < 5 or parts[0] != "cases" or parts[2] != "rounds":
        return False
    # When the parent launches a reviewer it exports the active case/round
    # (CLAUDE_REVIEW_CASE / CLAUDE_REVIEW_ROUND); if present, confine the write to
    # that exact case and round so a reviewer cannot touch another student's
    # case. Until the spawner sets them (B3), only the owned tail is enforced.
    case_scope = os.environ.get("CLAUDE_REVIEW_CASE")
    round_scope = os.environ.get("CLAUDE_REVIEW_ROUND")
    if case_scope and parts[1] != case_scope:
        return False
    if round_scope and parts[3] != round_scope:
        return False
    tail = "/".join(parts[4:])
    return any(tail == pattern or fnmatch.fnmatch(tail, pattern) for pattern in allowed)


def decide(payload: dict, root: Path) -> dict | None:
    """Return a deny hookSpecificOutput mapping, or None to allow."""
    if not payload.get("agent_id"):
        return None  # parent/main session (agent_id is the subagent discriminator)
    tool = str(payload.get("tool_name", ""))
    policy = load_policy(root)
    if policy is None:
        # Cannot determine the reviewer policy: fail closed for any write tool.
        if tool in WRITE_TOOLS:
            return _deny("reviewer write policy is unreadable; failing closed")
        return _deny(f"reviewer write policy is unreadable; refusing {tool or 'tool'}")
    agent_type = normalize_agent_type(str(payload.get("agent_type", "")))
    if agent_type not in policy:
        return None  # not one of our reviewer adapters
    if tool in READ_TOOLS:
        return None
    if tool in WRITE_TOOLS:
        target = target_path(payload.get("tool_input", {}))
        if not target:
            return _deny(f"{agent_type} attempted a {tool} with no target path")
        resolved = Path(target)
        if not resolved.is_absolute():
            resolved = root / resolved
        resolved = resolved.resolve()  # collapses symlinks and .. to block escapes
        if owned_write(resolved, root, policy[agent_type]):
            return None
        return _deny(
            f"{agent_type} may write only its owned outputs {policy[agent_type]} under "
            f"cases/<case-id>/rounds/<round-id>/. Refused write to: {target}"
        )
    return _deny(f"reviewer subagent {agent_type} may not use the {tool} tool")


def _deny(reason: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        json.dump(_deny("write guard could not parse hook input"), sys.stdout)
        return 0
    decision = decide(payload, repo_root())
    if decision is not None:
        json.dump(decision, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
