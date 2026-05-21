"""Shared role-coverage inference for thesis review rounds."""

from __future__ import annotations

import hashlib
import json
import re
import tarfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from thesis_review_workflow.artifact_classification import (
    ARCHIVE_SUFFIXES,
    archive_entry_code_like,
    archive_may_be_code_from_name,
    archive_suffix,
    folded,
)
from thesis_review_workflow.artifact_registry import final_output_paths, opponent_final_output_paths
from thesis_review_workflow.paths import is_safe_round_relative_path
from thesis_review_workflow.reuse import (
    REUSE_INDEX_SCHEMA_VERSION,
    ROLE_PLAN_REUSE_ARTIFACTS,
    ArtifactRole,
    CoverageSatisfiedBy,
    NextAction,
    ReuseStatus,
    SourceClass,
    artifact_role_for_role_plan_role,
    coverage_satisfies_without_fresh_review,
    source_classes_for_role,
)
from thesis_review_workflow.theses_similarity import (
    THESES_SIMILARITY_ASSESSMENT_REL,
    THESES_SIMILARITY_REVIEW_REL,
    theses_similarity_materiality_evidence_present,
)
from thesis_review_workflow.theses_similarity_coverage import theses_similarity_silent_internal_evidence_satisfied

COVERAGE_REL = Path("work/agent_coverage.json")
REUSE_INDEX_REL = Path("work/reuse/reuse_index.json")
SCHEMA_VERSION = "agent-coverage-v1"
ROLE_STATUSES = {"required", "blocked", "not_applicable"}
REUSE_AWARE_ROLES = frozenset(ROLE_PLAN_REUSE_ARTIFACTS)
LIMITATION_TYPES = {
    "unavailable_evidence",
    "unavailable_tool",
    "manual_review_required",
    "not_material_to_final",
    "out_of_scope_for_round",
    "upstream_or_external_scope",
}
ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
UNSATISFIED_ROLE_LABEL_TOKENS = (
    "parent",
    "fallback",
    "limited",
    "failed",
    "failure",
    "nooutput",
    "missingoutput",
)

FINAL_OUTPUTS = final_output_paths()
OPPONENT_FINAL_OUTPUTS = opponent_final_output_paths()
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
    ".ipynb",
}


def is_optional_omen_limitation(role: str, limitation: dict[str, Any]) -> bool:
    if role != "code_quality":
        return False
    if str(limitation.get("type", "")).strip() != "unavailable_tool":
        return False
    tool = str(limitation.get("tool", "")).strip().lower()
    return tool == "omen"


GITHUB_MARKERS = (
    "inputs/github/",
    "work/github-intake/",
)
QUANTITATIVE_CLAIMS_REL = "work/quantitative_claims.json"


@dataclass(frozen=True)
class RoleSpec:
    role: str
    trigger: str
    skill: str
    evidence_path: str
    required_for: tuple[str, ...]
    requires_review: bool = False
    coverage_kind: str = "generator"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_safe_relative(value: str) -> bool:
    return is_safe_round_relative_path(value)


def load_json_object(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return loaded


def artifact_by_path(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    artifacts = manifest.get("artifacts")
    if isinstance(artifacts, list):
        for artifact in artifacts:
            if isinstance(artifact, dict) and isinstance(artifact.get("path"), str):
                result[artifact["path"]] = artifact
    work_artifacts = manifest.get("supporting_work_artifacts")
    if isinstance(work_artifacts, list):
        for artifact in work_artifacts:
            if isinstance(artifact, dict) and isinstance(artifact.get("path"), str):
                result.setdefault(artifact["path"], artifact)
    return result


def load_reuse_index(round_dir: Path) -> dict[str, Any] | None:
    try:
        return load_json_object(round_dir / REUSE_INDEX_REL)
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def reuse_decision_for_role(round_dir: Path, role: str) -> dict[str, Any] | None:
    artifact_role = artifact_role_for_role_plan_role(role)
    if artifact_role is None:
        return None
    index = load_reuse_index(round_dir)
    if not index:
        return None
    decisions = index.get("decisions")
    if not isinstance(decisions, list):
        return None
    for decision in decisions:
        if isinstance(decision, dict) and decision.get("artifact_role") == artifact_role.value:
            return decision
    return None


def reuse_decisions_for_role(index: dict[str, Any], role: str) -> list[dict[str, Any]]:
    artifact_role = artifact_role_for_role_plan_role(role)
    decisions = index.get("decisions")
    if artifact_role is None or not isinstance(decisions, list):
        return []
    return [
        decision
        for decision in decisions
        if isinstance(decision, dict) and decision.get("artifact_role") == artifact_role.value
    ]


def reuse_fields_for_role(round_dir: Path, role: str, artifact: dict[str, Any] | None) -> dict[str, Any]:
    decision = reuse_decision_for_role(round_dir, role)
    artifact_present = artifact is not None
    fields: dict[str, Any] = {
        "coverage_required": True,
        "fresh_review_required": True,
        "coverage_satisfied_by": (
            CoverageSatisfiedBy.FRESH_ROLE_REVIEW.value if artifact_present else CoverageSatisfiedBy.NOT_SATISFIED.value
        ),
        "reuse_index_path": REUSE_INDEX_REL.as_posix() if decision else "",
        "reuse_status": "",
        "reuse_next_action": "",
    }
    if role not in REUSE_AWARE_ROLES or decision is None:
        return fields

    status = decision.get("status")
    fields["reuse_status"] = status if isinstance(status, str) else ""
    next_action = decision.get("next_action")
    fields["reuse_next_action"] = next_action if isinstance(next_action, str) else ""
    if (
        artifact_present
        and status == ReuseStatus.UNCHANGED_REUSABLE.value
        and decision.get("fresh_semantic_review_required") is False
        and decision.get("coverage_satisfied_by") == CoverageSatisfiedBy.CURRENT_REVIEWED_ARTIFACT.value
    ):
        fields["fresh_review_required"] = False
        fields["coverage_satisfied_by"] = CoverageSatisfiedBy.CURRENT_REVIEWED_ARTIFACT.value
    elif status == ReuseStatus.CHANGED_DELTA_REQUIRED.value:
        fields["fresh_review_required"] = True
        fields["coverage_satisfied_by"] = (
            CoverageSatisfiedBy.FRESH_ROLE_REVIEW.value if artifact_present else CoverageSatisfiedBy.NOT_SATISFIED.value
        )
    return fields


def output_paths(round_dir: Path) -> set[str]:
    outputs = round_dir / "outputs"
    if not outputs.is_dir():
        return set()
    return {f"outputs/{path.name}" for path in outputs.glob("*.md") if path.is_file()}


def source_like_input_present(round_dir: Path) -> bool:
    source_dirs = ("inputs/code", "inputs/src", "inputs/source", "inputs/submission")
    return any((round_dir / directory).is_dir() for directory in source_dirs)


def is_archive_path(path: str) -> bool:
    value = Path(path)
    suffix = archive_suffix(value)
    return suffix in ARCHIVE_SUFFIXES


def archive_contains_code(path: Path, *, max_entries: int = 5000) -> bool:
    if not path.is_file():
        return archive_may_be_code_from_name(path)
    suffix = archive_suffix(path)
    names: list[str] = []
    try:
        if suffix == ".zip":
            with zipfile.ZipFile(path) as handle:
                for index, item in enumerate(handle.infolist()):
                    if index >= max_entries:
                        break
                    names.append(item.filename)
        elif suffix in {".tar", ".tar.gz", ".tar.bz2", ".tar.xz", ".tgz", ".tbz", ".tbz2", ".txz"}:
            with tarfile.open(path, mode="r:*") as handle:
                for index, member in enumerate(handle):
                    if index >= max_entries:
                        break
                    names.append(member.name)
        else:
            return archive_may_be_code_from_name(path)
    except (OSError, tarfile.TarError, zipfile.BadZipFile):
        return archive_may_be_code_from_name(path)
    if names:
        return any(archive_entry_code_like(name) for name in names)
    return archive_may_be_code_from_name(path)


def code_evidence_present(round_dir: Path, manifest: dict[str, Any]) -> bool:
    if (round_dir / "work" / "code").is_dir():
        return True
    if source_like_input_present(round_dir):
        return True
    for collection in ("inputs", "supporting_work_artifacts"):
        records = manifest.get(collection)
        if not isinstance(records, list):
            continue
        for item in records:
            if not isinstance(item, dict):
                continue
            path = str(item.get("path", "")).lower()
            kind = str(item.get("kind", "")).lower()
            if "/github/" in path or path.startswith("work/github-intake/"):
                return True
            if kind == "archive" or is_archive_path(path):
                if archive_contains_code(round_dir / str(item.get("path", ""))):
                    return True
    return False


def github_evidence_present(round_dir: Path, manifest: dict[str, Any]) -> bool:
    if (round_dir / "inputs" / "github").is_dir() or (round_dir / "work" / "github-intake").is_dir():
        return True
    for collection in ("inputs", "supporting_work_artifacts"):
        records = manifest.get(collection)
        if not isinstance(records, list):
            continue
        for item in records:
            if not isinstance(item, dict):
                continue
            path = str(item.get("path", "")).lower()
            if any(marker in path for marker in GITHUB_MARKERS):
                return True
    return False


def quantitative_claims_present(round_dir: Path, manifest: dict[str, Any]) -> bool:
    if (round_dir / QUANTITATIVE_CLAIMS_REL).is_file():
        return True
    records = manifest.get("supporting_work_artifacts")
    if not isinstance(records, list):
        return False
    for item in records:
        if isinstance(item, dict) and item.get("path") == QUANTITATIVE_CLAIMS_REL:
            return True
    return False


def theses_similarity_evidence_path(
    round_dir: Path,
    manifest: dict[str, Any],
    *,
    allowed_synthesis_paths: tuple[str, ...] = (),
) -> str:
    artifacts = artifact_by_path(manifest)
    if (round_dir / THESES_SIMILARITY_REVIEW_REL).is_file() or THESES_SIMILARITY_REVIEW_REL in artifacts:
        return THESES_SIMILARITY_REVIEW_REL
    if theses_similarity_silent_internal_evidence_satisfied(
        round_dir,
        manifest,
        allowed_synthesis_paths=allowed_synthesis_paths,
    ):
        return THESES_SIMILARITY_ASSESSMENT_REL
    return THESES_SIMILARITY_REVIEW_REL


def media_evidence_present(round_dir: Path) -> bool:
    candidate_bases = (
        round_dir / "inputs" / "media",
        round_dir / "inputs" / "figures",
        round_dir / "inputs" / "screenshots",
        round_dir / "inputs" / "demo",
        round_dir / "inputs" / "presentation",
        round_dir / "work" / "figure_media",
        round_dir / "work" / "thesis-source",
        round_dir / "work" / "demo",
        round_dir / "work" / "media",
    )
    for base in candidate_bases:
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix.lower() in MEDIA_SUFFIXES:
                return True
    inputs = round_dir / "inputs"
    if inputs.is_dir():
        for path in inputs.iterdir():
            if path.is_file() and path.suffix.lower() in MEDIA_SUFFIXES:
                return True
    return False


def literature_trigger_present(round_dir: Path, manifest: dict[str, Any]) -> bool:
    trigger_patterns = ("literature", "citation", "citace", "bibliography", "source-map", "reference-map")
    for collection in ("inputs", "notes", "supporting_work_artifacts"):
        records = manifest.get(collection)
        if not isinstance(records, list):
            continue
        for item in records:
            if not isinstance(item, dict):
                continue
            rel_path = folded(str(item.get("path", "")))
            if any(pattern in rel_path for pattern in trigger_patterns):
                return True
    for base_name in ("notes", "inputs", "work"):
        base = round_dir / base_name
        if not base.is_dir():
            continue
        for path in base.glob("*"):
            if any(pattern in folded(path.name) for pattern in trigger_patterns):
                return True
    return False


def inferred_role_specs(round_dir: Path, manifest: dict[str, Any]) -> dict[str, RoleSpec]:
    paths = output_paths(round_dir) | set(artifact_by_path(manifest))
    final_paths = tuple(sorted(paths & FINAL_OUTPUTS))
    opponent_paths = tuple(sorted(paths & OPPONENT_FINAL_OUTPUTS))
    specs: dict[str, RoleSpec] = {}

    if "outputs/feedback_student.md" in paths:
        specs["supervisor_feedback_review"] = RoleSpec(
            "supervisor_feedback_review",
            "student-facing supervisor feedback is present",
            "thesis-supervisor-feedback-review",
            "outputs/feedback_student.md",
            ("outputs/feedback_student.md",),
            requires_review=True,
            coverage_kind="review",
        )

    if "outputs/vedouci_posudek_revidovany.md" in paths:
        specs["supervisor_report_review"] = RoleSpec(
            "supervisor_report_review",
            "reviewed supervisor report is present",
            "thesis-supervisor-report-review",
            "outputs/vedouci_posudek_revidovany.md",
            ("outputs/vedouci_posudek_revidovany.md",),
            requires_review=True,
            coverage_kind="review",
        )

    if final_paths and code_evidence_present(round_dir, manifest):
        specs["code_consistency"] = RoleSpec(
            "code_consistency",
            "code evidence is available and feeds a final/synthesis artifact",
            "thesis-code-consistency",
            "outputs/code_consistency.md",
            final_paths,
        )
        specs["code_quality"] = RoleSpec(
            "code_quality",
            "code evidence is available and feeds a final/synthesis artifact",
            "thesis-code-quality-review",
            "outputs/code_quality_review.md",
            final_paths,
        )

    if final_paths and github_evidence_present(round_dir, manifest):
        specs["github_intake"] = RoleSpec(
            "github_intake",
            "GitHub repository or PR evidence is available for the round",
            "thesis-github-code-intake",
            "outputs/github_code_intake.md",
            final_paths,
        )

    if final_paths and quantitative_claims_present(round_dir, manifest):
        specs["quantitative_claims"] = RoleSpec(
            "quantitative_claims",
            "structured quantitative claims artifact feeds a final/synthesis artifact",
            "thesis-quantitative-claims-review",
            QUANTITATIVE_CLAIMS_REL,
            final_paths,
        )

    if final_paths and theses_similarity_materiality_evidence_present(round_dir):
        evidence_path = theses_similarity_evidence_path(
            round_dir,
            manifest,
            allowed_synthesis_paths=final_paths,
        )
        specs["theses_similarity"] = RoleSpec(
            "theses_similarity",
            "Theses.cz similarity-report evidence is available and feeds a final/synthesis artifact",
            "thesis-theses-similarity-review",
            evidence_path,
            final_paths,
        )

    if final_paths and media_evidence_present(round_dir):
        specs["figure_media"] = RoleSpec(
            "figure_media",
            "visual, media, slide, or notebook evidence is available for a final/synthesis artifact",
            "thesis-figure-media-review",
            "outputs/figure_media_review.md",
            final_paths,
        )

    if final_paths and (
        "outputs/literature_citation_review.md" in paths or literature_trigger_present(round_dir, manifest)
    ):
        specs["literature_citation"] = RoleSpec(
            "literature_citation",
            "literature/citation evidence is used by a final/synthesis artifact",
            "thesis-literature-citation-review",
            "outputs/literature_citation_review.md",
            final_paths,
        )

    if opponent_paths:
        specs["typography_formal"] = RoleSpec(
            "typography_formal",
            "opponent-stage final artifact needs late formal/typography calibration or an explicit limitation",
            "thesis-typography-formal-review",
            "outputs/typography_formal_review.md",
            opponent_paths,
        )

    if "outputs/oponent_podklady_revidovane.md" in paths:
        specs["opponent_materials_review"] = RoleSpec(
            "opponent_materials_review",
            "reviewed opponent materials are present",
            "thesis-opponent-materials-review",
            "outputs/oponent_podklady_revidovane.md",
            ("outputs/oponent_podklady_revidovane.md",),
            requires_review=True,
            coverage_kind="review",
        )

    if "outputs/feedback_k_posudku.md" in paths:
        specs["opponent_report_review"] = RoleSpec(
            "opponent_report_review",
            "opponent report review output is present",
            "thesis-opponent-report-review",
            "outputs/feedback_k_posudku.md",
            ("outputs/feedback_k_posudku.md",),
            requires_review=True,
            coverage_kind="review",
        )

    return specs


def first_recorded_generator(artifact: dict[str, Any] | None) -> tuple[str, str]:
    if not artifact:
        return "not_recorded", "not_recorded"
    generated = artifact.get("generated_by")
    if not isinstance(generated, list):
        role = str(artifact.get("producer_role", "")).strip() or "not_recorded"
        raw_agent = artifact.get("producer_agent")
        agent = raw_agent.strip() if isinstance(raw_agent, str) and raw_agent.strip() else "not_recorded"
        if agent == "not_recorded" and artifact.get("producer_type") == "human":
            agent = "human_reviewer"
        if role != "not_recorded" or agent != "not_recorded":
            return role, agent
        return "not_recorded", "not_recorded"
    fallback = ("not_recorded", "not_recorded")
    for item in generated:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "")).strip() or "not_recorded"
        agent = str(item.get("agent", "")).strip() or "not_recorded"
        if role != "not_recorded" and agent != "not_recorded":
            return role, agent
        fallback = (role, agent)
    return fallback


def normalized_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", folded(value))


def role_label_matches(value: str, spec: RoleSpec) -> bool:
    normalized = normalized_token(value)
    if not normalized or normalized == "notrecorded":
        return False
    candidates = {
        normalized_token(spec.role),
        normalized_token(spec.skill),
        normalized_token(spec.skill.removeprefix("thesis-")),
    }
    return any(candidate and candidate in normalized for candidate in candidates)


def label_indicates_unsatisfied_role(value: str) -> bool:
    normalized = normalized_token(value)
    return any(token in normalized for token in UNSATISFIED_ROLE_LABEL_TOKENS)


def review_fields(
    artifact: dict[str, Any] | None,
    artifacts: dict[str, dict[str, Any]],
) -> tuple[str, str, str]:
    if not artifact:
        return "not_recorded", "not_recorded", ""
    review = artifact.get("independent_review")
    if not isinstance(review, dict):
        return "not_recorded", "not_recorded", ""
    reviewed_hash = str(review.get("reviewed_hash", "")).strip()
    reviewer_role = str(review.get("reviewer_role", "")).strip() or "not_recorded"
    reviewer_agent = str(review.get("reviewer_agent", "")).strip() or "not_recorded"
    if reviewed_hash:
        return reviewer_role, reviewer_agent, reviewed_hash

    covered_by = str(review.get("covered_by_artifact", "")).strip()
    evidence_hash = str(review.get("evidence_hash", "")).strip()
    if covered_by and evidence_hash:
        covered_artifact = artifacts.get(covered_by)
        covered_review = covered_artifact.get("independent_review") if isinstance(covered_artifact, dict) else None
        if isinstance(covered_review, dict):
            role = str(covered_review.get("reviewer_role", "")).strip() or "not_recorded"
            agent = str(covered_review.get("reviewer_agent", "")).strip() or "not_recorded"
            return role, agent, evidence_hash
        return "covered_by_synthesis", "not_recorded", evidence_hash

    return reviewer_role, reviewer_agent, ""


def role_record_from_spec(spec: RoleSpec, artifacts: dict[str, dict[str, Any]], round_dir: Path) -> dict[str, Any]:
    artifact = artifacts.get(spec.evidence_path)
    generator_role, generator_agent = first_recorded_generator(artifact)
    reviewer_role, reviewer_agent, reviewed_hash = review_fields(artifact, artifacts)
    evidence = [spec.evidence_path] if artifact else []
    record: dict[str, Any] = {
        "role": spec.role,
        "status": "required",
        "trigger": spec.trigger,
        "skill": spec.skill,
        "required_for": list(spec.required_for),
        "output_evidence": evidence,
        "generator_role": generator_role,
        "generator_agent": generator_agent,
        "reviewer_role": reviewer_role,
        "reviewer_agent": reviewer_agent,
        "reviewed_hash": reviewed_hash,
        "typed_limitation": {},
        "notes": "",
    }
    record.update(reuse_fields_for_role(round_dir, spec.role, artifact))
    if spec.role == "theses_similarity" and spec.evidence_path == THESES_SIMILARITY_ASSESSMENT_REL:
        record["fresh_review_required"] = False
        record["coverage_satisfied_by"] = CoverageSatisfiedBy.SILENT_INTERNAL_EVIDENCE.value
    return record


def merge_role_record(generated: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, Any]:
    if not previous:
        return generated
    merged = dict(generated)
    previous_status = previous.get("status")
    if previous_status in {"blocked", "not_applicable"}:
        merged["status"] = previous_status
    for field in ("typed_limitation", "notes"):
        if previous.get(field):
            merged[field] = previous[field]
    if previous.get("status") == "blocked":
        merged["output_evidence"] = previous.get("output_evidence", merged["output_evidence"])
    return merged


def stale_role_record(previous: dict[str, Any]) -> dict[str, Any]:
    stale = dict(previous)
    stale["status"] = "not_applicable"
    stale["trigger"] = "stale: no current default trigger requires this role"
    stale["required_for"] = []
    stale["output_evidence"] = []
    stale["generator_role"] = "not_recorded"
    stale["generator_agent"] = "not_recorded"
    stale["reviewer_role"] = "not_recorded"
    stale["reviewer_agent"] = "not_recorded"
    stale["reviewed_hash"] = ""
    stale["typed_limitation"] = {}
    stale["coverage_required"] = False
    stale["fresh_review_required"] = False
    stale["coverage_satisfied_by"] = CoverageSatisfiedBy.TYPED_NO_MATERIAL_ISSUE.value
    stale["reuse_index_path"] = ""
    stale["reuse_status"] = ""
    stale["reuse_next_action"] = ""
    stale["notes"] = "Preserved from previous coverage but no longer inferred for this round state."
    return stale


def build_coverage(
    case_id: str,
    round_id: str,
    round_dir: Path,
    manifest: dict[str, Any],
    existing: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    specs = inferred_role_specs(round_dir, manifest)
    previous_roles: dict[str, dict[str, Any]] = {}
    if existing and isinstance(existing.get("roles"), list):
        for item in existing["roles"]:
            if isinstance(item, dict) and isinstance(item.get("role"), str):
                previous_roles[item["role"]] = item

    if not specs and not previous_roles:
        return None

    artifacts = artifact_by_path(manifest)
    roles = []
    for role in sorted(specs):
        roles.append(
            merge_role_record(role_record_from_spec(specs[role], artifacts, round_dir), previous_roles.get(role))
        )
    for role, previous in sorted(previous_roles.items()):
        if role not in specs:
            roles.append(stale_role_record(previous))

    return {
        "schema_version": SCHEMA_VERSION,
        "case_id": case_id,
        "round_id": round_id,
        "updated_at": now_utc(),
        "coverage_path": COVERAGE_REL.as_posix(),
        "roles": roles,
    }


def write_coverage(path: Path, coverage: dict[str, Any] | None) -> None:
    if coverage is None:
        if path.exists():
            path.unlink()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(coverage, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def validate_reuse_index_decision_for_coverage(
    round_dir: Path,
    *,
    role: str,
    case_id: str,
    round_id: str,
) -> list[str]:
    errors: list[str] = []
    artifact_role = artifact_role_for_role_plan_role(role)
    if artifact_role is None:
        return [f"{role}: fresh_review_required=false is only supported for reuse-aware roles"]
    index = load_reuse_index(round_dir)
    if index is None:
        return [f"{role}: fresh_review_required=false requires {REUSE_INDEX_REL.as_posix()}"]
    if index.get("schema_version") != REUSE_INDEX_SCHEMA_VERSION:
        errors.append(f"{role}: {REUSE_INDEX_REL.as_posix()} schema_version must be {REUSE_INDEX_SCHEMA_VERSION}")
    if index.get("case_id") != case_id:
        errors.append(f"{role}: {REUSE_INDEX_REL.as_posix()} case_id must be {case_id}")
    if index.get("round_id") != round_id:
        errors.append(f"{role}: {REUSE_INDEX_REL.as_posix()} round_id must be {round_id}")
    decisions = reuse_decisions_for_role(index, role)
    if not decisions:
        return errors + [f"{role}: {REUSE_INDEX_REL.as_posix()} has no decision for {artifact_role.value}"]
    if len(decisions) > 1:
        errors.append(f"{role}: {REUSE_INDEX_REL.as_posix()} must contain exactly one decision for {artifact_role}")
    decision = decisions[0]
    if decision.get("status") != ReuseStatus.UNCHANGED_REUSABLE.value:
        errors.append(f"{role}: reuse decision must be unchanged_reusable to skip a fresh semantic review")
    if decision.get("fresh_semantic_review_required") is not False:
        errors.append(f"{role}: reuse decision must set fresh_semantic_review_required=false")
    if decision.get("coverage_satisfied_by") != CoverageSatisfiedBy.CURRENT_REVIEWED_ARTIFACT.value:
        errors.append(f"{role}: reuse decision must be satisfied by current_reviewed_artifact")
    if decision.get("next_action") != NextAction.REUSE_EXISTING_REVIEW.value:
        errors.append(f"{role}: reuse decision next_action must be reuse_existing_review")
    for field in ("changed_refs", "added_refs", "removed_refs", "missing_current_refs", "not_comparable_refs"):
        values = decision.get(field)
        if values != []:
            errors.append(f"{role}: reuse decision {field} must be empty to skip a fresh semantic review")
    for field in ("missing_current_source_classes", "missing_prior_source_classes"):
        values = decision.get(field)
        if values != []:
            errors.append(f"{role}: reuse decision {field} must be empty to skip a fresh semantic review")
    current_hashes, current_errors = current_role_source_hashes_from_reuse_index(index, role)
    errors.extend(current_errors)
    relevant_classes = decision.get("relevant_source_classes")
    expected_classes = sorted(source_class.value for source_class in expected_reuse_source_classes(role))
    if not isinstance(relevant_classes, list) or sorted(str(item) for item in relevant_classes) != expected_classes:
        errors.append(f"{role}: reuse decision relevant_source_classes must match role source dependencies")
    source_sha256 = decision.get("source_sha256")
    if not isinstance(source_sha256, dict) or not source_sha256:
        errors.append(f"{role}: reuse decision must record non-empty source_sha256")
        return errors
    if not current_errors and {str(ref): str(digest) for ref, digest in source_sha256.items()} != current_hashes:
        errors.append(f"{role}: reuse decision source_sha256 must match current role source fingerprints")
    for ref, digest in source_sha256.items():
        if not isinstance(ref, str) or not is_safe_relative(ref):
            errors.append(f"{role}: reuse source ref must be relative inside the round: {ref}")
            continue
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            errors.append(f"{role}: reuse source hash must be a sha256 hex string for {ref}")
            continue
        path = round_dir / ref
        if not path.is_file():
            errors.append(f"{role}: reuse source ref does not exist: {ref}")
        elif sha256_file(path) != digest:
            errors.append(f"{role}: reuse source hash is stale for {ref}")
    return errors


def expected_reuse_artifact_role(role: str) -> ArtifactRole:
    artifact_role = artifact_role_for_role_plan_role(role)
    if artifact_role is None:
        raise KeyError(role)
    return artifact_role


def expected_reuse_source_classes(role: str) -> frozenset[SourceClass]:
    return source_classes_for_role(expected_reuse_artifact_role(role))


def current_role_source_hashes_from_reuse_index(index: dict[str, Any], role: str) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    expected_classes = expected_reuse_source_classes(role)
    expected_class_values = {source_class.value for source_class in expected_classes}
    records = index.get("current_source_fingerprints")
    if not isinstance(records, list):
        return {}, [f"{role}: reuse index current_source_fingerprints must be a list"]
    hashes: dict[str, str] = {}
    observed_classes: set[str] = set()
    for item in records:
        if not isinstance(item, dict):
            continue
        source_class = item.get("source_class")
        if source_class not in expected_class_values:
            continue
        ref = item.get("source_ref")
        digest = item.get("sha256")
        state = item.get("state")
        available = item.get("available", True)
        if not isinstance(source_class, str):
            continue
        if not isinstance(ref, str) or not is_safe_relative(ref):
            errors.append(f"{role}: reuse current source ref must be relative inside the round: {ref}")
            continue
        if available is not True or state != "comparable":
            errors.append(f"{role}: reuse current source must be comparable for {ref}")
            continue
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            errors.append(f"{role}: reuse current source hash must be sha256 for {ref}")
            continue
        observed_classes.add(source_class)
        hashes[ref] = digest
    missing = sorted(expected_class_values - observed_classes)
    if missing:
        errors.append(f"{role}: reuse index missing current source classes: {', '.join(missing)}")
    return hashes, errors


def coverage_required(round_dir: Path, manifest: dict[str, Any]) -> bool:
    return bool(inferred_role_specs(round_dir, manifest)) or (round_dir / COVERAGE_REL).is_file()


def inferred_coverage_required(round_dir: Path, manifest: dict[str, Any]) -> bool:
    return bool(inferred_role_specs(round_dir, manifest))


def validate_coverage(
    coverage: dict[str, Any] | None,
    manifest: dict[str, Any],
    case_id: str,
    round_id: str,
    round_dir: Path,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    specs = inferred_role_specs(round_dir, manifest)
    if coverage is None:
        if specs:
            errors.append(f"missing agent coverage: {COVERAGE_REL.as_posix()}")
        return errors, warnings

    if coverage.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"wrong agent coverage schema_version: expected {SCHEMA_VERSION}")
    if coverage.get("case_id") != case_id:
        errors.append("case_id in agent coverage does not match requested case")
    if coverage.get("round_id") != round_id:
        errors.append("round_id in agent coverage does not match requested round")
    if coverage.get("coverage_path", COVERAGE_REL.as_posix()) != COVERAGE_REL.as_posix():
        errors.append(f"coverage_path must be {COVERAGE_REL.as_posix()}")

    roles = coverage.get("roles")
    if not isinstance(roles, list):
        errors.append("roles must be a list")
        return errors, warnings

    records: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(roles, start=1):
        if not isinstance(record, dict):
            errors.append(f"roles item {index}: expected object")
            continue
        role = record.get("role")
        if not isinstance(role, str) or not ID_RE.fullmatch(role):
            errors.append(f"roles item {index}: invalid role id")
            continue
        if role in records:
            errors.append(f"duplicate role coverage entry: {role}")
        records[role] = record
        status = record.get("status")
        if status not in ROLE_STATUSES:
            errors.append(f"{role}: unknown status {status!r}")
        coverage_required_value = record.get("coverage_required")
        fresh_required_value = record.get("fresh_review_required")
        coverage_value = record.get("coverage_satisfied_by")
        if not isinstance(coverage_required_value, bool):
            errors.append(f"{role}: coverage_required must be a boolean")
        if not isinstance(fresh_required_value, bool):
            errors.append(f"{role}: fresh_review_required must be a boolean")
        coverage_mode: CoverageSatisfiedBy | None = None
        if not isinstance(coverage_value, str):
            errors.append(f"{role}: coverage_satisfied_by must be a string")
        else:
            try:
                coverage_mode = CoverageSatisfiedBy(coverage_value)
            except ValueError:
                allowed = [item.value for item in CoverageSatisfiedBy]
                errors.append(f"{role}: coverage_satisfied_by must be one of {allowed}")
        if status == "required" and coverage_required_value is not True:
            errors.append(f"{role}: required roles must set coverage_required=true")
        if status == "not_applicable" and coverage_required_value is not False:
            errors.append(f"{role}: not_applicable roles must set coverage_required=false")
        if coverage_required_value is False and fresh_required_value is True:
            errors.append(f"{role}: fresh_review_required must be false when coverage_required is false")
        if fresh_required_value is False and coverage_mode is not None:
            if not coverage_satisfies_without_fresh_review(coverage_mode):
                errors.append(f"{role}: non-fresh coverage must use a reusable coverage_satisfied_by value")
            if status == "required":
                if coverage_mode == CoverageSatisfiedBy.CURRENT_REVIEWED_ARTIFACT:
                    errors.extend(
                        validate_reuse_index_decision_for_coverage(
                            round_dir,
                            role=role,
                            case_id=case_id,
                            round_id=round_id,
                        )
                    )
                elif coverage_mode == CoverageSatisfiedBy.SILENT_INTERNAL_EVIDENCE and role == "theses_similarity":
                    spec = specs.get(role)
                    if spec is None or not theses_similarity_silent_internal_evidence_satisfied(
                        round_dir,
                        manifest,
                        allowed_synthesis_paths=spec.required_for,
                        case_id=case_id,
                        round_id=round_id,
                    ):
                        errors.append(
                            f"{role}: silent_internal_evidence requires a current no-concern assessment "
                            "covered by a reviewed synthesis artifact"
                        )
                else:
                    errors.append(
                        f"{role}: required non-fresh coverage must use current_reviewed_artifact "
                        "or theses_similarity silent_internal_evidence"
                    )
        if record.get("reuse_index_path") not in {"", None, REUSE_INDEX_REL.as_posix()}:
            errors.append(f"{role}: reuse_index_path must be {REUSE_INDEX_REL.as_posix()} when present")
        if record.get("reuse_status") not in {
            "",
            None,
            ReuseStatus.UNCHANGED_REUSABLE.value,
            ReuseStatus.CHANGED_DELTA_REQUIRED.value,
            ReuseStatus.STALE_OR_UNREVIEWED.value,
            ReuseStatus.NOT_COMPARABLE.value,
        }:
            errors.append(f"{role}: reuse_status is not recognized")
        if record.get("reuse_next_action") not in {
            "",
            None,
            NextAction.REUSE_EXISTING_REVIEW.value,
            NextAction.DELTA_REVIEW.value,
            NextAction.FRESH_ROLE_REVIEW.value,
            NextAction.MANUAL_LIMITATION.value,
            NextAction.NOT_COMPARABLE_BACKFILL.value,
        }:
            errors.append(f"{role}: reuse_next_action is not recognized")
        if fresh_required_value is False and record.get("reuse_status") == ReuseStatus.CHANGED_DELTA_REQUIRED.value:
            errors.append(f"{role}: changed_delta_required reuse cannot skip a fresh or delta semantic review")
        if not str(record.get("trigger", "")).strip():
            errors.append(f"{role}: missing trigger")
        if "required_for" in record and not isinstance(record.get("required_for"), list):
            errors.append(f"{role}: required_for must be a list")
        evidence = record.get("output_evidence", [])
        if not isinstance(evidence, list):
            errors.append(f"{role}: output_evidence must be a list")
        elif status != "not_applicable":
            for path in evidence:
                if not isinstance(path, str) or not is_safe_relative(path):
                    errors.append(f"{role}: output_evidence path must be relative inside the round: {path}")
                elif not (round_dir / path).is_file():
                    errors.append(f"{role}: output_evidence path does not exist: {path}")
        if status == "blocked":
            limitation = record.get("typed_limitation")
            if not isinstance(limitation, dict):
                errors.append(f"{role}: blocked role requires typed_limitation object")
            else:
                limitation_type = str(limitation.get("type", "")).strip()
                if limitation_type not in LIMITATION_TYPES:
                    errors.append(f"{role}: typed_limitation.type must be one of {', '.join(sorted(LIMITATION_TYPES))}")
                if is_optional_omen_limitation(role, limitation):
                    errors.append(
                        f"{role}: Omen is optional advisory evidence and cannot be the typed limitation "
                        "that blocks the code-quality role"
                    )
                if not str(limitation.get("description", "")).strip():
                    errors.append(f"{role}: blocked role requires typed_limitation.description")
                if limitation.get("role") not in {"", None, role}:
                    errors.append(f"{role}: typed_limitation.role must match the blocked role")

    artifacts = artifact_by_path(manifest)
    for role, spec in sorted(specs.items()):
        record = records.get(role)
        if not record:
            errors.append(f"missing required agent role coverage: {role}")
            continue
        status = record.get("status")
        if status == "not_applicable":
            errors.append(f"{role}: inferred required role is marked not_applicable")
            continue
        if status == "blocked":
            artifact = artifacts.get(spec.evidence_path)
            limitation = record.get("typed_limitation")
            if isinstance(limitation, dict):
                if limitation.get("role") != role:
                    errors.append(f"{role}: typed_limitation.role must match the blocked role")
                if str(limitation.get("trigger", "")).strip() != spec.trigger:
                    errors.append(f"{role}: typed_limitation.trigger must match the current trigger")
                limitation_for = limitation.get("required_for")
                if not isinstance(limitation_for, list) or sorted(str(item) for item in limitation_for) != sorted(
                    spec.required_for
                ):
                    errors.append(f"{role}: typed_limitation.required_for must match current required_for outputs")
                if artifact and limitation.get("evidence_unusable") is not True:
                    errors.append(
                        f"{role}: blocked role has evidence output; set typed_limitation.evidence_unusable=true "
                        "with rationale or mark the role required"
                    )
            continue

        if record.get("skill") != spec.skill:
            errors.append(f"{role}: expected skill {spec.skill}")
        evidence = record.get("output_evidence", [])
        if spec.evidence_path not in evidence:
            errors.append(f"{role}: missing required output evidence {spec.evidence_path}")
            continue
        artifact = artifacts.get(spec.evidence_path)
        if not artifact:
            errors.append(f"{role}: evidence artifact is not recorded in review manifest: {spec.evidence_path}")
            continue
        record_coverage_mode: CoverageSatisfiedBy | None = None
        record_coverage_value = record.get("coverage_satisfied_by")
        if isinstance(record_coverage_value, str):
            try:
                record_coverage_mode = CoverageSatisfiedBy(record_coverage_value)
            except ValueError:
                record_coverage_mode = None
        skills = artifact.get("skills")
        if isinstance(skills, list) and spec.skill not in skills:
            errors.append(f"{role}: manifest artifact {spec.evidence_path} does not record skill {spec.skill}")
        generator_role = str(record.get("generator_role", "")).strip()
        generator_agent = str(record.get("generator_agent", "")).strip()
        if generator_role in {"", "not_recorded"}:
            errors.append(f"{role}: required role must record generator_role")
        if generator_agent in {"", "not_recorded"}:
            errors.append(f"{role}: required role must record generator_agent")
        if spec.coverage_kind == "generator" and generator_role not in {"", "not_recorded"}:
            if not role_label_matches(generator_role, spec):
                errors.append(f"{role}: generator_role does not match expected role/skill {spec.skill}")
        if (
            status == "required"
            and record_coverage_mode == CoverageSatisfiedBy.FRESH_ROLE_REVIEW
            and spec.coverage_kind == "generator"
            and (label_indicates_unsatisfied_role(generator_role) or label_indicates_unsatisfied_role(generator_agent))
        ):
            errors.append(
                f"{role}: required fresh role coverage cannot be satisfied by a parent/fallback/limited "
                "generator; rerun the role or mark it blocked with a typed limitation before synthesis"
            )

        current_hash = artifact.get("artifact_sha256")
        evidence_file = round_dir / spec.evidence_path
        actual_hash = sha256_file(evidence_file) if evidence_file.is_file() else ""
        if actual_hash and current_hash != actual_hash:
            errors.append(f"{role}: manifest artifact hash is stale for {spec.evidence_path}")
        reviewed_hash = str(record.get("reviewed_hash", "")).strip()
        if reviewed_hash and reviewed_hash != current_hash:
            errors.append(f"{role}: reviewed_hash does not match manifest artifact hash for {spec.evidence_path}")
        if reviewed_hash and actual_hash and reviewed_hash != actual_hash:
            errors.append(f"{role}: reviewed_hash does not match current file hash for {spec.evidence_path}")
        if record.get("fresh_review_required") is False:
            reviewer_role = str(record.get("reviewer_role", "")).strip()
            reviewer_agent = str(record.get("reviewer_agent", "")).strip()
            if not reviewed_hash:
                errors.append(f"{role}: non-fresh reused coverage must record reviewed_hash")
            if reviewer_role in {"", "not_recorded"}:
                errors.append(f"{role}: non-fresh reused coverage must record reviewer_role")
            if reviewer_agent in {"", "not_recorded"}:
                errors.append(f"{role}: non-fresh reused coverage must record reviewer_agent")
        if spec.requires_review:
            reviewer_role = str(record.get("reviewer_role", "")).strip()
            reviewer_agent = str(record.get("reviewer_agent", "")).strip()
            if reviewer_role in {"", "not_recorded"}:
                errors.append(f"{role}: review role must record reviewer_role")
            if reviewer_agent in {"", "not_recorded"}:
                errors.append(f"{role}: review role must record reviewer_agent")
            if not reviewed_hash:
                errors.append(f"{role}: review role must record reviewed_hash")
            if reviewer_role not in {"", "not_recorded"} and not role_label_matches(reviewer_role, spec):
                errors.append(f"{role}: reviewer_role does not match expected role/skill {spec.skill}")
            if record_coverage_mode == CoverageSatisfiedBy.FRESH_ROLE_REVIEW and (
                label_indicates_unsatisfied_role(reviewer_role) or label_indicates_unsatisfied_role(reviewer_agent)
            ):
                errors.append(
                    f"{role}: required review coverage cannot be satisfied by a parent/fallback/limited "
                    "reviewer; rerun the review role or mark it blocked with a typed limitation before closeout"
                )

    for role in sorted(set(records) - set(specs)):
        status = records[role].get("status")
        if status == "required":
            errors.append(f"{role}: role is marked required but no default trigger currently requires it")

    return errors, warnings
