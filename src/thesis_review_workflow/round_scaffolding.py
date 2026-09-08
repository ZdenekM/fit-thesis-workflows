"""Which notes templates a round gets, decided by its kind.

Scaffolding every template into every round is why `## Audit Base` of the supervision
season readiness plan measured thirteen rounds carrying a byte-identical unfilled
supervisor intake, eight of them opponent rounds. A round should carry the operator input
files it actually needs and nothing else, so the operator can tell which notes are theirs.

The kind is not a new vocabulary: it is the workflow profile id that already names this
round's purpose everywhere else in the pipeline.
"""

from __future__ import annotations

from thesis_review_workflow.review_profiles import profiles_by_id

TemplateSpec = tuple[str, str]
"""A template basename under `templates/` and the notes basename it is stored as."""

COMMON_TEMPLATES: tuple[TemplateSpec, ...] = (
    ("round-notes.md", "round-notes.md"),
    ("assignment.md", "assignment.md"),
)

KIND_TEMPLATES: dict[str, tuple[TemplateSpec, ...]] = {
    "supervisor_feedback": (("supervisor-intake.md", "supervisor-intake.md"),),
    # The report track has its own operator input, consumed under a different basename by
    # `supervisor_report.check_supervisor_report_intake`, and does not use the feedback intake.
    "supervisor_report": (("supervisor-report-intake.md", "supervisor-report-operator-input.md"),),
    "opponent_review": (("opponent-intake.md", "opponent-intake.md"),),
    "opponent_materials": (("opponent-intake.md", "opponent-intake.md"),),
    "opponent_report_review": (
        ("opponent-intake.md", "opponent-intake.md"),
        ("opponent-report-review-intake.md", "opponent-report-review-intake.md"),
    ),
}

UNSPECIFIED_KIND_TEMPLATES: tuple[TemplateSpec, ...] = (
    *COMMON_TEMPLATES,
    ("supervisor-intake.md", "supervisor-intake.md"),
    ("opponent-intake.md", "opponent-intake.md"),
    ("opponent-report-review-intake.md", "opponent-report-review-intake.md"),
)
"""What a round with no declared kind still gets: exactly what every round got before.

Deliberately not the union over all kinds. Adding the report intake here would put an
unfilled operator input into every round, which is the problem this module exists to fix.
"""

ON_DEMAND_TEMPLATES = frozenset(
    {
        # Copied into a case, not a round.
        "case-notes.md",
        "reviewer-profile.md",
        # Assignment authoring: a topic-proposal case has no review rounds at all.
        "topic-intake.md",
        "assignment-formal.md",
        "student-brief.md",
        # Created only when the operator actually has that input.
        "supervisor-reading-pass-intake.md",
        "opponent-report-quality-feedback-intake.md",
        "external-opponent-report-intake.md",
    }
)
"""Templates that are never scaffolded into a round.

A reading pass is optional per round, unlike a report intake, which a report round needs.
The contract test asserts every tracked template is either mapped to a kind or listed here,
so a new template cannot quietly return to being copied everywhere.
"""

SUPERVISOR_FEEDBACK_INTAKE = "supervisor-intake.md"
SUPERVISOR_REPORT_INTAKE = "supervisor-report-operator-input.md"
OPPONENT_INTAKE = "opponent-intake.md"

BOOTSTRAP_MODE_KINDS = {"supervisor": "supervisor_feedback", "opponent": "opponent_materials"}
"""Default kind for each `bootstrap-case` mode; `--round-kind` overrides it."""


def round_kinds() -> tuple[str, ...]:
    return tuple(sorted(profiles_by_id()))


def validate_round_kind(kind: str | None) -> None:
    if kind is None:
        return
    if kind not in round_kinds():
        raise ValueError(f"unknown round kind: {kind}; expected one of {', '.join(round_kinds())}")


def templates_for_kind(kind: str | None) -> tuple[TemplateSpec, ...]:
    """Template specs to scaffold, in a stable order."""

    validate_round_kind(kind)
    if kind is None:
        return UNSPECIFIED_KIND_TEMPLATES
    return (*COMMON_TEMPLATES, *KIND_TEMPLATES.get(kind, ()))


def skipped_for_kind(kind: str | None) -> tuple[str, ...]:
    """Notes basenames the unspecified-kind set carries that this kind does not need."""

    if kind is None:
        return ()
    kept = {target for _, target in templates_for_kind(kind)}
    return tuple(target for _, target in UNSPECIFIED_KIND_TEMPLATES if target not in kept)


def intake_basename_for_kind(kind: str | None) -> str | None:
    """The operator intake file a bootstrap run should fill for this kind, if any.

    `bootstrap_case.fill_intake` reads the file unconditionally, so a kind whose scaffolding
    omits an intake must report None rather than a path that does not exist.
    """

    validate_round_kind(kind)
    if kind is None:
        return SUPERVISOR_FEEDBACK_INTAKE
    if kind == "supervisor_feedback":
        return SUPERVISOR_FEEDBACK_INTAKE
    if kind == "supervisor_report":
        return SUPERVISOR_REPORT_INTAKE
    return OPPONENT_INTAKE


def readiness_command_for_kind(kind: str | None) -> str:
    """The readiness gate that applies to this kind.

    Supervisor deadline calibration applies to the feedback track only; every other kind
    stops at round readiness, which is what `AGENTS.md` requires for opponent materials.
    """

    validate_round_kind(kind)
    if kind in {None, "supervisor_feedback"}:
        return "scripts/check-supervisor-ready"
    if kind == "supervisor_report":
        return "scripts/check-supervisor-report-ready"
    return "scripts/check-round-ready"
