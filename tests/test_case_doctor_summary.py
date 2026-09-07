import json
from dataclasses import dataclass
from pathlib import Path

from thesis_review_workflow.artifact_classification import classify_path_evidence
from thesis_review_workflow.case_doctor_summary import (
    GateResult,
    Issue,
    agent_coverage_summary_lines,
    archive_entry_code_like,
    archive_may_be_code_from_name,
    archive_suffix,
    archive_top_entries,
    compact_output,
    file_size_label,
    gate_failure_severity,
    manifest_summary_lines,
    matching_extract,
    output_expectations,
)
from thesis_review_workflow.cli import case_doctor
from thesis_review_workflow.supervisor_reading_pass import SUPERVISOR_READING_PASS_REL


@dataclass(frozen=True)
class RoleSpec:
    skill: str
    evidence_path: str
    requires_review: bool = False


def test_archive_classification_helpers_are_name_and_suffix_based() -> None:
    assert archive_suffix(Path("submission.tar.gz")) == ".tar.gz"
    assert archive_suffix(Path("project.zip")) == ".zip"
    assert archive_may_be_code_from_name(Path("submitted-code.zip"))
    assert not archive_may_be_code_from_name(Path("thesis-overleaf.zip"))
    assert archive_entry_code_like("src/app/main.py")
    assert archive_entry_code_like("project/tests/test_app.py")
    assert archive_top_entries(["project/a.py", "project/b.py", "README.md"]) == ["project", "README.md"]


def test_shared_structural_path_classification_keeps_generated_vendor_and_tests_separate() -> None:
    assert classify_path_evidence("App/obj/Debug/net8.0/App.dll").artifact_class == "generated_or_vendor"
    assert classify_path_evidence("Game/Packages/com.vendor.sample/Runtime/Foo.cs").artifact_class == (
        "generated_or_vendor"
    )
    assert classify_path_evidence("Assets/Samples/Demo/Example.cs").artifact_class == "sample_or_vendor"
    assert classify_path_evidence("src/MyApp.Tests/UnitTest1.cs").artifact_class == "test_evidence"
    assert classify_path_evidence("README.md").artifact_class == "readme_candidate"
    assert classify_path_evidence("submission.7z").artifact_class == "unsupported_archive"


def test_matching_extract_prefers_exact_assignment_and_single_extract_matches() -> None:
    exact = Path("extracted/thesis.txt")
    assert matching_extract(
        Path("inputs/thesis.pdf"),
        [exact],
        pdf_count=1,
        used_extracts=set(),
    ) == (exact, "same-stem")

    assignment = Path("extracted/zadani.txt")
    assert matching_extract(
        Path("inputs/assignment.pdf"),
        [assignment],
        pdf_count=2,
        used_extracts=set(),
    ) == (assignment, "assignment heuristic")

    fallback = Path("extracted/document.txt")
    assert matching_extract(
        Path("inputs/report.pdf"),
        [fallback],
        pdf_count=1,
        used_extracts=set(),
    ) == (fallback, "single-extract heuristic")

    registered = Path("extracted/theses_similarity/report.txt")
    assert matching_extract(
        Path("inputs/theses_similarity/report.pdf"),
        [registered],
        pdf_count=2,
        used_extracts=set(),
        known_mappings={Path("inputs/theses_similarity/report.pdf"): registered},
    ) == (registered, "registered mapping")


def test_matching_extract_does_not_reuse_or_guess_ambiguous_extracts() -> None:
    exact = Path("extracted/thesis.txt")
    assert matching_extract(
        Path("inputs/thesis.pdf"),
        [exact],
        pdf_count=1,
        used_extracts={exact},
    ) == (None, "")

    assert matching_extract(
        Path("inputs/report.pdf"),
        [Path("extracted/appendix.txt")],
        pdf_count=2,
        used_extracts=set(),
    ) == (None, "")

    assert matching_extract(
        Path("inputs/thesis.pdf"),
        [Path("extracted/appendix.txt"), Path("extracted/slides.txt")],
        pdf_count=2,
        used_extracts=set(),
    ) == (None, "")

    assert matching_extract(
        Path("inputs/theses_similarity/report.pdf"),
        [Path("extracted/report.txt")],
        pdf_count=1,
        used_extracts=set(),
        known_mappings={Path("inputs/theses_similarity/report.pdf"): Path("extracted/theses_similarity/report.txt")},
    ) == (None, "")


def test_output_expectations_records_missing_review_surfaces() -> None:
    issues: list[Issue] = []
    lines = output_expectations(
        {"oponent_podklady_revidovane.md", "feedback_student.md", "opponent_reading_packet.md"},
        feedback_draft_present=False,
        opponent_materials_draft_present=False,
        reviewed_opponent_materials_present=True,
        opponent_report_trace_present=False,
        opponent_report_draft_present=False,
        opponent_report_review_present=False,
        code_present=True,
        issues=issues,
    )

    assert "- work/opponent_report_trace.json: missing (opponent report trace)" in lines
    assert "- opponent_reading_packet.md: present (opponent reading packet)" in lines
    assert any("work/opponent_report_trace.json is missing" in issue.message for issue in issues)
    assert any("missing code review outputs" in issue.message for issue in issues)


def test_manifest_summary_lines_records_coverage_and_shape_errors() -> None:
    issues: list[Issue] = []
    lines = manifest_summary_lines(
        manifest_present=True,
        outputs_present=True,
        manifest_error=None,
        artifacts={},
        supporting_work_artifacts=[],
        helper_checks=[],
        coverage_needed=True,
        coverage_present=False,
        manifest_rel="work/review_manifest.json",
        coverage_rel="work/agent_coverage.json",
        issues=issues,
    )

    assert "- agent coverage: missing (work/agent_coverage.json)" in lines
    assert any("Required agent coverage is missing" in issue.message for issue in issues)
    assert any("artifacts field is not a list" in issue.message for issue in issues)


def test_agent_coverage_summary_lines_reports_missing_required_fields() -> None:
    issues: list[Issue] = []
    lines = agent_coverage_summary_lines(
        specs={"code-quality": RoleSpec("thesis-code-quality-review", "outputs/code_quality_review.md", True)},
        coverage={
            "roles": [
                {
                    "role": "code-quality",
                    "status": "required",
                    "output_evidence": ["outputs/code_quality_review.md"],
                    "generator_agent": "not_recorded",
                    "reviewer_agent": "reviewer-1",
                    "reviewer_role": "reviewer",
                    "reviewed_hash": "",
                }
            ]
        },
        coverage_error=None,
        evidence_exists=lambda _path: False,
        issues=issues,
    )

    assert lines == [
        "- REQUIRED code-quality: thesis-code-quality-review; evidence outputs/code_quality_review.md; "
        "missing output_file, generator_agent, generator_role, reviewed_hash"
    ]


def test_gate_severity_and_output_compaction() -> None:
    assert file_size_label(1536) == "1.5 KiB"
    assert compact_output("one\n\n two\nthree\nfour", max_lines=2) == "one | two | ..."

    supervisor_gate = GateResult("supervisor readiness", "cmd", 1, "missing deadline")
    assert gate_failure_severity(supervisor_gate, set(), feedback_draft_present=False) == "WARNING"
    assert gate_failure_severity(supervisor_gate, set(), feedback_draft_present=True) == "ERROR"
    assert gate_failure_severity(supervisor_gate, {"feedback_student.md"}, feedback_draft_present=False) == "ERROR"


def test_reading_pass_lines_report_absence_as_valid(tmp_path: Path) -> None:
    round_dir = tmp_path / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "notes").mkdir(parents=True)
    issues: list[Issue] = []

    lines = case_doctor.reading_pass_lines(round_dir, issues)

    assert any("absent, which is valid" in line for line in lines)
    assert issues == []


def test_reading_pass_lines_warn_on_a_present_but_unusable_pass(tmp_path: Path) -> None:
    round_dir = tmp_path / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "notes").mkdir(parents=True)
    (round_dir / SUPERVISOR_READING_PASS_REL).write_text("# Reading Pass\n", encoding="utf-8")
    issues: list[Issue] = []

    lines = case_doctor.reading_pass_lines(round_dir, issues)

    assert any("present" in line for line in lines)
    assert [issue.severity for issue in issues] == ["WARNING"]


def make_declared_round(tmp_path: Path, *, code_source: str | None) -> Path:
    round_dir = tmp_path / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "work").mkdir(parents=True)
    payload: dict[str, object] = {"schema_version": "review-run-trace-v1"}
    if code_source is not None:
        payload["code_source"] = code_source
    (round_dir / "work" / "review_run_trace.json").write_text(json.dumps(payload), encoding="utf-8")
    return round_dir


def test_case_doctor_reports_an_undeclared_code_source(tmp_path: Path) -> None:
    round_dir = make_declared_round(tmp_path, code_source=None)

    lines = case_doctor.declared_code_source_lines(round_dir)

    assert lines == ["- Declared code source: (none declared)"]


def test_case_doctor_flags_a_declaration_until_the_intake_artifact_exists(tmp_path: Path) -> None:
    """Keyed on the artifact that clears the next action, not on the intake directory.

    import-github-code creates work/github-intake long before outputs/github_code_intake.md,
    so keying on the directory went quiet while the round was still blocked.
    """
    round_dir = make_declared_round(tmp_path, code_source="github")
    (round_dir / "work" / "github-intake").mkdir()

    flagged = case_doctor.declared_code_source_lines(round_dir)

    assert any("Declared code source: github" in line for line in flagged)
    assert any("unresolved" in line for line in flagged)

    (round_dir / "outputs").mkdir()
    (round_dir / "outputs" / "github_code_intake.md").write_text("# intake\n", encoding="utf-8")

    resolved = case_doctor.declared_code_source_lines(round_dir)

    assert not any("unresolved" in line for line in resolved)


def test_input_provenance_lines_report_where_each_input_went(tmp_path: Path) -> None:
    round_dir = tmp_path / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "inputs").mkdir(parents=True)
    (round_dir / "work").mkdir()
    (round_dir / "inputs" / "Thesis.pdf").write_bytes(b"%PDF-1.4\n")
    (round_dir / "work" / "input_provenance.json").write_text(
        json.dumps(
            {
                "schema_version": "input-provenance-v1",
                "case_id": "case-a",
                "round_id": "round-a",
                "generated_at": "2026-09-07T00:00:00Z",
                "inputs": [
                    {
                        "role": "thesis_pdf",
                        "original_name": "Thesis (1).pdf",
                        "stored_ref": "inputs/Thesis.pdf",
                        "sha256": "e5c62df5dab5c87b6a015ef3d43597074d1eec433b15f51aec63b8582d0e4ab4",
                        "size_bytes": 9,
                        "deduplicated": False,
                    },
                    {
                        "role": "assignment_pdf",
                        "original_name": "zadani.pdf",
                        "stored_ref": "inputs/Thesis.pdf",
                        "sha256": "e5c62df5dab5c87b6a015ef3d43597074d1eec433b15f51aec63b8582d0e4ab4",
                        "size_bytes": 9,
                        "deduplicated": True,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    issues: list[Issue] = []

    lines = case_doctor.input_provenance_lines(round_dir, issues)

    assert any("Thesis (1).pdf" in line for line in lines)
    assert any("deduplicated" in line for line in lines)
    assert issues == []


def test_input_provenance_lines_warn_when_the_record_does_not_match(tmp_path: Path) -> None:
    round_dir = tmp_path / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "inputs").mkdir(parents=True)
    (round_dir / "work").mkdir()
    (round_dir / "work" / "input_provenance.json").write_text(
        json.dumps(
            {
                "schema_version": "input-provenance-v1",
                "case_id": "case-a",
                "round_id": "round-a",
                "generated_at": "2026-09-07T00:00:00Z",
                "inputs": [
                    {
                        "role": "thesis_pdf",
                        "original_name": "thesis.pdf",
                        "stored_ref": "inputs/absent.pdf",
                        "sha256": "0" * 64,
                        "size_bytes": 1,
                        "deduplicated": False,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    issues: list[Issue] = []

    lines = case_doctor.input_provenance_lines(round_dir, issues)

    assert [issue.severity for issue in issues] == ["WARNING"]
    assert any("does not exist" in line for line in lines)
