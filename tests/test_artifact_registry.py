from thesis_review_workflow.artifact_registry import output_spec, review_basis_candidates


def test_opponent_report_review_prefers_clean_is_entry_proposal_basis() -> None:
    spec = output_spec("outputs/feedback_k_posudku.md")

    assert spec is not None
    assert spec.review_basis_candidates[0] == "outputs/oponent_posudek_navrh.md"
    assert "work/oponent_posudek_draft.md" in spec.review_basis_candidates


def test_clean_opponent_report_proposal_is_first_class_draft_artifact() -> None:
    spec = output_spec("outputs/oponent_posudek_navrh.md")

    assert spec is not None
    assert spec.artifact_type == "opponent_report_is_entry_proposal"
    assert spec.review_scope == "draft_only"
    assert review_basis_candidates("outputs/feedback_k_posudku.md")[0] == "outputs/oponent_posudek_navrh.md"
