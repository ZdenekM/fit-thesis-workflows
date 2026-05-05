"""Import read-only GitHub code/PR evidence into a thesis round workspace."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NoReturn

from thesis_review_workflow.paths import rel_round as format_rel_round

ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
GITHUB_LOGIN_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
GITHUB_REPO_RE = re.compile(
    r"^(?:https://github\.com/|git@github\.com:)?" r"(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)
GITHUB_PR_RE = re.compile(
    r"^https://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/"
    r"(?P<repo>[A-Za-z0-9_.-]+)/pull/(?P<number>[0-9]+)(?:[/?#].*)?$"
)
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
PR_VIEW_FIELDS = ",".join(
    [
        "number",
        "title",
        "state",
        "isDraft",
        "author",
        "url",
        "body",
        "baseRefName",
        "headRefName",
        "headRefOid",
        "headRepository",
        "headRepositoryOwner",
        "isCrossRepository",
        "createdAt",
        "updatedAt",
        "closedAt",
        "mergedAt",
        "mergedBy",
        "mergeStateStatus",
        "mergeable",
        "reviewDecision",
        "reviewRequests",
        "latestReviews",
        "commits",
        "files",
        "additions",
        "deletions",
        "changedFiles",
        "statusCheckRollup",
        "labels",
        "milestone",
    ]
)
REPO_VIEW_FIELDS = ",".join(
    [
        "nameWithOwner",
        "url",
        "description",
        "defaultBranchRef",
        "isFork",
        "parent",
        "isPrivate",
        "visibility",
        "licenseInfo",
        "primaryLanguage",
        "languages",
        "pushedAt",
        "updatedAt",
        "repositoryTopics",
    ]
)


@dataclass(frozen=True)
class CommandResult:
    args: list[str]
    returncode: int
    stdout: str
    stderr: str


@dataclass
class EvidenceFile:
    path: Path
    purpose: str


@dataclass
class PendingWrite:
    path: Path
    text: str
    purpose: str


@dataclass
class ImportContext:
    root: Path
    case_id: str
    round_dir: Path
    round_rel: Path
    timestamp: str
    refresh: bool
    no_checkout: bool
    student_login: str | None
    discovery_author: str | None
    expected_scope: str | None
    evidence: list[EvidenceFile] = field(default_factory=list)
    workspaces: list[tuple[Path, str, str]] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    repo_rows: list[dict[str, str]] = field(default_factory=list)
    pr_rows: list[dict[str, str]] = field(default_factory=list)
    changed_rows: list[tuple[str, str, str]] = field(default_factory=list)
    command_log: list[str] = field(default_factory=list)
    pending_writes: list[PendingWrite] = field(default_factory=list)

    def add_evidence(self, path: Path, purpose: str) -> None:
        self.evidence.append(EvidenceFile(path=path, purpose=purpose))

    def rel_round(self, path: Path) -> str:
        return format_rel_round(self.round_dir, path)


def repo_root() -> Path:
    output = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True)
    return Path(output.strip())


def die_usage(message: str) -> NoReturn:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def validate_id(label: str, value: str) -> None:
    if not ID_RE.fullmatch(value):
        die_usage(f"Invalid {label}. Use only letters, numbers, dot, underscore, and dash.")


def resolve_round(root: Path, case_id: str, round_id: str | None) -> Path:
    case_dir = root / "cases" / case_id
    if not case_dir.is_dir():
        die_usage(f"Case not found: {case_id}")

    if round_id is None:
        current_round = case_dir / "current-round.txt"
        if not current_round.is_file():
            die_usage("ROUND_ID not provided and current-round.txt is missing")
        round_id = current_round.read_text(encoding="utf-8").strip()

    validate_id("round id", round_id)
    round_dir = case_dir / "rounds" / round_id
    if not round_dir.is_dir():
        die_usage(f"Round not found: {round_id}")
    return round_dir


def parse_repo(value: str) -> tuple[str, str]:
    match = GITHUB_REPO_RE.match(value.strip())
    if not match:
        die_usage(f"Unsupported GitHub repository value: {value}")
    assert match is not None
    return match.group("owner"), match.group("repo")


def parse_pr_url(value: str) -> tuple[str, str, int]:
    match = GITHUB_PR_RE.match(value.strip())
    if not match:
        die_usage(f"Unsupported GitHub PR URL: {value}")
    assert match is not None
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


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(args: list[str], *, cwd: Path | None = None, allow_failure: bool = False) -> CommandResult:
    completed = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    result = CommandResult(
        args=args,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
    if result.returncode != 0 and not allow_failure:
        command = " ".join(args)
        print(f"Command failed: {command}", file=sys.stderr)
        if result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
        raise SystemExit(1)
    return result


def command_available(name: str) -> bool:
    return shutil.which(name) is not None


def ensure_clean_target(path: Path, *, refresh: bool, kind: str) -> None:
    if not path.exists():
        return
    if not refresh:
        raise SystemExit(
            f"{kind} already exists: {path}. Re-run with --refresh to replace this " "case-local GitHub snapshot."
        )
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def write_text(ctx: ImportContext, path: Path, text: str, purpose: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    ctx.add_evidence(path, purpose)


def write_json(ctx: ImportContext, path: Path, data: Any, purpose: str) -> None:
    write_text(ctx, path, json.dumps(data, ensure_ascii=False, indent=2) + "\n", purpose)


def load_json_text(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def load_json_file(path: Path) -> Any:
    return load_json_text(path.read_text(encoding="utf-8"))


def write_command_stdout(
    ctx: ImportContext,
    path: Path,
    args: list[str],
    purpose: str,
    *,
    allow_failure: bool = False,
    empty_on_failure: str | None = None,
) -> CommandResult:
    result = run(args, allow_failure=allow_failure)
    ctx.command_log.append(f"{result.returncode}\t{' '.join(args)}\t-> {ctx.rel_round(path)}")
    if result.returncode != 0 and empty_on_failure is not None and not result.stdout:
        stdout = empty_on_failure
    else:
        stdout = result.stdout
    write_text(ctx, path, stdout, purpose)
    if result.returncode != 0:
        ctx.limitations.append(f"`{' '.join(args[:3])}` failed for {ctx.rel_round(path)}; see import log.")
    return result


def write_import_log(
    ctx: ImportContext, mode: str, toolchain: dict[str, str], repos: list[str], pr_urls: list[str]
) -> None:
    lines = [
        "GitHub code intake import log",
        f"started_at: {ctx.timestamp}",
        f"finished_at: {utc_now()}",
        f"mode: {mode}",
        "toolchain:",
    ]
    for key, value in sorted(toolchain.items()):
        lines.append(f"  {key}: {value}")
    lines.extend(["sources:", "  repositories:"])
    if repos:
        lines.extend(f"    - {repo}" for repo in repos)
    else:
        lines.append("    []")
    lines.append("  pull_requests:")
    if pr_urls:
        lines.extend(f"    - {url}" for url in pr_urls)
    else:
        lines.append("    []")
    lines.append("commands:")
    if ctx.command_log:
        lines.extend(f"  {item}" for item in ctx.command_log)
    else:
        lines.append("  []")
    lines.append("limitations:")
    if ctx.limitations:
        lines.extend(f"  - {item}" for item in ctx.limitations)
    else:
        lines.append("  []")
    lines.append("")
    write_text(ctx, ctx.round_dir / "inputs" / "github" / "import.log", "\n".join(lines), "GitHub intake import log")


def summarize_toolchain(ctx: ImportContext) -> dict[str, str]:
    toolchain: dict[str, str] = {}
    if command_available("gh"):
        result = run(["gh", "--version"], allow_failure=True)
        first_line = result.stdout.splitlines()[0] if result.stdout.splitlines() else "available"
        toolchain["gh"] = first_line
        auth = run(["gh", "auth", "status"], allow_failure=True)
        toolchain["gh_auth"] = "authenticated" if auth.returncode == 0 else "unauthenticated_or_unavailable"
        if auth.returncode != 0:
            ctx.limitations.append("`gh auth status` did not confirm authenticated access.")
    else:
        toolchain["gh"] = "unavailable"
        toolchain["gh_auth"] = "not_checked"
        ctx.limitations.append("`gh` CLI is unavailable; GitHub API evidence cannot be imported.")

    if command_available("git"):
        result = run(["git", "--version"], allow_failure=True)
        toolchain["git"] = result.stdout.strip() or "available"
    else:
        toolchain["git"] = "unavailable"
        ctx.limitations.append("`git` is unavailable; code checkout cannot be prepared.")
    toolchain["github_mcp"] = "not_used_by_helper"
    return toolchain


def discover_pr_urls(ctx: ImportContext, repo: str, author: str, limit: int) -> list[str]:
    owner, repo_name = parse_repo(repo)
    discovery_dir = ctx.round_dir / "inputs" / "github" / "discovery"
    urls: list[str] = []
    for state in ("open", "closed"):
        output_path = discovery_dir / f"{repo_slug(owner, repo_name)}__author-{author}__{state}.json"
        args = [
            "gh",
            "search",
            "prs",
            "--repo",
            f"{owner}/{repo_name}",
            "--author",
            author,
            "--state",
            state,
            "--json",
            "url,number,title,state,author,createdAt,updatedAt",
            "--limit",
            str(limit),
        ]
        result = run(args)
        ctx.command_log.append(f"{result.returncode}\t{' '.join(args)}\t-> {ctx.rel_round(output_path)}")
        ctx.pending_writes.append(
            PendingWrite(
                path=output_path,
                text=result.stdout,
                purpose=f"GitHub search result for {state} PRs by author",
            )
        )
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            data = None
        if not isinstance(data, list):
            ctx.limitations.append(f"Could not parse discovered PR list from {ctx.rel_round(output_path)}.")
            continue
        for item in data:
            if isinstance(item, dict) and isinstance(item.get("url"), str):
                urls.append(item["url"])
    seen: set[str] = set()
    deduped_urls: list[str] = []
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        deduped_urls.append(url)
    urls = deduped_urls
    if not urls:
        ctx.limitations.append(f"No PRs discovered for author `{author}` in `{owner}/{repo_name}`.")
    return urls


def markdown_body(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return text if text else "_No body._"


def comments_to_markdown(path: Path, title: str, kind: str) -> str:
    data = load_json_file(path)
    if data is None:
        return f"# {title}\n\nCould not parse `{path.name}`.\n"
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


def checks_to_markdown(meta_checks: Any, plain_path: Path) -> tuple[str, str]:
    data = meta_checks if isinstance(meta_checks, list) else []
    lines = ["# PR checks", ""]
    plain_text = plain_path.read_text(encoding="utf-8", errors="replace") if plain_path.is_file() else ""
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


def import_pr(ctx: ImportContext, url: str) -> dict[str, Any]:
    owner, repo_name, number = parse_pr_url(url)
    slug = pr_slug(owner, repo_name, number)
    pr_dir = ctx.round_dir / "inputs" / "github" / "prs" / slug

    meta_result = run(["gh", "pr", "view", url, "--json", PR_VIEW_FIELDS])
    meta = load_json_text(meta_result.stdout)
    if not isinstance(meta, dict):
        raise SystemExit(f"Could not parse PR metadata from gh pr view for {url}")

    ensure_clean_target(pr_dir, refresh=ctx.refresh, kind="PR evidence directory")
    pr_dir.mkdir(parents=True, exist_ok=True)

    write_text(ctx, pr_dir / "pr.url.txt", url + "\n", "Original pull request URL")
    meta_path = pr_dir / "pr.meta.json"
    ctx.command_log.append(f"{meta_result.returncode}\t{' '.join(meta_result.args)}\t-> {ctx.rel_round(meta_path)}")
    write_text(ctx, meta_path, meta_result.stdout, "Pull request metadata from gh pr view")

    diff_path = pr_dir / "pr.diff"
    write_command_stdout(
        ctx,
        diff_path,
        ["gh", "pr", "diff", url, "--color", "never"],
        "Pull request diff",
        allow_failure=True,
        empty_on_failure="",
    )
    patch_path = pr_dir / "pr.patch"
    write_command_stdout(
        ctx,
        patch_path,
        ["gh", "pr", "diff", url, "--patch", "--color", "never"],
        "Pull request patch",
        allow_failure=True,
        empty_on_failure="",
    )
    files_path = pr_dir / "pr.files.txt"
    files_result = write_command_stdout(
        ctx,
        files_path,
        ["gh", "pr", "diff", url, "--name-only"],
        "Pull request changed file list",
        allow_failure=True,
        empty_on_failure="",
    )
    files = normalize_file_list(files_result.stdout)
    write_json(ctx, pr_dir / "pr.files.json", meta.get("files") or [], "Pull request files from metadata")

    api_specs = [
        (
            "pr.issue-comments.json",
            ["gh", "api", "--paginate", f"repos/{owner}/{repo_name}/issues/{number}/comments"],
            "Issue/PR conversation comments",
        ),
        (
            "pr.reviews.json",
            ["gh", "api", "--paginate", f"repos/{owner}/{repo_name}/pulls/{number}/reviews"],
            "Formal pull request reviews",
        ),
        (
            "pr.review-comments.json",
            ["gh", "api", "--paginate", f"repos/{owner}/{repo_name}/pulls/{number}/comments"],
            "Line-level review comments",
        ),
    ]
    for filename, command, purpose in api_specs:
        output_path = pr_dir / filename
        write_command_stdout(
            ctx,
            output_path,
            command,
            purpose,
            allow_failure=True,
            empty_on_failure="[]\n",
        )

    for json_name, md_name, title, kind in [
        ("pr.issue-comments.json", "pr.issue-comments.md", "PR conversation comments", "comment"),
        ("pr.reviews.json", "pr.reviews.md", "Formal PR reviews", "review"),
        ("pr.review-comments.json", "pr.review-comments.md", "Line-level PR review comments", "line comment"),
    ]:
        write_text(
            ctx,
            pr_dir / md_name,
            comments_to_markdown(pr_dir / json_name, title, kind),
            f"Markdown summary of {title.lower()}",
        )

    checks_path = pr_dir / "pr.checks.json"
    write_json(
        ctx,
        checks_path,
        meta.get("statusCheckRollup") or [],
        "Pull request statusCheckRollup from gh pr view",
    )
    checks_text_path = pr_dir / "pr.checks.txt"
    write_command_stdout(
        ctx,
        checks_text_path,
        ["gh", "pr", "checks", url],
        "Plain pull request checks from gh pr checks",
        allow_failure=True,
        empty_on_failure="checks unavailable\n",
    )
    checks_md, checks_summary = checks_to_markdown(meta.get("statusCheckRollup"), checks_text_path)
    write_text(ctx, pr_dir / "pr.checks.md", checks_md, "Markdown summary of pull request checks")

    summary = pr_summary_markdown(url, meta, checks_summary, files)
    write_text(ctx, pr_dir / "pr.summary.md", summary, "Human-readable pull request summary")

    workspace_note = (
        checkout_pr(ctx, owner, repo_name, number, meta) if not ctx.no_checkout else "checkout skipped by --no-checkout"
    )
    if ctx.no_checkout:
        ctx.limitations.append(f"Checkout skipped for PR #{number} by --no-checkout.")
        ctx.limitations.append(
            f"PR #{number} was imported through multiple live GitHub reads without checkout SHA validation."
        )

    for file_path in files:
        ctx.changed_rows.append((f"{owner}/{repo_name}#{number}", file_path, file_category(file_path)))

    ctx.pr_rows.append(
        {
            "pr": f"{owner}/{repo_name}#{number}",
            "url": url,
            "state": str(meta.get("state") or "unknown"),
            "draft": str(meta.get("isDraft")),
            "base": format_ref_plain(meta.get("baseRefName"), meta.get("baseRefOid")),
            "head": format_ref_plain(meta.get("headRefName"), meta.get("headRefOid")),
            "merge": str(meta.get("mergeStateStatus") or "unknown"),
            "checks": checks_summary,
            "changed": str(meta.get("changedFiles") or len(files) or "unknown"),
            "notes": workspace_note,
        }
    )
    return meta


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


def checkout_pr(ctx: ImportContext, owner: str, repo_name: str, number: int, meta: dict[str, Any]) -> str:
    if not command_available("git"):
        ctx.limitations.append(f"`git` unavailable; PR #{number} checkout was not prepared.")
        return "checkout unavailable: git missing"
    slug = pr_slug(owner, repo_name, number)
    work_dir = ctx.round_dir / "work" / "code" / slug
    ensure_clean_target(work_dir, refresh=ctx.refresh, kind="PR checkout directory")
    work_dir.parent.mkdir(parents=True, exist_ok=True)
    repo_url = f"https://github.com/{owner}/{repo_name}.git"
    clone = run(["git", "clone", "--no-checkout", repo_url, str(work_dir)], allow_failure=True)
    if clone.returncode != 0:
        ctx.limitations.append(f"Could not clone `{owner}/{repo_name}` for PR #{number}.")
        return "checkout failed: clone"
    head_fetch = run(
        ["git", "-C", str(work_dir), "fetch", "origin", f"pull/{number}/head:pr-{number}-head"], allow_failure=True
    )
    if head_fetch.returncode != 0:
        ctx.limitations.append(f"Could not fetch `pull/{number}/head` for PR #{number}.")
        return "checkout failed: head fetch"
    checkout = run(["git", "-C", str(work_dir), "checkout", "--detach", f"pr-{number}-head"], allow_failure=True)
    if checkout.returncode != 0:
        ctx.limitations.append(f"Could not checkout PR #{number} head.")
        return "checkout failed: head checkout"

    intake_dir = ctx.round_dir / "work" / "github-intake"
    intake_dir.mkdir(parents=True, exist_ok=True)
    head_sha = run(["git", "-C", str(work_dir), "rev-parse", "HEAD"], allow_failure=True)
    write_text(ctx, intake_dir / f"{slug}.head-sha.txt", head_sha.stdout, "Checked out PR head SHA")
    expected_head = str(meta.get("headRefOid") or "").strip()
    actual_head = head_sha.stdout.strip()
    if expected_head and actual_head and expected_head != actual_head:
        ctx.limitations.append(
            f"PR #{number} checkout head `{actual_head}` differs from metadata headRefOid `{expected_head}`; "
            "the PR may have moved during import."
        )
    if meta.get("baseRefOid"):
        write_text(
            ctx, intake_dir / f"{slug}.base-sha.txt", str(meta["baseRefOid"]) + "\n", "PR base SHA from metadata"
        )

    merge_fetch = run(
        ["git", "-C", str(work_dir), "fetch", "origin", f"refs/pull/{number}/merge:pr-{number}-merge"],
        allow_failure=True,
    )
    if merge_fetch.returncode == 0:
        merge_sha = run(["git", "-C", str(work_dir), "rev-parse", f"pr-{number}-merge"], allow_failure=True)
        write_text(ctx, intake_dir / f"{slug}.merge-sha.txt", merge_sha.stdout, "GitHub PR merge ref SHA")
    else:
        write_text(ctx, intake_dir / f"{slug}.merge-sha.txt", "merge ref unavailable\n", "GitHub PR merge ref status")
        ctx.limitations.append(f"GitHub merge ref unavailable for PR #{number}.")

    for name, command, purpose in [
        ("status.txt", ["git", "-C", str(work_dir), "status", "--short", "--branch"], "PR checkout git status"),
        (
            "recent-log.txt",
            ["git", "-C", str(work_dir), "log", "--oneline", "--decorate", "-n", "50"],
            "PR checkout recent git log",
        ),
        (
            "submodules.txt",
            ["git", "-C", str(work_dir), "submodule", "status", "--recursive"],
            "PR checkout submodule status",
        ),
    ]:
        result = run(command, allow_failure=True)
        write_text(ctx, intake_dir / f"{slug}.{name}", result.stdout or result.stderr, purpose)

    ctx.workspaces.append(
        (work_dir, "PR head checkout", "Inspect statically; do not run untrusted code without explicit review.")
    )
    inventory_workspace(ctx, work_dir, slug)
    return "head checkout prepared"


def import_repo(ctx: ImportContext, repo_value: str, ref: str | None, commit: str | None) -> None:
    owner, repo_name = parse_repo(repo_value)
    slug = repo_slug(owner, repo_name)
    repo_dir = ctx.round_dir / "inputs" / "github" / "repos" / slug
    ensure_clean_target(repo_dir, refresh=ctx.refresh, kind="repository evidence directory")
    repo_dir.mkdir(parents=True, exist_ok=True)
    canonical = f"{owner}/{repo_name}"
    write_command_stdout(
        ctx,
        repo_dir / "repo.meta.json",
        ["gh", "repo", "view", canonical, "--json", REPO_VIEW_FIELDS],
        "Repository metadata from gh repo view",
        allow_failure=True,
        empty_on_failure="{}\n",
    )
    write_text(ctx, repo_dir / "repo.url.txt", f"https://github.com/{owner}/{repo_name}\n", "Repository URL")

    checkout_sha = "not checked out"
    workspace_note = "checkout skipped by --no-checkout"
    if ctx.no_checkout:
        ctx.limitations.append(f"Checkout skipped for repository `{canonical}` by --no-checkout.")
    else:
        checkout_sha, workspace_note = checkout_repo(ctx, owner, repo_name, ref, commit)

    meta = load_json_file(repo_dir / "repo.meta.json")
    default_branch = ""
    visibility = ""
    if isinstance(meta, dict):
        default_ref = meta.get("defaultBranchRef") or {}
        if isinstance(default_ref, dict):
            default_branch = str(default_ref.get("name") or "")
        visibility = str(meta.get("visibility") or ("private" if meta.get("isPrivate") else "unknown"))
    ctx.repo_rows.append(
        {
            "repo": canonical,
            "ref": commit or ref or "default branch at import time",
            "checkout": checkout_sha.strip(),
            "default": default_branch,
            "visibility": visibility,
            "notes": workspace_note,
        }
    )


def checkout_repo(
    ctx: ImportContext,
    owner: str,
    repo_name: str,
    ref: str | None,
    commit: str | None,
) -> tuple[str, str]:
    if not command_available("git"):
        ctx.limitations.append(f"`git` unavailable; repository `{owner}/{repo_name}` checkout was not prepared.")
        return "unavailable", "checkout unavailable: git missing"
    slug = f"{repo_slug(owner, repo_name)}__standalone"
    work_dir = ctx.round_dir / "work" / "code" / slug
    ensure_clean_target(work_dir, refresh=ctx.refresh, kind="repository checkout directory")
    work_dir.parent.mkdir(parents=True, exist_ok=True)
    clone = run(["git", "clone", f"https://github.com/{owner}/{repo_name}.git", str(work_dir)], allow_failure=True)
    if clone.returncode != 0:
        ctx.limitations.append(f"Could not clone repository `{owner}/{repo_name}`.")
        return "unavailable", "checkout failed: clone"
    run(["git", "-C", str(work_dir), "fetch", "--all", "--tags"], allow_failure=True)
    requested = commit or ref
    if requested:
        checkout = run(["git", "-C", str(work_dir), "checkout", "--detach", requested], allow_failure=True)
        if checkout.returncode != 0:
            ctx.limitations.append(f"Could not checkout requested ref `{requested}` in `{owner}/{repo_name}`.")
            return "unavailable", "checkout failed: requested ref"
    sha = run(["git", "-C", str(work_dir), "rev-parse", "HEAD"], allow_failure=True).stdout.strip()
    intake_dir = ctx.round_dir / "work" / "github-intake"
    intake_dir.mkdir(parents=True, exist_ok=True)
    write_text(ctx, intake_dir / f"{slug}.checkout-sha.txt", sha + "\n", "Standalone repository checkout SHA")
    for name, command, purpose in [
        ("remotes.txt", ["git", "-C", str(work_dir), "remote", "-v"], "Repository remotes"),
        ("status.txt", ["git", "-C", str(work_dir), "status", "--short", "--branch"], "Repository checkout status"),
        (
            "recent-log.txt",
            ["git", "-C", str(work_dir), "log", "--oneline", "--decorate", "-n", "50"],
            "Repository recent git log",
        ),
        (
            "submodules.txt",
            ["git", "-C", str(work_dir), "submodule", "status", "--recursive"],
            "Repository submodule status",
        ),
    ]:
        result = run(command, allow_failure=True)
        write_text(ctx, intake_dir / f"{slug}.{name}", result.stdout or result.stderr, purpose)
    ctx.workspaces.append(
        (work_dir, "Standalone repository checkout", "Inspect statically; run code only after explicit risk review.")
    )
    inventory_workspace(ctx, work_dir, slug)
    note = "pinned commit checkout" if commit else ("requested ref checkout" if ref else "live default-branch checkout")
    if not commit:
        ctx.limitations.append(f"`{owner}/{repo_name}` was imported from a live ref, not a pinned commit SHA.")
    return sha, note


def inventory_workspace(ctx: ImportContext, work_dir: Path, slug: str) -> None:
    inventory_dir = ctx.round_dir / "work" / "github-intake"
    inventory_dir.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(work_dir):
        dirnames[:] = [name for name in dirnames if name not in SAFE_SKIP_DIRS]
        for filename in filenames:
            path = Path(dirpath) / filename
            files.append(path)
            if len(files) >= 5000:
                ctx.limitations.append(f"Inventory for `{slug}` was truncated at 5000 files.")
                break
        if len(files) >= 5000:
            break

    readmes: list[str] = []
    dependencies: list[str] = []
    tests: list[str] = []
    ci: list[str] = []
    large: list[str] = []
    for path in files:
        rel = path.relative_to(work_dir).as_posix()
        lower = rel.lower()
        name = path.name
        if name.lower().startswith("readme"):
            readmes.append(rel)
        if name in DEPENDENCY_NAMES:
            dependencies.append(rel)
        if lower.startswith(".github/workflows/"):
            ci.append(rel)
        if re.search(r"(^|/)(test|tests|spec|specs)(/|$)", lower) or re.search(r"(test|spec)\.", name.lower()):
            tests.append(rel)
        try:
            if path.stat().st_size >= 10 * 1024 * 1024:
                large.append(rel)
        except OSError:
            pass

    lines = [
        f"# GitHub Code Inventory: {slug}",
        "",
        f"- Workspace: `{ctx.rel_round(work_dir)}`",
        f"- Files inventoried: {len(files)}",
        "",
        "## README files",
        *list_items(readmes),
        "",
        "## Dependency/build manifests",
        *list_items(dependencies),
        "",
        "## Test files/directories",
        *list_items(tests[:100]),
        "",
        "## CI config",
        *list_items(ci),
        "",
        "## Large files",
        *list_items(large),
        "",
    ]
    write_text(ctx, inventory_dir / f"{slug}.inventory.md", "\n".join(lines), "Static workspace inventory")


def list_items(values: list[str]) -> list[str]:
    if not values:
        return ["- none found"]
    return [f"- `{value}`" for value in values]


def write_contribution_map(ctx: ImportContext) -> None:
    intake_dir = ctx.round_dir / "work" / "github-intake"
    intake_dir.mkdir(parents=True, exist_ok=True)
    by_category: dict[str, int] = {}
    for _, _, category in ctx.changed_rows:
        by_category[category] = by_category.get(category, 0) + 1
    lines = [
        "# GitHub Contribution Map",
        "",
        "This is intake evidence for PR-based thesis review. It scopes changed files",
        "and review metadata; it is not a final code-quality judgment.",
        "",
        "## Changed Files By Category",
        "",
        "| Category | Count |",
        "|---|---:|",
    ]
    if by_category:
        for category, count in sorted(by_category.items()):
            lines.append(f"| {category} | {count} |")
    else:
        lines.append("| none | 0 |")
    lines.extend(["", "## Changed Files", "", "| PR | File | Category |", "|---|---|---|"])
    if ctx.changed_rows:
        for pr, file_path, category in ctx.changed_rows:
            lines.append(f"| {pr} | `{file_path}` | {category} |")
    else:
        lines.append("| none |  |  |")
    lines.extend(
        [
            "",
            "## Attribution Notes",
            "",
            f"- Student GitHub login supplied: `{ctx.student_login or 'unknown'}`.",
            f"- PR discovery author supplied: `{ctx.discovery_author or 'not used'}`.",
            "- Treat upstream code as baseline/context. Review student-owned contribution through PR diffs, "
            "commits, tests, docs, and review discussion.",
            "- If commit authorship or PR authorship is ambiguous, keep it as a limitation until checked "
            "against thesis text or a CONTRIBUTIONS/README-THESIS file.",
            "",
        ]
    )
    write_text(ctx, intake_dir / "contribution-map.md", "\n".join(lines), "PR contribution map")
    tsv = "pr\tfile\tcategory\n" + "\n".join("\t".join(row) for row in ctx.changed_rows) + "\n"
    write_text(ctx, intake_dir / "changed-files.tsv", tsv, "Changed file inventory")


def write_generated_manifest(ctx: ImportContext, repos: list[str], pr_urls: list[str], mode: str) -> None:
    manifest = ctx.round_dir / "inputs" / "github" / "code-manifest.generated.yml"
    lines = [
        f"code_submission_mode: {mode}",
        "student:",
        f"  github_login: {ctx.student_login or 'unknown'}",
        f"  declared_role: {ctx.expected_scope or 'unknown'}",
        "repositories:",
    ]
    if repos:
        for repo in repos:
            lines.extend(
                ["  - repo: " + "/".join(parse_repo(repo)), f"    url: https://github.com/{'/'.join(parse_repo(repo))}"]
            )
    else:
        lines.append("  []")
    lines.append("pull_requests:")
    if pr_urls:
        for url in pr_urls:
            lines.extend(["  - url: " + url, "    role: contribution"])
    else:
        lines.append("  []")
    lines.extend(["review_focus:", "  - code/text consistency", "  - code quality", ""])
    write_text(ctx, manifest, "\n".join(lines), "Generated GitHub intake manifest")


def preflight_all_targets(ctx: ImportContext, repos: list[str], pr_urls: list[str]) -> None:
    targets: list[tuple[Path, str]] = [
        (ctx.round_dir / "inputs" / "github" / "code-manifest.generated.yml", "generated GitHub manifest"),
        (ctx.round_dir / "inputs" / "github" / "import.log", "GitHub import log"),
        (ctx.round_dir / "work" / "github-intake" / "contribution-map.md", "GitHub contribution map"),
        (ctx.round_dir / "work" / "github-intake" / "changed-files.tsv", "GitHub changed-file inventory"),
        (ctx.round_dir / "outputs" / "github_code_intake.md", "GitHub intake output"),
    ]
    targets.extend((item.path, "PR discovery evidence") for item in ctx.pending_writes)
    for repo_value in repos:
        owner, repo_name = parse_repo(repo_value)
        targets.append(
            (
                ctx.round_dir / "inputs" / "github" / "repos" / repo_slug(owner, repo_name),
                "repository evidence directory",
            )
        )
        if not ctx.no_checkout:
            targets.append(
                (
                    ctx.round_dir / "work" / "code" / f"{repo_slug(owner, repo_name)}__standalone",
                    "repository checkout directory",
                )
            )
    for url in pr_urls:
        owner, repo_name, number = parse_pr_url(url)
        targets.append(
            (ctx.round_dir / "inputs" / "github" / "prs" / pr_slug(owner, repo_name, number), "PR evidence directory")
        )
        if not ctx.no_checkout:
            targets.append(
                (ctx.round_dir / "work" / "code" / pr_slug(owner, repo_name, number), "PR checkout directory")
            )

    seen: set[Path] = set()
    for path, kind in targets:
        if path in seen:
            continue
        seen.add(path)
        ensure_clean_target(path, refresh=ctx.refresh, kind=kind)


def flush_pending_writes(ctx: ImportContext) -> None:
    for item in ctx.pending_writes:
        write_text(ctx, item.path, item.text, item.purpose)
    ctx.pending_writes.clear()


def write_output(
    ctx: ImportContext, mode: str, toolchain: dict[str, str], repos: list[str], pr_urls: list[str]
) -> None:
    output = ctx.round_dir / "outputs" / "github_code_intake.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# GitHub Code Intake",
        "",
        "## Summary",
        "",
        f"- Mode: `{mode}`",
        f"- Import timestamp: `{ctx.timestamp}`",
        "- Access method: `gh CLI` for GitHub metadata; `git` for checkout when enabled.",
        f"- Authentication: `{toolchain.get('gh_auth', 'unknown')}`",
        f"- Student GitHub login: `{ctx.student_login or 'unknown'}`",
        f"- PR discovery author: `{ctx.discovery_author or 'not used'}`",
        f"- Expected scope: {ctx.expected_scope or 'not provided'}",
        (
            "- Checkout mode: "
            f"{'skipped by --no-checkout' if ctx.no_checkout else 'prepared under work/code when possible'}"
        ),
        "",
        "## Inputs Received",
        "",
        "| Type | Value | Notes |",
        "|---|---|---|",
    ]
    for repo in repos:
        lines.append(f"| repository | `{repo}` | standalone GitHub source |")
    for url in pr_urls:
        lines.append(f"| pull request | {url} | PR contribution source |")
    if not repos and not pr_urls:
        lines.append("| none |  | no GitHub source imported |")

    lines.extend(["", "## Toolchain", "", "| Tool | Status |", "|---|---|"])
    for key, value in sorted(toolchain.items()):
        lines.append(f"| `{key}` | {value} |")

    lines.extend(
        [
            "",
            "## Repository Snapshots",
            "",
            "| Repo | Ref requested | Checkout SHA | Default branch | Visibility | Notes |",
            "|---|---|---|---|---|---|",
        ]
    )
    if ctx.repo_rows:
        for row in ctx.repo_rows:
            lines.append(
                f"| `{row['repo']}` | `{row['ref']}` | `{row['checkout']}` | "
                f"`{row['default']}` | `{row['visibility']}` | {row['notes']} |"
            )
    else:
        lines.append("| none |  |  |  |  |  |")

    lines.extend(
        [
            "",
            "## Pull Request Snapshots",
            "",
            "| PR | State | Draft | Base | Head | Merge state | Checks | Notes |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    if ctx.pr_rows:
        for row in ctx.pr_rows:
            lines.append(
                f"| `{row['pr']}` | `{row['state']}` | `{row['draft']}` | "
                f"`{row['base']}` | `{row['head']}` | `{row['merge']}` | `{row['checks']}` | {row['notes']} |"
            )
    else:
        lines.append("| none |  |  |  |  |  |  |  |")

    lines.extend(["", "## Evidence Files Written", "", "| File | Purpose |", "|---|---|"])
    for evidence in sorted(ctx.evidence, key=lambda item: str(item.path)):
        lines.append(f"| `{ctx.rel_round(evidence.path)}` | {evidence.purpose} |")

    lines.extend(["", "## Code Workspace", "", "| Path | Meaning | Safe to inspect? | Notes |", "|---|---|---|---|"])
    if ctx.workspaces:
        for path, meaning, note in ctx.workspaces:
            lines.append(f"| `{ctx.rel_round(path)}` | {meaning} | yes, static inspection | {note} |")
    else:
        lines.append("| none |  | no checkout prepared | Use frozen diff/metadata only. |")

    lines.extend(
        [
            "",
            "## Inventory Highlights",
            "",
            "- See `work/github-intake/*.inventory.md` for checkout inventories when checkout was enabled.",
            "- See `work/github-intake/contribution-map.md` for PR changed-file scope.",
            "- Do not treat upstream baseline code as the student's implementation; "
            "use PR diffs and declared scope for attribution.",
            "",
            "## Handoff Recommendations",
            "",
            "- Run thesis-code-consistency: yes, if thesis text claims implementation scope, tests, CI, "
            "reproducibility, or upstream contribution.",
            "- Run thesis-code-quality-review: yes, but scope the review to student-owned PR diffs "
            "or the imported standalone checkout.",
            "- Run figure/media review only if repository screenshots/result images are used as thesis evidence.",
            "- For PR-based work, use `outputs/github_code_intake.md` as intake evidence before making "
            "code-quality or text-code consistency claims.",
            "",
            "## Limitations",
            "",
        ]
    )
    if ctx.limitations:
        lines.extend(f"- {item}" for item in ctx.limitations)
    else:
        lines.append("- No intake limitations recorded by the helper.")

    write_text(ctx, output, "\n".join(lines) + "\n", "GitHub intake operator evidence")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import read-only GitHub repo/PR evidence into an ignored thesis round workspace.",
        usage=(
            "scripts/import-github-code CASE_ID [ROUND_ID] "
            "[--pr-url URL ...] [--repo OWNER/REPO] [--discover-prs OWNER/REPO --author LOGIN]"
        ),
    )
    parser.add_argument("positionals", nargs="*", help="CASE_ID and optional ROUND_ID")
    parser.add_argument("--pr-url", action="append", default=[], help="GitHub pull request URL to import")
    parser.add_argument("--repo", action="append", default=[], help="GitHub repository URL or OWNER/REPO")
    parser.add_argument("--ref", help="Branch or tag for standalone repository import")
    parser.add_argument("--commit", help="Exact commit SHA for standalone repository import")
    parser.add_argument("--student-login", help="Student GitHub login for attribution context")
    parser.add_argument("--expected-scope", help="Short human note about expected thesis-relevant contribution scope")
    parser.add_argument("--discover-prs", action="append", default=[], help="Discover PRs by author in OWNER/REPO")
    parser.add_argument("--author", help="GitHub author login for --discover-prs; defaults to --student-login")
    parser.add_argument("--limit", type=int, default=30, help="Maximum PRs to discover per repository")
    parser.add_argument(
        "--no-checkout", action="store_true", help="Import metadata/diffs only; do not run git clone/fetch"
    )
    parser.add_argument(
        "--refresh", action="store_true", help="Replace previous case-local GitHub evidence for the same sources"
    )
    args = parser.parse_args(argv)
    if len(args.positionals) not in {1, 2}:
        parser.error("expected CASE_ID and optional ROUND_ID")
    if not args.pr_url and not args.repo and not args.discover_prs:
        parser.error("provide --pr-url, --repo, or --discover-prs")
    if args.discover_prs and not (args.author or args.student_login):
        parser.error("--discover-prs requires --author or --student-login")
    if args.limit < 1:
        parser.error("--limit must be positive")
    for label, value in [("--student-login", args.student_login), ("--author", args.author)]:
        if value and not GITHUB_LOGIN_RE.fullmatch(value):
            parser.error(f"{label} must look like a GitHub login")
    return args


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    case_id = args.positionals[0]
    validate_id("case id", case_id)
    round_id = args.positionals[1] if len(args.positionals) == 2 else None
    if round_id:
        validate_id("round id", round_id)

    root = repo_root()
    round_dir = resolve_round(root, case_id, round_id)
    ctx = ImportContext(
        root=root,
        case_id=case_id,
        round_dir=round_dir,
        round_rel=round_dir.relative_to(root),
        timestamp=utc_now(),
        refresh=args.refresh,
        no_checkout=args.no_checkout,
        student_login=args.student_login or args.author,
        discovery_author=args.author,
        expected_scope=args.expected_scope,
    )

    toolchain = summarize_toolchain(ctx)
    if toolchain["gh"] == "unavailable":
        raise SystemExit("`gh` CLI is required for V1 GitHub intake.")

    pr_urls: list[str] = list(args.pr_url)
    for repo_value in args.discover_prs:
        pr_urls.extend(discover_pr_urls(ctx, repo_value, args.author or args.student_login, args.limit))

    seen: set[str] = set()
    deduped_pr_urls: list[str] = []
    for url in pr_urls:
        if url in seen:
            continue
        seen.add(url)
        deduped_pr_urls.append(url)
    pr_urls = deduped_pr_urls

    repos: list[str] = list(args.repo)
    if pr_urls and repos:
        mode = "mixed"
    elif pr_urls:
        mode = "upstream_pr_contribution"
    else:
        mode = "standalone_repo"

    preflight_all_targets(ctx, repos, pr_urls)

    for repo_value in repos:
        import_repo(ctx, repo_value, args.ref, args.commit)
    for url in pr_urls:
        import_pr(ctx, url)

    flush_pending_writes(ctx)
    write_generated_manifest(ctx, repos, pr_urls, mode)
    write_contribution_map(ctx)
    write_import_log(ctx, mode, toolchain, repos, pr_urls)
    write_output(ctx, mode, toolchain, repos, pr_urls)

    output_rel = ctx.rel_round(ctx.round_dir / "outputs" / "github_code_intake.md")
    print(f"GitHub code intake written: {ctx.round_rel}/{output_rel}")
    if ctx.limitations:
        print(f"Completed with {len(ctx.limitations)} limitation(s).")
    else:
        print("Completed without recorded intake limitations.")
    return 0


def console_main() -> int:
    return main(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(console_main())
