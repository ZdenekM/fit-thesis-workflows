import zipfile
from pathlib import Path

from thesis_review_workflow.cli.opponent_preflight import output_next_actions
from thesis_review_workflow.submission_bundle import (
    build_submission_bundle_inventory,
    write_submission_bundle_inventory,
)


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


def test_preflight_reports_submission_bundle_inventory(capsys, tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    (round_dir / "inputs").mkdir(parents=True)
    with zipfile.ZipFile(round_dir / "inputs" / "submission.zip", "w") as handle:
        handle.writestr("handoff/src/main.py", "print('synthetic')\n")
        handle.writestr("handoff/demo.mp4", b"mp4")
        handle.writestr("handoff/app.apk", b"apk")
    payload = build_submission_bundle_inventory(
        case_id="case-a",
        round_id="round-a",
        round_dir=round_dir,
        bundle_refs=["inputs/submission.zip"],
        producer="scripts/review-round-start",
        generated_at="2026-05-19T12:00:00Z",
    )
    write_submission_bundle_inventory(round_dir=round_dir, payload=payload)

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
    assert "## Submission Bundle Inventory" in output
    assert "First-party-looking code:" in output
    assert "Demo/media/executables:" in output
    assert "executable_artifact" in output
