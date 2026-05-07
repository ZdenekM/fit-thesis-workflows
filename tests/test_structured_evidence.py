import copy
import hashlib
import json
from pathlib import Path

from thesis_review_workflow.structured_evidence import (
    OPPONENT_REPORT_TRACE_REL,
    REQUIRED_OPPONENT_IS_ITEM_IDS,
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
        "work/oponent_posudek_draft.md",
    ):
        path = round_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture\n", encoding="utf-8")


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
                "reproducibility_refs": [],
                "evidence_refs": ["extracted/thesis.txt"],
                "requires_reviewer_verification": True,
            }
        ],
    }
    write_json(round_dir / "work" / "quantitative_claims.json", payload)

    errors = validate_structured_evidence_artifact(round_dir, "work/quantitative_claims.json")

    assert any("practical_context must be one of" in error for error in errors)


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
                "source_refs": ["outputs/oponent_podklady_revidovane.md"],
                "target_section_ids": ["overall_assessment"],
                "report_refs": ["work/oponent_posudek_draft.md"],
                "status": "carried_to_report",
            }
        ],
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
