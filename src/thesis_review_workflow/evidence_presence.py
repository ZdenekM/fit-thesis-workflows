"""Structural media inventory helpers for evidence review."""

from __future__ import annotations

import json
from pathlib import Path

from thesis_review_workflow.artifact_classification import (
    AUDIO_SUFFIXES,
    MEDIA_SUFFIXES,
    PRESENTATION_SUFFIXES,
    VIDEO_SUFFIXES,
)
from thesis_review_workflow.artifact_metadata import structural_metadata_for_artifact
from thesis_review_workflow.artifact_validation import sha256_file

MEDIA_INVENTORY_SCHEMA = "visual-media-inventory-v1"
MEDIA_PRESENCE_INVENTORY_REL = Path("work/media_presence_inventory.jsonl")


def rel(round_dir: Path, path: Path) -> str:
    return path.relative_to(round_dir).as_posix()


def iter_round_files(round_dir: Path) -> list[Path]:
    roots = [round_dir / name for name in ("inputs", "extracted", "notes", "work", "outputs")]
    files: list[Path] = []
    for root in roots:
        if root.is_dir():
            files.extend(path for path in sorted(root.rglob("*")) if path.is_file() and not path.is_symlink())
    return files


def media_files(round_dir: Path) -> list[Path]:
    return [path for path in iter_round_files(round_dir) if path.suffix.lower() in MEDIA_SUFFIXES]


def media_category(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in VIDEO_SUFFIXES:
        return "video"
    if suffix in AUDIO_SUFFIXES:
        return "audio"
    if suffix in PRESENTATION_SUFFIXES:
        return "presentation"
    return "image"


def build_media_inventory(round_dir: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for path in media_files(round_dir):
        rel_path = rel(round_dir, path)
        digest = sha256_file(path)
        record: dict[str, object] = {
            "schema_version": MEDIA_INVENTORY_SCHEMA,
            "path": rel_path,
            "category": media_category(path),
            "state": "present-uninspected",
            "inspection_depth": "metadata-only",
        }
        metadata = structural_metadata_for_artifact(
            path_ref=rel_path,
            artifact_class="media_artifact",
            size_bytes=path.stat().st_size,
            sha256=digest,
        )
        if metadata is not None:
            record["deterministic_metadata"] = metadata
        records.append(record)
    return records


def write_media_inventory(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records)
    path.write_text(text, encoding="utf-8")
