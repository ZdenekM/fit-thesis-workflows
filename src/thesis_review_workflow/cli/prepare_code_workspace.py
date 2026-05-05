"""CLI wrapper for preparing a thesis-round code workspace."""

from __future__ import annotations

import sys

from thesis_review_workflow.code_workspace import main as prepare_code_workspace_main


def console_main() -> int:
    return prepare_code_workspace_main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
