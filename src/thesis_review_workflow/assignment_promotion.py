"""Turn an approved assignment variant into a thesis case's assignment context.

Promotion is the moment a topic proposal becomes the artifact every other
workflow measures a thesis against, so it is guarded on four independent axes:
the bundle is approved, the operator asserts the assignment was ISSUED to this
student, the target is the right kind of case for this variant, and every write
lands inside the private case root.

Approval and issuance are different facts. `scripts/check-assignment-bundle`
establishes that a variant may be published; nothing in a bundle establishes
that a student received it, and `check_round_ready` reads section content and
cannot tell the difference. Promoting on approval alone would grade a student
against requirements they never got.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from thesis_review_workflow.assignment_bundle import approval_rel
from thesis_review_workflow.assignment_draft import RENDERINGS, read_text
from thesis_review_workflow.markdown_utils import section_body, section_text
from thesis_review_workflow.metadata import case_kind, read_fields

ASSIGNMENT_REL = Path("notes/assignment.md")
RETAINED_APPROVAL_DIR = Path("work/assignment_source")

WORK_TYPE_BY_VARIANT = {"bp": "BP", "dp": "DP"}
"""Which `Work type` a variant may be promoted into. `unknown` is never one of them."""

HEADING_RE = re.compile(r"^(#{1,6})(\s+)")


def retained_approval_rel(topic_case_id: str, variant: str) -> Path:
    return RETAINED_APPROVAL_DIR / f"{topic_case_id}__{variant}__approval.json"


@dataclass(frozen=True)
class PromotionTarget:
    case_dir: Path
    round_dir: Path
    round_id: str


def private_root_errors(root: Path, case_dir: Path) -> list[str]:
    """The resolved case must sit under the resolved `cases/` root, which must sit in the repo.

    Confining writes to the resolved CASE is one level too low: a `cases/<id>`
    that links to `docs/<id>` carries valid metadata and a real round, so every
    other check passes while private content lands where `.gitignore` does not
    cover it.
    """

    errors: list[str] = []
    cases_root = (root / "cases").resolve()
    # Not merely "inside the repository": a `cases/` linked to `docs/` resolves inside the repo
    # and every descendant check then passes while `.gitignore`'s lexical `/cases/*` covers none
    # of it. The root must BE the private root.
    if cases_root != root.resolve() / "cases":
        return [
            f"the private case root is redirected: cases/ resolves to {cases_root}; "
            "promotion refuses to write private content through it"
        ]
    resolved = case_dir.resolve()
    try:
        resolved.relative_to(cases_root)
    except ValueError:
        errors.append(
            f"{case_dir.name} resolves to {resolved}, outside the private case root {cases_root}; "
            "promotion refuses to write private content there"
        )
    return errors


def contained_write_errors(case_dir: Path, targets: list[Path]) -> list[str]:
    """Every destination must resolve beneath the case, whether or not it exists yet.

    Resolving only an existing path missed the dangling symlink: a
    `notes/assignment.md` linking to a file that does not exist yet reports
    `exists()` false, so an earlier version checked its parent and then wrote
    straight through the link.
    """

    resolved_case = case_dir.resolve()
    errors: list[str] = []
    for target in targets:
        try:
            target.resolve(strict=False).relative_to(resolved_case)
        except ValueError:
            errors.append(f"write target escapes the target case: {target}")
    return errors


def target_errors(root: Path, case_dir: Path, case_id: str, variant: str) -> list[str]:
    errors = private_root_errors(root, case_dir)
    if errors:
        return errors
    fields = read_fields(case_dir / "case.md")
    kind = case_kind(fields)
    if kind != "thesis-review":
        errors.append(f"{case_id} is `Case kind: {kind or '(unknown value)'}`; promote into a thesis-review case")
    expected = WORK_TYPE_BY_VARIANT.get(variant)
    actual = fields.get("work type", "").strip()
    if expected is None:
        errors.append(f"variant `{variant}` has no known work type; extend WORK_TYPE_BY_VARIANT first")
    elif actual.upper() != expected:
        errors.append(
            f"{case_id} has `Work type: {actual or '(missing)'}` but variant `{variant}` is a {expected}; "
            "set the work type before promoting, since promotion is when it is knowable"
        )
    return errors


def demote_headings(text: str, levels: int = 2) -> str:
    """Push every heading down so a copied section cannot end its container.

    The brief projection carries an H2, and `check_round_ready` ends a section
    at the next H2, so a verbatim copy would cut
    `## Private Assignment Notes For Student` in half.
    """

    out: list[str] = []
    for line in text.splitlines():
        match = HEADING_RE.match(line)
        if match:
            depth = min(len(match.group(1)) + levels, 6)
            out.append("#" * depth + match.group(2) + line[match.end() :])
        else:
            out.append(line)
    return "\n".join(out)


def formal_text(assignment: str) -> str:
    """Points, literature and the semestral requirement.

    The semestral-defence requirement is a distinct formal field, and a mapping
    that carries only points and literature drops a real obligation.
    """

    lines = assignment.splitlines()
    rendering = next((item for item in RENDERINGS.values() if item.heading in assignment), None)
    if rendering is None:
        return ""
    block = section_body(lines, rendering.heading, stop_pattern=r"^#{1,2}\s+") or []
    parts = []
    for heading in ("### Assignment Points", "### Literature", "### Semestral Defence Requirement"):
        body = section_text(block, heading, stop_pattern=r"^#{1,3}\s+")
        if body:
            parts.append(demote_headings(body))
    return "\n\n".join(parts).strip()


def render_assignment_context(
    *,
    topic_case_id: str,
    variant: str,
    approval_sha256: str,
    retained_rel: Path,
    assignment: str,
    brief: str,
    issued_by: str,
    issued_note: str,
) -> str:
    return f"""# Assignment Context

Assignment source: topic={topic_case_id} variant={variant} approval_sha256={approval_sha256}
Assignment source record: {retained_rel.as_posix()}
Assignment issued: {issued_note} (asserted by {issued_by})

## Formal Assignment Artifacts

- Promoted from topic case `{topic_case_id}`, variant `{variant}`, approved in
  `{approval_rel(variant)}` and retained at `{retained_rel.as_posix()}`.

## Formal Assignment Text Or Summary

{formal_text(assignment)}

## Private Assignment Notes For Student

{demote_headings(brief).strip()}

## Assignment Coverage Hints

-
"""


def read_bundle(topic_case_dir: Path, variant: str) -> tuple[str, str]:
    assignment = read_text(topic_case_dir / f"outputs/assignment_formal_{variant}.md")
    brief = read_text(topic_case_dir / f"outputs/student_brief_{variant}.md")
    return assignment, brief
