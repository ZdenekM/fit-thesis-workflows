"""Contract tests for promoting an approved assignment variant into a thesis case.

Promotion makes an assignment the thing every later workflow grades against, so
each guard here has its own case: approval, issuance, target fitness, and
containment are independent, and passing three of them is not enough.
"""

import json
from pathlib import Path

import pytest

from thesis_review_workflow.assignment_bundle import approval_rel, build_bundle_approval_payload
from thesis_review_workflow.assignment_promotion import (
    ASSIGNMENT_REL,
    PromotionTarget,
    demote_headings,
    retained_approval_rel,
)
from thesis_review_workflow.cli.promote_assignment import promote
from thesis_review_workflow.markdown_utils import section_text

# Sibling import, not `tests.`: the test root is not a package in the Pants sandbox.
from test_assignment_draft import BRIEF_SOURCE, INTAKE, assignment, projection

TOPIC_ID = "topic-case"
TARGET_ID = "student-case"
ROUND_ID = "r1"


def make_topic_case(root: Path) -> Path:
    case_dir = root / "cases" / TOPIC_ID
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
    record = build_bundle_approval_payload(
        case_dir,
        case_id=TOPIC_ID,
        variant="bp",
        author_agent="authoring-parent",
        reviewer_agent="thesis-assignment-reviewer",
        reviewer_role="thesis-assignment-review",
        verdict="approved",
        blocking_findings_count=0,
        checks_observed=["scripts/check-assignment-draft"],
        limitations=[],
        timestamp="2026-09-08T10:00:00Z",
    )
    (case_dir / approval_rel("bp")).write_text(json.dumps(record), encoding="utf-8")
    return case_dir


def make_target(root: Path, work_type: str = "BP", kind: str = "thesis-review") -> PromotionTarget:
    case_dir = root / "cases" / TARGET_ID
    round_dir = case_dir / "rounds" / ROUND_ID
    (round_dir / "notes").mkdir(parents=True)
    (case_dir / "case.md").write_text(
        f"Case ID: s\nCase kind: {kind}\nWork type: {work_type}\nStudent feedback language: cs\n", encoding="utf-8"
    )
    return PromotionTarget(case_dir, round_dir, ROUND_ID)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "cases").mkdir()
    return tmp_path


def run(root: Path, topic: Path, target: PromotionTarget, **overrides: object) -> list[str]:
    kwargs: dict = {"issued": True, "issued_note": "2026-09-01", "replace": False, "actor": "operator"}
    kwargs.update(overrides)
    return promote(root, topic, TOPIC_ID, "bp", target, TARGET_ID, **kwargs)


def test_promotion_writes_the_assignment_context(repo: Path) -> None:
    topic = make_topic_case(repo)
    target = make_target(repo)
    assert run(repo, topic, target) == []

    text = (target.round_dir / ASSIGNMENT_REL).read_text(encoding="utf-8")
    assert f"Assignment source: topic={TOPIC_ID} variant=bp approval_sha256=" in text
    assert "Assignment issued: 2026-09-01 (asserted by operator)" in text
    for heading in (
        "## Formal Assignment Artifacts",
        "## Formal Assignment Text Or Summary",
        "## Private Assignment Notes For Student",
        "## Assignment Coverage Hints",
    ):
        assert heading in text


def test_the_semestral_requirement_survives_promotion(repo: Path) -> None:
    """A points-and-literature mapping drops a distinct formal obligation."""

    topic = make_topic_case(repo)
    target = make_target(repo)
    run(repo, topic, target)
    text = (target.round_dir / ASSIGNMENT_REL).read_text(encoding="utf-8")
    formal = section_text(text.splitlines(), "## Formal Assignment Text Or Summary")
    assert "Proveďte rešerši." in formal
    assert "Example, A. Provenance. Journal, 2026." in formal
    assert "Bod 1." in formal, "the semestral-defence requirement is missing"


def test_the_brief_headings_do_not_end_the_private_notes_section(repo: Path) -> None:
    """`check_round_ready` ends a section at the next H2, and the projection carries one."""

    topic = make_topic_case(repo)
    target = make_target(repo)
    run(repo, topic, target)
    text = (target.round_dir / ASSIGNMENT_REL).read_text(encoding="utf-8")
    notes = section_text(text.splitlines(), "## Private Assignment Notes For Student")
    assert "Contribution framing" in notes, "the delta fell outside the section"
    assert "\n## " not in notes


def test_the_approval_record_is_retained_beside_its_hash(repo: Path) -> None:
    """A hash is an identity; the record it names is overwritten by the next approval."""

    topic = make_topic_case(repo)
    target = make_target(repo)
    run(repo, topic, target)
    retained = target.round_dir / retained_approval_rel(TOPIC_ID, "bp")
    assert retained.is_file()
    assert json.loads(retained.read_text(encoding="utf-8"))["reviewer_agent"] == "thesis-assignment-reviewer"
    text = (target.round_dir / ASSIGNMENT_REL).read_text(encoding="utf-8")
    assert retained_approval_rel(TOPIC_ID, "bp").as_posix() in text


def test_the_operation_log_records_the_promotion(repo: Path) -> None:
    topic = make_topic_case(repo)
    target = make_target(repo)
    run(repo, topic, target)
    log = target.round_dir / "work" / "operation_log.jsonl"
    assert log.is_file()
    entry = json.loads(log.read_text(encoding="utf-8").splitlines()[-1])
    assert entry["operation"] == "promote-assignment"
    assert entry["details"]["variant"] == "bp"


def test_promotion_without_the_issuance_assertion_is_refused(repo: Path) -> None:
    """Approval says the variant may be published, not that the student received it."""

    topic = make_topic_case(repo)
    target = make_target(repo)
    findings = run(repo, topic, target, issued=False)
    assert any("explicit issuance assertion" in finding for finding in findings)
    assert not (target.round_dir / ASSIGNMENT_REL).exists()


def test_an_unapproved_variant_is_refused(repo: Path) -> None:
    topic = make_topic_case(repo)
    (topic / approval_rel("bp")).unlink()
    target = make_target(repo)
    assert any("not approved and current" in finding for finding in run(repo, topic, target))


def test_a_stale_bundle_is_refused(repo: Path) -> None:
    topic = make_topic_case(repo)
    path = topic / "outputs/assignment_formal_bp.md"
    path.write_text(path.read_text(encoding="utf-8") + "\nEdited after approval.\n", encoding="utf-8")
    target = make_target(repo)
    assert any("not approved and current" in finding for finding in run(repo, topic, target))


def approve(topic: Path, variant: str) -> None:
    record = build_bundle_approval_payload(
        topic,
        case_id=TOPIC_ID,
        variant=variant,
        author_agent="authoring-parent",
        reviewer_agent="thesis-assignment-reviewer",
        reviewer_role="thesis-assignment-review",
        verdict="approved",
        blocking_findings_count=0,
        checks_observed=["scripts/check-assignment-draft"],
        limitations=[],
        timestamp="2026-09-08T10:00:00Z",
    )
    (topic / approval_rel(variant)).write_text(json.dumps(record), encoding="utf-8")


@pytest.mark.parametrize("replace", [False, True])
def test_an_approved_dp_bundle_into_a_bp_case_is_refused(repo: Path, replace: bool) -> None:
    """The DP must be APPROVED, or this never reaches the work-type check it is testing."""

    topic = make_topic_case(repo)
    approve(topic, "dp")
    target = make_target(repo, work_type="BP")
    findings = promote(
        repo,
        topic,
        TOPIC_ID,
        "dp",
        target,
        TARGET_ID,
        issued=True,
        issued_note="x",
        replace=replace,
        actor="operator",
    )
    assert any("variant `dp` is a DP" in finding for finding in findings), findings
    assert not (target.round_dir / ASSIGNMENT_REL).exists()


def test_an_unknown_work_type_is_refused(repo: Path) -> None:
    topic = make_topic_case(repo)
    target = make_target(repo, work_type="unknown")
    assert any("Work type" in finding for finding in run(repo, topic, target))


def test_a_target_that_is_not_a_thesis_review_case_is_refused(repo: Path) -> None:
    topic = make_topic_case(repo)
    target = make_target(repo, kind="topic-proposal")
    assert any("promote into a thesis-review case" in finding for finding in run(repo, topic, target))


def test_a_case_directory_linked_out_of_the_private_root_is_refused(repo: Path) -> None:
    """`.gitignore` protects the lexical `cases/` path, not a redirected one."""

    outside = repo / "docs" / TARGET_ID
    (outside / "rounds" / ROUND_ID / "notes").mkdir(parents=True)
    (outside / "case.md").write_text("Case kind: thesis-review\nWork type: BP\n", encoding="utf-8")
    link = repo / "cases" / TARGET_ID
    link.symlink_to(outside, target_is_directory=True)

    topic = make_topic_case(repo)
    target = PromotionTarget(link, link / "rounds" / ROUND_ID, ROUND_ID)
    findings = run(repo, topic, target)
    assert any("outside the private case root" in finding for finding in findings)
    assert not (outside / "rounds" / ROUND_ID / ASSIGNMENT_REL).exists()


def test_replace_does_not_lift_the_containment_refusal(repo: Path) -> None:
    outside = repo / "docs" / TARGET_ID
    (outside / "rounds" / ROUND_ID / "notes").mkdir(parents=True)
    (outside / "case.md").write_text("Case kind: thesis-review\nWork type: BP\n", encoding="utf-8")
    link = repo / "cases" / TARGET_ID
    link.symlink_to(outside, target_is_directory=True)

    topic = make_topic_case(repo)
    target = PromotionTarget(link, link / "rounds" / ROUND_ID, ROUND_ID)
    assert any("outside the private case root" in finding for finding in run(repo, topic, target, replace=True))


def test_an_existing_assignment_is_not_overwritten_without_replace(repo: Path) -> None:
    topic = make_topic_case(repo)
    target = make_target(repo)
    existing = target.round_dir / ASSIGNMENT_REL
    existing.write_text("# The assignment this case was reviewed against\n", encoding="utf-8")
    assert any("--replace" in finding for finding in run(repo, topic, target))
    assert existing.read_text(encoding="utf-8").startswith("# The assignment this case")

    assert run(repo, topic, target, replace=True) == []
    assert "Assignment source:" in existing.read_text(encoding="utf-8")


def test_demote_headings_never_exceeds_h6() -> None:
    assert demote_headings("###### deep") == "###### deep"


def test_a_dangling_destination_symlink_is_refused(repo: Path) -> None:
    """`exists()` is false for a dangling link, so an earlier version checked only its parent."""

    topic = make_topic_case(repo)
    target = make_target(repo)
    leak = repo / "docs" / "leak.md"
    leak.parent.mkdir(parents=True, exist_ok=True)
    (target.round_dir / ASSIGNMENT_REL).symlink_to(leak)

    findings = run(repo, topic, target)
    assert any("escapes the target case" in finding for finding in findings), findings
    assert not leak.exists()


def test_a_redirected_operation_log_is_refused_before_any_write(repo: Path) -> None:
    topic = make_topic_case(repo)
    target = make_target(repo)
    outside = repo / "docs" / "operation_log.jsonl"
    outside.parent.mkdir(parents=True, exist_ok=True)
    outside.write_text("", encoding="utf-8")
    log = target.round_dir / "work" / "operation_log.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.symlink_to(outside)

    findings = run(repo, topic, target)
    assert any("escapes the target case" in finding for finding in findings), findings
    assert outside.read_text(encoding="utf-8") == ""
    assert not (target.round_dir / ASSIGNMENT_REL).exists()


def test_a_redirected_private_root_is_refused(repo: Path) -> None:
    """A `cases/` linked elsewhere resolves inside the repo, so descendant checks all pass."""

    topic = make_topic_case(repo)
    target = make_target(repo)
    elsewhere = repo / "elsewhere"
    (repo / "cases").rename(elsewhere)
    (repo / "cases").symlink_to(elsewhere, target_is_directory=True)

    findings = run(repo, topic, PromotionTarget(repo / "cases" / TARGET_ID, target.round_dir, ROUND_ID))
    assert any("private case root is redirected" in finding for finding in findings), findings


@pytest.mark.parametrize("linked", ["rounds", "rounds/r1", "rounds/r1/notes", "rounds/r1/work"])
def test_no_directory_on_a_write_path_can_redirect_out_of_the_case(repo: Path, linked: str) -> None:
    """Every write destination resolves through its whole path, so any link on it is caught."""

    topic = make_topic_case(repo)
    target = make_target(repo)
    outside = repo / "docs" / "redirected"
    outside.mkdir(parents=True)

    victim = target.case_dir / linked
    if victim.exists():
        for child in sorted(victim.rglob("*"), reverse=True):
            child.rmdir() if child.is_dir() else child.unlink()
        victim.rmdir()
    victim.parent.mkdir(parents=True, exist_ok=True)
    victim.symlink_to(outside, target_is_directory=True)

    findings = run(repo, topic, target)
    assert any("escapes the target case" in finding for finding in findings), findings
    assert not list(outside.rglob("*")), "promotion wrote through the redirected directory"


def test_a_case_created_by_the_normal_command_is_a_valid_promotion_target(repo: Path, monkeypatch) -> None:
    """The smoke fixture hand-wrote metadata and hid this: `new-case` left `Case kind` unresolved."""

    from thesis_review_workflow.cli import new_case

    template = Path("templates/case-notes.md").read_text(encoding="utf-8")
    (repo / "templates").mkdir(exist_ok=True)
    (repo / "templates" / "case-notes.md").write_text(template, encoding="utf-8")

    case_dir = repo / "cases" / TARGET_ID
    case_dir.mkdir(parents=True)
    (case_dir / "case.md").write_text(template, encoding="utf-8")
    new_case.replace_field(case_dir / "case.md", "Case ID", TARGET_ID)
    new_case.replace_field(case_dir / "case.md", "Case kind", "thesis-review")
    new_case.replace_field(case_dir / "case.md", "Work type", "BP")

    from thesis_review_workflow.metadata import case_kind, read_fields

    assert case_kind(read_fields(case_dir / "case.md")) == "thesis-review"

    round_dir = case_dir / "rounds" / ROUND_ID
    (round_dir / "notes").mkdir(parents=True)
    topic = make_topic_case(repo)
    assert run(repo, topic, PromotionTarget(case_dir, round_dir, ROUND_ID)) == []
