import json
from pathlib import Path

from thesis_review_workflow.claim_review_basis import CLAIM_REVIEW_BASIS_REL, CLAIM_REVIEW_BASIS_SCHEMA
from thesis_review_workflow.evidence_capsules import EVIDENCE_CAPSULE_SCHEMA, EVIDENCE_CAPSULES_REL
from thesis_review_workflow.review_packets import COMMON_BRIEFING_REL, write_common_briefing
from thesis_review_workflow.work_artifacts import (
    collect_supporting_work_artifacts,
    sha256_file,
    validate_supporting_work_artifacts,
)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def collect_hash(path: Path) -> str:
    return sha256_file(path)


def test_collect_supporting_work_artifacts_records_known_json_and_packet(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    (round_dir / "notes").mkdir(parents=True)
    (round_dir / "notes" / "assignment.md").write_text("# Assignment\n", encoding="utf-8")
    (round_dir / "extracted").mkdir(parents=True)
    (round_dir / "extracted" / "thesis.txt").write_text("Thesis text.\n", encoding="utf-8")
    write_json(
        round_dir / "work" / "assignment_coverage_agent.json",
        {
            "schema_version": "assignment-coverage-agent-v1",
            "case_id": "case-a",
            "round_id": "round-a",
            "generated_at": "2026-05-06T00:00:00Z",
            "producer_type": "agent",
            "producer_role": "assignment-coverage-reviewer",
            "producer_agent": "agent-a",
            "authorization_note": "Authorized in current request.",
            "source_refs": ["notes/assignment.md", "extracted/thesis.txt"],
            "assignment_points": [
                {
                    "point_id": "A1",
                    "summary": "Requirement.",
                    "source_refs": ["notes/assignment.md"],
                    "coverage": {
                        "status": "covered",
                        "evidence_refs": ["extracted/thesis.txt"],
                        "limitations": [],
                        "requires_reviewer_verification": False,
                    },
                }
            ],
            "limitations": [],
        },
    )
    write_json(
        round_dir / "work" / "theses_similarity" / "intake.json",
        {
            "schema_version": "theses-similarity-intake-v1",
            "case_id": "case-a",
            "round_id": "round-a",
            "generated_at": "2026-05-12T00:00:00Z",
            "producer_type": "deterministic_helper",
            "producer_role": "import-theses-report",
            "producer_agent": "import-theses-report",
            "source_refs": ["inputs/theses_similarity/report.pdf", "extracted/theses_similarity/report.txt"],
            "limitations": [],
            "report_pdf": {"path": "inputs/theses_similarity/report.pdf", "sha256": "0" * 64, "page_count": 1},
            "extracted_text": {
                "path": "extracted/theses_similarity/report.txt",
                "sha256": "0" * 64,
                "extractor": "pdftotext -layout",
            },
            "current_submission_link": "unverified",
            "source_documents": [],
            "matched_passages": [],
        },
    )
    packet = round_dir / "work" / "opponent_packets" / "synthesis.md"
    packet.parent.mkdir(parents=True, exist_ok=True)
    packet.write_text("# Packet\n", encoding="utf-8")
    supervisor_packet = round_dir / "work" / "supervisor_packets" / "text_assignment.md"
    supervisor_packet.parent.mkdir(parents=True, exist_ok=True)
    supervisor_packet.write_text("# Supervisor Packet\n", encoding="utf-8")

    records = collect_supporting_work_artifacts(round_dir)

    by_path = {record["path"]: record for record in records}
    assert by_path["work/assignment_coverage_agent.json"]["schema_version"] == "assignment-coverage-agent-v1"
    assert by_path["work/assignment_coverage_agent.json"]["producer_role"] == "assignment-coverage-reviewer"
    assert by_path["work/assignment_coverage_agent.json"]["producer_agent"] == "agent-a"
    assert by_path["work/assignment_coverage_agent.json"]["artifact_sha256"]
    assert by_path["work/theses_similarity/intake.json"]["schema_version"] == "theses-similarity-intake-v1"
    assert by_path["work/theses_similarity/intake.json"]["producer_role"] == "import-theses-report"
    assert by_path["work/opponent_packets/synthesis.md"]["kind"] == "text"
    assert by_path["work/supervisor_packets/text_assignment.md"]["kind"] == "text"


def test_validate_supporting_work_artifacts_rejects_stale_hash_and_wrong_case(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    (round_dir / "notes").mkdir(parents=True)
    (round_dir / "notes" / "assignment.md").write_text("# Assignment\n", encoding="utf-8")
    write_json(
        round_dir / "work" / "evidence_requirements.json",
        {
            "schema_version": "evidence-requirements-v1",
            "case_id": "other-case",
            "round_id": "round-a",
            "generated_at": "2026-05-06T00:00:00Z",
            "producer_type": "agent",
            "producer_role": "evidence-requirements-reviewer",
            "producer_agent": "agent-a",
            "authorization_note": "Authorized in current request.",
            "source_refs": ["notes/assignment.md"],
            "requirements": [],
            "limitations": [],
        },
    )

    errors = validate_supporting_work_artifacts(
        [
            {
                "path": "work/evidence_requirements.json",
                "kind": "structured_data",
                "artifact_sha256": "0" * 64,
            }
        ],
        round_dir,
        case_id="case-a",
        round_id="round-a",
    )

    assert any("artifact_sha256 is stale" in error for error in errors)
    assert any("case_id does not match requested case" in error for error in errors)


def test_github_snapshot_manifest_is_case_bound_supporting_work_artifact(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-a"
    write_json(
        round_dir / "work" / "github-intake" / "snapshot-manifest.json",
        {
            "schema_version": "github-snapshot-manifest-v1",
            "case_id": "case-a",
            "round_id": "round-a",
            "generated_at": "2026-05-13T12:00:00Z",
            "producer": "scripts/import-github-code",
            "repositories": [],
            "pull_requests": [],
            "changed_file_list": {"available": False},
            "checks": [],
            "checks_summary_sha256": "0" * 64,
            "checkout_paths": [],
        },
    )

    records = collect_supporting_work_artifacts(round_dir)
    by_path = {record["path"]: record for record in records}

    assert by_path["work/github-intake/snapshot-manifest.json"]["schema_version"] == "github-snapshot-manifest-v1"
    assert validate_supporting_work_artifacts(records, round_dir, case_id="case-a", round_id="round-a") == []


def test_reuse_index_is_case_bound_supporting_work_artifact(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-a"
    write_json(
        round_dir / "work" / "reuse" / "reuse_index.json",
        {
            "schema_version": "round-reuse-index-v1",
            "case_id": "case-a",
            "round_id": "round-a",
            "generated_at": "2026-05-13T12:00:00Z",
            "producer": "scripts/update-round-reuse-index",
            "current_source_fingerprints": [],
            "previous_round_candidates": [],
            "decisions": [],
            "limitations": [],
        },
    )

    records = collect_supporting_work_artifacts(round_dir)
    by_path = {record["path"]: record for record in records}

    assert by_path["work/reuse/reuse_index.json"]["schema_version"] == "round-reuse-index-v1"
    assert validate_supporting_work_artifacts(records, round_dir, case_id="case-a", round_id="round-a") == []


def test_context_handoff_artifacts_are_case_bound_supporting_work_artifacts(tmp_path: Path) -> None:
    round_dir = tmp_path / "round-a"
    draft = round_dir / "work" / "feedback_student_draft.md"
    evidence = round_dir / "extracted" / "thesis.txt"
    draft.parent.mkdir(parents=True, exist_ok=True)
    evidence.parent.mkdir(parents=True, exist_ok=True)
    draft.write_text("Draft claim.\n", encoding="utf-8")
    evidence.write_text("Anchored source.\n", encoding="utf-8")
    evidence_hash = collect_hash(round_dir / "extracted" / "thesis.txt")
    write_json(
        round_dir / EVIDENCE_CAPSULES_REL,
        {
            "schema_version": EVIDENCE_CAPSULE_SCHEMA,
            "case_id": "case-a",
            "round_id": "round-a",
            "generated_at": "2026-05-13T12:00:00Z",
            "producer_type": "agent",
            "producer_role": "text-reader",
            "producer_agent": "agent-a",
            "source_refs": ["extracted/thesis.txt"],
            "source_sha256": {"extracted/thesis.txt": evidence_hash},
            "capsules": [
                {
                    "capsule_id": "cap-1",
                    "source_ref": "extracted/thesis.txt",
                    "source_sha256": evidence_hash,
                    "anchor_refs": [
                        {
                            "anchor_id": "a1",
                            "source_ref": "extracted/thesis.txt",
                            "anchor_type": "section",
                            "locator": "Section 1",
                        }
                    ],
                    "summary": "Anchored source summary.",
                    "extracted_facts": [],
                    "candidate_claims": [],
                    "uncertainties": [],
                    "limitations": [],
                    "open_raw_source_if": [],
                }
            ],
            "limitations": [],
        },
    )
    capsule_hash = collect_hash(round_dir / EVIDENCE_CAPSULES_REL)
    write_json(
        round_dir / CLAIM_REVIEW_BASIS_REL,
        {
            "schema_version": CLAIM_REVIEW_BASIS_SCHEMA,
            "case_id": "case-a",
            "round_id": "round-a",
            "generated_at": "2026-05-13T12:00:00Z",
            "producer_type": "agent",
            "producer_role": "synthesis-reviewer",
            "producer_agent": "agent-a",
            "draft_ref": "work/feedback_student_draft.md",
            "draft_sha256": collect_hash(draft),
            "capsule_refs": [EVIDENCE_CAPSULES_REL],
            "claims": [
                {
                    "claim_id": "p2-claim",
                    "claim_text": "Draft claim.",
                    "priority": "p2",
                    "grade_impact": False,
                    "evidence_refs": ["extracted/thesis.txt"],
                    "capsule_refs": [EVIDENCE_CAPSULES_REL],
                    "source_sha256": {
                        "extracted/thesis.txt": evidence_hash,
                        EVIDENCE_CAPSULES_REL: capsule_hash,
                    },
                    "verification_status": "verified_from_basis",
                    "raw_source_escalations": [],
                }
            ],
            "limitations": [],
        },
    )

    records = collect_supporting_work_artifacts(round_dir)
    by_path = {record["path"]: record for record in records}

    assert by_path[EVIDENCE_CAPSULES_REL]["schema_version"] == EVIDENCE_CAPSULE_SCHEMA
    assert by_path[CLAIM_REVIEW_BASIS_REL]["schema_version"] == CLAIM_REVIEW_BASIS_SCHEMA
    assert validate_supporting_work_artifacts(records, round_dir, case_id="case-a", round_id="round-a") == []


def test_common_briefing_is_deep_validated_supporting_work_artifact(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    round_dir = repo_root / "cases" / "case-a" / "rounds" / "round-a"
    (repo_root / "profiles").mkdir(parents=True)
    (repo_root / "profiles" / "default.md").write_text("# Default profile\n", encoding="utf-8")
    (round_dir.parents[1]).mkdir(parents=True)
    (round_dir.parents[1] / "case.md").write_text("Reviewer profile: default\n", encoding="utf-8")
    (round_dir / "notes").mkdir(parents=True)
    (round_dir / "notes" / "assignment.md").write_text("# Assignment\n", encoding="utf-8")
    write_common_briefing("case-a", "round-a", "2026-05-13T12:00:00Z", round_dir)

    records = collect_supporting_work_artifacts(round_dir)
    by_path = {record["path"]: record for record in records}

    assert by_path[COMMON_BRIEFING_REL]["schema_version"] == "common-briefing-v1"
    assert validate_supporting_work_artifacts(records, round_dir, case_id="case-a", round_id="round-a") == []

    payload = json.loads((round_dir / COMMON_BRIEFING_REL).read_text(encoding="utf-8"))
    payload["context_handoffs"][0]["path"] = "../private.txt"
    write_json(round_dir / COMMON_BRIEFING_REL, payload)

    records = collect_supporting_work_artifacts(round_dir)
    errors = validate_supporting_work_artifacts(records, round_dir, case_id="case-a", round_id="round-a")

    assert any("context_handoffs item 1: path must be a safe relative path" in error for error in errors)


def test_common_briefing_rejects_false_present_record_for_missing_file(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    round_dir = repo_root / "cases" / "case-a" / "rounds" / "round-a"
    (round_dir / "notes").mkdir(parents=True)
    (round_dir / "notes" / "assignment.md").write_text("# Assignment\n", encoding="utf-8")
    write_common_briefing("case-a", "round-a", "2026-05-13T12:00:00Z", round_dir)
    payload = json.loads((round_dir / COMMON_BRIEFING_REL).read_text(encoding="utf-8"))
    payload["base_inputs"][0]["path"] = "notes/missing.md"
    payload["base_inputs"][0]["status"] = "present"
    payload["base_inputs"][0].pop("sha256", None)
    write_json(round_dir / COMMON_BRIEFING_REL, payload)

    records = collect_supporting_work_artifacts(round_dir)
    errors = validate_supporting_work_artifacts(records, round_dir, case_id="case-a", round_id="round-a")

    assert any("base_inputs item 1: present records must point to an existing file" in error for error in errors)


def test_collect_supporting_work_artifacts_records_human_producer_identity(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    (round_dir / "inputs").mkdir(parents=True)
    (round_dir / "inputs" / "results.csv").write_text("metric,value\nlatency,42\n", encoding="utf-8")
    write_json(
        round_dir / "work" / "quantitative_claims.json",
        {
            "schema_version": "quantitative-claims-v1",
            "case_id": "case-a",
            "round_id": "round-a",
            "generated_at": "2026-05-11T00:00:00Z",
            "producer_type": "human",
            "producer_role": "quantitative-claims-reviewer",
            "producer_agent": None,
            "human_reviewer_note": "Reviewed by operator.",
            "source_refs": ["inputs/results.csv"],
            "claims": [
                {
                    "claim_id": "Q1",
                    "summary": "Synthetic metric claim.",
                    "kind": "metric",
                    "status": "needs_context",
                    "unit": "ms",
                    "baseline_status": "missing",
                    "practical_context": "weak",
                    "scale_context": "Latency scale is a single synthetic value.",
                    "sample_context": "Synthetic result file is the sample context.",
                    "practical_magnitude": "Magnitude is not interpreted against a baseline.",
                    "overclaim_risk": "moderate",
                    "reproducibility_refs": ["inputs/results.csv"],
                    "evidence_refs": ["inputs/results.csv"],
                    "requires_reviewer_verification": True,
                }
            ],
            "limitations": [],
        },
    )

    records = collect_supporting_work_artifacts(round_dir)
    quantitative = {record["path"]: record for record in records}["work/quantitative_claims.json"]

    assert quantitative["producer_type"] == "human"
    assert quantitative["producer_role"] == "quantitative-claims-reviewer"
    assert quantitative["producer_agent"] == "human_reviewer"
    assert validate_supporting_work_artifacts(records, round_dir, case_id="case-a", round_id="round-a") == []


def test_validate_supporting_work_artifacts_requires_hash_and_payload_fields(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    write_json(
        round_dir / "work" / "assignment_coverage_agent.json",
        {
            "schema_version": "assignment-coverage-agent-v1",
            "case_id": "case-a",
            "round_id": "round-a",
            "generated_at": "2026-05-06T00:00:00Z",
            "producer_type": "agent",
            "producer_role": "assignment-coverage-reviewer",
            "producer_agent": "agent-a",
            "authorization_note": "Authorized in current request.",
            "source_refs": [],
            "limitations": [],
        },
    )
    write_json(
        round_dir / "work" / "code_reproducibility.json",
        {
            "schema_version": "code-reproducibility-v1",
            "case_id": "case-a",
            "round_id": "round-a",
            "generated_at": "2026-05-06T00:00:00Z",
        },
    )

    errors = validate_supporting_work_artifacts(
        [
            {"path": "work/assignment_coverage_agent.json", "kind": "structured_data"},
            {
                "path": "work/code_reproducibility.json",
                "kind": "structured_data",
                "artifact_sha256": "not-a-hash",
            },
        ],
        round_dir,
        case_id="case-a",
        round_id="round-a",
    )

    assert any("artifact_sha256 must be a 64-character hex string" in error for error in errors)
    assert any("assignment_points must be list" in error for error in errors)
    assert any("classification must be str" in error for error in errors)


def test_validate_supporting_work_artifacts_rejects_unsafe_path_before_hashing(tmp_path: Path) -> None:
    outside = tmp_path / "outside.json"
    outside.write_text("{}\n", encoding="utf-8")
    round_dir = tmp_path / "round"
    round_dir.mkdir()

    errors = validate_supporting_work_artifacts(
        [
            {
                "path": outside.as_posix(),
                "kind": "structured_data",
                "artifact_sha256": "0" * 64,
            }
        ],
        round_dir,
        case_id="case-a",
        round_id="round-a",
    )

    assert errors == ["supporting_work_artifacts item 1: path must be relative inside the round"]
