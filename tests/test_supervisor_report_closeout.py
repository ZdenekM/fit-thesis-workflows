from pathlib import Path

from thesis_review_workflow.cli import supervisor_report_closeout
from thesis_review_workflow.commands import Step


def make_round(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    case_dir = root / "cases" / "case-a"
    round_dir = case_dir / "rounds" / "round-a"
    round_dir.mkdir(parents=True)
    (case_dir / "current-round.txt").write_text("round-a\n", encoding="utf-8")
    (case_dir / "case.md").write_text("Work type: BP\nAcademic year: 2025/2026\n", encoding="utf-8")
    return root, round_dir


def test_supervisor_report_closeout_refreshes_manifest_before_final_wave(tmp_path: Path, monkeypatch) -> None:
    root, round_dir = make_round(tmp_path)
    printed_labels: list[str] = []

    def fake_run_step(root_arg: Path, label: str, args: list[str], *, required: bool = True) -> Step:
        assert root_arg == root
        if label == "Current evidence snapshot":
            assert "--no-known" not in args
            assert "work/review_manifest.json" not in args
            assert "work/agent_coverage.json" not in args
        if label == "Pre-wave review manifest refresh":
            coverage = round_dir / "work" / "agent_coverage.json"
            coverage.parent.mkdir(parents=True, exist_ok=True)
            coverage.write_text("{}\n", encoding="utf-8")
        return Step(label=label, command=args, returncode=0, output=f"{label} passed", required=required)

    def fake_print_step(step: Step, *, output_limit: int) -> None:
        assert output_limit == 1000
        printed_labels.append(step.label)

    monkeypatch.setattr(supervisor_report_closeout, "repo_root", lambda: root)
    monkeypatch.setattr(supervisor_report_closeout, "run_step", fake_run_step)
    monkeypatch.setattr(supervisor_report_closeout, "print_step", fake_print_step)
    monkeypatch.setattr(
        supervisor_report_closeout,
        "unresolved_required_next_actions",
        lambda *args, **kwargs: ([], []),
    )

    result = supervisor_report_closeout.main(
        ["scripts/supervisor-report-closeout", "--skip-repo-hygiene", "case-a", "round-a"]
    )

    assert result == 0
    assert printed_labels == [
        "Free-space preflight",
        "Supervisor report readiness",
        "Reviewed and confirmed supervisor report",
        "Current evidence snapshot",
        "Final supervisor report materiality",
        "Final materiality next actions",
        "Pre-wave review manifest refresh",
        "Final supervisor report review wave",
        "Post-wave review manifest refresh",
        "Agent role coverage",
        "Review manifest completeness",
    ]


def test_supervisor_report_closeout_can_reuse_shared_current_evidence_refresh(tmp_path: Path, monkeypatch) -> None:
    root, _ = make_round(tmp_path)
    run_labels: list[str] = []

    def fake_run_step(root_arg: Path, label: str, args: list[str], *, required: bool = True) -> Step:
        assert root_arg == root
        run_labels.append(label)
        return Step(label=label, command=args, returncode=0, output=f"{label} passed", required=required)

    monkeypatch.setattr(supervisor_report_closeout, "repo_root", lambda: root)
    monkeypatch.setattr(supervisor_report_closeout, "run_step", fake_run_step)
    monkeypatch.setattr(supervisor_report_closeout, "print_step", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        supervisor_report_closeout,
        "unresolved_required_next_actions",
        lambda *args, **kwargs: ([], []),
    )

    result = supervisor_report_closeout.main(
        [
            "scripts/supervisor-report-closeout",
            "--skip-repo-hygiene",
            "--skip-current-evidence-refresh",
            "case-a",
            "round-a",
        ]
    )

    assert result == 0
    assert "Free-space preflight" not in run_labels
    assert "Current evidence snapshot" not in run_labels


def test_supervisor_report_closeout_fails_unresolved_final_materiality_actions(tmp_path: Path, monkeypatch) -> None:
    root, _ = make_round(tmp_path)

    monkeypatch.setattr(supervisor_report_closeout, "repo_root", lambda: root)
    monkeypatch.setattr(
        supervisor_report_closeout,
        "run_step",
        lambda root_arg, label, args, *, required=True: Step(
            label=label,
            command=args,
            returncode=0,
            output=f"{label} passed",
            required=required,
        ),
    )
    monkeypatch.setattr(
        supervisor_report_closeout,
        "unresolved_required_next_actions",
        lambda *args, **kwargs: (
            [
                {
                    "role": "quantitative_claims",
                    "required_artifact_path": "work/quantitative_claims.json",
                    "reason": "material quantitative claim needs review",
                }
            ],
            [],
        ),
    )

    result = supervisor_report_closeout.main(
        ["scripts/supervisor-report-closeout", "--skip-repo-hygiene", "case-a", "round-a"]
    )

    assert result == 1
