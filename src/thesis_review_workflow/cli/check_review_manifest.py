"""Validate a round review provenance manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from thesis_review_workflow.agent_coverage import COVERAGE_REL
from thesis_review_workflow.agent_coverage import code_evidence_present as inferred_code_evidence_present
from thesis_review_workflow.agent_coverage import coverage_required
from thesis_review_workflow.artifact_registry import (
    closeout_independent_review_required_paths,
    output_spec,
    review_basis_candidates,
)
from thesis_review_workflow.claim_review_basis import CLAIM_REVIEW_BASIS_REL, validate_claim_review_basis_payload
from thesis_review_workflow.cli.context import (
    repo_root,
    require_case_dir,
    require_round_dir,
    resolve_round,
    validate_id,
)
from thesis_review_workflow.commands import repo_command_environment, resolve_repo_command
from thesis_review_workflow.literature_source_acquisition import SOURCE_ACQUISITION_REL
from thesis_review_workflow.opponent_calibration import calibration_profile_check_targets
from thesis_review_workflow.paths import is_safe_round_relative_path
from thesis_review_workflow.report_calibration import (
    REPORT_CALIBRATION_BASIS_REL,
    report_calibration_check_required,
    report_calibration_check_targets,
    round_uses_report_calibration_basis,
)
from thesis_review_workflow.review_approvals import (
    is_review_approval_path,
    load_review_approval,
    validate_review_approval_with_manifest,
)
from thesis_review_workflow.review_manifest import claim_basis_applies_to_artifact, claim_basis_dependency_refs
from thesis_review_workflow.review_materiality import validate_materiality_workflow_limitations
from thesis_review_workflow.supervisor_report_calibration import supervisor_report_calibration_profile_check_targets
from thesis_review_workflow.theses_similarity import theses_similarity_check_targets, theses_similarity_evidence_present
from thesis_review_workflow.work_artifacts import validate_supporting_work_artifacts

ABSOLUTE_PATH_RE = re.compile(r"(?<!\w)/(?:home|Users|tmp|var|workspace|mnt)/[^\s)\"']*")
MANIFEST_REL = "work/review_manifest.json"
SCHEMA_VERSION = "review-manifest-v1"

KNOWN_REVIEW_SCOPES = {
    "sendable_final",
    "standalone_final",
    "covered_by_synthesis",
    "draft_only",
    "internal_only",
    "not_used",
}
REVIEWED_STATUSES = {"reviewed", "reviewed_with_notes"}
KNOWN_REVIEW_STATUSES = REVIEWED_STATUSES | {
    "draft",
    "not_reviewed",
    "not_recorded",
    "not_required",
    "failed",
    "exception",
}
KNOWN_CHECK_STATUSES = {"passed", "failed", "not_run", "not_recorded", "not_applicable"}
FINAL_SCOPES = {"sendable_final", "standalone_final"}
INDEPENDENT_REVIEW_REQUIRED_OUTPUTS = closeout_independent_review_required_paths()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: Path, errors: list[str]) -> dict[str, Any] | None:
    if not path.is_file():
        errors.append(f"missing review manifest: {MANIFEST_REL}")
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON in {MANIFEST_REL}: {exc.msg}")
        return None
    if not isinstance(loaded, dict):
        errors.append("review manifest must be a JSON object")
        return None
    return loaded


def is_safe_relative(value: str) -> bool:
    return is_safe_round_relative_path(value)


def validate_rel_path(
    label: str,
    value: Any,
    round_dir: Path,
    errors: list[str],
    *,
    must_exist: bool = True,
) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label}: missing path")
        return None
    if ABSOLUTE_PATH_RE.search(value) or not is_safe_relative(value):
        errors.append(f"{label}: path must be relative inside the round: {value}")
        return None
    path = round_dir / value
    if must_exist and not path.exists():
        errors.append(f"{label}: referenced path does not exist: {value}")
    return path


def records_by_path(records: Any, label: str, round_dir: Path, errors: list[str]) -> None:
    if records is None:
        return
    if not isinstance(records, list):
        errors.append(f"{label} must be a list")
        return
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            errors.append(f"{label} item {index}: expected object")
            continue
        validate_rel_path(f"{label} item {index}", record.get("path"), round_dir, errors)
        recorded_hash = record.get("artifact_sha256")
        if recorded_hash is not None and not isinstance(recorded_hash, str):
            errors.append(f"{label} item {index}: artifact_sha256 must be a string")


def record_paths(records: Any) -> set[str]:
    if not isinstance(records, list):
        return set()
    return {record["path"] for record in records if isinstance(record, dict) and isinstance(record.get("path"), str)}


def helper_check_names(records: Any) -> set[str]:
    if not isinstance(records, list):
        return set()
    return {record["check"] for record in records if isinstance(record, dict) and isinstance(record.get("check"), str)}


def check_ref_list(
    *,
    artifact_path: str,
    field: str,
    refs: Any,
    allowed_paths: set[str],
    allowed_checks: set[str],
    round_dir: Path,
    errors: list[str],
) -> None:
    location = {
        "input_refs": "manifest inputs/extracted_artifacts/notes",
        "evidence_refs": "manifest supporting_work_artifacts/artifacts",
        "handoff_refs": "manifest supporting_work_artifacts/artifacts",
    }.get(field, "manifest inputs, work, or outputs")
    if not isinstance(refs, list):
        errors.append(f"{artifact_path}: {field} must be a list")
        return
    for index, ref in enumerate(refs, start=1):
        if not isinstance(ref, str) or not ref:
            errors.append(f"{artifact_path}: {field} item {index} must be a non-empty string")
            continue
        if field == "check_refs":
            if ref not in allowed_checks:
                errors.append(f"{artifact_path}: check_refs item {index} is not a manifest helper check: {ref}")
            continue
        validate_rel_path(f"{artifact_path}: {field} item {index}", ref, round_dir, errors)
        if ref not in allowed_paths:
            errors.append(
                f"{artifact_path}: {field} item {index} is not recorded in {location}: {ref}; "
                "run init-review-manifest or register the referenced artifact before closeout"
            )


def check_source_hashes(
    artifact_path: str,
    artifact: dict[str, Any],
    refs: list[str],
    round_dir: Path,
    errors: list[str],
) -> None:
    recorded = artifact.get("source_sha256")
    if not isinstance(recorded, dict):
        errors.append(f"{artifact_path}: calibrated internal evidence requires source_sha256")
        return
    if not refs:
        errors.append(f"{artifact_path}: calibrated internal evidence requires source refs")
        return
    for ref in refs:
        path = validate_rel_path(f"{artifact_path}: source_sha256 {ref}", ref, round_dir, errors, must_exist=True)
        if path is None or not path.is_file():
            continue
        recorded_hash = recorded.get(ref)
        if not isinstance(recorded_hash, str) or not recorded_hash:
            errors.append(f"{artifact_path}: source_sha256 missing hash for {ref}")
        elif recorded_hash != sha256_file(path):
            errors.append(f"{artifact_path}: source_sha256 is stale for {ref}")


def check_claim_review_basis_dependency(
    artifact_path: str,
    artifact: dict[str, Any],
    round_dir: Path,
    case_id: str,
    round_id: str,
    errors: list[str],
) -> None:
    spec = output_spec(artifact_path)
    if spec is None or not spec.final_output:
        return
    basis_path = round_dir / CLAIM_REVIEW_BASIS_REL
    if not basis_path.is_file():
        return
    evidence_refs = artifact.get("evidence_refs")
    basis_ref_recorded = isinstance(evidence_refs, list) and CLAIM_REVIEW_BASIS_REL in evidence_refs
    try:
        loaded = json.loads(basis_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        if basis_ref_recorded:
            errors.append(f"{CLAIM_REVIEW_BASIS_REL}: invalid JSON: {exc.msg}")
        return
    if not isinstance(loaded, dict):
        if basis_ref_recorded:
            errors.append(f"{CLAIM_REVIEW_BASIS_REL}: claim review basis artifact must be an object")
        return
    basis_applies = claim_basis_applies_to_artifact(loaded, artifact_path, artifact)
    if not basis_applies and not basis_ref_recorded:
        return
    if not basis_applies:
        errors.append(f"{artifact_path}: claim review basis draft_ref must match independent_review.review_basis_path")
        return
    if not isinstance(evidence_refs, list) or CLAIM_REVIEW_BASIS_REL not in evidence_refs:
        errors.append(f"{artifact_path}: evidence_refs must include {CLAIM_REVIEW_BASIS_REL}")
    basis_input_refs, basis_evidence_refs = claim_basis_dependency_refs(
        round_dir,
        artifact_path=artifact_path,
        artifact=artifact,
    )
    artifact_input_refs = artifact.get("input_refs")
    artifact_evidence_refs = artifact.get("evidence_refs")
    input_set = (
        {item for item in artifact_input_refs if isinstance(item, str)}
        if isinstance(artifact_input_refs, list)
        else set()
    )
    evidence_set = (
        {item for item in artifact_evidence_refs if isinstance(item, str)}
        if isinstance(artifact_evidence_refs, list)
        else set()
    )
    for ref in basis_input_refs:
        if ref not in input_set:
            errors.append(f"{artifact_path}: input_refs must include claim-basis dependency {ref}")
    for ref in basis_evidence_refs:
        if ref not in evidence_set:
            errors.append(f"{artifact_path}: evidence_refs must include claim-basis dependency {ref}")
    errors.extend(
        validate_claim_review_basis_payload(
            loaded,
            CLAIM_REVIEW_BASIS_REL,
            round_dir=round_dir,
            case_id=case_id,
            round_id=round_id,
        )
    )
    review = artifact.get("independent_review")
    review_basis_path = review.get("review_basis_path") if isinstance(review, dict) else None
    draft_ref = loaded.get("draft_ref")
    if isinstance(review_basis_path, str) and review_basis_path and draft_ref != review_basis_path:
        errors.append(f"{artifact_path}: claim review basis draft_ref must match independent_review.review_basis_path")


def artifact_source_refs(artifact: dict[str, Any]) -> list[str]:
    source_refs: list[str] = []
    for field in ("input_refs", "evidence_refs"):
        values = artifact.get(field)
        if isinstance(values, list):
            source_refs.extend(ref for ref in values if isinstance(ref, str))
    return source_refs


def check_no_absolute_command(label: str, value: Any, errors: list[str]) -> None:
    if isinstance(value, str) and ABSOLUTE_PATH_RE.search(value):
        errors.append(f"{label}: command contains an absolute filesystem path")


def required_helper_targets(name: str, round_dir: Path) -> set[str]:
    if name == "check-agent-coverage":
        return {COVERAGE_REL.as_posix()}
    if name == "check-evaluation-claims":
        return {"work/quantitative_claims.json"}
    if name == "check-literature-citation-review":
        return {"outputs/literature_citation_review.md", SOURCE_ACQUISITION_REL}
    if name == "check-report-calibration":
        return set(report_calibration_check_targets(round_dir))
    if name in {"check-opponent-report", "check-opponent-report:canonical"}:
        targets = {"work/opponent_report_trace.json", "outputs/oponent_podklady_revidovane.md"}
        if round_uses_report_calibration_basis(round_dir):
            targets.add(REPORT_CALIBRATION_BASIS_REL)
        if (
            (round_dir / "work" / "oponent_posudek_draft.md").is_file()
            or (round_dir / "outputs" / "oponent_posudek_navrh.md").is_file()
            or (round_dir / "outputs" / "feedback_k_posudku.md").is_file()
        ):
            targets.add("work/oponent_posudek_draft.md")
        return targets
    if name == "check-opponent-report:clean":
        targets = {
            "work/opponent_report_trace.json",
            "outputs/oponent_podklady_revidovane.md",
            "outputs/oponent_posudek_navrh.md",
        }
        if round_uses_report_calibration_basis(round_dir):
            targets.add(REPORT_CALIBRATION_BASIS_REL)
        return targets
    if name == "check-supervisor-report":
        targets = {"work/supervisor_report_trace.json", "outputs/vedouci_posudek_revidovany.md"}
        if (round_dir / "work" / "vedouci_posudek_draft.md").is_file():
            targets.add("work/vedouci_posudek_draft.md")
        return targets
    if name == "check-theses-similarity-report":
        return set(theses_similarity_check_targets(round_dir))
    if name == "check-opponent-calibration-profile":
        return set(calibration_profile_check_targets(round_dir))
    if name == "check-supervisor-report-calibration-profile":
        return set(supervisor_report_calibration_profile_check_targets(round_dir))
    return set()


def output_paths(round_dir: Path) -> set[str]:
    outputs = round_dir / "outputs"
    if not outputs.is_dir():
        return set()
    return {f"outputs/{path.name}" for path in outputs.glob("*.md") if path.is_file()}


def top_level_limitations(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    limitations = manifest.get("workflow_limitations")
    if not isinstance(limitations, list):
        return []
    return [item for item in limitations if isinstance(item, dict)]


def has_relevant_limitation(manifest: dict[str, Any], term: str | None = None) -> bool:
    for item in top_level_limitations(manifest):
        description = str(item.get("description", ""))
        impact = str(item.get("impact", ""))
        status = str(item.get("status", ""))
        text = f"{description} {impact}".lower()
        if status and (term is None or term.lower() in text):
            return True
    return False


def check_helper_checks(
    checks: Any,
    required: set[str],
    round_dir: Path,
    require_complete: bool,
    errors: list[str],
    warnings: list[str],
) -> None:
    if not isinstance(checks, list):
        errors.append("helper_checks must be a list")
        return
    seen: set[str] = set()
    for index, check in enumerate(checks, start=1):
        if not isinstance(check, dict):
            errors.append(f"helper_checks item {index}: expected object")
            continue
        name = check.get("check")
        status = check.get("status")
        command = check.get("command")
        if not isinstance(name, str) or not name:
            errors.append(f"helper_checks item {index}: missing check name")
            continue
        seen.add(name)
        if status not in KNOWN_CHECK_STATUSES:
            errors.append(f"helper_checks {name}: unknown status {status!r}")
        elif status == "failed":
            errors.append(f"helper_checks {name}: recorded failed status")
        elif name in required and name != "check-review-manifest" and require_complete and status != "passed":
            errors.append(f"helper_checks {name}: required closeout check must be passed, not {status}")
        elif status in {"not_run", "not_recorded"}:
            warnings.append(f"helper_checks {name}: status is {status}")
        if name in required and name != "check-review-manifest" and require_complete:
            if check.get("exit_code") != 0:
                errors.append(f"helper_checks {name}: required closeout check must record exit_code 0")
            if not str(check.get("checked_at", "")).strip():
                errors.append(f"helper_checks {name}: required closeout check must record checked_at")
        if not isinstance(command, str) or not command:
            errors.append(f"helper_checks {name}: missing command")
        check_no_absolute_command(f"helper_checks {name}", command, errors)
        targets = check.get("target_artifacts", [])
        if not isinstance(targets, list):
            errors.append(f"helper_checks {name}: target_artifacts must be a list")
            targets = []
        if require_complete and name in required:
            target_set = {target for target in targets if isinstance(target, str)}
            missing_targets = sorted(required_helper_targets(name, round_dir) - target_set)
            for target in missing_targets:
                errors.append(f"helper_checks {name}: missing required target artifact {target}")
        recorded_hashes = check.get("target_sha256", {})
        if require_complete and name in required and name != "check-review-manifest":
            if not isinstance(recorded_hashes, dict):
                errors.append(f"helper_checks {name}: target_sha256 must record checked target hashes")
                recorded_hashes = {}
            for target in targets:
                path = validate_rel_path(
                    f"helper_checks {name} target",
                    target,
                    round_dir,
                    errors,
                    must_exist=True,
                )
                if path and path.is_file():
                    recorded_hash = recorded_hashes.get(target)
                    if not isinstance(recorded_hash, str) or not recorded_hash:
                        errors.append(f"helper_checks {name}: missing target hash for {target}")
                    elif recorded_hash != sha256_file(path):
                        errors.append(f"helper_checks {name}: target hash is stale for {target}")
            validate_helper_check_freshness(check, round_dir, errors)
    missing = sorted(required - seen)
    for name in missing:
        errors.append(f"missing required helper check record: {name}")


def validate_helper_check_freshness(check: dict[str, Any], round_dir: Path, errors: list[str]) -> None:
    name = check.get("check")
    if name == "check-review-manifest" or not isinstance(name, str) or not name:
        return
    # Imported lazily to keep the manifest validator usable without importing
    # init-review-manifest during module import.
    from thesis_review_workflow.cli.init_review_manifest import (
        helper_dependency_hashes,
        repo_root_from_round,
        workflow_checker_version,
    )

    current_version = workflow_checker_version(repo_root_from_round(round_dir))
    recorded_version = check.get("checker_version")
    if not isinstance(recorded_version, str) or not recorded_version:
        errors.append(f"helper_checks {name}: missing checker_version")
    elif recorded_version != current_version:
        errors.append(f"helper_checks {name}: checker_version is stale")

    recorded_dependencies = check.get("dependency_sha256")
    current_dependencies = helper_dependency_hashes(round_dir, name)
    if not isinstance(recorded_dependencies, dict):
        errors.append(f"helper_checks {name}: missing dependency_sha256")
    elif recorded_dependencies != current_dependencies:
        errors.append(f"helper_checks {name}: dependency_sha256 is stale")


def required_checks(paths: set[str], round_dir: Path, manifest: dict[str, Any]) -> set[str]:
    required = {"check-review-manifest"}
    if "outputs/feedback_student.md" in paths:
        required.update({"check-supervisor-ready", "check-feedback-language", "check-feedback-output"})
    if "outputs/vedouci_posudek_revidovany.md" in paths:
        required.update({"check-supervisor-report-ready", "check-supervisor-report"})
    if "outputs/oponent_podklady_revidovane.md" in paths:
        required.update({"check-round-ready", "check-opponent-materials", "check-opponent-report:canonical"})
    if "outputs/oponent_posudek_navrh.md" in paths or "outputs/feedback_k_posudku.md" in paths:
        required.update({"check-opponent-report:canonical", "check-opponent-report:clean"})
    if report_calibration_check_required(round_dir):
        required.add("check-report-calibration")
    if "outputs/figure_media_review.md" in paths:
        required.add("check-figure-media-review")
    if "outputs/literature_citation_review.md" in paths:
        required.add("check-literature-citation-review")
    if "outputs/typography_formal_review.md" in paths:
        required.add("check-typography-formal")
    if theses_similarity_evidence_present(round_dir):
        required.add("check-theses-similarity-report")
    if "outputs/code_consistency.md" in paths:
        required.add("check-code-consistency")
    if "outputs/code_quality_review.md" in paths:
        required.add("check-code-quality-review")
    if supporting_work_artifact_present(manifest, "work/quantitative_claims.json"):
        required.add("check-evaluation-claims")
    if "outputs/revision_diff.md" in paths:
        required.add("check-revision-diff")
    if "outputs/reviewer_calibration_profile.md" in paths:
        required.add("check-opponent-calibration-profile")
    if "outputs/supervisor_report_calibration_profile.md" in paths:
        required.add("check-supervisor-report-calibration-profile")
    if coverage_required(round_dir, manifest):
        required.add("check-agent-coverage")
    return required


def supporting_work_artifact_present(manifest: dict[str, Any], rel_path: str) -> bool:
    records = manifest.get("supporting_work_artifacts")
    if not isinstance(records, list):
        return False
    return any(isinstance(record, dict) and record.get("path") == rel_path for record in records)


def check_agent_coverage_gate(
    root: Path,
    case_id: str,
    round_id: str,
    round_dir: Path,
    manifest: dict[str, Any],
    require_complete: bool,
    errors: list[str],
) -> None:
    if not require_complete or not coverage_required(round_dir, manifest):
        return
    result = subprocess.run(
        resolve_repo_command(root, ["scripts/check-agent-coverage", case_id, round_id]),
        cwd=root,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=repo_command_environment(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        detail = " | ".join(
            line.strip() for line in (result.stderr + "\n" + result.stdout).splitlines() if line.strip()
        )
        errors.append(f"agent coverage failed: {detail}")


def artifact_review_ok(
    artifact: dict[str, Any],
    manifest: dict[str, Any],
    artifacts_by_path: dict[str, dict[str, Any]],
    round_dir: Path,
    case_id: str,
    round_id: str,
    require_complete: bool,
    errors: list[str],
    warnings: list[str],
) -> None:
    path = artifact.get("path")
    scope = artifact.get("review_scope")
    review = artifact.get("independent_review")
    if scope not in KNOWN_REVIEW_SCOPES:
        errors.append(f"{path}: unknown review_scope {scope!r}")
        return
    if not isinstance(review, dict):
        errors.append(f"{path}: independent_review must be an object")
        return

    status = review.get("status")
    if status not in KNOWN_REVIEW_STATUSES:
        errors.append(f"{path}: unknown independent_review.status {status!r}")
        return

    if status == "failed" and scope in FINAL_SCOPES:
        errors.append(f"{path}: final/sendable artifact has failed review status")

    if status in REVIEWED_STATUSES:
        reviewer_agent = str(review.get("reviewer_agent", "")).strip()
        reviewer_role = str(review.get("reviewer_role", "")).strip()
        reviewed_at = str(review.get("reviewed_at", "")).strip()
        if reviewer_agent in {"", "not_recorded"}:
            errors.append(f"{path}: reviewed status requires independent_review.reviewer_agent")
        if reviewer_role in {"", "not_recorded"}:
            errors.append(f"{path}: reviewed status requires independent_review.reviewer_role")
        if not reviewed_at:
            errors.append(f"{path}: reviewed status requires independent_review.reviewed_at")
        reviewed_hash = review.get("reviewed_hash")
        if not isinstance(reviewed_hash, str) or not reviewed_hash:
            errors.append(f"{path}: reviewed status requires independent_review.reviewed_hash")
        elif reviewed_hash != artifact.get("artifact_sha256"):
            errors.append(f"{path}: review is stale_after_edit; reviewed_hash does not match current artifact_sha256")
        approval_required = require_complete and scope in FINAL_SCOPES
        approval_record_path = review.get("approval_record_path")
        if approval_record_path:
            if not isinstance(approval_record_path, str) or not is_review_approval_path(approval_record_path):
                errors.append(f"{path}: approval_record_path must match work/reviews/*_review.json")
            else:
                validate_rel_path(f"{path}: approval_record_path", approval_record_path, round_dir, errors)
                if approval_record_path not in record_paths(manifest.get("supporting_work_artifacts")):
                    errors.append(f"{path}: approval_record_path is not recorded in supporting_work_artifacts")
                if isinstance(path, str):
                    loaded, approval_errors = load_review_approval(round_dir, approval_record_path)
                    if approval_errors or loaded is None:
                        for error in approval_errors:
                            errors.append(f"{path}: {error}")
                    else:
                        for error in validate_review_approval_with_manifest(
                            loaded,
                            approval_record_path,
                            round_dir,
                            manifest=manifest,
                            case_id=case_id,
                            round_id=round_id,
                            reviewed_artifact_path=path,
                        ):
                            errors.append(f"{path}: {error}")
        elif approval_required:
            errors.append(f"{path}: final/sendable artifact requires independent_review.approval_record_path")
    elif scope in FINAL_SCOPES:
        if require_complete:
            errors.append(f"{path}: final/sendable artifact must have a recorded independent review in closeout mode")
        else:
            exception = str(review.get("exception", "")).strip()
            limitations = artifact.get("limitations")
            if not exception or not isinstance(limitations, list) or not limitations:
                errors.append(
                    f"{path}: final/sendable artifact needs an independent review "
                    "or an explicit exception plus limitations"
                )
            else:
                warnings.append(f"{path}: final/sendable artifact has review status {status}; exception recorded")

    if require_complete and path in INDEPENDENT_REVIEW_REQUIRED_OUTPUTS:
        if scope != "internal_only":
            errors.append(f"{path}: calibrated internal evidence must use review_scope internal_only")
        if status not in REVIEWED_STATUSES:
            errors.append(f"{path}: calibrated internal evidence requires a recorded independent review")
        generated = artifact.get("generated_by")
        has_recorded_generator = False
        if isinstance(generated, list):
            for generator in generated:
                if not isinstance(generator, dict):
                    continue
                agent = str(generator.get("agent", "")).strip()
                role = str(generator.get("role", "")).strip()
                if agent not in {"", "not_recorded"} and role not in {"", "not_recorded"}:
                    has_recorded_generator = True
        if not has_recorded_generator:
            errors.append(f"{path}: calibrated internal evidence requires a recorded generator")

    if scope == "covered_by_synthesis":
        covered_by = review.get("covered_by_artifact")
        used_findings = str(review.get("used_findings", "")).strip()
        evidence_hash = str(review.get("evidence_hash", "")).strip()
        if not covered_by:
            errors.append(f"{path}: covered_by_synthesis requires covered_by_artifact")
        elif covered_by not in artifacts_by_path:
            errors.append(f"{path}: covered_by_artifact is not present in manifest: {covered_by}")
        if not used_findings or used_findings == "not_recorded":
            if require_complete:
                errors.append(
                    f"{path}: covered_by_synthesis requires a concrete used_findings summary in closeout mode"
                )
            else:
                warnings.append(f"{path}: covered_by_synthesis has no concrete used_findings summary")
        if require_complete:
            if not evidence_hash:
                errors.append(f"{path}: covered_by_synthesis requires evidence_hash in closeout mode")
            elif evidence_hash != artifact.get("artifact_sha256"):
                errors.append(f"{path}: covered_by_synthesis evidence_hash does not match current artifact_sha256")

    generated = artifact.get("generated_by")
    if not isinstance(generated, list) or not generated:
        errors.append(f"{path}: generated_by must contain at least one record")
    else:
        reviewer_agent = str(review.get("reviewer_agent", "")).strip()
        reviewer_role = str(review.get("reviewer_role", "")).strip()
        has_recorded_generator = False
        for index, generator in enumerate(generated, start=1):
            if not isinstance(generator, dict):
                errors.append(f"{path}: generated_by item {index} must be an object")
                continue
            agent = str(generator.get("agent", "")).strip()
            role = str(generator.get("role", "")).strip()
            if not role:
                errors.append(f"{path}: generated_by item {index} missing role")
            if agent not in {"", "not_recorded"} and role not in {"", "not_recorded"}:
                has_recorded_generator = True
            contribution = str(generator.get("contribution", "")).strip().lower()
            requires_independence = contribution in {
                "",
                "generation",
                "draft_generation",
                "initial_synthesis",
            }
            if (
                requires_independence
                and agent
                and reviewer_agent
                and agent not in {"not_recorded", "manual"}
                and reviewer_agent not in {"not_recorded", "manual"}
                and agent == reviewer_agent
            ):
                errors.append(f"{path}: generator and reviewer agent are identical")
            if (
                requires_independence
                and role
                and reviewer_role
                and role != "not_recorded"
                and reviewer_role != "not_recorded"
                and role == reviewer_role
            ):
                errors.append(f"{path}: generator and reviewer role are identical")
        if require_complete and scope in FINAL_SCOPES and not has_recorded_generator:
            errors.append(f"{path}: final/sendable artifact requires a recorded generator or finalizer")

    if require_complete and scope in FINAL_SCOPES and status in REVIEWED_STATUSES:
        review_basis_path = review.get("review_basis_path")
        review_basis_sha256 = review.get("review_basis_sha256")
        basis_candidates = review_basis_candidates(str(path))
        default_basis = next((candidate for candidate in basis_candidates if (round_dir / candidate).is_file()), None)
        if default_basis and (round_dir / default_basis).is_file():
            basis = validate_rel_path(f"{path}: review_basis_path", review_basis_path, round_dir, errors)
            if basis and basis.is_file():
                current_basis_hash = sha256_file(basis)
                if review_basis_sha256 != current_basis_hash:
                    errors.append(f"{path}: review_basis_sha256 does not match current review basis file")
            elif not review_basis_path:
                errors.append(f"{path}: reviewed output should record review_basis_path for {default_basis}")
        elif review_basis_path:
            basis = validate_rel_path(f"{path}: review_basis_path", review_basis_path, round_dir, errors)
            if basis and basis.is_file() and review_basis_sha256 != sha256_file(basis):
                errors.append(f"{path}: review_basis_sha256 does not match current review basis file")

    limitations = artifact.get("limitations")
    if limitations == [] and scope in FINAL_SCOPES and status not in REVIEWED_STATUSES:
        errors.append(f"{path}: limitations must be non-empty when final review is not passed")


def check_artifacts(
    manifest: dict[str, Any],
    case_id: str,
    round_id: str,
    round_dir: Path,
    require_complete: bool,
    errors: list[str],
    warnings: list[str],
) -> set[str]:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        errors.append("artifacts must be a list")
        return set()

    actual_outputs = output_paths(round_dir)
    artifacts_by_path: dict[str, dict[str, Any]] = {}
    manifest_paths: set[str] = set()
    pending: list[tuple[str, dict[str, Any], Path | None]] = []
    for index, artifact in enumerate(artifacts, start=1):
        if not isinstance(artifact, dict):
            errors.append(f"artifacts item {index}: expected object")
            continue
        path_value = artifact.get("path")
        artifact_path = validate_rel_path(f"artifacts item {index}", path_value, round_dir, errors)
        if not isinstance(path_value, str):
            continue
        if path_value in artifacts_by_path:
            errors.append(f"duplicate artifact entry: {path_value}")
        if not path_value.startswith("outputs/"):
            errors.append(f"{path_value}: generated artifact path must be under outputs/")
        manifest_paths.add(path_value)
        artifacts_by_path[path_value] = artifact
        pending.append((path_value, artifact, artifact_path))

    input_paths = set().union(
        record_paths(manifest.get("inputs")),
        record_paths(manifest.get("extracted_artifacts")),
        record_paths(manifest.get("notes")),
    )
    work_paths = record_paths(manifest.get("supporting_work_artifacts"))
    helper_names = helper_check_names(manifest.get("helper_checks"))
    artifact_paths = set(artifacts_by_path)

    for path_value, artifact, artifact_path in pending:
        spec = output_spec(path_value)
        if spec is not None:
            if artifact.get("artifact_type") != spec.artifact_type:
                errors.append(f"{path_value}: artifact_type must be {spec.artifact_type}")
            if artifact.get("skills") != list(spec.skills):
                errors.append(f"{path_value}: skills must be {list(spec.skills)}")
            scope = artifact.get("review_scope")
            allowed_scopes = {spec.review_scope}
            if spec.internal_evidence and not spec.explicit_internal_review:
                allowed_scopes.add("covered_by_synthesis")
            if scope not in allowed_scopes:
                rendered = ", ".join(sorted(allowed_scopes))
                errors.append(f"{path_value}: review_scope must be one of {rendered}")
        if artifact_path and artifact_path.is_file():
            current_hash = sha256_file(artifact_path)
            recorded_hash = artifact.get("artifact_sha256")
            if recorded_hash != current_hash:
                errors.append(f"{path_value}: artifact_sha256 does not match current file")
        if not isinstance(artifact.get("skills"), list):
            errors.append(f"{path_value}: skills must be a list")
        if not isinstance(artifact.get("helper_checks", []), list):
            errors.append(f"{path_value}: helper_checks must be a list")
        if "input_refs" in artifact:
            check_ref_list(
                artifact_path=path_value,
                field="input_refs",
                refs=artifact.get("input_refs"),
                allowed_paths=input_paths,
                allowed_checks=helper_names,
                round_dir=round_dir,
                errors=errors,
            )
        if "evidence_refs" in artifact:
            check_ref_list(
                artifact_path=path_value,
                field="evidence_refs",
                refs=artifact.get("evidence_refs"),
                allowed_paths=work_paths | artifact_paths,
                allowed_checks=helper_names,
                round_dir=round_dir,
                errors=errors,
            )
        if "check_refs" in artifact:
            check_ref_list(
                artifact_path=path_value,
                field="check_refs",
                refs=artifact.get("check_refs"),
                allowed_paths=set(),
                allowed_checks=helper_names,
                round_dir=round_dir,
                errors=errors,
            )
        if "handoff_refs" in artifact:
            check_ref_list(
                artifact_path=path_value,
                field="handoff_refs",
                refs=artifact.get("handoff_refs"),
                allowed_paths=work_paths | artifact_paths,
                allowed_checks=helper_names,
                round_dir=round_dir,
                errors=errors,
            )
        artifact_review_ok(
            artifact,
            manifest,
            artifacts_by_path,
            round_dir,
            case_id,
            round_id,
            require_complete,
            errors,
            warnings,
        )
        spec = output_spec(path_value)
        if require_complete:
            check_claim_review_basis_dependency(path_value, artifact, round_dir, case_id, round_id, errors)
        if require_complete and spec is not None and spec.final_output:
            check_source_hashes(path_value, artifact, artifact_source_refs(artifact), round_dir, errors)
        if require_complete and path_value in INDEPENDENT_REVIEW_REQUIRED_OUTPUTS:
            check_source_hashes(path_value, artifact, artifact_source_refs(artifact), round_dir, errors)

    missing_outputs = sorted(actual_outputs - manifest_paths)
    if missing_outputs and require_complete:
        for path in missing_outputs:
            errors.append(f"outputs artifact missing from manifest: {path}")
    elif missing_outputs:
        for path in missing_outputs:
            warnings.append(f"outputs artifact missing from manifest: {path}")

    stale_entries = sorted(manifest_paths - actual_outputs)
    for path in stale_entries:
        errors.append(f"manifest references missing output artifact: {path}")
    return manifest_paths


def check_manifest(
    manifest: dict[str, Any],
    case_id: str,
    round_id: str,
    root: Path,
    round_dir: Path,
    require_complete: bool,
    errors: list[str],
    warnings: list[str],
) -> None:
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"wrong schema_version: expected {SCHEMA_VERSION}")
    if manifest.get("case_id") != case_id:
        errors.append("case_id in manifest does not match requested case")
    if manifest.get("round_id") != round_id:
        errors.append("round_id in manifest does not match requested round")
    validate_rel_path("manifest_path", manifest.get("manifest_path", MANIFEST_REL), round_dir, errors)

    records_by_path(manifest.get("inputs"), "inputs", round_dir, errors)
    records_by_path(manifest.get("extracted_artifacts"), "extracted_artifacts", round_dir, errors)
    records_by_path(manifest.get("notes"), "notes", round_dir, errors)
    supporting_work_artifacts = manifest.get("supporting_work_artifacts")
    if not isinstance(supporting_work_artifacts, list):
        errors.append("supporting_work_artifacts must be a list")
    else:
        records_by_path(supporting_work_artifacts, "supporting_work_artifacts", round_dir, errors)
        errors.extend(
            validate_supporting_work_artifacts(
                supporting_work_artifacts,
                round_dir,
                case_id=case_id,
                round_id=round_id,
            )
        )

    limitations = manifest.get("workflow_limitations")
    if limitations is not None and not isinstance(limitations, list):
        errors.append("workflow_limitations must be a list")
    else:
        errors.extend(validate_materiality_workflow_limitations(limitations))

    artifact_paths = check_artifacts(manifest, case_id, round_id, round_dir, require_complete, errors, warnings)
    check_helper_checks(
        manifest.get("helper_checks"),
        required_checks(artifact_paths, round_dir, manifest),
        round_dir,
        require_complete,
        errors,
        warnings,
    )
    check_agent_coverage_gate(root, case_id, round_id, round_dir, manifest, require_complete, errors)

    final_outputs = {
        "outputs/feedback_student.md",
        "outputs/vedouci_posudek_revidovany.md",
        "outputs/oponent_podklady_revidovane.md",
    }
    if inferred_code_evidence_present(round_dir, manifest) and artifact_paths & final_outputs:
        missing = {
            "outputs/code_consistency.md",
            "outputs/code_quality_review.md",
        } - artifact_paths
        if missing and not has_relevant_limitation(manifest, "code"):
            errors.append(
                "code evidence is present, but supervisor/opponent final output lacks both code consistency "
                "and code quality evidence entries or a code-specific limitation"
            )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-complete", action="store_true", help="require every outputs/*.md file to be listed")
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    args = parser.parse_args(argv[1:])

    validate_id("CASE_ID", args.case_id, stderr=True)
    root = repo_root()
    try:
        case_dir = require_case_dir(root, args.case_id, error_prefix="ERROR: ", stderr=True)
        round_id = resolve_round(case_dir, args.round_id, stderr=True)
        round_dir = require_round_dir(case_dir, args.case_id, round_id, error_prefix="ERROR: ", stderr=True)
    except SystemExit as exc:
        if exc.code == 2:
            return 2
        raise

    errors: list[str] = []
    warnings: list[str] = []
    manifest = load_manifest(round_dir / MANIFEST_REL, errors)
    if manifest is not None:
        check_manifest(manifest, args.case_id, round_id, root, round_dir, args.require_complete, errors, warnings)

    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("Review manifest check passed")
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
