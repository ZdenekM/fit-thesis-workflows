"""Refresh `cases/_rag/`, the allowlisted copy of case Markdown that local RAG indexes.

The workstation's local-rag sync runs this before every sync; see
`docs/local-rag-usage.md`. It never ingests anything itself.
"""

from __future__ import annotations

import argparse
import sys

from thesis_review_workflow.cases import repo_root
from thesis_review_workflow.rag_case_mirror import MIRROR_DIR, refresh_mirror


def build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="scripts/refresh-rag-case-mirror",
        description=f"Copy allowlisted case Markdown into cases/{MIRROR_DIR}/ for local RAG.",
    )


def main(argv: list[str] | None = None) -> int:
    build_parser().parse_args(argv)
    cases_root = repo_root() / "cases"
    if not cases_root.is_dir():
        print("No cases/ directory.", file=sys.stderr)
        return 1
    try:
        result = refresh_mirror(cases_root)
    except (OSError, ValueError) as exc:
        print(f"refresh-rag-case-mirror: {exc}", file=sys.stderr)
        return 1
    print(
        f"cases/{MIRROR_DIR}: {result.copied} copied, {result.unchanged} unchanged, "
        f"{result.removed} removed"
    )
    return 0


def console_main() -> int:
    return main(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(console_main())
