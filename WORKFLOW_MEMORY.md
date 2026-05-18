# Workflow Memory

This file keeps durable workflow lessons, preferences, and rationale that are
useful when evolving the thesis-review workflow. It is not a case archive and
it is not a second instruction system.

Active rules belong in `AGENTS.md`, workflow procedures in `.agents/skills/`,
operator documentation in `README.md`, and future implementation work in
`TODO.md`. Case-specific notes belong under the ignored `cases/<case-id>/`
workspace.

## Rules For This File

- Do not include student names or identifiers, exact case IDs, exact round IDs,
  private thesis excerpts, private supervisor notes, local/workspace paths,
  source archive filenames, generated case outputs, or examples only meaningful
  for one real case.
- Keep entries short and reusable across cases.
- Mark whether a lesson is `candidate`, `promoted`, or `superseded`.
- When a lesson becomes an active rule, promote it into the relevant skill,
  README, AGENTS, template, or TODO item.
- Prefer updating an existing entry over adding near-duplicates.

## Durable Preferences

- Keep the operator workflow simple and conversational; hide packet-level or
  implementation detail unless it helps the current task.
- Keep `AGENTS.md` short. Put reusable procedures into skills, templates, or
  focused docs.
- Keep `TODO.md` as an unnumbered list of open work; remove completed items
  instead of preserving checked-off history.
- Preserve repeated-round history and revision diffs as first-class workflow
  evidence.
- Keep real case data private by default; tracked workflow files must not
  contain student PDFs, source zips, extracted thesis text, code submissions, or
  generated case outputs.
- Student-facing feedback should be concrete, supportive, readable, and
  actionable for both student and supervisor.

## Lessons Learned

### 2026-04-29: Submitted PDF Is The Rendered Source Of Truth

Status: promoted

Use the submitted thesis PDF as the authoritative rendered artifact. Use
LaTeX/Overleaf source zips for text diffs, search, and precise evidence. Do not
build LaTeX by default because students often compile on Overleaf and local TeX
failures can reflect the review environment rather than the thesis source.

Promoted to: `AGENTS.md`, `README.md`, supervisor/opponent skills.

### 2026-04-29: Supervisor Notes Are Hypotheses

Status: promoted

Supervisor notes should guide what to verify, not supply text to paste into
student-facing feedback. For each note, verify available evidence, classify the
result privately, and write only the student-relevant synthesis into the final
feedback.

Promoted to: `templates/round-notes.md`, `thesis-supervisor-feedback`,
`thesis-supervisor-feedback-review`, `README.md`.

### 2026-04-29: Student-Facing Feedback Should Avoid Internal IDs

Status: promoted

Student-facing feedback can include a human-readable review date, but should
avoid exact case IDs, round IDs, workspace paths, internal artifact filenames,
and workflow mechanics unless the student needs them to act.

Promoted to: supervisor feedback skills.

### 2026-04-29: Reviewer Profiles Are Active Configuration

Status: promoted

Reviewer profiles capture stable personal preferences, but they are active
workflow configuration rather than workflow memory. Public defaults belong in
`profiles/default.md`; personal overrides stay ignored under `profiles/local/`.

Promoted to: `profiles/README.md`, `README.md`, profile checker, privacy guard.

### 2026-04-29: PDF Detail Layer Before Literature Review

Status: promoted

Keep `pdftotext -layout` as the stable case evidence path. Use `pdf-reader-mcp`
only as an optional targeted detail layer for page ranges, metadata, figures,
tables, layout-sensitive checks, and literature PDFs that need page-local
evidence.

Promoted to: `docs/pdf-detail-layer.md`, README, thesis skills.

### 2026-05-04: Recurrent Review Patterns Should Be Promoted

Status: promoted

When a concrete case exposes a review issue that is likely to recur across BP/DP
work, finish the current artifact first and then offer to promote the pattern
into the workflow. Promote it at the right level: core guardrail in `AGENTS.md`,
procedure in a skill, operator guidance in `README.md`, template text, or TODO
for future automation.

Promoted to: `AGENTS.md`, `README.md`.

### 2026-05-14: Operator Wording Feedback Should Calibrate Profiles

Status: promoted

Operator corrections to generated report or feedback wording can reveal stable
style and assessment preferences. Finish and re-review the current artifact
first, then classify the correction: case-specific, durable personal preference,
or general workflow rule. Durable personal preferences belong in the active
private reviewer profile; general workflow rules belong in skills, docs,
templates, or TODO. Do not promote case-specific facts or student details.

Promoted to: `AGENTS.md`, `profiles/local/default.md`.

### 2026-05-15: Ask For New Round Materials When Prompt Implies Them

Status: promoted

When an operator asks for a follow-up thesis-feedback round and says the student
added, finished, or changed current chapters, tests, code, or other materials,
first verify that the active case contains a matching newer PDF/source
zip/code artifact. If the newest artifacts in the case are older than the
operator-described update, ask for the new materials before generating
sendable feedback, unless the operator explicitly wants a provisional
stale-artifact review.

Promoted to: `AGENTS.md`.

### 2026-05-15: Implementation Text Needs Principles, Visuals, And Test Layers

Status: promoted

For code-backed theses, review implementation chapters for opponent-readable
explanation: architecture, algorithmic principle, state/data flow, and design
choice should not collapse into a list of functions, endpoints, files, or
classes. Prefer diagrams or tables over dense prose for geometric algorithms,
workflow phases, state machines, and multi-component runtime flows. When
evaluating tests, distinguish deterministic algorithmic units from integration
tests that exercise service/runtime wiring. If a final-round thesis has only
integration tests for an isolated algorithm, surface it as a calibrated
limitation without implying that the whole work must be rewritten.

Promoted to: `AGENTS.md`, supervisor/opponent/report skills.

### 2026-05-18: Calibrate Overclaims Against Practical Impact

Status: promoted

When a thesis statement is stronger than the available evidence, first decide
whether it is a serious defect, a reproducibility uncertainty, or mainly
imprecise wording. If the implementation contains a plausible alternate
configuration for a claimed runtime path but the submitted default/build artifact
does not prove it was used, formulate the issue as a manual-check or
reproducibility uncertainty. If broad wording such as large scale, modular,
easily extensible, guaranteed, or fully supported is only partially supported,
calibrate it as an overclaim according to practical impact instead of treating it
as automatically grade-impacting.

Promoted to: `thesis-code-consistency`, `thesis-opponent-materials`,
`thesis-opponent-materials-review`.

### 2026-05-18: Required Role Failures Must Stop The Pipeline

Status: promoted

When a required role agent or helper fails to produce expected artifacts, the
workflow must stop before synthesis or closeout. Report the failed role, expected
paths, observed files, and checker result to the operator. Do not silently
substitute a smaller parent-generated artifact and mark coverage as satisfied;
rerun/repair the role, or record a blocked typed limitation only after the
operator chooses that route.

Promoted to: `AGENTS.md`, `docs/agent-scheduling.md`,
`thesis-figure-media-review`, `thesis-opponent-materials`, agent-coverage and
figure/media checkers.

### 2026-05-18: Targeted Literature Source Acquisition

Status: promoted

Literature/citation review must not leave selected key or suspicious citations
as manual external-source work just because no local PDFs were submitted. The
role should triage the bibliography, legally resolve public metadata/PDFs for
only material or suspicious items, cache evidence under the ignored
`work/literature/` workspace, and record the result in
`work/literature/source_acquisition.json`. The handoff must hash-bind the
thesis/bibliography `source_refs` with `source_sha256`. If access is blocked or
the operator disables external lookup, that limitation must be explicit in the
structured handoff; a blanket "no local PDFs, no external papers read"
limitation is not enough for pipeline-ready evidence.

Promoted to: `thesis-literature-citation-review`,
`scripts/check-literature-citation-review`, review manifest checks.

### 2026-05-18: Omen Has Separate Repo And Case Roles

Status: promoted

`pants run :omen` is developer hygiene for this workflow repository and its
`omen.toml` intentionally ignores `cases/` to avoid scanning private thesis
data. That privacy boundary does not prohibit targeted Omen use on submitted
student code after it has been prepared under an ignored case workspace. In
thesis code-quality review, Omen is optional advisory evidence only: MCP may be
used when scoped to a real prepared root, CLI may be used with cwd/path set to
that root, and zero-file MCP results for non-empty submitted code must be
reported as a tool/path-handling limitation rather than a code-quality signal.

Promoted to: `AGENTS.md`, `thesis-code-quality-review`, packet prompts, dev
hygiene docs.

### 2026-05-18: Case Operations Need A Reconstruction Trail

Status: promoted

When a case pipeline role fails, is skipped, is replaced by parent fallback, or
gets recalibrated by the operator, that must not remain only in chat history or
inside a generated artifact. Record the operational fact in a round-local
append-only `work/operation_log.jsonl` event with the affected artifacts/checks.
The log is intentionally separate from manifest hash gating: the manifest proves
reviewed artifact freshness, while the operation log reconstructs how the round
got there.

Promoted to: `AGENTS.md`, README, `record-workflow-operation`, `case-doctor`.

### 2026-05-04: Thesis Headings Need Structure Review

Status: promoted

Thesis text review should include a quick outline pass over chapter and section
headings. Check title length, whether the title matches the following content,
unnecessary repetition with parent or neighboring headings, and whether design,
implementation, testing, results, and discussion levels are clearly separated.
Calibrate severity by phase; in final rounds this is usually presentation polish
unless the outline harms orientation or defensibility.

Promoted to: supervisor/opponent skills.

### 2026-05-04: Figure/Media Claims Need Reusable Visual Evidence

Status: promoted

Visual thesis findings need a reusable per-item record. Text extraction can
inventory figures and captions, but claims about what an image shows require a
concrete PDF-detail/vision check or a source asset explicitly linked to the
rendered PDF. Figure/media review should also compare visual evidence between
rounds when previous inventories are available.

Promoted to: `thesis-figure-media-review`, `AGENTS.md`, README, figure/media checker.

### 2026-05-04: Figure/Media Cache Must Separate Visual Reuse From Context Claims

Status: promoted

Expensive visual descriptions may be reused between rounds only when the source
asset or rendered crop hash and visual-analysis version match. Claim alignment
is a separate judgment: it may be reused only when the visual hash, normalized
caption/text context hash, and claim-alignment version all match. If the
surrounding text or role of the figure changes, keep the visual reuse but redo
the claim-alignment pass.

Promoted to: `thesis-figure-media-review`, figure/media checker, supervisor/opponent skills.

### 2026-05-05: Windows Support Is A Standing Workflow Contract

Status: promoted

The repository must keep working for operators on native Windows without WSL-only
assumptions. Operator-facing helpers need a Python/Pants/PEX command surface or
native `.cmd`/`.ps1` launchers; POSIX shell may remain as convenience wrappers
or smoke maintenance only. Path handling, subprocess calls, temporary files,
text encoding, and operator documentation should be reviewed for Windows impact
whenever workflow commands change. In chat-first use, agents should treat
`scripts/<tool>` references as logical workflow tool names and route them to the
platform-appropriate launcher instead of asking Windows operators to use Bash or
WSL.

Promoted to: `AGENTS.md`, `README.md`, `scripts/check-scripts`, TODO.
