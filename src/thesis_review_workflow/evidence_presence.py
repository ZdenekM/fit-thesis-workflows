"""Advisory evidence-presence checks for opponent review."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from thesis_review_workflow.evaluation_claims import (
    is_data_artifact_path,
    is_script_artifact_path,
    script_artifact_from_data_path,
)

SCHEMA_VERSION = "evidence-presence-v1"
MEDIA_INVENTORY_SCHEMA = "visual-media-inventory-v1"
ASSIGNMENT_REL = Path("notes/assignment.md")
CODE_REPRO_ARTIFACT_REL = Path("work/code_reproducibility.json")
MEDIA_PRESENCE_INVENTORY_REL = Path("work/media_presence_inventory.jsonl")
FIGURE_MEDIA_INVENTORY_REL = Path("work/figure_media/visual_inventory.jsonl")

MEDIA_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
    ".ppt",
    ".pptx",
    ".odp",
    ".key",
}
MEDIA_REQUIREMENT_TOKENS = {
    "video": ("video", "nahrav", "nahráv"),
    "poster": ("poster", "plakat", "plakát"),
    "presentation": ("presentation", "prezentac", "slides", "slidy"),
}
METRIC_CLAIM_RE = re.compile(
    r"\b(metric|metrik|evaluac|experiment|accuracy|precision|recall|f1|auc|mae|rmse|vysledk|výsledk)\w*",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class EvidenceFinding:
    category: str
    state: str
    summary: str
    evidence: list[str]
    request: str


def rel(round_dir: Path, path: Path) -> str:
    return path.relative_to(round_dir).as_posix()


def assignment_text(round_dir: Path) -> str:
    path = round_dir / ASSIGNMENT_REL
    return path.read_text(encoding="utf-8", errors="ignore") if path.is_file() else ""


def required_media_categories(text: str) -> list[str]:
    folded = text.lower()
    required = []
    for category, tokens in MEDIA_REQUIREMENT_TOKENS.items():
        if any(token in folded for token in tokens):
            required.append(category)
    return required


def iter_round_files(round_dir: Path) -> list[Path]:
    roots = [round_dir / name for name in ("inputs", "extracted", "notes", "work")]
    files: list[Path] = []
    for root in roots:
        if root.is_dir():
            files.extend(path for path in sorted(root.rglob("*")) if path.is_file())
    return files


def media_files(round_dir: Path) -> list[Path]:
    return [path for path in iter_round_files(round_dir) if path.suffix.lower() in MEDIA_SUFFIXES]


def data_and_script_artifacts(round_dir: Path) -> tuple[list[Path], list[Path]]:
    data: list[Path] = []
    scripts: list[Path] = []
    for path in iter_round_files(round_dir):
        if is_data_artifact_path(path):
            data.append(path)
            if script_artifact_from_data_path(path):
                scripts.append(path)
        elif is_script_artifact_path(path):
            scripts.append(path)
    return data, scripts


def metric_claims_present(round_dir: Path) -> bool:
    for path in [round_dir / "extracted", round_dir / "notes"]:
        if not path.is_dir():
            continue
        for text_file in sorted(path.rglob("*")):
            if text_file.suffix.lower() not in {".txt", ".md"} or not text_file.is_file():
                continue
            if METRIC_CLAIM_RE.search(text_file.read_text(encoding="utf-8", errors="ignore")):
                return True
    return False


def load_code_reproducibility(round_dir: Path) -> str | None:
    path = round_dir / CODE_REPRO_ARTIFACT_REL
    if not path.is_file():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "invalid"
    if not isinstance(loaded, dict):
        return "invalid"
    classification = loaded.get("classification")
    return classification if isinstance(classification, str) else "invalid"


def build_media_inventory(round_dir: Path, required_categories: list[str]) -> list[dict[str, object]]:
    present = media_files(round_dir)
    records: list[dict[str, object]] = [
        {
            "schema_version": MEDIA_INVENTORY_SCHEMA,
            "path": rel(round_dir, path),
            "category": media_category(path),
            "state": "present-uninspected",
            "inspection_depth": "metadata-only",
        }
        for path in present
    ]
    present_categories = {str(record["category"]) for record in records}
    for category in required_categories:
        if category not in present_categories:
            records.append(
                {
                    "schema_version": MEDIA_INVENTORY_SCHEMA,
                    "path": "",
                    "category": category,
                    "state": "missing",
                    "inspection_depth": "not-inspected",
                }
            )
    return records


def media_category(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".mp4", ".mov", ".avi", ".mkv", ".webm"}:
        return "video"
    if suffix in {".ppt", ".pptx", ".odp", ".key"}:
        return "presentation"
    return "image"


def inspected_media_records(round_dir: Path) -> list[str]:
    path = round_dir / FIGURE_MEDIA_INVENTORY_REL
    if not path.is_file():
        return []
    inspected: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            loaded = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(loaded, dict):
            continue
        status = loaded.get("inspection_status")
        if status in {"pdf_inspected", "source_asset_checked"}:
            item_id = loaded.get("item_id")
            inspected.append(str(item_id) if item_id else "inspected-item")
    return inspected


def findings(round_dir: Path) -> tuple[list[EvidenceFinding], list[dict[str, object]]]:
    text = assignment_text(round_dir)
    required_categories = required_media_categories(text)
    media_records = build_media_inventory(round_dir, required_categories)
    result: list[EvidenceFinding] = []

    missing_media = [record for record in media_records if record["state"] == "missing"]
    inspected_media = inspected_media_records(round_dir)
    if missing_media:
        result.append(
            EvidenceFinding(
                "media",
                "missing",
                "Assignment or notes mention media/demo evidence, but matching media artifacts were not found.",
                [str(record["category"]) for record in missing_media],
                "Ask for the missing media/demo artifact or record why it is out of scope.",
            )
        )
    elif inspected_media:
        result.append(
            EvidenceFinding(
                "media",
                "inspected",
                "Figure/media inventory records inspected media evidence.",
                inspected_media[:8],
                "Use figure/media review for visual-content claims.",
            )
        )
    elif media_records:
        result.append(
            EvidenceFinding(
                "media",
                "present-uninspected",
                "Media/demo artifacts are present but only inventoried, not visually inspected.",
                [str(record["path"]) for record in media_records if record.get("path")],
                "Route substantive visual/demo claims to figure/media review before relying on them.",
            )
        )

    data_artifacts, script_artifacts = data_and_script_artifacts(round_dir)
    if metric_claims_present(round_dir):
        if not data_artifacts:
            result.append(
                EvidenceFinding(
                    "evaluation",
                    "missing_data",
                    "Metric/evaluation language is present, but no obvious data artifact was found.",
                    [],
                    "Request raw data, tables, logs, notebooks, or reproducibility notes for quantitative claims.",
                )
            )
        if not script_artifacts:
            result.append(
                EvidenceFinding(
                    "evaluation",
                    "missing_script",
                    "Metric/evaluation language is present, but no obvious calculation script or notebook was found.",
                    [rel(round_dir, path) for path in data_artifacts[:8]],
                    "Request or cite calculation scripts/notebooks before relying on exact metrics.",
                )
            )

    code_classification = load_code_reproducibility(round_dir)
    if code_classification in {"not_attempted", "missing_instructions", "missing_test_commands", "invalid"}:
        result.append(
            EvidenceFinding(
                "code_reproducibility",
                code_classification,
                "Code reproducibility classification is not ready for strong runtime claims.",
                [CODE_REPRO_ARTIFACT_REL.as_posix()],
                "Use cautious opponent wording or resolve the code reproducibility evidence first.",
            )
        )
    return result, media_records


def to_artifact(
    case_id: str, round_id: str, generated_at: str, round_dir: Path
) -> tuple[dict[str, object], list[dict[str, object]]]:
    found, media_records = findings(round_dir)
    artifact = {
        "schema_version": SCHEMA_VERSION,
        "case_id": case_id,
        "round_id": round_id,
        "generated_at": generated_at,
        "advisory": True,
        "findings": [
            {
                "category": item.category,
                "state": item.state,
                "summary": item.summary,
                "evidence": item.evidence,
                "request": item.request,
            }
            for item in found
        ],
    }
    return artifact, media_records


def write_json(path: Path, artifact: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_media_inventory(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records)
    path.write_text(text, encoding="utf-8")
