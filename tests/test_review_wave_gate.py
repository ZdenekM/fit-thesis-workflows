import json
import zipfile
from pathlib import Path

from thesis_review_workflow import agent_coverage
from thesis_review_workflow.review_approvals import sha256_file
from thesis_review_workflow.review_materiality import MaterialityDecision, write_materiality_decisions
from thesis_review_workflow.review_wave_gate import builtin_wave_spec, load_wave_spec, validate_wave
from thesis_review_workflow.theses_similarity import THESES_SIMILARITY_REPORT_REL


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
        round_dir / "work" / "reviews" / "supervisor_feedback_review.json",
        {
            "workflow_profile": "supervisor_feedback",
            "reviewer_role": "thesis-supervisor-feedback-review",
            "verdict": "approved",
            "blocking_findings_count": 0,
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
                        "path": "work/reviews/supervisor_feedback_review.json",
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
    assert any("reviewed_artifact_sha256 is stale" in error for error in stale.errors)


def test_approval_record_rejects_negative_verdict_and_missing_basis(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    output = round_dir / "outputs" / "feedback_student.md"
    output.parent.mkdir()
    output.write_text("# Reviewed\n", encoding="utf-8")
    write_json(
        round_dir / "work" / "reviews" / "supervisor_feedback_review.json",
        {
            "workflow_profile": "supervisor_feedback",
            "reviewer_role": "thesis-supervisor-feedback-review",
            "verdict": "rejected",
            "blocking_findings_count": 1,
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
                    "approval_record": "work/reviews/supervisor_feedback_review.json",
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
    assert any("review_basis_path points to a missing file" in error for error in result.errors)


def test_approval_record_rejects_approved_with_blocking_findings(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    output = round_dir / "outputs" / "feedback_student.md"
    basis = round_dir / "work" / "feedback_student_draft.md"
    output.parent.mkdir()
    basis.parent.mkdir()
    output.write_text("# Reviewed\n", encoding="utf-8")
    basis.write_text("# Draft\n", encoding="utf-8")
    write_json(
        round_dir / "work" / "reviews" / "supervisor_feedback_review.json",
        {
            "workflow_profile": "supervisor_feedback",
            "reviewer_role": "thesis-supervisor-feedback-review",
            "verdict": "approved",
            "blocking_findings_count": 1,
            "reviewed_artifact_path": "outputs/feedback_student.md",
            "reviewed_artifact_sha256": sha256_file(output),
            "review_basis_path": "work/feedback_student_draft.md",
            "review_basis_sha256": sha256_file(basis),
            "checks_observed": ["check-feedback-output"],
            "limitations": ["Blocking issue remains."],
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
                    "approval_record": "work/reviews/supervisor_feedback_review.json",
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

    assert any("blocking_findings_count 0" in error for error in result.errors)


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
                        "path": "work/reviews/supervisor_feedback_review.json",
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

    opponent_report_draft = builtin_wave_spec("opponent-report", "draft")
    assert opponent_report_draft.outputs[0].checks[0].args == ("check-opponent-report", "--mode", "canonical")

    opponent_report_review = builtin_wave_spec("opponent-report-review", "final")
    assert opponent_report_review.outputs[0].checks[0].args == ("check-opponent-report", "--mode", "canonical")
    assert opponent_report_review.outputs[0].checks[1].args == (
        "check-opponent-report",
        "--mode",
        "clean",
        "--path",
        "outputs/oponent_posudek_navrh.md",
    )
    assert opponent_report_review.outputs[0].approval_record is not None
    assert opponent_report_review.outputs[0].approval_record.path == "work/reviews/opponent_report_review.json"

    report_trace = builtin_wave_spec("supervisor-report", "trace")
    assert report_trace.outputs[0].paths == ("work/supervisor_report_trace.json",)
    assert report_trace.outputs[0].checks[0].args == ("check-supervisor-report",)

    report_draft = builtin_wave_spec("supervisor-report", "draft")
    assert report_draft.outputs[0].paths == ("work/vedouci_posudek_draft.md",)

    report_final = builtin_wave_spec("supervisor-report", "final")
    assert report_final.outputs[0].paths == ("outputs/vedouci_posudek_revidovany.md",)
    assert report_final.outputs[0].checks[0].args == ("check-supervisor-report", "--require-reviewed")
    assert report_final.outputs[0].approval_record is not None
    assert report_final.outputs[0].approval_record.path == "work/reviews/supervisor_report_review.json"


def test_wave_gate_blocks_unresolved_materiality_next_actions(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    draft = round_dir / "work" / "feedback_student_draft.md"
    draft.parent.mkdir(parents=True)
    draft.write_text("# Draft\n", encoding="utf-8")
    source = round_dir / "inputs" / "results.csv"
    source.parent.mkdir()
    source.write_text("metric,value\nlatency,42\n", encoding="utf-8")
    write_materiality_decisions(
        round_dir,
        [
            MaterialityDecision(
                role="quantitative_claims",
                recommendation="material",
                scope="explicit_request",
                impact="student-action priority",
                reason="test materiality decision",
                source_refs=("inputs/results.csv",),
            )
        ],
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
        phase="non_final",
        generated_at="2026-05-11T00:00:00Z",
    )

    result = validate_wave(
        tmp_path / "repo",
        round_dir,
        builtin_wave_spec("supervisor-feedback", "draft"),
        case_id="case-a",
        round_id="round-a",
    )

    assert any("materiality next action unresolved" in error for error in result.errors)


def test_wave_gate_blocks_unresolved_theses_similarity_next_action(tmp_path: Path) -> None:
    cases = (
        ("supervisor-feedback", "draft", "supervisor_feedback", "work/feedback_student_draft.md"),
        ("supervisor-report", "trace", "supervisor_report", "work/supervisor_report_trace.json"),
        ("opponent-materials", "draft", "opponent_review", "work/oponent_podklady_draft.md"),
    )
    for workflow, wave, profile, output_path in cases:
        root = tmp_path / workflow
        round_dir = make_round(root)
        output = round_dir / output_path
        output.parent.mkdir(parents=True)
        output.write_text("# Synthetic output\n", encoding="utf-8")
        report = round_dir / THESES_SIMILARITY_REPORT_REL
        report.parent.mkdir(parents=True)
        report.write_bytes(b"%PDF synthetic\n")
        write_materiality_decisions(
            round_dir,
            [
                MaterialityDecision(
                    role="theses_similarity",
                    recommendation="material",
                    scope="theses_similarity_report_evidence",
                    impact="report defensibility",
                    reason="Theses.cz report evidence exists.",
                    source_refs=(THESES_SIMILARITY_REPORT_REL,),
                )
            ],
            case_id="case-a",
            round_id="round-a",
            workflow_profile=profile,
            phase="final",
            generated_at="2026-05-12T00:00:00Z",
        )

        result = validate_wave(
            root / "repo",
            round_dir,
            builtin_wave_spec(workflow, wave),
            case_id="case-a",
            round_id="round-a",
        )

        assert any("materiality next action unresolved: theses_similarity requires" in error for error in result.errors)


def test_wave_gate_requires_materiality_index_for_synthesis_waves(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    draft = round_dir / "work" / "feedback_student_draft.md"
    draft.parent.mkdir(parents=True)
    draft.write_text("# Draft\n", encoding="utf-8")

    result = validate_wave(
        tmp_path / "repo",
        round_dir,
        builtin_wave_spec("supervisor-feedback", "draft"),
        case_id="case-a",
        round_id="round-a",
    )

    assert any("work/review_materiality/supervisor_feedback/index.json: missing" in error for error in result.errors)


def test_final_wave_gate_requires_review_manifest_for_agent_coverage(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    output = round_dir / "outputs" / "feedback_student.md"
    output.parent.mkdir(parents=True)
    output.write_text("# Feedback\n", encoding="utf-8")
    write_materiality_decisions(
        round_dir,
        [
            MaterialityDecision(
                role="figure_media",
                recommendation="not_material",
                scope="synthetic",
                impact="none",
                reason="no visual evidence in this synthetic wave",
                source_refs=("workflow-profile:supervisor_feedback",),
            )
        ],
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
        phase="non_final",
        generated_at="2026-05-13T00:00:00Z",
    )
    spec_path = round_dir / "work" / "wave.json"
    write_json(
        spec_path,
        {
            "workflow": "supervisor_feedback",
            "wave": "final",
            "outputs": [{"role": "feedback", "path": "outputs/feedback_student.md"}],
        },
    )

    result = validate_wave(
        tmp_path / "repo",
        round_dir,
        load_wave_spec(spec_path),
        case_id="case-a",
        round_id="round-a",
    )

    assert "agent coverage: work/review_manifest.json is required for final/reviewed waves" in result.errors


def test_wave_gate_consumes_agent_coverage_reuse_state(tmp_path: Path) -> None:
    round_dir = make_round(tmp_path)
    final_output = round_dir / "outputs" / "feedback_student.md"
    consistency_output = round_dir / "outputs" / "code_consistency.md"
    quality_output = round_dir / "outputs" / "code_quality_review.md"
    thesis_extract = round_dir / "extracted" / "thesis.txt"
    code_archive = round_dir / "inputs" / "code.zip"
    final_output.parent.mkdir(parents=True)
    thesis_extract.parent.mkdir(parents=True)
    code_archive.parent.mkdir(parents=True)
    final_output.write_text("# Feedback\n", encoding="utf-8")
    consistency_output.write_text("# Code Consistency\n", encoding="utf-8")
    quality_output.write_text("# Code Quality\n", encoding="utf-8")
    thesis_extract.write_text("Changed implementation claim.\n", encoding="utf-8")
    with zipfile.ZipFile(code_archive, "w") as handle:
        handle.writestr("project/src/main.py", "print('synthetic')\n")
    final_hash = sha256_file(final_output)
    consistency_hash = sha256_file(consistency_output)
    quality_hash = sha256_file(quality_output)
    write_json(
        round_dir / "work" / "review_manifest.json",
        {
            "schema_version": "review-manifest-v1",
            "case_id": "case-a",
            "round_id": "round-a",
            "inputs": [{"path": "inputs/code.zip", "kind": "archive"}],
            "supporting_work_artifacts": [],
            "artifacts": [
                {
                    "path": "outputs/feedback_student.md",
                    "artifact_sha256": final_hash,
                    "skills": ["thesis-supervisor-feedback-review"],
                    "generated_by": [{"role": "thesis-supervisor-feedback-review", "agent": "reviewer-a"}],
                    "independent_review": {
                        "reviewer_role": "thesis-supervisor-feedback-review",
                        "reviewer_agent": "reviewer-b",
                        "reviewed_hash": final_hash,
                    },
                },
                {
                    "path": "outputs/code_consistency.md",
                    "artifact_sha256": consistency_hash,
                    "skills": ["thesis-code-consistency"],
                    "generated_by": [{"role": "thesis-code-consistency", "agent": "code-a"}],
                    "independent_review": {
                        "reviewer_role": "thesis-code-consistency",
                        "reviewer_agent": "code-reviewer",
                        "reviewed_hash": consistency_hash,
                    },
                },
                {
                    "path": "outputs/code_quality_review.md",
                    "artifact_sha256": quality_hash,
                    "skills": ["thesis-code-quality-review"],
                    "generated_by": [{"role": "thesis-code-quality-review", "agent": "quality-a"}],
                    "independent_review": {
                        "reviewer_role": "thesis-code-quality-review",
                        "reviewer_agent": "quality-reviewer",
                        "reviewed_hash": quality_hash,
                    },
                },
            ],
        },
    )
    write_json(
        round_dir / "work" / "reuse" / "reuse_index.json",
        {
            "schema_version": agent_coverage.REUSE_INDEX_SCHEMA_VERSION,
            "case_id": "case-a",
            "round_id": "round-a",
            "generated_at": "2026-05-13T00:00:00Z",
            "producer": "update-round-reuse-index",
            "current_source_fingerprints": [],
            "previous_round_candidates": [],
            "limitations": [],
            "decisions": [
                {
                    "artifact_role": "code_consistency",
                    "status": "changed_delta_required",
                    "fresh_semantic_review_required": True,
                    "coverage_satisfied_by": "not_satisfied",
                    "next_action": "delta_review",
                    "relevant_source_classes": ["submitted_code", "thesis_extract"],
                    "source_sha256": {
                        "inputs/code.zip": sha256_file(code_archive),
                        "extracted/thesis.txt": sha256_file(thesis_extract),
                    },
                    "unchanged_refs": ["inputs/code.zip"],
                    "changed_refs": ["extracted/thesis.txt"],
                    "added_refs": [],
                    "removed_refs": [],
                    "missing_current_refs": [],
                    "not_comparable_refs": [],
                    "reasons": ["role-relevant source changed"],
                },
                {
                    "artifact_role": "code_quality",
                    "status": "unchanged_reusable",
                    "fresh_semantic_review_required": False,
                    "coverage_satisfied_by": "current_reviewed_artifact",
                    "next_action": "reuse_existing_review",
                    "relevant_source_classes": ["submitted_code"],
                    "source_sha256": {"inputs/code.zip": sha256_file(code_archive)},
                    "unchanged_refs": ["inputs/code.zip"],
                    "changed_refs": [],
                    "added_refs": [],
                    "removed_refs": [],
                    "missing_current_refs": [],
                    "not_comparable_refs": [],
                    "reasons": ["role-relevant sources unchanged and reviewed coverage is current"],
                },
            ],
        },
    )
    manifest = json.loads((round_dir / "work" / "review_manifest.json").read_text(encoding="utf-8"))
    coverage = agent_coverage.build_coverage("case-a", "round-a", round_dir, manifest)
    assert coverage is not None
    code_role = next(item for item in coverage["roles"] if item["role"] == "code_consistency")
    code_role["fresh_review_required"] = False
    code_role["coverage_satisfied_by"] = "current_reviewed_artifact"
    write_json(round_dir / "work" / "agent_coverage.json", coverage)
    write_materiality_decisions(
        round_dir,
        [
            MaterialityDecision(
                role="figure_media",
                recommendation="not_material",
                scope="synthetic",
                impact="none",
                reason="no visual evidence in this synthetic wave",
                source_refs=("workflow-profile:supervisor_feedback",),
            )
        ],
        case_id="case-a",
        round_id="round-a",
        workflow_profile="supervisor_feedback",
        phase="non_final",
        generated_at="2026-05-13T00:00:00Z",
    )
    spec_path = round_dir / "work" / "wave.json"
    write_json(
        spec_path,
        {
            "workflow": "supervisor_feedback",
            "wave": "final",
            "outputs": [{"role": "feedback", "path": "outputs/feedback_student.md"}],
        },
    )

    result = validate_wave(
        tmp_path / "repo",
        round_dir,
        load_wave_spec(spec_path),
        case_id="case-a",
        round_id="round-a",
    )

    assert any(
        "agent coverage: code_consistency: reuse decision must be unchanged_reusable" in error
        for error in result.errors
    )
