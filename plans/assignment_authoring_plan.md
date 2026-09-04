# Assignment Authoring Plan

Status: in_progress
Created: 2026-09-03

## Start Here

State: Slice 0 is done — the hand probe ran on a real topic and its eight
findings are in `## Progress`. Four of them change what Slices 1, 3 and 4 must
build. No tracked template, profile section, or code exists yet.

Next action: write the full Slice 1 charter, folding in the four probe findings
that change it — shared-plus-delta briefs, the citable-artifact intake slot, the
three-way split of success criteria, and supervision conventions belonging to
profile layer 3 — then review that charter before implementing it.

Do not read: the calibration corpus, the review transcripts, or the probe
artifacts; their conclusions are in `## Progress` and `## Decision Log`.

## Goal

Let a supervisor take an unstructured topic idea and leave with one shared
topic intake plus, for every variant they choose to publish, a reviewed bundle
of a formal assignment publishable to FIT IS and a starting brief sendable to
the student.

The assignment is the artifact every other workflow in this repository measures
a thesis against — `scripts/check-assignment-coverage`, supervisor feedback,
opponent materials, and the `Rozsah splneni pozadavku zadani` rubric item in
`docs/fit-is-rubric.md` all resolve against `notes/assignment.md`. So the
governing review criterion for a newly authored assignment is: could this
repository's own opponent pipeline evaluate a finished thesis against it. An
assignment point that is not verifiable returns a year later as an ungradable
fulfillment claim.

### The variant bundle

A topic carries N assignment variants (`bp`, `dp`). The variant is a
first-class identifier everywhere, not a filename suffix: each variant has its
own assignment draft and output, its own brief, its own approval record binding
every file and hash in that bundle, and its own promotion. `Assignment source:`
on a realized case names topic id, variant, and source hash. Shared material —
motivation, literature — is authored once in the intake and must appear
byte-identically in every variant that uses it.

### Three style layers

The workflow must work for a supervisor other than the operator, so it carries
three layers and only the first is fixed:

1. **School form** — the FIT IS field set and its order, in both its Czech and
   English rendering. Not a preference; tracked in
   `templates/assignment-formal.md`.
2. **Generic quality base** — tracked in `profiles/default.md` under a new
   `## Assignment Authoring Style` section, derived from what the
   cross-supervisor corpus shows to be institutional norm plus documented FIT
   rules. Never from one supervisor alone.
3. **Personal style** — ignored `profiles/local/<profile-id>.md`, same section:
   wording, literature-entry conventions, semester-requirement phrasing, BP/DP
   variant construction, preferred categories.

Factual field VALUES — institute, head of institute, supervisor identity — are
not style and must not live in a profile, because `profiles/README.md` makes a
profile a preference layer with no factual authority. They come from explicit
operator metadata.

Non-goal: automating topic invention. Phase 1 is a supervisor interview whose
output the supervisor owns.

## Audit Base

Current relevant state:

- `templates/assignment.md` treats the assignment strictly as an INPUT: formal
  artifacts, formal text, private notes, coverage hints. Nothing in the tree
  authors an assignment.
- The calibration corpus fixes the formal field set, the recurring point
  skeleton, which properties are institutional norm versus personal style, and
  the fact that point count does not separate BP from DP. Details in the
  calibration case's `work/assignment_style_calibration.md`; do not restate
  them here.
- `check_reviewer_profile.py` composes `profiles/default.md` followed by the
  selected local refinement and enforces no section schema, so a new section
  needs no validator change and no new configuration surface.
- The skill/role registry contract is wider than one registry entry. Beyond
  `thesis_review_workflow.agent_profiles::AGENT_PROFILE_ROUTES` and
  `docs/agent-profile-matrix.md`, the tests in
  `tests/test_agent_profile_contracts.py` bind `.codex/config.toml`, a Codex
  agent TOML, a byte-equal `.agents/roles/<role>.md` fragment, the
  `.claude/agents/` adapter, and `.claude/hooks/reviewer_write_policy.json`.
- `check_assignment_coverage` validates `work/assignment_coverage_agent.json`
  for an existing thesis. It cannot judge whether a newly authored point is
  assessable, so no gate may claim it does.
- `check_private` matches generated artifact names through an explicit
  filename pattern. It does not yet know `topic_intake`, `assignment_formal`,
  or `student_brief`.
- `case_doctor` runs round, supervisor and deadline readiness gates
  unconditionally, so a topic-proposal case would fail thesis-review gates.
- `AGENTS.md` forbids free-text heuristics as gates but permits bounded
  structural parsing of known labels, headings, placeholders, and privacy leak
  checks. Every deterministic check here stays inside that fence.
- `plans/case_format_migration_contract_plan.md` owns the case-layout contract
  and a planned format detector. This plan adds one `case.md` field and must not
  open a second layout contract beside it.

Context reads and checks used when creating this plan:

```bash
cat templates/assignment.md templates/case-notes.md profiles/README.md
sed -n '1,60p' docs/agent-profile-matrix.md
rg -n "codex/config.toml|agents/roles|reviewer_write_policy" tests/test_agent_profile_contracts.py
rg -n -A12 "PRIVATE_MARKDOWN_RE *=" src/thesis_review_workflow/cli/check_private.py
scripts/agent-review --staged --profile plan-critic
```

## Scope

In scope:

- `templates/topic-intake.md`, `templates/assignment-formal.md`,
  `templates/student-brief.md`
- an optional `## Assignment Authoring Style` section in
  `templates/reviewer-profile.md` and `profiles/default.md`, plus the
  `profiles/README.md` line that admits it
- `.agents/skills/thesis-assignment-authoring/SKILL.md`,
  `.agents/skills/thesis-assignment-review/SKILL.md` and the full registry
  surface those two directories oblige
- `docs/assignment-authoring.md` for the operator contract
- `Case kind:` in `templates/case-notes.md` and its readers
- a structural checker, a sendability check, and a promotion command, each with
  the full command surface and tests
- the new generated names in `check_private`
- skill routing lines in `AGENTS.md`, and `README.md` operator entry text

Out of scope:

- a second data layout beside `cases/`
- semantic scoring of topic quality, novelty, or difficulty by deterministic
  code
- retrospective learning from finished theses back into assignment authoring
- changing any existing readiness gate; the authoring workflow calls neither
  `scripts/check-supervisor-ready` nor `scripts/check-round-ready`, and
  `case_doctor` gains a branch rather than a modified gate

## Acceptance Contract

Publishing an assignment variant to FIT IS and sending its brief to a student
are both outward-facing and binding, and either can happen first. Before
EITHER, for the variant in question:

- `scripts/check-assignment-bundle <case-id> <variant> [round-id]`, delivered
  by Slice 4, passes: it validates every file and hash in that variant's
  bundle, and that its approval record names a reviewer distinct from the
  author;
- an explicit operator reading over the retained `notes/topic_intake.md`, the
  selected `outputs/assignment_formal_<variant>.md`, and its matching brief:
  feasible for the stated work type, every named resource dependency actually
  available, and every assignment point assessable.

Privacy and repository hygiene are deterministic and stay in slice
verification, not in this contract.

## Slices

### Slice 0 - Hand probe

Charter form: compacted
Landed: e402e78
Hand-authored one real topic end to end in an ignored topic case — intake, `bp`
and `dp` assignment variants, a brief per variant — touching no tracked path,
and recorded eight findings in `## Progress`.
Full charter: `plans/archive/assignment_authoring_plan/closed-slices-2026-09-04.md`.
Decisions: `2026-09-03 - Slice 0 shrinks to the hand probe`,
`2026-09-03 - A topic carries N assignment variants`.

### Slice 1 - Operator contract, templates, and the profile layer

- Status: planned
- Proposed commit message: `Add the assignment authoring contract and style layers`
- Why: the three artifacts and the style layering are the reusable half, and
  every later slice reads them as its contract. Writing them after the probe
  means they encode what worked rather than what was assumed.
- Expected paths: `docs/assignment-authoring.md`,
  `templates/topic-intake.md`, `templates/assignment-formal.md`,
  `templates/student-brief.md`, `templates/case-notes.md`,
  `templates/reviewer-profile.md`, `profiles/default.md`,
  `profiles/README.md`, `tests/test_assignment_authoring.py`
- Tasks:
  - Write the three templates. Only the field set and its order, in both
    language renderings, come from the corpus into
    `templates/assignment-formal.md`.
  - Add the optional `## Assignment Authoring Style` section to
    `templates/reviewer-profile.md` and a generic instance to
    `profiles/default.md`, derived from the cross-supervisor evidence. A
    property attested by one supervisor only is excluded. Absence of the
    section means the generic base applies.
  - Add the `profiles/README.md` line admitting generic assignment-authoring
    preferences, and state there that factual field values are not profile
    content.
  - Add `Case kind:` to `templates/case-notes.md`, defaulting to
    `thesis-review` when absent, and document the variant and `Depends on
    topic:` semantics in `docs/assignment-authoring.md`.
  - Deliver `tests/test_assignment_authoring.py` over synthetic fixtures:
    required template headings, accepted `Case kind` values, and that the
    default profile carries the new section. Why a test now: the previous
    charter set could have closed on hygiene commands alone.
- Out of scope: skills, roles, the structural checker, the brief language
  contract, promotion. No real case content in any tracked path.
- Verification:
  ```bash
  pants test tests/test_assignment_authoring.py
  python3 tests/test_plan_contract.py
  scripts/check-private
  scripts/check-scripts
  git diff --check
  ```

### Slice 2 - Skills and the full role registry surface

Charter form: stub

Objective: two skill directories — parent-owned authoring, final-reviewer
review — hence TWO registry routes and TWO matrix rows. The spawnable reviewer
additionally needs its `.codex/config.toml` entry, Codex agent TOML, byte-equal
`.agents/roles/` fragment, `.claude/agents/` adapter, and write-policy entry.
Its approval record binds an entire variant bundle.

Boundary: one reviewer role covers assignment and brief together; no second
semantic role. No checker or CLI.

### Slice 3 - Structural checker and command surface

Charter form: stub

Objective: `scripts/check-assignment-draft` over the calibrated field set,
non-placeholder literature, the semester-requirement field, coverage hints, and
byte-identical shared literature blocks across a topic's variants; plus the new
generated names in `check_private`. Full Windows command surface and tests.

Boundary: comparison is exact or structured, never fuzzy prose; point count
never infers work type or scope adequacy; no personal-layer preference becomes
a gate.

### Slice 4 - Brief language and bundle sendability

Charter form: stub

Objective: bind each brief to `Student feedback language` on the same terms as
`scripts/check-feedback-language`, and deliver
`scripts/check-assignment-bundle` as the `## Acceptance Contract` names it,
validating one variant bundle, its hashes, and author/reviewer distinctness.

Boundary: reuses the existing language semantics rather than reopening them.

### Slice 5 - Promotion and case-doctor branch

Charter form: stub

Objective: `scripts/promote-assignment <topic-case-id> <variant>
<target-case-id>` writing `notes/assignment.md`, `Assignment source:` with
topic, variant and hash, and an operation-log entry; plus a `Case kind` branch
in `case_doctor` so a topic case reports authoring diagnostics.

Boundary: no bulk migration, and no existing readiness gate is modified.

### Slice 6 - Real-topic run and closeout

Charter form: stub

Objective: publish one real topic through the finished workflow, discharge the
`## Acceptance Contract`, record the `## Final Audit`.

Boundary: no new workflow surface; residual findings become TODO entries or a
follow-up plan.

## Progress

Slice 0 is done. Calibration, one plan-critic round plus its narrow re-check,
and the hand probe are complete. Slice 1 is next and needs a full charter
review before implementation.

### Slice 0 probe findings

The probe hand-authored an intake, a `bp` and a `dp` assignment variant, and a
brief per variant for one real topic. What it refuted or added:

- **The brief must split shared from variant-specific.** Roughly 85% of the two
  briefs is variant-independent — what the platform is, reading order,
  develop-against-mocks, do not fork the core — and only the contribution
  framing, milestones and assessment differ. Two whole briefs per topic will
  drift. Slice 4 should carry a shared brief plus a variant delta, the same
  shape the assignment already uses for literature.
- **The intake needs a citable-artifact slot with identifiers.** The probe could
  not supply the platform's DOI and had to leave an explicit operator TODO,
  because an agent must not invent an identifier. This is the field that turns
  the corpus's placeholder literature into real entries.
- **Success criteria split three ways, not two.** One criterion — that a zero
  count of out-of-seam edits is not the success condition, a complete and
  justified enumeration is — fits the intake as rationale and the brief as
  interpretation, but does not fit an assignment point's style. So the brief is
  not merely derived from the assignment; it is where non-formalizable criteria
  land. Slice 1 must state that in `docs/assignment-authoring.md`.
- **Brief supervision conventions belong in the profile, not the intake.**
  Reading order, milestone spacing, "write to me if you are stuck more than two
  days" and commit-hygiene expectations are supervisor properties, not topic
  properties. They belong in layer 3 of `## Assignment Authoring Style`.
- **A boundary against sibling topics is not `Depends on topic:`.** This topic
  had to declare two separately proposed topics out of scope. That is a mutual
  exclusion between offered topics, not a dependency; the intake's out-of-scope
  section must be able to name sibling topics.
- **Confirmed: the variant model holds on a real pair.** The `dp` variant added
  one point plus a comparison point and escalated the semester requirement,
  matching the corpus construction. The shared/escalation split needed no
  invention.
- **Confirmed: one reviewer role for assignment and brief is right.** The probe
  produced a real cross-artifact defect — the BP brief says six points and the
  DP brief seven — which only a reviewer holding both artifacts can check.
- **Unresolved metadata must be flagged, not guessed.** The academic year was an
  assumption the probe marked in place. Slice 3's placeholder check must treat
  such markers as publication blockers.

## Decision Log

### 2026-09-03 - Assignment style is a profile layer, not a tracked template

Trigger: the operator intends to offer this repository to other supervisors and
asked for a built-in base that configuration can override.

- The mechanism already exists: `check_reviewer_profile.py` resolves an ordered
  profile file list without enforcing any section schema, so a new section
  needs no validator change and no new configuration surface.
- `profiles/README.md` already forbids putting recurring reviewer phrasings in
  the tracked default, which is exactly what deriving the tracked template from
  the operator's corpus would have done.

Decision: three layers per `## Goal` — fixed school form, generic base in
`profiles/default.md`, personal style in `profiles/local/`. Why: it reuses the
established preference mechanism and keeps one supervisor's house style out of
what a colleague inherits.

Residual risk: the generic/personal boundary is a judgment call. Mitigated by
excluding any property attested by a single supervisor.

### 2026-09-03 - Opponent cases supply the cross-supervisor corpus

Trigger: the operator pointed out that opposed theses carry assignments by other
supervisors, answering the single-supervisor limitation recorded the same day.

- Nine assignments by six other supervisors were read from the opponent cases;
  evidence in the calibration case's `work/assignment_style_calibration.md`.
- Most properties the previous entry would have defaulted to layer 3 are
  institutional norm: imperative phrasing, survey-first, a deliverable last, a
  filled semester requirement, real literature entries.
- One earlier reading was wrong: infinitive phrasing attributed to another
  supervisor came from a `notes/assignment.md` paraphrase, not the real page.

Decision: layer 2 is derived from the cross-supervisor section; a property
attested by one supervisor only stays in layer 3. Why: the corpus is
homogeneous enough that over-personalizing would leave a colleague with an
empty base.

Residual risk: all 45 assignments are UPGM/DCGM, so layer 2 is one-institute
calibrated. Stated as a limitation rather than mitigated.

### 2026-09-03 - A topic carries N assignment variants

Trigger: the operator accepted `cases/` but named two holes — a published topic
may never become a thesis, and the same topic may be published twice.

- A topic as a round of the eventual thesis case represents neither: an
  unrealized topic has no thesis case, and a twice-published topic would
  duplicate its authoring history into two cases.
- A separate `topics/` tree represents both but adds a second data contract
  beside the migration in `plans/case_format_migration_contract_plan.md`, and
  still needs the promotion step.
- The corpus shows the shape: two BP/DP pairs share title, leading points and
  literature, differing by one escalation point.

Decision: the topic is its own case under `cases/topic-<year>-<slug>/` with
`Case kind: topic-proposal`; realized theses stay separate cases carrying
`Assignment source:`. Why: one layout, 0..N realization as 0..N promotions.

Residual risk: unrealized topics accumulate in `cases/`. Accepted.

### 2026-09-03 - No English title field

Trigger: none of the 36 published assignments carries an English title; the
plan had assumed a `cs`/`en` title pair.

Decision: the template requires only `Název:`, and carries the Czech and
English renderings of the whole form. Why: four opponent-case assignments use
the English form wholesale, and no document is bilingual internally.

### 2026-09-03 - Artifact names stay language-neutral

Trigger: the tree mixes Czech deliverable names such as
`outputs/oponent_podklady.md` with English ones such as
`outputs/feedback_student.md`.

Decision: use `outputs/assignment_formal_<variant>.md` and
`outputs/student_brief_<variant>.md`. Why: both artifacts have a configurable
output language, so a Czech filename would misname the English case.

### 2026-09-03 - pre-send plan-critic round on the first charter set

Trigger: `scripts/agent-review --staged --profile plan-critic` returned
`changes_required` with five P1 findings, before any implementation.

Adjudicated:

- Variant not first-class across draft, review, approval and promotion:
  ACCEPTED, class (b). Fixed by `## Goal` `### The variant bundle`.
- Slice 0 could pass verification without implementing itself; `Expected
  paths:` omitted `templates/reviewer-profile.md` and `profiles/default.md`:
  ACCEPTED, class (b). Fixed by the shrink below plus
  `tests/test_assignment_authoring.py` in Slice 1.
- Registry surface wider than enumerated — `.codex/config.toml`, Codex TOML,
  byte-equal `.agents/roles/` fragment, `.claude/hooks/reviewer_write_policy.json`
  (`tests/test_agent_profile_contracts.py:11,268,326,335,339`): ACCEPTED,
  class (b). Fixed in Slice 2.
- `## Acceptance Contract` unproducible and escapable: the brief could be sent
  before publication, and `check_assignment_coverage.py:20` validates
  `work/assignment_coverage_agent.json` for an existing thesis rather than
  judging a new point. ACCEPTED, class (a). Contract re-derived to three
  criteria over a variant bundle, triggered by either outward action.
- `check_private.py:33-45` does not know the new generated names: ACCEPTED,
  class (b). Added to Slice 3.
- `case_doctor.py:512-518` runs thesis-review gates unconditionally: ACCEPTED,
  class (b). Added to Slice 5 as a branch, not a gate change.
- Tracked default may hold only generic opponent-report preferences: PARTLY
  REJECTED. That sentence closes `## Report Calibration Boundary` in
  `profiles/README.md:35` and is scoped to opponent-report content; the default
  already carries feedback, supervisor and report style sections. The remedy is
  adopted anyway as one clarifying line, and the reviewer's stronger point —
  factual institute constants are not preferences — is ACCEPTED and fixed in
  `## Goal`.
- Citation consistency must not be fuzzy prose comparison: ACCEPTED, class (b);
  Slice 3 compares byte-identical shared literature blocks.

Residual risk: one narrow re-check is owed on this fix batch only.

### 2026-09-03 - Narrow re-check closes the chain at two rounds

Trigger: the owed re-check returned three P1 and one P2, all local corrections
introducing no new scope.

- Slice 0 verification observed only hygiene, so the probe could be skipped:
  ACCEPTED. Second prose correction of "a slice can close without doing its
  work", so under `plans/README.md` the fix is the instrument — the block now
  resolves the topic case and tests each probe artifact non-empty.
- `## Goal` promised three artifacts against the bundle: ACCEPTED.
- Slice 2 said one route and one row, but two skill directories oblige two of
  each (`tests/test_agent_profile_contracts.py:25,86`): ACCEPTED.
- Sendability command unnamed: ACCEPTED, named
  `scripts/check-assignment-bundle` and folded the separate approval criterion
  into it, leaving two live criteria.

Decision: the chain stops here per `## Plan-Change Review`. Why: the rule is
one round plus one re-check, and a third round needs explicit user approval.

Residual risk: this fix batch is itself unreviewed.

### 2026-09-03 - Slice 0 shrinks to the hand probe

Trigger: five P1 findings on one charter set is a direction signal under
`plans/README.md` `## Plan-Change Review`, which requires answering three
questions before new charters are written.

- (i) What the gated action needs: a correct assignment variant, an independent
  review of it, and a brief that matches it. Not templates, not a profile
  section, not a checker.
- (ii) Cheaper to delete the requirement? The templates are the reusable point
  of the workflow, so no — but the requirement that Slice 0 deliver them goes.
- (iii) Cheapest action producing new information: hand-authoring one real
  topic, which touches no tracked file and can refute the artifact shape.

Decision: Slice 0 is the probe alone; templates, profile layer and operator doc
move to Slice 1, and the former slices renumber to 2 through 6. Why: the probe
was previously buried behind the text it is most likely to invalidate.

Residual risk: the probe produces no reusable artifact, so its value depends on
`## Progress` recording what it refuted.

## Final Audit

Not started.
