"""Cheap non-executing metadata for media and executable artifacts."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

from thesis_review_workflow.artifact_classification import EXECUTABLE_SUFFIXES, MEDIA_SUFFIXES

DETERMINISTIC_ARTIFACT_METADATA_SCHEMA = "deterministic-artifact-metadata-v1"


def structural_metadata_for_artifact(
    *,
    path_ref: str,
    artifact_class: str,
    size_bytes: int | None,
    sha256: str | None,
) -> dict[str, Any] | None:
    suffix = PurePosixPath(path_ref).suffix.lower()
    if artifact_class == "media_artifact":
        category = "media"
    elif artifact_class == "executable_artifact":
        category = "executable"
    elif suffix in MEDIA_SUFFIXES:
        category = "media"
    elif suffix in EXECUTABLE_SUFFIXES:
        category = "executable"
    else:
        return None

    record: dict[str, Any] = {
        "schema_version": DETERMINISTIC_ARTIFACT_METADATA_SCHEMA,
        "artifact_category": category,
        "extension": suffix,
        "metadata_mode": "non_executing_structural_metadata",
        "content_inspection": "not_performed",
        "semantic_observation": "not_performed",
        "execution_state": "not_run",
        "stream_metadata_state": "not_collected",
    }
    if isinstance(size_bytes, int):
        record["size_bytes"] = size_bytes
    if sha256:
        record["sha256"] = sha256
    else:
        record["sha256_state"] = "not_collected_due_to_inventory_limit"
    return record
