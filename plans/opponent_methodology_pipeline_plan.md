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
  graph/table quality checks, and historical opponent-report calibration.

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
- Pre-draft operator challenge intake for opponent reports: before report trace
  finalization and `draft-opponent-report`, the pipeline should surface a compact
  list of unresolved evidence challenges, contribution-boundary choices,
  methodology concerns, and report-facing calibration questions.
- Report-trace controls that carry only compact, report-relevant conclusions
  from methodology evidence into the public report, private student comment,
  defense questions, or manual checklist.

Out of scope:

- Historical opponent-report calibration implementation. Keep it as a follow-up
  through `plans/historical_opponent_calibration_plan.md`.
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
  contribution_boundary, novelty, comparison, reproducibility, other.
- `claim_strength`: descriptive, exploratory, indicative, comparative,
  causal, statistical, deployment_ready, not_clear.
- `evidence_mode`: thesis_text, submitted_data, submitted_code, logs,
  notebooks, figures_tables, video_demo, external_source, operator_observation,
  not_available.
- `method_fit`: suitable, partially_suitable, weak, unclear, not_verifiable.
- `traceability`: direct, partial, scattered, missing, not_applicable.
- `source_basis`: thesis_internal, submitted_artifact, cited_literature,
  methodological_source, operator_expertise, missing, not_applicable.
- `review_action`: use_in_public_report, private_student_comment,
  defense_question, manual_check, keep_internal, no_action.

These enums are intentionally broad. The reviewer explains the concrete case in
natural language with evidence refs; validators check only shape and refs.

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
  `plans/historical_opponent_calibration_plan.md`, and
  `plans/case_format_migration_contract_plan.md`.
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
    or claim strength;
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

### Slice 4 - Pre-Draft Operator Challenge Intake

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

- Add a required pre-draft checkpoint after reviewed materials and before final
  report trace/export when methodology evidence contains unresolved operator
  questions, source-lookup requests, material evidence challenges, or
  contribution-boundary decisions.
- Reuse `notes/opponent-report-operator-feedback.md` and
  `work/opponent_report_revision_request.json` where possible instead of
  inventing another ledger.
- If the operator has no additional challenge, record a typed limitation or
  accepted no-action state with current source hashes.
- Make `draft-opponent-report` fail with a concrete recovery message when
  unresolved material methodology questions should be resolved before drafting.
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

### Slice 7 - Smoke Coverage, Docs, TODO Reconciliation, And Archive

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
  question, resolved operator question, and no-source-needed paths.
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
- Reuse existing operator-note and revision-request surfaces where possible.
  Avoid adding a parallel ledger for every new correction type.
- Keep report output compact. Methodology ledgers and source-acquisition detail
  belong in internal evidence, not in public IS prose.

## Final Audit

Not run yet. This plan is not complete.
