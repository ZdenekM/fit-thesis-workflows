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

## Supervisor Report Style

These preferences apply to the formal supervisor report, not to iterative
student-facing feedback. They describe wording style only; the supervisor's
explicit input and current-case evidence remain authoritative.

Tone: formal, concise, fair, and clearly written in the supervisor's voice.

Detail level: compact. Prefer one short paragraph per FIT IS field, usually one
to three sentences, unless a serious limitation needs explicit explanation.

Prefer:

- first-person evaluative Czech wording where natural, equivalent to "I
  consider", "I evaluate", or "I recommend";
- assignment-context paragraphs that first characterize difficulty or context,
  then state result quality and assignment fulfillment;
- calibrated phrases such as rather demanding, average difficulty, fulfilled
  with reservations, formally fulfilled, or fulfilled in full, chosen according
  to current evidence;
- process paragraphs grounded in supervisor input: consultation regularity,
  preparedness, independence, communication, responsiveness to feedback, and
  finishing timing;
- concise literature paragraphs unless literature work is a major strength or
  risk;
- publication, award, open-source release, or external-impact statements only
  when there is actual evidence or the supervisor explicitly wants them
  evaluated; do not spell out routine absence as a finding in normal reports;
  if the target form requires non-empty text, use a neutral one-line comment;
- overall assessment paragraphs that balance strengths and reservations and
  make the grade/points feel proportionate to the text;
- a separate private student comment that may be more personal, motivating, and
  forward-looking than the official report text.

Avoid:

- long audit-style reports, bullet-heavy prose, or internal workflow language;
- over-explaining routine sections when the point can be said in one sentence;
- inferring student activity, independence, or communication from indirect
  artifacts when supervisor input is missing;
- copying student-facing feedback into the official report without adapting it
  to the official FIT IS fields;
- mixing the private student comment into official report fields;
- naming unverifiable publications, awards, open-source status, or external
  impact without current evidence.
- repeating that no publication or award is recorded when that is the ordinary
  state and has no bearing on the grade.

## Opponent Priorities

- Keep evidence labels explicit and conservative.
- Distinguish assignment gaps, text-code mismatches, implementation quality
  issues, reproducibility limits, and presentation weaknesses.
- Identify strong parts with the same care as risks.
- Suggest defense questions that are fair and grounded in the submitted
  materials.

## Opponent Report Style

These preferences apply to the final opponent report and its private student
comment. They are generic communication defaults only; current evidence, FIT IS
rubric fields, `work/report_calibration_basis.json`, and explicit operator
input remain authoritative.

Prefer:

- cautious wording for evidence that was not directly checked;
- visible assignment traceability in the assignment-fulfillment and overall
  assessment sections;
- rubric-specific comments that do not move the same criticism between
  unrelated FIT IS fields;
- balanced strengths and limitations, with strengths stated when they are
  supported by current evidence;
- explicit point/grade calibration, so the prose and proposed assessment feel
  proportionate to each other;
- platform or domain difficulty as a calibration factor, not as a replacement
  for evidence about the submitted work;
- compact IS prose that mentions decisive evidence and leaves audit detail in
  internal materials;
- focused defense questions tied to important evidence gaps, tensions, or
  clarifications.

Avoid:

- categorical claims about missing functionality when the actual limitation is
  that the provided materials did not evidence it;
- using the private student comment to introduce new unsupported criticisms;
- expanding the public report with trace, packet, manifest, or confidence-label
  detail.

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
