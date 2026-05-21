"""Source-ref rules for long-lived semantic evidence artifacts."""

from __future__ import annotations

from typing import Any

GENERATED_ROLE_PACKET_PREFIXES = (
    "work/opponent_packets/",
    "work/supervisor_packets/",
    "work/supervisor_report_packets/",
)
AGGREGATE_SNAPSHOT_REFS = frozenset({"work/current_evidence_snapshot.json"})


def generated_role_packet_ref(value: str) -> bool:
    return value.startswith(GENERATED_ROLE_PACKET_PREFIXES) and value.endswith(".md")


def aggregate_snapshot_ref(value: str) -> bool:
    return value in AGGREGATE_SNAPSHOT_REFS


def forbidden_long_lived_semantic_source_reason(value: str) -> str | None:
    if generated_role_packet_ref(value):
        return "generated role packets are handoff prompts, not primary evidence"
    if aggregate_snapshot_ref(value):
        return "aggregate evidence snapshots can include the role artifact and create hash cycles"
    return None


def validate_long_lived_semantic_source_refs(
    rel_path: str,
    label: str,
    refs: Any,
    errors: list[str],
) -> None:
    if not isinstance(refs, list):
        return
    for value in refs:
        if not isinstance(value, str):
            continue
        reason = forbidden_long_lived_semantic_source_reason(value)
        if reason is None:
            continue
        errors.append(
            f"{rel_path}: {label} must cite primary case artifacts, stable notes, "
            f"imported reports, or reviewed outputs; {reason}: {value}"
        )
