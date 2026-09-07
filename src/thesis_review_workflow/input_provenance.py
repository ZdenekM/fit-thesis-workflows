"""Normalized, deduplicated input storage with a provenance record.

`## Audit Base` of the supervision season readiness plan measured two rounds storing the
same similarity report twice under two names and extracting both copies, plus filenames
carrying download suffixes and one broken-encoding name. Both entrypoints that import
inputs - `import-round` and `bootstrap-case`, which builds its own copy plan - go through
this module, so a round ends up with one copy per distinct content, a name that a Windows
operator can actually store, and a record saying where each original went.

Deduplication is physical, never logical: an operator who supplies the same PDF as both
thesis and assignment declared two inputs with two roles, and downstream metadata filters
by role, so both occurrences survive pointing at one stored file.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import urllib.parse
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from thesis_review_workflow.paths import is_safe_round_relative_path

INPUT_PROVENANCE_REL = "work/input_provenance.json"
INPUT_PROVENANCE_SCHEMA = "input-provenance-v1"

WINDOWS_RESERVED_BASENAMES = frozenset(
    {
        "con",
        "prn",
        "aux",
        "nul",
        *(f"com{digit}" for digit in range(1, 10)),
        *(f"lpt{digit}" for digit in range(1, 10)),
    }
)
UNSAFE_CHARACTERS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
DOWNLOAD_SUFFIX_RE = re.compile(r"[ _-]*\((\d+)\)$")
SEPARATOR_RUN_RE = re.compile(r"[\s_]+")
DASH_RUN_RE = re.compile(r"-{2,}")
FALLBACK_STEM = "input"
MAX_STORED_NAME_BYTES = 120
"""Byte budget for a stored basename.

NFC composition can expand a name rather than shrink it, so a source name that is legal on
ext4 can normalize past the 255-byte limit and make the copy fail with a raw OSError. The
budget is well under 255 because the name sits below `rounds/<round-id>/inputs/`, and
Windows bounds the whole path rather than the component.
"""
BIDI_CONTROL_RE = re.compile("[\u200e\u200f\u202a-\u202e\u2066-\u2069]")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def percent_decoded(value: str) -> str:
    """Decode percent escapes, leaving an invalid escape literal rather than replacing it.

    Permissive decoding would silently turn an undecodable byte into a replacement
    character, which loses the operator's original text irreversibly. A name that does not
    decode cleanly keeps its escapes and stays recognizable.
    """

    if "%" not in value:
        return value
    try:
        decoded = urllib.parse.unquote(value, errors="strict")
    except (UnicodeDecodeError, ValueError):
        return value
    return decoded


def normalize_input_name(name: str) -> str:
    """A stored basename that is deterministic, recognizable and storable on Windows.

    Order matters: decoding can introduce combining characters, so NFC runs after it.
    """

    suffix_source = PurePosixPath(name.replace("\\", "/")).name or name
    decoded = percent_decoded(suffix_source)
    normalized = unicodedata.normalize("NFC", decoded)
    normalized = UNSAFE_CHARACTERS_RE.sub("-", normalized)
    # A stored name whose display order is reversed is not recognizable, which is the whole
    # point of keeping the stem, so bidi and isolate controls go too.
    normalized = BIDI_CONTROL_RE.sub("", normalized)
    path = PurePosixPath(normalized)
    stem, suffix = path.stem, path.suffix.lower()
    if not stem and suffix:
        # A dotfile such as `.gitignore` parses as suffix-only; treat it as the stem. The
        # leading dot does not survive the strip below, on purpose: a stored input should not
        # be hidden in a directory an operator browses.
        stem, suffix = suffix, ""
    stem = DOWNLOAD_SUFFIX_RE.sub("", stem)
    stem = SEPARATOR_RUN_RE.sub("-", stem.strip())
    stem = DASH_RUN_RE.sub("-", stem).strip("-. ")
    if stem.casefold() in WINDOWS_RESERVED_BASENAMES:
        stem = f"{stem}-input"
    if not stem or stem in {".", ".."}:
        stem = FALLBACK_STEM
    suffix = suffix.rstrip(". ")
    candidate = bounded_name(stem, suffix)
    if candidate in {".", ".."} or not candidate:
        candidate = FALLBACK_STEM
    return candidate


def bounded_name(stem: str, suffix: str) -> str:
    """Join stem and suffix within the byte budget, trimming the stem rather than the suffix.

    The suffix decides how downstream code treats the file - extraction filters on it - so it
    is kept whole and the stem gives way.
    """

    suffix_bytes = suffix.encode("utf-8")
    if len(suffix_bytes) >= MAX_STORED_NAME_BYTES:
        return suffix.strip(".") or FALLBACK_STEM
    budget = MAX_STORED_NAME_BYTES - len(suffix_bytes)
    encoded = stem.encode("utf-8")
    if len(encoded) <= budget:
        return f"{stem}{suffix}"
    trimmed = encoded[:budget].decode("utf-8", errors="ignore").rstrip("-. ")
    return f"{trimmed or FALLBACK_STEM}{suffix}"


@dataclass(frozen=True)
class InputRequest:
    """One input the operator declared, before storage decides where it lands."""

    role: str
    source: Path
    dest_dir_rel: PurePosixPath


@dataclass(frozen=True)
class StoredInput:
    """One declared occurrence, and the stored file it resolves to."""

    role: str
    original_name: str
    stored_rel: str
    sha256: str
    size_bytes: int
    is_first_occurrence: bool


@dataclass(frozen=True)
class InputStoragePlan:
    copies: tuple[tuple[Path, str], ...]
    """Source path and round-relative destination for each physical copy to make."""

    records: tuple[StoredInput, ...]
    """One record per declared occurrence, in request order."""

    def stored_rel_for(self, role: str, source: Path) -> str | None:
        for record in self.records:
            if record.role == role and record.original_name == source.name:
                return record.stored_rel
        return None


def plan_input_storage(
    requests: list[InputRequest],
    *,
    refuse_case_insensitive_clash: bool = False,
) -> InputStoragePlan:
    """Decide stored names, deduplicate identical content and keep every occurrence.

    Raises ValueError when two different contents normalize to one destination, which no
    entrypoint can store; content-identical inputs are resolved first, so that error only
    fires for a genuine clash.

    `refuse_case_insensitive_clash` preserves each caller's existing guarantee about two
    names differing only in case. `import-round` refused that outright, so it still does.
    `bootstrap-case` stored both and let `code_workspace.CaseInsensitivePathRegistry` report
    the collision when unpacking, which is a tested path, so it still does.
    """

    copies: list[tuple[Path, str]] = []
    records: list[StoredInput] = []
    stored_by_digest: dict[tuple[str, str], str] = {}
    digest_by_destination: dict[str, str] = {}
    claimed_destinations: set[str] = set()

    for request in requests:
        digest = sha256_file(request.source)
        size = request.source.stat().st_size
        stored_name = normalize_input_name(request.source.name)
        destination = (request.dest_dir_rel / stored_name).as_posix()
        key = (digest, request.dest_dir_rel.as_posix())
        existing = stored_by_digest.get(key) if size else None
        if existing is not None:
            # Same bytes in the same directory: one stored file, both occurrences kept. The
            # first occurrence's stored name wins, including its suffix, so a later
            # occurrence that carried a more useful suffix is recorded as a separate copy.
            if PurePosixPath(existing).suffix == PurePosixPath(destination).suffix:
                records.append(
                    StoredInput(
                        role=request.role,
                        original_name=request.source.name,
                        stored_rel=existing,
                        sha256=digest,
                        size_bytes=size,
                        is_first_occurrence=False,
                    )
                )
                continue
        if destination in claimed_destinations and digest_by_destination.get(destination) == digest:
            # A later occurrence resolving to a destination already claimed by the same bytes.
            # Without this it would be copied and extracted a second time, which is the
            # measured defect this module exists to remove.
            records.append(
                StoredInput(
                    role=request.role,
                    original_name=request.source.name,
                    stored_rel=destination,
                    sha256=digest,
                    size_bytes=size,
                    is_first_occurrence=False,
                )
            )
            continue
        exact_claim = digest_by_destination.get(destination)
        if exact_claim is not None and exact_claim != digest:
            raise ValueError(
                f"two different inputs normalize to the same destination: {destination}; " "rename one before importing"
            )
        if refuse_case_insensitive_clash:
            for claimed_destination, claimed_digest in digest_by_destination.items():
                if claimed_destination.casefold() == destination.casefold() and claimed_digest != digest:
                    raise ValueError(
                        "two inputs would differ only by case on Windows: " f"{claimed_destination} and {destination}"
                    )
        digest_by_destination[destination] = digest
        claimed_destinations.add(destination)
        stored_by_digest.setdefault(key, destination)
        copies.append((request.source, destination))
        records.append(
            StoredInput(
                role=request.role,
                original_name=request.source.name,
                stored_rel=destination,
                sha256=digest,
                size_bytes=size,
                is_first_occurrence=True,
            )
        )
    return InputStoragePlan(copies=tuple(copies), records=tuple(records))


def directory_input_record(source: Path, stored_rel: str) -> StoredInput:
    """A provenance record for a directory input.

    Tree hashing is out of scope, so the digest is empty and the validator skips the on-disk
    hash comparison for it. Recording where the original went is not out of scope: an
    operator who imported `student repo (1)` needs to find it under its stored name.
    """

    return StoredInput(
        role="input",
        original_name=source.name,
        stored_rel=stored_rel,
        sha256="",
        size_bytes=0,
        is_first_occurrence=True,
    )


def build_input_provenance_payload(
    *,
    case_id: str,
    round_id: str,
    generated_at: str,
    records: tuple[StoredInput, ...],
) -> dict[str, object]:
    return {
        "schema_version": INPUT_PROVENANCE_SCHEMA,
        "case_id": case_id,
        "round_id": round_id,
        "generated_at": generated_at,
        "inputs": [
            {
                "role": record.role,
                "original_name": record.original_name,
                "stored_ref": record.stored_rel,
                "sha256": record.sha256,
                "size_bytes": record.size_bytes,
                "deduplicated": not record.is_first_occurrence,
            }
            for record in records
        ],
    }


def write_input_provenance(
    round_dir: Path,
    *,
    case_id: str,
    round_id: str,
    records: tuple[StoredInput, ...],
    generated_at: str | None = None,
) -> Path | None:
    """Write the provenance record, or nothing when the round imported no files."""

    if not records:
        return None
    payload = build_input_provenance_payload(
        case_id=case_id,
        round_id=round_id,
        generated_at=generated_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        records=records,
    )
    target = round_dir / INPUT_PROVENANCE_REL
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def validate_input_provenance_payload(payload: object, *, round_dir: Path | None = None) -> list[str]:
    """Structural and on-disk validation of a provenance record.

    Registering the schema buys only the envelope check, so a record with plausible fields
    but a fabricated hash, a missing file or a ref escaping the round would otherwise pass.
    """

    rel_path = INPUT_PROVENANCE_REL
    errors: list[str] = []
    if not isinstance(payload, dict):
        return [f"{rel_path}: payload must be an object"]
    inputs = payload.get("inputs")
    if not isinstance(inputs, list):
        return [f"{rel_path}: inputs must be a list"]
    for index, item in enumerate(inputs, start=1):
        prefix = f"{rel_path}: inputs[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        for field in ("role", "original_name", "stored_ref"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                errors.append(f"{prefix}: {field} must be a non-empty string")
        # An empty digest means a directory input, whose tree this slice does not hash.
        if not isinstance(item.get("sha256"), str):
            errors.append(f"{prefix}: sha256 must be a string")
        size = item.get("size_bytes")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            errors.append(f"{prefix}: size_bytes must be a non-negative integer")
        if not isinstance(item.get("deduplicated"), bool):
            errors.append(f"{prefix}: deduplicated must be a boolean")
        stored_ref = item.get("stored_ref")
        if not isinstance(stored_ref, str) or not stored_ref.strip():
            continue
        if not is_safe_round_relative_path(stored_ref) or not stored_ref.startswith("inputs/"):
            errors.append(f"{prefix}: stored_ref must be a safe round-relative path under inputs/")
            continue
        if round_dir is None:
            continue
        stored_path = round_dir / stored_ref
        digest = item.get("sha256")
        if isinstance(digest, str) and not digest:
            if not stored_path.is_dir():
                errors.append(f"{prefix}: stored_ref has no digest but is not a directory: {stored_ref}")
            continue
        if not stored_path.is_file():
            errors.append(f"{prefix}: stored_ref does not exist: {stored_ref}")
            continue
        if isinstance(digest, str) and digest != sha256_file(stored_path):
            errors.append(f"{prefix}: sha256 does not match {stored_ref}")
        if isinstance(size, int) and not isinstance(size, bool) and size != stored_path.stat().st_size:
            errors.append(f"{prefix}: size_bytes does not match {stored_ref}")
    return errors
