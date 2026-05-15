"""Pure orchestration contracts for optimized thesis review rounds."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from thesis_review_workflow.paths import is_safe_round_relative_path
from thesis_review_workflow.review_profiles import WorkflowReviewProfile, get_workflow_review_profile

REVIEW_RUN_TRACE_SCHEMA = "review-run-trace-v1"
TracePhase = Literal[
    "start",
    "import",
    "extraction",
    "packet_prep",
    "role_plan",
    "role_waves",
    "synthesis",
    "independent_review",
    "operator_delta",
    "manifest_refresh",
    "closeout",
]
TRACE_PHASES: tuple[str, ...] = (
    "start",
    "import",
    "extraction",
    "packet_prep",
    "role_plan",
    "role_waves",
    "synthesis",
    "independent_review",
    "operator_delta",
    "manifest_refresh",
    "closeout",
)
TRACE_STATUSES = {"planned", "started", "skipped", "blocked", "passed", "failed"}
REVIEW_RUN_TRACE_REL = "work/review_run_trace.json"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class ReviewRunTraceEvent:
    phase: TracePhase
    status: str
    command: str = ""
    started_at: str = ""
    completed_at: str = ""
    source_refs: tuple[str, ...] = ()
    output_refs: tuple[str, ...] = ()
    source_sha256: tuple[tuple[str, str], ...] = ()
    output_sha256: tuple[tuple[str, str], ...] = ()
    notes: tuple[str, ...] = ()

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "phase": self.phase,
            "status": self.status,
            "source_refs": list(self.source_refs),
            "output_refs": list(self.output_refs),
            "source_sha256": dict(self.source_sha256),
            "output_sha256": dict(self.output_sha256),
            "notes": list(self.notes),
        }
        if self.command:
            payload["command"] = self.command
        if self.started_at:
            payload["started_at"] = self.started_at
        if self.completed_at:
            payload["completed_at"] = self.completed_at
        return payload


def build_review_run_trace_payload(
    *,
    case_id: str,
    round_id: str,
    profile_id: str,
    generated_at: str,
    events: tuple[ReviewRunTraceEvent, ...],
) -> dict[str, Any]:
    profile = get_workflow_review_profile(profile_id)
    payload = {
        "schema_version": REVIEW_RUN_TRACE_SCHEMA,
        "case_id": case_id,
        "round_id": round_id,
        "profile_id": profile.profile_id,
        "workflow_profile": profile.workflow_profile,
        "materiality_profile": profile.effective_materiality_profile,
        "operator_surface": profile.operator_surface,
        "generated_at": generated_at,
        "trace_path": REVIEW_RUN_TRACE_REL,
        "events": [event.to_json() for event in events],
    }
    errors = validate_review_run_trace_payload(payload)
    if errors:
        raise ValueError("; ".join(errors))
    return payload


def trace_profile_summary(profile_id: str) -> dict[str, str | None]:
    profile: WorkflowReviewProfile = get_workflow_review_profile(profile_id)
    return {
        "profile_id": profile.profile_id,
        "workflow_profile": profile.workflow_profile,
        "materiality_profile": profile.effective_materiality_profile,
        "operator_surface": profile.operator_surface,
        "final_artifact": profile.final_artifact,
        "approval_record": profile.approval_record,
        "wave_workflow": profile.effective_wave_workflow,
    }


def validate_review_run_trace_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != REVIEW_RUN_TRACE_SCHEMA:
        errors.append(f"schema_version must be {REVIEW_RUN_TRACE_SCHEMA}")
    for field in ("case_id", "round_id", "profile_id", "workflow_profile", "operator_surface", "generated_at"):
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{field} must be a non-empty string")
    trace_path = payload.get("trace_path")
    if trace_path != REVIEW_RUN_TRACE_REL:
        errors.append(f"trace_path must be {REVIEW_RUN_TRACE_REL}")
    profile_id = payload.get("profile_id")
    if isinstance(profile_id, str) and profile_id.strip():
        try:
            profile = get_workflow_review_profile(profile_id)
        except ValueError as exc:
            errors.append(str(exc))
        else:
            if payload.get("workflow_profile") != profile.workflow_profile:
                errors.append(f"workflow_profile must be {profile.workflow_profile}")
            if payload.get("materiality_profile") != profile.effective_materiality_profile:
                errors.append(f"materiality_profile must be {profile.effective_materiality_profile}")
            if payload.get("operator_surface") != profile.operator_surface:
                errors.append(f"operator_surface must be {profile.operator_surface}")
    events = payload.get("events")
    if not isinstance(events, list):
        errors.append("events must be a list")
        return errors
    for index, event in enumerate(events, start=1):
        prefix = f"events[{index}]"
        if not isinstance(event, dict):
            errors.append(f"{prefix} must be an object")
            continue
        phase = event.get("phase")
        if phase not in TRACE_PHASES:
            errors.append(f"{prefix}.phase must be one of {sorted(TRACE_PHASES)}")
        status = event.get("status")
        if status not in TRACE_STATUSES:
            errors.append(f"{prefix}.status must be one of {sorted(TRACE_STATUSES)}")
        _validate_trace_ref_list(event, "source_refs", prefix, errors)
        _validate_trace_ref_list(event, "output_refs", prefix, errors)
        _validate_trace_hash_map(event, "source_sha256", prefix, errors)
        _validate_trace_hash_map(event, "output_sha256", prefix, errors)
    return errors


def _validate_trace_ref_list(event: dict[str, Any], field: str, prefix: str, errors: list[str]) -> None:
    value = event.get(field, [])
    if not isinstance(value, list):
        errors.append(f"{prefix}.{field} must be a list")
        return
    for item_index, rel_path in enumerate(value, start=1):
        if not isinstance(rel_path, str) or not is_safe_round_relative_path(rel_path):
            errors.append(f"{prefix}.{field}[{item_index}] must be a safe round-relative path")


def _validate_trace_hash_map(event: dict[str, Any], field: str, prefix: str, errors: list[str]) -> None:
    value = event.get(field, {})
    if not isinstance(value, dict):
        errors.append(f"{prefix}.{field} must be an object")
        return
    for rel_path, digest in value.items():
        if not isinstance(rel_path, str) or not is_safe_round_relative_path(rel_path):
            errors.append(f"{prefix}.{field} path must be a safe round-relative path")
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            errors.append(f"{prefix}.{field}[{rel_path!r}] must be a sha256 hex string")
