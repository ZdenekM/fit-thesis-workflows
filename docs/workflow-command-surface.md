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

The optimized review pipeline uses shared round-level commands before
workflow-specific packet generation. `review-round-start` is the deterministic
entrypoint for current-material registration, PDF extraction, GitHub/code
workspace preparation, current-evidence refresh, reuse-index refresh, readiness
gates, and `work/review_run_trace.json`. It accepts workflow review profiles
such as `supervisor_feedback`, `supervisor_report`, and `opponent_materials`;
these are not Codex agent profiles. The command deliberately stops at the
`prepare-review-round <case-id> <round-id>` boundary and must not write
`work/review_role_plan.json`.

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
workflow execution.

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
