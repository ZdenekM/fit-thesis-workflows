import copy
import hashlib
import json
from pathlib import Path

from thesis_review_workflow.structured_evidence import (
    CURRENT_EVIDENCE_SNAPSHOT_REL,
    OPPONENT_REPORT_TRACE_REL,
    REQUIRED_OPPONENT_IS_ITEM_IDS,
    SUPERVISOR_REPORT_CONFIRMATION_REL,
    SUPERVISOR_REPORT_FEEDBACK_HISTORY_REL,
    SUPERVISOR_REPORT_TRACE_REL,
    build_current_evidence_snapshot_payload,
    current_evidence_default_source_refs,
    validate_structured_evidence_artifact,
)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def create_round_refs(round_dir: Path) -> None:
    for rel in (
        "notes/assignment.md",
        "extracted/thesis.txt",
        "inputs/results.csv",
        "outputs/oponent_podklady_revidovane.md",
        "outputs/vedouci_posudek_revidovany.md",
        "work/oponent_posudek_draft.md",
        "work/vedouci_posudek_draft.md",
        "notes/supervisor-report-operator-input.md",
    ):
        path = round_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture\n", encoding="utf-8")


def write_text(round_dir: Path, rel: str, text: str = "fixture\n") -> Path:
    path = round_dir / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def copy_round_file(round_dir: Path, source_rel: str, target_rel: str) -> Path:
    target = round_dir / target_rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((round_dir / source_rel).read_bytes())
    return target


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def common_fields(schema_version: str) -> dict[str, object]:
    return {
        "schema_version": schema_version,
        "case_id": "case-a",
        "round_id": "round-a",
        "generated_at": "2026-05-07T00:00:00Z",
        "producer_type": "agent",
        "producer_role": "structured-evidence-reviewer",
        "producer_agent": "agent-a",
        "authorization_note": "Current request explicitly authorized agents.",
        "source_refs": ["notes/assignment.md"],
        "limitations": [],
    }


def calibration_common_fields(schema_version: str) -> dict[str, object]:
    return {
        **common_fields(schema_version),
        "reviewer_profile_id": "default",
    }


def test_validate_assignment_coverage_accepts_valid_payload(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_round_refs(round_dir)
    payload = {
        **common_fields("assignment-coverage-agent-v1"),
        "assignment_points": [
            {
                "point_id": "A1",
                "summary": "Requirement.",
                "source_refs": ["notes/assignment.md"],
                "coverage": {
                    "status": "partially_covered",
                    "evidence_refs": ["extracted/thesis.txt"],
                    "limitations": [],
                    "requires_reviewer_verification": True,
                },
            }
        ],
    }
    write_json(round_dir / "work" / "assignment_coverage_agent.json", payload)

    errors = validate_structured_evidence_artifact(
        round_dir,
        "work/assignment_coverage_agent.json",
        case_id="case-a",
        round_id="round-a",
    )

    assert errors == []


def test_validate_assignment_coverage_rejects_bad_status_and_unsafe_ref(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_round_refs(round_dir)
    payload = {
        **common_fields("assignment-coverage-agent-v1"),
        "assignment_points": [
            {
                "point_id": "A1",
                "summary": "Requirement.",
                "source_refs": ["/home/private/assignment.md"],
                "coverage": {
                    "status": "good-enough",
                    "evidence_refs": ["extracted/thesis.txt"],
                    "limitations": [],
                    "requires_reviewer_verification": False,
                },
            }
        ],
    }
    write_json(round_dir / "work" / "assignment_coverage_agent.json", payload)

    errors = validate_structured_evidence_artifact(round_dir, "work/assignment_coverage_agent.json")

    assert any("status must be one of" in error for error in errors)
    assert any("ref must be relative inside the round" in error for error in errors)


def test_validate_assignment_coverage_requires_agent_identity(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_round_refs(round_dir)
    payload = {
        **common_fields("assignment-coverage-agent-v1"),
        "producer_agent": "",
        "assignment_points": [],
    }
    write_json(round_dir / "work" / "assignment_coverage_agent.json", payload)

    errors = validate_structured_evidence_artifact(round_dir, "work/assignment_coverage_agent.json")

    assert any("producer_agent must be non-empty str" in error for error in errors)


def test_validate_evidence_requirements_accepts_human_payload(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_round_refs(round_dir)
    payload = {
        **common_fields("evidence-requirements-v1"),
        "producer_type": "human",
        "producer_agent": None,
        "human_reviewer_note": "Reviewed manually.",
        "requirements": [
            {
                "requirement_id": "E1",
                "category": "evaluation_data",
                "state": "weak",
                "request": "Check reported results against submitted data.",
                "evidence_refs": ["inputs/results.csv"],
                "requires_reviewer_verification": True,
            }
        ],
    }
    payload.pop("authorization_note")
    write_json(round_dir / "work" / "evidence_requirements.json", payload)

    errors = validate_structured_evidence_artifact(round_dir, "work/evidence_requirements.json")

    assert errors == []


def test_validate_structured_artifact_reports_unreadable_path(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    (round_dir / "work" / "evidence_requirements.json").mkdir(parents=True)

    errors = validate_structured_evidence_artifact(round_dir, "work/evidence_requirements.json")

    assert any("cannot read structured evidence artifact" in error for error in errors)


def test_validate_quantitative_claims_requires_enum_values(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_round_refs(round_dir)
    payload = {
        **common_fields("quantitative-claims-v1"),
        "claims": [
            {
                "claim_id": "Q1",
                "summary": "Metric claim.",
                "kind": "metric",
                "status": "needs_context",
                "unit": "%",
                "baseline_status": "stated",
                "practical_context": "marketing",
                "scale_context": "Percentage denominator is stated.",
                "sample_context": "Sample size is stated.",
                "practical_magnitude": "Magnitude is interpreted against a stated baseline.",
                "overclaim_risk": "low",
                "reproducibility_refs": [],
                "evidence_refs": ["extracted/thesis.txt"],
                "requires_reviewer_verification": True,
            }
        ],
    }
    write_json(round_dir / "work" / "quantitative_claims.json", payload)

    errors = validate_structured_evidence_artifact(round_dir, "work/quantitative_claims.json")

    assert any("practical_context must be one of" in error for error in errors)


def test_validate_quantitative_claims_requires_evidence_anchor(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_round_refs(round_dir)
    payload = {
        **common_fields("quantitative-claims-v1"),
        "claims": [
            {
                "claim_id": "Q1",
                "summary": "Metric claim.",
                "kind": "metric",
                "status": "needs_context",
                "baseline_status": "missing",
                "practical_context": "weak",
                "scale_context": "Metric scale is unclear.",
                "sample_context": "Sample size is not stated.",
                "practical_magnitude": "Magnitude is not interpreted.",
                "overclaim_risk": "moderate",
                "reproducibility_refs": [],
                "evidence_refs": [],
                "requires_reviewer_verification": True,
            }
        ],
    }
    write_json(round_dir / "work" / "quantitative_claims.json", payload)

    errors = validate_structured_evidence_artifact(round_dir, "work/quantitative_claims.json")

    assert any("evidence_refs must not be empty" in error for error in errors)


def test_validate_quantitative_claims_requires_semantic_context_fields(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_round_refs(round_dir)
    payload = {
        **common_fields("quantitative-claims-v1"),
        "claims": [
            {
                "claim_id": "Q1",
                "summary": "Metric claim.",
                "kind": "metric",
                "status": "needs_context",
                "baseline_status": "missing",
                "practical_context": "weak",
                "reproducibility_refs": [],
                "evidence_refs": ["extracted/thesis.txt"],
                "requires_reviewer_verification": True,
            }
        ],
    }
    write_json(round_dir / "work" / "quantitative_claims.json", payload)

    errors = validate_structured_evidence_artifact(round_dir, "work/quantitative_claims.json")

    assert any("unit must be non-empty str" in error for error in errors)
    assert any("scale_context must be non-empty str" in error for error in errors)
    assert any("sample_context must be non-empty str" in error for error in errors)
    assert any("practical_magnitude must be non-empty str" in error for error in errors)
    assert any("overclaim_risk must be one of" in error for error in errors)


def test_validate_structured_evidence_artifact_rejects_backslash_path(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_round_refs(round_dir)

    errors = validate_structured_evidence_artifact(round_dir, "work\\quantitative_claims.json")

    assert errors == ["work\\quantitative_claims.json: structured evidence path must be relative inside the round"]


def test_validate_structured_evidence_artifact_rejects_unknown_path(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_round_refs(round_dir)

    errors = validate_structured_evidence_artifact(round_dir, "work/unknown.json")

    assert errors == ["work/unknown.json: unknown structured evidence artifact path"]


def test_validate_current_evidence_snapshot_accepts_hash_bound_items(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_round_refs(round_dir)
    source = write_text(round_dir, "work/code_workspace.md")
    payload = {
        **common_fields("current-evidence-snapshot-v1"),
        "source_refs": ["work/code_workspace.md"],
        "items": [
            {
                "item_id": "code-workspace",
                "path": "work/code_workspace.md",
                "status": "present",
                "sha256": sha256_file(source),
                "freshness": "current",
                "recorded_at": "2026-05-11T00:00:00Z",
                "readiness_relevant": True,
                "limitations": [],
            }
        ],
    }
    write_json(round_dir / CURRENT_EVIDENCE_SNAPSHOT_REL, payload)

    errors = validate_structured_evidence_artifact(
        round_dir,
        CURRENT_EVIDENCE_SNAPSHOT_REL,
        case_id="case-a",
        round_id="round-a",
    )

    assert errors == []


def test_validate_current_evidence_snapshot_rejects_stale_hash_and_unsafe_path(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_round_refs(round_dir)
    source = write_text(round_dir, "work/code_workspace.md")
    payload = {
        **common_fields("current-evidence-snapshot-v1"),
        "source_refs": ["work/code_workspace.md"],
        "items": [
            {
                "item_id": "code-workspace",
                "path": "work/code_workspace.md",
                "status": "present",
                "sha256": "0" * 64,
                "freshness": "current",
                "recorded_at": "2026-05-11T00:00:00Z",
                "readiness_relevant": True,
                "limitations": [],
            },
            {
                "item_id": "private",
                "path": "/home/private/work.json",
                "status": "missing",
                "freshness": "not_checked",
                "recorded_at": "2026-05-11T00:00:00Z",
                "readiness_relevant": False,
                "limitations": [],
            },
        ],
    }
    write_json(round_dir / CURRENT_EVIDENCE_SNAPSHOT_REL, payload)
    source.write_text("changed\n", encoding="utf-8")

    errors = validate_structured_evidence_artifact(round_dir, CURRENT_EVIDENCE_SNAPSHOT_REL)

    assert any("sha256 is stale for work/code_workspace.md" in error for error in errors)
    assert any("path must be under inputs/, extracted/, notes/, work/, or outputs/" in error for error in errors)


def test_validate_current_evidence_snapshot_rejects_negative_status_for_existing_file(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_round_refs(round_dir)
    source = write_text(round_dir, "work/code_workspace.md")
    payload = {
        **common_fields("current-evidence-snapshot-v1"),
        "source_refs": [],
        "items": [
            {
                "item_id": "code-workspace",
                "path": "work/code_workspace.md",
                "status": "missing",
                "freshness": "not_checked",
                "recorded_at": "2026-05-11T00:00:00Z",
                "readiness_relevant": True,
                "limitations": [],
            },
            {
                "item_id": "code-workspace-invalid",
                "path": "work/code_workspace.md",
                "status": "invalid",
                "sha256": sha256_file(source),
                "freshness": "stale",
                "recorded_at": "2026-05-11T00:00:00Z",
                "readiness_relevant": True,
                "limitations": [],
            },
        ],
    }
    write_json(round_dir / CURRENT_EVIDENCE_SNAPSHOT_REL, payload)

    errors = validate_structured_evidence_artifact(round_dir, CURRENT_EVIDENCE_SNAPSHOT_REL)

    assert any("path marked missing but file exists or is invalid" in error for error in errors)
    assert any("path marked invalid but file is present" in error for error in errors)


def test_build_current_evidence_snapshot_refreshes_hash_and_preserves_annotations(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    source = write_text(round_dir, "outputs/github_code_intake.md", "old\n")
    existing_payload = {
        **common_fields("current-evidence-snapshot-v1"),
        "source_refs": ["outputs/github_code_intake.md"],
        "items": [
            {
                "item_id": "current-evidence-outputs-github-code-intake-md",
                "path": "outputs/github_code_intake.md",
                "status": "present",
                "sha256": sha256_file(source),
                "freshness": "current",
                "recorded_at": "2026-05-10T00:00:00Z",
                "readiness_relevant": False,
                "limitations": ["Preserve this note."],
            }
        ],
    }
    source.write_text("new\n", encoding="utf-8")

    payload = build_current_evidence_snapshot_payload(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        generated_at="2026-05-11T00:00:00Z",
        source_refs=["outputs/github_code_intake.md"],
        existing_payload=existing_payload,
    )
    write_json(round_dir / CURRENT_EVIDENCE_SNAPSHOT_REL, payload)

    item = payload["items"][0]
    assert item["sha256"] == sha256_file(source)
    assert item["limitations"] == ["Preserve this note."]
    assert item["readiness_relevant"] is False
    assert validate_structured_evidence_artifact(round_dir, CURRENT_EVIDENCE_SNAPSHOT_REL) == []


def test_build_current_evidence_snapshot_records_missing_explicit_ref_without_source_ref(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"

    payload = build_current_evidence_snapshot_payload(
        round_dir,
        case_id="case-a",
        round_id="round-a",
        generated_at="2026-05-11T00:00:00Z",
        source_refs=["notes/missing-late-note.md"],
        limitations_by_path={"notes/missing-late-note.md": ["Operator expected a late note, but it is absent."]},
    )
    write_json(round_dir / CURRENT_EVIDENCE_SNAPSHOT_REL, payload)

    assert payload["source_refs"] == []
    assert payload["items"][0]["status"] == "missing"
    assert "sha256" not in payload["items"][0]
    assert validate_structured_evidence_artifact(round_dir, CURRENT_EVIDENCE_SNAPSHOT_REL) == []


def test_build_current_evidence_snapshot_rejects_unsafe_source_refs_before_hashing(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    outside = tmp_path / "private.txt"
    outside.write_text("private\n", encoding="utf-8")

    try:
        build_current_evidence_snapshot_payload(
            round_dir,
            case_id="case-a",
            round_id="round-a",
            generated_at="2026-05-11T00:00:00Z",
            source_refs=["../private.txt"],
        )
    except ValueError as exc:
        assert "safe round-relative ref" in str(exc)
    else:
        raise AssertionError("unsafe snapshot source ref was accepted")


def test_current_evidence_default_source_refs_expands_review_records(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    write_text(round_dir, "work/review_manifest.json", "{}\n")
    write_text(round_dir, "work/reviews/feedback_student_review.json", "{}\n")

    refs = current_evidence_default_source_refs(round_dir)

    assert "work/review_manifest.json" in refs
    assert "work/reviews/feedback_student_review.json" in refs
    assert "outputs/github_code_intake.md" not in refs


def trace_payload(source_hash: str) -> dict[str, object]:
    items = [
        {
            "item_id": item_id,
            "title": item_id.replace("_", " "),
            "formulation": "Draft-ready formulation.",
            "evidence_refs": ["outputs/oponent_podklady_revidovane.md"],
        }
        for item_id in sorted(REQUIRED_OPPONENT_IS_ITEM_IDS)
    ]
    return {
        **common_fields("opponent-report-trace-v1"),
        "source_refs": ["outputs/oponent_podklady_revidovane.md"],
        "source_materials_path": "outputs/oponent_podklady_revidovane.md",
        "source_materials_sha256": source_hash,
        "trace_review_status": "accepted",
        "reviewer_role": "independent-opponent-report-trace-reviewer",
        "reviewed_at": "2026-05-07T00:00:00Z",
        "trace_generated_from": ["outputs/oponent_podklady_revidovane.md"],
        "is_items": items,
        "defense_questions": [
            {
                "question_id": "D1",
                "question": "Question?",
                "evidence_refs": ["outputs/oponent_podklady_revidovane.md"],
            }
        ],
        "pre_submission_checks": [
            {
                "check_id": "C1",
                "instruction": "Manual calibration.",
                "evidence_refs": ["outputs/oponent_podklady_revidovane.md"],
            }
        ],
        "uncertainty_items": [
            {
                "claim_id": "U1",
                "summary": "Runtime was not fully verified.",
                "handling_instruction": "Preserve cautious wording in the overall assessment.",
                "source_refs": ["outputs/oponent_podklady_revidovane.md"],
                "target_section_ids": ["overall_assessment"],
                "report_refs": ["work/oponent_posudek_draft.md"],
                "status": "carried_to_report",
            }
        ],
        "limitations": [],
    }


def supervisor_feedback_history_payload(round_dir: Path, status: str = "evidenced_response") -> dict[str, object]:
    feedback = write_text(round_dir, "outputs/feedback_student.md", "# Feedback\n")
    revision = write_text(round_dir, "outputs/revision_diff.md", "# Revision\n")
    return {
        **common_fields("supervisor-report-feedback-history-v1"),
        "source_refs": ["outputs/feedback_student.md", "outputs/revision_diff.md"],
        "feedback_status": status,
        "summary": "Student reacted to prior feedback in a later revision.",
        "feedback_round_refs": ["outputs/feedback_student.md"],
        "revision_evidence_refs": ["outputs/revision_diff.md"],
        "source_ref_hashes": {
            "outputs/feedback_student.md": sha256_file(feedback),
            "outputs/revision_diff.md": sha256_file(revision),
        },
        "evidence_items": [
            {
                "item_id": "response-1",
                "status": status,
                "summary": "Synthetic response evidence.",
                "feedback_refs": ["outputs/feedback_student.md"],
                "revision_evidence_refs": ["outputs/revision_diff.md"],
                "limitations": [],
            }
        ],
    }


def supervisor_trace_payload(round_dir: Path, *, include_feedback: bool = True) -> dict[str, object]:
    input_path = round_dir / "notes/supervisor-report-operator-input.md"
    fields = [
        ("assignment_information", "Informace k zadání", "Zadání bylo splněno.", "official"),
        ("literature_work", "Práce s literaturou", "Student pracoval s literaturou.", "official"),
        (
            "activity_during_solution",
            "Aktivita během řešení, konzultace, komunikace",
            "Student konzultoval průběžně.",
            "official",
        ),
        ("completion_activity", "Aktivita při dokončování", "Obsah byl konzultován.", "official"),
        ("publication_activity", "Publikační činnost, ocenění", "Publikace nejsou.", "official"),
        ("overall_assessment", "Celkové hodnocení", "Doporučuji hodnocení B.", "official"),
        ("student_comment", "Komentář pro studenta", "Děkuji za práci.", "private_student_comment"),
    ]
    payload: dict[str, object] = {
        **common_fields("supervisor-report-trace-v1"),
        "source_refs": ["notes/supervisor-report-operator-input.md"],
        "supervisor_input_path": "notes/supervisor-report-operator-input.md",
        "supervisor_input_sha256": sha256_file(input_path),
        "prior_feedback_status": "evidenced_response" if include_feedback else "absent",
        "report_fields": [
            {
                "field_id": field_id,
                "title": title,
                "formulation": formulation,
                "visibility": visibility,
                "evidence_refs": ["notes/supervisor-report-operator-input.md"],
                "supervisor_input_refs": ["notes/supervisor-report-operator-input.md"],
                "prior_feedback_refs": [SUPERVISOR_REPORT_FEEDBACK_HISTORY_REL] if include_feedback else [],
                "report_refs": ["work/vedouci_posudek_draft.md"],
            }
            for field_id, title, formulation, visibility in fields
        ],
        "grading": {
            "grade": "B",
            "points": 82,
            "points_interval": None,
            "rationale": "Supervisor input supports B.",
            "supervisor_input_refs": ["notes/supervisor-report-operator-input.md"],
        },
        "uncertainty_items": [],
        "manual_checks": [],
    }
    if include_feedback:
        history = round_dir / SUPERVISOR_REPORT_FEEDBACK_HISTORY_REL
        payload["feedback_history_path"] = SUPERVISOR_REPORT_FEEDBACK_HISTORY_REL
        payload["feedback_history_sha256"] = sha256_file(history)
    return payload


def test_validate_supervisor_report_feedback_history_requires_hashes_for_evidenced_status(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_round_refs(round_dir)
    payload = supervisor_feedback_history_payload(round_dir)
    payload["source_ref_hashes"] = {}
    write_json(round_dir / SUPERVISOR_REPORT_FEEDBACK_HISTORY_REL, payload)

    errors = validate_structured_evidence_artifact(
        round_dir,
        SUPERVISOR_REPORT_FEEDBACK_HISTORY_REL,
        case_id="case-a",
        round_id="round-a",
    )

    assert any("missing 64-character hash for outputs/feedback_student.md" in error for error in errors)


def test_validate_supervisor_report_feedback_history_hashes_evidenced_item_status(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_round_refs(round_dir)
    payload = supervisor_feedback_history_payload(round_dir, status="present")
    items = payload["evidence_items"]
    assert isinstance(items, list)
    items[0]["status"] = "evidenced_partial_response"
    payload.pop("source_ref_hashes")
    write_json(round_dir / SUPERVISOR_REPORT_FEEDBACK_HISTORY_REL, payload)

    errors = validate_structured_evidence_artifact(round_dir, SUPERVISOR_REPORT_FEEDBACK_HISTORY_REL)

    assert any("source_ref_hashes must be object" in error for error in errors)


def test_validate_supervisor_report_feedback_history_accepts_absent_status(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_round_refs(round_dir)
    payload = {
        **common_fields("supervisor-report-feedback-history-v1"),
        "feedback_status": "absent",
        "summary": "No prior feedback exists.",
        "feedback_round_refs": [],
        "revision_evidence_refs": [],
        "evidence_items": [],
    }
    write_json(round_dir / SUPERVISOR_REPORT_FEEDBACK_HISTORY_REL, payload)

    errors = validate_structured_evidence_artifact(
        round_dir,
        SUPERVISOR_REPORT_FEEDBACK_HISTORY_REL,
        case_id="case-a",
        round_id="round-a",
    )

    assert errors == []


def test_validate_supervisor_report_trace_accepts_complete_payload(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_round_refs(round_dir)
    write_json(round_dir / SUPERVISOR_REPORT_FEEDBACK_HISTORY_REL, supervisor_feedback_history_payload(round_dir))
    write_json(round_dir / SUPERVISOR_REPORT_TRACE_REL, supervisor_trace_payload(round_dir))

    errors = validate_structured_evidence_artifact(
        round_dir,
        SUPERVISOR_REPORT_TRACE_REL,
        case_id="case-a",
        round_id="round-a",
    )

    assert errors == []


def test_validate_supervisor_report_trace_requires_all_fields_and_private_visibility(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_round_refs(round_dir)
    payload = supervisor_trace_payload(round_dir, include_feedback=False)
    fields = payload["report_fields"]
    assert isinstance(fields, list)
    fields = fields[:-1]
    fields[0]["visibility"] = "private_student_comment"
    payload["report_fields"] = fields
    write_json(round_dir / SUPERVISOR_REPORT_TRACE_REL, payload)

    errors = validate_structured_evidence_artifact(round_dir, SUPERVISOR_REPORT_TRACE_REL)

    assert any("missing required report_fields: student_comment" in error for error in errors)
    assert any("only student_comment may have private_student_comment visibility" in error for error in errors)


def test_validate_supervisor_report_trace_requires_history_binding_for_evidenced_feedback(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_round_refs(round_dir)
    payload = supervisor_trace_payload(round_dir, include_feedback=False)
    payload["prior_feedback_status"] = "evidenced_response"
    write_json(round_dir / SUPERVISOR_REPORT_TRACE_REL, payload)

    errors = validate_structured_evidence_artifact(round_dir, SUPERVISOR_REPORT_TRACE_REL)

    assert any("feedback_history_path and feedback_history_sha256 are required" in error for error in errors)
    assert any("requires at least one report field prior_feedback_refs" in error for error in errors)


def test_validate_supervisor_report_confirmation_rejects_stale_reviewed_hash(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_round_refs(round_dir)
    payload = {
        **common_fields("supervisor-report-confirmation-v1"),
        "source_refs": ["outputs/vedouci_posudek_revidovany.md"],
        "reviewed_report_path": "outputs/vedouci_posudek_revidovany.md",
        "reviewed_report_sha256": "0" * 64,
        "grade": "B",
        "points": 82,
        "official_text_confirmed": True,
        "student_comment_confirmed": True,
        "ready_for_is": True,
        "confirmed_by": "supervisor",
        "confirmed_at": "2026-05-12T00:00:00Z",
    }
    write_json(round_dir / SUPERVISOR_REPORT_CONFIRMATION_REL, payload)

    errors = validate_structured_evidence_artifact(round_dir, SUPERVISOR_REPORT_CONFIRMATION_REL)

    assert any("reviewed_report_sha256 is stale" in error for error in errors)


def trace_calibration_context(round_dir: Path) -> dict[str, object]:
    materials_hash = sha256_file(round_dir / "outputs/oponent_podklady_revidovane.md")
    write_json(round_dir / OPPONENT_REPORT_TRACE_REL, trace_payload(materials_hash))
    trace_hash = sha256_file(round_dir / OPPONENT_REPORT_TRACE_REL)
    advisory = {
        **calibration_common_fields("opponent-calibration-advisory-v1"),
        "source_refs": ["outputs/oponent_podklady_revidovane.md", OPPONENT_REPORT_TRACE_REL],
        "limitations": ["Synthetic no-profile advisory."],
        "source_materials_path": "outputs/oponent_podklady_revidovane.md",
        "source_materials_sha256": materials_hash,
        "opponent_report_trace_path": OPPONENT_REPORT_TRACE_REL,
        "opponent_report_trace_sha256": trace_hash,
        "no_profile_reason": "missing_profile",
        "advisory_status": "non_blocking",
        "normal_workflow_continues": True,
        "recommendation": "Add historical reports later.",
        "reviewer_profile_gate": {"required": True, "satisfied_by_historical_calibration": False},
    }
    write_json(round_dir / "work/opponent_calibration_advisory.json", advisory)
    feedback = write_text(round_dir, "notes/opponent-report-operator-feedback.md", "# Operator feedback\n")
    comparison = write_text(round_dir, "outputs/reference_report_comparison.md")
    packet = write_text(round_dir, "outputs/opponent_reading_packet.md")
    trace_snapshot = copy_round_file(
        round_dir,
        OPPONENT_REPORT_TRACE_REL,
        "work/opponent_report_revision_sources/opponent_report_trace.json",
    )
    draft_snapshot = copy_round_file(
        round_dir,
        "work/oponent_posudek_draft.md",
        "work/opponent_report_revision_sources/oponent_posudek_draft.md",
    )
    revision_request = {
        **calibration_common_fields("opponent-report-revision-request-v1"),
        "source_refs": [
            "notes/opponent-report-operator-feedback.md",
            "outputs/oponent_podklady_revidovane.md",
            "work/opponent_report_revision_sources/opponent_report_trace.json",
            "work/opponent_report_revision_sources/oponent_posudek_draft.md",
            "work/opponent_calibration_advisory.json",
            "outputs/reference_report_comparison.md",
            "outputs/opponent_reading_packet.md",
        ],
        "limitations": ["Synthetic revision request."],
        "operator_feedback_path": "notes/opponent-report-operator-feedback.md",
        "operator_feedback_sha256": sha256_file(feedback),
        "source_materials_path": "outputs/oponent_podklady_revidovane.md",
        "source_materials_sha256": materials_hash,
        "opponent_report_trace_path": "work/opponent_report_revision_sources/opponent_report_trace.json",
        "opponent_report_trace_sha256": sha256_file(trace_snapshot),
        "opponent_report_draft_path": "work/opponent_report_revision_sources/oponent_posudek_draft.md",
        "opponent_report_draft_sha256": sha256_file(draft_snapshot),
        "calibration_advisory_path": "work/opponent_calibration_advisory.json",
        "calibration_advisory_sha256": sha256_file(round_dir / "work/opponent_calibration_advisory.json"),
        "reference_report_comparison_path": "outputs/reference_report_comparison.md",
        "reference_report_comparison_sha256": sha256_file(comparison),
        "opponent_reading_packet_path": "outputs/opponent_reading_packet.md",
        "opponent_reading_packet_sha256": sha256_file(packet),
        "feedback_items": [
            {
                "item_id": "F1",
                "category": "grading_calibration",
                "summary": "Operator wants stricter calibration.",
                "requested_action": "Re-check point interval.",
                "evidence_refs": ["notes/opponent-report-operator-feedback.md"],
            }
        ],
        "requested_extra_checks": [],
    }
    write_json(round_dir / "work/opponent_report_revision_request.json", revision_request)
    paths = {
        "calibration_advisory": round_dir / "work/opponent_calibration_advisory.json",
        "reference_report_comparison": comparison,
        "opponent_reading_packet": packet,
        "revision_request": round_dir / "work/opponent_report_revision_request.json",
    }
    return {
        "calibration_advisory_path": "work/opponent_calibration_advisory.json",
        "calibration_advisory_sha256": sha256_file(paths["calibration_advisory"]),
        "reference_report_comparison_path": "outputs/reference_report_comparison.md",
        "reference_report_comparison_sha256": sha256_file(paths["reference_report_comparison"]),
        "opponent_reading_packet_path": "outputs/opponent_reading_packet.md",
        "opponent_reading_packet_sha256": sha256_file(paths["opponent_reading_packet"]),
        "revision_request_path": "work/opponent_report_revision_request.json",
        "revision_request_sha256": sha256_file(paths["revision_request"]),
        "revision_applied": True,
        "anti_overfit_review_status": "reviewed",
        "anti_overfit_reviewer_role": "anti-overfit-reviewer",
        "anti_overfit_reviewer_agent": "agent-b",
        "reviewed_at": "2026-05-07T00:01:00Z",
        "limitations": [],
    }


def test_validate_opponent_report_trace_requires_all_is_items(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_round_refs(round_dir)
    payload = trace_payload(sha256_file(round_dir / "outputs" / "oponent_podklady_revidovane.md"))
    items = copy.deepcopy(payload["is_items"])
    assert isinstance(items, list)
    payload["is_items"] = items[:-1]
    write_json(round_dir / OPPONENT_REPORT_TRACE_REL, payload)

    errors = validate_structured_evidence_artifact(round_dir, OPPONENT_REPORT_TRACE_REL)

    assert any("missing required is_items" in error for error in errors)


def test_validate_opponent_report_trace_accepts_complete_payload(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_round_refs(round_dir)
    write_json(
        round_dir / OPPONENT_REPORT_TRACE_REL,
        trace_payload(sha256_file(round_dir / "outputs" / "oponent_podklady_revidovane.md")),
    )

    errors = validate_structured_evidence_artifact(
        round_dir,
        OPPONENT_REPORT_TRACE_REL,
        case_id="case-a",
        round_id="round-a",
    )

    assert errors == []


def test_validate_opponent_report_trace_requires_unique_anchored_is_items(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_round_refs(round_dir)
    payload = trace_payload(sha256_file(round_dir / "outputs" / "oponent_podklady_revidovane.md"))
    items = copy.deepcopy(payload["is_items"])
    assert isinstance(items, list)
    items[1]["item_id"] = items[0]["item_id"]
    items[0]["evidence_refs"] = []
    payload["is_items"] = items
    write_json(round_dir / OPPONENT_REPORT_TRACE_REL, payload)

    errors = validate_structured_evidence_artifact(round_dir, OPPONENT_REPORT_TRACE_REL)

    assert any("duplicate item_id" in error for error in errors)
    assert any("evidence_refs must not be empty" in error for error in errors)


def test_validate_opponent_report_trace_allows_future_report_ref(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_round_refs(round_dir)
    (round_dir / "work" / "oponent_posudek_draft.md").unlink()
    write_json(
        round_dir / OPPONENT_REPORT_TRACE_REL,
        trace_payload(sha256_file(round_dir / "outputs" / "oponent_podklady_revidovane.md")),
    )

    errors = validate_structured_evidence_artifact(round_dir, OPPONENT_REPORT_TRACE_REL)

    assert errors == []


def test_validate_opponent_report_trace_requires_questions(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_round_refs(round_dir)
    payload = trace_payload(sha256_file(round_dir / "outputs" / "oponent_podklady_revidovane.md"))
    payload["defense_questions"] = []
    write_json(round_dir / OPPONENT_REPORT_TRACE_REL, payload)

    errors = validate_structured_evidence_artifact(round_dir, OPPONENT_REPORT_TRACE_REL)

    assert any("defense_questions must not be empty" in error for error in errors)


def test_validate_opponent_report_trace_restricts_report_refs_to_generated_draft(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_round_refs(round_dir)
    payload = trace_payload(sha256_file(round_dir / "outputs" / "oponent_podklady_revidovane.md"))
    uncertainty_items = payload["uncertainty_items"]
    assert isinstance(uncertainty_items, list)
    uncertainty_items[0]["report_refs"] = ["work/not_the_generated_report.md"]
    write_json(round_dir / OPPONENT_REPORT_TRACE_REL, payload)

    errors = validate_structured_evidence_artifact(round_dir, OPPONENT_REPORT_TRACE_REL)

    assert any("report_refs item 1 must be work/oponent_posudek_draft.md" in error for error in errors)


def test_validate_opponent_report_trace_requires_uncertainty_content(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_round_refs(round_dir)
    payload = trace_payload(sha256_file(round_dir / "outputs" / "oponent_podklady_revidovane.md"))
    uncertainty_items = payload["uncertainty_items"]
    assert isinstance(uncertainty_items, list)
    uncertainty_items[0]["summary"] = ""
    uncertainty_items[0].pop("handling_instruction")
    write_json(round_dir / OPPONENT_REPORT_TRACE_REL, payload)

    errors = validate_structured_evidence_artifact(round_dir, OPPONENT_REPORT_TRACE_REL)

    assert any("summary must be non-empty str" in error for error in errors)
    assert any("handling_instruction must be non-empty str" in error for error in errors)


def test_validate_opponent_report_trace_rejects_stale_materials_hash(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_round_refs(round_dir)
    write_json(round_dir / OPPONENT_REPORT_TRACE_REL, trace_payload("0" * 64))

    errors = validate_structured_evidence_artifact(round_dir, OPPONENT_REPORT_TRACE_REL)

    assert any("source_materials_sha256 is stale" in error for error in errors)


def test_validate_opponent_report_trace_rejects_unsafe_materials_path_before_hashing(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_round_refs(round_dir)
    outside = tmp_path / "outside.md"
    outside.write_text("outside\n", encoding="utf-8")
    payload = trace_payload("0" * 64)
    payload["source_materials_path"] = outside.as_posix()
    write_json(round_dir / OPPONENT_REPORT_TRACE_REL, payload)

    errors = validate_structured_evidence_artifact(round_dir, OPPONENT_REPORT_TRACE_REL)

    assert any("source_materials_path must be outputs/oponent_podklady_revidovane.md" in error for error in errors)
    assert any("source_materials_path: ref must be relative inside the round" in error for error in errors)
    assert not any("source_materials_sha256 is stale" in error for error in errors)


def test_validate_opponent_report_trace_accepts_calibration_context_hash_bindings(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_round_refs(round_dir)
    payload = trace_payload(sha256_file(round_dir / "outputs" / "oponent_podklady_revidovane.md"))
    payload["calibration_context"] = trace_calibration_context(round_dir)
    write_json(round_dir / OPPONENT_REPORT_TRACE_REL, payload)

    errors = validate_structured_evidence_artifact(
        round_dir,
        OPPONENT_REPORT_TRACE_REL,
        case_id="case-a",
        round_id="round-a",
    )

    assert errors == []


def test_validate_opponent_report_trace_rejects_stale_calibration_context_source(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_round_refs(round_dir)
    payload = trace_payload(sha256_file(round_dir / "outputs" / "oponent_podklady_revidovane.md"))
    payload["calibration_context"] = trace_calibration_context(round_dir)
    write_text(round_dir, "work/opponent_report_revision_request.json", "changed\n")
    write_json(round_dir / OPPONENT_REPORT_TRACE_REL, payload)

    errors = validate_structured_evidence_artifact(round_dir, OPPONENT_REPORT_TRACE_REL)

    assert any("revision_request_sha256 is stale" in error for error in errors)


def test_validate_opponent_report_trace_rejects_invalid_bound_calibration_artifact(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_round_refs(round_dir)
    payload = trace_payload(sha256_file(round_dir / "outputs" / "oponent_podklady_revidovane.md"))
    context = trace_calibration_context(round_dir)
    write_text(round_dir, "work/opponent_calibration_advisory.json", "{}\n")
    context["calibration_advisory_sha256"] = sha256_file(round_dir / "work/opponent_calibration_advisory.json")
    payload["calibration_context"] = context
    write_json(round_dir / OPPONENT_REPORT_TRACE_REL, payload)

    errors = validate_structured_evidence_artifact(round_dir, OPPONENT_REPORT_TRACE_REL)

    assert any("schema_version must be opponent-calibration-advisory-v1" in error for error in errors)


def test_validate_opponent_report_trace_rejects_wrong_round_calibration_context(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_round_refs(round_dir)
    payload = trace_payload(sha256_file(round_dir / "outputs" / "oponent_podklady_revidovane.md"))
    context = trace_calibration_context(round_dir)
    advisory_path = round_dir / "work/opponent_calibration_advisory.json"
    advisory = json.loads(advisory_path.read_text(encoding="utf-8"))
    advisory["round_id"] = "other-round"
    write_json(advisory_path, advisory)
    context["calibration_advisory_sha256"] = sha256_file(advisory_path)
    payload["calibration_context"] = context
    write_json(round_dir / OPPONENT_REPORT_TRACE_REL, payload)

    errors = validate_structured_evidence_artifact(
        round_dir,
        OPPONENT_REPORT_TRACE_REL,
        case_id="case-a",
        round_id="round-a",
    )

    assert any("round_id does not match requested round" in error for error in errors)


def test_validate_opponent_report_trace_rejects_invalid_revision_request_schema(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_round_refs(round_dir)
    payload = trace_payload(sha256_file(round_dir / "outputs" / "oponent_podklady_revidovane.md"))
    context = trace_calibration_context(round_dir)
    write_json(round_dir / "work/opponent_report_revision_request.json", {})
    context["revision_request_sha256"] = sha256_file(round_dir / "work/opponent_report_revision_request.json")
    payload["calibration_context"] = context
    write_json(round_dir / OPPONENT_REPORT_TRACE_REL, payload)

    errors = validate_structured_evidence_artifact(
        round_dir,
        OPPONENT_REPORT_TRACE_REL,
        case_id="case-a",
        round_id="round-a",
    )

    assert any("schema_version must be opponent-report-revision-request-v1" in error for error in errors)


def test_validate_opponent_report_trace_requires_comparison_packet_and_revision_when_applied(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    create_round_refs(round_dir)
    payload = trace_payload(sha256_file(round_dir / "outputs" / "oponent_podklady_revidovane.md"))
    context = trace_calibration_context(round_dir)
    context.pop("reference_report_comparison_path")
    context.pop("reference_report_comparison_sha256")
    context.pop("revision_request_path")
    context.pop("revision_request_sha256")
    payload["calibration_context"] = context
    write_json(round_dir / OPPONENT_REPORT_TRACE_REL, payload)

    errors = validate_structured_evidence_artifact(round_dir, OPPONENT_REPORT_TRACE_REL)

    assert any(
        "reference_report_comparison_path and reference_report_comparison_sha256 are required" in error
        for error in errors
    )
    assert any("revision_request_path and revision_request_sha256 are required" in error for error in errors)
