"""Pure helpers for GitHub intake evidence rendering and classification."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

GITHUB_REPO_RE = re.compile(
    r"^(?:https://github\.com/|git@github\.com:)?" r"(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)
GITHUB_PR_RE = re.compile(
    r"^https://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/"
    r"(?P<repo>[A-Za-z0-9_.-]+)/pull/(?P<number>[0-9]+)(?:[/?#].*)?$"
)
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


class GitHubValueError(ValueError):
    """Unsupported GitHub repository or pull-request value."""


def parse_repo(value: str) -> tuple[str, str]:
    match = GITHUB_REPO_RE.match(value.strip())
    if not match:
        raise GitHubValueError(f"Unsupported GitHub repository value: {value}")
    return match.group("owner"), match.group("repo")


def parse_pr_url(value: str) -> tuple[str, str, int]:
    match = GITHUB_PR_RE.match(value.strip())
    if not match:
        raise GitHubValueError(f"Unsupported GitHub PR URL: {value}")
    return match.group("owner"), match.group("repo"), int(match.group("number"))


def repo_slug(owner: str, repo: str) -> str:
    raw = f"{owner}__{repo}"
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", raw)


def pr_slug(owner: str, repo: str, number: int) -> str:
    return f"{repo_slug(owner, repo)}__pr-{number}"


def format_ref(name: Any, oid: Any) -> str:
    ref_name = str(name or "").strip()
    ref_oid = str(oid or "").strip()
    if ref_name and ref_oid:
        return f"{ref_name} `{ref_oid}`"
    if ref_name:
        return ref_name
    if ref_oid:
        return f"`{ref_oid}`"
    return "unknown"


def format_ref_plain(name: Any, oid: Any) -> str:
    ref_name = str(name or "").strip()
    ref_oid = str(oid or "").strip()
    return " ".join(part for part in [ref_name, ref_oid] if part) or "unknown"


def markdown_body(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return text if text else "_No body._"


def comments_to_markdown(data: Any, source_name: str, title: str, kind: str) -> str:
    if data is None:
        return f"# {title}\n\nCould not parse `{source_name}`.\n"
    if not isinstance(data, list):
        data = [data]
    lines = [f"# {title}", ""]
    if not data:
        lines.extend(["No comments returned.", ""])
        return "\n".join(lines)
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            continue
        user = item.get("user") or item.get("author") or {}
        if isinstance(user, dict):
            author = user.get("login") or user.get("name") or "unknown"
        else:
            author = str(user)
        state = item.get("state") or kind
        created = (
            item.get("created_at") or item.get("createdAt") or item.get("submitted_at") or item.get("submittedAt") or ""
        )
        url = item.get("html_url") or item.get("url") or ""
        path_value = item.get("path")
        line_value = item.get("line") or item.get("original_line") or item.get("position")
        lines.append(f"## {index}. {author} - {state}")
        if created:
            lines.append(f"- Time: {created}")
        if path_value:
            suffix = f":{line_value}" if line_value else ""
            lines.append(f"- Location: `{path_value}{suffix}`")
        if url:
            lines.append(f"- URL: {url}")
        lines.extend(["", markdown_body(item.get("body")), ""])
    return "\n".join(lines)


def summarize_plain_checks(plain_text: str) -> str:
    buckets: dict[str, int] = {}
    for raw_line in plain_text.splitlines():
        parts = [part.strip() for part in raw_line.split("\t")]
        if len(parts) < 2 or not parts[0]:
            continue
        state = parts[1] or "unknown"
        buckets[state] = buckets.get(state, 0) + 1
    return ", ".join(f"{name}:{count}" for name, count in sorted(buckets.items()))


def checks_to_markdown(meta_checks: Any, plain_text: str) -> tuple[str, str]:
    data = meta_checks if isinstance(meta_checks, list) else []
    lines = ["# PR checks", ""]
    plain_summary = summarize_plain_checks(plain_text)
    if plain_text.strip():
        lines.extend(["## gh pr checks output", "", "```text", plain_text.strip(), "```", ""])
    lines.extend(["## statusCheckRollup", "", "| Check | State | Bucket | Workflow | Link |", "|---|---|---|---|---|"])
    buckets: dict[str, int] = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        state = str(item.get("state") or item.get("bucket") or "unknown")
        bucket = str(item.get("bucket") or "")
        buckets[bucket or state] = buckets.get(bucket or state, 0) + 1
        lines.append(
            "| "
            + " | ".join(
                [
                    str(item.get("name") or ""),
                    state,
                    bucket,
                    str(item.get("workflow") or ""),
                    str(item.get("link") or ""),
                ]
            )
            + " |"
        )
    summary = plain_summary or ", ".join(f"{name}:{count}" for name, count in sorted(buckets.items())) or "none"
    if not data and not plain_text.strip():
        summary = "unavailable"
        lines.append("| unavailable |  |  |  |  |")
    return "\n".join(lines) + "\n", summary


def normalize_file_list(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def file_category(path: str) -> str:
    lower = path.lower()
    name = Path(path).name
    if lower.startswith(".github/workflows/"):
        return "ci"
    if name in DEPENDENCY_NAMES:
        return "dependency"
    if name.lower().startswith("readme") or lower.endswith((".md", ".rst", ".adoc")):
        return "docs"
    if re.search(r"(^|/)(test|tests|spec|specs)(/|$)", lower) or re.search(r"(test|spec)\.", name.lower()):
        return "tests"
    if lower.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".zip", ".bin", ".onnx", ".pt", ".pth")):
        return "binary_or_artifact"
    return "source_or_config"


def commit_authors(meta: dict[str, Any]) -> str:
    commits = meta.get("commits")
    nodes: list[Any] = []
    if isinstance(commits, list):
        nodes = commits
    elif isinstance(commits, dict):
        nodes = commits.get("nodes") or []
    authors: dict[str, int] = {}
    for item in nodes:
        if not isinstance(item, dict):
            continue
        author = item.get("author") or {}
        name = None
        if isinstance(author, dict):
            user = author.get("user") or {}
            if isinstance(user, dict):
                name = user.get("login")
            name = name or author.get("name") or author.get("email")
        if not name:
            name = "unknown"
        authors[str(name)] = authors.get(str(name), 0) + 1
    if not authors:
        return "unavailable"
    return ", ".join(f"{name} ({count})" for name, count in sorted(authors.items()))


def pr_summary_markdown(url: str, meta: dict[str, Any], checks_summary: str, files: list[str]) -> str:
    lines = [
        "# Pull Request Snapshot",
        "",
        f"- URL: {url}",
        f"- Title: {meta.get('title') or ''}",
        f"- State: {meta.get('state') or 'unknown'}",
        f"- Draft: {meta.get('isDraft')}",
        (
            f"- Author: {(meta.get('author') or {}).get('login')}"
            if isinstance(meta.get("author"), dict)
            else f"- Author: {meta.get('author')}"
        ),
        f"- Base: {format_ref(meta.get('baseRefName'), meta.get('baseRefOid'))}",
        f"- Head: {format_ref(meta.get('headRefName'), meta.get('headRefOid'))}",
        f"- Merge state: {meta.get('mergeStateStatus') or 'unknown'}",
        f"- Review decision: {meta.get('reviewDecision') or 'unknown'}",
        f"- Changed files: {meta.get('changedFiles') or len(files) or 'unknown'}",
        f"- Additions/deletions: {meta.get('additions') or 'unknown'} / {meta.get('deletions') or 'unknown'}",
        f"- Checks: {checks_summary}",
        "",
        "## Changed Files",
        "",
    ]
    if files:
        lines.extend(f"- `{item}`" for item in files)
    else:
        lines.append("- unavailable")
    return "\n".join(lines) + "\n"


def load_json_text(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
