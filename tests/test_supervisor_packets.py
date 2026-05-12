import json
from pathlib import Path

from thesis_review_workflow.review_materiality import MaterialityDecision, write_materiality_decisions
from thesis_review_workflow.supervisor_packets import PACKET_ROLES, generate_packets, render_packet
from thesis_review_workflow.theses_similarity import THESES_SIMILARITY_REPORT_REL, THESES_SIMILARITY_REVIEW_REL

DEADLINE_CONTEXT = """Supervisor deadline context
Case: case-a
Round: round-a
Academic year: 2025/2026
Work type: BP
Official deadline: 2026-05-13 (2 days until deadline)
Calibration: final week; prioritize blockers, assignment coverage, technical truth, and submission artifacts
"""


def make_round(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    round_dir = repo_root / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "notes").mkdir(parents=True)
    (round_dir / "inputs").mkdir()
    (round_dir / "extracted").mkdir()
    (round_dir / "work").mkdir()
    (repo_root / "profiles").mkdir(parents=True)
    (repo_root / "profiles" / "default.md").write_text("# Default profile\n", encoding="utf-8")
    (round_dir.parents[1] / "case.md").write_text(
        "Work type: BP\nAcademic year: 2025/2026\nReviewer profile: default\n", encoding="utf-8"
    )
    (round_dir / "notes" / "assignment.md").write_text(
        "# Assignment\n\n"
        "## Formal Assignment Artifacts\n\n"
        "- Synthetic assignment.\n\n"
        "## Formal Assignment Text Or Summary\n\n"
        "- Implement and evaluate a helper.\n\n"
        "## Private Assignment Notes For Student\n\n"
        "- Focus on defensible evidence.\n",
        encoding="utf-8",
    )
    return round_dir


def write_materiality(round_dir: Path, role: str) -> None:
    write_materiality_decisions(
        round_dir,
        [
            MaterialityDecision(
                role=role,
                recommendation="material",
                scope="explicit_request",
                impact="student-action priority",
                reason="test materiality decision",
                source_refs=(f"operator-request:{role}",),
            )
        ],
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
        phase="non_final",
        generated_at="2026-05-11T00:00:00Z",
    )


def write_quantitative_claims(round_dir: Path) -> None:
    (round_dir / "extracted").mkdir(exist_ok=True)
    (round_dir / "extracted" / "thesis.txt").write_text("Metric claim.\n", encoding="utf-8")
    payload = {
        "schema_version": "quantitative-claims-v1",
        "case_id": "case-a",
        "round_id": "round-a",
        "generated_at": "2026-05-11T00:00:00Z",
        "producer_type": "agent",
        "producer_role": "quantitative-claims-reviewer",
        "producer_agent": "agent-a",
        "authorization_note": "Current request explicitly authorized agents.",
        "source_refs": ["extracted/thesis.txt"],
        "claims": [
            {
                "claim_id": "Q1",
                "summary": "Reported percentage lacks a baseline.",
                "kind": "metric",
                "status": "needs_context",
                "unit": "%",
                "baseline_status": "missing",
                "practical_context": "weak",
                "scale_context": "Percentage denominator is not explicit.",
                "sample_context": "Sample size is not stated.",
                "practical_magnitude": "Magnitude is not interpreted against a user-visible impact.",
                "overclaim_risk": "moderate",
                "reproducibility_refs": [],
                "evidence_refs": ["extracted/thesis.txt"],
                "requires_reviewer_verification": True,
            }
        ],
        "limitations": [],
    }
    path = round_dir / "work" / "quantitative_claims.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_generate_supervisor_packets_starts_with_mandatory_base_only(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)

    written = generate_packets(
        "case-a",
        "round-a",
        "2026-05-11T00:00:00Z",
        round_dir,
        deadline_context=DEADLINE_CONTEXT,
    )

    assert [path.name for path in written] == ["text_assignment.md", "current_evidence_snapshot.md"]
    text = (round_dir / "work" / "supervisor_packets" / "text_assignment.md").read_text(encoding="utf-8")
    assert "Schema version: `supervisor-feedback-packet-v1`" in text
    assert "Recommended model: `gpt-5.5`" in text
    assert "Official deadline: 2026-05-13" in text
    assert "## Final-Sprint Action Budget" in text
    assert str(tmp_path) not in text


def test_supervisor_packets_emit_code_and_structured_optional_packets_only_when_triggered(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    (round_dir / "work" / "code_workspace.md").write_text("Prepared code root.\n", encoding="utf-8")
    (round_dir / "work" / "figure_media").mkdir(parents=True)
    (round_dir / "work" / "figure_media" / "visual_inventory.jsonl").write_text("{}\n", encoding="utf-8")
    write_materiality(round_dir, "figure_media")
    (round_dir / "outputs").mkdir()
    (round_dir / "outputs" / "typography_formal_review.md").write_text("# Typography\n", encoding="utf-8")

    written = generate_packets(
        "case-a",
        "round-a",
        "2026-05-11T00:00:00Z",
        round_dir,
        deadline_context=DEADLINE_CONTEXT,
    )
    names = {path.name for path in written}

    assert "code_consistency.md" in names
    assert "code_quality.md" in names
    assert "figure_media.md" in names
    assert "typography_formal.md" not in names
    code_quality = (round_dir / "work" / "supervisor_packets" / "code_quality.md").read_text(encoding="utf-8")
    assert "## Omen Advisory Static Analysis" in code_quality
    assert "not an operator prerequisite" in code_quality


def test_supervisor_code_packets_require_prepared_code_workspace_not_raw_archive(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    (round_dir / "inputs" / "thesis-source.zip").write_text("not necessarily submitted code\n", encoding="utf-8")

    written = generate_packets(
        "case-a",
        "round-a",
        "2026-05-11T00:00:00Z",
        round_dir,
        deadline_context=DEADLINE_CONTEXT,
    )
    names = {path.name for path in written}

    assert "code_consistency.md" not in names
    assert "code_quality.md" not in names


def test_supervisor_code_reproducibility_artifact_alone_does_not_activate_code_packets(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    (round_dir / "work" / "code_reproducibility.json").write_text(
        '{"classification": "no_code_evidence"}\n',
        encoding="utf-8",
    )

    written = generate_packets(
        "case-a",
        "round-a",
        "2026-05-11T00:00:00Z",
        round_dir,
        deadline_context=DEADLINE_CONTEXT,
    )
    names = {path.name for path in written}

    assert "code_consistency.md" not in names
    assert "code_quality.md" not in names


def test_supervisor_inactive_optional_packets_are_pruned(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    materiality = round_dir / "work" / "review_materiality" / "supervisor_feedback" / "figure_media.json"
    write_materiality(round_dir, "figure_media")

    generate_packets(
        "case-a",
        "round-a",
        "2026-05-11T00:00:00Z",
        round_dir,
        deadline_context=DEADLINE_CONTEXT,
    )
    assert (round_dir / "work" / "supervisor_packets" / "figure_media.md").is_file()

    materiality.unlink()
    generate_packets(
        "case-a",
        "round-a",
        "2026-05-11T00:00:00Z",
        round_dir,
        deadline_context=DEADLINE_CONTEXT,
    )

    assert not (round_dir / "work" / "supervisor_packets" / "figure_media.md").exists()


def test_supervisor_ignores_opponent_materiality_profile(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    write_materiality_decisions(
        round_dir,
        [
            MaterialityDecision(
                role="figure_media",
                recommendation="material",
                scope="opponent_is_item",
                impact="opponent report defensibility",
                reason="opponent-only materiality decision",
                source_refs=("workflow-profile:opponent_review",),
            )
        ],
        case_id="case-a",
        round_id="round-a",
        workflow_profile="opponent_review",
        phase="final",
        generated_at="2026-05-11T00:00:00Z",
    )

    written = generate_packets(
        "case-a",
        "round-a",
        "2026-05-11T00:00:00Z",
        round_dir,
        deadline_context=DEADLINE_CONTEXT,
    )
    names = {path.name for path in written}

    assert "figure_media.md" not in names


def test_supervisor_optional_materiality_paths_are_role_specific(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    write_materiality(round_dir, "literature_citation")

    written = generate_packets(
        "case-a",
        "round-a",
        "2026-05-11T00:00:00Z",
        round_dir,
        deadline_context=DEADLINE_CONTEXT,
    )
    names = {path.name for path in written}

    assert "literature_citation.md" in names
    assert "typography_formal.md" not in names


def test_supervisor_packet_renders_materiality_next_actions(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    (round_dir / "inputs" / "results.csv").write_text("metric,value\nlatency,42\n", encoding="utf-8")
    write_materiality_decisions(
        round_dir,
        [
            MaterialityDecision(
                role="quantitative_claims",
                recommendation="material",
                scope="explicit_request",
                impact="student-action priority",
                reason="test materiality decision",
                source_refs=("inputs/results.csv",),
            )
        ],
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
        phase="non_final",
        generated_at="2026-05-11T00:00:00Z",
    )
    role = next(item for item in PACKET_ROLES if item.key == "text_assignment")

    text = render_packet(
        "case-a",
        "round-a",
        "2026-05-11T00:00:00Z",
        round_dir,
        role,
        deadline_context=DEADLINE_CONTEXT,
    )

    assert "## Materiality Next Actions" in text
    assert "`quantitative_claims` requires `work/quantitative_claims.json`" in text
    assert "thesis-quantitative-claims-review" in text
    assert "use it with the materiality next action to author the structured handoff" in text

    written = generate_packets(
        "case-a",
        "round-a",
        "2026-05-11T00:00:00Z",
        round_dir,
        deadline_context=DEADLINE_CONTEXT,
    )
    assert "quantitative_claims.md" in {path.name for path in written}


def test_supervisor_packets_emit_theses_similarity_packet_from_next_action(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    report = round_dir / THESES_SIMILARITY_REPORT_REL
    report.parent.mkdir(parents=True)
    report.write_bytes(b"%PDF synthetic\n")
    write_materiality(round_dir, "theses_similarity")

    written = generate_packets(
        "case-a",
        "round-a",
        "2026-05-12T00:00:00Z",
        round_dir,
        deadline_context=DEADLINE_CONTEXT,
    )
    names = {path.name for path in written}
    text = (round_dir / "work" / "supervisor_packets" / "theses_similarity.md").read_text(encoding="utf-8")

    assert "theses_similarity.md" in names
    assert f"`theses_similarity` requires `{THESES_SIMILARITY_REVIEW_REL}`" in text
    assert THESES_SIMILARITY_REPORT_REL in text
    assert "Keep clean or resolved reports silent in student-facing feedback." in text


def test_supervisor_packet_consumes_quantitative_claims_handoff(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    write_quantitative_claims(round_dir)

    written = generate_packets(
        "case-a",
        "round-a",
        "2026-05-11T00:00:00Z",
        round_dir,
        deadline_context=DEADLINE_CONTEXT,
    )
    names = {path.name for path in written}
    text = (round_dir / "work" / "supervisor_packets" / "synthesis.md").read_text(encoding="utf-8")

    assert "quantitative_claims.md" in names
    assert "## Quantitative Claims Handoff" in text
    assert "Status counts: needs_context=1" in text
    assert "`Q1` metric/needs_context, baseline=missing, practical_context=weak; overclaim_risk=moderate" in text
    assert "magnitude: Magnitude is not interpreted against a user-visible impact." in text
    assert "Open raw result sections only to verify material claims" in text


def test_supervisor_packet_includes_previous_feedback_index(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    previous = round_dir.parents[0] / "round-previous" / "outputs" / "feedback_student.md"
    previous.parent.mkdir(parents=True)
    previous.write_text("# Feedback\n", encoding="utf-8")

    role = next(item for item in PACKET_ROLES if item.key == "text_assignment")
    text = render_packet(
        "case-a",
        "round-a",
        "2026-05-11T00:00:00Z",
        round_dir,
        role,
        deadline_context=DEADLINE_CONTEXT,
    )

    assert "round `round-previous`: `outputs/feedback_student.md`" in text


def test_supervisor_final_review_uses_draft_shape_gate() -> None:
    final_review = next(role for role in PACKET_ROLES if role.key == "final_review")

    assert final_review.activation == "check"
    assert final_review.activation_check == (
        "check-review-wave",
        "--workflow",
        "supervisor_feedback",
        "--wave",
        "draft",
    )
