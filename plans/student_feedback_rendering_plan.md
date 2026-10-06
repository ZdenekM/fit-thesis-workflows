# Student Feedback Rendering Plan

Status: in_progress
Created: 2026-10-06

## Start Here

State: in_progress (operator activated 2026-10-06). Slice 1 is done and committed; its
charter is not yet compacted. Next action: compact Slice 1 into
`plans/archive/student_feedback_rendering_plan/` with its commit, write the full Slice 3
charter (it becomes the next slice), then implement Slice 2, whose charter was reviewed
in the 2026-10-06 plan-critic round. Do not re-derive the format decision (Markdown
source + Quarto/Typst PDF) or re-read the Slice 1 review entries; both are adjudicated.

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

Status: done
Proposed commit message: Render reviewed student feedback to a PDF the student can open
Why: the student gets a plain Markdown file today; the prototype showed a readable
PDF needs no change to the source, the agents, or the checkers.
Expected paths:

- `src/thesis_review_workflow/render/feedback/**` (Typst partial, Lua filters, Quarto
  defaults, vendored OFL fonts with their licence files)
- `src/thesis_review_workflow/render/BUILD`
- `src/thesis_review_workflow/BUILD` (dependency override: `importlib.resources` use is
  invisible to inference)
- `src/thesis_review_workflow/feedback_render.py`
- `src/thesis_review_workflow/cli/render_feedback.py`
- `src/thesis_review_workflow/cli/BUILD` (its `python_source` target)
- `src/thesis_review_workflow/commands.py` (`WORKFLOW_COMMAND_MODULES` entry)
- `scripts/render-feedback`, `scripts/BUILD` (`shell_sources`, `pex_binary`, and
  `WORKFLOW_CLI_RUNTIME_DEPS`)
- `scripts/smoke-render-feedback`
- `tests/test_feedback_render.py`
- `src/thesis_review_workflow/cli/check_tooling.py`

The registration list follows `docs/workflow-command-surface.md`
(`### Operator Workflow Tools`); `tests/test_workflow_python_contracts.py` enforces it.

Tasks:

- Move the prototype template and filters into package resources loaded through
  `importlib.resources`, and declare them with a Pants `resources` target so the PEX
  carries them. Vendor one OFL sans family, subset (see `## Decision Log`), and point
  Typst `font-paths` at it.
- `render-feedback <case-id> [round-id]`: resolve the round as the other tools do;
  read `Student:` and `Topic:` through `metadata.py::read_fields` and the language through
  `check_feedback_output.py::read_language`; read the Markdown bytes once; copy them and
  the resources into a `tempfile` directory; run `quarto render` there; write
  `outputs/feedback_student.pdf`.
- Refuse to render unless the round's supervisor-feedback approval passes
  `review_approvals.py::validate_review_approval_with_manifest` (the gate
  `confirm-supervisor-report` uses) bound to the requested case, round, and
  `outputs/feedback_student.md`, and its artifact hash equals the bytes read for
  rendering. Remove `outputs/feedback_student.pdf` whenever no approval covers the
  current Markdown and before every approved render. `--draft` renders anyway to
  `work/feedback_student_preview.pdf` with a visible `NÁVRH` / `DRAFT` stamp, for
  operator preview only.
- Renderer values (language, title-block fields, mapped headings, stamp) go to
  `feedback-render.json`, which the pre-AST filter assigns over any source front matter.
- Title-block labels and date format follow `Student feedback language` (cs/en).
  Omit the supervisor name (see `## Decision Log`).
- Record the render with `operation_log.py::append_operation`: source hash, PDF hash,
  `quarto --version`, draft flag.
- Fail with a typed, readable message when `quarto` is missing or older than the
  tested version; add `quarto` to `check_tooling.py::OPTIONAL_COMMANDS`.
- Tests without Quarto: metadata extraction, draft flag, missing binary, and the
  approval gate, including rejection of a stale review basis, of feedback edited after
  approval, of a missing manifest or observed check, and of an invalid approval whose
  artifact hash still matches; the mapped headings exist in the skill's output contract.
- `scripts/smoke-render-feedback` renders a synthetic case-neutral cs and en fixture
  when `quarto` is present (a skip otherwise), through the generated packaged launcher
  in a copy without checkout sources (the pattern of
  `scripts/smoke-package-workflow-tools`), so missing package resources fail there.
  Text assertions use `pdftotext`: correct Czech quote pairs (also inside a callout), the
  date line, every priority row with its cell text, the draft stamp. Link assertions use
  `pdfinfo -url`: each DOI/arXiv target present, a link whose label differs from its
  destination, and no re-link of an identifier inside an existing link label.
- Windows-aware: `pathlib` only, no shell strings, explicit UTF-8, `quarto` resolved
  with `shutil.which` (picks up `quarto.exe`/`.cmd`).

Out of scope: the citation-format change (Slice 2), profile-level style overrides,
docs beyond the command's `--help` (Slice 3).
Verification:

- `pants test tests/test_feedback_render.py`
- `pants test tests/test_workflow_python_contracts.py`
- `scripts/package-workflow-tools`, then `scripts/smoke-render-feedback`
- `scripts/check-scripts`, `scripts/check-private`, `git diff --check`
- Omen on `src/thesis_review_workflow/feedback_render.py` and
  `src/thesis_review_workflow/cli/render_feedback.py` (CLI `omen -f json complexity`;
  the MCP server returned zero files, see `## Decision Log`).
- Manual: render one real approved round into its ignored `outputs/`, open the PDF.

### Slice 2 - Short, clickable sources in student feedback

Status: planned
Proposed commit message: Write student-facing sources as short links, not formal citations
Why: the operator asked (2026-10-06) for clickable literature without full formal
citations; a student needs to recognise and open a source, and writes the formal
citation in the thesis anyway.
Expected paths:

- `.agents/skills/thesis-supervisor-feedback/SKILL.md`
- `.agents/skills/thesis-supervisor-feedback-review/SKILL.md`
- `src/thesis_review_workflow/cli/check_feedback_output.py`
- `scripts/smoke-feedback-output`

Tasks:

- Skill rule: every source named in student-facing feedback carries a resolvable link
  (DOI preferred, then arXiv, then a stable URL), written as
  `**Authors, Venue Year:** [Title](https://doi.org/...)` in lists and as
  `[Short title](...) (Authors, Venue Year)` in tables; drop a long subtitle after a
  colon; no full formal citation and no bare DOI text.
- Review skill: the sendability pass checks the rule.
- `check_feedback_output.py`: a warning (not an error) for a `DOI 10.…` or
  `arXiv NNNN.NNNNN` identifier outside a Markdown link. Identifier syntax only.
- Smoke: one positive and one negative case.

Out of scope: the literature-citation review's internal evidence format; already sent
feedback.
Verification:

- `scripts/smoke-feedback-output`
- `pants test tests/test_feedback_shape.py`
- `scripts/check-scripts`, `git diff --check`

### Slice 3 - Operator documentation and Windows check

Charter form: stub
Objective: document `render-feedback` in `docs/operator-reference.md` and the
closing step of the supervisor-feedback skill (render after approval, attach the PDF),
add a one-line mention to the README's chat-first path, and run the packaged
launcher once on Windows with Quarto installed.
Boundary: no new behaviour; a Windows failure reopens Slice 1.
Serves: `## Goal` for operators on both platforms.

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

## Final Audit

Not started. Closeout runs `pants run :omen`, the Slice 1 and 2 verification blocks,
`python3 tests/test_plan_contract.py`, `scripts/check-private`, `scripts/check-scripts`,
and `git status --short --untracked-files=all`.
