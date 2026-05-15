"""Pure orchestration contracts for optimized thesis review rounds."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from thesis_review_workflow import agent_coverage
from thesis_review_workflow.paths import is_safe_round_relative_path
from thesis_review_workflow.review_materiality import (
    profile_index_rel,
    role_file_for_profile,
    unresolved_required_next_actions,
)
from thesis_review_workflow.review_packets import (
    COMMON_BRIEFING_REL,
    REUSE_INDEX_REL,
    PacketRole,
    has_code_evidence,
    rel_status,
    role_is_active,
    sha256_file,
)
from thesis_review_workflow.review_profiles import WorkflowReviewProfile, get_workflow_review_profile

REVIEW_RUN_TRACE_SCHEMA = "review-run-trace-v1"
REVIEW_ROLE_PLAN_SCHEMA = "review-role-plan-v1"
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
REVIEW_ROLE_PLAN_REL = "work/review_role_plan.json"
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
ROLE_PLAN_STATES = {
    "required_fresh",
    "delta_review",
    "reusable_current",
    "blocked_with_typed_limitation",
    "not_material",
}
ROLE_PLAN_CLOSEOUT_REQUIRED_STATES = {"required_fresh", "delta_review"}
REUSE_UNCHANGED_REUSABLE = "unchanged_reusable"
REUSE_CHANGED_DELTA_REQUIRED = "changed_delta_required"
REUSE_CURRENT_REVIEWED_ARTIFACT = "current_reviewed_artifact"
ROLE_PLAN_MAX_CONCURRENCY = 2


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


def packet_contract_for_profile(profile_id: str) -> tuple[tuple[PacketRole, ...], str, str]:
    profile = get_workflow_review_profile(profile_id)
    workflow = profile.effective_wave_workflow
    if workflow == "supervisor_feedback":
        from thesis_review_workflow import supervisor_packets

        return (
            supervisor_packets.PACKET_ROLES,
            supervisor_packets.PACKET_DIR_REL.as_posix(),
            ("prepare-supervisor-packets"),
        )
    if workflow == "supervisor_report":
        from thesis_review_workflow import supervisor_report_packets

        return (
            supervisor_report_packets.PACKET_ROLES,
            supervisor_report_packets.PACKET_DIR_REL.as_posix(),
            "prepare-supervisor-report-packets",
        )
    if workflow in {"opponent_materials", "opponent_report", "opponent_report_review"}:
        from thesis_review_workflow import opponent_packets

        return opponent_packets.PACKET_ROLES, opponent_packets.PACKET_DIR_REL.as_posix(), "prepare-opponent-packets"
    raise ValueError(f"{profile.profile_id}: no packet contract for wave workflow {workflow!r}")


def build_review_role_plan_payload(
    *,
    case_id: str,
    round_id: str,
    profile_id: str,
    generated_at: str,
    round_dir: Path,
) -> dict[str, Any]:
    profile = get_workflow_review_profile(profile_id)
    packet_roles, packet_dir, packet_command = packet_contract_for_profile(profile_id)
    role_records = [
        role_plan_record(
            role,
            round_dir=round_dir,
            case_id=case_id,
            round_id=round_id,
            profile=profile,
            packet_dir=packet_dir,
        )
        for role in packet_roles
    ]
    code_contract = code_bearing_contract(profile, round_dir, role_records)
    materiality_next_actions, materiality_errors = materiality_next_action_records(
        round_dir,
        case_id=case_id,
        round_id=round_id,
        profile=profile,
    )
    payload = {
        "schema_version": REVIEW_ROLE_PLAN_SCHEMA,
        "case_id": case_id,
        "round_id": round_id,
        "profile_id": profile.profile_id,
        "workflow_profile": profile.workflow_profile,
        "materiality_profile": profile.effective_materiality_profile,
        "operator_surface": profile.operator_surface,
        "final_artifact": profile.final_artifact,
        "approval_record": profile.approval_record,
        "generated_at": generated_at,
        "role_plan_path": REVIEW_ROLE_PLAN_REL,
        "packet_command": packet_command,
        "packet_dir": packet_dir,
        "common_briefing": COMMON_BRIEFING_REL,
        "source_contracts": source_contract_records(round_dir, case_id=case_id, round_id=round_id, profile=profile),
        "role_states": role_records,
        "wave_schedule": wave_schedule(role_records),
        "code_bearing_contract": code_contract,
        "materiality_next_actions": materiality_next_actions,
        "materiality_errors": materiality_errors,
        "advisory_static_analysis": advisory_static_analysis_state(round_dir),
    }
    errors = validate_review_role_plan_payload(payload, round_dir=round_dir)
    if errors:
        raise ValueError("; ".join(errors))
    return payload


def role_plan_record(
    role: PacketRole,
    *,
    round_dir: Path,
    case_id: str,
    round_id: str,
    profile: WorkflowReviewProfile,
    packet_dir: str,
) -> dict[str, Any]:
    active = role_is_active(round_dir, role, case_id=case_id, round_id=round_id)
    reuse_projection = reuse_projection_for_role(round_dir, role.key)
    coverage_role = coverage_role_for_packet_role(profile, role)
    coverage_projection = agent_coverage_projection_for_role(round_dir, coverage_role)
    materiality_projection = materiality_projection_for_role(round_dir, role.key, profile=profile)
    state = role_plan_state(
        active=active,
        role=role,
        reuse_projection=reuse_projection,
        agent_coverage_projection=coverage_projection,
        materiality_projection=materiality_projection,
    )
    packet_path = f"{packet_dir}/{role.key}.md"
    record: dict[str, Any] = {
        "role": role.key,
        "coverage_role": coverage_role,
        "title": role.title,
        "skill": role.skill,
        "state": state,
        "activation": role.activation,
        "expected_output": role.expected_output,
        "registration_preset": registration_preset_for_role(role),
        "packet_path": packet_path,
        "packet_status": "present" if (round_dir / packet_path).is_file() else "missing",
        "output_status": output_status(round_dir, role.expected_output, case_id=case_id, round_id=round_id),
        "role_inputs": [
            role_input_record(round_dir, rel_path, case_id=case_id, round_id=round_id) for rel_path in role.role_inputs
        ],
        "reuse_projection": reuse_projection,
        "agent_coverage_projection": coverage_projection,
        "materiality_projection": materiality_projection,
        "materiality_profile": profile.effective_materiality_profile,
        "open_full_artifact_triggers": [
            "missing_anchor",
            "contradiction",
            "p0_p1_verification",
            "grade_impact",
            "reviewer_challenge",
        ],
    }
    if role.key == "code_quality":
        record["advisory_static_analysis_state"] = advisory_static_analysis_state(round_dir)["state"]
    return record


def role_plan_state(
    *,
    active: bool,
    role: PacketRole,
    reuse_projection: dict[str, Any],
    agent_coverage_projection: dict[str, Any],
    materiality_projection: dict[str, Any],
) -> str:
    if agent_coverage_projection.get("status") == "blocked":
        return "blocked_with_typed_limitation"
    if materiality_projection.get("coverage_state") == "typed_limitation":
        return "blocked_with_typed_limitation"
    if not active:
        return "not_material"
    if materiality_projection.get("recommendation") == "not_material":
        return "not_material"
    if role.key in {"code_consistency", "code_quality"}:
        if (
            agent_coverage_projection.get("fresh_review_required") is False
            and agent_coverage_projection.get("coverage_satisfied_by") == REUSE_CURRENT_REVIEWED_ARTIFACT
        ):
            return "reusable_current"
        status = reuse_projection.get("reuse_status")
        if (
            status == REUSE_UNCHANGED_REUSABLE
            and reuse_projection.get("fresh_review_required") is False
            and reuse_projection.get("coverage_satisfied_by") == REUSE_CURRENT_REVIEWED_ARTIFACT
        ):
            return "reusable_current"
        if status == REUSE_CHANGED_DELTA_REQUIRED:
            return "delta_review"
    return "required_fresh"


def coverage_role_for_packet_role(profile: WorkflowReviewProfile, role: PacketRole) -> str:
    if role.key in {"final_review", "report_review"}:
        return profile.final_review_role
    if role.key == "materials_review":
        return "opponent_materials_review"
    if role.key == "trace":
        return "supervisor_report_trace"
    if role.key == "report_trace":
        return "opponent_report_trace"
    return role.key


def registration_preset_for_role(role: PacketRole) -> str:
    first_path = role.expected_output.split(" and ", 1)[0]
    if first_path.startswith("outputs/") or first_path.startswith("work/"):
        return first_path
    return ""


def output_status(round_dir: Path, expected_output: str, *, case_id: str, round_id: str) -> str:
    first_path = expected_output.split(" and ", 1)[0]
    if not is_safe_round_relative_path(first_path):
        return "invalid_artifact"
    status = rel_status(round_dir, first_path, case_id=case_id, round_id=round_id)
    if status == "missing":
        return "missing_artifact"
    if status == "invalid":
        return "invalid_artifact"
    return "present_but_not_standalone_reviewed"


def role_input_record(round_dir: Path, rel_path: str, *, case_id: str, round_id: str) -> dict[str, str]:
    record = {"path": rel_path, "status": "invalid_artifact"}
    if is_safe_round_relative_path(rel_path):
        status = rel_status(round_dir, rel_path, case_id=case_id, round_id=round_id)
        record["status"] = (
            "missing_artifact" if status == "missing" else "invalid_artifact" if status == "invalid" else status
        )
        digest = sha256_file(round_dir / rel_path)
        if digest:
            record["sha256"] = digest
    return record


def reuse_projection_for_role(round_dir: Path, role: str) -> dict[str, Any]:
    path = round_dir / REUSE_INDEX_REL
    projection: dict[str, Any] = {
        "reuse_index_path": REUSE_INDEX_REL,
        "reuse_status": "",
        "fresh_review_required": True,
        "coverage_satisfied_by": "fresh_role_review",
        "reuse_next_action": "",
    }
    if role not in {"code_consistency", "code_quality"} or not path.is_file():
        return projection
    try:
        loaded = _load_json_object(path)
    except ValueError as exc:
        projection["error"] = str(exc)
        return projection
    artifact_role = "code_consistency" if role == "code_consistency" else "code_quality"
    decisions = loaded.get("decisions")
    if not isinstance(decisions, list):
        projection["error"] = "reuse index decisions must be a list"
        return projection
    for item in decisions:
        if isinstance(item, dict) and item.get("artifact_role") == artifact_role:
            projection["reuse_status"] = str(item.get("status", ""))
            projection["fresh_review_required"] = item.get("fresh_semantic_review_required", True)
            projection["coverage_satisfied_by"] = str(item.get("coverage_satisfied_by", ""))
            projection["reuse_next_action"] = str(item.get("next_action", ""))
            break
    return projection


def materiality_projection_for_role(
    round_dir: Path,
    role: str,
    *,
    profile: WorkflowReviewProfile,
) -> dict[str, Any]:
    materiality_profile = profile.effective_materiality_profile
    projection: dict[str, Any] = {
        "materiality_profile": materiality_profile or "",
        "decision_path": "",
        "recommendation": "",
        "coverage_required": "",
        "fresh_review_required": "",
        "coverage_satisfied_by": "",
        "coverage_state": "",
    }
    if materiality_profile is None:
        return projection
    rel_path = role_file_for_profile(role, materiality_profile)
    if rel_path is None:
        rel_path = profile_index_rel(materiality_profile)
    projection["decision_path"] = rel_path.as_posix()
    path = round_dir / rel_path
    if not path.is_file():
        return projection
    try:
        loaded = _load_json_object(path)
    except ValueError as exc:
        projection["error"] = str(exc)
        return projection
    if loaded.get("schema_version") == "review-materiality-index-v1":
        decisions = loaded.get("decisions")
        if isinstance(decisions, list):
            for decision in decisions:
                if isinstance(decision, dict) and decision.get("role") == role:
                    loaded = decision
                    break
    for field in (
        "recommendation",
        "coverage_satisfied_by",
        "coverage_state",
        "scope",
        "impact",
        "reason",
    ):
        value = loaded.get(field)
        if isinstance(value, str):
            projection[field] = value
    for field in ("coverage_required", "fresh_review_required"):
        value = loaded.get(field)
        if isinstance(value, bool):
            projection[field] = value
    return projection


def agent_coverage_projection_for_role(round_dir: Path, role: str) -> dict[str, Any]:
    path = round_dir / "work" / "agent_coverage.json"
    if not path.is_file():
        return {"coverage_path": "work/agent_coverage.json", "status": "missing"}
    try:
        loaded = _load_json_object(path)
    except ValueError as exc:
        return {"coverage_path": "work/agent_coverage.json", "status": "invalid", "error": str(exc)}
    roles = loaded.get("roles")
    if not isinstance(roles, list):
        return {"coverage_path": "work/agent_coverage.json", "status": "invalid", "error": "roles must be a list"}
    for item in roles:
        if isinstance(item, dict) and item.get("role") == role:
            projection: dict[str, Any] = {
                "coverage_path": "work/agent_coverage.json",
                "status": str(item.get("status", "")),
                "coverage_satisfied_by": str(item.get("coverage_satisfied_by", "")),
                "fresh_review_required": item.get("fresh_review_required", ""),
                "reuse_status": str(item.get("reuse_status", "")),
                "reuse_next_action": str(item.get("reuse_next_action", "")),
            }
            output_evidence = item.get("output_evidence")
            if isinstance(output_evidence, list):
                projection["output_evidence"] = [ref for ref in output_evidence if isinstance(ref, str)]
            typed_limitation = item.get("typed_limitation")
            if isinstance(typed_limitation, dict):
                projection["typed_limitation"] = typed_limitation
            return projection
    return {"coverage_path": "work/agent_coverage.json", "status": "not_recorded"}


def source_contract_records(
    round_dir: Path,
    *,
    case_id: str,
    round_id: str,
    profile: WorkflowReviewProfile,
) -> list[dict[str, str]]:
    refs = [
        "work/current_evidence_snapshot.json",
        REUSE_INDEX_REL,
        "work/agent_coverage.json",
        (
            f"work/review_materiality/{profile.effective_materiality_profile}/index.json"
            if profile.effective_materiality_profile
            else ""
        ),
        COMMON_BRIEFING_REL,
    ]
    records: list[dict[str, str]] = []
    for rel_path in refs:
        if not rel_path:
            continue
        records.append(role_input_record(round_dir, rel_path, case_id=case_id, round_id=round_id))
    return records


def code_bearing_contract(
    profile: WorkflowReviewProfile,
    round_dir: Path,
    role_records: list[dict[str, Any]],
) -> dict[str, Any]:
    manifest = role_plan_manifest_projection(round_dir)
    code_present = has_code_evidence(round_dir) or agent_coverage.code_evidence_present(round_dir, manifest)
    applies = profile.profile_id in {
        "supervisor_feedback",
        "supervisor_report",
        "opponent_review",
        "opponent_materials",
    }
    code_roles = {
        record["role"]: record for record in role_records if record.get("role") in set(profile.code_bearing_roles)
    }
    satisfied_roles = [
        role
        for role, record in sorted(code_roles.items())
        if record.get("state")
        in {"required_fresh", "delta_review", "reusable_current", "blocked_with_typed_limitation"}
    ]
    return {
        "applies": applies,
        "code_evidence_present": code_present,
        "source": "prepared_workspace_or_manifest_projection",
        "required_roles": list(profile.code_bearing_roles) if applies and code_present else [],
        "satisfied_roles": satisfied_roles if applies and code_present else [],
        "status": (
            "satisfied"
            if (not applies or not code_present or set(satisfied_roles) >= set(profile.code_bearing_roles))
            else "blocked"
        ),
    }


def role_plan_manifest_projection(round_dir: Path) -> dict[str, Any]:
    manifest_path = round_dir / "work" / "review_manifest.json"
    if manifest_path.is_file():
        try:
            return _load_json_object(manifest_path)
        except ValueError:
            return {}
    inputs: list[dict[str, str]] = []
    inputs_dir = round_dir / "inputs"
    if inputs_dir.is_dir():
        for path in sorted(inputs_dir.iterdir()):
            if path.is_file() or path.is_dir():
                rel_path = path.relative_to(round_dir).as_posix()
                kind = "archive" if path.is_file() and path.suffix.lower() in {".zip", ".7z", ".rar"} else "input"
                inputs.append({"path": rel_path, "kind": kind})
    return {"inputs": inputs, "supporting_work_artifacts": [], "artifacts": []}


def materiality_next_action_records(
    round_dir: Path,
    *,
    case_id: str,
    round_id: str,
    profile: WorkflowReviewProfile,
) -> tuple[list[dict[str, Any]], list[str]]:
    materiality_profile = profile.effective_materiality_profile
    if materiality_profile is None:
        return [], []
    actions, errors = unresolved_required_next_actions(
        round_dir,
        workflow_profile=materiality_profile,
        case_id=case_id,
        round_id=round_id,
    )
    records: list[dict[str, Any]] = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        required_path = str(action.get("required_artifact_path", ""))
        status = artifact_next_action_state(
            round_dir,
            required_path,
            case_id=case_id,
            round_id=round_id,
            action=action,
        )
        records.append(
            {
                "role": str(action.get("role", "")),
                "status": str(action.get("status", "")),
                "next_action_state": status,
                "required_artifact_path": required_path,
                "command": str(action.get("command", "")),
                "skill": str(action.get("skill", "")),
            }
        )
    return records, errors


def artifact_next_action_state(
    round_dir: Path,
    rel_path: str,
    *,
    case_id: str,
    round_id: str,
    action: dict[str, Any] | None = None,
) -> str:
    if not is_safe_round_relative_path(rel_path):
        return "invalid_artifact"
    status = rel_status(round_dir, rel_path, case_id=case_id, round_id=round_id)
    if status == "missing":
        return "missing_artifact"
    if status == "invalid":
        return "invalid_artifact"
    action_text = materiality_action_text(action)
    if any(marker in action_text for marker in ("invalid", "validation", "cannot read", "missing required")):
        return "invalid_artifact"
    if any(marker in action_text for marker in ("synthesis-covered", "synthesis covered", "covered by")):
        return "present_but_not_synthesis_covered"
    return "present_but_not_standalone_reviewed"


def materiality_action_text(action: dict[str, Any] | None) -> str:
    if action is None:
        return ""
    parts: list[str] = []
    for field in ("reason", "command", "skill"):
        value = action.get(field)
        if isinstance(value, str):
            parts.append(value)
    limitations = action.get("limitations")
    if isinstance(limitations, list):
        parts.extend(item for item in limitations if isinstance(item, str))
    return " ".join(parts).lower()


def advisory_static_analysis_state(round_dir: Path) -> dict[str, str]:
    candidates = ("work/code_quality_omen.json", "work/code_quality_omen.md")
    present = [rel_path for rel_path in candidates if (round_dir / rel_path).is_file()]
    if not present:
        return {
            "tool": "omen",
            "state": "tool_unavailable",
            "reason": "no Omen advisory output is present; code-quality review must record this as a limitation",
        }
    non_empty = [rel_path for rel_path in present if (round_dir / rel_path).stat().st_size > 0]
    if not non_empty:
        return {"tool": "omen", "state": "available_no_findings", "reason": "Omen output files are empty"}
    if any((round_dir / rel_path).suffix == ".json" for rel_path in non_empty):
        return {"tool": "omen", "state": "available_with_findings", "reason": "Omen JSON output is present"}
    return {"tool": "omen", "state": "unsupported_or_uninformative", "reason": "only unstructured Omen text is present"}


def wave_schedule(role_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scheduled = [record for record in role_records if record.get("state") in {"required_fresh", "delta_review"}]
    buckets: dict[str, list[str]] = {}
    for record in scheduled:
        buckets.setdefault(wave_group(str(record["role"])), []).append(str(record["role"]))
    schedule: list[dict[str, Any]] = []
    for group in ("evidence_1", "evidence_2", "calibration", "synthesis", "independent_review"):
        roles = buckets.get(group, [])
        for index in range(0, len(roles), ROLE_PLAN_MAX_CONCURRENCY):
            chunk = roles[index : index + ROLE_PLAN_MAX_CONCURRENCY]
            schedule.append(
                {
                    "wave_id": f"{group}_{index // ROLE_PLAN_MAX_CONCURRENCY + 1}",
                    "max_concurrent_agents": ROLE_PLAN_MAX_CONCURRENCY,
                    "roles": chunk,
                }
            )
    return schedule


def wave_group(role: str) -> str:
    if role in {"text_assignment", "text_structure_assignment", "trace", "code_consistency"}:
        return "evidence_1"
    if role in {
        "code_quality",
        "figure_media",
        "literature_citation",
        "typography_formal",
        "quantitative_claims",
        "theses_similarity",
        "current_evidence_snapshot",
        "github_intake",
    }:
        return "evidence_2"
    if role in {"evidence_calibration"}:
        return "calibration"
    if role in {"synthesis", "report_trace"}:
        return "synthesis"
    return "independent_review"


def validate_review_role_plan_payload(payload: dict[str, Any], *, round_dir: Path | None = None) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != REVIEW_ROLE_PLAN_SCHEMA:
        errors.append(f"schema_version must be {REVIEW_ROLE_PLAN_SCHEMA}")
    for field in ("case_id", "round_id", "profile_id", "workflow_profile", "operator_surface", "generated_at"):
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{field} must be a non-empty string")
    if payload.get("role_plan_path") != REVIEW_ROLE_PLAN_REL:
        errors.append(f"role_plan_path must be {REVIEW_ROLE_PLAN_REL}")
    for field in ("final_artifact", "approval_record", "packet_dir", "common_briefing"):
        value = payload.get(field)
        if not isinstance(value, str) or not is_safe_round_relative_path(value):
            errors.append(f"{field} must be a safe round-relative path")
    roles = payload.get("role_states")
    if not isinstance(roles, list) or not roles:
        errors.append("role_states must be a non-empty list")
    elif round_dir is not None:
        for index, role in enumerate(roles, start=1):
            _validate_role_plan_record(role, f"role_states[{index}]", errors)
    waves = payload.get("wave_schedule")
    if not isinstance(waves, list):
        errors.append("wave_schedule must be a list")
    else:
        for index, wave in enumerate(waves, start=1):
            if not isinstance(wave, dict):
                errors.append(f"wave_schedule[{index}] must be an object")
                continue
            if wave.get("max_concurrent_agents") != ROLE_PLAN_MAX_CONCURRENCY:
                errors.append(f"wave_schedule[{index}].max_concurrent_agents must be {ROLE_PLAN_MAX_CONCURRENCY}")
            wave_roles = wave.get("roles")
            if not isinstance(wave_roles, list) or len(wave_roles) > ROLE_PLAN_MAX_CONCURRENCY:
                errors.append(f"wave_schedule[{index}].roles must contain at most {ROLE_PLAN_MAX_CONCURRENCY} roles")
    contract = payload.get("code_bearing_contract")
    if isinstance(contract, dict) and contract.get("status") == "blocked":
        errors.append("code_bearing_contract is blocked")
    elif not isinstance(contract, dict):
        errors.append("code_bearing_contract must be an object")
    return errors


def closeout_wave_for_profile(profile_id: str) -> tuple[str, str]:
    profile = get_workflow_review_profile(profile_id)
    if profile.effective_wave_workflow == "opponent_materials":
        return profile.effective_wave_workflow, "reviewed"
    return profile.effective_wave_workflow, "final"


def load_review_role_plan(round_dir: Path) -> dict[str, Any] | None:
    path = round_dir / REVIEW_ROLE_PLAN_REL
    if not path.is_file():
        return None
    return _load_json_object(path)


def validate_role_plan_for_closeout(
    payload: dict[str, Any] | None,
    *,
    round_dir: Path,
    case_id: str,
    round_id: str,
    profile_id: str,
) -> list[str]:
    if payload is None:
        return [f"{REVIEW_ROLE_PLAN_REL} is missing; run prepare-review-round before closeout"]
    errors = validate_review_role_plan_payload(payload, round_dir=round_dir)
    if payload.get("case_id") != case_id:
        errors.append(f"role plan case_id must be {case_id}")
    if payload.get("round_id") != round_id:
        errors.append(f"role plan round_id must be {round_id}")
    if payload.get("profile_id") != profile_id:
        errors.append(f"role plan profile_id must be {profile_id}")

    manifest = role_plan_manifest_projection(round_dir)
    for record in payload.get("role_states", []):
        if not isinstance(record, dict):
            continue
        role = str(record.get("role", ""))
        state = str(record.get("state", ""))
        coverage_role = str(record.get("coverage_role") or role)
        coverage_projection = agent_coverage_projection_for_role(round_dir, coverage_role)
        if state in ROLE_PLAN_CLOSEOUT_REQUIRED_STATES:
            if role_output_or_limitation_present(round_dir, manifest, record, coverage_projection):
                continue
            expected = str(record.get("registration_preset") or record.get("expected_output") or "").split(" and ", 1)[
                0
            ]
            errors.append(
                f"{role}: role plan state {state} requires current output or typed limitation; "
                f"expected {expected or 'registered role output'}"
            )
        elif state == "reusable_current":
            if coverage_projection.get("coverage_satisfied_by") != REUSE_CURRENT_REVIEWED_ARTIFACT:
                errors.append(
                    f"{role}: reusable_current requires current reviewed coverage in work/agent_coverage.json"
                )
        elif state == "blocked_with_typed_limitation":
            if not typed_limitation_present(record, coverage_projection):
                errors.append(f"{role}: blocked_with_typed_limitation requires a concrete typed limitation")
    return errors


def role_output_or_limitation_present(
    round_dir: Path,
    manifest: dict[str, Any],
    record: dict[str, Any],
    coverage_projection: dict[str, Any],
) -> bool:
    if typed_limitation_present(record, coverage_projection):
        return True
    refs: list[str] = []
    output_evidence = coverage_projection.get("output_evidence")
    if isinstance(output_evidence, list):
        refs.extend(ref for ref in output_evidence if isinstance(ref, str))
    preset = record.get("registration_preset")
    if isinstance(preset, str) and preset:
        refs.append(preset)
    expected = record.get("expected_output")
    if isinstance(expected, str) and expected:
        refs.append(expected.split(" and ", 1)[0])
    return any(role_output_ref_registered_current(round_dir, manifest, ref, coverage_projection) for ref in refs)


def role_output_ref_registered_current(
    round_dir: Path,
    manifest: dict[str, Any],
    rel_path: str,
    coverage_projection: dict[str, Any],
) -> bool:
    if not is_safe_round_relative_path(rel_path) or not (round_dir / rel_path).is_file():
        return False
    if rel_path in coverage_projection.get("output_evidence", []):
        return True
    record = manifest_record_for_path(manifest, rel_path)
    if record is None:
        return False
    recorded_hash = record.get("artifact_sha256")
    current_hash = sha256_file(round_dir / rel_path)
    if not isinstance(recorded_hash, str) or not current_hash or recorded_hash != current_hash:
        return False
    generated = record.get("generated_by")
    if isinstance(generated, list) and any(isinstance(item, dict) for item in generated):
        return True
    role = str(record.get("role", "")).strip()
    agent = str(record.get("agent", "")).strip()
    if role and role != "not_recorded" and agent and agent != "not_recorded":
        return True
    producer_role = str(record.get("producer_role", "")).strip()
    producer_agent = str(record.get("producer_agent", "")).strip()
    return bool(producer_role and producer_agent)


def manifest_record_for_path(manifest: dict[str, Any], rel_path: str) -> dict[str, Any] | None:
    for collection in ("artifacts", "supporting_work_artifacts"):
        records = manifest.get(collection)
        if not isinstance(records, list):
            continue
        for record in records:
            if isinstance(record, dict) and record.get("path") == rel_path:
                return record
    return None


def typed_limitation_present(record: dict[str, Any], coverage_projection: dict[str, Any]) -> bool:
    materiality = record.get("materiality_projection")
    if isinstance(materiality, dict) and materiality.get("coverage_state") == "typed_limitation":
        return True
    limitation = coverage_projection.get("typed_limitation")
    if not isinstance(limitation, dict):
        return False
    return bool(str(limitation.get("type", "")).strip() and str(limitation.get("description", "")).strip())


def _validate_role_plan_record(record: object, prefix: str, errors: list[str]) -> None:
    if not isinstance(record, dict):
        errors.append(f"{prefix} must be an object")
        return
    if record.get("state") not in ROLE_PLAN_STATES:
        errors.append(f"{prefix}.state must be one of {sorted(ROLE_PLAN_STATES)}")
    for field in ("expected_output", "packet_path"):
        value = record.get(field)
        if not isinstance(value, str):
            errors.append(f"{prefix}.{field} must be string")
            continue
        first_path = value.split(" and ", 1)[0]
        if not is_safe_round_relative_path(first_path):
            errors.append(f"{prefix}.{field} must start with a safe round-relative path")


def _load_json_object(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"{path.name} must be a JSON object")
    return loaded


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
