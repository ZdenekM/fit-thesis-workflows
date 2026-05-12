import json
from pathlib import Path

from thesis_review_workflow.supervisor_report_calibration import (
    SUPERVISOR_REPORT_CALIBRATION_ADVISORY_REL,
    SUPERVISOR_REPORT_CALIBRATION_PROFILE_REL,
    SUPERVISOR_REPORT_CALIBRATION_USE_REL,
    SUPERVISOR_REPORT_CHECKLIST_REL,
    SUPERVISOR_REPORT_TRACE_REL,
    supervisor_report_calibration_profile_check_targets,
    validate_supervisor_report_calibration_artifact,
    validate_supervisor_report_calibration_payload,
)
from thesis_review_workflow.work_artifacts import collect_supporting_work_artifacts, sha256_file


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def common(schema_version: str) -> dict[str, object]:
    return {
        "schema_version": schema_version,
        "case_id": "case-a",
        "round_id": "round-a",
        "generated_at": "2026-05-12T00:00:00Z",
        "producer_type": "agent",
        "producer_role": "historical-supervisor-report-calibration",
        "producer_agent": "agent-a",
        "authorization_note": "Synthetic test fixture.",
        "source_refs": ["inputs/historical_cases/case-001/report.md"],
        "limitations": ["Synthetic fixture."],
    }


def test_historical_supervisor_case_analysis_validates_field_patterns(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    source = round_dir / "inputs/historical_cases/case-001/report.md"
    source.parent.mkdir(parents=True)
    source.write_text("# Report\n", encoding="utf-8")
    rel = "work/calibration/supervisor_report/historical_case_analyses/case-001.json"
    write_json(
        round_dir / rel,
        {
            **common("historical-supervisor-report-case-analysis-v1"),
            "historical_case_id": "case-001",
            "work_type": "bachelor thesis",
            "domain": "software engineering",
            "case_strength": "typical",
            "tone_observations": ["formal and concise"],
            "length_observations": ["one paragraph per field"],
            "grading_observations": ["grade justified by reservations"],
            "field_patterns": [
                {
                    "field_id": "overall_assessment",
                    "summary": "Balanced strengths and reservations.",
                    "evidence_refs": ["inputs/historical_cases/case-001/report.md"],
                }
            ],
            "do_not_generalize": ["current student activity"],
        },
    )

    errors = validate_supervisor_report_calibration_artifact(
        round_dir,
        rel,
        case_id="case-a",
        round_id="round-a",
    )

    assert errors == []


def test_historical_supervisor_case_analysis_rejects_current_case_input_refs(tmp_path: Path) -> None:
    rel = "work/calibration/supervisor_report/historical_case_analyses/case-001.json"
    payload = {
        **common("historical-supervisor-report-case-analysis-v1"),
        "source_refs": ["inputs/current_case/supervisor_input.md"],
        "historical_case_id": "case-001",
        "work_type": "bachelor thesis",
        "domain": "software engineering",
        "case_strength": "typical",
        "tone_observations": ["formal and concise"],
        "length_observations": ["one paragraph per field"],
        "grading_observations": ["grade justified by reservations"],
        "field_patterns": [
            {
                "field_id": "overall_assessment",
                "summary": "Balanced strengths and reservations.",
                "evidence_refs": ["inputs/historical_cases/case-002/report.md"],
            }
        ],
        "do_not_generalize": ["current student activity"],
    }

    errors = validate_supervisor_report_calibration_payload(payload, rel, require_existing_refs=False)

    assert any("historical analysis ref must stay under inputs/historical_cases/case-001/" in error for error in errors)


def test_historical_supervisor_case_analysis_rejects_traversal_refs(tmp_path: Path) -> None:
    rel = "work/calibration/supervisor_report/historical_case_analyses/case-001.json"
    payload = {
        **common("historical-supervisor-report-case-analysis-v1"),
        "historical_case_id": "case-001",
        "work_type": "bachelor thesis",
        "domain": "software engineering",
        "case_strength": "typical",
        "tone_observations": ["formal and concise"],
        "length_observations": ["one paragraph per field"],
        "grading_observations": ["grade justified by reservations"],
        "field_patterns": [
            {
                "field_id": "overall_assessment",
                "summary": "Balanced strengths and reservations.",
                "evidence_refs": ["inputs/historical_cases/case-001/../case-002/report.md"],
            }
        ],
        "do_not_generalize": ["current student activity"],
    }

    errors = validate_supervisor_report_calibration_payload(payload, rel, require_existing_refs=False)

    assert any("historical analysis ref must stay under inputs/historical_cases/case-001/" in error for error in errors)


def test_supervisor_calibration_use_is_hash_bound_to_trace_and_profile(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    for rel_path, text in (
        (SUPERVISOR_REPORT_CALIBRATION_PROFILE_REL, "{}\n"),
        (SUPERVISOR_REPORT_CHECKLIST_REL, "{}\n"),
        (SUPERVISOR_REPORT_TRACE_REL, "{}\n"),
    ):
        path = round_dir / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    payload = {
        **common("supervisor-report-calibration-use-v1"),
        "source_refs": [
            SUPERVISOR_REPORT_CALIBRATION_PROFILE_REL,
            SUPERVISOR_REPORT_CHECKLIST_REL,
            SUPERVISOR_REPORT_TRACE_REL,
        ],
        "selected_profile_path": SUPERVISOR_REPORT_CALIBRATION_PROFILE_REL,
        "selected_profile_sha256": sha256_file(round_dir / SUPERVISOR_REPORT_CALIBRATION_PROFILE_REL),
        "selected_checklist_path": SUPERVISOR_REPORT_CHECKLIST_REL,
        "selected_checklist_sha256": sha256_file(round_dir / SUPERVISOR_REPORT_CHECKLIST_REL),
        "target_report_trace_path": SUPERVISOR_REPORT_TRACE_REL,
        "target_report_trace_sha256": sha256_file(round_dir / SUPERVISOR_REPORT_TRACE_REL),
        "applicability_status": "matching",
        "anti_overfit_review_status": "reviewed",
        "current_case_evidence_boundaries": ["Supervisor input remains authoritative."],
    }

    assert (
        validate_supervisor_report_calibration_payload(
            payload,
            SUPERVISOR_REPORT_CALIBRATION_USE_REL,
            round_dir=round_dir,
            case_id="case-a",
            round_id="round-a",
        )
        == []
    )

    (round_dir / SUPERVISOR_REPORT_TRACE_REL).write_text('{"changed": true}\n', encoding="utf-8")

    errors = validate_supervisor_report_calibration_payload(
        payload,
        SUPERVISOR_REPORT_CALIBRATION_USE_REL,
        round_dir=round_dir,
        case_id="case-a",
        round_id="round-a",
    )

    assert any("target_report_trace_sha256 is stale" in error for error in errors)

    (round_dir / SUPERVISOR_REPORT_CHECKLIST_REL).unlink()
    missing_errors = validate_supervisor_report_calibration_payload(
        payload,
        SUPERVISOR_REPORT_CALIBRATION_USE_REL,
        round_dir=round_dir,
        case_id="case-a",
        round_id="round-a",
    )

    assert any(
        "missing bound artifact work/calibration/supervisor_report/checklist.json" in error for error in missing_errors
    )


def test_supervisor_calibration_advisory_is_non_blocking_and_trace_bound(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    trace = round_dir / SUPERVISOR_REPORT_TRACE_REL
    trace.parent.mkdir(parents=True)
    trace.write_text("{}\n", encoding="utf-8")
    payload = {
        **common("supervisor-report-calibration-advisory-v1"),
        "source_refs": [SUPERVISOR_REPORT_TRACE_REL],
        "advisory_reason": "missing_profile",
        "operator_message": "No historical supervisor calibration profile is available.",
        "target_report_trace_path": SUPERVISOR_REPORT_TRACE_REL,
        "target_report_trace_sha256": sha256_file(trace),
    }

    errors = validate_supervisor_report_calibration_payload(
        payload,
        SUPERVISOR_REPORT_CALIBRATION_ADVISORY_REL,
        round_dir=round_dir,
        case_id="case-a",
        round_id="round-a",
    )

    assert errors == []

    without_trace = dict(payload)
    without_trace.pop("target_report_trace_path")
    without_trace.pop("target_report_trace_sha256")
    without_trace["source_refs"] = []

    missing_errors = validate_supervisor_report_calibration_payload(
        without_trace,
        SUPERVISOR_REPORT_CALIBRATION_ADVISORY_REL,
        round_dir=round_dir,
        case_id="case-a",
        round_id="round-a",
    )

    assert (
        "work/supervisor_report_calibration_advisory.json: target_report_trace_path "
        "must be work/supervisor_report_trace.json" in missing_errors
    )
    assert (
        "work/supervisor_report_calibration_advisory.json: source_refs must include work/supervisor_report_trace.json"
        in missing_errors
    )


def test_supervisor_calibration_work_artifacts_are_collected(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    profile = round_dir / SUPERVISOR_REPORT_CALIBRATION_PROFILE_REL
    profile.parent.mkdir(parents=True)
    write_json(profile, {**common("supervisor-report-calibration-profile-v1"), "source_refs": []})

    records = collect_supporting_work_artifacts(round_dir)

    assert any(record["path"] == SUPERVISOR_REPORT_CALIBRATION_PROFILE_REL for record in records)


def test_supervisor_calibration_profile_targets_include_nested_artifacts(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    analysis = round_dir / "work/calibration/supervisor_report/historical_case_analyses/case-001.json"
    snapshot = round_dir / "work/calibration/supervisor_report/profile_versions/v1.md"
    analysis.parent.mkdir(parents=True)
    snapshot.parent.mkdir(parents=True)
    analysis.write_text("{}\n", encoding="utf-8")
    snapshot.write_text("# Snapshot\n", encoding="utf-8")

    targets = supervisor_report_calibration_profile_check_targets(round_dir)

    assert "work/calibration/supervisor_report/historical_case_analyses/case-001.json" in targets
    assert "work/calibration/supervisor_report/profile_versions/v1.md" in targets
