import json
from pathlib import Path

from thesis_review_workflow.cli import review_round_closeout
from thesis_review_workflow.commands import Step


def write_transition_artifacts(round_dir: Path, *, profile_id: str = "opponent_report_review") -> None:
    (round_dir / "work").mkdir(parents=True, exist_ok=True)
    trace = {
        "schema_version": "review-run-trace-v1",
        "case_id": "case-a",
        "round_id": "round-a",
        "profile_id": profile_id,
        "workflow_profile": "opponent_report_review",
        "materiality_profile": "opponent_review",
        "operator_surface": "opponent_report_review",
        "generated_at": "2026-05-15T12:00:00Z",
        "trace_path": "work/review_run_trace.json",
        "events": [],
    }
    plan = {
        "schema_version": "review-role-plan-v1",
        "case_id": "case-a",
        "round_id": "round-a",
        "profile_id": profile_id,
        "workflow_profile": "opponent_report_review",
        "operator_surface": "opponent_report_review",
        "generated_at": "2026-05-15T12:00:00Z",
        "role_plan_path": "work/review_role_plan.json",
        "final_artifact": "outputs/feedback_k_posudku.md",
        "approval_record": "work/reviews/opponent_report_review.json",
        "packet_dir": "work/opponent_packets",
        "common_briefing": "work/common_briefing.json",
        "role_states": [
            {
                "role": "final_review",
                "state": "not_material",
                "expected_output": "outputs/feedback_k_posudku.md",
                "packet_path": "work/opponent_packets/report_review.md",
            }
        ],
        "wave_schedule": [],
        "code_bearing_contract": {"status": "not_required"},
    }
    (round_dir / "work" / "review_run_trace.json").write_text(json.dumps(trace) + "\n", encoding="utf-8")
    (round_dir / "work" / "review_role_plan.json").write_text(json.dumps(plan) + "\n", encoding="utf-8")


def test_closeout_profile_transition_preflight_blocks_mismatch_before_manifest(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "work").mkdir(parents=True)
    for rel_path in ("work/review_run_trace.json", "work/review_role_plan.json"):
        (round_dir / rel_path).write_text(
            json.dumps({"case_id": "case-a", "round_id": "round-a", "profile_id": "supervisor_feedback"}) + "\n",
            encoding="utf-8",
        )

    step = review_round_closeout.profile_transition_step(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        profile_id="opponent_report_review",
    )

    assert step.returncode == 1
    assert "work/review_run_trace.json records profile_id='supervisor_feedback'" in step.output
    assert "scripts/review-round-start --profile opponent_report_review case-a round-a" in step.output
    assert "scripts/prepare-review-round --profile opponent_report_review case-a round-a" in step.output


def test_closeout_profile_transition_preflight_accepts_matching_artifacts(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    write_transition_artifacts(round_dir)

    step = review_round_closeout.profile_transition_step(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        profile_id="opponent_report_review",
    )

    assert step.returncode == 0


def test_closeout_profile_transition_preflight_blocks_malformed_same_profile_state(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    write_transition_artifacts(round_dir)
    (round_dir / "work" / "review_run_trace.json").write_text(
        json.dumps({"case_id": "case-a", "round_id": "round-a", "profile_id": "opponent_report_review"}) + "\n",
        encoding="utf-8",
    )

    step = review_round_closeout.profile_transition_step(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        profile_id="opponent_report_review",
    )

    assert step.returncode == 1
    assert "work/review_run_trace.json: schema_version must be review-run-trace-v1" in step.output
    assert "scripts/review-round-start --profile opponent_report_review case-a round-a" in step.output


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
