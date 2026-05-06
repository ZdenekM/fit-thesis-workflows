from thesis_review_workflow.internal_evidence_validators import PROFILES, validate_artifact_text


def test_code_consistency_accepts_skill_shape_with_anchors() -> None:
    text = "\n".join(
        [
            "# Soulad textu s kodem",
            "",
            "## Rozsah kontroly",
            "Checked `extracted/thesis.txt`, `work/code/project/README.md`, and `work/code/project/src/app.py`.",
            "",
            "## Podporena tvrzeni",
            "- The README describes the import workflow in `work/code/project/README.md`.",
            "",
            "## Nejasna nebo neoverena tvrzeni",
            "| Tvrzeni v textu | Opora v textu | Opora v kodu | Problem |",
            "|---|---|---|---|",
            "| Evaluation accuracy | chapter 4 | `work/code/project/results.csv` | missing calculation path |",
            "",
            "## Reprodukovatelnost",
            "Static review only; no submitted code was executed.",
            "",
            "## Review Status",
            "Reviewed by downstream synthesis for the findings used in opponent materials.",
            "",
            "## Rucni kontroly",
            "- Verify page 42 in the rendered PDF if the exact metric is needed.",
        ]
    )

    result = validate_artifact_text(text, PROFILES["code_consistency"])

    assert result.errors == ()


def test_code_quality_requires_concrete_risk_anchor() -> None:
    text = "\n".join(
        [
            "# Internal Code Quality Review",
            "## Rozsah kontroly",
            "Reviewed `work/code/project/src/app.py`.",
            "## Technicky prehled implementace",
            "Small prototype.",
            "## Hlavni technicka rizika",
            "There are maintainability risks.",
            "## Testy, smoke testy a reprodukovatelnost",
            "No tests were executed.",
            "## README, build a vyvojarska dokumentace",
            "README was inspected.",
            "## Review Status",
            "Reviewed.",
            "## Rucni kontroly",
            "None remain.",
        ]
    )

    result = validate_artifact_text(text, PROFILES["code_quality"])

    assert "required section lacks concrete evidence anchor: ## Hlavni technicka rizika" in result.errors


def test_revision_diff_rejects_placeholders_and_case_workspace_paths() -> None:
    text = "\n".join(
        [
            "# Revision Diff",
            "## Compared Rounds",
            "Compared `outputs/feedback_student.md` against `extracted/thesis.txt`.",
            "## High-Level Progress",
            "TBD",
            "## Previous Feedback Status",
            "`outputs/feedback_student.md` item 1 remains open.",
            "## Thesis Text Changes",
            "Chapter 3 changed.",
            "## Code / Artifact Changes",
            "`inputs/code.zip` changed.",
            "## New Risks",
            "cases/private-case/current-round.txt leaked.",
            "## Review Status",
            "Draft.",
            "## Items Requiring Manual Check",
            "None remain.",
        ]
    )

    result = validate_artifact_text(text, PROFILES["revision_diff"])

    assert any("placeholder" in error for error in result.errors)
    assert any("case workspace path" in error for error in result.errors)
    assert any("draft or pending" in error for error in result.errors)


def test_missing_required_heading_fails() -> None:
    text = "# Revision Diff\n\n## Compared Rounds\n`outputs/feedback_student.md`.\n"

    result = validate_artifact_text(text, PROFILES["revision_diff"])

    assert any("missing required section" in error for error in result.errors)


def test_generic_findings_cannot_satisfy_code_consistency_sections() -> None:
    text = "\n".join(
        [
            "# Code Consistency Review",
            "## Review Scope",
            "Checked `extracted/thesis.txt` and `work/code/project/README.md`.",
            "## Findings",
            "`work/code/project/README.md` supports one implementation claim.",
            "## Reproducibility",
            "Limitation: no submitted code was executed.",
            "## Review Status",
            "Reviewed.",
            "## Manual Checks",
            "None remain.",
        ]
    )

    result = validate_artifact_text(text, PROFILES["code_consistency"])

    assert any("supported or checked claims" in error for error in result.errors)
    assert any("unclear claims or mismatches" in error for error in result.errors)


def test_artifact_must_state_limitations() -> None:
    text = "\n".join(
        [
            "# Internal Code Quality Review",
            "## Rozsah kontroly",
            "Reviewed `work/code/project/src/app.py`.",
            "## Technicky prehled implementace",
            "Small prototype.",
            "## Hlavni technicka rizika",
            "`work/code/project/src/app.py` has a validation risk.",
            "## Testy, smoke testy a reprodukovatelnost",
            "Tests are documented.",
            "## README, build a vyvojarska dokumentace",
            "README was inspected.",
            "## Review Status",
            "Reviewed.",
            "## Rucni kontroly",
            "None remain.",
        ]
    )

    result = validate_artifact_text(text, PROFILES["code_quality"])

    assert "artifact does not state review limitations or that no relevant limitations remain" in result.errors
