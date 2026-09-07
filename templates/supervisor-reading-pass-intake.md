# Supervisor Reading Pass Intake

The supervisor's own reading pass over the current thesis artifact, usually
dictated and formalized by an agent rather than written by hand. It is optional:
a round without a reading pass is valid, and nothing here is a readiness gate.

Copy this template to
`cases/<case-id>/rounds/<round-id>/notes/supervisor-reading-pass.md` and fill the
copy. Do not fill this tracked template with case data.

Validate the filled copy with
`scripts/check-supervisor-reading-pass <case-id> [round-id]`.

Cteny artefakt:
Datum cteni:
Forma zapisu: diktovano / psano
Rozsah cteni:
Co jsem necetl:

## Poznamky

One `###` block per observation; its heading is a short free title. Every block
repeats all three labels below, and all three must be filled.

`Evidence:` names where the observation is anchored: a chapter, section, page,
file, path, figure, or table. When it is not anchored yet, write the single
token `neoverovano`; such a block must route to `verify_first` or `discard`.

`Routing:` is exactly one of:

- `student_feedback` - may become a student-facing action item directly.
- `internal_only` - the supervisor's own note; never reaches student output.
- `verify_first` - usable only after the claim is confirmed against the
  authoritative artifact, with the confirming anchor written into `Evidence:`
  in place of the unverified token.
- `discard` - considered and dropped; recorded so it is not raised again.

### Nazev pozorovani

Pozorovani:
Evidence:
Routing:
