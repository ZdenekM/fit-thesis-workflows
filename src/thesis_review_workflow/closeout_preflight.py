"""Preflight helpers shared by closeout commands."""

from __future__ import annotations

import shutil
from pathlib import Path

from thesis_review_workflow.commands import Step

DEFAULT_MIN_FREE_BYTES = 512 * 1024 * 1024


def format_bytes(value: int) -> str:
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    amount = float(max(value, 0))
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.1f} {unit}" if unit != "B" else f"{int(amount)} B"
        amount /= 1024
    return f"{int(value)} B"


def display_target(path: Path) -> str:
    parts = path.parts
    if "cases" in parts:
        return Path(*parts[parts.index("cases") :]).as_posix()
    if path.name:
        return path.name
    return path.anchor or "."


def filesystem_label(path: Path) -> str:
    if path.drive:
        return path.drive
    return path.anchor or "."


def free_space_preflight_step(round_dir: Path, *, min_free_bytes: int = DEFAULT_MIN_FREE_BYTES) -> Step:
    target = round_dir if round_dir.exists() else round_dir.parent
    target_display = display_target(target)
    filesystem = filesystem_label(target)
    usage = shutil.disk_usage(target)
    if usage.free < min_free_bytes:
        return Step(
            label="Free-space preflight",
            command=None,
            returncode=1,
            output=(
                f"Filesystem for `{target_display}` (root `{filesystem}`) has {format_bytes(usage.free)} free; "
                f"{format_bytes(min_free_bytes)} is required before write-heavy closeout phases.\n"
                "Safe regenerable cleanup candidates, if present: `.pants.d/`, `dist/workflow-tools/pex/`, "
                "and tool caches under the operator's cache directory. No cleanup was performed automatically."
            ),
        )
    return Step(
        label="Free-space preflight",
        command=None,
        returncode=0,
        output=(
            f"Filesystem for `{target_display}` (root `{filesystem}`) has {format_bytes(usage.free)} free; "
            f"required minimum is {format_bytes(min_free_bytes)}."
        ),
    )
