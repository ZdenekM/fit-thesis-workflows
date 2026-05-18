from pathlib import Path

from thesis_review_workflow.operation_log import (
    OPERATION_LOG_REL,
    append_operation,
    operation_log_summary_lines,
    validate_operation_log,
)


def test_operation_log_append_validate_and_summarize(tmp_path: Path) -> None:
    round_dir = tmp_path / "cases" / "case-a" / "rounds" / "round-a"
    append_operation(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        operation="figure-media-role",
        status="failed",
        actor="codex",
        summary="Role agent ended without output files.",
        command="spawn thesis_figure_media_reviewer",
        artifacts=["outputs/figure_media_review.md", "outputs/figure_media_review.md"],
        checks=["check-figure-media-review"],
        details={"next_action": "rerun_role"},
    )

    assert (round_dir / OPERATION_LOG_REL).is_file()
    assert validate_operation_log(round_dir, case_id="case-a", round_id="round-a") == []

    lines = operation_log_summary_lines(round_dir, case_id="case-a", round_id="round-a")
    assert lines[0] == "- operation log: present (1 event(s)); latest first"
    assert "failed figure-media-role by codex: Role agent ended without output files." in lines[1]


def test_operation_log_validation_rejects_wrong_case(tmp_path: Path) -> None:
    round_dir = tmp_path / "cases" / "case-a" / "rounds" / "round-a"
    append_operation(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        operation="literature-source-acquisition",
        status="blocked",
        actor="operator",
        summary="External source resolution was not authorized.",
    )

    errors = validate_operation_log(round_dir, case_id="other-case", round_id="round-a")
    assert any("case_id does not match requested case" in error for error in errors)
