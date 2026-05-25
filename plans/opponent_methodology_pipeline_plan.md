# Opponent Methodology Pipeline Plan

Status: planned
Created: 2026-05-25

## Goal

Improve opponent-materials and opponent-report quality by adding a generalized
methodology/evaluation evidence layer and an earlier operator challenge intake,
without turning recent case lessons into a pile of brittle one-off rules.

The target outcome is a pipeline that can ask and answer broader review
questions such as:

- What kind of evaluation did the thesis actually run?
- What claims does that evaluation support, and at what strength?
- What evidence would normally be expected for that method and claim type?
- What is missing, unverifiable, or only suitable for a defense question?
- Which concerns belong in the public report, private student comment, internal
  manual checklist, or no output at all?

The plan must generalize findings into evidence classes, review prompts,
structured artifacts, and optional source acquisition. It must not encode
case-specific facts, concrete metric values, domain names, datasets, or narrow
lexical triggers as workflow behavior.

## Audit Base

Current state:

- Opponent workflows already have strong evidence plumbing: readiness gates,
  `review-round-start`, role packets, role plans, review manifests, approval
  records, review deltas, `work/opponent_report_trace.json`, canonical report
  drafting, clean export, and independent report review.
- `thesis-quantitative-claims-review` covers material quantitative,
  experiment, metric, performance, scale, count, and result claims in
  `work/quantitative_claims.json`.
- `thesis-literature-citation-review` can acquire targeted public source
  evidence for key or suspicious citations and write
  `work/literature/source_acquisition.json`.
- `docs/opponent-review-workflow.md#report-quality-controls` already names
  many report controls, but current recurring methodology issues still tend to
  surface through late operator notes, review deltas, or report wording passes.
- The current local reviewer profile already contains many style and calibration
  preferences derived from recent report iterations. Those preferences are
  useful, but they should not become deterministic semantic rules.
- `TODO.md` already tracks visual/media evidence-mode work, video/demo intake,
  and graph/table quality checks. Historical opponent-report calibration is now
  implemented and archived separately; this plan promotes the evidence-mode
  matrix into the methodology/report-readiness contract, while broader
  media-specific review remains owned by the figure/media workflow.
- `plans/review_manifest_closeout_repair_plan.md` owns general manifest,
  approval, stale hash, operation-log, and closeout-recovery mechanics. This
  plan should integrate with those mechanics, not duplicate them.
- Existing opponent-facing boundary rules, tracked/local reviewer profiles,
  `thesis-opponent-report-review`, `export-opponent-report`, and
  `check-opponent-report --mode clean` already own clean public report hygiene:
  no internal paths, hashes, checker mechanics, raw PR/GitHub metadata, private
  URLs, generated-draft state, or no-concern similarity details. This plan must
  consume and extend those gates only where methodology evidence introduces a
  new typed dependency; it should not reimplement a parallel public-prose leak
  checker.

Plan-creation checks and context reads:

```bash
git status --short --untracked-files=all
sed -n '1,220p' plans/README.md
find plans -maxdepth 1 -type f -name '*plan.md' -print | sort
sed -n '180,260p' docs/opponent-review-workflow.md
sed -n '90,170p' profiles/default.md
sed -n '114,260p' profiles/local/default.md
sed -n '1,130p' TODO.md
sed -n '1,180p' .agents/skills/thesis-quantitative-claims-review/SKILL.md
sed -n '1,160p' .agents/skills/thesis-literature-citation-review/SKILL.md
rg -n "quantitative_claims|evaluation|experiment|methodology|evidence_requirements|assignment_coverage|report_quality|opponent_report_trace|schema_version" src/thesis_review_workflow -g '*.py'
```

Serena preflight:

- `mcp__serena__.get_current_config` confirmed active project
  `diplomky_v2`, language backend LSP, and editing mode.

Observed private-case pattern, recorded here only case-neutrally:

- Late operator notes often added evidence challenges or contribution-boundary
  calibration after reviewed materials already existed.
- Some issues were not really "metric" issues; they were about method fit,
  claim strength, participant/sample traceability, study protocol, benchmark
  construction, source of domain requirements, comparison baseline, or
  reproducibility of evaluation.
- Operator calibration often concerned the report stance rather than a single
  missing fact: grade strictness, assignment interpretation, contribution
  boundary, public/private wording, defense questions, and whether late evidence
  should alter the report trace.
- Media, checker, figure, and video signals often failed at the evidence-mode
  level: an artifact may be inventoried or sampled without being fully reviewed,
  operator-accepted, or strong enough to support a report claim.
- Runtime, build, test, and log evidence has the same problem: static code
  inspection, syntax checks, README presence, APK/archive presence, smoke runs,
  full runtime execution, benchmark replay, and submitted logs are different
  evidence states. The report must not collapse missing runtime evidence into a
  claim of non-functionality, nor treat artifact existence as full verification.
- Several cases needed source-support triage: background literature may be
  relevant while still failing to support a concrete domain, state-of-practice,
  metric, dataset, tool-quality, or build-vs-adapt claim.
- Final report review repeatedly produced a practical IS handoff checklist:
  exact field values, grade/points, public/private separation, defense-question
  count, and absence of internal paths, hashes, workflow details, Theses.cz
  no-concern evidence, or unsupported GitHub/CI/runtime claims.
- Several reviewed artifacts kept intermediate-state wording after later
  approval or submitted-report capture. Final readiness needs a terminal state
  that supersedes stale reviewer TODO text rather than asking the operator to
  infer which intermediate note is current.
- Operation logs, approval records, submitted-report records, and machine-readable
  trace fields need structural validation because later workflow decisions rely
  on them as provenance, not just as narrative notes.
- Style-only report deltas repeatedly replaced internal workflow jargon with
  plain, report-facing wording.
- Operator feedback confirms that a low-level rule such as "small n should use
  exact counts" is too narrow. The durable rule is broader: evaluation reporting
  should be judged against the chosen method, claim strength, available evidence,
  thesis level, assignment, and field norms.

Constraints:

- Keep real thesis/case data in ignored `cases/`; tracked plans, docs, tests, and
  fixtures must be case-neutral and synthetic.
- Do not add brittle free-text heuristics over thesis/report prose. Semantic
  interpretation belongs to authorized agents or human-authored structured
  artifacts.
- Deterministic helpers may validate schemas, hashes, paths, allowed enums,
  missing refs, stale state, privacy leaks, and whether required structured
  artifacts exist. They must not decide whether a user study, benchmark, or
  experiment is good by keyword matching.
- Windows remains supported. New operator-facing helpers need Python/Pants/PEX
  command surfaces and generated `.cmd`/`.ps1` launchers.
- Run Pants commands sequentially.
- Preserve existing role separation and independent review gates.
- Historical/personal calibration is a follow-up, not part of the core
  methodology pipeline slices below.

## Scope

In scope:

- A case-neutral methodology/evaluation evidence taxonomy that covers
  qualitative, quantitative, mixed-method, benchmark, simulation, case-study,
  expert-review, user-study, field-trial, and artifact-demonstration evidence.
- A structured methodology artifact, tentatively
  `work/methodology_evidence.json`, produced by an authorized semantic reviewer
  or human and validated by a deterministic checker.
- Opponent packet and role-plan integration so methodology review is scheduled
  when current evidence or operator notes make evaluation methodology material.
  V1 is opponent-first; keep the artifact schema reusable, but defer supervisor
  wiring until the opponent workflow proves the contract.
- Prompt/skill updates that make the reviewer reason from method class and claim
  strength, not from narrow rules. For example, "small n exact counts" becomes
  part of a broader "sampling, traceability, and reporting precision appropriate
  to the method and conclusion" dimension.
- Optional source-acquisition routing: when the reviewer needs methodological
  standards or field-specific norms, it should route targeted lookup through the
  literature/source workflow or ask the operator to approve external lookup.
- Pre-draft operator calibration intake for opponent reports: before report trace
  finalization and `draft-opponent-report`, the pipeline should surface and
  record target grade-strictness posture, contribution-boundary choices,
  assignment-fulfillment interpretation, public/private wording preferences,
  defense questions, and unresolved evidence challenges.
- Material delta gating: unresolved late `material_claim_delta` or
  `evidence_challenge` inputs should block report draft/export until they are
  reflected in `work/report_calibration_basis.json`,
  `work/opponent_report_trace.json`, and independent re-review evidence.
  Bounded style-only deltas remain allowed when they do not change evidence,
  grade, points, IS selections, defense questions, or public criticism.
- Report-trace controls that carry only compact, report-relevant conclusions
  from methodology evidence into the public report, private student comment,
  defense questions, or manual checklist.
- An evidence-mode matrix for video, media, checker, and figure/table signals,
  distinguishing inventoried, sampled, full-reviewed, operator-accepted, and
  claim-supporting evidence states.
- A verification-state matrix for submitted code, runtime/build evidence,
  smoke/full runs, benchmark replay, test logs, generated outputs, and packaged
  artifacts.
- Source-support triage for related work and literature: distinguish background
  relevance, direct support for a concrete claim, assignment-required source
  coverage, domain/state-of-practice grounding, and unsupported or overstated
  use of a citation.
- Final IS handoff controls so the reviewed public/private report can be copied
  without losing exact points, selected IS values, private-comment boundary, or
  report-safe wording.
- First-class terminal states for `ready_for_is`, `submitted_captured`,
  `submitted_delta_blocked`, and `archive_ready`, with methodology/report gates
  feeding those states instead of stopping at clean export.
- Target-level bindings from methodology items to assignment points, FIT IS
  items, public/private/defense/manual targets, grade/points impact, source
  hashes, and selected report trace entries.
- Operator-feedback promotion: after report/material review feedback changes
  wording, tone, grade posture, evidence handling, or workflow behavior, classify
  the lesson as case-only, reviewer-profile preference, workflow docs/templates
  update, or TODO/follow-up, with source hashes where practical.

Out of scope:

- Historical opponent-report calibration implementation. That workflow is
  implemented and archived under
  `plans/archive/historical_opponent_calibration_plan.md`; this plan may consume
  calibration promotion decisions, but must not reimplement profile refresh.
- A generic supervisor-report calibration subsystem.
- A large source database, UI, or ontology of all research methods.
- Automatic judgment from raw free text, raw filenames, or hard-coded keyword
  lists.
- Running submitted student code by default.
- Rewriting existing final case artifacts as part of this maintainer plan.
- Storing real case snippets, metrics, student names, thesis titles, or private
  report text in tracked fixtures or docs.

## Conceptual Contract

### Methodology Evidence Dimensions

The methodology reviewer should classify each material evaluation or
methodology-sensitive claim along broad dimensions:

- `method_family`: qualitative, quantitative, mixed_method, benchmark,
  simulation, case_study, expert_review, user_study, field_trial,
  artifact_demo, static_analysis, literature_based, other.
- `claim_type`: effectiveness, usability, accuracy, performance, robustness,
  scalability, practical_usefulness, domain_fit, requirement_validity,
  problem_framing, stakeholder_input, contribution_boundary, assignment_fit,
  novelty, comparison, reproducibility, other.
- `claim_strength`: descriptive, exploratory, indicative, comparative,
  causal, statistical, deployment_ready, not_clear.
- `evidence_mode`: thesis_text, submitted_data, submitted_code, logs,
  notebooks, figures_tables, video_demo, checker_report, media_asset,
  build_artifact, runtime_log, test_log, benchmark_replay, external_source,
  operator_observation, not_available.
- `evidence_state`: inventoried, sampled, full_reviewed, operator_accepted,
  static_inspected, syntax_checked, smoke_run, full_run, benchmark_replayed,
  claim_supporting, unsupported, not_reviewed, not_applicable.
- `method_fit`: suitable, partially_suitable, weak, unclear, not_verifiable.
- `traceability`: direct, partial, scattered, missing, not_applicable.
- `source_basis`: thesis_internal, submitted_artifact, cited_literature,
  methodological_source, operator_expertise, missing, not_applicable.
- `review_action`: use_in_public_report, private_student_comment,
  defense_question, manual_check, keep_internal, no_action.

These enums are intentionally broad. The reviewer explains the concrete case in
natural language with evidence refs; validators check only shape and refs.

### Pre-Draft Calibration And Delta Gate

Before final report trace approval and before `draft-opponent-report`, the
operator should have a compact calibration intake covering:

- target grade-strictness posture and any point/grade tension;
- contribution-boundary stance;
- assignment-fulfillment interpretation;
- public versus private wording preferences;
- defense questions that should be asked or suppressed;
- unresolved evidence challenges or manual checks.

If late `material_claim_delta` or `evidence_challenge` inputs exist, draft and
export should stop until the changed stance is represented in structured current
evidence, especially `work/report_calibration_basis.json` and
`work/opponent_report_trace.json`, and the affected artifact has independent
re-review. A bounded style-only delta can remain a fast path only when it does
not alter evidence, grade/points, IS selections, defense questions, or public
criticism.

The gate should be shared across `draft-opponent-report`,
`export-opponent-report`, canonical/clean report checks, final report review, and
closeout. A material unresolved input should not be allowed through one command
only to fail later in another command.

### Methodology Checklist Families

The methodology reviewer should systematically inspect these families when they
are material to the thesis claims, assignment, or report wording:

- `problem_framing_and_stakeholders`: whether claimed analysis, stakeholder
  input, domain need, or requirements evidence exists as a visible method or
  source, not just as an assertion.
- `user_study_protocol`: whether user or expert evaluation records tasks,
  protocol, participant/sample description, result form, and limits of
  interpretation at a level proportionate to the claim.
- `sampling_and_reporting_precision`: whether small, sparse, or qualitative
  evidence is reported with suitable precision and traceability. Exact counts
  are one possible expression of this broader dimension, not a standalone rule.
- `claim_strength_alignment`: whether conclusions are descriptive,
  exploratory, comparative, causal, deployment-ready, or not clear, and whether
  public report wording stays within what the evidence supports.
- `benchmark_or_dataset_construction`: whether construction, filtering, splits,
  baselines, comparison units, and reproducibility are visible enough for the
  claim being made.
- `runtime_and_reproducibility_stance`: whether claims rely on static code
  inspection, syntax/config checks, submitted logs, smoke execution, full system
  execution, benchmark replay, or operator observation; missing runtime proof is
  a verifiability limitation, not automatic evidence of non-functionality.
- `related_work_and_source_support`: whether sources are used as background,
  direct support for a concrete claim, state-of-practice grounding, comparison
  baseline, assignment-required reading, or overextended citation support.

### Contribution Boundary Calibration

For theses built on existing frameworks, libraries, datasets, generated
components, or public examples, the reviewer should separate:

- upstream or inherited infrastructure;
- domain integration and adaptation;
- the student's own implementation and design choices;
- benchmark, dataset, experiment, or workflow construction;
- assignment literalness versus positive generalization, justified deviation, or
  unclear fulfillment.

This boundary is semantic reviewer work. Deterministic helpers may only validate
that boundary fields and evidence refs exist when the report relies on them.

### Evidence-Mode Matrix

Video, media, checker, figure, and table evidence should be represented by both
mode and review state. The workflow should not treat "file exists" as equivalent
to "supports this public report claim".

Useful states:

- `inventoried`: artifact exists and was registered, but not substantively
  reviewed.
- `sampled`: reviewer inspected selected parts and records the sampling limits.
- `full_reviewed`: reviewer inspected the relevant artifact end to end or the
  relevant figure/table in full.
- `operator_accepted`: operator supplied or accepted the observation as evidence.
- `claim_supporting`: the reviewed artifact directly supports a specific report
  claim, defense question, or private comment.
- `unsupported`: the artifact exists but does not support the claim being
  considered.

The figure/media workflow still owns detailed visual descriptions and
media-specific evidence. Code-consistency and code-quality workflows still own
implementation and reproducibility evidence. This plan only adds the
report-readiness contract that downstream synthesis can consume across those
evidence sources.

### Source-Support Triage

Literature and source evidence should be routed by support role, not by raw
presence or count. Useful states:

- `background_relevant`: source is relevant context but does not directly
  support a specific report-critical claim.
- `direct_claim_support`: source directly supports a claim used in the report.
- `state_of_practice`: source helps assess existing solutions or build-vs-adapt
  justification.
- `assignment_required`: source or topic is explicitly part of the assignment
  expectations.
- `citation_hygiene_issue`: bibliographic or citation precision problem that
  should not be inflated into total absence of literature.
- `unsupported_claim`: cited or uncited thesis claim exceeds available source
  support.

The literature/citation workflow owns source acquisition and citation evidence.
The methodology/report layer consumes only the support classification and keeps
the public report proportionate.

### Final IS Handoff Controls

Before treating a clean report as ready for operator submission, the workflow
should verify a compact handoff checklist:

- exact IS select values, category points, total points, and grade;
- public report text and private student comment remain separated;
- defense-question count and wording match the approved trace/calibration;
- existing clean-report and opponent-facing-boundary checks passed; methodology
  additions must not bypass those checks or add a parallel duplicate detector for
  internal paths, hashes, packet/check names, workflow state, private URLs,
  Theses.cz no-concern details, or unsupported GitHub/CI/runtime claims;
- any manual shortening for IS keeps evidence boundaries, points, selected
  values, defense questions, and public/private separation unchanged.

After the operator submits or exports the final official report, the workflow
should capture the submitted PDF/text and classify any submitted-report delta.
Only a clean submitted capture with no unresolved material delta should become
`archive_ready`.

### Target Bindings

Methodology items should not remain only as generic handoff suggestions. When a
methodology, evidence-state, contribution-boundary, or source-support item
affects the report, it should bind to explicit targets:

- assignment point ids or typed assignment-coverage refs;
- FIT IS item, category points, total points, and grade impact when relevant;
- public report, private student comment, defense question, manual check, or
  keep-internal target;
- source refs and hashes used for the item;
- selected `work/opponent_report_trace.json` entries or report-quality controls;
- whether the item is resolved, operator-accepted, blocked, or deferred to
  defense.

Validators check the existence, enum values, and referenced artifacts; semantic
meaning remains reviewer work.

### Operator Feedback Promotion

Operator feedback after materials review, report review, or submitted-report
capture should not disappear into a one-off correction. The workflow should
record one compact promotion decision when the feedback changes stance, tone,
grade strictness, public/private wording, evidence handling, defense questions,
or workflow behavior:

- `case_only`: useful for the current report, not reusable.
- `reviewer_profile`: durable personal preference for future wording or
  calibration.
- `workflow_docs_or_templates`: general workflow rule, prompt, skill, template,
  or checker contract.
- `todo_or_follow_up_plan`: useful, but outside the current rollout.

The record should point to the feedback source and affected artifact hashes
where practical. It should not copy private case wording into tracked docs.

### Provenance And Anchor Hygiene

Generated internal evidence should preserve full evidence anchors even when the
human-readable Markdown uses shortened display. A later audit should be able to
recover canonical `path:line` or `path:line-line` refs from the artifact or its
machine-readable companion without re-reading the whole case.

General operation-log parsing, stale approval/hash repair, and mutually
exclusive closeout states belong to `plans/review_manifest_closeout_repair_plan.md`.
This plan only requires that methodology/report gates produce structured inputs
that those closeout commands can validate.

### Generalization Rule

Do not add rules like:

- "small n must use exact counts"
- "qualitative studies need quotes"
- "latency must be measured"
- "there must be CI"
- "video must be watched fully"

Instead, encode review prompts like:

- Does the reporting precision match the method, sample, and strength of the
  thesis conclusion?
- Does the evaluation design match the claim being made?
- Is the source of requirements, domain need, or stakeholder evidence visible?
- Are benchmark construction, filtering, splits, and comparison units
  traceable enough for the claim strength?
- Are method limitations handled proportionately rather than used as automatic
  grade penalties?
- Is missing evidence a public report issue, a private student note, a defense
  question, a manual check, or only an internal limitation?

Concrete examples may appear in skill prompts as illustrations, but not as
deterministic gates or narrow trigger rules.

### Source Lookup Rule

When methodological norms are material and not obvious from current reviewer
knowledge, the methodology reviewer can request targeted source acquisition.
The route should be:

1. State the methodological question and why it matters to the current report.
2. Ask the operator for approval if external lookup is not already authorized.
3. Use `thesis-literature-citation-review` style acquisition rules to record
   public metadata/PDF evidence under ignored `work/literature/` or a dedicated
   methodology source workspace.
4. Cite the acquired source only to calibrate evaluation expectations; do not
   turn methodology literature into a new thesis requirement unless the
   assignment, field, or thesis claim makes it material.

## Proposed Artifact

`work/methodology_evidence.json`:

```json
{
  "schema_version": "methodology-evidence-v1",
  "case_id": "synthetic-methodology-case",
  "round_id": "20260525-000000-methodology-review",
  "generated_at": "YYYY-MM-DDTHH:MM:SSZ",
  "producer_type": "agent",
  "producer_role": "methodology-evidence-reviewer",
  "producer_agent": "synthetic-reviewer",
  "authorization_note": "Current request explicitly authorized agents.",
  "source_refs": [
    "extracted/thesis.txt",
    "notes/assignment.md",
    "work/quantitative_claims.json"
  ],
  "methodology_items": [
    {
      "item_id": "M1",
      "summary": "Short semantic summary of the evaluated method/claim.",
      "method_family": "user_study",
      "claim_type": "usability",
      "claim_strength": "exploratory",
      "evidence_mode": ["thesis_text", "figures_tables"],
      "evidence_state": "sampled",
      "method_fit": "partially_suitable",
      "traceability": "partial",
      "source_basis": "thesis_internal",
      "evidence_refs": ["extracted/thesis.txt"],
      "supporting_refs": [],
      "limitations": [
        "The thesis describes the study at a high level but does not provide enough traceable protocol or result detail for stronger comparative claims."
      ],
      "report_impact": "Use cautious public wording; consider a defense question if this affects grading.",
      "review_action": "defense_question",
      "requires_operator_decision": false,
      "requires_source_lookup": false
    }
  ],
  "contribution_boundary_items": [
    {
      "item_id": "CB1",
      "summary": "Short distinction between inherited infrastructure, integration, own implementation, and assignment interpretation.",
      "evidence_refs": ["extracted/thesis.txt"],
      "assignment_interpretation": "unclear",
      "review_action": "defense_question"
    }
  ],
  "evidence_mode_matrix": [
    {
      "ref": "extracted/figures/figure-1.png",
      "mode": "figures_tables",
      "review_state": "sampled",
      "supports_item_ids": ["M1"],
      "limitations": ["The figure was inspected for report relevance, but it is not by itself full evidence for the usability claim."]
    }
  ],
  "operator_questions": [],
  "source_lookup_requests": [],
  "synthesis_handoff": {
    "public_report_candidates": [],
    "private_comment_candidates": [],
    "defense_question_candidates": [],
    "manual_checks": [],
    "do_not_overstate": []
  },
  "limitations": []
}
```

The exact schema should be finalized during Slice 2 after code audit and
review. The artifact is internal/operator evidence. Downstream synthesis should
carry only selected, compact conclusions into the report trace.

## Slices

### Slice 0 - Plan Review And Scope Lock

Status: planned

Expected paths:

- `plans/opponent_methodology_pipeline_plan.md`

Work:

- Review this plan for overlap with active plans:
  `plans/token_efficiency_reuse_plan.md`,
  `plans/review_manifest_closeout_repair_plan.md`,
  archived `plans/archive/historical_opponent_calibration_plan.md`, and
  `plans/case_format_migration_contract_plan.md`.
- Treat manifest/approval/operation-log/closeout normalization as a prerequisite
  contract for slices that depend on terminal readiness; if the closeout-repair
  plan does not expose the needed state, block or rescope those slices instead
  of inventing parallel closeout mechanics.
- Confirm that methodology review is a core evidence workflow, while
  historical/personal report calibration stays a follow-up.
- Record the V1 scope as opponent-first with a reusable schema, and keep
  supervisor wiring as a later explicit plan if the opponent workflow proves the
  contract.

Verification:

```bash
git diff --check
scripts/check-private
scripts/check-scripts
```

### Slice 1 - Case-Neutral Methodology Review Contract

Status: planned

Expected paths:

- `docs/methodology-evidence-review.md`
- `.agents/skills/thesis-quantitative-claims-review/SKILL.md`
- `.agents/skills/thesis-opponent-materials/SKILL.md`
- `.agents/skills/thesis-opponent-materials-review/SKILL.md`
- `.agents/skills/thesis-opponent-report-review/SKILL.md`
- `TODO.md` only if residual work remains outside this plan

Work:

- Write a case-neutral methodology/evaluation review guide.
- Refactor examples into broad evidence dimensions rather than low-level rules.
- Clarify how methodology review relates to quantitative claims:
  quantitative claims cover numbers and result interpretation;
  methodology evidence covers method fit, evidence traceability, source of
  requirements/domain claims, study design, benchmark construction, and claim
  strength.
- Include the methodology checklist families explicitly:
  problem framing/stakeholder input, user-study protocol, sampling/reporting
  precision, claim-strength alignment, benchmark/dataset construction, and
  factual contribution-boundary evidence and target binding. Reviewer-specific
  weighting of an already established contribution boundary belongs to the
  calibration profile.
- Update opponent skills so synthesis and report review consult methodology
  evidence when present.
- Add source-lookup guidance that routes through targeted acquisition and
  operator approval instead of broad web searches or raw-text heuristics.

Verification:

```bash
git diff --check
scripts/check-private
scripts/check-scripts
```

### Slice 2 - Structured Artifact And Validator

Status: planned

Expected paths:

- `src/thesis_review_workflow/methodology_evidence.py`
- `src/thesis_review_workflow/cli/check_methodology_evidence.py`
- `src/thesis_review_workflow/commands.py`
- `src/thesis_review_workflow/work_artifacts.py`
- `src/thesis_review_workflow/review_manifest.py`
- `src/thesis_review_workflow/cli/init_review_manifest.py`
- `src/thesis_review_workflow/cli/check_review_manifest.py`
- `scripts/BUILD`
- `scripts/check-methodology-evidence`
- `tests/test_methodology_evidence.py`
- `tests/test_work_artifacts.py`
- `tests/test_review_manifest_helpers.py`

Work:

- Implement `methodology-evidence-v1` schema validation.
- Keep validation structural: schema version, case/round identity, allowed enum
  values, non-empty summaries, safe refs, existing refs, hashes where needed,
  privacy/path checks, and no obvious placeholder text.
- Include structural fields for checklist family, evidence state,
  contribution-boundary items, evidence-mode matrix entries, operator questions,
  source-lookup requests, and synthesis handoff. Validators must not decide
  whether a study protocol, stakeholder input, media item, or contribution claim
  is substantively strong.
- Include verification-state and source-support role fields so runtime/build
  evidence and literature evidence can be consumed without overstating what was
  actually checked.
- Include `target_bindings` that connect methodology items to assignment refs,
  FIT IS items, report/public-private/defense/manual targets, grade/points
  impact, source hashes, report trace entries, and resolution state.
- Register `work/methodology_evidence.json` as a private supporting work
  artifact.
- Add manifest/helper-check integration when the artifact exists and synthesis
  uses it.
- Add anonymized synthetic fixtures only.

Verification:

```bash
pants fmt src/thesis_review_workflow:: tests:: scripts::
pants lint src/thesis_review_workflow:: tests:: scripts::
pants check src/thesis_review_workflow:: tests:: scripts::
pants test tests/test_methodology_evidence.py tests/test_work_artifacts.py tests/test_review_manifest_helpers.py
scripts/check-private
scripts/check-scripts
git diff --check
```

### Slice 3 - Role Plan, Packets, And Materiality Routing

Status: planned

Expected paths:

- `src/thesis_review_workflow/agent_profiles.py`
- `src/thesis_review_workflow/review_profiles.py` if a new role key is needed
- `src/thesis_review_workflow/review_materiality.py`
- `src/thesis_review_workflow/opponent_packets.py`
- `docs/agent-profile-matrix.md`
- `docs/agent-scheduling.md`
- `tests/test_agent_profile_contracts.py`
- `tests/test_opponent_packets.py`
- `tests/test_review_pipeline_orchestration.py`
- `tests/test_review_materiality.py`

Work:

- Add a methodology evidence role or packet section. Prefer the smallest role
  boundary that avoids duplicating quantitative-claims review.
- Decide trigger semantics:
  - required when assignment/evidence explicitly centers on user study,
    benchmark, field evaluation, simulation, expert review, domain analysis, or
    methodology-sensitive claims;
  - `delta_review` when operator notes or changed evidence challenge method fit
    or claim strength, problem framing, stakeholder evidence, contribution
    boundary, assignment interpretation, evidence mode, verification state, or
    source-support role;
  - `blocked_with_typed_limitation` when the reviewer needs source lookup or
    operator clarification before report-ready synthesis.
- Ensure packets explain that examples are illustrative, not low-level matching
  criteria.
- Keep max-2 agent scheduling unchanged.

Verification:

```bash
pants test tests/test_agent_profile_contracts.py tests/test_opponent_packets.py tests/test_review_pipeline_orchestration.py tests/test_review_materiality.py
scripts/smoke-opponent-packets
scripts/smoke-prepare-review-round
scripts/check-private
scripts/check-scripts
git diff --check
```

### Slice 4 - Pre-Draft Operator Calibration Intake

Status: planned

Expected paths:

- `docs/opponent-review-workflow.md`
- `.agents/skills/thesis-opponent-materials-review/SKILL.md`
- `.agents/skills/thesis-opponent-report-review/SKILL.md`
- `src/thesis_review_workflow/opponent_calibration.py` only if extending the
  existing revision-request contract is cleaner than adding a new artifact
- `src/thesis_review_workflow/report_calibration.py` only for structural
  binding to current report calibration, not for semantic decisions
- `src/thesis_review_workflow/cli/check_opponent_report.py`
- `src/thesis_review_workflow/cli/draft_opponent_report.py`
- `tests/test_opponent_report.py`
- `tests/test_report_calibration.py`
- `tests/test_opponent_calibration.py`

Work:

- Add a required pre-draft calibration checkpoint after reviewed materials and
  before final report trace/export. The checkpoint should ask for and record:
  target grade-strictness posture, contribution-boundary stance, assignment
  fulfillment interpretation, public/private wording preference, defense
  questions, and evidence challenges.
- Reuse `notes/opponent-report-operator-feedback.md` and
  `work/opponent_report_revision_request.json` where possible instead of
  inventing another ledger.
- If the operator has no additional challenge, record a typed limitation or
  accepted no-action state with current source hashes.
- Add a promotion decision for material operator feedback: case-only correction,
  reviewer-profile preference, workflow docs/templates update, or TODO/follow-up
  plan.
- Make `draft-opponent-report` and `export-opponent-report` fail with concrete
  recovery messages when unresolved material methodology questions, late
  `material_claim_delta`, or `evidence_challenge` inputs should be resolved
  before drafting/exporting.
- Implement or reuse one shared unresolved-input gate so draft, export,
  canonical/clean report checks, final report review, and closeout all see the
  same blocking state.
- Require material deltas to be reflected in `work/report_calibration_basis.json`
  and `work/opponent_report_trace.json`, then independently re-reviewed before
  final closeout.
- Keep style-only wording deltas as bounded post-review exceptions when they do
  not alter evidence, grade, points, IS selections, defense questions, or public
  criticism.

Verification:

```bash
pants test tests/test_opponent_report.py tests/test_report_calibration.py tests/test_opponent_calibration.py
scripts/smoke-opponent-report
scripts/smoke-opponent-closeout
scripts/check-private
scripts/check-scripts
git diff --check
```

### Slice 5 - Report Trace And Report-Review Integration

Status: planned

Expected paths:

- `src/thesis_review_workflow/cli/check_opponent_report.py`
- `src/thesis_review_workflow/cli/draft_opponent_report.py`
- `src/thesis_review_workflow/cli/export_opponent_report.py`
- `src/thesis_review_workflow/review_wave_gate.py`
- `.agents/skills/thesis-opponent-report-review/SKILL.md`
- `docs/opponent-review-workflow.md`
- `tests/test_opponent_report.py`
- `tests/test_review_wave_gate.py`

Work:

- Add compact methodology controls to `work/opponent_report_trace.json` or bind
  methodology evidence through existing `uncertainty_items`,
  `pre_submission_checks`, `defense_questions`, and report-quality controls.
- Bind contribution-boundary decisions, assignment-interpretation stance,
  evidence-mode matrix items, verification-state items, source-support
  classifications, final IS handoff controls, and pre-draft calibration intake
  to the report trace when they affect public criticism, grade/points, defense
  questions, or private comments.
- Require report review to verify those target bindings against assignment
  coverage, FIT IS items, grade/point rationale, evidence matrix, and
  public/private/defense/manual targets.
- Ensure clean public report proposals do not leak methodology ledgers,
  source-acquisition mechanics, role packets, hashes, or internal review
  process.
- Teach report review to check that public wording reflects method fit and claim
  strength without turning internal methodology detail into the report.
- Preserve concise report style.

Verification:

```bash
pants test tests/test_opponent_report.py tests/test_review_wave_gate.py
scripts/smoke-opponent-report
scripts/check-private
scripts/check-scripts
git diff --check
```

### Slice 6 - Source-Lookup And Operator-Question Routing

Status: planned

Expected paths:

- `docs/methodology-evidence-review.md`
- `.agents/skills/thesis-literature-citation-review/SKILL.md`
- `.agents/skills/thesis-quantitative-claims-review/SKILL.md`
- `src/thesis_review_workflow/methodology_evidence.py`
- `tests/test_methodology_evidence.py`

Work:

- Add a structured way for methodology review to say:
  - source lookup is needed,
  - source lookup is optional,
  - operator disabled lookup,
  - operator expertise is sufficient,
  - no external source is necessary for the current report.
- Keep lookup targeted to methodological questions that affect a material
  finding, report wording, grade calibration, or defense question.
- Ensure acquired methodology sources are stored under ignored round workspaces
  and do not become tracked fixtures.
- The checker validates only source-request state and refs, not source meaning.

Verification:

```bash
pants test tests/test_methodology_evidence.py
scripts/check-private
scripts/check-scripts
git diff --check
```

### Slice 7 - Evidence And Verification State Integration

Status: planned

Expected paths:

- `docs/methodology-evidence-review.md`
- `docs/opponent-review-workflow.md`
- `.agents/skills/thesis-figure-media-review/SKILL.md`
- `.agents/skills/thesis-code-consistency/SKILL.md`
- `.agents/skills/thesis-code-quality-review/SKILL.md`
- `.agents/skills/thesis-literature-citation-review/SKILL.md`
- `.agents/skills/thesis-opponent-materials-review/SKILL.md`
- `.agents/skills/thesis-opponent-report-review/SKILL.md`
- `src/thesis_review_workflow/methodology_evidence.py`
- `src/thesis_review_workflow/cli/check_methodology_evidence.py`
- `tests/test_methodology_evidence.py`
- `tests/test_opponent_report.py`
- `TODO.md`

Work:

- Add the evidence-mode matrix states for video, media, checker reports,
  figures, and tables.
- Add verification states for submitted code, build artifacts, runtime logs,
  test logs, smoke runs, full runs, benchmark replay, and operator observation.
- Add source-support role states for literature/related-work claims.
- Define how the matrix consumes figure/media review outputs when present, and
  how it consumes code/literature evidence without making those roles rerun.
- Record a typed limitation when only inventory, sampling, static inspection, or
  background-relevant sources are available.
- Make report synthesis distinguish artifact existence from claim support,
  static inspection from runtime proof, and background literature from direct
  claim support.
- Route unsupported or only sampled media evidence to private notes, defense
  questions, or manual checks unless the operator explicitly accepts it for the
  report.
- Reconcile `TODO.md`: keep deeper visual/video feature work only if this slice
  does not complete it.

Verification:

```bash
pants test tests/test_methodology_evidence.py tests/test_opponent_report.py
scripts/smoke-opponent-methodology-evidence
scripts/check-private
scripts/check-scripts
git diff --check
```

### Slice 8 - Final Readiness And Submission States

Status: planned

Expected paths:

- `docs/opponent-review-workflow.md`
- `.agents/skills/thesis-opponent-report-review/SKILL.md`
- `src/thesis_review_workflow/cli/check_opponent_report.py`
- `src/thesis_review_workflow/cli/review_round_closeout.py`
- `src/thesis_review_workflow/cli/case_doctor.py`
- `src/thesis_review_workflow/submitted_reports.py` if submitted-report state
  integration is needed
- `tests/test_opponent_report.py`
- `tests/test_review_round_closeout.py`
- `tests/test_submitted_reports.py`

Work:

- Add explicit report terminal states: `ready_for_is`, `submitted_captured`,
  `submitted_delta_blocked`, and `archive_ready`.
- Keep clean export and independent report review as prerequisites, not the end
  of readiness.
- Reuse existing `check-opponent-report --mode clean`, report-review, and
  opponent-facing-boundary controls for public-prose hygiene. This slice should
  add terminal-state/readiness semantics, not a second implementation of leak
  detection that is already covered elsewhere.
- Require submitted report capture and submitted delta classification before
  archive readiness when a final submitted artifact exists.
- Ensure stale intermediate reviewer TODO text or superseded approval notes do
  not override a later terminal state; closeout should point to the current
  terminal state and any remaining blockers.
- Coordinate with `plans/review_manifest_closeout_repair_plan.md` for operation
  log validation, manifest/hash repair, and approval provenance mechanics.

Verification:

```bash
pants test tests/test_opponent_report.py tests/test_review_round_closeout.py tests/test_submitted_reports.py
scripts/smoke-opponent-report
scripts/smoke-opponent-closeout
scripts/check-private
scripts/check-scripts
git diff --check
```

### Slice 9 - Operation Log And Canonical Anchor Follow-Up

Status: planned

Expected paths:

- `plans/review_manifest_closeout_repair_plan.md`
- `docs/opponent-review-workflow.md`
- `.agents/skills/thesis-opponent-report-review/SKILL.md`
- `TODO.md` only if residual work is intentionally left outside this plan

Work:

- Decide whether operation-log JSONL validation and unresolved-operation
  computation should move fully into `plans/review_manifest_closeout_repair_plan.md`.
- Record that methodology/report artifacts must emit structured source refs that
  closeout can validate; avoid shortened-only Markdown anchors in generated
  internal evidence.
- If canonical anchor validation is not implemented in this plan, add a precise
  TODO or closeout-repair slice rather than leaving it as an informal reviewer
  preference.
- Treat Omen MCP prepared-code-root failures as advisory tool preflight debt for
  code-review workflows, not as methodology semantics; route to TODO or a
  separate tooling plan unless this rollout touches that surface.

Verification:

```bash
git diff --check
scripts/check-private
scripts/check-scripts
```

### Slice 10 - Smoke Coverage, Docs, TODO Reconciliation, And Archive

Status: planned

Expected paths:

- `scripts/smoke-opponent-methodology-evidence`
- `scripts/BUILD`
- `README.md` only if the operator-facing top path changes
- `docs/opponent-review-workflow.md`
- `TODO.md`
- `plans/opponent_methodology_pipeline_plan.md`
- `plans/archive/opponent_methodology_pipeline_plan.md` after final audit

Work:

- Add a smoke case with synthetic methodology evidence, unresolved operator
  question, resolved operator question, no-source-needed path,
  contribution-boundary calibration, material-delta blocking, bounded style-only
  exception, evidence-mode matrix states, runtime-verification states,
  source-support triage, target bindings, final IS handoff checks, and final
  submission/archive states.
- Reconcile `TODO.md`: remove only work completed by this plan, keep visual/video
  and historical calibration items if they remain future work.
- Keep README chat-first. Mention methodology evidence only if operators need a
  new prompt pattern; otherwise leave details in docs/skills.
- Run final hygiene and archive the plan after residuals are copied to TODO.

Verification:

```bash
pants fmt src/thesis_review_workflow:: tests:: scripts::
pants lint src/thesis_review_workflow:: tests:: scripts::
pants check src/thesis_review_workflow:: tests:: scripts::
pants test tests/test_methodology_evidence.py tests/test_opponent_packets.py tests/test_review_pipeline_orchestration.py tests/test_opponent_report.py tests/test_review_manifest_helpers.py
scripts/smoke-opponent-methodology-evidence
scripts/smoke-opponent-packets
scripts/smoke-opponent-report
scripts/smoke-opponent-closeout
scripts/smoke-package-workflow-tools
scripts/check-private
scripts/smoke-private
scripts/check-scripts
git diff --check
```

If code changed materially in this repository, also attempt:

```bash
pants run :omen
```

Record Omen absence or failure as developer-hygiene limitation, not as a thesis
case pipeline blocker.

## Progress

- 2026-05-25: Plan created from a case-neutral synthesis of recent opponent
  report work. The plan intentionally generalizes narrow observations into a
  methodology/evaluation evidence workflow and leaves historical/personal
  calibration as follow-up.
- 2026-05-25: Expanded plan scope before implementation to include explicit
  pre-draft operator calibration intake, material-delta draft/export blocking,
  problem-framing and user-study checklist families, contribution-boundary
  calibration, and the evidence-mode matrix for media/checker/figure signals.
- 2026-05-25: Ran a second case-neutral audit with agents and added the remaining
  generalized gaps: runtime/build/test/log verification states, source-support
  triage, target bindings, final IS/submitted/archive terminal states, operator
  feedback promotion, and closeout/provenance handoff to the closeout-repair
  plan.

## Decision Log

- Generalize from examples to evidence dimensions. Narrow observations such as
  "small n should use exact counts" are treated only as examples of the broader
  reporting-precision, sampling-traceability, and claim-strength question.
- V1 is opponent-first. The methodology artifact should remain reusable, but
  supervisor and supervisor-report wiring are deferred until the opponent path
  demonstrates useful evidence and report integration.
- Prefer a structured methodology artifact over adding more free-form checklist
  prose to report drafts.
- Keep deterministic validation structural. No raw thesis/report keyword
  heuristics for method quality, assignment fulfillment, grade, or report
  wording.
- Keep calibration as follow-up. This plan may use current
  `work/report_calibration_basis.json` and `work/opponent_report_trace.json`
  bindings, but it does not implement historical opponent calibration or a new
  personal preference refresh workflow.
- Treat material deltas differently from style-only wording changes. Material
  evidence or claim changes must flow through structured calibration/trace
  artifacts and independent re-review; bounded style-only edits may remain a
  narrower exception.
- Promote evidence-mode handling for media/checker/figure signals into this
  plan, while leaving detailed visual/media review ownership in the existing
  figure/media workflow.
- Extend evidence-state handling beyond media: runtime/build/test/log evidence
  and literature/source support need the same "what was actually checked and
  what claim does it support" discipline.
- Require methodology findings that affect the report to bind to concrete
  targets: assignment refs, FIT IS items, grade/points, public/private/defense
  destination, trace refs, source hashes, and resolution state.
- Treat clean export, independent report review, submitted-report capture,
  submitted-delta classification, and archive readiness as distinct terminal
  states. Do not imply that clean export alone is archive-ready.
- Keep operation-log integrity, stale approval/hash reconciliation, and
  prepared-code-tool preflight mostly in the closeout/tooling plans; this plan
  only depends on their structured contracts.
- Reuse existing operator-note and revision-request surfaces where possible.
  Avoid adding a parallel ledger for every new correction type.
- Keep report output compact. Methodology ledgers and source-acquisition detail
  belong in internal evidence, not in public IS prose.

## Final Audit

Not run yet. This plan is not complete.
