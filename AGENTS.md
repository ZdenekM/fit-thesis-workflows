# diplomky_v2 Agent Instructions

This repository is a workflow layer for supervising and reviewing BP/DP theses. It is not an application. Keep the system simple: use project instructions, skills, plain Markdown artifacts, and small helper scripts only when they remove repeated manual work.

## Core Rules

- Work in one mode only: `DEEP`. Do not ask the user to choose FAST/STANDARD/DEEP.
- Case data lives under `cases/`. The directory is intentionally gitignored except for `cases/README.md`.
- Never move student PDFs, source zips, extracted text, code submissions, private notes, or generated case outputs into tracked paths.
- Do not preserve backward compatibility with older `~/code/diplomky` workflows unless the user explicitly asks.
- Avoid workaround thinking. If the workflow is too complicated, simplify the workflow rather than adding fallback layers.
- Windows is a supported operator platform. Do not introduce WSL-only assumptions: workflow helpers that operators or agents run directly need a Python/Pants/PEX command surface or native `.cmd`/`.ps1` launchers, POSIX shell entrypoints may only be convenience wrappers, and new path/subprocess/temp-file/encoding behavior must be Windows-aware.
- For non-trivial code navigation or edits, prefer Serena MCP for symbol-aware work when the language/root is supported; use `docs/serena-code-navigation.md` for repo and submitted-code scoping rules.
- Preserve `README.md` as the human/operator-facing chat-first entrypoint. Its top path should explain what a supervisor or opponent writes to the agent, include concise prompt examples, and keep script/skill internals as lower-level reference. Do not let it regress into a script-first runbook; move detailed procedures into skills, templates, or focused docs.
- Pipeline and helper-script extensions must be general and context-aware. Do not encode one real thesis, domain, dataset, concrete metric value, filename, or expected conclusion as an active workflow rule. When a case exposes a useful pattern, generalize it into evidence classes, configurable reviewer prompts, or cross-case checks, and apply the interpretation in the context of the current assignment, thesis phase, artifacts, and claims.
- Do not add brittle free-text heuristics such as "if raw thesis/code/README
  text contains this substring, infer meaning or choose workflow behavior."
  Semantic interpretation of free-form text belongs to an explicitly authorized
  agent/LLM workflow that writes a structured artifact with evidence anchors.
  Deterministic code should consume structured metadata, parsed sections with
  documented schemas, explicit operator configuration, typed evidence classes,
  manifests, hashes, or agent-produced JSON/Markdown contracts. String matching
  is acceptable only for bounded structural parsing such as known metadata
  labels, command output markers, file extensions, section headings, internal
  placeholders, path/privacy leak checks, or schema validation. Any temporary
  lexical detector over free-form text must be advisory, clearly labeled as a
  prompt for agent/human verification, and must not by itself become a gate,
  routing decision, readiness decision, migration decision, semantic finding,
  grading point, feedback/report wording, or claim about thesis/code quality.
- When a concrete case reveals a likely recurring review pattern, finish the case artifact first, then proactively suggest whether that pattern should be promoted into workflow docs, skills, templates, or TODO. If the user approves, update the workflow at the right level instead of leaving the lesson as an ad hoc memory.
- Keep `TODO.md` as an unnumbered list of open work only; delete completed items instead of leaving checked-off historical entries.
- Use tracked plan files for non-trivial multi-slice workflow/tooling changes. Active plans live under `plans/*_plan.md`, completed or superseded plans move under `plans/archive/`, and `plans/README.md` defines the plan contract. Tracked plans must stay case-neutral and must not include private case data.
- Do not pretend to have checked anything that was not available in the inputs. Mark indirect conclusions as estimates, risks, or items for manual verification.
- When the user asks about a detail of a concrete student, case, thesis, or submitted codebase, verify that detail in the active case artifacts before answering: rendered PDF/extracted text first, then source zips, notes, outputs, and submitted code where relevant. State whether the detail is explicit, inferred from code/config, or absent, and turn missing facts into precise follow-up questions or evidence requests.
- Important negative claims must cite evidence: a chapter/section/page, a file/path/function, a README/config/test, a missing artifact, or a concrete mismatch.
- Quantitative, evaluation, experiment, metric, performance, and result claims require semantic sanity review: check unit/scale, baseline, practical magnitude, reproducibility, and whether the thesis interpretation is proportionate to the values.
- Treat the submitted thesis PDF as the authoritative rendered thesis artifact. Do not run LaTeX/Overleaf builds by default; use source zips for diff/search/evidence. Compile only when the user explicitly asks, or when no rendered PDF is available and the limitation is stated.
- Before generating supervisor feedback, require assignment, deadline, and reviewer-profile context with `scripts/check-supervisor-ready <case-id> [round-id]`. If it fails, stop and ask for the missing assignment, academic year, work type, deadline override, or valid reviewer profile.
- Before generating opponent materials, require assignment and reviewer-profile context with `scripts/check-round-ready <case-id> [round-id]`. Supervisor deadline calibration does not apply to opponent reports.
- Use `scripts/case-doctor <case-id> [round-id]` as a read-only operator snapshot when orienting in a case or checking what is missing; it summarizes state but does not replace required workflow gates.
- Supervisor feedback, opponent materials, opponent-report review, revision diff, code consistency, code quality, and literature/citation review are multi-agent workflows. If the user has not explicitly authorized agent use in the current request, stop before producing or revising sendable/final artifacts and ask for explicit permission to use agents. Once authorized, use role-split agents and give them enough time.

## Command Routing

Treat `scripts/<tool>` references in these instructions and skills as logical workflow tool names. On Linux development checkouts, POSIX `scripts/<tool>` wrappers are acceptable. On native Windows operator checkouts, first package tools with `scripts\package-workflow-tools.cmd` or `.\scripts\package-workflow-tools.ps1`, then run `dist\workflow-tools\bin\<tool>.cmd` or `.\dist\workflow-tools\bin\<tool>.ps1`; do not ask operators to install Bash or WSL just to run this workflow. If a packaged launcher is missing or stale, rebuild it with the platform-native packaging entrypoint.

## Skill Routing

Use these repo-local skills as the primary workflow definitions:

- `.agents/skills/thesis-supervisor-feedback/SKILL.md` for iterative student-facing supervisor feedback.
- `.agents/skills/thesis-supervisor-feedback-review/SKILL.md` for the required critical second pass before sending supervisor feedback.
- `.agents/skills/thesis-opponent-materials/SKILL.md` for internal opponent preparation materials.
- `.agents/skills/thesis-opponent-materials-review/SKILL.md` for reviewing and hardening generated opponent materials.
- `.agents/skills/thesis-opponent-report-review/SKILL.md` for reviewing a draft opponent report before submission.
- `.agents/skills/thesis-revision-diff/SKILL.md` for comparing thesis/code revisions and checking whether prior feedback was addressed.
- `.agents/skills/thesis-github-code-intake/SKILL.md` for read-only GitHub repository and upstream PR contribution intake before code reviews.
- `.agents/skills/thesis-code-consistency/SKILL.md` for thesis-text versus code/reproducibility checks.
- `.agents/skills/thesis-code-quality-review/SKILL.md` for implementation quality, architecture/design, maintainability, runtime risks, and reviewer-facing developer evidence.
- `.agents/skills/thesis-literature-citation-review/SKILL.md` for cited-literature relevance, source availability, and citation-support checks.
- `.agents/skills/thesis-figure-media-review/SKILL.md` for internal visual evidence about thesis figures, tables, screenshots, result images, diagrams, reusable visual descriptions, context/claim alignment, and figure changes between rounds.
- `.agents/skills/thesis-typography-formal-review/SKILL.md` for late-stage, language-calibrated typography and formal-presentation checks.

When a round contains code, supervisor feedback and opponent materials must use both `thesis-code-consistency` and `thesis-code-quality-review`, or explicitly state why one of them could not be performed from the available inputs.

Code artifacts include source directories and archives copied into `inputs/`, plus read-only GitHub repo/PR snapshots imported into the ignored round workspace. If both a submitted archive and GitHub source are present, treat the submitted archive as the authoritative code submission unless case/round notes explicitly say the GitHub snapshot is the submitted source; if they are not compared, carry that limitation into downstream findings. After agent use is explicitly authorized, make code inspectable under the ignored round workspace, typically with `scripts/prepare-code-workspace <case-id> [round-id]` or GitHub intake before delegating to read-only reviewer agents. Prefer Serena for symbol-aware inspection of prepared code roots when practical. If authorization is missing, stop before generating any agent-dependent final artifact and ask for it.

Keep this `AGENTS.md` short. Put long task procedures into skills or templates.
When changing workflow docs or skills, scan `WORKFLOW_MEMORY.md` for reusable
lessons and promote active rules into the appropriate workflow file instead of
treating memory as a second instruction system.

## Case Layout

Use this shape for local work:

```text
cases/<case-id>/
  case.md
  current-round.txt
  rounds/
    <timestamp>-<label>/
      notes/
      inputs/
      extracted/
      work/
      outputs/
```

For iterative supervisor feedback, always inspect previous rounds in the same case before writing new feedback. Read earlier `outputs/feedback_student.md` files and distinguish:

- feedback already addressed,
- feedback partially addressed,
- feedback still relevant,
- new risks introduced by the current revision.

Do not repeat old feedback mechanically.

## Parallel Review

When the user explicitly authorizes agents, give them enough time. If authorization is missing, ask once and wait; do not begin the parallel review or generate a sendable/final artifact. For thesis/code reviews, split work by role rather than by arbitrary files:

- text structure and assignment coverage,
- figure/media evidence, captions, visual claims, context/claim alignment, and figure changes between rounds,
- code/reproducibility and text-code consistency,
- code quality/design and reviewer-facing implementation evidence,
- GitHub/PR contribution intake when code evidence comes from GitHub URLs or upstream PRs,
- literature/citation relevance, source availability, and claim support,
- late-stage typography/formal presentation when the round is near final or explicitly asks for it,
- evidence and claim calibration,
- synthesis into the final Markdown artifact.

The final output must integrate findings into the requested artifact, not just list reviewer comments.

Bound agent concurrency by default: run at most two spawned workflow agents at the same time, and use one on memory-constrained machines. Higher concurrency requires an explicit project config change before the run, not only an ad hoc decision in the prompt. This is scheduling only; it does not reduce required role coverage, evidence artifacts, independent review, manifest hashes, or `scripts/check-agent-coverage`. For larger workflows, run role agents in waves according to `docs/agent-scheduling.md` and let each wave finish before starting the next one.

When spawning reviewer agents, prefer concise self-contained prompts with exact case/round paths and role-owned outputs. Do not use full-history/forked context by default; use it only when the role genuinely needs the whole conversation. If a spawn invocation fails because full-history/fork options are incompatible with explicit agent type or reasoning effort, retry with the simpler no-fork invocation and carry the needed context in the prompt.

## Generated Artifact Review Loop

Any generated Markdown artifact under `outputs/` that is sendable to a student/opponent context, or used as final operator evidence, must pass an explicitly authorized independent agent review loop. If the user has not authorized agents in the current request, ask for authorization and stop before writing or revising the final artifact. The loop terminates only when a different explicitly authorized reviewer agent checks the draft or evidence and either writes the reviewed target artifact or explicitly approves it. Material edits after that review reopen the draft state.

Dedicated review loops:

- supervisor feedback: first draft in `work/feedback_student_draft.md`, then `thesis-supervisor-feedback-review` writes reviewed `outputs/feedback_student.md`;
- opponent materials: first draft in `work/oponent_podklady_draft.md` or `outputs/oponent_podklady.md`, then `thesis-opponent-materials-review` writes reviewed `outputs/oponent_podklady_revidovane.md`;
- opponent report draft: `scripts/draft-opponent-report <case-id> [round-id]` may create `work/oponent_posudek_draft.md` from reviewed opponent materials; the generated file is intentionally not sendable until a human calibrates concrete points/grade, resolves open wording, and `scripts/check-opponent-report <case-id> [round-id]` passes against the current reviewed materials hash;
- opponent report review: this is itself a review of a human draft; if an agent also rewrites the report text, run a fresh review pass before treating that rewrite as sendable.

Internal evidence artifacts such as `outputs/revision_diff.md`, `outputs/github_code_intake.md`, `outputs/code_consistency.md`, `outputs/code_quality_review.md`, `outputs/literature_citation_review.md`, `outputs/figure_media_review.md`, and `outputs/typography_formal_review.md` must be reviewed before they are relied on as final standalone evidence. A downstream synthesis review certifies only the findings it uses in supervisor feedback or opponent materials; it does not automatically mark the whole evidence artifact final. For standalone final use, a separate evidence-calibration reviewer must check the artifact and the review verdict must be recorded in the artifact, the provenance manifest, or the final response. Record any exception or unavailable review explicitly.

Keep generated-artifact provenance in the ignored round workspace at `work/review_manifest.json`. The manifest records contributing inputs, checks, skills, generator/reviewer roles, review scope, limitations, and the reviewed artifact hash so material edits after review are visible as stale. Required multi-agent role coverage is generated into `work/agent_coverage.json` from the manifest and validated by `scripts/check-agent-coverage <case-id> [round-id]`; missing required roles must be fixed in the manifest or recorded as typed limitations before closeout.

## Output Conventions

Default outputs go into the active round:

- supervisor feedback: `outputs/feedback_student.md`
- supervisor feedback draft for agent-generated first passes: `work/feedback_student_draft.md`
- revision comparison: `outputs/revision_diff.md`
- GitHub code intake: `outputs/github_code_intake.md`
- code consistency check: `outputs/code_consistency.md`
- code quality/design review: `outputs/code_quality_review.md`
- literature/citation review: `outputs/literature_citation_review.md`
- figure/media review: `outputs/figure_media_review.md`
- typography/formal review: `outputs/typography_formal_review.md`
- reusable visual inventory: `work/figure_media/visual_inventory.jsonl`
- review evidence/provenance manifest: `work/review_manifest.json`
- agent role coverage manifest: `work/agent_coverage.json`
- opponent materials: `outputs/oponent_podklady.md`
- reviewed opponent materials: `outputs/oponent_podklady_revidovane.md`
- opponent materials draft for agent-generated first passes: `work/oponent_podklady_draft.md`
- opponent report draft: `work/oponent_posudek_draft.md`
- opponent report review: `outputs/feedback_k_posudku.md`

Standalone GitHub intake, code consistency, code quality, literature/citation, figure/media, and typography/formal outputs are internal/operator evidence unless the user explicitly asks to send them. Student-facing feedback should contain only selected, phase-appropriate action items.

Student-facing supervisor feedback must respect `Student feedback language` from `case.md`: default `cs` with Czech diacritics, or explicit `en`. Do not infer feedback language from the thesis language in intake notes.
`Thesis language: cs/en/auto` is optional metadata for thesis-text checks and does not control feedback language.

Before closing a task, run relevant lightweight checks such as `git status --short --untracked-files=all`, `scripts/check-private`, `scripts/check-scripts`, and `git diff --check`. For larger repo-tooling edits, consider the dev-only hygiene targets in `docs/dev-hygiene.md`; they must not become thesis case pipeline gates. When changing deterministic checkers, run their smoke scripts too. After generating or revising round outputs, update and validate provenance with `scripts/init-review-manifest --run-checks <case-id> [round-id]`, `scripts/check-agent-coverage <case-id> [round-id]` when role coverage is required, and `scripts/check-review-manifest --require-complete <case-id> [round-id]`. Before sending student-facing supervisor feedback, also run `scripts/check-feedback-language <case-id> [round-id]` and `scripts/check-feedback-output <case-id> [round-id]`. Before relying on figure/media evidence, run `scripts/check-figure-media-review <case-id> [round-id]`. Before relying on typography/formal evidence, run `scripts/check-typography-formal --require-output <case-id> [round-id]`. Before relying on reviewed opponent materials, run `scripts/check-opponent-materials <case-id> [round-id]`. Before using an opponent-report draft, run `scripts/check-opponent-report <case-id> [round-id]`.
