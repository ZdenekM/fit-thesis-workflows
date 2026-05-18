import json
import sys
from pathlib import Path

from thesis_review_workflow.agent_coverage import COVERAGE_REL, build_coverage
from thesis_review_workflow.claim_review_basis import CLAIM_REVIEW_BASIS_REL, CLAIM_REVIEW_BASIS_SCHEMA
from thesis_review_workflow.cli import init_review_manifest, register_review_artifact
from thesis_review_workflow.cli.check_review_manifest import (
    check_helper_checks,
    check_manifest,
    check_source_hashes,
    required_helper_targets,
)
from thesis_review_workflow.cli.init_review_manifest import (
    helper_dependency_hashes,
    merge_checks,
    output_artifacts,
    required_checks,
    run_check_record,
    workflow_checker_version,
)
from thesis_review_workflow.review_manifest import (
    REUSE_INDEX_REL,
    apply_artifact_dependency_refs,
    apply_artifact_registration_sidecars,
    apply_review_approval_records,
    ensure_manifest,
    merge_supporting_work_artifacts,
    output_defaults,
    register_artifact,
)
from thesis_review_workflow.work_artifacts import (
    collect_supporting_work_artifacts,
    sha256_file,
    validate_supporting_work_artifacts,
)


def write_claim_review_basis(round_dir: Path, *, draft_ref: str = "work/feedback_student_draft.md") -> None:
    draft = round_dir / draft_ref
    evidence = round_dir / "extracted" / "thesis.txt"
    draft.parent.mkdir(parents=True, exist_ok=True)
    evidence.parent.mkdir(parents=True, exist_ok=True)
    draft.write_text("# Draft\n", encoding="utf-8")
    evidence.write_text("Anchored claim.\n", encoding="utf-8")
    path = round_dir / CLAIM_REVIEW_BASIS_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": CLAIM_REVIEW_BASIS_SCHEMA,
        "case_id": "case-a",
        "round_id": "round-a",
        "generated_at": "2026-05-13T00:00:00Z",
        "producer_type": "agent",
        "producer_role": "synthesis-reviewer",
        "producer_agent": "agent-a",
        "draft_ref": draft_ref,
        "draft_sha256": sha256_file(draft),
        "capsule_refs": [],
        "claims": [
            {
                "claim_id": "P1:claim",
                "claim_text": "The final artifact contains an anchored claim.",
                "priority": "p1",
                "grade_impact": False,
                "evidence_refs": ["extracted/thesis.txt"],
                "capsule_refs": [],
                "source_sha256": {"extracted/thesis.txt": sha256_file(evidence)},
                "verification_status": "needs_raw_source",
                "raw_source_escalations": [
                    {
                        "reason": "p0_p1_verification",
                        "source_refs": ["extracted/thesis.txt"],
                    }
                ],
            }
        ],
        "limitations": [],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_review_manifest_validates_supporting_work_artifact_schema(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    artifact = round_dir / "work" / "assignment_coverage_agent.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text(
        json.dumps(
            {
                "schema_version": "wrong-schema",
                "case_id": "case-a",
                "round_id": "round-a",
                "generated_at": "2026-05-06T00:00:00Z",
                "producer_type": "agent",
                "producer_role": "assignment-coverage-reviewer",
                "producer_agent": "agent-a",
                "authorization_note": "Authorized in current request.",
                "source_refs": [],
                "assignment_points": [],
                "limitations": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = {
        "schema_version": "review-manifest-v1",
        "case_id": "case-a",
        "round_id": "round-a",
        "manifest_path": "work/review_manifest.json",
        "inputs": [],
        "extracted_artifacts": [],
        "notes": [],
        "supporting_work_artifacts": [
            {
                "path": "work/assignment_coverage_agent.json",
                "kind": "structured_data",
                "artifact_sha256": "0" * 64,
            }
        ],
        "workflow_limitations": [],
        "artifacts": [],
        "helper_checks": [],
    }
    errors: list[str] = []
    warnings: list[str] = []

    check_manifest(manifest, "case-a", "round-a", root, round_dir, False, errors, warnings)

    assert any("artifact_sha256 is stale" in error for error in errors)
    assert any("schema_version must be assignment-coverage-agent-v1" in error for error in errors)


def test_review_manifest_requires_supporting_work_artifacts_list(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "work").mkdir(parents=True)
    manifest = {
        "schema_version": "review-manifest-v1",
        "case_id": "case-a",
        "round_id": "round-a",
        "manifest_path": "work/review_manifest.json",
        "inputs": [],
        "extracted_artifacts": [],
        "notes": [],
        "workflow_limitations": [],
        "artifacts": [],
        "helper_checks": [],
    }
    errors: list[str] = []

    check_manifest(manifest, "case-a", "round-a", root, round_dir, False, errors, [])

    assert "supporting_work_artifacts must be a list" in errors


def test_review_manifest_validates_artifact_refs_against_manifest_records(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    output = round_dir / "outputs" / "oponent_podklady_revidovane.md"
    output.parent.mkdir(parents=True)
    output.write_text("# Reviewed\n", encoding="utf-8")
    assignment = round_dir / "work" / "assignment_coverage_agent.json"
    assignment.parent.mkdir(parents=True)
    assignment.write_text("{}\n", encoding="utf-8")
    manifest = {
        "schema_version": "review-manifest-v1",
        "case_id": "case-a",
        "round_id": "round-a",
        "manifest_path": "work/review_manifest.json",
        "inputs": [],
        "extracted_artifacts": [],
        "notes": [],
        "supporting_work_artifacts": [],
        "workflow_limitations": [
            {"scope": "code", "description": "No code was submitted.", "impact": "None.", "status": "closed"}
        ],
        "artifacts": [
            {
                "path": "outputs/oponent_podklady_revidovane.md",
                "artifact_sha256": "stale",
                "artifact_type": "opponent_materials_reviewed",
                "review_scope": "standalone_final",
                "skills": [],
                "generated_by": [],
                "independent_review": {"status": "not_required"},
                "helper_checks": [],
                "input_refs": ["/home/private/input.pdf"],
                "evidence_refs": ["work/assignment_coverage_agent.json"],
                "check_refs": ["missing-check"],
            }
        ],
        "helper_checks": [],
    }
    errors: list[str] = []

    check_manifest(manifest, "case-a", "round-a", root, round_dir, False, errors, [])

    assert any("input_refs item 1: path must be relative inside the round" in error for error in errors)
    assert any(
        "evidence_refs item 1 is not recorded in manifest supporting_work_artifacts/artifacts" in error
        for error in errors
    )
    assert any("check_refs item 1 is not a manifest helper check" in error for error in errors)


def test_review_manifest_validates_known_output_metadata_against_registry(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    output = round_dir / "outputs" / "code_quality_review.md"
    output.parent.mkdir(parents=True)
    output.write_text("# Code Quality\n", encoding="utf-8")
    manifest = {
        "schema_version": "review-manifest-v1",
        "case_id": "case-a",
        "round_id": "round-a",
        "manifest_path": "work/review_manifest.json",
        "inputs": [],
        "extracted_artifacts": [],
        "notes": [],
        "supporting_work_artifacts": [],
        "workflow_limitations": [],
        "artifacts": [
            {
                "path": "outputs/code_quality_review.md",
                "artifact_sha256": sha256_file(output),
                "artifact_type": "generated_markdown",
                "review_scope": "standalone_final",
                "skills": [],
                "generated_by": [{"role": "not_recorded", "agent": "not_recorded", "contribution": "generation"}],
                "independent_review": {"status": "not_recorded"},
                "helper_checks": [],
                "limitations": [],
            }
        ],
        "helper_checks": [],
    }
    errors: list[str] = []

    check_manifest(manifest, "case-a", "round-a", root, round_dir, False, errors, [])

    assert "outputs/code_quality_review.md: artifact_type must be code_quality_review" in errors
    assert "outputs/code_quality_review.md: skills must be ['thesis-code-quality-review']" in errors
    assert any("review_scope must be one of covered_by_synthesis, internal_only" in error for error in errors)


def test_review_manifest_requires_internal_evidence_validators_when_artifacts_exist(tmp_path: Path) -> None:
    from thesis_review_workflow.cli.check_review_manifest import required_checks as check_required_checks
    from thesis_review_workflow.cli.init_review_manifest import required_checks as init_required_checks

    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    paths = {
        "outputs/code_consistency.md",
        "outputs/code_quality_review.md",
        "outputs/literature_citation_review.md",
        "outputs/revision_diff.md",
        "outputs/reviewer_calibration_profile.md",
    }

    manifest = {
        "supporting_work_artifacts": [
            {
                "path": "work/quantitative_claims.json",
                "kind": "structured_data",
                "artifact_sha256": "0" * 64,
            }
        ]
    }

    init_names = {item["check"] for item in init_required_checks("case-a", "round-a", paths, round_dir, manifest)}
    check_names = check_required_checks(paths, round_dir, manifest)

    assert "check-code-consistency" in init_names
    assert "check-code-quality-review" in init_names
    assert "check-literature-citation-review" in init_names
    assert "check-revision-diff" in init_names
    assert "check-opponent-calibration-profile" in init_names
    assert "check-evaluation-claims" in init_names
    assert "check-code-consistency" in check_names
    assert "check-code-quality-review" in check_names
    assert "check-literature-citation-review" in check_names
    assert "check-revision-diff" in check_names
    assert "check-opponent-calibration-profile" in check_names
    assert "check-evaluation-claims" in check_names


def test_review_manifest_requires_theses_similarity_validator_when_evidence_exists(tmp_path: Path) -> None:
    from thesis_review_workflow.cli.check_review_manifest import required_checks as check_required_checks
    from thesis_review_workflow.cli.init_review_manifest import required_checks as init_required_checks

    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    intake = round_dir / "work" / "theses_similarity" / "intake.json"
    intake.parent.mkdir(parents=True)
    intake.write_text("{}\n", encoding="utf-8")
    paths = {"outputs/theses_similarity_review.md"}
    manifest = {"supporting_work_artifacts": [{"path": "work/theses_similarity/intake.json"}]}

    init_checks = init_required_checks("case-a", "round-a", paths, round_dir, manifest)
    init_names = {item["check"] for item in init_checks}
    check_names = check_required_checks(paths, round_dir, manifest)
    theses_check = next(item for item in init_checks if item["check"] == "check-theses-similarity-report")

    assert "check-theses-similarity-report" in init_names
    assert "check-theses-similarity-report" in check_names
    assert theses_check["command"] == "check-theses-similarity-report case-a round-a"
    assert "work/theses_similarity/intake.json" in theses_check["target_artifacts"]


def test_review_manifest_requires_theses_similarity_validator_for_partial_raw_report(tmp_path: Path) -> None:
    from thesis_review_workflow.cli.check_review_manifest import required_checks as check_required_checks
    from thesis_review_workflow.cli.init_review_manifest import required_checks as init_required_checks

    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    report = round_dir / "inputs" / "theses_similarity" / "report.pdf"
    report.parent.mkdir(parents=True)
    report.write_bytes(b"%PDF synthetic\n")
    paths: set[str] = set()
    manifest: dict[str, object] = {}

    init_names = {item["check"] for item in init_required_checks("case-a", "round-a", paths, round_dir, manifest)}
    check_names = check_required_checks(paths, round_dir, manifest)

    assert "check-theses-similarity-report" in init_names
    assert "check-theses-similarity-report" in check_names


def test_init_manifest_required_checks_use_logical_commands(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    checks = required_checks(
        "case-a",
        "round-a",
        {"outputs/feedback_student.md"},
        round_dir,
        {},
    )

    commands = {item["check"]: item["command"] for item in checks}

    assert commands["check-supervisor-ready"] == "check-supervisor-ready case-a round-a"
    assert commands["check-feedback-output"] == "check-feedback-output case-a round-a"
    assert commands["check-review-manifest"] == "check-review-manifest --require-complete case-a round-a"
    assert all(not command.startswith("scripts/") for command in commands.values())


def test_run_check_record_executes_generated_logical_command(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    round_dir.mkdir(parents=True)
    module_dir = root / "src" / "thesis_review_workflow" / "cli"
    module_dir.mkdir(parents=True)
    (module_dir.parent / "__init__.py").write_text("", encoding="utf-8")
    (module_dir / "__init__.py").write_text("", encoding="utf-8")
    (module_dir / "check_reviewer_profile.py").write_text(
        "import sys\n"
        "\n"
        "def main(argv):\n"
        "    return 0 if argv[1:] == ['case-a'] else 1\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    raise SystemExit(main(sys.argv))\n",
        encoding="utf-8",
    )
    check: dict[str, object] = {
        "check": "check-reviewer-profile",
        "command": "check-reviewer-profile case-a",
        "target_artifacts": [],
        "target_sha256": {},
        "status": "not_recorded",
        "checked_at": "",
        "exit_code": None,
        "notes": "",
    }

    run_check_record(root, round_dir, check)

    assert check["status"] == "passed", check["notes"]
    assert check["exit_code"] == 0


def test_review_manifest_requires_opponent_report_trace_check_target(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    materials = round_dir / "outputs" / "oponent_podklady_revidovane.md"
    trace = round_dir / "work" / "opponent_report_trace.json"
    materials.parent.mkdir(parents=True)
    trace.parent.mkdir(parents=True)
    materials.write_text("# Reviewed materials\n", encoding="utf-8")
    trace.write_text("{}\n", encoding="utf-8")
    errors: list[str] = []

    check_helper_checks(
        [
            {
                "check": "check-opponent-report",
                "command": "scripts/check-opponent-report case-a round-a",
                "target_artifacts": ["outputs/oponent_podklady_revidovane.md"],
                "target_sha256": {"outputs/oponent_podklady_revidovane.md": "0" * 64},
                "status": "passed",
                "checked_at": "2026-05-07T00:00:00Z",
                "exit_code": 0,
            }
        ],
        {"check-opponent-report"},
        round_dir,
        True,
        errors,
        [],
    )

    assert (
        "helper_checks check-opponent-report: missing required target artifact work/opponent_report_trace.json"
        in errors
    )


def test_review_manifest_requires_theses_similarity_check_targets(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    intake = round_dir / "work" / "theses_similarity" / "intake.json"
    output = round_dir / "outputs" / "theses_similarity_review.md"
    intake.parent.mkdir(parents=True)
    output.parent.mkdir(parents=True)
    intake.write_text("{}\n", encoding="utf-8")
    output.write_text("# Review\n", encoding="utf-8")
    errors: list[str] = []

    check_helper_checks(
        [
            {
                "check": "check-theses-similarity-report",
                "command": "check-theses-similarity-report case-a round-a",
                "target_artifacts": ["outputs/theses_similarity_review.md"],
                "target_sha256": {"outputs/theses_similarity_review.md": sha256_file(output)},
                "status": "passed",
                "checked_at": "2026-05-12T12:00:00Z",
                "exit_code": 0,
            }
        ],
        {"check-theses-similarity-report"},
        round_dir,
        True,
        errors,
        [],
    )

    assert (
        "helper_checks check-theses-similarity-report: missing required target artifact "
        "work/theses_similarity/intake.json"
    ) in errors


def test_review_manifest_theses_similarity_targets_exclude_approval_record(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    for rel_path in (
        "work/theses_similarity/intake.json",
        "outputs/theses_similarity_review.md",
        "work/reviews/theses_similarity_review.json",
    ):
        path = round_dir / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic fixture\n", encoding="utf-8")

    targets = required_helper_targets("check-theses-similarity-report", round_dir)

    assert "work/reviews/theses_similarity_review.json" not in targets
    assert targets == {"work/theses_similarity/intake.json", "outputs/theses_similarity_review.md"}


def test_review_manifest_requires_agent_coverage_check_target() -> None:
    round_dir = Path("/synthetic/repo/cases/case-a/rounds/round-a")

    assert required_helper_targets("check-agent-coverage", round_dir) == {COVERAGE_REL.as_posix()}


def test_review_manifest_rejects_agent_coverage_check_without_coverage_target(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    output = round_dir / "outputs" / "feedback_student.md"
    coverage = round_dir / COVERAGE_REL
    output.parent.mkdir(parents=True)
    coverage.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("# Feedback\n", encoding="utf-8")
    coverage.write_text("{}\n", encoding="utf-8")
    errors: list[str] = []

    check_helper_checks(
        [
            {
                "check": "check-agent-coverage",
                "command": "check-agent-coverage case-a round-a",
                "target_artifacts": ["outputs/feedback_student.md"],
                "target_sha256": {
                    "outputs/feedback_student.md": sha256_file(output),
                    COVERAGE_REL.as_posix(): sha256_file(coverage),
                },
                "dependency_sha256": helper_dependency_hashes(round_dir, "check-agent-coverage"),
                "checker_version": workflow_checker_version(root),
                "status": "passed",
                "checked_at": "2026-05-13T00:00:00Z",
                "exit_code": 0,
            }
        ],
        {"check-agent-coverage"},
        round_dir,
        True,
        errors,
        [],
    )

    assert f"helper_checks check-agent-coverage: missing required target artifact {COVERAGE_REL.as_posix()}" in errors


def test_review_manifest_rejects_stale_helper_dependency_hash(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    case_dir = root / "cases" / "case-a"
    output = round_dir / "outputs" / "feedback_student.md"
    case_dir.mkdir(parents=True)
    output.parent.mkdir(parents=True)
    (case_dir / "case.md").write_text("# Case\n", encoding="utf-8")
    (case_dir / "current-round.txt").write_text("round-a\n", encoding="utf-8")
    output.write_text("# Feedback\n", encoding="utf-8")
    errors: list[str] = []

    check_helper_checks(
        [
            {
                "check": "check-supervisor-ready",
                "command": "check-supervisor-ready case-a round-a",
                "target_artifacts": ["outputs/feedback_student.md"],
                "target_sha256": {"outputs/feedback_student.md": sha256_file(output)},
                "dependency_sha256": {"case:case.md": "0" * 64},
                "checker_version": workflow_checker_version(root),
                "status": "passed",
                "checked_at": "2026-05-13T00:00:00Z",
                "exit_code": 0,
            }
        ],
        {"check-supervisor-ready"},
        round_dir,
        True,
        errors,
        [],
    )

    assert "helper_checks check-supervisor-ready: dependency_sha256 is stale" in errors


def test_review_manifest_rejects_stale_helper_checker_version(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    output = round_dir / "outputs" / "feedback_student.md"
    output.parent.mkdir(parents=True)
    output.write_text("# Feedback\n", encoding="utf-8")
    errors: list[str] = []

    check_helper_checks(
        [
            {
                "check": "check-supervisor-ready",
                "command": "check-supervisor-ready case-a round-a",
                "target_artifacts": ["outputs/feedback_student.md"],
                "target_sha256": {"outputs/feedback_student.md": sha256_file(output)},
                "dependency_sha256": helper_dependency_hashes(round_dir, "check-supervisor-ready"),
                "checker_version": "stale-checker-version",
                "status": "passed",
                "checked_at": "2026-05-13T00:00:00Z",
                "exit_code": 0,
            }
        ],
        {"check-supervisor-ready"},
        round_dir,
        True,
        errors,
        [],
    )

    assert "helper_checks check-supervisor-ready: checker_version is stale" in errors


def test_review_manifest_requires_calibration_profile_check_targets(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    for rel_path in (
        "outputs/reviewer_calibration_profile.md",
        "work/calibration/reviewer_calibration_profile.json",
        "work/calibration/reviewer_checklist.json",
        "work/calibration/reviewer_calibration_profile_history.jsonl",
        "work/calibration/reviewer_profile_change_log.md",
        "work/calibration/profile_review.md",
        "work/calibration/historical_case_analyses/case-001.json",
        "work/calibration/historical_case_analyses/nested/case-002.json",
    ):
        path = round_dir / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic fixture\n", encoding="utf-8")
    errors: list[str] = []

    check_helper_checks(
        [
            {
                "check": "check-opponent-calibration-profile",
                "command": "scripts/check-opponent-calibration-profile case-a round-a",
                "target_artifacts": ["outputs/reviewer_calibration_profile.md"],
                "target_sha256": {"outputs/reviewer_calibration_profile.md": "0" * 64},
                "status": "passed",
                "checked_at": "2026-05-07T00:00:00Z",
                "exit_code": 0,
            }
        ],
        {"check-opponent-calibration-profile"},
        round_dir,
        True,
        errors,
        [],
    )

    assert (
        "helper_checks check-opponent-calibration-profile: missing required target artifact "
        "work/calibration/reviewer_calibration_profile.json"
    ) in errors
    assert (
        "helper_checks check-opponent-calibration-profile: missing required target artifact "
        "work/calibration/historical_case_analyses/nested/case-002.json"
    ) in errors
    assert "work/calibration/profile_review.md" in required_helper_targets(
        "check-opponent-calibration-profile", round_dir
    )


def test_review_manifest_requires_supervisor_calibration_profile_check_targets(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    for rel_path in (
        "outputs/supervisor_report_calibration_profile.md",
        "work/calibration/supervisor_report/profile.json",
        "work/calibration/supervisor_report/checklist.json",
        "work/calibration/supervisor_report/profile_history.jsonl",
        "work/calibration/supervisor_report/profile_change_log.md",
        "work/calibration/supervisor_report/profile_review.md",
        "work/calibration/supervisor_report/historical_case_analyses/case-001.json",
    ):
        path = round_dir / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic fixture\n", encoding="utf-8")
    errors: list[str] = []

    check_helper_checks(
        [
            {
                "check": "check-supervisor-report-calibration-profile",
                "command": "check-supervisor-report-calibration-profile case-a round-a",
                "target_artifacts": ["outputs/supervisor_report_calibration_profile.md"],
                "target_sha256": {"outputs/supervisor_report_calibration_profile.md": "0" * 64},
                "status": "passed",
                "checked_at": "2026-05-12T00:00:00Z",
                "exit_code": 0,
            }
        ],
        {"check-supervisor-report-calibration-profile"},
        round_dir,
        True,
        errors,
        [],
    )

    assert (
        "helper_checks check-supervisor-report-calibration-profile: missing required target artifact "
        "work/calibration/supervisor_report/profile.json"
    ) in errors
    assert "work/calibration/supervisor_report/profile_review.md" in required_helper_targets(
        "check-supervisor-report-calibration-profile", round_dir
    )


def test_supervisor_calibration_profile_manifest_requires_independent_generator_and_reviewer(tmp_path: Path) -> None:
    from thesis_review_workflow.cli.check_supervisor_report_calibration_profile import manifest_profile_errors

    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    profile_md = round_dir / "outputs/supervisor_report_calibration_profile.md"
    review = round_dir / "work/calibration/supervisor_report/profile_review.md"
    analysis = round_dir / "work/calibration/supervisor_report/historical_case_analyses/case-001.json"
    profile_md.parent.mkdir(parents=True)
    review.parent.mkdir(parents=True)
    analysis.parent.mkdir(parents=True)
    profile_md.write_text("# Profile\n", encoding="utf-8")
    review.write_text("# Review\n", encoding="utf-8")
    analysis.write_text("{}\n", encoding="utf-8")
    manifest_path = round_dir / "work/review_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "review-manifest-v1",
                "case_id": "case-a",
                "round_id": "round-a",
                "artifacts": [
                    {
                        "path": "outputs/supervisor_report_calibration_profile.md",
                        "artifact_sha256": sha256_file(profile_md),
                        "artifact_type": "supervisor_report_calibration_profile",
                        "skills": ["historical-supervisor-report-calibration"],
                        "review_scope": "internal_only",
                        "generated_by": [{"role": "same-role", "agent": "same-agent"}],
                        "limitations": ["Synthetic."],
                        "evidence_refs": [
                            "work/calibration/supervisor_report/profile.json",
                            "work/calibration/supervisor_report/checklist.json",
                            "work/calibration/supervisor_report/profile_history.jsonl",
                            "work/calibration/supervisor_report/profile_change_log.md",
                            "work/calibration/supervisor_report/profile_review.md",
                            "work/calibration/supervisor_report/historical_case_analyses/case-001.json",
                        ],
                        "independent_review": {
                            "status": "reviewed",
                            "reviewer_role": "same-role",
                            "reviewer_agent": "same-agent",
                            "reviewed_at": "2026-05-12T00:00:00Z",
                            "reviewed_hash": sha256_file(profile_md),
                            "review_basis_path": "work/calibration/supervisor_report/profile_review.md",
                            "review_basis_sha256": sha256_file(review),
                        },
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    errors = manifest_profile_errors(
        round_dir,
        ["work/calibration/supervisor_report/historical_case_analyses/case-001.json"],
    )

    assert (
        "outputs/supervisor_report_calibration_profile.md: generator and reviewer agent must be independent" in errors
    )
    assert "outputs/supervisor_report_calibration_profile.md: generator and reviewer role must be independent" in errors


def test_init_manifest_keeps_calibration_profile_independently_reviewed_with_synthesis(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    outputs = round_dir / "outputs"
    outputs.mkdir(parents=True)
    (outputs / "oponent_podklady_revidovane.md").write_text("# Reviewed materials\n", encoding="utf-8")
    (outputs / "reviewer_calibration_profile.md").write_text("# Calibration profile\n", encoding="utf-8")
    (outputs / "reference_report_comparison.md").write_text("# Reference comparison\n", encoding="utf-8")
    (outputs / "opponent_reading_packet.md").write_text("# Reading packet\n", encoding="utf-8")

    artifacts = output_artifacts(round_dir, {})
    by_path = {item["path"]: item for item in artifacts}

    assert by_path["outputs/oponent_podklady_revidovane.md"]["review_scope"] == "standalone_final"
    assert by_path["outputs/reviewer_calibration_profile.md"]["review_scope"] == "internal_only"
    assert by_path["outputs/reference_report_comparison.md"]["review_scope"] == "internal_only"
    assert by_path["outputs/opponent_reading_packet.md"]["review_scope"] == "internal_only"


def test_init_manifest_repairs_stale_synthesis_scope_for_calibration_outputs(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    outputs = round_dir / "outputs"
    outputs.mkdir(parents=True)
    (outputs / "oponent_podklady_revidovane.md").write_text("# Reviewed materials\n", encoding="utf-8")
    (outputs / "reference_report_comparison.md").write_text("# Reference comparison\n", encoding="utf-8")

    artifacts = output_artifacts(
        round_dir,
        {
            "artifacts": [
                {
                    "path": "outputs/reference_report_comparison.md",
                    "review_scope": "covered_by_synthesis",
                    "independent_review": {
                        "status": "not_required",
                        "covered_by_artifact": "outputs/oponent_podklady_revidovane.md",
                    },
                }
            ]
        },
    )
    by_path = {item["path"]: item for item in artifacts}

    assert by_path["outputs/reference_report_comparison.md"]["review_scope"] == "internal_only"
    assert by_path["outputs/reference_report_comparison.md"]["independent_review"]["status"] == "not_recorded"


def test_init_manifest_marks_changed_helper_target_set_stale() -> None:
    generated = [
        {
            "check": "check-opponent-report",
            "command": "scripts/check-opponent-report case-a round-a",
            "target_artifacts": ["work/opponent_report_trace.json", "outputs/oponent_podklady_revidovane.md"],
            "target_sha256": {
                "work/opponent_report_trace.json": "1" * 64,
                "outputs/oponent_podklady_revidovane.md": "2" * 64,
            },
            "status": "not_recorded",
            "checked_at": "",
            "exit_code": None,
            "notes": "new",
        }
    ]
    existing = {
        "helper_checks": [
            {
                "check": "check-opponent-report",
                "command": "scripts/check-opponent-report case-a round-a",
                "target_artifacts": ["outputs/oponent_podklady_revidovane.md"],
                "target_sha256": {
                    "work/opponent_report_trace.json": "1" * 64,
                    "outputs/oponent_podklady_revidovane.md": "2" * 64,
                },
                "status": "passed",
                "checked_at": "2026-05-07T00:00:00Z",
                "exit_code": 0,
                "notes": "old",
            }
        ]
    }

    merged = merge_checks(existing, generated)

    assert merged[0]["status"] == "not_recorded"
    assert "Target artifact set changed" in merged[0]["notes"]
    assert merged[0]["target_artifacts"] == [
        "work/opponent_report_trace.json",
        "outputs/oponent_podklady_revidovane.md",
    ]


def test_init_manifest_preserves_status_when_command_surface_changes() -> None:
    generated = [
        {
            "check": "check-opponent-report",
            "command": "check-opponent-report case-a round-a",
            "target_artifacts": ["work/opponent_report_trace.json", "outputs/oponent_podklady_revidovane.md"],
            "target_sha256": {
                "work/opponent_report_trace.json": "1" * 64,
                "outputs/oponent_podklady_revidovane.md": "2" * 64,
            },
            "checker_version": "checker-a",
            "status": "not_recorded",
            "checked_at": "",
            "exit_code": None,
            "notes": "new",
        }
    ]
    existing = {
        "helper_checks": [
            {
                "check": "check-opponent-report",
                "command": "scripts/check-opponent-report case-a round-a",
                "target_artifacts": ["work/opponent_report_trace.json", "outputs/oponent_podklady_revidovane.md"],
                "target_sha256": {
                    "work/opponent_report_trace.json": "1" * 64,
                    "outputs/oponent_podklady_revidovane.md": "2" * 64,
                },
                "checker_version": "checker-a",
                "status": "passed",
                "checked_at": "2026-05-07T00:00:00Z",
                "exit_code": 0,
                "notes": "old",
            }
        ]
    }

    merged = merge_checks(existing, generated)

    assert merged[0]["status"] == "passed"
    assert merged[0]["command"] == "check-opponent-report case-a round-a"
    assert merged[0]["checker_version"] == "checker-a"


def test_init_manifest_marks_changed_checker_version_stale() -> None:
    generated = [
        {
            "check": "check-opponent-report",
            "command": "check-opponent-report case-a round-a",
            "target_artifacts": ["outputs/oponent_podklady_revidovane.md"],
            "target_sha256": {"outputs/oponent_podklady_revidovane.md": "2" * 64},
            "checker_version": "checker-b",
            "status": "not_recorded",
            "checked_at": "",
            "exit_code": None,
            "notes": "new",
        }
    ]
    existing = {
        "helper_checks": [
            {
                "check": "check-opponent-report",
                "command": "scripts/check-opponent-report case-a round-a",
                "target_artifacts": ["outputs/oponent_podklady_revidovane.md"],
                "target_sha256": {"outputs/oponent_podklady_revidovane.md": "2" * 64},
                "checker_version": "checker-a",
                "status": "passed",
                "checked_at": "2026-05-07T00:00:00Z",
                "exit_code": 0,
                "notes": "old",
            }
        ]
    }

    merged = merge_checks(existing, generated)

    assert merged[0]["status"] == "not_recorded"
    assert "Checker version changed" in merged[0]["notes"]


def test_init_manifest_does_not_reuse_failed_helper_check() -> None:
    generated = [
        {
            "check": "check-opponent-report",
            "command": "check-opponent-report case-a round-a",
            "target_artifacts": ["outputs/oponent_podklady_revidovane.md"],
            "target_sha256": {"outputs/oponent_podklady_revidovane.md": "2" * 64},
            "checker_version": "checker-a",
            "status": "not_recorded",
            "checked_at": "",
            "exit_code": None,
            "notes": "new",
        }
    ]
    existing = {
        "helper_checks": [
            {
                "check": "check-opponent-report",
                "command": "scripts/check-opponent-report case-a round-a",
                "target_artifacts": ["outputs/oponent_podklady_revidovane.md"],
                "target_sha256": {"outputs/oponent_podklady_revidovane.md": "2" * 64},
                "checker_version": "checker-a",
                "status": "failed",
                "checked_at": "2026-05-07T00:00:00Z",
                "exit_code": 1,
                "notes": "old",
            }
        ]
    }

    merged = merge_checks(existing, generated)

    assert merged[0]["status"] == "not_recorded"
    assert "not a passed reusable result" in merged[0]["notes"]


def test_init_manifest_marks_changed_helper_dependency_hash_stale() -> None:
    generated = [
        {
            "check": "check-supervisor-ready",
            "command": "check-supervisor-ready case-a round-a",
            "target_artifacts": ["outputs/feedback_student.md"],
            "target_sha256": {"outputs/feedback_student.md": "2" * 64},
            "dependency_sha256": {"case:case.md": "b" * 64},
            "checker_version": "checker-a",
            "status": "not_recorded",
            "checked_at": "",
            "exit_code": None,
            "notes": "new",
        }
    ]
    existing = {
        "helper_checks": [
            {
                "check": "check-supervisor-ready",
                "command": "scripts/check-supervisor-ready case-a round-a",
                "target_artifacts": ["outputs/feedback_student.md"],
                "target_sha256": {"outputs/feedback_student.md": "2" * 64},
                "dependency_sha256": {"case:case.md": "a" * 64},
                "checker_version": "checker-a",
                "status": "passed",
                "checked_at": "2026-05-07T00:00:00Z",
                "exit_code": 0,
                "notes": "old",
            }
        ]
    }

    merged = merge_checks(existing, generated)

    assert merged[0]["status"] == "not_recorded"
    assert "Helper dependency hash changed" in merged[0]["notes"]


def test_register_output_artifact_records_review_metadata(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    artifact = round_dir / "outputs" / "code_quality_review.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("# Internal Code Quality Review\n", encoding="utf-8")
    (round_dir / "outputs/oponent_podklady_revidovane.md").write_text("# Reviewed materials\n", encoding="utf-8")
    (round_dir / "notes").mkdir(parents=True, exist_ok=True)
    (round_dir / "notes/assignment.md").write_text("# Assignment\n", encoding="utf-8")
    (round_dir / "work").mkdir(parents=True, exist_ok=True)
    (round_dir / "work/code_reproducibility.json").write_text("{}\n", encoding="utf-8")
    manifest = ensure_manifest({}, "case-a", "round-a")

    register_artifact(
        manifest,
        round_dir,
        "outputs/code_quality_review.md",
        role="thesis-code-quality-review",
        agent="generator-agent",
        contribution="generation",
        review_scope="internal_only",
        review_status="reviewed",
        reviewer_role="evidence-calibration-reviewer",
        reviewer_agent="reviewer-agent",
        reviewed_at="2026-05-06T00:00:00Z",
        limitation=["Static review only."],
        feeds=["outputs/oponent_podklady_revidovane.md"],
        input_refs=["notes/assignment.md"],
        evidence_refs=["work/code_reproducibility.json"],
        check_refs=["check-code-quality-review"],
        used_findings="Implementation risk summary.",
        review_basis_path="",
        notes="Registered by helper.",
    )

    entry = manifest["artifacts"][0]

    assert entry["artifact_sha256"] == sha256_file(artifact)
    assert entry["generated_by"][0]["agent"] == "generator-agent"
    assert entry["independent_review"]["reviewed_hash"] == entry["artifact_sha256"]
    assert entry["limitations"] == ["Static review only."]
    assert entry["feeds"] == ["outputs/oponent_podklady_revidovane.md"]
    assert "outputs/oponent_podklady_revidovane.md" not in entry["evidence_refs"]
    assert "outputs/oponent_podklady_revidovane.md" not in entry["source_sha256"]
    assert entry["source_sha256"]["work/code_reproducibility.json"] == sha256_file(
        round_dir / "work/code_reproducibility.json"
    )


def test_reviewer_calibration_profile_manifest_defaults() -> None:
    artifact_type, skills, scope = output_defaults("outputs/reviewer_calibration_profile.md")

    assert artifact_type == "opponent_reviewer_calibration_profile"
    assert skills == ["historical-opponent-calibration"]
    assert scope == "internal_only"

    supervisor_type, supervisor_skills, supervisor_scope = output_defaults(
        "outputs/supervisor_report_calibration_profile.md"
    )

    assert supervisor_type == "supervisor_report_calibration_profile"
    assert supervisor_skills == ["historical-supervisor-report-calibration"]
    assert supervisor_scope == "internal_only"


def test_current_case_calibration_output_manifest_defaults() -> None:
    comparison_type, comparison_skills, comparison_scope = output_defaults("outputs/reference_report_comparison.md")
    packet_type, packet_skills, packet_scope = output_defaults("outputs/opponent_reading_packet.md")

    assert comparison_type == "reference_report_comparison"
    assert comparison_skills == ["historical-opponent-calibration"]
    assert comparison_scope == "internal_only"
    assert packet_type == "opponent_reading_packet"
    assert packet_skills == ["historical-opponent-calibration"]
    assert packet_scope == "internal_only"


def source_sha256(round_dir: Path, refs: list[str]) -> dict[str, str]:
    return {ref: sha256_file(round_dir / ref) for ref in refs}


def reviewed_internal_artifact(
    round_dir: Path,
    rel_path: str,
    *,
    reviewed: bool = True,
    input_refs: list[str] | None = None,
    evidence_refs: list[str] | None = None,
    generator_agent: str = "generator-agent",
) -> dict[str, object]:
    artifact = round_dir / rel_path
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(f"# {Path(rel_path).stem}\n", encoding="utf-8")
    current_hash = sha256_file(artifact)
    inputs = input_refs or []
    evidence = evidence_refs or []
    return {
        "path": rel_path,
        "artifact_type": output_defaults(rel_path)[0],
        "artifact_sha256": current_hash,
        "review_scope": "internal_only",
        "skills": output_defaults(rel_path)[1],
        "generated_by": [
            {
                "role": "historical-opponent-calibration",
                "agent": generator_agent,
                "contribution": "generation",
                "notes": "Synthetic generator.",
            }
        ],
        "independent_review": {
            "status": "reviewed" if reviewed else "not_recorded",
            "reviewer_role": "anti-overfit-reviewer" if reviewed else "not_recorded",
            "reviewer_agent": "reviewer-agent" if reviewed else "not_recorded",
            "reviewed_at": "2026-05-07T00:00:00Z" if reviewed else "",
            "reviewed_hash": current_hash if reviewed else "",
            "covered_by_artifact": "",
            "used_findings": "",
            "exception": "",
            "notes": "Synthetic independent review." if reviewed else "",
        },
        "helper_checks": [],
        "limitations": ["Synthetic fixture."],
        "input_refs": inputs,
        "evidence_refs": evidence,
        "source_sha256": source_sha256(round_dir, inputs + evidence),
        "check_refs": [],
    }


def calibration_outputs_manifest(round_dir: Path, *, reviewed: bool = True) -> dict[str, object]:
    manifest_path = round_dir / "work/review_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("{}\n", encoding="utf-8")
    notes_path = round_dir / "notes/assignment.md"
    sources_path = round_dir / "work/opponent_packets/current_case_sources.md"
    calibration_path = round_dir / "work/opponent_packets/calibration_context.md"
    for path, content in (
        (notes_path, "# Assignment\n"),
        (sources_path, "# Current case sources\n"),
        (calibration_path, "# Calibration context\n"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return {
        "schema_version": "review-manifest-v1",
        "case_id": "case-a",
        "round_id": "round-a",
        "updated_at": "2026-05-07T00:00:00Z",
        "manifest_path": "work/review_manifest.json",
        "inputs": [],
        "extracted_artifacts": [],
        "notes": [{"path": "notes/assignment.md", "kind": "text"}],
        "supporting_work_artifacts": [
            {
                "path": "work/opponent_packets/current_case_sources.md",
                "kind": "text",
                "artifact_sha256": sha256_file(sources_path),
            },
            {
                "path": "work/opponent_packets/calibration_context.md",
                "kind": "text",
                "artifact_sha256": sha256_file(calibration_path),
            },
        ],
        "workflow_limitations": [],
        "helper_checks": [
            {
                "check": "check-review-manifest",
                "command": "scripts/check-review-manifest --require-complete case-a round-a",
                "target_artifacts": [
                    "outputs/opponent_reading_packet.md",
                    "outputs/reference_report_comparison.md",
                ],
                "target_sha256": {},
                "status": "not_applicable",
                "checked_at": "",
                "exit_code": None,
                "notes": "Self check.",
            }
        ],
        "artifacts": [
            reviewed_internal_artifact(
                round_dir,
                "outputs/reference_report_comparison.md",
                reviewed=reviewed,
                input_refs=["notes/assignment.md"],
                evidence_refs=[
                    "work/opponent_packets/current_case_sources.md",
                    "work/opponent_packets/calibration_context.md",
                ],
                generator_agent="comparison-generator",
            ),
            reviewed_internal_artifact(
                round_dir,
                "outputs/opponent_reading_packet.md",
                reviewed=reviewed,
                input_refs=["notes/assignment.md"],
                evidence_refs=[
                    "work/opponent_packets/current_case_sources.md",
                    "work/opponent_packets/calibration_context.md",
                    "outputs/reference_report_comparison.md",
                ],
                generator_agent="packet-generator",
            ),
        ],
    }


def test_current_case_calibration_outputs_require_independent_review_in_closeout(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    manifest = calibration_outputs_manifest(round_dir, reviewed=False)
    errors: list[str] = []

    check_manifest(manifest, "case-a", "round-a", root, round_dir, True, errors, [])

    assert any(
        "outputs/reference_report_comparison.md: calibrated internal evidence requires a recorded independent review"
        in error
        for error in errors
    )
    assert any(
        "outputs/opponent_reading_packet.md: calibrated internal evidence requires a recorded independent review"
        in error
        for error in errors
    )


def test_current_case_calibration_outputs_pass_with_current_review_hashes(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    manifest = calibration_outputs_manifest(round_dir, reviewed=True)
    errors: list[str] = []

    check_manifest(manifest, "case-a", "round-a", root, round_dir, True, errors, [])

    assert errors == []


def test_current_case_calibration_outputs_reject_stale_review_hash(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    manifest = calibration_outputs_manifest(round_dir, reviewed=True)
    (round_dir / "outputs/reference_report_comparison.md").write_text("# Edited\n", encoding="utf-8")
    updated_hash = sha256_file(round_dir / "outputs/reference_report_comparison.md")
    artifacts = manifest["artifacts"]
    assert isinstance(artifacts, list)
    for artifact in artifacts:
        assert isinstance(artifact, dict)
        if artifact["path"] == "outputs/reference_report_comparison.md":
            artifact["artifact_sha256"] = updated_hash
    errors: list[str] = []

    check_manifest(manifest, "case-a", "round-a", root, round_dir, True, errors, [])

    assert any("outputs/reference_report_comparison.md: review is stale_after_edit" in error for error in errors)


def test_current_case_calibration_outputs_require_recorded_generator(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    manifest = calibration_outputs_manifest(round_dir, reviewed=True)
    artifacts = manifest["artifacts"]
    assert isinstance(artifacts, list)
    for artifact in artifacts:
        assert isinstance(artifact, dict)
        if artifact["path"] == "outputs/reference_report_comparison.md":
            artifact["generated_by"] = [
                {
                    "role": "not_recorded",
                    "agent": "not_recorded",
                    "contribution": "generation",
                    "notes": "",
                }
            ]
    errors: list[str] = []

    check_manifest(manifest, "case-a", "round-a", root, round_dir, True, errors, [])

    assert any(
        "outputs/reference_report_comparison.md: calibrated internal evidence requires a recorded generator" in error
        for error in errors
    )


def test_current_case_calibration_outputs_reject_stale_source_hash(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    manifest = calibration_outputs_manifest(round_dir, reviewed=True)
    (round_dir / "work/opponent_packets/current_case_sources.md").write_text("# Changed\n", encoding="utf-8")
    errors: list[str] = []

    check_manifest(manifest, "case-a", "round-a", root, round_dir, True, errors, [])

    expected = (
        "outputs/reference_report_comparison.md: "
        "source_sha256 is stale for work/opponent_packets/current_case_sources.md"
    )
    assert any(expected in error for error in errors)


def test_source_hash_check_covers_output_sources(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    source = round_dir / "outputs/oponent_podklady_revidovane.md"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("# Reviewed materials\n", encoding="utf-8")
    artifact = {
        "source_sha256": {
            "outputs/oponent_podklady_revidovane.md": sha256_file(source),
        }
    }
    source.write_text("# Edited reviewed materials\n", encoding="utf-8")
    errors: list[str] = []

    check_source_hashes(
        "outputs/reference_report_comparison.md",
        artifact,
        ["outputs/oponent_podklady_revidovane.md"],
        round_dir,
        errors,
    )

    assert errors == [
        "outputs/reference_report_comparison.md: source_sha256 is stale for outputs/oponent_podklady_revidovane.md"
    ]


def test_register_work_artifact_records_supporting_metadata(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    artifact = round_dir / "work" / "opponent_packets" / "code_quality_findings.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("Synthetic role findings.\n", encoding="utf-8")
    manifest = ensure_manifest({}, "case-a", "round-a")

    register_artifact(
        manifest,
        round_dir,
        "work/opponent_packets/code_quality_findings.md",
        role="code-quality-reviewer",
        agent="agent-a",
        contribution="generation",
        review_scope="internal_only",
        review_status="not_recorded",
        reviewer_role="not_recorded",
        reviewer_agent="not_recorded",
        reviewed_at="",
        limitation=["Feeds synthesis only."],
        feeds=["outputs/oponent_podklady_revidovane.md"],
        input_refs=[],
        evidence_refs=[],
        check_refs=[],
        used_findings="",
        review_basis_path="",
        notes="Role packet finding.",
    )

    entry = manifest["supporting_work_artifacts"][0]

    assert entry["path"] == "work/opponent_packets/code_quality_findings.md"
    assert entry["artifact_sha256"] == sha256_file(artifact)
    assert entry["role"] == "code-quality-reviewer"
    assert entry["feeds"] == ["outputs/oponent_podklady_revidovane.md"]


def test_merge_supporting_work_artifacts_preserves_registered_metadata(tmp_path: Path) -> None:
    previous = [
        {
            "path": "work/opponent_packets/code_quality_findings.md",
            "kind": "text",
            "artifact_sha256": "old",
            "role": "code-quality-reviewer",
            "agent": "agent-a",
            "limitations": ["Feeds synthesis only."],
            "independent_review": {
                "status": "not_required",
                "covered_by_artifact": "outputs/vedouci_posudek_revidovany.md",
                "used_findings": "silent_internal_evidence:no_material_concern",
                "evidence_hash": "old",
            },
            "source_sha256": {"inputs/source.pdf": "0" * 64},
        }
    ]
    generated = [
        {
            "path": "work/opponent_packets/code_quality_findings.md",
            "kind": "text",
            "artifact_sha256": "new",
        }
    ]

    merged = merge_supporting_work_artifacts(previous, generated)

    assert merged[0]["artifact_sha256"] == "new"
    assert merged[0]["role"] == "code-quality-reviewer"
    assert merged[0]["limitations"] == ["Feeds synthesis only."]
    assert merged[0]["independent_review"]["used_findings"] == "silent_internal_evidence:no_material_concern"
    assert merged[0]["source_sha256"] == {"inputs/source.pdf": "0" * 64}


def test_register_artifact_rejects_paths_outside_round(tmp_path: Path) -> None:
    manifest = ensure_manifest({}, "case-a", "round-a")

    try:
        register_artifact(
            manifest,
            tmp_path / "round",
            "../outputs/leak.md",
            role="role",
            agent="agent",
            contribution="generation",
            review_scope=None,
            review_status="not_recorded",
            reviewer_role="not_recorded",
            reviewer_agent="not_recorded",
            reviewed_at="",
            limitation=[],
            feeds=[],
            input_refs=[],
            evidence_refs=[],
            check_refs=[],
            used_findings="",
            review_basis_path="",
            notes="",
        )
    except ValueError as exc:
        assert "safe relative path" in str(exc)
    else:
        raise AssertionError("unsafe artifact path should fail")


def test_register_final_artifact_records_review_basis(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    output = round_dir / "outputs" / "feedback_student.md"
    draft = round_dir / "work" / "feedback_student_draft.md"
    output.parent.mkdir(parents=True)
    draft.parent.mkdir(parents=True)
    output.write_text("# Reviewed feedback\n", encoding="utf-8")
    draft.write_text("# Draft feedback\n", encoding="utf-8")
    manifest = ensure_manifest({}, "case-a", "round-a")

    register_artifact(
        manifest,
        round_dir,
        "outputs/feedback_student.md",
        role="thesis-supervisor-feedback",
        agent="generator-agent",
        contribution="generation",
        review_scope="sendable_final",
        review_status="reviewed",
        reviewer_role="thesis-supervisor-feedback-review",
        reviewer_agent="reviewer-agent",
        reviewed_at="2026-05-06T00:00:00Z",
        limitation=["None."],
        feeds=[],
        input_refs=[],
        evidence_refs=[],
        check_refs=[],
        used_findings="",
        review_basis_path="work/feedback_student_draft.md",
        notes="",
    )
    review = manifest["artifacts"][0]["independent_review"]

    assert review["review_basis_path"] == "work/feedback_student_draft.md"
    assert review["review_basis_sha256"] == sha256_file(draft)


def test_apply_review_approval_record_updates_final_review_metadata(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    output = round_dir / "outputs" / "feedback_student.md"
    draft = round_dir / "work" / "feedback_student_draft.md"
    approval = round_dir / "work" / "reviews" / "supervisor_feedback_review.json"
    output.parent.mkdir(parents=True)
    draft.parent.mkdir(parents=True)
    approval.parent.mkdir(parents=True)
    output.write_text("# Reviewed feedback\n", encoding="utf-8")
    draft.write_text("# Draft feedback\n", encoding="utf-8")
    approval.write_text(
        json.dumps(
            {
                "workflow_profile": "supervisor_feedback",
                "reviewer_role": "thesis-supervisor-feedback-review",
                "reviewer_agent": "review-agent",
                "verdict": "approved",
                "blocking_findings_count": 0,
                "reviewed_artifact_path": "outputs/feedback_student.md",
                "reviewed_artifact_sha256": sha256_file(output),
                "review_basis_path": "work/feedback_student_draft.md",
                "review_basis_sha256": sha256_file(draft),
                "checks_observed": ["check-supervisor-ready", "check-feedback-language", "check-feedback-output"],
                "limitations": ["Synthetic limitation."],
                "timestamp": "2026-05-11T00:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = ensure_manifest({}, "case-a", "round-a")
    register_artifact(
        manifest,
        round_dir,
        "outputs/feedback_student.md",
        role="thesis-supervisor-feedback",
        agent="generator-agent",
        contribution="generation",
        review_scope="sendable_final",
        review_status="not_recorded",
        reviewer_role="not_recorded",
        reviewer_agent="not_recorded",
        reviewed_at="",
        limitation=[],
        feeds=[],
        input_refs=[],
        evidence_refs=[],
        check_refs=[],
        used_findings="",
        review_basis_path="",
        notes="",
    )
    output_hash = sha256_file(output)
    manifest["helper_checks"] = [
        {
            "check": name,
            "command": f"scripts/{name} case-a round-a",
            "target_artifacts": ["outputs/feedback_student.md"],
            "target_sha256": {"outputs/feedback_student.md": output_hash},
            "status": "passed",
            "checked_at": "2026-05-11T00:00:00Z",
            "exit_code": 0,
            "notes": "Synthetic passed check.",
        }
        for name in ("check-supervisor-ready", "check-feedback-language", "check-feedback-output")
    ]

    apply_review_approval_records(manifest, round_dir)
    review = manifest["artifacts"][0]["independent_review"]

    assert review["status"] == "reviewed"
    assert review["reviewer_role"] == "thesis-supervisor-feedback-review"
    assert review["reviewer_agent"] == "review-agent"
    assert review["reviewed_hash"] == sha256_file(output)
    assert review["review_basis_path"] == "work/feedback_student_draft.md"
    assert review["approval_record_path"] == "work/reviews/supervisor_feedback_review.json"
    assert manifest["artifacts"][0]["limitations"] == ["Synthetic limitation."]


def test_agent_coverage_built_after_review_approval_uses_review_fields(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    output = round_dir / "outputs" / "vedouci_posudek_revidovany.md"
    draft = round_dir / "work" / "vedouci_posudek_draft.md"
    approval = round_dir / "work" / "reviews" / "supervisor_report_review.json"
    output.parent.mkdir(parents=True)
    draft.parent.mkdir(parents=True)
    approval.parent.mkdir(parents=True)
    output.write_text("# Posudek vedoucího\n", encoding="utf-8")
    draft.write_text("# Návrh posudku vedoucího\n", encoding="utf-8")
    approval.write_text(
        json.dumps(
            {
                "workflow_profile": "supervisor_report",
                "reviewer_role": "thesis-supervisor-report-review",
                "reviewer_agent": "review-agent",
                "verdict": "approved",
                "blocking_findings_count": 0,
                "reviewed_artifact_path": "outputs/vedouci_posudek_revidovany.md",
                "reviewed_artifact_sha256": sha256_file(output),
                "review_basis_path": "work/vedouci_posudek_draft.md",
                "review_basis_sha256": sha256_file(draft),
                "checks_observed": ["check-supervisor-report", "check-supervisor-report-ready"],
                "limitations": [],
                "timestamp": "2026-05-11T00:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = ensure_manifest({}, "case-a", "round-a")
    register_artifact(
        manifest,
        round_dir,
        "outputs/vedouci_posudek_revidovany.md",
        role="thesis-supervisor-report",
        agent="generator-agent",
        contribution="generation",
        review_scope="sendable_final",
        review_status="not_recorded",
        reviewer_role="not_recorded",
        reviewer_agent="not_recorded",
        reviewed_at="",
        limitation=[],
        feeds=[],
        input_refs=[],
        evidence_refs=[],
        check_refs=[],
        used_findings="",
        review_basis_path="",
        notes="",
    )
    manifest["helper_checks"] = [
        {
            "check": name,
            "command": f"{name} case-a round-a",
            "target_artifacts": ["outputs/vedouci_posudek_revidovany.md"],
            "target_sha256": {"outputs/vedouci_posudek_revidovany.md": sha256_file(output)},
            "status": "passed",
            "checked_at": "2026-05-11T00:00:00Z",
            "exit_code": 0,
            "notes": "Synthetic passed check.",
        }
        for name in ("check-supervisor-report", "check-supervisor-report-ready")
    ]

    apply_review_approval_records(manifest, round_dir)
    coverage = build_coverage("case-a", "round-a", round_dir, manifest)

    assert coverage is not None
    role = next(item for item in coverage["roles"] if item["role"] == "supervisor_report_review")
    assert role["reviewer_role"] == "thesis-supervisor-report-review"
    assert role["reviewer_agent"] == "review-agent"
    assert role["reviewed_hash"] == sha256_file(output)


def test_init_review_manifest_run_checks_applies_approval_before_agent_coverage(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "repo"
    case_dir = root / "cases" / "case-a"
    round_dir = case_dir / "rounds" / "round-a"
    output = round_dir / "outputs" / "vedouci_posudek_revidovany.md"
    draft = round_dir / "work" / "vedouci_posudek_draft.md"
    approval = round_dir / "work" / "reviews" / "supervisor_report_review.json"
    output.parent.mkdir(parents=True)
    draft.parent.mkdir(parents=True)
    approval.parent.mkdir(parents=True)
    (case_dir / "current-round.txt").write_text("round-a\n", encoding="utf-8")
    (case_dir / "case.md").write_text("Work type: BP\nAcademic year: 2025/2026\n", encoding="utf-8")
    output.write_text("# Posudek vedoucího\n", encoding="utf-8")
    draft.write_text("# Návrh posudku vedoucího\n", encoding="utf-8")
    approval.write_text(
        json.dumps(
            {
                "workflow_profile": "supervisor_report",
                "reviewer_role": "thesis-supervisor-report-review",
                "reviewer_agent": "review-agent",
                "verdict": "approved",
                "blocking_findings_count": 0,
                "reviewed_artifact_path": "outputs/vedouci_posudek_revidovany.md",
                "reviewed_artifact_sha256": sha256_file(output),
                "review_basis_path": "work/vedouci_posudek_draft.md",
                "review_basis_sha256": sha256_file(draft),
                "checks_observed": ["check-supervisor-report", "check-supervisor-report-ready"],
                "limitations": [],
                "timestamp": "2026-05-11T00:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    observed: dict[str, str] = {}

    def fake_run_check_record(root_arg: Path, round_dir_arg: Path, check: dict) -> None:
        assert root_arg == root
        check["status"] = "passed"
        check["checked_at"] = "2026-05-13T00:00:00Z"
        check["exit_code"] = 0
        check["notes"] = "Synthetic check."
        if check.get("check") == "check-agent-coverage":
            coverage = json.loads((round_dir_arg / COVERAGE_REL).read_text(encoding="utf-8"))
            role = next(item for item in coverage["roles"] if item["role"] == "supervisor_report_review")
            observed["reviewer_agent"] = role["reviewer_agent"]
            observed["reviewed_hash"] = role["reviewed_hash"]

    monkeypatch.setattr(init_review_manifest, "repo_root", lambda: root)
    monkeypatch.setattr(init_review_manifest, "run_check_record", fake_run_check_record)
    monkeypatch.setattr(
        sys,
        "argv",
        ["scripts/init-review-manifest", "--run-checks", "case-a", "round-a"],
    )

    assert init_review_manifest.main() == 0

    manifest = json.loads((round_dir / "work" / "review_manifest.json").read_text(encoding="utf-8"))
    coverage = json.loads((round_dir / COVERAGE_REL).read_text(encoding="utf-8"))
    artifact = next(item for item in manifest["artifacts"] if item["path"] == "outputs/vedouci_posudek_revidovany.md")
    role = next(item for item in coverage["roles"] if item["role"] == "supervisor_report_review")

    assert observed == {"reviewer_agent": "review-agent", "reviewed_hash": sha256_file(output)}
    assert artifact["independent_review"]["reviewer_agent"] == "review-agent"
    assert role["reviewer_agent"] == "review-agent"
    assert role["reviewed_hash"] == sha256_file(output)


def test_review_approval_records_are_collected_and_hash_validated(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    output = round_dir / "outputs" / "oponent_podklady_revidovane.md"
    draft = round_dir / "work" / "oponent_podklady_draft.md"
    approval = round_dir / "work" / "reviews" / "opponent_materials_review.json"
    output.parent.mkdir(parents=True)
    draft.parent.mkdir(parents=True)
    approval.parent.mkdir(parents=True)
    output.write_text("# Reviewed materials\n", encoding="utf-8")
    draft.write_text("# Draft materials\n", encoding="utf-8")
    approval.write_text(
        json.dumps(
            {
                "workflow_profile": "opponent_review",
                "reviewer_role": "thesis-opponent-materials-review",
                "verdict": "approved",
                "blocking_findings_count": 0,
                "reviewed_artifact_path": "outputs/oponent_podklady_revidovane.md",
                "reviewed_artifact_sha256": sha256_file(output),
                "review_basis_path": "work/oponent_podklady_draft.md",
                "review_basis_sha256": sha256_file(draft),
                "checks_observed": ["check-opponent-materials"],
                "limitations": [],
                "timestamp": "2026-05-11T00:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    records = collect_supporting_work_artifacts(round_dir)
    rel_paths = {record["path"] for record in records}
    assert "work/reviews/opponent_materials_review.json" in rel_paths
    assert validate_supporting_work_artifacts(records, round_dir, case_id="case-a", round_id="round-a") == []

    output.write_text("# Edited reviewed materials\n", encoding="utf-8")
    errors = validate_supporting_work_artifacts(records, round_dir, case_id="case-a", round_id="round-a")

    assert any("reviewed_artifact_sha256 is stale" in error for error in errors)


def test_review_manifest_requires_approval_record_as_supporting_work_artifact(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    output = round_dir / "outputs" / "feedback_student.md"
    draft = round_dir / "work" / "feedback_student_draft.md"
    approval = round_dir / "work" / "reviews" / "supervisor_feedback_review.json"
    output.parent.mkdir(parents=True)
    draft.parent.mkdir(parents=True)
    approval.parent.mkdir(parents=True)
    output.write_text("# Reviewed feedback\n", encoding="utf-8")
    draft.write_text("# Draft feedback\n", encoding="utf-8")
    approval.write_text(
        json.dumps(
            {
                "workflow_profile": "supervisor_feedback",
                "reviewer_role": "thesis-supervisor-feedback-review",
                "reviewer_agent": "review-agent",
                "verdict": "approved",
                "blocking_findings_count": 0,
                "reviewed_artifact_path": "outputs/feedback_student.md",
                "reviewed_artifact_sha256": sha256_file(output),
                "review_basis_path": "work/feedback_student_draft.md",
                "review_basis_sha256": sha256_file(draft),
                "checks_observed": ["check-feedback-output"],
                "limitations": [],
                "timestamp": "2026-05-11T00:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = {
        "schema_version": "review-manifest-v1",
        "case_id": "case-a",
        "round_id": "round-a",
        "manifest_path": "work/review_manifest.json",
        "inputs": [],
        "extracted_artifacts": [],
        "notes": [],
        "supporting_work_artifacts": [],
        "workflow_limitations": [],
        "helper_checks": [],
        "artifacts": [
            {
                "path": "outputs/feedback_student.md",
                "artifact_type": "supervisor_feedback",
                "artifact_sha256": sha256_file(output),
                "review_scope": "sendable_final",
                "skills": [],
                "generated_by": [
                    {
                        "role": "thesis-supervisor-feedback",
                        "agent": "generator-agent",
                        "contribution": "generation",
                    }
                ],
                "independent_review": {
                    "status": "reviewed",
                    "reviewer_role": "thesis-supervisor-feedback-review",
                    "reviewer_agent": "review-agent",
                    "reviewed_at": "2026-05-11T00:00:00Z",
                    "reviewed_hash": sha256_file(output),
                    "review_basis_path": "work/feedback_student_draft.md",
                    "review_basis_sha256": sha256_file(draft),
                    "approval_record_path": "work/reviews/supervisor_feedback_review.json",
                },
                "helper_checks": [],
                "limitations": [],
            }
        ],
    }
    errors: list[str] = []

    check_manifest(manifest, "case-a", "round-a", root, round_dir, False, errors, [])

    assert any("approval_record_path is not recorded in supporting_work_artifacts" in error for error in errors)


def test_review_manifest_closeout_requires_structured_approval_record(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    output = round_dir / "outputs" / "custom_final.md"
    output.parent.mkdir(parents=True)
    output.write_text("# Reviewed final\n", encoding="utf-8")
    current_hash = sha256_file(output)
    manifest = {
        "schema_version": "review-manifest-v1",
        "case_id": "case-a",
        "round_id": "round-a",
        "manifest_path": "work/review_manifest.json",
        "inputs": [],
        "extracted_artifacts": [],
        "notes": [],
        "supporting_work_artifacts": [],
        "workflow_limitations": [],
        "helper_checks": [],
        "artifacts": [
            {
                "path": "outputs/custom_final.md",
                "artifact_type": "custom_final",
                "artifact_sha256": current_hash,
                "review_scope": "standalone_final",
                "skills": [],
                "generated_by": [
                    {
                        "role": "custom-generator",
                        "agent": "generator-agent",
                        "contribution": "generation",
                    }
                ],
                "independent_review": {
                    "status": "reviewed",
                    "reviewer_role": "custom-reviewer",
                    "reviewer_agent": "review-agent",
                    "reviewed_at": "2026-05-11T00:00:00Z",
                    "reviewed_hash": current_hash,
                },
                "helper_checks": [],
                "limitations": [],
            }
        ],
    }
    errors: list[str] = []

    check_manifest(manifest, "case-a", "round-a", root, round_dir, True, errors, [])

    assert any("requires independent_review.approval_record_path" in error for error in errors)


def test_review_manifest_rejects_unrelated_approval_record(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    output = round_dir / "outputs" / "custom_final.md"
    other = round_dir / "outputs" / "other_final.md"
    draft = round_dir / "work" / "custom_draft.md"
    approval = round_dir / "work" / "reviews" / "custom_review.json"
    output.parent.mkdir(parents=True)
    draft.parent.mkdir(parents=True)
    approval.parent.mkdir(parents=True)
    output.write_text("# Reviewed final\n", encoding="utf-8")
    other.write_text("# Other final\n", encoding="utf-8")
    draft.write_text("# Draft\n", encoding="utf-8")
    approval.write_text(
        json.dumps(
            {
                "workflow_profile": "custom",
                "reviewer_role": "custom-reviewer",
                "reviewer_agent": "review-agent",
                "verdict": "approved",
                "blocking_findings_count": 0,
                "reviewed_artifact_path": "outputs/other_final.md",
                "reviewed_artifact_sha256": sha256_file(other),
                "review_basis_path": "work/custom_draft.md",
                "review_basis_sha256": sha256_file(draft),
                "checks_observed": ["custom-check"],
                "limitations": [],
                "timestamp": "2026-05-11T00:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = {
        "schema_version": "review-manifest-v1",
        "case_id": "case-a",
        "round_id": "round-a",
        "manifest_path": "work/review_manifest.json",
        "inputs": [],
        "extracted_artifacts": [],
        "notes": [],
        "supporting_work_artifacts": [
            {
                "path": "work/reviews/custom_review.json",
                "kind": "structured_data",
                "artifact_sha256": sha256_file(approval),
            }
        ],
        "workflow_limitations": [],
        "helper_checks": [],
        "artifacts": [
            {
                "path": "outputs/custom_final.md",
                "artifact_type": "custom_final",
                "artifact_sha256": sha256_file(output),
                "review_scope": "standalone_final",
                "skills": [],
                "generated_by": [
                    {
                        "role": "custom-generator",
                        "agent": "generator-agent",
                        "contribution": "generation",
                    }
                ],
                "independent_review": {
                    "status": "reviewed",
                    "reviewer_role": "custom-reviewer",
                    "reviewer_agent": "review-agent",
                    "reviewed_at": "2026-05-11T00:00:00Z",
                    "reviewed_hash": sha256_file(output),
                    "approval_record_path": "work/reviews/custom_review.json",
                },
                "helper_checks": [],
                "limitations": [],
            }
        ],
    }
    errors: list[str] = []

    check_manifest(manifest, "case-a", "round-a", root, round_dir, True, errors, [])

    assert any("reviewed_artifact_path must be outputs/custom_final.md" in error for error in errors)


def test_register_covered_by_synthesis_sets_evidence_hash(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    final = round_dir / "outputs" / "oponent_podklady_revidovane.md"
    evidence = round_dir / "outputs" / "code_quality_review.md"
    final.parent.mkdir(parents=True)
    final.write_text("# Reviewed materials\n", encoding="utf-8")
    evidence.write_text("# Internal Code Quality Review\n", encoding="utf-8")
    manifest = ensure_manifest({}, "case-a", "round-a")

    register_artifact(
        manifest,
        round_dir,
        "outputs/oponent_podklady_revidovane.md",
        role="thesis-opponent-materials",
        agent="generator-agent",
        contribution="generation",
        review_scope="standalone_final",
        review_status="reviewed",
        reviewer_role="thesis-opponent-materials-review",
        reviewer_agent="reviewer-agent",
        reviewed_at="2026-05-06T00:00:00Z",
        limitation=["None."],
        feeds=[],
        input_refs=[],
        evidence_refs=[],
        check_refs=[],
        used_findings="",
        review_basis_path="",
        notes="",
    )
    register_artifact(
        manifest,
        round_dir,
        "outputs/code_quality_review.md",
        role="thesis-code-quality-review",
        agent="code-agent",
        contribution="generation",
        review_scope="covered_by_synthesis",
        review_status="not_required",
        reviewer_role="not_recorded",
        reviewer_agent="not_recorded",
        reviewed_at="",
        limitation=["Covered by synthesis."],
        feeds=["outputs/oponent_podklady_revidovane.md"],
        input_refs=[],
        evidence_refs=[],
        check_refs=[],
        used_findings="Used implementation risk P1.",
        review_basis_path="",
        notes="",
    )
    evidence_entry = next(item for item in manifest["artifacts"] if item["path"] == "outputs/code_quality_review.md")

    assert evidence_entry["independent_review"]["evidence_hash"] == evidence_entry["artifact_sha256"]


def test_register_refs_survive_init_manifest_refresh(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    output = round_dir / "outputs" / "code_quality_review.md"
    output.parent.mkdir(parents=True)
    output.write_text("# Internal Code Quality Review\n", encoding="utf-8")
    manifest = ensure_manifest({}, "case-a", "round-a")

    register_artifact(
        manifest,
        round_dir,
        "outputs/code_quality_review.md",
        role="thesis-code-quality-review",
        agent="generator-agent",
        contribution="generation",
        review_scope="internal_only",
        review_status="not_recorded",
        reviewer_role="not_recorded",
        reviewer_agent="not_recorded",
        reviewed_at="",
        limitation=[],
        feeds=[],
        input_refs=["notes/assignment.md"],
        evidence_refs=["work/code_reproducibility.json"],
        check_refs=["check-code-quality-review"],
        used_findings="",
        review_basis_path="",
        notes="",
    )
    existing = {"artifacts": manifest["artifacts"]}

    from thesis_review_workflow.cli.init_review_manifest import output_artifacts

    refreshed = output_artifacts(round_dir, existing)

    assert refreshed[0]["input_refs"] == ["notes/assignment.md"]
    assert refreshed[0]["evidence_refs"] == ["work/code_reproducibility.json"]
    assert refreshed[0]["check_refs"] == ["check-code-quality-review"]


def test_review_artifact_registration_sidecar_updates_manifest_without_hashing_handoffs(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    final = round_dir / "outputs" / "feedback_student.md"
    output = round_dir / "outputs" / "code_quality_review.md"
    assignment = round_dir / "notes" / "assignment.md"
    briefing = round_dir / "work" / "common_briefing.json"
    sidecar = round_dir / "work" / "review_artifacts" / "code_quality_review.json"
    output.parent.mkdir(parents=True)
    assignment.parent.mkdir(parents=True)
    briefing.parent.mkdir(parents=True)
    sidecar.parent.mkdir(parents=True)
    final.write_text("# Feedback\n", encoding="utf-8")
    output.write_text("# Internal Code Quality Review\n", encoding="utf-8")
    assignment.write_text("# Assignment\n", encoding="utf-8")
    briefing.write_text('{"schema_version":"common-briefing-v1"}\n', encoding="utf-8")
    sidecar.write_text(
        json.dumps(
            {
                "schema_version": "review-artifact-registration-v1",
                "artifact_path": "outputs/code_quality_review.md",
                "agent": "code-agent",
                "contribution": "generation",
                "feeds": ["outputs/feedback_student.md"],
                "input_refs": ["notes/assignment.md"],
                "handoff_refs": ["work/common_briefing.json"],
                "used_findings": "Used implementation readability risk.",
                "limitations": ["Covered by final synthesis review."],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = ensure_manifest({}, "case-a", "round-a")

    apply_artifact_registration_sidecars(manifest, round_dir)

    entry = next(item for item in manifest["artifacts"] if item["path"] == "outputs/code_quality_review.md")
    assert entry["generated_by"][0]["agent"] == "code-agent"
    assert entry["independent_review"]["status"] == "not_required"
    assert entry["independent_review"]["covered_by_artifact"] == "outputs/feedback_student.md"
    assert entry["independent_review"]["evidence_hash"] == entry["artifact_sha256"]
    assert entry["input_refs"] == ["notes/assignment.md"]
    assert "outputs/feedback_student.md" not in entry.get("evidence_refs", [])
    assert entry["handoff_refs"] == ["work/common_briefing.json"]
    assert "outputs/feedback_student.md" not in entry.get("source_sha256", {})
    assert "work/common_briefing.json" not in entry.get("source_sha256", {})


def test_register_work_role_output_records_review_and_synthesis_metadata(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    final = round_dir / "outputs" / "feedback_student.md"
    evidence = round_dir / "work" / "quantitative_claims.json"
    source = round_dir / "extracted" / "thesis.txt"
    briefing = round_dir / "work" / "common_briefing.json"
    final.parent.mkdir(parents=True)
    evidence.parent.mkdir(parents=True)
    source.parent.mkdir(parents=True)
    final.write_text("# Feedback\n", encoding="utf-8")
    evidence.write_text('{"schema_version":"quantitative-claims-v1","claims":[]}\n', encoding="utf-8")
    source.write_text("Quantitative claim source.\n", encoding="utf-8")
    briefing.write_text('{"schema_version":"common-briefing-v1"}\n', encoding="utf-8")
    manifest = ensure_manifest({}, "case-a", "round-a")

    register_artifact(
        manifest,
        round_dir,
        "work/quantitative_claims.json",
        role="thesis-quantitative-claims-review",
        agent="quant-agent",
        contribution="generation",
        review_scope="covered_by_synthesis",
        review_status="not_required",
        reviewer_role="not_recorded",
        reviewer_agent="not_recorded",
        reviewed_at="",
        limitation=["Covered by final synthesis."],
        feeds=["outputs/feedback_student.md"],
        input_refs=["extracted/thesis.txt"],
        evidence_refs=[],
        handoff_refs=["work/common_briefing.json"],
        check_refs=["check-evaluation-claims"],
        used_findings="Used metric-scale sanity check.",
        review_basis_path="",
        notes="Synthetic work evidence registration.",
    )

    entry = next(
        item for item in manifest["supporting_work_artifacts"] if item["path"] == "work/quantitative_claims.json"
    )
    assert entry["generated_by"][0]["agent"] == "quant-agent"
    assert entry["skills"] == ["thesis-quantitative-claims-review"]
    assert entry["independent_review"]["status"] == "not_required"
    assert entry["independent_review"]["covered_by_artifact"] == "outputs/feedback_student.md"
    assert entry["independent_review"]["evidence_hash"] == entry["artifact_sha256"]
    assert entry["independent_review"]["used_findings"] == "Used metric-scale sanity check."
    assert entry["feeds"] == ["outputs/feedback_student.md"]
    assert "outputs/feedback_student.md" not in entry.get("evidence_refs", [])
    assert entry["source_sha256"] == {"extracted/thesis.txt": sha256_file(source)}
    assert entry["handoff_refs"] == ["work/common_briefing.json"]
    assert entry["check_refs"] == ["check-evaluation-claims"]


def test_register_review_artifact_auto_classifies_refs_and_common_output_preset() -> None:
    parser = register_review_artifact.build_parser()
    args = parser.parse_args(
        [
            "case-a",
            "round-a",
            "outputs/code_quality_review.md",
            "--agent",
            "agent-a",
            "--feeds",
            "outputs/vedouci_posudek_revidovany.md",
            "--ref",
            "notes/assignment.md",
            "--ref",
            "extracted/thesis.txt",
            "--ref",
            "work/quantitative_claims.json",
            "--ref",
            "work/common_briefing.json",
        ]
    )

    options, errors = register_review_artifact.registration_options(args)

    assert errors == []
    assert options is not None
    assert options["role"] == "thesis-code-quality-review"
    assert options["review_scope"] == "covered_by_synthesis"
    assert options["review_status"] == "not_required"
    assert options["input_refs"] == ["notes/assignment.md", "extracted/thesis.txt"]
    assert options["evidence_refs"] == ["work/quantitative_claims.json"]
    assert options["handoff_refs"] == ["work/common_briefing.json"]


def test_register_review_artifact_rejects_accidental_ref_misclassification() -> None:
    parser = register_review_artifact.build_parser()
    args = parser.parse_args(
        [
            "case-a",
            "round-a",
            "outputs/code_quality_review.md",
            "--evidence-ref",
            "notes/assignment.md",
        ]
    )

    options, errors = register_review_artifact.registration_options(args)

    assert options is None
    assert any("use --input-ref" in error for error in errors)

    override_args = parser.parse_args(
        [
            "case-a",
            "round-a",
            "outputs/code_quality_review.md",
            "--evidence-ref",
            "notes/assignment.md",
            "--allow-ref-class-override",
            "--notes",
            "Expert override for synthetic test.",
        ]
    )
    options, errors = register_review_artifact.registration_options(override_args)

    assert errors == []
    assert options is not None
    assert options["evidence_refs"] == ["notes/assignment.md"]

    handoff_args = parser.parse_args(
        [
            "case-a",
            "round-a",
            "outputs/code_quality_review.md",
            "--evidence-ref",
            "work/common_briefing.json",
        ]
    )
    options, errors = register_review_artifact.registration_options(handoff_args)

    assert options is None
    assert any("use --handoff-ref" in error for error in errors)


def test_init_manifest_uses_reviewed_supervisor_report_as_synthesis_target(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    outputs = round_dir / "outputs"
    outputs.mkdir(parents=True)
    (outputs / "vedouci_posudek_revidovany.md").write_text("# Reviewed Supervisor Report\n", encoding="utf-8")
    (outputs / "code_quality_review.md").write_text("# Code Quality\n", encoding="utf-8")

    artifacts = output_artifacts(round_dir, {})
    by_path = {item["path"]: item for item in artifacts}

    code_quality = by_path["outputs/code_quality_review.md"]
    assert by_path["outputs/vedouci_posudek_revidovany.md"]["review_scope"] == "sendable_final"
    assert code_quality["review_scope"] == "covered_by_synthesis"
    assert code_quality["independent_review"]["covered_by_artifact"] == "outputs/vedouci_posudek_revidovany.md"


def test_artifact_dependency_refs_use_claim_basis_without_blanket_notes_or_work(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    output = round_dir / "outputs" / "feedback_student.md"
    unrelated_note = round_dir / "notes" / "unrelated.md"
    unrelated_work = round_dir / "work" / "unrelated.json"
    unused_internal_evidence = round_dir / "outputs" / "code_quality_review.md"
    output.parent.mkdir(parents=True)
    unrelated_note.parent.mkdir(parents=True)
    unrelated_work.parent.mkdir(parents=True)
    output.write_text("# Feedback\n", encoding="utf-8")
    unused_internal_evidence.write_text("# Code Quality\n", encoding="utf-8")
    unrelated_note.write_text("Unrelated note.\n", encoding="utf-8")
    unrelated_work.write_text("{}\n", encoding="utf-8")
    write_claim_review_basis(round_dir)
    manifest = {
        "supporting_work_artifacts": [
            {"path": CLAIM_REVIEW_BASIS_REL},
            {"path": "work/unrelated.json"},
        ],
        "artifacts": [
            {
                "path": "outputs/feedback_student.md",
                "artifact_type": "supervisor_feedback",
                "artifact_sha256": sha256_file(output),
                "review_scope": "sendable_final",
                "skills": ["thesis-supervisor-feedback-review"],
                "generated_by": [],
                "independent_review": {"status": "not_recorded"},
                "helper_checks": [],
                "limitations": [],
                "input_refs": ["notes/unrelated.md"],
                "evidence_refs": ["work/unrelated.json"],
            },
            {
                "path": "outputs/code_quality_review.md",
                "artifact_type": "code_quality",
                "artifact_sha256": sha256_file(unused_internal_evidence),
                "review_scope": "internal_evidence",
                "skills": ["thesis-code-quality-review"],
                "generated_by": [],
                "independent_review": {"status": "not_recorded"},
                "helper_checks": [],
                "limitations": [],
                "input_refs": [],
                "evidence_refs": [],
            },
        ],
    }

    apply_artifact_dependency_refs(manifest, round_dir)
    artifacts = manifest["artifacts"]
    assert isinstance(artifacts, list)
    artifact = artifacts[0]
    assert isinstance(artifact, dict)

    assert artifact["input_refs"] == ["extracted/thesis.txt"]
    assert CLAIM_REVIEW_BASIS_REL in artifact["evidence_refs"]
    assert "notes/unrelated.md" not in artifact["input_refs"]
    assert "work/unrelated.json" not in artifact["evidence_refs"]
    assert "outputs/code_quality_review.md" not in artifact["evidence_refs"]
    assert set(artifact["source_sha256"]) == set(artifact["input_refs"] + artifact["evidence_refs"])


def test_final_artifact_packet_dependencies_are_handoff_refs_not_semantic_sources(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    feedback = round_dir / "outputs" / "feedback_student.md"
    packet = round_dir / "work" / "supervisor_packets" / "code_quality.md"
    briefing = round_dir / "work" / "common_briefing.json"
    feedback.parent.mkdir(parents=True)
    packet.parent.mkdir(parents=True)
    feedback.write_text("# Feedback\n", encoding="utf-8")
    packet.write_text("# Code quality packet\n", encoding="utf-8")
    briefing.write_text('{"schema_version":"common-briefing-v1"}\n', encoding="utf-8")
    manifest = {
        "supporting_work_artifacts": [
            {"path": "work/common_briefing.json"},
            {"path": "work/supervisor_packets/code_quality.md"},
        ],
        "artifacts": [
            {
                "path": "outputs/feedback_student.md",
                "artifact_type": "supervisor_feedback",
                "artifact_sha256": sha256_file(feedback),
                "review_scope": "sendable_final",
                "skills": ["thesis-supervisor-feedback", "thesis-supervisor-feedback-review"],
                "generated_by": [],
                "independent_review": {"status": "not_recorded"},
                "helper_checks": [],
                "limitations": [],
            }
        ],
    }

    apply_artifact_dependency_refs(manifest, round_dir)

    artifacts = manifest["artifacts"]
    assert isinstance(artifacts, list)
    artifact = artifacts[0]
    assert isinstance(artifact, dict)
    assert "work/common_briefing.json" in artifact["handoff_refs"]
    assert "work/supervisor_packets/code_quality.md" in artifact["handoff_refs"]
    assert "work/common_briefing.json" not in artifact["evidence_refs"]
    assert "work/supervisor_packets/code_quality.md" not in artifact["evidence_refs"]
    assert "work/common_briefing.json" not in artifact.get("source_sha256", {})
    assert "work/supervisor_packets/code_quality.md" not in artifact.get("source_sha256", {})


def test_claim_basis_dependency_refs_apply_only_to_matching_final_artifact(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    feedback = round_dir / "outputs" / "feedback_student.md"
    report = round_dir / "outputs" / "vedouci_posudek_revidovany.md"
    feedback.parent.mkdir(parents=True)
    feedback.write_text("# Feedback\n", encoding="utf-8")
    report.write_text("# Supervisor Report\n", encoding="utf-8")
    write_claim_review_basis(round_dir, draft_ref="work/feedback_student_draft.md")
    manifest = {
        "artifacts": [
            {
                "path": "outputs/feedback_student.md",
                "artifact_type": "supervisor_feedback",
                "artifact_sha256": sha256_file(feedback),
                "review_scope": "sendable_final",
                "skills": ["thesis-supervisor-feedback-review"],
                "generated_by": [],
                "independent_review": {"status": "not_recorded"},
                "helper_checks": [],
                "limitations": [],
                "input_refs": [],
                "evidence_refs": [],
            },
            {
                "path": "outputs/vedouci_posudek_revidovany.md",
                "artifact_type": "supervisor_report_reviewed",
                "artifact_sha256": sha256_file(report),
                "review_scope": "sendable_final",
                "skills": ["thesis-supervisor-report-review"],
                "generated_by": [],
                "independent_review": {"status": "not_recorded"},
                "helper_checks": [],
                "limitations": [],
                "input_refs": [],
                "evidence_refs": [],
            },
        ]
    }

    apply_artifact_dependency_refs(manifest, round_dir)

    feedback_artifact, report_artifact = manifest["artifacts"]
    assert CLAIM_REVIEW_BASIS_REL in feedback_artifact["evidence_refs"]
    assert CLAIM_REVIEW_BASIS_REL not in report_artifact["evidence_refs"]
    assert "extracted/thesis.txt" in feedback_artifact["input_refs"]
    assert "extracted/thesis.txt" not in report_artifact["input_refs"]


def test_reuse_index_dependency_refs_ignore_unmatched_role_decisions(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    output = round_dir / "outputs" / "feedback_student.md"
    source = round_dir / "notes" / "assignment.md"
    reuse_index = round_dir / REUSE_INDEX_REL
    output.parent.mkdir(parents=True)
    source.parent.mkdir(parents=True)
    reuse_index.parent.mkdir(parents=True)
    output.write_text("# Feedback\n", encoding="utf-8")
    source.write_text("# Assignment\n", encoding="utf-8")
    reuse_index.write_text(
        json.dumps(
            {
                "decisions": [
                    {
                        "artifact_role": "code_quality",
                        "source_sha256": {"notes/assignment.md": sha256_file(source)},
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = {
        "artifacts": [
            {
                "path": "outputs/feedback_student.md",
                "artifact_type": "supervisor_feedback",
                "artifact_sha256": sha256_file(output),
                "review_scope": "sendable_final",
                "skills": ["thesis-supervisor-feedback-review"],
                "generated_by": [],
                "independent_review": {"status": "not_recorded"},
                "helper_checks": [],
                "limitations": [],
                "input_refs": [],
                "evidence_refs": [],
            }
        ]
    }

    apply_artifact_dependency_refs(manifest, round_dir)

    artifact = manifest["artifacts"][0]
    assert REUSE_INDEX_REL not in artifact["evidence_refs"]
    assert "notes/assignment.md" not in artifact["input_refs"]


def test_review_manifest_requires_claim_basis_ref_for_final_artifact(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    output = round_dir / "outputs" / "feedback_student.md"
    output.parent.mkdir(parents=True)
    output.write_text("# Feedback\n", encoding="utf-8")
    write_claim_review_basis(round_dir)
    manifest = {
        "schema_version": "review-manifest-v1",
        "case_id": "case-a",
        "round_id": "round-a",
        "manifest_path": "work/review_manifest.json",
        "inputs": [],
        "extracted_artifacts": [{"path": "extracted/thesis.txt", "kind": "text"}],
        "notes": [],
        "supporting_work_artifacts": [{"path": CLAIM_REVIEW_BASIS_REL, "kind": "json"}],
        "workflow_limitations": [],
        "helper_checks": [],
        "artifacts": [
            {
                "path": "outputs/feedback_student.md",
                "artifact_type": "supervisor_feedback",
                "artifact_sha256": sha256_file(output),
                "review_scope": "sendable_final",
                "skills": ["thesis-supervisor-feedback-review"],
                "generated_by": [],
                "independent_review": {"status": "not_recorded"},
                "helper_checks": [],
                "limitations": [],
                "input_refs": ["extracted/thesis.txt"],
                "evidence_refs": [],
            }
        ],
    }
    errors: list[str] = []

    check_manifest(manifest, "case-a", "round-a", root, round_dir, True, errors, [])

    assert any(f"evidence_refs must include {CLAIM_REVIEW_BASIS_REL}" in error for error in errors)


def test_review_manifest_rejects_stale_final_claim_basis_source_hash(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    output = round_dir / "outputs" / "feedback_student.md"
    output.parent.mkdir(parents=True)
    output.write_text("# Feedback\n", encoding="utf-8")
    write_claim_review_basis(round_dir)
    claim_basis_hash = sha256_file(round_dir / CLAIM_REVIEW_BASIS_REL)
    thesis_hash = sha256_file(round_dir / "extracted" / "thesis.txt")
    manifest = {
        "schema_version": "review-manifest-v1",
        "case_id": "case-a",
        "round_id": "round-a",
        "manifest_path": "work/review_manifest.json",
        "inputs": [],
        "extracted_artifacts": [{"path": "extracted/thesis.txt", "kind": "text"}],
        "notes": [],
        "supporting_work_artifacts": [{"path": CLAIM_REVIEW_BASIS_REL, "kind": "json"}],
        "workflow_limitations": [],
        "helper_checks": [],
        "artifacts": [
            {
                "path": "outputs/feedback_student.md",
                "artifact_type": "supervisor_feedback",
                "artifact_sha256": sha256_file(output),
                "review_scope": "sendable_final",
                "skills": ["thesis-supervisor-feedback-review"],
                "generated_by": [],
                "independent_review": {"status": "not_recorded"},
                "helper_checks": [],
                "limitations": [],
                "input_refs": ["extracted/thesis.txt"],
                "evidence_refs": [CLAIM_REVIEW_BASIS_REL],
                "source_sha256": {
                    "extracted/thesis.txt": thesis_hash,
                    CLAIM_REVIEW_BASIS_REL: claim_basis_hash,
                },
            }
        ],
    }
    (round_dir / CLAIM_REVIEW_BASIS_REL).write_text('{"schema_version": "claim-review-basis-v1"}\n', encoding="utf-8")
    errors: list[str] = []

    check_manifest(manifest, "case-a", "round-a", root, round_dir, True, errors, [])

    assert any(f"source_sha256 is stale for {CLAIM_REVIEW_BASIS_REL}" in error for error in errors)


def test_claim_basis_does_not_replace_review_approval_basis_path(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    output = round_dir / "outputs" / "feedback_student.md"
    output.parent.mkdir(parents=True)
    output.write_text("# Feedback\n", encoding="utf-8")
    write_claim_review_basis(round_dir, draft_ref="work/other_draft.md")
    manifest = {
        "schema_version": "review-manifest-v1",
        "case_id": "case-a",
        "round_id": "round-a",
        "manifest_path": "work/review_manifest.json",
        "inputs": [],
        "extracted_artifacts": [{"path": "extracted/thesis.txt", "kind": "text"}],
        "notes": [],
        "supporting_work_artifacts": [{"path": CLAIM_REVIEW_BASIS_REL, "kind": "json"}],
        "workflow_limitations": [],
        "helper_checks": [],
        "artifacts": [
            {
                "path": "outputs/feedback_student.md",
                "artifact_type": "supervisor_feedback",
                "artifact_sha256": sha256_file(output),
                "review_scope": "sendable_final",
                "skills": ["thesis-supervisor-feedback-review"],
                "generated_by": [],
                "independent_review": {
                    "status": "reviewed",
                    "review_basis_path": "work/feedback_student_draft.md",
                },
                "helper_checks": [],
                "limitations": [],
                "input_refs": ["extracted/thesis.txt"],
                "evidence_refs": [CLAIM_REVIEW_BASIS_REL],
            }
        ],
    }
    errors: list[str] = []

    check_manifest(manifest, "case-a", "round-a", root, round_dir, True, errors, [])

    assert any(
        "claim review basis draft_ref must match independent_review.review_basis_path" in error for error in errors
    )


def test_review_manifest_enforces_canonical_approval_review_basis_path(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    output = round_dir / "outputs" / "feedback_student.md"
    canonical_draft = round_dir / "work" / "feedback_student_draft.md"
    other_draft = round_dir / "work" / "other_draft.md"
    output.parent.mkdir(parents=True)
    canonical_draft.parent.mkdir(parents=True)
    output.write_text("# Feedback\n", encoding="utf-8")
    canonical_draft.write_text("# Canonical draft\n", encoding="utf-8")
    other_draft.write_text("# Other draft\n", encoding="utf-8")
    write_claim_review_basis(round_dir, draft_ref="work/other_draft.md")
    approval = round_dir / "work" / "reviews" / "supervisor_feedback_review.json"
    approval.parent.mkdir(parents=True)
    approval.write_text(
        json.dumps(
            {
                "schema_version": "review-approval-v1",
                "workflow_profile": "supervisor_feedback",
                "reviewer_role": "thesis-supervisor-feedback-review",
                "reviewer_agent": "review-agent",
                "verdict": "approved",
                "blocking_findings_count": 0,
                "reviewed_artifact_path": "outputs/feedback_student.md",
                "reviewed_artifact_sha256": sha256_file(output),
                "review_basis_path": "work/other_draft.md",
                "review_basis_sha256": sha256_file(other_draft),
                "checks_observed": ["check-feedback-language", "check-feedback-output", "check-supervisor-ready"],
                "limitations": [],
                "timestamp": "2026-05-13T00:00:00Z",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = {
        "schema_version": "review-manifest-v1",
        "case_id": "case-a",
        "round_id": "round-a",
        "manifest_path": "work/review_manifest.json",
        "inputs": [],
        "extracted_artifacts": [{"path": "extracted/thesis.txt", "kind": "text"}],
        "notes": [],
        "supporting_work_artifacts": [
            {"path": CLAIM_REVIEW_BASIS_REL, "kind": "json"},
            {"path": "work/reviews/supervisor_feedback_review.json", "kind": "json"},
        ],
        "workflow_limitations": [],
        "helper_checks": [],
        "artifacts": [
            {
                "path": "outputs/feedback_student.md",
                "artifact_type": "supervisor_feedback",
                "artifact_sha256": sha256_file(output),
                "review_scope": "sendable_final",
                "skills": ["thesis-supervisor-feedback-review"],
                "generated_by": [{"role": "thesis-supervisor-feedback", "agent": "generator-agent"}],
                "independent_review": {
                    "status": "reviewed",
                    "reviewer_role": "thesis-supervisor-feedback-review",
                    "reviewer_agent": "review-agent",
                    "reviewed_at": "2026-05-13T00:00:00Z",
                    "reviewed_hash": sha256_file(output),
                    "approval_record_path": "work/reviews/supervisor_feedback_review.json",
                    "review_basis_path": "work/other_draft.md",
                },
                "helper_checks": [],
                "limitations": [],
                "input_refs": ["extracted/thesis.txt"],
                "evidence_refs": [CLAIM_REVIEW_BASIS_REL],
            }
        ],
    }
    errors: list[str] = []

    check_manifest(manifest, "case-a", "round-a", root, round_dir, True, errors, [])

    assert any("review_basis_path must be one of: work/feedback_student_draft.md" in error for error in errors)


def test_review_manifest_reports_missing_approval_record_without_crashing(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    round_dir = root / "cases" / "case-a" / "rounds" / "round-a"
    output = round_dir / "outputs" / "feedback_student.md"
    output.parent.mkdir(parents=True)
    output.write_text("# Feedback\n", encoding="utf-8")
    manifest = {
        "schema_version": "review-manifest-v1",
        "case_id": "case-a",
        "round_id": "round-a",
        "manifest_path": "work/review_manifest.json",
        "inputs": [],
        "extracted_artifacts": [],
        "notes": [],
        "supporting_work_artifacts": [],
        "workflow_limitations": [],
        "helper_checks": [],
        "artifacts": [
            {
                "path": "outputs/feedback_student.md",
                "artifact_type": "supervisor_feedback",
                "artifact_sha256": sha256_file(output),
                "review_scope": "sendable_final",
                "skills": ["thesis-supervisor-feedback", "thesis-supervisor-feedback-review"],
                "generated_by": [{"role": "thesis-supervisor-feedback", "agent": "generator-agent"}],
                "independent_review": {
                    "status": "reviewed",
                    "reviewer_role": "thesis-supervisor-feedback-review",
                    "reviewer_agent": "review-agent",
                    "reviewed_at": "2026-05-13T00:00:00Z",
                    "reviewed_hash": sha256_file(output),
                    "approval_record_path": "work/reviews/supervisor_feedback_review.json",
                },
                "helper_checks": [],
                "limitations": [],
                "input_refs": [],
                "evidence_refs": [],
            }
        ],
    }
    errors: list[str] = []

    check_manifest(manifest, "case-a", "round-a", root, round_dir, True, errors, [])

    assert any(
        "work/reviews/supervisor_feedback_review.json: missing review approval record" in error for error in errors
    )


def test_merge_supporting_work_artifacts_keeps_registered_only_work_artifact() -> None:
    previous = [
        {
            "path": "work/custom_reviewer_note.md",
            "kind": "text",
            "artifact_sha256": "old",
            "role": "custom-reviewer",
        }
    ]

    merged = merge_supporting_work_artifacts(previous, [])

    assert merged == previous


def test_register_artifact_rejects_unsafe_refs(tmp_path: Path) -> None:
    round_dir = tmp_path / "repo" / "cases" / "case-a" / "rounds" / "round-a"
    artifact = round_dir / "outputs" / "code_quality_review.md"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("# Internal Code Quality Review\n", encoding="utf-8")
    manifest = ensure_manifest({}, "case-a", "round-a")

    try:
        register_artifact(
            manifest,
            round_dir,
            "outputs/code_quality_review.md",
            role="role",
            agent="agent",
            contribution="generation",
            review_scope="internal_only",
            review_status="not_recorded",
            reviewer_role="not_recorded",
            reviewer_agent="not_recorded",
            reviewed_at="",
            limitation=[],
            feeds=["/home/private/output.md"],
            input_refs=[],
            evidence_refs=[],
            check_refs=[],
            used_findings="",
            review_basis_path="",
            notes="",
        )
    except ValueError as exc:
        assert "feeds" in str(exc)
    else:
        raise AssertionError("unsafe feeds ref should fail")
