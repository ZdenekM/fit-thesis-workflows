import json
from pathlib import Path
from typing import Any, cast

from thesis_review_workflow.cli.update_round_reuse_index import (
    artifact_review_current,
    backfill_pdf_extract_sidecars,
    build_reuse_index,
    collect_round_source_fingerprints,
)
from thesis_review_workflow.pdf_extracts import pdf_extract_sidecar_path, write_pdf_extract_manifest
from thesis_review_workflow.reuse import ArtifactRole, ReuseStatus, SourceClass
from thesis_review_workflow.work_artifacts import sha256_file


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def make_round(case_dir: Path, round_id: str) -> Path:
    round_dir = case_dir / "rounds" / round_id
    (round_dir / "inputs").mkdir(parents=True)
    (round_dir / "extracted").mkdir()
    (round_dir / "work").mkdir()
    (round_dir / "outputs").mkdir()
    return round_dir


def add_pdf_sidecar(round_dir: Path, *, pdf_bytes: bytes, text: str) -> None:
    pdf = round_dir / "inputs" / "thesis.pdf"
    extracted = round_dir / "extracted" / "thesis.txt"
    pdf.write_bytes(pdf_bytes)
    extracted.write_text(text, encoding="utf-8")
    write_pdf_extract_manifest(
        round_dir,
        pdf,
        extracted,
        extractor_version="pdftotext synthetic",
        generated_at="2026-05-13T12:00:00Z",
    )


def add_reviewed_feedback(round_dir: Path) -> None:
    feedback = round_dir / "outputs" / "feedback_student.md"
    feedback.write_text("# Feedback\n", encoding="utf-8")
    feedback_hash = sha256_file(feedback)
    write_json(
        round_dir / "work" / "review_manifest.json",
        {
            "artifacts": [
                {
                    "path": "outputs/feedback_student.md",
                    "artifact_sha256": feedback_hash,
                    "independent_review": {"reviewed_hash": feedback_hash},
                }
            ]
        },
    )


def add_reviewed_feedback_with_fresh_helper_gate(round_dir: Path) -> None:
    feedback = round_dir / "outputs" / "feedback_student.md"
    feedback.write_text("# Feedback\n", encoding="utf-8")
    feedback_hash = sha256_file(feedback)
    write_json(
        round_dir / "work" / "review_manifest.json",
        {
            "artifacts": [
                {
                    "path": "outputs/feedback_student.md",
                    "artifact_sha256": feedback_hash,
                    "independent_review": {
                        "status": "reviewed",
                        "reviewed_hash": feedback_hash,
                    },
                }
            ],
            "helper_checks": [
                {
                    "check": "check-agent-coverage",
                    "status": "passed",
                    "exit_code": 0,
                    "target_artifacts": ["outputs/feedback_student.md"],
                    "target_sha256": {"outputs/feedback_student.md": feedback_hash},
                },
                {
                    "check": "check-review-manifest",
                    "status": "not_applicable",
                    "target_artifacts": ["outputs/feedback_student.md"],
                },
            ],
        },
    )


def add_github_snapshot(round_dir: Path) -> None:
    write_json(
        round_dir / "work" / "github-intake" / "snapshot-manifest.json",
        {
            "schema_version": "github-snapshot-manifest-v1",
            "case_id": "case-a",
            "round_id": round_dir.name,
            "generated_at": "2026-05-13T12:00:00Z",
            "producer": "scripts/import-github-code",
            "mode": "upstream_pr_contribution",
            "no_checkout": True,
            "requested_repositories": [],
            "requested_pull_requests": ["https://github.com/owner/project/pull/1"],
            "repositories": [],
            "pull_requests": [
                {
                    "pr": "owner/project#1",
                    "url": "https://github.com/owner/project/pull/1",
                    "head_sha": "a" * 40,
                }
            ],
            "changed_file_list": {"normalized_sha256": "b" * 64},
            "checks_summary_sha256": "c" * 64,
            "checkout_paths": [],
            "limitations_sha256": "d" * 64,
        },
    )
    note = round_dir / "notes" / "github-intake-note.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text("Static GitHub intake note.\n", encoding="utf-8")


def add_reviewed_github_intake_with_fresh_helper_gate(round_dir: Path) -> None:
    output = round_dir / "outputs" / "github_code_intake.md"
    output.write_text("# GitHub Intake\n", encoding="utf-8")
    output_hash = sha256_file(output)
    write_json(
        round_dir / "work" / "review_manifest.json",
        {
            "artifacts": [
                {
                    "path": "outputs/github_code_intake.md",
                    "artifact_sha256": output_hash,
                    "independent_review": {
                        "status": "reviewed",
                        "reviewed_hash": output_hash,
                    },
                }
            ],
            "helper_checks": [
                {
                    "check": "check-agent-coverage",
                    "status": "passed",
                    "exit_code": 0,
                    "target_artifacts": ["outputs/github_code_intake.md"],
                    "target_sha256": {"outputs/github_code_intake.md": output_hash},
                }
            ],
        },
    )


def test_collect_round_sources_marks_missing_pdf_sidecars_not_comparable(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path / "case-a", "20260513-current")
    (round_dir / "inputs" / "thesis.pdf").write_bytes(b"%PDF synthetic\n")
    (round_dir / "extracted" / "thesis.txt").write_text("Extracted text\n", encoding="utf-8")

    sources, notes = collect_round_source_fingerprints(round_dir)

    by_key = {(source.source_ref, source.source_class): source for source in sources}
    assert by_key[("inputs/thesis.pdf", SourceClass.THESIS_PDF)].sha256 is None
    assert by_key[("extracted/thesis.txt", SourceClass.THESIS_EXTRACT)].sha256 is None
    assert any("marked not_comparable" in note for note in notes)


def test_collect_round_sources_marks_stale_pdf_sidecars_not_comparable(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path / "case-a", "20260513-current")
    add_pdf_sidecar(round_dir, pdf_bytes=b"%PDF synthetic\n", text="Extracted text\n")
    (round_dir / "extracted" / "thesis.txt").write_text("Changed text\n", encoding="utf-8")

    sources, notes = collect_round_source_fingerprints(round_dir)

    by_key = {(source.source_ref, source.source_class): source for source in sources}
    assert by_key[("inputs/thesis.pdf", SourceClass.THESIS_PDF)].sha256 is None
    assert by_key[("extracted/thesis.txt", SourceClass.THESIS_EXTRACT)].sha256 is None
    assert any("stale or incomplete" in note for note in notes)


def test_artifact_review_current_requires_review_status_and_fresh_helper_gate(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path / "case-a", "20260513-current")
    add_reviewed_feedback(round_dir)

    assert not artifact_review_current(round_dir, "outputs/feedback_student.md")

    add_reviewed_feedback_with_fresh_helper_gate(round_dir)

    assert artifact_review_current(round_dir, "outputs/feedback_student.md")

    feedback = round_dir / "outputs" / "feedback_student.md"
    feedback_hash = sha256_file(feedback)
    write_json(
        round_dir / "work" / "review_manifest.json",
        {
            "artifacts": [
                {
                    "path": "outputs/feedback_student.md",
                    "artifact_sha256": feedback_hash,
                    "independent_review": {
                        "status": "reviewed",
                        "reviewed_hash": feedback_hash,
                    },
                }
            ],
            "helper_checks": [
                {
                    "check": "check-feedback-language",
                    "status": "passed",
                    "exit_code": 0,
                    "target_artifacts": ["outputs/feedback_student.md"],
                    "target_sha256": {"outputs/feedback_student.md": feedback_hash},
                }
            ],
        },
    )

    assert not artifact_review_current(round_dir, "outputs/feedback_student.md")


def test_reuse_index_keeps_incomplete_role_coverage_not_comparable(tmp_path: Path) -> None:
    case_dir = tmp_path / "case-a"
    prior_round = make_round(case_dir, "20260512-prior")
    current_round = make_round(case_dir, "20260513-current")
    add_pdf_sidecar(prior_round, pdf_bytes=b"%PDF same\n", text="same text\n")
    add_pdf_sidecar(current_round, pdf_bytes=b"%PDF same\n", text="same text\n")
    add_reviewed_feedback_with_fresh_helper_gate(prior_round)
    current_sources, current_notes = collect_round_source_fingerprints(current_round)

    index = build_reuse_index(
        case_id="case-a",
        current_round_id="20260513-current",
        case_dir_path=case_dir,
        current_sources=current_sources,
        current_notes=current_notes,
    )

    decision_items = cast(list[dict[str, Any]], index["decisions"])
    decisions = {decision["artifact_role"]: decision for decision in decision_items}
    feedback_decision = decisions[ArtifactRole.SUPERVISOR_FEEDBACK.value]
    candidate_artifacts = cast(list[dict[str, object]], feedback_decision["candidate_artifacts"])

    assert feedback_decision["candidate_round_id"] == "20260512-prior"
    assert feedback_decision["status"] == ReuseStatus.NOT_COMPARABLE.value
    assert feedback_decision["fresh_semantic_review_required"] is True
    assert "role source coverage is incomplete" in feedback_decision["reasons"]
    assert "assignment" in feedback_decision["missing_current_source_classes"]
    assert candidate_artifacts[0]["path"] == "outputs/feedback_student.md"


def test_reuse_index_prefers_older_eligible_candidate_over_nearest_stale_candidate(tmp_path: Path) -> None:
    case_dir = tmp_path / "case-a"
    older_round = make_round(case_dir, "20260511-older")
    nearest_round = make_round(case_dir, "20260512-nearest")
    current_round = make_round(case_dir, "20260513-current")
    add_github_snapshot(older_round)
    add_reviewed_github_intake_with_fresh_helper_gate(older_round)
    output = nearest_round / "outputs" / "github_code_intake.md"
    output.write_text("# Stale GitHub Intake\n", encoding="utf-8")
    add_github_snapshot(current_round)
    current_sources, current_notes = collect_round_source_fingerprints(current_round)

    index = build_reuse_index(
        case_id="case-a",
        current_round_id="20260513-current",
        case_dir_path=case_dir,
        current_sources=current_sources,
        current_notes=current_notes,
    )
    decision_items = cast(list[dict[str, Any]], index["decisions"])
    feedback_decision = next(
        decision for decision in decision_items if decision["artifact_role"] == ArtifactRole.GITHUB_CODE_INTAKE.value
    )
    candidate_decisions = cast(list[dict[str, object]], feedback_decision["candidate_decisions"])

    assert feedback_decision["candidate_round_id"] == "20260511-older"
    assert feedback_decision["status"] == ReuseStatus.UNCHANGED_REUSABLE.value
    assert [decision["candidate_round_id"] for decision in candidate_decisions] == [
        "20260512-nearest",
        "20260511-older",
    ]


def test_backfill_current_writes_only_missing_pdf_extract_sidecars(tmp_path: Path, monkeypatch) -> None:
    round_dir = make_round(tmp_path / "case-a", "20260513-current")
    pdf = round_dir / "inputs" / "thesis.pdf"
    extracted = round_dir / "extracted" / "thesis.txt"
    pdf.write_bytes(b"%PDF synthetic\n")
    extracted.write_text("Extracted text\n", encoding="utf-8")
    monkeypatch.setattr(
        "thesis_review_workflow.cli.update_round_reuse_index.pdftotext_version",
        lambda: "pdftotext synthetic",
    )

    written = backfill_pdf_extract_sidecars(round_dir)

    assert written == ["extracted/thesis.txt.pdf-extract.json"]
    assert pdf_extract_sidecar_path(extracted).is_file()
