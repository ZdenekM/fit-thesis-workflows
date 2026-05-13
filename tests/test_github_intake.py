from pathlib import Path

from thesis_review_workflow.cli.import_github_code import (
    GITHUB_SNAPSHOT_SCHEMA_VERSION,
    ImportContext,
    build_github_snapshot_manifest,
)
from thesis_review_workflow.github_intake import (
    GitHubValueError,
    checks_to_markdown,
    comments_to_markdown,
    commit_authors,
    file_category,
    format_ref,
    normalize_file_list,
    parse_pr_url,
    parse_repo,
    pr_slug,
    pr_summary_markdown,
    repo_slug,
    summarize_plain_checks,
)


def capture_value_error(func, *args) -> GitHubValueError:
    try:
        func(*args)
    except GitHubValueError as exc:
        return exc
    raise AssertionError("Expected GitHubValueError")


def test_parse_repo_and_pr_url_accept_supported_github_shapes() -> None:
    assert parse_repo("owner/repo") == ("owner", "repo")
    assert parse_repo("https://github.com/owner/repo.git") == ("owner", "repo")
    assert parse_repo("git@github.com:owner/repo.git") == ("owner", "repo")
    assert parse_pr_url("https://github.com/owner/repo/pull/42/files") == ("owner", "repo", 42)
    assert "Unsupported GitHub PR URL" in str(capture_value_error(parse_pr_url, "https://example.com/pull/1"))


def test_slugs_and_refs_are_stable_for_paths_and_markdown() -> None:
    assert repo_slug("org-name", "repo/name") == "org-name__repo_name"
    assert pr_slug("org", "repo", 7) == "org__repo__pr-7"
    assert format_ref("main", "abc123") == "main `abc123`"
    assert format_ref("", "abc123") == "`abc123`"
    assert format_ref("", "") == "unknown"


def test_comment_and_check_markdown_rendering() -> None:
    comments = [
        {
            "user": {"login": "reviewer"},
            "state": "COMMENTED",
            "created_at": "2026-01-01T00:00:00Z",
            "path": "src/app.py",
            "line": 12,
            "html_url": "https://github.com/org/repo/pull/1#discussion",
            "body": "Looks good",
        }
    ]

    rendered = comments_to_markdown(comments, "comments.json", "PR comments", "comment")

    assert "## 1. reviewer - COMMENTED" in rendered
    assert "- Location: `src/app.py:12`" in rendered
    assert "Looks good" in rendered
    assert comments_to_markdown(None, "bad.json", "PR comments", "comment").startswith("# PR comments")

    meta_checks = [{"name": "lint", "state": "SUCCESS", "bucket": "pass", "workflow": "ci", "link": "url"}]
    checks_md, summary = checks_to_markdown(meta_checks, "lint\tPASS\nunit\tFAIL\n")
    assert "| lint | SUCCESS | pass | ci | url |" in checks_md
    assert summary == "FAIL:1, PASS:1"
    assert summarize_plain_checks("") == ""


def test_file_classification_and_pr_summary_helpers() -> None:
    assert normalize_file_list("\n src/app.py \n\n tests/test_app.py\n") == ["src/app.py", "tests/test_app.py"]
    assert file_category(".github/workflows/ci.yml") == "ci"
    assert file_category("requirements.txt") == "dependency"
    assert file_category("README.md") == "docs"
    assert file_category("tests/test_app.py") == "tests"
    assert file_category("models/model.onnx") == "binary_or_artifact"
    assert file_category("src/app.py") == "source_or_config"

    meta = {
        "title": "Add feature",
        "state": "OPEN",
        "isDraft": False,
        "author": {"login": "student"},
        "baseRefName": "main",
        "baseRefOid": "base",
        "headRefName": "feature",
        "headRefOid": "head",
        "changedFiles": 2,
        "additions": 10,
        "deletions": 1,
        "commits": {"nodes": [{"author": {"user": {"login": "student"}}}, {"author": {"name": "mentor"}}]},
    }

    summary = pr_summary_markdown("https://github.com/org/repo/pull/1", meta, "PASS:1", ["src/app.py"])

    assert "- Author: student" in summary
    assert "- Base: main `base`" in summary
    assert "- `src/app.py`" in summary
    assert commit_authors(meta) == "mentor (1), student (1)"


def test_github_snapshot_manifest_hashes_changed_files_checks_and_checkout(tmp_path: Path) -> None:
    round_dir = tmp_path / "cases" / "case-a" / "rounds" / "round-a"
    pr_dir = round_dir / "inputs" / "github" / "prs" / "owner__project__pr-123"
    intake_dir = round_dir / "work" / "github-intake"
    checkout_dir = round_dir / "work" / "code" / "owner__project__pr-123"
    pr_dir.mkdir(parents=True)
    intake_dir.mkdir(parents=True)
    checkout_dir.mkdir(parents=True)
    (pr_dir / "pr.checks.json").write_text("[]\n", encoding="utf-8")
    (pr_dir / "pr.checks.txt").write_text("unit\tpass\n", encoding="utf-8")
    (pr_dir / "pr.checks.md").write_text("# Checks\n", encoding="utf-8")
    (intake_dir / "changed-files.tsv").write_text(
        "pr\tfile\tcategory\nowner/project#123\tsrc/app.py\tsource\n", encoding="utf-8"
    )
    (checkout_dir / "src").mkdir()
    (checkout_dir / "src" / "app.py").write_text("print('demo')\n", encoding="utf-8")
    ctx = ImportContext(
        root=tmp_path,
        case_id="case-a",
        round_dir=round_dir,
        round_rel=Path("cases/case-a/rounds/round-a"),
        timestamp="2026-05-13T12:00:00Z",
        refresh=False,
        no_checkout=False,
        student_login="student",
        discovery_author=None,
        expected_scope="demo",
    )
    ctx.pr_rows.append(
        {
            "pr": "owner/project#123",
            "url": "https://github.com/owner/project/pull/123",
            "state": "OPEN",
            "draft": "False",
            "base": "main " + "1" * 40,
            "base_sha": "1" * 40,
            "head": "feature " + "2" * 40,
            "head_sha": "2" * 40,
            "merge": "CLEAN",
            "checks": "PASS:1",
            "changed": "1",
            "notes": "head checkout prepared",
        }
    )
    ctx.changed_rows.append(("owner/project#123", "src/app.py", "source"))
    ctx.workspaces.append((checkout_dir, "PR head checkout", "static inspection only"))

    manifest = build_github_snapshot_manifest(
        ctx,
        mode="upstream_pr_contribution",
        toolchain={"gh": "gh version smoke", "git": "git version smoke"},
        repos=[],
        pr_urls=["https://github.com/owner/project/pull/123"],
    )

    pull_requests = manifest["pull_requests"]
    changed_file_list = manifest["changed_file_list"]
    checkout_paths = manifest["checkout_paths"]

    assert isinstance(pull_requests, list)
    assert isinstance(changed_file_list, dict)
    assert isinstance(checkout_paths, list)
    assert manifest["schema_version"] == GITHUB_SNAPSHOT_SCHEMA_VERSION
    assert manifest["case_id"] == "case-a"
    assert manifest["round_id"] == "round-a"
    assert pull_requests[0]["head_sha"] == "2" * 40
    assert changed_file_list["available"] is True
    assert changed_file_list["normalized_sha256"]
    assert manifest["checks_summary_sha256"]
    assert checkout_paths[0]["path"] == "work/code/owner__project__pr-123"
    assert checkout_paths[0]["sha256"]
