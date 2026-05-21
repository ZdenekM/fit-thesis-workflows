# Workflow Command Surface

This repository treats `scripts/<tool>` names as logical workflow commands. The
implementation surface depends on who runs the command and where.

## Command Categories

### Operator Workflow Tools

Operator workflow tools are commands that supervisors, opponents, or agents may
run repeatedly while working on a case. Each tool must have:

- an executable POSIX convenience wrapper under `scripts/`;
- a Python CLI module under `src/thesis_review_workflow/cli/`;
- an entry in `WORKFLOW_COMMAND_MODULES`;
- a `python_source` target in `src/thesis_review_workflow/cli/BUILD`;
- coverage in `WORKFLOW_CLI_RUNTIME_DEPS` when the tool is packaged;
- a `pex_binary(tags=["workflow-tool"])` target in `scripts/BUILD` with
  `output_path="workflow-tools/pex/<tool>"`;
- generated launchers in `dist/workflow-tools/bin/<tool>`,
  `dist/workflow-tools/bin/<tool>.cmd`, and
  `dist/workflow-tools/bin/<tool>.ps1`;
- focused pytest or smoke coverage for the command contract.

Supervisor-report commands follow the same operator-tool contract. In
particular, `check-supervisor-report-ready`, `prepare-supervisor-report-packets`,
`draft-supervisor-report`, `check-supervisor-report`,
`confirm-supervisor-report`, `supervisor-report-closeout`, and
`check-supervisor-report-calibration-profile` must be available through the
logical `scripts/<tool>` name in development checkouts and through generated
`.cmd`/`.ps1` launchers after packaging.

The final supervisor-report operator path is command-surface sensitive because
it is used by role agents as well as humans. `prepare-supervisor-report-packets`
must be run only after current-request agent authorization is explicit; its
normal invocation includes `--agents-authorized` and refreshes current evidence
plus final `supervisor_report` materiality before packet emission. After the
reviewed report and `work/reviews/supervisor_report_review.json` exist,
`init-review-manifest --run-checks`, `confirm-supervisor-report`, and
`supervisor-report-closeout` are the supported closeout surface. Closeout
performs the manifest refresh before final-wave validation and again after
checks that may update provenance; operators should not edit
`work/review_manifest.json` by hand for normal final-report registration.
Post-review operator corrections use `record-review-delta`, which writes the
canonical `work/review_deltas/*.json` record for style/preference corrections,
evidence challenges, material claim changes, and durable workflow lessons.
`record-report-amendment` remains only a supervisor-report convenience wrapper
around that shared delta record; it does not maintain a separate amendment
ledger. Material claim and evidence-challenge deltas reopen the relevant
profile independent review before closeout can pass.
Delta `evidence_refs` must point to stable evidence outside the before/current
artifact pair. Do not cite the updated trace/report artifact itself, the delta
record, or append-only operator notes such as
`notes/opponent-report-operator-feedback.md`; snapshot those notes into a
bounded `work/review_deltas/` or other structured work artifact first.
When a correction raises calibration/profile governance, the same delta record
can include a `classification_reason`, bounded `rejected_targets`,
`privacy_review`, and an optional hash-bound `profile_proposal_ref` under the
ignored round workspace. `private-reviewer-profile:local/<profile-id>` is only a
destination marker for a private profile proposal; it is not a profile update
command and it must not copy private profile text into tracked files.

The optimized review pipeline uses shared round-level commands before
workflow-specific packet generation. `review-round-start` is the deterministic
entrypoint for current-material registration, PDF extraction, GitHub/code
workspace preparation, current-evidence refresh, reuse-index refresh, readiness
gates, and `work/review_run_trace.json`. It accepts workflow review profiles
such as `supervisor_feedback`, `supervisor_report`, and `opponent_materials`;
these are not Codex agent profiles. The command deliberately stops at the
`prepare-review-round <case-id> <round-id>` boundary and must not write
`work/review_role_plan.json`.

`prepare-review-round` is the next deterministic boundary. It reads the
`review-round-start` trace, delegates packet emission to the existing
profile-specific packet command, and writes `work/review_role_plan.json` with
role states, packet refs, bounded wave schedule, materiality next-action states,
reuse projection, and code-bearing role coverage. It prepares files for the
parent agent to spawn authorized role agents; it does not spawn agents itself.

`review-round-closeout` is the shared final closeout surface for optimized
rounds. It first requires `work/review_run_trace.json` and
`work/review_role_plan.json` to match the requested profile, so profile changes
are repaired by rerunning `review-round-start --profile ...` and
`prepare-review-round --profile ...` before manifest state is mutated. It then
refreshes the manifest, validates `work/review_role_plan.json` against current
role outputs, runs the profile final-wave gate, refreshes coverage and manifest
completeness, records a closeout trace event, and then refreshes the manifest
again so the trace hash is not stale. For
`supervisor_report`, `opponent_review`, and `opponent_materials`, the generic
command delegates profile-specific checks to `supervisor-report-closeout` or
`opponent-closeout` while preserving the shared role-plan and trace boundary.

`record-workflow-operation` is the lightweight reconstruction surface for case
work. It appends JSONL events to `work/operation_log.jsonl` when a role fails,
is blocked, is skipped, gets a manual fallback, or receives an operator
calibration decision. This log is deliberately separate from
`work/review_manifest.json` hash gating so diagnostic notes do not make a closed
manifest stale.

Default colleague/operator issue reporting is case-local. Put limitations,
sanitized issue reports, review deltas, and operation events under the ignored
round workspace, and cite tracked workflow owners only by public path when a
fix should be considered later. Editing tracked workflow/docs/skills/tests is
maintainer work: it requires explicit current-request consent, keeps the same
DEEP/review requirements, and must run `scripts/check-private` before commit.
That consent is a write-scope opt-in only; it is not a second review mode,
profile-update command, closeout shortcut, or alternate command surface.

`refresh-round-hashes` is a deterministic maintenance surface for stale helper
hashes after operator-note or approval-record edits. It currently refreshes
existing support metadata in `work/current_evidence_snapshot.json` and
`work/common_briefing.json` only. It must not change approval records,
`work/review_deltas/*.json`, report text, grades, verdicts, private comments,
or semantic findings; material report changes still go through
`record-review-delta` and the relevant independent review loop.
If current-evidence support metadata cannot be rebuilt safely, repair it with
`update-current-evidence-snapshot <case-id> [round-id]` using explicit refs
before rerunning materiality or closeout checks.
When refreshing an existing supervisor-report common briefing, it preserves the
stored `workflow_profile` / `report_calibration_scope` boundary and must not
reintroduce the opponent-report `work/report_calibration_basis.json` into
supervisor-report handoffs.

`check-report-calibration` is the deterministic checker for the opponent-report
reviewer-profile application basis. It validates structured JSON, hashes,
profile/operator source records, expected IS values, grade/point intervals,
defense-question count, private-comment requirement, and stale-input state. It
does not interpret free-form profile prose. The helper is required when an
opponent report trace, draft, clean export, or independent report-review basis
is bound to `work/report_calibration_basis.json`. It is not a supervisor-report
gate; supervisor reports use their own trace, confirmation, review, and
optional supervisor-report calibration artifacts.

On Linux development checkouts the POSIX `scripts/<tool>` wrappers are fine for
quick use. On Windows, do not run or click extensionless `scripts/<tool>` files:
Windows treats them as files to open, not native commands, and may show a
"Select an app" dialog. For repeated operator and agent runs, package the tools
first and use `dist/workflow-tools/bin/`.

### Packaging Bootstrap Commands

`scripts/package-workflow-tools` and its `.cmd`/`.ps1` variants are bootstrap
commands. They run `thesis_review_workflow.cli.package_workflow_tools`, package
all `workflow-tool` PEX targets, and generate POSIX, `.cmd`, and `.ps1`
launchers.

The packaging bootstrap is intentionally not an operator workflow tool:

- it is not in `WORKFLOW_COMMAND_MODULES`;
- it is not a `workflow-tool` PEX target;
- it must remain runnable from POSIX, Windows cmd, and PowerShell before the
  generated package exists.

### Generated Package Launchers

Generated launchers under `dist/workflow-tools/bin/` are build outputs, not
tracked source. They are the preferred repeated-run surface after packaging.

The launchers:

- run from the repository root while preserving the original caller cwd in
  `THESIS_REVIEW_CALLER_CWD`;
- clear `PYTHONPATH` so local source shadowing does not leak into packaged runs;
- default `PEX_ROOT` to `.pants.d/pex_root` inside the repository;
- require Python 3.12, with `WORKFLOW_TOOLS_PYTHON` as an explicit override.

Generated provenance such as `work/review_manifest.json` stores helper check
commands as logical workflow command names, for example
`check-supervisor-ready <case-id> [round-id]`, not as POSIX wrapper
paths. Repository Python runners resolve those logical names directly to CLI
modules; Windows operators should translate them to the matching packaged
`.cmd` or `.ps1` launcher.

### Developer Smokes

`scripts/smoke-*` commands are development and closeout checks. They may remain
POSIX shell scripts and are not operator entrypoints unless they are separately
promoted into the operator workflow-tool contract.

`scripts/smoke-package-workflow-tools` proves generated launcher structure and
POSIX launcher execution in this Linux checkout. It checks that `.cmd` and
`.ps1` launchers are generated with the expected content, but it is not native
Windows runtime proof.

### Dev Hygiene Targets

`pants run :vulture`, `pants run :jscpd`, and `pants run :omen` are developer
hygiene signals. They help maintain the repository as it grows, but they are not
case-pipeline gates and must not be required for normal supervisor or opponent
workflow execution. The repo Omen target intentionally ignores `cases/`; a
code-quality reviewer may still run targeted Omen advisory analysis inside an
ignored prepared case workspace and record it as case-local evidence.

## Windows Evidence Boundary

Windows is a supported operator platform. A new operator workflow command is not
complete until it can be packaged into `.cmd` and `.ps1` launchers.

Linux checks can prove:

- command registry consistency;
- generated launcher presence and structure;
- POSIX launcher behavior;
- package independence from the source checkout.

Native Windows runtime behavior requires an actual Windows cmd, PowerShell, or
CI run. Do not present Linux structural checks as Windows runtime evidence.
