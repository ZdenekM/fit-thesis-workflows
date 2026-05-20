# Reviewer Profile Application Contract Plan

Status: active
Created: 2026-05-20

## Goal

Make reviewer-profile and operator-calibration preferences visible, current, and
verifiably applied in the generated opponent-report workflow.

V1 is opponent-report-only. Supervisor-report reuse is a deliberate later
boundary decision because the repository already has separate supervisor-report
calibration artifacts and confirmation gates. This plan must not quietly create a
half-integrated generic calibration subsystem.

The current repository can validate that a reviewer profile exists and can pass
profile files to agents as context. That is not enough. The target behavior is:

- the workflow identifies which profile/operator preferences are relevant to
  the current report;
- those preferences are recorded in a case-local, hash-bound calibration basis;
- report trace, draft, clean export, and independent report review consume that
  basis explicitly;
- deterministic helpers validate structured facts such as selected IS values,
  point/grade bands, defense-question count, and source hashes;
- semantic interpretation remains in authorized human/agent review, not in
  brittle free-text matching.

## Audit Base

This plan is based on a recent final opponent-report loop in an ignored
`cases/` workspace. The concrete student, thesis, and report content remain
private; only workflow-level findings are recorded here.

Observed workflow failures:

- `scripts/check-reviewer-profile` correctly reported effective files
  `profiles/default.md` and `profiles/local/default.md`, but downstream report
  trace generation treated those files as advisory context rather than as an
  applied checklist.
- `work/common_briefing.json` included `reviewer_profile_inputs`, but only as
  file records. It did not include an extracted current-case calibration basis,
  and it did not automatically incorporate later operator notes that changed
  report calibration.
- `work/opponent_report_trace.json` could remain valid while containing report
  formulations that contradicted durable local-profile preferences, such as
  inflating routine web/mobile/backend stack difficulty, giving too much weight
  to implementation breadth, keeping too many defense questions, or using a
  grade band inconsistent with the selected assignment-fulfillment level.
- `scripts/draft-opponent-report` deterministically copied formulations and
  questions from `work/opponent_report_trace.json`; it did not apply reviewer
  profile preferences itself and had no structured calibration basis to check.
- `scripts/check-opponent-report` validated shape, privacy, headings, concrete
  points, grade, and IS values, but not consistency with structured
  reviewer-profile application decisions.
- Independent report review could catch profile drift after the operator
  complained, but that made profile use reactive instead of part of the normal
  report contract.

Repository paths inspected while creating this plan:

```bash
scripts/check-reviewer-profile <case-id>
sed -n '1,280p' profiles/local/default.md
sed -n '1,380p' src/thesis_review_workflow/cli/draft_opponent_report.py
sed -n '1,420p' src/thesis_review_workflow/cli/check_opponent_report.py
sed -n '1,770p' src/thesis_review_workflow/review_packets.py
sed -n '330,470p' src/thesis_review_workflow/opponent_packets.py
sed -n '1,150p' .agents/skills/thesis-opponent-materials-review/SKILL.md
sed -n '1,260p' .agents/skills/thesis-opponent-report-review/SKILL.md
```

Existing useful controls:

- Reviewer profiles are already private-by-default, validated through
  `scripts/check-reviewer-profile`, and listed in common briefing.
- Repo instructions already require storing durable personal preferences in the
  active private reviewer profile after current artifacts are fixed.
- The free-text boundary is explicit: deterministic code must not infer meaning
  from raw thesis/report/profile prose. Semantic profile application must be
  human/agent-authored and then validated structurally.
- Opponent reports already have a trace-bound canonical draft, clean export,
  report review, and validators. The missing piece is a first-class calibration
  basis that those steps can consume.
- Existing historical/opponent calibration artifacts already exist:
  `work/opponent_calibration_use.json`, `work/opponent_calibration_advisory.json`,
  `work/opponent_report_revision_request.json`, and trace-level
  `calibration_context`. They are source-binding and optional historical or
  operator-feedback revision controls. The new contract must compose with them;
  it must not create a second independent calibration authority.

## Scope

In scope:

- Add a case-local structured artifact for applied reviewer-profile and
  operator-calibration decisions.
- Include explicit hashes for source profile files and operator-calibration
  notes used by that artifact.
- Update common briefing and role packets so agents start from the applied
  calibration basis, not from raw profile files alone.
- Bind opponent report trace and report review to the calibration basis.
- Add deterministic checks for structured calibration expectations, such as:
  expected IS selectbox values, point/grade interval, defense-question count,
  and stale profile/operator-note hashes.
- Update opponent-materials, opponent-report-review, and relevant docs so the
  normal workflow makes profile application visible.
- Integrate the new checker into the full workflow command surface, including
  command registry, Pants targets, PEX packaging, and Windows launchers.
- Update privacy and provenance helpers so `work/report_calibration_basis.json`
  is treated as private case-local evidence and is hash-bound in manifests,
  approval records, and report checks.
- Add focused synthetic tests and smoke coverage.
- Keep the existing TODO entry pointing to this plan until the plan is
  implemented and archived.

Out of scope:

- Adding real private profile text, real case facts, or student report excerpts
  to tracked files.
- Automatically interpreting arbitrary profile prose with deterministic string
  matching.
- Historical opponent-report calibration. That remains a separate optional
  workflow in `plans/historical_opponent_calibration_plan.md`.
- Automatic grading. The workflow may validate a human/agent-authored expected
  grade/point band, but it must not calculate the grade from profile text.
- Backward compatibility with older `~/code/diplomky` workflow layouts.
- Replacing or deprecating the existing historical opponent-calibration
  workflow. If this implementation later proves that those artifacts should be
  merged into the report-calibration basis, write a separate migration plan
  instead of changing their meaning in-place.
- Broad filename-glob discovery of semantic operator notes. Deterministic
  helpers may use fixed logical note paths and typed operation/delta artifacts,
  but they must not route report calibration from arbitrary note filenames.

## Target Contract

Add a structured artifact under each relevant round:

```text
work/report_calibration_basis.json
```

Suggested schema version:

```json
{
  "schema_version": "report-calibration-basis-v1",
  "case_id": "<case-id>",
  "round_id": "<round-id>",
  "calibration_scope": "opponent_report",
  "reviewer_profile_id": "default",
  "workflow_profile": "opponent_review",
  "operator_surface": "opponent_materials",
  "wave_workflow": "opponent_report",
  "generated_at": "<iso8601>",
  "producer_type": "agent|human",
  "producer_role": "<role>",
  "producer_agent": "<nullable>",
  "authorization_note": "<string>",
  "source_refs": [
    "notes/opponent-report-operator-feedback.md",
    "work/opponent_report_revision_request.json"
  ],
  "profile_sources": [
    {
      "path": "profiles/default.md",
      "sha256": "<hash>",
      "sections_used": ["Opponent Report Style"]
    }
  ],
  "operator_calibration_sources": [
    {
      "path": "notes/opponent-report-operator-feedback.md",
      "sha256": "<hash>",
      "purpose": "report calibration"
    }
  ],
  "related_calibration_artifacts": [
    {
      "path": "work/opponent_report_revision_request.json",
      "sha256": "<hash>",
      "relationship": "operator_feedback_source"
    }
  ],
  "applied_preferences": [
    {
      "preference_id": "opponent.assignment_difficulty.stack_not_enough",
      "source_keys": ["profile:profiles/local/default.md", "operator:notes/opponent-report-operator-feedback.md"],
      "applies_to": ["assignment_difficulty"],
      "instruction": "Do not rate routine web/mobile/backend stack as above average unless higher difficulty is supported by domain collaboration, methodology, or unusual technical risk.",
      "priority": "must|should|advisory",
      "status": "applied|not_applicable|conflict",
      "decision_reason": "<short evidence-bound reason>"
    }
  ],
  "expected_report_controls": {
    "is_select_values": {
      "Náročnost zadání": "průměrně obtížné zadání",
      "Rozsah splnění požadavků zadání": "zadání splněno s vážnějšími výhradami"
    },
    "overall_grade": "D",
    "overall_points_interval": [65, 74],
    "defense_question_count": {
      "min": 1,
      "max": 3
    },
    "public_report_length": "compact",
    "private_comment_required": true
  },
  "limitations": []
}
```

Rules:

- This artifact is semantic. It is written by a human or explicitly authorized
  semantic reviewer agent, not by deterministic profile-prose parsing.
- Common structured-evidence `source_refs` remain round-local refs only. Profile
  files use `profile_sources`, and operator/profile source objects deliberately
  avoid a `*_refs` field name because the generic structured-evidence ref walker
  treats every `*_refs` value as a list of round-local string refs.
- Deterministic validators may check schema, source hashes, safe paths, allowed
  enum values, expected IS values, point/grade interval consistency, and count
  bounds.
- Profile source paths are repo-relative and whitelisted to
  `profiles/default.md` or ignored `profiles/local/<profile-id>.md`. Operator
  calibration source paths are round-relative and whitelisted to fixed logical
  paths such as `notes/opponent-report-operator-feedback.md`,
  `notes/opponent-report-review-intake.md`, `work/review_deltas/*.json`,
  `work/operation_log.jsonl`, and `work/opponent_report_revision_request.json`.
- The artifact may reference profile lines or operator notes, but public report
  prose must not expose private profile paths, raw operator-note paths, hashes,
  or internal workflow mechanics.

Relationship to existing calibration artifacts:

- `work/report_calibration_basis.json` is the ordinary current-case application
  basis for reviewer-profile and operator-calibration preferences before report
  drafting.
- `work/opponent_calibration_use.json`,
  `work/opponent_calibration_advisory.json`, and trace `calibration_context`
  remain historical/reference-report calibration and operator-feedback
  source-binding artifacts.
- If either existing calibration artifact influenced the report, the basis must
  list it under `related_calibration_artifacts`, and the trace must bind both the
  basis and the existing `calibration_context`. Validators must reject stale
  hashes or conflicting controls rather than letting both artifacts make
  independent claims about grade, IS selections, or defense questions.

## Slices

### Slice 1 - Schema And Validator

Implement the structured artifact contract.

Expected paths:

- `src/thesis_review_workflow/report_calibration.py`
- `src/thesis_review_workflow/structured_evidence.py`
- `src/thesis_review_workflow/work_artifacts.py`
- `scripts/check-report-calibration`
- `src/thesis_review_workflow/cli/check_report_calibration.py`
- `src/thesis_review_workflow/commands.py`
- `src/thesis_review_workflow/cli/BUILD`
- `scripts/BUILD`
- `scripts/smoke-report-calibration`
- `src/thesis_review_workflow/cli/check_private.py`
- `scripts/smoke-private`
- synthetic fixtures/tests under tracked test paths

Work:

- Add `work/report_calibration_basis.json` as a known private work artifact.
- Add a dedicated validator instead of relying only on the generic
  `structured_evidence` ref walker. The validator must accept round-local
  `source_refs`, explicitly whitelisted repo-profile paths in
  `profile_sources`, fixed round-local operator-calibration sources, source
  hashes, workflow-profile fields, producer metadata, applied preference
  statuses, expected control shapes, and limitations.
- Register the artifact in supporting-work collection and privacy checks so it
  cannot be accidentally tracked outside ignored `cases/`.
- Add a helper command:

  ```bash
  scripts/check-report-calibration <case-id> [round-id]
  ```

- Add the command to the full operator command surface:
  POSIX wrapper, `WORKFLOW_COMMAND_MODULES`,
  `src/thesis_review_workflow/cli/BUILD`, `scripts/BUILD`
  `pex_binary(tags=["workflow-tool"])`, workflow runtime deps, package smoke,
  and generated `.cmd`/`.ps1` launcher coverage.
- Keep the command structural. It must not parse profile prose semantically.

Verification:

```bash
scripts/smoke-report-calibration
scripts/smoke-package-workflow-tools
scripts/check-private
scripts/check-scripts
pants test tests/test_report_calibration.py tests/test_work_artifacts.py tests/test_check_private.py tests/test_check_scripts_contracts.py
git diff --check
```

### Slice 2 - Common Briefing And Explicit Calibration Sources

Make profile application visible in packets and keep late operator calibration
notes from being silently missed.

Expected paths:

- `src/thesis_review_workflow/report_calibration.py`
- `src/thesis_review_workflow/review_packets.py`
- `src/thesis_review_workflow/opponent_packets.py`
- `src/thesis_review_workflow/supervisor_packets.py` if shared helpers are used
- `src/thesis_review_workflow/cli/refresh_round_hashes.py`
- `scripts/smoke-opponent-packets`
- `scripts/smoke-refresh-round-hashes`
- focused tests/smokes for common briefing shape

Work:

- Add `work/report_calibration_basis.json` to common briefing records and
  snapshot refs.
- Add an explicit structural input set for calibration sources:
  `notes/opponent-report-operator-feedback.md`,
  `notes/opponent-report-review-intake.md`, `work/review_deltas/*.json`,
  `work/operation_log.jsonl`, and
  `work/opponent_report_revision_request.json`. Treat them as available source
  refs, not as deterministic semantic input.
- Do not add broad note filename globs such as `notes/*operator*feedback*.md`.
  Additional note types must be registered explicitly or through a typed
  operation/delta artifact.
- Packet text should say that agents start from
  `work/report_calibration_basis.json` when present, and must either use it,
  refresh it, or record why it is unavailable.
- Ensure refreshing packets/common briefing after late operator notes changes
  updates hashes rather than leaving stale pre-note packets as the natural
  basis for report work.

Verification:

```bash
scripts/smoke-opponent-packets
scripts/smoke-refresh-round-hashes
pants test tests/test_opponent_packets.py tests/test_work_artifacts.py
git diff --check
```

### Slice 3 - Opponent Trace Binding

Bind report trace to the applied calibration basis before report drafting.

Expected paths:

- `src/thesis_review_workflow/report_calibration.py`
- `src/thesis_review_workflow/structured_evidence.py`
- `src/thesis_review_workflow/opponent_calibration.py`
- `.agents/skills/thesis-opponent-materials-review/SKILL.md`
- `.agents/skills/thesis-opponent-materials/SKILL.md`
- `src/thesis_review_workflow/opponent_packets.py`
- `tests/test_structured_evidence.py`
- `tests/test_opponent_calibration.py`
- `scripts/smoke-opponent-report`

Work:

- Extend `work/opponent_report_trace.json` with a calibration-basis binding:

  ```json
  {
    "report_calibration_basis_path": "work/report_calibration_basis.json",
    "report_calibration_basis_sha256": "<hash>",
    "calibration_preference_ids": ["opponent.assignment_difficulty.stack_not_enough"]
  }
  ```

- Update opponent-materials review instructions so the reviewer writes or
  refreshes `work/report_calibration_basis.json` before writing trace when the
  report depends on profile/operator calibration.
- Require trace authors to map calibration preferences to affected IS items,
  defense questions, and overall grade/points where relevant.
- Keep missing basis compatible only while closing reviewed opponent materials
  with no report draft/export yet, or when a typed limitation states that no
  profile-specific or operator-calibration preference was applicable. Once
  `draft-opponent-report`, canonical report validation, clean export, or
  opponent-report-review runs, a current basis is required whenever an effective
  reviewer profile or operator calibration source exists.
- Preserve existing `calibration_context` semantics for historical/reference
  calibration. If both it and `report_calibration_basis` are present, validators
  must verify both hash bindings and reject conflicting expected controls.
  Neither artifact may silently override the other.

Verification:

```bash
scripts/smoke-opponent-report
pants test tests/test_structured_evidence.py tests/test_opponent_calibration.py tests/test_opponent_report.py
git diff --check
```

### Slice 4 - Report Draft And Clean-Report Checks

Use the calibration basis to catch drift before the operator has to complain.

Expected paths:

- `src/thesis_review_workflow/report_calibration.py`
- `src/thesis_review_workflow/cli/draft_opponent_report.py`
- `src/thesis_review_workflow/cli/check_opponent_report.py`
- `src/thesis_review_workflow/cli/export_opponent_report.py`
- `src/thesis_review_workflow/submitted_reports.py`
- `scripts/smoke-opponent-report`
- `scripts/smoke-export-opponent-report`
- `tests/test_draft_opponent_report.py`
- `tests/test_opponent_report.py`
- `tests/test_export_opponent_report.py`

Work:

- `draft-opponent-report` should require a current trace-bound calibration
  basis when applicable, then copy calibration metadata into canonical draft
  source comments or the private pre-submission checklist, without leaking it
  into clean report prose.
- `check-opponent-report` should call or share logic with
  `check-report-calibration` and validate structured expectations:
  - selected IS values equal `expected_report_controls.is_select_values`;
  - overall grade equals expected grade if present;
  - point value falls within the expected interval if present;
  - defense-question count is within bounds;
  - calibration source hashes are current.
- `export-opponent-report` should continue to strip source metadata and private
  checklist detail. Clean report checks must reject leaked calibration paths,
  hashes, profile paths, or internal workflow mechanics.
- Submitted-report capture and delta checks must treat later changes to IS
  selections, category points, overall points/grade, defense questions, or
  private-comment presence as report-calibration drift that reopens report
  review.
- Keep checks structural. Do not add substring rules such as "if report says
  backend/web/mobile then reject".
- Make failures actionable: report the expected structured control, the actual
  report field, and the calibration-basis path/hash that supplied it.

Verification:

```bash
scripts/smoke-opponent-report
scripts/smoke-export-opponent-report
pants test tests/test_draft_opponent_report.py tests/test_opponent_report.py tests/test_export_opponent_report.py tests/test_submitted_reports.py
git diff --check
```

### Slice 5 - Independent Report Review Uses Calibration Basis

Make final review check profile application, not just prose quality after the
fact.

Expected paths:

- `.agents/skills/thesis-opponent-report-review/SKILL.md`
- `src/thesis_review_workflow/report_calibration.py`
- `src/thesis_review_workflow/opponent_packets.py`
- `src/thesis_review_workflow/review_profiles.py`
- `src/thesis_review_workflow/review_wave_gate.py`
- `src/thesis_review_workflow/review_approvals.py`
- `src/thesis_review_workflow/cli/write_review_approval.py`
- `src/thesis_review_workflow/cli/init_review_manifest.py`
- `src/thesis_review_workflow/cli/check_review_manifest.py`
- `tests/test_review_approvals.py`
- `tests/test_review_manifest_helpers.py`
- `tests/test_review_wave_gate.py`

Work:

- Add `work/report_calibration_basis.json` as a primary input for opponent
  report review packets.
- Report review must explicitly answer:
  - Which applied preferences affected the public report?
  - Are IS selections, grade/points, report length, and defense questions
    consistent with the basis?
  - Are any profile preferences intentionally not applied, and is that
    justified by current-case evidence or operator instruction?
- Include `check-report-calibration` in observed checks for valid
  opponent-report-review approval records.
- Add first-class manifest/helper-target handling for `check-report-calibration`
  so approval records and review manifests hash-bind
  `work/report_calibration_basis.json` and any report draft/clean proposal that
  consumed it.
- Update `opponent_review`, `opponent_materials`, and
  `opponent_report_review` closeout/readiness gates only where the basis is
  required. The reviewed-materials path may still close with a typed limitation
  before a report draft exists, but report draft/export/review paths must not
  pass with a stale or missing applicable basis.
- Ensure `write-review-approval --profile opponent-report-review` requires the
  new observed check when the reviewed basis is a calibration-bound report.
- Ensure review feedback distinguishes text-prose issues from calibration-basis
  drift.

Verification:

```bash
scripts/smoke-opponent-report
scripts/smoke-review-manifest
pants test tests/test_review_approvals.py tests/test_review_manifest_helpers.py tests/test_review_wave_gate.py tests/test_agent_profile_contracts.py
git diff --check
```

### Slice 6 - Supervisor Report Boundary

Keep V1 opponent-report-only and document the supervisor-report boundary
explicitly.

Expected paths:

- `.agents/skills/thesis-supervisor-report/SKILL.md`
- `.agents/skills/thesis-supervisor-report-review/SKILL.md`
- `src/thesis_review_workflow/cli/check_supervisor_report.py`
- `src/thesis_review_workflow/supervisor_report_calibration.py`
- `docs/agent-profile-matrix.md`
- `profiles/README.md`
- `TODO.md`

Work:

- Audit the existing supervisor-report calibration surface and record why this
  plan does not change it in V1.
- Document that `work/report_calibration_basis.json` currently supports
  `calibration_scope: opponent_report` only. Supervisor reports continue to use
  their existing trace, confirmation, and supervisor-report calibration
  contracts.
- Add or keep a clear TODO for a later convergence decision after both
  workflows have been exercised. The TODO must not imply supervisor support has
  landed in this plan.

Verification:

```bash
scripts/smoke-supervisor-report
pants test tests/test_supervisor_report.py tests/test_supervisor_report_calibration.py tests/test_agent_profile_contracts.py
git diff --check
```

### Slice 7 - Operator Documentation And Closeout

Make the new behavior discoverable and keep the plan from becoming another
hidden convention.

Expected paths:

- `README.md`
- `profiles/README.md`
- `docs/opponent-review-workflow.md`
- `docs/workflow-command-surface.md`
- `docs/agent-profile-matrix.md`
- `TODO.md`
- this plan

Work:

- Document the difference between:
  - reviewer profile exists,
  - reviewer profile is available in common briefing,
  - reviewer profile was applied through `work/report_calibration_basis.json`,
  - report text passed calibration checks.
- Add concise operator guidance for what to do after late calibration feedback:
  update the report, refresh/write calibration basis, regenerate trace/draft if
  needed, re-export clean report, and rerun independent review.
- Add or keep a TODO entry pointing to this active plan until it is implemented
  and archived.
- Record the Serena preflight and scoped search result in the final plan
  progress/closeout notes for this tracked Markdown workflow change.
- Record final commands in `Final Audit` and archive the plan after completion.

Verification:

```bash
scripts/check-private
scripts/check-scripts
scripts/smoke-report-calibration
git diff --check
```

## Progress

- 2026-05-20: Plan created from a concrete opponent-report calibration failure.
  No implementation slices have started.
- 2026-05-20: Multi-agent plan review completed and findings patched into the
  plan. Main repairs: V1 narrowed to opponent-report-only, workflow profile
  fields split from wave workflow names, existing `opponent_calibration_*` and
  `calibration_context` relationship documented, broad operator-note globs
  removed, command-surface/privacy/provenance paths added, and placeholder
  verification commands replaced with concrete smoke/test targets.
- 2026-05-20: Serena preflight completed for this tracked Markdown workflow
  edit: `initial_instructions` activated project `diplomky_v2`, and a scoped
  `search_for_pattern` over this plan confirmed the calibration-basis,
  `workflow_profile`, `opponent_report_review`, TODO, and supervisor-boundary
  references that were then patched.
- 2026-05-20: Implementation intake for end-to-end execution started. Read
  `AGENTS.md`, `plans/README.md`, `docs/agent-scheduling.md`,
  `docs/agent-profile-matrix.md`, `docs/dev-hygiene.md`, the relevant opponent
  repo-local skills, and this plan. Worktree before Slice 1 already contained
  user-authored changes in `AGENTS.md`, `TODO.md`, and `docs/dev-hygiene.md`,
  plus this untracked plan.
- 2026-05-20: Serena preflight for this execution completed:
  `initial_instructions` activated project `diplomky_v2`; scoped symbol
  overviews were used for `work_artifacts.py`, `structured_evidence.py`,
  `opponent_calibration.py`, and `check_opponent_report.py` before Slice 1 code
  edits.
- 2026-05-20: Omen MCP preflight succeeded at repo root:
  `repomap(/home/zdenekm/code/diplomky_v2)` reported 119 files and 1592
  symbols. During Slice 1, Omen MCP could inspect existing
  `src/thesis_review_workflow/work_artifacts.py` through semantic search, but
  `repomap` for the newly added `report_calibration.py` and package directory
  returned zero files/symbols; treat that as an MCP index/path limitation for
  the new file, not as code-quality evidence. Reproducible `pants run :omen`
  remains required for Slice 1 closeout.
- 2026-05-20: Slice 1 implemented. Added
  `src/thesis_review_workflow/report_calibration.py`,
  `scripts/check-report-calibration`,
  `src/thesis_review_workflow/cli/check_report_calibration.py`, command
  registry/Pants/PEX surface, privacy registration, work-artifact collection,
  `scripts/smoke-report-calibration`, and focused tests. Initial checks passed:
  `scripts/smoke-report-calibration`, `scripts/smoke-package-workflow-tools`,
  `scripts/check-private`, `scripts/check-scripts`, `scripts/smoke-private`,
  and `pants test tests/test_report_calibration.py tests/test_work_artifacts.py
  tests/test_check_private.py tests/test_check_scripts_contracts.py`.
- 2026-05-20: Slice 1 review and closeout completed. Subagents reviewed the
  technical validator/CLI/test contract, workflow/provenance integration, and
  privacy/packaging command surface. Findings were patched before commit:
  preference `source_keys` are now hash-bound to declared source records,
  `check-report-calibration` validates the effective reviewer-profile files
  from `case.md`, expected report controls reject unknown or empty shapes, and
  point intervals must be compatible with the declared grade band. Post-fix
  checks passed: `scripts/smoke-report-calibration`,
  `scripts/smoke-package-workflow-tools`, `dist/workflow-tools/bin/check-report-calibration --help`,
  `scripts/check-private`, `scripts/check-scripts`, `scripts/smoke-private`,
  `pants check src/thesis_review_workflow/report_calibration.py src/thesis_review_workflow/cli/check_report_calibration.py tests/test_report_calibration.py`,
  `pants test tests/test_report_calibration.py tests/test_work_artifacts.py tests/test_check_private.py tests/test_check_scripts_contracts.py`,
  `git diff --check`, and `pants run :omen`. Omen MCP scoped follow-up
  recovered after indexing through semantic search over
  `report_calibration.py` and `check_report_calibration.py`; repo-level Omen
  reported grade A, overall score 90.88, 180 files analyzed, and no smells.
- 2026-05-20: Slice 2 implemented. Added
  `work/report_calibration_basis.json` to common briefing snapshot/advisory
  records and reusable handoff refs, added explicit structural
  `report_calibration_sources` for
  `notes/opponent-report-operator-feedback.md`,
  `notes/opponent-report-review-intake.md`, `work/operation_log.jsonl`,
  `work/opponent_report_revision_request.json`, and
  `work/review_deltas/*.json`, and updated opponent packets so agents start
  from the basis when present and must refresh it or record a typed limitation
  when unavailable. `refresh-round-hashes` now refreshes registered
  calibration-source hashes without blessing semantic report/output edits.
- 2026-05-20: Slice 2 review and closeout completed. Serena symbol navigation
  was used for `review_packets.py`, `opponent_packets.py`, and
  `refresh_round_hashes.py` before edits. Omen MCP file-scoped `repomap` and
  semantic search returned zero results for touched files, so that was recorded
  as a path/index limitation; repo-root `repomap` and HyDE semantic search then
  found the touched `rel_status`, `validate_common_briefing_payload`,
  `_validate_report_calibration_source_records`, and
  `check_report_calibration.main` symbols. Subagent findings were patched:
  `report_calibration_sources` validation now rejects unregistered paths,
  requires the current dynamic `work/review_deltas/*.json` set, and packet
  status validates the basis against the effective Reviewer profile from
  `case.md`. Post-fix checks passed: `scripts/smoke-opponent-packets`,
  `scripts/smoke-refresh-round-hashes`, `scripts/smoke-report-calibration`,
  `scripts/check-private`, `scripts/check-scripts`,
  `pants check src/thesis_review_workflow/report_calibration.py src/thesis_review_workflow/review_packets.py src/thesis_review_workflow/opponent_packets.py src/thesis_review_workflow/cli/refresh_round_hashes.py src/thesis_review_workflow/cli/check_report_calibration.py tests/test_opponent_packets.py tests/test_refresh_round_hashes.py`,
  `pants test tests/test_opponent_packets.py tests/test_work_artifacts.py tests/test_refresh_round_hashes.py tests/test_report_calibration.py`,
  `git diff --check`, and `pants run :omen`. Repo-level Omen reported grade A,
  overall score 90.88, 180 files analyzed, and no smells.

## Decision Log

- Use a new structured calibration-basis artifact instead of adding more prose
  to `profiles/local/default.md`. The failure was not missing preference text
  alone; it was that the workflow did not force preferences to be selected,
  applied, and verified.
- Keep deterministic code structural. It may compare exact expected values and
  hashes from a semantic artifact, but it must not infer report quality or
  profile meaning from free-form text.
- Bind calibration before report drafting. Catching drift only in the final
  report review is too late and makes the operator repeat the same corrections.
- Keep historical opponent-report calibration separate. Historical reports can
  enrich the reviewer profile later, but the immediate defect is current-profile
  application in ordinary report generation.
- Use `work/report_calibration_basis.json` as an upstream current-profile
  application basis, not as a replacement for historical/reference calibration
  artifacts. Existing `opponent_calibration_*` artifacts remain source-binding
  controls and must be explicitly related when they influence the same report.
- Keep V1 opponent-report-only. Supervisor report calibration remains on its
  existing trace/confirmation/calibration contracts until a separate convergence
  decision is reviewed.

## Final Audit

Whole-plan final audit not run yet. Slice-level closeouts are recorded in
`Progress`; this plan remains active until all slices are implemented, reviewed,
verified, committed, and archived.
