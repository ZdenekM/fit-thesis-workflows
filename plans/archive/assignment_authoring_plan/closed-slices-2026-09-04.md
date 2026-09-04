# Closed slice charters - assignment_authoring_plan

Append-only. Charters moved verbatim here when their slice was marked
`done` and compacted inline, per `plans/README.md`
`## Charter Tiers And Compaction`.

## 2026-09-04

### Slice 0 - Hand probe

- Status: done
- Proposed commit message: `Record the assignment authoring hand-probe findings`
- Why: it is the cheapest action that produces new information, and it needs no
  template, profile section, or checker to run. Every later slice builds on the
  artifact shape this probe is able to refute.
- Expected paths: `plans/assignment_authoring_plan.md` only. All probe output
  goes to an ignored topic case under `cases/`.
- Tasks:
  - Create an ignored topic case for one real topic and hand-author, with no
    tracked file touched: the intake, one `bp` variant, one `dp` variant of the
    same topic, and a brief for each.
  - The operator chose a NEW topic over a corpus outlier: extending the Mozart
    DOI platform with a new application domain through its documented extension
    seam. The outlier path was not exercised; the real-topic path was.
  - Record in `## Progress` what the exercise refuted: which intake questions
    produced nothing usable, whether the shared/escalation split holds for a
    real BP/DP pair, whether one reviewer role can judge assignment and brief
    together, and what the brief needed that the intake did not capture.
- Out of scope: every tracked template, doc, profile section, skill, checker,
  and CLI. This slice deliberately writes no reusable artifact.
- Verification:
  ```bash
  python3 tests/test_plan_contract.py
  scripts/check-private
  git status --short --untracked-files=all
  tc="$(ls -d cases/topic-* | head -1)"; r="$(cat "$tc/current-round.txt")"
  for f in notes/topic_intake.md outputs/assignment_formal_bp.md \
    outputs/assignment_formal_dp.md outputs/student_brief_bp.md \
    outputs/student_brief_dp.md; do
    test -s "$tc/rounds/$r/$f" || echo "PROBE MISSING: $f"; done
  ```
  `git status` must show no new tracked-path file except the plan, and the
  probe loop must print nothing. Closure also requires an explicit reading of
  `## Progress` confirming each observation in `Tasks:` is recorded; that
  reading is the criterion, not a command.
