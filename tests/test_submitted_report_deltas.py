from thesis_review_workflow.submitted_report_deltas import opponent_public_section_diffs


def test_opponent_public_section_diffs_are_section_scoped_and_normalized() -> None:
    reviewed = """# Návrh

## 9. Celkové hodnocení

Práci doporučuji k obhajobě.

## 10. Otázky k obhajobě

- Co byste ověřil?
"""
    submitted = """# Návrh

## 9. Celkové hodnocení

Práci   doporučuji k obhajobě. IS export obsahuje úpravu.

## 10. Otázky k obhajobě

- Co byste ověřil?
"""

    diffs = opponent_public_section_diffs(reviewed, submitted)

    assert [diff["section"] for diff in diffs] == ["## 9. Celkové hodnocení"]
    assert diffs[0]["normalized_before"] == "Práci doporučuji k obhajobě."
    assert diffs[0]["normalized_after"] == "Práci doporučuji k obhajobě. IS export obsahuje úpravu."
