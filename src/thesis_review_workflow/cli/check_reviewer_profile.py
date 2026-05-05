"""Validate effective reviewer profile configuration for a thesis case."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from thesis_review_workflow.cases import repo_root
from thesis_review_workflow.ids import validate_id


def profile_values(case_md: Path) -> list[str]:
    values: list[str] = []
    for line in case_md.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip().lower() == "reviewer profile":
            values.append(value.strip())
    return values


def usage() -> str:
    return (
        "Usage: scripts/check-reviewer-profile CASE_ID\n\n"
        "Validates the Reviewer profile setting in cases/<case-id>/case.md and prints\n"
        "the effective profile files."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/check-reviewer-profile",
        description="Validate reviewer profile configuration for a thesis case.",
    )
    parser.add_argument("case_id")
    return parser


def main(argv: list[str]) -> int:
    if any(arg in {"-h", "--help"} for arg in argv[1:]):
        print(usage())
        return 0
    parser = build_parser()
    args = parser.parse_args(argv[1:])

    try:
        validate_id("CASE_ID", args.case_id)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    root = repo_root()
    case_dir = root / "cases" / args.case_id
    case_md = case_dir / "case.md"
    public_default = root / "profiles" / "default.md"
    local_default = root / "profiles" / "local" / "default.md"

    if not case_dir.is_dir():
        print(f"Case does not exist: cases/{args.case_id}", file=sys.stderr)
        return 1
    if not case_md.is_file():
        print(f"Missing case metadata: cases/{args.case_id}/case.md", file=sys.stderr)
        return 1
    if not public_default.is_file():
        print("Missing public reviewer profile: profiles/default.md", file=sys.stderr)
        return 1

    values = profile_values(case_md)
    if len(values) > 1:
        print(f"Duplicate Reviewer profile fields in cases/{args.case_id}/case.md", file=sys.stderr)
        return 1

    profile = values[0] if values else "default"
    profile = profile or "default"
    relative_files = ["profiles/default.md"]

    if profile == "default":
        if local_default.is_file():
            relative_files.append("profiles/local/default.md")
    elif profile.startswith("local/"):
        profile_id = profile.removeprefix("local/")
        try:
            validate_id("profile-id", profile_id)
        except ValueError:
            print(
                f"Invalid Reviewer profile in case.md: '{profile}'. "
                "Profile id must use only letters, numbers, dot, underscore, and dash.",
                file=sys.stderr,
            )
            return 1
        if ".." in profile_id:
            print(
                f"Invalid Reviewer profile in case.md: '{profile}'. Profile id must not contain '..'.", file=sys.stderr
            )
            return 1
        local_profile = root / "profiles" / "local" / f"{profile_id}.md"
        if not local_profile.is_file():
            print(f"Missing private reviewer profile: profiles/local/{profile_id}.md", file=sys.stderr)
            return 1
        relative_files.append(f"profiles/local/{profile_id}.md")
    else:
        print(
            f"Invalid Reviewer profile in case.md: '{profile}'.\n"
            "Expected 'default' or 'local/<profile-id>' where profile-id uses only letters, numbers, "
            "dot, underscore, and dash.",
            file=sys.stderr,
        )
        return 1

    print(f"Reviewer profile: {profile}")
    print("Effective profile files:")
    for relative_file in relative_files:
        print(f"- {relative_file}")
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
