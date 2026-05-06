import json
from pathlib import Path

from thesis_review_workflow.cli.check_review_manifest import check_manifest


def test_review_manifest_validates_supporting_work_artifact_schema(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    artifact = round_dir / "work" / "assignment_coverage_map.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text(
        json.dumps(
            {
                "schema_version": "wrong-schema",
                "case_id": "case-a",
                "round_id": "round-a",
                "generated_at": "2026-05-06T00:00:00Z",
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
                "path": "work/assignment_coverage_map.json",
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
    assert any("schema_version must be assignment-coverage-map-v1" in error for error in errors)


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
    assignment = round_dir / "work" / "assignment_coverage_map.json"
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
                "evidence_refs": ["work/assignment_coverage_map.json"],
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
