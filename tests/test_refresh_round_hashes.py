import json
from pathlib import Path

from thesis_review_workflow.artifact_validation import sha256_file
from thesis_review_workflow.cli import refresh_round_hashes
from thesis_review_workflow.review_packets import (
    COMMON_BRIEFING_REL,
    validate_common_briefing_artifact,
    write_common_briefing,
)


def make_round(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    case_dir = root / "cases" / "case-a"
    round_dir = case_dir / "rounds" / "round-a"
    notes = round_dir / "notes" / "assignment.md"
    notes.parent.mkdir(parents=True)
    notes.write_text("# Assignment\n\nInitial note.\n", encoding="utf-8")
    case_dir.joinpath("case.md").write_text("Reviewer profile: default\n", encoding="utf-8")
    case_dir.joinpath("current-round.txt").write_text("round-a\n", encoding="utf-8")
    return root, round_dir


def test_refresh_round_hashes_updates_common_briefing_after_note_edit(tmp_path: Path, monkeypatch) -> None:
    root, round_dir = make_round(tmp_path)
    monkeypatch.setattr(refresh_round_hashes, "repo_root", lambda: root)
    write_common_briefing("case-a", "round-a", "2026-05-18T10:00:00Z", round_dir)
    before = sha256_file(round_dir / COMMON_BRIEFING_REL)
    (round_dir / "notes" / "assignment.md").write_text("# Assignment\n\nEdited note.\n", encoding="utf-8")

    stale_errors = validate_common_briefing_artifact(round_dir, case_id="case-a", round_id="round-a")
    assert any("sha256 is stale for notes/assignment.md" in error for error in stale_errors)

    result = refresh_round_hashes.main(
        [
            "--generated-at",
            "2026-05-18T10:01:00Z",
            "case-a",
            "round-a",
        ]
    )

    assert result == 0
    assert validate_common_briefing_artifact(round_dir, case_id="case-a", round_id="round-a") == []
    assert sha256_file(round_dir / COMMON_BRIEFING_REL) != before
    payload = json.loads((round_dir / COMMON_BRIEFING_REL).read_text(encoding="utf-8"))
    assignment = next(item for item in payload["base_inputs"] if item["path"] == "notes/assignment.md")
    assert assignment["sha256"] == sha256_file(round_dir / "notes" / "assignment.md")


def test_refresh_round_hashes_does_not_modify_approval_records(tmp_path: Path, monkeypatch) -> None:
    root, round_dir = make_round(tmp_path)
    monkeypatch.setattr(refresh_round_hashes, "repo_root", lambda: root)
    approval = round_dir / "work" / "reviews" / "opponent_report_review.json"
    approval.parent.mkdir(parents=True)
    approval.write_text('{"verdict":"approved","notes":"operator wording"}\n', encoding="utf-8")
    approval_before = approval.read_text(encoding="utf-8")

    result = refresh_round_hashes.main(
        [
            "--generated-at",
            "2026-05-18T10:01:00Z",
            "case-a",
            "round-a",
        ]
    )

    assert result == 0
    assert approval.read_text(encoding="utf-8") == approval_before


def test_refresh_round_hashes_refuses_to_bless_changed_review_outputs(tmp_path: Path, monkeypatch, capsys) -> None:
    root, round_dir = make_round(tmp_path)
    monkeypatch.setattr(refresh_round_hashes, "repo_root", lambda: root)
    output = round_dir / "outputs" / "oponent_podklady_revidovane.md"
    output.parent.mkdir(parents=True)
    output.write_text("# Reviewed materials\n", encoding="utf-8")
    write_common_briefing("case-a", "round-a", "2026-05-18T10:00:00Z", round_dir)
    output.write_text("# Edited reviewed materials\n", encoding="utf-8")

    result = refresh_round_hashes.main(
        [
            "--generated-at",
            "2026-05-18T10:01:00Z",
            "case-a",
            "round-a",
        ]
    )

    assert result == 1
    captured = capsys.readouterr()
    assert "refusing to refresh hash for outputs/oponent_podklady_revidovane.md" in captured.out
    assert "record a review delta or rerun the relevant review/check" in captured.out
