import zipfile
from pathlib import Path

from thesis_review_workflow.cli import check_supervisor_ready
from thesis_review_workflow.commands import Step
from thesis_review_workflow.submission_bundle import (
    build_submission_bundle_inventory,
    write_submission_bundle_inventory,
)


def test_supervisor_ready_prints_bundle_visibility_before_failed_gate(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    case_dir = root / "cases" / "case-a"
    round_dir = case_dir / "rounds" / "round-a"
    (round_dir / "inputs").mkdir(parents=True)
    with zipfile.ZipFile(round_dir / "inputs" / "submission.zip", "w") as handle:
        handle.writestr("handoff/assignment-zadani.pdf", b"%PDF-1.4\n")
    payload = build_submission_bundle_inventory(
        case_id="case-a",
        round_id="round-a",
        round_dir=round_dir,
        bundle_refs=["inputs/submission.zip"],
        producer="scripts/review-round-start",
        generated_at="2026-05-19T12:00:00Z",
    )
    write_submission_bundle_inventory(round_dir=round_dir, payload=payload)
    monkeypatch.setattr(check_supervisor_ready, "repo_root", lambda: root)

    def fake_run_step(root_arg: Path, label: str, args: list[str]) -> Step:
        assert root_arg == root
        return Step(label=label, command=args, returncode=1, output="missing assignment")

    monkeypatch.setattr(check_supervisor_ready, "run_step", fake_run_step)

    result = check_supervisor_ready.main(["scripts/check-supervisor-ready", "case-a", "round-a"])

    output = capsys.readouterr().out
    assert result == 1
    assert "Submission Bundle Inventory" in output
    assert "expected extract `extracted/submission_bundle/" in output
    assert output.index("Submission Bundle Inventory") < output.index("missing assignment")
