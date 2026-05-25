# Historical Opponent Calibration

This workflow lets an opponent use their own historical reports as private
calibration evidence. It is optional: missing historical reports should produce
a clear non-blocking advisory, not a failed readiness check.

Historical calibration is not model fine-tuning and does not replace the normal
`Reviewer profile` configured in `case.md`. The existing reviewer profile stays
the readiness gate for opponent workflows. Historical calibration is additional
case-local context that an explicitly authorized agent may use after the current
case already has reviewed opponent materials and an accepted report trace.

Command routing: `scripts/<tool>` examples in this document are Linux/dev
shorthand and logical workflow command names. On Windows, package the workflow
tools first and use `dist\workflow-tools\bin\<tool>.cmd` or the matching
PowerShell launcher; do not run or click extensionless `scripts/<tool>` files.

## Private Workspace

Historical reports, theses, source archives, extracted text, notes, generated
case analyses, reviewer profiles, checklists, and calibration history live under
ignored `cases/`, for example:

```text
cases/opponent-calibration-private/
  case.md
  current-round.txt
  rounds/
    2026-05-07-historical-pilot/
      inputs/
        historical_cases/
      work/
        calibration/
          historical_case_analyses/
          reviewer_calibration_profile.json
          reviewer_calibration_profile_history.jsonl
          reviewer_checklist.json
          reviewer_profile_change_log.md
          profile_review.md
      outputs/
        reviewer_calibration_profile.md
```

Tracked docs and tests may use only synthetic fixtures. Do not copy real
historical reports or generated private calibration outputs into tracked paths.

## Artifact Shape

The authoritative reviewer profile is Markdown:

- `outputs/reviewer_calibration_profile.md`

The companion JSON is only a manifest:

- `work/calibration/reviewer_calibration_profile.json`

The manifest binds the Markdown profile by path and hash, records versioning,
source case analyses, applicability, confidence by dimension, limitations,
ownership boundaries, and the boundaries where the profile must not be used.
Deterministic helpers may validate these fields and hashes, but must not
semantically parse the Markdown profile text.

Every profile refresh must triage candidate lessons by ownership before writing
the active profile or checklist:

- `baseline_workflow_owned`: already-owned workflow hygiene, privacy,
  public/private wording, checker/export, readiness, and manifest rules.
- `methodology_pipeline_owned`: methodology, evidence-mode, problem framing,
  contribution-boundary, evaluation, user-study, figure/media, or quantitative
  checks that belong to the opponent methodology pipeline. For contribution
  boundaries, this means factual evidence, assignment interpretation, and target
  binding.
- `calibration_profile_owned`: reviewer-specific calibration of severity,
  grading strictness, contribution-credit weight after the factual boundary is
  established, emphasis, defense-question style, and wording preferences that
  are not normal workflow baseline.
- `do_not_duplicate`: concrete rules that must stay out of active calibration
  prompts because another workflow surface owns them.

Only `calibration_profile_owned` lessons may become active checklist prompts.
The profile manifest must include all four ownership boundary keys. The active
`calibration_profile_owned` and `do_not_duplicate` lists must be non-empty;
baseline and methodology lists may be empty when the refresh did not observe a
new lesson for those owners. Every `work/calibration/reviewer_checklist.json`
item must declare `ownership_scope: "calibration_profile"` with a unique
`item_id`. Baseline and methodology lessons should be promoted to their owning
docs/skills/plans or tracked as follow-up work, not parked in the private
calibration checklist.

The synthesized profile can be checked with:

```bash
scripts/check-opponent-calibration-profile <calibration-case-id> [round-id]
```

The profile check requires at least two historical case analyses, the Markdown
profile, profile manifest, checklist, append-only profile history, private
`work/calibration/reviewer_profile_change_log.md` and
`work/calibration/profile_review.md`, and a current reviewed
`work/review_manifest.json` entry for `outputs/reviewer_calibration_profile.md`.
It is still only a structural gate; synthesis and anti-overfit judgment belong
to explicitly authorized agents or human reviewers.

The independent profile review must include an ownership-boundary check: active
calibration should not duplicate public-report hygiene, path/privacy leak
checks, final export/readiness checks, or methodology-pipeline work that is
already owned elsewhere. This is a semantic review requirement; deterministic
helpers validate the review path, hash, metadata, and structured profile
manifest, but they do not parse Markdown review prose for meaning.

Historical case analyses are path-classified artifacts:

- `work/calibration/historical_case_analyses/<historical-case-id>.json`

Each analysis must use the schema
`historical-opponent-case-analysis-v1`, carry corpus coverage metadata, and
anchor evidence to private round-relative refs. Reusable `recurring_checks`
entries are structural objects with unique `check_id`, `evidence_class`, and
`prompt`; deterministic validation checks shape and uniqueness only, not the
semantic meaning of the prompt.

Validate the current calibration round with:

```bash
scripts/check-opponent-calibration-case <calibration-case-id> [round-id]
```

The command is deterministic. It only checks that authorized agent- or
human-authored historical case analysis JSON files are structurally valid,
case/round-bound, path-safe, and anchored to existing private inputs. It does
not create semantic analysis and does not read historical report prose to infer
reviewer style.

Profile refresh history is append-only JSONL:

- `work/calibration/reviewer_calibration_profile_history.jsonl`

Each line records the new profile version, previous/current hashes, source case
refs, review state, a versioned profile snapshot path, the previous history
entry hash, and change summary. Every refresh version after version 1 must also
record explicit structured operator approval bound to that history entry,
including the approved profile version, profile Markdown hash, and profile
manifest hash. The structural checker rejects refreshes that break the history
chain, skip versions, reuse a stale previous-profile hash, or drop earlier
source refs silently.

## Current-Case Use

For a normal opponent case, historical calibration can be used only after:

- `outputs/oponent_podklady_revidovane.md` exists and is current;
- `work/opponent_report_trace.json` exists and is accepted;
- current-request agent authorization is explicit.

If a profile is selected, the workflow writes:

- `work/opponent_calibration_use.json`

This use artifact binds the current reviewed opponent materials, accepted report
trace, selected private profile manifest, and checklist by path and SHA-256. It
also records applicability dimensions, confidence by dimension, explicit
operator approval for using the profile in the current case, and a structural
marker that the normal `Reviewer profile` gate remains required and cannot be
satisfied by historical calibration.

`scripts/draft-opponent-report` validates any recorded
`work/opponent_calibration_use.json` or `work/opponent_calibration_advisory.json`
before writing a draft. If both exist, or if the recorded artifact is stale or
invalid, drafting stops until the current-case calibration context is refreshed
or removed.

If no profile exists or the operator chooses not to use it, the workflow writes:

- `work/opponent_calibration_advisory.json`

The advisory is a quality recommendation only. The workflow should continue
without calibrated style or strictness guidance.

Stable current-case Markdown outputs such as
`outputs/reference_report_comparison.md` and
`outputs/opponent_reading_packet.md` are reviewed internal evidence. They must
have review-manifest entries, source hashes, independent review records, and
current reviewed hashes before they are used to revise the report trace or draft.

After the operator reads the broad materials and report draft, their free-form
notes live in `notes/opponent-report-operator-feedback.md`. An explicitly
authorized agent, or a human reviewer, then writes
`work/opponent_report_revision_request.json` with schema
`opponent-report-revision-request-v1`. The revision request binds the feedback,
reviewed materials, pre-revision trace snapshot, pre-revision draft snapshot,
calibration-use or advisory artifact, reference comparison, and reading packet
by path and SHA-256. Store the pre-revision snapshots under
`work/opponent_report_revision_sources/` before the active trace or draft is
overwritten. It normalizes operator requests into typed categories:

- `evidence_request`
- `grading_calibration`
- `tone_style`
- `missing_check`
- `factual_correction`
- `wording_preference`
- `defense_question`
- `scope_limitation`

The revision request is a structured handoff for later trace editing.
Deterministic helpers validate only schema, categories, paths, hashes, and
source refs; semantic interpretation of the operator notes remains an
authorized agent or human-review step.

When the revision request is applied, the authorized agent or human reviewer
updates `work/opponent_report_trace.json` and records a `calibration_context`
object. This object binds, by path and SHA-256, the selected calibration-use or
advisory artifact, `outputs/reference_report_comparison.md`,
`outputs/opponent_reading_packet.md`, and, when operator feedback was applied,
`work/opponent_report_revision_request.json`. It also records anti-overfit
review status, reviewer identity or human note, review timestamp, and
limitations.

After regenerating the draft, refresh `work/review_manifest.json`, run the
required manifest and agent-coverage checks, and run an independent
opponent-report review before treating the revised draft as sendable.

`calibration_context` is intentionally a source-binding record. It validates the
exact input artifacts used for the trace revision. It must not recursively
reinterpret those inputs against the newly revised trace, because the revision
request and earlier calibration-use/advisory artifacts may intentionally bind
the pre-revision trace or draft the operator actually read.

After the opponent report has been human-finalized and independently reviewed,
the operator may mark the case as eligible for a future calibration refresh with
`work/opponent_calibration_refresh_eligibility.json`. This private marker binds
the reviewed opponent materials, accepted trace, finalized draft,
opponent-report review, finalization manifest snapshot, and operator approval by
path and SHA-256. The manifest snapshot lives at
`work/opponent_calibration_refresh_sources/review_manifest.json` to avoid a
self-referential hash cycle with the active manifest. Capture that snapshot
after final report checks/review pass but before the eligibility marker itself
is collected into the active manifest. It must record
`profile_update_status: not_started`, `does_not_update_profile: true`, and a
copy policy of `private_case_local_refs_only`. The marker does not copy data and
does not update the reviewer profile; a later profile refresh still requires a
separate authorized historical-case analysis, independent review, history entry,
and default-profile approval.

## Agent Authorization

Semantic interpretation of historical reports, current materials, or operator
feedback belongs to explicitly authorized agents or human reviewers. Without
authorization, commands and skills must stop before reading private materials or
writing semantic calibration artifacts.

Deterministic code may:

- validate schemas and path safety;
- validate hashes and stale references;
- collect work artifacts for provenance;
- display non-blocking advisory text;
- pass Markdown profile text to an authorized agent.

Deterministic code must not:

- infer reviewer style from raw report text;
- infer thesis quality from historical reports;
- turn keyword matches into grading, routing, readiness, or report wording;
- use a historical profile as primary evidence about a new student's work.
