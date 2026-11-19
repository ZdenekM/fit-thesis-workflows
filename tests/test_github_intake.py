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


def test_a_failed_requested_ref_leaves_no_unrecorded_checkout(tmp_path: Path, monkeypatch) -> None:
    """The clone holds the default branch; leaving it would make the wrong revision reviewable."""
    from thesis_review_workflow.cli import import_github_code

    round_dir = tmp_path / "cases" / "case-a" / "rounds" / "round-a"
    round_dir.mkdir(parents=True)

    def fake_run(args: list[str], **kwargs: object):
        if "clone" in args:
            target = Path(args[-1])
            target.mkdir(parents=True)
            (target / "main.py").write_text("x = 1\n", encoding="utf-8")
        returncode = 1 if "checkout" in args else 0
        return import_github_code.CommandResult(args=args, returncode=returncode, stdout="", stderr="")

    monkeypatch.setattr(import_github_code, "command_available", lambda name: True)
    monkeypatch.setattr(import_github_code, "run", fake_run)
    ctx = make_import_context(tmp_path, round_dir)

    status, note = import_github_code.checkout_repo(ctx, "owner", "project", "v-missing", None)

    assert (status, note) == ("unavailable", "checkout failed: requested ref")
    assert not (round_dir / "work" / "code" / "owner__project__standalone").exists()
    assert not any((round_dir / "work" / "code").iterdir())
    assert ctx.workspaces == []
    assert any("v-missing" in limitation for limitation in ctx.limitations)


def make_import_context(tmp_path: Path, round_dir: Path) -> ImportContext:
    return ImportContext(
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


def test_confirmed_gh_auth_gives_every_github_git_call_its_credentials(tmp_path: Path, monkeypatch) -> None:
    """A private repository cloned only after the operator passed a credential helper by hand."""
    from thesis_review_workflow.cli import import_github_code

    round_dir = tmp_path / "cases" / "case-a" / "rounds" / "round-a"
    round_dir.mkdir(parents=True)
    calls: list[tuple[list[str], object]] = []

    def fake_run(args: list[str], **kwargs: object):
        calls.append((args, kwargs.get("env")))
        if "clone" in args:
            target = Path(args[-1])
            target.mkdir(parents=True)
            (target / "main.py").write_text("x = 1\n", encoding="utf-8")
        return import_github_code.CommandResult(args=args, returncode=0, stdout="gh version x\n", stderr="")

    monkeypatch.setattr(import_github_code, "command_available", lambda name: True)
    monkeypatch.setattr(import_github_code, "run", fake_run)
    ctx = make_import_context(tmp_path, round_dir)

    toolchain = import_github_code.summarize_toolchain(ctx)
    import_github_code.checkout_repo(ctx, "owner", "private-project", "v1", None)

    assert toolchain["gh_auth"] == "authenticated"
    assert ["gh", "api", "--hostname", "github.com", "user", "--jq", ".login"] in [args for args, _ in calls]
    # A checkout counts as network: a Git LFS smudge downloads objects during it.
    network = [(args, env) for args, env in calls if {"clone", "fetch", "checkout"} & set(args)]
    assert len(network) == 3
    for args, env in network:
        assert args[:7] == ["git", "-c", "core.askPass=", *import_github_code.GH_GIT_CREDENTIAL_ARGS]
        assert env == {"GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "", "GCM_INTERACTIVE": "never"}


def test_unconfirmed_gh_auth_leaves_git_credentials_alone_and_says_why_a_clone_failed(
    tmp_path: Path, monkeypatch
) -> None:
    from thesis_review_workflow.cli import import_github_code

    round_dir = tmp_path / "cases" / "case-a" / "rounds" / "round-a"
    round_dir.mkdir(parents=True)
    calls: list[list[str]] = []

    def fake_run(args: list[str], **kwargs: object):
        calls.append(args)
        failed = args[:2] == ["gh", "api"] or "clone" in args
        return import_github_code.CommandResult(args=args, returncode=1 if failed else 0, stdout="", stderr="")

    monkeypatch.setattr(import_github_code, "command_available", lambda name: True)
    monkeypatch.setattr(import_github_code, "run", fake_run)
    ctx = make_import_context(tmp_path, round_dir)

    import_github_code.summarize_toolchain(ctx)
    status, _ = import_github_code.checkout_repo(ctx, "owner", "private-project", None, None)

    assert status == "unavailable"
    clone = next(args for args in calls if "clone" in args)
    assert clone[:4] == ["git", "-c", "core.askPass=", "clone"]
    assert any("gh auth login" in limitation for limitation in ctx.limitations)


def test_a_clone_failing_with_gh_credentials_names_the_account_to_check(tmp_path: Path, monkeypatch) -> None:
    """The helper replaces the operator's git credentials, so a wrong gh account must be named."""
    from thesis_review_workflow.cli import import_github_code

    round_dir = tmp_path / "cases" / "case-a" / "rounds" / "round-a"
    round_dir.mkdir(parents=True)

    def fake_run(args: list[str], **kwargs: object):
        return import_github_code.CommandResult(args=args, returncode=1 if "clone" in args else 0, stdout="", stderr="")

    monkeypatch.setattr(import_github_code, "command_available", lambda name: True)
    monkeypatch.setattr(import_github_code, "run", fake_run)
    ctx = make_import_context(tmp_path, round_dir)
    import_github_code.summarize_toolchain(ctx)

    import_github_code.checkout_repo(ctx, "owner", "private-project", None, None)

    assert any("gh auth switch" in limitation for limitation in ctx.limitations)


def test_run_adds_the_given_environment_to_the_inherited_one(monkeypatch) -> None:
    import sys

    from thesis_review_workflow.cli import import_github_code

    monkeypatch.setenv("INHERITED_MARKER", "kept")
    script = "import os; print(os.environ['GIT_TERMINAL_PROMPT'], os.environ['INHERITED_MARKER'])"

    result = import_github_code.run([sys.executable, "-c", script], env={"GIT_TERMINAL_PROMPT": "0"})

    assert result.stdout.split() == ["0", "kept"]


def test_remove_tree_removes_read_only_git_objects(tmp_path: Path, monkeypatch) -> None:
    """Git writes pack files read-only; on Windows a plain rmtree aborts the import on them.

    POSIX deletes a read-only file from a writable directory, so the Windows rule is
    simulated: unlinking a file without its write bit fails until the bit is restored.
    """
    import os
    import stat

    from thesis_review_workflow.cli import import_github_code

    pack = tmp_path / "clone" / ".git" / "objects" / "pack" / "pack-x.pack"
    pack.parent.mkdir(parents=True)
    pack.write_bytes(b"x")
    pack.chmod(stat.S_IREAD)
    real_unlink = os.unlink
    refused: list[str] = []

    def windows_like_unlink(path, *args, **kwargs):
        dir_fd = kwargs.get("dir_fd")
        mode = os.stat(path, dir_fd=dir_fd).st_mode if dir_fd is not None else os.stat(path).st_mode
        if not mode & stat.S_IWRITE:
            refused.append(str(path))
            raise PermissionError(13, "Access is denied", str(path))
        return real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(os, "unlink", windows_like_unlink)

    import_github_code.remove_tree(tmp_path / "clone")

    assert refused
    assert not (tmp_path / "clone").exists()
