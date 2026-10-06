# Closed slice charters - student_feedback_rendering_plan

Append-only. Charters moved verbatim here when their slice was marked
`done` and compacted inline, per `plans/README.md`
`## Charter Tiers And Compaction`.

## 2026-10-06

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

Status: done
Proposed commit message: Write student-facing sources as short links, not formal citations
Why: the operator asked (2026-10-06) for clickable literature without full formal
citations; a student needs to recognise and open a source, and writes the formal
citation in the thesis anyway.
Expected paths:

- `.agents/skills/thesis-supervisor-feedback/SKILL.md`
- `.agents/skills/thesis-supervisor-feedback-review/SKILL.md`
- `src/thesis_review_workflow/cli/check_feedback_output.py`
- `scripts/smoke-feedback-output`
- `tests/test_feedback_shape.py`
- `src/thesis_review_workflow/render/feedback/filters/identifier-links.lua` and
  `scripts/smoke-render-feedback` (same identifier forms as the checker)

Tasks:

- Skill rule: every source the feedback recommends or discusses carries a link taken
  from a source opened in the round, never from memory (DOI preferred, then arXiv, then
  a stable public URL; authors, venue and year only when none was verified), written as
  `**Authors, Venue Year:** [Title](https://doi.org/...)` in lists and as
  `[Short title](...) (Authors, Venue Year)` in tables; drop a long subtitle after a
  colon; no full formal citation and no bare DOI text.
- Review skill: the unconditional `check-feedback-output` step checks the rule.
- `check_feedback_output.py::check_bare_identifiers`: a `verify:` warning (not an error)
  for a `DOI 10.…`, `doi:10.…` or `arXiv NNNN.NNNNN` identifier outside a Markdown link.
  Identifier syntax only; the PDF filter links the same forms.
- Smoke: one positive and one negative case.

Out of scope: the literature-citation review's internal evidence format; already sent
feedback.
Verification:

- `scripts/smoke-feedback-output`, and `scripts/smoke-render-feedback` after
  `scripts/package-workflow-tools`
- `pants test tests/test_feedback_shape.py`
- `scripts/check-scripts`, `git diff --check`

### Slice 3 - Operator documentation and Windows check

Status: done
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
