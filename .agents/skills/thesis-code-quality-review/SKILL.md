---
name: thesis-code-quality-review
description: Review BP/DP submitted code for architecture, design quality, maintainability, runtime risks, documentation, and smoke-test readiness, separate from thesis-text versus code consistency.
---

# Thesis Code Quality Review

Command routing: treat `scripts/<tool>` examples below as logical workflow
command names. On Windows, use the packaged
`dist\workflow-tools\bin\<tool>.cmd` or `.ps1` launcher from `README.md`; do
not run or click extensionless `scripts/<tool>` files.

Use this skill when a thesis round contains implementation artifacts and you need to assess whether the implementation is technically well engineered and defensible.

This is not the text-code consistency check. Use `thesis-code-consistency` for whether thesis claims match code, README, configs, tests, and results. Use this skill for the quality of the implementation itself.

## Inputs

Use the active round unless the user specifies another:

```text
cases/<case-id>/current-round.txt
cases/<case-id>/rounds/<round-id>/
  notes/
  inputs/
  extracted/
  work/
  outputs/
```

Prefer unpacked code under `work/code/` when available. Archives in `inputs/` count as code. GitHub repo/PR snapshots imported by `thesis-github-code-intake` also count as code evidence, but PR-mode review must stay scoped to student-owned diffs and contribution areas. After agent use is authorized, the main workflow should run `scripts/prepare-code-workspace <case-id> [round-id]` or otherwise unpack/import code into `work/code/` before delegating to read-only reviewers. If the code cannot be unpacked or inspected, state that concrete limitation instead of inventing findings.

## Process

1. Resolve the active case and round.
2. Confirm that the user explicitly authorized agent use in the current request when this review will produce final standalone evidence or feed supervisor/opponent artifacts. If explicit authorization is missing, stop before writing the artifact and ask the user to authorize agents.
3. Enumerate available code artifacts, GitHub intake evidence, README/developer docs, dependency files, configs, tests, experiment scripts, generated/bundled assets, thesis text that explains implementation choices, current-evidence snapshots, reuse-index decisions, role packets, reusable evidence artifacts, `work/context/evidence_capsules.json`, and `work/context/claim_review_basis.json` when present. Use the inventory to choose targeted reads; do not load broad source trees only because they exist.
4. If code is present only as an archive, run `scripts/prepare-code-workspace <case-id> [round-id]` when the current task permits writing ignored case workspace evidence. Use `work/code_workspace.md` and `work/serena_roots.json` as orientation aids; activate Serena only on one listed code root at a time. For Python and other supported language roots, prefer Serena symbol overview, definition, and reference tools for non-trivial architecture and maintainability inspection before falling back to broad file reads. Use `--refresh` only after confirming the whole ignored `work/code/` workspace can be rebuilt, because it removes manually imported code roots too. If GitHub URL/PR evidence is present but not yet imported, run or request `thesis-github-code-intake` before judging code quality. If you are in a read-only reviewer agent, report the missing prepared workspace/evidence instead of silently skipping the review.
5. Identify the project type and framework conventions before judging design. Do not punish a small thesis prototype for not looking like a production service.
6. For upstream PR contribution mode, use upstream code as integration context and focus findings on changed files, tests/docs, PR review discussion, CI state, and declared thesis scope.
7. Inspect the main implementation paths through prepared workspace summaries,
   GitHub contribution maps, relevant claim-basis entries, current
   `work/context/evidence_capsules.json` capsule refs, and targeted source reads
   first. Open broader code areas only for changed fingerprints,
   architecture/design claims, maintainability risks, contradiction, missing
   anchors, runtime concerns, or reviewer challenges. Assess:
   - architecture/design fit for the assignment and chosen framework,
   - module boundaries, data model, naming, and cohesion,
   - maintainability and readability,
   - error handling, validation, state handling, async/concurrency/runtime risks,
   - testing strategy, smoke-test workflow, and reproducibility for a reviewer,
   - README/developer documentation and installation/build instructions,
   - whether comments explain non-obvious logic without replacing clear code.
8. Omen may be used as an advisory static-analysis layer over prepared submitted-code roots or changed contribution paths. Prefer targeted complexity, dead-code, churn, and ownership checks that help validate maintainability and reviewer-confidence risks. This is distinct from repo developer hygiene: `pants run :omen` intentionally ignores `cases/` and does not decide whether case-local submitted code may be inspected. Prefer Omen MCP only when it can inspect the actual prepared code root; if MCP returns zero files/functions for a non-empty `work/code/` root, classify that as an MCP/path-handling failure, not as evidence about the submitted code. If the Omen CLI is available, it may be run with cwd/path set to the prepared submitted-code root and its output recorded under `work/code_quality_omen.json` or `work/code_quality_omen.md`. Do not require Omen for operator use; if it is unavailable or cannot inspect the submitted code root, record that limitation and continue with normal static review.
9. Run only simple local checks when they are documented, bounded, and do not need missing external data, credentials, services, models, or long execution.
10. Classify findings by severity and phase. In early drafts, prefer design direction and test plan feedback. In final checks, focus on issues that affect defensibility, runtime correctness, reviewer confidence, or grading.

## Evidence Rules

- Cite concrete code paths, functions, configs, README sections, missing tests, or missing build instructions.
- Do not claim that code ran unless you actually ran a specific command.
- Do not treat "not runnable from available inputs" as "broken".
- Separate code quality from text-code mismatch. If the issue is mainly that the thesis overclaims what code shows, route it through `thesis-code-consistency`.
- For PR-based work, do not treat the whole upstream repository as the student's implementation. Cite PR changed files, contribution map, review comments, CI state, or specific checkout paths from `outputs/github_code_intake.md`.
- If both a submitted archive and GitHub evidence exist, use the submitted archive as authoritative unless case/round notes explicitly declare GitHub as the submitted source; if they were not compared, keep GitHub-only quality findings scoped as supplemental evidence.
- For README, reproducibility, and smoke-test evidence: `thesis-code-consistency` checks whether thesis claims are supported by artifacts; this skill checks whether the submitted implementation is reviewable and maintainable independent of thesis claims. Cross-reference only when the same evidence affects both.
- Avoid low-value style nits unless they are repeated, confuse the implementation, or affect maintainability.
- Do not reward noisy comments. Prefer clear code plus useful comments around non-obvious decisions.
- Treat Omen findings as signals to verify against concrete code, not as standalone verdicts. Cite the code path/function and explain the maintainability or defensibility impact; do not expose Omen internals in student-facing prose unless the student needs a concrete action.

## Severity

- `P0`: can affect assignment fulfillment, defensibility, core runtime correctness, submission completeness, or grade.
- `P1`: significant engineering weakness or reviewer-confidence risk.
- `P2`: useful maintainability, documentation, or testability improvement.
- `P3`: minor style/readability issue; include only if repeated or representative.

## Review Loop

When this artifact is generated as standalone output, it is draft evidence until a different explicitly authorized reviewer agent checks it. If agent authorization is missing, ask before marking or relying on it as final standalone evidence; if authorization is not granted, stop before final standalone use or before using the artifact in a sendable supervisor/opponent synthesis. A downstream synthesis review certifies only the findings it uses, not the whole standalone artifact.

After writing or revising `outputs/code_quality_review.md`, register the
artifact through the current `work/review_role_plan.json` preset when available,
usually with `scripts/register-review-artifact <case-id> <round-id>
outputs/code_quality_review.md --role code_quality`, including source refs,
checks, limitations, and whether downstream synthesis uses the findings. Then
run `scripts/init-review-manifest --run-checks <case-id> [round-id]` and record
whether the artifact is standalone final evidence or only covered by a
downstream synthesis review. Before relying on it, run
`scripts/check-review-manifest --require-complete <case-id> [round-id]`.

Code-bearing workflow role packets must include the expected output path, this
artifact skeleton, registration preset, and the validator command
`scripts/check-code-quality-review --require-synthesis-handoff <case-id>
[round-id]`. If the packet or `work/review_role_plan.json` omits that contract,
ask the parent session to regenerate the round plan before writing final
evidence. For profile terminology boundaries, use
`docs/agent-profile-matrix.md`.

## Agent Final Response Contract

When acting as a workflow agent, write full evidence content to the owned round
file and keep the chat final response compact. Do not paste full Markdown
artifacts that are already on disk.

Use the default handoff shape in `docs/agent-scheduling.md#subagent-handoffs`,
plus any role-specific validation status, owned output paths, and limitations
that affect parent verification.

## Model And Reasoning

Use the strongest available model with high reasoning effort for this semantic
workflow. In the current repo-local Codex profile this role is pinned to
`gpt-5.5` with `model_reasoning_effort = "xhigh"`. Packet prompts generated for
this skill must carry the same requirement. Do not downshift to Spark or another
low-cost model for the first or only pass over implementation design,
maintainability, runtime risk, reviewer-confidence findings, or Omen-informed
interpretation. Mechanical helper summaries may use cheaper models only when
validator-backed and consumed by a high-reasoning semantic pass.

## Output

Write `outputs/code_quality_review.md` when used as a standalone artifact:

```markdown
# Internal Code Quality Review

## Rozsah kontroly

## Technicky prehled implementace

## Silne technicke stranky

## Hlavni technicka rizika

| Priorita | Oblast | Evidence v kodu | Dopad | Doporuceni |
|---|---|---|---|---|

## Architektura a modularita

## Runtime, validace a chybove stavy

## Testy, smoke testy a reprodukovatelnost

## README, build a vyvojarska dokumentace

## Komentare, citelnost a udrzovatelnost

## Review Status

## Synthesis Handoff

- Workflow/audience:
- Use in synthesis:
- Do not overstate:
- P0/P1 anchors:
- Limitations/manual checks:
- Calibration:
- Supervisor action / opponent impact:

## Rucni kontroly
```

This standalone artifact is internal/operator evidence, not student-facing output by default. For supervisor feedback, summarize only actionable, phase-appropriate findings in `outputs/feedback_student.md`. For opponent materials, use the review as internal evidence for realization quality, reproducibility, risk calibration, and fair defense questions.
