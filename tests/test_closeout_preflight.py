import sys
from collections import namedtuple
from pathlib import Path

from thesis_review_workflow import closeout_preflight
from thesis_review_workflow.cli import (
    init_review_manifest,
    opponent_closeout,
    record_workflow_operation,
    review_round_closeout,
    supervisor_report_closeout,
    write_review_approval,
)
from thesis_review_workflow.commands import Step

DiskUsage = namedtuple("DiskUsage", "total used free")


def test_free_space_preflight_reports_recovery_without_cleanup(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        closeout_preflight.shutil,
        "disk_usage",
        lambda _path: DiskUsage(total=1024, used=1000, free=24),
    )

    step = closeout_preflight.free_space_preflight_step(tmp_path, min_free_bytes=128)

    assert step.returncode == 1
    assert "Filesystem for" in step.output
    assert "Safe regenerable cleanup candidates" in step.output
    assert "No cleanup was performed automatically" in step.output


def test_free_space_preflight_passes_when_space_is_available(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        closeout_preflight.shutil,
        "disk_usage",
        lambda _path: DiskUsage(total=1024, used=100, free=924),
    )

    step = closeout_preflight.free_space_preflight_step(tmp_path, min_free_bytes=128)

    assert step.returncode == 0
    assert "required minimum" in step.output


def test_record_workflow_operation_stops_before_log_write_on_low_space(tmp_path: Path, monkeypatch, capsys) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    round_dir.mkdir(parents=True)
    (root / "cases" / "case-a" / "current-round.txt").write_text("round-a\n", encoding="utf-8")
    monkeypatch.setattr(record_workflow_operation, "repo_root", lambda: root)
    monkeypatch.setattr(
        record_workflow_operation,
        "free_space_preflight_step",
        lambda _round_dir: Step(
            label="Free-space preflight",
            command=None,
            returncode=1,
            output=("Filesystem for round-a has too little free space. " "Safe regenerable cleanup candidates listed."),
        ),
    )

    result = record_workflow_operation.main(
        [
            "record-workflow-operation",
            "case-a",
            "round-a",
            "--operation",
            "smoke",
            "--status",
            "blocked",
            "--summary",
            "Synthetic low-space smoke.",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "ERROR: Filesystem for round-a has too little free space" in captured.out
    assert not (round_dir / "work" / "operation_log.jsonl").exists()


def test_init_review_manifest_stops_before_manifest_write_on_low_space(tmp_path: Path, monkeypatch, capsys) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    round_dir.mkdir(parents=True)
    (root / "cases" / "case-a" / "current-round.txt").write_text("round-a\n", encoding="utf-8")
    monkeypatch.setattr(init_review_manifest, "repo_root", lambda: root)
    monkeypatch.setattr(init_review_manifest, "free_space_preflight_step", low_space_step)
    monkeypatch.setattr(sys, "argv", ["scripts/init-review-manifest", "case-a", "round-a"])

    result = init_review_manifest.main()

    captured = capsys.readouterr()
    assert result == 1
    assert "ERROR: low space before write-heavy phase" in captured.out
    assert not (round_dir / "work" / "review_manifest.json").exists()


def test_write_review_approval_stops_before_approval_write_on_low_space(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    round_dir.mkdir(parents=True)
    (root / "cases" / "case-a" / "current-round.txt").write_text("round-a\n", encoding="utf-8")
    monkeypatch.setattr(write_review_approval, "repo_root", lambda: root)
    monkeypatch.setattr(write_review_approval, "free_space_preflight_step", low_space_step)

    result = write_review_approval.main(
        [
            "--profile",
            "supervisor-feedback",
            "--reviewer-agent",
            "review-agent",
            "case-a",
            "round-a",
        ]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "ERROR: low space before write-heavy phase" in captured.out
    assert not (round_dir / "work" / "reviews" / "supervisor_feedback_review.json").exists()


def test_review_round_closeout_stops_before_refresh_steps_on_low_space(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    round_dir.mkdir(parents=True)
    monkeypatch.setattr(review_round_closeout, "free_space_preflight_step", low_space_step)

    def fail_run_step(*args, **kwargs) -> Step:
        raise AssertionError("run_step must not execute after failed preflight")

    monkeypatch.setattr(review_round_closeout, "run_step", fail_run_step)

    steps = review_round_closeout.generic_closeout_steps(
        root,
        case_id="case-a",
        round_id="round-a",
        profile_id="opponent_materials",
    )

    assert len(steps) == 1
    assert steps[0].label == "Free-space preflight"
    assert steps[0].returncode == 1


def test_opponent_closeout_stops_before_manifest_write_on_low_space(tmp_path: Path, monkeypatch, capsys) -> None:
    root = tmp_path / "repo"
    make_case_round(root)
    monkeypatch.setattr(opponent_closeout, "repo_root", lambda: root)
    monkeypatch.setattr(opponent_closeout, "free_space_preflight_step", low_space_step)

    def fail_run_step(*args, **kwargs) -> Step:
        raise AssertionError("run_step must not execute after failed preflight")

    monkeypatch.setattr(opponent_closeout, "run_step", fail_run_step)

    result = opponent_closeout.main(["scripts/opponent-closeout", "--skip-repo-hygiene", "case-a", "round-a"])

    captured = capsys.readouterr()
    assert result == 1
    assert "Free-space preflight: FAIL" in captured.out
    assert "Review manifest refresh" not in captured.out


def test_supervisor_report_closeout_stops_before_manifest_write_on_low_space(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    root = tmp_path / "repo"
    make_case_round(root)
    monkeypatch.setattr(supervisor_report_closeout, "repo_root", lambda: root)
    monkeypatch.setattr(supervisor_report_closeout, "free_space_preflight_step", low_space_step)

    def fail_run_step(*args, **kwargs) -> Step:
        raise AssertionError("run_step must not execute after failed preflight")

    monkeypatch.setattr(supervisor_report_closeout, "run_step", fail_run_step)

    result = supervisor_report_closeout.main(
        ["scripts/supervisor-report-closeout", "--skip-repo-hygiene", "case-a", "round-a"]
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "Free-space preflight: FAIL" in captured.out
    assert "Pre-wave review manifest refresh" not in captured.out


def low_space_step(_round_dir: Path) -> Step:
    return Step(
        label="Free-space preflight",
        command=None,
        returncode=1,
        output="low space before write-heavy phase",
    )


def make_case_round(root: Path) -> Path:
    case_dir = root / "cases" / "case-a"
    round_dir = case_dir / "rounds" / "round-a"
    round_dir.mkdir(parents=True)
    (case_dir / "current-round.txt").write_text("round-a\n", encoding="utf-8")
    (case_dir / "case.md").write_text("Work type: BP\nAcademic year: 2025/2026\n", encoding="utf-8")
    return round_dir
