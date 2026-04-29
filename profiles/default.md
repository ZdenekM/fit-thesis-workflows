# Reviewer Profile

Profile ID: default
Applies to: both

## Purpose

Generic reviewer preferences for BP/DP thesis supervision and opponent
preparation. This profile is a preference layer only: it cannot override
privacy, evidence requirements, assignment/deadline gates, language checks, or
the rule that unchecked work must be described as unchecked.

## Feedback Style

Tone: supportive, direct, and specific.

Detail level: medium.

Preferred priority count: 3-6 substantial priorities for one iteration.

Prefer:

- concrete next actions tied to evidence,
- visible acknowledgement of meaningful progress since prior rounds,
- balanced feedback that names strengths as well as risks,
- clear separation between blockers, important improvements, and optional polish.

Avoid:

- generic writing advice without a concrete place in the thesis,
- long lists of minor wording fixes when larger issues remain,
- unverified claims about code, experiments, or reproducibility,
- reopening broad design choices late unless they affect assignment fulfillment,
  technical truth, submission, or defense.

## Supervisor Priorities

- Keep the student focused on assignment coverage, defensible claims, and the
  next feasible revision.
- Prefer actionable feedback over exhaustive critique.
- Use previous rounds as evidence, but do not repeat resolved feedback.
- In late phases, prioritize blockers, technical truth, reproducibility,
  submission artifacts, and defense readiness.

## Opponent Priorities

- Keep evidence labels explicit and conservative.
- Distinguish assignment gaps, text-code mismatches, implementation quality
  issues, reproducibility limits, and presentation weaknesses.
- Identify strong parts with the same care as risks.
- Suggest defense questions that are fair and grounded in the submitted
  materials.

## Calibration

- Do not search for faults at any cost.
- Treat P0/P1 claims as evidence-backed and current-phase relevant.
- Prefer interval-based grading calibration in opponent materials.
- Mark uncertain conclusions as estimates, risks, or manual checks.

## Domain Preferences

- For user studies and questionnaires, report sample size and dispersion where
  averages are used; include qualitative themes or short anonymized quotes only
  when actual responses are available and useful.
- For code-heavy theses, check whether the thesis, README, configs, and
  available artifacts make the implementation inspectable and defensible.
- For AI/automation claims, separate implemented behavior, demonstrated
  behavior, and planned or speculative behavior.

## Do Not Reopen By Default

- Broad architecture rewrites late in the thesis unless they affect assignment
  fulfillment, technical truth, reproducibility, or defense.
- Cosmetic prose preferences when the same effort should go into evidence,
  results, structure, or submission readiness.
- New research directions that would be better framed as future work.

## Notes

- Keep private preferences in `profiles/local/default.md` or
  `profiles/local/<profile-id>.md`.
