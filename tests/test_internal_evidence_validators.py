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
            "## Synthesis Handoff",
            "- Workflow/audience: supervisor_feedback and opponent_materials.",
            "- Use in synthesis: cite `work/code/project/README.md` for the import claim.",
            "- Do not overstate: do not claim runtime behavior was verified.",
            "- P0/P1 anchors: `work/code/project/results.csv` and chapter 4.",
            "- Limitations/manual checks: no submitted code was executed; verify page 42 if needed.",
            "- Calibration: final-submission check; keep as report-confidence limitation.",
            "- Supervisor action / opponent impact: ask for calculation path or carry a cautious report limitation.",
            "",
            "## Rucni kontroly",
            "- Verify page 42 in the rendered PDF if the exact metric is needed.",
        ]
    )

    result = validate_artifact_text(text, PROFILES["code_consistency"])

    assert result.errors == ()

    synthesis_result = validate_artifact_text(
        text,
        PROFILES["code_consistency"],
        require_synthesis_handoff=True,
    )
    assert synthesis_result.errors == ()


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


def test_missing_synthesis_handoff_warns_or_fails_only_when_requested() -> None:
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
            "Limitation: no tests were executed.",
            "## README, build a vyvojarska dokumentace",
            "README was inspected.",
            "## Review Status",
            "Reviewed.",
            "## Rucni kontroly",
            "None remain.",
        ]
    )

    standalone = validate_artifact_text(text, PROFILES["code_quality"])
    warning = validate_artifact_text(text, PROFILES["code_quality"], warn_synthesis_handoff=True)
    required = validate_artifact_text(text, PROFILES["code_quality"], require_synthesis_handoff=True)

    assert not any("synthesis handoff" in error for error in standalone.errors)
    assert any("missing synthesis handoff" in item for item in warning.warnings)
    assert "missing synthesis handoff section: Synthesis Handoff" in required.errors


def test_blank_synthesis_handoff_template_fails_when_required_and_warns_when_advisory() -> None:
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
            "Limitation: no tests were executed.",
            "## README, build a vyvojarska dokumentace",
            "README was inspected.",
            "## Review Status",
            "Reviewed.",
            "## Synthesis Handoff",
            "- Workflow/audience:",
            "- Use in synthesis:",
            "- Do not overstate:",
            "- P0/P1 anchors:",
            "- Limitations/manual checks:",
            "- Calibration:",
            "- Supervisor action / opponent impact:",
            "`work/code/project/src/app.py`",
            "## Rucni kontroly",
            "None remain.",
        ]
    )

    required = validate_artifact_text(text, PROFILES["code_quality"], require_synthesis_handoff=True)
    warning = validate_artifact_text(text, PROFILES["code_quality"], warn_synthesis_handoff=True)

    assert "empty synthesis handoff field: workflow/audience" in required.errors
    assert "empty synthesis handoff field: p0/p1 anchors" in required.errors
    assert any("student action or opponent impact" in error for error in required.errors)
    assert warning.errors == ()
    assert any("empty synthesis handoff field: workflow/audience" in item for item in warning.warnings)


def test_label_as_value_synthesis_handoff_template_fails() -> None:
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
            "Limitation: no tests were executed.",
            "## README, build a vyvojarska dokumentace",
            "README was inspected.",
            "## Review Status",
            "Reviewed.",
            "## Synthesis Handoff",
            "- Workflow/audience: workflow/audience",
            "- Use in synthesis: use in synthesis",
            "- Do not overstate: do not overstate",
            "- P0/P1 anchors: `work/code/project/src/app.py`",
            "- Limitations/manual checks: limitations/manual checks",
            "- Calibration: calibration",
            "- Supervisor action / opponent impact: supervisor action / opponent impact",
            "## Rucni kontroly",
            "None remain.",
        ]
    )

    result = validate_artifact_text(text, PROFILES["code_quality"], require_synthesis_handoff=True)

    assert "placeholder synthesis handoff field value: workflow/audience" in result.errors
    assert "placeholder synthesis handoff field value: use in synthesis" in result.errors
    assert "placeholder synthesis handoff field value: calibration" in result.errors
    assert "placeholder synthesis handoff field value: supervisor action / opponent impact" in result.errors


def test_synthesis_handoff_requires_synthesis_contract_fields() -> None:
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
            "Limitation: no tests were executed.",
            "## README, build a vyvojarska dokumentace",
            "README was inspected.",
            "## Review Status",
            "Reviewed.",
            "## Synthesis Handoff",
            "This mentions `work/code/project/src/app.py` but omits synthesis guidance.",
            "## Rucni kontroly",
            "None remain.",
        ]
    )

    result = validate_artifact_text(text, PROFILES["code_quality"], require_synthesis_handoff=True)

    assert "missing synthesis handoff field: workflow/audience" in result.errors
    assert "missing synthesis handoff field: do not overstate" in result.errors
    assert "missing synthesis handoff field: supervisor action / opponent impact" in result.errors
    assert "missing synthesis handoff field: calibration" in result.errors
