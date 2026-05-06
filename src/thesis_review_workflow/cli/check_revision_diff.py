"""Validate the internal revision-diff artifact shape."""

from __future__ import annotations

from thesis_review_workflow.cli.internal_evidence_validator_cli import run


def main(argv: list[str] | None = None) -> int:
    return run(
        "revision_diff",
        "scripts/check-revision-diff",
        "Validate the internal revision-diff artifact shape.",
        argv,
    )


def console_main() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(console_main())
