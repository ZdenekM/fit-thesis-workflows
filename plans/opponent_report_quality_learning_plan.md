# Opponent Report Quality Learning Plan

Status: active
Created: 2026-05-20

## Goal

Turn recurring external feedback on generated opponent-report drafts into a
case-neutral improvement loop for the opponent-report pipeline.

The target is not longer reports. The target is a draft route that consistently:

- maps important judgments to assignment points and FIT IS criteria;
- distinguishes "not evidenced in available materials" from "not done";
- records what the agent actually checked before making claims about code,
  reproducibility, licensing, media, testing, or deployment;
- keeps strengths visible and explains why they do or do not move the grade;
- calibrates points, grade, IS selections, and wording against each other;
- produces fair, focused defense questions tied to evidence gaps or grading
  tension.

The public IS report must stay reasonably short. Extra evidence belongs in
internal trace, ledgers, packets, reviewed materials, and review notes; only the
smallest defensible synthesis should reach `outputs/oponent_posudek_navrh.md`.

This plan is intentionally case-neutral. It must not encode facts, names,
topics, point values, grades, or conclusions from any one real thesis case.

## Audit Base

Input that motivated this plan:

- operator-supplied external meta-reviews of generated BP opponent-report
  drafts, used only as abstract quality signals;
- no tracked case contents were copied into this plan;
- no concrete student identity, case id, round id, thesis topic, report points,
  grade, or case-specific findings are retained here.

Repository context inspected:

```bash
sed -n '1,260p' AGENTS.md
sed -n '1,260p' plans/README.md
sed -n '1,260p' docs/agent-profile-matrix.md
sed -n '1,300p' .agents/skills/thesis-opponent-report-review/SKILL.md
sed -n '1,320p' .agents/skills/thesis-opponent-materials/SKILL.md
sed -n '1,340p' docs/opponent-review-workflow.md
sed -n '1,260p' docs/fit-is-rubric.md
sed -n '1,260p' profiles/default.md
sed -n '1,280p' plans/archive/reviewer_profile_application_plan.md
sed -n '394,660p' src/thesis_review_workflow/structured_evidence.py
sed -n '220,520p' src/thesis_review_workflow/cli/draft_opponent_report.py
sed -n '520,760p' src/thesis_review_workflow/cli/check_opponent_report.py
```

Serena preflight and scoped use:

- `mcp__serena__.initial_instructions` activated project `diplomky_v2`.
- `mcp__serena__.search_for_pattern` over `src/thesis_review_workflow` found
  existing report-calibration, opponent-report-trace, assignment-coverage, and
  draft/check surfaces. Result: this plan should extend existing
  `work/opponent_report_trace.json`, `work/report_calibration_basis.json`,
  role packets, and report checks instead of inventing a parallel report
  generator.

Current useful controls:

- `docs/fit-is-rubric.md` already states the compact FIT IS checklist and the
  key unverifiability warning.
- `work/assignment_coverage_agent.json` already exists as the semantic
  assignment-coverage source; deterministic helpers validate it structurally
  rather than inferring coverage from raw thesis text.
- `work/opponent_report_trace.json` already maps reviewed opponent materials
  into FIT IS sections, defense questions, pre-submission checks, and
  uncertainty items.
- `work/report_calibration_basis.json` already binds applied reviewer-profile
  and operator-calibration preferences to report controls.
- `scripts/check-opponent-report` already validates report shape, privacy,
  concrete points/grade, IS values, calibration controls, question count, and
  removal of internal confidence labels from public prose.
- Opponent materials already include an evidence ledger and confidence labels;
  the report draft currently consumes only selected trace fields, so some useful
  internal discipline can be lost at the report boundary.

Quality gaps abstracted from feedback batches:

- FIT IS criteria can become headings rather than criterion-specific reasoning.
- Assignment fulfillment can be discussed globally instead of point by point.
- A generated report can sound too certain about code, reproducibility,
  licensing, media, or submitted auxiliary artifacts when those were not
  actually inspected.
- "The thesis did not document X" can drift into "the work did not do X".
- Experiments and user studies need a clearer distinction between existence,
  data quality, sample relevance, interpretation limits, and what the results
  actually support.
- Evaluation criticism should credit evidence that is actually present and then
  name the missing repeatability pieces precisely: task list, instructions,
  ordering/counterbalancing, metric definitions, per-participant or aggregated
  data, and uncertainty.
- Strong claim words such as effectiveness, precision, usability, intuitiveness,
  innovation, scalability, robustness, or practical deployability need explicit
  evidence, metric, comparator, or limitation handling before they become public
  report claims.
- Claims about scalability, performance, robustness, "many items", or broad
  operating conditions need explicit stress, scale, or boundary evidence rather
  than extrapolation from a small demonstration.
- Positive implementation evidence should be preserved, but the report should
  also explain why implementation breadth may not offset weak analysis,
  literature, validation, or assignment traceability.
- Technically risky platforms or hardware/software integration can make a
  prototype a stronger achievement than a routine application, but difficulty is
  a calibration factor, not a reason to ignore validation or evidence limits.
- Technical difficulty should separate integration breadth, algorithmic
  originality, implementation depth, and evaluation difficulty. A strong
  integration contribution is legitimate, but it is not the same as inventing a
  new core algorithm.
- Technical-report scope should not be inferred from PDF page count. The normal
  final-report route should require an operator-supplied FIT Theses Checker
  result for normostrany; if that result is unavailable, the report should carry
  a typed limitation instead of silently estimating from PDF pages.
- Literature review should check nearest comparable work and tools, not only
  general background, framework documentation, or adjacent technology sources.
- Literature review should also sample whether cited sources actually support
  the claims they are attached to; topical bibliography relevance is not enough
  when individual citation-to-claim bindings look suspicious.
- Third-party libraries, generated code, AI assistance, assets, and licenses
  should be part of internal realization-output confidence when the submitted
  materials make them material.
- Point/grade calibration needs an explicit self-check against the prose, not a
  mechanical average or one-shot number.
- Defense questions should be diagnostic and single-focus, not a dumping ground
  for every missing detail.
- Internal evidence growth must not turn into public-report growth. The report
  route needs an explicit compression step that keeps only grade-relevant
  strengths, limitations, and uncertainties in public prose and moves supporting
  detail to internal materials or private pre-submission checks.

## Scope

In scope:

- Case-neutral workflow, skill, profile, template, and validator changes that
  improve generated opponent-report drafts.
- A reusable intake format for future external meta-reviews of generated
  reports, with a strict abstraction step before anything is promoted.
- Extensions to opponent report trace, report calibration, packets, and report
  checks when they remove real recurring ambiguity.
- A private, hash-bound intake contract for FIT Theses Checker results used to
  evaluate technical-report scope.
- Report-length and compression controls for the clean IS proposal.
- Updates to public default profile preferences only for generic reviewer
  behavior. Durable personal preferences remain in ignored local profiles.
- Synthetic tests and smoke coverage only.

Out of scope:

- Editing any concrete case output under `cases/`.
- Encoding one student's topic, assignment wording, domain, metrics, report
  points, grade, or case-specific conclusions into tracked workflow files.
- Deterministic free-text heuristics over thesis/report/profile prose to infer
  meaning, grade, assignment fulfillment, or workflow routing.
- Automatic grading.
- Replacing the existing opponent-materials, report-trace, report-calibration,
  clean-export, and independent-review route.
- Backward compatibility with older `~/code/diplomky` workflows.

## Target Contract

The opponent-report route should keep the current canonical flow:

```text
outputs/oponent_podklady_revidovane.md
  -> work/opponent_report_trace.json
  -> work/oponent_posudek_draft.md
  -> outputs/oponent_posudek_navrh.md
  -> outputs/feedback_k_posudku.md
```

The improvement should happen by strengthening the structured inputs to that
flow, not by hand-editing clean exports.

## Architecture Fit And Non-Duplication

This plan extends the current opponent-report workflow; it must not create a
parallel report pipeline.

Reuse rules:

- Keep `outputs/oponent_podklady_revidovane.md` as the reviewed internal
  evidence synthesis, `work/opponent_report_trace.json` as the bridge from
  evidence into FIT IS report fields, `work/report_calibration_basis.json` as
  the opponent-report preference/control application contract, and
  `outputs/oponent_posudek_navrh.md` as the clean IS proposal.
- Treat new trace names below as candidate sections or fields inside existing
  `work/opponent_report_trace.json`, not as new standalone artifacts unless a
  slice explicitly justifies otherwise.
- Reuse existing role-owned evidence outputs. For example,
  `citation_support_review` belongs in `thesis-literature-citation-review` and
  `outputs/literature_citation_review.md`; code/reproducibility/authorship
  signals belong in `outputs/code_consistency.md`,
  `outputs/code_quality_review.md`, `work/code_reproducibility.json`, and
  synthesis trace references; quantitative/evaluation metric sanity belongs in
  `work/quantitative_claims.json` when metrics are material.
- If an existing artifact such as `work/context/claim_review_basis.json`,
  `work/context/evidence_capsules.json`, `work/evidence_requirements.json`, or
  `work/current_evidence_snapshot.json` already owns the needed evidence, the
  implementation should reference or extend that artifact instead of duplicating
  the same facts in a new structure.
- Do not add a new Codex agent role profile for these refinements unless an
  implementation slice first shows that the current role matrix cannot own the
  evidence cleanly. Prefer packet/skill updates for existing roles.
- Deterministic helpers may validate shape, hashes, safe refs, allowed enums,
  length classes, and privacy boundaries. They must not judge thesis quality,
  infer semantic meaning from raw prose, or calculate grades.

The only new standalone private artifact proposed by this plan is
`work/theses_checker_summary.json`, because FIT Theses Checker normostrany are
currently an external operator-provided measurement with no existing structured
home in the workflow.

## Promotion Rules

Promote each recurring lesson at the narrowest durable layer:

- Repo-local skills: role procedure, evidence expectations, wording discipline,
  compression rules, and handoff requirements.
- `docs/fit-is-rubric.md`: compact FIT IS interpretation shared across opponent
  materials and report review.
- `docs/opponent-review-workflow.md`: orchestration, artifact boundaries,
  provenance, closeout, and operator-visible workflow contracts.
- `profiles/default.md`: generic reviewer preferences only, such as compact
  prose, epistemic caution, and balanced strengths/limitations.
- `profiles/local/*`: personal grading style, strictness, phrase preferences,
  or private reviewer calibration, only after explicit operator instruction.
- Deterministic checkers: structural contract enforcement only.
- `TODO.md`: deferred automation or optional enhancements that should not enter
  V1. Do not use tracked `TODO.md` for private reviewer-profile refreshes;
  those remain private opt-in work under ignored local profile or case
  workspaces.

Do not promote case-specific facts, domain examples, concrete technologies,
point values, or one-off conclusions into tracked workflow rules.

Candidate new private work artifact:

- `work/theses_checker_summary.json`: normalized operator-supplied FIT Theses
  Checker result for the submitted rendered PDF. The workflow should not depend
  on scraping or automating the web app. The operator can save, screenshot,
  export, or paste the checker output into the ignored round workspace; a small
  `record-theses-checker-summary` helper then records source path, source hash,
  checked rendered-PDF ref/hash or an explicit typed limitation, normostrany
  value, relevant thresholds, checker timestamp or operator capture timestamp,
  producer, and limitations. The similarly named Theses.cz similarity workflow
  remains separate.

Trace additions are report-bound controls and references, not a new evidence
warehouse. The trace may summarize only the smallest report-facing conclusion
needed to draft or check the IS proposal; detailed evidence stays in role-owned
artifacts. New trace fields should carry ids, safe refs, enums, short summaries,
wording modes, and typed limitations; they must not copy tables, raw logs, long
review excerpts, citation inventories, code diagnostics, or experiment-protocol
detail from role-owned evidence.

V1 required trace controls:

| Trace control | Evidence owner | Trigger | Structural proof or limitation |
| --- | --- | --- | --- |
| `assignment_fulfillment_map` | `work/assignment_coverage_agent.json` and reviewed materials | assignment is available | `scripts/check-assignment-coverage` passed, or typed missing-assignment limitation |
| `rubric_alignment` | `work/opponent_report_trace.json` synthesis over FIT IS items | every final opponent report | all required IS item ids present, with criterion scope, evidence refs, and do-not-mix notes |
| `report_claim_ledger` | trace synthesis over reviewed materials and role outputs | every material public claim | claim id, target IS item, evidence refs, evidence class, evidence strength, and public wording mode |
| `checked_scope` | common briefing, current evidence snapshot, role outputs, and operator notes | every final opponent report | evidence class statuses such as checked, sampled, not_available, not_checked, or manual_check |
| `evidence_source_matrix` | role-owned evidence plus trace refs | every material claim about implementation, experiments, media, code, run/demo, literature, licensing, or deployment | source-class refs and support mode; media status must distinguish `pdf_inspected`, `source_asset_checked`, `inventoried_only`, and `not_checked` |
| `technical_report_scope_basis` | `work/theses_checker_summary.json` | technical-report-scope IS item in final-route reports | checker summary hash binding, or operator-accepted typed limitation with cautious wording mode |
| `strength_grade_tension` | report calibration basis and reviewed materials | every calibrated report | strongest positives, limiting factors, grade/point interval rationale, and private-comment focus refs |
| `defense_question_strategy` | trace defense questions | every report with defense questions | one issue per question, linked evidence gap or grading tension, target IS item, and question-count control |

Materiality-bound trace references:

- `evaluation_claim_review` references `work/quantitative_claims.json` when
  testing, experiments, metrics, performance, or result claims are material.
- `scaling_claim_review` references quantitative claims, code-quality evidence,
  run/demo evidence, or a manual-check limitation when scalability,
  performance, robustness, or broad operating-condition claims are material.
- `third_party_authorship_review` and `contribution_boundary_review` reference
  code consistency, code quality, code reproducibility, literature/citation, or
  figure/media evidence when libraries, assets, generated code, AI assistance,
  tutorials, templates, or standard platform capabilities affect the realization
  output score.
- `citation_support_review` references `outputs/literature_citation_review.md`
  when material or suspicious citation-to-claim bindings affect literature or
  technical-claim support.
- `technical_difficulty_breakdown`, `result_usability_level`, and
  `deployment_readiness` reference reviewed materials, code evidence,
  reproducibility evidence, run/demo evidence, and operator notes when they
  affect difficulty, usefulness, or deployability wording.

Do not implement a broad optional-then-required transition. In V1, required
trace controls are required for the final report route; materiality-bound
references are required only when a role-owned artifact, role plan, current
evidence snapshot, or authorized reviewer finding makes that evidence class
material. Otherwise the trace records a typed limitation or omission reason
instead of duplicating role evidence.

Candidate additions to `work/report_calibration_basis.json`:

- expected report controls remain profile/operator calibration controls such
  as final grade, point interval, IS select values, defense-question count,
  public-report length class, and private-comment requirement;
- grade/point interval rationale is recorded in `strength_grade_tension` on
  `work/opponent_report_trace.json`, where it can cite current evidence rather
  than pretending to be a profile preference;
- semantic compression priorities stay in skills/review guidance unless an
  operator or profile explicitly provides them as a calibration preference.
  Deterministic checks enforce only declared length class, question bounds,
  private-comment presence, and missing-control drift;
- private-comment controls should require a useful private student comment and
  prevent it from introducing new unsupported criticism or a different grade
  rationale than the public report;
- optional profile preferences for epistemic caution, assignment traceability,
  and implementation-versus-methodology grading tension.

Candidate report draft/export behavior:

- keep public report prose compact;
- for each FIT IS item, prefer one short paragraph; use two only when a serious
  grade-relevant tension would otherwise be unclear;
- do not copy tables, ledgers, detailed checklists, raw code diagnostics,
  citation audits, or experiment-protocol inventories into the clean IS report;
- keep the "what was checked / not checked" summary in the canonical draft's
  private pre-submission section or review basis. It must not reach the clean
  IS export except as compact public wording about a decisive limitation or
  manual uncertainty;
- when a public claim depends only on thesis text, use wording such as "the
  submitted text does not document..." rather than implying the activity did
  not happen;
- when code or auxiliary artifacts were not inspected, avoid public claims that
  require that inspection, and put the unresolved item into manual checks or a
  defense question.
- when the report refers to implementation quality, include enough evidence to
  show whether it comes from code analysis, submitted documentation, demo/run
  evidence, or a limitation, without turning the IS report into a technical
  audit dump.
- add a compression review before export: if a sentence does not explain the
  selected points/grade, a material strength, a material limitation, a manual
  uncertainty, or a focused defense question, it should remain internal.

## Slices

### Slice 1 - Feedback Intake And Abstraction Contract

Create a repeatable way to add future external meta-review batches without
turning them into case-specific rules.

Expected paths:

- `plans/opponent_report_quality_learning_plan.md`
- `templates/opponent-report-quality-feedback-intake.md`
- `WORKFLOW_MEMORY.md` only if a lesson is promoted, not as a private archive

Work:

- Add an intake template that separates:
  - source status and privacy warning;
  - case-specific observations to discard;
  - abstract recurring pattern;
  - classification as case-specific feedback, durable private reviewer
    preference, or general workflow rule;
  - proposed workflow level: skill, profile, trace schema, checker, docs, TODO;
  - evidence that the pattern is recurring or still just a candidate.
- Add a "Feedback Batch Log" section to this plan and record only abstracted
  themes from each batch.
- State explicitly that the external feedback is calibration/advisory input,
  not primary evidence about a new case.

Verification:

```bash
git diff --check
scripts/check-private
scripts/check-scripts
```

### Slice 2 - Skill And Rubric Instruction Upgrade

Tighten semantic instructions before changing code.

Expected paths:

- `.agents/skills/thesis-opponent-materials/SKILL.md`
- `.agents/skills/thesis-opponent-materials-review/SKILL.md`
- `.agents/skills/thesis-opponent-report-review/SKILL.md`
- `docs/fit-is-rubric.md`
- `docs/opponent-review-workflow.md`
- `README.md` only for operator-visible chat-first guidance, if needed

Work:

- Make assignment-point mapping a required internal synthesis input whenever the
  assignment is available.
- Add explicit wording guidance for "not evidenced" versus "not done".
- Strengthen rubric separation: difficulty, fulfillment, report scope,
  presentation, formal quality, literature, implementation output, usability,
  overall assessment, and defense questions should not collapse into one
  generic critique.
- Require a testing/evaluation interpretation pass: what the experiments show,
  what they do not show, and whether the sample/context supports the thesis
  conclusion.
- Require evaluation critiques to be specific. If the thesis reports some
  participants, environment, device/setup, results, graphs, or limitations,
  acknowledge that evidence and criticize missing repeatability, metric
  definitions, data granularity, or uncertainty instead of saying only that
  testing is unclear.
- Require a claim-word pass for strong terms such as effectiveness, precision,
  usability, intuitiveness, innovation, scalability, robustness, and practical
  deployability.
- Add a scaling/performance-claim pass for "many items", broad operating
  conditions, stress robustness, or real-time performance. Require a stress
  test, boundary experiment, comparator, measured runtime/latency/resource
  signal, or softer wording.
- Add a technical-report-scope guard: final opponent-report drafting should
  require a current FIT Theses Checker result for normostrany, or a typed
  limitation explicitly accepted by the operator. Without it, phrase only
  information value and content allocation; do not make categorical length
  claims.
- Add nearest-comparable-work guidance for literature: do not stop at general
  background or framework/tool documentation when closer research, products, or
  domain tools are central to the assignment.
- Add citation-support guidance for literature: sample material or suspicious
  citation-to-claim bindings and distinguish thematic source relevance from
  whether the cited item actually supports the local technical claim.
- Add realization-output source separation: public report wording should make
  clear when implementation claims are supported by code analysis or run/demo
  evidence versus only by thesis text.
- Add a third-party/authorship/licensing check as internal evidence when
  libraries, assets, AI assistance, generated code, tutorials, or templates are
  material to the realization-output score.
- Add contribution-boundary guidance: value integration work where it is real,
  but avoid wording that turns a standard library/framework capability into the
  student's invented method or algorithm.
- Add technical-difficulty breakdown guidance so `Náročnost zadání` can
  distinguish integration breadth, algorithmic originality, implementation
  depth, platform risk, evaluation complexity, and domain/data complexity.
- Add a report-compression rule: public comments should be short criterion
  syntheses, not miniature audit reports. Detailed evidence stays in internal
  materials unless it directly explains points, grade, or a defense question.
- Require positives plus limiting-factor synthesis: what is genuinely strong,
  and why it does or does not compensate for weaknesses.
- Keep all guidance case-neutral and avoid examples tied to one domain.

Verification:

```bash
git diff --check
scripts/check-private
scripts/check-scripts
```

### Slice 3 - Trace And Calibration Schema Extension

Make the report boundary preserve the reasoning that the external feedback
found useful.

Expected paths:

- `src/thesis_review_workflow/structured_evidence.py`
- `src/thesis_review_workflow/report_calibration.py`
- `src/thesis_review_workflow/cli/check_report_calibration.py`
- `src/thesis_review_workflow/cli/check_opponent_report.py`
- `src/thesis_review_workflow/work_artifacts.py`
- `scripts/record-theses-checker-summary`
- `scripts/check-theses-checker-summary`
- `src/thesis_review_workflow/cli/record_theses_checker_summary.py`
- `src/thesis_review_workflow/cli/check_theses_checker_summary.py`
- `scripts/BUILD`
- `src/thesis_review_workflow/cli/BUILD`
- `src/thesis_review_workflow/commands.py`
- private-artifact, manifest, review-wave, closeout, and command-surface checks
  where needed
- focused tests such as `tests/test_theses_checker_summary.py`,
  `tests/test_structured_evidence.py`, `tests/test_work_artifacts.py`,
  `tests/test_opponent_report.py`, `tests/test_report_calibration.py`, and
  `tests/test_workflow_python_contracts.py`

Work:

- Add `work/theses_checker_summary.json` as a known private work artifact.
- Add `record-theses-checker-summary` as the chat-first operator helper that
  normalizes a saved, pasted, or operator-transcribed FIT Theses Checker result
  into `work/theses_checker_summary.json`.
- Add a structural validator for the checker summary. It should validate schema,
  safe source refs, hashes, current rendered-PDF binding or typed limitation,
  numeric normostrany value, threshold/status fields, producer metadata, and
  limitations. It must not infer normostrany from raw PDF text or PDF page
  count.
- Before adding any other field or schema, audit whether the same information is
  already owned by `work/context/claim_review_basis.json`,
  `work/context/evidence_capsules.json`, `work/evidence_requirements.json`,
  `work/current_evidence_snapshot.json`, `work/quantitative_claims.json`,
  `outputs/literature_citation_review.md`, `outputs/code_consistency.md`, or
  `outputs/code_quality_review.md`. Reference or extend the owner instead of
  creating duplicate state.
- Extend `work/opponent_report_trace.json` validation according to the V1 trace
  required-controls and materiality-bound references table above. Each new field
  must be a compact report-facing ref or control, not a duplicate of role-owned
  review content.
- Make technical-report-scope basis require `work/theses_checker_summary.json`
  for the normal final opponent-report route. Permit a typed limitation only
  when the operator explicitly accepts proceeding without the checker result.
- Keep deterministic validation structural: fields, enums, safe refs, hashes,
  non-empty evidence refs where required, and consistency with existing trace
  item ids. Do not parse raw prose semantically.
- Extend `work/report_calibration_basis.json` only where it naturally controls
  report style, point/grade interval, question count, public-report length
  class, compression priorities, private-comment requirements, or profile
  application. Preserve the hard `calibration_scope: opponent_report` invariant
  and do not route this basis into supervisor-report workflows.
- Integrate `work/theses_checker_summary.json` into manifest/check target and
  closeout surfaces only as supporting private evidence for technical-report
  scope; do not make it a public report attachment.
- Add migration/rollout behavior deliberately. Since this is an experimental
  repo, prefer updating the current contract over carrying broad fallback
  behavior.

Verification:

```bash
PANTS_CONCURRENT=false pants test tests/test_theses_checker_summary.py tests/test_structured_evidence.py tests/test_work_artifacts.py tests/test_opponent_report.py tests/test_report_calibration.py tests/test_workflow_python_contracts.py
scripts/smoke-theses-checker-summary
scripts/smoke-opponent-report
scripts/smoke-opponent-closeout
scripts/smoke-report-calibration
scripts/smoke-package-workflow-tools
git diff --check
scripts/check-private
scripts/check-scripts
```

### Slice 4 - Packet And Draft Route Integration

Ensure agents see the stronger contract and the generated draft carries it to
the right place.

Expected paths:

- `src/thesis_review_workflow/opponent_packets.py`
- `src/thesis_review_workflow/review_packets.py`
- `src/thesis_review_workflow/cli/draft_opponent_report.py`
- `src/thesis_review_workflow/cli/export_opponent_report.py` only if clean
  export needs explicit stripping or preservation rules
- `.agents/skills/thesis-opponent-materials/SKILL.md`
- `.agents/skills/thesis-opponent-report-review/SKILL.md`

Work:

- Add packet sections that point role agents to assignment coverage, checked
  scope, claim ledger, evidence-source matrix, evaluation-claim review,
  scaling-claim review, Theses Checker summary, third-party/authorship checks,
  contribution-boundary checks, media/visual status, citation-support checks,
  deployment readiness, technical-difficulty breakdown, uncertainty items, and
  calibration controls.
- Route those sections to existing role-owned artifacts and skills first; do not
  create new packet roles or output files merely because the trace has a new
  section name.
- Update draft generation so internal pre-submission checks include the
  checked-scope, evidence-source, claim-ledger, claim-word, and
  scaling/contribution/citation/third-party cautions without leaking internal
  paths or confidence labels into clean public prose.
- Keep clean export compact and IS-oriented.
- Add or update a clean-report length/compression check. It should be a
  structural/procedural guard, not a prose judge: check declared length class,
  excessive question count, leaked audit-table patterns, private checklist
  absence, internal-only section classes, and source metadata absence from clean
  export. Semantic compression remains in the authorized review loop.
- Ensure report-review agents start from `## Synthesis Handoff` and the new
  trace sections before reopening full evidence.

Verification:

```bash
PANTS_CONCURRENT=false pants test tests/test_opponent_packets.py tests/test_draft_opponent_report.py tests/test_export_opponent_report.py tests/test_opponent_report.py tests/test_review_wave_gate.py
scripts/smoke-opponent-closeout
scripts/smoke-review-manifest
scripts/smoke-opponent-report
scripts/smoke-export-opponent-report
git diff --check
scripts/check-private
scripts/check-scripts
```

### Slice 5 - Profile Calibration Defaults

Promote only general style preferences into the public default profile; keep
personal or reviewer-specific calibration private.

Expected paths:

- `profiles/default.md`
- `profiles/README.md`
- `docs/opponent-review-workflow.md`

Work:

- Add generic opponent-report preferences for:
  - epistemic caution about unverified evidence;
  - assignment traceability;
  - rubric-specific comments;
  - balanced strengths and limitations;
  - explicit grade/prose calibration;
  - platform-difficulty calibration as a factor, not a substitute for evidence;
  - compact IS prose that references only the decisive evidence, not the full
    internal audit trail;
  - focused defense questions.
- Do not add preferences that are really one operator's private grading style.
  Those belong in `profiles/local/default.md` or another ignored local profile,
  after the operator explicitly asks for that private update.
- Keep profile text short enough that it remains a preference layer, not a
  second procedure manual.

Verification:

```bash
scripts/check-private
scripts/smoke-reviewer-profile
PANTS_CONCURRENT=false pants test tests/test_report_calibration.py tests/test_opponent_report.py
git diff --check
scripts/check-scripts
```

### Slice 6 - End-To-End Synthetic Proof

Prove the improved route without real case data.

Expected paths:

- `scripts/smoke-opponent-closeout`
- `scripts/smoke-report-calibration`
- focused pytest fixtures under tracked test paths
- `docs/opponent-review-workflow.md`
- `README.md` if operator guidance changed

Work:

- Add or update a synthetic opponent-report fixture that exercises:
  - assignment point mapping;
  - "not evidenced" wording;
  - a checked-scope limitation;
  - text/code/run/demo evidence-source separation;
  - media and visual claim status where an `inventoried_only` image or
    screenshot cannot support a visual-content claim by itself;
  - testing/evaluation interpretation;
  - precise evaluation criticism that credits existing partial evidence while
    naming missing repeatability fields;
  - strong claim words without matching metrics or comparator;
  - scaling/performance claim without a stress or boundary test;
  - required Theses Checker normostrany evidence for technical-report scope;
  - typed-limitation behavior when Theses Checker output is intentionally absent;
  - nearest-comparable-work limitation in literature;
  - citation-to-claim support warning separate from bibliography relevance;
  - third-party/authorship/licensing internal check state;
  - contribution-boundary wording for library/framework-supported work;
  - technical-difficulty breakdown into integration, algorithmic, platform, and
    evaluation dimensions;
  - clean-report compression from detailed internal evidence to compact IS
    paragraphs;
  - result-usability level such as demonstrator versus deployable tool;
  - deployment-readiness wording for build/install/run evidence, environment
    assumptions, operator documentation, and demo-only limitations;
  - private comment consistency with the same grade/point rationale and without
    new unsupported claims;
  - strengths-versus-grade tension;
  - focused defense questions;
  - calibration-aware canonical and clean checks.
- Run the relevant closeout path sequentially.
- Keep synthetic data generic and obviously artificial.

Verification:

```bash
PANTS_CONCURRENT=false pants test src/thesis_review_workflow:: tests::
scripts/smoke-theses-checker-summary
scripts/smoke-opponent-report
scripts/smoke-opponent-closeout
scripts/smoke-report-calibration
scripts/check-private
scripts/check-scripts
git diff --check
```

## Feedback Batch Log

### 2026-05-20 - First External Meta-Review Batch

Status: abstracted into this plan

Reusable themes:

- assignment fulfillment should be internally mapped point by point;
- FIT IS criteria should drive the substance of each report section;
- reports need careful wording for undocumented or unverified work;
- experiments need support/limit interpretation, not only existence checks;
- report-facing claims need an internal evidence ledger and evidence-strength
  state;
- claims about code, reproducibility, licensing, media, and auxiliary outputs
  require an explicit checked-scope basis;
- grade, points, IS selections, and prose should be self-checked together;
- strong parts should be stated and then calibrated against the limiting factors;
- defense questions should be fair, diagnostic, answerable, and focused.

Discarded as case-specific:

- concrete thesis topic;
- concrete assignment wording;
- concrete report points, grade, or alternative grade boundary;
- concrete literature/domain examples;
- concrete implementation architecture and experiment details.

### 2026-05-20 - Second External Meta-Review Batch

Status: abstracted into this plan

Reusable themes:

- technically risky platforms, hardware integration, or specialized runtime
  environments should influence difficulty and tolerance calibration, but not
  erase validation limits;
- report-scope comments should use FIT Theses Checker normostrany in the normal
  final-report path; without a checker result they should be limited to
  information value and allocation of attention unless the operator explicitly
  accepts a typed limitation;
- implementation claims should record whether they are supported by thesis text,
  code/static analysis, run/demo evidence, media inspection, or remain
  unverified;
- code analysis should feed the realization-output assessment with concise,
  report-relevant signals, not raw audit detail;
- testing should be classified as exploratory/formative, quantitative,
  comparative, reproducible, or deployment-like according to actual evidence;
- strong terms such as effectiveness, precision, usability, intuitiveness, and
  innovation need evidence, metrics, comparator, or softer public wording;
- literature assessment should consider nearest comparable systems and tools,
  not only general theory or framework documentation;
- result usability should distinguish demonstrator, research prototype, pilot
  tool, and practically deployable tool;
- third-party libraries, assets, AI assistance, generated code, licenses, and
  contribution boundaries are part of internal realization-output confidence
  when material;
- public report tone should match the point band: strong grades still need
  visible reservations, while reservations must not make the prose sound like a
  much lower grade.

Discarded as case-specific:

- concrete thesis topic and technical platform;
- concrete assignment wording and auxiliary artifacts;
- concrete code modules, libraries, frameworks, assets, and feature list;
- concrete participant counts, questionnaire values, and test observations;
- concrete report points, grade, and alternative grade boundaries;
- concrete defense-question wording tied to the case domain.

### 2026-05-20 - Third External Meta-Review Batch

Status: abstracted into this plan

Reusable themes:

- evaluation criticism should be precise: acknowledge concrete evidence that is
  present, then name missing repeatability, metric-definition, data-granularity,
  and uncertainty pieces;
- technical difficulty should distinguish integration breadth, algorithmic
  originality, implementation depth, platform/runtime risk, evaluation
  complexity, and domain/data complexity;
- implementation praise should separate a real integration contribution from
  standard capabilities of libraries, frameworks, platforms, or templates;
- scaling, robustness, performance, and "many item" claims need stress or
  boundary evidence, measured runtime/resource signals, a comparator, or softer
  wording;
- code analysis should provide report-relevant signals about structure,
  runtime/build boundaries, reproducibility, tests, dependencies, and licensing
  without leaking raw audit detail into the IS report;
- literature assessment should include targeted citation-to-claim support checks
  for material or suspicious citations, not only bibliography relevance and
  source availability;
- presentation review should separate navigation/structure from argument
  precision, contribution boundaries, and strength of conclusions;
- technical-report-scope discussion should distinguish normostrany evidence
  from information density and allocation of attention across theory,
  implementation, and evaluation.

Discarded as case-specific:

- concrete thesis topic, technology stack, libraries, frameworks, and runtime
  components;
- concrete assignment wording and artifact names;
- concrete participant counts, age ranges, devices, measured values, and graph
  descriptions;
- concrete citation identifiers and bibliography anomalies;
- concrete report points, grade, and grade-boundary alternatives;
- concrete defense-question wording tied to the case domain.

## Progress

- 2026-05-20: Plan created from a case-neutral abstraction of the first external
  meta-review batch. No case files or generated report outputs were edited.
- 2026-05-20: Added a second case-neutral feedback batch. The update expands
  evidence-source, platform-difficulty, normostrany, claim-word,
  third-party/authorship, and result-usability themes without naming or encoding
  the concrete case.
- 2026-05-20: Promoted operator feedback that FIT Theses Checker is normally
  available for final rounds. The plan now treats checker-derived normostrany as
  the required normal technical-report-scope input, with absence handled as an
  explicit typed limitation rather than PDF-page estimation.
- 2026-05-20: Added a third case-neutral feedback batch. The update expands
  evaluation-repeatability, contribution-boundary, scaling-claim,
  citation-support, technical-difficulty-breakdown, and information-density
  themes without retaining concrete case details.
- 2026-05-20: Added an explicit anti-bloat guard. New evidence fields are for
  internal precision; the clean IS report must remain compact and pass a
  compression-oriented review/check.
- 2026-05-20: Added architecture-fit and promotion rules. The plan now states
  that candidate trace names are not new standalone mechanisms, existing
  role-owned artifacts must be reused first, and durable lessons should be
  promoted to the narrowest appropriate layer.
- 2026-05-20: Ran role-split agent review across workflow architecture,
  opponent-report/FIT IS alignment, profile/calibration boundary,
  deterministic-checker/testability impact, and operator UX/report-length risk.
  Findings were folded into this plan: trace expansion is tiered into V1
  required controls versus materiality-bound references, Theses Checker intake
  gains a chat-first record helper and current-PDF binding, synthetic validation
  commands no longer use placeholders, private profile refresh is excluded from
  tracked TODO, and clean export exclusion of private/manual-check detail is now
  mandatory.
- 2026-05-20: Slice 1 started. Scope is limited to a tracked, case-neutral
  feedback-intake template and progress/audit updates in this plan.
- 2026-05-20: Slice 1 implemented and reviewed. The review found that the first
  template draft could look like a parallel path for concrete report feedback,
  so it was revised to require the existing ignored
  `notes/opponent-report-operator-feedback.md` to
  `work/opponent_report_revision_request.json` route before any tracked
  meta-learning promotion. The template now also names secondary routing for
  current-case report correction, current report calibration, private profile
  preference, historical calibration, public workflow rule, or no promotion.
- 2026-05-20: Slice 2 started. Scope is limited to skill/rubric/workflow-doc
  instruction upgrades; `AGENTS.md` and concrete case outputs remain untouched.
- 2026-05-20: Slice 2 implemented and agent-reviewed. Initial review found
  duplicated report-quality checklists across skills/docs and guidance that
  implied future trace/checker contracts already existed. The fix keeps the
  canonical checklist in `docs/opponent-review-workflow.md`, makes the three
  opponent skills reference it with role-specific obligations, and softens
  FIT Theses Checker wording to apply when a validated summary exists.
- 2026-05-20: Slice 3 started. Scope is Python command/artifact/schema work for
  Theses Checker summary and trace/calibration structural controls; Pants
  commands will be run serially.
- 2026-05-20: Slice 3 implemented and agent-reviewed. The slice adds
  `work/theses_checker_summary.json`, `record-theses-checker-summary`,
  `check-theses-checker-summary`, `opponent-report-trace-v2`, required
  report-quality trace controls, manifest/approval/closeout integration, and
  focused tests/smokes. Review findings fixed before commit: the checker
  summary check is required when bound, approval validation checks summary
  dependency freshness, summary refs require `status: checker_summary`, direct
  technical-report-scope wording requires a bound rendered PDF and categorical
  checker status, numeric thresholds reject non-finite/inconsistent values,
  checked PDF refs are constrained to `inputs/*.pdf`, and grade rationale or
  compression priorities were kept out of report-calibration controls unless
  they are explicit profile/operator preferences. Omen MCP semantic search
  found the intended touched symbols; Omen MCP complexity returned zero files
  for this repo path, so reproducible closeout used `pants run :omen`.

## Decision Log

- Keep the improvement anchored in existing trace, calibration, packet, export,
  and review contracts. A separate "report advice" artifact would add another
  authority and make closeout harder to reason about.
- Treat future external meta-reviews as advisory calibration input. They may
  reveal workflow gaps, but they are not evidence about a different thesis.
- Prefer semantic artifacts plus structural validators over deterministic
  free-text heuristics.
- Do not promote personal reviewer strictness into `profiles/default.md`.
  Public defaults may carry generic epistemic and rubric-alignment preferences;
  personal calibration stays in ignored local profiles.
- Treat platform or domain examples in external feedback as source evidence for
  a broader class of technically risky or specialized-runtime theses. Do not
  create one-off rules for a single platform.
- Put implementation-source certainty into structured trace state. Public
  report prose should stay concise, but the pipeline must know whether a claim
  came from text, static code analysis, execution/demo evidence, or a limitation.
- Treat FIT Theses Checker output as operator-provided evidence, not as a web
  automation dependency. The durable contract should be a private, validated,
  hash-bound round artifact that can be supplied from a saved export,
  screenshot, copied output, or future helper.
- Critique partial evidence proportionately. When a thesis includes some
  participant, environment, setup, graph, limitation, or code evidence, the
  report should not erase it; the useful criticism is normally about
  repeatability, auditability, metric definitions, or unsupported generalization.
- Treat contribution boundaries as a recurring implementation-quality concern:
  strong integration can be a valid student contribution, but report wording
  should not imply invention of standard library/framework behavior unless that
  is separately evidenced.
- Optimize for concise public judgments, not maximum evidence transfer. The
  pipeline should use structured evidence to choose better words, not to copy
  every supporting detail into the report.
- Avoid parallel mechanisms. Except for the Theses Checker summary, proposed
  additions should normally be fields, sections, references, or validations on
  existing artifacts rather than new workflow surfaces.
- For durable updates, route the change intentionally: skills for role
  behavior, docs for workflow contracts, profile files for reviewer preference,
  checkers for structure, and TODO for deferred automation.
- Treat trace growth as report-bound control state. Role-owned evidence remains
  authoritative; trace fields carry compact refs, wording modes, materiality
  decisions, typed limitations, and report controls.
- Keep Theses Checker support operator-driven and explicit. The workflow records
  a supplied checker result for the current rendered thesis PDF; it does not
  scrape the web app or infer normostrany from PDF page counts.
- Public default profile changes are limited to generic opponent-report
  preferences. Private reviewer calibration refreshes do not enter tracked
  plans or TODO.
- Slice 3 intentionally bumps `work/opponent_report_trace.json` to
  `opponent-report-trace-v2`. This experimental repo does not carry broad
  fallback behavior for older trace contracts; current rounds should regenerate
  the trace through the active opponent-report workflow.

## Final Audit

Plan checks run on 2026-05-20 after the first batch:

```bash
git diff --check                  # passed
scripts/check-private             # passed
scripts/check-scripts             # passed
```

Repeat checks after the second batch update:

```bash
git diff --check                  # passed
scripts/check-private             # passed
scripts/check-scripts             # passed
```

Repeat checks after the FIT Theses Checker input-contract update:

```bash
git diff --check                  # passed
scripts/check-private             # passed
scripts/check-scripts             # passed
```

Repeat checks after the third batch update:

```bash
git diff --check                  # passed
scripts/check-private             # passed
scripts/check-scripts             # passed
```

Repeat checks after the anti-bloat guard update:

```bash
git diff --check                  # passed
scripts/check-private             # passed
scripts/check-scripts             # passed
rg -n "compact|compression|public-report|clean IS|audit trail|length" \
  plans/opponent_report_quality_learning_plan.md
# reviewed; anti-bloat controls are present
```

Repeat checks after the architecture-fit/non-duplication update:

```bash
git diff --check                  # passed
scripts/check-private             # passed
scripts/check-scripts             # passed
rg -n "Architecture Fit|Non-Duplication|Promotion Rules|parallel|reuse|standalone|role-owned|narrowest" \
  plans/opponent_report_quality_learning_plan.md
# reviewed; reuse and promotion controls are present
```

Repeat checks after role-split agent review and plan hardening:

```bash
git diff --check                  # passed
scripts/check-private             # passed
scripts/check-scripts             # passed
rg -n "[<]synthetic|[<]round|[<]case|case-specific term[s]|not necessar[y]" \
  plans/opponent_report_quality_learning_plan.md
# passed; no matches
```

Slice 1 checks after template implementation and review fixes:

```bash
git diff --check                  # passed
scripts/check-private             # passed
scripts/check-scripts             # passed
```

Slice 2 checks after skill/doc implementation and review fixes:

```bash
git diff --check                  # passed
scripts/check-private             # passed
scripts/check-scripts             # passed
```

Slice 3 checks after schema/helper implementation, agent review, and fixes:

```bash
pants test tests/test_theses_checker_summary.py tests/test_structured_evidence.py tests/test_work_artifacts.py tests/test_opponent_report.py tests/test_opponent_calibration.py tests/test_review_manifest_helpers.py tests/test_review_approvals.py tests/test_report_calibration.py tests/test_workflow_python_contracts.py
# passed
pants lint src/thesis_review_workflow/theses_checker_summary.py src/thesis_review_workflow/structured_evidence.py src/thesis_review_workflow/review_approvals.py src/thesis_review_workflow/report_calibration.py src/thesis_review_workflow/cli/init_review_manifest.py src/thesis_review_workflow/cli/check_review_manifest.py tests/test_theses_checker_summary.py tests/test_structured_evidence.py tests/test_review_manifest_helpers.py tests/test_review_approvals.py
# passed
pants check src/thesis_review_workflow/theses_checker_summary.py src/thesis_review_workflow/structured_evidence.py src/thesis_review_workflow/review_approvals.py src/thesis_review_workflow/report_calibration.py src/thesis_review_workflow/cli/init_review_manifest.py src/thesis_review_workflow/cli/check_review_manifest.py src/thesis_review_workflow/work_artifacts.py src/thesis_review_workflow/cli/check_theses_checker_summary.py src/thesis_review_workflow/cli/record_theses_checker_summary.py
# passed
scripts/smoke-theses-checker-summary      # passed
scripts/smoke-opponent-report             # passed
scripts/smoke-opponent-closeout           # passed
scripts/smoke-export-opponent-report      # passed
scripts/smoke-report-calibration          # passed
scripts/smoke-package-workflow-tools      # passed
pants run :omen                           # passed; existing hotspot report, no critical exit
git diff --check                          # passed
scripts/check-private                     # passed
scripts/check-scripts                     # passed
```

No concrete case output under `cases/` has been edited.
