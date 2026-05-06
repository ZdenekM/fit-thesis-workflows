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
