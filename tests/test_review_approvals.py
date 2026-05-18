import json
from pathlib import Path
from typing import Any

from thesis_review_workflow.cli import write_review_approval
from thesis_review_workflow.review_approvals import (
    REVIEW_APPROVAL_SCHEMA,
    build_review_approval_payload,
    reviewer_matches_generator,
    sha256_file,
    validate_required_checks,
)


def make_case(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    case_dir = root / "cases" / "case-a"
    round_dir = case_dir / "rounds" / "round-a"
    round_dir.mkdir(parents=True)
    case_dir.joinpath("case.md").write_text("Reviewer profile: default\n", encoding="utf-8")
    case_dir.joinpath("current-round.txt").write_text("round-a\n", encoding="utf-8")
    return round_dir


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def helper_check(name: str, output: Path, rel_output: str) -> dict[str, object]:
    return {
        "check": name,
        "status": "passed",
        "exit_code": 0,
        "checked_at": "2026-05-11T12:00:00Z",
        "target_artifacts": [rel_output],
        "target_sha256": {rel_output: sha256_file(output)},
    }


def helper_check_record(name: str, round_dir: Path, targets: list[str]) -> dict[str, object]:
    return {
        "check": name,
        "status": "passed",
        "exit_code": 0,
        "checked_at": "2026-05-11T12:00:00Z",
        "target_artifacts": targets,
        "target_sha256": {target: sha256_file(round_dir / target) for target in targets},
    }


def test_write_review_approval_creates_hash_bound_supervisor_record(tmp_path: Path, monkeypatch) -> None:
    round_dir = make_case(tmp_path)
    root = round_dir.parents[3]
    monkeypatch.setattr(write_review_approval, "repo_root", lambda: root)
    output = round_dir / "outputs" / "feedback_student.md"
    draft = round_dir / "work" / "feedback_student_draft.md"
    output.parent.mkdir()
    draft.parent.mkdir()
    output.write_text("# Reviewed feedback\n", encoding="utf-8")
    draft.write_text("# Draft feedback\n", encoding="utf-8")
    write_json(
        round_dir / "work" / "review_manifest.json",
        {
            "schema_version": "review-manifest-v1",
            "case_id": "case-a",
            "round_id": "round-a",
            "artifacts": [
                {
                    "path": "outputs/feedback_student.md",
                    "review_scope": "sendable_final",
                    "generated_by": [
                        {
                            "role": "thesis-supervisor-feedback",
                            "agent": "generator-agent",
                            "contribution": "generation",
                        }
                    ],
                }
            ],
            "helper_checks": [
                helper_check("check-supervisor-ready", output, "outputs/feedback_student.md"),
                helper_check("check-feedback-language", output, "outputs/feedback_student.md"),
                helper_check("check-feedback-output", output, "outputs/feedback_student.md"),
            ],
        },
    )

    result = write_review_approval.main(
        [
            "--profile",
            "supervisor-feedback",
            "--reviewer-agent",
            "review-agent",
            "--check",
            "check-supervisor-ready",
            "--check",
            "check-feedback-language",
            "--check",
            "check-feedback-output",
            "--timestamp",
            "2026-05-11T12:00:00Z",
            "case-a",
            "round-a",
        ]
    )

    assert result == 0
    payload = json.loads((round_dir / "work" / "reviews" / "supervisor_feedback_review.json").read_text())
    assert payload["schema_version"] == REVIEW_APPROVAL_SCHEMA
    assert payload["reviewed_artifact_sha256"] == sha256_file(output)
    assert payload["review_basis_sha256"] == sha256_file(draft)
    assert payload["checks_observed"] == [
        "check-feedback-language",
        "check-feedback-output",
        "check-supervisor-ready",
    ]


def test_write_review_approval_creates_theses_similarity_record(tmp_path: Path, monkeypatch) -> None:
    round_dir = make_case(tmp_path)
    root = round_dir.parents[3]
    monkeypatch.setattr(write_review_approval, "repo_root", lambda: root)
    output = round_dir / "outputs" / "theses_similarity_review.md"
    draft = round_dir / "work" / "theses_similarity" / "review_draft.md"
    output.parent.mkdir()
    draft.parent.mkdir(parents=True)
    output.write_text("# Theses.cz Similarity Review\n", encoding="utf-8")
    draft.write_text("# Draft Theses.cz Similarity Review\n", encoding="utf-8")
    write_json(
        round_dir / "work" / "review_manifest.json",
        {
            "schema_version": "review-manifest-v1",
            "case_id": "case-a",
            "round_id": "round-a",
            "artifacts": [
                {
                    "path": "outputs/theses_similarity_review.md",
                    "review_scope": "internal_only",
                    "generated_by": [
                        {
                            "role": "thesis-theses-similarity-review",
                            "agent": "generator-agent",
                            "contribution": "generation",
                        }
                    ],
                }
            ],
            "helper_checks": [
                helper_check("check-theses-similarity-report", output, "outputs/theses_similarity_review.md"),
            ],
        },
    )

    result = write_review_approval.main(
        [
            "--profile",
            "theses-similarity-review",
            "--reviewer-agent",
            "review-agent",
            "--check",
            "check-theses-similarity-report",
            "--timestamp",
            "2026-05-12T12:00:00Z",
            "case-a",
            "round-a",
        ]
    )

    assert result == 0
    payload = json.loads((round_dir / "work" / "reviews" / "theses_similarity_review.json").read_text())
    assert payload["schema_version"] == REVIEW_APPROVAL_SCHEMA
    assert payload["reviewed_artifact_path"] == "outputs/theses_similarity_review.md"
    assert payload["reviewed_artifact_sha256"] == sha256_file(output)
    assert payload["review_basis_path"] == "work/theses_similarity/review_draft.md"
    assert payload["review_basis_sha256"] == sha256_file(draft)
    assert payload["reviewer_role"] == "evidence-calibration-reviewer"


def test_write_review_approval_prefers_clean_opponent_report_basis(tmp_path: Path, monkeypatch) -> None:
    round_dir = make_case(tmp_path)
    root = round_dir.parents[3]
    monkeypatch.setattr(write_review_approval, "repo_root", lambda: root)
    review_output = round_dir / "outputs" / "feedback_k_posudku.md"
    clean_basis = round_dir / "outputs" / "oponent_posudek_navrh.md"
    canonical_draft = round_dir / "work" / "oponent_posudek_draft.md"
    materials = round_dir / "outputs" / "oponent_podklady_revidovane.md"
    trace = round_dir / "work" / "opponent_report_trace.json"
    review_output.parent.mkdir(parents=True)
    canonical_draft.parent.mkdir(parents=True)
    review_output.write_text("# Report review\n", encoding="utf-8")
    clean_basis.write_text("# Clean report proposal\n", encoding="utf-8")
    canonical_draft.write_text("# Canonical draft\n", encoding="utf-8")
    materials.write_text("# Reviewed materials\n", encoding="utf-8")
    trace.write_text("{}\n", encoding="utf-8")
    write_json(
        round_dir / "work" / "review_manifest.json",
        {
            "schema_version": "review-manifest-v1",
            "case_id": "case-a",
            "round_id": "round-a",
            "artifacts": [
                {
                    "path": "outputs/feedback_k_posudku.md",
                    "review_scope": "standalone_final",
                    "generated_by": [{"role": "thesis-opponent-report-review", "agent": "generator-agent"}],
                }
            ],
            "helper_checks": [
                helper_check_record(
                    "check-opponent-report:canonical",
                    round_dir,
                    [
                        "work/opponent_report_trace.json",
                        "outputs/oponent_podklady_revidovane.md",
                        "work/oponent_posudek_draft.md",
                    ],
                ),
                helper_check_record(
                    "check-opponent-report:clean",
                    round_dir,
                    [
                        "work/opponent_report_trace.json",
                        "outputs/oponent_podklady_revidovane.md",
                        "outputs/oponent_posudek_navrh.md",
                    ],
                ),
            ],
        },
    )

    result = write_review_approval.main(
        [
            "--profile",
            "opponent-report-review",
            "--reviewer-agent",
            "review-agent",
            "--check",
            "check-opponent-report:canonical",
            "--check",
            "check-opponent-report:clean",
            "--check",
            "check-review-wave.opponent-report.draft",
            "--timestamp",
            "2026-05-11T12:00:00Z",
            "case-a",
            "round-a",
        ]
    )

    assert result == 0
    payload = json.loads((round_dir / "work" / "reviews" / "opponent_report_review.json").read_text())
    assert payload["reviewed_artifact_path"] == "outputs/feedback_k_posudku.md"
    assert payload["review_basis_path"] == "outputs/oponent_posudek_navrh.md"
    assert payload["checks_observed"] == [
        "check-opponent-report:canonical",
        "check-opponent-report:clean",
        "check-review-wave.opponent-report.draft",
    ]


def test_review_approval_requires_mode_specific_opponent_report_targets(tmp_path: Path) -> None:
    round_dir = make_case(tmp_path)
    clean_basis = round_dir / "outputs" / "oponent_posudek_navrh.md"
    clean_basis.parent.mkdir(parents=True)
    clean_basis.write_text("# Clean report proposal\n", encoding="utf-8")
    manifest = {
        "helper_checks": [
            helper_check_record("check-opponent-report:clean", round_dir, ["outputs/oponent_posudek_navrh.md"])
        ]
    }

    errors = validate_required_checks(
        required_checks=("check-opponent-report:clean",),
        checks_observed=["check-opponent-report:clean"],
        rel_path="work/reviews/opponent_report_review.json",
        round_dir=round_dir,
        reviewed_artifact_path="outputs/feedback_k_posudku.md",
        manifest=manifest,
    )

    assert (
        "work/reviews/opponent_report_review.json: helper check check-opponent-report:clean "
        "missing required target artifact work/opponent_report_trace.json"
    ) in errors
    assert (
        "work/reviews/opponent_report_review.json: helper check check-opponent-report:clean "
        "missing required target artifact outputs/oponent_podklady_revidovane.md"
    ) in errors


def test_review_approval_wave_route_checks_are_observed_only(tmp_path: Path) -> None:
    round_dir = make_case(tmp_path)

    errors = validate_required_checks(
        required_checks=("check-review-wave.opponent-report.draft",),
        checks_observed=["check-review-wave.opponent-report.draft"],
        rel_path="work/reviews/opponent_report_review.json",
        round_dir=round_dir,
        reviewed_artifact_path="outputs/feedback_k_posudku.md",
        manifest=None,
    )

    assert errors == []


def test_build_review_approval_rejects_structured_check_objects(tmp_path: Path) -> None:
    round_dir = make_case(tmp_path)
    output = round_dir / "outputs" / "feedback_k_posudku.md"
    basis = round_dir / "outputs" / "oponent_posudek_navrh.md"
    output.parent.mkdir(parents=True)
    output.write_text("# Report review\n", encoding="utf-8")
    basis.write_text("# Clean report proposal\n", encoding="utf-8")
    checks: Any = [{"check": "check-opponent-report:clean", "status": "passed"}]

    try:
        build_review_approval_payload(
            round_dir,
            case_id="case-a",
            round_id="round-a",
            workflow_profile="opponent_report_review",
            reviewer_role="thesis-opponent-report-review",
            reviewer_agent="review-agent",
            verdict="approved",
            blocking_findings_count=0,
            reviewed_artifact_path="outputs/feedback_k_posudku.md",
            review_basis_path="outputs/oponent_posudek_navrh.md",
            checks_observed=checks,
            limitations=[],
            timestamp="2026-05-11T00:00:00Z",
            approval_path="work/reviews/opponent_report_review.json",
        )
    except ValueError as exc:
        assert "checks_observed item 1 must be a non-empty string" in str(exc)
    else:
        raise AssertionError("structured check objects must be rejected")


def test_reviewer_match_ignores_imported_final_review_metadata() -> None:
    manifest = {
        "artifacts": [
            {
                "path": "outputs/feedback_k_posudku.md",
                "review_scope": "standalone_final",
                "generated_by": [
                    {
                        "role": "thesis-opponent-report-review",
                        "agent": "review-agent",
                        "contribution": "final_review",
                    }
                ],
            }
        ]
    }

    assert not reviewer_matches_generator(
        manifest,
        reviewed_artifact_path="outputs/feedback_k_posudku.md",
        reviewer_agent="review-agent",
    )


def test_write_review_approval_rejects_generator_as_reviewer(tmp_path: Path, monkeypatch) -> None:
    round_dir = make_case(tmp_path)
    root = round_dir.parents[3]
    monkeypatch.setattr(write_review_approval, "repo_root", lambda: root)
    output = round_dir / "outputs" / "feedback_student.md"
    draft = round_dir / "work" / "feedback_student_draft.md"
    output.parent.mkdir()
    draft.parent.mkdir()
    output.write_text("# Reviewed feedback\n", encoding="utf-8")
    draft.write_text("# Draft feedback\n", encoding="utf-8")
    write_json(
        round_dir / "work" / "review_manifest.json",
        {
            "schema_version": "review-manifest-v1",
            "case_id": "case-a",
            "round_id": "round-a",
            "artifacts": [
                {
                    "path": "outputs/feedback_student.md",
                    "review_scope": "sendable_final",
                    "generated_by": [{"agent": "same-agent"}],
                }
            ],
            "helper_checks": [
                helper_check("check-supervisor-ready", output, "outputs/feedback_student.md"),
                helper_check("check-feedback-language", output, "outputs/feedback_student.md"),
                helper_check("check-feedback-output", output, "outputs/feedback_student.md"),
            ],
        },
    )

    result = write_review_approval.main(
        [
            "--profile",
            "supervisor-feedback",
            "--reviewer-agent",
            "same-agent",
            "--check",
            "check-supervisor-ready",
            "--check",
            "check-feedback-language",
            "--check",
            "check-feedback-output",
            "case-a",
            "round-a",
        ]
    )

    assert result == 1
    assert not (round_dir / "work" / "reviews" / "supervisor_feedback_review.json").exists()


def test_write_review_approval_rejects_missing_custom_fields(tmp_path: Path, monkeypatch) -> None:
    round_dir = make_case(tmp_path)
    root = round_dir.parents[3]
    monkeypatch.setattr(write_review_approval, "repo_root", lambda: root)

    result = write_review_approval.main(["--profile", "custom", "case-a", "round-a"])

    assert result == 1


def test_write_review_approval_rejects_self_certified_checks(tmp_path: Path, monkeypatch) -> None:
    round_dir = make_case(tmp_path)
    root = round_dir.parents[3]
    monkeypatch.setattr(write_review_approval, "repo_root", lambda: root)
    output = round_dir / "outputs" / "feedback_student.md"
    draft = round_dir / "work" / "feedback_student_draft.md"
    output.parent.mkdir()
    draft.parent.mkdir()
    output.write_text("# Reviewed feedback\n", encoding="utf-8")
    draft.write_text("# Draft feedback\n", encoding="utf-8")
    write_json(
        round_dir / "work" / "review_manifest.json",
        {
            "schema_version": "review-manifest-v1",
            "case_id": "case-a",
            "round_id": "round-a",
            "artifacts": [],
            "helper_checks": [
                helper_check("check-supervisor-ready", output, "outputs/feedback_student.md"),
                helper_check("check-feedback-output", output, "outputs/feedback_student.md"),
            ],
        },
    )

    result = write_review_approval.main(
        [
            "--profile",
            "supervisor-feedback",
            "--reviewer-agent",
            "review-agent",
            "--check",
            "check-supervisor-ready",
            "--check",
            "check-feedback-language",
            "--check",
            "check-feedback-output",
            "case-a",
            "round-a",
        ]
    )

    assert result == 1
    assert not (round_dir / "work" / "reviews" / "supervisor_feedback_review.json").exists()


def test_write_review_approval_rejects_canonical_role_override(tmp_path: Path, monkeypatch) -> None:
    round_dir = make_case(tmp_path)
    root = round_dir.parents[3]
    monkeypatch.setattr(write_review_approval, "repo_root", lambda: root)
    output = round_dir / "outputs" / "feedback_student.md"
    draft = round_dir / "work" / "feedback_student_draft.md"
    output.parent.mkdir()
    draft.parent.mkdir()
    output.write_text("# Reviewed feedback\n", encoding="utf-8")
    draft.write_text("# Draft feedback\n", encoding="utf-8")

    result = write_review_approval.main(
        [
            "--profile",
            "supervisor-feedback",
            "--reviewer-role",
            "custom-reviewer",
            "--reviewer-agent",
            "review-agent",
            "case-a",
            "round-a",
        ]
    )

    assert result == 1
