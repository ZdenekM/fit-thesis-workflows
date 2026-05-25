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
