"""Deterministic context-budget accounting for round workflow artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

ESTIMATED_CHARS_PER_TOKEN = 4
DEFAULT_MAX_COMMON_BRIEFING_TOKENS = 4000
DEFAULT_MAX_ROLE_PACKET_TOKENS = 4000
DEFAULT_MAX_MANAGED_CONTEXT_TOKENS = 24000
DEFAULT_RAW_TRANSFER_RATIO = 0.75
MAX_RENDERED_PATHS = 20

SCHEMA_VERSION = "context-budget-audit-v1"


@dataclass(frozen=True)
class SurfaceSpec:
    name: str
    description: str
    patterns: tuple[str, ...]


MANAGED_SURFACES = (
    SurfaceSpec(
        "common_briefing",
        "Stable case/round briefing consumed by parent and role agents.",
        ("work/common_briefing.json",),
    ),
    SurfaceSpec(
        "role_packets",
        "Role-specific Markdown packets that should stay smaller than full evidence.",
        (
            "work/supervisor_packets/*.md",
            "work/supervisor_report_packets/*.md",
            "work/opponent_packets/*.md",
        ),
    ),
    SurfaceSpec(
        "evidence_capsules",
        "Structured extractor/subagent capsules used before opening raw sources.",
        ("work/context/evidence_capsules.json",),
    ),
    SurfaceSpec(
        "claim_review_basis",
        "Claim-level basis for synthesis/final review.",
        ("work/context/claim_review_basis.json",),
    ),
    SurfaceSpec(
        "structured_handoffs",
        "Other hash-bound handoffs and provenance artifacts used for routing.",
        (
            "work/current_evidence_snapshot.json",
            "work/reuse/reuse_index.json",
            "work/quantitative_claims.json",
            "work/review_manifest.json",
            "work/agent_coverage.json",
            "work/supervisor_report_trace.json",
            "work/opponent_report_trace.json",
        ),
    ),
)

RAW_SOURCE_SURFACE = SurfaceSpec(
    "raw_sources",
    "Round-local raw or extracted evidence that should not be copied wholesale into prompts.",
    (
        "inputs/**/*",
        "extracted/**/*",
        "work/code/**/*",
    ),
)


def estimate_tokens(size_bytes: int) -> int:
    return (max(size_bytes, 0) + ESTIMATED_CHARS_PER_TOKEN - 1) // ESTIMATED_CHARS_PER_TOKEN


def iter_surface_files(round_dir: Path, patterns: tuple[str, ...]) -> list[Path]:
    files: set[Path] = set()
    for pattern in patterns:
        for path in round_dir.glob(pattern):
            if path.is_file() and not path.is_symlink():
                files.add(path)
    return sorted(files, key=lambda path: path.relative_to(round_dir).as_posix())


def file_record(round_dir: Path, path: Path) -> dict[str, Any]:
    size = path.stat().st_size
    return {
        "path": path.relative_to(round_dir).as_posix(),
        "size_bytes": size,
        "estimated_tokens": estimate_tokens(size),
    }


def summarize_surface(round_dir: Path, spec: SurfaceSpec) -> dict[str, Any]:
    records = [file_record(round_dir, path) for path in iter_surface_files(round_dir, spec.patterns)]
    total_bytes = sum(int(record["size_bytes"]) for record in records)
    largest = sorted(records, key=lambda record: (-int(record["size_bytes"]), str(record["path"])))
    return {
        "name": spec.name,
        "description": spec.description,
        "patterns": list(spec.patterns),
        "file_count": len(records),
        "total_bytes": total_bytes,
        "estimated_tokens": estimate_tokens(total_bytes),
        "largest_files": largest[:MAX_RENDERED_PATHS],
        "omitted_file_count": max(0, len(largest) - MAX_RENDERED_PATHS),
    }


def warning(code: str, message: str, *, surface: str | None = None) -> dict[str, str]:
    item = {"severity": "warning", "code": code, "message": message}
    if surface is not None:
        item["surface"] = surface
    return item


def build_context_budget_report(
    case_id: str,
    round_id: str,
    round_dir: Path,
    *,
    max_common_briefing_tokens: int = DEFAULT_MAX_COMMON_BRIEFING_TOKENS,
    max_role_packet_tokens: int = DEFAULT_MAX_ROLE_PACKET_TOKENS,
    max_managed_context_tokens: int = DEFAULT_MAX_MANAGED_CONTEXT_TOKENS,
    raw_transfer_ratio: float = DEFAULT_RAW_TRANSFER_RATIO,
) -> dict[str, Any]:
    managed: list[dict[str, Any]] = [summarize_surface(round_dir, spec) for spec in MANAGED_SURFACES]
    raw = summarize_surface(round_dir, RAW_SOURCE_SURFACE)
    by_name: dict[str, dict[str, Any]] = {str(surface["name"]): surface for surface in managed}

    managed_tokens = sum(int(surface["estimated_tokens"]) for surface in managed)
    raw_tokens = int(raw["estimated_tokens"])
    structured_tokens = sum(
        int(by_name[name]["estimated_tokens"])
        for name in ("common_briefing", "evidence_capsules", "claim_review_basis", "structured_handoffs")
    )

    warnings: list[dict[str, str]] = []
    common = by_name["common_briefing"]
    if int(common["file_count"]) == 0:
        warnings.append(
            warning(
                "missing_common_briefing",
                "No common briefing found; parent and role agents may repeat broad case context.",
                surface="common_briefing",
            )
        )
    elif int(common["estimated_tokens"]) > max_common_briefing_tokens:
        warnings.append(
            warning(
                "large_common_briefing",
                f"Common briefing is estimated at {common['estimated_tokens']} tokens.",
                surface="common_briefing",
            )
        )

    role_packets = by_name["role_packets"]
    if int(role_packets["file_count"]) == 0:
        warnings.append(
            warning(
                "missing_role_packets",
                "No role packets found; role agents may need broader ad hoc context.",
                surface="role_packets",
            )
        )
    for record in role_packets["largest_files"]:
        if int(record["estimated_tokens"]) > max_role_packet_tokens:
            warnings.append(
                warning(
                    "large_role_packet",
                    f"{record['path']} is estimated at {record['estimated_tokens']} tokens.",
                    surface="role_packets",
                )
            )

    if managed_tokens > max_managed_context_tokens:
        warnings.append(
            warning(
                "large_managed_context",
                f"Managed context surfaces total {managed_tokens} estimated tokens.",
            )
        )
    if raw_tokens > 0 and managed_tokens / raw_tokens >= raw_transfer_ratio:
        warnings.append(
            warning(
                "managed_context_near_raw_source_size",
                "Managed context surfaces are approaching raw source size; check for duplicated evidence transfer.",
            )
        )
    if raw_tokens > 0 and structured_tokens == 0:
        warnings.append(
            warning(
                "missing_structured_handoffs",
                "Raw sources exist but no common briefing, capsules, claim basis, or structured handoffs were found.",
            )
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "case_id": case_id,
        "round_id": round_id,
        "advisory": True,
        "thresholds": {
            "max_common_briefing_tokens": max_common_briefing_tokens,
            "max_role_packet_tokens": max_role_packet_tokens,
            "max_managed_context_tokens": max_managed_context_tokens,
            "raw_transfer_ratio": raw_transfer_ratio,
        },
        "totals": {
            "managed_context_estimated_tokens": managed_tokens,
            "structured_handoff_estimated_tokens": structured_tokens,
            "raw_source_estimated_tokens": raw_tokens,
            "managed_to_raw_ratio": round(managed_tokens / raw_tokens, 3) if raw_tokens else None,
        },
        "surfaces": managed + [raw],
        "warnings": warnings,
    }


def render_context_budget_report(report: dict[str, Any]) -> str:
    totals_value = report.get("totals")
    totals: dict[str, Any] = totals_value if isinstance(totals_value, dict) else {}
    warnings_value = report.get("warnings")
    warnings: list[Any] = warnings_value if isinstance(warnings_value, list) else []
    lines = [
        "# Context Budget Audit",
        "",
        f"Case: `{report.get('case_id', '')}`",
        f"Round: `{report.get('round_id', '')}`",
        "Mode: advisory; warnings do not replace semantic review or readiness gates.",
        "",
        "## Totals",
        "",
        f"- managed context estimated tokens: {totals.get('managed_context_estimated_tokens', 0)}",
        f"- structured handoff estimated tokens: {totals.get('structured_handoff_estimated_tokens', 0)}",
        f"- raw source estimated tokens: {totals.get('raw_source_estimated_tokens', 0)}",
        f"- managed/raw ratio: {totals.get('managed_to_raw_ratio', 'n/a')}",
        f"- warnings: {len(warnings)}",
        "",
        "## Surfaces",
        "",
    ]
    surfaces_value = report.get("surfaces")
    surfaces: list[Any] = surfaces_value if isinstance(surfaces_value, list) else []
    for surface in surfaces:
        if not isinstance(surface, dict):
            continue
        lines.append(
            f"- `{surface.get('name')}`: files={surface.get('file_count', 0)}, "
            f"bytes={surface.get('total_bytes', 0)}, "
            f"estimated_tokens={surface.get('estimated_tokens', 0)}"
        )
        largest = surface.get("largest_files")
        if isinstance(largest, list):
            for record in largest[:3]:
                if isinstance(record, dict):
                    lines.append(f"  - `{record.get('path')}`: {record.get('estimated_tokens', 0)} estimated tokens")
    lines.extend(["", "## Warnings", ""])
    if not warnings:
        lines.append("- none")
    else:
        for item in warnings:
            if isinstance(item, dict):
                surface = f" `{item['surface']}`" if item.get("surface") else ""
                lines.append(f"- {item.get('code')}{surface}: {item.get('message')}")
    lines.append("")
    return "\n".join(lines)
