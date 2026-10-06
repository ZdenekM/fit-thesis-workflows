# Student Feedback Rendering Plan

Status: in_progress
Created: 2026-10-06

## Start Here

State: in_progress (operator activated 2026-10-06). Slices 1 and 2 are done and
committed; Slice 1 is compacted, Slice 2 is not. Next action: compact Slice 2 into
`plans/archive/student_feedback_rendering_plan/closed-slices-2026-10-06.md`, review the
Slice 3 charter once (plan-critic), then implement Slice 3. Its Windows run is an
operator step: ask, do not assume. Do not re-read the Slice 1 or 2 review entries;
they are adjudicated.

## Goal

An operator turns a reviewed `outputs/feedback_student.md` into a readable, searchable
A4 PDF with one command, `scripts/render-feedback <case-id> [round-id]`, to attach to
an e-mail or a Discord message. The Markdown stays the single source of truth for
agents, checkers, revision diffs, and local RAG; the PDF is a derived presentation
artifact. Student-facing literature in the feedback becomes clickable and short.

## Audit Base

Prototype, 2026-10-06, in a session scratchpad (not tracked, not under `cases/`):

- Toolchain: Quarto 1.10.18 with its bundled Typst 0.15.1 (`quarto typst --version`).
  No LaTeX. One real supervisor round's `feedback_student.md` rendered byte-unchanged
  (`cmp` against the case file) to a 5-page A4 PDF of about 100 kB with extractable
  Czech text (`pdftotext`).
- Shape that worked: a Typst template partial replacing Quarto's `typst-template.typ`
  (keeping its `article()` signature) plus three Lua filters: section-heading to block
  mapping and priority table to per-row cards (`at: pre-ast`), DOI/arXiv identifiers to
  links, and a Czech quote fix.
- Traps found, each needing an instrument in Slice 1:
  - Pandoc's Typst writer emits a closing `“` as a smart `"` but keeps the opening `„`
    literal, so Typst renders `„klasika„`.
  - A Czech date `6. 10. 2026` placed in Typst content starts an enumerated list;
    non-breaking spaces avoid it.
  - Quarto's Typst callout is `breakable: false` and colours `important` alarm-red;
    the template redefines `callout`.
  - A user filter that emits callout Divs must run `at: pre-ast`; listed plainly,
    it runs after Quarto has already processed callouts and the Divs stay plain.
  - The prototype used system fonts (Lato, Noto Sans); a Windows operator machine
    will not have them, so Typst would silently fall back to a different face.

Contracts the render must not disturb:

- Section headings are fixed and bilingual in
  `.agents/skills/thesis-supervisor-feedback/SKILL.md` (Czech names first); the
  priority table is parsed by `src/thesis_review_workflow/cli/check_feedback_output.py::check_priority_table`.
- The sendable review's approval payload binds the reviewed artifact and the review
  basis by hash (`src/thesis_review_workflow/review_approvals.py::build_review_approval_payload`),
  and `review_approvals.py::validate_review_approval_artifact` checks the whole
  contract; the supervisor-feedback approval lives at
  `work/reviews/supervisor_feedback_review.json` (`docs/agent-profile-matrix.md`).
- Workflow tools are a `scripts/<tool>` POSIX wrapper over
  `thesis_review_workflow.cli.<module>`, listed in `scripts/BUILD` `shell_sources`, and
  a `pex_binary` tagged `workflow-tool` there; `scripts/package-workflow-tools`
  (`src/thesis_review_workflow/cli/package_workflow_tools.py`) then generates the
  Windows `.cmd`/`.ps1` launchers from the tagged targets.
- Optional external tools are reported by
  `src/thesis_review_workflow/cli/check_tooling.py::OPTIONAL_COMMANDS`.
- Round events go to `work/operation_log.jsonl` through
  `src/thesis_review_workflow/operation_log.py::append_operation`.
- `profiles/README.md` (`## Assignment Authoring Boundary`): a supervisor name is
  case data, never profile content.
- `case.md` carries `Student:`, `Topic:`, and `Student feedback language:`.

## Scope

In scope:

- A render command for `outputs/feedback_student.md` (cs and en), its template,
  filters, and vendored fonts as package resources, packaged like every other
  workflow tool.
- A student-facing source-link convention in the supervisor-feedback skills, with a
  deterministic advisory check for bare DOI/arXiv identifiers.
- Operator documentation of the command.

Out of scope:

- Changing the Markdown section contract or adding `:::` blocks to the source.
- Rendering supervisor reports (they go to FIT IS as text), opponent materials
  (internal), or any `work/` evidence.
- Making Quarto a required dependency: without it, the operator sends the Markdown
  as before.
- HTML output, e-mail sending, or any upload.
- Student briefs from assignment authoring; revisit after this plan lands.

## Slices

### Slice 1 - Render command for approved student feedback

Charter form: compacted
Landed: 4f73817
Delivered `scripts/render-feedback` (packaged with Windows launchers): renders an
approved `outputs/feedback_student.md` to `outputs/feedback_student.pdf` behind the
manifest-backed approval gate, `--draft` to a stamped `work/feedback_student_preview.pdf`,
with package-resource template, filters and a Noto Sans subset; unit tests and
`scripts/smoke-render-feedback`.
Full charter: `plans/archive/student_feedback_rendering_plan/closed-slices-2026-10-06.md`.
Decisions: `2026-10-06 - Vendored font: Noto Sans, subset`,
`2026-10-06 - Slice 1 internal review (Claude read-only subagent)`,
`2026-10-06 - Slice 1 Codex slice review and narrow re-check`.

### Slice 2 - Short, clickable sources in student feedback

Charter form: compacted
Landed: bdd9a54
Added the short-link source rule (link only from an opened source) to the
supervisor-feedback skill and its review step, an advisory `verify:` warning for bare
DOI/arXiv identifiers in `check-feedback-output`, and the same identifier forms in the
PDF link filter; unit tests and smoke cases.
Full charter: `plans/archive/student_feedback_rendering_plan/closed-slices-2026-10-06.md`.
Decisions: `2026-10-06 - Link convention is a tracked skill default`,
`2026-10-06 - Slice 2 internal review (Claude read-only subagent)`.

### Slice 3 - Operator documentation and Windows check

Status: planned
Proposed commit message: Tell operators and agents when and how to render the feedback PDF
Why: `render-feedback` exists but nothing in the operator path or the skill names it, so
the PDF only happens when someone already knows the command.
Expected paths:

- `.agents/skills/thesis-supervisor-feedback/SKILL.md` (closing step after closeout)
- `.agents/skills/thesis-supervisor-feedback-review/SKILL.md` (hand-off to that step)
- `docs/operator-reference.md` (`## Výstupy` entry and a short render subsection)
- `README.md` (`## Co vznikne`, one line)

Tasks:

- Skill: after a successful `review-round-closeout`, when `quarto` is on PATH, the
  parent runs `scripts/render-feedback <case-id> [round-id]` and reports the PDF path
  only when the command succeeded. On failure (missing or too old Quarto, render error)
  report the error and that no `outputs/feedback_student.pdf` exists, unless the error
  says the stale PDF could not be removed: then the operator must close and delete it
  or rerun. The Markdown stays the sendable artifact while its approval is valid. Rendering is not sending; the agent
  never sends, and never treats `--draft` output as sendable.
- Review skill: after approval, the parent applies that closing step, also when the
  review was requested on its own; the reviewer role does not render.
- Operator reference: what the command does, the approval gate, stale-PDF removal,
  `--draft` to `work/feedback_student_preview.pdf`, Quarto as an optional dependency
  with the tested minimum version, Windows launcher names.
- README: one line under `## Co vznikne` for `outputs/feedback_student.pdf`; the
  chat-first top path stays unchanged.
- Windows: ask the operator to run, on a native Windows checkout with Quarto 1.10.18 or
  newer and a local round that has `outputs/feedback_student.md`,
  `scripts\package-workflow-tools.cmd`, then
  `dist\workflow-tools\bin\render-feedback.cmd <case-id> <round-id> --draft`, and open
  the PDF. This is draft-path evidence only. Record the result, without case details, in
  `## Decision Log`. A setup blocker (missing Quarto, round, or Markdown) is fixed on the
  operator side; only a reproducible renderer defect reopens Slice 1. Stay pending while
  the question is unanswered; move the check to `TODO.md` only when the operator confirms
  no Windows machine is available during this plan.

Out of scope: new behaviour of the command; profile styling (Slice 4); student briefs.
Verification:

- `pants test tests/test_feedback_shape.py tests/test_feedback_render.py tests/test_workflow_python_contracts.py`
- `scripts/check-scripts`, `scripts/check-private`, `git diff --check`
- `python3 tests/test_plan_contract.py`

### Slice 4 - Profile-level rendering style

Charter form: stub
Objective: let `profiles/local/<profile-id>.md` override accent colour and font family
through a small labelled section; the tracked template stays neutral.
Boundary: content, section mapping and the approval gate are not overridable.
Serves: other supervisors using the repo (house style belongs in the profile layer).
Charter only when a second supervisor or the operator asks for a different look.

## Progress

- 2026-10-06: plan created from the prototype session; no slice started.
- 2026-10-06: Slice 1/2 charter review (Codex plan-critic) adjudicated; fixes applied.
- 2026-10-06: Slice 1 done: unit tests, contract test, packaged smoke and one real
  approved round pass; internal review, Codex slice review and narrow re-check adjudicated.
- 2026-10-06: Slice 1 compacted; Slice 3 charter written (not yet reviewed). Slice 2
  done: tests, both smokes, and the checker on one real round (three advisory warnings).

## Decision Log

### 2026-10-06 - Markdown source, Quarto with Typst for the PDF

Trigger: operator asked to move student feedback from plain Markdown to something
nicer; compared Quarto (used in another repo) and hand-written HTML printed by Chrome
(used ad hoc in a third).
Decision: keep `feedback_student.md` as source and render with Quarto's Typst route.
Why: agents, `check-feedback-output`, revision diffs and RAG all read the Markdown;
per-document HTML would drift visually and move review onto markup; Typst ships inside
Quarto, needs no TeX, and runs natively on Windows.

### 2026-10-06 - Layout from the existing heading contract, not source markup

Decision: a pre-AST Lua filter maps the skill's fixed bilingual headings to blocks and
the priority table to cards; the Markdown gets no `:::` fences.
Why: the source contract and its checker stay untouched; AGENTS.md allows bounded
structural parsing of documented section headings. Sections outside the mapping render
as plain text by design.

### 2026-10-06 - No supervisor name in the title block

Decision: omit it. Why: `profiles/README.md` keeps supervisor names out of profiles,
`case.md` has no such field, and the sender of the e-mail is the supervisor anyway.
Residual: add a `case.md` field later if the operator wants the name printed.

### 2026-10-06 - Link convention is a tracked skill default

Decision: Slice 2 puts the short-link source format in the tracked skill, not the
private profile. Why: it is student readability, not personal style; the bare-identifier
check stays a warning so rounds in flight are not blocked.

### 2026-10-06 - Plan-critic review of the Slice 1 and 2 charters

Trigger: `scripts/agent-review --profile plan-critic --base HEAD~1` on commit `378fcae`.
- (a) Hash equality is not approval: confirmed, `review_approvals.py:502` also checks
  verdict, findings, basis hash. Fix: gate on `validate_review_approval_artifact`.
- (b) Registration incomplete: confirmed, `docs/workflow-command-surface.md:13`,
  `tests/test_workflow_python_contracts.py:522`. Fix: paths and contract test added.
- (b) Packaged resources unverified: confirmed. Fix: smoke runs the packaged launcher
  without checkout sources.
- (b) `pdftotext` cannot see link annotations: confirmed. Fix: `pdfinfo -url`.
- Slice 2's identifier check: no finding.
Decision: all four accepted. Narrow re-check of the fix batch: pass, no new findings.

### 2026-10-06 - Vendored font: Noto Sans, subset

Decision: one family, Noto Sans Regular/Bold/Italic/BoldItalic (OFL 1.1, no Reserved
Font Name) from Debian `fonts-noto-core`, subset with fontTools to Czech/Western Latin,
punctuation, Greek, arrows and common operators; recipe in
`src/thesis_review_workflow/render/feedback/fonts/SUBSET.md`.
Why: every workflow-tool PEX depends on `WORKFLOW_CLI_RUNTIME_DEPS`, so resources ship in
all of them. Measured: full four files 2.09 MB, Lato 2.74 MB, the subset 265 kB; render
resources add about 330 kB per PEX. Out-of-range characters fall back to any font Typst
finds. The licence file is `LICENSE-OFL`, since `check-private` treats `*.txt` as
extracted thesis text.

### 2026-10-06 - Slice 1 internal review (Claude read-only subagent)

- Gate used the base validator, which skips observed checks, basis candidates and
  reviewer independence: confirmed against `confirm_supervisor_report.py`. Fix: gate on
  `validate_review_approval_with_manifest`; the one real approved round passes it.
- Stale approved PDF survives a refused render: accepted, removed on refusal.
- Check-then-render race: accepted, bytes read once and bound to the approval hash.
- Windows locking on replace and temp cleanup: accepted, typed error, `.partial` unlinked.
- Card title assumed column 2: accepted, area located by header (`AREA_HEADER`).
- Draft output named like the review basis: renamed `work/feedback_student_preview.pdf`.
- Test and smoke gaps (edited source, cell bodies, link label, stamp, callout): accepted.
- Deferred nits: `doi:`/versioned arXiv forms (Slice 2 territory); `case.md` values
  are parsed as Markdown by Quarto, so a topic starting `1. ` would render as a list.
Omen MCP returned zero files for the repo root and both modules (path handling); the
`omen` CLI measured them instead, `main` split from cyclomatic 13 to 8.

### 2026-10-06 - Slice 1 Codex slice review and narrow re-check

Trigger: `scripts/agent-review --profile slice-review` on the uncommitted slice, verdict
`changes_required`; fixes re-checked by a read-only Claude subagent, not by Codex.
- Front matter overrode `feedback.draft`: confirmed, worse (it replaced the whole map, so
  no stamp, no section mapping, no cards). Fix: `feedback-render.json` read by the
  pre-AST filter overrides front matter; smoke fixture with such front matter.
- Missing-source refusal kept a stale PDF: accepted, removed on that path too.
- Area-cell links dropped from card titles: accepted, title is a callout heading.
- Re-check: fixes 1 and 3 verified; the new unlink could raise on a PDF open in a
  Windows viewer, and a failed re-render kept the earlier approved PDF. Fix: typed
  error on removal failure; the PDF is cleared before every approved render.
Residual: raw Typst or `header-includes` in the Markdown could still hide the stamp
(code injection, not metadata override); `pants check` on tests lacks pytest stubs
(pre-existing, `tests/test_feedback_shape.py` too).

### 2026-10-06 - Slice 2 internal review (Claude read-only subagent)

- Links could be written from memory: accepted, the rule requires a link from a source
  opened in the round, else authors, venue and year.
- Review check contradicted the writer rule and sat under a conditional item: accepted,
  moved to the unconditional `check-feedback-output` step and aligned.
- Rule covered quoting the student's own bibliography: accepted, narrowed to sources the
  feedback recommends or discusses.
- Warning read as an instruction: accepted, prefixed `verify:` per AGENTS.md.
- Regex kept a trailing backtick or table pipe: fixed; filter and checker grammars
  differed: `identifier-links.lua` now links `DOI:`, `doi:` and versioned arXiv forms.
Decision: no separate Codex round for this skill-text and advisory-warning slice; the
plan's closeout cross-provider review covers it. Residual: old-style arXiv ids
(`cs/0112017`) are neither warned nor linked.

### 2026-10-06 - Slice 3 charter review (Codex plan-critic)

Trigger: `scripts/agent-review --profile plan-critic --base 4f73817`, `changes_required`.
- Review skill had no render hand-off, so a standalone review left an old PDF: accepted
  (b), the review skill joins the expected paths with a parent hand-off.
- Closing step had no failure path; `check-tooling` reports Quarto by presence, not
  version (`check_tooling.py::check_optional_commands`): accepted (b), report a PDF only
  after success, else the error and the absent PDF.
- Windows step lacked preconditions and reopened Slice 1 on any failure: accepted (b),
  preconditions named, setup blockers separated from renderer defects.
- `tests/test_feedback_render.py` added to verification (c).
Decision: all accepted. Narrow re-check (Claude subagent): fixes 1, 3, 4 pass; fix 2
claimed no PDF remains, false when a locked stale PDF cannot be removed
(`render_feedback.py::remove_stale_pdf`); wording corrected, review chain closed.

## Final Audit

Not started. Closeout runs `pants run :omen`, the Slice 1 and 2 verification blocks,
`python3 tests/test_plan_contract.py`, `scripts/check-private`, `scripts/check-scripts`,
and `git status --short --untracked-files=all`.
