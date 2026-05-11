# Agent Scheduling

This workflow uses role coverage, not unlimited concurrency. When a user
explicitly authorizes agents, keep review quality and required role separation,
but bound the number of live agents so thesis rounds can run on machines with
limited RAM.

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
config if the project default changes.

## Model And Reasoning Defaults

Quality-critical thesis-review roles should use the strongest available model
and reasoning effort. The tracked thesis reviewer profiles under `.codex/agents/`
therefore default to `gpt-5.5` with `model_reasoning_effort = "xhigh"` for text
review, code consistency, code quality, and evidence calibration.

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
3. Evidence wave: code quality plus figure/media, literature, or typography,
   depending on round triggers and available inputs.
4. Calibration wave: evidence/claim calibration or grading calibration when the
   workflow needs it.
5. Synthesis: integrate findings into the draft or final Markdown artifact.
6. Independent review: use a different agent from the generator/finalizer for
   the required review pass.

Standalone evidence workflows can use the same pattern with fewer waves: one
generator role, then a different reviewer role if the artifact will be relied on
as final standalone evidence.

## Non-Negotiables

- Required roles remain required even when the concurrency limit is 1.
- Code-bearing supervisor/opponent rounds still need both code consistency and
  code quality evidence, or a concrete limitation explaining why one could not
  be performed.
- Final/sendable artifacts still need an independent review by a different
  agent and a fresh manifest hash.
- Closing agents after they finish is fine; cancelling useful in-progress work
  just to start another role is not serialization.
