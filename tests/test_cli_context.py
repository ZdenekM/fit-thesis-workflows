import json
from pathlib import Path

from thesis_review_workflow.cli import context


def capture_exit(func, *args, **kwargs) -> SystemExit:
    try:
        func(*args, **kwargs)
    except SystemExit as exc:
        return exc
    raise AssertionError("Expected SystemExit")


def test_cli_context_prints_stderr_for_invalid_id(capsys) -> None:
    exc = capture_exit(context.validate_id, "CASE_ID", "../case", stderr=True)

    assert exc.code == 2
    assert "Invalid CASE_ID" in capsys.readouterr().err


def test_cli_context_preserves_textual_exit_for_invalid_id_without_stderr(capsys) -> None:
    exc = capture_exit(context.validate_id, "CASE_ID", "../case")

    assert "Invalid CASE_ID" in str(exc)
    assert capsys.readouterr().err == ""


def test_cli_context_resolves_current_round_and_reports_missing(capsys, tmp_path: Path) -> None:
    exc = capture_exit(context.resolve_round, tmp_path, None, stderr=True)

    assert exc.code == 2
    assert f"Missing current round: {tmp_path}/current-round.txt" in capsys.readouterr().err

    (tmp_path / "current-round.txt").write_text("round-a\n", encoding="utf-8")
    assert context.resolve_round(tmp_path, None, stderr=True) == "round-a"


def test_cli_context_preserves_textual_exit_for_missing_current_round(tmp_path: Path) -> None:
    exc = capture_exit(context.resolve_round, tmp_path, None)

    assert str(exc) == f"Missing current round: {tmp_path}/current-round.txt"


def test_cli_context_case_and_round_errors_can_return_usage_status(capsys, tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    case_exc = capture_exit(context.require_case_dir, root, "case-a", error_prefix="ERROR: ", stderr=True)

    assert case_exc.code == 2
    assert "ERROR: Case does not exist: cases/case-a" in capsys.readouterr().err

    case_dir = root / "cases" / "case-a"
    case_dir.mkdir(parents=True)
    round_exc = capture_exit(
        context.require_round_dir,
        case_dir,
        "case-a",
        "round-a",
        error_prefix="ERROR: ",
        stderr=True,
    )

    assert round_exc.code == 2
    assert "ERROR: Round does not exist: cases/case-a/rounds/round-a" in capsys.readouterr().err


def test_load_json_manifest_preserves_manifest_error_contracts(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    missing_exc = capture_exit(
        context.load_json_manifest,
        missing,
        label="work/review_manifest.json",
        missing_message="ERROR: Missing review manifest: work/review_manifest.json",
        not_object_message="ERROR: Review manifest must be a JSON object: work/review_manifest.json",
    )
    assert str(missing_exc) == "ERROR: Missing review manifest: work/review_manifest.json"

    manifest = tmp_path / "manifest.json"
    manifest.write_text("[]\n", encoding="utf-8")
    type_exc = capture_exit(
        context.load_json_manifest,
        manifest,
        label="work/review_manifest.json",
        missing_message="ERROR: Missing review manifest: work/review_manifest.json",
        not_object_message="ERROR: Review manifest must be a JSON object: work/review_manifest.json",
    )
    assert str(type_exc) == "ERROR: Review manifest must be a JSON object: work/review_manifest.json"

    manifest.write_text(json.dumps({"ok": True}), encoding="utf-8")
    assert context.load_json_manifest(
        manifest,
        label="work/review_manifest.json",
        missing_message="ERROR: Missing review manifest: work/review_manifest.json",
        not_object_message="ERROR: Review manifest must be a JSON object: work/review_manifest.json",
    ) == {"ok": True}
