"""Metadata parsing helpers for case files and notes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

FIELD_RE = re.compile(r"^\s*([^:\n]+):\s*(.*?)\s*$")
THESIS_LANGUAGE_LABELS = {
    "thesis language",
    "jazyk prace",
    "jazyk práce",
}


@dataclass(frozen=True)
class ThesisLanguageResolution:
    display_language: str
    rule_family: str
    source_path: Path | None
    source_line: int | None
    warnings: tuple[str, ...]


def read_fields(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    if not path.is_file():
        return fields
    for line in path.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip().lower()] = value.strip()
    return fields


def normalize_thesis_language(raw: str) -> str | None:
    value = raw.strip().lower().strip(" .;")
    aliases = {
        "": "auto",
        "auto": "auto",
        "unknown": "auto",
        "neznam": "auto",
        "nevim": "auto",
        "cs": "cs",
        "cz": "cs",
        "czech": "cs",
        "cesky": "cs",
        "česky": "cs",
        "cestina": "cs",
        "čeština": "cs",
        "sk": "sk",
        "slovak": "sk",
        "slovensky": "sk",
        "slovenština": "sk",
        "en": "en",
        "eng": "en",
        "english": "en",
        "anglicky": "en",
        "angličtina": "en",
    }
    return aliases.get(value)


def thesis_language_rule_family(display_language: str) -> str:
    if display_language in {"cs", "sk"}:
        return "cs_sk"
    if display_language == "en":
        return "en"
    return "auto"


def normalized_field_label(label: str) -> str:
    return re.sub(r"\s*\(.*$", "", label.strip().lower()).strip()


def thesis_language_fields(path: Path) -> list[tuple[int, str]]:
    if not path.is_file():
        return []
    fields: list[tuple[int, str]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        match = FIELD_RE.match(line)
        if not match:
            continue
        if normalized_field_label(match.group(1)) in THESIS_LANGUAGE_LABELS:
            fields.append((number, match.group(2).strip()))
    return fields


def resolve_thesis_language(case_dir: Path, round_dir: Path) -> ThesisLanguageResolution:
    """Resolve thesis language from structured metadata only.

    `case.md` is canonical. `notes/round-notes.md` may provide a round-local
    value when `case.md` is absent or explicitly set to `auto`. Free-form intake
    files are intentionally ignored.
    """

    warnings: list[str] = []
    case_path = case_dir / "case.md"
    case_fields = thesis_language_fields(case_path)
    for number, raw_value in case_fields:
        language = normalize_thesis_language(raw_value)
        if language in {"cs", "sk", "en"}:
            return ThesisLanguageResolution(
                language,
                thesis_language_rule_family(language),
                case_path,
                number,
                tuple(warnings),
            )
        if language == "auto":
            round_resolution = resolve_round_thesis_language(round_dir, warnings)
            if round_resolution is not None:
                return round_resolution
            return ThesisLanguageResolution("auto", "auto", case_path, number, tuple(warnings))
        warnings.append(
            "Unsupported thesis language value "
            f"`{raw_value}` in {case_path.as_posix()}:{number}; "
            "expected `cs`, `sk`, `en`, or `auto`, so auto detection was used."
        )
        return ThesisLanguageResolution("auto", "auto", case_path, number, tuple(warnings))

    round_resolution = resolve_round_thesis_language(round_dir, warnings)
    if round_resolution is not None:
        return round_resolution
    return ThesisLanguageResolution("auto", "auto", None, None, tuple(warnings))


def resolve_round_thesis_language(round_dir: Path, warnings: list[str]) -> ThesisLanguageResolution | None:
    path = round_dir / "notes" / "round-notes.md"
    for number, raw_value in thesis_language_fields(path):
        language = normalize_thesis_language(raw_value)
        if language in {"cs", "sk", "en"}:
            return ThesisLanguageResolution(
                language,
                thesis_language_rule_family(language),
                path,
                number,
                tuple(warnings),
            )
        if language == "auto":
            return ThesisLanguageResolution("auto", "auto", path, number, tuple(warnings))
        warnings.append(
            "Unsupported thesis language value "
            f"`{raw_value}` in {path.as_posix()}:{number}; "
            "expected `cs`, `sk`, `en`, or `auto`, so auto detection was used."
        )
        return ThesisLanguageResolution("auto", "auto", path, number, tuple(warnings))
    return None
