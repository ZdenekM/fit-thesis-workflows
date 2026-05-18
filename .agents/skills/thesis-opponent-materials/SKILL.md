---
name: thesis-opponent-materials
description: DEEP workflow for internal opponent materials for a BP/DP report, with evidence labels, risk calibration, thesis/code consistency review, and code-quality/design review.
---

# Thesis Opponent Materials

Command routing: treat `scripts/<tool>` examples below as logical workflow
command names. On Windows, use the packaged
`dist\workflow-tools\bin\<tool>.cmd` or `.ps1` launcher from `README.md`; do
not run or click extensionless `scripts/<tool>` files.

Use this skill to prepare internal materials for an opponent report. The output is not the final report to submit.

## Inputs

Use the active round unless the user specifies another:

```text
cases/<case-id>/rounds/<round-id>/
  notes/assignment.md
  notes/opponent-intake.md
  notes/round-notes.md
  inputs/
  extracted/
  work/
  outputs/
```

## Process

1. Resolve the active case and round.
2. Confirm that the user explicitly authorized agent use in the current request. This workflow requires role-split agents. If explicit authorization is missing, stop before generating or revising opponent materials and ask the user to authorize agents.
3. Run `scripts/check-round-ready <case-id> [round-id]`. If it fails, stop before generating materials and ask the user to add the formal assignment, private assignment notes, or valid reviewer profile.
4. Read the effective profile files from the readiness output, or rerun `scripts/check-reviewer-profile <case-id>` if the file list is no longer visible. Profiles apply only to preference conflicts. They never override case workflow configuration, readiness gates, evidence requirements, verified notes, or this skill.
5. Read `current-round.txt` and inventory `notes/assignment.md`, `notes/opponent-intake.md`, `notes/round-notes.md`, thesis text, available code/artifacts, README, experiment results, and human notes. Start analysis from `work/common_briefing.json`, `work/current_evidence_snapshot.json`, materiality decisions, role packets, reusable standalone evidence, `work/context/evidence_capsules.json`, and `work/context/claim_review_basis.json` when present. Open full raw sources only for changed fingerprints, missing anchors, contradictions, P0/P1 or grade-impacting verification, reviewer challenges, unsupported synthesis wording, or role scope that cannot be resolved from current capsule refs.
6. Enumerate available inputs and extract PDF text into `extracted/` when needed and possible. Treat submitted PDFs as rendered thesis evidence; use LaTeX/Overleaf sources for diff/search/evidence and do not build them by default. Use `pdf-reader-mcp` only as an optional targeted detail layer for page ranges, metadata, page counts, figures/tables, layout-sensitive checks, or ambiguous extraction. State what was not available or not runnable.
7. If code is present only as an archive in `inputs/`, prepare an inspectable copy under `work/code/` before delegating to read-only reviewers. If the code is available through GitHub repo/PR URLs, run `thesis-github-code-intake` first and keep the resulting `outputs/github_code_intake.md` as internal evidence. If agent authorization is missing, stop before final output and ask for authorization instead of recording an agent-review limitation.
8. When quantitative, evaluation, experiment, metric, performance, or result claims matter to opponent synthesis, an authorized quantitative-claims reviewer agent or human must first write `work/quantitative_claims.json` with evidence anchors, units, scale/sample context, baseline/comparator status, practical magnitude, overclaim risk, reproducibility refs, and limitations. Then run `scripts/check-evaluation-claims <case-id> [round-id]` to validate that structured artifact before synthesis. Do not use deterministic text matching to decide whether such claims exist or what they mean. Text, code, and figure/media agents that discover material prose-only quantitative claims must route them to this skill rather than expanding deterministic raw-text scans.
9. Before spawning role-split agents, use the optimized deterministic boundary:
   `scripts/review-round-start --profile opponent_materials <case-id> [round-id]`
   to confirm current materials and write `work/review_run_trace.json`, then
   `scripts/prepare-review-round --profile opponent_materials <case-id> [round-id]`
   to write `work/review_role_plan.json` and opponent packets. Do not manually
   reconstruct role needs from chat when a current role plan can be generated.
   Use the generated `work/opponent_packets/*.md` packets as the compact role
   handoff, and regenerate them after assignment/evidence/reproducibility
   artifacts change. Role states in `work/review_role_plan.json` decide whether
   a role needs fresh review, scoped delta review, current reviewed reuse, or a
   concrete typed limitation. Packets render materiality `next_actions`;
   resolve required GitHub, quantitative, and Theses.cz similarity-report
   actions with a current artifact or a typed `work/review_manifest.json`
   limitation that records `trigger`, `scope`, `type`, `required_for`,
   `description`, `impact`, `status`, and `accepted_by` or `reviewer_role`
   before synthesis/reviewed wave readiness. Packets, reuse-index decisions,
   and capsules reduce repeated context; they do not replace this skill,
   required semantic role coverage, independent review, approval records, or
   manifest validation.
10. Build a map of:
   - assignment points and where they are covered,
   - reviewer profile preferences that are relevant to this round,
   - main technical contribution,
   - thesis structure and heading/outline quality,
   - figure/media evidence, visual descriptions, and figure changes between rounds,
   - GitHub/PR intake evidence and contribution scope when applicable,
   - implementation and artifact evidence,
   - implementation quality and design evidence,
   - experiments/results and whether conclusions are supported,
   - imported Theses.cz similarity-report status and any unresolved concerns,
   - reproducibility status,
   - literature/citation issues,
   - typography/formal presentation issues calibrated by thesis language,
   - likely strengths,
   - risks that may affect grading.
11. Run `thesis-figure-media-review` when thesis figures, tables, screenshots, result images, diagrams, or visual changes between rounds materially affect the opponent assessment. Leave reusable evidence in `work/figure_media/visual_inventory.jsonl` and `outputs/figure_media_review.md`; summarize only relevant findings and limitations in the materials.
    If the role agent or helper fails to produce its expected output, stop the
    opponent-materials pipeline before synthesis, report the failed role and
    expected paths, and ask the operator whether to rerun/repair the role or
    accept a blocked typed limitation. Do not silently replace the missing role
    with a parent-generated limited substitute.
12. Run `thesis-code-consistency` and `thesis-code-quality-review` when code is available. When code comes from GitHub repo/PR evidence, use `thesis-github-code-intake` first and scope downstream review to the imported checkout or PR contribution map. Leave visible evidence in `outputs/code_consistency.md` and `outputs/code_quality_review.md`, and summarize the relevant findings and limitations in the materials.
    In code-backed opponent materials, also assess whether the implementation
    explanation is understandable without reading the source code line by line:
    prefer principle, architecture, state/data flow, and visual summaries over
    function inventories. Distinguish unit-level evidence for deterministic
    algorithms from integration tests for service/runtime wiring when this
    affects defensibility or grading.
13. Run `thesis-literature-citation-review` when literature relevance, citation support, or source defensibility is material to the opponent assessment. For opponent work, use it only for relevance, defensibility, citation quality, and support for submitted claims; do not turn it into literature coaching.
14. Run `thesis-typography-formal-review` when the thesis is in final submission state or formal presentation may affect report quality. Use it as pattern evidence; do not turn it into a long typo inventory.
15. Run `thesis-theses-similarity-review` when an imported Theses.cz report is present. Keep no-concern or resolved matches internal; surface only reviewed unresolved/material concerns or manual checks, and do not expose raw report URLs/source internals.
16. Calibrate severity. Do not search for faults at any cost; identify strong parts with equal care. Distinguish an unsupported or overstated thesis claim from a serious defect in the work itself:
   - if a claimed runtime path is implemented and has a plausible alternate
     scene/profile/configuration, but the submitted default/build artifacts do
     not prove it was used, present it as an evidence or reproducibility
     uncertainty and a defense question, not as proof that the path was absent;
   - if a broad phrase such as "large scale", "modular", "easily extensible",
     "guaranteed", or "fully supported" is stronger than the evidence, surface
     the wording overclaim only at the severity justified by its practical
     impact;
   - keep minor overclaims as presentation/claim-calibration notes unless they
     affect assignment fulfillment, experimental conclusions, or a central
     implementation promise.
17. Use `docs/fit-is-rubric.md` as the shared checklist for FIT IS item coverage.
18. Use confidence labels for important statements:
   - `[FAKT]` directly verified from inputs,
   - `[INTERPRETACE]` reasonable conclusion from multiple inputs,
   - `[ODHAD]` likely but not fully verified,
   - `[NEOVERENO]` not verifiable from provided materials,
   - `[K RUCNI KONTROLE]` important but requires manual opponent verification.
19. In DEEP mode, run `thesis-opponent-materials-review` as an independent review pass before treating the materials as ready for writing the report. When a first draft was produced by another agent or model, have a different explicitly authorized reviewer agent run that review pass.
20. After the reviewed output exists, run `scripts/check-opponent-materials <case-id> [round-id]`. Fix hard failures before treating `outputs/oponent_podklady_revidovane.md` as ready. Warnings are operator prompts; resolve or explicitly accept them in the closeout.
21. After each role output is written, use `scripts/register-review-artifact`
    or its sidecar path so `work/review_manifest.json` records generator role,
    source hashes, checks, limitations, and synthesis use as the output is
    created. Then run `scripts/init-review-manifest --run-checks <case-id>
    [round-id]`, record generator/reviewer roles, covered evidence artifacts,
    checks, limitations, and compact `used_findings` summaries for each
    evidence artifact covered by synthesis in `work/review_manifest.json`, then
    run `scripts/check-review-manifest --require-complete <case-id> [round-id]`.
    If reviewed materials change afterward, the materials are draft again:
    rerun independent review and refresh
    `work/reviews/opponent_materials_review.json`, or record a hash-bound
    `work/review_deltas/*.json` via `scripts/record-review-delta` when the
    change is a bounded operator delta with a typed exception or profile-review
    reopening. Manifest refresh alone is insufficient. Finish optimized rounds
    with `scripts/review-round-closeout --profile opponent_materials <case-id>
    [round-id]`.

## Free-Text Boundary

Deterministic helper output is a prompt or structured evidence source, not a
substitute for semantic opponent review. Start from structured artifacts, role
handoffs, claim-basis refs, and reusable capsules; open exact free-form thesis,
README, notes, code, or generated-prose evidence only when needed for a material
verification trigger. Reusable conclusions must be recorded as structured
evidence with anchors. Do not turn raw keyword or token matches into assignment
fulfillment, IS-item wording, grading rationale, or report-ready findings.

For assignment coverage, the text/assignment role should create or update
`work/assignment_coverage_agent.json` before `scripts/check-assignment-coverage`
runs. The helper validates that structured artifact; it does not derive coverage
from thesis or report prose.

## When Using Agents

For a large opponent review, split reviewer agents by role:

- thesis text, structure, and assignment coverage,
- figure/media evidence, visual claims, captions, and figure changes,
- GitHub/PR intake and contribution scoping when code evidence comes from GitHub,
- code/reproducibility and text-code consistency,
- code quality/design, maintainability, runtime risks, and developer evidence,
- quantitative/result claims, units, baselines, practical magnitude, and reproducibility context,
- Theses.cz similarity-report context when an imported report is present,
- literature/citation relevance, source availability, and claim support,
- typography/formal presentation for final submitted text,
- evidence labels, severity, and grading calibration,
- synthesis into draft `work/oponent_podklady_draft.md` or `outputs/oponent_podklady.md`, followed by review into `outputs/oponent_podklady_revidovane.md`.

Use `work/opponent_packets/<role>.md` as the default handoff for each role when
available. The packets do not replace the skills or evidence checks; they make
the role scope, available inputs, reusable current evidence, missing inputs,
claim-basis triggers, and constraints explicit before agents start.

Follow `docs/agent-scheduling.md`: default to at most 2 concurrent spawned
workflow agents, use 1 on memory-constrained machines, and run roles in waves
instead of spawning every role at once. The concurrency limit must not remove
required role coverage, typography/formal limitations when needed, or the
independent review pass.

Use `scripts/check-review-wave --workflow opponent_materials --wave draft`
after draft generation and `--wave reviewed` after the independent review pass.
If the gate contradicts an agent's final message, trust the file/checker result
and repair the artifact or approval record.

The synthesis step must read each available `## Synthesis Handoff`,
`work/context/claim_review_basis.json`, and current
`work/context/evidence_capsules.json` capsule refs first. Open the full evidence
artifact only for grade-impacting verification, contradiction checks, missing
anchors, unresolved claim-basis triggers, confidence-label calibration, or
reviewer challenges.
Translate low-level diagnostics into report impact, grading/IS calibration, or
manual-check language; do not leak supervisor-style student-action wording into
opponent materials. The synthesis step must integrate findings into one
coherent operator artifact.

Do not leak internal packet paths, manifest hashes, private URLs, raw PR
metadata, review-thread details, local workspace paths, or generated-draft state
into opponent-facing prose. Convert them into evidence-backed findings,
confidence labels, limitations, and manual checks.

## Severity

- `P0`: can materially affect defensibility, assignment fulfillment, or grade.
- `P1`: significant weakness.
- `P2`: partial weakness worth considering.
- `P3`: minor issue, include only if repeated or relevant.

## Agent Final Response Contract

When acting as a workflow agent, write full materials or evidence content to the
owned round files and keep the chat final response compact. Do not paste full
Markdown artifacts that are already on disk.

Return only:

- files written or changed;
- top 3-5 findings, verdicts, or risks;
- commands/checks run;
- explicit limitations;
- whether expected output validation passed.

The main session must verify file claims with expected-output checks before
relying on them.

## Model And Reasoning

Use the strongest available model with high reasoning effort for this semantic
workflow. In the current Codex setup, use `gpt-5.5` with `xhigh` reasoning when
that choice is exposed. Packet prompts generated for this skill must carry the
same requirement. Do not downshift to Spark or another low-cost model for the
first or only pass over thesis text, code evidence, reviewed evidence,
opponent-materials synthesis, grading/report calibration, confidence labels, or
defense questions. Mechanical helper summaries may use cheaper models only when
validator-backed and consumed by a high-reasoning semantic pass.

## Output

Write `outputs/oponent_podklady.md` for the first generated materials. Agent-generated drafts should preferably go to `work/oponent_podklady_draft.md`; the review pass writes `outputs/oponent_podklady_revidovane.md`.

Before closeout, validate reviewed materials with:

```bash
scripts/check-opponent-materials <case-id> [round-id]
scripts/check-review-manifest --require-complete <case-id> [round-id]
```

```markdown
# Podklady pro oponentsky posudek

## 1. Rozsah kontroly

## 2. Strucna mapa prace

## 3. Technicke jadro prace vysvetlene oponentovi

## 4. Mapa textu, kodu a artefaktu

## 5. Splneni zadani

| Bod zadani | Opora v textu | Opora ve vystupu/kodu | Stav | Dopad |
|---|---|---|---|---|

## 6. Evidence ledger: hlavni tvrzeni a opora

| Tvrzeni | Znacka jistoty | Opora | Dopad na posudek | Pouzit do posudku? |
|---|---|---|---|---|

## 7. Silne stranky

## 8. Hlavni rizika a nedostatky

| Priorita | Tvrzeni | Evidence | Dopad | Mozna formulace do posudku |
|---|---|---|---|---|

## 9. Pokryti polozek IS a navrhy formulaci

| Polozka IS | Stav | Evidence | Dopad | Mozna formulace |
|---|---|---|---|---|

## 10. Technicka spravnost a realizacni vystup

Shrn text-code consistency i code-quality/design review. Jasne oddel, co je rozpor mezi textem a artefakty, co je technicke riziko implementace, a co zustalo jen k rucni kontrole. Standalone `outputs/code_consistency.md` a `outputs/code_quality_review.md` ber jako internal/operator evidence.

## 11. Experimenty, vysledky a reprodukovatelnost

Zahrn relevantni figure/media zjisteni, pokud grafy, tabulky, screenshoty nebo diagramy nesou vysledkova nebo funkcni tvrzeni. Vizualni tvrzeni pouzij jen tehdy, kdyz maji `pdf_inspected` nebo `source_asset_checked` status a claim alignment podporuje prislusne textove tvrzeni; jinak je formuluj jako omezeni nebo rucni kontrolu. Cache hashe, reuse metadata a nazvy internich evidence souboru nepřenášej do oponentskych podkladu.

## 12. Text, struktura, formalni stranka a literatura

Zhodnot strukturu textu vcetne nadpisu kapitol a podkapitol: delku, srozumitelnost, vztah k nasledujicimu obsahu, zbytecne opakovani slov z nadrazenych nebo sousednich nadpisu a jasne rozliseni navrhu, implementace, testovani, vysledku a diskuse. Shrn relevantni body z `outputs/literature_citation_review.md`, pokud byl tento review pouzit. Pokud byl pouzit `outputs/typography_formal_review.md`, zohledni jen opakovane vzorce a dopad na profesionalni uroven textu, ne seznam jednotlivych preklepu nebo radkovych problemu. U oponentskych podkladu res hlavne relevanci, obhajitelnost a oporu citaci pro tvrzeni v praci; nenavrhuj studentovi novou literaturu jako coaching.

## 13. Orientacni kalibrace hodnoceni

Uved konzervativni, standardni a mirnejsi interpretaci, pokud jsou rozumne obhajitelne. Pouzij intervaly, ne autoritativni bodovy verdikt.

## 14. Navrhy otazek k obhajobe

## 15. Rucni kontroly pred napsanim posudku
```

Use intervals and rationale for grading calibration, not false precision.
