# Closed slice charters - assignment_authoring_plan

Append-only. Charters moved verbatim here when their slice was marked
`done` and compacted inline, per `plans/README.md`
`## Charter Tiers And Compaction`.

## 2026-09-08

### Slice 1 - Operator contract, templates, and the profile layer

- Status: done
- Proposed commit message: `Add the assignment authoring contract and style layers`
- Why: the three artifacts and the style layering are the reusable half, and
  every later slice reads them as its contract. Writing them after the probe
  means they encode the shape that survived one real topic rather than the
  assumed one.
- Expected paths: `docs/assignment-authoring.md`,
  `templates/topic-intake.md`, `templates/assignment-formal.md`,
  `templates/student-brief.md`, `templates/case-notes.md`,
  `templates/reviewer-profile.md`, `profiles/default.md`,
  `profiles/README.md`, `src/thesis_review_workflow/metadata.py`,
  `src/thesis_review_workflow/round_scaffolding.py`, `BUILD`, `tests/BUILD`,
  `tests/test_assignment_authoring.py`
- Tasks:
  - `templates/assignment-formal.md`: the FIT IS field set and its order as TWO
    selectable rendering blocks, Czech and English, of which the author keeps
    one. That field set is the only thing the corpus puts into a tracked
    template. A single mixed block was the first review's finding: a filled
    copy has to produce one rendering's exact labels, `Institut:` included.
  - `templates/topic-intake.md`: the variant-independent material authored
    once — motivation, literature, boundary, success-criteria rationale — plus
    the variant list. Two slots the probe forced:
    - a citable-artifact slot whose entries carry an identifier field (DOI,
      arXiv id, ISBN, or URL). The probe could not supply a platform DOI, and
      an agent must not invent an identifier, so an unresolved one is written
      with the marker below and never guessed.
    - an out-of-scope section that can name sibling offered topics. Mutual
      exclusion between simultaneously offered topics is not
      `Depends on topic:` and needs its own slot.
  - `templates/student-brief.md`: a shared body plus a per-variant delta
    section, the shape the assignment already uses for literature. In the
    probe roughly 85% of two briefs for one topic was variant-independent, so
    two whole briefs per topic would drift. The template is the canonical
    per-topic SOURCE at `notes/student_brief.md`, and
    `outputs/student_brief_<variant>.md` is a projection of it — named as such
    in both the template and the doc's layout, because the first review found
    them describing two different shapes. Slice 1 delivers the shape only;
    language binding, the projection command and bundle validation stay in
    Slice 4.
  - One unresolved-metadata marker: the literal token `UNRESOLVED:` in the
    VALUE position, documented in `docs/assignment-authoring.md` as a
    publication blocker with a worked resolved/unresolved example. The rule
    ships as the instrument `thesis_review_workflow.metadata::UNRESOLVED_VALUE_RE`
    behind `thesis_review_workflow.metadata::unresolved_values`, which Slice 3
    consumes instead of re-deriving. Position, not mere presence, because the
    first review found a token-anywhere reading blocking a bundle whose values
    were all resolved: the templates explain the marker in their own prose. The
    probe left the academic year as a marked assumption, which is exactly the
    case that must not reach FIT IS.
  - `docs/assignment-authoring.md`: the operator contract — the intake, the
    variant bundle, and `Depends on topic:` semantics — plus the three-way
    split of success criteria. A criterion lands in an assignment point, in
    the intake as rationale, or in the brief as interpretation; the brief is
    therefore not derived from the assignment, it is where non-formalizable
    criteria live. The probe's enumeration criterion — that a complete and
    justified enumeration, not a zero count, is the success condition — fit
    the intake and the brief and no assignment point.
  - Add the optional `## Assignment Authoring Style` section to
    `templates/reviewer-profile.md` and a generic instance to
    `profiles/default.md`, derived from the cross-supervisor evidence. A
    property attested by one supervisor only is excluded, and absence of the
    section means the generic base applies.
  - The template names supervision conventions — reading order, milestone
    spacing, responsiveness expectations, commit hygiene — as layer 3. They
    must appear in neither `profiles/default.md` nor the intake: the probe
    showed them to be supervisor properties, not topic properties.
  - Layer 2 carries the open-solution-space criterion and its test, because it
    is in direct tension with assessability: a point may leave the solution
    open, and the reviewer must NOT push toward specifying it. What the
    reviewer flags is openness without a criterion the choice can be judged
    against. `Vyberte vhodnou metodu` alone is weak; the same point plus
    stated selection criteria is assessable while staying open.
  - `profiles/README.md`: the line admitting generic assignment-authoring
    preferences, stating there that factual field values are not profile
    content.
  - `templates/case-notes.md`: `Case kind:` with `thesis-review` and
    `topic-proposal`, defaulting to `thesis-review` when absent. The accepted
    values live once in `thesis_review_workflow.metadata::CASE_KINDS` beside
    a `thesis_review_workflow.metadata::case_kind` reader that applies the
    default, so Slices 3 and 5 consume them instead of re-deriving the list.
    No caller changes here.
  - List the three new templates in
    `thesis_review_workflow.round_scaffolding::ON_DEMAND_TEMPLATES`, because a
    topic-proposal case has no review rounds and
    `tests/test_round_scaffolding.py` requires every tracked template to be
    mapped or explicitly on-demand. Expose `docs/assignment-authoring.md` and
    the two tracked `profiles/*.md` to the test sandbox through a root
    `files(name="assignment_authoring_metadata")` target listed file by file,
    so no ignored private profile is globbed in.
  - `tests/test_assignment_authoring.py` reads the tracked templates and
    profile directly, as `tests/test_agent_profile_contracts.py` does: the
    required headings of each new template, the intake's identifier and
    sibling-topic slots, the brief's shared and delta sections, the marker
    token in the templates being the one the doc declares, `CASE_KINDS` with
    the `case_kind` default, and that `profiles/default.md` carries the new
    section including the open-solution-space criterion. Why a test now: the
    previous charter set could have closed on hygiene commands alone.
- Out of scope: skills and roles, the structural checker, the `check_private`
  names, the brief language contract, bundle sendability, promotion, and any
  `case_doctor` or other reader change. No real case content, and no
  supervisor-attributable style, in any tracked path.
- Verification:
  ```bash
  pants test tests::
  python3 tests/test_plan_contract.py
  scripts/check-private
  scripts/check-scripts
  git diff --check
  ```
  The sweep rather than the single target, because a new tracked template is
  checked by `tests/test_round_scaffolding.py` as well.
  Scoped Omen MCP over `src/thesis_review_workflow/metadata.py` during
  implementation, since that is the only Python this slice touches; record the
  observed result or a concrete blocker in `## Progress`.
