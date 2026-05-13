import json
from pathlib import Path

from thesis_review_workflow.cli import prepare_supervisor_report_packets
from thesis_review_workflow.commands import Step
from thesis_review_workflow.review_materiality import MaterialityDecision, write_materiality_decisions
from thesis_review_workflow.supervisor_report_packets import generate_packets
from thesis_review_workflow.theses_similarity import THESES_SIMILARITY_REPORT_REL, THESES_SIMILARITY_REVIEW_REL


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
        "- Implement and evaluate a helper.\n",
        encoding="utf-8",
    )
    (round_dir / "notes" / "supervisor-report-operator-input.md").write_text(
        "# Supervisor Report Intake\n\n## Informace k zadani\n\nNarocnost prace: stredni\n",
        encoding="utf-8",
    )
    return round_dir


def write_materiality(round_dir: Path, role: str, *, workflow_profile: str = "supervisor_report") -> None:
    write_materiality_decisions(
        round_dir,
        [
            MaterialityDecision(
                role=role,
                recommendation="material",
                scope="explicit_request",
                impact="supervisor report context",
                reason="test materiality decision",
                source_refs=(f"operator-request:{role}",),
            )
        ],
        case_id="case-a",
        round_id="round-a",
        workflow_profile=workflow_profile,
        phase="final",
        generated_at="2026-05-12T00:00:00Z",
    )


def test_generate_supervisor_report_packets_starts_with_mandatory_roles(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)

    written = generate_packets("case-a", "round-a", "2026-05-12T00:00:00Z", round_dir)

    assert [path.name for path in written] == ["trace.md", "current_evidence_snapshot.md"]
    text = (round_dir / "work" / "supervisor_report_packets" / "trace.md").read_text(encoding="utf-8")
    assert "Schema version: `supervisor-report-packet-v1`" in text
    assert "Expected output: `work/supervisor_report_trace.json`" in text
    assert "Supervisor input is authoritative" in text
    assert str(tmp_path) not in text


def test_supervisor_report_packets_emit_code_and_report_review_when_triggered(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    (round_dir / "work" / "code_workspace.md").write_text("Prepared code root.\n", encoding="utf-8")
    (round_dir / "work" / "vedouci_posudek_draft.md").write_text("# Návrh posudku vedoucího\n", encoding="utf-8")

    written = generate_packets("case-a", "round-a", "2026-05-12T00:00:00Z", round_dir)
    names = {path.name for path in written}

    assert "code_consistency.md" in names
    assert "code_quality.md" in names
    assert "report_review.md" in names
    code_quality = (round_dir / "work" / "supervisor_report_packets" / "code_quality.md").read_text(encoding="utf-8")
    assert "## Omen Advisory Static Analysis" in code_quality
    report_review = (round_dir / "work" / "supervisor_report_packets" / "report_review.md").read_text(encoding="utf-8")
    assert "work/vedouci_posudek_draft.md" in report_review
    assert "supervisor_report_confirmation.json" in report_review


def test_supervisor_report_packets_use_supervisor_report_materiality_profile(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    write_materiality(round_dir, "literature_citation")

    written = generate_packets("case-a", "round-a", "2026-05-12T00:00:00Z", round_dir)
    names = {path.name for path in written}

    assert "literature_citation.md" in names
    assert "typography_formal.md" not in names


def test_supervisor_report_packets_emit_theses_similarity_packet_from_next_action(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    report = round_dir / THESES_SIMILARITY_REPORT_REL
    report.parent.mkdir(parents=True)
    report.write_bytes(b"%PDF synthetic\n")
    write_materiality(round_dir, "theses_similarity")

    written = generate_packets("case-a", "round-a", "2026-05-12T00:00:00Z", round_dir)
    names = {path.name for path in written}
    text = (round_dir / "work" / "supervisor_report_packets" / "theses_similarity.md").read_text(encoding="utf-8")

    assert "theses_similarity.md" in names
    assert f"`theses_similarity` requires `{THESES_SIMILARITY_REVIEW_REL}`" in text
    assert THESES_SIMILARITY_REPORT_REL in text
    assert "Keep no-concern and resolved findings silent" in text


def test_supervisor_report_packets_ignore_supervisor_feedback_materiality(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    write_materiality(round_dir, "figure_media", workflow_profile="supervisor_feedback")

    written = generate_packets("case-a", "round-a", "2026-05-12T00:00:00Z", round_dir)
    names = {path.name for path in written}

    assert "figure_media.md" not in names


def test_supervisor_report_inactive_optional_packets_are_pruned(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    materiality = round_dir / "work" / "review_materiality" / "supervisor_report" / "literature_citation.json"
    write_materiality(round_dir, "literature_citation")
    generate_packets("case-a", "round-a", "2026-05-12T00:00:00Z", round_dir)
    assert (round_dir / "work" / "supervisor_report_packets" / "literature_citation.md").is_file()

    materiality.unlink()
    generate_packets("case-a", "round-a", "2026-05-12T00:00:00Z", round_dir)

    assert not (round_dir / "work" / "supervisor_report_packets" / "literature_citation.md").exists()


def test_supervisor_report_packets_show_report_artifact_hashes(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    payload = {"schema_version": "supervisor-report-trace-v1"}
    (round_dir / "work" / "supervisor_report_trace.json").write_text(
        json.dumps(payload) + "\n",
        encoding="utf-8",
    )

    generate_packets("case-a", "round-a", "2026-05-12T00:00:00Z", round_dir)
    text = (round_dir / "work" / "supervisor_report_packets" / "trace.md").read_text(encoding="utf-8")

    assert "`work/supervisor_report_trace.json` (invalid, sha256=" in text


def test_prepare_supervisor_report_packets_refreshes_snapshot_before_materiality(tmp_path: Path, monkeypatch) -> None:
    round_dir = make_round(tmp_path)
    root = round_dir.parents[3]
    calls: list[str] = []

    def fake_run_step(root_arg: Path, label: str, args: list[str], *, required: bool = True) -> Step:
        assert root_arg == root
        calls.append(label)
        return Step(label=label, command=args, returncode=0, output="", required=required)

    monkeypatch.setattr(prepare_supervisor_report_packets, "repo_root", lambda: root)
    monkeypatch.setattr(prepare_supervisor_report_packets, "run_step", fake_run_step)

    result = prepare_supervisor_report_packets.main(["case-a", "round-a"])

    assert result == 0
    assert calls == [
        "supervisor report readiness",
        "current evidence snapshot",
        "supervisor report materiality",
    ]
