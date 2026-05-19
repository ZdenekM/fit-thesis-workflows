import json
from pathlib import Path

from thesis_review_workflow.artifact_validation import sha256_file
from thesis_review_workflow.cli import check_evidence_presence
from thesis_review_workflow.evidence_presence import (
    MEDIA_PRESENCE_INVENTORY_REL,
    build_media_inventory,
    write_media_inventory,
)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def make_round(root: Path) -> Path:
    case_dir = root / "cases" / "case-a"
    round_dir = case_dir / "rounds" / "round-a"
    (round_dir / "notes").mkdir(parents=True)
    (round_dir / "inputs").mkdir()
    (round_dir / "work").mkdir()
    (case_dir / "case.md").write_text("Reviewer profile: default\n", encoding="utf-8")
    (case_dir / "current-round.txt").write_text("round-a\n", encoding="utf-8")
    (round_dir / "notes" / "assignment.md").write_text("# Assignment\n", encoding="utf-8")
    return round_dir


def evidence_requirements(case_id: str = "case-a") -> dict[str, object]:
    return {
        "schema_version": "evidence-requirements-v1",
        "case_id": case_id,
        "round_id": "round-a",
        "generated_at": "2026-05-07T00:00:00Z",
        "producer_type": "agent",
        "producer_role": "evidence-requirements-reviewer",
        "producer_agent": "agent-a",
        "authorization_note": "Current request explicitly authorized agents.",
        "source_refs": ["notes/assignment.md"],
        "requirements": [
            {
                "requirement_id": "E1",
                "category": "media",
                "state": "present",
                "request": "Check demo evidence.",
                "evidence_refs": ["inputs/demo.mp4"],
                "requires_reviewer_verification": False,
            },
            {
                "requirement_id": "E2",
                "category": "evaluation_data",
                "state": "weak",
                "request": "Review result data.",
                "evidence_refs": [],
                "requires_reviewer_verification": True,
            },
        ],
        "limitations": [],
    }


def test_check_evidence_presence_validates_requirements_and_writes_media_inventory(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    root = tmp_path / "repo"
    round_dir = make_round(root)
    (round_dir / "inputs" / "demo.mp4").write_text("synthetic", encoding="utf-8")
    write_json(round_dir / "work" / "evidence_requirements.json", evidence_requirements())
    monkeypatch.setattr(check_evidence_presence, "repo_root", lambda: root)

    assert check_evidence_presence.main(["case-a", "round-a"]) == 0

    output = capsys.readouterr().out
    assert "Evidence requirements artifact: cases/case-a/rounds/round-a/work/evidence_requirements.json" in output
    assert "Evidence requirements: 2" in output
    assert "Requirement states: present=1, weak=1" in output
    assert "Media inventory records: 1" in output
    inventory = (round_dir / MEDIA_PRESENCE_INVENTORY_REL).read_text(encoding="utf-8").splitlines()
    record = json.loads(inventory[0])
    assert record["path"] == "inputs/demo.mp4"
    assert record["deterministic_metadata"]["metadata_mode"] == "non_executing_structural_metadata"
    assert record["deterministic_metadata"]["semantic_observation"] == "not_performed"
    assert record["deterministic_metadata"]["sha256"] == sha256_file(round_dir / "inputs" / "demo.mp4")
    assert not (round_dir / "work" / "evidence_presence.json").exists()


def test_check_evidence_presence_requires_structured_requirements(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    root = tmp_path / "repo"
    round_dir = make_round(root)
    stale_inventory = round_dir / MEDIA_PRESENCE_INVENTORY_REL
    stale_inventory.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(check_evidence_presence, "repo_root", lambda: root)

    assert check_evidence_presence.main(["case-a", "round-a"]) == 1

    output = capsys.readouterr().out
    assert "missing structured evidence artifact" in output
    assert "Create `work/evidence_requirements.json`" in output
    assert not (round_dir / MEDIA_PRESENCE_INVENTORY_REL).exists()


def test_check_evidence_presence_rejects_invalid_state(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    root = tmp_path / "repo"
    round_dir = make_round(root)
    payload = evidence_requirements()
    requirements = payload["requirements"]
    assert isinstance(requirements, list)
    requirements[0]["state"] = "unknown"
    write_json(round_dir / "work" / "evidence_requirements.json", payload)
    (round_dir / MEDIA_PRESENCE_INVENTORY_REL).write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(check_evidence_presence, "repo_root", lambda: root)

    assert check_evidence_presence.main(["case-a", "round-a"]) == 1

    output = capsys.readouterr().out
    assert "state must be one of" in output
    assert not (round_dir / MEDIA_PRESENCE_INVENTORY_REL).exists()


def test_build_media_inventory_records_present_media_only(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    (round_dir / "notes").mkdir(parents=True)
    (round_dir / "inputs").mkdir()
    (round_dir / "notes" / "assignment.md").write_text("Provide a demo video.\n", encoding="utf-8")
    (round_dir / "inputs" / "demo.mp4").write_text("synthetic", encoding="utf-8")
    (round_dir / "inputs" / "screenshot.png").write_text("image", encoding="utf-8")

    records = build_media_inventory(round_dir)

    digest = sha256_file(round_dir / "inputs" / "demo.mp4")
    by_path = {str(record["path"]): record for record in records}
    assert by_path["inputs/demo.mp4"] == {
        "schema_version": "visual-media-inventory-v1",
        "path": "inputs/demo.mp4",
        "category": "video",
        "state": "present-uninspected",
        "inspection_depth": "metadata-only",
        "deterministic_metadata": {
            "schema_version": "deterministic-artifact-metadata-v1",
            "artifact_category": "media",
            "extension": ".mp4",
            "metadata_mode": "non_executing_structural_metadata",
            "content_inspection": "not_performed",
            "semantic_observation": "not_performed",
            "execution_state": "not_run",
            "stream_metadata_state": "not_collected",
            "size_bytes": len("synthetic"),
            "sha256": digest,
        },
    }
    image_record = by_path["inputs/screenshot.png"]
    assert image_record["category"] == "image"
    image_metadata = image_record["deterministic_metadata"]
    assert isinstance(image_metadata, dict)
    assert image_metadata["extension"] == ".png"


def test_write_media_inventory_uses_jsonl(tmp_path: Path) -> None:
    path = tmp_path / MEDIA_PRESENCE_INVENTORY_REL
    write_media_inventory(path, [{"schema_version": "visual-media-inventory-v1", "path": "inputs/demo.mp4"}])

    assert json.loads(path.read_text(encoding="utf-8"))["path"] == "inputs/demo.mp4"
