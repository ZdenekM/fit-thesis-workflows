"""Structured final-review approval records for generated review artifacts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from thesis_review_workflow.artifact_registry import output_spec
from thesis_review_workflow.helper_checks import validate_helper_check_ids
from thesis_review_workflow.paths import is_safe_round_relative_path
from thesis_review_workflow.report_calibration import (
    report_calibration_check_targets,
    report_calibration_review_basis_requires_check,
)
from thesis_review_workflow.theses_checker_summary import THESES_CHECKER_SUMMARY_REL, round_uses_theses_checker_summary
from thesis_review_workflow.theses_similarity import (
    THESES_SIMILARITY_ASSESSMENT_REL,
    THESES_SIMILARITY_REVIEW_APPROVAL_REL,
    THESES_SIMILARITY_REVIEW_DRAFT_REL,
    THESES_SIMILARITY_REVIEW_REL,
)

REVIEW_APPROVAL_SCHEMA = "review-approval-v1"
APPROVED_VERDICTS = {"approved", "pass"}
REVIEW_APPROVAL_GLOB = "work/reviews/*_review.json"
FINAL_REVIEW_SCOPES = {"sendable_final", "standalone_final"}
OBSERVED_ONLY_REQUIRED_CHECKS = {
    "check-review-wave.opponent-report.draft",
}
REPORT_CALIBRATION_REQUIRED_CHECK = "check-report-calibration"
THESES_CHECKER_SUMMARY_REQUIRED_CHECK = "check-theses-checker-summary"


@dataclass(frozen=True)
class ReviewApprovalProfile:
    profile: str
    workflow_profile: str
    approval_path: str
    reviewed_artifact_path: str
    review_basis_candidates: tuple[str, ...]
    reviewer_role: str
    required_checks: tuple[str, ...]
    review_basis_required: bool = False


APPROVAL_PROFILES = {
    "supervisor-feedback": ReviewApprovalProfile(
        profile="supervisor-feedback",
        workflow_profile="supervisor_feedback",
        approval_path="work/reviews/supervisor_feedback_review.json",
        reviewed_artifact_path="outputs/feedback_student.md",
        review_basis_candidates=("work/feedback_student_draft.md",),
        reviewer_role="thesis-supervisor-feedback-review",
        required_checks=("check-supervisor-ready", "check-feedback-language", "check-feedback-output"),
    ),
    "supervisor-report": ReviewApprovalProfile(
        profile="supervisor-report",
        workflow_profile="supervisor_report",
        approval_path="work/reviews/supervisor_report_review.json",
        reviewed_artifact_path="outputs/vedouci_posudek_revidovany.md",
        review_basis_candidates=("work/vedouci_posudek_draft.md",),
        reviewer_role="thesis-supervisor-report-review",
        required_checks=("check-supervisor-report-ready", "check-supervisor-report"),
    ),
    "opponent-materials": ReviewApprovalProfile(
        profile="opponent-materials",
        workflow_profile="opponent_review",
        approval_path="work/reviews/opponent_materials_review.json",
        reviewed_artifact_path="outputs/oponent_podklady_revidovane.md",
        review_basis_candidates=("work/oponent_podklady_draft.md",),
        reviewer_role="thesis-opponent-materials-review",
        required_checks=("check-round-ready", "check-opponent-materials", "check-opponent-report:canonical"),
    ),
    "opponent-report-review": ReviewApprovalProfile(
        profile="opponent-report-review",
        workflow_profile="opponent_report_review",
        approval_path="work/reviews/opponent_report_review.json",
        reviewed_artifact_path="outputs/feedback_k_posudku.md",
        review_basis_candidates=(
            "outputs/oponent_posudek_navrh.md",
            "work/oponent_posudek_draft.md",
        ),
        reviewer_role="thesis-opponent-report-review",
        required_checks=(
            "check-opponent-report:canonical",
            "check-opponent-report:clean",
            "check-review-wave.opponent-report.draft",
        ),
    ),
    "theses-similarity-review": ReviewApprovalProfile(
        profile="theses-similarity-review",
        workflow_profile="theses_similarity_review",
        approval_path=THESES_SIMILARITY_REVIEW_APPROVAL_REL,
        reviewed_artifact_path=THESES_SIMILARITY_REVIEW_REL,
        review_basis_candidates=(THESES_SIMILARITY_REVIEW_DRAFT_REL, THESES_SIMILARITY_ASSESSMENT_REL),
        reviewer_role="evidence-calibration-reviewer",
        required_checks=("check-theses-similarity-report",),
    ),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_review_approval_path(rel_path: str) -> bool:
    path = Path(rel_path)
    return (
        len(path.parts) == 3
        and path.parts[0] == "work"
        and path.parts[1] == "reviews"
        and path.name.endswith("_review.json")
    )


def require_review_approval_path(rel_path: str) -> None:
    if not is_review_approval_path(rel_path):
        raise ValueError(f"review approval path must match {REVIEW_APPROVAL_GLOB}: {rel_path}")


def resolve_review_basis(round_dir: Path, profile: ReviewApprovalProfile, explicit_basis: str) -> str:
    if explicit_basis:
        if not is_safe_round_relative_path(explicit_basis):
            raise ValueError("review basis path must be relative inside the round")
        if profile.review_basis_candidates and explicit_basis not in profile.review_basis_candidates:
            choices = ", ".join(profile.review_basis_candidates)
            raise ValueError(f"review basis for {profile.profile} must be one of: {choices}")
        if not (round_dir / explicit_basis).is_file():
            raise ValueError(f"review basis file does not exist: {explicit_basis}")
        return explicit_basis
    for candidate in profile.review_basis_candidates:
        if (round_dir / candidate).is_file():
            return candidate
    if profile.review_basis_required:
        raise ValueError(f"--review-basis is required for {profile.profile}")
    choices = ", ".join(profile.review_basis_candidates)
    raise ValueError(f"no review basis exists for {profile.profile}; expected one of: {choices}")


def validate_required_checks(
    *,
    required_checks: tuple[str, ...],
    checks_observed: list[str],
    rel_path: str,
    round_dir: Path,
    reviewed_artifact_path: str,
    manifest: dict[str, Any] | None,
) -> list[str]:
    errors: list[str] = []
    observed_names: set[str] = set()
    for index, item in enumerate(checks_observed, start=1):
        if isinstance(item, str) and item.strip():
            observed_names.add(item)
        else:
            errors.append(f"{rel_path}: checks_observed item {index} must be a non-empty string")
    string_checks = [item for item in checks_observed if isinstance(item, str)]
    errors.extend(
        f"{rel_path}: {error}"
        for error in validate_helper_check_ids(
            string_checks,
            label="checks_observed",
            allow_observed_only=True,
        )
    )
    allowed_observed = set(required_checks)
    for name in sorted(observed_names - allowed_observed):
        errors.append(
            f"{rel_path}: unexpected observed check {name}; expected one of: " f"{', '.join(sorted(allowed_observed))}"
        )
    missing = sorted(set(required_checks) - observed_names)
    for check in missing:
        errors.append(
            f"{rel_path}: missing required observed check: {check}; required checks: "
            f"{', '.join(sorted(required_checks))}"
        )
    helper_required_checks = tuple(check for check in required_checks if check not in OBSERVED_ONLY_REQUIRED_CHECKS)
    if helper_required_checks and not manifest:
        errors.append(f"{rel_path}: review manifest is required to verify required observed checks")
        return errors
    if manifest is None:
        return errors
    helper_checks = manifest.get("helper_checks")
    if not isinstance(helper_checks, list):
        return errors
    for item in helper_checks:
        if not isinstance(item, dict):
            continue
        check_name = item.get("check")
        if check_name not in helper_required_checks:
            continue
        if item.get("status") != "passed":
            errors.append(f"{rel_path}: helper check {check_name} must be passed before approval")
        if item.get("exit_code") != 0:
            errors.append(f"{rel_path}: helper check {check_name} must record exit_code 0")
        if not str(item.get("checked_at", "")).strip():
            errors.append(f"{rel_path}: helper check {check_name} must record checked_at")
        targets = item.get("target_artifacts")
        if not isinstance(targets, list) or not targets:
            errors.append(f"{rel_path}: helper check {check_name} must record target_artifacts")
            continue
        target_set = {target for target in targets if isinstance(target, str)}
        required_targets = required_helper_targets_for_approval(str(check_name), round_dir, rel_path)
        for missing_target in sorted(required_targets - target_set):
            errors.append(f"{rel_path}: helper check {check_name} missing required target artifact {missing_target}")
        recorded_hashes = item.get("target_sha256")
        if not isinstance(recorded_hashes, dict):
            errors.append(f"{rel_path}: helper check {check_name} must record target_sha256")
        else:
            for target_path in targets:
                if not isinstance(target_path, str):
                    errors.append(f"{rel_path}: helper check {check_name} target_artifacts items must be strings")
                    continue
                target_file = round_dir / target_path
                if not target_file.is_file():
                    continue
                recorded = recorded_hashes.get(target_path)
                if not isinstance(recorded, str) or not recorded:
                    errors.append(f"{rel_path}: helper check {check_name} missing target hash for {target_path}")
                elif recorded != sha256_file(target_file):
                    errors.append(f"{rel_path}: helper check {check_name} target hash is stale for {target_path}")
        _validate_required_helper_freshness(check_name, item, rel_path, round_dir, errors)
    seen = {item.get("check") for item in helper_checks if isinstance(item, dict)}
    for check in sorted(set(helper_required_checks) - {item for item in seen if isinstance(item, str)}):
        errors.append(f"{rel_path}: missing manifest helper check record: {check}")
    return errors


def _validate_required_helper_freshness(
    name: Any,
    check: dict[str, Any],
    rel_path: str,
    round_dir: Path,
    errors: list[str],
) -> None:
    if name != THESES_CHECKER_SUMMARY_REQUIRED_CHECK:
        return
    from thesis_review_workflow.cli.init_review_manifest import (
        helper_dependency_hashes,
        repo_root_from_round,
        workflow_checker_version,
    )

    current_version = workflow_checker_version(repo_root_from_round(round_dir))
    recorded_version = check.get("checker_version")
    if not isinstance(recorded_version, str) or not recorded_version:
        errors.append(f"{rel_path}: helper check {name} missing checker_version")
    elif recorded_version != current_version:
        errors.append(f"{rel_path}: helper check {name} checker_version is stale")

    recorded_dependencies = check.get("dependency_sha256")
    current_dependencies = helper_dependency_hashes(round_dir, str(name))
    if not isinstance(recorded_dependencies, dict):
        errors.append(f"{rel_path}: helper check {name} missing dependency_sha256")
    elif recorded_dependencies != current_dependencies:
        errors.append(f"{rel_path}: helper check {name} dependency_sha256 is stale")


def required_checks_for_review_approval(
    profile: ReviewApprovalProfile,
    round_dir: Path,
    review_basis_path: str,
) -> tuple[str, ...]:
    checks = list(profile.required_checks)
    if (
        profile.profile == "opponent-report-review"
        and report_calibration_review_basis_requires_check(round_dir, review_basis_path)
        and REPORT_CALIBRATION_REQUIRED_CHECK not in checks
    ):
        checks.append(REPORT_CALIBRATION_REQUIRED_CHECK)
    if (
        profile.profile in {"opponent-materials", "opponent-report-review"}
        and round_uses_theses_checker_summary(round_dir)
        and THESES_CHECKER_SUMMARY_REQUIRED_CHECK not in checks
    ):
        checks.append(THESES_CHECKER_SUMMARY_REQUIRED_CHECK)
    return tuple(checks)


def required_helper_targets_for_approval(name: str, round_dir: Path, approval_path: str) -> set[str]:
    if name == REPORT_CALIBRATION_REQUIRED_CHECK:
        return set(report_calibration_check_targets(round_dir))
    if name == THESES_CHECKER_SUMMARY_REQUIRED_CHECK:
        return {THESES_CHECKER_SUMMARY_REL}
    if name == "check-opponent-report:canonical":
        targets = {"work/opponent_report_trace.json", "outputs/oponent_podklady_revidovane.md"}
        if round_uses_theses_checker_summary(round_dir):
            targets.add(THESES_CHECKER_SUMMARY_REL)
        if (
            approval_path == "work/reviews/opponent_report_review.json"
            or (round_dir / "work" / "oponent_posudek_draft.md").is_file()
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
        if round_uses_theses_checker_summary(round_dir):
            targets.add(THESES_CHECKER_SUMMARY_REL)
        return targets
    return set()


def reviewer_matches_generator(
    manifest: dict[str, Any] | None,
    *,
    reviewed_artifact_path: str,
    reviewer_agent: str,
) -> bool:
    if not manifest:
        return False
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        return False
    for artifact in artifacts:
        if not isinstance(artifact, dict) or artifact.get("path") != reviewed_artifact_path:
            continue
        if artifact.get("review_scope") not in FINAL_REVIEW_SCOPES:
            return False
        generated = artifact.get("generated_by")
        if not isinstance(generated, list):
            return False
        for record in generated:
            if not isinstance(record, dict):
                continue
            contribution = str(record.get("contribution", "")).strip().lower()
            if contribution not in {"", "generation", "draft_generation", "initial_synthesis"}:
                continue
            generator_agent = str(record.get("agent", "")).strip()
            if (
                generator_agent
                and generator_agent not in {"manual", "not_recorded"}
                and generator_agent == reviewer_agent
            ):
                return True
    return False


def build_review_approval_payload(
    round_dir: Path,
    *,
    case_id: str,
    round_id: str,
    workflow_profile: str,
    reviewer_role: str,
    reviewer_agent: str,
    verdict: str,
    blocking_findings_count: int,
    reviewed_artifact_path: str,
    review_basis_path: str,
    checks_observed: list[str],
    limitations: list[str],
    timestamp: str,
    human_reviewer: str = "",
    notes: str = "",
    used_findings: str = "",
    manifest: dict[str, Any] | None = None,
    required_checks: tuple[str, ...] = (),
    approval_path: str = "work/reviews/review_record_review.json",
) -> dict[str, Any]:
    if verdict.strip().lower() not in APPROVED_VERDICTS:
        raise ValueError("review approval records are pass-only; keep failed reviews as findings, not approval JSON")
    if blocking_findings_count != 0:
        raise ValueError("approved/pass review approval records require blocking_findings_count=0")
    if not reviewer_agent.strip():
        raise ValueError("reviewer_agent or human reviewer identifier is required")
    if reviewer_matches_generator(
        manifest,
        reviewed_artifact_path=reviewed_artifact_path,
        reviewer_agent=reviewer_agent,
    ):
        raise ValueError("reviewer identity matches the recorded generator for this final artifact")
    for label, rel_path in (
        ("reviewed_artifact_path", reviewed_artifact_path),
        ("review_basis_path", review_basis_path),
    ):
        if not is_safe_round_relative_path(rel_path):
            raise ValueError(f"{label} must be relative inside the round")
        if not (round_dir / rel_path).is_file():
            raise ValueError(f"{label} file does not exist: {rel_path}")
    payload: dict[str, Any] = {
        "schema_version": REVIEW_APPROVAL_SCHEMA,
        "case_id": case_id,
        "round_id": round_id,
        "workflow_profile": workflow_profile,
        "reviewer_role": reviewer_role,
        "reviewer_agent": reviewer_agent,
        "verdict": verdict.strip().lower(),
        "blocking_findings_count": blocking_findings_count,
        "reviewed_artifact_path": reviewed_artifact_path,
        "reviewed_artifact_sha256": sha256_file(round_dir / reviewed_artifact_path),
        "review_basis_path": review_basis_path,
        "review_basis_sha256": sha256_file(round_dir / review_basis_path),
        "checks_observed": checks_observed,
        "limitations": limitations,
        "timestamp": timestamp,
    }
    if human_reviewer:
        payload["human_reviewer"] = human_reviewer
    if notes:
        payload["notes"] = notes
    if used_findings:
        payload["used_findings"] = used_findings
    errors = validate_required_checks(
        required_checks=required_checks,
        checks_observed=checks_observed,
        rel_path=approval_path,
        round_dir=round_dir,
        reviewed_artifact_path=reviewed_artifact_path,
        manifest=manifest,
    )
    errors.extend(
        validate_review_approval_payload(
            payload,
            approval_path,
            round_dir,
            case_id=case_id,
            round_id=round_id,
            reviewed_artifact_path=reviewed_artifact_path,
        )
    )
    if errors:
        raise ValueError("; ".join(errors))
    return payload


def load_review_approval(round_dir: Path, rel_path: str) -> tuple[dict[str, Any] | None, list[str]]:
    if not is_review_approval_path(rel_path):
        return None, [f"{rel_path}: unknown review approval path"]
    try:
        loaded = json.loads((round_dir / rel_path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, [f"{rel_path}: missing review approval record"]
    except OSError as exc:
        return None, [f"{rel_path}: cannot read review approval record: {exc}"]
    except json.JSONDecodeError as exc:
        return None, [f"{rel_path}: invalid JSON: {exc.msg}"]
    if not isinstance(loaded, dict):
        return None, [f"{rel_path}: review approval record must be a JSON object"]
    return loaded, []


def _require_string(payload: dict[str, Any], field: str, rel_path: str, errors: list[str]) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{rel_path}: {field} must be a non-empty string")
        return ""
    return value


def _require_hash_bound_path(
    payload: dict[str, Any],
    path_field: str,
    hash_field: str,
    rel_path: str,
    round_dir: Path,
    errors: list[str],
) -> str:
    path_value = _require_string(payload, path_field, rel_path, errors)
    if not path_value:
        return ""
    if not is_safe_round_relative_path(path_value):
        errors.append(f"{rel_path}: {path_field} must be relative inside the round")
        return ""
    path = round_dir / path_value
    if not path.is_file():
        errors.append(f"{rel_path}: {path_field} points to a missing file: {path_value}")
        return path_value
    recorded_hash = payload.get(hash_field)
    if not isinstance(recorded_hash, str) or not recorded_hash:
        errors.append(f"{rel_path}: {hash_field} must be a non-empty string")
    elif recorded_hash != sha256_file(path):
        if hash_field == "review_basis_sha256":
            errors.append(f"{rel_path}: review basis changed after approval; {hash_field} is stale for {path_value}")
        else:
            errors.append(f"{rel_path}: {hash_field} is stale for {path_value}")
    return path_value


def validate_review_approval_payload(
    payload: dict[str, Any],
    rel_path: str,
    round_dir: Path,
    *,
    case_id: str | None = None,
    round_id: str | None = None,
    reviewed_artifact_path: str | None = None,
) -> list[str]:
    errors: list[str] = []
    schema = payload.get("schema_version")
    if schema not in {None, REVIEW_APPROVAL_SCHEMA}:
        errors.append(f"{rel_path}: schema_version must be {REVIEW_APPROVAL_SCHEMA}")
    _require_string(payload, "workflow_profile", rel_path, errors)
    _require_string(payload, "reviewer_role", rel_path, errors)
    _require_string(payload, "timestamp", rel_path, errors)
    blocking_findings_count = payload.get("blocking_findings_count")
    if not isinstance(blocking_findings_count, int) or blocking_findings_count < 0:
        errors.append(f"{rel_path}: blocking_findings_count must be a non-negative integer")
    elif blocking_findings_count != 0:
        errors.append(f"{rel_path}: approved/pass review must have blocking_findings_count 0")
    reviewer_agent = payload.get("reviewer_agent")
    if reviewer_agent is not None and not isinstance(reviewer_agent, str):
        errors.append(f"{rel_path}: reviewer_agent must be a string when present")
    notes = payload.get("notes")
    if notes is not None and not isinstance(notes, str):
        errors.append(f"{rel_path}: notes must be a string when present")
    if case_id is not None and payload.get("case_id") not in {None, case_id}:
        errors.append(f"{rel_path}: case_id does not match requested case")
    if round_id is not None and payload.get("round_id") not in {None, round_id}:
        errors.append(f"{rel_path}: round_id does not match requested round")

    verdict = payload.get("verdict")
    if not isinstance(verdict, str) or verdict.strip().lower() not in APPROVED_VERDICTS:
        errors.append(f"{rel_path}: verdict must be approved/pass")

    reviewed_path = _require_hash_bound_path(
        payload,
        "reviewed_artifact_path",
        "reviewed_artifact_sha256",
        rel_path,
        round_dir,
        errors,
    )
    if reviewed_artifact_path is not None and reviewed_path and reviewed_path != reviewed_artifact_path:
        errors.append(f"{rel_path}: reviewed_artifact_path must be {reviewed_artifact_path}")

    _require_hash_bound_path(
        payload,
        "review_basis_path",
        "review_basis_sha256",
        rel_path,
        round_dir,
        errors,
    )
    checks_observed = payload.get("checks_observed")
    if not isinstance(checks_observed, list):
        errors.append(f"{rel_path}: checks_observed must be a list")
    else:
        string_checks = [item for item in checks_observed if isinstance(item, str)]
        errors.extend(
            f"{rel_path}: {error}"
            for error in validate_helper_check_ids(
                string_checks,
                label="checks_observed",
                allow_observed_only=True,
            )
        )
        for index, item in enumerate(checks_observed, start=1):
            if not isinstance(item, str) or not item.strip():
                errors.append(f"{rel_path}: checks_observed item {index} must be a non-empty string")
        profile = canonical_profile_for_artifact(reviewed_path) if reviewed_path else None
        review_basis = payload.get("review_basis_path")
        if profile is not None and isinstance(review_basis, str):
            required_checks = required_checks_for_review_approval(profile, round_dir, review_basis)
            allowed_observed = set(required_checks)
            for name in sorted(set(string_checks) - allowed_observed):
                errors.append(
                    f"{rel_path}: unexpected observed check {name}; expected one of: "
                    f"{', '.join(sorted(allowed_observed))}"
                )
            if (
                REPORT_CALIBRATION_REQUIRED_CHECK in required_checks
                and REPORT_CALIBRATION_REQUIRED_CHECK not in checks_observed
            ):
                errors.append(f"{rel_path}: missing required observed check: {REPORT_CALIBRATION_REQUIRED_CHECK}")
    limitations = payload.get("limitations")
    if not isinstance(limitations, list):
        errors.append(f"{rel_path}: limitations must be a list")
    else:
        for index, item in enumerate(limitations, start=1):
            if not isinstance(item, str):
                errors.append(f"{rel_path}: limitations item {index} must be a string")
    return errors


def canonical_profile_for_artifact(reviewed_artifact_path: str) -> ReviewApprovalProfile | None:
    for profile in APPROVAL_PROFILES.values():
        if profile.reviewed_artifact_path == reviewed_artifact_path:
            return profile
    return None


def validate_review_approval_with_manifest(
    payload: dict[str, Any],
    rel_path: str,
    round_dir: Path,
    *,
    manifest: dict[str, Any],
    case_id: str | None = None,
    round_id: str | None = None,
    reviewed_artifact_path: str | None = None,
) -> list[str]:
    errors = validate_review_approval_payload(
        payload,
        rel_path,
        round_dir,
        case_id=case_id,
        round_id=round_id,
        reviewed_artifact_path=reviewed_artifact_path,
    )
    reviewed_path = payload.get("reviewed_artifact_path")
    if not isinstance(reviewed_path, str):
        return errors
    profile = canonical_profile_for_artifact(reviewed_path)
    if profile is not None:
        if rel_path != profile.approval_path:
            errors.append(f"{rel_path}: canonical approval path must be {profile.approval_path}")
        if payload.get("workflow_profile") != profile.workflow_profile:
            errors.append(f"{rel_path}: workflow_profile must be {profile.workflow_profile}")
        if payload.get("reviewer_role") != profile.reviewer_role:
            errors.append(f"{rel_path}: reviewer_role must be {profile.reviewer_role}")
        basis = payload.get("review_basis_path")
        if basis not in profile.review_basis_candidates:
            choices = ", ".join(profile.review_basis_candidates)
            errors.append(f"{rel_path}: review_basis_path must be one of: {choices}")
        checks = string_list(payload.get("checks_observed"))
        required_checks = required_checks_for_review_approval(
            profile, round_dir, basis if isinstance(basis, str) else ""
        )
        errors.extend(
            validate_required_checks(
                required_checks=required_checks,
                checks_observed=checks,
                rel_path=rel_path,
                round_dir=round_dir,
                reviewed_artifact_path=reviewed_path,
                manifest=manifest,
            )
        )
    elif output_spec(Path(reviewed_path).name) is not None:
        errors.append(f"{rel_path}: no canonical approval profile for known artifact {reviewed_path}")
    reviewer_agent = str(payload.get("reviewer_agent", "")).strip()
    if reviewer_agent and reviewer_matches_generator(
        manifest,
        reviewed_artifact_path=reviewed_path,
        reviewer_agent=reviewer_agent,
    ):
        errors.append(f"{rel_path}: reviewer identity matches the recorded generator")
    return errors


def validate_review_approval_artifact(
    round_dir: Path,
    rel_path: str,
    *,
    case_id: str | None = None,
    round_id: str | None = None,
    reviewed_artifact_path: str | None = None,
) -> list[str]:
    payload, errors = load_review_approval(round_dir, rel_path)
    if errors:
        return errors
    assert payload is not None
    return validate_review_approval_payload(
        payload,
        rel_path,
        round_dir,
        case_id=case_id,
        round_id=round_id,
        reviewed_artifact_path=reviewed_artifact_path,
    )


def review_record_from_approval(payload: dict[str, Any], approval_path: str) -> dict[str, Any]:
    return {
        "status": "reviewed",
        "reviewer_role": str(payload.get("reviewer_role") or "not_recorded"),
        "reviewer_agent": str(payload.get("reviewer_agent") or "manual"),
        "reviewed_at": str(payload.get("timestamp") or ""),
        "reviewed_hash": str(payload.get("reviewed_artifact_sha256") or ""),
        "covered_by_artifact": "",
        "used_findings": str(payload.get("used_findings") or ""),
        "exception": "",
        "notes": f"Imported from structured approval record `{approval_path}`.",
        "review_basis_path": str(payload.get("review_basis_path") or ""),
        "review_basis_sha256": str(payload.get("review_basis_sha256") or ""),
        "approval_record_path": approval_path,
        "checks_observed": string_list(payload.get("checks_observed")),
        "blocking_findings_count": payload.get("blocking_findings_count", 0),
    }


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
