from pathlib import Path

from thesis_review_workflow.review_profiles import profiles_by_id
from thesis_review_workflow.round_scaffolding import (
    BOOTSTRAP_MODE_KINDS,
    COMMON_TEMPLATES,
    KIND_TEMPLATES,
    ON_DEMAND_TEMPLATES,
    UNSPECIFIED_KIND_TEMPLATES,
    intake_basename_for_kind,
    readiness_command_for_kind,
    round_kinds,
    skipped_for_kind,
    templates_for_kind,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_round_kinds_are_the_workflow_profile_ids() -> None:
    """A round kind is not a new vocabulary; two names for one thing would drift."""

    assert set(round_kinds()) == set(profiles_by_id())


def test_every_kind_gets_the_common_templates() -> None:
    for kind in round_kinds():
        targets = [target for _, target in templates_for_kind(kind)]
        for _, common in COMMON_TEMPLATES:
            assert common in targets, kind


def test_the_report_kind_gets_its_operator_input_and_not_the_feedback_intake() -> None:
    """The measured defect: report rounds carried an unfilled feedback intake they never use."""

    targets = [target for _, target in templates_for_kind("supervisor_report")]

    assert "supervisor-report-operator-input.md" in targets
    assert "supervisor-intake.md" not in targets


def test_the_report_template_is_stored_under_its_consumed_name() -> None:
    from thesis_review_workflow.supervisor_report import SUPERVISOR_REPORT_INPUT_REL

    specs = dict(templates_for_kind("supervisor_report"))

    assert specs["supervisor-report-intake.md"] == Path(SUPERVISOR_REPORT_INPUT_REL).name


def test_an_unspecified_kind_keeps_exactly_the_previous_behaviour() -> None:
    """Not the union over kinds: that would add an unfilled report intake to every round."""

    targets = {target for _, target in UNSPECIFIED_KIND_TEMPLATES}

    assert targets == {
        "round-notes.md",
        "assignment.md",
        "supervisor-intake.md",
        "opponent-intake.md",
        "opponent-report-review-intake.md",
    }
    assert "supervisor-report-operator-input.md" not in targets


def test_declaring_a_kind_skips_something_for_every_kind() -> None:
    for kind in round_kinds():
        assert skipped_for_kind(kind), f"{kind} scaffolds everything, so the kind buys nothing"


def test_every_tracked_template_is_mapped_or_explicitly_on_demand() -> None:
    """The guard against a new template quietly returning to every round."""

    mapped = {template for _, template in UNSPECIFIED_KIND_TEMPLATES}
    for specs in KIND_TEMPLATES.values():
        mapped.update(template for template, _ in specs)
    tracked = {path.name for path in (REPO_ROOT / "templates").glob("*.md")}

    unaccounted = tracked - mapped - set(ON_DEMAND_TEMPLATES)

    assert not unaccounted, f"map these to a kind or list them as on-demand: {sorted(unaccounted)}"


def test_on_demand_templates_are_never_scaffolded() -> None:
    for kind in (None, *round_kinds()):
        scaffolded = {template for template, _ in templates_for_kind(kind)}
        assert not scaffolded & set(ON_DEMAND_TEMPLATES), kind


def test_the_reading_pass_stays_on_demand() -> None:
    """A reading pass is optional per round, unlike a report intake."""

    assert "supervisor-reading-pass-intake.md" in ON_DEMAND_TEMPLATES


def test_intake_basename_matches_what_the_kind_actually_scaffolds() -> None:
    """bootstrap reads the intake unconditionally, so a name it does not scaffold would raise."""

    for kind in round_kinds():
        basename = intake_basename_for_kind(kind)
        targets = {target for _, target in templates_for_kind(kind)}
        assert basename in targets, (kind, basename)


def test_readiness_command_follows_the_kind_not_the_mode() -> None:
    assert readiness_command_for_kind("supervisor_feedback").endswith("check-supervisor-ready")
    assert readiness_command_for_kind("supervisor_report").endswith("check-supervisor-report-ready")
    for kind in ("opponent_review", "opponent_materials", "opponent_report_review"):
        assert readiness_command_for_kind(kind).endswith("check-round-ready"), kind


def test_bootstrap_modes_map_to_real_kinds() -> None:
    assert set(BOOTSTRAP_MODE_KINDS) == {"supervisor", "opponent"}
    for kind in BOOTSTRAP_MODE_KINDS.values():
        assert kind in round_kinds()


def test_an_unknown_kind_is_rejected() -> None:
    for value in ("supervisor", "opponent", "report", ""):
        try:
            templates_for_kind(value)
        except ValueError as exc:
            assert "unknown round kind" in str(exc)
        else:  # pragma: no cover - the guard must fire
            raise AssertionError(f"{value!r} must not be accepted as a kind")
