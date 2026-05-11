import json
from pathlib import Path

from thesis_review_workflow.review_wave_gate import builtin_wave_spec, load_wave_spec, sha256_file, validate_wave


def make_round(tmp_path: Path) -> Path:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    round_dir.mkdir(parents=True)
    return round_dir


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_custom_wave_requires_nonempty_output_and_handoff(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    evidence = round_dir / "work" / "evidence.md"
    evidence.parent.mkdir()
    evidence.write_text("# Evidence\n\n## Synthesis Handoff\n\n- Synthetic finding.\n", encoding="utf-8")
    spec_path = round_dir / "work" / "wave.json"
    write_json(
        spec_path,
        {
            "workflow": "custom",
            "wave": "smoke",
            "outputs": [{"role": "evidence", "path": "work/evidence.md", "handoff_required": True}],
        },
    )

    result = validate_wave(
        tmp_path / "repo",
        round_dir,
        load_wave_spec(spec_path),
        case_id="case-a",
        round_id="round-a",
    )

    assert result.errors == []
    assert any("synthesis handoff present" in item for item in result.passed)


def test_wave_reports_missing_output_and_trailing_whitespace(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    bad = round_dir / "work" / "bad.md"
    bad.parent.mkdir()
    bad.write_text("# Bad \n", encoding="utf-8")
    spec_path = round_dir / "work" / "wave.json"
    write_json(
        spec_path,
        {
            "workflow": "custom",
            "wave": "bad",
            "outputs": [
                {"role": "missing", "path": "work/missing.md"},
                {"role": "bad", "path": "work/bad.md"},
            ],
        },
    )

    result = validate_wave(
        tmp_path / "repo",
        round_dir,
        load_wave_spec(spec_path),
        case_id="case-a",
        round_id="round-a",
    )

    assert "missing: missing expected output: work/missing.md" in result.errors
    assert any("trailing whitespace in work/bad.md:1" in item for item in result.errors)


def test_approval_record_is_hash_bound_to_reviewed_artifact_and_basis(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    output = round_dir / "outputs" / "feedback_student.md"
    basis = round_dir / "work" / "feedback_student_draft.md"
    output.parent.mkdir()
    basis.parent.mkdir()
    output.write_text("# Reviewed\n", encoding="utf-8")
    basis.write_text("# Draft\n", encoding="utf-8")
    write_json(
        round_dir / "work" / "review.json",
        {
            "workflow_profile": "supervisor_feedback",
            "reviewer_role": "thesis-supervisor-feedback-review",
            "verdict": "approved",
            "reviewed_artifact_path": "outputs/feedback_student.md",
            "reviewed_artifact_sha256": sha256_file(output),
            "review_basis_path": "work/feedback_student_draft.md",
            "review_basis_sha256": sha256_file(basis),
            "checks_observed": ["check-feedback-output"],
            "limitations": [],
            "timestamp": "2026-05-11T12:00:00Z",
        },
    )
    spec_path = round_dir / "work" / "wave.json"
    write_json(
        spec_path,
        {
            "workflow": "custom",
            "wave": "review",
            "outputs": [
                {
                    "role": "feedback_review",
                    "path": "outputs/feedback_student.md",
                    "approval_record": {
                        "path": "work/review.json",
                        "reviewed_artifact_path": "outputs/feedback_student.md",
                    },
                }
            ],
        },
    )

    result = validate_wave(
        tmp_path / "repo",
        round_dir,
        load_wave_spec(spec_path),
        case_id="case-a",
        round_id="round-a",
    )
    assert result.errors == []

    output.write_text("# Reviewed changed\n", encoding="utf-8")
    stale = validate_wave(
        tmp_path / "repo",
        round_dir,
        load_wave_spec(spec_path),
        case_id="case-a",
        round_id="round-a",
    )
    assert any("reviewed artifact hash is stale" in error for error in stale.errors)


def test_approval_record_rejects_negative_verdict_and_missing_basis(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    output = round_dir / "outputs" / "feedback_student.md"
    output.parent.mkdir()
    output.write_text("# Reviewed\n", encoding="utf-8")
    write_json(
        round_dir / "work" / "review.json",
        {
            "workflow_profile": "supervisor_feedback",
            "reviewer_role": "thesis-supervisor-feedback-review",
            "verdict": "rejected",
            "reviewed_artifact_path": "outputs/feedback_student.md",
            "reviewed_artifact_sha256": sha256_file(output),
            "review_basis_path": "work/missing_basis.md",
            "review_basis_sha256": "0" * 64,
            "checks_observed": [],
            "limitations": [],
            "timestamp": "2026-05-11T12:00:00Z",
        },
    )
    spec_path = round_dir / "work" / "wave.json"
    write_json(
        spec_path,
        {
            "workflow": "custom",
            "wave": "review",
            "outputs": [
                {
                    "role": "feedback_review",
                    "path": "outputs/feedback_student.md",
                    "approval_record": "work/review.json",
                }
            ],
        },
    )

    result = validate_wave(
        tmp_path / "repo",
        round_dir,
        load_wave_spec(spec_path),
        case_id="case-a",
        round_id="round-a",
    )

    assert any("verdict must be approved/pass" in error for error in result.errors)
    assert any("review basis is missing" in error for error in result.errors)


def test_approval_record_spec_rejects_unsafe_reviewed_artifact_path(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    spec_path = round_dir / "work" / "wave.json"
    write_json(
        spec_path,
        {
            "workflow": "custom",
            "wave": "review",
            "outputs": [
                {
                    "role": "feedback_review",
                    "path": "outputs/feedback_student.md",
                    "approval_record": {
                        "path": "work/review.json",
                        "reviewed_artifact_path": "../escape.md",
                    },
                }
            ],
        },
    )

    try:
        load_wave_spec(spec_path)
    except ValueError as exc:
        assert "approval_record.reviewed_artifact_path" in str(exc)
    else:
        raise AssertionError("Expected unsafe reviewed_artifact_path to fail")


def test_builtin_profiles_keep_draft_and_post_review_gates_separate() -> None:
    supervisor_draft = builtin_wave_spec("supervisor-feedback", "draft")
    assert supervisor_draft.outputs[0].paths == ("work/feedback_student_draft.md",)
    assert supervisor_draft.outputs[0].checks[0].args == (
        "check-feedback-language",
        "--artifact",
        "work/feedback_student_draft.md",
    )

    opponent_draft = builtin_wave_spec("opponent-materials", "draft")
    assert opponent_draft.outputs[0].paths == ("work/oponent_podklady_draft.md", "outputs/oponent_podklady.md")
    assert opponent_draft.outputs[0].checks == ()

    opponent_reviewed = builtin_wave_spec("opponent-materials", "reviewed")
    assert opponent_reviewed.outputs[0].checks[0].args == ("check-opponent-materials",)
