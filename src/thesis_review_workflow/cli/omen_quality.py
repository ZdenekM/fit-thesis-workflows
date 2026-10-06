"""Run Omen over the workflow code with a validated scope and a compact, ratcheted report.

Dev-only (`pants run scripts:omen`); never part of the thesis case pipeline. The runner
exists because raw `omen` output proved easy to misread here:

- A run that analyses zero files looks like a clean result. The Omen MCP server did
  exactly that for this repository (empty payloads for a non-empty root), so an empty
  file-level payload is a FAILURE here, never a pass.
- Private case data must never be analysed. `omen.toml` excludes `cases/**`, and every
  path in every payload is checked against that boundary on our side as well. `churn`
  reads git history and ignores `exclude`, so it can name a tracked public file under
  `cases/`; only the paths `check_private.allowed_sensitive_tracked` allows pass.
- `omen.toml` keys that look right can be ignored: `exclude_patterns`, `[churn] since`
  and `top`, and `[hotspot] top` all had no effect on omen 4.24.2. The churn window is
  therefore passed as `--days` here.
- Some analyzers measure nothing for this code and still print a number. Measured on
  omen 4.24.2 (2026-10-06): `deadcode` reported 0 items with all 3443 definitions
  "reachable" (no Python call graph; `pants run :vulture` is the dead-code authority),
  and `smells` saw 0 import edges between 217 components, so its zero and the score's
  coupling/smells components are not evidence. Both stay out of the default set, and the
  report labels the score components that rest on an empty graph.
- `.claude/hooks` and `.codex/hooks` are hidden directories Omen skips; their Python is
  not covered.

Pattern adapted from shaas-suite `research/brick_smr/scripts/omen_quality.py`.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from thesis_review_workflow.cli.check_private import allowed_sensitive_tracked

DEFAULT_ANALYZERS = ("score", "complexity", "clones", "satd", "tdg", "hotspot")
SUPPORTED_ANALYZERS = DEFAULT_ANALYZERS + ("churn",)
# Where each analyzer reports how many files it analysed. Zero means Omen looked at the
# wrong root or excluded everything, not that the code is clean. `hotspot` and `churn`
# are history-based: an empty window is possible and is reported, not failed.
FILE_COUNTS = {
    "score": ("summary", "files_analyzed"),
    "complexity": ("summary", "total_files"),
    "clones": ("total_files_scanned",),
    "tdg": ("total_files",),
}
PRIVATE_PREFIXES = ("cases/", "dist/")
PATH_KEYS = {"file", "file_a", "file_b", "file_path", "path", "relative_path"}
PATH_LIST_KEYS = {"hotspot_files", "stable_files"}
CHURN_DAYS = 180
OMEN_CONFIG = "omen.toml"
OMEN_TIMEOUT_SECONDS = 600
TOP = 5


@dataclass(frozen=True)
class Threshold:
    """A ratchet on one summarized metric: the code may not get worse than this."""

    analyzer: str
    field: str
    limit: float
    direction: str  # "min": value >= limit; "max": value <= limit
    rationale: str

    def holds(self, value: float) -> bool:
        return value >= self.limit if self.direction == "min" else value <= self.limit

    def describe(self) -> str:
        return f"{self.analyzer}.{self.field} {'>=' if self.direction == 'min' else '<='} {self.limit}"


# Ratchets, not aspirations: each sits a small step beyond the value measured on
# 2026-10-06 with omen 4.24.2 at 4922837. Lower a max / raise a min when the code improves;
# loosening one needs a recorded reason in docs/dev-hygiene.md.
THRESHOLDS = (
    Threshold("score", "overall_score", 88.0, "min", "measured 90.14-90.17"),
    Threshold("complexity", "max_cyclomatic", 85, "max", "measured 81; the worst function may not get worse"),
    Threshold("complexity", "p90_cyclomatic", 9, "max", "measured 8"),
    Threshold("clones", "duplication_ratio", 0.115, "max", "measured 0.102"),
    Threshold("tdg", "average_score", 88.0, "min", "measured 89.75"),
)


class OmenRunError(Exception):
    """Omen could not produce trustworthy evidence for the requested scope."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pants run scripts:omen --",
        description="Dev-only Omen health report over the workflow code, with scope validation and ratchets.",
    )
    parser.add_argument(
        "analyzers",
        nargs="*",
        metavar="ANALYZER",
        help=f"subset to run, from: {' '.join(SUPPORTED_ANALYZERS)} (default: {' '.join(DEFAULT_ANALYZERS)})",
    )
    parser.add_argument(
        "--focus",
        action="append",
        default=[],
        metavar="PATH",
        help="also list per-function complexity for this repo-relative file (repeatable); "
        "a path Omen did not analyse is an error",
    )
    return parser


def repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise OmenRunError("not inside a git checkout; run from the repository")
    return Path(result.stdout.strip())


def omen_binary(root: Path) -> str:
    candidates = [os.environ.get("OMEN_BIN"), shutil.which("omen")]
    candidates += [str(root / ".pants.d/dev-tools/omen/bin" / name) for name in ("omen", "omen.exe")]
    for candidate in candidates:
        if candidate and (shutil.which(candidate) or Path(candidate).is_file()):
            return candidate
    raise OmenRunError(
        "omen not found. Install it on PATH, set OMEN_BIN, or install it into "
        ".pants.d/dev-tools/omen/bin/; see docs/dev-hygiene.md"
    )


def run_analyzer(binary: str, root: Path, analyzer: str) -> dict[str, Any]:
    command = [binary, "-c", OMEN_CONFIG, "-p", ".", "-f", "json", analyzer]
    if analyzer == "churn":
        command += ["--days", str(CHURN_DAYS)]
    try:
        result = subprocess.run(
            command,
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=OMEN_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise OmenRunError(f"omen {analyzer} failed to run: {exc}") from exc
    if result.returncode != 0:
        raise OmenRunError(f"omen {analyzer} exited {result.returncode}: {result.stderr.strip()[:500]}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise OmenRunError(f"omen {analyzer} did not return JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise OmenRunError(f"omen {analyzer} returned {type(payload).__name__}, not an object")
    return payload


def payload_paths(value: Any) -> set[str]:
    """Every repo-relative path named anywhere in a payload, normalised without `./`."""
    found: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key in PATH_KEYS and isinstance(item, str):
                found.add(item.removeprefix("./"))
            if key in PATH_LIST_KEYS and isinstance(item, list):
                found |= {entry.removeprefix("./") for entry in item if isinstance(entry, str)}
            found |= payload_paths(item)
    elif isinstance(value, list):
        for item in value:
            found |= payload_paths(item)
    return found


def file_count(analyzer: str, payload: dict[str, Any]) -> Any:
    value: Any = payload
    for key in FILE_COUNTS[analyzer]:
        value = value.get(key) if isinstance(value, dict) else None
    return value


def scope_errors(analyzer: str, payload: dict[str, Any]) -> list[str]:
    errors = [
        f"{analyzer}: analysed a private or build path: {path}"
        for path in sorted(payload_paths(payload))
        if path.startswith(PRIVATE_PREFIXES) and not allowed_sensitive_tracked(path)
    ]
    if analyzer in FILE_COUNTS and not file_count(analyzer, payload):
        errors.append(
            f"{analyzer}: zero files analysed; a path-handling failure, not a clean result "
            f"(check `{OMEN_CONFIG}` excludes and the working directory)"
        )
    return errors


def summarize(analyzer: str, payload: dict[str, Any]) -> dict[str, Any]:
    """The few numbers per analyzer the report and the ratchets use."""
    summary = payload.get("summary") or {}
    if analyzer == "score":
        return {"overall_score": payload.get("overall_score"), "grade": payload.get("grade")}
    if analyzer == "complexity":
        return {key: summary.get(key) for key in ("total_files", "max_cyclomatic", "p90_cyclomatic", "max_cognitive")}
    if analyzer == "clones":
        return {"duplication_ratio": summary.get("duplication_ratio"), "total_groups": summary.get("total_groups")}
    if analyzer == "satd":
        severities: dict[str, int] = {}
        for item in payload.get("items", []):
            severity = str(item.get("severity", "unclassified"))
            severities[severity] = severities.get(severity, 0) + 1
        return {"total_items": summary.get("total_items"), "by_severity": severities}
    if analyzer == "tdg":
        return {"average_score": payload.get("average_score"), "average_grade": payload.get("average_grade")}
    if analyzer == "hotspot":
        return {key: summary.get(key) for key in ("total_hotspots", "critical_count", "high_count")}
    return {"files": len(payload.get("files") or []), "period_days": payload.get("period_days")}


def evaluate_thresholds(summaries: dict[str, dict[str, Any]]) -> list[tuple[Threshold, float | None, bool]]:
    results = []
    for threshold in THRESHOLDS:
        if threshold.analyzer not in summaries:
            continue
        value = summaries[threshold.analyzer].get(threshold.field)
        ok = isinstance(value, (int, float)) and threshold.holds(float(value))
        results.append((threshold, value if isinstance(value, (int, float)) else None, ok))
    return results


def unmeasured_score_components(payload: dict[str, Any]) -> list[str]:
    """Score components Omen computed from an empty import graph (Python here)."""
    components = payload.get("components") or {}
    coupling = str((components.get("coupling") or {}).get("details", ""))
    if "avg degree: 0.0" in coupling:
        return [name for name in ("coupling", "smells") if name in components]
    return []


def top_lines(analyzer: str, payload: dict[str, Any]) -> list[str]:
    if analyzer == "complexity":
        functions = [
            (
                fn.get("metrics", {}).get("cyclomatic", 0),
                fn.get("metrics", {}).get("cognitive", 0),
                f["path"],
                fn["name"],
            )
            for f in payload.get("files", [])
            for fn in f.get("functions", [])
        ]
        return [
            f"  {cyc:>3} cyc {cog:>3} cog  {path.removeprefix('./')}::{name}"
            for cyc, cog, path, name in sorted(functions, reverse=True)[:TOP]
        ]
    if analyzer == "hotspot":
        return [
            f"  {item['score']:.2f} {item['severity']:<8} {item['file']}" for item in payload.get("hotspots", [])[:TOP]
        ]
    if analyzer == "clones":
        hotspots = payload.get("summary", {}).get("hotspots", [])
        return [f"  {item['duplicate_lines']:>4} dup lines  {item['file']}" for item in hotspots[:TOP]]
    if analyzer == "tdg":
        files = sorted(payload.get("files", []), key=lambda f: f.get("total", 100.0))
        return [f"  {f.get('grade', '?'):<7} {f['file_path'].removeprefix('./')}" for f in files[:TOP]]
    if analyzer == "satd":
        items = payload.get("items", [])[:TOP]
        return [f"  {i['severity']:<8} {i['file'].removeprefix('./')}:{i['line']} {i['marker']}" for i in items]
    return []


def focus_lines(payload: dict[str, Any], focus: list[str]) -> tuple[list[str], list[str]]:
    """Per-function complexity for the focus files, and errors for files Omen did not analyse."""
    by_path = {f["path"].removeprefix("./"): f for f in payload.get("files", [])}
    lines: list[str] = []
    errors: list[str] = []
    for path in focus:
        record = by_path.get(path.removeprefix("./"))
        if record is None:
            errors.append(
                f"--focus {path}: not in the complexity payload (excluded, hidden, or not a supported language)"
            )
            continue
        lines.append(f"  {path}")
        for fn in sorted(record.get("functions", []), key=lambda f: -f.get("metrics", {}).get("cyclomatic", 0)):
            metrics = fn.get("metrics", {})
            lines.append(
                f"    {metrics.get('cyclomatic', 0):>3} cyc {metrics.get('cognitive', 0):>3} cog  {fn['name']}"
            )
    return lines, errors


def rounded(summary: dict[str, Any]) -> dict[str, Any]:
    return {key: round(value, 3) if isinstance(value, float) else value for key, value in summary.items()}


def print_sections(payloads: dict[str, dict[str, Any]], summaries: dict[str, dict[str, Any]]) -> None:
    for name, payload in payloads.items():
        print(f"## {name}: {json.dumps(rounded(summaries[name]), ensure_ascii=False)}")
        if name == "score":
            for component in unmeasured_score_components(payload):
                print(f"  NOT MEASURED: score component `{component}` rests on an empty import graph")
        lines = top_lines(name, payload)
        if name in ("hotspot", "churn") and not (payload.get("hotspots") or payload.get("files")):
            lines = ["  no files changed in the history window; not a quality signal"]
        for line in lines:
            print(line)


def print_focus(payloads: dict[str, dict[str, Any]], focus: list[str]) -> list[str]:
    if "complexity" not in payloads:
        return ["--focus needs the complexity analyzer"]
    print("## focus")
    lines, errors = focus_lines(payloads["complexity"], focus)
    for line in lines:
        print(line)
    return errors


def print_ratchets(summaries: dict[str, dict[str, Any]]) -> list[str]:
    print("## ratchets")
    failures = []
    for threshold, value, ok in evaluate_thresholds(summaries):
        shown = round(value, 3) if isinstance(value, float) else value
        print(f"  {'PASS' if ok else 'FAIL'} {threshold.describe()} (value {shown}; {threshold.rationale})")
        if not ok:
            failures.append(f"ratchet failed: {threshold.describe()} (value {shown})")
    return failures


def report(payloads: dict[str, dict[str, Any]], focus: list[str]) -> int:
    summaries = {name: summarize(name, payload) for name, payload in payloads.items()}
    print_sections(payloads, summaries)
    failures = print_focus(payloads, focus) if focus else []
    failures += print_ratchets(summaries)
    for failure in failures:
        print(f"ERROR: {failure}", file=sys.stderr)
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_intermixed_args(argv[1:])
    unknown = sorted(set(args.analyzers) - set(SUPPORTED_ANALYZERS))
    if unknown:
        parser.error(f"unsupported analyzer(s): {', '.join(unknown)}")
    analyzers = tuple(dict.fromkeys(args.analyzers)) or DEFAULT_ANALYZERS
    if args.focus and "complexity" not in analyzers:
        analyzers = ("complexity", *analyzers)
    try:
        root = repo_root()
        binary = omen_binary(root)
        payloads: dict[str, dict[str, Any]] = {}
        errors: list[str] = []
        for analyzer in analyzers:
            payloads[analyzer] = run_analyzer(binary, root, analyzer)
            errors.extend(scope_errors(analyzer, payloads[analyzer]))
    except OmenRunError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print("ERROR: Omen evidence is not trustworthy for this scope; no report printed.", file=sys.stderr)
        return 1
    return report(payloads, args.focus)


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
