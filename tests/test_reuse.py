from thesis_review_workflow.reuse import (
    ArtifactRole,
    CoverageSatisfiedBy,
    NextAction,
    ReuseStatus,
    SourceClass,
    SourceFingerprint,
    compare_source_fingerprints,
    decide_reuse,
    source_classes_for_role,
    source_fingerprint_from_record,
    source_fingerprint_to_record,
    stable_json_sha256,
)

HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64


def source(
    ref: str, source_class: SourceClass, sha256: str | None = HASH_A, *, available: bool = True
) -> SourceFingerprint:
    return SourceFingerprint(ref, source_class, sha256, available=available)


def assert_raises_value_error(message_fragment: str, factory: object) -> None:
    if not callable(factory):
        raise AssertionError("factory must be callable")
    try:
        factory()
    except ValueError as exc:
        assert message_fragment in str(exc)
        return
    raise AssertionError("expected ValueError")


def test_role_dependencies_keep_code_quality_separate_from_thesis_text() -> None:
    code_quality_sources = source_classes_for_role(ArtifactRole.CODE_QUALITY)
    code_consistency_sources = source_classes_for_role(ArtifactRole.CODE_CONSISTENCY)

    assert SourceClass.CODE_WORKSPACE in code_quality_sources
    assert SourceClass.THESIS_EXTRACT not in code_quality_sources
    assert SourceClass.CODE_WORKSPACE in code_consistency_sources
    assert SourceClass.THESIS_EXTRACT in code_consistency_sources


def test_unchanged_reviewed_sources_are_reusable_without_fresh_semantic_review() -> None:
    current = [source("work/code_workspace.md", SourceClass.CODE_WORKSPACE)]
    prior = [source("work/code_workspace.md", SourceClass.CODE_WORKSPACE)]

    decision = decide_reuse(
        artifact_role=ArtifactRole.CODE_QUALITY,
        current_sources=current,
        prior_sources=prior,
        prior_review_current=True,
        schema_compatible=True,
        coverage_satisfied_by=CoverageSatisfiedBy.CURRENT_REVIEWED_ARTIFACT,
    )

    assert decision.status == ReuseStatus.UNCHANGED_REUSABLE
    assert decision.fresh_semantic_review_required is False
    assert decision.coverage_satisfied_by == CoverageSatisfiedBy.CURRENT_REVIEWED_ARTIFACT
    assert decision.next_action == NextAction.REUSE_EXISTING_REVIEW
    assert decision.source_sha256 == {"work/code_workspace.md": HASH_A}
    assert decision.unchanged_refs == ("work/code_workspace.md",)


def test_role_irrelevant_source_changes_do_not_force_delta_review() -> None:
    current = [
        source("work/code_workspace.md", SourceClass.CODE_WORKSPACE, HASH_A),
        source("extracted/thesis.txt", SourceClass.THESIS_EXTRACT, HASH_B),
    ]
    prior = [
        source("work/code_workspace.md", SourceClass.CODE_WORKSPACE, HASH_A),
        source("extracted/thesis.txt", SourceClass.THESIS_EXTRACT, HASH_C),
    ]

    decision = decide_reuse(
        artifact_role=ArtifactRole.CODE_QUALITY,
        current_sources=current,
        prior_sources=prior,
        prior_review_current=True,
        schema_compatible=True,
    )

    assert decision.status == ReuseStatus.UNCHANGED_REUSABLE
    assert decision.changed_refs == ()
    assert decision.source_sha256 == {"work/code_workspace.md": HASH_A}


def test_changed_role_relevant_source_requires_delta_review() -> None:
    current = [source("work/code_workspace.md", SourceClass.CODE_WORKSPACE, HASH_A)]
    prior = [source("work/code_workspace.md", SourceClass.CODE_WORKSPACE, HASH_B)]

    decision = decide_reuse(
        artifact_role=ArtifactRole.CODE_QUALITY,
        current_sources=current,
        prior_sources=prior,
        prior_review_current=True,
        schema_compatible=True,
    )

    assert decision.status == ReuseStatus.CHANGED_DELTA_REQUIRED
    assert decision.fresh_semantic_review_required is True
    assert decision.coverage_satisfied_by == CoverageSatisfiedBy.NOT_SATISFIED
    assert decision.next_action == NextAction.DELTA_REVIEW
    assert decision.changed_refs == ("work/code_workspace.md",)


def test_missing_current_source_requires_manual_limitation() -> None:
    current = [source("work/code_workspace.md", SourceClass.CODE_WORKSPACE, None, available=False)]
    prior = [source("work/code_workspace.md", SourceClass.CODE_WORKSPACE, HASH_A)]

    decision = decide_reuse(
        artifact_role=ArtifactRole.CODE_QUALITY,
        current_sources=current,
        prior_sources=prior,
        prior_review_current=True,
        schema_compatible=True,
    )

    assert decision.status == ReuseStatus.STALE_OR_UNREVIEWED
    assert decision.next_action == NextAction.MANUAL_LIMITATION
    assert decision.missing_current_refs == ("work/code_workspace.md",)


def test_stale_prior_review_requires_fresh_role_review_even_when_sources_match() -> None:
    current = [source("work/code_workspace.md", SourceClass.CODE_WORKSPACE)]
    prior = [source("work/code_workspace.md", SourceClass.CODE_WORKSPACE)]

    decision = decide_reuse(
        artifact_role=ArtifactRole.CODE_QUALITY,
        current_sources=current,
        prior_sources=prior,
        prior_review_current=False,
        schema_compatible=True,
    )

    assert decision.status == ReuseStatus.STALE_OR_UNREVIEWED
    assert decision.fresh_semantic_review_required is True
    assert decision.next_action == NextAction.FRESH_ROLE_REVIEW
    assert "prior review is stale or absent" in decision.reasons


def test_fresh_role_review_coverage_is_not_reused() -> None:
    current = [source("work/code_workspace.md", SourceClass.CODE_WORKSPACE)]
    prior = [source("work/code_workspace.md", SourceClass.CODE_WORKSPACE)]

    decision = decide_reuse(
        artifact_role=ArtifactRole.CODE_QUALITY,
        current_sources=current,
        prior_sources=prior,
        prior_review_current=True,
        schema_compatible=True,
        coverage_satisfied_by=CoverageSatisfiedBy.FRESH_ROLE_REVIEW,
    )

    assert decision.status == ReuseStatus.STALE_OR_UNREVIEWED
    assert decision.fresh_semantic_review_required is True
    assert decision.coverage_satisfied_by == CoverageSatisfiedBy.FRESH_ROLE_REVIEW
    assert decision.next_action == NextAction.FRESH_ROLE_REVIEW


def test_missing_hash_is_not_comparable_until_backfill() -> None:
    current = [source("work/code_workspace.md", SourceClass.CODE_WORKSPACE, None)]
    prior = [source("work/code_workspace.md", SourceClass.CODE_WORKSPACE, HASH_A)]

    decision = decide_reuse(
        artifact_role=ArtifactRole.CODE_QUALITY,
        current_sources=current,
        prior_sources=prior,
        prior_review_current=True,
        schema_compatible=True,
    )

    assert decision.status == ReuseStatus.NOT_COMPARABLE
    assert decision.fresh_semantic_review_required is True
    assert decision.next_action == NextAction.NOT_COMPARABLE_BACKFILL
    assert decision.not_comparable_refs == ("work/code_workspace.md",)


def test_absent_role_relevant_fingerprints_are_not_comparable() -> None:
    decision = decide_reuse(
        artifact_role=ArtifactRole.CODE_QUALITY,
        current_sources=[source("extracted/thesis.txt", SourceClass.THESIS_EXTRACT, HASH_A)],
        prior_sources=[source("extracted/thesis.txt", SourceClass.THESIS_EXTRACT, HASH_A)],
        prior_review_current=True,
        schema_compatible=True,
    )

    assert decision.status == ReuseStatus.NOT_COMPARABLE
    assert decision.next_action == NextAction.NOT_COMPARABLE_BACKFILL
    assert "no current role-relevant source fingerprints" in decision.reasons


def test_empty_current_with_prior_role_relevant_source_preserves_removed_ref() -> None:
    decision = decide_reuse(
        artifact_role=ArtifactRole.CODE_QUALITY,
        current_sources=[source("extracted/thesis.txt", SourceClass.THESIS_EXTRACT, HASH_A)],
        prior_sources=[source("work/code_workspace.md", SourceClass.CODE_WORKSPACE, HASH_A)],
        prior_review_current=True,
        schema_compatible=True,
    )

    assert decision.status == ReuseStatus.NOT_COMPARABLE
    assert decision.next_action == NextAction.NOT_COMPARABLE_BACKFILL
    assert decision.removed_refs == ("work/code_workspace.md",)


def test_schema_incompatibility_is_not_comparable_even_when_hashes_match() -> None:
    current = [source("work/code_workspace.md", SourceClass.CODE_WORKSPACE)]
    prior = [source("work/code_workspace.md", SourceClass.CODE_WORKSPACE)]

    decision = decide_reuse(
        artifact_role=ArtifactRole.CODE_QUALITY,
        current_sources=current,
        prior_sources=prior,
        prior_review_current=True,
        schema_compatible=False,
    )

    assert decision.status == ReuseStatus.NOT_COMPARABLE
    assert decision.next_action == NextAction.NOT_COMPARABLE_BACKFILL
    assert "producer schema is not compatible" in decision.reasons


def test_source_comparison_reports_added_and_removed_role_relevant_sources() -> None:
    comparison = compare_source_fingerprints(
        current_sources=[source("work/code_workspace.md", SourceClass.CODE_WORKSPACE, HASH_A)],
        prior_sources=[source("work/old_code_workspace.md", SourceClass.CODE_WORKSPACE, HASH_A)],
        role=ArtifactRole.CODE_QUALITY,
    )

    assert comparison.added_refs == ("work/code_workspace.md",)
    assert comparison.removed_refs == ("work/old_code_workspace.md",)


def test_source_fingerprint_rejects_unsafe_paths_and_bad_hashes() -> None:
    assert_raises_value_error(
        "unsafe source_ref",
        lambda: SourceFingerprint("/tmp/private.pdf", SourceClass.THESIS_PDF, HASH_A),
    )
    assert_raises_value_error(
        "64-character hex",
        lambda: SourceFingerprint("inputs/thesis.pdf", SourceClass.THESIS_PDF, "not-a-hash"),
    )


def test_duplicate_fingerprints_are_rejected() -> None:
    assert_raises_value_error(
        "duplicate source fingerprint",
        lambda: decide_reuse(
            artifact_role=ArtifactRole.CODE_QUALITY,
            current_sources=[
                source("work/code_workspace.md", SourceClass.CODE_WORKSPACE, HASH_A),
                source("work/code_workspace.md", SourceClass.CODE_WORKSPACE, HASH_B),
            ],
            prior_sources=[source("work/code_workspace.md", SourceClass.CODE_WORKSPACE, HASH_A)],
            prior_review_current=True,
            schema_compatible=True,
        ),
    )


def test_source_fingerprint_records_preserve_not_comparable_state() -> None:
    fingerprint = source("inputs/thesis.pdf", SourceClass.THESIS_PDF, None)

    record = source_fingerprint_to_record(fingerprint)
    restored = source_fingerprint_from_record(record)

    assert record["state"] == "not_comparable"
    assert restored == fingerprint


def test_stable_json_hash_ignores_object_key_order() -> None:
    assert stable_json_sha256({"b": 2, "a": 1}) == stable_json_sha256({"a": 1, "b": 2})


def test_every_artifact_role_has_source_dependency_mapping() -> None:
    for role in ArtifactRole:
        dependencies = source_classes_for_role(role)
        assert dependencies
        assert all(isinstance(source_class, SourceClass) for source_class in dependencies)


def test_common_briefing_and_role_packet_dependencies_include_handoff_context() -> None:
    common_sources = source_classes_for_role(ArtifactRole.COMMON_BRIEFING)
    packet_sources = source_classes_for_role(ArtifactRole.ROLE_PACKET)

    assert SourceClass.PREVIOUS_FEEDBACK in common_sources
    assert SourceClass.REVIEW_ARTIFACT in common_sources
    assert SourceClass.GENERATED_PACKET in packet_sources
    assert SourceClass.MATERIALITY_DECISION in packet_sources
