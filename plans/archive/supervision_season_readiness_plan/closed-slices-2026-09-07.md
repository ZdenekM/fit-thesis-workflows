# Closed Slice Charters - Supervision Season Readiness Plan

Append-only. Each entry is the charter as it stood when the slice closed.

### Slice 2 - Carry an explicit early phase end to end, and unblock the season gate

- Status: done
- Proposed commit message: `Add 2026/2027 deadlines and carry an explicit early review phase`
- Why: the readiness gate fails for the new academic year, and the phase that
  every later slice keys on cannot reach the deterministic layer at all. Adding
  the enum value without its carrier would produce unreachable code, so the
  carrier and the enum land together with end-to-end tests.
- Expected paths: `config/supervisor-deadlines.tsv`,
  `src/thesis_review_workflow/review_materiality.py`,
  `src/thesis_review_workflow/review_pipeline_orchestration.py`,
  `src/thesis_review_workflow/cli/review_round_start.py`,
  `src/thesis_review_workflow/cli/prepare_review_round.py`,
  `src/thesis_review_workflow/cli/review_round_closeout.py`,
  `tests/test_review_materiality.py`,
  `tests/test_review_pipeline_orchestration.py`,
  `tests/test_supervisor_ready.py`, `tests/BUILD`, `config/BUILD`,
  `docs/operator-reference.md`, `docs/workflow-command-surface.md`
- Tasks:
  - Add 2026/2027 BP and DP rows with every column filled from
    operator-supplied values: `official_deadline`, `recommended_finish`,
    `deferred_window`, `notes`. Do not guess or leave a field blank; stop for
    the operator when a value is unknown, because a blank `recommended_finish`
    silently retargets calibration to the official deadline.
  - Add an `early` phase to the materiality phase set, plus a
    `DECLARABLE_PHASES` set for the phases an operator may declare, which the
    `check-review-materiality`, `review-round-start` and `prepare-review-round`
    argument surfaces derive their choices from.
  - Add an explicit review-phase option to `scripts/review-round-start`, persist
    it as a validated top-level `review_phase` field of
    `work/review_run_trace.json` — `phase` is already taken by the per-event
    `review_pipeline_orchestration.py::TracePhase` — and read it in
    `prepare_review_round.py::refresh_materiality_before_packets` so the
    materiality refresh passes the declared phase instead of defaulting to
    `auto`. Keep `supervisor_report` pinned to `final`.
  - Add a pass-through phase option to `scripts/prepare-review-round` for a
    round whose trace predates the field. Make the refresh helper's phase
    parameter required rather than defaulting, so a future call site cannot
    silently drop the declared phase, which is the failure the charter review
    found.
  - Give `config/supervisor-deadlines.tsv` a `files` target and depend on it
    from `tests/BUILD`, so a test can assert the shipped configuration rather
    than a fixture copy of it.
  - Extend the tests: `early` is accepted end to end from round start to the
    materiality decision, an absent field still resolves as today, an unknown
    phase still errors, and a 2026/2027 case reaches a passing
    `check-supervisor-ready` with a recommended-finish-based calibration line.
  - Regenerate the packaged launchers if the command surface changed, and note
    the new option and the deadline prerequisite in `docs/operator-reference.md`.
- Out of scope: the early-phase role set (Slice 3), the feedback output shape
  (Slice 4), inference of the phase from round contents, and any change to how
  `final` behaves.
- Verification:
  - `pants test tests/test_review_materiality.py`
  - `pants test tests/test_review_pipeline_orchestration.py`
  - `pants test tests/test_supervisor_ready.py`
  - `scripts/smoke-prepare-review-round`
  - `scripts/smoke-review-round-start`
  - `pants test tests/test_workflow_python_contracts.py tests/test_work_artifacts.py`
  - `pants test tests/test_review_round_closeout.py tests/test_closeout_preflight.py`
  - `scripts/smoke-review-round-closeout`
  - `pants lint` over the touched modules and tests
  - `pants run :omen` as dev-hygiene evidence, since code changed materially
  - `scripts/check-scripts`
  - `python3 tests/test_plan_contract.py`

