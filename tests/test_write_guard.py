"""Contract tests for the Claude reviewer write-boundary PreToolUse guard."""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GUARD = REPO_ROOT / ".claude" / "hooks" / "pre_tool_use_write_guard.py"
CANARY = "thesis-code-quality-reviewer"
OWNED = "cases/demo/rounds/r1/outputs/code_quality_review.md"


def _denies(payload: dict | str, root: Path = REPO_ROOT, extra_env: dict | None = None, scope: bool = True) -> bool:
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    env = {"CLAUDE_PROJECT_DIR": str(root), "PATH": ""}
    if scope:
        # The parent exports the active case/round when launching a reviewer;
        # the guard fails closed without it. Tests supply demo/r1 by default.
        env["CLAUDE_REVIEW_CASE"] = "demo"
        env["CLAUDE_REVIEW_ROUND"] = "r1"
    if extra_env:
        env.update(extra_env)
    result = subprocess.run(
        [sys.executable, str(GUARD)],
        input=raw,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0
    return '"permissionDecision": "deny"' in result.stdout


def _reviewer(tool: str, path: str | None = None) -> dict:
    payload: dict = {"agent_type": CANARY, "agent_id": "abc", "tool_name": tool, "tool_input": {}}
    if path is not None:
        field = "notebook_path" if tool == "NotebookEdit" else "file_path"
        payload["tool_input"][field] = path
    return payload


def _abs(rel: str) -> str:
    return str(REPO_ROOT / rel)


def test_parent_is_never_constrained() -> None:
    # No agent_id => main/parent session, even if agent_type is present
    # (claude --agent gives the main thread an agent_type).
    assert not _denies({"tool_name": "Edit", "tool_input": {"file_path": _abs("AGENTS.md")}})
    assert not _denies({"agent_type": CANARY, "tool_name": "Edit", "tool_input": {"file_path": _abs("AGENTS.md")}})


def test_non_reviewer_subagent_is_not_constrained() -> None:
    assert not _denies(
        {
            "agent_type": "general-purpose",
            "agent_id": "abc",
            "tool_name": "Edit",
            "tool_input": {"file_path": _abs("src/thesis_review_workflow/x.py")},
        }
    )


def test_reviewer_may_write_only_its_owned_output() -> None:
    assert not _denies(_reviewer("Write", _abs(OWNED)))


def test_reviewer_may_not_write_sibling_or_other_role_outputs() -> None:
    assert _denies(_reviewer("Write", _abs("cases/demo/rounds/r1/outputs/feedback_student.md")))
    assert _denies(_reviewer("Write", _abs("cases/demo/rounds/r1/work/reviews/x_review.json")))


def test_reviewer_may_not_write_tracked_or_outside_paths() -> None:
    assert _denies(_reviewer("Edit", _abs("AGENTS.md")))
    assert _denies(_reviewer("Write", _abs("src/thesis_review_workflow/x.py")))
    assert _denies(_reviewer("Write", "/tmp/evil.txt"))
    assert _denies(_reviewer("NotebookEdit", _abs("docs/x.ipynb")))


def test_reviewer_cannot_escape_via_parent_refs() -> None:
    assert _denies(_reviewer("Write", _abs("cases/demo/rounds/r1/outputs/../../../../AGENTS.md")))


def test_reviewer_may_not_use_shell_spawn_network_or_mcp_tools() -> None:
    for tool in ("Bash", "Agent", "WebFetch", "WebSearch", "mcp__filesystem__write_file"):
        assert _denies({"agent_type": CANARY, "agent_id": "abc", "tool_name": tool, "tool_input": {}}), tool


def test_write_guard_is_wired_as_catch_all() -> None:
    # The guard must be dispatched for every tool (so Agent/MCP writes cannot
    # bypass it); a narrow matcher would silently let them through.
    settings = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    entries = settings["hooks"]["PreToolUse"]
    guard_entries = [
        e for e in entries if any("pre_tool_use_write_guard.py" in h.get("command", "") for h in e.get("hooks", []))
    ]
    assert len(guard_entries) == 1, "expected exactly one write-guard PreToolUse entry"
    assert guard_entries[0].get("matcher", "") in {"*", ""}, "write guard must use a catch-all matcher"


def test_reviewer_read_tools_are_allowed() -> None:
    for tool in ("Read", "Grep", "Glob"):
        assert not _denies({"agent_type": CANARY, "agent_id": "abc", "tool_name": tool, "tool_input": {}}), tool


def test_reviewer_write_without_path_fails_closed() -> None:
    assert _denies(_reviewer("Write", None))


def test_active_case_round_scope_confines_cross_case_writes() -> None:
    # When the parent exports the active case/round (as B3 will), a reviewer may
    # write only within that case and round, not another student's case.
    scope = {"CLAUDE_REVIEW_CASE": "demo", "CLAUDE_REVIEW_ROUND": "r1"}
    assert not _denies(_reviewer("Write", _abs(OWNED)), extra_env=scope)
    assert _denies(
        _reviewer("Write", _abs("cases/other-student/rounds/r1/outputs/code_quality_review.md")), extra_env=scope
    )
    assert _denies(_reviewer("Write", _abs("cases/demo/rounds/r9/outputs/code_quality_review.md")), extra_env=scope)


def test_final_reviewer_may_write_output_but_not_parent_mediated_approval() -> None:
    # Under the parent-mediated protocol a Claude final reviewer writes only its
    # analysis output; the hash-bound approval record is written by the parent,
    # so the reviewer's own attempt to write it is denied.
    reviewer = "thesis-supervisor-feedback-reviewer"

    def payload(rel: str) -> dict:
        return {"agent_type": reviewer, "agent_id": "x", "tool_name": "Write", "tool_input": {"file_path": _abs(rel)}}

    assert not _denies(payload("cases/demo/rounds/r1/outputs/feedback_student.md"))
    assert _denies(payload("cases/demo/rounds/r1/work/reviews/supervisor_feedback_review.json"))


def test_reviewer_write_without_active_scope_fails_closed() -> None:
    # No CLAUDE_REVIEW_CASE/ROUND exported -> the guard cannot confine the write
    # to the active student's round, so even an owned-output write is denied.
    assert _denies(_reviewer("Write", _abs(OWNED)), scope=False)


def test_malformed_input_fails_closed() -> None:
    assert _denies("this is not json")


def test_orphan_adapter_absent_from_policy_fails_closed(tmp_path: Path) -> None:
    # A Claude adapter that exists on disk but is not covered by the policy must
    # not run unconstrained: the guard denies rather than treating it as a
    # non-reviewer.
    (tmp_path / ".claude" / "agents").mkdir(parents=True)
    (tmp_path / ".claude" / "agents" / "orphan.md").write_text("---\nname: orphan\n---\nbody\n", encoding="utf-8")
    (tmp_path / ".claude" / "hooks").mkdir(parents=True)
    (tmp_path / ".claude" / "hooks" / "reviewer_write_policy.json").write_text("{}\n", encoding="utf-8")
    payload = {
        "agent_type": "orphan",
        "agent_id": "x",
        "tool_name": "Write",
        "tool_input": {"file_path": str(tmp_path / "AGENTS.md")},
    }
    assert _denies(payload, root=tmp_path)


def test_missing_policy_fails_closed_for_reviewer_writes(tmp_path: Path) -> None:
    # Point the guard at a project dir with no policy file: a subagent write
    # must be denied rather than silently allowed.
    assert _denies(
        _reviewer("Write", str(tmp_path / "cases/demo/rounds/r1/outputs/code_quality_review.md")), root=tmp_path
    )
