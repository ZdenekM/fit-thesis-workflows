"""Validate the internal text-code consistency artifact shape."""

from __future__ import annotations

from thesis_review_workflow.cli.internal_evidence_validator_cli import run


def main(argv: list[str] | None = None) -> int:
    return run(
        "code_consistency",
        "scripts/check-code-consistency",
        "Validate the internal text-code consistency artifact shape.",
        argv,
    )


def console_main() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(console_main())
