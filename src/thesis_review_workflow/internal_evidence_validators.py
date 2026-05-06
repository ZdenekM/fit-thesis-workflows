"""Structural validators for internal opponent evidence artifacts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from thesis_review_workflow.markdown_utils import section_body


@dataclass(frozen=True)
class RequiredSection:
    label: str
    aliases: tuple[str, ...]
    require_anchor: bool = False
    require_status: bool = False


@dataclass(frozen=True)
class ArtifactProfile:
    key: str
    display_name: str
    relative_path: Path
    title_aliases: tuple[str, ...]
    required_sections: tuple[RequiredSection, ...]


@dataclass(frozen=True)
class ValidationResult:
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.errors


ACCENT_TRANS = str.maketrans(
    "ěščřžýáíéúůňťďóĚŠČŘŽÝÁÍÉÚŮŇŤĎÓ",
    "escrzyaieuuntdoESCRZYAIEUUNTDO",
)
PLACEHOLDER_PATTERNS = (
    r"\bTODO\b",
    r"\bTBD\b",
    r"\bFIXME\b",
    r"\bYYYY-MM-DD\b",
    r"\blorem ipsum\b",
    r"\[\[[^\]]+\]\]",
)
ANGLE_PLACEHOLDER_RE = re.compile(r"<([^>\n]+)>")
AUTOLINK_RE = re.compile(
    r"(?:https?://|mailto:)[^\s<>]+|[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+",
    re.IGNORECASE,
)
ABSOLUTE_POSIX_PATH_RE = re.compile(r"(?<!\w)/(?:home|Users|tmp|var|workspace|mnt)/[^\s)]*")
ABSOLUTE_WINDOWS_PATH_RE = re.compile(r"\b[A-Za-z]:\\[^\s)]*")
CASE_PATH_RE = re.compile(r"(?<!\w)cases/[A-Za-z0-9_.-]+(?:/[^\s)]*)?")
CONCRETE_ANCHOR_RE = re.compile(
    r"("
    r"`[^`\n]{2,}`|"
    r"\b(?:notes|inputs|extracted|work|outputs)/[A-Za-z0-9_./-]+|"
    r"\b[A-Za-z0-9_.-]+\."
    r"(?:py|md|toml|json|jsonl|ya?ml|txt|pdf|zip|csv|ipynb|tex|bib|xml|js|ts|java|cs|cpp|h|sql)\b|"
    r"\b(?:README|pyproject\.toml|requirements\.txt|package\.json|pom\.xml|pytest|unittest|mvn|npm|git|"
    r"commit|sha256)\b|"
    r"\b(?:page|strana|chapter|kapitola|section|sekce|line|radek|radka|PR|pull request)\s*[#:]?\s*\d+"
    r")",
    re.IGNORECASE,
)
STATUS_RE = re.compile(
    r"\b("
    r"reviewed|approved|passed|"
    r"covered by downstream synthesis|downstream synthesis|independent review|"
    r"exception|manual check|unavailable|not available|n/a|"
    r"revidovano|schvaleno|vyjimka|vyjimkou|rucni kontrola"
    r")\b",
    re.IGNORECASE,
)
PENDING_STATUS_RE = re.compile(
    r"\b(draft|not reviewed|pending review|needs review|requires review|review required|vyzaduje revizi)\b",
    re.IGNORECASE,
)
LIMITATION_RE = re.compile(
    r"\b("
    r"limitation|limitations|limit|limited|"
    r"omezen[aiyeo]?|omezeni|limit[uy]?|"
    r"not verified|not checked|not executed|no submitted code was executed|"
    r"neoveren[ao]?|neprover[ei]n[ao]?|nespusten[ao]?|"
    r"manual check|rucni kontrol|requires manual|verify|overit|overeni"
    r")\b",
    re.IGNORECASE,
)


CODE_CONSISTENCY_PROFILE = ArtifactProfile(
    key="code_consistency",
    display_name="code consistency review",
    relative_path=Path("outputs/code_consistency.md"),
    title_aliases=(
        "Soulad textu s kodem",
        "Code Consistency Review",
        "Text-Code Consistency Review",
    ),
    required_sections=(
        RequiredSection("review scope", ("Rozsah kontroly", "Review Scope"), require_anchor=True),
        RequiredSection("supported or checked claims", ("Podporena tvrzeni", "Supported Claims", "Checked Claims")),
        RequiredSection(
            "unclear claims or mismatches",
            (
                "Nejasna nebo neoverena tvrzeni",
                "Mozne rozpory textu a kodu",
                "Unclear Claims",
                "Mismatches",
            ),
            require_anchor=True,
        ),
        RequiredSection("reproducibility", ("Reprodukovatelnost", "Reproducibility")),
        RequiredSection("review status", ("Review Status", "Stav revize"), require_status=True),
        RequiredSection("manual checks", ("Rucni kontroly", "Manual Checks", "Items Requiring Manual Check")),
    ),
)

CODE_QUALITY_PROFILE = ArtifactProfile(
    key="code_quality",
    display_name="code quality review",
    relative_path=Path("outputs/code_quality_review.md"),
    title_aliases=(
        "Internal Code Quality Review",
        "Code Quality Review",
    ),
    required_sections=(
        RequiredSection("review scope", ("Rozsah kontroly", "Review Scope"), require_anchor=True),
        RequiredSection("technical overview", ("Technicky prehled implementace", "Technical Overview")),
        RequiredSection(
            "main technical risks",
            ("Hlavni technicka rizika", "Main Technical Risks", "Technical Risks"),
            require_anchor=True,
        ),
        RequiredSection(
            "tests and reproducibility",
            ("Testy, smoke testy a reprodukovatelnost", "Tests And Reproducibility"),
        ),
        RequiredSection(
            "developer documentation",
            ("README, build a vyvojarska dokumentace", "README / Build / Developer Documentation"),
        ),
        RequiredSection("review status", ("Review Status", "Stav revize"), require_status=True),
        RequiredSection("manual checks", ("Rucni kontroly", "Manual Checks", "Items Requiring Manual Check")),
    ),
)

REVISION_DIFF_PROFILE = ArtifactProfile(
    key="revision_diff",
    display_name="revision diff",
    relative_path=Path("outputs/revision_diff.md"),
    title_aliases=("Revision Diff",),
    required_sections=(
        RequiredSection("compared rounds", ("Compared Rounds", "Porovnane verze"), require_anchor=True),
        RequiredSection("high-level progress", ("High-Level Progress", "High Level Progress")),
        RequiredSection(
            "previous feedback status",
            ("Previous Feedback Status", "Stav predchozi zpetne vazby"),
            require_anchor=True,
        ),
        RequiredSection("thesis text changes", ("Thesis Text Changes", "Zmeny textu prace")),
        RequiredSection("code or artifact changes", ("Code / Artifact Changes", "Code Artifact Changes")),
        RequiredSection("new risks", ("New Risks", "Nova rizika")),
        RequiredSection("review status", ("Review Status", "Stav revize"), require_status=True),
        RequiredSection(
            "manual checks",
            ("Items Requiring Manual Check", "Manual Checks", "Rucni kontroly"),
        ),
    ),
)

PROFILES = {
    CODE_CONSISTENCY_PROFILE.key: CODE_CONSISTENCY_PROFILE,
    CODE_QUALITY_PROFILE.key: CODE_QUALITY_PROFILE,
    REVISION_DIFF_PROFILE.key: REVISION_DIFF_PROFILE,
}


def normalize_heading(value: str) -> str:
    value = re.sub(r"^#{1,6}\s+", "", value.strip())
    value = re.sub(r"`([^`]*)`", r"\1", value)
    value = value.translate(ACCENT_TRANS).lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def heading_titles(lines: list[str], *, level: int) -> list[str]:
    prefix = "#" * level + " "
    return [line.removeprefix(prefix).strip() for line in lines if line.startswith(prefix)]


def section_body_by_alias(lines: list[str], aliases: tuple[str, ...]) -> tuple[str | None, list[str]]:
    normalized_aliases = {normalize_heading(alias) for alias in aliases}
    for title in heading_titles(lines, level=2):
        if normalize_heading(title) not in normalized_aliases:
            continue
        body = section_body(lines, f"## {title}")
        return title, body or []
    return None, []


def has_concrete_anchor(value: str) -> bool:
    return bool(CONCRETE_ANCHOR_RE.search(value))


def nonempty_section(body: list[str]) -> bool:
    text = "\n".join(body).strip()
    if not text:
        return False
    return any(line.strip() and not re.fullmatch(r"[\s|:-]+", line) for line in body)


def check_title(profile: ArtifactProfile, lines: list[str], errors: list[str]) -> None:
    present = {normalize_heading(title) for title in heading_titles(lines, level=1)}
    expected = {normalize_heading(title) for title in profile.title_aliases}
    if not present.intersection(expected):
        aliases = ", ".join(profile.title_aliases)
        errors.append(f"missing expected H1 title for {profile.display_name}: {aliases}")


def check_required_sections(profile: ArtifactProfile, lines: list[str], errors: list[str], warnings: list[str]) -> None:
    for required in profile.required_sections:
        title, body = section_body_by_alias(lines, required.aliases)
        if title is None:
            aliases = ", ".join(required.aliases)
            errors.append(f"missing required section for {required.label}: {aliases}")
            continue
        if not nonempty_section(body):
            errors.append(f"empty required section: ## {title}")
            continue

        text = "\n".join(body)
        if required.require_anchor and not has_concrete_anchor(text):
            errors.append(f"required section lacks concrete evidence anchor: ## {title}")
        if required.require_status and not STATUS_RE.search(text):
            errors.append(f"review status is not explicit in section: ## {title}")
        if required.require_status and PENDING_STATUS_RE.search(text):
            errors.append(f"review status still indicates draft or pending review: ## {title}")
        if len(text.strip()) < 25:
            warnings.append(f"very short section may be too thin: ## {title}")


def check_text_hygiene(text: str, errors: list[str]) -> None:
    for pattern in PLACEHOLDER_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE):
            errors.append(f"leftover placeholder/template text matching: {pattern}")
    for match in ANGLE_PLACEHOLDER_RE.finditer(text):
        value = match.group(1).strip()
        if not AUTOLINK_RE.fullmatch(value):
            errors.append("leftover angle-bracket placeholder/template text")
            break
    if ABSOLUTE_POSIX_PATH_RE.search(text):
        errors.append("artifact contains an absolute POSIX filesystem path")
    if ABSOLUTE_WINDOWS_PATH_RE.search(text):
        errors.append("artifact contains an absolute Windows filesystem path")
    if CASE_PATH_RE.search(text):
        errors.append("artifact contains an exact case workspace path; use round-relative paths instead")


def validate_artifact_text(text: str, profile: ArtifactProfile) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    lines = text.splitlines()

    check_title(profile, lines, errors)
    check_required_sections(profile, lines, errors, warnings)
    check_text_hygiene(text, errors)
    if not has_concrete_anchor(text):
        errors.append("artifact contains no concrete evidence anchors")
    if not LIMITATION_RE.search(text):
        errors.append("artifact does not state review limitations or that no relevant limitations remain")

    return ValidationResult(tuple(errors), tuple(warnings))


def validate_artifact_path(path: Path, profile: ArtifactProfile) -> ValidationResult:
    if not path.is_file():
        return ValidationResult((f"missing artifact: {profile.relative_path.as_posix()}",), ())
    return validate_artifact_text(path.read_text(encoding="utf-8", errors="replace"), profile)
