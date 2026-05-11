from pathlib import Path

from thesis_review_workflow.supervisor_packets import PACKET_ROLES, generate_packets, render_packet

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
    (round_dir / "work" / "figure_media").mkdir(parents=True)
    inventory = round_dir / "work" / "figure_media" / "visual_inventory.jsonl"
    inventory.write_text("{}\n", encoding="utf-8")

    generate_packets(
        "case-a",
        "round-a",
        "2026-05-11T00:00:00Z",
        round_dir,
        deadline_context=DEADLINE_CONTEXT,
    )
    assert (round_dir / "work" / "supervisor_packets" / "figure_media.md").is_file()

    inventory.unlink()
    generate_packets(
        "case-a",
        "round-a",
        "2026-05-11T00:00:00Z",
        round_dir,
        deadline_context=DEADLINE_CONTEXT,
    )

    assert not (round_dir / "work" / "supervisor_packets" / "figure_media.md").exists()


def test_supervisor_optional_materiality_paths_are_role_specific(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    (round_dir / "work" / "review_materiality").mkdir(parents=True)
    (round_dir / "work" / "review_materiality" / "literature_citation.json").write_text("{}\n", encoding="utf-8")

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
