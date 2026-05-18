import json
from pathlib import Path
from typing import cast

from thesis_review_workflow import agent_coverage
from thesis_review_workflow.theses_similarity import (
    THESES_SIMILARITY_ASSESSMENT_REL,
    THESES_SIMILARITY_EXTRACTED_TEXT_REL,
    THESES_SIMILARITY_INTAKE_REL,
    THESES_SIMILARITY_REPORT_REL,
    THESES_SIMILARITY_REVIEW_APPROVAL_REL,
    THESES_SIMILARITY_REVIEW_REL,
    THESES_SIMILARITY_SILENT_USED_FINDINGS,
)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def make_final_round(tmp_path: Path) -> Path:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    final_output = round_dir / "outputs" / "feedback_student.md"
    final_output.parent.mkdir(parents=True)
    final_output.write_text("# Feedback\n", encoding="utf-8")
    return round_dir


def reviewed_feedback_artifact(round_dir: Path) -> dict[str, object]:
    final_output = round_dir / "outputs" / "feedback_student.md"
    final_hash = agent_coverage.sha256_file(final_output)
    return {
        "path": "outputs/feedback_student.md",
        "artifact_sha256": final_hash,
        "skills": ["thesis-supervisor-feedback-review"],
        "generated_by": [{"role": "thesis-supervisor-feedback-review", "agent": "reviewer-a"}],
        "independent_review": {
            "reviewer_role": "thesis-supervisor-feedback-review",
            "reviewer_agent": "reviewer-b",
            "reviewed_hash": final_hash,
        },
    }


def test_agent_coverage_uses_supporting_quantitative_claims_artifact(tmp_path: Path) -> None:
    round_dir = make_final_round(tmp_path)
    thesis_text = round_dir / "extracted" / "thesis.txt"
    quantitative = round_dir / "work" / "quantitative_claims.json"
    thesis_text.parent.mkdir(parents=True)
    quantitative.parent.mkdir(parents=True)
    thesis_text.write_text("Metric claim.\n", encoding="utf-8")
    quantitative.write_text(
        json.dumps(
            {
                "schema_version": "quantitative-claims-v1",
                "case_id": "case-a",
                "round_id": "round-a",
                "generated_at": "2026-05-11T00:00:00Z",
                "producer_type": "agent",
                "producer_role": "quantitative-claims-reviewer",
                "producer_agent": "agent-q",
                "authorization_note": "Authorized in current request.",
                "source_refs": ["extracted/thesis.txt"],
                "claims": [
                    {
                        "claim_id": "Q1",
                        "summary": "Reported metric needs context.",
                        "kind": "metric",
                        "status": "needs_context",
                        "unit": "not_verifiable",
                        "baseline_status": "missing",
                        "practical_context": "weak",
                        "scale_context": "Metric scale is not verifiable from the available evidence.",
                        "sample_context": "Sample size is not verifiable from the available evidence.",
                        "practical_magnitude": "Practical magnitude is not verifiable from the available evidence.",
                        "overclaim_risk": "moderate",
                        "reproducibility_refs": [],
                        "evidence_refs": ["extracted/thesis.txt"],
                        "requires_reviewer_verification": True,
                    }
                ],
                "limitations": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    quantitative_hash = agent_coverage.sha256_file(quantitative)
    manifest = {
        "inputs": [],
        "supporting_work_artifacts": [
            {
                "path": "work/quantitative_claims.json",
                "kind": "structured_data",
                "artifact_sha256": quantitative_hash,
                "schema_version": "quantitative-claims-v1",
                "producer_role": "quantitative-claims-reviewer",
                "producer_agent": "agent-q",
            }
        ],
        "artifacts": [reviewed_feedback_artifact(round_dir)],
    }

    specs = agent_coverage.inferred_role_specs(round_dir, manifest)
    coverage = agent_coverage.build_coverage("case-a", "round-a", round_dir, manifest)
    assert coverage is not None
    coverage["roles"].append(
        {
            "role": "not_material_side_role",
            "status": "not_applicable",
            "coverage_required": False,
            "fresh_review_required": False,
            "coverage_satisfied_by": "current_handoff",
            "trigger": "synthetic trailing not-applicable role",
            "required_for": [],
            "output_evidence": [],
        }
    )
    errors, warnings = agent_coverage.validate_coverage(coverage, manifest, "case-a", "round-a", round_dir)

    assert specs["quantitative_claims"].skill == "thesis-quantitative-claims-review"
    assert coverage is not None
    role = next(item for item in coverage["roles"] if item["role"] == "quantitative_claims")
    assert role["output_evidence"] == ["work/quantitative_claims.json"]
    assert role["generator_role"] == "quantitative-claims-reviewer"
    assert role["generator_agent"] == "agent-q"
    assert errors == []
    assert warnings == []

    supporting_records = cast(list[dict[str, object]], manifest["supporting_work_artifacts"])
    human_supporting = [dict(supporting_records[0])]
    human_supporting[0]["producer_type"] = "human"
    human_supporting[0]["producer_agent"] = None
    human_manifest = {**manifest, "supporting_work_artifacts": human_supporting}
    human_coverage = agent_coverage.build_coverage("case-a", "round-a", round_dir, human_manifest)
    assert human_coverage is not None
    human_errors, human_warnings = agent_coverage.validate_coverage(
        human_coverage,
        human_manifest,
        "case-a",
        "round-a",
        round_dir,
    )
    human_role = next(item for item in human_coverage["roles"] if item["role"] == "quantitative_claims")

    assert human_role["generator_agent"] == "human_reviewer"
    assert human_errors == []
    assert human_warnings == []


def test_agent_coverage_rejects_omen_unavailable_as_code_quality_role_block(tmp_path: Path) -> None:
    round_dir = make_final_round(tmp_path)
    (round_dir / "work" / "code").mkdir(parents=True, exist_ok=True)
    (round_dir / "work" / "code_workspace.md").write_text("Prepared submitted code root.\n", encoding="utf-8")
    manifest = {"inputs": [], "supporting_work_artifacts": [], "artifacts": [reviewed_feedback_artifact(round_dir)]}
    coverage = agent_coverage.build_coverage("case-a", "round-a", round_dir, manifest)
    assert coverage is not None
    roles = cast(list[dict[str, object]], coverage["roles"])
    code_quality = next(item for item in roles if item["role"] == "code_quality")
    code_quality["status"] = "blocked"
    code_quality["typed_limitation"] = {
        "role": "code_quality",
        "type": "unavailable_tool",
        "tool": "omen",
        "trigger": code_quality["trigger"],
        "required_for": code_quality["required_for"],
        "description": "Omen was unavailable in the operator environment.",
    }

    errors, _warnings = agent_coverage.validate_coverage(coverage, manifest, "case-a", "round-a", round_dir)

    assert any("Omen is optional advisory evidence" in error for error in errors)


def test_agent_coverage_requires_explicit_omen_tool_for_optional_tool_block(tmp_path: Path) -> None:
    round_dir = make_final_round(tmp_path)
    (round_dir / "work" / "code").mkdir(parents=True, exist_ok=True)
    (round_dir / "work" / "code_workspace.md").write_text("Prepared submitted code root.\n", encoding="utf-8")
    manifest = {"inputs": [], "supporting_work_artifacts": [], "artifacts": [reviewed_feedback_artifact(round_dir)]}
    coverage = agent_coverage.build_coverage("case-a", "round-a", round_dir, manifest)
    assert coverage is not None
    roles = cast(list[dict[str, object]], coverage["roles"])
    code_quality = next(item for item in roles if item["role"] == "code_quality")
    code_quality["status"] = "blocked"
    code_quality["typed_limitation"] = {
        "role": "code_quality",
        "type": "unavailable_tool",
        "trigger": code_quality["trigger"],
        "required_for": code_quality["required_for"],
        "description": "Omen was mentioned in notes, but the blocking evidence is a missing submitted source zip.",
    }

    errors, _warnings = agent_coverage.validate_coverage(coverage, manifest, "case-a", "round-a", round_dir)

    assert all("Omen is optional advisory evidence" not in error for error in errors)


def test_agent_coverage_requires_theses_similarity_review_for_final_outputs(tmp_path: Path) -> None:
    round_dir = make_final_round(tmp_path)
    theses_review = round_dir / THESES_SIMILARITY_REVIEW_REL
    report = round_dir / THESES_SIMILARITY_REPORT_REL
    theses_review.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True)
    theses_review.write_text("# Theses.cz Similarity Review\n", encoding="utf-8")
    report.write_bytes(b"%PDF synthetic\n")
    theses_hash = agent_coverage.sha256_file(theses_review)
    manifest = {
        "inputs": [{"path": THESES_SIMILARITY_REPORT_REL, "kind": "pdf"}],
        "supporting_work_artifacts": [],
        "artifacts": [
            reviewed_feedback_artifact(round_dir),
            {
                "path": THESES_SIMILARITY_REVIEW_REL,
                "artifact_sha256": theses_hash,
                "skills": ["thesis-theses-similarity-review"],
                "generated_by": [{"role": "thesis-theses-similarity-review", "agent": "agent-sim"}],
                "independent_review": {"status": "not_recorded"},
            },
        ],
    }

    specs = agent_coverage.inferred_role_specs(round_dir, manifest)
    coverage = agent_coverage.build_coverage("case-a", "round-a", round_dir, manifest)
    assert coverage is not None
    coverage["roles"].append(
        {
            "role": "not_material_side_role",
            "status": "not_applicable",
            "coverage_required": False,
            "fresh_review_required": False,
            "coverage_satisfied_by": "current_handoff",
            "trigger": "synthetic trailing not-applicable role",
            "required_for": [],
            "output_evidence": [],
        }
    )
    errors, warnings = agent_coverage.validate_coverage(coverage, manifest, "case-a", "round-a", round_dir)

    assert specs["theses_similarity"].skill == "thesis-theses-similarity-review"
    assert coverage is not None
    role = next(item for item in coverage["roles"] if item["role"] == "theses_similarity")
    assert role["output_evidence"] == [THESES_SIMILARITY_REVIEW_REL]
    assert role["generator_role"] == "thesis-theses-similarity-review"
    assert role["generator_agent"] == "agent-sim"
    assert errors == []
    assert warnings == []


def test_agent_coverage_rejects_parent_fallback_for_required_fresh_role(tmp_path: Path) -> None:
    round_dir = make_final_round(tmp_path)
    media_input = round_dir / "inputs" / "demo.mp4"
    figure_review = round_dir / "outputs" / "figure_media_review.md"
    media_input.parent.mkdir(parents=True)
    media_input.write_bytes(b"synthetic media\n")
    figure_review.write_text("# Figure/Media Review\n", encoding="utf-8")
    figure_hash = agent_coverage.sha256_file(figure_review)
    manifest = {
        "inputs": [{"path": "inputs/demo.mp4", "kind": "file"}],
        "supporting_work_artifacts": [],
        "artifacts": [
            reviewed_feedback_artifact(round_dir),
            {
                "path": "outputs/figure_media_review.md",
                "artifact_sha256": figure_hash,
                "skills": ["thesis-figure-media-review"],
                "generated_by": [
                    {
                        "role": "thesis-figure-media-review",
                        "agent": "limited_figure_media_parent_review",
                    }
                ],
                "independent_review": {
                    "status": "not_required",
                    "covered_by_artifact": "outputs/feedback_student.md",
                    "used_findings": "Synthetic cautious downstream use.",
                    "evidence_hash": figure_hash,
                },
            },
        ],
    }

    coverage = agent_coverage.build_coverage("case-a", "round-a", round_dir, manifest)
    errors, warnings = agent_coverage.validate_coverage(coverage, manifest, "case-a", "round-a", round_dir)

    assert warnings == []
    assert any(
        "figure_media: required fresh role coverage cannot be satisfied by a parent/fallback/limited generator" in error
        for error in errors
    )


def test_agent_coverage_tracks_silent_similarity_assessment_as_internal_evidence(tmp_path: Path) -> None:
    round_dir = make_final_round(tmp_path)
    for rel_path, content in (
        (THESES_SIMILARITY_REPORT_REL, b"%PDF synthetic\n"),
        (THESES_SIMILARITY_EXTRACTED_TEXT_REL, b"Extracted similarity text.\n"),
        (THESES_SIMILARITY_INTAKE_REL, b'{"matched_passages": [{"passage_id": "passage-1"}]}\n'),
    ):
        path = round_dir / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    refs = [THESES_SIMILARITY_REPORT_REL, THESES_SIMILARITY_EXTRACTED_TEXT_REL, THESES_SIMILARITY_INTAKE_REL]
    write_json(
        round_dir / THESES_SIMILARITY_ASSESSMENT_REL,
        {
            "schema_version": "theses-similarity-assessment-v1",
            "case_id": "case-a",
            "round_id": "round-a",
            "generated_at": "2026-05-12T00:00:00Z",
            "producer_type": "agent",
            "producer_role": "thesis-theses-similarity-review",
            "producer_agent": "agent-sim",
            "authorization_note": "Authorized in current request.",
            "source_refs": refs,
            "source_sha256": {ref: agent_coverage.sha256_file(round_dir / ref) for ref in refs},
            "current_submission_match": "matched",
            "judgments": [
                {
                    "judgment_id": "S1",
                    "source_ids": [1],
                    "passage_refs": [f"{THESES_SIMILARITY_INTAKE_REL}#passage-1"],
                    "basis_refs": [THESES_SIMILARITY_INTAKE_REL],
                    "category": "no_material_concern",
                    "rationale": "Synthetic no-concern structured judgment.",
                    "confidence": "high",
                    "evidence_refs": [THESES_SIMILARITY_EXTRACTED_TEXT_REL],
                    "synthesis_action": "silent",
                    "requires_reviewer_verification": False,
                    "limitations": [],
                }
            ],
            "limitations": [],
        },
    )
    assessment_hash = agent_coverage.sha256_file(round_dir / THESES_SIMILARITY_ASSESSMENT_REL)
    manifest = {
        "inputs": [{"path": THESES_SIMILARITY_REPORT_REL, "kind": "pdf"}],
        "supporting_work_artifacts": [
            {
                "path": THESES_SIMILARITY_ASSESSMENT_REL,
                "kind": "structured_data",
                "artifact_sha256": assessment_hash,
                "schema_version": "theses-similarity-assessment-v1",
                "skills": ["thesis-theses-similarity-review"],
                "producer_role": "thesis-theses-similarity-review",
                "producer_agent": "agent-sim",
                "review_scope": "covered_by_synthesis",
                "independent_review": {
                    "status": "not_required",
                    "covered_by_artifact": "outputs/feedback_student.md",
                    "used_findings": THESES_SIMILARITY_SILENT_USED_FINDINGS,
                    "evidence_hash": assessment_hash,
                },
            }
        ],
        "artifacts": [reviewed_feedback_artifact(round_dir)],
    }

    specs = agent_coverage.inferred_role_specs(round_dir, manifest)
    coverage = agent_coverage.build_coverage("case-a", "round-a", round_dir, manifest)
    errors, warnings = agent_coverage.validate_coverage(coverage, manifest, "case-a", "round-a", round_dir)

    assert specs["theses_similarity"].evidence_path == THESES_SIMILARITY_ASSESSMENT_REL
    assert coverage is not None
    role = next(item for item in coverage["roles"] if item["role"] == "theses_similarity")
    assert role["output_evidence"] == [THESES_SIMILARITY_ASSESSMENT_REL]
    assert role["generator_role"] == "thesis-theses-similarity-review"
    assert role["generator_agent"] == "agent-sim"
    assert role["reviewed_hash"] == assessment_hash
    assert errors == []
    assert warnings == []


def test_agent_coverage_ignores_orphan_theses_similarity_approval_record(tmp_path: Path) -> None:
    round_dir = make_final_round(tmp_path)
    approval = round_dir / THESES_SIMILARITY_REVIEW_APPROVAL_REL
    approval.parent.mkdir(parents=True)
    approval.write_text("{}\n", encoding="utf-8")
    manifest: dict[str, object] = {"inputs": [], "supporting_work_artifacts": [], "artifacts": []}

    specs = agent_coverage.inferred_role_specs(round_dir, manifest)

    assert "theses_similarity" not in specs
