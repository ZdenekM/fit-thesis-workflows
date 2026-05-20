import json
from pathlib import Path

from thesis_review_workflow.artifact_validation import sha256_file
from thesis_review_workflow.cli import refresh_round_hashes
from thesis_review_workflow.review_packets import (
    COMMON_BRIEFING_REL,
    validate_common_briefing_artifact,
    write_common_briefing,
)
from thesis_review_workflow.report_calibration import REPORT_CALIBRATION_BASIS_REL


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


def test_refresh_round_hashes_preserves_supervisor_report_common_briefing_scope(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, round_dir = make_round(tmp_path)
    monkeypatch.setattr(refresh_round_hashes, "repo_root", lambda: root)
    basis = round_dir / REPORT_CALIBRATION_BASIS_REL
    basis.parent.mkdir(parents=True, exist_ok=True)
    basis.write_text('{"schema_version": "report-calibration-basis-v1"}\n', encoding="utf-8")
    write_common_briefing(
        "case-a",
        "round-a",
        "2026-05-18T10:00:00Z",
        round_dir,
        workflow_profile="supervisor_report",
    )
    (round_dir / "notes" / "assignment.md").write_text("# Assignment\n\nEdited note.\n", encoding="utf-8")

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
    payload = json.loads((round_dir / COMMON_BRIEFING_REL).read_text(encoding="utf-8"))
    assert payload["workflow_profile"] == "supervisor_report"
    assert payload["report_calibration_scope"] == "not_applicable"
    assert payload["report_calibration_sources"] == []
    for field in ("snapshot_refs", "advisory_artifacts", "context_handoffs"):
        assert REPORT_CALIBRATION_BASIS_REL not in {item["path"] for item in payload[field]}


def test_refresh_round_hashes_updates_report_calibration_source_refs(tmp_path: Path, monkeypatch) -> None:
    root, round_dir = make_round(tmp_path)
    monkeypatch.setattr(refresh_round_hashes, "repo_root", lambda: root)
    feedback = round_dir / "notes" / "opponent-report-operator-feedback.md"
    feedback.write_text("# Operator calibration\n\nInitial.\n", encoding="utf-8")
    review_delta = round_dir / "work" / "review_deltas" / "report-calibration.json"
    review_delta.parent.mkdir(parents=True)
    review_delta.write_text('{"schema_version":"review-delta-v1","state":"initial"}\n', encoding="utf-8")
    write_common_briefing("case-a", "round-a", "2026-05-18T10:00:00Z", round_dir)
    feedback.write_text("# Operator calibration\n\nEdited.\n", encoding="utf-8")
    review_delta.write_text('{"schema_version":"review-delta-v1","state":"edited"}\n', encoding="utf-8")

    stale_errors = validate_common_briefing_artifact(round_dir, case_id="case-a", round_id="round-a")
    assert any("sha256 is stale for notes/opponent-report-operator-feedback.md" in error for error in stale_errors)
    assert any("sha256 is stale for work/review_deltas/report-calibration.json" in error for error in stale_errors)

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
    payload = json.loads((round_dir / COMMON_BRIEFING_REL).read_text(encoding="utf-8"))
    sources = {item["path"]: item for item in payload["report_calibration_sources"]}
    assert sources["notes/opponent-report-operator-feedback.md"]["sha256"] == sha256_file(feedback)
    assert sources["work/review_deltas/report-calibration.json"]["sha256"] == sha256_file(review_delta)


def test_refresh_round_hashes_detects_new_report_calibration_delta_after_briefing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, round_dir = make_round(tmp_path)
    monkeypatch.setattr(refresh_round_hashes, "repo_root", lambda: root)
    write_common_briefing("case-a", "round-a", "2026-05-18T10:00:00Z", round_dir)
    review_delta = round_dir / "work" / "review_deltas" / "report-calibration.json"
    review_delta.parent.mkdir(parents=True)
    review_delta.write_text('{"schema_version":"review-delta-v1","state":"new"}\n', encoding="utf-8")

    stale_errors = validate_common_briefing_artifact(round_dir, case_id="case-a", round_id="round-a")
    assert any(
        "report_calibration_sources missing current source work/review_deltas/report-calibration.json" in error
        for error in stale_errors
    )

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
    payload = json.loads((round_dir / COMMON_BRIEFING_REL).read_text(encoding="utf-8"))
    sources = {item["path"]: item for item in payload["report_calibration_sources"]}
    assert sources["work/review_deltas/report-calibration.json"]["sha256"] == sha256_file(review_delta)


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


def test_refresh_round_hashes_updates_common_briefing_after_bundle_inventory_refresh(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root, round_dir = make_round(tmp_path)
    monkeypatch.setattr(refresh_round_hashes, "repo_root", lambda: root)
    inventory = round_dir / "work" / "submission_bundle_inventory.json"
    summary = round_dir / "work" / "submission_bundle_inventory.md"
    inventory.parent.mkdir(parents=True)
    inventory.write_text(
        json.dumps(
            {
                "schema_version": "submission-bundle-inventory-v1",
                "case_id": "case-a",
                "round_id": "round-a",
                "generated_at": "2026-05-19T12:00:00Z",
                "producer": "scripts/review-round-start",
                "limits": {},
                "source_bundles": [],
                "candidates": [],
                "skipped_entries": [],
                "summary": {},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    summary.write_text("# Submission Bundle Inventory\n", encoding="utf-8")
    write_common_briefing("case-a", "round-a", "2026-05-18T10:00:00Z", round_dir)
    inventory.write_text(
        json.dumps(
            {
                "schema_version": "submission-bundle-inventory-v1",
                "case_id": "case-a",
                "round_id": "round-a",
                "generated_at": "2026-05-19T12:01:00Z",
                "producer": "scripts/review-round-start",
                "limits": {},
                "source_bundles": [],
                "candidates": [
                    {
                        "candidate_id": "sb-readme",
                        "candidate_ref": "inputs/submission.zip!README.md",
                        "artifact_class": "readme_candidate",
                        "state": "materialize_candidate",
                    }
                ],
                "skipped_entries": [],
                "summary": {},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    stale_errors = validate_common_briefing_artifact(round_dir, case_id="case-a", round_id="round-a")
    assert any("sha256 is stale for work/submission_bundle_inventory.json" in error for error in stale_errors)

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
