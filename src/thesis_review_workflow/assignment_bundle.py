"""The bundle approval record that gates publishing one assignment variant.

`assignment-bundle-approval-v1` is deliberately NOT
`review_approvals::REVIEW_APPROVAL_SCHEMA`. That payload fixes one
`reviewed_artifact_path` and one `review_basis_path`, while a bundle is four
files, and it judges reviewer independence against `work/review_manifest.json`,
which a `Case kind: topic-proposal` case does not have. Field names are mirrored
where they mean the same thing; behaviour is not inherited and is re-stated here
on purpose.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from thesis_review_workflow.review_approvals import APPROVED_VERDICTS, sha256_file

BUNDLE_APPROVAL_SCHEMA = "assignment-bundle-approval-v1"

INTAKE_REL = "notes/topic_intake.md"
BRIEF_SOURCE_REL = "notes/student_brief.md"


def approval_rel(variant: str) -> str:
    return f"work/reviews/assignment_approval_{variant}.json"


def findings_rel(variant: str) -> str:
    return f"work/reviews/assignment_review_{variant}.md"


def bundle_paths(variant: str) -> tuple[str, ...]:
    """The four files one approval binds: what publishing a variant actually sends."""

    return (
        INTAKE_REL,
        BRIEF_SOURCE_REL,
        f"outputs/assignment_formal_{variant}.md",
        f"outputs/student_brief_{variant}.md",
    )


@dataclass(frozen=True)
class BundleApproval:
    case_id: str
    variant: str
    author_agent: str
    reviewer_agent: str
    reviewer_role: str
    verdict: str
    blocking_findings_count: int


def _approved(verdict: str) -> bool:
    return verdict.strip().lower() in APPROVED_VERDICTS


def _is_zero_count(value: object) -> bool:
    """A real integer zero. `False` and `0.0` both equal 0 and are not counts."""

    return isinstance(value, int) and not isinstance(value, bool) and value == 0


def build_bundle_approval_payload(
    case_dir: Path,
    *,
    case_id: str,
    variant: str,
    author_agent: str,
    reviewer_agent: str,
    reviewer_role: str,
    verdict: str,
    blocking_findings_count: int,
    checks_observed: list[str],
    limitations: list[str],
    timestamp: str,
    human_reviewer: str = "",
    notes: str = "",
) -> dict[str, Any]:
    if not _approved(verdict):
        raise ValueError("bundle approval records are pass-only; keep a failed review as findings")
    if not _is_zero_count(blocking_findings_count):
        raise ValueError("an approved bundle record requires an integer blocking_findings_count of 0")
    if not reviewer_agent.strip():
        raise ValueError("reviewer_agent or human reviewer identifier is required")
    if not author_agent.strip():
        raise ValueError("author_agent is required; independence is judged on this record")
    if author_agent.strip() == reviewer_agent.strip():
        raise ValueError("the reviewer must be a different agent than the bundle author")

    files: list[dict[str, str]] = []
    for rel_path in bundle_paths(variant):
        path = case_dir / rel_path
        if not path.is_file():
            raise ValueError(f"bundle file does not exist: {rel_path}")
        files.append({"path": rel_path, "sha256": sha256_file(path)})

    payload = {
        "schema_version": BUNDLE_APPROVAL_SCHEMA,
        "case_id": case_id,
        "variant": variant,
        "files": files,
        "author_agent": author_agent.strip(),
        "reviewer_agent": reviewer_agent.strip(),
        "reviewer_role": reviewer_role,
        "human_reviewer": human_reviewer,
        "verdict": verdict.strip().lower(),
        "blocking_findings_count": blocking_findings_count,
        "checks_observed": checks_observed,
        "limitations": limitations,
        "timestamp": timestamp,
        "notes": notes,
    }
    # Parity by construction, not by two lists staying in step: the builder cannot emit a record
    # its own reader would reject. The explicit checks above stay for their error messages.
    errors = validate_bundle_approval_payload(
        payload, case_dir, case_id=case_id, variant=variant, rel_path=approval_rel(variant)
    )
    if errors:
        raise ValueError("; ".join(errors))
    return payload


def validate_bundle_approval_payload(
    payload: Any, case_dir: Path, *, case_id: str, variant: str, rel_path: str
) -> list[str]:
    """Every rule the builder enforces, enforced again on read.

    A record is a file anyone can write by hand, so build-time rejection
    protects nothing: `verdict: pass` carrying one blocking finding would
    otherwise publish.
    """

    errors: list[str] = []
    if not isinstance(payload, dict):
        return [f"{rel_path}: approval record must be a JSON object"]

    if payload.get("schema_version") != BUNDLE_APPROVAL_SCHEMA:
        errors.append(f"{rel_path}: schema_version must be {BUNDLE_APPROVAL_SCHEMA}")
    if payload.get("case_id") != case_id:
        errors.append(f"{rel_path}: case_id must be {case_id}")
    if payload.get("variant") != variant:
        errors.append(f"{rel_path}: variant must be {variant}")

    verdict = payload.get("verdict")
    if not isinstance(verdict, str) or not _approved(verdict):
        errors.append(f"{rel_path}: verdict must be one of {sorted(APPROVED_VERDICTS)}")
    blocking = payload.get("blocking_findings_count")
    if not _is_zero_count(blocking):
        errors.append(
            f"{rel_path}: an approved record must carry an integer blocking_findings_count of 0, "
            f"not {blocking!r}"
        )

    errors.extend(_audit_field_errors(payload, rel_path))

    author = payload.get("author_agent")
    reviewer = payload.get("reviewer_agent")
    for label, value in (("author_agent", author), ("reviewer_agent", reviewer)):
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{rel_path}: {label} is required")
    if isinstance(author, str) and isinstance(reviewer, str) and author.strip() and author.strip() == reviewer.strip():
        errors.append(f"{rel_path}: the reviewer must be a different agent than the bundle author")

    errors.extend(_file_errors(payload, case_dir, variant, rel_path))
    return errors


def _audit_field_errors(payload: dict[str, Any], rel_path: str) -> list[str]:
    """Audit metadata is shape-checked even though it proves nothing on its own.

    It records what the reviewer said it did. A record missing `timestamp`, or
    carrying a number where `checks_observed` belongs, is malformed, and a
    malformed record must not pass a publication gate just because the fields it
    breaks are not themselves evidence.
    """

    errors: list[str] = []
    for field in ("reviewer_role", "timestamp"):
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{rel_path}: {field} must be a non-empty string")
    for field in ("checks_observed", "limitations"):
        value = payload.get(field)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            errors.append(f"{rel_path}: {field} must be a list of strings")
    for field in ("human_reviewer", "notes"):
        if not isinstance(payload.get(field, ""), str):
            errors.append(f"{rel_path}: {field} must be a string when present")
    return errors


def _file_errors(payload: dict[str, Any], case_dir: Path, variant: str, rel_path: str) -> list[str]:
    entries = payload.get("files")
    if not isinstance(entries, list):
        return [f"{rel_path}: files must be a list of path/sha256 objects"]

    recorded: dict[str, str] = {}
    errors: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            errors.append(f"{rel_path}: every files entry needs a string path")
            continue
        digest = entry.get("sha256")
        if not isinstance(digest, str) or not digest:
            errors.append(f"{rel_path}: files entry {entry['path']} has no sha256")
            continue
        if entry["path"] in recorded:
            # Last-wins would let a wrong hash be followed by the right one.
            errors.append(f"{rel_path}: {entry['path']} is bound more than once")
            continue
        recorded[entry["path"]] = digest

    for expected in bundle_paths(variant):
        if expected not in recorded:
            errors.append(f"{rel_path}: the approval does not bind {expected}")
            continue
        path = case_dir / expected
        if not path.is_file():
            errors.append(f"{rel_path}: bound file is missing from the case: {expected}")
            continue
        if sha256_file(path) != recorded[expected]:
            errors.append(
                f"{rel_path}: {expected} changed after approval; a material edit reopens draft state"
            )
    for extra in sorted(set(recorded) - set(bundle_paths(variant))):
        errors.append(f"{rel_path}: the approval binds a file outside the bundle: {extra}")
    return errors
