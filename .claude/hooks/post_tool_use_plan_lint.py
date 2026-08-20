#!/usr/bin/env python3
"""Run the plan-contract gate immediately after a tracked plan document is edited.

Feedback in seconds instead of at commit time: a swallowed required heading, a charter that lost a
label, an oversized Decision Log entry, or a new line anchor in living text surfaces right after
the Write/Edit that introduced it. Plan review then spends its rounds on judgement instead of on
lint work, which is what let one sibling-repo plan burn four review rounds on its own prose.

Reads the Claude Code PostToolUse JSON payload on stdin; exit 2 feeds the gate's output back to the
agent. The gate itself is ``tests/test_plan_contract.py``, runnable standalone via its ``__main__``
so this hook needs no pytest.
"""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any

GATE = "tests/test_plan_contract.py"


def main() -> int:
    try:
        payload: dict[str, Any] = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return 0
    file_path = str((payload.get("tool_input") or {}).get("file_path", ""))
    if "plans/" not in file_path.replace("\\", "/") or not file_path.endswith(".md"):
        return 0
    root_probe = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False)
    root = root_probe.stdout.strip()
    if not root:
        return 0
    gate = subprocess.run([sys.executable, GATE], capture_output=True, text=True, check=False, cwd=root)
    if gate.returncode == 0:
        return 0
    sys.stderr.write(gate.stdout + gate.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
