from pathlib import Path

from thesis_review_workflow.cli.opponent_preflight import output_next_actions


def test_preflight_reports_evidence_requirements_without_code(capsys, tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    (round_dir / "work").mkdir(parents=True)
    (round_dir / "work" / "evidence_requirements.json").write_text("{}\n", encoding="utf-8")

    output_next_actions(
        round_dir=round_dir,
        code_present=False,
        code_evidence=[],
        github_hits=[],
        github_scope_done=False,
        prepared_code=False,
        code_root_count=0,
    )

    output = capsys.readouterr().out
    assert "Code evidence detected: no" in output
    assert "Existing evidence requirements artifact detected" in output
    assert "scripts/check-evidence-presence" in output
