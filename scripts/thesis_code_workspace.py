#!/usr/bin/env python3
"""Prepare an ignored, inspectable code workspace for a thesis round."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import unicodedata
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import BinaryIO


ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
MAX_WALK_FILES = 5000
MAX_EXTRACTED_FILES = 20000
MAX_EXTRACTED_FILE_BYTES = 250 * 1024 * 1024
MAX_EXTRACTED_BYTES = 1024 * 1024 * 1024
MAX_LIST = 20
MAX_ARCHIVE_BYTES = 500 * 1024 * 1024
REPORT_REL = Path("work/code_workspace.md")
SERENA_ROOTS_REL = Path("work/serena_roots.json")
WORKSPACE_MANIFEST_NAME = ".prepare-code-workspace-manifest.json"

SAFE_SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".cache",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "target",
    ".venv",
    "venv",
}
DEPENDENCY_NAMES = {
    "requirements.txt",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "pom.xml",
    "build.gradle",
    "settings.gradle",
    "Cargo.toml",
    "Cargo.lock",
    "go.mod",
    "go.sum",
    "CMakeLists.txt",
    "Makefile",
    "Dockerfile",
    "docker-compose.yml",
    "compose.yml",
}
CODE_DEPENDENCY_NAMES = DEPENDENCY_NAMES - {"Makefile", "CMakeLists.txt"}
CODE_SUFFIX_LANGUAGES = {
    ".py": "python",
    ".ipynb": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".kt": "kotlin",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".c": "cpp",
    ".h": "cpp",
    ".hpp": "cpp",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".r": "r",
    ".R": "r",
    ".jl": "julia",
    ".m": "matlab",
}
ARCHIVE_SUFFIXES = {
    ".zip",
    ".tar",
    ".tgz",
    ".tbz",
    ".tbz2",
    ".txz",
    ".tar.gz",
    ".tar.bz2",
    ".tar.xz",
}
UNSUPPORTED_ARCHIVE_SUFFIXES = {
    ".7z",
    ".rar",
    ".gz",
    ".bz2",
    ".xz",
    ".zst",
}
TEXT_ARCHIVE_HINTS = {
    "thesis",
    "latex",
    "overleaf",
    "zadani",
    "assignment",
    "prace",
    "bakalar",
    "diplom",
    "report",
}
CODE_ARCHIVE_HINTS = {
    "code",
    "src",
    "source",
    "repo",
    "project",
    "app",
    "software",
    "implementation",
    "submission",
}


@dataclass
class DirectoryInventory:
    path: Path
    files_seen: int = 0
    truncated: bool = False
    readmes: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)
    ci: list[str] = field(default_factory=list)
    large_files: list[str] = field(default_factory=list)
    code_files: list[str] = field(default_factory=list)
    languages: set[str] = field(default_factory=set)

    @property
    def code_like(self) -> bool:
        return bool(
            self.code_files
            or self.tests
            or any(Path(item).name in CODE_DEPENDENCY_NAMES for item in self.dependencies)
        )


@dataclass(frozen=True)
class ArchiveProbe:
    path: Path
    size: int
    entries_seen: int
    truncated: bool
    code_like: bool
    possible_code: bool
    note: str


@dataclass(frozen=True)
class PreparedSource:
    source: Path
    target: Path
    action: str
    note: str
    source_fingerprint: str


@dataclass
class CopyBudget:
    total_bytes: int = 0

    def reserve(self, label: str, size: int) -> str | None:
        if size > MAX_EXTRACTED_FILE_BYTES:
            return f"{label} ({format_bytes(size)} exceeds per-file limit {format_bytes(MAX_EXTRACTED_FILE_BYTES)})"
        if self.total_bytes + size > MAX_EXTRACTED_BYTES:
            return f"{label} (workspace copy limit {format_bytes(MAX_EXTRACTED_BYTES)} would be exceeded)"
        self.total_bytes += size
        return None


def repo_root() -> Path:
    output = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True)
    return Path(output.strip())


def validate_id(label: str, value: str) -> None:
    if not ID_RE.fullmatch(value) or set(value) == {"."}:
        print(
            f"Invalid {label}. Use only letters, numbers, dot, underscore, and dash; dot-only ids are not allowed.",
            file=sys.stderr,
        )
        raise SystemExit(2)


def resolve_round(case_dir: Path, round_id: str | None) -> str:
    if round_id:
        validate_id("ROUND_ID", round_id)
        return round_id
    current_round = case_dir / "current-round.txt"
    if not current_round.is_file():
        print(f"Missing current round: {case_dir}/current-round.txt", file=sys.stderr)
        raise SystemExit(1)
    resolved = current_round.read_text(encoding="utf-8").strip()
    validate_id("ROUND_ID", resolved)
    return resolved


def rel_round(round_dir: Path, path: Path) -> str:
    return path.relative_to(round_dir).as_posix()


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def format_bytes(value: int) -> str:
    units = ("B", "KiB", "MiB", "GiB")
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.1f} {unit}" if unit != "B" else f"{value} B"
        amount /= 1024
    return f"{value} B"


def folded(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char)).lower()


def safe_name(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip(".-")
    return safe or "code"


def archive_suffix(path: Path) -> str:
    suffixes = [suffix.lower() for suffix in path.suffixes]
    if len(suffixes) >= 2 and suffixes[-2:] in (
        [".tar", ".gz"],
        [".tar", ".bz2"],
        [".tar", ".xz"],
    ):
        return "".join(suffixes[-2:])
    return suffixes[-1] if suffixes else ""


def is_archive(path: Path) -> bool:
    return path.is_file() and archive_suffix(path) in ARCHIVE_SUFFIXES


def is_unsupported_archive(path: Path) -> bool:
    return path.is_file() and archive_suffix(path) in UNSUPPORTED_ARCHIVE_SUFFIXES


def archive_name_possible_code(path: Path) -> bool:
    name = folded(path.name)
    if any(token in name for token in TEXT_ARCHIVE_HINTS):
        return False
    return True


def archive_entry_code_like(name: str) -> bool:
    pure_name = PurePosixPath(name).name
    lower = name.lower()
    return (
        pure_name in CODE_DEPENDENCY_NAMES
        or PurePosixPath(pure_name).suffix in CODE_SUFFIX_LANGUAGES
        or "/test/" in lower
        or "/tests/" in lower
        or lower.startswith("test/")
        or lower.startswith("tests/")
    )


def iter_archive_names(path: Path) -> tuple[list[str], bool, str]:
    suffix = archive_suffix(path)
    names: list[str] = []
    truncated = False
    note = "metadata listed"
    try:
        if suffix == ".zip":
            with zipfile.ZipFile(path) as handle:
                for index, item in enumerate(handle.infolist()):
                    if index >= MAX_WALK_FILES:
                        truncated = True
                        break
                    names.append(item.filename)
        elif suffix in {".tar", ".tar.gz", ".tar.bz2", ".tar.xz", ".tgz", ".tbz", ".tbz2", ".txz"}:
            with tarfile.open(path, mode="r:*") as handle:
                for index, member in enumerate(handle):
                    if index >= MAX_WALK_FILES:
                        truncated = True
                        break
                    names.append(member.name)
        else:
            note = "unsupported archive format"
    except (OSError, tarfile.TarError, zipfile.BadZipFile) as exc:
        note = f"metadata unreadable: {exc}"
    return names, truncated, note


def probe_archive(path: Path) -> ArchiveProbe:
    size = path.stat().st_size
    if size > MAX_ARCHIVE_BYTES:
        return ArchiveProbe(
            path=path,
            size=size,
            entries_seen=0,
            truncated=True,
            code_like=False,
            possible_code=archive_name_possible_code(path),
            note="large archive; not unpacked automatically",
        )
    names, truncated, note = iter_archive_names(path)
    code_like = any(archive_entry_code_like(name) for name in names)
    name_hint = any(token in folded(path.name) for token in CODE_ARCHIVE_HINTS)
    possible_code = code_like or (name_hint and archive_name_possible_code(path))
    return ArchiveProbe(
        path=path,
        size=size,
        entries_seen=len(names),
        truncated=truncated,
        code_like=code_like,
        possible_code=possible_code,
        note=note + ("; truncated" if truncated else ""),
    )


def safe_member_path(target: Path, member_name: str) -> Path | None:
    relative = PurePosixPath(member_name)
    if relative.is_absolute() or ".." in relative.parts:
        return None
    destination = (target / Path(*relative.parts)).resolve()
    target_resolved = target.resolve()
    if destination != target_resolved and target_resolved not in destination.parents:
        return None
    return destination


def copy_stream_limited(source: BinaryIO, destination: Path, expected_size: int, budget: CopyBudget, label: str) -> int:
    skipped = budget.reserve(label, expected_size)
    if skipped is not None:
        raise ValueError(skipped)
    destination.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with destination.open("wb") as handle:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            written += len(chunk)
            if written > expected_size:
                destination.unlink(missing_ok=True)
                raise ValueError(f"{label} exceeded declared size while copying")
            handle.write(chunk)
    return written


def extract_zip(path: Path, target: Path) -> tuple[int, list[str]]:
    extracted = 0
    skipped: list[str] = []
    budget = CopyBudget()
    with zipfile.ZipFile(path) as handle:
        for item in handle.infolist():
            if extracted >= MAX_EXTRACTED_FILES:
                skipped.append(f"truncated after {MAX_EXTRACTED_FILES} files")
                break
            destination = safe_member_path(target, item.filename)
            if destination is None:
                skipped.append(item.filename)
                continue
            if item.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            with handle.open(item) as source:
                try:
                    copy_stream_limited(source, destination, item.file_size, budget, item.filename)
                except ValueError as exc:
                    skipped.append(str(exc))
                    continue
            extracted += 1
    return extracted, skipped


def extract_tar(path: Path, target: Path) -> tuple[int, list[str]]:
    extracted = 0
    skipped: list[str] = []
    budget = CopyBudget()
    with tarfile.open(path, mode="r:*") as handle:
        for member in handle:
            if extracted >= MAX_EXTRACTED_FILES:
                skipped.append(f"truncated after {MAX_EXTRACTED_FILES} files")
                break
            destination = safe_member_path(target, member.name)
            if destination is None or member.issym() or member.islnk():
                skipped.append(member.name)
                continue
            if member.isdir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                skipped.append(member.name)
                continue
            source = handle.extractfile(member)
            if source is None:
                skipped.append(member.name)
                continue
            with source:
                try:
                    copy_stream_limited(source, destination, member.size, budget, member.name)
                except ValueError as exc:
                    skipped.append(str(exc))
                    continue
            extracted += 1
    return extracted, skipped


def extract_archive(path: Path, target: Path) -> tuple[int, list[str]]:
    suffix = archive_suffix(path)
    if suffix == ".zip":
        return extract_zip(path, target)
    if suffix in {".tar", ".tar.gz", ".tar.bz2", ".tar.xz", ".tgz", ".tbz", ".tbz2", ".txz"}:
        return extract_tar(path, target)
    return 0, [f"unsupported archive format: {suffix}"]


def collapse_duplicate_top_level(target: Path) -> bool:
    children = list(target.iterdir()) if target.is_dir() else []
    if len(children) != 1:
        return False
    child = children[0]
    if not child.is_dir() or child.name != target.name:
        return False
    temporary = target.with_name(f".{target.name}.collapse")
    if temporary.exists():
        shutil.rmtree(temporary)
    child.rename(temporary)
    shutil.rmtree(target)
    temporary.rename(target)
    return True


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint_source(path: Path) -> str:
    if path.is_file():
        return f"sha256:{sha256_file(path)};size:{path.stat().st_size}"
    digest = hashlib.sha256()
    files_seen = 0
    total_bytes = 0
    for dirpath, dirnames, filenames in os.walk(path):
        dirnames[:] = sorted(
            name
            for name in dirnames
            if name not in SAFE_SKIP_DIRS and not (Path(dirpath) / name).is_symlink()
        )
        for filename in sorted(filenames):
            file_path = Path(dirpath) / filename
            if file_path.is_symlink() or not file_path.is_file():
                continue
            stat = file_path.stat()
            rel = file_path.relative_to(path).as_posix()
            digest.update(rel.encode("utf-8", errors="surrogateescape"))
            digest.update(str(stat.st_size).encode("ascii"))
            digest.update(str(stat.st_mtime_ns).encode("ascii"))
            files_seen += 1
            total_bytes += stat.st_size
            if files_seen >= MAX_WALK_FILES:
                digest.update(b"truncated")
                return f"tree-sha256:{digest.hexdigest()};files:{files_seen};bytes:{total_bytes};truncated"
    return f"tree-sha256:{digest.hexdigest()};files:{files_seen};bytes:{total_bytes}"


def load_workspace_manifest(workspace: Path) -> dict[str, object]:
    path = workspace / WORKSPACE_MANIFEST_NAME
    if not path.is_file():
        return {"schema": "prepare-code-workspace-manifest-v1", "sources": {}}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"schema": "prepare-code-workspace-manifest-v1", "sources": {}}
    if not isinstance(loaded, dict) or not isinstance(loaded.get("sources"), dict):
        return {"schema": "prepare-code-workspace-manifest-v1", "sources": {}}
    return loaded


def write_workspace_manifest(workspace: Path, manifest: dict[str, object]) -> None:
    manifest["schema"] = "prepare-code-workspace-manifest-v1"
    manifest["updated_at"] = now_utc()
    (workspace / WORKSPACE_MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def manifest_sources(manifest: dict[str, object]) -> dict[str, dict[str, object]]:
    sources = manifest.setdefault("sources", {})
    if not isinstance(sources, dict):
        manifest["sources"] = {}
        return {}
    return sources  # type: ignore[return-value]


def current_input_source_keys(inputs: Path) -> set[str]:
    if not inputs.is_dir():
        return set()
    keys: set[str] = set()
    for source in sorted(inputs.iterdir()):
        if source.is_symlink():
            continue
        if is_archive(source) or is_unsupported_archive(source):
            keys.add(source.relative_to(inputs.parent).as_posix())
        elif source.is_dir() and source.name not in SAFE_SKIP_DIRS:
            inventory = inventory_directory(source)
            if inventory.code_like:
                keys.add(source.relative_to(inputs.parent).as_posix())
    return keys


def prune_stale_manifest_sources(
    round_dir: Path,
    workspace: Path,
    sources: dict[str, dict[str, object]],
    current_keys: set[str],
) -> list[str]:
    skipped: list[str] = []
    for source_key, record in list(sources.items()):
        if source_key in current_keys:
            continue
        target_rel = record.get("target")
        if not isinstance(target_rel, str):
            sources.pop(source_key, None)
            continue
        target = round_dir / target_rel
        try:
            target.relative_to(workspace)
        except ValueError:
            skipped.append(f"`{source_key}`: stale manifest target outside work/code was ignored")
            sources.pop(source_key, None)
            continue
        if target.exists():
            shutil.rmtree(target)
            skipped.append(f"`{source_key}`: removed stale prepared workspace `{rel_round(round_dir, target)}`")
        sources.pop(source_key, None)
    return skipped


def inventory_directory(path: Path) -> DirectoryInventory:
    inventory = DirectoryInventory(path=path)
    for dirpath, dirnames, filenames in os.walk(path):
        dirnames[:] = [name for name in dirnames if name not in SAFE_SKIP_DIRS]
        for filename in filenames:
            file_path = Path(dirpath) / filename
            inventory.files_seen += 1
            rel = file_path.relative_to(path).as_posix()
            lower = rel.lower()
            suffix = file_path.suffix
            if filename.lower().startswith("readme") and len(inventory.readmes) < MAX_LIST:
                inventory.readmes.append(rel)
            if filename in DEPENDENCY_NAMES and len(inventory.dependencies) < MAX_LIST:
                inventory.dependencies.append(rel)
            if lower.startswith(".github/workflows/") and len(inventory.ci) < MAX_LIST:
                inventory.ci.append(rel)
            if (
                re.search(r"(^|/)(test|tests|spec|specs)(/|$)", lower)
                or re.search(r"(test|spec)\.", filename.lower())
            ) and len(inventory.tests) < MAX_LIST:
                inventory.tests.append(rel)
            if suffix in CODE_SUFFIX_LANGUAGES:
                inventory.languages.add(CODE_SUFFIX_LANGUAGES[suffix])
                if len(inventory.code_files) < MAX_LIST:
                    inventory.code_files.append(rel)
            try:
                if file_path.stat().st_size >= 10 * 1024 * 1024 and len(inventory.large_files) < MAX_LIST:
                    inventory.large_files.append(rel)
            except OSError:
                pass
            if inventory.files_seen >= MAX_WALK_FILES:
                inventory.truncated = True
                return inventory
    return inventory


def likely_project_roots(workspace: Path) -> list[DirectoryInventory]:
    candidates: dict[Path, int] = {}
    for root, dirnames, filenames in os.walk(workspace):
        dirnames[:] = [name for name in dirnames if name not in SAFE_SKIP_DIRS]
        path = Path(root)
        score = 0
        if any(name in DEPENDENCY_NAMES for name in filenames):
            score += 4
        if any(name.lower().startswith("readme") for name in filenames):
            score += 2
        if any(Path(name).suffix in CODE_SUFFIX_LANGUAGES for name in filenames):
            score += 1
        if score:
            candidates[path] = score
    if not candidates and workspace.is_dir():
        for child in workspace.iterdir():
            if child.is_dir() and child.name not in SAFE_SKIP_DIRS:
                candidates[child] = 1
    ordered = sorted(candidates, key=lambda item: (-candidates[item], len(item.parts), item.as_posix()))
    inventories: list[DirectoryInventory] = []
    for path in ordered[:MAX_LIST]:
        if any(selected.path == path or selected.path in path.parents for selected in inventories):
            continue
        inventory = inventory_directory(path)
        if inventory.code_like:
            inventories.append(inventory)
    return inventories


def direct_input_code_dirs(inputs: Path) -> list[Path]:
    if not inputs.is_dir():
        return []
    dirs: list[Path] = []
    for path in sorted(inputs.iterdir()):
        if path.is_symlink() or not path.is_dir() or path.name in SAFE_SKIP_DIRS:
            continue
        inventory = inventory_directory(path)
        if inventory.code_like:
            dirs.append(path)
    return dirs


def target_for_source(workspace: Path, source: Path) -> Path:
    base = safe_name(source.stem if source.is_file() else source.name)
    return workspace / base


def safe_copy_input_dir(source: Path, target: Path) -> tuple[int, list[str]]:
    copied = 0
    skipped: list[str] = []
    budget = CopyBudget()
    source_root = source.resolve()
    for dirpath, dirnames, filenames in os.walk(source):
        current_dir = Path(dirpath)
        kept_dirs: list[str] = []
        for dirname in dirnames:
            child = current_dir / dirname
            if dirname in SAFE_SKIP_DIRS:
                continue
            if child.is_symlink():
                skipped.append(child.relative_to(source).as_posix())
                continue
            kept_dirs.append(dirname)
        dirnames[:] = kept_dirs

        rel_dir = current_dir.relative_to(source)
        (target / rel_dir).mkdir(parents=True, exist_ok=True)
        for filename in filenames:
            source_file = current_dir / filename
            rel_file = source_file.relative_to(source)
            label = rel_file.as_posix()
            if source_file.is_symlink() or not source_file.is_file():
                skipped.append(label)
                continue
            try:
                resolved = source_file.resolve(strict=True)
            except OSError:
                skipped.append(label)
                continue
            if resolved != source_root and source_root not in resolved.parents:
                skipped.append(label)
                continue
            stat = source_file.stat()
            destination = target / rel_file
            try:
                with source_file.open("rb") as handle:
                    copy_stream_limited(handle, destination, stat.st_size, budget, label)
            except (OSError, ValueError) as exc:
                skipped.append(f"{label} ({exc})")
                continue
            copied += 1
            if copied >= MAX_EXTRACTED_FILES:
                skipped.append(f"truncated after {MAX_EXTRACTED_FILES} files")
                return copied, skipped
    return copied, skipped


def suggest_commands(inventory: DirectoryInventory) -> list[str]:
    manifests = {Path(item).name for item in inventory.dependencies}
    languages = inventory.languages
    commands: list[str] = []
    if "python" in languages:
        commands.append("python -m compileall .")
        if inventory.tests:
            commands.append("python -m pytest -q")
    if "package.json" in manifests:
        commands.append("npm test")
        commands.append("npm run build")
    if "go.mod" in manifests:
        commands.append("go test ./...")
    if "Cargo.toml" in manifests:
        commands.append("cargo test")
    if "pom.xml" in manifests:
        commands.append("mvn test")
    if "build.gradle" in manifests or "settings.gradle" in manifests:
        commands.append("./gradlew test")
    if "Makefile" in manifests and not commands:
        commands.append("make test")
    return commands[:MAX_LIST]


def serena_suitable(inventory: DirectoryInventory) -> bool:
    return bool(inventory.languages & {"python", "typescript", "javascript", "java", "kotlin", "cpp", "csharp", "go", "rust"})


def format_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- none"]


def write_report(
    round_dir: Path,
    prepared: list[PreparedSource],
    skipped: list[str],
    roots: list[DirectoryInventory],
) -> None:
    report = round_dir / REPORT_REL
    serena_json = round_dir / SERENA_ROOTS_REL
    report.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Code Workspace Preparation",
        "",
        f"- Generated at: {now_utc()}",
        f"- Workspace: `work/code/`",
        "- Scope: ignored case-local workspace; original submitted inputs remain under `inputs/`.",
        "",
        "## Prepared Sources",
    ]
    if prepared:
        for item in prepared:
            lines.append(f"- `{rel_round(round_dir, item.source)}` -> `{rel_round(round_dir, item.target)}` ({item.action}; {item.note})")
            lines.append(f"  - Source fingerprint: `{item.source_fingerprint}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Skipped Or Manual Inputs"])
    lines.extend(format_list(skipped))
    lines.extend(["", "## Likely Code Roots"])

    root_records: list[dict[str, object]] = []
    if roots:
        for inventory in roots:
            rel = rel_round(round_dir, inventory.path)
            abs_path = inventory.path.resolve()
            languages = sorted(inventory.languages)
            commands = suggest_commands(inventory)
            lines.extend(
                [
                    f"### `{rel}`",
                    "",
                    f"- Files inventoried: {inventory.files_seen}{' (truncated)' if inventory.truncated else ''}",
                    f"- Languages: {', '.join(languages) if languages else 'unknown'}",
                    f"- Serena suitable: {'yes' if serena_suitable(inventory) else 'no'}",
                    f"- Serena activation path: `{abs_path}`",
                    "- README files:",
                    *format_list(inventory.readmes),
                    "- Dependency/build manifests:",
                    *format_list(inventory.dependencies),
                    "- Tests:",
                    *format_list(inventory.tests),
                    "- CI:",
                    *format_list(inventory.ci),
                    "- Large files:",
                    *format_list(inventory.large_files),
                    "- Example code files:",
                    *format_list(inventory.code_files),
                    "- Suggested cheap smoke commands (do not run unless the review scope permits it):",
                    *format_list(commands),
                    "",
                ]
            )
            root_records.append(
                {
                    "path": rel,
                    "absolute_path": abs_path.as_posix(),
                    "languages": languages,
                    "serena_suitable": serena_suitable(inventory),
                    "suggested_smoke_commands": commands,
                    "files_seen": inventory.files_seen,
                    "inventory_truncated": inventory.truncated,
                }
            )
    else:
        lines.append("- none")

    lines.extend(
        [
            "## Serena Usage",
            "",
            "- Activate Serena on one likely code root at a time, not on `cases/` or a whole round.",
            "- The repository `.serena/project.yml` is only for the workflow repo and intentionally ignores `cases/**`; case code roots are separate Serena projects.",
            "- Treat Serena as navigation support; findings still need concrete file/function/config/test evidence.",
            "- Do not run untrusted code just because a smoke command was inferred.",
            "",
        ]
    )
    report.write_text("\n".join(lines), encoding="utf-8")

    serena_json.write_text(
        json.dumps(
            {
                "schema": "serena-code-roots-v1",
                "generated_at": now_utc(),
                "roots": root_records,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def prepare(round_dir: Path, *, refresh: bool) -> tuple[list[PreparedSource], list[str], list[DirectoryInventory]]:
    inputs = round_dir / "inputs"
    workspace = round_dir / "work" / "code"
    if refresh and workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    workspace_manifest = load_workspace_manifest(workspace)
    sources = manifest_sources(workspace_manifest)
    current_keys = current_input_source_keys(inputs)

    prepared: list[PreparedSource] = []
    skipped: list[str] = prune_stale_manifest_sources(round_dir, workspace, sources, current_keys)

    for archive in sorted(inputs.iterdir()) if inputs.is_dir() else []:
        if archive.is_symlink():
            skipped.append(f"`{rel_round(round_dir, archive)}`: symlink input skipped")
            continue
        if is_unsupported_archive(archive):
            skipped.append(f"`{rel_round(round_dir, archive)}`: unsupported archive format; inspect or unpack manually if it contains code")
            continue
        if not is_archive(archive):
            continue
        probe = probe_archive(archive)
        rel = rel_round(round_dir, archive)
        fingerprint = fingerprint_source(archive)
        if probe.size > MAX_ARCHIVE_BYTES:
            skipped.append(f"`{rel}`: {probe.note}")
            continue
        if not probe.possible_code:
            skipped.append(f"`{rel}`: not classified as code archive ({probe.note})")
            continue
        target = target_for_source(workspace, archive)
        rel_target = rel_round(round_dir, target)
        existing = sources.get(rel)
        if target.exists():
            if existing and existing.get("target") == rel_target and existing.get("fingerprint") == fingerprint:
                prepared.append(PreparedSource(archive, target, "already current", "source fingerprint unchanged", fingerprint))
                continue
            if existing and existing.get("target") == rel_target:
                shutil.rmtree(target)
            else:
                skipped.append(
                    f"`{rel}`: target `{rel_target}` already exists without a matching prepare manifest; "
                    "left unchanged. Run with `--refresh` after confirming the workspace can be rebuilt."
                )
                continue
        target.mkdir(parents=True, exist_ok=True)
        extracted, unsafe = extract_archive(archive, target)
        note = f"{extracted} files extracted"
        if collapse_duplicate_top_level(target):
            note += "; collapsed duplicate top-level directory"
        if unsafe:
            note += f"; skipped {len(unsafe)} unsafe/unsupported/over-limit entries"
        prepared.append(PreparedSource(archive, target, "extracted archive", note, fingerprint))
        sources[rel] = {"target": rel_target, "fingerprint": fingerprint, "prepared_at": now_utc()}

    for source in direct_input_code_dirs(inputs):
        target = target_for_source(workspace, source)
        rel = rel_round(round_dir, source)
        rel_target = rel_round(round_dir, target)
        fingerprint = fingerprint_source(source)
        existing = sources.get(rel)
        if target.exists():
            if existing and existing.get("target") == rel_target and existing.get("fingerprint") == fingerprint:
                prepared.append(PreparedSource(source, target, "already current", "source fingerprint unchanged", fingerprint))
                continue
            if existing and existing.get("target") == rel_target:
                shutil.rmtree(target)
            else:
                skipped.append(
                    f"`{rel}`: target `{rel_target}` already exists without a matching prepare manifest; "
                    "left unchanged. Run with `--refresh` after confirming the workspace can be rebuilt."
                )
                continue
        target.mkdir(parents=True, exist_ok=True)
        copied, unsafe = safe_copy_input_dir(source, target)
        note = f"{copied} files copied"
        if unsafe:
            note += f"; skipped {len(unsafe)} symlink/unsafe/unsupported/over-limit entries"
        prepared.append(PreparedSource(source, target, "copied directory", note, fingerprint))
        sources[rel] = {"target": rel_target, "fingerprint": fingerprint, "prepared_at": now_utc()}

    write_workspace_manifest(workspace, workspace_manifest)
    roots = likely_project_roots(workspace)
    write_report(round_dir, prepared, skipped, roots)
    return prepared, skipped, roots


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="scripts/prepare-code-workspace",
        description="Unpack/copy submitted code into work/code and write a compact code/Serena inventory.",
    )
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="replace the whole existing work/code workspace before preparing; removes manually imported code roots",
    )
    args = parser.parse_args(argv[1:])

    validate_id("CASE_ID", args.case_id)
    root = repo_root()
    case_dir = root / "cases" / args.case_id
    if not case_dir.is_dir():
        print(f"Case does not exist: cases/{args.case_id}", file=sys.stderr)
        return 1
    round_id = resolve_round(case_dir, args.round_id)
    round_dir = case_dir / "rounds" / round_id
    if not round_dir.is_dir():
        print(f"Round does not exist: cases/{args.case_id}/rounds/{round_id}", file=sys.stderr)
        return 1

    prepared, skipped, roots = prepare(round_dir, refresh=args.refresh)
    print("Code workspace preparation")
    print(f"Case: {args.case_id}")
    print(f"Round: {round_id}")
    print(f"Prepared sources: {len(prepared)}")
    print(f"Skipped/manual inputs: {len(skipped)}")
    print(f"Likely code roots: {len(roots)}")
    print(f"Report: {REPORT_REL.as_posix()}")
    print(f"Serena roots: {SERENA_ROOTS_REL.as_posix()}")
    if not roots:
        print("No likely code roots found; inspect inputs manually before code review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
