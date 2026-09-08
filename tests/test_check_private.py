from thesis_review_workflow.cli.check_private import PRIVATE_MARKDOWN_RE, is_sensitive_artifact


def test_theses_similarity_artifacts_are_private() -> None:
    assert is_sensitive_artifact("work/theses_similarity/intake.json")
    assert is_sensitive_artifact("work/theses_similarity/assessment.json")
    assert is_sensitive_artifact("work/theses_similarity/source_matches.json")
    assert is_sensitive_artifact("work/reviews/theses_similarity_review.json")
    assert PRIVATE_MARKDOWN_RE.search("work/theses_similarity/review_draft.md")
    assert PRIVATE_MARKDOWN_RE.search("outputs/theses_similarity_review.md")
    assert is_sensitive_artifact("inputs/theses_similarity/report.pdf")
    assert is_sensitive_artifact("extracted/theses_similarity/report.txt")


def test_external_opponent_feedback_artifacts_are_private() -> None:
    assert is_sensitive_artifact("work/external_opponent_report_intake.json")
    assert is_sensitive_artifact("work/external_opponent_feedback_findings.json")
    assert is_sensitive_artifact("work/supervisor_learning_candidates.json")
    assert is_sensitive_artifact("work/reviews/external_opponent_feedback_review.json")
    assert PRIVATE_MARKDOWN_RE.search("outputs/external_opponent_feedback_analysis.md")
    assert is_sensitive_artifact("inputs/external_opponent_report/opponent-report.txt")
    assert is_sensitive_artifact("inputs/external_opponent_report/opponent-report.md")
    assert is_sensitive_artifact("inputs/external_opponent_report/opponent-report.html")


def test_report_calibration_basis_is_private() -> None:
    assert is_sensitive_artifact("work/report_calibration_basis.json")
    assert is_sensitive_artifact("cases/case-a/rounds/round-a/work/report_calibration_basis.json")


def test_assignment_authoring_artifacts_are_private() -> None:
    assert PRIVATE_MARKDOWN_RE.search("notes/topic_intake.md")
    assert PRIVATE_MARKDOWN_RE.search("notes/student_brief.md")
    assert PRIVATE_MARKDOWN_RE.search("outputs/assignment_formal_bp.md")
    assert PRIVATE_MARKDOWN_RE.search("outputs/assignment_formal_dp.md")
    assert PRIVATE_MARKDOWN_RE.search("outputs/student_brief_bp.md")
    assert PRIVATE_MARKDOWN_RE.search("work/reviews/assignment_review_bp.md")
    # The bundle-binding approval is not named `_review.json`, so it needed its own pattern.
    assert is_sensitive_artifact("work/reviews/assignment_approval_bp.json")


def test_the_tracked_authoring_templates_are_not_mistaken_for_case_artifacts() -> None:
    """Template basenames are hyphenated; generated case artifacts use underscores."""

    assert not PRIVATE_MARKDOWN_RE.search("templates/topic-intake.md")
    assert not PRIVATE_MARKDOWN_RE.search("templates/student-brief.md")
    assert not PRIVATE_MARKDOWN_RE.search("templates/assignment-formal.md")
    assert not PRIVATE_MARKDOWN_RE.search("docs/assignment-authoring.md")
