import json
from pathlib import Path

from thesis_review_workflow.cli.check_review_manifest import check_manifest
from thesis_review_workflow.review_manifest import ensure_manifest, merge_supporting_work_artifacts, register_artifact
from thesis_review_workflow.work_artifacts import sha256_file


def test_review_manifest_validates_supporting_work_artifact_schema(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    artifact = round_dir / "work" / "assignment_coverage_agent.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text(
        json.dumps(
            {
                "schema_version": "wrong-schema",
                "case_id": "case-a",
                "round_id": "round-a",
                "generated_at": "2026-05-06T00:00:00Z",
                "producer_type": "agent",
                "producer_role": "assignment-coverage-reviewer",
                "producer_agent": "agent-a",
                "authorization_note": "Authorized in current request.",
                "source_refs": [],
                "assignment_points": [],
                "limitations": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = {
        "schema_version": "review-manifest-v1",
        "case_id": "case-a",
        "round_id": "round-a",
        "manifest_path": "work/review_manifest.json",
        "inputs": [],
        "extracted_artifacts": [],
        "notes": [],
        "supporting_work_artifacts": [
            {
                "path": "work/assignment_coverage_agent.json",
                "kind": "structured_data",
                "artifact_sha256": "0" * 64,
            }
        ],
        "workflow_limitations": [],
        "artifacts": [],
        "helper_checks": [],
    }
    errors: list[str] = []
    warnings: list[str] = []

    check_manifest(manifest, "case-a", "round-a", root, round_dir, False, errors, warnings)

    assert any("artifact_sha256 is stale" in error for error in errors)
    assert any("schema_version must be assignment-coverage-agent-v1" in error for error in errors)


def test_review_manifest_requires_supporting_work_artifacts_list(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "work").mkdir(parents=True)
    manifest = {
        "schema_version": "review-manifest-v1",
        "case_id": "case-a",
        "round_id": "round-a",
        "manifest_path": "work/review_manifest.json",
        "inputs": [],
        "extracted_artifacts": [],
        "notes": [],
        "workflow_limitations": [],
        "artifacts": [],
        "helper_checks": [],
    }
    errors: list[str] = []

    check_manifest(manifest, "case-a", "round-a", root, round_dir, False, errors, [])

    assert "supporting_work_artifacts must be a list" in errors


def test_review_manifest_validates_artifact_refs_against_manifest_records(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    output = round_dir / "outputs" / "oponent_podklady_revidovane.md"
    output.parent.mkdir(parents=True)
    output.write_text("# Reviewed\n", encoding="utf-8")
    assignment = round_dir / "work" / "assignment_coverage_agent.json"
    assignment.parent.mkdir(parents=True)
    assignment.write_text("{}\n", encoding="utf-8")
    manifest = {
        "schema_version": "review-manifest-v1",
        "case_id": "case-a",
        "round_id": "round-a",
        "manifest_path": "work/review_manifest.json",
        "inputs": [],
        "extracted_artifacts": [],
        "notes": [],
        "supporting_work_artifacts": [],
        "workflow_limitations": [
            {"scope": "code", "description": "No code was submitted.", "impact": "None.", "status": "closed"}
        ],
        "artifacts": [
            {
                "path": "outputs/oponent_podklady_revidovane.md",
                "artifact_sha256": "stale",
                "artifact_type": "opponent_materials_reviewed",
                "review_scope": "standalone_final",
                "skills": [],
                "generated_by": [],
                "independent_review": {"status": "not_required"},
                "helper_checks": [],
                "input_refs": ["/home/private/input.pdf"],
                "evidence_refs": ["work/assignment_coverage_agent.json"],
                "check_refs": ["missing-check"],
            }
        ],
        "helper_checks": [],
    }
    errors: list[str] = []

    check_manifest(manifest, "case-a", "round-a", root, round_dir, False, errors, [])

    assert any("input_refs item 1: path must be relative inside the round" in error for error in errors)
    assert any("evidence_refs item 1 is not recorded in manifest" in error for error in errors)
    assert any("check_refs item 1 is not a manifest helper check" in error for error in errors)


def test_review_manifest_requires_internal_evidence_validators_when_artifacts_exist(tmp_path: Path) -> None:
    from thesis_review_workflow.cli.check_review_manifest import required_checks as check_required_checks
    from thesis_review_workflow.cli.init_review_manifest import required_checks as init_required_checks

    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    paths = {
        "outputs/code_consistency.md",
        "outputs/code_quality_review.md",
        "outputs/revision_diff.md",
    }

    init_names = {item["check"] for item in init_required_checks("case-a", "round-a", paths, round_dir, {})}
    check_names = check_required_checks(paths, round_dir, {})

    assert "check-code-consistency" in init_names
    assert "check-code-quality-review" in init_names
    assert "check-revision-diff" in init_names
    assert "check-code-consistency" in check_names
    assert "check-code-quality-review" in check_names
    assert "check-revision-diff" in check_names


def test_register_output_artifact_records_review_metadata(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    artifact = round_dir / "outputs" / "code_quality_review.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("# Internal Code Quality Review\n", encoding="utf-8")
    manifest = ensure_manifest({}, "case-a", "round-a")

    register_artifact(
        manifest,
        round_dir,
        "outputs/code_quality_review.md",
        role="thesis-code-quality-review",
        agent="generator-agent",
        contribution="generation",
        review_scope="internal_only",
        review_status="reviewed",
        reviewer_role="evidence-calibration-reviewer",
        reviewer_agent="reviewer-agent",
        reviewed_at="2026-05-06T00:00:00Z",
        limitation=["Static review only."],
        feeds=["outputs/oponent_podklady_revidovane.md"],
        input_refs=["notes/assignment.md"],
        evidence_refs=["work/code_reproducibility.json"],
        check_refs=["check-code-quality-review"],
        used_findings="Implementation risk summary.",
        review_basis_path="",
        notes="Registered by helper.",
    )

    entry = manifest["artifacts"][0]

    assert entry["artifact_sha256"] == sha256_file(artifact)
    assert entry["generated_by"][0]["agent"] == "generator-agent"
    assert entry["independent_review"]["reviewed_hash"] == entry["artifact_sha256"]
    assert entry["limitations"] == ["Static review only."]
    assert "outputs/oponent_podklady_revidovane.md" in entry["evidence_refs"]


def test_register_work_artifact_records_supporting_metadata(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    artifact = round_dir / "work" / "opponent_packets" / "code_quality_findings.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("Synthetic role findings.\n", encoding="utf-8")
    manifest = ensure_manifest({}, "case-a", "round-a")

    register_artifact(
        manifest,
        round_dir,
        "work/opponent_packets/code_quality_findings.md",
        role="code-quality-reviewer",
        agent="agent-a",
        contribution="generation",
        review_scope="internal_only",
        review_status="not_recorded",
        reviewer_role="not_recorded",
        reviewer_agent="not_recorded",
        reviewed_at="",
        limitation=["Feeds synthesis only."],
        feeds=["outputs/oponent_podklady_revidovane.md"],
        input_refs=[],
        evidence_refs=[],
        check_refs=[],
        used_findings="",
        review_basis_path="",
        notes="Role packet finding.",
    )

    entry = manifest["supporting_work_artifacts"][0]

    assert entry["path"] == "work/opponent_packets/code_quality_findings.md"
    assert entry["artifact_sha256"] == sha256_file(artifact)
    assert entry["role"] == "code-quality-reviewer"
    assert entry["feeds"] == ["outputs/oponent_podklady_revidovane.md"]


def test_merge_supporting_work_artifacts_preserves_registered_metadata(tmp_path: Path) -> None:
    previous = [
        {
            "path": "work/opponent_packets/code_quality_findings.md",
            "kind": "text",
            "artifact_sha256": "old",
            "role": "code-quality-reviewer",
            "agent": "agent-a",
            "limitations": ["Feeds synthesis only."],
        }
    ]
    generated = [
        {
            "path": "work/opponent_packets/code_quality_findings.md",
            "kind": "text",
            "artifact_sha256": "new",
        }
    ]

    merged = merge_supporting_work_artifacts(previous, generated)

    assert merged[0]["artifact_sha256"] == "new"
    assert merged[0]["role"] == "code-quality-reviewer"
    assert merged[0]["limitations"] == ["Feeds synthesis only."]


def test_register_artifact_rejects_paths_outside_round(tmp_path: Path) -> None:
    manifest = ensure_manifest({}, "case-a", "round-a")

    try:
        register_artifact(
            manifest,
            tmp_path / "round",
            "../outputs/leak.md",
            role="role",
            agent="agent",
            contribution="generation",
            review_scope=None,
            review_status="not_recorded",
            reviewer_role="not_recorded",
            reviewer_agent="not_recorded",
            reviewed_at="",
            limitation=[],
            feeds=[],
            input_refs=[],
            evidence_refs=[],
            check_refs=[],
            used_findings="",
            review_basis_path="",
            notes="",
        )
    except ValueError as exc:
        assert "safe relative path" in str(exc)
    else:
        raise AssertionError("unsafe artifact path should fail")


def test_register_final_artifact_records_review_basis(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    output = round_dir / "outputs" / "feedback_student.md"
    draft = round_dir / "work" / "feedback_student_draft.md"
    output.parent.mkdir(parents=True)
    draft.parent.mkdir(parents=True)
    output.write_text("# Reviewed feedback\n", encoding="utf-8")
    draft.write_text("# Draft feedback\n", encoding="utf-8")
    manifest = ensure_manifest({}, "case-a", "round-a")

    register_artifact(
        manifest,
        round_dir,
        "outputs/feedback_student.md",
        role="thesis-supervisor-feedback",
        agent="generator-agent",
        contribution="generation",
        review_scope="sendable_final",
        review_status="reviewed",
        reviewer_role="thesis-supervisor-feedback-review",
        reviewer_agent="reviewer-agent",
        reviewed_at="2026-05-06T00:00:00Z",
        limitation=["None."],
        feeds=[],
        input_refs=[],
        evidence_refs=[],
        check_refs=[],
        used_findings="",
        review_basis_path="work/feedback_student_draft.md",
        notes="",
    )
    review = manifest["artifacts"][0]["independent_review"]

    assert review["review_basis_path"] == "work/feedback_student_draft.md"
    assert review["review_basis_sha256"] == sha256_file(draft)


def test_register_covered_by_synthesis_sets_evidence_hash(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    final = round_dir / "outputs" / "oponent_podklady_revidovane.md"
    evidence = round_dir / "outputs" / "code_quality_review.md"
    final.parent.mkdir(parents=True)
    final.write_text("# Reviewed materials\n", encoding="utf-8")
    evidence.write_text("# Internal Code Quality Review\n", encoding="utf-8")
    manifest = ensure_manifest({}, "case-a", "round-a")

    register_artifact(
        manifest,
        round_dir,
        "outputs/oponent_podklady_revidovane.md",
        role="thesis-opponent-materials",
        agent="generator-agent",
        contribution="generation",
        review_scope="standalone_final",
        review_status="reviewed",
        reviewer_role="thesis-opponent-materials-review",
        reviewer_agent="reviewer-agent",
        reviewed_at="2026-05-06T00:00:00Z",
        limitation=["None."],
        feeds=[],
        input_refs=[],
        evidence_refs=[],
        check_refs=[],
        used_findings="",
        review_basis_path="",
        notes="",
    )
    register_artifact(
        manifest,
        round_dir,
        "outputs/code_quality_review.md",
        role="thesis-code-quality-review",
        agent="code-agent",
        contribution="generation",
        review_scope="covered_by_synthesis",
        review_status="not_required",
        reviewer_role="not_recorded",
        reviewer_agent="not_recorded",
        reviewed_at="",
        limitation=["Covered by synthesis."],
        feeds=["outputs/oponent_podklady_revidovane.md"],
        input_refs=[],
        evidence_refs=[],
        check_refs=[],
        used_findings="Used implementation risk P1.",
        review_basis_path="",
        notes="",
    )
    evidence_entry = next(item for item in manifest["artifacts"] if item["path"] == "outputs/code_quality_review.md")

    assert evidence_entry["independent_review"]["evidence_hash"] == evidence_entry["artifact_sha256"]


def test_register_refs_survive_init_manifest_refresh(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    output = round_dir / "outputs" / "code_quality_review.md"
    output.parent.mkdir(parents=True)
    output.write_text("# Internal Code Quality Review\n", encoding="utf-8")
    manifest = ensure_manifest({}, "case-a", "round-a")

    register_artifact(
        manifest,
        round_dir,
        "outputs/code_quality_review.md",
        role="thesis-code-quality-review",
        agent="generator-agent",
        contribution="generation",
        review_scope="internal_only",
        review_status="not_recorded",
        reviewer_role="not_recorded",
        reviewer_agent="not_recorded",
        reviewed_at="",
        limitation=[],
        feeds=[],
        input_refs=["notes/assignment.md"],
        evidence_refs=["work/code_reproducibility.json"],
        check_refs=["check-code-quality-review"],
        used_findings="",
        review_basis_path="",
        notes="",
    )
    existing = {"artifacts": manifest["artifacts"]}

    from thesis_review_workflow.cli.init_review_manifest import output_artifacts

    refreshed = output_artifacts(round_dir, existing)

    assert refreshed[0]["input_refs"] == ["notes/assignment.md"]
    assert refreshed[0]["evidence_refs"] == ["work/code_reproducibility.json"]
    assert refreshed[0]["check_refs"] == ["check-code-quality-review"]


def test_merge_supporting_work_artifacts_keeps_registered_only_work_artifact() -> None:
    previous = [
        {
            "path": "work/custom_reviewer_note.md",
            "kind": "text",
            "artifact_sha256": "old",
            "role": "custom-reviewer",
        }
    ]

    merged = merge_supporting_work_artifacts(previous, [])

    assert merged == previous


def test_register_artifact_rejects_unsafe_refs(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    artifact = round_dir / "outputs" / "code_quality_review.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("# Internal Code Quality Review\n", encoding="utf-8")
    manifest = ensure_manifest({}, "case-a", "round-a")

    try:
        register_artifact(
            manifest,
            round_dir,
            "outputs/code_quality_review.md",
            role="role",
            agent="agent",
            contribution="generation",
            review_scope="internal_only",
            review_status="not_recorded",
            reviewer_role="not_recorded",
            reviewer_agent="not_recorded",
            reviewed_at="",
            limitation=[],
            feeds=["/home/private/output.md"],
            input_refs=[],
            evidence_refs=[],
            check_refs=[],
            used_findings="",
            review_basis_path="",
            notes="",
        )
    except ValueError as exc:
        assert "feeds" in str(exc)
    else:
        raise AssertionError("unsafe feeds ref should fail")
