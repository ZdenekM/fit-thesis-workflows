# Reviewer Profiles

Reviewer profiles capture stable preferences for a supervisor or opponent:
feedback style, typical priorities, strictness calibration, domain preferences,
and topics that should not be reopened by default.

Profiles are a preference layer only. They cannot override repository hard
rules such as privacy, evidence requirements, assignment/deadline gates,
student feedback language checks, or the rule that unchecked work must be
described as unchecked.

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

## Checking A Case

Validate the selected profile with:

```bash
scripts/check-reviewer-profile <case-id>
```

Supervisor and opponent readiness checks run this profile check automatically.
