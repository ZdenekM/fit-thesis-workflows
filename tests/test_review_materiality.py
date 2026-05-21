import json
from pathlib import Path

from thesis_review_workflow.cli import check_review_materiality
from thesis_review_workflow.review_materiality import (
    QUANTITATIVE_CLAIMS_REL,
    build_materiality_decisions,
    load_review_materiality_index,
    sha256_file,
    unresolved_required_next_actions,
    validate_materiality_workflow_limitations,
    validate_review_materiality_artifact,
    write_materiality_decisions,
)
from thesis_review_workflow.theses_similarity import (
    THESES_SIMILARITY_ASSESSMENT_REL,
    THESES_SIMILARITY_EXTRACTED_TEXT_REL,
    THESES_SIMILARITY_INTAKE_REL,
    THESES_SIMILARITY_REPORT_REL,
    THESES_SIMILARITY_REVIEW_APPROVAL_REL,
    THESES_SIMILARITY_REVIEW_REL,
    THESES_SIMILARITY_SILENT_USED_FINDINGS,
)


def make_round(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "notes").mkdir(parents=True)
    (round_dir.parents[1] / "case.md").write_text("Reviewer profile: default\n", encoding="utf-8")
    (round_dir.parents[1] / "current-round.txt").write_text("round-a\n", encoding="utf-8")
    return round_dir


def material_roles(round_dir: Path, *, workflow_profile: str = "supervisor_feedback", phase: str = "auto") -> set[str]:
    decisions, errors, _ = build_materiality_decisions(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        workflow_profile=workflow_profile,
        phase=phase,
    )
    assert errors == []
    return {decision.role for decision in decisions if decision.material}


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def quantitative_claims_payload() -> dict[str, object]:
    return {
        "schema_version": "quantitative-claims-v1",
        "case_id": "case-a",
        "round_id": "round-a",
        "generated_at": "2026-05-11T00:00:00Z",
        "producer_type": "human",
        "producer_role": "quantitative-claims-reviewer",
        "producer_agent": None,
        "human_reviewer_note": "Synthetic structured quantitative claims for materiality tests.",
        "claims": [
            {
                "claim_id": "Q1",
                "summary": "Synthetic metric claim.",
                "kind": "metric",
                "status": "needs_context",
                "baseline_status": "missing",
                "practical_context": "weak",
                "unit": "ms",
                "scale_context": "Latency scale is a single synthetic value.",
                "sample_context": "Synthetic result file is the sample context.",
                "practical_magnitude": "Magnitude is not interpreted against a baseline.",
                "overclaim_risk": "moderate",
                "reproducibility_refs": ["inputs/results.csv"],
                "evidence_refs": ["inputs/results.csv"],
                "requires_reviewer_verification": True,
            }
        ],
        "source_refs": ["inputs/results.csv"],
        "limitations": [],
    }


def write_reviewed_supervisor_report_manifest(
    round_dir: Path,
    *,
    supporting_path: str,
    supporting_hash: str,
    used_findings: str,
    supporting_source_sha256: dict[str, str] | None = None,
) -> None:
    final = round_dir / "outputs" / "vedouci_posudek_revidovany.md"
    final.parent.mkdir(parents=True, exist_ok=True)
    final.write_text("# Reviewed Supervisor Report\n", encoding="utf-8")
    final_hash = sha256_file(final)
    write_json(
        round_dir / "work" / "review_manifest.json",
        {
            "schema_version": "review-manifest-v1",
            "case_id": "case-a",
            "round_id": "round-a",
            "inputs": [],
            "supporting_work_artifacts": [
                {
                    "path": supporting_path,
                    "kind": "structured_data",
                    "artifact_sha256": supporting_hash,
                    "skills": ["thesis-theses-similarity-review", "thesis-quantitative-claims-review"],
                    "producer_role": "thesis-theses-similarity-review",
                    "producer_agent": "agent-a",
                    "review_scope": "covered_by_synthesis",
                    "independent_review": {
                        "status": "not_required",
                        "covered_by_artifact": "outputs/vedouci_posudek_revidovany.md",
                        "used_findings": used_findings,
                        "evidence_hash": supporting_hash,
                    },
                    **({"source_sha256": supporting_source_sha256} if supporting_source_sha256 else {}),
                }
            ],
            "artifacts": [
                {
                    "path": "outputs/vedouci_posudek_revidovany.md",
                    "artifact_sha256": final_hash,
                    "skills": ["thesis-supervisor-report-review"],
                    "generated_by": [{"role": "thesis-supervisor-report-review", "agent": "reviewer-a"}],
                    "independent_review": {
                        "status": "reviewed",
                        "reviewer_role": "thesis-supervisor-report-review",
                        "reviewer_agent": "reviewer-b",
                        "reviewed_hash": final_hash,
                    },
                }
            ],
        },
    )


def write_reviewed_opponent_materials_manifest(
    round_dir: Path,
    *,
    supporting_path: str,
    supporting_hash: str,
    used_findings: str,
) -> None:
    final = round_dir / "outputs" / "oponent_podklady_revidovane.md"
    final.parent.mkdir(parents=True, exist_ok=True)
    final.write_text("# Reviewed Opponent Materials\n", encoding="utf-8")
    final_hash = sha256_file(final)
    write_json(
        round_dir / "work" / "review_manifest.json",
        {
            "schema_version": "review-manifest-v1",
            "case_id": "case-a",
            "round_id": "round-a",
            "inputs": [],
            "supporting_work_artifacts": [
                {
                    "path": supporting_path,
                    "kind": "structured_data",
                    "artifact_sha256": supporting_hash,
                    "skills": ["thesis-theses-similarity-review"],
                    "producer_role": "thesis-theses-similarity-review",
                    "producer_agent": "agent-a",
                    "review_scope": "covered_by_synthesis",
                    "independent_review": {
                        "status": "not_required",
                        "covered_by_artifact": "outputs/oponent_podklady_revidovane.md",
                        "used_findings": used_findings,
                        "evidence_hash": supporting_hash,
                    },
                }
            ],
            "artifacts": [
                {
                    "path": "outputs/oponent_podklady_revidovane.md",
                    "artifact_sha256": final_hash,
                    "skills": ["thesis-opponent-materials-review"],
                    "generated_by": [{"role": "thesis-opponent-materials-review", "agent": "reviewer-a"}],
                    "independent_review": {
                        "status": "reviewed",
                        "reviewer_role": "thesis-opponent-materials-review",
                        "reviewer_agent": "reviewer-b",
                        "reviewed_hash": final_hash,
                    },
                }
            ],
        },
    )


def write_silent_theses_similarity_assessment(round_dir: Path) -> None:
    for rel_path, content in (
        (THESES_SIMILARITY_REPORT_REL, b"%PDF synthetic\n"),
        (THESES_SIMILARITY_EXTRACTED_TEXT_REL, b"Synthetic extracted similarity text.\n"),
        (
            THESES_SIMILARITY_INTAKE_REL,
            json.dumps({"matched_passages": [{"passage_id": "passage-1"}]}).encode("utf-8"),
        ),
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
            "source_sha256": {ref: sha256_file(round_dir / ref) for ref in refs},
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


def test_text_only_supervisor_non_final_writes_only_index(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    decisions, errors, phase = build_materiality_decisions(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
    )

    assert errors == []
    assert phase == "non_final"
    assert {decision.role for decision in decisions if decision.material} == set()

    written = write_materiality_decisions(
        round_dir,
        decisions,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
        phase=phase,
        generated_at="2026-05-11T00:00:00Z",
    )

    assert [path.relative_to(round_dir).as_posix() for path in written] == [
        "work/review_materiality/supervisor_feedback/index.json"
    ]
    index = json.loads(
        (round_dir / "work" / "review_materiality" / "supervisor_feedback" / "index.json").read_text(encoding="utf-8")
    )
    assert all(item["coverage_required"] is False for item in index["decisions"])
    assert all(item["fresh_review_required"] is False for item in index["decisions"])
    assert {item["coverage_satisfied_by"] for item in index["decisions"]} == {"typed_no_material_issue"}
    assert not (round_dir / "work" / "review_materiality" / "supervisor_feedback" / "figure_media.json").exists()


def test_materiality_writer_keeps_hash_stable_for_timestamp_only_change(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    decisions, errors, phase = build_materiality_decisions(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
        phase="final",
    )
    assert errors == []

    write_materiality_decisions(
        round_dir,
        decisions,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
        phase=phase,
        generated_at="2026-05-11T00:00:00Z",
    )
    index_path = round_dir / "work" / "review_materiality" / "supervisor_feedback" / "index.json"
    typography_path = round_dir / "work" / "review_materiality" / "supervisor_feedback" / "typography_formal.json"
    before = {path: sha256_file(path) for path in (index_path, typography_path)}

    write_materiality_decisions(
        round_dir,
        decisions,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
        phase=phase,
        generated_at="2026-05-11T00:05:00Z",
    )

    assert {path: sha256_file(path) for path in (index_path, typography_path)} == before


def test_materiality_writer_repairs_invalid_generated_at_metadata(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    decisions, errors, phase = build_materiality_decisions(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
        phase="final",
    )
    assert errors == []
    write_materiality_decisions(
        round_dir,
        decisions,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
        phase=phase,
        generated_at="2026-05-11T00:00:00Z",
    )
    index_path = round_dir / "work" / "review_materiality" / "supervisor_feedback" / "index.json"
    typography_rel = "work/review_materiality/supervisor_feedback/typography_formal.json"
    typography_path = round_dir / typography_rel
    index_payload = json.loads(index_path.read_text(encoding="utf-8"))
    index_payload["generated_at"] = ""
    index_payload["decisions"][0]["generated_at"] = ""
    write_json(index_path, index_payload)
    typography_payload = json.loads(typography_path.read_text(encoding="utf-8"))
    typography_payload["generated_at"] = ""
    write_json(typography_path, typography_payload)

    write_materiality_decisions(
        round_dir,
        decisions,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
        phase=phase,
        generated_at="2026-05-11T00:05:00Z",
    )

    repaired_index = json.loads(index_path.read_text(encoding="utf-8"))
    repaired_typography = json.loads(typography_path.read_text(encoding="utf-8"))
    assert repaired_index["generated_at"] == "2026-05-11T00:05:00Z"
    assert repaired_index["decisions"][0]["generated_at"] == "2026-05-11T00:05:00Z"
    assert repaired_typography["generated_at"] == "2026-05-11T00:05:00Z"
    _, index_errors = load_review_materiality_index(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
    )
    assert index_errors == []
    assert (
        validate_review_materiality_artifact(
            round_dir,
            typography_rel,
            case_id="case-a",
            round_id="round-a",
        )
        == []
    )


def test_final_supervisor_phase_marks_typography_material(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)

    roles = material_roles(round_dir, phase="final")

    assert "typography_formal" in roles
    assert "literature_citation" not in roles


def test_supervisor_auto_phase_does_not_route_from_free_text_notes(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    (round_dir / "notes" / "supervisor-intake.md").write_text(
        "Stav prace podle vedouciho: finalni kontrola. Repo: https://github.com/example/project\n",
        encoding="utf-8",
    )

    decisions, errors, phase = build_materiality_decisions(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
    )

    assert errors == []
    assert phase == "non_final"
    assert "typography_formal" not in {decision.role for decision in decisions if decision.material}
    assert "github_intake" not in {decision.role for decision in decisions if decision.material}


def test_code_workspace_marks_code_roles_without_optional_packet_files(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    (round_dir / "work").mkdir()
    (round_dir / "work" / "code_workspace.md").write_text("Prepared workspace.\n", encoding="utf-8")

    decisions, errors, phase = build_materiality_decisions(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
    )
    written = write_materiality_decisions(
        round_dir,
        decisions,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
        phase=phase,
        generated_at="2026-05-11T00:00:00Z",
    )

    assert errors == []
    assert {decision.role for decision in decisions if decision.material} == {"code_consistency", "code_quality"}
    assert [path.relative_to(round_dir).as_posix() for path in written] == [
        "work/review_materiality/supervisor_feedback/index.json"
    ]


def test_video_media_inventory_creates_narrow_figure_materiality(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    path = round_dir / "work" / "media_presence_inventory.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "visual-media-inventory-v1",
                "path": "inputs/demo.mp4",
                "category": "video",
                "state": "present-uninspected",
                "inspection_depth": "metadata-only",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    decisions, errors, phase = build_materiality_decisions(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
    )
    written = write_materiality_decisions(
        round_dir,
        decisions,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
        phase=phase,
        generated_at="2026-05-11T00:00:00Z",
    )

    assert errors == []
    figure = next(decision for decision in decisions if decision.role == "figure_media")
    assert figure.material
    assert figure.scope == "presentation_demo_boundary"
    assert (round_dir / "work" / "review_materiality" / "supervisor_feedback" / "figure_media.json") in written
    assert (
        validate_review_materiality_artifact(
            round_dir,
            "work/review_materiality/supervisor_feedback/figure_media.json",
            case_id="case-a",
            round_id="round-a",
        )
        == []
    )


def test_image_media_inventory_creates_visual_review_materiality(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    path = round_dir / "work" / "media_presence_inventory.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "visual-media-inventory-v1",
                "path": "inputs/result.png",
                "category": "image",
                "state": "present-uninspected",
                "inspection_depth": "metadata-only",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    decisions, errors, _ = build_materiality_decisions(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
    )

    assert errors == []
    figure = next(decision for decision in decisions if decision.role == "figure_media")
    assert figure.material
    assert figure.scope == "visual_media_review"


def test_opponent_profile_marks_report_defensibility_roles(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)

    decisions, errors, phase = build_materiality_decisions(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="opponent_review",
    )

    assert errors == []
    assert phase == "final"
    by_role = {decision.role: decision for decision in decisions}
    assert by_role["typography_formal"].material
    assert by_role["literature_citation"].material
    assert "IS-item impact" in by_role["literature_citation"].impact


def test_supervisor_report_profile_uses_final_phase_and_report_impacts(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)

    decisions, errors, phase = build_materiality_decisions(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_report",
        requested_roles=("literature_citation",),
    )

    assert errors == []
    assert phase == "final"
    by_role = {decision.role: decision for decision in decisions}
    assert by_role["literature_citation"].material
    assert "supervisor report field" in by_role["literature_citation"].impact
    assert not by_role["typography_formal"].material


def test_quantitative_claims_and_evaluation_tables_are_material_without_text_matching(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    (round_dir / "inputs").mkdir()
    (round_dir / "inputs" / "results.csv").write_text("metric,value\nlatency,42\n", encoding="utf-8")
    write_json(round_dir / "work" / "quantitative_claims.json", quantitative_claims_payload())

    roles = material_roles(round_dir)

    assert "quantitative_claims" in roles


def test_material_quantitative_claims_create_next_action_when_handoff_missing(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    (round_dir / "inputs").mkdir()
    (round_dir / "inputs" / "results.csv").write_text("metric,value\nlatency,42\n", encoding="utf-8")
    decisions, errors, phase = build_materiality_decisions(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
    )
    assert errors == []

    write_materiality_decisions(
        round_dir,
        decisions,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
        phase=phase,
        generated_at="2026-05-11T00:00:00Z",
    )

    index = json.loads(
        (round_dir / "work" / "review_materiality" / "supervisor_feedback" / "index.json").read_text(encoding="utf-8")
    )
    [action] = index["next_actions"]
    assert action["role"] == "quantitative_claims"
    assert action["required_artifact_path"] == "work/quantitative_claims.json"
    assert action["status"] == "unresolved"
    assert action["source_sha256"]["inputs/results.csv"]
    unresolved, errors = unresolved_required_next_actions(
        round_dir,
        workflow_profile="supervisor_feedback",
        case_id="case-a",
        round_id="round-a",
    )
    assert errors == []
    assert [item["role"] for item in unresolved] == ["quantitative_claims"]


def test_theses_similarity_report_creates_required_next_action_until_review_exists(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    report = round_dir / THESES_SIMILARITY_REPORT_REL
    report.parent.mkdir(parents=True)
    report.write_bytes(b"%PDF synthetic\n")
    decisions, errors, phase = build_materiality_decisions(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="opponent_review",
    )

    assert errors == []
    by_role = {decision.role: decision for decision in decisions}
    assert by_role["theses_similarity"].material
    assert by_role["theses_similarity"].source_refs == (THESES_SIMILARITY_REPORT_REL,)

    write_materiality_decisions(
        round_dir,
        decisions,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="opponent_review",
        phase=phase,
        generated_at="2026-05-12T00:00:00Z",
    )
    index = json.loads(
        (round_dir / "work" / "review_materiality" / "opponent_review" / "index.json").read_text(encoding="utf-8")
    )
    theses_actions = [item for item in index["next_actions"] if item["role"] == "theses_similarity"]

    assert len(theses_actions) == 1
    assert theses_actions[0]["required_artifact_path"] == THESES_SIMILARITY_REVIEW_REL
    assert theses_actions[0]["skill"] == "thesis-theses-similarity-review"


def test_theses_similarity_approval_record_alone_does_not_trigger_materiality(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    approval = round_dir / THESES_SIMILARITY_REVIEW_APPROVAL_REL
    approval.parent.mkdir(parents=True)
    approval.write_text("{}\n", encoding="utf-8")

    decisions, errors, _ = build_materiality_decisions(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
    )

    assert errors == []
    assert not next(decision for decision in decisions if decision.role == "theses_similarity").material


def test_theses_similarity_final_review_without_assessment_stays_unresolved(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    for rel_path in (THESES_SIMILARITY_REPORT_REL, THESES_SIMILARITY_EXTRACTED_TEXT_REL, THESES_SIMILARITY_INTAKE_REL):
        path = round_dir / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n", encoding="utf-8")
    (round_dir / THESES_SIMILARITY_REVIEW_REL).parent.mkdir(parents=True)
    (round_dir / THESES_SIMILARITY_REVIEW_REL).write_text("# Theses.cz Similarity Review\n", encoding="utf-8")
    decisions, errors, phase = build_materiality_decisions(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_report",
    )
    assert errors == []

    write_materiality_decisions(
        round_dir,
        decisions,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_report",
        phase=phase,
        generated_at="2026-05-12T00:00:00Z",
    )

    unresolved, errors = unresolved_required_next_actions(
        round_dir,
        workflow_profile="supervisor_report",
        case_id="case-a",
        round_id="round-a",
    )

    assert errors == []
    assert any(item["role"] == "theses_similarity" for item in unresolved)
    assert any(
        THESES_SIMILARITY_ASSESSMENT_REL in limitation
        for item in unresolved
        if item["role"] == "theses_similarity"
        for limitation in item["limitations"]
    )


def test_final_supervisor_report_silent_similarity_assessment_needs_synthesis_marker(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    write_silent_theses_similarity_assessment(round_dir)
    decisions, errors, phase = build_materiality_decisions(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_report",
    )
    assert errors == []

    write_materiality_decisions(
        round_dir,
        decisions,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_report",
        phase=phase,
        generated_at="2026-05-12T00:00:00Z",
    )

    index_path = round_dir / "work" / "review_materiality" / "supervisor_report" / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    assert [item["role"] for item in index["next_actions"]] == ["theses_similarity"]
    [theses_action] = index["next_actions"]
    assert theses_action["state"] == "silent_no_concern_waiting_for_reviewed_synthesis"
    assert theses_action["required_artifact_path"] == "outputs/vedouci_posudek_revidovany.md"
    assert theses_action["skill"] == "thesis-supervisor-report-review"
    assert "waiting for reviewed synthesis" in theses_action["reason"]
    assert THESES_SIMILARITY_SILENT_USED_FINDINGS in theses_action["command"]
    theses = next(item for item in index["decisions"] if item["role"] == "theses_similarity")
    assert theses["fresh_review_required"] is False
    assert theses["coverage_satisfied_by"] == "not_satisfied"
    assert theses["coverage_state"] == "silent_no_concern_waiting_for_reviewed_synthesis"

    assessment_path = round_dir / THESES_SIMILARITY_ASSESSMENT_REL
    write_reviewed_supervisor_report_manifest(
        round_dir,
        supporting_path=THESES_SIMILARITY_ASSESSMENT_REL,
        supporting_hash=sha256_file(assessment_path),
        used_findings=THESES_SIMILARITY_SILENT_USED_FINDINGS,
    )
    write_materiality_decisions(
        round_dir,
        decisions,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_report",
        phase=phase,
        generated_at="2026-05-12T00:01:00Z",
    )

    index = json.loads(index_path.read_text(encoding="utf-8"))
    theses = next(item for item in index["decisions"] if item["role"] == "theses_similarity")
    assert theses["coverage_required"] is True
    assert theses["fresh_review_required"] is False
    assert theses["coverage_satisfied_by"] == "silent_internal_evidence"
    assert theses["coverage_state"] == "silent_internal_evidence"
    assert index["next_actions"] == []
    unresolved, errors = unresolved_required_next_actions(
        round_dir,
        workflow_profile="supervisor_report",
        case_id="case-a",
        round_id="round-a",
    )
    assert errors == []
    assert unresolved == []


def test_final_opponent_review_silent_similarity_assessment_needs_synthesis_marker(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    write_silent_theses_similarity_assessment(round_dir)
    decisions, errors, phase = build_materiality_decisions(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="opponent_review",
    )
    assert errors == []

    write_materiality_decisions(
        round_dir,
        decisions,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="opponent_review",
        phase=phase,
        generated_at="2026-05-12T00:00:00Z",
    )

    index_path = round_dir / "work" / "review_materiality" / "opponent_review" / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    assert [item["role"] for item in index["next_actions"]] == ["theses_similarity"]
    [theses_action] = index["next_actions"]
    assert theses_action["state"] == "silent_no_concern_waiting_for_reviewed_synthesis"
    assert theses_action["required_artifact_path"] == "outputs/oponent_podklady_revidovane.md"
    assert theses_action["skill"] == "thesis-opponent-materials-review"
    theses = next(item for item in index["decisions"] if item["role"] == "theses_similarity")
    assert theses["fresh_review_required"] is False
    assert theses["coverage_satisfied_by"] == "not_satisfied"
    assert theses["coverage_state"] == "silent_no_concern_waiting_for_reviewed_synthesis"

    assessment_path = round_dir / THESES_SIMILARITY_ASSESSMENT_REL
    write_reviewed_opponent_materials_manifest(
        round_dir,
        supporting_path=THESES_SIMILARITY_ASSESSMENT_REL,
        supporting_hash=sha256_file(assessment_path),
        used_findings=THESES_SIMILARITY_SILENT_USED_FINDINGS,
    )
    write_materiality_decisions(
        round_dir,
        decisions,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="opponent_review",
        phase=phase,
        generated_at="2026-05-12T00:01:00Z",
    )

    index = json.loads(index_path.read_text(encoding="utf-8"))
    theses = next(item for item in index["decisions"] if item["role"] == "theses_similarity")
    assert theses["coverage_satisfied_by"] == "silent_internal_evidence"
    assert theses["coverage_state"] == "silent_internal_evidence"
    assert index["next_actions"] == []
    unresolved, errors = unresolved_required_next_actions(
        round_dir,
        workflow_profile="opponent_review",
        case_id="case-a",
        round_id="round-a",
    )
    assert errors == []
    assert unresolved == []


def test_supervisor_feedback_silent_similarity_assessment_still_requires_role_review(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    write_silent_theses_similarity_assessment(round_dir)
    decisions, errors, phase = build_materiality_decisions(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
    )
    assert errors == []

    write_materiality_decisions(
        round_dir,
        decisions,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
        phase=phase,
        generated_at="2026-05-12T00:00:00Z",
    )

    index_path = round_dir / "work" / "review_materiality" / "supervisor_feedback" / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    [theses_action] = [item for item in index["next_actions"] if item["role"] == "theses_similarity"]
    theses = next(item for item in index["decisions"] if item["role"] == "theses_similarity")
    assert theses_action["state"] == "present_not_synthesis_covered"
    assert theses_action["required_artifact_path"] == THESES_SIMILARITY_REVIEW_REL
    assert theses_action["skill"] == "thesis-theses-similarity-review"
    assert theses["fresh_review_required"] is True
    assert theses["coverage_satisfied_by"] == "not_satisfied"
    assert theses["coverage_state"] == "not_satisfied"


def test_material_quantitative_next_action_resolves_after_current_handoff_exists(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    (round_dir / "inputs").mkdir()
    (round_dir / "inputs" / "results.csv").write_text("metric,value\nlatency,42\n", encoding="utf-8")
    decisions, errors, phase = build_materiality_decisions(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
    )
    assert errors == []
    write_materiality_decisions(
        round_dir,
        decisions,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
        phase=phase,
        generated_at="2026-05-11T00:00:00Z",
    )
    write_json(round_dir / "work" / "quantitative_claims.json", quantitative_claims_payload())

    unresolved, errors = unresolved_required_next_actions(
        round_dir,
        workflow_profile="supervisor_feedback",
        case_id="case-a",
        round_id="round-a",
    )

    assert errors == []
    assert unresolved == []


def test_material_quantitative_current_handoff_splits_coverage_from_fresh_review(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    (round_dir / "inputs").mkdir()
    (round_dir / "inputs" / "results.csv").write_text("metric,value\nlatency,42\n", encoding="utf-8")
    write_json(round_dir / "work" / "quantitative_claims.json", quantitative_claims_payload())
    decisions, errors, phase = build_materiality_decisions(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
    )
    assert errors == []

    write_materiality_decisions(
        round_dir,
        decisions,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
        phase=phase,
        generated_at="2026-05-11T00:00:00Z",
    )

    index = json.loads(
        (round_dir / "work" / "review_materiality" / "supervisor_feedback" / "index.json").read_text(encoding="utf-8")
    )
    quantitative = next(item for item in index["decisions"] if item["role"] == "quantitative_claims")
    assert quantitative["coverage_required"] is True
    assert quantitative["fresh_review_required"] is False
    assert quantitative["coverage_satisfied_by"] == "current_handoff"
    assert quantitative["coverage_state"] == "current_handoff"
    assert index["next_actions"] == []


def test_final_supervisor_report_quantitative_handoff_requires_review_or_synthesis(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    (round_dir / "inputs").mkdir()
    (round_dir / "inputs" / "results.csv").write_text("metric,value\nlatency,42\n", encoding="utf-8")
    write_json(round_dir / "work" / "quantitative_claims.json", quantitative_claims_payload())
    decisions, errors, phase = build_materiality_decisions(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_report",
    )
    assert errors == []

    write_materiality_decisions(
        round_dir,
        decisions,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_report",
        phase=phase,
        generated_at="2026-05-11T00:00:00Z",
    )

    index_path = round_dir / "work" / "review_materiality" / "supervisor_report" / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    quantitative = next(item for item in index["decisions"] if item["role"] == "quantitative_claims")
    assert quantitative["coverage_required"] is True
    assert quantitative["fresh_review_required"] is True
    assert quantitative["coverage_satisfied_by"] == "not_satisfied"
    assert [item["role"] for item in index["next_actions"]] == ["quantitative_claims"]

    quantitative_path = round_dir / "work" / "quantitative_claims.json"
    write_reviewed_supervisor_report_manifest(
        round_dir,
        supporting_path="work/quantitative_claims.json",
        supporting_hash=sha256_file(quantitative_path),
        used_findings="quantitative_claims:covered_by_reviewed_supervisor_report",
    )
    write_materiality_decisions(
        round_dir,
        decisions,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_report",
        phase=phase,
        generated_at="2026-05-11T00:01:00Z",
    )

    index = json.loads(index_path.read_text(encoding="utf-8"))
    quantitative = next(item for item in index["decisions"] if item["role"] == "quantitative_claims")
    assert quantitative["fresh_review_required"] is False
    assert quantitative["coverage_satisfied_by"] == "current_synthesis_covered_artifact"
    assert index["next_actions"] == []
    unresolved, errors = unresolved_required_next_actions(
        round_dir,
        workflow_profile="supervisor_report",
        case_id="case-a",
        round_id="round-a",
    )
    assert errors == []
    assert unresolved == []


def test_final_supervisor_report_quantitative_synthesis_coverage_tracks_supporting_source_hashes(
    tmp_path: Path,
) -> None:
    round_dir = make_round(tmp_path)
    (round_dir / "inputs").mkdir()
    source = round_dir / "inputs" / "results.csv"
    source.write_text("metric,value\nlatency,42\n", encoding="utf-8")
    write_json(round_dir / "work" / "quantitative_claims.json", quantitative_claims_payload())
    quantitative_path = round_dir / "work" / "quantitative_claims.json"
    write_reviewed_supervisor_report_manifest(
        round_dir,
        supporting_path="work/quantitative_claims.json",
        supporting_hash=sha256_file(quantitative_path),
        used_findings="quantitative_claims:covered_by_reviewed_supervisor_report",
        supporting_source_sha256={"inputs/results.csv": sha256_file(source)},
    )
    decisions, errors, phase = build_materiality_decisions(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_report",
    )
    assert errors == []

    source.write_text("metric,value\nlatency,99\n", encoding="utf-8")
    write_materiality_decisions(
        round_dir,
        decisions,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_report",
        phase=phase,
        generated_at="2026-05-11T00:01:00Z",
    )

    index = json.loads(
        (round_dir / "work" / "review_materiality" / "supervisor_report" / "index.json").read_text(encoding="utf-8")
    )
    quantitative = next(item for item in index["decisions"] if item["role"] == "quantitative_claims")
    assert quantitative["fresh_review_required"] is True
    assert quantitative["coverage_satisfied_by"] == "not_satisfied"
    assert [item["role"] for item in index["next_actions"]] == ["quantitative_claims"]
    assert any(
        "manifest source hash is stale for inputs/results.csv" in item
        for item in index["next_actions"][0]["limitations"]
    )


def test_materiality_index_rejects_missing_source_hash_for_material_decision(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    (round_dir / "inputs").mkdir()
    (round_dir / "inputs" / "results.csv").write_text("metric,value\nlatency,42\n", encoding="utf-8")
    decisions, errors, phase = build_materiality_decisions(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
    )
    assert errors == []
    write_materiality_decisions(
        round_dir,
        decisions,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
        phase=phase,
        generated_at="2026-05-11T00:00:00Z",
    )
    index_path = round_dir / "work" / "review_materiality" / "supervisor_feedback" / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    quantitative = next(item for item in index["decisions"] if item["role"] == "quantitative_claims")
    quantitative["source_sha256"] = {}
    index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")

    unresolved, errors = unresolved_required_next_actions(
        round_dir,
        workflow_profile="supervisor_feedback",
        case_id="case-a",
        round_id="round-a",
    )

    assert unresolved == []
    assert any("source_sha256 missing hash for source_ref inputs/results.csv" in error for error in errors)


def test_materiality_index_rejects_inconsistent_coverage_state(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    (round_dir / "inputs").mkdir()
    (round_dir / "inputs" / "results.csv").write_text("metric,value\nlatency,42\n", encoding="utf-8")
    write_json(round_dir / "work" / "quantitative_claims.json", quantitative_claims_payload())
    decisions, errors, phase = build_materiality_decisions(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
    )
    assert errors == []
    write_materiality_decisions(
        round_dir,
        decisions,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
        phase=phase,
        generated_at="2026-05-11T00:00:00Z",
    )
    index_path = round_dir / "work" / "review_materiality" / "supervisor_feedback" / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    quantitative = next(item for item in index["decisions"] if item["role"] == "quantitative_claims")
    quantitative["coverage_state"] = "current_reviewed_artifact"
    index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")

    unresolved, errors = unresolved_required_next_actions(
        round_dir,
        workflow_profile="supervisor_feedback",
        case_id="case-a",
        round_id="round-a",
    )

    assert unresolved == []
    assert any("coverage_state must match coverage_satisfied_by=current_handoff" in error for error in errors)


def test_materiality_index_reports_contradictory_stored_next_action(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    (round_dir / "inputs").mkdir()
    (round_dir / "inputs" / "results.csv").write_text("metric,value\nlatency,42\n", encoding="utf-8")
    write_json(round_dir / QUANTITATIVE_CLAIMS_REL, quantitative_claims_payload())
    decisions, errors, phase = build_materiality_decisions(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
    )
    assert errors == []
    write_materiality_decisions(
        round_dir,
        decisions,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
        phase=phase,
        generated_at="2026-05-12T00:00:00Z",
    )
    index_path = round_dir / "work" / "review_materiality" / "supervisor_feedback" / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    assert index["next_actions"] == []
    index["next_actions"].append(
        {
            "role": "quantitative_claims",
            "workflow_profile": "supervisor_feedback",
            "status": "unresolved",
            "severity": "required",
            "required_artifact_path": QUANTITATIVE_CLAIMS_REL.as_posix(),
            "reason": "Synthetic stale action.",
            "command": "Run an authorized thesis-quantitative-claims-review, then check-evaluation-claims.",
            "skill": "thesis-quantitative-claims-review",
            "source_refs": ["inputs/results.csv"],
            "source_sha256": {"inputs/results.csv": sha256_file(round_dir / "inputs" / "results.csv")},
            "typed_limitation_scope": "quantitative_claims",
            "limitations": [],
            "state": "missing_artifact",
        }
    )
    index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")

    unresolved, errors = unresolved_required_next_actions(
        round_dir,
        workflow_profile="supervisor_feedback",
        case_id="case-a",
        round_id="round-a",
    )

    assert unresolved == []
    assert any(
        "next_actions item 1 for quantitative_claims contradicts decision coverage_state=current_handoff" in error
        for error in errors
    )


def test_materiality_index_ignores_resolved_stored_next_action(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    (round_dir / "inputs").mkdir()
    (round_dir / "inputs" / "results.csv").write_text("metric,value\nlatency,42\n", encoding="utf-8")
    write_json(round_dir / QUANTITATIVE_CLAIMS_REL, quantitative_claims_payload())
    decisions, errors, phase = build_materiality_decisions(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
    )
    assert errors == []
    write_materiality_decisions(
        round_dir,
        decisions,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
        phase=phase,
        generated_at="2026-05-12T00:00:00Z",
    )
    index_path = round_dir / "work" / "review_materiality" / "supervisor_feedback" / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["next_actions"].append(
        {
            "role": "quantitative_claims",
            "workflow_profile": "supervisor_feedback",
            "status": "resolved_by_artifact",
            "severity": "required",
            "required_artifact_path": QUANTITATIVE_CLAIMS_REL.as_posix(),
            "reason": "Synthetic historical action.",
            "command": "Run an authorized thesis-quantitative-claims-review, then check-evaluation-claims.",
            "skill": "thesis-quantitative-claims-review",
            "source_refs": ["inputs/results.csv"],
            "source_sha256": {"inputs/results.csv": sha256_file(round_dir / "inputs" / "results.csv")},
            "typed_limitation_scope": "quantitative_claims",
            "limitations": [],
            "state": "missing_artifact",
        }
    )
    index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")

    unresolved, errors = unresolved_required_next_actions(
        round_dir,
        workflow_profile="supervisor_feedback",
        case_id="case-a",
        round_id="round-a",
    )

    assert unresolved == []
    assert errors == []


def test_materiality_index_reports_same_role_next_action_state_drift(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    report = round_dir / THESES_SIMILARITY_REPORT_REL
    report.parent.mkdir(parents=True)
    report.write_bytes(b"%PDF synthetic\n")
    decisions, errors, phase = build_materiality_decisions(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="opponent_review",
    )
    assert errors == []
    write_materiality_decisions(
        round_dir,
        decisions,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="opponent_review",
        phase=phase,
        generated_at="2026-05-12T00:00:00Z",
    )
    write_silent_theses_similarity_assessment(round_dir)

    unresolved, errors = unresolved_required_next_actions(
        round_dir,
        workflow_profile="opponent_review",
        case_id="case-a",
        round_id="round-a",
    )

    assert [item["role"] for item in unresolved] == ["theses_similarity"]
    assert unresolved[0]["state"] == "silent_no_concern_waiting_for_reviewed_synthesis"
    assert any(
        "next_actions item 1 for theses_similarity is stale: stored state=missing_artifact "
        "current state=silent_no_concern_waiting_for_reviewed_synthesis" in error
        for error in errors
    )


def test_material_quantitative_next_action_stays_unresolved_when_source_hash_changes(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    (round_dir / "inputs").mkdir()
    source = round_dir / "inputs" / "results.csv"
    source.write_text("metric,value\nlatency,42\n", encoding="utf-8")
    decisions, errors, phase = build_materiality_decisions(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
    )
    assert errors == []
    write_materiality_decisions(
        round_dir,
        decisions,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
        phase=phase,
        generated_at="2026-05-11T00:00:00Z",
    )
    write_json(round_dir / "work" / "quantitative_claims.json", quantitative_claims_payload())
    source.write_text("metric,value\nlatency,99\n", encoding="utf-8")

    unresolved, errors = unresolved_required_next_actions(
        round_dir,
        workflow_profile="supervisor_feedback",
        case_id="case-a",
        round_id="round-a",
    )

    assert errors == []
    assert unresolved[0]["role"] == "quantitative_claims"
    assert "stored materiality source hash is stale" in unresolved[0]["reason"]


def test_material_github_intake_next_action_resolves_with_typed_limitation(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    github_source = round_dir / "inputs" / "github" / "prs" / "owner__project__pr-1" / "pr.meta.json"
    github_source.parent.mkdir(parents=True)
    github_source.write_text("{}\n", encoding="utf-8")
    write_json(
        round_dir / "work" / "review_manifest.json",
        {
            "schema_version": "review-manifest-v1",
            "case_id": "case-a",
            "round_id": "round-a",
            "workflow_limitations": [
                {
                    "type": "out_of_scope_for_round",
                    "scope": "github_intake",
                    "trigger": "materiality_next_action",
                    "required_for": ["supervisor_feedback"],
                    "description": "GitHub evidence is out of scope for this round.",
                    "impact": "Use submitted archive only.",
                    "status": "closed",
                    "accepted_by": "test-reviewer",
                }
            ],
        },
    )

    decisions, errors, phase = build_materiality_decisions(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
    )
    assert errors == []
    write_materiality_decisions(
        round_dir,
        decisions,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
        phase=phase,
        generated_at="2026-05-11T00:00:00Z",
    )

    index = json.loads(
        (round_dir / "work" / "review_materiality" / "supervisor_feedback" / "index.json").read_text(encoding="utf-8")
    )
    assert index["next_actions"] == []
    github = next(item for item in index["decisions"] if item["role"] == "github_intake")
    assert github["coverage_required"] is True
    assert github["fresh_review_required"] is False
    assert github["coverage_satisfied_by"] == "typed_limitation"
    assert github["coverage_state"] == "typed_limitation"


def test_materiality_limitation_requires_typed_contract() -> None:
    errors = validate_materiality_workflow_limitations(
        [
            {
                "scope": "github_intake",
                "description": "Too weak.",
                "impact": "Ambiguous.",
                "status": "closed",
            }
        ],
        workflow_profile="supervisor_feedback",
    )

    assert any("trigger must be materiality_next_action" in error for error in errors)
    assert any("required_for must be a non-empty list" in error for error in errors)
    assert any("accepted_by or reviewer_role" in error for error in errors)


def test_material_github_intake_marks_stale_source_hash(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    source = round_dir / "inputs" / "github" / "prs" / "owner__project__pr-1" / "pr.meta.json"
    source.parent.mkdir(parents=True)
    source.write_text("{}\n", encoding="utf-8")
    output = round_dir / "outputs" / "github_code_intake.md"
    output.parent.mkdir()
    output.write_text("# GitHub intake\n", encoding="utf-8")
    write_json(
        round_dir / "work" / "review_manifest.json",
        {
            "schema_version": "review-manifest-v1",
            "case_id": "case-a",
            "round_id": "round-a",
            "workflow_limitations": [],
            "artifacts": [
                {
                    "path": "outputs/github_code_intake.md",
                    "source_sha256": {"inputs/github/prs/owner__project__pr-1/pr.meta.json": "0" * 64},
                }
            ],
        },
    )

    decisions, errors, phase = build_materiality_decisions(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
    )
    assert errors == []
    write_materiality_decisions(
        round_dir,
        decisions,
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
        phase=phase,
        generated_at="2026-05-11T00:00:00Z",
    )

    unresolved, errors = unresolved_required_next_actions(
        round_dir,
        workflow_profile="supervisor_feedback",
        case_id="case-a",
        round_id="round-a",
    )
    assert errors == []
    assert unresolved[0]["role"] == "github_intake"
    assert "source hash is stale" in unresolved[0]["reason"]


def test_cli_writes_and_prunes_role_files(tmp_path: Path, monkeypatch, capsys) -> None:
    round_dir = make_round(tmp_path)
    root = round_dir.parents[3]
    monkeypatch.setattr(check_review_materiality, "repo_root", lambda: root)

    assert (
        check_review_materiality.main(
            [
                "scripts/check-review-materiality",
                "--workflow",
                "supervisor_feedback",
                "--phase",
                "final",
                "case-a",
                "round-a",
            ]
        )
        == 0
    )
    assert (round_dir / "work" / "review_materiality" / "supervisor_feedback" / "typography_formal.json").is_file()

    assert (
        check_review_materiality.main(
            [
                "scripts/check-review-materiality",
                "--workflow",
                "supervisor_feedback",
                "--phase",
                "non_final",
                "case-a",
                "round-a",
            ]
        )
        == 0
    )

    output = capsys.readouterr().out
    assert "Review materiality check passed" in output
    assert not (round_dir / "work" / "review_materiality" / "supervisor_feedback" / "typography_formal.json").exists()
