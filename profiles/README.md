# Reviewer Profiles

Reviewer profiles capture stable preferences for a supervisor or opponent:
feedback style, typical priorities, strictness calibration, domain preferences,
and topics that should not be reopened by default.

Profiles are a preference layer only. They cannot override repository hard
rules such as privacy, evidence requirements, assignment/deadline gates,
student feedback language checks, or the rule that unchecked work must be
described as unchecked.

## Report Calibration Boundary

`work/report_calibration_basis.json` is currently the structured application
contract for opponent reports only. Its payload must declare
`calibration_scope: opponent_report`; it is not a supervisor-report input and
does not mean supervisor-report support has landed.

Supervisor reports keep their separate trace, confirmation, review, and
optional supervisor-report calibration contracts. Revisit convergence only
after both workflows have been exercised enough to justify one shared contract.

For opponent reports, distinguish four states:

- the reviewer profile file exists and passes `scripts/check-reviewer-profile`;
- the profile is listed in `work/common_briefing.json`, which makes it context
  for agents but does not prove application;
- `work/report_calibration_basis.json` records which profile or operator
  preferences were applied, with hashes, `calibration_scope:
  opponent_report`, and structured expected report controls;
- report text passed the calibration-aware checks, including
  `scripts/check-report-calibration`, canonical/clean opponent-report checks,
  and the independent review gate when the report basis is calibration-bound.

## Public And Private Profiles

The public repository tracks only:

- `profiles/default.md`
- `profiles/README.md`

Personal profiles and local overrides are private by default and must stay out
of git:

```text
profiles/local/default.md
profiles/local/<profile-id>.md
```

`profiles/local/default.md` refines the generic default profile for your local
machine. Use `Reviewer profile: local/<profile-id>` in an ignored case
`case.md` to select a specific private profile.

Do not force-add `profiles/local/*` or other personal profile files. Other
`profiles/*` files are ignored as a privacy guard, but they are not selectable
through `Reviewer profile`; use `profiles/local/<profile-id>.md` for selectable
private profiles.

## Local Profile Audit Boundary

Auditing or updating a local profile is private, opt-in work. Keep local profile
notes, diffs, and proposals under the ignored case or round workspace. A
review-delta record may point to a redacted proposal with `profile_proposal_ref`
and `private-reviewer-profile:local/<profile-id>`, but that pointer is not a
profile update command and does not copy private profile text into tracked
files. Local profile checks are never a tracked-plan, case closeout, or CI
prerequisite.

## Checking A Case

Validate the selected profile with:

```bash
scripts/check-reviewer-profile <case-id>
```

Supervisor and opponent readiness checks run this profile check automatically.
