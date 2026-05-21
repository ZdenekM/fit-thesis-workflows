"""Shared manifest/helper-check identifiers."""

from __future__ import annotations

GENERIC_OPPONENT_REPORT_CHECK = "check-opponent-report"
OPPONENT_REPORT_CHECK_IDS = frozenset(
    {
        "check-opponent-report:canonical",
        "check-opponent-report:clean",
    }
)
OBSERVED_ONLY_CHECK_IDS = frozenset({"check-review-wave.opponent-report.draft"})
KNOWN_HELPER_CHECK_IDS = frozenset(
    {
        "check-agent-coverage",
        "check-code-consistency",
        "check-code-quality-review",
        "check-evaluation-claims",
        "check-feedback-language",
        "check-feedback-output",
        "check-figure-media-review",
        "check-literature-citation-review",
        "check-opponent-calibration-profile",
        "check-opponent-materials",
        *OPPONENT_REPORT_CHECK_IDS,
        "check-report-calibration",
        "check-review-manifest",
        "check-revision-diff",
        "check-round-ready",
        "check-supervisor-ready",
        "check-supervisor-report",
        "check-supervisor-report-calibration-profile",
        "check-supervisor-report-ready",
        "check-theses-checker-summary",
        "check-theses-similarity-report",
        "check-typography-formal",
    }
)


def helper_check_id_error(check_id: str, *, allow_observed_only: bool = False) -> str:
    if check_id == GENERIC_OPPONENT_REPORT_CHECK:
        return (
            "generic check-opponent-report is ambiguous; use check-opponent-report:canonical "
            "or check-opponent-report:clean"
        )
    allowed = KNOWN_HELPER_CHECK_IDS | (OBSERVED_ONLY_CHECK_IDS if allow_observed_only else frozenset())
    if check_id not in allowed:
        return f"unknown helper check id: {check_id}"
    return ""


def validate_helper_check_ids(
    check_ids: list[str] | tuple[str, ...],
    *,
    label: str,
    allow_observed_only: bool = False,
) -> list[str]:
    errors: list[str] = []
    for index, check_id in enumerate(check_ids, start=1):
        issue = helper_check_id_error(check_id, allow_observed_only=allow_observed_only)
        if issue:
            errors.append(f"{label} item {index}: {issue}")
    return errors
