"""Validate the structural half of an authored topic assignment bundle."""

from __future__ import annotations

import argparse
from pathlib import Path

from thesis_review_workflow.assignment_draft import (
    VARIANT_RE,
    BriefLanguage,
    brief_language,
    forbidden_headings_in,
    assignment_findings,
    brief_findings,
    citable_artifacts,
    declared_variants,
    read_text,
    repeated_headings_in,
    supplement_line,
    unresolved_findings,
)
from thesis_review_workflow.cli.check_feedback_language import report_missing
from thesis_review_workflow.cli.context import repo_root, require_case_dir, validate_id
from thesis_review_workflow.metadata import case_kind, read_fields
from thesis_review_workflow.paths import rel_repo

INTAKE_REL = Path("notes/topic_intake.md")
BRIEF_SOURCE_REL = Path("notes/student_brief.md")


def assignment_rel(variant: str) -> Path:
    return Path(f"outputs/assignment_formal_{variant}.md")


def brief_rel(variant: str) -> Path:
    return Path(f"outputs/student_brief_{variant}.md")


def language_findings(label: str, text: str, language: BriefLanguage, variant: str | None) -> list[str]:
    """The three rules `scripts/check-feedback-language` applies, plus heading uniqueness.

    `report_missing` is reused for the required set. The forbidden side cannot
    be: it matches heading BASES so that any variant suffix is caught, which an
    exact-list reporter cannot express.

    The uniqueness rule is here rather than beside the projection comparison
    because only the SOURCE lacked one. A projection is compared whole against
    its canonical shape, so a doubled body there already fails; the source has
    no canonical form, and `existing` below is a set, so a source carrying its
    body twice passed every rule and then projected cleanly.
    """

    required = language.source_headings() if variant is None else language.projection_headings(variant)
    existing = {line.strip() for line in text.splitlines() if line.strip().startswith("#")}
    errors: list[str] = []
    report_missing(f"{label}: missing headings for the case feedback language:", list(required), existing, errors)
    offending = forbidden_headings_in(text, language, variant)
    if offending:
        errors.append(f"{label}: headings of the wrong language or spelling:")
        errors.extend(f"- {heading}" for heading in offending)
    repeated = repeated_headings_in(text, required)
    if repeated:
        errors.append(
            f"{label}: required heading occurs more than once; the section readers take the first "
            "and the duplicate goes unchecked:"
        )
        errors.extend(f"- {heading}" for heading in repeated)
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scripts/check-assignment-draft",
        description="Validate the structure of a topic-proposal case's assignment variants and briefs.",
    )
    parser.add_argument("case_id")
    parser.add_argument("variant", nargs="?", help="Check one variant; default is every variant the intake lists.")
    return parser


def check_case(case_dir: Path, requested: str | None) -> tuple[list[str], list[str]]:
    """Return (findings, checked variants)."""

    kind = case_kind(read_fields(case_dir / "case.md"))
    if kind is None:
        return ([f"`Case kind:` in {case_dir.name}/case.md is not a known kind"], [])
    if kind != "topic-proposal":
        return (
            [
                f"`Case kind: {kind}` — assignment authoring runs only in a `topic-proposal` case; "
                "see docs/assignment-authoring.md"
            ],
            [],
        )

    language = brief_language(read_fields(case_dir / "case.md"))
    if language is None:
        return (
            [
                "`Student feedback language:` in case.md is not a supported value; "
                "expected `cs` or `en` (see AGENTS.md `## Output Conventions`)"
            ],
            [],
        )

    intake = read_text(case_dir / INTAKE_REL)
    if not intake:
        return ([f"missing {INTAKE_REL.as_posix()}; author the topic intake first"], [])

    findings = unresolved_findings(INTAKE_REL.as_posix(), intake)
    artifacts = citable_artifacts(intake)
    supplement = supplement_line(intake)
    variants = declared_variants(intake)
    if not variants:
        return (findings + [f"{INTAKE_REL.as_posix()} declares no `Variants:`"], [])
    # A variant becomes a filename segment, so it is validated rather than trusted.
    unsafe = [variant for variant in variants if not VARIANT_RE.match(variant)]
    if unsafe:
        return (findings + [f"unusable variant identifier(s) in {INTAKE_REL.as_posix()}: {', '.join(unsafe)}"], [])

    if requested is not None:
        if requested not in variants:
            return (
                findings + [f"variant `{requested}` is not declared in {INTAKE_REL.as_posix()} (`{'/'.join(variants)}`)"],
                [],
            )
        checked = [requested]
    else:
        checked = variants

    brief_source = read_text(case_dir / BRIEF_SOURCE_REL)
    if brief_source:
        findings.extend(unresolved_findings(BRIEF_SOURCE_REL.as_posix(), brief_source))
        findings.extend(
            language_findings(BRIEF_SOURCE_REL.as_posix(), brief_source, language, None)
        )
    else:
        findings.append(f"missing {BRIEF_SOURCE_REL.as_posix()}; the brief source is authored once per topic")

    for variant in checked:
        rel = assignment_rel(variant)
        assignment = read_text(case_dir / rel)
        if not assignment:
            findings.append(f"missing {rel.as_posix()}")
        else:
            findings.extend(unresolved_findings(rel.as_posix(), assignment))
            findings.extend(
                f"{rel.as_posix()}: {finding}"
                for finding in assignment_findings(assignment, variant, artifacts, supplement)
            )

        projection_rel = brief_rel(variant)
        projection = read_text(case_dir / projection_rel)
        if not projection:
            findings.append(f"missing {projection_rel.as_posix()}")
        elif brief_source:
            findings.extend(unresolved_findings(projection_rel.as_posix(), projection))
            findings.extend(
                language_findings(projection_rel.as_posix(), projection, language, variant)
            )
            findings.extend(
                f"{projection_rel.as_posix()}: {finding}"
                for finding in brief_findings(brief_source, projection, variant, language)
            )

    # No separate cross-variant equality check: every literature bullet must equal an intake
    # entry exactly, so two variants citing one entry necessarily cite it identically. Requiring
    # identical MEMBERSHIP instead would reject a DP that legitimately cites one more work.
    return (findings, checked)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    validate_id("CASE_ID", args.case_id)
    root = repo_root()
    case_dir = require_case_dir(root, args.case_id)

    findings, checked = check_case(case_dir, args.variant)
    print(f"Topic case: {rel_repo(root, case_dir)}")
    if checked:
        print(f"Variants checked: {', '.join(checked)}")
    if findings:
        for finding in findings:
            print(f"ERROR: {finding}")
        print(
            "Structural checks failed. Assessability, criterion quality and wording stay with "
            ".agents/skills/thesis-assignment-review/SKILL.md; this command only decides what needs no judgment."
        )
        return 1
    print("Assignment draft structural check passed")
    return 0


def console_main() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(console_main())
