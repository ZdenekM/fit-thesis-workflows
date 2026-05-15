"""Pure orchestration contracts for optimized thesis review rounds."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
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
MATERIAL_CURRENTNESS = {"current", "newer_than_previous", "stale", "missing", "unknown"}
FRESH_CURRENTNESS = {"current", "newer_than_previous"}
MATERIAL_KINDS = {
    "thesis_pdf",
    "source_archive",
    "code_archive",
    "code_directory",
    "github_snapshot_request",
    "github_pr_url",
    "theses_similarity_report",
    "reviewed_report_draft",
    "submission_bundle",
}
BUNDLE_CLASSIFICATIONS = {"", "container_bundle", "reference_bundle"}
ROUND_START_NEXT_COMMAND = "prepare-review-round"


@dataclass(frozen=True, slots=True)
class RoundMaterialDescriptor:
    kind: str
    path: str = ""
    url: str = ""
    currentness: str = "current"
    bundle_classification: str = ""
    decomposed_authoritative_refs: tuple[str, ...] = ()
    note: str = ""

    @property
    def ref(self) -> str:
        return self.path or self.url

    @property
    def is_current(self) -> bool:
        return self.currentness in FRESH_CURRENTNESS

    @property
    def is_bundle_container(self) -> bool:
        return self.bundle_classification in {"container_bundle", "reference_bundle"}

    @property
    def code_relevant(self) -> bool:
        return self.kind in {"code_archive", "code_directory", "github_snapshot_request", "github_pr_url"}


@dataclass(frozen=True, slots=True)
class RoundStartAction:
    action_id: str
    command: str
    reason: str
    material_refs: tuple[str, ...] = ()
    target_refs: tuple[str, ...] = ()

    def to_json(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "command": self.command,
            "reason": self.reason,
            "material_refs": list(self.material_refs),
            "target_refs": list(self.target_refs),
        }


@dataclass(frozen=True, slots=True)
class RoundStartDiagnostic:
    code: str
    severity: str
    message: str
    material_refs: tuple[str, ...] = ()

    def to_json(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "material_refs": list(self.material_refs),
        }


@dataclass(frozen=True, slots=True)
class RoundStartBlocker:
    code: str
    message: str
    material_refs: tuple[str, ...] = ()

    def to_json(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "material_refs": list(self.material_refs),
        }


@dataclass(frozen=True, slots=True)
class RoundStartPlan:
    case_id: str
    round_id: str
    profile_id: str
    workflow_profile: str
    materiality_profile: str | None
    final_artifact: str
    readiness_gates: tuple[str, ...]
    actions: tuple[RoundStartAction, ...]
    diagnostics: tuple[RoundStartDiagnostic, ...]
    blockers: tuple[RoundStartBlocker, ...]
    next_command: str = ROUND_START_NEXT_COMMAND

    @property
    def ok(self) -> bool:
        return not self.blockers

    def to_json(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "round_id": self.round_id,
            "profile_id": self.profile_id,
            "workflow_profile": self.workflow_profile,
            "materiality_profile": self.materiality_profile,
            "final_artifact": self.final_artifact,
            "readiness_gates": list(self.readiness_gates),
            "actions": [action.to_json() for action in self.actions],
            "diagnostics": [diagnostic.to_json() for diagnostic in self.diagnostics],
            "blockers": [blocker.to_json() for blocker in self.blockers],
            "next_command": self.next_command,
        }


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


def plan_review_round_start(
    *,
    case_id: str,
    round_id: str,
    profile_id: str,
    materials: tuple[RoundMaterialDescriptor, ...] = (),
    fresh_materials_expected: bool = False,
    provisional_stale_review: bool = False,
    metadata_fields: dict[str, str] | None = None,
) -> RoundStartPlan:
    profile = get_workflow_review_profile(profile_id)
    diagnostics: list[RoundStartDiagnostic] = []
    blockers: list[RoundStartBlocker] = []
    _, metadata_diagnostics = normalize_metadata_fields(metadata_fields or {})
    diagnostics.extend(metadata_diagnostics)

    for material in materials:
        errors = validate_round_material_descriptor(material)
        if errors:
            blockers.extend(
                RoundStartBlocker("invalid_material_descriptor", error, (material.ref,) if material.ref else ())
                for error in errors
            )

    fresh_refs = tuple(material.ref for material in materials if material.ref and material.is_current)
    if fresh_materials_expected and not fresh_refs:
        stale_refs = tuple(material.ref for material in materials if material.ref)
        if provisional_stale_review:
            diagnostics.append(
                RoundStartDiagnostic(
                    "provisional_stale_review",
                    "warning",
                    "fresh materials were expected, but no descriptor is marked current or newer_than_previous",
                    stale_refs,
                )
            )
        else:
            blockers.append(
                RoundStartBlocker(
                    "fresh_materials_missing",
                    "fresh_materials_expected=true requires at least one current or newer material descriptor",
                    stale_refs,
                )
            )

    actions = list(round_start_actions(profile, materials))
    if blockers:
        actions = [action for action in actions if action.action_id in {"classify_bundle", "normalize_metadata"}]
    return RoundStartPlan(
        case_id=case_id,
        round_id=round_id,
        profile_id=profile.profile_id,
        workflow_profile=profile.workflow_profile,
        materiality_profile=profile.effective_materiality_profile,
        final_artifact=profile.final_artifact,
        readiness_gates=profile.readiness_gates,
        actions=tuple(actions),
        diagnostics=tuple(diagnostics),
        blockers=tuple(blockers),
    )


def validate_round_material_descriptor(material: RoundMaterialDescriptor) -> list[str]:
    errors: list[str] = []
    if material.kind not in MATERIAL_KINDS:
        errors.append(f"{material.ref or material.kind}: unknown material kind {material.kind!r}")
    if material.currentness not in MATERIAL_CURRENTNESS:
        errors.append(f"{material.ref or material.kind}: currentness must be one of {sorted(MATERIAL_CURRENTNESS)}")
    if material.bundle_classification not in BUNDLE_CLASSIFICATIONS:
        errors.append(
            f"{material.ref or material.kind}: bundle_classification must be one of {sorted(BUNDLE_CLASSIFICATIONS)}"
        )
    if not material.path and not material.url:
        errors.append(f"{material.kind}: path or url is required")
    if material.path and not is_safe_round_relative_path(material.path):
        errors.append(f"{material.path}: path must be a safe round-relative path")
    for rel_path in material.decomposed_authoritative_refs:
        if not is_safe_round_relative_path(rel_path):
            errors.append(f"{rel_path}: decomposed authoritative ref must be a safe round-relative path")
    if material.url and material.kind not in {"github_snapshot_request", "github_pr_url"}:
        errors.append(f"{material.url}: url descriptors are supported only for GitHub material requests")
    if material.is_bundle_container and not material.decomposed_authoritative_refs:
        errors.append(f"{material.ref}: {material.bundle_classification} requires decomposed authoritative refs")
    return errors


def round_start_actions(
    profile: WorkflowReviewProfile,
    materials: tuple[RoundMaterialDescriptor, ...],
) -> tuple[RoundStartAction, ...]:
    actions: list[RoundStartAction] = []
    for material in materials:
        if material.is_bundle_container:
            actions.append(
                RoundStartAction(
                    "classify_bundle",
                    "record container_bundle/reference_bundle classification in review_run_trace",
                    "parent submission bundles are provenance inputs, not independent code submissions",
                    (material.ref,),
                    material.decomposed_authoritative_refs,
                )
            )
        if material.kind == "thesis_pdf" and material.path:
            actions.append(
                RoundStartAction(
                    "extract_pdf_text",
                    "extract-pdf-text <input-pdf> <output-text>",
                    "rendered thesis PDFs need current extracted text for downstream review",
                    (material.path,),
                    (_pdf_extract_target(material.path),),
                )
            )
        elif material.kind in {"github_snapshot_request", "github_pr_url"}:
            actions.append(
                RoundStartAction(
                    "import_github_snapshot",
                    "import-github-code <case-id> <round-id> ...",
                    "GitHub repository or PR evidence must be imported before code review roles use it",
                    (material.ref,),
                    ("inputs/github/**", "work/github/**", "outputs/github_code_intake.md"),
                )
            )
        elif material.kind in {"code_archive", "code_directory"}:
            actions.append(
                RoundStartAction(
                    "prepare_code_workspace",
                    "prepare-code-workspace <case-id> <round-id>",
                    "code evidence must be inspectable under the ignored round workspace",
                    (material.path,),
                    ("work/code_workspace.md", "work/serena_roots.json"),
                )
            )
    if profile.profile_id == "supervisor_report":
        actions.append(
            RoundStartAction(
                "ensure_profile_note",
                "copy supervisor-report operator-intake template",
                "supervisor report readiness expects the canonical note filename",
                (),
                ("notes/supervisor-report-operator-input.md",),
            )
        )
    actions.append(
        RoundStartAction(
            "update_current_evidence",
            "update-current-evidence-snapshot <case-id> <round-id>",
            "current evidence snapshot is the shared freshness handoff",
            tuple(material.ref for material in materials if material.ref),
            ("work/current_evidence_snapshot.json",),
        )
    )
    actions.append(
        RoundStartAction(
            "update_reuse_index",
            "update-round-reuse-index <case-id> <round-id>",
            "round-start prepares reuse decisions before role planning",
            (),
            ("work/reuse/reuse_index.json",),
        )
    )
    for gate in profile.readiness_gates:
        actions.append(
            RoundStartAction(
                "run_readiness_gate",
                f"{gate} <case-id> <round-id>",
                "profile readiness must pass before role-plan preparation",
                (),
                (),
            )
        )
    actions.append(
        RoundStartAction(
            "prepare_role_plan",
            f"{ROUND_START_NEXT_COMMAND} <case-id> <round-id>",
            "round start stops at the deterministic role-plan boundary",
            (),
            ("work/review_role_plan.json",),
        )
    )
    return tuple(actions)


def normalize_metadata_fields(fields: dict[str, str]) -> tuple[dict[str, str], tuple[RoundStartDiagnostic, ...]]:
    normalized: dict[str, str] = {}
    diagnostics: list[RoundStartDiagnostic] = []
    for key, value in fields.items():
        if "\\n" in value:
            normalized[key] = value.replace("\\n", "\n")
            diagnostics.append(
                RoundStartDiagnostic(
                    "literal_escaped_newline",
                    "warning",
                    f"{key} contains literal escaped newline sequences; use a --*-file input for multiline text",
                )
            )
        else:
            normalized[key] = value
    return normalized, tuple(diagnostics)


def _pdf_extract_target(rel_path: str) -> str:
    path = Path(rel_path)
    return (Path("extracted") / f"{path.stem}.txt").as_posix()


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
