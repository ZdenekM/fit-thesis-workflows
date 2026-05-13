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
        "Use repo-local skills in .agents/skills and the Codex agent role profile matrix "
        "in docs/agent-profile-matrix.md for role routing.",
        "For code-bearing supervisor/opponent rounds, run both code consistency and code quality review "
        "or state the concrete limitation.",
        "Real student data belongs under gitignored cases/; never force-add case contents.",
        "Before supervisor feedback, run logical workflow command check-supervisor-ready for the active case; "
        "on Windows use the packaged .cmd/.ps1 launcher from README.md.",
        "Before opponent materials, run logical workflow command check-round-ready for the active case; "
        "on Windows use the packaged .cmd/.ps1 launcher from README.md.",
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
