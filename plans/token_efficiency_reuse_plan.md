# Token Efficiency And Artifact Reuse Plan

Status: active
Created: 2026-05-13

## Goal

Reduce unnecessary model context and repeated semantic work across round
workflows. Unchanged artifact reprocessing is one important case, but the wider
target is a pipeline that can tell when it needs a fresh semantic pass, when a
current handoff is enough, and when a reviewer must open full evidence.

The target is not "shorter prompts at any cost"; it is a simpler pipeline that
can distinguish:

- unchanged evidence that can be reused,
- changed evidence that needs a delta review,
- required coverage that can be satisfied by current reviewed evidence,
- stale or missing evidence that must be regenerated or recorded as a typed
  limitation,
- full-artifact rechecks that are required because a claim is P0/P1,
  contradicted, challenged, or missing anchors.

## Audit Base

This audit checked workflow docs, repo-local skills, packet generation, code
workspace preparation, PDF extraction, materiality routing, review-wave gates,
final-review skill scope, and review-manifest closeout. It did not inspect
private case contents.

Commands and documents used:

```bash
git status --short --untracked-files=all
sed -n '1,220p' AGENTS.md
sed -n '1,260p' README.md
sed -n '1,240p' plans/archive/review_context_efficiency_plan.md
sed -n '1,260p' docs/agent-scheduling.md
sed -n '1,260p' docs/opponent-review-workflow.md
sed -n '1,220p' docs/raw-text-processing-audit.md
rg -n "token|reuse|cache|hash|unchanged|stale|snapshot|manifest|packet" -g '!cases/**'
rg -n "Inspect all|read all|full artifacts|Open full|role-split|material|mandatory|required role|run .*before|context|packet" .agents/skills docs README.md AGENTS.md -g '!cases/**'
```

Positive current controls:

- Packet-first workflow is already established. `docs/agent-scheduling.md`
  says `work/supervisor_packets/*.md` and `work/opponent_packets/*.md` are
  compact handoffs, and synthesis should open full artifacts only when needed.
- Subagent final responses are already constrained to concise handoffs rather
  than full artifact dumps.
- `scripts/prepare-code-workspace` already avoids re-unpacking unchanged
  within a round when the existing target and source fingerprint match
  (`src/thesis_review_workflow/code_workspace.py:980-986`,
  `src/thesis_review_workflow/code_workspace.py:1019-1024`).
- Figure/media review already has the right reusable-evidence shape: visual
  descriptions are reused only when visual hashes and analysis version match,
  and claim alignment is reused only when both visual and context hashes match
  (`.agents/skills/thesis-figure-media-review/SKILL.md:42-60`).
- Materiality next actions already detect missing or stale optional structured
  artifacts through source hashes and current-evidence snapshot checks
  (`src/thesis_review_workflow/review_materiality.py:692-813`).
- The packet workflow already says not to fork full conversation history by
  default and to use concise self-contained role prompts
  (`AGENTS.md:127`, `docs/agent-scheduling.md:99-110`).
- Some skills already model the desired budget discipline. Quantitative review
  starts from compact packets and opens full artifacts only for material claims,
  contradictions, or missing anchors
  (`.agents/skills/thesis-quantitative-claims-review/SKILL.md:33-44`), and
  figure/media review has explicit reusable inventory state
  (`.agents/skills/thesis-figure-media-review/SKILL.md:42-60`).

External design notes used only as architectural calibration:

- Anthropic's context-engineering guidance recommends compaction, structured
  note-taking, and multi-agent architectures for long-horizon work; subagents
  are useful because they keep detailed exploration in separate context windows
  and return distilled summaries to the lead agent.
  <https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents>
- Anthropic's multi-agent research write-up frames search as compression, but
  also warns that multi-agent systems spend many more tokens and are a poorer fit
  for tightly coupled tasks with heavy shared context.
  <https://www.anthropic.com/engineering/multi-agent-research-system>
- LangGraph handoff guidance recommends passing selected handoff messages or
  summaries instead of raw subagent history to avoid context bloat.
  <https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs>
- OpenAI Agents SDK supports specialist-agent handoffs and typed/structured
  outputs, which matches the desired "reader returns a validated capsule"
  pattern.
  <https://openai.github.io/openai-agents-python/agents/>

Findings:

### P1 - Broad intake wording can defeat packet-first routing

Supervisor feedback still instructs the main workflow to "inspect all current
inputs" across assignment, thesis, source, code, README, configs, experiments,
screenshots, and notes before or alongside packet preparation
(`.agents/skills/thesis-supervisor-feedback/SKILL.md:41-46`). Opponent materials
similarly tell the workflow to read thesis text, available code/artifacts,
README, experiment results, and notes before packet preparation
(`.agents/skills/thesis-opponent-materials/SKILL.md:36-40`).

Effect: even with compact role packets, the parent or synthesis pass can spend a
large context budget rediscovering the whole case. The contract should separate
"inventory all available evidence" from "open full evidence now". Full evidence
opens should be driven by role scope, changed source fingerprints, missing
handoff anchors, contradictions, P0/P1 verification, or reviewer challenge.

### P1 - Parent/subagent context boundary is implied, not enforceable

The workflow already expects role-split agents and compact handoffs, but the
contract is mostly procedural: subagents write Markdown artifacts and the parent
or synthesis pass decides how much raw evidence to reopen. There is no
first-class artifact that says "the parent consumed these structured capsules
and did not need raw source text" or "this full source was reopened for this
trigger".

Effect: subagents can protect the parent context in practice, but the pipeline
cannot verify the boundary. A context-efficient design should make the parent a
coordinator over typed evidence capsules, claim ledgers, and targeted drill-down
requests, with raw thesis/code reads reserved for explicit triggers.

### P1 - Mandatory semantic roles cannot accept current reusable evidence

Code-bearing supervisor/opponent rounds always activate code consistency and
code quality packet roles when a prepared code workspace exists
(`src/thesis_review_workflow/supervisor_packets.py:92-140`,
`src/thesis_review_workflow/opponent_packets.py:91-141`,
`src/thesis_review_workflow/review_packets.py:252-263`). The code workspace may
be "already current", but the semantic outputs still have no first-class state
for "current and reusable for the unchanged source set".

Effect: unchanged code can avoid a mechanical unpack/copy, but reviewers still
receive a role packet that implies a fresh full semantic pass. This is the main
token-waste risk.

### P1 - Role activation conflates coverage with fresh review need

Materiality routing currently marks opponent typography/formal and
literature/citation roles as material whenever the workflow profile is
`opponent_review`, because opponent materials have IS/report calibration items
for those roles (`src/thesis_review_workflow/review_materiality.py:537-546`).
That is a valid coverage requirement, but not always evidence that a fresh
standalone role agent must reread the thesis. Similarly, code roles are
mandatory when code exists, but there is no separate state for "coverage
required and already satisfied by current reviewed evidence".

Effect: the system can prove that a role must be represented in the final
artifact, but not that the representation can be satisfied by reusable current
evidence, a no-material-issue handoff, or a typed limitation. This pushes
workflows toward fresh agents even when the only real requirement is coverage.

### P1 - Cross-round reuse exists only as manual context, not a contract

Repeated-round support currently lists previous feedback paths
(`src/thesis_review_workflow/review_packets.py:342-357`) and import-round writes
`notes/previous-feedback-index.md` as a path list
(`src/thesis_review_workflow/cli/import_round.py:156-164`). Skills then tell
agents to read current inputs and prior feedback
(`.agents/skills/thesis-supervisor-feedback/SKILL.md:41-46`) and inspect code
artifacts again
(`.agents/skills/thesis-code-consistency/SKILL.md:23-44`,
`.agents/skills/thesis-code-quality-review/SKILL.md:37-49`).

Effect: prior outputs are discoverable, but there is no hash-bound answer to
"which prior conclusions still apply because the source did not change?"

### P1 - Review manifest source refs are over-broad by default

`init-review-manifest` defaults `input_refs` for each artifact to every recorded
input, extracted artifact, and note, and defaults synthesis `evidence_refs` to
all supporting work artifacts
(`src/thesis_review_workflow/cli/init_review_manifest.py:459-499`). For
calibrated internal evidence, closeout then validates `source_sha256` for every
recorded source ref
(`src/thesis_review_workflow/cli/check_review_manifest.py:166-188`,
`src/thesis_review_workflow/cli/check_review_manifest.py:674-680`).

Effect: a small unrelated note or work artifact can make an artifact appear
stale, or force a conservative re-review, because the manifest lacks
role-specific dependency edges.

### P2 - Role packets repeat broad common context in every packet

Supervisor and opponent packet renderers include common case, round, schema,
profile, base-input, extracted-text, active-packet, advisory-artifact, snapshot,
materiality, and handoff sections in every active role packet
(`src/thesis_review_workflow/supervisor_packets.py:408-537`,
`src/thesis_review_workflow/opponent_packets.py:460-557`). The packet text also
duplicates stable constraints that already live in skills and project
instructions.

Effect: packet generation is useful, but it spends prompt budget repeatedly on
case/common boilerplate. A better contract is one stable common briefing plus
small role packets containing role deltas, missing inputs, current handoffs, and
the exact full-artifact triggers for that role.

### P2 - Packet generation creates timestamp churn

`prepare-supervisor-packets` and `prepare-opponent-packets` pass `now_utc()` into
packet generation (`src/thesis_review_workflow/cli/prepare_supervisor_packets.py:61`,
`src/thesis_review_workflow/cli/prepare_opponent_packets.py:54`). Rendered
packets include `Generated at` and are written unconditionally
(`src/thesis_review_workflow/supervisor_packets.py:443-456`,
`src/thesis_review_workflow/supervisor_packets.py:540-567`).

Effect: regenerating packets can change packet hashes even when role-relevant
inputs did not change. That increases provenance churn and makes it harder to
tell whether a role packet materially changed.

### P2 - Final review skills have broad recheck wording

Supervisor feedback review says to re-check every P0/P1 claim against assignment
context, deadline context, thesis text, code, README, PDF text, LaTeX sources,
previous feedback, internal evidence artifacts, and notes
(`.agents/skills/thesis-supervisor-feedback-review/SKILL.md:38-59`). Opponent
materials review uses the same broad pattern for P0/P1 and grade-impacting
statements (`.agents/skills/thesis-opponent-materials-review/SKILL.md:37-56`).
Both skills include good handoff-first guidance, but the required review basis
is not yet a structured input.

Effect: independent review remains necessary, but the reviewer may reopen far
more raw context than needed. The pipeline should pass a claim-level
`claim_review_basis` that names only the anchors used by the draft, plus a
policy for opening full artifacts when anchors are missing, contradictory, or
grade-impacting.

### P2 - Post-review wording amendments lack a bounded delta path

After a reviewed supervisor report is edited for style or IS-entry fit, the
current workflow can only treat the reviewed Markdown as stale and rebuild the
full review-approval/provenance chain. That is correct for material edits, but
too coarse for bounded human-confirmed wording amendments such as removing a
future-work sentence, changing direct-address style, or simplifying a routine
publication paragraph.

Effect: a small, low-risk text amendment can trigger a fresh semantic reviewer
or broad context reload even when the report's grade, evidence-backed claims,
and public IS fields are unchanged. Add a hash-bound amendment record that
classifies the edit as `style_only`, `public_text_delta`, `private_comment_delta`,
or `material_claim_delta`, records the previous/current hashes, and states which
review path is required. Style-only or public-text cleanup still needs approval,
but the reviewer should start from a compact diff and current review basis
rather than from all source evidence.

### P2 - Submitted supervisor-report artifacts are not first-class evidence

The workflow has reviewed Markdown and `work/supervisor_report_confirmation.json`,
but the actually submitted IS/PDF report is not modeled as a first-class
artifact. A human can submit a lightly edited public report, while the local
Markdown may still contain private sections or review-only wording. The current
closeout can confirm the Markdown, but it does not natively capture the
submitted PDF hash, extracted public text, or equivalence between the submitted
public fields and the reviewed Markdown's public report text.

Effect: closeout can require manual `pdftotext`, manual comparison, and manual
copying into the ignored case workspace. Add a submitted-report record that
binds the submitted PDF, extracted text, public-report hash, grade/points, and
confirmation record. This keeps future agents from reopening the full PDF just
to establish what was actually sent.

### P2 - PDF extraction is not source-hash aware

`scripts/extract-pdf-text` always runs `pdftotext -layout` and overwrites the
requested output (`src/thesis_review_workflow/cli/extract_pdf_text.py:84-99`).
`scripts/import-round` extracts each copied PDF during new-round import
(`src/thesis_review_workflow/cli/import_round.py:141-155`), but there is no
extraction manifest binding input PDF hash, extractor version/options, and
output text hash.

Effect: identical PDFs across rounds cannot be safely copied/reused, and agents
do not get a cheap "rendered thesis text unchanged" signal.

### P2 - GitHub intake is intentionally frozen but not idempotent

`scripts/import-github-code` refuses to replace existing GitHub snapshot targets
without `--refresh`
(`src/thesis_review_workflow/cli/import_github_code.py:239-249`). That protects
frozen evidence, but there is no snapshot manifest that says "same repo/PR/head
SHA/check set, existing intake is reusable".

Effect: operators must choose between keeping an old frozen snapshot or doing a
full refresh; the pipeline cannot cheaply prove that the external evidence did
not materially change.

### P3 - Closeout helper checks are not target-hash incremental

`init-review-manifest --run-checks` reruns every helper check listed in the
manifest except `check-review-manifest`, then records target hashes afterward
(`src/thesis_review_workflow/cli/init_review_manifest.py:541-559`). These checks
are deterministic and cheaper than LLM work, so this is a lower-priority issue,
but the same pattern creates avoidable runtime churn and noisy timestamps.

Effect: repeated closeout can look materially fresh even when all check targets
and check commands are unchanged. A cached pass-through record keyed by command,
target hashes, and checker version would reduce noise without weakening gates.

### P3 - Closeout refresh can require two manifest passes after approval changes

After a final review approval record changes, `init-review-manifest --run-checks`
can write a manifest with the current reviewed hash while `work/agent_coverage.json`
still reflects the pre-approval state until the command is run again. The
underlying issue is refresh ordering: approval records are applied after coverage
is built.

Effect: a valid closeout can fail once with stale role coverage and then pass on
the next identical refresh. Apply approval records before coverage generation
and helper-check execution so one manifest refresh is sufficient.

## Scope

In scope:

- define a case-neutral reuse contract for current-round and previous-round
  evidence;
- define a prompt/context budget contract for common briefing, role packet,
  synthesis, and final-review stages;
- add a parent/subagent context boundary: document-reader or evidence-extractor
  agents write typed capsules, while the parent normally consumes capsule
  summaries, freshness state, and claim ledgers rather than raw document text;
- add deterministic source fingerprints for PDF extracts, code workspaces,
  GitHub snapshots, packet inputs, and generated review artifacts;
- add first-class submitted-report records for supervisor reports first,
  including submitted PDF hash, extracted public text hash, grade/points, and
  equivalence to reviewed public Markdown. Keep the schema generic enough for
  opponent reports, but do not claim opponent report command coverage until a
  dedicated slice or follow-up lands;
- add bounded post-review amendment records so small human-confirmed wording
  changes can be reviewed from a compact diff and claim-level basis rather than
  reopening full evidence by default;
- make packet generation write only when material content changes;
- replace blanket manifest dependency defaults with artifact-specific source
  refs;
- extend materiality and wave gates so mandatory roles can be satisfied by a
  current reviewed output or an explicit reuse record, not only by a fresh agent
  pass;
- split "role coverage is required" from "fresh semantic review is required";
- replace broad final-review inputs with claim-level `claim_review_basis` refs
  wherever a draft already has anchored evidence;
- update skills so agents start from reuse/handoff state and open full artifacts
  only for changed inputs, P0/P1 verification, contradictions, or reviewer
  challenges;
- add synthetic tests and smokes only.

Out of scope:

- weakening DEEP mode, role coverage, independent review, or reviewer-profile
  rules;
- automatically trusting old semantic conclusions without matching source hashes
  and a recorded reuse decision;
- caching raw LLM prompts, completions, or private case data outside ignored
  case workspaces;
- replacing semantic thesis/code review with extractive document summaries;
- spawning subagents for every file by default. Reader agents should be used
  where source volume or modality justifies isolation; deterministic inventory
  and targeted excerpting remain the first layer;
- executing submitted student code;
- adding compatibility layers for older `~/code/diplomky` workflows.

## Reuse Contract

Add a structured artifact such as `work/reuse/reuse_index.json` with:

- current source fingerprints for input PDFs, extracted text, code workspace
  sources, GitHub snapshots, materiality decisions, and reviewed evidence
  artifacts;
- nearest previous-round candidates by artifact role;
- reuse status: `unchanged_reusable`, `changed_delta_required`,
  `stale_or_unreviewed`, `not_comparable`;
- fresh semantic review required: `true` or `false`;
- coverage satisfied by: `current_reviewed_artifact`, `current_handoff`,
  `typed_no_material_issue`, `typed_limitation`, `fresh_role_review`, or
  `not_satisfied`;
- next action: `reuse_existing_review`, `delta_review`, `fresh_role_review`,
  `manual_limitation`, or `not_comparable_backfill`;
- exact source refs and hashes that justify the status;
- producer fields and schema version so deterministic validators can check it.

The reuse index is advisory until a role/wave gate consumes it. For semantic
outputs, reuse is valid only when:

- source hashes match the previous reviewed artifact's source refs;
- the producing skill/schema version is compatible;
- the prior artifact has current independent review or is explicitly covered by
  a current downstream synthesis review;
- required role coverage, review approvals, and review-manifest freshness remain
  valid for the artifact being reused;
- changed surrounding context does not affect the claim being reused.

## Prompt And Review Budget Contract

Add a companion contract for model context:

- `common_briefing`: one stable, hashable case/round briefing that inventories
  available evidence, readiness output, current evidence snapshot, materiality
  decisions, previous feedback index, prepared code roots, and limitations;
- `role_packet`: a small role-specific delta that references the common briefing
  and includes only mission, focus, active role inputs, reusable prior evidence,
  missing role inputs, required output, and full-artifact triggers;
- `evidence_capsule`: a structured subagent or deterministic extractor output
  keyed by source hash, section/page/path anchors, producer role, extraction
  schema, summary, reusable facts, unresolved ambiguities, and "open raw source
  if" triggers;
- `coverage_decision`: structured state separating `coverage_required` from
  `fresh_review_required`, with reasons such as `changed_sources`,
  `missing_reviewed_artifact`, `existing_current_handoff`, `no_material_issue`,
  or `typed_limitation`;
- `claim_review_basis`: claim-level anchors used by synthesis or final drafts,
  distinct from the existing artifact-level `review_basis_path` recorded in
  review approval records. The independent reviewer verifies actual P0/P1 and
  grade-impacting claims from this ledger before reopening broader sources;
- `amendment_delta`: a compact record for post-review edits that stores
  previous/current hashes, changed public/private sections, edit class, compact
  diff, and required review/approval action;
- `submitted_report`: an operator-submitted artifact record keyed by submitted
  file hash, extracted public text hash, reviewed public Markdown hash,
  grade/points, and confirmation status;
- `check_reuse`: deterministic helper-check status keyed by command, checker
  version, target hashes, and previous exit status. This may only skip checks
  that are explicitly pure/read-only and whose target hash set is unchanged.

## Artifact Schema And Validator Contract

Every new reusable workflow artifact must follow the existing structured-artifact
pattern: versioned schema, explicit required fields, bounded enums, deterministic
validator, manifest integration, and synthetic tests. Initial schemas:

- `reuse-index-v1`: `schema_version`, `case_id`, `round_id`, `source_set`,
  `artifact_candidates`, `reuse_status`, `fresh_semantic_review_required`,
  `coverage_satisfied_by`, `next_action`, `source_sha256`, `producer`, and
  `limitations`.
- `common-briefing-v1`: `schema_version`, `case_id`, `round_id`, readiness
  status, current evidence snapshot refs, materiality refs, previous feedback
  refs, prepared code roots, capsule refs, and limitations.
- `evidence-capsule-v1`: `schema_version`, `source_ref`, `source_sha256`,
  `producer_role`, `anchor_refs`, `summary`, `extracted_facts`,
  `candidate_claims`, `uncertainties`, `limitations`, and
  `open_raw_source_if`.
- `claim-review-basis-v1`: `schema_version`, `draft_ref`, `draft_sha256`,
  `claim_id`, `claim_text`, `priority`, `evidence_refs`, `capsule_refs`,
  `source_sha256`, `verification_status`, and `raw_source_escalations`.
- `submitted-report-v1`: `schema_version`, submitted artifact refs and hashes,
  extracted public text hash, reviewed public Markdown hash, grade/points,
  confirmation refs, equivalence result, and limitations.
- `amendment-delta-v1`: `schema_version`, previous/current artifact hashes,
  changed sections, edit class, compact diff refs, affected claims, required
  review action, approval refs, and limitations.
- `context-budget-report-v1`: `schema_version`, generated artifacts, approximate
  byte/token estimates, raw-source transfer warnings, and threshold decisions.

Backfill rule: existing rounds without the new sidecars are deterministic
`not_comparable` until an operator runs an explicit ignored-workspace backfill or
refresh command. The pipeline must not silently infer old fingerprints from
private raw content during normal synthesis.

## Slices

### Slice 1 - Reuse Contract And Dependency Model

- Status: done
- Proposed commit message: `docs(workflow): plan token reuse contract`
- Expected paths:
  - `plans/token_efficiency_reuse_plan.md`
  - `src/thesis_review_workflow/reuse.py`
  - `tests/test_reuse.py`
- Tasks:
  - Define typed source fingerprints and reuse statuses.
  - Define which source classes affect each artifact role.
  - Add pure helper tests for unchanged, changed, missing, stale, and
    not-comparable cases.
  - Keep free-text interpretation out of deterministic reuse decisions.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests::`
  - `pants check src/thesis_review_workflow:: tests::`
  - `pants test tests/test_reuse.py`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 2 - Deterministic Source Fingerprints

- Status: done
- Proposed commit message: `feat(workflow): fingerprint reusable round sources`
- Expected paths:
  - `src/thesis_review_workflow/pdf_extracts.py`
  - `src/thesis_review_workflow/code_workspace.py`
  - `src/thesis_review_workflow/cli/extract_pdf_text.py`
  - `src/thesis_review_workflow/cli/import_round.py`
  - `src/thesis_review_workflow/cli/import_github_code.py`
  - `src/thesis_review_workflow/work_artifacts.py`
  - tests for the touched helpers
- Tasks:
  - Add PDF extraction sidecars recording PDF hash, extractor command/version,
    output path, and output hash.
  - Let PDF extraction skip or copy a known-current extract when the source hash
    and extractor contract match.
  - Preserve the current code-workspace manifest behavior and expose its source
    fingerprints to the reuse index.
  - Add a GitHub snapshot manifest that records repo/PR identity, head SHA,
    changed-file list hash, checks summary hash, and checkout path hashes.
  - Define existing rounds without sidecars as `not_comparable`; do not infer
    missing fingerprints from raw private content during normal review.
  - Add an explicit ignored-workspace backfill mode for the current active round
    so operators can regenerate sidecars intentionally.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - targeted pytest for PDF/code/GitHub fingerprint helpers
  - relevant smoke scripts such as `scripts/smoke-prepare-code-workspace` and
    `scripts/smoke-github-code-intake`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 3 - Round Reuse Index

- Status: done
- Proposed commit message: `feat(workflow): add round reuse index`
- Expected paths:
  - `scripts/update-round-reuse-index`
  - `scripts/BUILD`
  - `src/thesis_review_workflow/commands.py`
  - `src/thesis_review_workflow/cli/update_round_reuse_index.py`
  - `src/thesis_review_workflow/reuse.py`
  - `src/thesis_review_workflow/cli/BUILD`
  - `tests/test_reuse.py`
  - `tests/test_workflow_python_contracts.py`
  - `scripts/smoke-round-reuse-index`
- Tasks:
  - Compare current round source fingerprints with previous rounds in the same
    case without reading private content into tracked files.
  - Write `work/reuse/reuse_index.json`.
  - Record candidate prior artifacts and why each one is reusable, delta-only,
    stale, or not comparable.
  - Make the command read-only except for the ignored current-round work output.
  - Add an explicit `--backfill-current` or equivalent mode that writes missing
    sidecars only under the ignored active round workspace.
  - Wire the command through the standard command surface: `commands.py`, CLI
    `BUILD`, shell wrapper, `scripts/BUILD` PEX entry, package metadata, smoke,
    and generated Windows launchers.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - `pants test tests/test_reuse.py tests/test_workflow_python_contracts.py`
  - `scripts/smoke-round-reuse-index`
  - `scripts/smoke-package-workflow-tools`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 4 - Evidence Capsule And Claim-Basis Schemas

- Status: pending
- Proposed commit message: `feat(workflow): add context handoff schemas`
- Expected paths:
  - `src/thesis_review_workflow/evidence_capsules.py`
  - `src/thesis_review_workflow/claim_review_basis.py`
  - `src/thesis_review_workflow/work_artifacts.py`
  - `tests/test_evidence_capsules.py`
  - `tests/test_claim_review_basis.py`
- Tasks:
  - Implement validators for `evidence-capsule-v1` and
    `claim-review-basis-v1` before packet or skill rewrites consume them.
  - Keep `claim_review_basis` distinct from existing review approval
    `review_basis_path`; the former is a claim-anchor ledger, the latter remains
    the reviewed draft/artifact path.
  - Record raw-source escalation reasons in the claim basis: missing anchor,
    contradiction, P0/P1 verification, grade impact, or reviewer challenge.
  - Add manifest-safe path/hash helpers without reading private content into
    tracked fixtures.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests::`
  - `pants check src/thesis_review_workflow:: tests::`
  - `pants test tests/test_evidence_capsules.py tests/test_claim_review_basis.py`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 5 - Common Briefing And Packet Rendering

- Status: pending
- Proposed commit message: `feat(workflow): split common briefing from role packets`
- Expected paths:
  - `src/thesis_review_workflow/review_packets.py`
  - `src/thesis_review_workflow/supervisor_packets.py`
  - `src/thesis_review_workflow/opponent_packets.py`
  - `src/thesis_review_workflow/supervisor_report_packets.py`
  - `src/thesis_review_workflow/cli/prepare_supervisor_packets.py`
  - `src/thesis_review_workflow/cli/prepare_opponent_packets.py`
  - `src/thesis_review_workflow/cli/prepare_supervisor_report_packets.py`
  - `tests/test_supervisor_packets.py`
  - `tests/test_opponent_packets.py`
  - `tests/test_supervisor_report_packets.py`
  - packet smoke scripts
- Tasks:
  - Generate one stable `work/common_briefing.json` or Markdown equivalent per
    workflow run and have supervisor, opponent, and supervisor-report packets
    reference it instead of repeating all common context.
  - Keep role packets focused on mission, focus, required output, role-specific
    evidence, reusable handoffs, missing role inputs, and full-artifact triggers.
  - Stop rewriting packet files when material content is unchanged; move volatile
    timestamps to sidecar metadata or stable generated-at records that do not
    invalidate role content.
  - Include current capsule refs and claim-basis refs when they are current for
    source hash and schema.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests::`
  - `pants check src/thesis_review_workflow:: tests::`
  - targeted packet pytest
  - `scripts/smoke-supervisor-packets`
  - `scripts/smoke-opponent-packets`
  - `scripts/smoke-supervisor-report-packets`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 6 - Materiality And Wave-Gate Reuse Consumption

- Status: pending
- Proposed commit message: `feat(workflow): separate role coverage from fresh review`
- Expected paths:
  - `src/thesis_review_workflow/review_materiality.py`
  - `src/thesis_review_workflow/review_wave_gate.py`
  - `src/thesis_review_workflow/agent_coverage.py`
  - `src/thesis_review_workflow/reuse.py`
  - materiality/wave-gate tests
- Tasks:
  - Split materiality output into `coverage_required` and
    `fresh_review_required`, including no-material-issue, current-handoff, typed
    limitation, and current-reviewed-artifact states.
  - Extend mandatory role handling so code consistency and code quality remain
    required, but a current reviewed artifact plus reuse index can satisfy the
    wave without a fresh full semantic pass.
  - Ensure changed thesis claims around unchanged code still trigger a delta
    text-code consistency review.
  - Preserve independent review and manifest gates for sendable or standalone
    final artifacts.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests::`
  - `pants check src/thesis_review_workflow:: tests::`
  - targeted materiality/wave-gate pytest
  - `scripts/smoke-review-wave`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 7 - Manifest Dependency Precision And Claim Basis

- Status: pending
- Proposed commit message: `feat(workflow): bind review artifacts to precise sources`
- Expected paths:
  - `src/thesis_review_workflow/cli/init_review_manifest.py`
  - `src/thesis_review_workflow/review_manifest.py`
  - `src/thesis_review_workflow/cli/check_review_manifest.py`
  - `src/thesis_review_workflow/review_approvals.py`
  - `src/thesis_review_workflow/claim_review_basis.py`
  - `src/thesis_review_workflow/cli/register_review_artifact.py`
  - manifest/claim-basis tests
- Tasks:
  - Replace blanket `input_refs`/`evidence_refs` defaults with role-aware
    dependency refs derived from artifact type, registration metadata, packet
    inputs, claim basis entries, capsule refs, and reuse index entries.
  - Teach manifest closeout to flag missing dependency refs for final artifacts
    without over-binding every artifact to every note or work file.
  - Validate `claim_review_basis` for final drafts and reviewed materials so
    independent reviewers can start from exact anchors.
  - Keep existing `review_basis_path` approval semantics intact and explicitly
    test that claim-basis additions do not weaken review approval records.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests::`
  - `pants check src/thesis_review_workflow:: tests::`
  - targeted review-manifest and claim-basis pytest
  - `scripts/smoke-review-manifest`
  - `scripts/smoke-register-review-artifact`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 8 - Skill Wording And Parent/Synthesis Instructions

- Status: pending
- Proposed commit message: `docs(workflow): route agents through capsules first`
- Expected paths:
  - `.agents/skills/thesis-supervisor-feedback/SKILL.md`
  - `.agents/skills/thesis-supervisor-feedback-review/SKILL.md`
  - `.agents/skills/thesis-supervisor-report/SKILL.md`
  - `.agents/skills/thesis-supervisor-report-review/SKILL.md`
  - `.agents/skills/thesis-opponent-materials/SKILL.md`
  - `.agents/skills/thesis-opponent-materials-review/SKILL.md`
  - `.agents/skills/thesis-code-consistency/SKILL.md`
  - `.agents/skills/thesis-code-quality-review/SKILL.md`
  - `.agents/skills/thesis-quantitative-claims-review/SKILL.md`
  - `.agents/skills/thesis-literature-citation-review/SKILL.md`
  - `.agents/skills/thesis-typography-formal-review/SKILL.md`
  - `.agents/skills/thesis-theses-similarity-review/SKILL.md`
  - `docs/agent-scheduling.md`
- Tasks:
  - Change broad "inspect/read all" instructions to "inventory all, open current
    capsules, role-relevant evidence, or claim-basis evidence first, then
    escalate to full sources only for explicit triggers".
  - State explicitly that reuse and capsules do not waive independent review for
    sendable or standalone final artifacts.
  - Keep reader/extractor agents extractive and evidence-oriented; semantic
    grading, thesis/code consistency judgments, and sendable wording stay with
    reviewer roles and independent review loops.
- Verification:
  - `git diff --check`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - targeted line-level inspection of edited skill sections

### Slice 9 - Submitted Report Capture And Amendment Deltas

- Status: pending
- Proposed commit message: `feat(workflow): record submitted supervisor report state`
- Expected paths:
  - `scripts/record-submitted-supervisor-report`
  - `scripts/record-report-amendment`
  - `scripts/BUILD`
  - `src/thesis_review_workflow/commands.py`
  - `src/thesis_review_workflow/cli/record_submitted_supervisor_report.py`
  - `src/thesis_review_workflow/cli/record_report_amendment.py`
  - `src/thesis_review_workflow/cli/BUILD`
  - `src/thesis_review_workflow/submitted_reports.py`
  - `src/thesis_review_workflow/amendments.py`
  - `src/thesis_review_workflow/supervisor_report.py`
  - submitted-report/amendment tests
  - smoke scripts
- Tasks:
  - Add submitted-report capture/validation for supervisor reports first: import
    the submitted PDF into the ignored round workspace, extract/hash public
    report text, compare grade/points and public fields against reviewed
    Markdown, and bind the result to supervisor confirmation.
  - Keep the schema generic enough for opponent reports, but do not claim
    opponent submitted-report support until a dedicated slice or follow-up adds
    command coverage.
  - Add a bounded amendment-delta path for post-review wording edits. Minor
    style/private-comment/public-text cleanup records a compact diff and fresh
    approval hash; material claim, grade, or evidence-anchor changes still
    trigger normal semantic review.
  - Keep submitted PDFs, extracts, amendment records, and operator logs under
    ignored case workspaces.
  - Package new operator commands for Windows launchers.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - targeted submitted-report/amendment pytest
  - `scripts/smoke-supervisor-report`
  - new submitted-report/amendment smoke scripts
  - `scripts/smoke-package-workflow-tools`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 10 - Manifest Refresh Ordering And Helper-Check Reuse

- Status: pending
- Proposed commit message: `fix(workflow): make manifest refresh single-pass`
- Expected paths:
  - `src/thesis_review_workflow/cli/init_review_manifest.py`
  - `src/thesis_review_workflow/review_approvals.py`
  - `src/thesis_review_workflow/agent_coverage.py`
  - `src/thesis_review_workflow/cli/check_agent_coverage.py`
  - manifest/approval tests
- Tasks:
  - Apply structured review approval records before agent coverage generation and
    helper-check execution so one manifest refresh is enough after approval
    changes.
  - Add optional incremental recording for pure helper checks when command,
    checker version, target hashes, and previous pass status match.
  - Limit helper-check reuse to read-only deterministic checks; never skip
    semantic review, approval, or user-facing output validation from cache alone.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests::`
  - `pants check src/thesis_review_workflow:: tests::`
  - targeted manifest/approval pytest
  - `scripts/smoke-review-approval`
  - `scripts/smoke-review-manifest`
  - `scripts/smoke-supervisor-report`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

### Slice 11 - Context-Budget Audit Command

- Status: pending
- Proposed commit message: `feat(workflow): add context budget audit`
- Expected paths:
  - `scripts/audit-context-budget`
  - `scripts/BUILD`
  - `src/thesis_review_workflow/commands.py`
  - `src/thesis_review_workflow/cli/audit_context_budget.py`
  - `src/thesis_review_workflow/cli/BUILD`
  - `src/thesis_review_workflow/context_budget.py`
  - `tests/test_context_budget.py`
  - `scripts/smoke-audit-context-budget`
- Tasks:
  - Add a context-budget report that estimates common briefing, role packet,
    capsule, claim-basis, and handoff size and warns when a workflow regresses
    toward raw-artifact transfer.
  - Wire the command through the normal workflow command surface:
    `commands.py`, CLI `BUILD`, shell wrapper, `scripts/BUILD` PEX entry,
    package metadata, and smoke coverage.
  - Keep the audit deterministic and advisory. It may flag oversized context
    surfaces, but must not decide semantic quality or readiness.
- Verification:
  - `pants fmt ::`
  - `pants lint src/thesis_review_workflow:: tests:: scripts::`
  - `pants check src/thesis_review_workflow:: tests:: scripts::`
  - `pants test tests/test_context_budget.py tests/test_workflow_python_contracts.py`
  - `scripts/audit-context-budget --help`
  - `scripts/smoke-audit-context-budget`
  - `scripts/smoke-package-workflow-tools`
  - `scripts/check-private`
  - `scripts/check-scripts`
  - `git diff --check`

## Progress

- 2026-05-13: Slice 3 started. Sanity review passed: Slice 2 is committed as
  `7e5c0c2`, the only unrelated worktree change is still `TODO.md`, and Slice 3
  is scoped to a standard workflow command plus ignored current-round
  `work/reuse/reuse_index.json` output. Command-surface and Windows packaging
  coverage must be updated in the same slice.
- 2026-05-13: Slice 3 implementation and agent review complete. Added
  `scripts/update-round-reuse-index`, standard command/PEX/package coverage,
  `work/reuse/reuse_index.json` validation, and smoke coverage. Fixed reviewer
  findings by validating PDF sidecar currentness, requiring complete observed
  role-source coverage before reuse, requiring `check-agent-coverage` as the
  reusable prior-artifact gate, limiting `--backfill-current` to the active
  current round, and ranking older eligible candidates ahead of nearer stale
  candidates. Verification passed: `pants fmt ::`, `pants lint
  src/thesis_review_workflow:: tests:: scripts::`, `pants check
  src/thesis_review_workflow:: tests:: scripts::`, targeted pytest for reuse,
  round-reuse, work-artifact, workflow-contract, and PDF helper tests,
  `scripts/smoke-round-reuse-index`, `scripts/smoke-package-workflow-tools`,
  `scripts/check-private`, `scripts/check-scripts`, and `git diff --check`.
  Ready to commit Slice 3.
- 2026-05-13: Slice 2 started. Sanity review passed: Slice 1 is committed,
  the only unrelated worktree change is `TODO.md`, and the Slice 2 scope is
  limited to deterministic PDF/code/GitHub fingerprints plus focused tests and
  smokes. No private case data will be read into tracked files.
- 2026-05-13: Slice 2 implementation and agent review complete. Added
  hash-bound PDF extraction sidecars with explicit backfill, code-workspace
  manifest fingerprint exposure, and a GitHub snapshot manifest for PR/repo,
  changed-file, checks, and checkout identity. Fixed reviewer finding by binding
  the GitHub snapshot manifest to `case_id`/`round_id` so provenance validation
  accepts it. Verification passed: `pants fmt ::`, `pants lint
  src/thesis_review_workflow:: tests:: scripts::`, `pants check
  src/thesis_review_workflow:: tests:: scripts::`, targeted pytest for
  PDF/GitHub/code-workspace/work-artifact helpers,
  `scripts/smoke-prepare-code-workspace`, `scripts/smoke-github-code-intake`,
  `scripts/check-private`, `scripts/check-scripts`, and `git diff --check`.
  Ready to commit Slice 2.
- 2026-05-13: Slice 1 started. Sanity review passed: scope is limited to the
  tracked plan, a pure reuse/dependency model, and focused tests. Existing
  `TODO.md` modifications are outside this slice and must not be staged with the
  Slice 1 commit.
- 2026-05-13: Slice 1 implementation drafted in
  `src/thesis_review_workflow/reuse.py` and `tests/test_reuse.py`. Local
  verification passed: `pants fmt ::`, `pants lint src/thesis_review_workflow::
  tests::`, `pants check src/thesis_review_workflow:: tests::`,
  `pants test tests/test_reuse.py`, `scripts/check-private`,
  `scripts/check-scripts`, and `git diff --check`. Agent review in progress.
- 2026-05-13: Slice 1 agent review complete. Fixed findings: missing/legacy
  prior fingerprints now stay `not_comparable`, `FRESH_ROLE_REVIEW` coverage
  cannot be reused, duplicate fingerprints are rejected, empty current
  role-relevant sources preserve removed refs, and common-briefing dependencies
  include previous feedback. Verification rerun passed with the same Slice 1
  gate. Ready to commit Slice 1.
- 2026-05-13: Initial audit complete. Plan created from findings; no
  implementation started.
- 2026-05-13: Broadened audit beyond unchanged-file reuse to role activation,
  packet/common-context repetition, final-review scope, and deterministic
  closeout churn. Plan updated; no implementation started.
- 2026-05-13: Added parent/subagent context-boundary architecture: typed
  evidence capsules, claim-level review basis, targeted drill-down, and
  context-budget instrumentation. Plan updated; no implementation started.
- 2026-05-13: Added lessons from a final supervisor-report closeout: submitted
  report capture, bounded post-review wording amendments, and manifest refresh
  ordering after approval changes. Plan updated; no implementation started.
- 2026-05-13: Multi-agent plan review complete. Findings folded in: gate
  semantics no longer use `required verification: none`; over-broad slices were
  split; minimal capsule/claim-basis schemas moved earlier; supervisor-report
  packets, command-surface packaging, backfill behavior, and final smoke coverage
  were made explicit. No implementation started.

## Decision Log

- Keep reuse explicit and hash-bound. Do not add a fallback layer that silently
  accepts old conclusions.
- Treat figure/media reuse as the model pattern: separate stable source identity
  from context-dependent claim alignment.
- Deterministic helpers may compare hashes, schemas, paths, and structured
  metadata. They must not decide whether a thesis/code claim is semantically
  still valid from raw free text.
- Mandatory roles stay mandatory. The improvement is that a role can be
  satisfied by current reviewed evidence plus a recorded delta decision when
  source hashes prove the relevant evidence is unchanged.
- Coverage requirements and fresh-review requirements are separate states. A
  workflow can require a role to be represented without requiring a new full
  semantic pass when current reviewed evidence or a typed no-material-issue
  handoff satisfies the role.
- Prompt budget is part of the contract. Common context should be written once,
  role packets should carry role deltas, and final reviewers should start from
  claim-level `claim_review_basis` refs before opening broad raw evidence.
- Subagents are useful as context isolators only when they return structured,
  anchor-rich capsules. Passing raw subagent histories or broad Markdown dumps
  back to the parent would move the token problem rather than solve it.
- Do not let reader capsules replace reviewer judgment. Capsules reduce raw
  context load; reviewer roles still own semantic findings, grade-impacting
  interpretations, and sendable wording.
- The submitted report is a separate state from the reviewed draft. Capture the
  submitted artifact and its public text/hash instead of relying on future
  agents to infer what was sent from local Markdown or chat history.
- Minor post-review wording edits should be explicit deltas, not hidden
  rewrites. The workflow should preserve independent approval while letting
  reviewers inspect the changed text first and escalate only when claims,
  grade/points, or evidence anchors changed.

## Final Audit

Not started. When implemented, close with:

```bash
pants fmt ::
pants lint src/thesis_review_workflow:: tests:: scripts::
pants check src/thesis_review_workflow:: tests:: scripts::
pants test tests/test_reuse.py tests/test_evidence_capsules.py tests/test_claim_review_basis.py tests/test_context_budget.py tests/test_workflow_python_contracts.py
scripts/smoke-prepare-code-workspace
scripts/smoke-github-code-intake
scripts/smoke-round-reuse-index
scripts/smoke-supervisor-packets
scripts/smoke-opponent-packets
scripts/smoke-supervisor-report-packets
scripts/smoke-review-wave
scripts/smoke-review-manifest
scripts/smoke-register-review-artifact
scripts/smoke-review-approval
scripts/smoke-supervisor-report
scripts/smoke-audit-context-budget
scripts/smoke-package-workflow-tools
scripts/check-private
scripts/check-scripts
git diff --check
```

Record any intentionally skipped smoke, missing platform proof, or residual risk
before moving this plan to `plans/archive/`.
