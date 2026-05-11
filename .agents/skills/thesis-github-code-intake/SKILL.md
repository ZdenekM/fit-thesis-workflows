---
name: thesis-github-code-intake
description: Read-only GitHub repository and pull-request intake for BP/DP code evidence, including upstream PR contribution mode, frozen metadata/diff/comment/check snapshots, and handoff to code consistency and code quality review.
---

# Thesis GitHub Code Intake

Command routing: treat `scripts/<tool>` examples below as logical workflow
command names. On Windows, use the packaged
`dist\workflow-tools\bin\<tool>.cmd` or `.ps1` launcher from `README.md`; do
not run or click extensionless `scripts/<tool>` files.

Use this skill when a thesis round provides GitHub repository URLs, branch/tag
or commit references, pull request URLs, fork/upstream contribution context, or
when the student has no standalone repository and their code contribution lives
in one or more upstream PRs.

This skill is intake evidence, not a final code-quality judgment. It prepares
local evidence frozen at import time and a scoped code workspace for
`thesis-code-consistency` and `thesis-code-quality-review`. GitHub itself is a
live source; if the helper reads metadata, diffs, comments, checks, and checkout
state through separate commands, keep possible same-import drift as a caveat
unless a pinned SHA or submitted archive anchors the review.

## Inputs

Use the active round unless the user specifies another:

```text
cases/<case-id>/case.md
cases/<case-id>/rounds/<round-id>/
  notes/
  inputs/
  work/
  outputs/
```

Typical user-provided inputs:

- GitHub PR URL: `https://github.com/<owner>/<repo>/pull/<number>`
- upstream repository and student GitHub login for PR discovery,
- standalone repository URL plus branch/tag/commit,
- expected thesis-relevant scope from the supervisor/student,
- submitted code archive or `CONTRIBUTIONS.md`/`README-THESIS.md`, if available.

## Process

1. Stay read-only. Do not comment on PRs, request reviews, push, merge, close,
   label, trigger workflows, or otherwise mutate GitHub state unless the user
   explicitly asks outside the thesis-review workflow.
2. If the task will feed sendable supervisor feedback, opponent materials, or
   final standalone evidence, require explicitly authorized agents according to
   the main repo workflow.
3. Resolve the case and round. For supervisor feedback, run
   `scripts/check-supervisor-ready <case-id> [round-id]`; for opponent work, run
   `scripts/check-round-ready <case-id> [round-id]`.
4. If both a submitted code archive and GitHub source are available, treat the
   submitted archive as authoritative unless case/round notes explicitly declare
   GitHub as the submission source. If the two sources were not compared, record
   that limitation before making code-review findings.
5. Prefer structured GitHub MCP/App reads when available in the current agent
   session. Use `gh` CLI as the deterministic export mechanism and `git` only
   for local checkout/fetch inside the ignored round workspace.
6. For PR-based work, import each known PR URL:

   ```bash
   scripts/import-github-code <case-id> [round-id] \
     --pr-url https://github.com/<owner>/<repo>/pull/<number> \
     --student-login <login> \
     --expected-scope "<short scope>"
   ```

7. If only the upstream repo and student login are known, first discover PRs:

   ```bash
   scripts/import-github-code <case-id> [round-id] \
     --discover-prs <owner>/<repo> \
     --author <login>
   ```

8. For standalone GitHub repositories, import the repository metadata and
   checkout:

   ```bash
   scripts/import-github-code <case-id> [round-id] \
     --repo https://github.com/<owner>/<repo> \
     --ref <branch-or-tag>
   ```

   Prefer a pinned commit SHA for final/opponent review. If a live branch is
   imported, keep that reproducibility caveat visible.
9. Treat `outputs/github_code_intake.md` as the frozen operator evidence. It
   records imported URLs, PR/repo metadata, evidence files, checkout workspace,
   changed-file scope, and limitations.
10. For PR contribution mode, evaluate only student-owned contribution evidence:
   PR diffs, changed files, commits, tests/docs added by the PR, review
   discussion, CI state, and declared scope. Upstream code is context and
   baseline, not automatically the student's implementation.
11. Feed the scoped evidence to:
   - `thesis-code-consistency` for thesis text versus GitHub/code evidence,
   - `thesis-code-quality-review` for implementation/design risks in the
     student-owned contribution.
12. Do not run untrusted code, install dependencies, execute postinstall hooks,
   run Docker Compose, or use host secrets from the student checkout by default.
   Static inspection, git metadata, diffs, README/config/test inventory, and CI
   metadata are safe default actions.

## Model And Reasoning

Use the strongest available model with high reasoning effort when this intake
will feed supervisor feedback, opponent materials, code consistency, code
quality, or final standalone evidence. In the current Codex setup, use
`gpt-5.5` with `xhigh` reasoning when that choice is exposed. Packet prompts
generated for this skill must carry the same requirement. Do not downshift to
Spark or another low-cost model for the first or only pass over PR scope,
student contribution boundaries, GitHub-vs-archive authority, review/CI
limitations, or synthesis implications. Mechanical helper summaries may use
cheaper models only when validator-backed and consumed by a high-reasoning
semantic pass.

## Output

The helper writes ignored case-local evidence:

```text
inputs/github/
  code-manifest.generated.yml
  repos/<owner>__<repo>/
  prs/<owner>__<repo>__pr-<number>/
work/github-intake/
  changed-files.tsv
  contribution-map.md
  *.inventory.md
work/code/
  <owner>__<repo>__pr-<number>/
  <owner>__<repo>__standalone/
outputs/github_code_intake.md
```

`outputs/github_code_intake.md` is internal/operator evidence. Student-facing
feedback should include only selected, phase-appropriate action items such as:
"The thesis should clearly separate existing upstream functionality from the
changes introduced in PR #N" or "The PR has unresolved review/CI evidence that
needs to be addressed or explained before final submission."

Do not paste raw PR comment bodies, reviewer usernames, private PR URLs, branch
names, CI links, review-thread details, manifest hashes, local workspace paths,
or generated-draft state into student-facing or opponent-facing prose. Keep
those details in internal evidence; summarize review discussion as issue
patterns and cite the internal evidence privately.

## Review Loop

When `outputs/github_code_intake.md` is used as final standalone evidence, it is
draft evidence until a different explicitly authorized reviewer agent checks it.
A downstream synthesis review certifies only the findings it uses, not the whole
standalone artifact.

After writing or revising `outputs/github_code_intake.md`, run
`scripts/init-review-manifest --run-checks <case-id> [round-id]` and record whether the intake
is standalone final evidence or only covered by downstream synthesis. Before
relying on it, run `scripts/check-review-manifest --require-complete <case-id>
[round-id]`.

## Agent Final Response Contract

When acting as a workflow agent, write full intake evidence to the owned round
files and keep the chat final response compact. Do not paste full Markdown
artifacts that are already on disk.

Return only:

- files written or changed;
- top 3-5 findings, verdicts, or risks;
- commands/checks run;
- explicit limitations;
- whether expected output validation passed.

The main session must verify file claims with expected-output checks before
relying on them.

## Limits Of V1

- The helper is `gh`/`git` based; MCP/App reads are a workflow preference for
  agents, not a deterministic script dependency.
- V1 writes `outputs/github_code_intake.md`; a separate
  `outputs/pr_contribution_review.md` remains deferred.
- Multiple PR relation graphs, precise resolved/unresolved review-thread state,
  archive-vs-GitHub diffing, and automatic large-PR slicing are TODO items.
