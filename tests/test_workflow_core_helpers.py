import os
import sys
from pathlib import Path

from thesis_review_workflow.cases import MissingCurrentRound, read_current_round, resolve_round
from thesis_review_workflow.cli import check_reviewer_profile, check_tooling
from thesis_review_workflow.commands import (
    Step,
    canonical_command_args,
    canonical_command_text,
    command_display,
    compact_output,
    repo_command_environment,
    resolve_repo_command,
    workflow_command_module,
)
from thesis_review_workflow.ids import invalid_id_message, is_valid_id, validate_id
from thesis_review_workflow.metadata import read_fields, resolve_thesis_language
from thesis_review_workflow.paths import caller_cwd, rel_repo, rel_round, resolve_caller_path, strict_rel_round


def test_workflow_ids_accept_safe_case_and_round_names() -> None:
    assert is_valid_id("abc")
    assert is_valid_id("a.b_c-1")


def test_workflow_ids_reject_path_like_or_dot_only_names() -> None:
    for value in ["", "../x", "/tmp/x", ".", ".."]:
        assert not is_valid_id(value)
        try:
            validate_id("CASE_ID", value)
        except ValueError as exc:
            assert str(exc).startswith("Invalid CASE_ID")
        else:
            raise AssertionError(f"Expected invalid workflow id: {value}")


def test_invalid_id_message_matches_cli_contract() -> None:
    assert (
        invalid_id_message("ROUND_ID")
        == "Invalid ROUND_ID. Use only letters, numbers, dot, underscore, and dash; dot-only ids are not allowed."
    )


def test_read_current_round_strips_content_and_allows_missing_file(tmp_path: Path) -> None:
    assert read_current_round(tmp_path) is None
    (tmp_path / "current-round.txt").write_text("round-a\n", encoding="utf-8")
    assert read_current_round(tmp_path) == "round-a"


def test_resolve_round_prefers_explicit_round_without_current_round(tmp_path: Path) -> None:
    assert resolve_round(tmp_path, "round-a") == "round-a"


def test_resolve_round_reads_current_round(tmp_path: Path) -> None:
    (tmp_path / "current-round.txt").write_text("round-a\n", encoding="utf-8")
    assert resolve_round(tmp_path, None) == "round-a"


def test_resolve_round_reports_missing_current_round(tmp_path: Path) -> None:
    try:
        resolve_round(tmp_path, None)
    except MissingCurrentRound as exc:
        assert str(exc) == f"Missing current round: {tmp_path}/current-round.txt"
    else:
        raise AssertionError("Expected missing current round error")


def test_resolve_round_rejects_invalid_current_round(tmp_path: Path) -> None:
    (tmp_path / "current-round.txt").write_text("...\n", encoding="utf-8")

    try:
        resolve_round(tmp_path, None)
    except ValueError as exc:
        assert str(exc).startswith("Invalid ROUND_ID")
    else:
        raise AssertionError("Expected invalid current round error")


def test_read_fields_preserves_simple_case_metadata_contract(tmp_path: Path) -> None:
    path = tmp_path / "case.md"
    path.write_text(
        "\n".join(
            [
                "# Case",
                "Work type: DP",
                "Student feedback language: cs",
                "Note without separator",
                "Reviewer profile: default:extended",
            ]
        ),
        encoding="utf-8",
    )

    assert read_fields(path) == {
        "work type": "DP",
        "student feedback language": "cs",
        "reviewer profile": "default:extended",
    }


def test_resolve_thesis_language_preserves_slovak_display_and_ignores_feedback_language(tmp_path: Path) -> None:
    case_dir = tmp_path / "cases" / "case-a"
    round_dir = case_dir / "rounds" / "round-a"
    round_dir.mkdir(parents=True)
    (case_dir / "case.md").write_text(
        "Thesis language: sk\nStudent feedback language: cs\n",
        encoding="utf-8",
    )

    resolved = resolve_thesis_language(case_dir, round_dir)

    assert resolved.display_language == "sk"
    assert resolved.rule_family == "cs_sk"
    assert resolved.source_path == case_dir / "case.md"


def test_resolve_thesis_language_uses_round_notes_only_after_case_auto(tmp_path: Path) -> None:
    case_dir = tmp_path / "cases" / "case-a"
    round_dir = case_dir / "rounds" / "round-a"
    notes = round_dir / "notes"
    notes.mkdir(parents=True)
    (case_dir / "case.md").write_text("Thesis language: auto\n", encoding="utf-8")
    (notes / "round-notes.md").write_text("Thesis language: en\n", encoding="utf-8")
    (notes / "supervisor-intake.md").write_text("Thesis language: cs\n", encoding="utf-8")

    resolved = resolve_thesis_language(case_dir, round_dir)

    assert resolved.display_language == "en"
    assert resolved.rule_family == "en"
    assert resolved.source_path == notes / "round-notes.md"


def test_resolve_thesis_language_ignores_free_form_intake_metadata(tmp_path: Path) -> None:
    case_dir = tmp_path / "cases" / "case-a"
    round_dir = case_dir / "rounds" / "round-a"
    notes = round_dir / "notes"
    notes.mkdir(parents=True)
    (case_dir / "case.md").write_text("Thesis language: auto\n", encoding="utf-8")
    (notes / "supervisor-intake.md").write_text("Thesis language: en\n", encoding="utf-8")

    resolved = resolve_thesis_language(case_dir, round_dir)

    assert resolved.display_language == "auto"
    assert resolved.rule_family == "auto"
    assert resolved.source_path == case_dir / "case.md"


def test_resolve_thesis_language_does_not_override_invalid_case_metadata(tmp_path: Path) -> None:
    case_dir = tmp_path / "cases" / "case-a"
    round_dir = case_dir / "rounds" / "round-a"
    notes = round_dir / "notes"
    notes.mkdir(parents=True)
    (case_dir / "case.md").write_text("Thesis language: klingon\n", encoding="utf-8")
    (notes / "round-notes.md").write_text("Thesis language: en\n", encoding="utf-8")

    resolved = resolve_thesis_language(case_dir, round_dir)

    assert resolved.display_language == "auto"
    assert resolved.rule_family == "auto"
    assert resolved.source_path == case_dir / "case.md"
    assert resolved.warnings


def test_rel_helpers_preserve_relative_and_fallback_behavior(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    round_path = root / "cases" / "case-a" / "rounds" / "round-a"
    inside = round_path / "outputs" / "feedback.md"
    outside = tmp_path / "outside.md"

    assert rel_repo(root, inside) == "cases/case-a/rounds/round-a/outputs/feedback.md"
    assert rel_round(round_path, inside) == "outputs/feedback.md"
    assert rel_repo(root, outside) == outside.as_posix()
    assert rel_round(round_path, outside) == outside.as_posix()

    try:
        strict_rel_round(round_path, outside)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected strict round-relative path failure")


def test_resolve_caller_path_uses_recorded_invocation_cwd(tmp_path: Path, monkeypatch) -> None:
    caller = tmp_path / "caller"
    repo = tmp_path / "repo"
    caller.mkdir()
    repo.mkdir()
    monkeypatch.chdir(repo)
    monkeypatch.setenv("THESIS_REVIEW_CALLER_CWD", str(caller))

    assert caller_cwd() == caller
    assert resolve_caller_path("input.pdf") == caller / "input.pdf"
    assert resolve_caller_path(str(tmp_path / "absolute.pdf")) == tmp_path / "absolute.pdf"


def test_step_status_distinguishes_required_and_optional_failures() -> None:
    assert Step(label="ok", command=None, returncode=0, output="done").status == "PASS"
    assert Step(label="required", command=None, returncode=1, output="bad", required=True).status == "FAIL"
    assert Step(label="optional", command=None, returncode=1, output="bad", required=False).status == "WARN"


def test_command_display_allows_synthetic_steps_without_commands() -> None:
    assert command_display(None) == ""
    assert command_display(["scripts/check-private"]) == "check-private"
    assert command_display(["scripts/prepare-review-round", "--authorization-note", "approved by supervisor"]) == (
        "prepare-review-round --authorization-note 'approved by supervisor'"
    )


def test_command_display_uses_windows_packaged_launcher(monkeypatch) -> None:
    import thesis_review_workflow.commands as commands

    monkeypatch.setattr(commands.os, "name", "nt", raising=False)

    assert (
        command_display(["scripts/init-review-manifest", "--run-checks", "case-a", "round-a"])
        == ".\\dist\\workflow-tools\\bin\\init-review-manifest.cmd --run-checks case-a round-a"
    )


def test_canonical_command_normalizes_workflow_wrappers() -> None:
    assert canonical_command_args(["scripts/check-private"]) == ["check-private"]
    assert canonical_command_args(["check-private"]) == ["check-private"]
    assert canonical_command_text("scripts/init-review-manifest --run-checks case-a round-a") == (
        "init-review-manifest --run-checks case-a round-a"
    )
    assert canonical_command_text(r"dist\workflow-tools\bin\check-opponent-report.cmd case-a round-a") == (
        "check-opponent-report case-a round-a"
    )
    assert (
        canonical_command_text(r".\dist\workflow-tools\bin\check-review-manifest.ps1 --require-complete case-a round-a")
        == "check-review-manifest --require-complete case-a round-a"
    )
    assert workflow_command_module(r"dist\workflow-tools\bin\check-private.cmd") == (
        "thesis_review_workflow.cli.check_private"
    )


def test_compact_output_drops_blank_lines_and_truncates() -> None:
    assert compact_output(" first\n\nsecond \n", limit=100) == " first\nsecond"
    assert compact_output("abcdef", limit=5) == "ab..."


def test_resolve_repo_command_uses_python_modules_for_workflow_commands(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    script = root / "scripts" / "check-private"
    script.parent.mkdir(parents=True)
    script.write_text("#!/usr/bin/env bash\n", encoding="utf-8")

    assert resolve_repo_command(root, ["scripts/check-private"]) == [
        sys.executable,
        "-m",
        "thesis_review_workflow.cli.check_private",
    ]
    assert resolve_repo_command(root, ["git", "diff", "--check"]) == ["git", "diff", "--check"]


def test_repo_command_environment_prepends_repo_src(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    env = repo_command_environment(root)

    assert env["PYTHONPATH"].split(os.pathsep)[0] == str(root / "src")


def test_python_reviewer_profile_rejects_parent_marker_in_local_profile(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "repo"
    case = root / "cases" / "case-a"
    profile = root / "profiles" / "local" / "a..b.md"
    case.mkdir(parents=True)
    profile.parent.mkdir(parents=True)
    (root / "profiles" / "default.md").write_text("# Default\n", encoding="utf-8")
    profile.write_text("# Local\n", encoding="utf-8")
    (case / "case.md").write_text("Reviewer profile: local/a..b\n", encoding="utf-8")

    monkeypatch.setattr(check_reviewer_profile, "repo_root", lambda: root)

    assert check_reviewer_profile.main(["scripts/check-reviewer-profile", "case-a"]) == 1


def test_tooling_pdf_extract_count_uses_shared_non_guessing_matcher() -> None:
    assert (
        check_tooling.count_missing_pdf_extracts(
            [Path("inputs/report.pdf")],
            [Path("extracted/report.txt")],
        )
        == 0
    )
    assert (
        check_tooling.count_missing_pdf_extracts(
            [Path("inputs/report.pdf"), Path("inputs/appendix.pdf")],
            [Path("extracted/report.txt")],
        )
        == 1
    )
    assert (
        check_tooling.count_missing_pdf_extracts(
            [Path("inputs/report.pdf"), Path("inputs/appendix.pdf")],
            [Path("extracted/only-extract.txt")],
        )
        == 2
    )
