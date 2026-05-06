import json
from pathlib import Path
from typing import Any, cast

from thesis_review_workflow.evidence_presence import MEDIA_PRESENCE_INVENTORY_REL, to_artifact, write_media_inventory


def test_evidence_presence_flags_missing_required_media_and_metric_inputs(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    (round_dir / "notes").mkdir(parents=True)
    (round_dir / "extracted").mkdir()
    (round_dir / "work").mkdir()
    (round_dir / "notes" / "assignment.md").write_text(
        "## Formal Assignment Text Or Summary\n- Provide demo video.\n",
        encoding="utf-8",
    )
    (round_dir / "extracted" / "thesis.txt").write_text(
        "Evaluation reports accuracy and F1 metrics.\n",
        encoding="utf-8",
    )
    (round_dir / "work" / "code_reproducibility.json").write_text(
        json.dumps({"classification": "missing_instructions"}) + "\n",
        encoding="utf-8",
    )

    artifact, media = to_artifact("case-a", "round-a", "2026-05-06T00:00:00Z", round_dir)
    findings = cast(list[dict[str, Any]], artifact["findings"])
    states = {(item["category"], item["state"]) for item in findings}
    by_state = {item["state"]: item for item in findings if item["category"] == "evaluation"}

    assert artifact["schema_version"] == "evidence-presence-v1"
    assert ("media", "missing") in states
    assert ("evaluation", "missing_data") in states
    assert ("evaluation", "missing_script") in states
    assert "Request raw data" in by_state["missing_data"]["request"]
    assert "Request or cite calculation scripts" in by_state["missing_script"]["request"]
    assert ("code_reproducibility", "missing_instructions") in states
    assert media[0]["category"] == "video"
    assert media[0]["state"] == "missing"


def test_evidence_presence_uses_structural_eval_artifacts_to_suppress_metric_requests(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    (round_dir / "extracted").mkdir(parents=True)
    (round_dir / "inputs").mkdir()
    (round_dir / "work").mkdir()
    (round_dir / "extracted" / "thesis.txt").write_text(
        "Evaluation reports accuracy and F1 metrics.\n",
        encoding="utf-8",
    )
    (round_dir / "inputs" / "eval_results.csv").write_text("metric,value\naccuracy,0.98\n", encoding="utf-8")
    (round_dir / "work" / "eval_metrics.py").write_text("print('synthetic')\n", encoding="utf-8")

    artifact, _media = to_artifact("case-a", "round-a", "2026-05-06T00:00:00Z", round_dir)
    findings = cast(list[dict[str, Any]], artifact["findings"])

    assert not any(item["category"] == "evaluation" for item in findings)


def test_evidence_presence_does_not_treat_generic_json_or_app_script_as_eval_evidence(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    (round_dir / "extracted").mkdir(parents=True)
    (round_dir / "inputs").mkdir()
    (round_dir / "work").mkdir()
    (round_dir / "extracted" / "thesis.txt").write_text(
        "Evaluation reports accuracy and F1 metrics.\n",
        encoding="utf-8",
    )
    (round_dir / "inputs" / "config.json").write_text("{}\n", encoding="utf-8")
    (round_dir / "work" / "app.py").write_text("print('synthetic')\n", encoding="utf-8")

    artifact, _media = to_artifact("case-a", "round-a", "2026-05-06T00:00:00Z", round_dir)
    findings = cast(list[dict[str, Any]], artifact["findings"])
    states = {(item["category"], item["state"]) for item in findings}

    assert ("evaluation", "missing_data") in states
    assert ("evaluation", "missing_script") in states


def test_evidence_presence_records_present_media_as_uninspected(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    (round_dir / "inputs").mkdir(parents=True)
    (round_dir / "inputs" / "demo.mp4").write_text("synthetic", encoding="utf-8")

    artifact, media = to_artifact("case-a", "round-a", "2026-05-06T00:00:00Z", round_dir)
    findings = cast(list[dict[str, Any]], artifact["findings"])

    assert findings[0]["state"] == "present-uninspected"
    assert media[0]["path"] == "inputs/demo.mp4"
    assert media[0]["inspection_depth"] == "metadata-only"


def test_evidence_presence_does_not_treat_demo_as_unsatisfiable_media_category(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    (round_dir / "notes").mkdir(parents=True)
    (round_dir / "inputs").mkdir()
    (round_dir / "notes" / "assignment.md").write_text(
        "## Formal Assignment Text Or Summary\n- Provide demo video.\n",
        encoding="utf-8",
    )
    (round_dir / "inputs" / "demo.mp4").write_text("synthetic", encoding="utf-8")

    artifact, _media = to_artifact("case-a", "round-a", "2026-05-06T00:00:00Z", round_dir)
    findings = cast(list[dict[str, Any]], artifact["findings"])

    assert not any(item["state"] == "missing" for item in findings)


def test_evidence_presence_reads_existing_figure_media_inventory_without_overwriting(tmp_path: Path) -> None:
    round_dir = tmp_path / "round"
    inventory = round_dir / "work" / "figure_media" / "visual_inventory.jsonl"
    inventory.parent.mkdir(parents=True)
    inventory.write_text(
        json.dumps({"item_id": "fig-1", "inspection_status": "pdf_inspected"}) + "\n",
        encoding="utf-8",
    )

    artifact, _media = to_artifact("case-a", "round-a", "2026-05-06T00:00:00Z", round_dir)
    findings = cast(list[dict[str, Any]], artifact["findings"])

    assert findings[0]["state"] == "inspected"
    assert inventory.read_text(encoding="utf-8").strip()


def test_write_media_inventory_uses_jsonl(tmp_path: Path) -> None:
    path = tmp_path / MEDIA_PRESENCE_INVENTORY_REL
    write_media_inventory(path, [{"schema_version": "visual-media-inventory-v1", "path": "inputs/demo.mp4"}])

    assert json.loads(path.read_text(encoding="utf-8"))["path"] == "inputs/demo.mp4"
