"""Shared structural artifact and archive classification helpers."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

MAX_LIST = 12
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
    "Library",
    "Temp",
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
    ".jl": "julia",
    ".m": "matlab",
    ".sql": "sql",
}
CODE_SUFFIXES = set(CODE_SUFFIX_LANGUAGES)
SUPPORTED_ARCHIVE_SUFFIXES = {
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
ARCHIVE_SUFFIXES = SUPPORTED_ARCHIVE_SUFFIXES | UNSUPPORTED_ARCHIVE_SUFFIXES
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
ASSIGNMENT_PDF_HINTS = {
    "assignment",
    "zadani",
    "specification",
}
THESIS_PDF_HINTS = {
    "thesis",
    "prace",
    "bakalar",
    "diplom",
    "report",
}
VIDEO_SUFFIXES = {
    ".avi",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp4",
    ".webm",
}
AUDIO_SUFFIXES = {".mp3", ".ogg", ".wav"}
IMAGE_SUFFIXES = {".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp"}
PRESENTATION_SUFFIXES = {".key", ".odp", ".ppt", ".pptx"}
MEDIA_SUFFIXES = VIDEO_SUFFIXES | AUDIO_SUFFIXES | IMAGE_SUFFIXES | PRESENTATION_SUFFIXES
EXECUTABLE_SUFFIXES = {
    ".apk",
    ".appimage",
    ".bat",
    ".cmd",
    ".dll",
    ".dmg",
    ".exe",
    ".jar",
    ".msi",
    ".ps1",
    ".sh",
    ".war",
}
UNITY_VENDOR_ROOTS = {"packages", "library", "temp", "logs", "obj"}
UNITY_SAMPLE_PARTS = {"samples", "sample", "samples~"}
GENERATED_PARTS = {"bin", "obj", "build", "dist", "target", ".gradle", ".vs", "__pycache__"}
VENDOR_PARTS = {"node_modules", "vendor", "packages", "library", "externals", "third_party", "third-party"}
TEST_PART_RE = re.compile(r"(^|[_ .-])(test|tests|spec|specs)([_ .-]|$)")


@dataclass(frozen=True)
class PathEvidence:
    normalized_path: str
    reason_codes: tuple[str, ...]
    artifact_class: str
    confidence: str


def folded(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char)).lower()


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


def is_supported_archive_file(path: Path) -> bool:
    return path.is_file() and archive_suffix(path) in SUPPORTED_ARCHIVE_SUFFIXES


def is_unsupported_archive_file(path: Path) -> bool:
    return path.is_file() and archive_suffix(path) in UNSUPPORTED_ARCHIVE_SUFFIXES


def archive_may_be_code_from_name(path: Path) -> bool:
    name = folded(path.name)
    if any(token in name for token in TEXT_ARCHIVE_HINTS):
        return False
    return True


def archive_entry_code_like(name: str) -> bool:
    pure_name = PurePosixPath(name).name
    lower = name.lower()
    return (
        pure_name in CODE_DEPENDENCY_NAMES
        or PurePosixPath(pure_name).suffix.lower() in CODE_SUFFIX_LANGUAGES
        or "/test/" in lower
        or "/tests/" in lower
        or lower.startswith("test/")
        or lower.startswith("tests/")
    )


def archive_top_entries(names: list[str]) -> list[str]:
    entries: list[str] = []
    seen: set[str] = set()
    for name in names:
        first = name.split("/", 1)[0].strip()
        if not first or first in seen:
            continue
        seen.add(first)
        entries.append(first)
        if len(entries) >= MAX_LIST:
            break
    return entries


def normalize_artifact_path(value: str) -> str:
    return PurePosixPath(value.replace("\\", "/")).as_posix().strip("/")


def classify_path_evidence(value: str) -> PathEvidence:
    normalized = normalize_artifact_path(value)
    parts = tuple(part for part in normalized.split("/") if part)
    folded_parts = tuple(folded(part) for part in parts)
    name = parts[-1] if parts else ""
    lower_name = name.lower()
    suffix = PurePosixPath(lower_name).suffix
    full_folded_path = folded(normalized)
    compound_archive_suffix = archive_suffix(Path(normalized))
    reasons: list[str] = []

    if not parts:
        return PathEvidence(normalized, ("empty_path",), "unknown", "low")
    if lower_name.startswith("readme"):
        reasons.append("readme_candidate")
    if name in DEPENDENCY_NAMES:
        reasons.append("dependency_or_build_manifest")
    if any(part in GENERATED_PARTS for part in folded_parts):
        reasons.append("generated_or_build_output")
    if any(part in VENDOR_PARTS for part in folded_parts):
        reasons.append("vendor_or_package_content")
    if any(part in UNITY_VENDOR_ROOTS for part in folded_parts):
        reasons.append("unity_package_or_generated_content")
    if any(part in UNITY_SAMPLE_PARTS for part in folded_parts):
        reasons.append("sample_content")
    if any(TEST_PART_RE.search(part) for part in folded_parts) or TEST_PART_RE.search(lower_name):
        reasons.append("test_evidence")
    if suffix in CODE_SUFFIX_LANGUAGES:
        reasons.append("code_file")
    if suffix == ".pdf":
        reasons.append("pdf_artifact")
        if any(hint in full_folded_path for hint in ASSIGNMENT_PDF_HINTS):
            reasons.append("assignment_pdf_hint")
        if any(hint in full_folded_path for hint in THESIS_PDF_HINTS):
            reasons.append("thesis_pdf_hint")
    if suffix in MEDIA_SUFFIXES:
        reasons.append("media_artifact")
    if suffix in EXECUTABLE_SUFFIXES:
        reasons.append("executable_artifact")
    if compound_archive_suffix in UNSUPPORTED_ARCHIVE_SUFFIXES:
        reasons.append("unsupported_archive_suffix")
    elif compound_archive_suffix in SUPPORTED_ARCHIVE_SUFFIXES:
        reasons.append("supported_archive_suffix")
        if any(hint in full_folded_path for hint in TEXT_ARCHIVE_HINTS):
            reasons.append("thesis_source_archive_hint")
        elif any(hint in full_folded_path for hint in CODE_ARCHIVE_HINTS):
            reasons.append("code_archive_hint")

    if "unsupported_archive_suffix" in reasons:
        artifact_class = "unsupported_archive"
    elif "generated_or_build_output" in reasons or "unity_package_or_generated_content" in reasons:
        artifact_class = "generated_or_vendor"
    elif "sample_content" in reasons or "vendor_or_package_content" in reasons:
        artifact_class = "sample_or_vendor"
    elif "assignment_pdf_hint" in reasons:
        artifact_class = "assignment_pdf_candidate"
    elif "thesis_pdf_hint" in reasons:
        artifact_class = "thesis_pdf_candidate"
    elif "pdf_artifact" in reasons:
        artifact_class = "pdf_artifact"
    elif "media_artifact" in reasons:
        artifact_class = "media_artifact"
    elif "executable_artifact" in reasons:
        artifact_class = "executable_artifact"
    elif "test_evidence" in reasons:
        artifact_class = "test_evidence"
    elif "readme_candidate" in reasons:
        artifact_class = "readme_candidate"
    elif "thesis_source_archive_hint" in reasons:
        artifact_class = "thesis_source_archive_candidate"
    elif "code_archive_hint" in reasons:
        artifact_class = "code_archive_candidate"
    elif "code_file" in reasons or "dependency_or_build_manifest" in reasons:
        artifact_class = "first_party_candidate"
    elif "supported_archive_suffix" in reasons:
        artifact_class = "supported_archive"
    else:
        artifact_class = "unknown"

    confidence = "high" if reasons else "low"
    return PathEvidence(normalized, tuple(dict.fromkeys(reasons)), artifact_class, confidence)
