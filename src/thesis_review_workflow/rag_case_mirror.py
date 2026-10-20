"""Mirror the case Markdown that local RAG may index into `cases/_rag/`.

The shared local-rag bridge has no exclude configuration: a sync walks every
supported file (`.md`, `.txt`, `.pdf`, `.docx`) under each configured root. With
the whole `cases/` directory as a root it indexed submitted code, LaTeX sources,
raw GitHub intake, extracted thesis text and thesis PDFs, which
`docs/local-rag-usage.md` keeps out of the index. Those chunks crowded the
operator's own notes out of the results.

So the bridge indexes `cases/_rag/` instead, and this module keeps that
directory an exact copy of an allowlist of case Markdown: a file reaches the
index only when a rule below names it, and a missing rule leaves a file out
rather than letting it in. Mirror path `cases/_rag/<rel>` is the original
`cases/<rel>`; a RAG hit is a pointer to that original.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

MIRROR_DIR = "_rag"
LITERATURE_DIR = "_literature"

# Top-level `work/*.md` files that are mechanical inventories, not review
# evidence; they mostly add file-list noise to semantic search.
WORK_INVENTORIES = {
    "code_workspace.md",
    "source_workspace.md",
    "submission_bundle_inventory.md",
}
# Reviewed or reviewer-written subdirectories of `work/` whose Markdown is
# operator evidence. Packet prompts (`work/*_packets/<role>.md`) are not: only
# the role-owned `*_findings.md` sidecars are mirrored from those.
WORK_EVIDENCE_DIRS = {"reviews", "literature", "submitted_reports"}
WORK_EVIDENCE_TREES = {"calibration"}
GITHUB_CONTRIBUTION_MAP = ("github-intake", "contribution-map.md")


@dataclass(frozen=True)
class MirrorResult:
    copied: int
    unchanged: int
    removed: int


def _unit_markdown(unit: Path) -> list[Path]:
    """Allowed Markdown of one case unit: a round directory, or a case without rounds."""

    selected: list[Path] = []
    notes = unit / "notes"
    if notes.is_dir():
        selected.extend(notes.rglob("*.md"))
        selected.extend(notes.rglob("*.txt"))
    outputs = unit / "outputs"
    if outputs.is_dir():
        selected.extend(outputs.rglob("*.md"))
    # `inputs/` is not mirrored: next to prior feedback it holds what students
    # submitted (working documents, package READMEs), and nothing structural tells
    # the two apart. Prior feedback reaches the index from the earlier round's
    # `outputs/`.
    work = unit / "work"
    if work.is_dir():
        selected.extend(path for path in work.glob("*.md") if path.name not in WORK_INVENTORIES)
        selected.extend(work.glob("*_packets/*_findings.md"))
        for name in WORK_EVIDENCE_DIRS:
            selected.extend((work / name).glob("*.md"))
        for name in WORK_EVIDENCE_TREES:
            selected.extend((work / name).rglob("*.md"))
        contribution_map = work.joinpath(*GITHUB_CONTRIBUTION_MAP)
        if contribution_map.is_file():
            selected.append(contribution_map)
    return selected


def _no_symlink_below(root: Path, path: Path) -> bool:
    """True when no component between `root` and `path`, inclusive, is a symlink."""

    current = path
    while current != root:
        if current.is_symlink():
            return False
        current = current.parent
    return True


def select_case_markdown(cases_root: Path) -> list[str]:
    """Return the allowlisted files, as POSIX paths relative to `cases_root`."""

    selected: list[Path] = []
    for case in sorted(cases_root.iterdir()):
        if not case.is_dir() or case.is_symlink():
            continue
        if case.name == LITERATURE_DIR:
            selected.extend(case.glob("*/notes.md"))
            continue
        if case.name.startswith("_"):
            continue  # the mirror itself and any other non-case directory
        case_md = case / "case.md"
        if case_md.is_file():
            selected.append(case_md)
        selected.extend(_unit_markdown(case))
        rounds = case / "rounds"
        if rounds.is_dir():
            for round_dir in sorted(rounds.iterdir()):
                if round_dir.is_dir() and not round_dir.is_symlink():
                    selected.extend(_unit_markdown(round_dir))
    return sorted(
        {
            path.relative_to(cases_root).as_posix()
            for path in selected
            if path.is_file() and _no_symlink_below(cases_root, path)
        }
    )


def refresh_mirror(cases_root: Path) -> MirrorResult:
    """Make `cases/_rag/` an exact copy of the allowlist; remove everything else in it."""

    mirror = cases_root / MIRROR_DIR
    if mirror.is_symlink():
        raise ValueError(f"{mirror} is a symlink; refusing to write through it")
    wanted = select_case_markdown(cases_root)
    # The mirror is a configured index root: it must exist even when empty, or the
    # whole sync fails on a missing base directory.
    mirror.mkdir(exist_ok=True)
    copied = unchanged = removed = 0
    for rel in wanted:
        data = (cases_root / rel).read_bytes()
        target = mirror / rel
        # Checked before mkdir, which would otherwise create directories through a
        # symlink planted in the mirror.
        if not _no_symlink_below(mirror, target) or target.is_dir():
            raise ValueError(f"{target} is not a regular file in the mirror; refusing to write it")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_file() and target.read_bytes() == data:
            unchanged += 1
            continue
        target.write_bytes(data)
        copied += 1
    keep = set(wanted)
    if mirror.is_dir():
        for path in sorted(mirror.rglob("*"), reverse=True):
            rel = path.relative_to(mirror).as_posix()
            if path.is_symlink() or (path.is_file() and rel not in keep):
                path.unlink()
                removed += 1
            elif path.is_dir() and not any(path.iterdir()):
                path.rmdir()
    return MirrorResult(copied=copied, unchanged=unchanged, removed=removed)
