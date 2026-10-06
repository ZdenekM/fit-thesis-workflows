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
