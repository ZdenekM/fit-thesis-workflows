"""Shared role-coverage inference for thesis review rounds."""

from __future__ import annotations

import hashlib
import json
import re
import tarfile
import unicodedata
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from thesis_review_workflow.artifact_registry import final_output_paths, opponent_final_output_paths
from thesis_review_workflow.paths import is_safe_round_relative_path
from thesis_review_workflow.theses_similarity import (
    THESES_SIMILARITY_REVIEW_REL,
    theses_similarity_materiality_evidence_present,
)

COVERAGE_REL = Path("work/agent_coverage.json")
SCHEMA_VERSION = "agent-coverage-v1"
ROLE_STATUSES = {"required", "blocked", "not_applicable"}
LIMITATION_TYPES = {
    "unavailable_evidence",
    "unavailable_tool",
    "manual_review_required",
    "not_material_to_final",
    "out_of_scope_for_round",
    "upstream_or_external_scope",
}
ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")

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
ARCHIVE_SUFFIXES = {
    ".zip",
    ".tar",
    ".tgz",
    ".tbz",
    ".tbz2",
    ".txz",
    ".gz",
    ".bz2",
    ".xz",
    ".7z",
    ".rar",
}
CODE_SUFFIXES = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".kt",
    ".cs",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".swift",
    ".ipynb",
    ".sql",
    ".r",
    ".m",
    ".jl",
}
CODE_DEPENDENCY_NAMES = {
    "requirements.txt",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "pom.xml",
    "build.gradle",
    "settings.gradle",
    "Cargo.toml",
    "Cargo.lock",
    "go.mod",
    "go.sum",
    "Dockerfile",
    "docker-compose.yml",
    "compose.yml",
}
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


def output_paths(round_dir: Path) -> set[str]:
    outputs = round_dir / "outputs"
    if not outputs.is_dir():
        return set()
    return {f"outputs/{path.name}" for path in outputs.glob("*.md") if path.is_file()}


def source_like_input_present(round_dir: Path) -> bool:
    source_dirs = ("inputs/code", "inputs/src", "inputs/source", "inputs/submission")
    return any((round_dir / directory).is_dir() for directory in source_dirs)


def folded(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    return ascii_text.lower()


def archive_suffix(path: Path) -> str:
    suffixes = [suffix.lower() for suffix in path.suffixes]
    if len(suffixes) >= 2 and suffixes[-2:] in (
        [".tar", ".gz"],
        [".tar", ".bz2"],
        [".tar", ".xz"],
    ):
        return "".join(suffixes[-2:])
    return suffixes[-1] if suffixes else ""


def is_archive_path(path: str) -> bool:
    value = Path(path)
    suffix = archive_suffix(value)
    return suffix in ARCHIVE_SUFFIXES or any(path.lower().endswith(item) for item in (".tar.gz", ".tar.bz2", ".tar.xz"))


def archive_may_be_code_from_name(path: Path) -> bool:
    name = folded(path.name)
    source_text_tokens = (
        "thesis",
        "latex",
        "overleaf",
        "zadani",
        "assignment",
        "prace",
        "bakalar",
        "diplom",
        "report",
    )
    if any(token in name for token in source_text_tokens):
        return False
    code_tokens = (
        "code",
        "src",
        "source",
        "repo",
        "project",
        "app",
        "software",
        "implementation",
        "submission",
    )
    if any(token in name for token in code_tokens):
        return True
    return True


def archive_entry_code_like(name: str) -> bool:
    pure_name = Path(name).name
    lower = name.lower()
    return (
        pure_name in CODE_DEPENDENCY_NAMES
        or Path(pure_name).suffix.lower() in CODE_SUFFIXES
        or "/test/" in lower
        or "/tests/" in lower
        or lower.startswith("test/")
        or lower.startswith("tests/")
    )


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
        specs["theses_similarity"] = RoleSpec(
            "theses_similarity",
            "Theses.cz similarity-report evidence is available and feeds a final/synthesis artifact",
            "thesis-theses-similarity-review",
            THESES_SIMILARITY_REVIEW_REL,
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


def role_record_from_spec(spec: RoleSpec, artifacts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    artifact = artifacts.get(spec.evidence_path)
    generator_role, generator_agent = first_recorded_generator(artifact)
    reviewer_role, reviewer_agent, reviewed_hash = review_fields(artifact, artifacts)
    evidence = [spec.evidence_path] if artifact else []
    return {
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
        roles.append(merge_role_record(role_record_from_spec(specs[role], artifacts), previous_roles.get(role)))
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

    for role in sorted(set(records) - set(specs)):
        status = records[role].get("status")
        if status == "required":
            errors.append(f"{role}: role is marked required but no default trigger currently requires it")

    return errors, warnings
