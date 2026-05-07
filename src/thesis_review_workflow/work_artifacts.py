"""Round-local work artifact contracts used by review provenance."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from thesis_review_workflow.paths import is_safe_round_relative_path
from thesis_review_workflow.structured_evidence import STRUCTURED_EVIDENCE_SCHEMAS, validate_structured_evidence_payload

KNOWN_JSON_ARTIFACT_SCHEMAS: dict[str, set[str]] = {
    "work/assignment_coverage_agent.json": {"assignment-coverage-agent-v1"},
    "work/evidence_requirements.json": {"evidence-requirements-v1"},
    "work/quantitative_claims.json": {"quantitative-claims-v1"},
    "work/opponent_report_trace.json": {"opponent-report-trace-v1"},
    "work/code_reproducibility.json": {"code-reproducibility-v1"},
}

JSON_ARTIFACT_REQUIRED_FIELDS: dict[str, dict[str, type]] = {
    "work/assignment_coverage_agent.json": {"assignment_points": list},
    "work/evidence_requirements.json": {"requirements": list},
    "work/quantitative_claims.json": {"claims": list},
    "work/opponent_report_trace.json": {"is_items": list, "defense_questions": list, "uncertainty_items": list},
    "work/code_reproducibility.json": {"classification": str},
}

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

EXPLICIT_WORK_ARTIFACTS = (
    "work/feedback_student_draft.md",
    "work/oponent_podklady_draft.md",
    "work/oponent_posudek_draft.md",
    "work/code_workspace.md",
    "work/serena_roots.json",
    "work/agent_coverage.json",
    "work/code/.prepare-code-workspace-manifest.json",
    "work/figure_media/visual_inventory.jsonl",
    "work/assignment_coverage_agent.json",
    "work/evidence_requirements.json",
    "work/quantitative_claims.json",
    "work/opponent_report_trace.json",
    "work/code_reproducibility.json",
    "work/media_presence_inventory.jsonl",
)

WORK_ARTIFACT_GLOBS = (
    "work/agent_*.md",
    "work/opponent_packets/*.md",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix in {".zip", ".tar", ".gz", ".tgz", ".7z"}:
        return "archive"
    if suffix in {".md", ".txt"}:
        return "text"
    if suffix in {".json", ".jsonl", ".yml", ".yaml", ".toml"}:
        return "structured_data"
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
        return "image"
    return "file"


def round_relative(round_dir: Path, path: Path) -> str:
    return path.relative_to(round_dir).as_posix()


def work_artifact_record(round_dir: Path, path: Path) -> dict[str, str]:
    rel_path = round_relative(round_dir, path)
    record = {
        "path": rel_path,
        "kind": artifact_kind(path),
        "artifact_sha256": sha256_file(path),
    }
    schema_version = json_schema_version(path) if rel_path in KNOWN_JSON_ARTIFACT_SCHEMAS else None
    if schema_version:
        record["schema_version"] = schema_version
    return record


def json_schema_version(path: Path) -> str | None:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(loaded, dict):
        return None
    schema_version = loaded.get("schema_version")
    return schema_version if isinstance(schema_version, str) else None


def collect_supporting_work_artifacts(round_dir: Path) -> list[dict[str, str]]:
    work = round_dir / "work"
    if not work.is_dir():
        return []

    paths: list[Path] = []
    for rel_path in EXPLICIT_WORK_ARTIFACTS:
        path = round_dir / rel_path
        if path.is_file():
            paths.append(path)
    for pattern in WORK_ARTIFACT_GLOBS:
        paths.extend(path for path in sorted(round_dir.glob(pattern)) if path.is_file())

    github_intake = work / "github-intake"
    if github_intake.is_dir():
        paths.extend(path for path in sorted(github_intake.rglob("*")) if path.is_file())

    seen: set[str] = set()
    records: list[dict[str, str]] = []
    for path in sorted(paths):
        rel_path = round_relative(round_dir, path)
        if rel_path in seen:
            continue
        seen.add(rel_path)
        records.append(work_artifact_record(round_dir, path))
    return records


def validate_supporting_work_artifacts(
    records: Any,
    round_dir: Path,
    *,
    case_id: str | None = None,
    round_id: str | None = None,
) -> list[str]:
    if not isinstance(records, list):
        return []
    errors: list[str] = []
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            continue
        rel_path = record.get("path")
        if not isinstance(rel_path, str):
            continue
        if not is_safe_round_relative_path(rel_path):
            errors.append(f"supporting_work_artifacts item {index}: path must be relative inside the round")
            continue
        path = round_dir / rel_path
        if not path.is_file():
            errors.append(f"supporting_work_artifacts item {index}: referenced file is missing: {rel_path}")
            continue
        recorded_hash = record.get("artifact_sha256")
        if not isinstance(recorded_hash, str) or not SHA256_RE.fullmatch(recorded_hash):
            errors.append(f"supporting_work_artifacts item {index}: artifact_sha256 must be a 64-character hex string")
        elif recorded_hash != sha256_file(path):
            errors.append(f"supporting_work_artifacts item {index}: artifact_sha256 is stale for {rel_path}")
        expected_schemas = KNOWN_JSON_ARTIFACT_SCHEMAS.get(rel_path)
        if expected_schemas:
            validate_json_work_artifact(path, rel_path, expected_schemas, round_dir, case_id, round_id, errors)
    return errors


def validate_json_work_artifact(
    path: Path,
    rel_path: str,
    expected_schemas: set[str],
    round_dir: Path,
    case_id: str | None,
    round_id: str | None,
    errors: list[str],
) -> None:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{rel_path}: invalid JSON: {exc.msg}")
        return
    if not isinstance(loaded, dict):
        errors.append(f"{rel_path}: JSON work artifact must be an object")
        return
    schema_version = loaded.get("schema_version")
    if schema_version not in expected_schemas:
        expected = ", ".join(sorted(expected_schemas))
        errors.append(f"{rel_path}: schema_version must be {expected}")
    if case_id is not None and loaded.get("case_id") != case_id:
        errors.append(f"{rel_path}: case_id does not match requested case")
    if round_id is not None and loaded.get("round_id") != round_id:
        errors.append(f"{rel_path}: round_id does not match requested round")
    for field in ("generated_at",):
        if not isinstance(loaded.get(field), str) or not loaded[field]:
            errors.append(f"{rel_path}: missing {field}")
    for field, expected_type in JSON_ARTIFACT_REQUIRED_FIELDS.get(rel_path, {}).items():
        if not isinstance(loaded.get(field), expected_type):
            errors.append(f"{rel_path}: {field} must be {expected_type.__name__}")
    if rel_path in STRUCTURED_EVIDENCE_SCHEMAS:
        errors.extend(
            validate_structured_evidence_payload(
                loaded,
                rel_path,
                round_dir=round_dir,
                case_id=case_id,
                round_id=round_id,
            )
        )
