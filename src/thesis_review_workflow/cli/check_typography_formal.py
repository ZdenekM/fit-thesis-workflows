"""Flag typography and formal-presentation issues for late thesis review.

This helper is a reviewer prompt, not a proofreader. It reads the rendered PDF
text extract as the source of truth, uses LaTeX sources only for repair hints,
and prints grouped warnings with representative examples instead of a full
student-facing checklist.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from thesis_review_workflow.markdown_utils import markdown_section
from thesis_review_workflow.metadata import resolve_thesis_language, thesis_language_rule_family
from thesis_review_workflow.paths import rel_repo

ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
CZECH_SHORT_LINE_RE = re.compile(r"(?i)(?:^|\s)([aikosuvz])\s*$")
SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+[.,;:!?](?!\d)")
MISSING_SPACE_AFTER_PUNCT_RE = re.compile(r"(?:[;:!?]|,(?!\d))(?=[^\s\])}\"'.,;:!?])")
MISSING_SPACE_AFTER_PERIOD_RE = re.compile(
    r"(?<!\b[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ])(?<!Ph)(?<!ph)(?<!Ing)(?<!ing)(?<!doc)(?<!Doc)" r"\.(?=[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ])"
)
SPACE_AFTER_OPEN_BRACKET_RE = re.compile(r"[\[(]\s+")
SPACE_BEFORE_CLOSE_BRACKET_RE = re.compile(r"\s+[\])]")
MISSING_SPACE_BEFORE_OPEN_PAREN_RE = re.compile(r"[A-Za-zÀ-ž0-9][(]")
RANGE_HYPHEN_RE = re.compile(r"\b\d+\s+-\s+\d+\b|\b\d+-\d+\b")
TEXT_DASH_HYPHEN_RE = re.compile(r"[A-Za-zÀ-ž][ \t]+-[ \t]+[A-Za-zÀ-ž]")
PLACEHOLDER_RE = re.compile(
    r"(\[\[[^\]]+\]\]|\\todo\{[^}]*\}|\bTODO\b|\bTBD\b|\bxxx\b|\blorem ipsum\b)",
    re.IGNORECASE,
)
STRAIGHT_DOUBLE_QUOTE_RE = re.compile(r'"')
CZECH_OPEN_QUOTE_RE = re.compile(r"„")
ENGLISH_DOUBLE_QUOTE_RE = re.compile(r"[“”]")
URL_OR_EMAIL_RE = re.compile(r"(?:https?://|mailto:)|[^@\s]+@[^@\s]+\.[^@\s]+", re.IGNORECASE)
LATEX_SHORT_SPACE_RE = re.compile(r"(?i)(?<![\\\w])([aikosuvz]) (?=[A-Za-zÀ-ž])")
LATEX_COMMAND_RE = re.compile(r"\\[A-Za-z@]+")
LATEX_DOCUMENTCLASS_RE = re.compile(r"\\documentclass(?:\[[^\]]*\])?\{[^}]+\}")
LATEX_INPUT_RE = re.compile(r"\\(?:input|include)\{([^}]+)\}")

CZECH_HINT_RE = re.compile(
    r"\b("
    r"prace|práce|kapitola|kapitoly|řešení|reseni|cil|cíl|cílem|"
    r"zadani|zadání|vysledk\w*|výsledk\w*|implementace|navrh|návrh|"
    r"testovani|testování|tato|tento|ktere|které|protoze|protože|"
    r"student|vedouci|vedoucí"
    r")\b",
    re.IGNORECASE,
)
ENGLISH_HINT_RE = re.compile(
    r"\b("
    r"thesis|chapter|implementation|results?|evaluation|method|methods|"
    r"this|that|with|from|student|supervisor|assignment|conclusion|"
    r"experiment|experiments|design|testing"
    r")\b",
    re.IGNORECASE,
)
CZECH_DIACRITICS_RE = re.compile(r"[áčďéěíňóřšťúůýžÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ]")
NON_THESIS_EXTRACT_RE = re.compile(
    r"(zadani|zadání|assignment|reviewer|posudek|oponent|opponent|feedback|zpetna|zpětn[áa])",
    re.IGNORECASE,
)
ARTIFACT_REQUIRED_HEADINGS = (
    "Review Scope",
    "Thesis Language",
    "Deterministic Checker Findings",
    "Source-Level Hints",
    "Student-Facing Synthesis",
    "Downstream Use",
    "Review Status",
    "Manual Checks",
)
ARTIFACT_STATUS_OK_RE = re.compile(
    r"\b(approved|reviewed|review passed|revidov[aá]no|schv[aá]len[oa]?|"
    r"exception|v[yý]jimk|unavailable|not available|not applicable|n/a)\b",
    re.IGNORECASE,
)
ARTIFACT_STATUS_PENDING_RE = re.compile(
    r"\b(still required|needs review|pending review|not yet reviewed|" r"review is required|review required)\b",
    re.IGNORECASE,
)
ARTIFACT_LOCATION_RE = re.compile(
    r"(?:cases/[^\s:]+/rounds/[^\s:]+/[^\s:]+:\d+|" r"(?:extracted|work/thesis-source)/[^\s:]+:\d+)"
)


@dataclass(frozen=True)
class SourceLine:
    path: Path
    number: int
    text: str


def usage() -> str:
    return "Usage: scripts/check-typography-formal [--require-output] CASE_ID [ROUND_ID]"


def repo_root() -> Path:
    output = subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return Path(output.strip())


def die_usage(message: str) -> None:
    print(message, file=sys.stderr)
    print(usage(), file=sys.stderr)
    raise SystemExit(2)


def validate_id(label: str, value: str) -> None:
    if not ID_RE.fullmatch(value):
        die_usage(f"Invalid {label}. Use only letters, numbers, dot, underscore, and dash.")


def resolve_round(root: Path, case_id: str, round_id: str | None) -> Path:
    case_dir = root / "cases" / case_id
    if not case_dir.is_dir():
        die_usage(f"Case not found: {case_id}")

    if round_id is None:
        current_round = case_dir / "current-round.txt"
        if not current_round.is_file():
            die_usage("ROUND_ID not provided and current-round.txt is missing")
        round_id = current_round.read_text(encoding="utf-8").strip()

    validate_id("round id", round_id)
    round_dir = case_dir / "rounds" / round_id
    if not round_dir.is_dir():
        die_usage(f"Round not found: {round_id}")
    return round_dir


def rel(path: Path, root: Path) -> str:
    return rel_repo(root, path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def read_lines(paths: list[Path]) -> list[SourceLine]:
    lines: list[SourceLine] = []
    for path in paths:
        for number, text in enumerate(read_text(path).splitlines(), start=1):
            lines.append(SourceLine(path=path, number=number, text=text.rstrip("\n")))
    return lines


def thesis_text_paths(round_dir: Path) -> list[Path]:
    extracted = round_dir / "extracted"
    if not extracted.is_dir():
        return []
    candidates = sorted(path for path in extracted.rglob("*") if path.is_file() and path.suffix.lower() == ".txt")
    return [path for path in candidates if not NON_THESIS_EXTRACT_RE.search(path.name)]


def latex_source_paths(round_dir: Path) -> list[Path]:
    source_base = round_dir / "work" / "thesis-source"
    if not source_base.is_dir():
        return []
    ignored_parts = {".git", "node_modules", "target", "build", ".cache"}
    return sorted(
        path
        for path in source_base.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".tex", ".sty", ".cls", ".bib", ".mk", ".latexmkrc"}
        and not any(part in ignored_parts for part in path.parts)
    )


def strip_latex_comment(line: str) -> str:
    escaped = False
    result: list[str] = []
    for char in line:
        if char == "%" and not escaped:
            break
        result.append(char)
        escaped = char == "\\" and not escaped
        if char != "\\":
            escaped = False
    return "".join(result)


def resolve_latex_reference(base: Path, reference: str) -> Path | None:
    raw = base / reference
    candidates = [raw]
    if raw.suffix == "":
        candidates.append(raw.with_suffix(".tex"))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def effective_latex_source_paths(round_dir: Path) -> list[Path]:
    """Return likely student-authored source files used by the root document."""

    all_tex = [path for path in latex_source_paths(round_dir) if path.suffix.lower() == ".tex"]
    root_docs = []
    for path in all_tex:
        uncommented = "\n".join(strip_latex_comment(line) for line in read_text(path).splitlines())
        if LATEX_DOCUMENTCLASS_RE.search(uncommented):
            root_docs.append(path)
    if not root_docs:
        return all_tex

    selected: set[Path] = set()
    pending = list(root_docs)
    while pending:
        path = pending.pop()
        if path in selected:
            continue
        selected.add(path)
        for line in read_text(path).splitlines():
            uncommented = strip_latex_comment(line)
            for match in LATEX_INPUT_RE.finditer(uncommented):
                referenced = resolve_latex_reference(path.parent, match.group(1).strip())
                if referenced is not None and referenced.suffix.lower() == ".tex":
                    pending.append(referenced)

    return sorted(selected)


def likely_build_files(round_dir: Path) -> list[Path]:
    source_base = round_dir / "work" / "thesis-source"
    if not source_base.is_dir():
        return []
    names = {"makefile", "latexmkrc", ".latexmkrc"}
    return sorted(
        path
        for path in source_base.rglob("*")
        if path.is_file() and (path.name.lower() in names or path.suffix.lower() in {".mk", ".sh"})
    )


def detect_language(text: str, configured: str) -> tuple[str, str, str]:
    if configured in {"cs", "sk", "en"}:
        return configured, thesis_language_rule_family(configured), "metadata"

    czech_score = len(CZECH_HINT_RE.findall(text)) + len(CZECH_DIACRITICS_RE.findall(text)) * 3
    english_score = len(ENGLISH_HINT_RE.findall(text))
    if czech_score >= max(6, english_score * 2):
        return "cs", "cs_sk", "auto"
    if english_score >= max(6, czech_score * 2):
        return "en", "en", "auto"
    return "cs", "cs_sk", "auto-default"


def should_skip_line(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    if URL_OR_EMAIL_RE.search(stripped):
        return True
    if re.search(r"(?:\.\s+){4,}\d+\s*$", stripped):
        return True
    if re.fullmatch(r"[\d\s.:-]+", stripped):
        return True
    return False


def sample(lines: list[SourceLine], root: Path, limit: int = 5) -> str:
    values = []
    for item in lines[:limit]:
        text = item.text.strip()
        if len(text) > 120:
            text = text[:117] + "..."
        values.append(f"{rel(item.path, root)}:{item.number}: {text}")
    return "; ".join(values)


def collect_line_pattern(
    lines: list[SourceLine],
    pattern: re.Pattern[str],
    *,
    skip_short: bool = False,
) -> list[SourceLine]:
    matches: list[SourceLine] = []
    for item in lines:
        if should_skip_line(item.text):
            continue
        if skip_short and len(item.text.strip()) < 20:
            continue
        if pattern.search(item.text):
            matches.append(item)
    return matches


def source_line_is_probably_text(text: str) -> bool:
    stripped = strip_latex_comment(text).strip()
    if not stripped or stripped.startswith("%"):
        return False
    if stripped.startswith("\\"):
        return False
    if re.match(r"^[A-Za-z0-9_.-]+(?:\.[A-Za-z]+)?\s*=", stripped):
        return False
    if "$" in stripped or "\\begin{" in stripped or "\\end{" in stripped:
        return False
    return True


def collect_latex_short_space(lines: list[SourceLine]) -> list[SourceLine]:
    matches: list[SourceLine] = []
    for item in lines:
        if not source_line_is_probably_text(item.text):
            continue
        if LATEX_SHORT_SPACE_RE.search(strip_latex_comment(item.text)):
            matches.append(item)
    return matches


def quote_style_examples(lines: list[SourceLine]) -> dict[str, list[SourceLine]]:
    styles: dict[str, list[SourceLine]] = {}
    for item in lines:
        if should_skip_line(item.text):
            continue
        if STRAIGHT_DOUBLE_QUOTE_RE.search(item.text):
            styles.setdefault("straight double quotes", []).append(item)
        if CZECH_OPEN_QUOTE_RE.search(item.text):
            styles.setdefault("Czech curly double quotes", []).append(item)
        elif ENGLISH_DOUBLE_QUOTE_RE.search(item.text):
            styles.setdefault("English curly double quotes", []).append(item)
    return styles


def print_warning(
    warnings: list[str],
    category: str,
    message: str,
    examples: list[SourceLine],
    root: Path,
) -> None:
    suffix = ""
    if examples:
        suffix = f" Examples: {sample(examples, root)}"
    warnings.append(f"WARNING [{category}]: {message}{suffix}")


def artifact_warnings(round_dir: Path, require_output: bool) -> tuple[list[str], bool]:
    artifact = round_dir / "outputs" / "typography_formal_review.md"
    if not artifact.is_file():
        if not require_output:
            return [], False
        return [
            "ERROR [output-artifact]: outputs/typography_formal_review.md is missing; "
            "write or review the internal typography/formal artifact before relying on it."
        ], True

    text = read_text(artifact)
    messages: list[str] = []
    failed = False
    for heading in ARTIFACT_REQUIRED_HEADINGS:
        if not re.search(rf"(?m)^##\s+{re.escape(heading)}\s*$", text):
            prefix = "ERROR" if require_output else "WARNING"
            messages.append(
                f"{prefix} [output-artifact]: outputs/typography_formal_review.md "
                f"is missing required heading `## {heading}`."
            )
            failed = failed or require_output
            continue
        if require_output and not markdown_section(text, heading).strip():
            messages.append(
                "ERROR [output-artifact]: outputs/typography_formal_review.md "
                f"has an empty required section `## {heading}`."
            )
            failed = True

    if require_output:
        status = markdown_section(text, "Review Status")
        if status.strip():
            if ARTIFACT_STATUS_PENDING_RE.search(status):
                messages.append(
                    "ERROR [output-artifact]: `## Review Status` says independent "
                    "review is still pending; record an approval or explicit exception "
                    "before relying on this artifact."
                )
                failed = True
            elif not ARTIFACT_STATUS_OK_RE.search(status):
                messages.append(
                    "ERROR [output-artifact]: `## Review Status` does not contain "
                    "a recognizable review verdict or explicit exception."
                )
                failed = True

    synthesis = markdown_section(text, "Student-Facing Synthesis")
    if synthesis:
        location_count = len(ARTIFACT_LOCATION_RE.findall(synthesis))
        if location_count > 2:
            prefix = "ERROR" if require_output else "WARNING"
            messages.append(
                f"{prefix} [output-artifact]: `Student-Facing Synthesis` contains "
                f"{location_count} line-level location(s); keep student guidance as "
                "a repeated pattern and repair workflow, not an audit list."
            )
            failed = failed or require_output
    return messages, failed


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[1] in {"-h", "--help"}:
        print(usage())
        return 0

    args = argv[1:]
    require_output = False
    if args and args[0] == "--require-output":
        require_output = True
        args = args[1:]
    if any(arg.startswith("-") for arg in args):
        die_usage("Unknown option.")
    if len(args) not in {1, 2}:
        die_usage("Expected CASE_ID and optional ROUND_ID.")

    case_id = args[0]
    validate_id("case id", case_id)
    round_id = args[1] if len(args) == 2 else None
    if round_id is not None:
        validate_id("round id", round_id)

    root = repo_root()
    round_dir = resolve_round(root, case_id, round_id)
    case_dir = round_dir.parents[1]
    source_paths = thesis_text_paths(round_dir)
    if not source_paths:
        print(
            "ERROR: no extracted thesis text was found; typography/formal checks use "
            "the submitted PDF text extract as the rendered source of truth.",
            file=sys.stderr,
        )
        return 1

    lines = read_lines(source_paths)
    all_text = "\n".join(item.text for item in lines)
    configured = resolve_thesis_language(case_dir, round_dir)
    display_language, rule_family, language_source = detect_language(all_text, configured.display_language)
    if configured.source_path is None:
        configured_source = "default"
    else:
        configured_source = rel(configured.source_path, root)
        if configured.source_line is not None:
            configured_source += f":{configured.source_line}"
    print(
        f"Thesis language: {display_language} "
        f"({language_source}; configured={configured.display_language} from {configured_source}; "
        f"rules={rule_family})"
    )

    warnings: list[str] = [f"WARNING [language-metadata]: {warning}" for warning in configured.warnings]
    if rule_family == "cs_sk":
        short_line_matches = collect_line_pattern(lines, CZECH_SHORT_LINE_RE)
        if short_line_matches:
            print_warning(
                warnings,
                "cs-line-breaks",
                (
                    f"Czech/Slovak one-letter words appear at rendered line ends "
                    f"{len(short_line_matches)} time(s). Use nonbreaking spaces, "
                    "usually by running `vlna`, and manually check the rendered PDF."
                ),
                short_line_matches,
                root,
            )

    spacing_checks = [
        (
            "space-before-punctuation",
            SPACE_BEFORE_PUNCT_RE,
            "Suspicious spaces before punctuation appear {count} time(s).",
        ),
        (
            "missing-space-after-punctuation",
            MISSING_SPACE_AFTER_PUNCT_RE,
            "Suspicious missing spaces after punctuation appear {count} time(s).",
        ),
        (
            "missing-space-after-period",
            MISSING_SPACE_AFTER_PERIOD_RE,
            "Suspicious missing spaces after sentence periods appear {count} time(s).",
        ),
        (
            "bracket-spacing",
            SPACE_AFTER_OPEN_BRACKET_RE,
            "Suspicious spaces after opening brackets appear {count} time(s).",
        ),
        (
            "bracket-spacing",
            SPACE_BEFORE_CLOSE_BRACKET_RE,
            "Suspicious spaces before closing brackets appear {count} time(s).",
        ),
        (
            "missing-space-before-parenthesis",
            MISSING_SPACE_BEFORE_OPEN_PAREN_RE,
            "Suspicious missing spaces before opening parentheses appear {count} time(s).",
        ),
        (
            "dash-hyphen",
            RANGE_HYPHEN_RE,
            "Numeric ranges with plain hyphen appear {count} time(s); "
            "check whether an en dash or LaTeX `--` is intended.",
        ),
        (
            "dash-hyphen",
            TEXT_DASH_HYPHEN_RE,
            "Text dashes written as plain hyphen appear {count} time(s); check typographic dash usage.",
        ),
        (
            "leftover-placeholders",
            PLACEHOLDER_RE,
            "Template/TODO placeholders appear {count} time(s); "
            "in near-final/final review these should be removed or explained.",
        ),
    ]
    for category, pattern, message in spacing_checks:
        matches = collect_line_pattern(lines, pattern, skip_short=category == "missing-space-before-parenthesis")
        if not matches:
            continue
        print_warning(
            warnings,
            category,
            message.format(count=len(matches)),
            matches,
            root,
        )

    quote_styles = quote_style_examples(lines)
    if len(quote_styles) > 1:
        examples = [items[0] for items in quote_styles.values() if items]
        print_warning(
            warnings,
            "quote-consistency",
            (
                "Multiple double-quote styles appear in the rendered text "
                f"({', '.join(sorted(quote_styles))}); check consistency for the thesis language."
            ),
            examples,
            root,
        )

    latex_paths = effective_latex_source_paths(round_dir)
    if latex_paths and rule_family == "cs_sk":
        latex_lines = read_lines(latex_paths)
        source_short_matches = collect_latex_short_space(latex_lines)
        if source_short_matches:
            print_warning(
                warnings,
                "cs-latex-nonbreaking-space",
                (
                    f"LaTeX sources contain possible missing `~` after short Czech/Slovak "
                    f"words {len(source_short_matches)} time(s). Prefer running `vlna` "
                    "or fixing nonbreaking spaces, then verify the rendered PDF."
                ),
                source_short_matches,
                root,
            )

        build_files = likely_build_files(round_dir)
        vlna_files = [
            path
            for path in build_files + latex_paths
            if "vlna" in read_text(path).lower() or "vlna" in path.name.lower()
        ]
        if build_files and not vlna_files:
            print_warning(
                warnings,
                "cs-latex-vlna",
                (
                    "LaTeX source/build files are present, but no obvious `vlna` "
                    "invocation was found. If this uses the FIT template, verify "
                    "whether the student's build actually runs `vlna`."
                ),
                [],
                root,
            )
        elif vlna_files:
            print(
                "LaTeX source hint: found `vlna` reference in " + ", ".join(rel(path, root) for path in vlna_files[:5])
            )

    if rule_family == "en":
        print(
            "English typography mode: Czech `vlna` line-break rules are not applied; "
            "use editor/Overleaf spell and grammar tooling plus manual final proofread."
        )

    artifact_messages, artifact_failed = artifact_warnings(round_dir, require_output)
    warnings.extend(artifact_messages)

    if warnings:
        for warning in warnings:
            print(warning)
        if artifact_failed:
            print("Typography/formal check failed because --require-output found an invalid output artifact.")
            return 1
        print(f"Typography/formal check completed with {len(warnings)} warning(s).")
    else:
        print("Typography/formal check passed.")
    return 0


def console_main() -> int:
    return main(sys.argv)


if __name__ == "__main__":
    raise SystemExit(console_main())
