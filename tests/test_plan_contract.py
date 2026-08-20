"""Deterministic gate for the tracked plan contract (`plans/README.md`).

Review rounds were doing lint work — heading structure, charter shape, entry size, stale line
anchors — and every prose fix bought the next round. This module owns the mechanical half so plan
review can own judgement.

Two checks are RATCHETS calibrated by measuring this tree at adoption (2026-08-20): the per-plan
line budget and the count of line anchors outside `## Decision Log`. Measured then:

    case_format_migration_contract_plan.md          312 lines, 0 anchors
    multi_provider_agent_workflow_plan.md           669 lines, 1 anchor  (`AGENTS.md:12`)
    opponent_methodology_pipeline_plan.md         1,108 lines, 0 anchors
    review_manifest_closeout_repair_plan.md         374 lines, 0 anchors
    supervisor_opponent_feedback_learning_plan.md    432 lines, 0 anchors

The size budgets are CEILINGS against bloat, not change detectors: an in-progress plan legitimately
grows as slices execute, so each budget deliberately carries headroom over the measured count.
Pinning budgets to exact counts is deliberately NOT done — it would fire on every routine Progress
or Decision Log update and would normalize bumping the baseline, which is worse than headroom. What
the ratchet must stop is unbounded growth, and it does: growth past the ceiling blocks the next
slice until the plan is compacted. Lower a baseline whenever compaction shrinks a plan; raising one
needs a `## Decision Log` entry in that plan saying why.

Runs under Pants (`pants test tests/test_plan_contract.py`) and standalone via `__main__`
(`python3 tests/test_plan_contract.py`), because the PostToolUse plan-lint hook has no pytest.
"""

import re
from collections.abc import Callable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLANS_DIR = REPO_ROOT / "plans"

VALID_STATUSES = ("planned", "in_progress", "blocked", "done", "superseded")

REQUIRED_HEADINGS = (
    "## Goal",
    "## Audit Base",
    "## Scope",
    "## Slices",
    "## Progress",
    "## Decision Log",
    "## Final Audit",
)

# One tuple per required charter item; the first spelling is the item's key. `Work:` is an existing
# synonym of `Tasks:` in this tree, kept because forbidding it would force rewriting adjudicated
# slice text for no added information.
SLICE_LABEL_GROUPS = (
    ("Status:",),
    ("Proposed commit message:",),
    ("Why:",),
    ("Expected paths:",),
    ("Tasks:", "Work:"),
    ("Out of scope:",),
    ("Verification:",),
)

# Pre-adoption charter dialects, grandfathered with the exact scope of the exemption. These plans
# may omit the listed labels; every other check in this module still applies to them, and a plan
# absent from these two tables gets the full label set. Do not extend either table for new text —
# a legacy plan that adopts the full labels should be removed from it instead.
LEGACY_MISSING_LABELS = {
    "case_format_migration_contract_plan.md": {"Why:", "Out of scope:"},
    "opponent_methodology_pipeline_plan.md": {"Proposed commit message:", "Why:", "Out of scope:"},
    "review_manifest_closeout_repair_plan.md": {"Out of scope:"},
    "supervisor_opponent_feedback_learning_plan.md": {"Proposed commit message:", "Why:", "Out of scope:"},
}

# This plan's `### A1 — ...` blocks are prose status notes rather than charters, so no label subset
# describes them; its slice-charter form is exempt entirely until they are rewritten as charters,
# stubs, or compacted records.
LEGACY_CHARTER_FORM_PLANS = {"multi_provider_agent_workflow_plan.md"}

DEFAULT_SIZE_BUDGET = 1_500
DEFAULT_ANCHOR_BUDGET = 0

SIZE_BUDGETS = {
    "case_format_migration_contract_plan.md": 450,
    "multi_provider_agent_workflow_plan.md": 800,
    "opponent_methodology_pipeline_plan.md": 1_300,
    "review_manifest_closeout_repair_plan.md": 500,
    "supervisor_opponent_feedback_learning_plan.md": 600,
}

# `AGENTS.md:12` in this plan's `## Audit Base`; adjudicated text is not reworded to satisfy a
# ratchet, so the anchor is grandfathered instead.
ANCHOR_BUDGETS = {"multi_provider_agent_workflow_plan.md": 1}

DECISION_LOG_ENTRY_LINE_CAP = 20
STUB_MAX_LINES = 12
# Ceiling, not a target: `plans/README.md` asks for ~10 lines, the one in_progress plan measured 13
# at adoption, and this stops the section growing back into a second plan.
START_HERE_MAX_LINES = 18

# The entry gating an irreversible or outward-facing action may carry its evidence inline
# (`plans/README.md` `## Charter Tiers And Compaction`). Either marker claims the exemption, and the
# gate allows at most one such entry per plan, because that pass is singular by nature. The marker
# is writable, so this is protection against accident, not against intent.
INLINE_EVIDENCE_MARKERS = ("pre-send", "pre-spend")

# A line anchor is a path-like token ending in `:NNN`, or a BUILD-file anchor. Fenced lines are
# exempt: verification blocks legitimately carry commands such as `sed -n '1,40p'`, and a command
# is not a citation that drifts.
LINE_ANCHOR = re.compile(
    r"(?:\.(?:py|md|json|jsonl|toml|ya?ml|cfg|ini|sh|bash|txt|cmd|ps1|tex)[^\s`]*:\d+)" r"|(?:\bBUILD[^\s`]*:\d+)"
)

STATUS_LINE = re.compile(r"^Status:\s*([A-Za-z_]+)")
# `Charter form:` must be its own line naming the form directly after the label, so a block that
# merely mentions "stub" or "compacted" somewhere cannot claim the form.
CHARTER_FORM = re.compile(r"^\s*(?:-\s+)?`?Charter form:`? *`?(stub|compacted)\b")
LANDED_LABEL = re.compile(r"^\s*(?:-\s+)?`?Landed:`?", re.MULTILINE)


def _plan_files() -> list[Path]:
    assert PLANS_DIR.is_dir(), (
        f"{PLANS_DIR} is not readable — the BUILD dependency on //plans:plan_documents is missing, "
        "and a silent skip would read as a pass"
    )
    files = sorted(PLANS_DIR.glob("*_plan.md"))
    assert files, f"no *_plan.md under {PLANS_DIR}; refusing to pass vacuously"
    return files


def _fenced(lines: list[str]) -> list[bool]:
    """Per-line flag: True while inside a ``` fence, so fenced text never parses as structure.

    Refuses an unbalanced fence: one unclosed ``` would mask the whole rest of the file and
    silently hide structure from every check below.
    """
    flags: list[bool] = []
    inside = False
    for line in lines:
        if line.lstrip().startswith("```"):
            inside = not inside
            flags.append(True)  # the fence markers themselves are not structure either
        else:
            flags.append(inside)
    assert not inside, "unbalanced ``` fence — the remainder of the file would be masked from the lint"
    return flags


def _sections(lines: list[str]) -> list[tuple[int, str]]:
    fenced = _fenced(lines)
    return [(i, line.rstrip()) for i, line in enumerate(lines) if line.startswith("## ") and not fenced[i]]


def _section_range(lines: list[str], heading: str) -> tuple[int, int]:
    """[start, end) line-index range of a `## ` section, or (-1, -1) when absent."""
    heads = _sections(lines)
    for pos, (index, text) in enumerate(heads):
        if text == heading:
            end = heads[pos + 1][0] if pos + 1 < len(heads) else len(lines)
            return index, end
    return -1, -1


def _status(lines: list[str]) -> str:
    """The plan status token, read from the header block above the first `## ` heading."""
    header_end = next((i for i, line in enumerate(lines) if line.startswith("## ")), len(lines))
    for line in lines[:header_end]:
        match = STATUS_LINE.match(line)
        if match:
            return match.group(1)
    raise AssertionError(f"no 'Status: <{'|'.join(VALID_STATUSES)}>' line above the first '## ' heading")


def _has_label(visible: list[str], label: str) -> bool:
    pattern = re.compile(rf"^\s*(?:-\s+)?`?{re.escape(label)}")
    return any(pattern.match(line) for line in visible)


def _decision_log_entries(lines: list[str]) -> list[tuple[int, list[str]]]:
    """Decision Log entries as (first line index, entry lines).

    Both dialects in this tree are supported: `### ` headed entries, and top-level `- ` bullets.
    Headings win when a section carries any, so bullets inside a headed entry do not split it.
    """
    start, end = _section_range(lines, "## Decision Log")
    assert start >= 0, "no `## Decision Log` section (plans/README.md `## Plan Shape`)"
    fenced = _fenced(lines)
    body = range(start + 1, end)
    heads = [i for i in body if lines[i].startswith("### ") and not fenced[i]]
    starts = heads or [i for i in body if lines[i].startswith("- ") and not fenced[i]]
    entries = []
    for pos, index in enumerate(starts):
        stop = starts[pos + 1] if pos + 1 < len(starts) else end
        entry = list(lines[index:stop])
        while entry and not entry[-1].strip():
            entry.pop()
        entries.append((index, entry))
    return entries


Plan = tuple[Path, list[str]]
Check = Callable[[Plan], None]


def _for_each_plan(check: Check) -> None:
    """Apply one check to every plan, naming the offending plan in the failure."""
    for path in _plan_files():
        try:
            check((path, path.read_text(encoding="utf-8").splitlines()))
        except AssertionError as error:
            raise AssertionError(f"{path.name}: {error}") from error


def test_no_generic_plan_md_exists() -> None:
    """The gate discovers plans as `*_plan.md`; a generic name would escape every check."""
    for name in ("PLAN.md", "plan.md"):
        assert not (PLANS_DIR / name).exists(), (
            f"plans/{name} exists but the gate discovers plans as *_plan.md only; rename it to a "
            "descriptive <topic>_plan.md (plans/README.md `## Layout`)"
        )


def _check_title_and_status_head_the_plan(plan: Plan) -> None:
    _, lines = plan
    assert lines and lines[0].startswith("# "), f"line 1 must be '# <Plan Title>', got {lines[:1]!r}"
    status = _status(lines)
    assert status in VALID_STATUSES, f"status {status!r} is not one of {VALID_STATUSES} (plans/README.md)"


def _check_required_headings_are_present_and_ordered(plan: Plan) -> None:
    _, lines = plan
    heads = [text for _, text in _sections(lines)]
    missing = [heading for heading in REQUIRED_HEADINGS if heading not in heads]
    assert not missing, f"missing required headings: {missing}"
    order = [heads.index(heading) for heading in REQUIRED_HEADINGS]
    assert order == sorted(order), f"required headings out of order: {heads}"
    if "## Acceptance Contract" in heads:
        assert (
            heads.index("## Scope") < heads.index("## Acceptance Contract") < heads.index("## Progress")
        ), "`## Acceptance Contract` must sit between `## Scope` and `## Progress` (plans/README.md)"


def _check_start_here_is_present_while_in_progress(plan: Plan) -> None:
    _, lines = plan
    if _status(lines) != "in_progress":
        return
    heads = [text for _, text in _sections(lines)]
    assert "## Start Here" in heads, "an in_progress plan must carry `## Start Here` (plans/README.md)"
    assert heads.index("## Start Here") < heads.index("## Goal"), "`## Start Here` belongs before `## Goal`"
    start, end = _section_range(lines, "## Start Here")
    block = list(lines[start:end])
    while block and not block[-1].strip():
        block.pop()
    assert len(block) <= START_HERE_MAX_LINES, (
        f"`## Start Here` is {len(block)} lines; the ceiling is {START_HERE_MAX_LINES} and the target "
        "is ~10 — state, exact next action, what not to read (plans/README.md `## Start Here`)"
    )


def _check_slice_charters_use_a_recognized_form(plan: Plan) -> None:
    """Every slice is a full charter, a marked stub, or a marked compacted record."""
    path, lines = plan
    if path.name in LEGACY_CHARTER_FORM_PLANS:
        return
    allowed_missing = LEGACY_MISSING_LABELS.get(path.name, set())
    start, end = _section_range(lines, "## Slices")
    assert start >= 0, "no `## Slices` section to read charters from (plans/README.md `## Plan Shape`)"
    fenced_all = _fenced(lines)  # file-level, so a fence straddling a section boundary keeps parity
    body = lines[start:end]
    fenced = fenced_all[start:end]
    slice_starts = [i for i, line in enumerate(body) if line.startswith("### ") and not fenced[i]]
    assert slice_starts, f"{path.name}: `## Slices` carries no `### ` slice heading"
    for pos, index in enumerate(slice_starts):
        heading = body[index].rstrip()
        stop = slice_starts[pos + 1] if pos + 1 < len(slice_starts) else len(body)
        block_lines = body[index:stop]
        while block_lines and not block_lines[-1].strip():
            block_lines.pop()
        # Structural matchers see only unfenced lines: a label inside a code block is content.
        visible = [line for line, in_fence in zip(block_lines, fenced[index:stop]) if not in_fence]
        forms = [match.group(1) for line in visible if (match := CHARTER_FORM.match(line))]
        if forms:
            assert len(forms) == 1, f"{heading}: more than one `Charter form:` line"
            if forms[0] == "compacted":
                assert LANDED_LABEL.search("\n".join(visible)), (
                    f"{heading}: a compacted record must carry a `Landed:` line with its commits "
                    "(plans/README.md `## Charter Tiers And Compaction`)"
                )
            else:
                assert len(block_lines) <= STUB_MAX_LINES, (
                    f"{heading}: a stub is at most {STUB_MAX_LINES} lines — objective, boundary and "
                    "what it serves; anything longer is a charter and needs the full label set"
                )
            continue
        missing = [
            group[0]
            for group in SLICE_LABEL_GROUPS
            if group[0] not in allowed_missing and not any(_has_label(visible, label) for label in group)
        ]
        assert not missing, (
            f"{heading}: neither a full charter nor a marked stub/compacted record; missing labels "
            f"{missing} (plans/README.md `## Slice Charters`)"
        )


def _check_decision_log_entries_fit_the_cap(plan: Plan) -> None:
    path, lines = plan
    exempted = 0
    for index, entry in _decision_log_entries(lines):
        if any(marker in entry[0].lower() for marker in INLINE_EVIDENCE_MARKERS):
            exempted += 1
            assert exempted <= 1, (
                f"{path.name} line {index + 1}: a second entry claims the inline-evidence exemption; "
                "only the one entry gating the irreversible action gets it (plans/README.md)"
            )
            continue
        assert len(entry) <= DECISION_LOG_ENTRY_LINE_CAP, (
            f"{path.name} line {index + 1}: Decision Log entry is {len(entry)} lines; the cap is "
            f"{DECISION_LOG_ENTRY_LINE_CAP} — move evidence behind a pointer (plans/README.md)"
        )


def _check_line_anchors_do_not_grow_outside_the_decision_log(plan: Plan) -> None:
    """Living text cites `path::symbol` or test names; line anchors drift and belong in dated records."""
    path, lines = plan
    dl_start, dl_end = _section_range(lines, "## Decision Log")
    fenced = _fenced(lines)
    count = sum(
        len(LINE_ANCHOR.findall(line)) for i, line in enumerate(lines) if not (dl_start <= i < dl_end) and not fenced[i]
    )
    budget = ANCHOR_BUDGETS.get(path.name, DEFAULT_ANCHOR_BUDGET)
    assert count <= budget, (
        f"{path.name}: {count} line anchors outside `## Decision Log` (budget {budget}). Living text "
        "cites `path::symbol`, a test name, or a workflow command; if anchors were removed, lower "
        "the baseline in this module"
    )


def _check_plans_stay_within_their_size_budget(plan: Plan) -> None:
    path, lines = plan
    budget = SIZE_BUDGETS.get(path.name, DEFAULT_SIZE_BUDGET)
    assert len(lines) <= budget, (
        f"{path.name}: {len(lines)} lines exceeds its budget of {budget}. Compact per plans/README.md "
        "`## Charter Tiers And Compaction` before starting a new slice; raising a budget requires a "
        "Decision Log entry saying why"
    )


def test_title_and_status_head_the_plan() -> None:
    _for_each_plan(_check_title_and_status_head_the_plan)


def test_required_headings_are_present_and_ordered() -> None:
    _for_each_plan(_check_required_headings_are_present_and_ordered)


def test_start_here_is_present_while_in_progress() -> None:
    _for_each_plan(_check_start_here_is_present_while_in_progress)


def test_slice_charters_use_a_recognized_form() -> None:
    _for_each_plan(_check_slice_charters_use_a_recognized_form)


def test_decision_log_entries_fit_the_cap() -> None:
    _for_each_plan(_check_decision_log_entries_fit_the_cap)


def test_line_anchors_do_not_grow_outside_the_decision_log() -> None:
    _for_each_plan(_check_line_anchors_do_not_grow_outside_the_decision_log)


def test_plans_stay_within_their_size_budget() -> None:
    _for_each_plan(_check_plans_stay_within_their_size_budget)


def main() -> int:
    """Run every check without pytest — used by the PostToolUse hook; also runnable by hand."""
    per_plan_checks = (
        _check_title_and_status_head_the_plan,
        _check_required_headings_are_present_and_ordered,
        _check_start_here_is_present_while_in_progress,
        _check_slice_charters_use_a_recognized_form,
        _check_decision_log_entries_fit_the_cap,
        _check_line_anchors_do_not_grow_outside_the_decision_log,
        _check_plans_stay_within_their_size_budget,
    )
    failures: list[str] = []
    try:
        test_no_generic_plan_md_exists()
    except AssertionError as error:
        failures.append(str(error))
    for path in _plan_files():
        pair = (path, path.read_text(encoding="utf-8").splitlines())
        for check in per_plan_checks:
            try:
                check(pair)
            except AssertionError as error:
                failures.append(f"{path.name} :: {check.__name__}: {error}")
    if failures:
        print("plan contract violations (plans/README.md):")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
