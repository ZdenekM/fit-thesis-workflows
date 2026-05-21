import json
import subprocess
from pathlib import Path
from typing import cast

from thesis_review_workflow import commands
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
    assert "review-round-start --profile opponent_report_review case-a round-a" in step.output
    assert "prepare-review-round --profile opponent_report_review case-a round-a" in step.output


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
    assert "review-round-start --profile opponent_report_review case-a round-a" in step.output


def test_closeout_refreshes_common_briefing_after_effective_materiality(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    round_dir.mkdir(parents=True)
    events: list[str] = []
    commands: list[tuple[str, list[str]]] = []

    def fake_run_step(
        root_path: Path,
        label: str,
        command: list[str],
        *,
        required: bool = True,
        extra_env: dict[str, str] | None = None,
    ) -> Step:
        events.append(label)
        commands.append((label, command))
        return Step(label=label, command=command, returncode=0, output="ok", required=required)

    def fake_write_common_briefing(
        case_id: str,
        round_id: str,
        generated_at: str,
        target_round_dir: Path,
        *,
        workflow_profile: str | None = None,
    ) -> Path:
        assert case_id == "case-a"
        assert round_id == "round-a"
        assert generated_at
        assert target_round_dir == round_dir
        assert workflow_profile is None
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
    assert steps[0].label == "Free-space preflight"
    assert events == [
        "Readiness gate: check-round-ready",
        "Current evidence snapshot refresh",
        "Final materiality profile: opponent_review",
        "common_briefing",
        "Review role plan refresh",
        "Review manifest refresh",
        "role_plan",
        "review_delta",
        "Delegated profile closeout: opponent-closeout",
    ]
    assert dict(commands)["Current evidence snapshot refresh"] == [
        "scripts/update-current-evidence-snapshot",
        "case-a",
        "round-a",
    ]
    materiality_command = dict(commands)["Final materiality profile: opponent_review"]
    assert materiality_command[:5] == [
        "scripts/check-review-materiality",
        "--workflow",
        "opponent_review",
        "--phase",
        "final",
    ]


def test_review_round_closeout_delegates_supervisor_report_after_shared_current_evidence(
    monkeypatch,
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    round_dir.mkdir(parents=True)
    events: list[str] = []
    commands_seen: dict[str, list[str]] = {}
    extra_envs: dict[str, dict[str, str] | None] = {}
    common_briefing_workflow_profiles: list[str | None] = []

    def fake_run_step(
        root_path: Path,
        label: str,
        command: list[str],
        *,
        required: bool = True,
        extra_env: dict[str, str] | None = None,
    ) -> Step:
        events.append(label)
        commands_seen[label] = command
        extra_envs[label] = extra_env
        return Step(label=label, command=command, returncode=0, output="ok", required=required)

    monkeypatch.setattr(review_round_closeout, "run_step", fake_run_step)

    def fake_write_common_briefing(*args, **kwargs) -> Path:
        common_briefing_workflow_profiles.append(kwargs.get("workflow_profile"))
        return round_dir / "work/common_briefing.json"

    monkeypatch.setattr(review_round_closeout, "write_common_briefing", fake_write_common_briefing)
    monkeypatch.setattr(
        review_round_closeout,
        "role_plan_step",
        lambda *args, **kwargs: Step(label="Review role plan closeout", command=None, returncode=0, output="ok"),
    )
    monkeypatch.setattr(
        review_round_closeout,
        "review_delta_step",
        lambda *args, **kwargs: Step(label="Review delta closeout", command=None, returncode=0, output="ok"),
    )

    steps = review_round_closeout.generic_closeout_steps(
        root,
        case_id="case-a",
        round_id="round-a",
        profile_id="supervisor_report",
    )

    assert [step.returncode for step in steps] == [0] * len(steps)
    assert "Current evidence snapshot refresh" in events
    assert common_briefing_workflow_profiles == ["supervisor_report"]
    assert steps[0].label == "Free-space preflight"
    assert any(step.label == "Review role plan refresh" for step in steps)
    assert commands_seen["Delegated profile closeout: supervisor-report-closeout"] == [
        "scripts/supervisor-report-closeout",
        "--skip-repo-hygiene",
        "--skip-current-evidence-refresh",
        "case-a",
        "round-a",
    ]
    assert extra_envs["Delegated profile closeout: supervisor-report-closeout"] == {
        commands.PROCESS_GROUP_MODE_ENV: commands.PROCESS_GROUP_MODE_INHERIT
    }


def test_closeout_first_failure_summary_prefers_first_required_failure(capsys) -> None:
    steps = [
        Step(
            label="Current evidence snapshot refresh",
            command=["scripts/update-current-evidence-snapshot"],
            returncode=1,
            output="bad",
        ),
        Step(
            label="Review manifest completeness",
            command=["scripts/check-review-manifest"],
            returncode=1,
            output="downstream",
        ),
    ]

    review_round_closeout.print_first_failure_summary(
        case_id="case-a",
        round_id="round-a",
        profile_id="opponent_report_review",
        steps=steps,
    )

    out = capsys.readouterr().out
    assert "## First Actionable Failure" in out
    assert "- Gate: Current evidence snapshot refresh" in out
    assert "- Class: upstream" in out
    assert "`update-current-evidence-snapshot`" in out
    assert "Review manifest completeness" not in out


def test_closeout_first_failure_summary_renders_internal_recovery(capsys) -> None:
    steps = [
        Step(label="Review delta closeout", command=None, returncode=1, output="delta missing"),
        Step(
            label="Final review wave: opponent_report_review:final",
            command=["scripts/check-review-wave"],
            returncode=1,
            output="later",
        ),
    ]

    review_round_closeout.print_first_failure_summary(
        case_id="case-a",
        round_id="round-a",
        profile_id="opponent_report_review",
        steps=steps,
    )

    out = capsys.readouterr().out
    assert "- Gate: Review delta closeout" in out
    assert "- Class: upstream" in out
    assert "`record-review-delta --profile opponent_report_review case-a round-a`" in out


def test_closeout_first_failure_summary_renders_profile_transition_recovery(capsys) -> None:
    steps = [
        Step(
            label="Review profile transition preflight",
            command=None,
            returncode=1,
            output="stale profile state",
            recovery_command=(
                "review-round-start --profile opponent_report_review case-a round-a && "
                "prepare-review-round --profile opponent_report_review case-a round-a"
            ),
        )
    ]

    review_round_closeout.print_first_failure_summary(
        case_id="case-a",
        round_id="round-a",
        profile_id="opponent_report_review",
        steps=steps,
    )

    out = capsys.readouterr().out
    assert "review-round-start --profile opponent_report_review case-a round-a" in out
    assert "prepare-review-round --profile opponent_report_review case-a round-a" in out


def test_closeout_first_failure_summary_uses_role_plan_file_recovery(capsys) -> None:
    steps = [
        Step(
            label="Review role plan closeout",
            command=None,
            returncode=1,
            output="code_quality requires current output",
            recovery_command=(
                "inspect work/review_role_plan.json, expected role output paths, validators, "
                "and work/operation_log.jsonl; then run check-review-manifest --require-complete case-a round-a"
            ),
        )
    ]

    review_round_closeout.print_first_failure_summary(
        case_id="case-a",
        round_id="round-a",
        profile_id="opponent_report_review",
        steps=steps,
    )

    out = capsys.readouterr().out
    assert "work/review_role_plan.json" in out
    assert "work/operation_log.jsonl" in out
    assert "check-review-manifest --require-complete case-a round-a" in out


def test_closeout_stops_generic_gates_after_first_required_failure(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    round_dir.mkdir(parents=True)
    events: list[str] = []

    def fake_run_step(
        root_path: Path,
        label: str,
        command: list[str],
        *,
        required: bool = True,
        extra_env: dict[str, str] | None = None,
    ) -> Step:
        events.append(label)
        returncode = 1 if label == "Current evidence snapshot refresh" else 0
        return Step(label=label, command=command, returncode=returncode, output="snapshot failed", required=required)

    monkeypatch.setattr(review_round_closeout, "run_step", fake_run_step)

    steps = review_round_closeout.generic_closeout_steps(
        root,
        case_id="case-a",
        round_id="round-a",
        profile_id="opponent_report_review",
    )

    assert steps[-1].label == "Current evidence snapshot refresh"
    assert "Review manifest refresh" not in [step.label for step in steps]
    assert events[-1] == "Current evidence snapshot refresh"


def test_closeout_progress_line_is_file_oriented_and_sanitized() -> None:
    line = review_round_closeout.closeout_progress_line(
        case_id="case-a",
        round_id="round-a",
        profile_id="opponent_report_review",
        check_label="Review manifest refresh",
        command=["scripts/init-review-manifest", "--run-checks", "case-a", "round-a"],
        artifact="outputs/feedback_k_posudku.md",
        elapsed_seconds=12.345,
    )

    assert "case=case-a" in line
    assert "profile=opponent_report_review" in line
    assert "artifact='outputs/feedback_k_posudku.md'" in line
    assert "init-review-manifest --run-checks case-a round-a" in line
    assert "/home/" not in line
    assert "cases/case-a" not in line


def test_closeout_logical_command_display_quotes_spaced_values() -> None:
    command = [
        "scripts/prepare-review-round",
        "--profile",
        "supervisor_report",
        "--authorization-note",
        "approved by supervisor",
        "case-a",
        "round-a",
    ]

    rendered = review_round_closeout.logical_command_display(command)

    assert rendered == (
        "prepare-review-round --profile supervisor_report --authorization-note "
        "'approved by supervisor' case-a round-a"
    )


def test_commands_run_step_terminates_process_tree_on_interrupt(monkeypatch, tmp_path: Path) -> None:
    events: list[str] = []

    class FakeProcess:
        pid = 12345
        returncode = None
        stdout = None

        def communicate(self):
            raise KeyboardInterrupt

        def poll(self):
            return None

        def wait(self, timeout=None):
            events.append(f"wait:{timeout}")
            self.returncode = -15
            return self.returncode

    def fake_popen(*args, **kwargs):
        events.append("popen")
        return FakeProcess()

    monkeypatch.setattr(commands.subprocess, "Popen", fake_popen)

    def fake_terminate(process) -> bool:
        events.append(f"terminated:{process.pid}")
        return True

    monkeypatch.setattr(commands, "terminate_process_tree", fake_terminate)

    try:
        commands.run_step(tmp_path, "Interrupted helper", ["scripts/check-private"])
    except KeyboardInterrupt:
        pass
    else:
        raise AssertionError("expected KeyboardInterrupt")

    assert events == ["popen", "terminated:12345"]


def test_commands_run_step_process_group_mode(monkeypatch, tmp_path: Path) -> None:
    captured: list[dict[str, object]] = []

    class FakeProcess:
        pid = 12345
        returncode = 0

        def communicate(self):
            return ("ok", None)

    def fake_popen(*args, **kwargs):
        captured.append(kwargs)
        return FakeProcess()

    monkeypatch.setattr(commands.os, "name", "posix")
    monkeypatch.delenv(commands.PROCESS_GROUP_MODE_ENV, raising=False)
    monkeypatch.setattr(commands.subprocess, "Popen", fake_popen)

    commands.run_step(tmp_path, "Default group", ["scripts/check-private"])
    assert captured[-1]["start_new_session"] is True

    monkeypatch.setenv(commands.PROCESS_GROUP_MODE_ENV, commands.PROCESS_GROUP_MODE_INHERIT)
    commands.run_step(tmp_path, "Inherited group", ["scripts/check-private"])
    assert "start_new_session" not in captured[-1]


def test_commands_run_step_merges_extra_env_without_changing_spawn_mode(monkeypatch, tmp_path: Path) -> None:
    captured: list[dict[str, object]] = []

    class FakeProcess:
        pid = 12345
        returncode = 0

        def communicate(self):
            return ("ok", None)

    def fake_popen(*args, **kwargs):
        captured.append(kwargs)
        return FakeProcess()

    monkeypatch.setattr(commands.os, "name", "posix")
    monkeypatch.delenv(commands.PROCESS_GROUP_MODE_ENV, raising=False)
    monkeypatch.setattr(commands.subprocess, "Popen", fake_popen)

    commands.run_step(
        tmp_path,
        "Env merge",
        ["scripts/check-private"],
        extra_env={commands.PROCESS_GROUP_MODE_ENV: commands.PROCESS_GROUP_MODE_INHERIT},
    )

    env = captured[-1]["env"]
    assert isinstance(env, dict)
    assert env[commands.PROCESS_GROUP_MODE_ENV] == commands.PROCESS_GROUP_MODE_INHERIT
    assert "PYTHONPATH" in env
    assert captured[-1]["start_new_session"] is True


def test_commands_run_step_windows_process_group_mode(monkeypatch, tmp_path: Path) -> None:
    captured: list[dict[str, object]] = []

    class FakeProcess:
        pid = 12345
        returncode = 0

        def communicate(self):
            return ("ok", None)

    def fake_popen(*args, **kwargs):
        captured.append(kwargs)
        return FakeProcess()

    monkeypatch.setattr(commands.os, "name", "nt")
    monkeypatch.setattr(commands.subprocess, "CREATE_NEW_PROCESS_GROUP", 512, raising=False)
    monkeypatch.delenv(commands.PROCESS_GROUP_MODE_ENV, raising=False)
    monkeypatch.setattr(commands.subprocess, "Popen", fake_popen)

    commands.run_step(tmp_path, "Default Windows group", ["scripts/check-private"])
    assert captured[-1]["creationflags"] == 512

    monkeypatch.setenv(commands.PROCESS_GROUP_MODE_ENV, commands.PROCESS_GROUP_MODE_INHERIT)
    commands.run_step(tmp_path, "Inherited Windows group", ["scripts/check-private"])
    assert "creationflags" not in captured[-1]


def test_commands_terminate_process_tree_reaps_posix_after_force_kill(monkeypatch) -> None:
    events: list[tuple[str, object]] = []

    class FakeProcess:
        pid = 12345
        returncode = None
        wait_calls = 0

        def poll(self):
            return self.returncode

        def wait(self, timeout=None):
            self.wait_calls += 1
            events.append(("wait", timeout))
            if self.wait_calls == 1:
                raise commands.subprocess.TimeoutExpired(cmd="helper", timeout=timeout)
            self.returncode = -9
            return self.returncode

        def kill(self):
            events.append(("kill", None))
            self.returncode = -9

    monkeypatch.setattr(commands.os, "name", "posix")
    monkeypatch.setattr(commands.os, "killpg", lambda pid, sig: events.append(("killpg", sig)))

    assert commands.terminate_process_tree(cast(subprocess.Popen[str], FakeProcess()), timeout=0.1) is True
    assert events == [
        ("killpg", commands.signal.SIGTERM),
        ("wait", 0.1),
        ("killpg", commands.signal.SIGKILL),
        ("wait", 0.1),
    ]


def test_commands_terminate_process_tree_reaps_windows_after_taskkill(monkeypatch) -> None:
    events: list[tuple[str, object]] = []

    class FakeProcess:
        pid = 12345
        returncode = None
        wait_calls = 0

        def poll(self):
            return self.returncode

        def send_signal(self, signal_value):
            events.append(("signal", signal_value))

        def wait(self, timeout=None):
            self.wait_calls += 1
            events.append(("wait", timeout))
            if self.wait_calls == 1:
                raise commands.subprocess.TimeoutExpired(cmd="helper", timeout=timeout)
            self.returncode = -9
            return self.returncode

    def fake_run(command, **kwargs):
        events.append(("taskkill", command))
        return None

    monkeypatch.setattr(commands.os, "name", "nt")
    monkeypatch.setattr(commands.signal, "CTRL_BREAK_EVENT", 1, raising=False)
    monkeypatch.setattr(commands.subprocess, "run", fake_run)

    assert commands.terminate_process_tree(cast(subprocess.Popen[str], FakeProcess()), timeout=0.1) is True
    assert events == [
        ("signal", 1),
        ("wait", 0.1),
        ("taskkill", ["taskkill", "/PID", "12345", "/T", "/F"]),
        ("wait", 0.1),
    ]
