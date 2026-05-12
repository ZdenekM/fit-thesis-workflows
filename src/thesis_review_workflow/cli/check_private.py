"""Check that private thesis artifacts are not tracked or misplaced."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from thesis_review_workflow.cases import repo_root

SENSITIVE_SUFFIX_RE = re.compile(r"\.(pdf|zip|docx?|odt|tex|bib|txt|log|csv|tsv|xlsx?|ipynb|png|jpe?g|webp)$", re.I)
PRIVATE_JSONL_RE = re.compile(
    r"(^|/)(visual_inventory|reviewer_calibration_profile_history|supervisor_report_calibration_profile_history|"
    r"profile_history)\.jsonl$"
)
PRIVATE_MANIFEST_RE = re.compile(
    r"(^|/)(review_manifest|agent_coverage|serena_roots|\.prepare-code-workspace-manifest|"
    r"opponent_calibration_use|opponent_calibration_advisory|opponent_report_revision_request|"
    r"supervisor_report_feedback_history|supervisor_report_trace|supervisor_report_confirmation|"
    r"supervisor_report_calibration_use|supervisor_report_calibration_advisory|"
    r"supervisor_report_calibration_profile|supervisor_report_calibration_checklist|"
    r"opponent_calibration_refresh_eligibility|reviewer_calibration_profile|reviewer_checklist)\.json$"
)
PRIVATE_CALIBRATION_TREE_RE = re.compile(r"(^|/)work/calibration/.*\.(json|jsonl|md)$")
PRIVATE_MARKDOWN_RE = re.compile(
    r"(^|/)(feedback_student|feedback_student_draft|feedback_k_posudku|revision_diff|code_workspace|"
    r"code_consistency|code_quality_review|literature_citation_review|figure_media_review|"
    r"typography_formal_review|github_code_intake|pr_contribution_review|demo_artifacts_review|"
    r"reference_report_comparison|opponent_reading_packet|reviewer_calibration_profile|"
    r"supervisor_report_calibration_profile|profile_change_log|"
    r"reviewer_profile_change_log|profile_review|opponent-report-operator-feedback|"
    r"supervisor-report-operator-input|vedouci_posudek_draft|vedouci_posudek_revidovany|"
    r"oponent_podklady|oponent_podklady_draft|"
    r"oponent_podklady_revidovane|oponent_posudek_draft)\.md$"
)
PRIVATE_GITHUB_RE = re.compile(
    r"(^|/)(code-manifest\.generated\.ya?ml|changed-files\.tsv|contribution-map\.md|"
    r"[^/]+\.inventory\.md|[^/]+__author-[^/]+__(open|closed)\.json|"
    r"pr\.(url\.txt|meta\.json|diff|patch|files\.(txt|json)|issue-comments\.(json|md)|"
    r"reviews\.(json|md)|review-comments\.(json|md)|checks\.(txt|json|md)|summary\.md)|"
    r"repo\.(url\.txt|meta\.json|refs\.json|readme\.md|license\.txt|default-branch\.txt|snapshot\.txt))$"
)


def git_lines(root: Path, args: list[str]) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(detail or f"git {' '.join(args)} failed")
    return result.stdout.splitlines()


def git_status_untracked(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace").strip() or "git status failed")
    entries = result.stdout.decode("utf-8", errors="replace").split("\0")
    return [entry[3:] for entry in entries if entry.startswith("?? ")]


def git_check_ignore(root: Path, path: str, *, no_index: bool = False) -> bool:
    args = ["git", "-C", str(root), "check-ignore"]
    if no_index:
        args.append("--no-index")
    args.extend(["-q", path])
    return subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False).returncode == 0


def is_sensitive_artifact(path: str) -> bool:
    return bool(
        SENSITIVE_SUFFIX_RE.search(path)
        or PRIVATE_JSONL_RE.search(path)
        or PRIVATE_MANIFEST_RE.search(path)
        or PRIVATE_CALIBRATION_TREE_RE.search(path)
        or PRIVATE_GITHUB_RE.search(path)
    )


def allowed_sensitive_tracked(path: str) -> bool:
    return path == "cases/README.md" or path.startswith("templates/") or path == "config/supervisor-deadlines.tsv"


def allowed_sensitive_untracked(path: str) -> bool:
    return path.startswith("cases/") or path.startswith("templates/") or path == "config/supervisor-deadlines.tsv"


def fail(title: str, paths: list[str]) -> int:
    print(title, file=sys.stderr)
    print("\n".join(paths), file=sys.stderr)
    return 1


def main() -> int:
    root = repo_root()
    try:
        tracked = git_lines(root, ["ls-files"])
        untracked = git_status_untracked(root)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    bad_tracked = [path for path in tracked if path.startswith("cases/") and path != "cases/README.md"]
    if bad_tracked:
        return fail("Private case data is tracked by git:", bad_tracked)

    bad_profile_tracked = [
        path
        for path in tracked
        if path.startswith("profiles/") and path not in {"profiles/README.md", "profiles/default.md"}
    ]
    if bad_profile_tracked:
        return fail("Private reviewer profiles are tracked by git:", bad_profile_tracked)

    sensitive_tracked = [
        path for path in tracked if is_sensitive_artifact(path) and not allowed_sensitive_tracked(path)
    ]
    if sensitive_tracked:
        return fail("Potential private thesis artifacts are tracked outside ignored cases/:", sensitive_tracked)

    private_markdown_tracked = [
        path for path in tracked if PRIVATE_MARKDOWN_RE.search(path) and not path.startswith("cases/")
    ]
    if private_markdown_tracked:
        return fail(
            "Potential private generated Markdown artifacts are tracked outside ignored cases/:",
            private_markdown_tracked,
        )

    sensitive_untracked = [
        path for path in untracked if is_sensitive_artifact(path) and not allowed_sensitive_untracked(path)
    ]
    if sensitive_untracked:
        return fail("Potential private thesis artifacts are present outside ignored cases/:", sensitive_untracked)

    private_markdown_untracked = [
        path for path in untracked if PRIVATE_MARKDOWN_RE.search(path) and not path.startswith("cases/")
    ]
    if private_markdown_untracked:
        return fail(
            "Potential private generated Markdown artifacts are present outside ignored cases/:",
            private_markdown_untracked,
        )

    if not git_check_ignore(root, "cases/__privacy_sentinel__/inputs/thesis.pdf"):
        print("cases/ data is not ignored as expected", file=sys.stderr)
        return 1
    for ignored_profile in ("profiles/local/default.md", "profiles/local/test.md", "profiles/private.md"):
        if not git_check_ignore(root, ignored_profile):
            print(f"{ignored_profile} is not ignored as expected", file=sys.stderr)
            return 1
    for public_profile in ("profiles/default.md", "profiles/README.md"):
        if git_check_ignore(root, public_profile, no_index=True):
            print(f"{public_profile} should be trackable but is ignored", file=sys.stderr)
            return 1

    print("Private workspace and reviewer profile check passed.")
    return 0


def console_main() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(console_main())
