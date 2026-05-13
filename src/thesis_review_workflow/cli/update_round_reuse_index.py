"""Build a hash-bound advisory reuse index for a thesis round."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from thesis_review_workflow.agent_coverage import COVERAGE_REL
from thesis_review_workflow.cases import MissingCurrentRound, case_dir, read_current_round, repo_root, resolve_round
from thesis_review_workflow.code_workspace import workspace_source_fingerprints
from thesis_review_workflow.ids import validate_id
from thesis_review_workflow.paths import is_safe_round_relative_path, rel_repo
from thesis_review_workflow.pdf_extracts import (
    load_pdf_extract_manifest,
    pdf_extract_is_current,
    pdf_extract_sidecar_path,
    pdftotext_version,
    source_fingerprints_from_pdf_extract_manifest,
    write_pdf_extract_manifest,
)
from thesis_review_workflow.reuse import (
    REUSE_INDEX_SCHEMA_VERSION,
    ArtifactRole,
    CoverageSatisfiedBy,
    NextAction,
    ReuseStatus,
    SourceClass,
    SourceFingerprint,
    decide_reuse,
    reuse_decision_to_record,
    source_classes_for_role,
    source_fingerprint_to_record,
    stable_json_sha256,
)
from thesis_review_workflow.work_artifacts import sha256_file

REUSE_INDEX_REL = Path("work/reuse/reuse_index.json")
REUSE_INDEX_PRODUCER = "scripts/update-round-reuse-index"
GITHUB_SNAPSHOT_REL = Path("work/github-intake/snapshot-manifest.json")
CODE_WORKSPACE_MANIFEST_REL = Path("work/code/.prepare-code-workspace-manifest.json")
MEDIA_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
EXPERIMENT_SUFFIXES = {".csv", ".tsv", ".xlsx", ".xls", ".json", ".jsonl"}
REVIEWED_STATUSES = {"reviewed", "reviewed_with_notes"}
REQUIRED_REUSE_HELPER_CHECK = "check-agent-coverage"

ROLE_ARTIFACTS: dict[ArtifactRole, tuple[str, ...]] = {
    ArtifactRole.TEXT_ASSIGNMENT: ("work/assignment_coverage_agent.json",),
    ArtifactRole.CODE_CONSISTENCY: ("outputs/code_consistency.md",),
    ArtifactRole.CODE_QUALITY: ("outputs/code_quality_review.md",),
    ArtifactRole.QUANTITATIVE_CLAIMS: ("work/quantitative_claims.json",),
    ArtifactRole.LITERATURE_CITATION: ("outputs/literature_citation_review.md",),
    ArtifactRole.FIGURE_MEDIA: ("outputs/figure_media_review.md",),
    ArtifactRole.TYPOGRAPHY_FORMAL: ("outputs/typography_formal_review.md",),
    ArtifactRole.THESES_SIMILARITY: ("outputs/theses_similarity_review.md",),
    ArtifactRole.GITHUB_CODE_INTAKE: ("outputs/github_code_intake.md",),
    ArtifactRole.REVISION_DIFF: ("outputs/revision_diff.md",),
    ArtifactRole.SUPERVISOR_FEEDBACK: ("outputs/feedback_student.md",),
    ArtifactRole.SUPERVISOR_REPORT: ("outputs/vedouci_posudek_revidovany.md",),
    ArtifactRole.OPPONENT_MATERIALS: ("outputs/oponent_podklady_revidovane.md", "outputs/oponent_podklady.md"),
    ArtifactRole.OPPONENT_REPORT_REVIEW: ("outputs/feedback_k_posudku.md",),
}


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def usage() -> str:
    return (
        "Usage: scripts/update-round-reuse-index CASE_ID [ROUND_ID] [--backfill-current]\n\n"
        "Writes cases/<case>/rounds/<round>/work/reuse/reuse_index.json from existing sidecars and manifests."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/update-round-reuse-index",
        description="Build an advisory reuse index from current and previous round fingerprints.",
    )
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    parser.add_argument(
        "--backfill-current",
        action="store_true",
        help="write missing PDF extraction sidecars for existing current-round PDF/text pairs before indexing",
    )
    return parser


def git_ignored(root: Path, path: Path) -> bool:
    rel = rel_repo(root, path)
    return (
        subprocess.run(
            ["git", "-C", str(root), "check-ignore", "-q", rel],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0
    )


def round_rel(round_dir: Path, path: Path) -> str:
    return path.relative_to(round_dir).as_posix()


def safe_round_ref(round_dir: Path, path: Path) -> str | None:
    try:
        value = round_rel(round_dir, path)
    except ValueError:
        return None
    return value if is_safe_round_relative_path(value) else None


def source_fingerprint(
    round_dir: Path,
    path: Path,
    source_class: SourceClass,
    *,
    sha256: str | None,
    available: bool = True,
    schema_version: str = "",
    producer: str = "",
) -> SourceFingerprint | None:
    source_ref = safe_round_ref(round_dir, path)
    if source_ref is None:
        return None
    return SourceFingerprint(
        source_ref=source_ref,
        source_class=source_class,
        sha256=sha256,
        available=available,
        schema_version=schema_version,
        producer=producer,
    )


def manifest_round_path(round_dir: Path, manifest: dict[str, Any], section: str) -> Path | None:
    value = manifest.get(section)
    if not isinstance(value, dict):
        return None
    source_ref = value.get("path")
    if not isinstance(source_ref, str) or not is_safe_round_relative_path(source_ref):
        return None
    return round_dir / source_ref


def not_comparable_manifest_sources(round_dir: Path, manifest: dict[str, Any]) -> list[SourceFingerprint]:
    sources: list[SourceFingerprint] = []
    for section, source_class in (
        ("input_pdf", SourceClass.THESIS_PDF),
        ("output_text", SourceClass.THESIS_EXTRACT),
    ):
        path = manifest_round_path(round_dir, manifest, section)
        if path is None:
            continue
        fingerprint = source_fingerprint(round_dir, path, source_class, sha256=None)
        if fingerprint is not None:
            sources.append(fingerprint)
    return sources


def backfill_pdf_extract_sidecars(round_dir: Path) -> list[str]:
    extractor_version = pdftotext_version()
    if extractor_version == "unavailable":
        raise SystemExit("Cannot backfill PDF extraction sidecars because pdftotext is unavailable.")
    written: list[str] = []
    inputs_dir = round_dir / "inputs"
    extracted_dir = round_dir / "extracted"
    for input_pdf in sorted(inputs_dir.glob("*.pdf")) if inputs_dir.is_dir() else []:
        output_txt = extracted_dir / f"{input_pdf.stem}.txt"
        sidecar = pdf_extract_sidecar_path(output_txt)
        if sidecar.is_file() or not output_txt.is_file():
            continue
        write_pdf_extract_manifest(round_dir, input_pdf, output_txt, extractor_version=extractor_version)
        written.append(round_rel(round_dir, sidecar))
    return written


def collect_pdf_source_fingerprints(round_dir: Path) -> tuple[list[SourceFingerprint], list[str]]:
    sources: list[SourceFingerprint] = []
    notes: list[str] = []
    seen: set[tuple[str, SourceClass]] = set()
    extracted_dir = round_dir / "extracted"
    for sidecar in sorted(extracted_dir.glob("*.pdf-extract.json")) if extracted_dir.is_dir() else []:
        manifest = load_pdf_extract_manifest(sidecar)
        if manifest is None:
            notes.append(f"{round_rel(round_dir, sidecar)} is unreadable; PDF sources are not comparable.")
            continue
        input_pdf = manifest_round_path(round_dir, manifest, "input_pdf")
        output_txt = manifest_round_path(round_dir, manifest, "output_text")
        extractor = manifest.get("extractor")
        extractor_version = extractor.get("version") if isinstance(extractor, dict) else None
        if (
            input_pdf is None
            or output_txt is None
            or not isinstance(extractor_version, str)
            or not pdf_extract_is_current(round_dir, input_pdf, output_txt, extractor_version=extractor_version)
        ):
            for fingerprint in not_comparable_manifest_sources(round_dir, manifest):
                if fingerprint.key not in seen:
                    sources.append(fingerprint)
                    seen.add(fingerprint.key)
            notes.append(f"{round_rel(round_dir, sidecar)} is stale or incomplete; PDF sources are not comparable.")
            continue
        for fingerprint in source_fingerprints_from_pdf_extract_manifest(manifest):
            if fingerprint.key not in seen:
                sources.append(fingerprint)
                seen.add(fingerprint.key)

    inputs_dir = round_dir / "inputs"
    for input_pdf in sorted(inputs_dir.glob("*.pdf")) if inputs_dir.is_dir() else []:
        source_ref = safe_round_ref(round_dir, input_pdf)
        if source_ref is None or (source_ref, SourceClass.THESIS_PDF) in seen:
            continue
        sources.append(SourceFingerprint(source_ref, SourceClass.THESIS_PDF, None))
        seen.add((source_ref, SourceClass.THESIS_PDF))
        notes.append(f"{source_ref} has no PDF extraction sidecar; marked not_comparable.")

    for output_txt in sorted(extracted_dir.glob("*.txt")) if extracted_dir.is_dir() else []:
        source_ref = safe_round_ref(round_dir, output_txt)
        if source_ref is None or (source_ref, SourceClass.THESIS_EXTRACT) in seen:
            continue
        sources.append(SourceFingerprint(source_ref, SourceClass.THESIS_EXTRACT, None))
        seen.add((source_ref, SourceClass.THESIS_EXTRACT))
        notes.append(f"{source_ref} has no PDF extraction sidecar; marked not_comparable.")
    return sources, notes


def github_snapshot_identity(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "mode": payload.get("mode"),
        "no_checkout": payload.get("no_checkout"),
        "requested_repositories": payload.get("requested_repositories"),
        "requested_pull_requests": payload.get("requested_pull_requests"),
        "repositories": payload.get("repositories"),
        "pull_requests": payload.get("pull_requests"),
        "changed_file_list": payload.get("changed_file_list"),
        "checks_summary_sha256": payload.get("checks_summary_sha256"),
        "checkout_paths": payload.get("checkout_paths"),
        "limitations_sha256": payload.get("limitations_sha256"),
    }


def collect_github_source_fingerprints(round_dir: Path) -> tuple[list[SourceFingerprint], list[str]]:
    manifest_path = round_dir / GITHUB_SNAPSHOT_REL
    if manifest_path.is_file():
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            fingerprint = source_fingerprint(
                round_dir,
                manifest_path,
                SourceClass.GITHUB_SNAPSHOT,
                sha256=stable_json_sha256(github_snapshot_identity(payload)),
                schema_version=str(payload.get("schema_version") or ""),
                producer=str(payload.get("producer") or "scripts/import-github-code"),
            )
            return ([fingerprint] if fingerprint is not None else []), []
        source = source_fingerprint(round_dir, manifest_path, SourceClass.GITHUB_SNAPSHOT, sha256=None)
        return ([source] if source is not None else []), [f"{GITHUB_SNAPSHOT_REL.as_posix()} is unreadable."]
    if (round_dir / "inputs" / "github").exists() or (round_dir / "outputs" / "github_code_intake.md").is_file():
        source = source_fingerprint(round_dir, manifest_path, SourceClass.GITHUB_SNAPSHOT, sha256=None)
        if source is not None:
            return [source], [f"{GITHUB_SNAPSHOT_REL.as_posix()} is missing; GitHub snapshot is not comparable."]
    return [], []


def hash_artifact_sources(round_dir: Path, pattern: str, source_class: SourceClass) -> list[SourceFingerprint]:
    sources: list[SourceFingerprint] = []
    for path in sorted(round_dir.glob(pattern)):
        if not path.is_file():
            continue
        fingerprint = source_fingerprint(
            round_dir,
            path,
            source_class,
            sha256=sha256_file(path),
            schema_version=json_schema_version(path),
        )
        if fingerprint is not None:
            sources.append(fingerprint)
    return sources


def hash_existing_source(round_dir: Path, rel_path: str, source_class: SourceClass) -> SourceFingerprint | None:
    path = round_dir / rel_path
    if not path.is_file():
        return None
    return source_fingerprint(
        round_dir,
        path,
        source_class,
        sha256=sha256_file(path),
        schema_version=json_schema_version(path),
    )


def collect_structural_source_fingerprints(round_dir: Path) -> list[SourceFingerprint]:
    sources: list[SourceFingerprint] = []
    for rel_path, structural_source_class in (
        ("notes/assignment.md", SourceClass.ASSIGNMENT),
        ("notes/previous-feedback-index.md", SourceClass.PREVIOUS_FEEDBACK),
    ):
        fingerprint = hash_existing_source(round_dir, rel_path, structural_source_class)
        if fingerprint is not None:
            sources.append(fingerprint)

    notes_dir = round_dir / "notes"
    for path in sorted(notes_dir.glob("*.md")) if notes_dir.is_dir() else []:
        if path.name in {"assignment.md", "previous-feedback-index.md"}:
            continue
        fingerprint = source_fingerprint(round_dir, path, SourceClass.OPERATOR_NOTE, sha256=sha256_file(path))
        if fingerprint is not None:
            sources.append(fingerprint)

    inputs_dir = round_dir / "inputs"
    for path in sorted(inputs_dir.rglob("*")) if inputs_dir.is_dir() else []:
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        source_class: SourceClass | None = None
        if suffix in MEDIA_SUFFIXES:
            source_class = SourceClass.MEDIA
        elif suffix in EXPERIMENT_SUFFIXES and "github" not in path.relative_to(inputs_dir).parts:
            source_class = SourceClass.EXPERIMENT_RESULT
        if source_class is None:
            continue
        fingerprint = source_fingerprint(round_dir, path, source_class, sha256=sha256_file(path))
        if fingerprint is not None:
            sources.append(fingerprint)
    return sources


def json_schema_version(path: Path) -> str:
    if path.suffix.lower() != ".json":
        return ""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("schema_version") or "")


def collect_round_source_fingerprints(
    round_dir: Path, *, backfill_current: bool = False
) -> tuple[list[SourceFingerprint], list[str]]:
    notes: list[str] = []
    if backfill_current:
        written = backfill_pdf_extract_sidecars(round_dir)
        if written:
            notes.append("Backfilled PDF extraction sidecars: " + ", ".join(written))
    sources: list[SourceFingerprint] = []
    sources.extend(collect_structural_source_fingerprints(round_dir))
    pdf_sources, pdf_notes = collect_pdf_source_fingerprints(round_dir)
    sources.extend(pdf_sources)
    notes.extend(pdf_notes)
    code_sources = list(workspace_source_fingerprints(round_dir))
    if code_sources:
        sources.extend(code_sources)
    elif (round_dir / "work" / "code").exists():
        source = source_fingerprint(
            round_dir, round_dir / CODE_WORKSPACE_MANIFEST_REL, SourceClass.CODE_WORKSPACE, sha256=None
        )
        if source is not None:
            sources.append(source)
            notes.append(f"{CODE_WORKSPACE_MANIFEST_REL.as_posix()} is missing; code workspace is not comparable.")
    github_sources, github_notes = collect_github_source_fingerprints(round_dir)
    sources.extend(github_sources)
    notes.extend(github_notes)
    sources.extend(hash_artifact_sources(round_dir, "work/review_materiality/*.json", SourceClass.MATERIALITY_DECISION))
    return dedupe_sources(sources), notes


def dedupe_sources(sources: list[SourceFingerprint]) -> list[SourceFingerprint]:
    by_key: dict[tuple[str, SourceClass], SourceFingerprint] = {}
    for source in sources:
        existing = by_key.get(source.key)
        if existing is None or (not existing.comparable and source.comparable):
            by_key[source.key] = source
    return [by_key[key] for key in sorted(by_key, key=lambda item: (item[1].value, item[0]))]


def previous_round_ids(case_dir_path: Path, current_round_id: str) -> list[str]:
    rounds_dir = case_dir_path / "rounds"
    if not rounds_dir.is_dir():
        return []
    names = sorted(path.name for path in rounds_dir.iterdir() if path.is_dir() and not path.name.startswith("."))
    if current_round_id in names:
        return list(reversed(names[: names.index(current_round_id)]))
    return list(reversed([name for name in names if name != current_round_id]))


def load_review_manifest(round_dir: Path) -> dict[str, Any]:
    manifest_path = round_dir / "work" / "review_manifest.json"
    if not manifest_path.is_file():
        return {}
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def artifact_review_current(round_dir: Path, rel_path: str) -> bool:
    path = round_dir / rel_path
    if not path.is_file():
        return False
    current_hash = sha256_file(path)
    manifest = load_review_manifest(round_dir)
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        return False
    for item in artifacts:
        if not isinstance(item, dict) or item.get("path") != rel_path:
            continue
        if item.get("artifact_sha256") != current_hash:
            return False
        review = item.get("independent_review")
        if not isinstance(review, dict):
            return False
        if review.get("status") not in REVIEWED_STATUSES:
            return False
        if not (review.get("reviewed_hash") == current_hash or review.get("evidence_hash") == current_hash):
            return False
        return helper_checks_current_for_artifact(round_dir, manifest, rel_path, current_hash)
    return False


def helper_checks_current_for_artifact(
    round_dir: Path,
    manifest: dict[str, Any],
    rel_path: str,
    current_hash: str,
) -> bool:
    helper_checks = manifest.get("helper_checks")
    if not isinstance(helper_checks, list):
        return False
    coverage_rel = COVERAGE_REL.as_posix()
    coverage_path = round_dir / coverage_rel
    if not coverage_path.is_file():
        return False
    coverage_hash = sha256_file(coverage_path)
    targeted = [
        check
        for check in helper_checks
        if isinstance(check, dict)
        and check.get("check") == REQUIRED_REUSE_HELPER_CHECK
        and isinstance(check.get("target_artifacts"), list)
        and rel_path in check["target_artifacts"]
    ]
    if not targeted:
        return False
    for check in targeted:
        if check.get("status") != "passed" or check.get("exit_code") != 0:
            return False
        target_set = {target for target in check["target_artifacts"] if isinstance(target, str)}
        if not {rel_path, coverage_rel}.issubset(target_set):
            return False
        target_sha256 = check.get("target_sha256")
        if not isinstance(target_sha256, dict) or target_sha256.get(rel_path) != current_hash:
            return False
        if target_sha256.get(coverage_rel) != coverage_hash:
            return False
    return True


def candidate_artifacts(round_dir: Path, role: ArtifactRole) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for rel_path in ROLE_ARTIFACTS.get(role, ()):
        path = round_dir / rel_path
        if not path.is_file():
            continue
        records.append(
            {
                "path": rel_path,
                "sha256": sha256_file(path),
                "review_current": artifact_review_current(round_dir, rel_path),
            }
        )
    return records


def schema_compatible_for_role(
    current_sources: list[SourceFingerprint],
    prior_sources: list[SourceFingerprint],
    role: ArtifactRole,
) -> bool:
    prior_by_key = {source.key: source for source in prior_sources}
    relevant_classes = set(role_source_classes(role))
    for current in current_sources:
        if current.normalized_source_class not in relevant_classes:
            continue
        prior = prior_by_key.get(current.key)
        if prior is None:
            continue
        if current.schema_version and prior.schema_version and current.schema_version != prior.schema_version:
            return False
    return True


def role_source_classes(role: ArtifactRole) -> tuple[SourceClass, ...]:
    return tuple(source_classes_for_role(role))


def observed_comparable_classes(sources: list[SourceFingerprint]) -> set[SourceClass]:
    return {source.normalized_source_class for source in sources if source.comparable}


def missing_role_source_classes(role: ArtifactRole, sources: list[SourceFingerprint]) -> list[str]:
    observed = observed_comparable_classes(sources)
    return sorted(source_class.value for source_class in role_source_classes(role) if source_class not in observed)


def apply_source_coverage_guard(
    record: dict[str, object],
    role: ArtifactRole,
    current_sources: list[SourceFingerprint],
    prior_sources: list[SourceFingerprint],
) -> dict[str, object]:
    missing_current = missing_role_source_classes(role, current_sources)
    missing_prior = missing_role_source_classes(role, prior_sources)
    record["missing_current_source_classes"] = missing_current
    record["missing_prior_source_classes"] = missing_prior
    if not (missing_current or missing_prior) or record.get("status") == ReuseStatus.NOT_COMPARABLE.value:
        return record
    guarded = dict(record)
    guarded["status"] = ReuseStatus.NOT_COMPARABLE.value
    guarded["fresh_semantic_review_required"] = True
    guarded["coverage_satisfied_by"] = CoverageSatisfiedBy.NOT_SATISFIED.value
    guarded["next_action"] = NextAction.NOT_COMPARABLE_BACKFILL.value
    reason_value = guarded.get("reasons")
    reasons = [item for item in reason_value if isinstance(item, str)] if isinstance(reason_value, list) else []
    reasons.append("role source coverage is incomplete")
    guarded["reasons"] = reasons
    return guarded


def decision_record_for_role(
    role: ArtifactRole,
    current_sources: list[SourceFingerprint],
    prior_round_dir: Path,
    prior_sources: list[SourceFingerprint],
) -> dict[str, object]:
    artifacts = candidate_artifacts(prior_round_dir, role)
    prior_review_current = any(bool(item.get("review_current")) for item in artifacts)
    decision = decide_reuse(
        artifact_role=role,
        current_sources=current_sources,
        prior_sources=prior_sources,
        prior_review_current=prior_review_current,
        schema_compatible=schema_compatible_for_role(current_sources, prior_sources, role),
        coverage_satisfied_by=(
            CoverageSatisfiedBy.CURRENT_REVIEWED_ARTIFACT if prior_review_current else CoverageSatisfiedBy.NOT_SATISFIED
        ),
    )
    record = reuse_decision_to_record(decision)
    record["candidate_round_id"] = prior_round_dir.name
    record["candidate_artifacts"] = artifacts
    return apply_source_coverage_guard(record, role, current_sources, prior_sources)


def no_candidate_decision(role: ArtifactRole) -> dict[str, object]:
    return {
        "artifact_role": role.value,
        "candidate_round_id": None,
        "candidate_artifacts": [],
        "status": ReuseStatus.NOT_COMPARABLE.value,
        "fresh_semantic_review_required": True,
        "coverage_satisfied_by": CoverageSatisfiedBy.NOT_SATISFIED.value,
        "next_action": NextAction.NOT_COMPARABLE_BACKFILL.value,
        "reasons": ["no previous round candidate"],
        "source_sha256": {},
        "unchanged_refs": [],
        "changed_refs": [],
        "added_refs": [],
        "removed_refs": [],
        "missing_current_refs": [],
        "not_comparable_refs": [],
    }


def build_reuse_index(
    *,
    case_id: str,
    current_round_id: str,
    case_dir_path: Path,
    current_sources: list[SourceFingerprint],
    current_notes: list[str],
) -> dict[str, object]:
    previous_ids = previous_round_ids(case_dir_path, current_round_id)
    prior_records: list[dict[str, object]] = []
    prior_source_cache: dict[str, list[SourceFingerprint]] = {}
    for prior_id in previous_ids:
        prior_round_dir = case_dir_path / "rounds" / prior_id
        prior_sources, prior_notes = collect_round_source_fingerprints(prior_round_dir)
        prior_source_cache[prior_id] = prior_sources
        artifact_candidates = {}
        for role in ROLE_ARTIFACTS:
            artifacts = candidate_artifacts(prior_round_dir, role)
            if artifacts:
                artifact_candidates[role.value] = artifacts
        prior_records.append(
            {
                "round_id": prior_id,
                "source_fingerprint_count": len(prior_sources),
                "not_comparable_count": sum(1 for source in prior_sources if not source.comparable),
                "candidate_artifacts": artifact_candidates,
                "notes": prior_notes,
            }
        )

    decisions: list[dict[str, object]] = []
    for role in ArtifactRole:
        if role in {ArtifactRole.COMMON_BRIEFING, ArtifactRole.ROLE_PACKET}:
            continue
        decisions.append(select_role_decision(role, current_sources, case_dir_path, previous_ids, prior_source_cache))

    return {
        "schema_version": REUSE_INDEX_SCHEMA_VERSION,
        "case_id": case_id,
        "round_id": current_round_id,
        "generated_at": utc_now(),
        "producer": REUSE_INDEX_PRODUCER,
        "current_source_fingerprints": [source_fingerprint_to_record(source) for source in current_sources],
        "previous_round_candidates": prior_records,
        "decisions": decisions,
        "limitations": current_notes,
    }


def select_role_decision(
    role: ArtifactRole,
    current_sources: list[SourceFingerprint],
    case_dir_path: Path,
    previous_ids: list[str],
    prior_source_cache: dict[str, list[SourceFingerprint]],
) -> dict[str, object]:
    if not previous_ids:
        return no_candidate_decision(role)
    candidate_decisions = [
        decision_record_for_role(
            role,
            current_sources,
            case_dir_path / "rounds" / prior_id,
            prior_source_cache[prior_id],
        )
        for prior_id in previous_ids
    ]
    selected = sorted(candidate_decisions, key=candidate_decision_rank)[0]
    result = dict(selected)
    result["candidate_decisions"] = candidate_decisions
    return result


def candidate_decision_rank(record: dict[str, object]) -> tuple[int, int]:
    if not record.get("candidate_artifacts"):
        return (4, 0)
    status = record.get("status")
    if status == ReuseStatus.UNCHANGED_REUSABLE.value:
        return (0, 0)
    if status == ReuseStatus.CHANGED_DELTA_REQUIRED.value:
        return (1, 0)
    if status == ReuseStatus.STALE_OR_UNREVIEWED.value:
        return (2, 0)
    return (3, 0)


def write_reuse_index(root: Path, round_dir: Path, index: dict[str, object]) -> Path:
    output = round_dir / REUSE_INDEX_REL
    output.parent.mkdir(parents=True, exist_ok=True)
    if not git_ignored(root, output):
        raise SystemExit(f"Refusing to write reuse index to a non-ignored path: {rel_repo(root, output)}")
    output.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output


def main(argv: list[str]) -> int:
    if any(arg in {"-h", "--help"} for arg in argv[1:]):
        print(usage())
        return 0
    parser = build_parser()
    args = parser.parse_args(argv[1:])

    try:
        validate_id("CASE_ID", args.case_id)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.round_id:
        try:
            validate_id("ROUND_ID", args.round_id)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2

    root = repo_root()
    case_dir_path = case_dir(root, args.case_id)
    if not case_dir_path.is_dir():
        print(f"Case does not exist: cases/{args.case_id}", file=sys.stderr)
        return 1
    try:
        round_id = resolve_round(case_dir_path, args.round_id)
    except MissingCurrentRound as exc:
        print(str(exc), file=sys.stderr)
        return 1
    round_dir = case_dir_path / "rounds" / round_id
    if not round_dir.is_dir():
        print(f"Round does not exist: cases/{args.case_id}/rounds/{round_id}", file=sys.stderr)
        return 1
    if args.backfill_current:
        active_round_id = read_current_round(case_dir_path)
        if active_round_id is None:
            print("--backfill-current requires cases/<case>/current-round.txt", file=sys.stderr)
            return 1
        if round_id != active_round_id:
            print(
                f"--backfill-current may only target the active current round ({active_round_id}), not {round_id}.",
                file=sys.stderr,
            )
            return 2

    current_sources, current_notes = collect_round_source_fingerprints(
        round_dir,
        backfill_current=args.backfill_current,
    )
    index = build_reuse_index(
        case_id=args.case_id,
        current_round_id=round_id,
        case_dir_path=case_dir_path,
        current_sources=current_sources,
        current_notes=current_notes,
    )
    output = write_reuse_index(root, round_dir, index)
    print(f"Round reuse index written: {rel_repo(root, output)}")
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
