import json
from pathlib import Path

from thesis_review_workflow.artifact_validation import sha256_file
from thesis_review_workflow.cli import check_theses_checker_summary, record_theses_checker_summary
from thesis_review_workflow.theses_checker_summary import (
    THESES_CHECKER_SUMMARY_REL,
    THESES_CHECKER_SUMMARY_SCHEMA,
    validate_theses_checker_summary_artifact,
)


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def make_round(root: Path) -> Path:
    case_dir = root / "cases" / "case-a"
    round_dir = case_dir / "rounds" / "round-a"
    write_text(case_dir / "case.md", "# Case\nReviewer profile: default\n")
    write_text(case_dir / "current-round.txt", "round-a\n")
    write_text(round_dir / "notes" / "theses-checker-output.txt", "Normostrany: 42.5\n")
    write_text(round_dir / "inputs" / "thesis.pdf", "Rendered thesis PDF fixture\n")
    return round_dir


def test_record_and_check_theses_checker_summary_bind_source_hashes(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "repo"
    round_dir = make_round(root)
    monkeypatch.setattr(record_theses_checker_summary, "repo_root", lambda: root)
    monkeypatch.setattr(check_theses_checker_summary, "repo_root", lambda: root)

    result = record_theses_checker_summary.main(
        [
            "record-theses-checker-summary",
            "--source",
            "notes/theses-checker-output.txt",
            "--source-kind",
            "copied_text",
            "--checked-pdf",
            "inputs/thesis.pdf",
            "--normostrany",
            "42.5",
            "--status",
            "within_required_range",
            "--minimum",
            "30",
            "--recommended-minimum",
            "35",
            "case-a",
            "round-a",
        ]
    )

    assert result == 0
    summary_path = round_dir / THESES_CHECKER_SUMMARY_REL
    loaded = json.loads(summary_path.read_text(encoding="utf-8"))
    assert loaded["schema_version"] == THESES_CHECKER_SUMMARY_SCHEMA
    assert loaded["source_artifact"]["sha256"] == sha256_file(round_dir / "notes/theses-checker-output.txt")
    assert loaded["checked_pdf"]["sha256"] == sha256_file(round_dir / "inputs/thesis.pdf")
    assert check_theses_checker_summary.main(["check-theses-checker-summary", "case-a", "round-a"]) == 0

    write_text(round_dir / "notes" / "theses-checker-output.txt", "Normostrany: changed\n")

    errors = validate_theses_checker_summary_artifact(round_dir, case_id="case-a", round_id="round-a")
    assert any("source_artifact: sha256 is stale" in error for error in errors)


def test_record_theses_checker_summary_accepts_typed_pdf_limitation(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "repo"
    round_dir = make_round(root)
    monkeypatch.setattr(record_theses_checker_summary, "repo_root", lambda: root)

    result = record_theses_checker_summary.main(
        [
            "record-theses-checker-summary",
            "--source",
            "notes/theses-checker-output.txt",
            "--checked-pdf-limitation",
            "source_does_not_identify_pdf",
            "--checked-pdf-limitation-note",
            "The saved checker output did not identify the rendered PDF.",
            "--normostrany",
            "42.5",
            "--status",
            "unknown_threshold",
            "case-a",
            "round-a",
        ]
    )

    assert result == 0
    loaded = json.loads((round_dir / THESES_CHECKER_SUMMARY_REL).read_text(encoding="utf-8"))
    assert loaded["checked_pdf"] is None
    assert loaded["checked_pdf_limitation"]["type"] == "source_does_not_identify_pdf"


def test_theses_checker_summary_rejects_non_finite_and_inconsistent_numbers(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    round_dir = make_round(root)
    source = round_dir / "notes" / "theses-checker-output.txt"
    checked_pdf = round_dir / "inputs" / "thesis.pdf"
    payload = {
        "schema_version": THESES_CHECKER_SUMMARY_SCHEMA,
        "case_id": "case-a",
        "round_id": "round-a",
        "generated_at": "2026-05-20T00:00:00Z",
        "producer_type": "deterministic_helper",
        "producer_role": "record-theses-checker-summary",
        "producer_agent": "record-theses-checker-summary",
        "source_refs": ["notes/theses-checker-output.txt", "inputs/thesis.pdf"],
        "source_artifact": {
            "path": "notes/theses-checker-output.txt",
            "sha256": sha256_file(source),
            "kind": "copied_text",
        },
        "checked_pdf": {"path": "inputs/thesis.pdf", "sha256": sha256_file(checked_pdf)},
        "checked_pdf_limitation": None,
        "normostrany": float("nan"),
        "thresholds": {"minimum": 30, "recommended_minimum": 20, "maximum": 80},
        "status": "below_required_minimum",
        "checker_timestamp": None,
        "captured_at": "2026-05-20T00:00:00Z",
        "limitations": [],
    }
    write_text(round_dir / THESES_CHECKER_SUMMARY_REL, json.dumps(payload) + "\n")

    errors = validate_theses_checker_summary_artifact(round_dir, case_id="case-a", round_id="round-a")

    assert any("normostrany must be a positive number" in error for error in errors)
    assert any("thresholds.recommended_minimum must be >= thresholds.minimum" in error for error in errors)


def test_theses_checker_summary_rejects_non_pdf_checked_pdf(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    round_dir = make_round(root)
    checked_text = write_text(round_dir / "inputs" / "thesis.txt", "not a rendered PDF\n")
    payload = {
        "schema_version": THESES_CHECKER_SUMMARY_SCHEMA,
        "case_id": "case-a",
        "round_id": "round-a",
        "generated_at": "2026-05-20T00:00:00Z",
        "producer_type": "deterministic_helper",
        "producer_role": "record-theses-checker-summary",
        "producer_agent": "record-theses-checker-summary",
        "source_refs": ["notes/theses-checker-output.txt", "inputs/thesis.txt"],
        "source_artifact": {
            "path": "notes/theses-checker-output.txt",
            "sha256": sha256_file(round_dir / "notes" / "theses-checker-output.txt"),
            "kind": "copied_text",
        },
        "checked_pdf": {"path": "inputs/thesis.txt", "sha256": sha256_file(checked_text)},
        "checked_pdf_limitation": None,
        "normostrany": 42.5,
        "thresholds": {"minimum": 30},
        "status": "within_required_range",
        "checker_timestamp": None,
        "captured_at": "2026-05-20T00:00:00Z",
        "limitations": [],
    }
    write_text(round_dir / THESES_CHECKER_SUMMARY_REL, json.dumps(payload) + "\n")

    errors = validate_theses_checker_summary_artifact(round_dir, case_id="case-a", round_id="round-a")

    assert any("checked_pdf: path must be a rendered thesis PDF under inputs/" in error for error in errors)
