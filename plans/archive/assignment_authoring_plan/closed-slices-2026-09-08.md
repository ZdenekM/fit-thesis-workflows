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

### Slice 2 - Skills and the full role registry surface

- Status: done
- Proposed commit message: `Add the assignment authoring and review roles`
- Why: Slice 1 left three templates and a contract that nothing executes. The
  two skills are what an operator and an agent actually run, and the reviewer
  is the independent role the `## Acceptance Contract` presupposes when it
  requires an approval record naming someone other than the author.
- Expected paths: `.agents/skills/thesis-assignment-authoring/SKILL.md`,
  `.agents/skills/thesis-assignment-review/SKILL.md`,
  `src/thesis_review_workflow/agent_profiles.py`,
  `docs/agent-profile-matrix.md`, `.codex/config.toml`,
  `.codex/agents/thesis-assignment-reviewer.toml`, `AGENTS.md`, `README.md`,
  `BUILD`, `tests/test_agent_profile_contracts.py`, `TODO.md`
- Tasks:
  - `.agents/skills/thesis-assignment-authoring/SKILL.md`: the parent-owned
    authoring workflow — intake first, then one assignment per variant, then
    the brief source and its per-variant projections, reading
    `docs/assignment-authoring.md` as its contract. Parent-owned because the
    parent already holds the operator dialogue that produces the intake.
  - `.agents/skills/thesis-assignment-review/SKILL.md`: the spawnable reviewer.
    ONE role holds a variant's assignment and its brief together, because the
    brief restates the assignment's point count and semestral obligation and
    only a reader of both can catch that coupling going stale. Its evidence
    rules are the layer-2 base in `profiles/default.md`, assessability, the
    open-solution-space boundary, byte-identical shared material across
    variants, and unresolved values. The reviewer READS the style layers as
    inputs and applies layer 2 item by item, because the first review found
    check rules that named the base without loading it; and it checks the
    intake's three-way criterion split reached the bundle, because byte-equal
    projections and matching point counts both pass while a criterion is simply
    dropped. Provenance of a value is reported as unverified, never as checked.
  - Two routes in `thesis_review_workflow.agent_profiles::AGENT_PROFILE_ROUTES`:
    the authoring skill as `parent-owned` / `parent-orchestration`, the review
    skill as `profile` / `final-reviewer` with
    `profile_id="thesis_assignment_reviewer"`, CODEX-ONLY providers. The
    authoring route names the reviewer as its `independent_review_profile`.
    Codex-only because the Claude write guard confines a reviewer to
    `cases/<id>/rounds/<round>/` and fails closed without both scope variables,
    which no round-less topic case can satisfy; the parity work and its
    prerequisite go to `TODO.md` per the decision below.
  - Owned outputs and writes for these two routes are CASE-relative, not
    round-relative: a topic-proposal case has no rounds. Confirm no consumer
    resolves this route's paths against a round — `agent_coverage` infers its
    specs from round artifacts and must keep the exact set
    `tests/test_agent_profile_contracts.py` already pins — and state the
    convention in `docs/agent-profile-matrix.md`. The one consumer that cannot
    honour it is the Claude write guard, which is why the route is codex-only.
  - Discharge the rest of the registry surface the reviewer obliges. Do not
    enumerate it from reading: `pants test tests/test_agent_profile_contracts.py`
    is the authority. For a codex-only route that is the Codex config entry and
    its agent TOML; the same test's bidirectional guard requires that the role
    get NO `.agents/roles/` fragment, `.claude/agents/` adapter, or write-policy
    entry until it advertises the claude provider.
  - The approval record binds a whole variant bundle — that variant's
    assignment, its brief projection, and the intake they derive from, each by
    path and hash — because the `## Acceptance Contract` gates the bundle, not
    a file. Follow the existing shape: the record is in the reviewer route's
    `owned_outputs` beside the artifact it approves, as every route matched by
    `thesis_review_workflow.review_profiles::workflow_review_profiles` already
    is, and the Codex reviewer writes it. When the Claude route lands it is
    excluded from `claude_writes` and the parent persists it, the
    parent-mediated protocol `agent_profiles::AgentProfileRoute` documents.
    Validating the record is `scripts/check-assignment-bundle` in Slice 4.
  - Add the two skill-routing lines to `AGENTS.md` `## Skill Routing` and the
    operator entry text to `README.md`, then close that class mechanically: a
    test asserting every registry skill id appears in `AGENTS.md`. Why a test:
    the routing list is prose that nothing currently binds to the registry, and
    `## Scope` had these two edits owned by no slice until now.
  - Expose `AGENTS.md` to the test sandbox through the existing root
    `files(name="agent_profile_registry_metadata")` target, which the new
    routing test needs.
  - One `TODO.md` entry for Claude parity of `thesis_assignment_reviewer`,
    naming its prerequisite: case-scoped support in
    `.claude/hooks/pre_tool_use_write_guard.py::owned_write` with allow/deny
    tests that keep cross-case denial and tracked-path denial intact.
- Out of scope: the structural checker and any CLI, the `check_private` names,
  bundle validation, promotion, `case_doctor`. No entry in
  `thesis_review_workflow.artifact_registry::OUTPUT_ARTIFACTS`, which is the
  registry of ROUND outputs. No second semantic role, and no change to any
  existing route. No change to `.claude/hooks/pre_tool_use_write_guard.py`:
  widening a privacy instrument is its own reviewed change, not a task inside a
  slice about skills.
- Verification:
  ```bash
  pants test tests::
  python3 tests/test_plan_contract.py
  scripts/check-private
  scripts/check-scripts
  git diff --check
  ```
  Scoped Omen over `src/thesis_review_workflow/agent_profiles.py` during
  implementation, `pants run :omen` at the end; record the observed result or a
  concrete blocker in `## Progress`.

### Slice 3 - Structural checker and command surface

- Status: in_progress
- Proposed commit message: `Add the assignment draft checker and its command surface`
- Why: Slices 1 and 2 produced a contract and two roles that read it, and
  nothing deterministic yet. Every property that can be decided without
  judgment must be decided here, so the reviewer role spends its round on
  assessability and wording rather than on counting fields.
- Expected paths: `src/thesis_review_workflow/assignment_draft.py`,
  `src/thesis_review_workflow/cli/check_assignment_draft.py`,
  `src/thesis_review_workflow/cli/check_private.py`,
  `src/thesis_review_workflow/cli/BUILD`,
  `src/thesis_review_workflow/commands.py`, `scripts/check-assignment-draft`,
  `scripts/smoke-assignment-draft`, `scripts/BUILD`,
  `src/thesis_review_workflow/agent_profiles.py`,
  `docs/agent-profile-matrix.md`, `docs/assignment-authoring.md`,
  `docs/workflow-command-surface.md`, `templates/topic-intake.md`,
  `tests/test_assignment_draft.py`, `tests/test_check_private.py`,
  `tests/test_assignment_authoring.py`
- Tasks:
  - `scripts/check-assignment-draft <case-id> [variant]`: refuse to run unless
    `thesis_review_workflow.metadata::case_kind` reads `topic-proposal`, then
    check one variant, or every variant the intake lists when none is named.
  - Per variant, decide only what is decidable without judgment: the declared
    rendering's field labels present and in the template's order, exactly one
    rendering used, the semestral-requirement field non-empty, at least one
    numbered assignment point, and no unresolved value anywhere in the bundle
    via `thesis_review_workflow.metadata::unresolved_values`.
  - Literature is checked STRUCTURALLY, never lexically. `AGENTS.md` forbids a
    free-text heuristic as a gate, and the corpus placeholders are ordinary
    Czech sentences, so "looks like a placeholder" cannot be the rule. The rule
    is provenance: every literature bullet in an assignment must equal an entry
    the intake's `## Citable Artifacts` authored, and every such entry must
    carry a non-empty identifier that is not an unresolved value. At least one
    such entry must exist per assignment — checking the provenance of every
    bullet says nothing when there are none, and an empty or supplement-only
    literature block is a deterministic failure of the layer-2 base, not a
    reviewer judgment. A supplement line is admissible only through an explicit
    intake field, not by matching its wording; add that field to
    `templates/topic-intake.md` if the shape needs it, and say so in
    `docs/assignment-authoring.md`. It did: the intake gains a
    `Supplement line:` field.
  - Cross-variant: shared material — every intake-sourced literature entry
    above all — must be byte-identical in every variant that uses it. The
    corpus pair that motivated this cited one shared paper two different ways.
    No separate check implements it: exact provenance against the intake
    already forces identical citation wherever an entry is used, and requiring
    identical MEMBERSHIP instead rejects a DP that legitimately cites one more
    work. The first review round proved that with a case.
  - Brief projections: `outputs/student_brief_<variant>.md` must carry the
    `## Shared Brief` body of `notes/student_brief.md` and its own variant's
    delta, both verbatim and nothing else. This needs a canonical projection
    shape, which Slice 1 never fixed: a title line, the shared body, then
    `## Variant Delta - <variant>` and that delta. Without it the check can
    only be a substring test, which the first review showed is unsound in both
    directions — one delta may legitimately contain another as a prefix, and an
    appended obligation goes unnoticed.
  - Validate the variant token before it becomes a filename segment, and match
    any safe suffix in `check_private` rather than `[a-z0-9]+`, which the first
    review showed lets `assignment_formal_dp-research.md` escape.
  - Add the generated names to `check_private`: the topic intake, the brief
    source, the per-variant assignment and brief, the reviewer's findings
    artifact, and its approval record, which today's
    `work/reviews/[^/]+_review\.json` pattern does not match. Extend
    `tests/test_check_private.py` with each new name.
  - Deliver the whole operator-tool surface `docs/workflow-command-surface.md`
    requires. Do not enumerate it here from reading: `pants test tests::` is
    the authority, and
    `test_workflow_command_modules_have_sources_runtime_deps_and_wrappers`
    together with `test_workflow_tool_pex_targets_match_command_module_map`
    fails until every piece exists. Windows needs no hand-written launcher; the
    packaging entrypoint generates `.cmd` and `.ps1`.
  - Name the new command in both routes' `required_validators` and update the
    two `docs/agent-profile-matrix.md` rows that currently read `none yet`.
  - Keep the FIT IS label sets in ONE place,
    `thesis_review_workflow.assignment_draft::RENDERINGS`, and have
    `tests/test_assignment_authoring.py` derive its expected template order from
    it. Slice 1's test carried its own copy, which would drift against the
    checker's.
  - `tests/test_assignment_draft.py` over synthetic topic cases in `tmp_path`:
    a clean bundle passes; each rule fails on exactly its own defect; empty
    literature and supplement-only literature each fail; a `thesis-review` case
    is refused; point count is never read as evidence of work type or scope; a
    variant that legitimately differs is not reported as drift.
- Out of scope: anything requiring judgment — assessability, whether an open
  point states a criterion, tone, topic quality. Structural provenance is not
  source verification: the checker proves a bullet came from the intake, never
  that the identifier resolves to a real work, and must not report otherwise. Approval records and hashes,
  the brief language binding and `scripts/check-assignment-bundle`, which are
  Slice 4. Promotion and `case_doctor`, which are Slice 5. No personal-layer
  profile preference becomes a gate, and no new gate is added to any existing
  thesis workflow.
- Verification:
  ```bash
  pants test tests::
  scripts/smoke-assignment-draft
  python3 tests/test_plan_contract.py
  scripts/check-private
  scripts/check-scripts
  git diff --check
  ```
  Scoped Omen over the two new Python modules during implementation, `pants run
  :omen` at the end; record the observed result or a concrete blocker in
  `## Progress`.
