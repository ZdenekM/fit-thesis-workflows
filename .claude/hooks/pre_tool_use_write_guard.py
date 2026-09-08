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
  only when the resolved target is one of the role's owned writes inside the
  active case — under ``cases/<id>/rounds/<round>/`` for a round-scoped role, or
  under ``cases/<id>/`` for a case-scoped one, since a ``topic-proposal`` case
  has no rounds. The scope comes from the policy entry, never from an unset
  environment variable. Deny every other tool (Bash, Task, WebFetch, ...) and
  every out-of-policy or path-less write.
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
SCOPES = {"round", "case"}


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


def load_policy(root: Path) -> dict[str, tuple[str, list[str]]] | None:
    """Return {reviewer-role: (scope, [allowed writes])} or None on error.

    The scope is carried in the POLICY, never inferred from an unset
    ``CLAUDE_REVIEW_ROUND``: inferring it would silently widen every round
    reviewer to case-level writes the first time a parent forgot to export the
    variable, which is the fail-open this guard exists to prevent.
    """
    try:
        raw = json.loads((root / POLICY_REL).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    policy: dict[str, tuple[str, list[str]]] = {}
    for role, entry in raw.items():
        if not isinstance(role, str) or not isinstance(entry, dict):
            return None
        scope = entry.get("scope")
        writes = entry.get("writes")
        if scope not in SCOPES or not isinstance(writes, list):
            return None
        policy[role] = (scope, [w for w in writes if isinstance(w, str)])
    return policy


def normalize_agent_type(agent_type: str) -> str:
    # Plugin-namespaced types look like "plugin:name"; take the final segment.
    return agent_type.split(":")[-1].strip()


def target_path(tool_input: dict) -> str:
    return str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")


def owned_write(resolved: Path, root: Path, scope: str, allowed: list[str]) -> bool:
    """True when `resolved` is one of this role's owned writes, inside its active case.

    `resolved` has already been symlink-resolved by the caller, and this
    `relative_to(root)` is what anchors the write to the repository's own
    `cases/` path: a `cases/<id>` redirected to `docs/<id>` lands outside that
    shape and is refused, which matters because a reviewer creates NEW files
    that no tracked-path check would see.
    """

    try:
        parts = resolved.relative_to(root).parts
    except ValueError:
        return False
    # The parent MUST export the active case (CLAUDE_REVIEW_CASE), and for a
    # round-scoped role the active round too. The guard fails closed without
    # them, and otherwise confines the write to that exact case, so a reviewer
    # cannot touch another student's case.
    case_scope = os.environ.get("CLAUDE_REVIEW_CASE")
    if not case_scope or not parts or parts[0] != "cases":
        return False
    if len(parts) < 2 or parts[1] != case_scope:
        return False

    if scope == "round":
        # cases/<id>/rounds/<round>/<tail...>
        round_scope = os.environ.get("CLAUDE_REVIEW_ROUND")
        if not round_scope:
            return False
        if len(parts) < 5 or parts[2] != "rounds" or parts[3] != round_scope:
            return False
        tail = "/".join(parts[4:])
    else:
        # cases/<id>/<tail...> — a `topic-proposal` case has no rounds at all.
        if len(parts) < 3:
            return False
        tail = "/".join(parts[2:])
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
        # If a Claude adapter exists for this agent_type but the policy does not
        # cover it, we cannot determine its owned writes: fail closed rather than
        # leave the reviewer unconstrained.
        if (root / ".claude" / "agents" / f"{agent_type}.md").is_file():
            return _deny(f"{agent_type} adapter is not covered by the reviewer write policy; failing closed")
        return None  # a non-reviewer subagent (no adapter)
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
        scope, allowed = policy[agent_type]
        if owned_write(resolved, root, scope, allowed):
            return None
        shape = "cases/<case-id>/rounds/<round-id>/" if scope == "round" else "cases/<case-id>/"
        return _deny(
            f"{agent_type} may write only its owned outputs {allowed} under {shape}. "
            f"Refused write to: {target}"
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
