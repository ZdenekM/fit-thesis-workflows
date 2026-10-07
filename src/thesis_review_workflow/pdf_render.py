"""Render one student-facing Markdown artifact to an A4 PDF with Quarto and Typst.

The Markdown stays the single source of truth; the PDF is a derived presentation
artifact. Each kind of document is a resource directory under `render/<kind>/` holding its
Quarto defaults and layout filter; `render/shared/` holds what every kind uses (the Typst
template partial, the common filters, the vendored fonts). Both are copied next to a copy
of the Markdown in a temporary directory for each render, so the source file is never
touched.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any

MIN_QUARTO_VERSION = (1, 10, 18)
"""The version the template and filters were tested with (bundles Typst 0.15.1)."""

RENDER_TIMEOUT_SECONDS = 300
SHARED_RESOURCES = "shared"
RENDER_VALUES_NAME = "render-values.json"
"""Read by each kind's layout filter, which lets these values override front matter."""
DRAFT_STAMP = {"cs": "NÁVRH", "en": "DRAFT"}
"""Stamped across every page of a preview rendered without an approval."""


class RenderError(Exception):
    """A render failure with an operator-readable message."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def find_quarto(markdown_rel: str) -> Path:
    """The Quarto binary; the error names the Markdown the operator can send instead."""
    found = shutil.which("quarto")
    if found is None:
        raise RenderError(
            "quarto is not installed or not on PATH; install Quarto "
            f"{format_version(MIN_QUARTO_VERSION)} or newer, or send {markdown_rel} as Markdown"
        )
    return Path(found)


def format_version(version: tuple[int, ...]) -> str:
    return ".".join(str(part) for part in version)


def parse_version(output: str) -> tuple[int, int, int] | None:
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", output)
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def quarto_version(quarto: Path) -> str:
    """The `quarto --version` string, refusing a version older than the tested one."""
    try:
        result = subprocess.run(
            [str(quarto), "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RenderError(f"cannot run {quarto} --version: {exc}") from exc
    text = result.stdout.strip()
    version = parse_version(text)
    if result.returncode != 0 or version is None:
        raise RenderError(f"cannot read the Quarto version from {quarto}: {text or result.stderr.strip()}")
    if version < MIN_QUARTO_VERSION:
        raise RenderError(
            f"Quarto {format_version(version)} is older than the tested {format_version(MIN_QUARTO_VERSION)}; "
            "update Quarto"
        )
    return format_version(version)


def resource_root(kind: str) -> Traversable:
    return resources.files("thesis_review_workflow").joinpath("render", kind)


def copy_resources(source: Traversable, destination: Path) -> None:
    """Copy a resource tree through `importlib.resources`, so packaged PEX files work too.

    Merges into an existing tree, so a kind's `filters/` joins the shared one.
    """
    destination.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        target = destination / item.name
        if item.is_dir():
            copy_resources(item, target)
        else:
            target.write_bytes(item.read_bytes())


def stage_resources(kind: str, destination: Path) -> None:
    """The shared resources, then the kind's own, as one Quarto project directory."""
    copy_resources(resource_root(SHARED_RESOURCES), destination)
    copy_resources(resource_root(kind), destination)


def render_pdf(
    kind: str, source_name: str, source: bytes, output_pdf: Path, values: dict[str, Any], quarto: Path
) -> None:
    """Render the Markdown `source` bytes to `output_pdf` with the `kind` layout, in a scratch directory."""
    # Quarto or Typst children may still hold files after a timeout, notably on Windows.
    with tempfile.TemporaryDirectory(prefix=f"render-{kind}-", ignore_cleanup_errors=True) as scratch:
        work = Path(scratch)
        stage_resources(kind, work)
        (work / source_name).write_bytes(source)
        text = json.dumps(values, ensure_ascii=False, indent=2) + "\n"
        (work / RENDER_VALUES_NAME).write_text(text, encoding="utf-8")
        try:
            result = subprocess.run(
                [str(quarto), "render", source_name, "--to", "typst"],
                cwd=work,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=RENDER_TIMEOUT_SECONDS,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RenderError(f"quarto render failed to run: {exc}") from exc
        rendered = work / Path(source_name).with_suffix(".pdf")
        if result.returncode != 0 or not rendered.is_file():
            tail = "\n".join((result.stdout + result.stderr).strip().splitlines()[-15:])
            raise RenderError(f"quarto render exited with {result.returncode}:\n{tail}")
        install_pdf(rendered, output_pdf)


def install_pdf(rendered: Path, output_pdf: Path) -> None:
    """Replace `output_pdf` atomically; a PDF open in a viewer on Windows cannot be replaced."""
    partial = output_pdf.with_name(output_pdf.name + ".partial")
    try:
        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(rendered, partial)
        partial.replace(output_pdf)
    except OSError as exc:
        partial.unlink(missing_ok=True)
        raise RenderError(f"cannot write {output_pdf.name} (close it if it is open in a viewer): {exc}") from exc


def remove_stale_pdf(output_dir: Path, pdf_rel: str, reason: str) -> bool:
    """Remove `pdf_rel` under `output_dir`; False when it exists but cannot be removed."""
    stale = output_dir / pdf_rel
    if not stale.is_file():
        return True
    try:
        stale.unlink()
    except OSError as exc:
        print(f"ERROR: cannot remove the stale {pdf_rel} (close it if it is open in a viewer): {exc}")
        return False
    if reason:
        print(f"Removed the stale {pdf_rel}: {reason}.")
    return True
