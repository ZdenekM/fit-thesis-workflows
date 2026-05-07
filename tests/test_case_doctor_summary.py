from dataclasses import dataclass
from pathlib import Path

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


def test_output_expectations_records_missing_review_surfaces() -> None:
    issues: list[Issue] = []
    lines = output_expectations(
        {"oponent_podklady_revidovane.md", "feedback_student.md"},
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
