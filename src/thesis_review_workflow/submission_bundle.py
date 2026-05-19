"""Bounded structural inventory for submitted parent bundles."""

from __future__ import annotations

import hashlib
import io
import json
import re
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
from thesis_review_workflow.paths import is_safe_round_relative_path

SUBMISSION_BUNDLE_INVENTORY_SCHEMA = "submission-bundle-inventory-v1"
SUBMISSION_BUNDLE_INVENTORY_REL = "work/submission_bundle_inventory.json"
SUBMISSION_BUNDLE_INVENTORY_SUMMARY_REL = "work/submission_bundle_inventory.md"
SUBMISSION_BUNDLE_MATERIALIZATION_SCHEMA = "submission-bundle-materialization-v1"
SUBMISSION_BUNDLE_MATERIALIZATION_REL = "work/submission_bundle_materialization.json"
SUBMISSION_BUNDLE_PRODUCER = "scripts/inventory-submission-bundle"
SUBMISSION_BUNDLE_MATERIALIZATION_PRODUCER = "scripts/materialize-submission-bundle-candidate"

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
    max_archive_bytes: int = 250 * 1024 * 1024
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
            pending.append((key, (display, record_kind)))
        for key, record in pending:
            self._records.setdefault(key, record)
        return None


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
    tests = [item.normalized_path for item in evidence if item.artifact_class == "test_evidence"]
    readmes = [item.normalized_path for item in evidence if item.artifact_class == "readme_candidate"]
    assignments = [item.normalized_path for item in evidence if item.artifact_class == "assignment_pdf_candidate"]
    generated_or_vendor = [
        item.normalized_path for item in evidence if item.artifact_class in {"generated_or_vendor", "sample_or_vendor"}
    ]
    return {
        "entries_seen": len(names),
        "truncated": truncated,
        "code_like": bool(code_like),
        "code_like_count": len(code_like),
        "test_count": len(tests),
        "readme_count": len(readmes),
        "assignment_pdf_count": len(assignments),
        "generated_or_vendor_count": len(generated_or_vendor),
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
                    reason_codes=("case_insensitive_path_collision",),
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
                    reason_codes=("case_insensitive_path_collision",),
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

    manifest_path = round_dir / SUBMISSION_BUNDLE_MATERIALIZATION_REL
    manifest = load_materialization_manifest(manifest_path, case_id=case_id, round_id=round_id)
    materializations = manifest["materializations"]
    inventory_path = round_dir / SUBMISSION_BUNDLE_INVENTORY_REL
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
        "source_inventory_sha256": sha256_file(inventory_path),
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
    candidate["materialized_ref"] = target_ref
    write_submission_bundle_inventory(round_dir=round_dir, payload=inventory)
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
