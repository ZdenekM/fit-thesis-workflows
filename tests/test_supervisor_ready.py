import datetime as dt
import zipfile
from pathlib import Path

from thesis_review_workflow.cli import check_supervisor_ready, supervisor_deadline
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


def test_deadline_config_rows_are_complete_and_internally_consistent() -> None:
    """Every configured row must be usable for phase calibration.

    A blank `recommended_finish` does not fail any gate: `supervisor_deadline.calibration`
    silently falls back to the later official deadline, which moves supervision guidance
    without telling anyone. So completeness is asserted per row rather than per year.
    """
    config_path = Path(__file__).resolve().parents[1] / "config" / "supervisor-deadlines.tsv"
    rows = supervisor_deadline.read_deadlines(config_path)

    assert rows, f"{config_path} carries no deadline rows; refusing to pass vacuously"
    for row in rows:
        label = f"{row.get('academic_year')} {row.get('work_type')}"
        official = supervisor_deadline.parse_date(row.get("official_deadline", ""))
        recommended = supervisor_deadline.parse_date(row.get("recommended_finish", ""))
        assert supervisor_deadline.normalize_work_type(row.get("work_type", "")), label
        assert supervisor_deadline.normalize_academic_year(row.get("academic_year", "")), label
        assert official is not None, f"{label}: official_deadline must be an ISO date"
        assert recommended is not None, f"{label}: recommended_finish must be an ISO date"
        assert recommended < official, f"{label}: recommended_finish must precede official_deadline"
        assert row.get("notes", "").strip(), f"{label}: notes must say where the dates came from"


def test_deadline_config_covers_both_work_types_of_its_latest_academic_year() -> None:
    config_path = Path(__file__).resolve().parents[1] / "config" / "supervisor-deadlines.tsv"
    rows = supervisor_deadline.read_deadlines(config_path)

    latest = max(supervisor_deadline.normalize_academic_year(row["academic_year"]) for row in rows)
    covered = {
        supervisor_deadline.normalize_work_type(row["work_type"])
        for row in rows
        if supervisor_deadline.normalize_academic_year(row["academic_year"]) == latest
    }

    assert covered == {"BP", "DP"}, f"{latest} must configure both BP and DP, found {sorted(covered)}"


def test_calibration_anchors_on_the_recommended_finish_not_the_official_deadline() -> None:
    today = dt.date(2027, 5, 1)
    recommended = dt.date(2027, 5, 5)
    official = dt.date(2027, 5, 12)

    anchored = supervisor_deadline.calibration(recommended, official, today)
    without_recommended = supervisor_deadline.calibration(None, official, today)

    assert "final week" in anchored
    assert "final week" not in without_recommended


def test_supervisor_deadline_resolves_the_latest_configured_academic_year(
    capsys,
    monkeypatch,
    tmp_path: Path,
) -> None:
    """The gate the season audit found failing must pass for the newest configured year."""
    config_path = Path(__file__).resolve().parents[1] / "config" / "supervisor-deadlines.tsv"
    rows = supervisor_deadline.read_deadlines(config_path)
    latest = max(supervisor_deadline.normalize_academic_year(row["academic_year"]) for row in rows)

    root = tmp_path / "repo"
    (root / "config").mkdir(parents=True)
    (root / "config" / "supervisor-deadlines.tsv").write_text(config_path.read_text(encoding="utf-8"), encoding="utf-8")
    case_dir = root / "cases" / "case-a"
    (case_dir / "rounds" / "round-a" / "notes").mkdir(parents=True)
    (case_dir / "case.md").write_text(
        f"Work type: BP\nAcademic year: {latest}\nDeadline mode: standard\n",
        encoding="utf-8",
    )
    (case_dir / "current-round.txt").write_text("round-a\n", encoding="utf-8")
    monkeypatch.setattr(supervisor_deadline, "repo_root", lambda: root)
    monkeypatch.setenv("THESIS_TODAY", "2026-09-07")

    result = supervisor_deadline.main(["scripts/supervisor-deadline", "case-a", "round-a"])

    output = capsys.readouterr().out
    assert result == 0, output
    assert f"Academic year: {latest}" in output
    assert "Recommended internal finish:" in output
