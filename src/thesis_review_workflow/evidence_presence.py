"""Structural media inventory helpers for evidence review."""

from __future__ import annotations

import json
from pathlib import Path

MEDIA_INVENTORY_SCHEMA = "visual-media-inventory-v1"
MEDIA_PRESENCE_INVENTORY_REL = Path("work/media_presence_inventory.jsonl")

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
    if suffix in {".mp4", ".mov", ".avi", ".mkv", ".webm"}:
        return "video"
    if suffix in {".ppt", ".pptx", ".odp", ".key"}:
        return "presentation"
    return "image"


def build_media_inventory(round_dir: Path) -> list[dict[str, object]]:
    return [
        {
            "schema_version": MEDIA_INVENTORY_SCHEMA,
            "path": rel(round_dir, path),
            "category": media_category(path),
            "state": "present-uninspected",
            "inspection_depth": "metadata-only",
        }
        for path in media_files(round_dir)
    ]


def write_media_inventory(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records)
    path.write_text(text, encoding="utf-8")
