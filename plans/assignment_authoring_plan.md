# Assignment Authoring Plan

Status: in_progress
Created: 2026-09-03

## Start Here

State: Slices 0 to 5 are done and green. The whole tracked workflow exists:
templates, contract, style layers, both skills, the reviewer route, both
checkers, the bundle approval, promotion and the case-doctor branch. Nothing has
authored a real topic through it yet, which is Slice 6.

A cumulative Codex pass over Slices 1 to 5 has run and its two cross-slice
findings are fixed, so the per-slice re-check gaps are closed.

Next action: compact the closed Slice 5b charter, then run Slice 6 on
`cases/topic-2026-extension-seam-domain` — the operator supplied that topic and
authorized agents. Write Slice 6's full charter first and review it.

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

- `scripts/check-assignment-bundle <case-id> <variant>`, delivered by Slice 4b,
  passes: it validates every file and hash in that variant's bundle, and that
  its approval record names a reviewer distinct from the author. No round id:
  a `topic-proposal` case has no rounds, which the architecture settled after
  this criterion was written;
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

Charter form: compacted
Landed: 16402a1
Delivered `templates/topic-intake.md`, `templates/assignment-formal.md` and
`templates/student-brief.md`, the `## Assignment Authoring Style` layer 2/3
split across `profiles/default.md` and `templates/reviewer-profile.md`,
`docs/assignment-authoring.md`, `Case kind:` behind
`thesis_review_workflow.metadata::CASE_KINDS`, the value-position unresolved
marker behind `thesis_review_workflow.metadata::unresolved_values`, and
`tests/test_assignment_authoring.py`.
Full charter: `plans/archive/assignment_authoring_plan/closed-slices-2026-09-08.md`.
Decisions: `2026-09-08 - Slice 1 charter review passes with no findings`,
`2026-09-08 - Slice 1 review: three findings, all fixed in one batch`.

### Slice 2 - Skills and the full role registry surface

Charter form: compacted
Landed: cebbc1f
Delivered `.agents/skills/thesis-assignment-authoring/SKILL.md` and
`.agents/skills/thesis-assignment-review/SKILL.md`, their two routes in
`thesis_review_workflow.agent_profiles::AGENT_PROFILE_ROUTES` with case-relative
owned outputs and a codex-only reviewer, the Codex config entry and adapter, two
`docs/agent-profile-matrix.md` rows, the `AGENTS.md` and `README.md` routing
text bound to the registry by
`test_agents_md_skill_routing_lists_every_registry_skill`, and the Claude-parity
`TODO.md` entry.
Full charter: `plans/archive/assignment_authoring_plan/closed-slices-2026-09-08.md`.
Decisions: `2026-09-08 - The assignment reviewer ships codex-only`,
`2026-09-08 - Slice 2 review: the reviewer named a standard it never loaded`.

### Slice 3 - Structural checker and command surface

Charter form: compacted
Landed: 7d14074
Delivered `thesis_review_workflow.assignment_draft` and
`scripts/check-assignment-draft` with the full operator-tool surface and smoke,
provenance-based literature checking against the intake, the canonical brief
projection shape, variant-token validation, the six new `check_private` names,
`required_validators` on both routes, and 29 checker tests.
Full charter: `plans/archive/assignment_authoring_plan/closed-slices-2026-09-08.md`.
Decisions: `2026-09-08 - Slice 3 review chain stops at its re-check, by the rule`.

### Slice 4a - Brief language binding

Charter form: compacted
Landed: 5d8c610
Gave the brief a Czech and an English heading contract selected by `Student
feedback language`, applied the three rules `scripts/check-feedback-language`
applies, renamed the English projection wrappers so no language heading is
spelled like a neutral source wrapper, and matched forbidden headings by base
rather than by enumerated form.
Full charter: `plans/archive/assignment_authoring_plan/closed-slices-2026-09-08.md`.
Decisions: `2026-09-08 - Slice 4a: enumerating heading forms failed twice`.

### Slice 4b - Bundle approval and sendability

Charter form: compacted
Landed: 6cc1a4d
Delivered `assignment-bundle-approval-v1` in
`thesis_review_workflow.assignment_bundle`, `scripts/check-assignment-bundle`
with its operator-tool surface and smoke, the record's field list in the
reviewer skill and Codex adapter, and 44 tests including builder/reader parity.
Full charter: `plans/archive/assignment_authoring_plan/closed-slices-2026-09-08.md`.
Decisions: `2026-09-08 - Slice 4b: the reader is the gate, so parity is structural now`.

### Slice 5 - Promotion and case-doctor branch

Charter form: compacted
Landed: 2b2d0ad
Delivered `scripts/promote-assignment` behind four independent refusals
(approval, issuance, target fitness, containment), the retained approval record
beside its hash, heading demotion so the brief cannot end its section, the
`case_doctor` topic-proposal branch, and 23 promotion tests.
Full charter: `plans/archive/assignment_authoring_plan/closed-slices-2026-09-08.md`.
Decisions: `2026-09-08 - Approval is not issuance, and containment needs a root`,
`2026-09-08 - Slice 5: three privacy escapes and a test that proved nothing`.

### Slice 5b - Claude parity for the assignment reviewer

Charter form: compacted
Landed: ac98b8c
Gave the reviewer write guard an explicit per-role write scope carried in the
policy, made `thesis_assignment_reviewer` claude-capable and case-scoped with
its fragment, adapter and policy entry, kept the repository-root containment
anchor, and named the parent-mediated approval cost with a frozen hash basis in
the skill, the adapter and `docs/agent-workflow.md`. 26 guard tests.
Full charter: `plans/archive/assignment_authoring_plan/closed-slices-2026-09-08.md`.
Decisions: `2026-09-08 - Claude parity comes back into the plan`,
`2026-09-08 - The Codex reviewer cannot start Serena, four reviews running`.

### Slice 6 - Real-topic run and closeout

- Status: planned
- Proposed commit message: `Close the assignment authoring plan after a real-topic run`
- Why: five slices built a workflow that no real topic has been through. The
  probe in Slice 0 was hand-authored and touched no tracked path, so nothing yet
  shows the tracked templates, checkers and roles working together on real
  material. Everything the plan claims is untested as a whole until this runs.
- Expected paths: `plans/assignment_authoring_plan.md`, `TODO.md`, and whatever
  the run itself proves defective. No new workflow surface is planned; a fix
  the run forces is a fix, and anything larger becomes a TODO entry or a
  follow-up plan rather than growing this slice.
- Tasks:
  - Operator decisions, both supplied: the topic is
    `cases/topic-2026-extension-seam-domain`, both `bp` and `dp`, and agent use
    is authorized for the reviewer role.
  - That case already holds the Slice 0 probe's material, and it does NOT match
    the tracked shape: it sits in a round, its intake carries Czech headings of
    its own invention, and its academic year is a marked assumption. Re-lay it
    into the tracked shape rather than authoring new content — migrating real
    material an operator actually wrote is a harder test than a fresh topic and
    is the one this slice wants.
  - Keep the probe round directory untouched as the before-state until the run
    is finished, so a difference between hand-written and tracked output stays
    visible.
  - Use `.agents/skills/thesis-assignment-authoring/SKILL.md` and the tracked
    templates; do not hand-write an artifact the templates cover.
  - Run `scripts/check-assignment-draft` and fix what it finds. A finding that
    is a defect in the CHECKER rather than in the topic is the most valuable
    result this slice can produce; record which kind each one was.
  - Have `thesis_assignment_reviewer` review each variant bundle. Run it as the
    CLAUDE subagent Slice 5b just delivered, so the run exercises the parity
    path a Claude-only supervisor will use: the reviewer writes findings
    carrying its verdict, blocking count and the frozen four-file hash basis,
    and this session as parent writes the approval record after re-checking that
    basis. It must be a different agent than the author.
  - Run `scripts/check-assignment-bundle` per variant.
  - Discharge the `## Acceptance Contract` explicitly: name the command result
    and record the operator's reading against the three criteria it states.
    Publishing to FIT IS and sending a brief are the operator's actions, not
    this slice's; the slice ends at "ready, and the operator decided".
  - Promote only if the operator says the assignment was issued, and only into a
    case they name. Promotion is not part of proving the workflow works.
  - Record the `## Final Audit`: commands run, checks skipped and why, residual
    risks, and the archive decision.
  - Route what the run teaches: a repeatable rule into `AGENTS.md`,
    `plans/README.md` or a skill; a mechanical trap into a test; anything left
    over into `TODO.md`. Then move the plan to `plans/archive/`.
  - One question the run should answer rather than assume: the tracked intake
    template uses English headings while a Czech-speaking supervisor wrote the
    real one in Czech. Decide from the run whether that is right, and record the
    answer; do not quietly change the template mid-run.
- Out of scope: a second topic, bulk authoring, Claude parity for the reviewer
  role, and any change to an existing thesis workflow. No private case content
  in any tracked path, the plan and TODO included.
- Verification:
  ```bash
  pants test tests::
  scripts/check-assignment-draft <topic-case-id>
  scripts/check-assignment-bundle <topic-case-id> <variant>
  scripts/case-doctor <topic-case-id>
  python3 tests/test_plan_contract.py
  scripts/check-private
  scripts/check-scripts
  git diff --check
  ```
  The three case-scoped commands take the real case id the operator supplies;
  their output is private and stays out of the plan.

## Progress

Slices 0 to 5 are done. Slice 1 landed the three templates, the
layer-2/layer-3 profile split, `docs/assignment-authoring.md`, `Case kind:` and
the unresolved-value instrument. Slice 2 landed the two skills, the two registry
routes, the Codex adapter, the matrix rows and routing text, and a test binding
`AGENTS.md` routing to the registry. Slice 3 landed
`scripts/check-assignment-draft` and its whole operator-tool surface, and Slice
4a the brief's Czech and English heading contract, at 41 checker tests. Slice
4b landed `assignment-bundle-approval-v1`, `scripts/check-assignment-bundle`
and 44 bundle tests, discharging the `## Acceptance Contract`'s executable half.
Slice 5 landed `scripts/promote-assignment` with its four independent refusals,
the retained approval record and the `case_doctor` topic branch, at 23 promotion
tests. Slice 5b made the reviewer Claude-capable by giving the write guard an
explicit per-role scope, at 26 guard tests.
Each slice took one review round plus its narrow re-check; on Slices 3 and 4a
the re-check found a defect in the round's own fixes and both chains stopped by
rule, and the 4b re-check returned `needs_human` on a Serena outage in its own
sandbox.

Omen limitation, every slice so far: the MCP server returned zero files for
every path attempted, file and directory alike, so `pants run :omen` is the only
static signal used. It now ranks `assignment_draft.py` a High hotspot, which is
churn from a new file rather than a quality signal: average complexity 3 over
one commit.

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
- **One reviewer role for assignment and brief is right.** The brief restates
  the assignment's point count and its semester obligation, so each brief is
  coupled to its own variant's assignment and would silently go stale if a
  point were added. Only a reviewer holding both artifacts can check that
  coupling. No such defect occurred in the probe; the coupling is the evidence,
  not a discovered error.
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

### 2026-09-04 - Open solution space is norm, not a defect

Trigger: the operator confirmed the probe's decision to leave the application
domain to the student, with two reasons: a change of direction then does not
require amending the assignment already approved in FIT IS, and the student
keeps room for own initiative.

- Attested in the assignment points of five of the six other supervisors and
  six of the operator's own; evidence in the calibration case's
  `work/assignment_style_calibration.md`. So layer 2, not layer 3.
- The amendment-cost reason generalizes: an approved assignment is expensive to
  change for any supervisor at this faculty.

Decision: layer 2 carries the criterion AND its boundary — a point may leave
the solution open, the reviewer must not push toward specifying it, and what
gets flagged is openness with no stated criterion the choice can be judged
against. Why: the naive assessability rule would have driven every assignment
toward over-specification, which is the opposite of the norm.

Residual risk: the weak/assessable line is a judgment the reviewer role owns.

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

### 2026-09-08 - Slice 1 charter review passes with no findings

Trigger: `plans/README.md` `## Plan-Change Review` requires a materially
rewritten slice charter to be reviewed before its implementation starts. The
rewrite folded the Slice 0 probe findings into Slice 1.

- `scripts/agent-review --profile plan-critic` over the uncommitted charter
  diff returned no actionable findings; verdict pass.
- It confirmed that six probe findings are built by Slice 1 and the remaining
  two are confirmations needing no build, and that the deferrals to Slices 3-5
  match the already adjudicated allocation.

Decision: no fix batch, so no narrow re-check is owed and Slice 1
implementation starts next. Why: the stopping rule owes a re-check only when a
fix batch carries class (a)/(b) findings, and there is no fix batch.

Residual risk: a clean charter review says the plan text is right, not that the
corpus-derived field set and the layer-2/layer-3 split survive being written
down. The slice's own test and review carry that.

### 2026-09-08 - Slice 1 review: three findings, all fixed in one batch

Trigger: the slice-review round on the staged Slice 1 implementation.

- (b) `docs/assignment-authoring.md` and `templates/student-brief.md` described
  two different brief shapes. Fixed: `notes/student_brief.md` is the canonical
  per-topic source and `outputs/student_brief_<variant>.md` a projection of it.
- (a) An `UNRESOLVED:`-anywhere reading would have blocked a bundle whose values
  were all resolved, because the templates explain the marker. Fixed as an
  instrument: `thesis_review_workflow.metadata::UNRESOLVED_VALUE_RE` matches the
  value position only, and a test asserts no template trips its own marker.
- (b) `templates/assignment-formal.md` carried one mixed metadata block reading
  `Institute:`. Fixed: two selectable rendering blocks with `Institut:`
  corrected, tested by ordered line-opening labels.

Decision: one narrow re-check scoped to the fix batch; it passed, closing the
chain at one round plus one re-check, as the (a)/(b) content of the batch owed.

Residual risk: Omen returned zero files on every path attempt in both rounds, so
`pants run :omen` is the only static signal over the one touched module.

### 2026-09-08 - The assignment reviewer ships codex-only

Trigger: the Slice 2 charter review found the Claude write guard unable to
permit the advertised route, and the approval record assigned to the wrong
party under Claude — two accepted findings, so the three direction answers.

- (i) The gated action needs an independent reviewer distinct from the author
  and a bundle-binding approval record. It does not need that reviewer to be a
  Claude subagent; `docs/agent-workflow.md` already makes Codex the independent
  reviewer of the developer track.
- (ii) Deleting the requirement is cheaper: dropping `claude` from this route
  removes the write-guard change, the adapter, the fragment and the policy entry
  from this plan, and the bidirectional guard in
  `tests/test_agent_profile_contracts.py` keeps that consistent by itself.
- (iii) Cheapest new information: implement the codex-only reviewer, the first
  role in this tree to write outside a round at all.

Decision: Slice 2 ships codex-only; Claude parity and its write-guard
prerequisite go to `TODO.md`. The approval record follows the existing
`review_profiles` shape instead of a new one.

### 2026-09-08 - Slice 2 review: the reviewer named a standard it never loaded

Trigger: the slice-review round on the staged Slice 2 implementation. Two
findings, both class (a).

- The reviewer skill listed the layer-2 base as its standard but did not read
  `profiles/default.md`, while a check claimed to detect profile-sourced values.
  Fixed: both style layers are required inputs with a stated missing-profile
  fallback, layer 2 is applied item by item, and provenance is reported as
  unverified rather than as a passed check.
- Nothing checked that the intake's three-way criterion split reached the
  bundle. A dropped `### Interpretation For The Student` criterion passed every
  check, because projections stay byte-identical and point counts still match.
  Fixed: an explicit walk of all three intake categories to their destinations.

Decision: fixed in the batch, one narrow re-check, which passed. Why it matters
beyond the fix: the second defect was invisible precisely because the Slice 1
mechanisms worked, so mechanical equality is not evidence that the content the
split protects survived.

### 2026-09-08 - Slice 4 splits, and the contract drops its round id

Trigger: writing the Slice 4 charter against the code showed two independent
commit-sized halves and one criterion whose premise had moved.

- Split: 4a binds the brief to `Student feedback language`, which needs a Czech
  heading rendering the template never had; 4b delivers the approval record and
  `scripts/check-assignment-bundle`. Each reviews on its own.
- The `## Acceptance Contract` named `check-assignment-bundle <case-id>
  <variant> [round-id]`, written before the round-less topic case was decided.
  Re-derived rather than patched, per `plans/README.md`: the round id is gone.
  This SHRINKS the criterion, which needs no operator approval.
- 4b will not reuse `review_approvals::REVIEW_APPROVAL_SCHEMA`: its payload
  fixes one `reviewed_artifact_path` and one `review_basis_path`, while a
  bundle is four artifacts. Manifest validation is a separate function, so it
  is not the reason; reuse is the hashing helper and the field vocabulary.

Decision: charter 4a in full, 4b as a stub. Why: the last three slices each
found defects a smaller object would have surfaced sooner.

### 2026-09-08 - Slice 3 review chain stops at its re-check, by the rule

Trigger: the slice review found five defects, all (a)/(b), all fixed; the narrow
re-check then found two blocking defects IN THOSE FIXES — the literature scan
still stopped at a nested heading and skipped inline label text, and the
projection comparison still ignored the title line.

- Both were fixed as SIMPLIFICATIONS, which is what the shrink rule asks for:
  the literature check now consumes the whole `### Literature` section instead
  of guessing where it ends, and the projection is compared WHOLE against one
  constructed canonical document instead of part by part.
- Deleted rather than fixed: the cross-variant equality check, subsumed by exact
  provenance, which rejected a DP legitimately citing one more work.

Decision: the chain STOPS here at one round plus one re-check. A third round on
the same object needs the direction check plus explicit operator approval under
`plans/README.md` `## Plan-Change Review`, and the operator has been asked.

Residual risk: the two fixes are unreviewed text by that same rule.

### 2026-09-08 - Slice 4a: enumerating heading forms failed twice

Trigger: the slice review found two ways a wrong-language heading reached a
student projection; the narrow re-check found a third in the fix.

- The exemption that kept the neutral wrappers safe let `# Student Brief` sit
  inside a Czech shared body. Fixed by removing the collision rather than the
  symptom: the English wrappers became `# Thesis Topic Brief` and
  `## For This Variant`, so no language heading is spelled like a wrapper. A
  contract test now holds that invariant.
- Enumerated exact forms left a suffix open twice — the variant-qualified ASCII
  fold, then any other variant's qualified heading. Fixed by matching heading
  BASES with a predicate, closing the class by construction, not by a list.
- The hand-written ASCII-fold list made a diacritic-free Czech heading both
  required and rejected; folds are derived now.

Decision: this chain also stops at one round plus one re-check. Why the shape
recurred: an enumeration of forms is a contract stated in prose, and
`plans/README.md` says the authority must be a mechanical check instead.

### 2026-09-08 - Slice 4b: the reader is the gate, so parity is structural now

Trigger: the slice review reproduced three live acceptances against the code,
and the narrow re-check stopped on its own tooling rather than confirming
builder/reader parity.

- Audit metadata was shape-checked nowhere though the charter required it, so a
  record missing `timestamp` published.
- Duplicate `files` entries were last-wins, so a wrong hash followed by the
  right one for the same path passed.
- The builder took `False` and `0.0` as a zero blocking count, emitting records
  its own reader rejected.

Decision: parity stopped being two hand-kept lists. The builder validates its
own output with the reader before returning, and a parametrized test asserts
every builder-refused input is refused when hand-written. Why: the re-check
could not verify parity by reading, and the property is cheap to assert.

Residual risk: that re-check returned `needs_human`, so this batch had no second
reader. Serena was reachable here and was used to read the builder.

### 2026-09-08 - Approval is not issuance, and containment needs a root

Trigger: the Slice 5 charter review returned four findings, two P1, and its
narrow re-check found the containment anchor still one level too low.

- Approval says a variant may be published, not that a student received it.
  Promotion turned the first into assessment authority, and no readiness check
  sees the difference. It now requires a recorded issuance assertion.
- The target went unvalidated: a `dp` bundle into a BP case gives the wrong
  assessment basis. The re-check then showed confining writes to the resolved
  CASE is too low an anchor, since the case can resolve out of `cases/`.
- The rendering mapping dropped the semestral requirement and would have cut
  `## Private Assignment Notes For Student` in half, because the projection
  carries an H2 and `check_round_ready` ends a section there.
- A record hash is an identity, not an archive: one fixed approval path per
  variant means a re-approval destroys what it refers to, so the record is
  retained.

Decision: chain stops at one round plus one re-check; the fix is one tightening
clause, not a third object. Residual risk: that clause is unreviewed.

### 2026-09-08 - Slice 5: three privacy escapes and a test that proved nothing

Trigger: the slice review found four defects in promotion, three of them ways
to write private content outside `cases/` while every stated guard passed.

- A dangling destination symlink: `exists()` is false, so the check resolved the
  parent and the write followed the link.
- The operation log was not a checked destination, so a redirected
  `work/operation_log.jsonl` carried case id, actor and issuance note out.
- A `cases/` linked to `docs/` passed a root check that asked only whether the
  root resolved inside the repository.
- The DP-into-BP test never reached the work-type check it named, because the
  fixture approved only BP; it would have passed with that check deleted.

Decision: containment is asserted over whole resolved paths now, and a
parametrized test links each directory on every write path in turn. Why that
shape: all three holes came from checking a path component rather than the
destination. The chain stops here; the re-check confirmed the fixes and returned
`needs_human` on its own Serena outage.

### 2026-09-08 - Cumulative review: two cross-slice defects per-slice review could not see

Trigger: the operator asked for one cumulative Codex pass over Slices 1 to 5,
since several narrow re-checks had ended without reading the round's last fixes.

- Validation and promotion read DIFFERENT boundaries for the semestral
  requirement: `assignment_draft` searched the whole rendering,
  `assignment_promotion::formal_text` only its section. A field under
  `### Footer` validated, was approved and hash-bound, and was then dropped on
  promotion — the obligation surviving in the approved file and not in the
  thesis case. Both read the section now.
- `scripts/new-case` copied `templates/case-notes.md` without resolving
  `Case kind:`, so every normally created thesis case was an invalid promotion
  target, and the promotion smoke hid it by hand-writing the metadata.

Decision: fixed in one batch with a regression each. Why the pass was worth it:
both defects live BETWEEN slices, where each slice's own review had nothing to
compare against, and one of them made an approved artifact and a promoted one
disagree.

### 2026-09-08 - Claude parity comes back into the plan

Trigger: the operator observed that holding both providers is the exceptional
case, and asked whether subagents could serve a Claude-only supervisor.

- They can, through the same `.claude/agents/` reviewer subagent the five other
  thesis roles use; the only blocker is that
  `pre_tool_use_write_guard.py::owned_write` hardcodes a round-shaped path.
- `2026-09-08 - The assignment reviewer ships codex-only` answered its direction
  question from an operator holding both. For a Claude-only supervisor there is
  no independent reviewer at all, so the `## Acceptance Contract` cannot be met.

Decision: chartered as Slice 5b, before the real-topic run, rather than left in
`TODO.md`, because this plan's own acceptance contract breaks without it.

Residual risk: under the parent-mediated protocol the author writes the approval
record attesting the reviewer's verdict, which is weaker than Codex, where the
reviewer writes it.

### 2026-09-08 - The Codex reviewer cannot start Serena, four reviews running

Trigger: the Slice 5b implementation review returned `needs_human`, the fourth
this session to stop on Serena rather than finish its verification.

- Cause is structural, not a transient outage: `~/.codex/config.toml` runs
  Serena as a STDIO server via `uvx --from git+...`, which cannot start under
  `codex exec --ephemeral --sandbox read-only`. The workstation already serves
  Serena over HTTP bridges, and Serena works from this session throughout.
- Effect: those reviews reported only what they could read, so their
  verification step never ran. That is a silent downgrade — a `needs_human`
  reads like caution rather than like a tool that was never available.

Decision: recorded in `TODO.md` with the concrete config change; not fixed here,
because `~/.codex/config.toml` is workstation configuration outside this repo
and outside this plan. The Slice 5b verification the reviewer could not perform
is instead carried by `tests/test_write_guard.py`, which now covers the
redirected root, the redirected case, the dangling link, and a round reviewer
NOT widening when its round variable is unset.

## Final Audit

Not started.
