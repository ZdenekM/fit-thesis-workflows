# Agent Scheduling

This workflow uses role coverage, not unlimited concurrency. When a user
explicitly authorizes agents, keep review quality and required role separation,
but bound the number of live agents so thesis rounds can run on machines with
limited RAM.

Command routing: `scripts/<tool>` examples in this document are Linux/dev
shorthand and logical workflow command names. On Windows, package the workflow
tools first and use `dist\workflow-tools\bin\<tool>.cmd` or the matching
PowerShell launcher; do not run or click extensionless `scripts/<tool>` files.

## Default Limit

- Run at most 2 spawned workflow agents concurrently by default.
- Use 1 concurrent spawned workflow agent when the machine is memory constrained
  or the case artifacts are unusually large.
- Do not run more than 2 concurrent spawned workflow agents under the tracked
  project config. Higher concurrency requires an intentional config change
  before the run.

The limit is about live spawned agents, excluding the main Codex session. It does
not reduce required role coverage, independent review, manifest evidence, or
`scripts/check-agent-coverage`.

The runtime default is enforced in `.codex/config.toml` with
`agents.max_threads = 2`, `agents.max_depth = 1`, and
`agents.job_max_runtime_seconds = 3600`. Keep this document aligned with that
config if the project default changes. Role-to-profile routing is tracked in
`docs/agent-profile-matrix.md`; keep that matrix and
`src/thesis_review_workflow/agent_profiles.py` aligned when adding or changing a
repo-local workflow skill.

## Model And Reasoning Defaults

Quality-critical thesis-review roles should use the strongest available model
and reasoning effort. The tracked thesis reviewer profiles under `.codex/agents/`
therefore default to `gpt-5.5` with `model_reasoning_effort = "xhigh"` for every
semantic role listed as `profile` in `docs/agent-profile-matrix.md`.

Do not downshift semantic roles that read thesis text, submitted code,
evidence artifacts, synthesis drafts, or final/reviewable outputs. Cheaper
models such as `gpt-5.3-codex-spark` are candidates only for mechanical,
validator-backed helper roles such as packet inventory summaries, expected-file
checks, or manifest-shape triage. Any Spark-produced helper output must be
validated by deterministic checks and reviewed by a high-reasoning semantic role
before it can affect evidence claims, grading/report calibration, or sendable
wording.

## Wave Pattern

Run agents in waves and let each wave finish before starting the next one. Do
not terminate an agent merely to free a slot unless the user redirects the task
or the agent is clearly blocked.

Typical supervisor/opponent waves:

1. Preparation by the main agent: readiness checks, round orientation, previous
   feedback, code workspace, GitHub intake preconditions.
2. Evidence wave: text/assignment coverage plus code consistency when both are
   needed.
3. Evidence wave: code quality plus quantitative claims, figure/media,
   literature, typography, or Theses.cz similarity-report review, depending on
   round triggers and available inputs.
4. Calibration wave: evidence/claim calibration or grading calibration when the
   workflow needs it.
5. Synthesis: integrate findings into the draft or final Markdown artifact.
6. Independent review: use a different agent from the generator/finalizer for
   the required review pass.

Standalone evidence workflows can use the same pattern with fewer waves: one
generator role, then a different reviewer role if the artifact will be relied on
as final standalone evidence.

## Packet And Wave Gates

`work/supervisor_packets/*.md` and `work/opponent_packets/*.md` are compact
handoffs for spawned agents. They reduce repeated context and prompt drift; they
do not reduce required role coverage, skill obligations, independent review, or
manifest/coverage checks.

Optimized rounds should reach role spawning through the deterministic boundary
`review-round-start` followed by `prepare-review-round`. The second command
writes `work/review_role_plan.json`; parent agents should treat that plan as
the wave schedule and role-state source of truth rather than reconstructing
role needs from chat. Role states mean:

- `required_fresh`: spawn or otherwise produce current role evidence, then
  register the output or record a concrete typed limitation;
- `delta_review`: current evidence changed enough that a scoped role review is
  required even if prior reviewed evidence exists;
- `reusable_current`: current `work/agent_coverage.json` and reuse-index
  evidence already satisfy coverage with a current reviewed artifact;
- `blocked_with_typed_limitation`: closeout needs a concrete limitation record
  rather than silent omission.

`review-round-start`, `prepare-review-round`, and `review-round-closeout` are
workflow-profile commands. They use values such as `supervisor_feedback`,
`supervisor_report`, `opponent_materials`, and `opponent_report_review`; those
are not Codex agent profiles from `.codex/agents/` or
`docs/agent-profile-matrix.md`.

The main session should inventory available `inputs/`, `extracted/`, `notes/`,
`work/`, and `outputs/` paths, but should not treat that inventory as permission
to load every raw source into the parent context. Start from
`work/common_briefing.json`, role packets, current-evidence snapshots,
materiality decisions, reuse-index decisions, structured evidence artifacts, and
`work/context/claim_review_basis.json` when present. Open full thesis, code,
README, result, note, or generated-output artifacts only for explicit triggers:
changed source fingerprints, missing anchors, contradiction, P0/P1 or
grade-impacting verification, reviewer challenge, unsupported synthesis wording,
or a role packet that cannot be resolved from current
`work/context/evidence_capsules.json` capsule refs.

Reusable capsules and reuse decisions satisfy context-routing needs only. They
do not waive DEEP mode, required semantic role coverage, the generator/reviewer
separation, approval records, review-manifest hashes, or
`scripts/check-agent-coverage`. Reader or helper agents should stay extractive:
they may summarize, anchor, and structurally classify evidence by source type,
source status, extraction confidence, and missing fields, but support verdicts,
materiality, severity, grade impact, thesis/code consistency judgments, sendable
wording, and final report calibration belong to the authorized semantic reviewer
roles and their independent review loop.

After a role wave, run the relevant `scripts/check-review-wave` profile before
using agent claims from the chat transcript. If an agent says it wrote a file but
the expected file is missing, empty, stale, or fails whitespace/approval-record
validation, trust the file system and checker result. The next step is to repair
or regenerate the artifact, not to rely on the agent final message.

If a required role agent or helper fails, times out, or exits without the
expected role-owned artifact, stop the wave. Do not satisfy role coverage by
writing a smaller parent-owned substitute and continuing. Report the failed
role, expected path, observed state, and checker result to the operator, then
rerun/repair the role or record a blocked typed limitation only after the
operator has chosen that route.

Structured final-review approval records belong under `work/reviews/*_review.json`.
They are part of closeout provenance: a material edit after approval requires a
fresh review or an explicit typed exception, never a manual hash adjustment.

## Subagent Handoffs

Subagent final responses should optimize for parent synthesis, not raw
transcript transfer. Do not paste raw logs, grep dumps, long stack traces, or
full file contents into final chat responses unless a minimal excerpt is needed
to support a finding. Prefer evidence references such as `file:line`,
`file:line-line`, `file:symbol`, artifact paths, command names, and verification
status.

Default handoff shape:

- one-paragraph summary;
- up to 5 prioritized findings with severity;
- exact evidence references;
- confidence per finding: high / medium / low;
- recommended next action.

If there are more than 5 findings, report the top findings and state how many
lower-priority findings were omitted unless the task explicitly requires
exhaustive coverage. If a subagent owns a required artifact or code change, it
must write it to disk and return only a concise handoff summary, changed paths,
and verification status. The parent agent must synthesize subagent outputs into
decisions, fixes, or final artifacts rather than concatenating subagent
responses.

This handoff rule does not override repo skills, role-owned outputs, required
review artifacts, coverage manifests, exhaustive audit requirements, or
validation checks.

## Non-Negotiables

- Required roles remain required even when the concurrency limit is 1.
- Code-bearing supervisor/opponent rounds still need both code consistency and
  code quality evidence, or a concrete limitation explaining why one could not
  be performed.
- Final/sendable artifacts still need an independent review by a different
  agent and a fresh manifest hash.
- Closing agents after they finish is fine; cancelling useful in-progress work
  just to start another role is not serialization.
