"""Bounded structural inventory for submitted parent bundles."""

from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import tarfile
import unicodedata
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from thesis_review_workflow.artifact_classification import (
    SUPPORTED_ARCHIVE_SUFFIXES,
    UNSUPPORTED_ARCHIVE_SUFFIXES,
    archive_entry_code_like,
    archive_suffix,
    classify_path_evidence,
    normalize_artifact_path,
)
from thesis_review_workflow.artifact_metadata import structural_metadata_for_artifact
from thesis_review_workflow.paths import is_safe_round_relative_path

SUBMISSION_BUNDLE_INVENTORY_SCHEMA = "submission-bundle-inventory-v1"
SUBMISSION_BUNDLE_INVENTORY_REL = "work/submission_bundle_inventory.json"
SUBMISSION_BUNDLE_INVENTORY_SUMMARY_REL = "work/submission_bundle_inventory.md"
SUBMISSION_BUNDLE_MATERIALIZATION_SCHEMA = "submission-bundle-materialization-v1"
SUBMISSION_BUNDLE_MATERIALIZATION_REL = "work/submission_bundle_materialization.json"
SUBMISSION_BUNDLE_EXPANSION_SCHEMA = "submission-bundle-expansion-v1"
SUBMISSION_BUNDLE_EXPANSION_REL = "work/submission_bundle_expansion.json"
SUBMISSION_BUNDLE_EXPANDED_ROOT_REL = "work/submission_bundle"
SUBMISSION_BUNDLE_PRODUCER = "scripts/inventory-submission-bundle"
SUBMISSION_BUNDLE_ROUND_START_PRODUCER = "scripts/review-round-start"
SUBMISSION_BUNDLE_MATERIALIZATION_PRODUCER = "scripts/materialize-submission-bundle-candidate"
SUBMISSION_BUNDLE_EXPANSION_PRODUCER = "scripts/materialize-submission-bundle"
SUBMISSION_BUNDLE_VISIBILITY_SCHEMA = "submission-bundle-visibility-v1"
SUBMISSION_BUNDLE_VISIBILITY_REFS = (
    SUBMISSION_BUNDLE_INVENTORY_REL,
    SUBMISSION_BUNDLE_INVENTORY_SUMMARY_REL,
    SUBMISSION_BUNDLE_MATERIALIZATION_REL,
    SUBMISSION_BUNDLE_EXPANSION_REL,
)

ACTIONABLE_CLASSES = {
    "assignment_pdf_candidate",
    "code_archive_candidate",
    "executable_artifact",
    "media_artifact",
    "pdf_artifact",
    "readme_candidate",
    "supported_archive",
    "thesis_pdf_candidate",
    "thesis_source_archive_candidate",
    "unsupported_archive",
}
AMBIGUOUS_CLASSES = {
    "assignment_pdf_candidate",
    "code_archive_candidate",
    "readme_candidate",
    "thesis_pdf_candidate",
    "thesis_source_archive_candidate",
}


@dataclass(frozen=True)
class BundleInventoryLimits:
    max_archive_bytes: int = 20 * 1024 * 1024 * 1024
    max_nested_archive_bytes: int = 64 * 1024 * 1024
    max_hash_bytes: int = 32 * 1024 * 1024
    max_read_bytes: int = 128 * 1024 * 1024
    max_entries: int = 5000
    max_archive_depth: int = 2

    def as_record(self) -> dict[str, int]:
        return {
            "max_archive_bytes": self.max_archive_bytes,
            "max_nested_archive_bytes": self.max_nested_archive_bytes,
            "max_hash_bytes": self.max_hash_bytes,
            "max_read_bytes": self.max_read_bytes,
            "max_entries": self.max_entries,
            "max_archive_depth": self.max_archive_depth,
        }


@dataclass(frozen=True)
class BundleExpansionLimits:
    max_total_bytes: int = 20 * 1024 * 1024 * 1024
    max_file_bytes: int = 5 * 1024 * 1024 * 1024
    max_entries: int = 100_000
    max_archive_depth: int = 4

    def as_record(self) -> dict[str, int]:
        return {
            "max_total_bytes": self.max_total_bytes,
            "max_file_bytes": self.max_file_bytes,
            "max_entries": self.max_entries,
            "max_archive_depth": self.max_archive_depth,
        }


@dataclass(frozen=True)
class SourceBundle:
    ref: str
    path: Path
    kind: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class ArchiveMember:
    name: str
    size_bytes: int
    is_dir: bool
    data: bytes | None


@dataclass(frozen=True)
class MaterializedCandidate:
    candidate: dict[str, Any]
    materialized_ref: str
    materialized_path: Path
    materialized_sha256: str
    manifest_path: Path
    action: str


@dataclass
class ReadBudget:
    limit: int
    used: int = 0
    skipped: list[str] = field(default_factory=list)

    def reserve(self, label: str, size: int) -> bool:
        if size < 0:
            self.skipped.append(f"{label}: negative archive member size")
            return False
        if self.used + size > self.limit:
            self.skipped.append(f"{label}: read budget {format_bytes(self.limit)} would be exceeded")
            return False
        self.used += size
        return True


@dataclass
class ExpansionBudget:
    limit: int
    used: int = 0

    def reserve(self, label: str, size: int) -> str | None:
        if size < 0:
            return f"{label}: negative archive member size"
        if self.used + size > self.limit:
            return f"{label}: total expansion limit {format_bytes(self.limit)} would be exceeded"
        self.used += size
        return None


@dataclass
class ExpansionStats:
    source_ref: str
    target_ref: str
    files_written: int = 0
    directories_written: int = 0
    archives_expanded: int = 0
    bytes_written: int = 0
    entries_seen: int = 0
    skipped_entries: list[dict[str, Any]] = field(default_factory=list)


class PortablePathRegistry:
    """Detect archive paths that cannot coexist on case-insensitive systems."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, ...], tuple[str, str]] = {}

    def register(self, rel_path: str, *, kind: str) -> str | None:
        parts = tuple(PurePosixPath(rel_path).parts)
        pending: list[tuple[tuple[str, ...], tuple[str, str]]] = []
        for index in range(1, len(parts) + 1):
            prefix = parts[:index]
            display = PurePosixPath(*prefix).as_posix()
            key = tuple(part.casefold() for part in prefix)
            record_kind = kind if index == len(parts) else "directory"
            existing = self._records.get(key)
            if existing is not None:
                existing_display, existing_kind = existing
                if existing_display != display:
                    return f"case-insensitive path collision with {existing_display}"
                if existing_kind != record_kind:
                    return f"path type collision with {existing_kind} {existing_display}"
                if index == len(parts):
                    return f"duplicate {record_kind} path {existing_display}"
            pending.append((key, (display, record_kind)))
        for key, record in pending:
            self._records.setdefault(key, record)
        return None


def path_collision_reason_code(detail: str) -> str:
    if detail.startswith("duplicate "):
        return "duplicate_path"
    return "case_insensitive_path_collision"


def reserve_expansion_entry(
    stats: ExpansionStats,
    *,
    chain: tuple[str, ...],
    limits: BundleExpansionLimits,
    archive_depth: int,
    detail: str,
) -> bool:
    if stats.entries_seen >= limits.max_entries:
        expansion_skip(
            stats,
            chain=chain,
            reason_code="entry_count_limit_reached",
            detail=detail,
            archive_depth=archive_depth,
        )
        return False
    stats.entries_seen += 1
    return True


WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}
WINDOWS_INVALID_CHARS_RE = re.compile(r'[<>:"|?*]')


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_directory(path: Path, limits: BundleInventoryLimits) -> tuple[str, int, bool]:
    digest = hashlib.sha256()
    digest.update(b"submission-bundle-directory-v1\0")
    files_seen = 0
    truncated = False
    for child in sorted(path.rglob("*"), key=lambda item: item.as_posix()):
        if child.is_symlink() or not child.is_file():
            continue
        files_seen += 1
        if files_seen > limits.max_entries:
            truncated = True
            digest.update(b"\0truncated")
            break
        rel = child.relative_to(path).as_posix()
        size = child.stat().st_size
        digest.update(rel.encode("utf-8", errors="surrogateescape"))
        digest.update(str(size).encode("ascii"))
        if size <= limits.max_hash_bytes:
            digest.update(sha256_file(child).encode("ascii"))
        else:
            digest.update(b"hash-skipped-due-to-size")
    return digest.hexdigest(), min(files_seen, limits.max_entries), truncated


def format_bytes(value: int) -> str:
    units = ("B", "KiB", "MiB", "GiB")
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.1f} {unit}" if unit != "B" else f"{value} B"
        amount /= 1024
    return f"{value} B"


def archive_name_suffix(name: str) -> str:
    return archive_suffix(Path(normalize_artifact_path(name)))


def is_supported_archive_name(name: str) -> bool:
    return archive_name_suffix(name) in SUPPORTED_ARCHIVE_SUFFIXES


def is_unsupported_archive_name(name: str) -> bool:
    return archive_name_suffix(name) in UNSUPPORTED_ARCHIVE_SUFFIXES


def is_safe_member_path(name: str) -> bool:
    return unsafe_portable_member_reason(name) is None


def unsafe_portable_member_reason(name: str) -> str | None:
    normalized = normalize_artifact_path(name)
    if name != normalized or not is_safe_round_relative_path(normalized):
        return "path is absolute, parent-relative, empty, or uses a non-portable separator"
    for part in PurePosixPath(normalized).parts:
        if WINDOWS_INVALID_CHARS_RE.search(part):
            return "path contains characters that are invalid on Windows"
        if part.endswith((" ", ".")):
            return "path segment ends with a dot or space, which is not portable on Windows"
        base = part.split(".", 1)[0].upper()
        if base in WINDOWS_RESERVED_NAMES:
            return f"path segment uses reserved Windows device name {base}"
    return None


def candidate_ref(source_ref: str, chain: Iterable[str]) -> str:
    parts = [normalize_artifact_path(part) for part in chain if normalize_artifact_path(part)]
    return source_ref if not parts else "!".join([source_ref, *parts])


def stable_candidate_id(source: SourceBundle, chain: Iterable[str]) -> str:
    material = "\0".join([source.ref, source.sha256, *[normalize_artifact_path(part) for part in chain]])
    return "sb-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def next_action_for_state(state: str) -> str:
    return {
        "duplicate_candidate": "compare with the first same-hash candidate before materialization",
        "materialize_candidate": "candidate is visible for the existing review-round intake boundary",
        "needs_operator_selection": "choose the intended candidate before materialization",
        "nested_archive_depth_limit": "materialize or inspect the nested archive explicitly",
        "not_listed_due_to_size": "increase inventory limits or ask the operator to decompose the bundle",
        "unsupported_archive_type": "convert or unpack the archive outside deterministic workflow helpers",
    }.get(state, "inspect inventory record")


def interesting_leaf_class(artifact_class: str) -> bool:
    return artifact_class in ACTIONABLE_CLASSES or artifact_class in {"first_party_candidate", "test_evidence"}


def pdf_extract_ref_for_candidate(source_ref: str, chain: tuple[str, ...]) -> str | None:
    if not chain or Path(chain[-1]).suffix.lower() != ".pdf":
        return None
    safe_tail = "__".join(part.replace("/", "_") for part in (source_ref, *chain))
    return f"extracted/submission_bundle/{safe_tail.removesuffix('.pdf')}.txt"


def base_candidate(
    *,
    source: SourceBundle,
    chain: tuple[str, ...],
    artifact_class: str,
    reason_codes: tuple[str, ...],
    confidence: str,
    state: str,
    archive_depth: int,
    limits: BundleInventoryLimits,
    size_bytes: int | None = None,
    sha256: str | None = None,
    summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "candidate_id": stable_candidate_id(source, chain),
        "source_bundle_ref": source.ref,
        "source_bundle_sha256": source.sha256,
        "nested_path_chain": list(chain),
        "candidate_ref": candidate_ref(source.ref, chain),
        "artifact_class": artifact_class,
        "reason_codes": list(dict.fromkeys(reason_codes)),
        "confidence": confidence,
        "state": state,
        "materialized_ref": "",
        "limits": limits.as_record(),
        "next_action": next_action_for_state(state),
        "archive_depth": archive_depth,
    }
    if size_bytes is not None:
        record["size_bytes"] = size_bytes
    if sha256 is not None:
        record["sha256"] = sha256
    metadata = structural_metadata_for_artifact(
        path_ref=candidate_ref(source.ref, chain),
        artifact_class=artifact_class,
        size_bytes=size_bytes,
        sha256=sha256,
    )
    if metadata is not None:
        record["deterministic_metadata"] = metadata
    extract_ref = pdf_extract_ref_for_candidate(source.ref, chain)
    if extract_ref is not None:
        record["expected_extract_ref"] = extract_ref
    if summary:
        record["summary"] = summary
    return record


def skipped_entry(
    *,
    source: SourceBundle,
    chain: tuple[str, ...],
    state: str,
    reason_codes: tuple[str, ...],
    archive_depth: int,
    limits: BundleInventoryLimits,
    detail: str,
) -> dict[str, Any]:
    return {
        "source_bundle_ref": source.ref,
        "source_bundle_sha256": source.sha256,
        "nested_path_chain": list(chain),
        "candidate_ref": candidate_ref(source.ref, chain),
        "state": state,
        "reason_codes": list(reason_codes),
        "archive_depth": archive_depth,
        "limits": limits.as_record(),
        "detail": detail,
        "next_action": next_action_for_state(state),
    }


def archive_summary_from_names(names: list[str], *, truncated: bool) -> dict[str, Any]:
    code_like = [name for name in names if archive_entry_code_like(name)]
    evidence = [classify_path_evidence(name) for name in names]
    first_party = [item.normalized_path for item in evidence if item.artifact_class == "first_party_candidate"]
    tests = [item.normalized_path for item in evidence if item.artifact_class == "test_evidence"]
    readmes = [item.normalized_path for item in evidence if item.artifact_class == "readme_candidate"]
    assignments = [item.normalized_path for item in evidence if item.artifact_class == "assignment_pdf_candidate"]
    generated_or_vendor = [item.normalized_path for item in evidence if item.artifact_class == "generated_or_vendor"]
    sample_or_vendor = [item.normalized_path for item in evidence if item.artifact_class == "sample_or_vendor"]
    return {
        "entries_seen": len(names),
        "truncated": truncated,
        "code_like": bool(code_like),
        "code_like_count": len(code_like),
        "first_party_count": len(first_party),
        "test_count": len(tests),
        "readme_count": len(readmes),
        "assignment_pdf_count": len(assignments),
        "generated_or_vendor_count": len(generated_or_vendor),
        "sample_or_vendor_count": len(sample_or_vendor),
    }


def classify_archive_candidate(
    path_chain: tuple[str, ...], summary: dict[str, Any]
) -> tuple[str, tuple[str, ...], str]:
    evidence = classify_path_evidence(path_chain[-1])
    reasons = list(evidence.reason_codes)
    artifact_class = evidence.artifact_class
    if summary.get("code_like"):
        reasons.append("archive_contains_code_evidence")
        if artifact_class == "supported_archive":
            artifact_class = "code_archive_candidate"
    if summary.get("test_count"):
        reasons.append("archive_contains_test_evidence")
    if summary.get("readme_count"):
        reasons.append("archive_contains_readme")
    if summary.get("assignment_pdf_count"):
        reasons.append("archive_contains_assignment_pdf")
    confidence = "high" if reasons else evidence.confidence
    return artifact_class, tuple(dict.fromkeys(reasons)), confidence


def read_zip_member(
    handle: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    limits: BundleInventoryLimits,
    read_budget: ReadBudget,
) -> bytes | None:
    if info.file_size > limits.max_nested_archive_bytes and is_supported_archive_name(info.filename):
        return None
    if info.file_size > limits.max_hash_bytes and not is_supported_archive_name(info.filename):
        return None
    if not read_budget.reserve(info.filename, info.file_size):
        return None
    return handle.read(info)


def zip_members(
    path_or_data: Path | bytes,
    limits: BundleInventoryLimits,
    read_budget: ReadBudget,
) -> tuple[list[ArchiveMember], bool, str]:
    members: list[ArchiveMember] = []
    truncated = False
    try:
        handle_context = zipfile.ZipFile(path_or_data if isinstance(path_or_data, Path) else io.BytesIO(path_or_data))
        with handle_context as handle:
            for index, info in enumerate(handle.infolist()):
                if index >= limits.max_entries:
                    truncated = True
                    break
                data = None if info.is_dir() else read_zip_member(handle, info, limits, read_budget)
                members.append(ArchiveMember(info.filename, info.file_size, info.is_dir(), data))
    except (OSError, zipfile.BadZipFile) as exc:
        return [], False, f"metadata unreadable: {exc}"
    return members, truncated, "metadata listed"


def tar_members(
    path_or_data: Path | bytes,
    limits: BundleInventoryLimits,
    read_budget: ReadBudget,
) -> tuple[list[ArchiveMember], bool, str]:
    members: list[ArchiveMember] = []
    truncated = False
    try:
        if isinstance(path_or_data, Path):
            handle_context = tarfile.open(path_or_data, mode="r:*")
        else:
            handle_context = tarfile.open(fileobj=io.BytesIO(path_or_data), mode="r:*")
        with handle_context as handle:
            for index, member in enumerate(handle):
                if index >= limits.max_entries:
                    truncated = True
                    break
                data = None
                should_read = (
                    is_supported_archive_name(member.name) and member.size <= limits.max_nested_archive_bytes
                ) or (not is_supported_archive_name(member.name) and member.size <= limits.max_hash_bytes)
                if member.isfile() and should_read and read_budget.reserve(member.name, member.size):
                    extracted = handle.extractfile(member)
                    if extracted is not None:
                        data = extracted.read()
                members.append(ArchiveMember(member.name, member.size, member.isdir(), data))
    except (OSError, tarfile.TarError) as exc:
        return [], False, f"metadata unreadable: {exc}"
    return members, truncated, "metadata listed"


def list_archive_members(
    path_or_data: Path | bytes,
    *,
    suffix: str,
    limits: BundleInventoryLimits,
    read_budget: ReadBudget,
) -> tuple[list[ArchiveMember], bool, str]:
    if suffix == ".zip":
        return zip_members(path_or_data, limits, read_budget)
    if suffix in {".tar", ".tar.gz", ".tar.bz2", ".tar.xz", ".tgz", ".tbz", ".tbz2", ".txz"}:
        return tar_members(path_or_data, limits, read_budget)
    return [], False, "unsupported archive format"


def member_names(members: Iterable[ArchiveMember]) -> list[str]:
    return [normalize_artifact_path(member.name) for member in members if not member.is_dir]


def add_archive_candidates(
    *,
    source: SourceBundle,
    path_or_data: Path | bytes,
    suffix: str,
    chain: tuple[str, ...],
    depth: int,
    limits: BundleInventoryLimits,
    candidates: list[dict[str, Any]],
    skipped: list[dict[str, Any]],
    read_budget: ReadBudget,
) -> None:
    budget_start = len(read_budget.skipped)
    members, truncated, note = list_archive_members(path_or_data, suffix=suffix, limits=limits, read_budget=read_budget)
    if note != "metadata listed":
        skipped.append(
            skipped_entry(
                source=source,
                chain=chain,
                state="unsupported_archive_type",
                reason_codes=("archive_metadata_unreadable",),
                archive_depth=depth,
                limits=limits,
                detail=note,
            )
        )
        return
    if truncated:
        skipped.append(
            skipped_entry(
                source=source,
                chain=chain,
                state="not_listed_due_to_size",
                reason_codes=("entry_count_limit_reached",),
                archive_depth=depth,
                limits=limits,
                detail=f"stopped after {limits.max_entries} archive entries",
            )
        )
    for budget_detail in read_budget.skipped[budget_start:]:
        skipped.append(
            skipped_entry(
                source=source,
                chain=chain,
                state="not_listed_due_to_size",
                reason_codes=("read_budget_limit_reached",),
                archive_depth=depth,
                limits=limits,
                detail=budget_detail,
            )
        )

    add_archive_member_candidates(
        source=source,
        members=members,
        chain=chain,
        depth=depth,
        limits=limits,
        candidates=candidates,
        skipped=skipped,
        read_budget=read_budget,
    )


def add_archive_member_candidates(
    *,
    source: SourceBundle,
    members: list[ArchiveMember],
    chain: tuple[str, ...],
    depth: int,
    limits: BundleInventoryLimits,
    candidates: list[dict[str, Any]],
    skipped: list[dict[str, Any]],
    read_budget: ReadBudget,
) -> None:
    registry = PortablePathRegistry()
    for member in members:
        normalized_name = normalize_artifact_path(member.name)
        member_chain = (*chain, normalized_name)
        unsafe_reason = unsafe_portable_member_reason(member.name)
        if unsafe_reason is not None:
            skipped.append(
                skipped_entry(
                    source=source,
                    chain=member_chain,
                    state="unsupported_archive_type",
                    reason_codes=("unsafe_archive_member_path",),
                    archive_depth=depth,
                    limits=limits,
                    detail=unsafe_reason,
                )
            )
            continue
        collision = registry.register(normalized_name, kind="directory" if member.is_dir else "file")
        if collision is not None:
            skipped.append(
                skipped_entry(
                    source=source,
                    chain=member_chain,
                    state="duplicate_candidate",
                    reason_codes=(path_collision_reason_code(collision),),
                    archive_depth=depth,
                    limits=limits,
                    detail=collision,
                )
            )
            continue
        if member.is_dir:
            continue

        evidence = classify_path_evidence(normalized_name)
        member_suffix = archive_name_suffix(normalized_name)
        member_hash = sha256_bytes(member.data) if member.data is not None else None
        if is_unsupported_archive_name(normalized_name):
            candidates.append(
                base_candidate(
                    source=source,
                    chain=member_chain,
                    artifact_class="unsupported_archive",
                    reason_codes=(*evidence.reason_codes, "unsupported_archive_type"),
                    confidence="high",
                    state="unsupported_archive_type",
                    archive_depth=depth,
                    limits=limits,
                    size_bytes=member.size_bytes,
                    sha256=member_hash,
                )
            )
            continue
        if is_supported_archive_name(normalized_name):
            if depth >= limits.max_archive_depth:
                candidates.append(
                    base_candidate(
                        source=source,
                        chain=member_chain,
                        artifact_class=evidence.artifact_class,
                        reason_codes=(*evidence.reason_codes, "nested_archive_depth_limit"),
                        confidence="high",
                        state="nested_archive_depth_limit",
                        archive_depth=depth,
                        limits=limits,
                        size_bytes=member.size_bytes,
                        sha256=member_hash,
                    )
                )
                continue
            if member.size_bytes > limits.max_nested_archive_bytes or member.data is None:
                candidates.append(
                    base_candidate(
                        source=source,
                        chain=member_chain,
                        artifact_class=evidence.artifact_class,
                        reason_codes=(*evidence.reason_codes, "archive_exceeds_inventory_limit"),
                        confidence="high",
                        state="not_listed_due_to_size",
                        archive_depth=depth,
                        limits=limits,
                        size_bytes=member.size_bytes,
                        sha256=member_hash,
                    )
                )
                continue
            nested_budget_start = len(read_budget.skipped)
            nested_members, nested_truncated, nested_note = list_archive_members(
                member.data,
                suffix=member_suffix,
                limits=limits,
                read_budget=read_budget,
            )
            if nested_note != "metadata listed":
                skipped.append(
                    skipped_entry(
                        source=source,
                        chain=member_chain,
                        state="unsupported_archive_type",
                        reason_codes=("archive_metadata_unreadable",),
                        archive_depth=depth + 1,
                        limits=limits,
                        detail=nested_note,
                    )
                )
                continue
            if nested_truncated:
                skipped.append(
                    skipped_entry(
                        source=source,
                        chain=member_chain,
                        state="not_listed_due_to_size",
                        reason_codes=("entry_count_limit_reached",),
                        archive_depth=depth + 1,
                        limits=limits,
                        detail=f"stopped after {limits.max_entries} archive entries",
                    )
                )
            for budget_detail in read_budget.skipped[nested_budget_start:]:
                skipped.append(
                    skipped_entry(
                        source=source,
                        chain=member_chain,
                        state="not_listed_due_to_size",
                        reason_codes=("read_budget_limit_reached",),
                        archive_depth=depth + 1,
                        limits=limits,
                        detail=budget_detail,
                    )
                )
            summary = archive_summary_from_names(member_names(nested_members), truncated=nested_truncated)
            artifact_class, reasons, confidence = classify_archive_candidate(member_chain, summary)
            candidates.append(
                base_candidate(
                    source=source,
                    chain=member_chain,
                    artifact_class=artifact_class,
                    reason_codes=reasons,
                    confidence=confidence,
                    state="materialize_candidate",
                    archive_depth=depth + 1,
                    limits=limits,
                    size_bytes=member.size_bytes,
                    sha256=member_hash,
                    summary=summary,
                )
            )
            add_archive_member_candidates(
                source=source,
                members=nested_members,
                chain=member_chain,
                depth=depth + 1,
                limits=limits,
                candidates=candidates,
                skipped=skipped,
                read_budget=read_budget,
            )
            continue
        if interesting_leaf_class(evidence.artifact_class):
            candidates.append(
                base_candidate(
                    source=source,
                    chain=member_chain,
                    artifact_class=evidence.artifact_class,
                    reason_codes=evidence.reason_codes,
                    confidence=evidence.confidence,
                    state="materialize_candidate",
                    archive_depth=depth,
                    limits=limits,
                    size_bytes=member.size_bytes,
                    sha256=member_hash,
                )
            )


def add_directory_candidates(
    *,
    source: SourceBundle,
    limits: BundleInventoryLimits,
    candidates: list[dict[str, Any]],
    skipped: list[dict[str, Any]],
) -> None:
    registry = PortablePathRegistry()
    files_seen = 0
    for child in sorted(source.path.rglob("*"), key=lambda item: item.as_posix()):
        rel = child.relative_to(source.path).as_posix()
        if child.is_symlink():
            skipped.append(
                skipped_entry(
                    source=source,
                    chain=(rel,),
                    state="unsupported_archive_type",
                    reason_codes=("directory_symlink_skipped",),
                    archive_depth=0,
                    limits=limits,
                    detail="directory bundle symlink skipped before hashing",
                )
            )
            continue
        if not child.is_file():
            continue
        files_seen += 1
        if files_seen > limits.max_entries:
            skipped.append(
                skipped_entry(
                    source=source,
                    chain=(),
                    state="not_listed_due_to_size",
                    reason_codes=("entry_count_limit_reached",),
                    archive_depth=0,
                    limits=limits,
                    detail=f"stopped after {limits.max_entries} directory entries",
                )
            )
            break
        unsafe_reason = unsafe_portable_member_reason(rel)
        if unsafe_reason is not None:
            skipped.append(
                skipped_entry(
                    source=source,
                    chain=(rel,),
                    state="unsupported_archive_type",
                    reason_codes=("unsafe_directory_member_path",),
                    archive_depth=0,
                    limits=limits,
                    detail=unsafe_reason,
                )
            )
            continue
        collision = registry.register(rel, kind="file")
        if collision is not None:
            skipped.append(
                skipped_entry(
                    source=source,
                    chain=(rel,),
                    state="duplicate_candidate",
                    reason_codes=(path_collision_reason_code(collision),),
                    archive_depth=0,
                    limits=limits,
                    detail=collision,
                )
            )
            continue
        evidence = classify_path_evidence(rel)
        if not interesting_leaf_class(evidence.artifact_class):
            continue
        size = child.stat().st_size
        child_hash = sha256_file(child) if size <= limits.max_hash_bytes else None
        candidates.append(
            base_candidate(
                source=source,
                chain=(rel,),
                artifact_class=evidence.artifact_class,
                reason_codes=evidence.reason_codes,
                confidence=evidence.confidence,
                state="materialize_candidate",
                archive_depth=0,
                limits=limits,
                size_bytes=size,
                sha256=child_hash,
            )
        )


def finalize_candidate_states(candidates: list[dict[str, Any]]) -> None:
    seen_hashes: dict[tuple[str, str], str] = {}
    for candidate in candidates:
        if candidate.get("state") != "materialize_candidate":
            continue
        sha = candidate.get("sha256")
        artifact_class = candidate.get("artifact_class")
        if not isinstance(sha, str) or not isinstance(artifact_class, str):
            continue
        key = (artifact_class, sha)
        first_ref = seen_hashes.get(key)
        if first_ref is not None:
            candidate["state"] = "duplicate_candidate"
            candidate["next_action"] = next_action_for_state("duplicate_candidate")
            candidate["duplicate_of"] = first_ref
        else:
            seen_hashes[key] = str(candidate.get("candidate_ref", ""))

    groups: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        if candidate.get("state") == "materialize_candidate" and candidate.get("artifact_class") in AMBIGUOUS_CLASSES:
            groups.setdefault(str(candidate["artifact_class"]), []).append(candidate)
    for grouped in groups.values():
        if len(grouped) < 2:
            continue
        for candidate in grouped:
            candidate["state"] = "needs_operator_selection"
            candidate["next_action"] = next_action_for_state("needs_operator_selection")


def resolve_source_bundle(round_dir: Path, bundle_ref: str, limits: BundleInventoryLimits) -> SourceBundle:
    if not is_safe_round_relative_path(bundle_ref):
        raise ValueError(f"Bundle ref must be a safe round-relative path: {bundle_ref}")
    if not bundle_ref.startswith("inputs/"):
        raise ValueError(f"Bundle ref must point to an existing round input under inputs/: {bundle_ref}")
    path = round_dir / bundle_ref
    if path.is_file():
        return SourceBundle(
            bundle_ref, path, "archive" if archive_suffix(path) else "file", path.stat().st_size, sha256_file(path)
        )
    if path.is_dir():
        digest, _, _ = sha256_directory(path, limits)
        return SourceBundle(bundle_ref, path, "directory", 0, digest)
    raise FileNotFoundError(f"Bundle ref does not exist: {bundle_ref}")


def build_submission_bundle_inventory(
    *,
    case_id: str,
    round_id: str,
    round_dir: Path,
    bundle_refs: Iterable[str],
    limits: BundleInventoryLimits | None = None,
    generated_at: str | None = None,
    producer: str = SUBMISSION_BUNDLE_PRODUCER,
) -> dict[str, Any]:
    active_limits = limits or BundleInventoryLimits()
    candidates: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    source_records: list[dict[str, Any]] = []
    for bundle_ref in bundle_refs:
        source = resolve_source_bundle(round_dir, bundle_ref, active_limits)
        source_records.append(
            {
                "source_bundle_ref": source.ref,
                "source_bundle_sha256": source.sha256,
                "kind": source.kind,
                "size_bytes": source.size_bytes,
            }
        )
        if source.kind == "directory":
            add_directory_candidates(source=source, limits=active_limits, candidates=candidates, skipped=skipped)
            continue
        suffix = archive_suffix(source.path)
        evidence = classify_path_evidence(source.ref)
        if suffix in UNSUPPORTED_ARCHIVE_SUFFIXES or suffix not in SUPPORTED_ARCHIVE_SUFFIXES:
            candidates.append(
                base_candidate(
                    source=source,
                    chain=(),
                    artifact_class="unsupported_archive",
                    reason_codes=(*evidence.reason_codes, "unsupported_archive_type"),
                    confidence="high",
                    state="unsupported_archive_type",
                    archive_depth=0,
                    limits=active_limits,
                    size_bytes=source.size_bytes,
                    sha256=source.sha256,
                )
            )
            continue
        if source.size_bytes > active_limits.max_archive_bytes:
            candidates.append(
                base_candidate(
                    source=source,
                    chain=(),
                    artifact_class="container_bundle",
                    reason_codes=(*evidence.reason_codes, "archive_exceeds_inventory_limit"),
                    confidence="high",
                    state="not_listed_due_to_size",
                    archive_depth=0,
                    limits=active_limits,
                    size_bytes=source.size_bytes,
                    sha256=source.sha256,
                )
            )
            continue
        read_budget = ReadBudget(active_limits.max_read_bytes)
        add_archive_candidates(
            source=source,
            path_or_data=source.path,
            suffix=suffix,
            chain=(),
            depth=0,
            limits=active_limits,
            candidates=candidates,
            skipped=skipped,
            read_budget=read_budget,
        )

    finalize_candidate_states(candidates)
    return {
        "schema_version": SUBMISSION_BUNDLE_INVENTORY_SCHEMA,
        "case_id": case_id,
        "round_id": round_id,
        "generated_at": generated_at or now_utc(),
        "producer": producer,
        "limits": active_limits.as_record(),
        "source_bundles": source_records,
        "candidates": candidates,
        "skipped_entries": skipped,
        "summary": {
            "source_bundle_count": len(source_records),
            "candidate_count": len(candidates),
            "skipped_entry_count": len(skipped),
            "materialize_candidate_count": sum(
                1 for item in candidates if item.get("state") == "materialize_candidate"
            ),
            "needs_operator_selection_count": sum(
                1 for item in candidates if item.get("state") == "needs_operator_selection"
            ),
            "not_listed_due_to_size_count": sum(
                1 for item in candidates if item.get("state") == "not_listed_due_to_size"
            ),
        },
    }


def render_inventory_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Submission Bundle Inventory",
        "",
        f"- Schema: `{payload.get('schema_version', '')}`",
        f"- Generated at: `{payload.get('generated_at', '')}`",
        f"- Producer: `{payload.get('producer', '')}`",
        "",
        "## Source Bundles",
        "",
    ]
    for source in payload.get("source_bundles", []):
        if not isinstance(source, dict):
            continue
        lines.append(
            "- "
            f"`{source.get('source_bundle_ref', '')}` "
            f"({source.get('kind', 'unknown')}, {format_bytes(int(source.get('size_bytes') or 0))}, "
            f"sha256 `{source.get('source_bundle_sha256', '')}`)"
        )
    if not payload.get("source_bundles"):
        lines.append("- none")
    lines.extend(["", "## Candidates", ""])
    lines.append("| ID | State | Class | Candidate | Size | Next Action |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for candidate in payload.get("candidates", []):
        if not isinstance(candidate, dict):
            continue
        size = candidate.get("size_bytes")
        size_text = format_bytes(int(size)) if isinstance(size, int) else ""
        lines.append(
            "| "
            f"`{candidate.get('candidate_id', '')}` | "
            f"`{candidate.get('state', '')}` | "
            f"`{candidate.get('artifact_class', '')}` | "
            f"`{candidate.get('candidate_ref', '')}` | "
            f"{size_text} | "
            f"{candidate.get('next_action', '')} |"
        )
    if not payload.get("candidates"):
        lines.append("| | | | no candidates | | |")
    skipped = payload.get("skipped_entries", [])
    if skipped:
        lines.extend(["", "## Skipped Entries", ""])
        for item in skipped:
            if not isinstance(item, dict):
                continue
            lines.append(
                "- " f"`{item.get('candidate_ref', '')}`: `{item.get('state', '')}` " f"({item.get('detail', '')})"
            )
    return "\n".join(lines) + "\n"


def write_submission_bundle_inventory(
    *,
    round_dir: Path,
    payload: dict[str, Any],
) -> tuple[Path, Path]:
    json_path = round_dir / SUBMISSION_BUNDLE_INVENTORY_REL
    md_path = round_dir / SUBMISSION_BUNDLE_INVENTORY_SUMMARY_REL
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_inventory_markdown(payload), encoding="utf-8")
    return json_path, md_path


def load_optional_submission_bundle_inventory(round_dir: Path) -> tuple[dict[str, Any] | None, str | None]:
    path = round_dir / SUBMISSION_BUNDLE_INVENTORY_REL
    if not path.is_file():
        return None, None
    try:
        return load_submission_bundle_inventory(round_dir), None
    except (OSError, ValueError) as exc:
        return None, str(exc)


def load_optional_materialization_manifest(round_dir: Path) -> tuple[dict[str, Any] | None, str | None]:
    path = round_dir / SUBMISSION_BUNDLE_MATERIALIZATION_REL
    if not path.is_file():
        return None, None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"{SUBMISSION_BUNDLE_MATERIALIZATION_REL}: cannot read materialization manifest: {exc}"
    if not isinstance(loaded, dict) or loaded.get("schema_version") != SUBMISSION_BUNDLE_MATERIALIZATION_SCHEMA:
        return None, f"{SUBMISSION_BUNDLE_MATERIALIZATION_REL}: unsupported schema_version"
    if not isinstance(loaded.get("materializations"), list):
        return None, f"{SUBMISSION_BUNDLE_MATERIALIZATION_REL}: materializations must be a list"
    return loaded, None


def load_optional_expansion_manifest(round_dir: Path) -> tuple[dict[str, Any] | None, str | None]:
    path = round_dir / SUBMISSION_BUNDLE_EXPANSION_REL
    if not path.is_file():
        return None, None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"{SUBMISSION_BUNDLE_EXPANSION_REL}: cannot read expansion manifest: {exc}"
    if not isinstance(loaded, dict) or loaded.get("schema_version") != SUBMISSION_BUNDLE_EXPANSION_SCHEMA:
        return None, f"{SUBMISSION_BUNDLE_EXPANSION_REL}: unsupported schema_version"
    if not isinstance(loaded.get("expansions"), list):
        return None, f"{SUBMISSION_BUNDLE_EXPANSION_REL}: expansions must be a list"
    if not isinstance(loaded.get("skipped_entries"), list):
        return None, f"{SUBMISSION_BUNDLE_EXPANSION_REL}: skipped_entries must be a list"
    return loaded, None


def _validate_sha256_file_field(
    *,
    payload: dict[str, Any],
    field: str,
    path: Path,
    prefix: str,
    errors: list[str],
) -> str | None:
    value = payload.get(field)
    if not isinstance(value, str) or not value:
        errors.append(f"{prefix}: {field} must be a non-empty sha256 string")
        return None
    if path.is_file() and sha256_file(path) != value:
        errors.append(f"{prefix}: {field} does not match current file")
    return value


def validate_submission_bundle_materialization_payload(
    payload: dict[str, Any],
    rel_path: str,
    *,
    round_dir: Path,
    case_id: str | None = None,
    round_id: str | None = None,
) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SUBMISSION_BUNDLE_MATERIALIZATION_SCHEMA:
        errors.append(f"{rel_path}: schema_version must be {SUBMISSION_BUNDLE_MATERIALIZATION_SCHEMA}")
    if case_id is not None and payload.get("case_id") != case_id:
        errors.append(f"{rel_path}: case_id does not match requested case")
    if round_id is not None and payload.get("round_id") != round_id:
        errors.append(f"{rel_path}: round_id does not match requested round")
    records = payload.get("materializations")
    if not isinstance(records, list):
        errors.append(f"{rel_path}: materializations must be a list")
        return errors
    for index, record in enumerate(records, start=1):
        prefix = f"{rel_path}: materializations item {index}"
        if not isinstance(record, dict):
            errors.append(f"{prefix}: must be an object")
            continue
        materialized_ref = record.get("materialized_ref")
        if not isinstance(materialized_ref, str) or not is_safe_round_relative_path(materialized_ref):
            errors.append(f"{prefix}: materialized_ref must be a safe round-relative path")
            continue
        materialized_path = round_dir / materialized_ref
        if not materialized_path.is_file():
            errors.append(f"{prefix}: materialized_ref does not exist: {materialized_ref}")
        materialized_sha = _validate_sha256_file_field(
            payload=record,
            field="materialized_sha256",
            path=materialized_path,
            prefix=prefix,
            errors=errors,
        )
        source_member_sha = record.get("source_member_sha256")
        if (
            isinstance(source_member_sha, str)
            and materialized_sha is not None
            and source_member_sha != materialized_sha
        ):
            errors.append(f"{prefix}: source_member_sha256 must match materialized_sha256")
        source_bundle_ref = record.get("source_bundle_ref")
        if not isinstance(source_bundle_ref, str) or not is_safe_round_relative_path(source_bundle_ref):
            errors.append(f"{prefix}: source_bundle_ref must be a safe round-relative path")
        else:
            _validate_sha256_file_field(
                payload=record,
                field="source_bundle_sha256",
                path=round_dir / source_bundle_ref,
                prefix=prefix,
                errors=errors,
            )
        source_inventory_ref = record.get("source_inventory_ref")
        if source_inventory_ref is not None:
            if not isinstance(source_inventory_ref, str) or not is_safe_round_relative_path(source_inventory_ref):
                errors.append(f"{prefix}: source_inventory_ref must be a safe round-relative path")
            else:
                _validate_sha256_file_field(
                    payload=record,
                    field="source_inventory_sha256",
                    path=round_dir / source_inventory_ref,
                    prefix=prefix,
                    errors=errors,
                )
        for field_name in ("candidate_id", "artifact_class", "action", "selected_at"):
            if not isinstance(record.get(field_name), str) or not str(record.get(field_name)).strip():
                errors.append(f"{prefix}: {field_name} must be a non-empty string")
        nested_path_chain = record.get("nested_path_chain")
        if not isinstance(nested_path_chain, list) or not all(isinstance(item, str) for item in nested_path_chain):
            errors.append(f"{prefix}: nested_path_chain must be a list of strings")
    return errors


def validate_submission_bundle_expansion_payload(
    payload: dict[str, Any],
    rel_path: str,
    *,
    round_dir: Path,
    case_id: str | None = None,
    round_id: str | None = None,
) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SUBMISSION_BUNDLE_EXPANSION_SCHEMA:
        errors.append(f"{rel_path}: schema_version must be {SUBMISSION_BUNDLE_EXPANSION_SCHEMA}")
    if case_id is not None and payload.get("case_id") != case_id:
        errors.append(f"{rel_path}: case_id does not match requested case")
    if round_id is not None and payload.get("round_id") != round_id:
        errors.append(f"{rel_path}: round_id does not match requested round")
    target_root_ref = payload.get("target_root_ref")
    if target_root_ref != SUBMISSION_BUNDLE_EXPANDED_ROOT_REL:
        errors.append(f"{rel_path}: target_root_ref must be {SUBMISSION_BUNDLE_EXPANDED_ROOT_REL}")
    records = payload.get("expansions")
    if not isinstance(records, list):
        errors.append(f"{rel_path}: expansions must be a list")
        return errors
    skipped = payload.get("skipped_entries")
    if not isinstance(skipped, list):
        errors.append(f"{rel_path}: skipped_entries must be a list")
    for index, record in enumerate(records, start=1):
        prefix = f"{rel_path}: expansions item {index}"
        if not isinstance(record, dict):
            errors.append(f"{prefix}: must be an object")
            continue
        source_bundle_ref = record.get("source_bundle_ref")
        if not isinstance(source_bundle_ref, str) or not is_safe_round_relative_path(source_bundle_ref):
            errors.append(f"{prefix}: source_bundle_ref must be a safe round-relative path")
        else:
            _validate_sha256_file_field(
                payload=record,
                field="source_bundle_sha256",
                path=round_dir / source_bundle_ref,
                prefix=prefix,
                errors=errors,
            )
        target_ref = record.get("target_ref")
        if (
            not isinstance(target_ref, str)
            or not is_safe_round_relative_path(target_ref)
            or not target_ref.startswith(f"{SUBMISSION_BUNDLE_EXPANDED_ROOT_REL}/")
        ):
            errors.append(f"{prefix}: target_ref must be below {SUBMISSION_BUNDLE_EXPANDED_ROOT_REL}/")
        else:
            target_path = round_dir / target_ref
            if not target_path.is_dir():
                errors.append(f"{prefix}: target_ref directory is missing: {target_ref}")
            else:
                try:
                    current_tree = expansion_tree_state(target_path)
                except (OSError, ValueError) as exc:
                    errors.append(f"{prefix}: target_ref tree is invalid: {exc}")
                else:
                    for field_name, expected in current_tree.items():
                        if record.get(field_name) != expected:
                            errors.append(f"{prefix}: {field_name} does not match current expanded tree")
        for field_name in (
            "files_written",
            "directories_written",
            "archives_expanded",
            "entries_seen",
            "bytes_written",
            "skipped_entry_count",
            "target_tree_file_count",
            "target_tree_directory_count",
            "target_tree_bytes",
        ):
            value = record.get(field_name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                errors.append(f"{prefix}: {field_name} must be a non-negative integer")
        if not isinstance(record.get("target_tree_sha256"), str) or not str(record.get("target_tree_sha256")).strip():
            errors.append(f"{prefix}: target_tree_sha256 must be a non-empty string")
        for field_name in ("kind", "action"):
            if not isinstance(record.get(field_name), str) or not str(record.get(field_name)).strip():
                errors.append(f"{prefix}: {field_name} must be a non-empty string")
    return errors


def _count_by(items: Iterable[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = item.get(key)
        if isinstance(value, str) and value:
            counts[value] = counts.get(value, 0) + 1
    return counts


def _count_text(counts: dict[str, int]) -> str:
    return ", ".join(f"{key}={counts[key]}" for key in sorted(counts)) if counts else "none"


def _round_identity(round_dir: Path) -> tuple[str | None, str | None]:
    if round_dir.parent.name != "rounds":
        return None, None
    return round_dir.parent.parent.name, round_dir.name


def _safe_int(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _candidate_label(candidate: dict[str, Any]) -> str:
    ref = str(candidate.get("candidate_ref", "unknown"))
    candidate_id = str(candidate.get("candidate_id", "unknown"))
    artifact_class = str(candidate.get("artifact_class", "unknown"))
    state = str(candidate.get("state", "unknown"))
    materialized_ref = str(candidate.get("materialized_ref", "") or "")
    suffix = f" -> `{materialized_ref}`" if materialized_ref else ""
    expected_extract = candidate.get("expected_extract_ref")
    extract_suffix = f"; expected extract `{expected_extract}`" if isinstance(expected_extract, str) else ""
    return f"`{candidate_id}` `{artifact_class}` `{state}` `{ref}`{suffix}{extract_suffix}"


def _candidate_materialized(candidate: dict[str, Any]) -> bool:
    value = candidate.get("materialized_ref")
    return isinstance(value, str) and bool(value)


def _archive_summary_line(candidate: dict[str, Any]) -> str | None:
    summary = candidate.get("summary")
    if not isinstance(summary, dict):
        return None
    counts = {
        "first_party": _safe_int(summary.get("first_party_count")),
        "tests": _safe_int(summary.get("test_count")),
        "generated_build": _safe_int(summary.get("generated_or_vendor_count")),
        "sample_vendor": _safe_int(summary.get("sample_or_vendor_count")),
    }
    return (
        f"{_candidate_label(candidate)}; "
        f"first-party-looking={counts['first_party']}; tests={counts['tests']}; "
        f"generated/build={counts['generated_build']}; sample/vendor={counts['sample_vendor']}"
    )


def _limited_labels(candidates: list[dict[str, Any]], *, limit: int) -> list[str]:
    labels = [_candidate_label(candidate) for candidate in candidates[:limit]]
    omitted = len(candidates) - limit
    if omitted > 0:
        labels.append(f"... {omitted} more")
    return labels


def _candidate_has_first_party_code(candidate: dict[str, Any]) -> bool:
    if candidate.get("artifact_class") == "first_party_candidate":
        return True
    summary = candidate.get("summary")
    return isinstance(summary, dict) and _safe_int(summary.get("first_party_count")) > 0


def _candidate_has_generated_sample_vendor(candidate: dict[str, Any]) -> bool:
    summary = candidate.get("summary")
    return isinstance(summary, dict) and (
        _safe_int(summary.get("generated_or_vendor_count")) > 0 or _safe_int(summary.get("sample_or_vendor_count")) > 0
    )


def submission_bundle_visibility_payload(round_dir: Path, *, limit: int = 8) -> dict[str, Any]:
    inventory, inventory_error = load_optional_submission_bundle_inventory(round_dir)
    materialization, materialization_error = load_optional_materialization_manifest(round_dir)
    expansion, expansion_error = load_optional_expansion_manifest(round_dir)
    expected_case_id, expected_round_id = _round_identity(round_dir)
    inventory_status = "invalid" if inventory_error else "present" if inventory else "missing"
    inventory_note = ""
    authoritative_inventory = False
    if inventory is not None and inventory_status == "present":
        if expected_case_id and inventory.get("case_id") != expected_case_id:
            inventory_status = "invalid"
            inventory_error = f"{SUBMISSION_BUNDLE_INVENTORY_REL}: case_id does not match round path"
        elif expected_round_id and inventory.get("round_id") != expected_round_id:
            inventory_status = "invalid"
            inventory_error = f"{SUBMISSION_BUNDLE_INVENTORY_REL}: round_id does not match round path"
        elif inventory.get("producer") != SUBMISSION_BUNDLE_ROUND_START_PRODUCER:
            inventory_status = "diagnostic"
            inventory_note = (
                f"produced by `{inventory.get('producer', '') or 'unknown'}`; rerun `scripts/review-round-start` "
                "before role packets or readiness checks rely on nested candidates"
            )
        else:
            authoritative_inventory = True
    materialization_status = "invalid" if materialization_error else "present" if materialization else "missing"
    if materialization is not None and materialization_status == "present":
        if expected_case_id and materialization.get("case_id") != expected_case_id:
            materialization_status = "invalid"
            materialization_error = f"{SUBMISSION_BUNDLE_MATERIALIZATION_REL}: case_id does not match round path"
        elif expected_round_id and materialization.get("round_id") != expected_round_id:
            materialization_status = "invalid"
            materialization_error = f"{SUBMISSION_BUNDLE_MATERIALIZATION_REL}: round_id does not match round path"
    expansion_status = "invalid" if expansion_error else "present" if expansion else "missing"
    if expansion is not None and expansion_status == "present":
        if expected_case_id and expansion.get("case_id") != expected_case_id:
            expansion_status = "invalid"
            expansion_error = f"{SUBMISSION_BUNDLE_EXPANSION_REL}: case_id does not match round path"
        elif expected_round_id and expansion.get("round_id") != expected_round_id:
            expansion_status = "invalid"
            expansion_error = f"{SUBMISSION_BUNDLE_EXPANSION_REL}: round_id does not match round path"
    candidates = [
        item for item in (inventory or {}).get("candidates", []) if authoritative_inventory and isinstance(item, dict)
    ]
    skipped = [
        item
        for item in (inventory or {}).get("skipped_entries", [])
        if authoritative_inventory and isinstance(item, dict)
    ]
    source_bundles = [
        item
        for item in (inventory or {}).get("source_bundles", [])
        if authoritative_inventory and isinstance(item, dict)
    ]
    materializations = [
        item
        for item in (materialization or {}).get("materializations", [])
        if materialization_status == "present" and isinstance(item, dict)
    ]
    expansions = [
        item
        for item in (expansion or {}).get("expansions", [])
        if expansion_status == "present" and isinstance(item, dict)
    ]
    expansion_skipped = [
        item
        for item in (expansion or {}).get("skipped_entries", [])
        if expansion_status == "present" and isinstance(item, dict)
    ]
    materialized_candidates = [candidate for candidate in candidates if _candidate_materialized(candidate)]
    first_party_candidates = [candidate for candidate in candidates if _candidate_has_first_party_code(candidate)]
    archive_summaries = [line for candidate in candidates if isinstance(line := _archive_summary_line(candidate), str)]
    generated_or_vendor = [
        line
        for candidate in candidates
        if _candidate_has_generated_sample_vendor(candidate)
        and isinstance(line := _archive_summary_line(candidate), str)
    ]
    demo_candidates = [
        candidate
        for candidate in candidates
        if candidate.get("artifact_class") in {"media_artifact", "executable_artifact"}
    ]
    next_action_candidates = [candidate for candidate in candidates if not _candidate_materialized(candidate)]
    return {
        "schema_version": SUBMISSION_BUNDLE_VISIBILITY_SCHEMA,
        "inventory_ref": SUBMISSION_BUNDLE_INVENTORY_REL,
        "inventory_status": inventory_status,
        "inventory_error": inventory_error or "",
        "inventory_note": inventory_note,
        "materialization_ref": SUBMISSION_BUNDLE_MATERIALIZATION_REL,
        "materialization_status": materialization_status,
        "materialization_error": materialization_error or "",
        "expansion_ref": SUBMISSION_BUNDLE_EXPANSION_REL,
        "expansion_status": expansion_status,
        "expansion_error": expansion_error or "",
        "expanded_root_ref": SUBMISSION_BUNDLE_EXPANDED_ROOT_REL,
        "source_bundles": source_bundles[:limit],
        "candidate_counts_by_class": _count_by(candidates, "artifact_class"),
        "candidate_counts_by_state": _count_by(candidates, "state"),
        "materialized_candidates": _limited_labels(materialized_candidates, limit=limit),
        "materialization_records": [
            {
                "candidate_id": str(record.get("candidate_id", "")),
                "materialized_ref": str(record.get("materialized_ref", "")),
                "artifact_class": str(record.get("artifact_class", "")),
                "source_candidate_ref": str(record.get("source_candidate_ref", "")),
            }
            for record in materializations[:limit]
        ],
        "expansion_records": [
            {
                "source_bundle_ref": str(record.get("source_bundle_ref", "")),
                "target_ref": str(record.get("target_ref", "")),
                "action": str(record.get("action", "")),
                "files_written": _safe_int(record.get("files_written")),
                "archives_expanded": _safe_int(record.get("archives_expanded")),
                "bytes_written": _safe_int(record.get("bytes_written")),
                "skipped_entry_count": _safe_int(record.get("skipped_entry_count")),
            }
            for record in expansions[:limit]
        ],
        "expansion_skipped_entry_count": len(expansion_skipped),
        "expansion_skipped_entry_examples": [
            "`{source}` `{chain}` `{reason}`: {detail}".format(
                source=item.get("source_bundle_ref", ""),
                chain=(
                    " / ".join(str(part) for part in item.get("nested_path_chain", []))
                    if isinstance(item.get("nested_path_chain"), list)
                    else ""
                ),
                reason=item.get("reason_code", ""),
                detail=item.get("detail", ""),
            )
            for item in expansion_skipped[:limit]
        ],
        "first_party_code_candidates": _limited_labels(first_party_candidates, limit=limit),
        "archive_code_summaries": archive_summaries[:limit],
        "generated_sample_vendor_summaries": generated_or_vendor[:limit],
        "demo_media_executable_candidates": _limited_labels(demo_candidates, limit=limit),
        "next_actions": [
            f"{_candidate_label(candidate)}: {candidate.get('next_action', 'inspect inventory record')}"
            for candidate in next_action_candidates[:limit]
        ],
        "skipped_entry_count": len(skipped),
        "skipped_entry_examples": [
            f"`{item.get('candidate_ref', '')}` `{item.get('state', '')}`: {item.get('detail', '')}"
            for item in skipped[:limit]
        ],
    }


def submission_bundle_visibility_lines(
    round_dir: Path,
    *,
    include_absent: bool = True,
    limit: int = 8,
) -> list[str]:
    payload = submission_bundle_visibility_payload(round_dir, limit=limit)
    if payload["inventory_status"] == "missing" and not include_absent:
        return []
    lines = [
        f"- Inventory: `{payload['inventory_ref']}` ({payload['inventory_status']})",
        f"- Materialization manifest: `{payload['materialization_ref']}` ({payload['materialization_status']})",
        (
            f"- Expanded bundle workspace: `{payload['expanded_root_ref']}` "
            f"via `{payload['expansion_ref']}` ({payload['expansion_status']})"
        ),
    ]
    if payload["inventory_error"]:
        lines.append(f"- Inventory error: {payload['inventory_error']}")
        return lines
    if payload["inventory_status"] == "diagnostic":
        lines.append(f"- Inventory note: {payload['inventory_note']}")
        return lines
    if payload["materialization_error"]:
        lines.append(f"- Materialization manifest error: {payload['materialization_error']}")
    if payload["expansion_error"]:
        lines.append(f"- Expanded bundle workspace error: {payload['expansion_error']}")
    source_lines = []
    for source in payload["source_bundles"]:
        ref = source.get("source_bundle_ref", "")
        kind = source.get("kind", "unknown")
        size = format_bytes(int(source.get("size_bytes") or 0))
        source_lines.append(f"`{ref}` ({kind}, {size})")
    lines.append(f"- Source bundles: {', '.join(source_lines) if source_lines else 'none'}")
    lines.append(f"- Candidate classes: {_count_text(payload['candidate_counts_by_class'])}")
    lines.append(f"- Candidate states: {_count_text(payload['candidate_counts_by_state'])}")
    materialized = payload["materialized_candidates"]
    lines.append("- Materialized candidates: " + ("; ".join(materialized) if materialized else "none"))
    expansion_records = payload["expansion_records"]
    if expansion_records:
        expanded_labels = [
            (
                "`{source}` -> `{target}` "
                "({action}, files={files}, archives={archives}, bytes={bytes}, skipped={skipped})"
            ).format(
                source=record["source_bundle_ref"],
                target=record["target_ref"],
                action=record["action"],
                files=record["files_written"],
                archives=record["archives_expanded"],
                bytes=format_bytes(int(record["bytes_written"])),
                skipped=record["skipped_entry_count"],
            )
            for record in expansion_records
        ]
        lines.append("- Expanded bundles: " + "; ".join(expanded_labels))
    else:
        lines.append("- Expanded bundles: none")
    expansion_skipped_count = int(payload["expansion_skipped_entry_count"])
    expansion_skipped = payload["expansion_skipped_entry_examples"]
    if expansion_skipped_count:
        lines.append(
            f"- Expansion skipped or bounded entries: {expansion_skipped_count}; " + "; ".join(expansion_skipped)
        )
    first_party = payload["first_party_code_candidates"]
    lines.append("- First-party-looking code: " + ("; ".join(first_party) if first_party else "none discovered"))
    archive_summaries = payload["archive_code_summaries"]
    if archive_summaries:
        lines.append("- Archive code summary: " + " | ".join(archive_summaries))
    generated = payload["generated_sample_vendor_summaries"]
    lines.append(
        "- Generated/build/sample/vendor code: " + (" | ".join(generated) if generated else "none recorded separately")
    )
    demo = payload["demo_media_executable_candidates"]
    lines.append("- Demo/media/executables: " + ("; ".join(demo) if demo else "none discovered"))
    actions = payload["next_actions"]
    lines.append("- Candidate next actions: " + ("; ".join(actions) if actions else "none"))
    skipped_count = int(payload["skipped_entry_count"])
    skipped = payload["skipped_entry_examples"]
    if skipped_count:
        lines.append(f"- Skipped or bounded entries: {skipped_count}; " + "; ".join(skipped))
    return lines


def render_submission_bundle_visibility_markdown(round_dir: Path, *, include_absent: bool = True) -> str:
    lines = submission_bundle_visibility_lines(round_dir, include_absent=include_absent)
    if not lines:
        return ""
    return "\n".join(["## Submission Bundle Inventory", "", *lines, ""])


def load_submission_bundle_inventory(round_dir: Path) -> dict[str, Any]:
    path = round_dir / SUBMISSION_BUNDLE_INVENTORY_REL
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Missing bundle inventory: {SUBMISSION_BUNDLE_INVENTORY_REL}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {SUBMISSION_BUNDLE_INVENTORY_REL}: {exc.msg}") from exc
    if not isinstance(loaded, dict) or loaded.get("schema_version") != SUBMISSION_BUNDLE_INVENTORY_SCHEMA:
        raise ValueError(f"{SUBMISSION_BUNDLE_INVENTORY_REL}: unsupported schema_version")
    return loaded


def require_round_start_inventory(inventory: dict[str, Any]) -> None:
    if inventory.get("producer") != "scripts/review-round-start":
        raise ValueError(
            f"{SUBMISSION_BUNDLE_INVENTORY_REL}: materialization requires inventory produced by review-round-start"
        )


def find_inventory_candidate(inventory: dict[str, Any], candidate_id: str) -> dict[str, Any]:
    candidates = inventory.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("submission bundle inventory has no candidates list")
    matches = [item for item in candidates if isinstance(item, dict) and item.get("candidate_id") == candidate_id]
    if not matches:
        raise ValueError(f"Unknown submission bundle candidate id: {candidate_id}")
    if len(matches) > 1:
        raise ValueError(f"Duplicate candidate id in submission bundle inventory: {candidate_id}")
    return matches[0]


def portable_filename(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_name = normalized.encode("ascii", errors="ignore").decode("ascii")
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", ascii_name).strip(" .-")
    if not safe:
        safe = "artifact"
    base = safe.split(".", 1)[0].upper()
    if base in WINDOWS_RESERVED_NAMES:
        safe = f"artifact-{safe}"
    return safe


def default_materialized_ref(candidate: dict[str, Any]) -> str:
    candidate_id = str(candidate.get("candidate_id") or "candidate")
    chain = candidate.get("nested_path_chain")
    leaf = "artifact"
    if isinstance(chain, list) and chain:
        last = chain[-1]
        if isinstance(last, str):
            leaf = PurePosixPath(last).name
    return f"inputs/{candidate_id}-{portable_filename(leaf)}"


def validate_materialized_ref(output_ref: str) -> None:
    if not is_safe_round_relative_path(output_ref):
        raise ValueError(f"Materialized output ref must be a safe round-relative path: {output_ref}")
    if not output_ref.startswith("inputs/"):
        raise ValueError(f"Materialized output ref must stay under inputs/: {output_ref}")
    if len(PurePosixPath(output_ref).parts) != 2:
        raise ValueError(f"Materialized output ref must be a direct inputs/ child: {output_ref}")
    unsafe_reason = unsafe_portable_member_reason(output_ref)
    if unsafe_reason is not None:
        raise ValueError(f"Materialized output ref is not portable: {unsafe_reason}")


def read_archive_member_bytes(
    path_or_data: Path | bytes,
    *,
    suffix: str,
    member_name: str,
    max_bytes: int,
) -> bytes:
    unsafe_reason = unsafe_portable_member_reason(member_name)
    if unsafe_reason is not None:
        raise ValueError(f"{member_name}: {unsafe_reason}")
    if suffix == ".zip":
        try:
            handle_context = zipfile.ZipFile(
                path_or_data if isinstance(path_or_data, Path) else io.BytesIO(path_or_data)
            )
            with handle_context as handle:
                for info in handle.infolist():
                    if normalize_artifact_path(info.filename) != member_name:
                        continue
                    if info.is_dir():
                        raise ValueError(f"{member_name}: archive member is a directory")
                    if info.file_size > max_bytes:
                        raise ValueError(f"{member_name}: exceeds materialization limit {format_bytes(max_bytes)}")
                    return handle.read(info)
        except (OSError, zipfile.BadZipFile) as exc:
            raise ValueError(f"Cannot read ZIP member {member_name}: {exc}") from exc
    elif suffix in {".tar", ".tar.gz", ".tar.bz2", ".tar.xz", ".tgz", ".tbz", ".tbz2", ".txz"}:
        try:
            if isinstance(path_or_data, Path):
                with tarfile.open(path_or_data, mode="r:*") as handle:
                    return read_tar_member_bytes(handle, member_name=member_name, max_bytes=max_bytes)
            else:
                with tarfile.open(fileobj=io.BytesIO(path_or_data), mode="r:*") as handle:
                    return read_tar_member_bytes(handle, member_name=member_name, max_bytes=max_bytes)
        except (OSError, tarfile.TarError) as exc:
            raise ValueError(f"Cannot read TAR member {member_name}: {exc}") from exc
    else:
        raise ValueError(f"Unsupported archive suffix for materialization: {suffix}")
    raise ValueError(f"Archive member not found: {member_name}")


def read_tar_member_bytes(handle: tarfile.TarFile, *, member_name: str, max_bytes: int) -> bytes:
    for member in handle:
        if normalize_artifact_path(member.name) != member_name:
            continue
        if not member.isfile():
            raise ValueError(f"{member_name}: archive member is not a file")
        if member.size > max_bytes:
            raise ValueError(f"{member_name}: exceeds materialization limit {format_bytes(max_bytes)}")
        extracted = handle.extractfile(member)
        if extracted is None:
            raise ValueError(f"{member_name}: archive member cannot be read")
        return extracted.read()
    raise ValueError(f"Archive member not found: {member_name}")


def read_candidate_bytes(
    *,
    round_dir: Path,
    source_ref: str,
    nested_path_chain: tuple[str, ...],
    max_materialize_bytes: int,
) -> bytes:
    source = resolve_source_bundle(round_dir, source_ref, BundleInventoryLimits())
    if not nested_path_chain:
        if not source.path.is_file():
            raise ValueError(f"{source_ref}: source bundle is not a materializable file candidate")
        if source.path.stat().st_size > max_materialize_bytes:
            raise ValueError(f"{source_ref}: exceeds materialization limit {format_bytes(max_materialize_bytes)}")
        return source.path.read_bytes()
    if source.kind == "directory":
        current_path = source.path
        current_data: bytes | None = None
        current_suffix = ""
        for index, part in enumerate(nested_path_chain):
            unsafe_reason = unsafe_portable_member_reason(part)
            if unsafe_reason is not None:
                raise ValueError(f"{part}: {unsafe_reason}")
            if current_data is None:
                next_path = current_path / part
                ensure_directory_materialization_path(source.path, next_path, label=part)
                if index == len(nested_path_chain) - 1:
                    if not next_path.is_file():
                        raise ValueError(f"{part}: directory candidate is not a file")
                    if next_path.stat().st_size > max_materialize_bytes:
                        raise ValueError(f"{part}: exceeds materialization limit {format_bytes(max_materialize_bytes)}")
                    return next_path.read_bytes()
                if not next_path.is_file():
                    raise ValueError(f"{part}: directory nested archive candidate is not a file")
                if next_path.stat().st_size > max_materialize_bytes:
                    raise ValueError(f"{part}: exceeds materialization limit {format_bytes(max_materialize_bytes)}")
                current_data = next_path.read_bytes()
                current_suffix = archive_suffix(next_path)
            else:
                data = read_archive_member_bytes(
                    current_data,
                    suffix=current_suffix,
                    member_name=part,
                    max_bytes=max_materialize_bytes,
                )
                if index == len(nested_path_chain) - 1:
                    return data
                current_data = data
                current_suffix = archive_name_suffix(part)
        raise ValueError("Empty nested path chain")
    current_data_or_path: Path | bytes = source.path
    current_suffix = archive_suffix(source.path)
    for index, part in enumerate(nested_path_chain):
        data = read_archive_member_bytes(
            current_data_or_path,
            suffix=current_suffix,
            member_name=part,
            max_bytes=max_materialize_bytes,
        )
        if index == len(nested_path_chain) - 1:
            return data
        current_data_or_path = data
        current_suffix = archive_name_suffix(part)
    raise ValueError("Empty nested path chain")


def ensure_directory_materialization_path(source_root: Path, target: Path, *, label: str) -> None:
    try:
        relative = target.relative_to(source_root)
    except ValueError as exc:
        raise ValueError(f"{label}: directory candidate is outside source root") from exc
    current = source_root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"{label}: refusing to materialize through a symlink")
    try:
        target.resolve(strict=True).relative_to(source_root.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise ValueError(f"{label}: resolved candidate escapes source root") from exc


def load_materialization_manifest(path: Path, *, case_id: str, round_id: str) -> dict[str, Any]:
    if not path.is_file():
        return {
            "schema_version": SUBMISSION_BUNDLE_MATERIALIZATION_SCHEMA,
            "case_id": case_id,
            "round_id": round_id,
            "generated_at": now_utc(),
            "producer": SUBMISSION_BUNDLE_MATERIALIZATION_PRODUCER,
            "materializations": [],
        }
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict) or loaded.get("schema_version") != SUBMISSION_BUNDLE_MATERIALIZATION_SCHEMA:
        raise ValueError(f"{SUBMISSION_BUNDLE_MATERIALIZATION_REL}: unsupported schema_version")
    if loaded.get("case_id") != case_id or loaded.get("round_id") != round_id:
        raise ValueError(f"{SUBMISSION_BUNDLE_MATERIALIZATION_REL}: case_id/round_id mismatch")
    if not isinstance(loaded.get("materializations"), list):
        raise ValueError(f"{SUBMISSION_BUNDLE_MATERIALIZATION_REL}: materializations must be a list")
    return loaded


def write_materialization_manifest(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def load_expansion_manifest(path: Path, *, case_id: str, round_id: str) -> dict[str, Any]:
    if not path.is_file():
        return {
            "schema_version": SUBMISSION_BUNDLE_EXPANSION_SCHEMA,
            "case_id": case_id,
            "round_id": round_id,
            "generated_at": now_utc(),
            "producer": SUBMISSION_BUNDLE_EXPANSION_PRODUCER,
            "target_root_ref": SUBMISSION_BUNDLE_EXPANDED_ROOT_REL,
            "limits": BundleExpansionLimits().as_record(),
            "expansions": [],
            "skipped_entries": [],
        }
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict) or loaded.get("schema_version") != SUBMISSION_BUNDLE_EXPANSION_SCHEMA:
        raise ValueError(f"{SUBMISSION_BUNDLE_EXPANSION_REL}: unsupported schema_version")
    if loaded.get("case_id") != case_id or loaded.get("round_id") != round_id:
        raise ValueError(f"{SUBMISSION_BUNDLE_EXPANSION_REL}: case_id/round_id mismatch")
    if not isinstance(loaded.get("expansions"), list):
        raise ValueError(f"{SUBMISSION_BUNDLE_EXPANSION_REL}: expansions must be a list")
    if not isinstance(loaded.get("skipped_entries"), list):
        raise ValueError(f"{SUBMISSION_BUNDLE_EXPANSION_REL}: skipped_entries must be a list")
    return loaded


def write_expansion_manifest(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def source_expansion_ref(source: SourceBundle) -> str:
    leaf = portable_filename(PurePosixPath(source.ref).name)
    return f"{SUBMISSION_BUNDLE_EXPANDED_ROOT_REL}/{source.sha256[:12]}-{leaf}"


def ensure_expansion_root(round_dir: Path) -> Path:
    work_dir = round_dir / "work"
    if work_dir.exists() and work_dir.is_symlink():
        raise ValueError("Expansion work directory must not be a symlink")
    work_dir.mkdir(parents=True, exist_ok=True)
    root = round_dir / SUBMISSION_BUNDLE_EXPANDED_ROOT_REL
    if root.exists() and root.is_symlink():
        raise ValueError(f"Expansion root must not be a symlink: {SUBMISSION_BUNDLE_EXPANDED_ROOT_REL}")
    try:
        root.resolve(strict=False).relative_to(round_dir.resolve(strict=False))
    except ValueError as exc:
        raise ValueError(
            f"Expansion root must stay below the round directory: {SUBMISSION_BUNDLE_EXPANDED_ROOT_REL}"
        ) from exc
    return root


def ensure_expansion_target(round_dir: Path, target: Path) -> None:
    root = ensure_expansion_root(round_dir)
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Expansion target is outside {SUBMISSION_BUNDLE_EXPANDED_ROOT_REL}: {target}") from exc
    if target == root:
        raise ValueError(f"Expansion target must be below {SUBMISSION_BUNDLE_EXPANDED_ROOT_REL}")
    if target.is_symlink():
        raise ValueError(f"Expansion target is a symlink: {target}")


def expansion_tree_state(root: Path) -> dict[str, int | str]:
    digest = hashlib.sha256()
    digest.update(b"submission-bundle-expansion-tree-v1\0")
    file_count = 0
    directory_count = 0
    byte_count = 0
    for child in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        rel = child.relative_to(root).as_posix()
        if child.is_symlink():
            raise ValueError(f"{rel}: expanded workspace must not contain symlinks")
        if child.is_dir():
            directory_count += 1
            digest.update(b"D\0")
            digest.update(rel.encode("utf-8", errors="surrogateescape"))
            digest.update(b"\0")
            continue
        if not child.is_file():
            raise ValueError(f"{rel}: expanded workspace contains an unsupported file type")
        size = child.stat().st_size
        file_count += 1
        byte_count += size
        digest.update(b"F\0")
        digest.update(rel.encode("utf-8", errors="surrogateescape"))
        digest.update(b"\0")
        digest.update(str(size).encode("ascii"))
        digest.update(b"\0")
        digest.update(sha256_file(child).encode("ascii"))
        digest.update(b"\0")
    return {
        "target_tree_sha256": digest.hexdigest(),
        "target_tree_file_count": file_count,
        "target_tree_directory_count": directory_count,
        "target_tree_bytes": byte_count,
    }


def expansion_record_matches_target(record: dict[str, Any], target: Path, limits: BundleExpansionLimits) -> bool:
    if record.get("limits") != limits.as_record():
        return False
    try:
        state = expansion_tree_state(target)
    except (OSError, ValueError):
        return False
    return all(record.get(key) == value for key, value in state.items())


def safe_child_target(root: Path, rel_path: str) -> Path:
    parts = PurePosixPath(rel_path).parts
    target = root.joinpath(*parts)
    current = root
    for part in parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"{rel_path}: refusing to extract through a symlinked parent")
    try:
        target.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError as exc:
        raise ValueError(f"{rel_path}: extraction target escapes expansion root") from exc
    return target


def expansion_skip(
    stats: ExpansionStats,
    *,
    chain: tuple[str, ...],
    reason_code: str,
    detail: str,
    archive_depth: int,
    target_ref: str = "",
) -> None:
    stats.skipped_entries.append(
        {
            "source_bundle_ref": stats.source_ref,
            "nested_path_chain": list(chain),
            "target_ref": target_ref,
            "reason_code": reason_code,
            "detail": detail,
            "archive_depth": archive_depth,
        }
    )


def write_expanded_file(
    *,
    target: Path,
    source: Any,
    size: int,
    label: str,
    stats: ExpansionStats,
    budget: ExpansionBudget,
    limits: BundleExpansionLimits,
) -> str | None:
    if size > limits.max_file_bytes:
        return f"{label}: exceeds per-file expansion limit {format_bytes(limits.max_file_bytes)}"
    budget_error = budget.reserve(label, size)
    if budget_error is not None:
        return budget_error
    if target.is_symlink():
        return f"{label}: target path is a symlink"
    if target.exists():
        return f"{label}: target path already exists"
    target.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    error: str | None = None
    with target.open("wb") as destination:
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk:
                break
            written += len(chunk)
            if written > size:
                error = f"{label}: wrote more bytes than declared"
                break
            destination.write(chunk)
    if error is not None:
        target.unlink(missing_ok=True)
        return error
    stats.files_written += 1
    stats.bytes_written += written
    return None


def expand_nested_archive_if_supported(
    *,
    archive_path: Path,
    chain: tuple[str, ...],
    depth: int,
    limits: BundleExpansionLimits,
    stats: ExpansionStats,
    budget: ExpansionBudget,
) -> None:
    suffix = archive_suffix(archive_path)
    if suffix not in SUPPORTED_ARCHIVE_SUFFIXES:
        return
    if depth >= limits.max_archive_depth:
        expansion_skip(
            stats,
            chain=chain,
            reason_code="nested_archive_depth_limit",
            detail=f"nested archive not expanded past depth {limits.max_archive_depth}",
            archive_depth=depth,
            target_ref=str(archive_path),
        )
        return
    chain_digest = hashlib.sha256("\0".join(chain).encode("utf-8", errors="surrogateescape")).hexdigest()[:12]
    nested_target = archive_path.with_name(f"{archive_path.name}.contents-{chain_digest}")
    nested_target.mkdir(parents=True, exist_ok=True)
    expand_supported_archive(
        archive_path,
        suffix=suffix,
        target_dir=nested_target,
        chain=chain,
        depth=depth + 1,
        limits=limits,
        stats=stats,
        budget=budget,
    )


def expand_zip_archive(
    archive_path: Path,
    *,
    target_dir: Path,
    chain: tuple[str, ...],
    depth: int,
    limits: BundleExpansionLimits,
    stats: ExpansionStats,
    budget: ExpansionBudget,
) -> None:
    registry = PortablePathRegistry()
    stats.archives_expanded += 1
    try:
        with zipfile.ZipFile(archive_path) as handle:
            for info in handle.infolist():
                if not reserve_expansion_entry(
                    stats,
                    chain=chain,
                    limits=limits,
                    archive_depth=depth,
                    detail=f"stopped after {limits.max_entries} total expanded entries",
                ):
                    break
                normalized = normalize_artifact_path(info.filename)
                member_chain = (*chain, normalized)
                unsafe_reason = unsafe_portable_member_reason(info.filename)
                if unsafe_reason is not None:
                    expansion_skip(
                        stats,
                        chain=member_chain,
                        reason_code="unsafe_archive_member_path",
                        detail=unsafe_reason,
                        archive_depth=depth,
                    )
                    continue
                collision = registry.register(normalized, kind="directory" if info.is_dir() else "file")
                if collision is not None:
                    expansion_skip(
                        stats,
                        chain=member_chain,
                        reason_code=path_collision_reason_code(collision),
                        detail=collision,
                        archive_depth=depth,
                    )
                    continue
                try:
                    target = safe_child_target(target_dir, normalized)
                except ValueError as exc:
                    expansion_skip(
                        stats,
                        chain=member_chain,
                        reason_code="unsafe_archive_member_path",
                        detail=str(exc),
                        archive_depth=depth,
                    )
                    continue
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    stats.directories_written += 1
                    continue
                with handle.open(info) as source:
                    error = write_expanded_file(
                        target=target,
                        source=source,
                        size=info.file_size,
                        label=info.filename,
                        stats=stats,
                        budget=budget,
                        limits=limits,
                    )
                if error is not None:
                    expansion_skip(
                        stats,
                        chain=member_chain,
                        reason_code="expansion_write_skipped",
                        detail=error,
                        archive_depth=depth,
                    )
                    continue
                expand_nested_archive_if_supported(
                    archive_path=target,
                    chain=member_chain,
                    depth=depth,
                    limits=limits,
                    stats=stats,
                    budget=budget,
                )
    except (OSError, zipfile.BadZipFile) as exc:
        expansion_skip(
            stats,
            chain=chain,
            reason_code="archive_metadata_unreadable",
            detail=str(exc),
            archive_depth=depth,
        )


def expand_tar_archive(
    archive_path: Path,
    *,
    target_dir: Path,
    chain: tuple[str, ...],
    depth: int,
    limits: BundleExpansionLimits,
    stats: ExpansionStats,
    budget: ExpansionBudget,
) -> None:
    registry = PortablePathRegistry()
    stats.archives_expanded += 1
    try:
        with tarfile.open(archive_path, mode="r:*") as handle:
            for member in handle:
                if not reserve_expansion_entry(
                    stats,
                    chain=chain,
                    limits=limits,
                    archive_depth=depth,
                    detail=f"stopped after {limits.max_entries} total expanded entries",
                ):
                    break
                normalized = normalize_artifact_path(member.name)
                member_chain = (*chain, normalized)
                unsafe_reason = unsafe_portable_member_reason(member.name)
                if unsafe_reason is not None:
                    expansion_skip(
                        stats,
                        chain=member_chain,
                        reason_code="unsafe_archive_member_path",
                        detail=unsafe_reason,
                        archive_depth=depth,
                    )
                    continue
                kind = "directory" if member.isdir() else "file"
                collision = registry.register(normalized, kind=kind)
                if collision is not None:
                    expansion_skip(
                        stats,
                        chain=member_chain,
                        reason_code=path_collision_reason_code(collision),
                        detail=collision,
                        archive_depth=depth,
                    )
                    continue
                try:
                    target = safe_child_target(target_dir, normalized)
                except ValueError as exc:
                    expansion_skip(
                        stats,
                        chain=member_chain,
                        reason_code="unsafe_archive_member_path",
                        detail=str(exc),
                        archive_depth=depth,
                    )
                    continue
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                    stats.directories_written += 1
                    continue
                if not member.isfile():
                    expansion_skip(
                        stats,
                        chain=member_chain,
                        reason_code="unsupported_tar_member_type",
                        detail="only regular files and directories are expanded",
                        archive_depth=depth,
                    )
                    continue
                extracted = handle.extractfile(member)
                if extracted is None:
                    expansion_skip(
                        stats,
                        chain=member_chain,
                        reason_code="archive_member_unreadable",
                        detail="tar member cannot be opened",
                        archive_depth=depth,
                    )
                    continue
                with extracted:
                    error = write_expanded_file(
                        target=target,
                        source=extracted,
                        size=member.size,
                        label=member.name,
                        stats=stats,
                        budget=budget,
                        limits=limits,
                    )
                if error is not None:
                    expansion_skip(
                        stats,
                        chain=member_chain,
                        reason_code="expansion_write_skipped",
                        detail=error,
                        archive_depth=depth,
                    )
                    continue
                expand_nested_archive_if_supported(
                    archive_path=target,
                    chain=member_chain,
                    depth=depth,
                    limits=limits,
                    stats=stats,
                    budget=budget,
                )
    except (OSError, tarfile.TarError) as exc:
        expansion_skip(
            stats,
            chain=chain,
            reason_code="archive_metadata_unreadable",
            detail=str(exc),
            archive_depth=depth,
        )


def expand_supported_archive(
    archive_path: Path,
    *,
    suffix: str,
    target_dir: Path,
    chain: tuple[str, ...],
    depth: int,
    limits: BundleExpansionLimits,
    stats: ExpansionStats,
    budget: ExpansionBudget,
) -> None:
    if suffix == ".zip":
        expand_zip_archive(
            archive_path,
            target_dir=target_dir,
            chain=chain,
            depth=depth,
            limits=limits,
            stats=stats,
            budget=budget,
        )
        return
    if suffix in {".tar", ".tar.gz", ".tar.bz2", ".tar.xz", ".tgz", ".tbz", ".tbz2", ".txz"}:
        expand_tar_archive(
            archive_path,
            target_dir=target_dir,
            chain=chain,
            depth=depth,
            limits=limits,
            stats=stats,
            budget=budget,
        )
        return
    expansion_skip(
        stats,
        chain=chain,
        reason_code="unsupported_archive_type",
        detail=f"unsupported archive suffix {suffix}",
        archive_depth=depth,
    )


def copy_file_to_expansion(
    *,
    source_path: Path,
    target_path: Path,
    chain: tuple[str, ...],
    limits: BundleExpansionLimits,
    stats: ExpansionStats,
    budget: ExpansionBudget,
) -> None:
    with source_path.open("rb") as source:
        error = write_expanded_file(
            target=target_path,
            source=source,
            size=source_path.stat().st_size,
            label=source_path.name,
            stats=stats,
            budget=budget,
            limits=limits,
        )
    if error is not None:
        expansion_skip(
            stats,
            chain=chain,
            reason_code="expansion_write_skipped",
            detail=error,
            archive_depth=0,
        )


def copy_directory_to_expansion(
    *,
    source: SourceBundle,
    target_dir: Path,
    limits: BundleExpansionLimits,
    stats: ExpansionStats,
    budget: ExpansionBudget,
) -> None:
    registry = PortablePathRegistry()
    for child in sorted(source.path.rglob("*"), key=lambda item: item.as_posix()):
        if not reserve_expansion_entry(
            stats,
            chain=(),
            limits=limits,
            archive_depth=0,
            detail=f"stopped after {limits.max_entries} total expanded entries",
        ):
            break
        rel = child.relative_to(source.path).as_posix()
        if child.is_symlink():
            expansion_skip(
                stats,
                chain=(rel,),
                reason_code="directory_symlink_skipped",
                detail="directory symlink skipped",
                archive_depth=0,
            )
            continue
        if not child.is_file() and not child.is_dir():
            continue
        unsafe_reason = unsafe_portable_member_reason(rel)
        if unsafe_reason is not None:
            expansion_skip(
                stats,
                chain=(rel,),
                reason_code="unsafe_directory_member_path",
                detail=unsafe_reason,
                archive_depth=0,
            )
            continue
        collision = registry.register(rel, kind="directory" if child.is_dir() else "file")
        if collision is not None:
            expansion_skip(
                stats,
                chain=(rel,),
                reason_code=path_collision_reason_code(collision),
                detail=collision,
                archive_depth=0,
            )
            continue
        target = safe_child_target(target_dir, rel)
        if child.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            stats.directories_written += 1
            continue
        copy_file_to_expansion(
            source_path=child,
            target_path=target,
            chain=(rel,),
            limits=limits,
            stats=stats,
            budget=budget,
        )
        expand_nested_archive_if_supported(
            archive_path=target,
            chain=(rel,),
            depth=0,
            limits=limits,
            stats=stats,
            budget=budget,
        )


def expansion_record(
    *,
    source: SourceBundle,
    target_ref: str,
    stats: ExpansionStats,
    limits: BundleExpansionLimits,
    action: str,
    tree_state: dict[str, int | str],
) -> dict[str, Any]:
    return {
        "source_bundle_ref": source.ref,
        "source_bundle_sha256": source.sha256,
        "kind": source.kind,
        "size_bytes": source.size_bytes,
        "target_ref": target_ref,
        "action": action,
        "files_written": stats.files_written,
        "directories_written": stats.directories_written,
        "archives_expanded": stats.archives_expanded,
        "entries_seen": stats.entries_seen,
        "bytes_written": stats.bytes_written,
        "skipped_entry_count": len(stats.skipped_entries),
        "limits": limits.as_record(),
        **tree_state,
    }


def materialize_submission_bundles(
    *,
    case_id: str,
    round_id: str,
    round_dir: Path,
    bundle_refs: Iterable[str],
    limits: BundleExpansionLimits | None = None,
    generated_at: str | None = None,
    producer: str = SUBMISSION_BUNDLE_EXPANSION_PRODUCER,
    refresh: bool = False,
) -> tuple[dict[str, Any], Path]:
    active_limits = limits or BundleExpansionLimits()
    manifest_path = round_dir / SUBMISSION_BUNDLE_EXPANSION_REL
    existing = load_expansion_manifest(manifest_path, case_id=case_id, round_id=round_id)
    existing_by_source = {
        (item.get("source_bundle_ref"), item.get("source_bundle_sha256")): item
        for item in existing.get("expansions", [])
        if isinstance(item, dict)
    }
    budget = ExpansionBudget(active_limits.max_total_bytes)
    expansions: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for bundle_ref in bundle_refs:
        source = resolve_source_bundle(round_dir, bundle_ref, BundleInventoryLimits())
        target_ref = source_expansion_ref(source)
        target = round_dir / target_ref
        ensure_expansion_target(round_dir, target)
        existing_record = existing_by_source.get((source.ref, source.sha256))
        if (
            not refresh
            and isinstance(existing_record, dict)
            and target.is_dir()
            and expansion_record_matches_target(existing_record, target, active_limits)
        ):
            reused = dict(existing_record)
            reused["action"] = "reused_existing"
            expansions.append(reused)
            continue
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        target.mkdir(parents=True, exist_ok=True)
        stats = ExpansionStats(source_ref=source.ref, target_ref=target_ref)
        if source.kind == "directory":
            copy_directory_to_expansion(
                source=source,
                target_dir=target,
                limits=active_limits,
                stats=stats,
                budget=budget,
            )
        else:
            suffix = archive_suffix(source.path)
            if suffix in SUPPORTED_ARCHIVE_SUFFIXES:
                expand_supported_archive(
                    source.path,
                    suffix=suffix,
                    target_dir=target,
                    chain=(),
                    depth=0,
                    limits=active_limits,
                    stats=stats,
                    budget=budget,
                )
            else:
                target_file = target / portable_filename(PurePosixPath(source.ref).name)
                copy_file_to_expansion(
                    source_path=source.path,
                    target_path=target_file,
                    chain=(),
                    limits=active_limits,
                    stats=stats,
                    budget=budget,
                )
        skipped.extend(stats.skipped_entries)
        tree_state = expansion_tree_state(target)
        expansions.append(
            expansion_record(
                source=source,
                target_ref=target_ref,
                stats=stats,
                limits=active_limits,
                action="expanded",
                tree_state=tree_state,
            )
        )
    payload = {
        "schema_version": SUBMISSION_BUNDLE_EXPANSION_SCHEMA,
        "case_id": case_id,
        "round_id": round_id,
        "generated_at": generated_at or now_utc(),
        "producer": producer,
        "target_root_ref": SUBMISSION_BUNDLE_EXPANDED_ROOT_REL,
        "limits": active_limits.as_record(),
        "expansions": expansions,
        "skipped_entries": skipped,
    }
    write_expansion_manifest(manifest_path, payload)
    return payload, manifest_path


def materialize_submission_bundle_candidate(
    *,
    case_id: str,
    round_id: str,
    round_dir: Path,
    candidate_id: str,
    output_ref: str | None = None,
    allow_ambiguous: bool = False,
    allow_duplicate: bool = False,
    max_materialize_bytes: int = 250 * 1024 * 1024,
    generated_at: str | None = None,
    producer: str = SUBMISSION_BUNDLE_MATERIALIZATION_PRODUCER,
) -> MaterializedCandidate:
    inventory = load_submission_bundle_inventory(round_dir)
    if inventory.get("case_id") != case_id or inventory.get("round_id") != round_id:
        raise ValueError(f"{SUBMISSION_BUNDLE_INVENTORY_REL}: case_id/round_id mismatch")
    require_round_start_inventory(inventory)
    candidate = find_inventory_candidate(inventory, candidate_id)
    state = candidate.get("state")
    if state == "needs_operator_selection" and not allow_ambiguous:
        raise ValueError(f"{candidate_id}: candidate requires explicit --allow-ambiguous selection")
    if state == "duplicate_candidate" and not allow_duplicate:
        raise ValueError(f"{candidate_id}: candidate requires explicit --allow-duplicate selection")
    if state not in {
        "materialize_candidate",
        "needs_operator_selection",
        "duplicate_candidate",
        "nested_archive_depth_limit",
    }:
        raise ValueError(f"{candidate_id}: candidate state {state!r} cannot be materialized")

    source_ref = candidate.get("source_bundle_ref")
    chain = candidate.get("nested_path_chain")
    if (
        not isinstance(source_ref, str)
        or not isinstance(chain, list)
        or not all(isinstance(item, str) for item in chain)
    ):
        raise ValueError(f"{candidate_id}: inventory candidate is missing source path data")
    target_ref = output_ref or default_materialized_ref(candidate)
    validate_materialized_ref(target_ref)

    data = read_candidate_bytes(
        round_dir=round_dir,
        source_ref=source_ref,
        nested_path_chain=tuple(chain),
        max_materialize_bytes=max_materialize_bytes,
    )
    data_sha256 = sha256_bytes(data)
    expected_sha = candidate.get("sha256")
    if isinstance(expected_sha, str) and expected_sha and expected_sha != data_sha256:
        raise ValueError(f"{candidate_id}: source bytes no longer match inventory hash")

    target_path = round_dir / target_ref
    action = "materialized"
    if target_path.exists():
        if not target_path.is_file():
            raise ValueError(f"{target_ref}: target exists and is not a file")
        if sha256_file(target_path) != data_sha256:
            raise ValueError(f"{target_ref}: target exists with different content")
        action = "reused_existing"
    else:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(data)

    candidate["materialized_ref"] = target_ref
    inventory_path = round_dir / SUBMISSION_BUNDLE_INVENTORY_REL
    write_submission_bundle_inventory(round_dir=round_dir, payload=inventory)
    manifest_path = round_dir / SUBMISSION_BUNDLE_MATERIALIZATION_REL
    manifest = load_materialization_manifest(manifest_path, case_id=case_id, round_id=round_id)
    materializations = manifest["materializations"]
    current_inventory_sha256 = sha256_file(inventory_path)
    for item in materializations:
        if isinstance(item, dict) and item.get("source_inventory_ref") == SUBMISSION_BUNDLE_INVENTORY_REL:
            item["source_inventory_sha256"] = current_inventory_sha256
    record = {
        "candidate_id": candidate_id,
        "source_bundle_ref": source_ref,
        "source_bundle_sha256": candidate.get("source_bundle_sha256", ""),
        "nested_path_chain": chain,
        "source_candidate_ref": candidate.get("candidate_ref", ""),
        "source_member_sha256": data_sha256,
        "artifact_class": candidate.get("artifact_class", ""),
        "reason_codes": candidate.get("reason_codes", []),
        "state_at_selection": state,
        "action": action,
        "materialized_ref": target_ref,
        "materialized_sha256": data_sha256,
        "size_bytes": len(data),
        "selected_at": generated_at or now_utc(),
        "producer": producer,
        "source_inventory_ref": SUBMISSION_BUNDLE_INVENTORY_REL,
        "source_inventory_sha256": current_inventory_sha256,
    }
    materializations[:] = [
        item
        for item in materializations
        if not isinstance(item, dict)
        or item.get("candidate_id") != candidate_id
        or item.get("materialized_ref") != target_ref
    ]
    materializations.append(record)
    manifest["generated_at"] = generated_at or now_utc()
    write_materialization_manifest(manifest_path, manifest)
    return MaterializedCandidate(
        candidate=candidate,
        materialized_ref=target_ref,
        materialized_path=target_path,
        materialized_sha256=data_sha256,
        manifest_path=manifest_path,
        action=action,
    )


def build_and_write_submission_bundle_inventory(
    *,
    case_id: str,
    round_id: str,
    round_dir: Path,
    bundle_refs: Iterable[str],
    limits: BundleInventoryLimits | None = None,
    generated_at: str | None = None,
    producer: str = SUBMISSION_BUNDLE_PRODUCER,
) -> tuple[dict[str, Any], Path, Path]:
    payload = build_submission_bundle_inventory(
        case_id=case_id,
        round_id=round_id,
        round_dir=round_dir,
        bundle_refs=bundle_refs,
        limits=limits,
        generated_at=generated_at,
        producer=producer,
    )
    json_path, md_path = write_submission_bundle_inventory(round_dir=round_dir, payload=payload)
    return payload, json_path, md_path
