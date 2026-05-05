from pathlib import Path

from thesis_review_workflow.cases import MissingCurrentRound, read_current_round, resolve_round
from thesis_review_workflow.ids import invalid_id_message, is_valid_id, validate_id
from thesis_review_workflow.metadata import read_fields
from thesis_review_workflow.paths import rel_repo, rel_round, strict_rel_round


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
