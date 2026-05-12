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
