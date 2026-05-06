import json
from pathlib import Path

from thesis_review_workflow.work_artifacts import collect_supporting_work_artifacts, validate_supporting_work_artifacts


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def test_collect_supporting_work_artifacts_records_known_json_and_packet(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    write_json(
        round_dir / "work" / "assignment_coverage_map.json",
        {
            "schema_version": "assignment-coverage-map-v1",
            "case_id": "case-a",
            "round_id": "round-a",
            "generated_at": "2026-05-06T00:00:00Z",
            "assignment_points": [],
        },
    )
    packet = round_dir / "work" / "opponent_packets" / "synthesis.md"
    packet.parent.mkdir(parents=True, exist_ok=True)
    packet.write_text("# Packet\n", encoding="utf-8")

    records = collect_supporting_work_artifacts(round_dir)

    by_path = {record["path"]: record for record in records}
    assert by_path["work/assignment_coverage_map.json"]["schema_version"] == "assignment-coverage-map-v1"
    assert by_path["work/assignment_coverage_map.json"]["artifact_sha256"]
    assert by_path["work/opponent_packets/synthesis.md"]["kind"] == "text"


def test_validate_supporting_work_artifacts_rejects_stale_hash_and_wrong_case(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    write_json(
        round_dir / "work" / "evidence_presence.json",
        {
            "schema_version": "evidence-presence-v1",
            "case_id": "other-case",
            "round_id": "round-a",
            "generated_at": "2026-05-06T00:00:00Z",
            "findings": [],
        },
    )

    errors = validate_supporting_work_artifacts(
        [
            {
                "path": "work/evidence_presence.json",
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


def test_validate_supporting_work_artifacts_requires_hash_and_payload_fields(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    write_json(
        round_dir / "work" / "assignment_coverage_map.json",
        {
            "schema_version": "assignment-coverage-map-v1",
            "case_id": "case-a",
            "round_id": "round-a",
            "generated_at": "2026-05-06T00:00:00Z",
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
            {"path": "work/assignment_coverage_map.json", "kind": "structured_data"},
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
