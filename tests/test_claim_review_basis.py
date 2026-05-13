from pathlib import Path
from typing import Any

from thesis_review_workflow.claim_review_basis import (
    CLAIM_REVIEW_BASIS_REL,
    CLAIM_REVIEW_BASIS_SCHEMA,
    validate_claim_review_basis_payload,
)
from thesis_review_workflow.evidence_capsules import source_sha256_for_refs
from thesis_review_workflow.work_artifacts import sha256_file


def valid_claim_basis(round_dir: Path) -> dict[str, Any]:
    draft = round_dir / "work" / "feedback_student_draft.md"
    evidence = round_dir / "extracted" / "thesis.txt"
    capsule = round_dir / "work" / "context" / "evidence_capsules.json"
    draft.parent.mkdir(parents=True, exist_ok=True)
    evidence.parent.mkdir(parents=True, exist_ok=True)
    capsule.parent.mkdir(parents=True, exist_ok=True)
    draft.write_text("Draft public claim.\n", encoding="utf-8")
    evidence.write_text("The thesis anchors the claim.\n", encoding="utf-8")
    capsule.write_text('{"schema_version": "evidence-capsule-v1"}\n', encoding="utf-8")
    claim_hashes = source_sha256_for_refs(round_dir, ["extracted/thesis.txt", "work/context/evidence_capsules.json"])
    return {
        "schema_version": CLAIM_REVIEW_BASIS_SCHEMA,
        "case_id": "case-a",
        "round_id": "round-a",
        "generated_at": "2026-05-13T12:00:00Z",
        "producer_type": "agent",
        "producer_role": "synthesis-reviewer",
        "producer_agent": "agent-a",
        "draft_ref": "work/feedback_student_draft.md",
        "draft_sha256": sha256_file(draft),
        "capsule_refs": ["work/context/evidence_capsules.json"],
        "claims": [
            {
                "claim_id": "P1:import",
                "claim_text": "The submitted thesis claims the prototype imports data.",
                "priority": "p1",
                "grade_impact": True,
                "evidence_refs": ["extracted/thesis.txt"],
                "capsule_refs": ["work/context/evidence_capsules.json"],
                "source_sha256": claim_hashes,
                "verification_status": "needs_raw_source",
                "raw_source_escalations": [
                    {
                        "reason": "p0_p1_verification",
                        "source_refs": ["extracted/thesis.txt"],
                        "note": "P1 claim needs anchored verification.",
                    },
                    {
                        "reason": "grade_impact",
                        "source_refs": ["extracted/thesis.txt"],
                    },
                ],
            }
        ],
        "limitations": [],
    }


def test_valid_claim_review_basis_is_distinct_from_review_approval_basis(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-a"
    payload = valid_claim_basis(round_dir)

    errors = validate_claim_review_basis_payload(
        payload,
        CLAIM_REVIEW_BASIS_REL,
        round_dir=round_dir,
        case_id="case-a",
        round_id="round-a",
    )

    assert errors == []
    assert "review_basis_path" not in payload


def test_claim_review_basis_rejects_review_approval_fields(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-a"
    payload = valid_claim_basis(round_dir)
    payload["review_basis_path"] = "work/feedback_student_draft.md"

    errors = validate_claim_review_basis_payload(payload, CLAIM_REVIEW_BASIS_REL, round_dir=round_dir)

    assert any("review_basis_path belongs only to approval records" in error for error in errors)


def test_claim_review_basis_records_required_raw_source_escalations(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-a"
    payload = valid_claim_basis(round_dir)
    claim = payload["claims"][0]
    claim["raw_source_escalations"] = []

    errors = validate_claim_review_basis_payload(payload, CLAIM_REVIEW_BASIS_REL, round_dir=round_dir)

    assert any("p0/p1 claims require p0_p1_verification escalation" in error for error in errors)
    assert any("grade-impacting claims require grade_impact escalation" in error for error in errors)
    assert any("needs_raw_source requires at least one raw_source_escalation" in error for error in errors)


def test_claim_review_basis_requires_missing_anchor_escalation_without_refs(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-a"
    payload = valid_claim_basis(round_dir)
    claim = payload["claims"][0]
    claim["priority"] = "p2"
    claim["grade_impact"] = False
    claim["verification_status"] = "pending"
    claim["evidence_refs"] = []
    claim["capsule_refs"] = []
    claim["source_sha256"] = {}
    claim["raw_source_escalations"] = []

    errors = validate_claim_review_basis_payload(payload, CLAIM_REVIEW_BASIS_REL, round_dir=round_dir)

    assert any("missing evidence/capsule refs require missing_anchor escalation" in error for error in errors)


def test_claim_review_basis_hash_binds_escalation_only_raw_source_refs(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-a"
    payload = valid_claim_basis(round_dir)
    raw_source = round_dir / "notes" / "operator-note.md"
    raw_source.parent.mkdir(parents=True, exist_ok=True)
    raw_source.write_text("Operator note.\n", encoding="utf-8")
    claim = payload["claims"][0]
    claim["raw_source_escalations"][0]["source_refs"] = ["notes/operator-note.md"]

    errors = validate_claim_review_basis_payload(payload, CLAIM_REVIEW_BASIS_REL, round_dir=round_dir)

    assert any("source_sha256 missing hash for notes/operator-note.md" in error for error in errors)

    claim["source_sha256"].update(source_sha256_for_refs(round_dir, ["notes/operator-note.md"]))
    raw_source.write_text("Changed note.\n", encoding="utf-8")

    errors = validate_claim_review_basis_payload(payload, CLAIM_REVIEW_BASIS_REL, round_dir=round_dir)

    assert any("source_sha256 is stale for notes/operator-note.md" in error for error in errors)


def test_claim_review_basis_rejects_stale_draft_hash(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-a"
    payload = valid_claim_basis(round_dir)
    (round_dir / "work" / "feedback_student_draft.md").write_text("Changed draft.\n", encoding="utf-8")

    errors = validate_claim_review_basis_payload(payload, CLAIM_REVIEW_BASIS_REL, round_dir=round_dir)

    assert any("draft_sha256 is stale" in error for error in errors)
