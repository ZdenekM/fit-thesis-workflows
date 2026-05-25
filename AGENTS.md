# diplomky_v2 Agent Instructions

This repository is a workflow layer for supervising and reviewing BP/DP theses. It is not an application. Keep the system simple: use project instructions, skills, plain Markdown artifacts, and small helper scripts only when they remove repeated manual work.

## Core Rules

- Work in one mode only: `DEEP`. Do not ask the user to choose FAST/STANDARD/DEEP.
- Case data lives under `cases/`. The directory is intentionally gitignored except for `cases/README.md`.
- Never move student PDFs, source zips, extracted text, code submissions, private notes, or generated case outputs into tracked paths.
- Do not preserve backward compatibility with older `~/code/diplomky` workflows unless the user explicitly asks.
- Avoid workaround thinking. If the workflow is too complicated, simplify the workflow rather than adding fallback layers.
- Windows is a supported operator platform. Do not introduce WSL-only assumptions: workflow helpers that operators or agents run directly need a Python/Pants/PEX command surface or native `.cmd`/`.ps1` launchers, POSIX shell entrypoints may only be convenience wrappers, and new path/subprocess/temp-file/encoding behavior must be Windows-aware.
- For non-trivial code navigation, edits, or tracked workflow Markdown section work, prefer Serena MCP when the language/root is supported; use `docs/serena-code-navigation.md` for repo and submitted-code scoping rules.
- When a prompt, plan, skill, or repo instruction explicitly requires a named tool such as Serena or Omen, preflight the tool at the start of the slice, perform at least one meaningful scoped use, and record the observed result in the plan, operation log, or closeout. If the tool cannot inspect the intended target, first try a reasonable repair or scope adjustment; if it is still blocked, stop before replacing it with another evidence source unless the workflow explicitly permits an optional typed limitation.
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
- When the operator gives calibration feedback on generated wording, tone, grading, emphasis, or report/feedback judgment, first fix the current artifact and run the required review loop. Then decide whether the feedback is case-specific, a durable personal preference, or a general workflow rule. Store durable personal preferences in the active private reviewer profile, promote general rules into skills/docs/templates/TODO, and mention the promotion in the closeout so the operator does not have to repeat the same correction next time.
- Keep `TODO.md` as an unnumbered list of open work only; delete completed items instead of leaving checked-off historical entries.
- Use tracked plan files for non-trivial multi-slice workflow/tooling changes. Active plans live under `plans/*_plan.md`, completed or superseded plans move under `plans/archive/`, and `plans/README.md` defines the plan contract. Tracked plans must stay case-neutral and must not include private case data.
- Use the configured `mcp-local-rag` server as an optional discovery layer for historical orientation across Markdown-heavy workflow docs, plans, skills, reviewer profiles, notes, and generated Markdown outputs; follow `docs/local-rag-usage.md`.
- When exact Markdown search would produce high-fanout narrative matches across many plans, docs, or skills, use local RAG as a triage step to identify the most likely 1-2 source documents before opening files broadly.
- Treat local RAG results as pointers, not evidence. Before making thesis-review claims, editing workflow files, or drafting report/feedback wording, open the authoritative source artifact and cite that path, section, page, or line instead of a RAG chunk or score.
- Keep local RAG databases, model caches, and any indexed case data outside tracked paths. If ignored `cases/` content is indexed locally, retrieved chunks inherit the same privacy boundary as the original case files.
- Do not treat `BASE_DIRS` as a safe file-level allowlist or exclude mechanism. If a broad root such as `cases/` is configured, it only makes targeted files reachable; use curated ingest logic or explicit safe subroots before bulk ingest.
- Do not bulk-index prepared submitted-code workspaces, unpacked submitted-source directories, raw GitHub intake snapshots, or extracted thesis text into local RAG, especially `cases/**/work/code/**`, `cases/**/work/submission_bundle/**`, raw `cases/**/inputs/github/**` diffs/patches/comments/logs, nested non-evidence `cases/**/inputs/**` source trees, and `cases/**/extracted/**`. Case RAG is for notes, assignments, direct Markdown inputs such as prior feedback, curated GitHub intake summaries, reviewer profiles, generated Markdown outputs, and operator work summaries; submitted code stays in the code-review path with `rg`, Serena, Omen, tests, and direct source reads.
- Do not pretend to have checked anything that was not available in the inputs. Mark indirect conclusions as estimates, risks, or items for manual verification.
- If the user describes a new or follow-up thesis round and says the student added, finished, or changed current materials, verify that the case contains a matching newer PDF/source zip/code artifact before drafting. If the newest available artifacts are older than the described update, explicitly ask for the new materials or state that only a provisional stale-artifact review is possible.
- When the user asks about a detail of a concrete student, case, thesis, or submitted codebase, verify that detail in the active case artifacts before answering: rendered PDF/extracted text first, then source zips, notes, outputs, and submitted code where relevant. State whether the detail is explicit, inferred from code/config, or absent, and turn missing facts into precise follow-up questions or evidence requests.
- Important negative claims must cite evidence: a chapter/section/page, a file/path/function, a README/config/test, a missing artifact, or a concrete mismatch.
- Quantitative, evaluation, experiment, metric, performance, and result claims require semantic sanity review: check unit/scale, baseline, practical magnitude, reproducibility, and whether the thesis interpretation is proportionate to the values.
- In code-backed theses, check whether implementation text explains architecture, algorithmic principles, state/data flow, and design choices at a level understandable to a supervisor or opponent, not only as a list of functions, endpoints, files, or classes. Prefer diagrams or tables over long verbal descriptions for complex geometry, workflows, state machines, and multi-component runtime flows. Distinguish unit-level tests for deterministic algorithmic components from integration tests for runtime/service wiring; missing unit coverage for an isolated algorithm should be surfaced as a calibrated limitation when material.
- Treat the submitted thesis PDF as the authoritative rendered thesis artifact. Do not run LaTeX/Overleaf builds by default; use source zips for diff/search/evidence. Compile only when the user explicitly asks, or when no rendered PDF is available and the limitation is stated.
- Before generating supervisor feedback, require assignment, deadline, and reviewer-profile context with `scripts/check-supervisor-ready <case-id> [round-id]`. If it fails, stop and ask for the missing assignment, academic year, work type, deadline override, or valid reviewer profile.
- Before generating opponent materials, require assignment and reviewer-profile context with `scripts/check-round-ready <case-id> [round-id]`. Supervisor deadline calibration does not apply to opponent reports.
- Use `scripts/case-doctor <case-id> [round-id]` as a read-only operator snapshot when orienting in a case or checking what is missing; it summarizes state but does not replace required workflow gates.
- Supervisor feedback, supervisor reports, opponent materials, opponent-report review, revision diff, code consistency, code quality, and literature/citation review are multi-agent workflows. If the user has not explicitly authorized agent use in the current request, stop before producing or revising sendable/final artifacts and ask for explicit permission to use agents. Once authorized, use role-split agents and give them enough time.
- Use the strongest available model and high reasoning effort for semantic thesis-review roles that read thesis text, submitted code, evidence, synthesis drafts, or final/reviewable artifacts. Lower-cost models such as Spark are acceptable only for mechanical, validator-backed helper roles and must not be the sole basis for evidence claims, grading/report calibration, or sendable wording.

## Command Routing

Treat `scripts/<tool>` references in these instructions and skills as logical workflow tool names. On Linux development checkouts, POSIX `scripts/<tool>` wrappers are acceptable. On native Windows operator checkouts, first package tools with `scripts\package-workflow-tools.cmd` or `.\scripts\package-workflow-tools.ps1`, then run `dist\workflow-tools\bin\<tool>.cmd` or `.\dist\workflow-tools\bin\<tool>.ps1`; do not ask operators to install Bash or WSL just to run this workflow. If a packaged launcher is missing or stale, rebuild it with the platform-native packaging entrypoint.

## Skill Routing

Use these repo-local skills as the primary workflow definitions:

- `.agents/skills/thesis-supervisor-feedback/SKILL.md` for iterative student-facing supervisor feedback.
- `.agents/skills/thesis-supervisor-feedback-review/SKILL.md` for the required critical second pass before sending supervisor feedback.
- `.agents/skills/thesis-supervisor-report/SKILL.md` for formal supervisor-report drafts for FIT IS.
- `.agents/skills/thesis-supervisor-report-review/SKILL.md` for the required independent review before treating a supervisor-report draft as reviewed.
- `.agents/skills/thesis-opponent-materials/SKILL.md` for internal opponent preparation materials.
- `.agents/skills/thesis-opponent-materials-review/SKILL.md` for reviewing and hardening generated opponent materials.
- `.agents/skills/thesis-opponent-report-review/SKILL.md` for reviewing a draft opponent report before submission.
- `.agents/skills/thesis-revision-diff/SKILL.md` for comparing thesis/code revisions and checking whether prior feedback was addressed.
- `.agents/skills/thesis-github-code-intake/SKILL.md` for read-only GitHub repository and upstream PR contribution intake before code reviews.
- `.agents/skills/thesis-code-consistency/SKILL.md` for thesis-text versus code/reproducibility checks.
- `.agents/skills/thesis-code-quality-review/SKILL.md` for implementation quality, architecture/design, maintainability, runtime risks, and reviewer-facing developer evidence.
- `.agents/skills/thesis-quantitative-claims-review/SKILL.md` for semantic quantitative/result-claim sanity checks into `work/quantitative_claims.json`.
- `.agents/skills/thesis-literature-citation-review/SKILL.md` for cited-literature relevance, source availability, and citation-support checks.
- `.agents/skills/thesis-figure-media-review/SKILL.md` for internal visual evidence about thesis figures, tables, screenshots, result images, diagrams, reusable visual descriptions, context/claim alignment, and figure changes between rounds.
- `.agents/skills/thesis-typography-formal-review/SKILL.md` for late-stage, language-calibrated typography and formal-presentation checks.
- `.agents/skills/thesis-theses-similarity-review/SKILL.md` for interpreting imported Theses.cz similarity reports in case context.
- `.agents/skills/historical-opponent-calibration/SKILL.md` for private historical opponent-report calibration profiles and checklists.
- `.agents/skills/historical-supervisor-report-calibration/SKILL.md` for private historical supervisor-report calibration profiles and checklists.

When a round contains code, supervisor feedback, supervisor reports, and opponent materials must use both `thesis-code-consistency` and `thesis-code-quality-review`, or explicitly state why one of them could not be performed from the available inputs.

Code artifacts include source directories and archives copied into `inputs/`, plus read-only GitHub repo/PR snapshots imported into the ignored round workspace. If both a submitted archive and GitHub source are present, treat the submitted archive as the authoritative code submission unless case/round notes explicitly say the GitHub snapshot is the submitted source; if they are not compared, carry that limitation into downstream findings. After agent use is explicitly authorized, make code inspectable under the ignored round workspace, typically with `scripts/prepare-code-workspace <case-id> [round-id]` or GitHub intake before delegating to read-only reviewer agents. Prefer Serena for symbol-aware inspection of prepared code roots when practical. If authorization is missing, stop before generating any agent-dependent final artifact and ask for it.

For repo-maintainer code changes, use Omen as an advisory code-quality signal:
attempt Omen MCP for scoped, iterative checks of touched Python modules during a
slice when it can inspect the intended target, and use reproducible `pants run
:omen` evidence for larger slice or closeout validation when code changed
materially. If Omen is requested by the user, prompt, plan, or repo instruction,
do not silently drop it after one failure: first repair scope/tooling when
reasonable, retry with a concrete module/root, and record the observed result.
Continue without Omen only after recording a specific blocker or typed
limitation; for code-heavy maintainer work where Omen was a required check, stop
and ask before substituting other evidence unless the workflow explicitly
permits continuing. For thesis code-quality review, Omen may be used as an
advisory static-analysis signal for complexity, dead code, churn, and ownership
risk on prepared submitted-code roots under the ignored case workspace. This is
separate from repo developer hygiene: `pants run :omen` uses `omen.toml` and
intentionally ignores `cases/` to avoid scanning private case data. Prefer the
Omen MCP server only when it can inspect the actual repo or prepared code root;
if MCP returns zero files for a non-empty root, treat that as an
MCP/path-handling failure, not as evidence about the code. The Omen CLI may be
used from the prepared code root when available. Omen absence or failure must be
recorded as a limitation, not treated as an operator-facing workflow blocker;
normal supervisor/opponent use must not require Omen.

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

When the user explicitly authorizes agents, use role coverage rather than
arbitrary file splits, and synthesize findings into the requested artifact. If
authorization is missing, ask once and stop before any parallel review or
sendable/final artifact generation.

`docs/agent-scheduling.md` owns concurrency, wave sequencing, subagent handoff
shape, role failure handling, and parent synthesis. `docs/agent-profile-matrix.md`
owns Codex role-profile routing, allowed writes, review separation, and
validators. The relevant repo-local skill owns role-specific evidence rules,
output paths, and checker expectations.

## Generated Artifact Review Loop

Any generated Markdown artifact under `outputs/` that is sendable to a
student/opponent context, or used as final operator evidence, must pass the
independent review loop defined by its repo-local skill and
`docs/agent-profile-matrix.md`. Material edits after that review reopen draft
state. A downstream synthesis review certifies only the findings it uses; it
does not automatically make every standalone evidence artifact final.

Generated-artifact provenance stays in the ignored round workspace. Use the
existing manifest, coverage, wave, approval, delta, and closeout commands named
by the relevant skill and `docs/agent-scheduling.md`; use
`scripts/record-workflow-operation` for the existing `work/operation_log.jsonl`
reconstruction trail. Do not invent replacement ledgers or closeout surfaces.

## Output Conventions

Default artifact paths live in the relevant repo-local skill and
`docs/agent-profile-matrix.md`. Standalone GitHub intake, code consistency,
code quality, literature/citation, figure/media, typography/formal, and
Theses.cz outputs are internal/operator evidence unless the user explicitly
asks to send them. Student-facing feedback should contain only selected,
phase-appropriate action items.

Student-facing supervisor feedback must respect `Student feedback language` from `case.md`: default `cs` with Czech diacritics, or explicit `en`. Do not infer feedback language from the thesis language in intake notes.
`Thesis language: cs/en/auto` is optional metadata for thesis-text checks and does not control feedback language.

Before closing a repo-maintainer task, run relevant lightweight checks such as
`git status --short --untracked-files=all`, `scripts/check-private`,
`scripts/check-scripts`, and `git diff --check`. For larger repo-tooling edits,
use the dev-only hygiene targets in `docs/dev-hygiene.md`; when the touched
surface includes analyzable Python workflow code or scripts, attempt scoped Omen
MCP during implementation when it can inspect the target, and use `pants run
:omen` for reproducible closeout. These developer checks must not become thesis
case pipeline gates.
When changing deterministic checkers, run their smoke scripts and targeted Pants
tests too. For generated thesis-review artifacts, use the role-specific
validators, manifest/coverage checks, and closeout command named by the relevant
skill and profile matrix.
