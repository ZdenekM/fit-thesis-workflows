"""Deterministic sidecars for PDF text extraction."""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from thesis_review_workflow.paths import is_safe_round_relative_path, rel_round
from thesis_review_workflow.reuse import SourceClass, SourceFingerprint
from thesis_review_workflow.work_artifacts import sha256_file

PDF_EXTRACT_SCHEMA_VERSION = "pdf-extract-v1"
PDF_EXTRACT_PRODUCER = "scripts/extract-pdf-text"
PDF_EXTRACT_COMMAND = "pdftotext"
PDF_EXTRACT_ARGS = ("-layout",)
PDF_EXTRACT_SIDECAR_SUFFIX = ".pdf-extract.json"


def now_utc() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def pdf_extract_sidecar_path(output_txt: Path) -> Path:
    return output_txt.with_name(f"{output_txt.name}{PDF_EXTRACT_SIDECAR_SUFFIX}")


def pdftotext_version() -> str:
    executable = shutil.which(PDF_EXTRACT_COMMAND)
    if executable is None:
        return "unavailable"
    result = subprocess.run(
        [executable, "-v"],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    text = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    return text.splitlines()[0] if text.splitlines() else "available"


def round_relative_or_none(round_dir: Path, path: Path) -> str | None:
    try:
        value = path.resolve().relative_to(round_dir.resolve()).as_posix()
    except ValueError:
        return None
    return value if is_safe_round_relative_path(value) else None


def file_record(round_dir: Path, path: Path) -> dict[str, object]:
    rel = round_relative_or_none(round_dir, path)
    return {
        "path": rel,
        "path_state": "round_relative" if rel is not None else "external",
        "display_name": path.name,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def extractor_contract_id(manifest: dict[str, Any]) -> str:
    extractor = manifest.get("extractor")
    if not isinstance(extractor, dict):
        return PDF_EXTRACT_SCHEMA_VERSION
    contract = json.dumps(extractor, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"{PDF_EXTRACT_SCHEMA_VERSION}:{contract}"


def build_pdf_extract_manifest(
    round_dir: Path,
    input_pdf: Path,
    output_txt: Path,
    *,
    extractor_version: str,
    generated_at: str | None = None,
) -> dict[str, object]:
    return {
        "schema_version": PDF_EXTRACT_SCHEMA_VERSION,
        "producer": PDF_EXTRACT_PRODUCER,
        "generated_at": generated_at or now_utc(),
        "input_pdf": file_record(round_dir, input_pdf),
        "output_text": file_record(round_dir, output_txt),
        "extractor": {
            "command": PDF_EXTRACT_COMMAND,
            "version": extractor_version,
            "args": list(PDF_EXTRACT_ARGS),
        },
    }


def load_pdf_extract_manifest(sidecar: Path) -> dict[str, Any] | None:
    try:
        loaded = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return loaded if isinstance(loaded, dict) else None


def write_pdf_extract_manifest(
    round_dir: Path,
    input_pdf: Path,
    output_txt: Path,
    *,
    extractor_version: str,
    generated_at: str | None = None,
) -> dict[str, object]:
    manifest = build_pdf_extract_manifest(
        round_dir,
        input_pdf,
        output_txt,
        extractor_version=extractor_version,
        generated_at=generated_at,
    )
    sidecar = pdf_extract_sidecar_path(output_txt)
    sidecar.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def _nested_str(manifest: dict[str, Any], section: str, field: str) -> str:
    value = manifest.get(section)
    if not isinstance(value, dict):
        return ""
    nested = value.get(field)
    return nested if isinstance(nested, str) else ""


def pdf_extract_is_current(
    round_dir: Path,
    input_pdf: Path,
    output_txt: Path,
    *,
    extractor_version: str,
) -> bool:
    sidecar = pdf_extract_sidecar_path(output_txt)
    if not output_txt.is_file() or not sidecar.is_file():
        return False
    manifest = load_pdf_extract_manifest(sidecar)
    if manifest is None or manifest.get("schema_version") != PDF_EXTRACT_SCHEMA_VERSION:
        return False
    extractor = manifest.get("extractor")
    if not isinstance(extractor, dict):
        return False
    if extractor.get("command") != PDF_EXTRACT_COMMAND:
        return False
    if extractor.get("args") != list(PDF_EXTRACT_ARGS):
        return False
    if extractor.get("version") != extractor_version:
        return False
    if _nested_str(manifest, "input_pdf", "sha256") != sha256_file(input_pdf):
        return False
    if _nested_str(manifest, "output_text", "sha256") != sha256_file(output_txt):
        return False
    output_path = _nested_str(manifest, "output_text", "path")
    return output_path == rel_round(round_dir, output_txt)


def source_fingerprints_from_pdf_extract_manifest(
    manifest: dict[str, Any],
) -> tuple[SourceFingerprint, ...]:
    if manifest.get("schema_version") != PDF_EXTRACT_SCHEMA_VERSION:
        return ()
    sources: list[SourceFingerprint] = []
    for section, source_class in (
        ("input_pdf", SourceClass.THESIS_PDF),
        ("output_text", SourceClass.THESIS_EXTRACT),
    ):
        value = manifest.get(section)
        if not isinstance(value, dict):
            continue
        source_ref = value.get("path")
        sha256 = value.get("sha256")
        if not isinstance(source_ref, str) or not isinstance(sha256, str):
            continue
        try:
            sources.append(
                SourceFingerprint(
                    source_ref=source_ref,
                    source_class=source_class,
                    sha256=sha256,
                    schema_version=extractor_contract_id(manifest),
                    producer=PDF_EXTRACT_PRODUCER,
                )
            )
        except ValueError:
            continue
    return tuple(sources)
