import json
from pathlib import Path

from thesis_review_workflow.cli import check_review_materiality
from thesis_review_workflow.review_materiality import (
    build_materiality_decisions,
    unresolved_required_next_actions,
    validate_materiality_workflow_limitations,
    validate_review_materiality_artifact,
    write_materiality_decisions,
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

    assert [path.relative_to(round_dir).as_posix() for path in written] == ["work/review_materiality/index.json"]
    assert not (round_dir / "work" / "review_materiality" / "figure_media.json").exists()


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
    assert [path.relative_to(round_dir).as_posix() for path in written] == ["work/review_materiality/index.json"]


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
    assert (round_dir / "work" / "review_materiality" / "figure_media.json") in written
    assert (
        validate_review_materiality_artifact(
            round_dir,
            "work/review_materiality/figure_media.json",
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

    index = json.loads((round_dir / "work" / "review_materiality" / "index.json").read_text(encoding="utf-8"))
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

    index = json.loads((round_dir / "work" / "review_materiality" / "index.json").read_text(encoding="utf-8"))
    assert index["next_actions"] == []


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
    assert (round_dir / "work" / "review_materiality" / "typography_formal.json").is_file()

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
    assert not (round_dir / "work" / "review_materiality" / "typography_formal.json").exists()
