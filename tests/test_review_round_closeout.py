from pathlib import Path

from thesis_review_workflow.cli import review_round_closeout
from thesis_review_workflow.commands import Step


def test_closeout_refreshes_common_briefing_after_effective_materiality(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    round_dir.mkdir(parents=True)
    events: list[str] = []
    commands: list[tuple[str, list[str]]] = []

    def fake_run_step(root_path: Path, label: str, command: list[str]) -> Step:
        events.append(label)
        commands.append((label, command))
        return Step(label=label, command=command, returncode=0, output="ok")

    def fake_write_common_briefing(case_id: str, round_id: str, generated_at: str, target_round_dir: Path) -> Path:
        assert case_id == "case-a"
        assert round_id == "round-a"
        assert generated_at
        assert target_round_dir == round_dir
        events.append("common_briefing")
        return target_round_dir / "work" / "common_briefing.json"

    def fake_role_plan_step(*args, **kwargs) -> Step:
        events.append("role_plan")
        return Step(label="Review role plan closeout", command=None, returncode=0, output="ok")

    def fake_review_delta_step(*args, **kwargs) -> Step:
        events.append("review_delta")
        return Step(label="Review delta closeout", command=None, returncode=0, output="ok")

    monkeypatch.setattr(review_round_closeout, "run_step", fake_run_step)
    monkeypatch.setattr(review_round_closeout, "write_common_briefing", fake_write_common_briefing)
    monkeypatch.setattr(review_round_closeout, "role_plan_step", fake_role_plan_step)
    monkeypatch.setattr(review_round_closeout, "review_delta_step", fake_review_delta_step)

    steps = review_round_closeout.generic_closeout_steps(
        root,
        case_id="case-a",
        round_id="round-a",
        profile_id="opponent_materials",
    )

    assert [step.returncode for step in steps] == [0] * len(steps)
    assert events == [
        "Readiness gate: check-round-ready",
        "Review manifest refresh",
        "Final materiality profile: opponent_review",
        "common_briefing",
        "role_plan",
        "review_delta",
        "Delegated profile closeout: opponent-closeout",
    ]
    materiality_command = dict(commands)["Final materiality profile: opponent_review"]
    assert materiality_command[:5] == [
        "scripts/check-review-materiality",
        "--workflow",
        "opponent_review",
        "--phase",
        "final",
    ]
