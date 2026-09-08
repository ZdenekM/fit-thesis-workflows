"""Contract tests for the assignment bundle approval and its check.

Every negative record here is written BY HAND. A test that only drives
`build_bundle_approval_payload` proves nothing about the checker, and the
checker is what stands between a record and publication.
"""

import json
from pathlib import Path

import pytest

from thesis_review_workflow.assignment_bundle import (
    BUNDLE_APPROVAL_SCHEMA,
    approval_rel,
    build_bundle_approval_payload,
    bundle_paths,
)
from thesis_review_workflow.cli.check_assignment_bundle import check_bundle
# Sibling import, not `tests.`: the test root is not a package in the Pants sandbox.
from test_assignment_draft import BRIEF_SOURCE, INTAKE, assignment, projection

CASE_ID = "topic-case"


@pytest.fixture
def approved_case(tmp_path: Path) -> Path:
    case_dir = tmp_path / CASE_ID
    (case_dir / "notes").mkdir(parents=True)
    (case_dir / "outputs").mkdir()
    (case_dir / "work" / "reviews").mkdir(parents=True)
    (case_dir / "case.md").write_text(
        "Case ID: t\nCase kind: topic-proposal\nStudent feedback language: en\n", encoding="utf-8"
    )
    (case_dir / "notes/topic_intake.md").write_text(INTAKE, encoding="utf-8")
    (case_dir / "notes/student_brief.md").write_text(BRIEF_SOURCE, encoding="utf-8")
    for variant in ("bp", "dp"):
        (case_dir / f"outputs/assignment_formal_{variant}.md").write_text(assignment(variant=variant), encoding="utf-8")
        (case_dir / f"outputs/student_brief_{variant}.md").write_text(projection(variant), encoding="utf-8")
    write_approval(case_dir, payload(case_dir))
    return case_dir


def payload(case_dir: Path, **overrides: object) -> dict:
    built = build_bundle_approval_payload(
        case_dir,
        case_id=CASE_ID,
        variant="bp",
        author_agent="authoring-parent",
        reviewer_agent="thesis-assignment-reviewer",
        reviewer_role="thesis-assignment-review",
        verdict="approved",
        blocking_findings_count=0,
        checks_observed=["scripts/check-assignment-draft"],
        limitations=["identifier resolution not verified against the publisher"],
        timestamp="2026-09-08T10:00:00Z",
    )
    built.update(overrides)
    return built


def write_approval(case_dir: Path, record: object, variant: str = "bp") -> None:
    (case_dir / approval_rel(variant)).write_text(json.dumps(record), encoding="utf-8")


def check(case_dir: Path, variant: str = "bp") -> list[str]:
    return check_bundle(case_dir, CASE_ID, variant)


def test_an_approved_bundle_passes(approved_case: Path) -> None:
    assert check(approved_case) == []


def test_the_approval_binds_every_bundle_file(approved_case: Path) -> None:
    record = json.loads((approved_case / approval_rel("bp")).read_text(encoding="utf-8"))
    assert [entry["path"] for entry in record["files"]] == list(bundle_paths("bp"))


def test_a_missing_approval_fails(approved_case: Path) -> None:
    (approved_case / approval_rel("bp")).unlink()
    assert any("an independent reviewer must approve" in finding for finding in check(approved_case))


def test_an_unapproved_variant_fails_even_though_another_is_approved(approved_case: Path) -> None:
    assert any("missing work/reviews/assignment_approval_dp.json" in finding for finding in check(approved_case, "dp"))


@pytest.mark.parametrize("rel_path", bundle_paths("bp"))
def test_editing_any_bound_file_after_approval_fails(approved_case: Path, rel_path: str) -> None:
    """The hash binding is the mechanism behind reopening draft state."""

    path = approved_case / rel_path
    path.write_text(path.read_text(encoding="utf-8") + "\nAn edit after approval.\n", encoding="utf-8")
    findings = check(approved_case)
    assert any("changed after approval" in finding or "structural check must pass" in finding for finding in findings)


def test_a_hand_written_nonzero_blocking_count_is_rejected(approved_case: Path) -> None:
    """The builder refuses this; the checker must refuse it too, because a record is just a file."""

    write_approval(approved_case, payload(approved_case, blocking_findings_count=1))
    assert any("blocking_findings_count of 0" in finding for finding in check(approved_case))


def test_a_hand_written_negative_verdict_is_rejected(approved_case: Path) -> None:
    write_approval(approved_case, payload(approved_case, verdict="changes_required"))
    assert any("verdict must be one of" in finding for finding in check(approved_case))


def test_a_hand_written_self_approval_is_rejected(approved_case: Path) -> None:
    write_approval(approved_case, payload(approved_case, reviewer_agent="authoring-parent"))
    assert any("different agent than the bundle author" in finding for finding in check(approved_case))


def test_a_missing_author_identity_is_rejected(approved_case: Path) -> None:
    write_approval(approved_case, payload(approved_case, author_agent="  "))
    assert any("author_agent is required" in finding for finding in check(approved_case))


def test_a_wrong_schema_version_is_rejected(approved_case: Path) -> None:
    write_approval(approved_case, payload(approved_case, schema_version="review-approval-v1"))
    assert any(BUNDLE_APPROVAL_SCHEMA in finding for finding in check(approved_case))


def test_a_record_for_another_case_or_variant_is_rejected(approved_case: Path) -> None:
    write_approval(approved_case, payload(approved_case, case_id="someone-else", variant="dp"))
    findings = check(approved_case)
    assert any("case_id must be" in finding for finding in findings)
    assert any("variant must be" in finding for finding in findings)


def test_an_approval_binding_a_file_outside_the_bundle_is_rejected(approved_case: Path) -> None:
    record = payload(approved_case)
    record["files"].append({"path": "outputs/assignment_formal_dp.md", "sha256": "0" * 64})
    write_approval(approved_case, record)
    assert any("outside the bundle" in finding for finding in check(approved_case))


def test_a_structurally_failing_bundle_fails_even_with_a_valid_record(approved_case: Path) -> None:
    """An approval over a broken bundle would read as reviewed, which is worse than none."""

    (approved_case / "outputs/assignment_formal_bp.md").write_text(
        assignment(literature="- Bude doplněno."), encoding="utf-8"
    )
    findings = check(approved_case)
    assert findings[0].startswith("the structural check must pass")


def test_the_builder_refuses_a_non_pass_verdict(approved_case: Path) -> None:
    """`payload()` overrides AFTER building, which is exactly why the hand-written cases exist."""

    with pytest.raises(ValueError, match="pass-only"):
        build_bundle_approval_payload(
            approved_case,
            case_id=CASE_ID,
            variant="bp",
            author_agent="authoring-parent",
            reviewer_agent="thesis-assignment-reviewer",
            reviewer_role="thesis-assignment-review",
            verdict="changes_required",
            blocking_findings_count=0,
            checks_observed=[],
            limitations=[],
            timestamp="2026-09-08T10:00:00Z",
        )


def test_the_builder_refuses_a_self_approval(approved_case: Path) -> None:
    with pytest.raises(ValueError, match="different agent"):
        build_bundle_approval_payload(
            approved_case,
            case_id=CASE_ID,
            variant="bp",
            author_agent="same",
            reviewer_agent="same",
            reviewer_role="thesis-assignment-review",
            verdict="approved",
            blocking_findings_count=0,
            checks_observed=[],
            limitations=[],
            timestamp="2026-09-08T10:00:00Z",
        )


@pytest.mark.parametrize("value", [False, 0.0, "0", None])
def test_a_blocking_count_that_is_not_an_integer_zero_is_rejected(approved_case: Path, value: object) -> None:
    """`False` and `0.0` both equal 0; neither is a count."""

    write_approval(approved_case, payload(approved_case, blocking_findings_count=value))
    assert any("integer blocking_findings_count" in finding for finding in check(approved_case))


def test_the_builder_refuses_a_blocking_count_that_is_not_an_integer(approved_case: Path) -> None:
    for value in (False, 0.0):
        with pytest.raises(ValueError, match="integer blocking_findings_count"):
            build_bundle_approval_payload(
                approved_case,
                case_id=CASE_ID,
                variant="bp",
                author_agent="authoring-parent",
                reviewer_agent="thesis-assignment-reviewer",
                reviewer_role="thesis-assignment-review",
                verdict="approved",
                blocking_findings_count=value,
                checks_observed=[],
                limitations=[],
                timestamp="2026-09-08T10:00:00Z",
            )


def test_a_duplicate_binding_is_rejected(approved_case: Path) -> None:
    """Last-wins let a wrong hash be followed by the right one for the same file."""

    record = payload(approved_case)
    record["files"].insert(0, {"path": "notes/topic_intake.md", "sha256": "0" * 64})
    write_approval(approved_case, record)
    assert any("bound more than once" in finding for finding in check(approved_case))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("reviewer_role", None),
        ("reviewer_role", ""),
        ("timestamp", None),
        ("checks_observed", "scripts/check-assignment-draft"),
        ("limitations", 3),
        ("checks_observed", [1, 2]),
        ("notes", 7),
    ],
)
def test_malformed_audit_metadata_is_rejected(approved_case: Path, field: str, value: object) -> None:
    """Audit fields prove nothing, but a malformed record must not pass a publication gate."""

    write_approval(approved_case, payload(approved_case, **{field: value}))
    assert any(field in finding for finding in check(approved_case))


def test_a_missing_audit_field_is_rejected(approved_case: Path) -> None:
    record = payload(approved_case)
    del record["timestamp"]
    write_approval(approved_case, record)
    assert any("timestamp must be" in finding for finding in check(approved_case))


BUILDER_REJECTS = [
    ("non-pass verdict", {"verdict": "changes_required"}),
    ("boolean blocking count", {"blocking_findings_count": False}),
    ("float blocking count", {"blocking_findings_count": 0.0}),
    ("nonzero blocking count", {"blocking_findings_count": 2}),
    ("blank reviewer", {"reviewer_agent": "   "}),
    ("blank author", {"author_agent": "   "}),
    ("self approval", {"reviewer_agent": "authoring-parent"}),
    ("empty reviewer role", {"reviewer_role": ""}),
    ("wrong checks_observed type", {"checks_observed": "one check"}),
    ("wrong limitations type", {"limitations": 3}),
    ("empty timestamp", {"timestamp": ""}),
]


@pytest.mark.parametrize(("label", "override"), BUILDER_REJECTS, ids=[case[0] for case in BUILDER_REJECTS])
def test_whatever_the_builder_rejects_the_reader_rejects_too(approved_case: Path, label: str, override: dict) -> None:
    """The gate is the reader. A builder rule the reader does not mirror protects nothing."""

    kwargs: dict = {
        "case_id": CASE_ID,
        "variant": "bp",
        "author_agent": "authoring-parent",
        "reviewer_agent": "thesis-assignment-reviewer",
        "reviewer_role": "thesis-assignment-review",
        "verdict": "approved",
        "blocking_findings_count": 0,
        "checks_observed": [],
        "limitations": [],
        "timestamp": "2026-09-08T10:00:00Z",
    }
    kwargs.update(override)
    with pytest.raises(ValueError):
        build_bundle_approval_payload(approved_case, **kwargs)

    write_approval(approved_case, payload(approved_case, **override))
    assert check(approved_case), f"the reader accepted a record the builder refused: {label}"


def test_the_builder_cannot_emit_a_record_its_reader_rejects(approved_case: Path) -> None:
    write_approval(approved_case, payload(approved_case))
    assert check(approved_case) == []
