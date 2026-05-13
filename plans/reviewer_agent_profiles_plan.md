# Codex Agent Role Profiles Plan

Status: planned
Created: 2026-05-13

## Goal

Make the workflow's required review roles directly spawnable, discoverable, and
validated through `.codex/agents/*` profiles and `.codex/config.toml`, so
role-split thesis workflows do not depend on ad hoc default-agent prompts for
specialized evidence and final-review roles.

## Recommendation

Add dedicated Codex agent role profiles for missing semantic review roles.

That is better than only documenting "use default agent with this skill" because
these roles affect evidence quality, grade/report calibration, privacy
boundaries, and final/sendable wording. A Codex agent role profile pins:

- model and reasoning defaults,
- read-only versus workspace-write expectations,
- role ownership and output contract,
- concise constraints that survive prompt variation,
- a stable agent id that can be recorded in `work/review_manifest.json` and
  `work/agent_coverage.json`.

The risk is profile sprawl. Avoid that by adding profiles only for roles that
own a distinct artifact, distinct evidence boundary, or distinct final-review
boundary. Do not create one profile per temporary wave or per case-specific
variant.

Terminology:

- Use "Codex agent role profile" or "agent profile" for `.codex/agents/*`.
- Reserve "reviewer profile" for case/operator preference files selected by the
  `Reviewer profile:` field in `case.md`.
- Documentation and tests added by this plan must keep those two profile concepts
  separate.

## Audit Base

This plan follows `docs/pipeline-housekeeping-audit.md`, especially:

- P1: specialist Codex profiles do not cover all required roles.
- P1: session-start hook mentions only a subset of today's skill surface.
- P2: missing mechanical guard for instruction/profile drift.

Current state:

- Existing profiles:
  - `.codex/agents/thesis-text-reviewer.toml`
  - `.codex/agents/thesis-code-consistency-reviewer.toml`
  - `.codex/agents/thesis-code-quality-reviewer.toml`
  - `.codex/agents/thesis-quantitative-claims-reviewer.toml`
  - `.codex/agents/thesis-evidence-calibrator.toml`
- Existing `.codex/config.toml` exposes only those five role agents.
- `AGENTS.md` and README route more roles than the tracked Codex profile set:
  GitHub intake, revision diff, figure/media, literature/citation,
  typography/formal, Theses.cz similarity, supervisor feedback review,
  supervisor report review, opponent materials review, and opponent report
  review.

Commands already run during audit:

```bash
sed -n '1,260p' docs/pipeline-housekeeping-audit.md
ls -1 .codex/agents
sed -n '1,140p' .codex/config.toml
git status --short --untracked-files=all
```

Known worktree constraint:

- `TODO.md` is already modified outside this plan.
- `docs/pipeline-housekeeping-audit.md` is new audit output and should remain
  separate from profile implementation commits unless the user explicitly wants
  one combined housekeeping commit.

## Scope

In scope:

- Add a small machine-checkable profile registry that is the source of truth for
  skill-to-agent routing, sandbox mode, owned outputs, standalone-review
  requirements, and deliberate parent-owned/no-profile decisions.
- Add missing `.codex/agents/*.toml` profiles for durable workflow roles.
- Normalize existing `.codex/agents/*.toml` profiles so old and new profiles obey
  the same concise contract.
- Register those profiles in `.codex/config.toml`.
- Add or update documentation mapping skills to Codex profiles.
- Update the session-start hook so it does not preserve a stale short list of
  roles.
- Add deterministic tests or checks that catch profile/config/documentation drift.
- Keep all profile instructions case-neutral and free of private case data.

Out of scope:

- Changing generated thesis-review artifacts under `cases/`.
- Changing workflow semantics, role coverage rules, or review-manifest schemas.
- Weakening DEEP mode, independent review, or high-reasoning semantic defaults.
- Adding lower-cost models for semantic roles.
- Creating profiles for case-specific reviewer preferences or historical student
  data.
- Refactoring duplicate validation code found by `jscpd`; that belongs in a
  separate validation-helper refactor plan.

## Target Role Set

The implementation should be exhaustive over repo-local thesis skills, but not
every skill needs its own spawned role profile. The matrix must use one of these
statuses for every `.agents/skills/*/SKILL.md` workflow skill:

- `profile`: a stable `.codex/agents/*` profile exists or will be added.
- `parent-owned`: the parent/main agent owns orchestration or synthesis, with
  required reviewer profiles named separately.
- `deferred`: no profile is added in this plan, with an explicit case-neutral
  rationale.

Generation/synthesis skills deliberately remain parent-owned in this plan:

- `thesis-supervisor-feedback`
  - parent-owned draft/synthesis workflow;
  - independent review profile: `thesis_supervisor_feedback_reviewer`.
- `thesis-supervisor-report`
  - parent-owned trace/draft/confirmation workflow;
  - independent review profile: `thesis_supervisor_report_reviewer`.
- `thesis-opponent-materials`
  - parent-owned synthesis workflow;
  - independent review profile: `thesis_opponent_materials_reviewer`.
- `historical-opponent-calibration`
  - deferred; private calibration workflow, no durable spawned role until repeat
    use proves a stable output boundary.
- `historical-supervisor-report-calibration`
  - deferred; private calibration workflow, no durable spawned role until repeat
    use proves a stable output boundary.

Add profiles for roles with distinct evidence or final-review ownership:

- `thesis_github_code_intake_reviewer`
  - skill: `thesis-github-code-intake`
  - writes/imports ignored round evidence when authorized;
  - must keep PR/upstream scope read-only and student-owned contribution scoped.
- `thesis_revision_diff_reviewer`
  - skill: `thesis-revision-diff`
  - compares rounds and prior feedback without repeating old feedback
    mechanically.
- `thesis_figure_media_reviewer`
  - skill: `thesis-figure-media-review`
  - owns visual inventory and visual/claim-alignment boundaries.
- `thesis_literature_citation_reviewer`
  - skill: `thesis-literature-citation-review`
  - owns source availability, citation support, and literature relevance.
- `thesis_typography_formal_reviewer`
  - skill: `thesis-typography-formal-review`
  - owns late-stage typography/formal presentation evidence and language
    calibration.
- `thesis_theses_similarity_reviewer`
  - skill: `thesis-theses-similarity-review`
  - owns Theses.cz similarity interpretation and no-plagiarism-overclaim
    boundary.
- `thesis_supervisor_feedback_reviewer`
  - skill: `thesis-supervisor-feedback-review`
  - owns final student-facing feedback review and `outputs/feedback_student.md`.
- `thesis_supervisor_report_reviewer`
  - skill: `thesis-supervisor-report-review`
  - owns formal supervisor-report review before confirmation/IS use.
- `thesis_opponent_materials_reviewer`
  - skill: `thesis-opponent-materials-review`
  - owns reviewed opponent materials and report trace readiness.
- `thesis_opponent_report_reviewer`
  - skill: `thesis-opponent-report-review`
  - owns review of a human or generated opponent-report draft.

Keep existing profiles:

- `thesis_text_reviewer` for text structure and assignment coverage.
- `thesis_code_consistency_reviewer` for thesis/code consistency.
- `thesis_code_quality_reviewer` for implementation quality/design.
- `thesis_quantitative_claims_reviewer` for quantitative/result claims.
- `thesis_evidence_calibrator` for generic stress-testing and standalone
  evidence calibration where no more specific final-review role applies.

Do not add a separate "synthesis agent" profile in this plan. Synthesis is
workflow-specific and should remain controlled by the relevant skill and parent
agent unless repeated use proves a stable synthesis profile would reduce
confusion.

## Role Registry Contract

Create a single structured source of truth, preferably
`src/thesis_review_workflow/agent_profiles.py`, before adding the full profile
set. The registry should be easy to test and should feed documentation rather
than being duplicated by hand.

Each registry row should include:

- skill id, or a role source for profile-only roles without a repo-local skill;
- profile id, or `parent-owned`/`deferred` status with rationale;
- role kind: generator, evidence producer, standalone evidence reviewer, final
  reviewer, calibrator, or parent orchestration;
- sandbox mode;
- owned outputs and allowed writes, using case-relative paths such as
  `outputs/...`, `work/...`, and `work/reviews/*.json`;
- standalone review profile when the role can produce evidence that may be used
  as final standalone evidence;
- whether downstream synthesis review can cover the artifact instead of a
  standalone evidence review;
- required validator or closeout command names.

Concrete initial sandbox and ownership decisions:

| Profile id | Skill or source | Sandbox | Owned outputs and allowed writes |
| --- | --- | --- | --- |
| `thesis_text_reviewer` | `AGENTS.md` text/assignment role; no repo-local skill | `read-only` | none; handoff only |
| `thesis_code_consistency_reviewer` | `thesis-code-consistency` | `workspace-write` | `outputs/code_consistency.md`; review metadata only when explicitly asked to finalize standalone evidence |
| `thesis_code_quality_reviewer` | `thesis-code-quality-review` | `workspace-write` | `outputs/code_quality_review.md`; review metadata only when explicitly asked to finalize standalone evidence |
| `thesis_quantitative_claims_reviewer` | `thesis-quantitative-claims-review` | `workspace-write` | `work/quantitative_claims.json`; no tracked workflow edits |
| `thesis_github_code_intake_reviewer` | `thesis-github-code-intake` | `workspace-write` | ignored round GitHub snapshot/workspace evidence and `outputs/github_code_intake.md`; no upstream writes |
| `thesis_revision_diff_reviewer` | `thesis-revision-diff` | `workspace-write` | `outputs/revision_diff.md` |
| `thesis_figure_media_reviewer` | `thesis-figure-media-review` | `workspace-write` | `work/figure_media/visual_inventory.jsonl`, `outputs/figure_media_review.md` |
| `thesis_literature_citation_reviewer` | `thesis-literature-citation-review` | `workspace-write` | `outputs/literature_citation_review.md` |
| `thesis_typography_formal_reviewer` | `thesis-typography-formal-review` | `workspace-write` | `outputs/typography_formal_review.md` |
| `thesis_theses_similarity_reviewer` | `thesis-theses-similarity-review` | `workspace-write` | `work/theses_similarity/*.json`, `work/theses_similarity/review_draft.md`, `outputs/theses_similarity_review.md`, `work/reviews/theses_similarity_review.json` when reviewing standalone similarity evidence |
| `thesis_supervisor_feedback_reviewer` | `thesis-supervisor-feedback-review` | `workspace-write` | `outputs/feedback_student.md`, `work/reviews/supervisor_feedback_review.json`, manifest/coverage updates required by the skill |
| `thesis_supervisor_report_reviewer` | `thesis-supervisor-report-review` | `workspace-write` | `outputs/vedouci_posudek_revidovany.md`, `work/reviews/supervisor_report_review.json`, manifest/coverage updates required by the skill |
| `thesis_opponent_materials_reviewer` | `thesis-opponent-materials-review` | `workspace-write` | `outputs/oponent_podklady_revidovane.md`, `work/opponent_report_trace.json`, `work/reviews/opponent_materials_review.json`, manifest/coverage updates required by the skill |
| `thesis_opponent_report_reviewer` | `thesis-opponent-report-review` | `workspace-write` | `outputs/feedback_k_posudku.md`, `work/reviews/opponent_report_review.json`, manifest/coverage updates required by the skill |
| `thesis_evidence_calibrator` | `AGENTS.md` standalone evidence calibration; no repo-local skill | `read-only` by default | no direct writes; reviewer verdict in chat unless a workflow explicitly routes it to a structured approval record |

Standalone evidence separation rule:

- A profile that produces a standalone evidence artifact must not be the profile
  that marks the same artifact reviewed for final standalone use.
- The registry/tests must name the independent reviewer profile, usually
  `thesis_evidence_calibrator` unless a more specific final-review profile owns
  the reviewed output.
- If a downstream supervisor/opponent synthesis review is allowed to cover a
  finding instead of marking the whole evidence artifact final, the registry must
  say so explicitly.

## Profile Contract

Each new profile should:

- use `model = "gpt-5.5"` and `model_reasoning_effort = "xhigh"`;
- use `approval_policy = "never"`;
- use `sandbox_mode = "workspace-write"` only when the role is expected to write
  ignored round artifacts, reviewed outputs, approval records, traces, or
  manifest/coverage records required by the owning skill;
- use `sandbox_mode = "read-only"` only for roles that must not write files in
  normal use;
- say explicitly that private case data stays under ignored `cases/`;
- say not to edit tracked workflow files;
- point to the owning repo-local skill by name when one exists, or state the
  role source and why no dedicated skill owns the profile;
- state the role-owned output paths or the reason no path is owned;
- return concise handoff summaries, not pasted full artifacts.

Existing profiles should be normalized to this contract in the same rollout; do
not let new tests apply only to newly added profiles while old tracked profiles
keep weaker instructions.

## Slices

### Slice 1 - Structured Role Registry And Profile Taxonomy

- Status: planned
- Proposed commit message: `feat(workflow): add thesis agent profile registry`
- Expected paths:
  - `src/thesis_review_workflow/agent_profiles.py`
  - `tests/test_agent_profile_contracts.py` or
    `tests/test_workflow_python_contracts.py`
  - `docs/agent-scheduling.md`
  - optionally `docs/agent-profile-matrix.md` if the table would make
    `agent-scheduling.md` too large
  - `.codex/hooks/session_start_context.py`
- Tasks:
  - Add the machine-checkable registry described above.
  - Add initial tests that parse the registry and assert every repo-local thesis
    skill is represented by `profile`, `parent-owned`, or `deferred`.
  - Add a generated or manually synchronized documentation matrix mapping each
    repo-local thesis skill to: profile id/status, expected sandbox mode, owned
    output, allowed writes, review separation, and whether the role is generator,
    evidence producer, evidence reviewer, final reviewer, or calibrator.
  - Record that missing durable roles should get explicit profiles rather than
    default-agent prompts.
  - Update the session-start hook to avoid the stale narrow role list. Prefer a
    short reminder to read `AGENTS.md` and the profile matrix.
  - Keep `AGENTS.md` short; do not paste the full matrix there.
- Verification:
  - `pants fmt src/thesis_review_workflow:: tests:: .codex/hooks::`
  - `pants check src/thesis_review_workflow:: tests:: .codex/hooks::`
  - targeted profile-registry tests
  - `git diff --check`
  - `scripts/check-private`
  - `scripts/check-scripts`

### Slice 2 - Add Profile Contract Tests And Normalize Existing Profiles

- Status: planned
- Proposed commit message: `test(workflow): validate thesis agent profile contracts`
- Expected paths:
  - `.codex/config.toml`
  - `.codex/agents/thesis-text-reviewer.toml`
  - `.codex/agents/thesis-code-consistency-reviewer.toml`
  - `.codex/agents/thesis-code-quality-reviewer.toml`
  - `.codex/agents/thesis-quantitative-claims-reviewer.toml`
  - `.codex/agents/thesis-evidence-calibrator.toml`
  - `tests/test_agent_profile_contracts.py` or
    `tests/test_workflow_python_contracts.py`
- Tasks:
  - Replace the current hardcoded five-profile smoke with registry-driven
    profile checks.
  - Normalize existing profile instructions so they name the owning skill,
    private-case boundary, tracked-file boundary, sandbox/write contract, and
    concise handoff contract.
  - Assert every profile in the registry has a `.codex/config.toml` entry, an
    existing profile file, `gpt-5.5`, `xhigh`, `approval_policy = "never"`, an
    allowed sandbox mode, and owning skill/status or role-source text in
    `developer_instructions`.
  - Assert workspace-write profiles include case-relative allowed writes, and
    read-only profiles explicitly say they do not write files in normal use.
  - Assert producer and standalone reviewer profiles differ when standalone
    final evidence is allowed.
- Verification:
  - `pants fmt src/thesis_review_workflow:: tests::`
  - `pants check src/thesis_review_workflow:: tests::`
  - targeted profile-contract tests
  - `git diff --check`
  - `scripts/check-private`
  - `scripts/check-scripts`

### Slice 3 - Add Missing Profile Files And Config Entries

- Status: planned
- Proposed commit message: `feat(workflow): add thesis reviewer agent profiles`
- Expected paths:
  - `.codex/config.toml`
  - `.codex/agents/thesis-github-code-intake-reviewer.toml`
  - `.codex/agents/thesis-revision-diff-reviewer.toml`
  - `.codex/agents/thesis-figure-media-reviewer.toml`
  - `.codex/agents/thesis-literature-citation-reviewer.toml`
  - `.codex/agents/thesis-typography-formal-reviewer.toml`
  - `.codex/agents/thesis-theses-similarity-reviewer.toml`
  - `.codex/agents/thesis-supervisor-feedback-reviewer.toml`
  - `.codex/agents/thesis-supervisor-report-reviewer.toml`
  - `.codex/agents/thesis-opponent-materials-reviewer.toml`
  - `.codex/agents/thesis-opponent-report-reviewer.toml`
- Tasks:
  - Add one profile per target role.
  - Register each profile under `[agents.<id>]` in `.codex/config.toml`.
  - Keep profile text concise and skill-referenced; do not duplicate full
    workflow procedures from skills.
  - Use workspace-write only where the role writes ignored round artifacts or
    reviewed outputs, approval records, traces, or manifest/coverage records.
  - Ensure profile ids use stable snake_case names matching manifest-friendly
    role names.
- Verification:
  - parse `.codex/config.toml` with Python `tomllib`;
  - verify every config `config_file` exists;
  - verify all profile files are UTF-8 text;
  - targeted profile-contract tests;
  - `git diff --check`
  - `scripts/check-private`
  - `scripts/check-scripts`

### Slice 4 - Add Profile Drift Checks

- Status: planned
- Proposed commit message: `test(workflow): validate thesis agent profile coverage`
- Expected paths:
  - `tests/test_agent_profile_contracts.py` or
    `tests/test_workflow_python_contracts.py`
  - optionally `src/thesis_review_workflow/agent_profiles.py` if a tiny shared
    parser avoids duplicating TOML logic in tests
- Tasks:
  - Add tests that assert every role in the profile matrix has:
    - a `.codex/config.toml` entry,
    - an existing profile file,
    - `gpt-5.5`,
    - `xhigh`,
    - `approval_policy = "never"`,
    - allowed sandbox mode,
    - owning skill name or role-source rationale in `developer_instructions`.
  - Assert that config entries do not point to missing files.
  - Assert no profile instructs agents to edit tracked workflow files or place
    private case artifacts outside `cases/`.
  - Assert docs/profile matrix entries match the structured registry.
  - Assert the session-start hook does not hardcode a stale subset of skills
    when the registry grows.
  - Keep tests deterministic and independent of private case data.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests:: .codex/hooks::`
  - `pants check src/thesis_review_workflow:: tests:: .codex/hooks::`
  - targeted pytest for the new profile tests
  - `git diff --check`
  - `scripts/check-private`
  - `scripts/check-scripts`

### Slice 5 - Documentation And Closeout

- Status: planned
- Proposed commit message: `docs(workflow): document agent profile routing`
- Expected paths:
  - `README.md`
  - `docs/agent-scheduling.md` or `docs/agent-profile-matrix.md`
  - `plans/reviewer_agent_profiles_plan.md`
- Tasks:
  - Update README's agent-maintenance section only enough to point at the profile
    matrix; keep README chat-first.
  - Record any role deliberately left on an existing profile and why.
  - Record parent-owned and deferred skills explicitly so "every skill has a
    routing decision" does not mean "every skill has a spawned profile".
  - Run full lightweight closeout.
  - Decide whether this plan should stay active for follow-up or be archived.
- Verification:
  - `pants fmt src/thesis_review_workflow:: tests:: .codex/hooks::`
  - `pants lint src/thesis_review_workflow:: tests:: .codex/hooks::`
  - `pants check src/thesis_review_workflow:: tests:: .codex/hooks::`
  - targeted profile-contract tests
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

## Progress

- 2026-05-13: Plan created from `docs/pipeline-housekeeping-audit.md`. Decision:
  add explicit profiles for durable missing semantic roles, with profile-sprawl
  controlled by the target role set above.
- 2026-05-13: Agent review tightened the plan around terminology, an exhaustive
  machine-checkable skill/profile registry, existing-profile normalization,
  exact workspace-write boundaries, and producer/reviewer separation for
  standalone evidence.

## Decision Log

- Explicit profiles are preferred for missing durable review roles because they
  pin model/reasoning/sandbox/ownership and make manifest role attribution more
  repeatable.
- The profile set should follow stable workflow roles, not every temporary wave
  or case-specific prompt.
- Existing `thesis_evidence_calibrator` stays useful for generic stress-testing;
  it should not be the only profile for roles with distinct output contracts such
  as similarity review or supervisor-report review.
- Keep operational procedure in skills. Profiles should be short routing and
  role-contract files, not another copy of the skill body.
- Do not touch real case artifacts while implementing this plan.
- Keep "reviewer profile" terminology reserved for case preference profiles; use
  "Codex agent role profile" for `.codex/agents/*`.
- Use the structured registry as the source of truth; docs and tests should
  consume or check it rather than maintaining independent role lists.
- Standalone evidence producer and reviewer roles must be different unless a
  typed limitation records why the artifact is not being treated as final
  standalone evidence.

## Final Audit

Not started. Close with:

```bash
pants fmt ::
pants lint src/thesis_review_workflow:: tests:: .codex/hooks::
pants check src/thesis_review_workflow:: tests:: .codex/hooks::
pants test tests/test_agent_profile_contracts.py
scripts/check-private
scripts/check-scripts
git diff --check
```

If the test file is merged into an existing suite, replace the targeted pytest
command with the final actual target before archiving this plan.
