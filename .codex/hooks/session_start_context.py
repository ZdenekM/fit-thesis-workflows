#!/usr/bin/env python3
"""Emit lightweight thesis-workflow reminders at Codex session start/resume."""

from __future__ import annotations

import json
import sys


def main() -> int:
    payload = json.load(sys.stdin)
    source = payload.get("source", "startup")

    reminders = [
        "Read AGENTS.md before thesis workflow work.",
        "Use repo-local skills in .agents/skills for supervisor feedback, opponent materials, revision diff, and code consistency.",
        "Real student data belongs under gitignored cases/; never force-add case contents.",
        "Before supervisor feedback, run scripts/check-supervisor-ready for the active case.",
        "Before opponent materials, run scripts/check-round-ready for the active case.",
        "Supervisor feedback is iterative: read prior outputs/feedback_student.md before writing a new round.",
    ]
    if source == "resume":
        reminders.append("On resume, re-check the active case current-round.txt and prior feedback index.")

    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": " ".join(reminders),
            }
        },
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
