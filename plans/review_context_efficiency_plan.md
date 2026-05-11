# Thesis Review Context Efficiency Plan

Status: active
Created: 2026-05-11

## Goal

Reduce context growth and repeated mechanical work in multi-agent thesis-review
workflows without lowering review quality, role coverage, evidence standards, or
the required independent review loops.

This plan covers two workflow profiles:

- `supervisor_feedback`: student-facing supervisor feedback in
  `outputs/feedback_student.md`;
- `opponent_review`: internal opponent materials, opponent report trace, optional
  report draft review, and `outputs/feedback_k_posudku.md` when a report draft is
  reviewed.

The intended outcome is a packet-first, evidence-on-disk workflow where agents
receive only role-relevant inputs, return short status summaries instead of full
artifact bodies, and synthesis/review steps consume compact handoffs before
opening detailed evidence.

## Audit Base

Recent final supervisor-feedback rounds showed that the quality gates are mostly
right, but the execution path is too context-expensive:

- spawned agents were usually scoped correctly and did not need full-history
  forked context;
- context still grew because agent final messages sometimes repeated long
  artifact content already written to disk;
- the main session often had to read full evidence artifacts to extract a small
  number of synthesis points;
- evidence artifacts were useful but lacked a uniform compact handoff section;
- output-file existence and validator checks were partly manual after each agent
  wave;
- manifest and role-coverage registration required a long sequence of repeated
  commands;
- late-breaking diagnostic notes used during synthesis could become important
  evidence, but were not always registered as supporting work artifacts before
  closeout;
- final supervisor feedback could be substantively good but still fail the
  required student-feedback shape check after review, forcing a post-review
  structural edit and stale review hash repair;
- PR/code evidence can drift during a round, so synthesis packets need a fresh
  compact snapshot of head SHA, PR state, review decision, and checks rather
  than relying only on an earlier intake artifact;
- reviewer approval stored only in an agent final message is too manual to
  translate into provenance; the workflow needs a small structured approval
  record tied to the reviewed artifact hash;
- figure/media and typography workflows are valuable, but should be triggered by
  materiality and phase rather than by broad artifact presence alone;
- required presentation videos can be material even when they are not thesis
  figures; they need a lightweight media intake that records existence,
  metadata, access limitations, sampled visual evidence, and the boundary
  between "presentation artifact" and "runtime validation evidence";
- final-sprint hardware failures or substitute simulations need an explicit
  evidence-mode matrix before synthesis, otherwise feedback or materials can
  accidentally overstate what was real hardware, real data, virtual/simulated,
  code-only, or only shown in a video;
- recent operator-provided communications can be decisive evidence about blocked
  hardware, submission timing, external video links, or intended substitute
  tests; they should be captured as round notes or current-evidence snapshots
  before agents receive packets, not repeatedly pasted into prompts;
- quantitative/evaluation claims that look central need a compact sanity summary
  covering unit/scale, baseline, reproducibility, practical magnitude, and
  whether the conclusion is proportionate to the numbers;
- once the internal finish target has passed, supervisor synthesis packets should
  carry a final-sprint action budget: prioritize blockers and truthfulness fixes,
  and explicitly avoid broad redesign advice unless it affects correctness,
  assignment coverage, or reviewer confidence;
- final supervisor-feedback quality depends on coherence and readability, not
  just auditability.

The current opponent workflow already has more of the packet and closeout
surface than supervisor feedback. This plan should reuse and harden that surface,
not rebuild it as a second supervisor workflow:

- `scripts/opponent-preflight` and `scripts/opponent-closeout` already define
  the operator gates for opponent work;
- `scripts/prepare-opponent-packets <case-id> [round-id]` already writes
  `work/opponent_packets/*.md`;
- `scripts/check-opponent-materials <case-id> [round-id]` validates reviewed
  opponent materials;
- `scripts/check-opponent-report <case-id> [round-id]` validates the reviewed
  trace and any existing canonical report draft;
- `work/opponent_report_trace.json` is the deterministic bridge from reviewed
  materials to `scripts/draft-opponent-report`, not just provenance metadata;
- `outputs/oponent_podklady_revidovane.md` and
  `work/opponent_report_trace.json` must stay hash-bound so stale reviewed
  materials or stale trace state cannot silently feed a report draft.

Relevant current workflow surfaces:

- `plans/supervisor_workflow_closeout_plan.md` covers the planned supervisor
  preflight and closeout command bundle. This plan should not duplicate that
  work; it should feed the closeout bundle with better artifact contracts.
- `docs/opponent-review-workflow.md` documents the existing opponent packet,
  trace, and closeout flow.
- `.agents/skills/thesis-supervisor-feedback/SKILL.md` and
  `.agents/skills/thesis-supervisor-feedback-review/SKILL.md` define the
  supervisor workflow and its independent review pass.
- `.agents/skills/thesis-opponent-materials/SKILL.md`,
  `.agents/skills/thesis-opponent-materials-review/SKILL.md`, and
  `.agents/skills/thesis-opponent-report-review/SKILL.md` define opponent
  materials, reviewed materials, report trace, and report-review boundaries.
- `.agents/skills/thesis-code-consistency/SKILL.md`,
  `.agents/skills/thesis-code-quality-review/SKILL.md`,
  `.agents/skills/thesis-figure-media-review/SKILL.md`,
  `.agents/skills/thesis-typography-formal-review/SKILL.md`, and
  `.agents/skills/thesis-literature-citation-review/SKILL.md` define the main
  internal evidence workflows shared by both profiles.
- `src/thesis_review_workflow/opponent_packets.py`,
  `src/thesis_review_workflow/cli/prepare_opponent_packets.py`, and
  `tests/test_opponent_packets.py` are the existing opponent packet
  implementation.
- `.codex/agents/*.toml` defines the repo-local thesis reviewer profiles. At
  plan update time, the semantic reviewer roles are pinned to `gpt-5.5` with
  `model_reasoning_effort = "xhigh"` so they do not silently downshift from the
  operator's intended high-quality default.
- `scripts/init-review-manifest --run-checks <case-id> [round-id]`,
  `scripts/register-review-artifact`, `scripts/check-agent-coverage`, and
  `scripts/check-review-manifest --require-complete` provide the provenance
  contract.
- When available in the current Codex session, the Omen MCP server is an
  advisory code-quality signal for complexity, dead-code, churn, and ownership
  analysis. The existing
  `pants run :omen` target remains a developer-hygiene signal for this workflow
  repository, not an operator-facing case gate.
- `WORKFLOW_MEMORY.md` records promoted lessons, especially that operator flow
  should stay conversational, internal IDs should stay out of final prose,
  current PDFs are the rendered source of truth, and recurring review patterns
  should be promoted into workflow files rather than left as ad hoc memory.

Constraints:

- Do not weaken DEEP mode, role coverage, evidence anchors, or independent
  review requirements.
- Do not move private PDFs, source zips, code submissions, notes, or generated
  case outputs into tracked paths.
- Tracked packet templates and tests must use anonymized synthetic fixtures only.
- Do not introduce brittle semantic routing based on raw free-text substring
  matches. Materiality gates may inspect structured metadata, file classes,
  explicit assignment notes, generated evidence contracts, manifests, and
  bounded structural signals; semantic interpretation belongs to an authorized
  agent or human-authored artifact.
- Windows remains supported. New operator-facing helpers need Python/Pants/PEX
  command surfaces or packaged launchers, not WSL-only shell behavior.
- Run Pants commands sequentially.
- Prefer Serena for non-trivial Python navigation when practical.
- `README.md` top path remains chat-first prompt examples for supervisors and
  opponents. Packet-first behavior is an internal implementation detail and may
  appear only in lower-level docs or under-the-hood sections.
- Keep high-quality semantic reviewer roles on the strongest available model and
  high reasoning effort. Lower-cost models such as Spark may be used only for
  mechanical, validator-backed helper roles, never as the sole basis for
  evidence claims, grading/report calibration, or sendable wording.
- Code-quality review should use Omen MCP when available as advisory static
  analysis, but operator workflows must not require Omen to run.
- Supervisor deadline calibration applies only to `supervisor_feedback`.
  Opponent workflows use `scripts/check-round-ready`, grading/IS calibration,
  confidence labels, and human point/grade decisions.
- A generated `work/oponent_posudek_draft.md` is not sendable until a human
  calibrates points, grade, and wording, and the current trace/report checks
  pass.

## Scope

In scope:

- define shared workflow-profile concepts: `review workflow`, `artifact role`,
  `synthesis handoff`, `approval record`, and `wave gate`;
- define model/reasoning selection rules for semantic reviewer roles versus
  mechanical helper roles;
- define a strict subagent final-response contract for all thesis-review agents;
- add a deterministic wave-output gate that verifies expected files, validators,
  short handoffs, and whitespace hygiene before the main session continues;
- add role-specific supervisor feedback packet generation;
- harden the existing opponent packet generator instead of duplicating it;
- add required or strongly recommended synthesis handoff sections to internal
  evidence artifacts used by supervisor or opponent synthesis;
- add supervisor synthesis and final-review packets;
- add opponent synthesis, materials-review, report-trace, and report-review
  packets where the existing `work/opponent_packets/*.md` set is incomplete;
- add a fresh evidence snapshot for drift-prone external state such as GitHub PR
  status, checks, reviewed commit identity, reviewed-material hashes, and report
  trace hashes;
- add a pre-review final-artifact shape gate so reviewer agents approve files
  that already satisfy required validators;
- add structured review-approval capture tied to artifact and review-basis
  hashes;
- add materiality gates for figure/media, typography/formal,
  literature/citation, GitHub intake, and quantitative claim review routing;
- add a presentation-video/demo intake snapshot for rounds where the assignment,
  operator notes, or submitted inputs make a video or demo artifact material;
- add an evidence-mode matrix for cases where claims depend on a mix of real
  hardware, real operational data, virtual twins, simulations, video, logs, or
  code-only inspection;
- add a quantitative-claims handoff into synthesis packets so final artifacts
  can use metric findings without reopening the full audit unless needed;
- add supervisor final-sprint action-budget guidance;
- add opponent report-calibration guidance for defensible IS wording, confidence
  labels, grading intervals, defense questions, and manual checks;
- add Omen MCP guidance to code-quality review and packet contracts while
  preserving Omen as optional for operator use;
- reduce manual manifest/coverage work by extending or feeding the planned
  supervisor closeout bundle and the existing opponent closeout bundle;
- update skills/docs so agents use packets and short final messages by default.

## Non-goals

- changing student-facing feedback structure or tone goals;
- changing opponent materials/report structure, IS item list, or grading policy;
- removing required code consistency or code quality review for code-bearing
  rounds;
- removing figure/media, typography, literature, quantitative, or GitHub review
  when they are material;
- executing submitted code by default;
- replacing existing opponent preflight, opponent packet generation, opponent
  trace, draft-opponent-report, or opponent closeout workflows;
- implementing the full supervisor preflight/closeout bundle already covered by
  `plans/supervisor_workflow_closeout_plan.md`;
- automatically producing a sendable IS opponent report without human
  calibration;
- preserving compatibility with older `~/code/diplomky` workflows.

## Sequencing Boundary

This plan lands shared context-efficiency primitives first: synthesis handoffs,
wave gates, packet scaffolding, approval records, model/reasoning policy, and
closeout integration contracts. Materiality-aware packet enrichment, media/demo
intake, quantitative handoffs, and opponent report-calibration extensions should
remain narrow follow-up work inside this plan unless they are required to make
the shared packet/wave-gate contract correct.

Do not start broad optional-role packet generation before a recorded
materiality decision exists. Optional evidence packets are emitted only from an
explicit user request, formal skill trigger, mandatory code-bearing rule, or a
recorded review-materiality decision. Mandatory base packets and current
workflow gates may land first.

## Proposed Contracts

### Workflow Profiles

Shared infrastructure should treat supervisor and opponent flows as concrete
workflow profiles, not as separate ad hoc command families.

Each profile should define:

- readiness gate:
  - supervisor: `scripts/check-supervisor-ready <case-id> [round-id]`;
  - opponent: `scripts/check-round-ready <case-id> [round-id]`;
- packet directory:
  - supervisor: `work/supervisor_packets/`;
  - opponent: existing canonical `work/opponent_packets/`;
- required artifact roles and expected owned outputs;
- pre-review validators;
- final artifact validators;
- independent reviewer skill;
- closeout command or integration point;
- structured approval-record path.

Do not introduce both `work/packets/<workflow>/` and
`work/<workflow>_packets/` styles. This plan uses `work/supervisor_packets/` for
the new supervisor profile and keeps `work/opponent_packets/` because that path
is already canonical in opponent skills, docs, tests, and implementation.

### Model And Reasoning Selection

Semantic thesis-review roles should default to the strongest available model and
high reasoning effort. For the current repo-local Codex profiles, that means
`gpt-5.5` with `model_reasoning_effort = "xhigh"` for:

- thesis text and assignment review;
- thesis-code consistency review;
- code quality/design review;
- evidence calibration, synthesis review, and sendability checks.

Do not downshift these roles when they are the first or only semantic pass over
thesis text, submitted code, evidence artifacts, synthesis drafts, reviewed
materials, report traces, or report drafts.

The tracked `.codex/agents/*.toml` profiles currently cover only text review,
code consistency, code quality, and evidence calibration. Semantic roles without
a repo-local TOML profile, such as supervisor final review, opponent materials
review, and opponent report review, must carry the same strongest-model/high
reasoning requirement in their packet and skill prompts; do not imply TOML
pinning covers every semantic role.

`gpt-5.3-codex-spark` is a candidate only for mechanical, validator-backed work
that does not create evidence claims by itself, for example:

- inventorying packet inputs and expected outputs;
- summarizing deterministic validator results;
- manifest-shape triage;
- smoke-test log condensation;
- preparing wave-gate status messages.

Any Spark-produced helper output must be validated by deterministic checks and
consumed by a high-reasoning semantic role before it can influence feedback,
opponent materials, report wording, grade calibration, or final readiness.

### Omen Code-Quality Signal

Code-quality review should use the Omen MCP server when available to gather
advisory static-analysis signals:

- complexity and hotspot concentration;
- likely dead or unreachable code;
- churn and unstable areas when git history is available;
- ownership or bus-factor risks when repository history makes that meaningful.

Omen findings must be verified against concrete code evidence before becoming a
review finding. Absence of Omen, MCP registration failure, or an unsupported code
root is a limitation, not a blocker. Supervisor and opponent operator workflows
must not require Omen to run.

### Subagent Final Response Contract

Every workflow agent that owns files should return only:

- files written or changed;
- top 3-5 findings, verdicts, or risks;
- commands/checks run;
- explicit limitations;
- whether expected output validation passed.

Agents should not paste full Markdown artifacts into their final response when
those artifacts are already written to disk. The main session should inspect the
file only when the short summary, expected-output gate, validator output, or a
review challenge shows a risk.

### Wave Output Gate

After each agent wave, the main session or helper command should verify:

- each role-owned output path exists and is non-empty;
- the relevant checker passes, when one exists;
- the artifact contains a compact synthesis handoff section when it will feed
  synthesis;
- `git diff --check -- <owned-paths>` passes;
- missing or mismatched expected outputs are hard failures, even if the agent
  final message claims success.

The core command should be workflow-neutral, backed by typed workflow specs.
Thin operator commands can call that core, for example:

- `scripts/check-supervisor-wave <case-id> [round-id]`;
- `scripts/check-opponent-wave <case-id> [round-id]`;
- or `scripts/check-review-wave --workflow <profile> <case-id> [round-id]` if a
  single operator command stays clearer.

Track-specific validators must remain explicit:

- supervisor final review should receive a draft that already passes
  draft-path-aware feedback language/output validators. The reviewed
  `outputs/feedback_student.md` still must pass the normal
  `scripts/check-feedback-language` and `scripts/check-feedback-output` gates
  after the independent review writes it.
- opponent materials draft review should start from an existing non-empty
  `work/oponent_podklady_draft.md` or `outputs/oponent_podklady.md` that passes
  hygiene checks. `scripts/check-opponent-materials` is a post-review gate for
  `outputs/oponent_podklady_revidovane.md`, not a pre-review draft gate.
- opponent trace/report work cannot proceed as ready until
  `scripts/check-opponent-report` passes for the current
  `work/opponent_report_trace.json` and any existing canonical
  `work/oponent_posudek_draft.md`;
- opponent report review must not treat a generated draft as sendable unless a
  human has calibrated points, grade, and wording in the canonical draft text or
  in a future structured `human_calibration` trace object.

### Synthesis Handoff

Internal evidence artifacts that may feed supervisor or opponent synthesis
should include a short section with a stable heading such as
`## Synthesis Handoff`.

The handoff should include:

- workflow/audience: `supervisor_feedback`, `opponent_materials`,
  `opponent_report_review`, or `standalone_internal`;
- findings to use in synthesis;
- findings not to use or overstate;
- P0/P1 evidence anchors;
- limitations and manual checks;
- one-line phase or report calibration.

For `supervisor_feedback`, include the student-facing action implied by each
important technical finding.

For `opponent_materials`, include the impact on report wording, grade/IS item
calibration, confidence label, and possible report formulation where useful.

For `opponent_report_review`, include report risk, suggested rewrite, and
point/grade consistency impact.

The synthesis step should read this handoff first and open the full artifact
only for P0/P1 verification, contradiction checks, grading/report calibration,
or final-review challenges. Raw technical diagnostics should be translated
before synthesis. For example, a low-level planning warning, fixture issue, or
API-boundary smell should become either a student action in supervisor mode or a
report-impact statement/manual check in opponent mode.

### Evidence Freshness Snapshot

For drift-prone external evidence, packets should include a compact current
snapshot captured as close as practical to synthesis:

- source identity such as repository, PR number, head SHA, branch, and import
  timestamp;
- PR state, draft status, merge state, review decision, and check summary;
- whether a targeted local smoke or diagnostic note was run after intake;
- absolute deadline dates and any unresolved ambiguity in operator-provided
  date notes;
- for opponent materials/report work, current reviewed-materials hash, trace
  hash, draft hash when present, and human calibration state;
- limitations about what was not refreshed.

Markdown snapshot packets are rendered views only. Any hash, freshness, or
external-state fact that drives a readiness decision must come from existing
structured/hash-bound artifacts or a structured source such as
`work/current_evidence_snapshot.json` with schema validation. The rendered
snapshot should be small enough to include in role packets and should point to
full intake/log artifacts on disk for verification. It must not infer semantic
conclusions from raw thesis or code text; it records structured state and
explicitly authored diagnostic notes.

### Presentation Video And Demo Intake

When a thesis assignment, operator notes, or submitted inputs make a video/demo
artifact material, create a compact ignored intake artifact before synthesis.
The artifact should record:

- file or link identity, size/duration/codec when available, and hash for local
  files;
- whether public or anonymous access was verified, not verified, or unavailable;
- sampled-frame or thumbnail anchors when visual inspection was performed;
- what the video/demo visibly supports;
- what it does not prove, especially hardware writes, simulator correctness,
  economic outcomes, or several-installation validation;
- the workflow-specific action:
  - supervisor: student-facing action such as "add final public URL" or "state
    what is real versus simulated";
  - opponent: report/manual-check impact such as "video supports presentation
    of a demo, not physical-hardware validation."

This intake feeds `thesis-figure-media-review` when material, but it should not
force a broad figure audit when the only material media question is whether a
required presentation video exists and what evidence boundary it has.

### Evidence-Mode Matrix

For final or report-facing rounds where the thesis relies on a mix of real
hardware, submitted code, generated logs, video, virtual twins, simulations, or
historical data, the synthesis packet should contain a small evidence-mode
matrix:

| Claim area | Real hardware | Real data | Virtual/simulated | Code-only | Video/log support | Safe wording |
|---|---|---|---|---|---|---|

The matrix should be generated from explicit notes, evidence artifacts,
structured review outputs, and agent-authored findings. It must not be a
deterministic semantic inference over raw thesis text. Its purpose is to keep
final artifacts honest: "showed/presented", "partially verified", "tested on
real data", and "verified on physical hardware" are different claims.

### Quantitative Claims Handoff

When `work/quantitative_claims.json` or an equivalent structured evidence
artifact exists, synthesis packets should include a compact handoff:

- central metrics and where they appear;
- whether source data and computation are reproducible from submitted inputs;
- unit/scale sanity and practical magnitude;
- baseline status;
- conclusion calibration: supported, needs context, overclaimed, or
  unsupported;
- supervisor student-facing action for each P0/P1 issue, or opponent
  grade/report impact and confidence label.

This avoids rereading full metric sections during synthesis while preserving the
semantic sanity review required by `AGENTS.md`.

### Supervisor Final-Sprint Action Budget

Supervisor synthesis packets should include deadline phase and a short action
budget. After the recommended internal finish date, default to:

- submission blockers;
- truthfulness and assignment-coverage fixes;
- broken links, placeholders, and render defects;
- minimal reproducibility/documentation needed by the reviewer;
- only small code fixes that are safer than merely documenting the limitation.

This keeps student-facing feedback coherent and usable under deadline pressure
instead of turning a final submission check into a redesign backlog.

### Opponent Report Calibration Budget

Opponent synthesis and report-review packets should include a compact
calibration budget:

- grade-impacting findings need evidence anchors and confidence labels;
- IS-item formulations should separate assignment fulfillment, thesis quality,
  realization output, formal presentation, literature, and usefulness;
- grading calibration should use intervals and rationale, not false precision;
- defense questions should be fair, answerable, and tied to important issues;
- manual checks should be explicit instead of hidden behind confident prose;
- generated report drafts remain internal until human point/grade calibration
  and `scripts/check-opponent-report` pass.

This prevents supervisor-style "student action" language from leaking into
opponent materials and keeps report-facing prose defensible.

### Final Artifact Shape Gate And Approval Record

Before an independent reviewer approves a final artifact, the reviewed draft
should already pass the profile-specific required validators. Material edits
after approval reopen the artifact as draft and require a fresh review or a
recorded typed exception.

Structured review records should live under ignored round work, for example:

- `work/reviews/feedback_student_review.json`;
- `work/reviews/opponent_materials_review.json`;
- `work/reviews/opponent_report_review.json`.

Each record should contain:

- workflow profile and reviewer role;
- reviewer agent or human reviewer identifier;
- verdict, blocking findings count, and optional notes;
- reviewed artifact path and SHA-256;
- review-basis path and SHA-256;
- checks observed by the reviewer;
- limitations;
- timestamp.

The human-readable agent final message may still be concise, but closeout should
read the structured approval record when registering manifest provenance.

### Opponent Trace Contract

`work/opponent_report_trace.json` must remain a first-class contract in any
context-efficiency work. It should preserve:

- reviewed-materials path and SHA-256;
- IS-item formulations derived from reviewed materials;
- defense questions;
- uncertainty ledger and manual checks;
- current reviewed-materials hash;
- optional `human_calibration` state for points, grade, and final report wording
  when the workflow chooses to track it structurally; otherwise human
  calibration remains validated through the canonical report draft text and
  `scripts/check-opponent-report`;
- source refs for any calibration, reading packet, comparison, or revision
  request that influenced the trace.

Packetization must not replace the trace with prose summaries. The trace is the
deterministic input to `scripts/draft-opponent-report` and the freshness anchor
for `scripts/check-opponent-report`.

### Role Packets

Generated role packets should be round-local ignored artifacts. They should
contain only the role's relevant context and exact paths to open when deeper
inspection is needed. Each packet should include the expected model/reasoning
class for the role and should distinguish semantic review roles from mechanical
helper roles. Code-quality packets should also say whether Omen MCP was
available, which Omen checks were run or skipped, and how to treat those signals
as advisory evidence.

Candidate supervisor packet outputs:

- `work/supervisor_packets/text_assignment.md`
- `work/supervisor_packets/code_consistency.md`
- `work/supervisor_packets/code_quality.md`
- `work/supervisor_packets/figure_media.md`
- `work/supervisor_packets/literature_citation.md`
- `work/supervisor_packets/typography_formal.md`
- `work/supervisor_packets/evidence_calibration.md`
- `work/supervisor_packets/synthesis.md`
- `work/supervisor_packets/final_review.md`
- `work/supervisor_packets/current_evidence_snapshot.md`

Existing opponent packet outputs to preserve and harden:

- `work/opponent_packets/text_structure_assignment.md`
- `work/opponent_packets/code_consistency.md`
- `work/opponent_packets/code_quality.md`
- `work/opponent_packets/figure_media.md`
- `work/opponent_packets/literature_citation.md`
- `work/opponent_packets/typography_formal.md`
- `work/opponent_packets/evidence_calibration.md`
- `work/opponent_packets/synthesis.md`

Candidate opponent packet additions:

- `work/opponent_packets/current_evidence_snapshot.md`
- `work/opponent_packets/materials_review.md`
- `work/opponent_packets/report_trace.md`
- `work/opponent_packets/report_review.md`

Packets must stay case-local and gitignored. Tracked templates may describe the
shape but must not include real case content.

## Slices

### Slice 1 - Plan Review And Shared Subagent Output Contract

- Status: completed
- Proposed commit message: `docs(workflow): plan thesis review context efficiency`
- Expected paths:
  - `plans/review_context_efficiency_plan.md`
  - `.codex/agents/thesis-text-reviewer.toml`
  - `.codex/agents/thesis-code-consistency-reviewer.toml`
  - `.codex/agents/thesis-code-quality-reviewer.toml`
  - `.codex/agents/thesis-evidence-calibrator.toml`
  - `.agents/skills/thesis-supervisor-feedback/SKILL.md`
  - `.agents/skills/thesis-supervisor-feedback-review/SKILL.md`
  - `.agents/skills/thesis-opponent-materials/SKILL.md`
  - `.agents/skills/thesis-opponent-materials-review/SKILL.md`
  - `.agents/skills/thesis-opponent-report-review/SKILL.md`
  - `.agents/skills/thesis-code-consistency/SKILL.md`
  - `.agents/skills/thesis-code-quality-review/SKILL.md`
  - `.agents/skills/thesis-github-code-intake/SKILL.md`
  - `.agents/skills/thesis-figure-media-review/SKILL.md`
  - `.agents/skills/thesis-typography-formal-review/SKILL.md`
  - `.agents/skills/thesis-literature-citation-review/SKILL.md`
  - `.agents/skills/thesis-revision-diff/SKILL.md`
  - `docs/agent-scheduling.md`
- Tasks:
  - Review this plan with agents before implementation.
  - Add the subagent final-response contract to the relevant skills.
  - Include shared evidence-intake and revision-diff skills because their
    outputs can feed supervisor feedback, opponent materials, and standalone
    evidence workflows.
  - Set repo-local semantic thesis reviewer profiles to `gpt-5.5` with
    `model_reasoning_effort = "xhigh"` unless an explicit future config change
    replaces that policy.
  - Document that `gpt-5.3-codex-spark` is reserved for mechanical,
    validator-backed helper roles, not semantic review or final synthesis.
  - State that file claims from agent final messages must be verified by
    expected-output checks.
  - Clarify that agents should write full evidence to owned files and return
    compact summaries only.
  - Preserve the existing concurrency limit and independent review rules.
  - Distinguish supervisor student-facing synthesis from opponent materials,
    trace, and report-review synthesis.
  - Add Omen MCP as an advisory code-quality signal, not an operator workflow
    dependency.
- Verification:
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 2 - Shared Wave Output Gate

- Status: completed
- Proposed commit message: `feat(workflow): add review wave output gate`
- Expected paths:
  - `src/thesis_review_workflow/review_wave_gate.py`
  - `src/thesis_review_workflow/cli/check_review_wave.py`
  - `src/thesis_review_workflow/cli/check_feedback_language.py`
  - `src/thesis_review_workflow/cli/check_feedback_output.py`
  - `src/thesis_review_workflow/cli/check_opponent_report.py`
  - `src/thesis_review_workflow/cli/BUILD`
  - `src/thesis_review_workflow/commands.py`
  - `scripts/check-review-wave`
  - `scripts/BUILD`
  - `scripts/smoke-review-wave`
  - `tests/test_review_wave_gate.py`
  - `tests/test_workflow_python_contracts.py`
- Tasks:
  - Define typed workflow specs for supervisor feedback, opponent materials,
    opponent trace/report, and opponent report review.
  - Define typed expected-output records for role, path, optional checker,
    optional synthesis-handoff heading, owned paths for `git diff --check`, and
    approval-record expectations.
  - Implement a read-only command that validates one wave from a small JSON spec
    or a workflow-profile argument.
  - Check file existence, non-empty content, checker pass/fail,
    approval-record shape, and whitespace hygiene for owned paths.
  - Stage synthesis-handoff enforcement: before Slice 3, allow the wave gate to
    warn on missing handoffs; after Slice 3 lands, make required handoff
    presence enforceable only for artifacts marked as synthesis inputs.
  - Add draft-path-aware feedback validation, for example
    `scripts/check-feedback-language --artifact work/feedback_student_draft.md`
    and `scripts/check-feedback-output --artifact work/feedback_student_draft.md`,
    so supervisor drafts can be shape-checked before independent review without
    treating `outputs/feedback_student.md` as already reviewed.
  - Support an opponent-materials draft gate for
    `work/oponent_podklady_draft.md` or `outputs/oponent_podklady.md` that
    checks existence, non-empty content, and hygiene before independent review.
  - Keep `scripts/check-opponent-materials` as the post-review gate for
    `outputs/oponent_podklady_revidovane.md`.
  - Support an opponent trace/report gate requiring `check-opponent-report` and
    either concrete human-calibrated points/grade in the canonical draft text or
    a future structured `human_calibration` trace object before a generated
    report draft can be treated as sendable.
  - Update the packaged workflow command registry and verify native Windows
    launcher coverage via `scripts/smoke-package-workflow-tools`.
  - Add smoke coverage with synthetic ignored-case fixtures.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - `pants test tests/test_review_wave_gate.py tests/test_workflow_python_contracts.py`
  - `scripts/smoke-review-wave`
  - `scripts/smoke-package-workflow-tools`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 3 - Synthesis Handoff Contract

- Status: pending
- Proposed commit message: `feat(workflow): add synthesis handoff summaries`
- Expected paths:
  - `.agents/skills/thesis-code-consistency/SKILL.md`
  - `.agents/skills/thesis-code-quality-review/SKILL.md`
  - `.agents/skills/thesis-figure-media-review/SKILL.md`
  - `.agents/skills/thesis-typography-formal-review/SKILL.md`
  - `.agents/skills/thesis-literature-citation-review/SKILL.md`
  - `.agents/skills/thesis-supervisor-feedback/SKILL.md`
  - `.agents/skills/thesis-opponent-materials/SKILL.md`
  - `.agents/skills/thesis-opponent-materials-review/SKILL.md`
  - `.agents/skills/thesis-opponent-report-review/SKILL.md`
  - `src/thesis_review_workflow/internal_evidence_validators.py`
  - `tests/test_internal_evidence_validators.py`
- Tasks:
  - Add a compact `Synthesis Handoff` section to internal evidence output
    templates.
  - Teach validators to require or warn on missing handoffs only for artifacts
    that feed synthesis.
  - Keep standalone evidence review requirements unchanged.
  - Ensure handoffs include workflow/audience, use, do-not-overstate, anchors,
    limitations, phase/report calibration, and either student action or
    opponent report/grade impact.
  - Add guidance that low-level diagnostic details should be translated into
    one actionable synthesis point unless the raw detail itself is needed for
    technical truth.
  - Update supervisor and opponent synthesis instructions to read handoffs
    first.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests::`
  - `pants check src/thesis_review_workflow:: tests::`
  - `pants test tests/test_internal_evidence_validators.py`
  - `scripts/smoke-internal-evidence-validators`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 4 - Packet Scaffolding And Workflow Adapters

- Status: pending
- Proposed commit message: `feat(workflow): scaffold review role packets`
- Expected paths:
  - `src/thesis_review_workflow/supervisor_packets.py`
  - `src/thesis_review_workflow/opponent_packets.py`
  - `src/thesis_review_workflow/cli/prepare_supervisor_packets.py`
  - `src/thesis_review_workflow/cli/prepare_opponent_packets.py`
  - `src/thesis_review_workflow/cli/BUILD`
  - `src/thesis_review_workflow/commands.py`
  - `scripts/prepare-supervisor-packets`
  - `scripts/prepare-opponent-packets`
  - `scripts/BUILD`
  - `scripts/smoke-supervisor-packets`
  - `scripts/smoke-opponent-packets`
  - `tests/test_supervisor_packets.py`
  - `tests/test_opponent_packets.py`
  - `tests/test_workflow_python_contracts.py`
- Tasks:
  - Generate mandatory supervisor role packets under
    `work/supervisor_packets/`.
  - Keep existing opponent role packets under `work/opponent_packets/` and
    extend them in place.
  - Do not emit optional evidence packets from broad artifact presence in this
    slice. Optional packets are emitted only from explicit user request, formal
    skill trigger, mandatory code-bearing rules, an existing structured
    evidence artifact, or a recorded review-materiality decision.
  - For supervisor packets, include deadline context, assignment summary,
    previous-feedback index, prior-feedback deltas, input inventory, prepared
    code roots, current-evidence snapshot, final-sprint action budget, and exact
    "open this only if needed" references.
  - For opponent packets, include assignment/IS rubric coverage, confidence
    labels, reviewer-profile preferences, grading calibration context, defense
    question support, reviewed-materials hash, trace hash, and report-review
    constraints.
  - Include role model/reasoning recommendations so semantic roles stay on
    `gpt-5.5`/`xhigh` and only mechanical helper roles can opt into Spark.
  - Include Omen MCP availability and advisory check status in code-quality
    packets without making Omen a hard prerequisite.
  - Generate or refresh a `current_evidence_snapshot` packet for drift-prone
    inputs such as PR metadata/checks, current code head identity, targeted
    smoke-test notes, reviewed-material hashes, trace hashes, and explicit
    limitations. If hash/freshness data affects readiness, render it from
    existing structured/hash-bound artifacts or a new
    `work/current_evidence_snapshot.json`; Markdown packets are not freshness
    validators by themselves.
  - Capture operator-provided late communications as referenced notes or
    structured snapshot entries before role packets are generated.
  - Render presentation-video/demo intake, evidence-mode matrices, and
    quantitative-claims handoffs only when the required structured artifact or
    materiality decision already exists. Full materiality routing lands in
    Slice 5.
  - Normalize deadline/date context into absolute dates when possible and flag
    unresolved ambiguity for synthesis rather than letting relative-date
    contradictions leak into final artifacts.
  - Generate synthesis, final-review, materials-review, report-trace, and
    report-review packets after evidence artifacts exist and after the relevant
    shape gate passes.
  - Include late-breaking diagnostic notes as packet references only if they are
    registered or registerable as supporting work artifacts.
  - Add manifest/supporting-work registration hooks or clear closeout
    integration points.
  - Update the packaged workflow command registry and verify native Windows
    launcher coverage via `scripts/smoke-package-workflow-tools`.
  - Ensure packets contain no tracked private data and are never force-added.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - `pants test tests/test_supervisor_packets.py tests/test_opponent_packets.py tests/test_workflow_python_contracts.py`
  - `scripts/smoke-supervisor-packets`
  - `scripts/smoke-opponent-packets`
  - `scripts/smoke-package-workflow-tools`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 5 - Materiality Gates For Optional Evidence Roles

- Status: pending
- Proposed commit message: `feat(workflow): add review evidence materiality gates`
- Expected paths:
  - `src/thesis_review_workflow/review_materiality.py`
  - `src/thesis_review_workflow/cli/check_review_materiality.py`
  - `src/thesis_review_workflow/cli/BUILD`
  - `src/thesis_review_workflow/commands.py`
  - `scripts/check-review-materiality`
  - `scripts/BUILD`
  - `tests/test_review_materiality.py`
- Tasks:
  - Add a deterministic advisory gate that recommends whether figure/media,
    typography/formal, literature/citation, GitHub intake, and quantitative
    claim roles are material for the selected workflow profile.
  - Base routing on phase, explicit notes, assignment requirements, structured
    manifests, existing output artifacts, media/code/GitHub artifact classes,
    and validated generated evidence, not semantic raw-text keyword decisions.
  - Treat assignment-required presentation video/demo artifacts as a narrow
    media materiality trigger: verify existence/access/evidence boundary without
    escalating to a broad visual audit unless thesis figures or visual claims
    are also material.
  - Treat structured quantitative-claim artifacts and explicit evaluation
    tables as synthesis materiality signals, with the same no-free-text-routing
    constraint as other gates.
  - Keep code consistency and code quality mandatory when code evidence exists.
  - In supervisor mode, express materiality as student-action priority.
  - In opponent mode, express materiality as report defensibility, confidence
    label, IS-item, grade-calibration, or manual-check impact. Literature review
    must not become student coaching in opponent mode.
  - Record materiality decisions as advisory support for packet generation and
    synthesis; do not treat "not material" as permission to ignore an explicit
    user request or formal skill trigger.
  - After materiality decisions exist, enrich packet generation so optional
    evidence packets are emitted only for explicit user requests, formal skill
    triggers, mandatory code-bearing rules, existing structured evidence, or
    recorded materiality decisions.
  - Update the packaged workflow command registry and verify native Windows
    launcher coverage via `scripts/smoke-package-workflow-tools`.
  - Add synthetic fixture coverage for final, non-final, code-bearing, video,
    figure-heavy, report-review, and text-only rounds.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - `pants test tests/test_review_materiality.py`
  - `scripts/smoke-package-workflow-tools`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 6 - Closeout Integration And Role Registration

- Status: pending
- Proposed commit message: `feat(workflow): streamline review provenance registration`
- Expected paths:
  - `plans/supervisor_workflow_closeout_plan.md`
  - `docs/opponent-review-workflow.md`
  - `src/thesis_review_workflow/cli/opponent_closeout.py`
  - `src/thesis_review_workflow/cli/check_review_manifest.py`
  - `src/thesis_review_workflow/review_manifest.py`
  - `src/thesis_review_workflow/agent_coverage.py`
  - `src/thesis_review_workflow/structured_evidence.py`
  - `src/thesis_review_workflow/work_artifacts.py`
  - `tests/test_opponent_report.py`
  - `tests/test_review_manifest_helpers.py`
  - `tests/test_structured_evidence.py`
  - `tests/test_work_artifacts.py`
- Tasks:
  - Coordinate with `plans/supervisor_workflow_closeout_plan.md` rather than
    duplicating the supervisor closeout command. This slice may only add
    integration data consumed by `supervisor-closeout` after
    `plans/supervisor_workflow_closeout_plan.md` Slices 1-3 land. Until then,
    do not edit `src/thesis_review_workflow/supervisor_checks.py` here; record
    required manifest/approval inputs as an integration contract.
  - Coordinate with existing `scripts/opponent-closeout` rather than replacing
    opponent closeout.
  - Add data structures or helper functions that can register common review
    artifacts from role outputs, synthesis handoffs, packets, traces, and review
    approvals.
  - Reduce the need for repeated manual `scripts/register-review-artifact`
    invocations after a normal supervisor or opponent run.
  - Auto-register supporting work artifacts referenced by final evidence,
    including late diagnostic notes, current-evidence snapshots, packet inputs,
    reviewed-material traces, and report-revision sources, or fail with a
    precise message before `check-review-manifest`.
  - Register structured final-review approvals from
    `work/reviews/feedback_student_review.json`,
    `work/reviews/opponent_materials_review.json`, and
    `work/reviews/opponent_report_review.json`.
  - Define and validate `work/reviews/*_review.json` as round-local supporting
    work artifacts, including stale-hash checks against the reviewed artifact
    and review basis, before closeout consumes them.
  - If human calibration becomes structural, add an optional
    `human_calibration` object in `work/opponent_report_trace.json` and
    hash-bind it to the draft/review record. Otherwise state that human
    calibration is validated only through the canonical draft text and
    `scripts/check-opponent-report`.
  - Treat any material edit to a reviewed sendable or reliance artifact as a
    stale review: closeout should either require a fresh review or record a
    typed exception, never silently patch `reviewed_hash`.
  - Preserve explicit generator and reviewer roles, artifact hashes,
    `covered_by_synthesis`, `used_findings`, limitations, review-basis hash,
    trace hash, and human-calibration state where relevant.
  - Keep manifest/coverage checks strict; automation should fill accurate
    metadata, not bypass validation.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests::`
  - `pants check src/thesis_review_workflow:: tests::`
  - `pants test tests/test_opponent_report.py tests/test_review_manifest_helpers.py tests/test_structured_evidence.py tests/test_work_artifacts.py`
  - `scripts/smoke-agent-coverage`
  - `scripts/smoke-review-manifest`
  - `scripts/smoke-opponent-report`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 7 - Documentation And Operator Flow

- Status: pending
- Proposed commit message: `docs(workflow): document packet-first review flow`
- Expected paths:
  - `README.md`
  - `docs/agent-scheduling.md`
  - `docs/opponent-review-workflow.md`
  - `.agents/skills/thesis-supervisor-feedback/SKILL.md`
  - `.agents/skills/thesis-supervisor-feedback-review/SKILL.md`
  - `.agents/skills/thesis-opponent-materials/SKILL.md`
  - `.agents/skills/thesis-opponent-materials-review/SKILL.md`
  - `.agents/skills/thesis-opponent-report-review/SKILL.md`
  - `TODO.md`
- Tasks:
  - Keep the top-level operator path chat-first and simple.
  - Document packet-first behavior as implementation detail, not as the primary
    mental model for supervisors or opponents.
  - Update TODO entries to point at completed commands or remaining follow-up.
  - Explicitly say that packet generation reduces context, not role coverage.
  - Explain that supervisor packets support student-facing feedback, while
    opponent packets support internal materials, trace, report draft boundaries,
    and report review.
  - Add a troubleshooting note: if an agent claims a file was written but the
    wave gate fails, trust the file/checker result.
  - Add a closeout troubleshooting note for stale review hashes: rerun review
    after material edits, or record a typed exception; do not manually adjust
    hashes without an approval record for the current artifact.
  - Add opponent-specific warnings against leaking internal packet paths,
    hashes, private URLs, raw PR metadata, or generated-draft state into
    opponent-facing prose.
- Verification:
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

## Progress

- 2026-05-11: Initial supervisor-only plan created from a post-run review of
  final supervisor-feedback context growth and workflow overhead. No
  implementation started.
- 2026-05-11: Added lessons from a final implementation-thesis feedback round:
  refresh drift-prone PR/check evidence before synthesis, register diagnostic
  notes used as evidence, run feedback shape checks before final review, capture
  reviewer approval structurally, and make stale reviewed hashes a first-class
  closeout failure rather than a manual repair step.
- 2026-05-11: Added lessons from a final BP supervisor-feedback round with a
  required video, hardware fault, virtual-inverter substitute evidence, and
  metric-heavy claims: add media/demo intake, evidence-mode matrices,
  quantitative handoffs, late-communication capture, and final-sprint action
  budgets.
- 2026-05-11: Generalized the plan from supervisor feedback to shared thesis
  review context efficiency. The plan now covers supervisor feedback and
  opponent review as separate workflow profiles, keeps existing opponent packet
  and closeout surfaces, and adds opponent-specific trace/report-review
  constraints.
- 2026-05-11: Added model/reasoning policy and updated repo-local semantic
  thesis reviewer profiles to `gpt-5.5` with `model_reasoning_effort = "xhigh"`.
  The plan now reserves `gpt-5.3-codex-spark` for mechanical,
  validator-backed helper roles only.
- 2026-05-11: Added Omen MCP guidance for code-quality review as optional
  advisory static analysis. Omen may support reviewer confidence, but it must
  not become an operator-facing supervisor/opponent gate.
- 2026-05-11: Reviewed the generalized plan with two agents and repaired the
  plan before implementation. Fixes tightened materiality-before-optional-packet
  sequencing, supervisor draft-path validation, opponent materials draft versus
  post-review gates, structured approval-record provenance, current-evidence
  snapshot hash boundaries, human-calibration trace wording, supervisor closeout
  dependency boundaries, Windows packaging verification, and stale test paths.
- 2026-05-11: Completed Slice 1. Added compact final-response contracts and
  explicit model/reasoning rules to thesis-review workflow/evidence skills,
  including revision diff and GitHub code intake; pinned repo-local semantic
  reviewer profiles to `gpt-5.5`/`xhigh`; documented Spark as mechanical
  validator-backed only; and recorded Omen as an advisory code-quality signal,
  not an operator gate. Verification passed:
  `scripts/check-private`, `scripts/check-scripts`, `git diff --check`, TOML
  parsing for `.codex/config.toml` and `.codex/agents/*.toml`, and untracked
  plan whitespace check.
- 2026-05-11: Completed Slice 2. Added `scripts/check-review-wave` backed by
  `review_wave_gate.py`, built-in supervisor/opponent wave specs, JSON custom
  specs, ignored-case whitespace checks, draft-path feedback validation via
  `--artifact`, approval-record hash/verdikt validation, and packaging registry
  coverage. Agent review found approval-record gaps; fixes require approved
  verdicts, safe reviewed paths, existing review-basis files, and current
  reviewed/basis hashes. Verification passed: `pants fmt ::`,
  `pants lint src/thesis_review_workflow:: tests:: scripts::`,
  `pants check src/thesis_review_workflow:: tests:: scripts::`,
  `pants test tests/test_review_wave_gate.py tests/test_workflow_python_contracts.py`,
  `scripts/smoke-review-wave`, `scripts/smoke-feedback-language`,
  `scripts/smoke-feedback-output`, `scripts/smoke-package-workflow-tools`,
  `scripts/check-private`, `scripts/check-scripts`, `git diff --check`, and
  `pants run :omen` (grade A, overall score 91.03; existing hotspots outside
  the new wave-gate files).

## Decision Log

- 2026-05-11: Keep agent concurrency at the existing default limit. The main
  optimization target is smaller context and stricter artifact contracts, not
  more simultaneous agents.
- 2026-05-11: Treat `plans/supervisor_workflow_closeout_plan.md` as the
  supervisor closeout-command home. This plan owns context efficiency,
  packetization, synthesis handoffs, wave gates, and closeout integration
  points.
- 2026-05-11: Treat existing opponent commands and docs as canonical
  implementation surfaces. This plan should harden `work/opponent_packets/`,
  `scripts/opponent-closeout`, and `work/opponent_report_trace.json`, not invent
  a parallel opponent flow.
- 2026-05-11: Do not make optional review roles disappear. Add materiality gates
  to avoid broad over-triggering, while preserving explicit user requests,
  formal skill triggers, and mandatory code-bearing review roles.
- 2026-05-11: Keep tracked plans case-neutral. Lessons from individual rounds
  should be promoted as generic workflow requirements, not as named student or
  private-case details.
- 2026-05-11: Put audience-specific translation into the evidence contract. Raw
  technical diagnostics are useful internally, but synthesis should carry either
  the minimal action the student can take or the report/grade/manual-check impact
  for an opponent.
- 2026-05-11: Treat video/demo artifacts as evidence-boundary objects, not
  automatic runtime proof. A video may satisfy a presentation assignment point
  while still being insufficient evidence for hardware validation.
- 2026-05-11: In final or report-facing work, prefer an explicit evidence-mode
  matrix over narrative reconstruction when claims mix real hardware, real data,
  simulations, virtual twins, code inspection, logs, and video.
- 2026-05-11: Use `work/supervisor_packets/` for the new supervisor profile and
  keep `work/opponent_packets/` for opponent review because it is already the
  canonical path in code, skills, docs, and tests.
- 2026-05-11: Keep semantic reviewer roles on `gpt-5.5`/`xhigh`. Use
  `gpt-5.3-codex-spark` only for mechanical status, inventory, or validation
  handoff work whose output is checked deterministically and consumed by a
  high-reasoning semantic role.
- 2026-05-11: Treat Omen MCP like Serena and pdf-reader in spirit: useful when
  available for a targeted evidence layer, but not required for normal operator
  workflow execution.

## Risks

- Synthesis handoffs can lose nuance if agents treat them as replacements for
  evidence rather than compact entrypoints.
- Materiality gates can create false negatives if they become semantic routing
  engines. They must remain advisory and structured-input based.
- A generated opponent report draft can be mistaken for sendable prose if human
  point/grade calibration is not explicit.
- Stale `work/opponent_report_trace.json` can make a report draft look current
  after reviewed materials changed.
- Opponent-facing prose can accidentally leak internal packet paths, hashes, PR
  metadata, private URLs, branch names, or generated-draft state.
- Grade-impacting opponent claims can become overconfident if confidence labels
  are not preserved through synthesis.
- Code text-code mismatch and code-quality/design risks can be conflated unless
  handoffs and packets keep them separate.
- Supervisor final-sprint action-budget language can leak into opponent
  materials, where the consumer needs defensible report wording and manual
  checks rather than coaching.
- Spark can be overused if "mechanical" is not defined narrowly. It must not
  produce final evidence claims, grading/report calibration, or sendable prose
  without high-reasoning review.
- Omen can be overinterpreted if its metrics are copied directly into feedback.
  Reviewers must map Omen signals back to concrete code evidence and thesis
  defensibility.
- Windows command-surface coverage can regress if new helper commands land only
  as POSIX wrappers.

## Final Audit

Not run yet. Before archiving this plan, record:

- implementation slices completed or explicitly deferred;
- plan-review findings and fixes;
- exact commands run for each slice;
- whether `scripts/supervisor-preflight` / `scripts/supervisor-closeout` work
  consumed the integration points here;
- whether `scripts/opponent-preflight` / `scripts/opponent-closeout` consumed
  the integration points here;
- residual risks, especially around handoff summary loss, materiality false
  negatives, stale opponent trace state, generated report draft boundaries, and
  Windows command-surface coverage.
