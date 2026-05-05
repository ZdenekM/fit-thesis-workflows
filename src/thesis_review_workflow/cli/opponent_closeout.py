"""Run closeout gates for reviewed opponent artifacts."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from thesis_review_workflow.commands import Step, print_step, run_step

ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
COVERAGE_REL = Path("work/agent_coverage.json")
OPPONENT_MATERIALS_REL = Path("outputs/oponent_podklady_revidovane.md")
OPPONENT_REPORT_DRAFT_REL = Path("work/oponent_posudek_draft.md")


def repo_root() -> Path:
    output = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True)
    return Path(output.strip())


def validate_id(label: str, value: str) -> None:
    if not ID_RE.fullmatch(value) or set(value) == {"."}:
        raise SystemExit(
            f"Invalid {label}. Use only letters, numbers, dot, underscore, and dash; dot-only ids are not allowed."
        )


def resolve_round(case_dir: Path, round_id: str | None) -> str:
    if round_id:
        validate_id("ROUND_ID", round_id)
        return round_id
    current = case_dir / "current-round.txt"
    if not current.is_file():
        raise SystemExit(f"Missing current round: {case_dir}/current-round.txt")
    resolved = current.read_text(encoding="utf-8").strip()
    validate_id("ROUND_ID", resolved)
    return resolved


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/opponent-closeout",
        description=(
            "Validate reviewed opponent materials, provenance, role coverage, repo hygiene, "
            "and any existing opponent report draft."
        ),
    )
    parser.add_argument("case_id")
    parser.add_argument("round_id", nargs="?")
    parser.add_argument(
        "--skip-repo-hygiene",
        action="store_true",
        help="skip check-private, check-scripts, and git diff --check",
    )
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv[1:])
    validate_id("CASE_ID", args.case_id)
    root = repo_root()
    case_dir = root / "cases" / args.case_id
    if not case_dir.is_dir():
        raise SystemExit(f"Case does not exist: cases/{args.case_id}")
    round_id = resolve_round(case_dir, args.round_id)
    round_dir = case_dir / "rounds" / round_id
    if not round_dir.is_dir():
        raise SystemExit(f"Round does not exist: cases/{args.case_id}/rounds/{round_id}")

    print("Opponent Closeout")
    print(f"Case: cases/{args.case_id}")
    print(f"Round: cases/{args.case_id}/rounds/{round_id}")

    steps: list[Step] = []
    steps.append(run_step(root, "Round readiness", ["scripts/check-round-ready", args.case_id, round_id]))
    steps.append(
        run_step(root, "Reviewed opponent materials", ["scripts/check-opponent-materials", args.case_id, round_id])
    )
    steps.append(
        run_step(
            root, "Review manifest refresh", ["scripts/init-review-manifest", "--run-checks", args.case_id, round_id]
        )
    )
    if (round_dir / COVERAGE_REL).is_file():
        steps.append(run_step(root, "Agent role coverage", ["scripts/check-agent-coverage", args.case_id, round_id]))
    else:
        steps.append(
            Step(
                label="Agent role coverage",
                command=["scripts/check-agent-coverage", args.case_id, round_id],
                returncode=0,
                output="skipped: work/agent_coverage.json is not present after manifest refresh",
                required=True,
            )
        )
    steps.append(
        run_step(
            root,
            "Review manifest completeness",
            ["scripts/check-review-manifest", "--require-complete", args.case_id, round_id],
        )
    )
    if (round_dir / OPPONENT_REPORT_DRAFT_REL).is_file():
        steps.append(run_step(root, "Opponent report draft", ["scripts/check-opponent-report", args.case_id, round_id]))

    if not args.skip_repo_hygiene:
        steps.append(run_step(root, "Private workspace hygiene", ["scripts/check-private"]))
        steps.append(run_step(root, "Script syntax", ["scripts/check-scripts"]))
        steps.append(run_step(root, "Whitespace/diff hygiene", ["git", "diff", "--check"]))

    for step in steps:
        print_step(step, output_limit=1000)

    print()
    print("## Opponent Closeout Summary")
    if not (round_dir / OPPONENT_MATERIALS_REL).is_file():
        print(f"- Missing reviewed materials: `{OPPONENT_MATERIALS_REL.as_posix()}`.")
    else:
        print(f"- Reviewed materials present: `{OPPONENT_MATERIALS_REL.as_posix()}`.")
    if (round_dir / OPPONENT_REPORT_DRAFT_REL).is_file():
        print(f"- Opponent report draft present and included in closeout: `{OPPONENT_REPORT_DRAFT_REL.as_posix()}`.")
    else:
        print("- No opponent report draft present; closeout covers reviewed materials only.")
    print("- PASS means reviewed materials and any existing report draft passed their current reliance gates.")
    print("- FAIL means fix the named gate before relying on the materials.")
    return 1 if any(not step.ok and step.required for step in steps) else 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
