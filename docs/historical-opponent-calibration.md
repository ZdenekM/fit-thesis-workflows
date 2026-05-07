# Historical Opponent Calibration

This workflow lets an opponent use their own historical reports as private
calibration evidence. It is optional: missing historical reports should produce
a clear non-blocking advisory, not a failed readiness check.

Historical calibration is not model fine-tuning and does not replace the normal
`Reviewer profile` configured in `case.md`. The existing reviewer profile stays
the readiness gate for opponent workflows. Historical calibration is additional
case-local context that an explicitly authorized agent may use after the current
case already has reviewed opponent materials and an accepted report trace.

## Private Workspace

Historical reports, theses, source archives, extracted text, notes, generated
case analyses, reviewer profiles, checklists, and calibration history live under
ignored `cases/`, for example:

```text
cases/opponent-calibration-zm/
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
source case analyses, applicability, confidence by dimension, limitations, and
the boundaries where the profile must not be used. Deterministic helpers may
validate these fields and hashes, but must not semantically parse the Markdown
profile text.

Historical case analyses are path-classified artifacts:

- `work/calibration/historical_case_analyses/<historical-case-id>.json`

Each analysis must use the schema
`historical-opponent-case-analysis-v1`, carry corpus coverage metadata, and
anchor evidence to private round-relative refs.

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
refs, review state, and change summary.

## Current-Case Use

For a normal opponent case, historical calibration can be used only after:

- `outputs/oponent_podklady_revidovane.md` exists and is current;
- `work/opponent_report_trace.json` exists and is accepted;
- current-request agent authorization is explicit.

If a profile is selected, the workflow writes:

- `work/opponent_calibration_use.json`

If no profile exists or the operator chooses not to use it, the workflow writes:

- `work/opponent_calibration_advisory.json`

The advisory is a quality recommendation only. The workflow should continue
without calibrated style or strictness guidance.

Stable current-case Markdown outputs such as
`outputs/reference_report_comparison.md` and
`outputs/opponent_reading_packet.md` are reviewed internal evidence. They must
have review-manifest entries, source hashes, independent review records, and
current reviewed hashes before they are used to revise the report trace or draft.

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
