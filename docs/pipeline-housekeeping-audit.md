# Pipeline Housekeeping Audit

Date: 2026-05-13

## Scope

Audit zkontroloval instrukce pro agenty, repo-local skills, workflow dokumentaci,
aktivni plany, TODO stav a lehke hygiene signaly. Neoteviral soukroma case data
pod `cases/`.

Pouzite prikazy:

```bash
git status --short --untracked-files=all
rg --files -g 'AGENTS.md' -g 'README.md' -g 'TODO.md' -g 'WORKFLOW_MEMORY.md' -g '*.md' .agents docs plans scripts
rg -n "explicitly authorizes|použij agenty|independent review|check-agent-coverage|DEEP|FAST|STANDARD|mode" AGENTS.md README.md docs .agents/skills plans/*.md -g '*.md'
rg -n "check-supervisor-ready|check-round-ready|case-doctor|init-review-manifest|check-review-manifest|check-review-wave|prepare-supervisor|prepare-opponent" AGENTS.md README.md docs .agents/skills plans/*.md -g '*.md'
rg -n "read all|inspect all|Open full|packet|common_briefing|evidence_capsules|claim_review_basis|reuse|stale|hash|unchanged" AGENTS.md README.md docs .agents/skills plans/*.md -g '*.md'
scripts/check-scripts
scripts/check-private
scripts/audit-context-budget --help
pants run :jscpd
pants run :vulture
pants run :omen
git log --oneline --decorate -12 -- plans/token_efficiency_reuse_plan.md TODO.md docs/dev-hygiene.md tests/test_import_theses_report.py src/thesis_review_workflow/structured_evidence.py src/thesis_review_workflow/cli/check_review_manifest.py
```

## Executive Summary

Nevidim jeden fatalni rozpor typu "jedno pravidlo rika opak druheho" v jadrovych
branach. DEEP mode, explicitni autorizace agentu, code-consistency plus
code-quality pro code-bearing roundy, Windows command routing, review manifesty a
nezavisla review smycka jsou napric `AGENTS.md`, README a skilly vetsinou
konzistentni.

Hlavni problem je jinde: repo rychle roste a stavove/indexacni artefakty uz
nestihaji uklizet po dokoncenych zmenach. To muze agentum zbytecne brat kontext,
vest je k praci na hotovych vecech, nebo rozostrit, ktere role a kontroly jsou
opravdu k dispozici.

## Findings

### P1 - Aktivni token-efficiency plan je implementovany, ale porad otevreny

`plans/token_efficiency_reuse_plan.md` ma porad `Status: active`
(`plans/token_efficiency_reuse_plan.md:3`) a final audit hlasi `Not started`
(`plans/token_efficiency_reuse_plan.md:1103-1105`). Soucasne ale plan zaznamenava
dokonceni vsech jedenacti slices a posledni commit je `feat(workflow): add context
budget audit` (`plans/token_efficiency_reuse_plan.md:830-844`, `git log`:
`95f169c`).

Impact: budouci agenti mohou brat uz hotove zmeny jako nedodelanou aktivni praci,
nebo prepisovat navazujici TODO bez jasne hranice. Tohle primo skodi efektivite
pipeline, protoze plan je dnes hlavni resume kontrakt pro velkou cast reuse a
context-budget prace.

Recommended next action: udelat final audit planu, zmenit status na `done` nebo
`superseded`, zkopirovat skutecne zbytky do `TODO.md` a plan archivovat.

### P1 - TODO obsahuje polozky, ktere vypadaji uz implementovane

`TODO.md` je jediny predexistujici dirty soubor (`git status`: `M TODO.md`), takze
jsem ho neupravoval. Obsahuje ale P0 polozku pro submitted supervisor reporty a
post-review wording amendments (`TODO.md:5-10`). Token-efficiency plan pritom
zaznamenava, ze Slice 9 pridal `record-submitted-supervisor-report` a
`record-report-amendment` vcetne smoke/test closeoutu
(`plans/token_efficiency_reuse_plan.md:876-896`), a command registry tyto prikazy
opravdu obsahuje (`src/thesis_review_workflow/commands.py:62-63`).

Impact: TODO prestava byt duveryhodny durable open-work index. Agent muze zacit
implementovat hotovy helper, misto aby resil skutecny zbytek, napr. dokumentacni
closeout nebo operator UX.

Recommended next action: po final auditu token-efficiency planu projit `TODO.md`
a nechat jen nedodelane casti. Dokoncene podbody smazat, ne nechavat zaskrtnute.

### P1 - Session-start hook zminuje jen malou cast dnesni skill surface

Hook `session_start_context.py` agentum pripomina jen supervisor feedback,
opponent materials, revision diff, code consistency a code quality
(`.codex/hooks/session_start_context.py:14-25`). `AGENTS.md` a README mezitim
routuje podstatne sirsi sadu workflow skillu: supervisor report, GitHub intake,
quantitative claims, literature/citation, figure/media, typography/formal,
Theses.cz similarity a historickou kalibraci (`AGENTS.md:52-69`,
`README.md:654-674`).

Impact: startovni kontext muze nevedomky biasovat agenta k puvodnimu uzsimu
workflow a prehlizet specializovane role, ktere maji velky dopad na kvalitu
pipeline, hlavne figure/media, literature, typography a similarity review.

Recommended next action: zkratit hook na "read AGENTS and use repo-local skills"
plus par skutecne kritickych bran, nebo ho generovat ze seznamu skillu. Pokud ma
zustat explicitni, aktualizovat ho na aktualni role surface.

### P1 - Specialisticke Codex agent profily nepokryvaji vsechny povinne role

`.codex/config.toml` definuje jen pet specializovanych agentu: text, code
consistency, code quality, quantitative claims a evidence calibrator
(`.codex/config.toml:16-34`). Workflow ale popisuje role pro figure/media,
literature/citation, typography/formal, Theses.cz similarity, supervisor report,
opponent materials a report review (`AGENTS.md:112-121`, `README.md:654-674`).

Impact: role coverage je dokumentacne povinna, ale pro cast roli neni jasny
spustitelny agent profile, model/reasoning default ani ownership. V praxi se to
da obejit default agentem a skill promptem, ale pak je kvalita mene opakovatelna
a hure auditovatelna.

Recommended next action: bud pridat missing role profiles, nebo do
`docs/agent-scheduling.md` explicitne namapovat specializovane skilly na existujici
profily a prompt template. U roli s vlastnim output schema je lepsi mit explicitni
profil.

### P1 - Dev-hygiene baseline je zastarala

`docs/dev-hygiene.md` tvrdi baseline `pants run :vulture` bez hlaseni, `:jscpd`
4 klony / 0.74 %, a `:omen` score 93.50 s 3 critical a 7 high hotspoty
(`docs/dev-hygiene.md:44-56`). Aktualni beh ukazal:

- `pants run :vulture` selhal na nepouzitem `root_arg` v
  `tests/test_import_theses_report.py:48` a `tests/test_import_theses_report.py:146`;
- `pants run :jscpd` nasel 17 klonu, 440 duplicitnich radku, 1.28 %;
- `pants run :omen` prosel, ale hlasi score 90.60, 9 critical a 15 high hotspotu,
  vcetne `structured_evidence.py`, `check_review_manifest.py`,
  `init_review_manifest.py`, `review_materiality.py`, `opponent_calibration.py`
  a `import_github_code.py`.

Impact: hygiene dok uz neodpovida realite a prestava fungovat jako kalibracni
signal. Hotspoty jsou hlavne v jadrovych manifest/materiality/structured-evidence
modulech, tedy presne tam, kde chyba umi znehodnotit pipeline vysledky.

Recommended next action: nejdriv opravit vulture nalezy, pak aktualizovat baseline
v `docs/dev-hygiene.md`. Nasledne zalozit uzky refaktor plan pro validacni a
calibration-profile duplicity, ne plosny cleanup.

### P2 - Command-routing pravidlo je hodne duplikovane a jen castecne lintovane

Windows/logical-command pravidlo je v `AGENTS.md`, README, nekolika docs a na
zacatku kazdeho skillu (`AGENTS.md:12`, `AGENTS.md:46`,
`.agents/skills/thesis-supervisor-feedback/SKILL.md:8-11`,
`docs/workflow-command-surface.md:3-23`). `scripts/check-scripts` kontroluje
zakladni markery ve vsech skillech (`src/thesis_review_workflow/cli/check_scripts.py:73-76`,
`src/thesis_review_workflow/cli/check_scripts.py:146-154`), ale nekontroluje
semantickou shodu celeho textu.

Impact: dnes to neni rozpor, ale je to drift risk. Pri dalsi zmene command surface
se muze cast instrukci zmenit a cast zustat stara.

Recommended next action: ponechat skilly self-contained, ale udelat jeden canonical
snippet nebo checklist s presnym textem a pridat lightweight linter, ktery hlida
shodu nebo explicitni "see README command routing" formuli.

### P2 - Context-budget audit meri round artefakty, ne instrukcni naloz

Novy `scripts/audit-context-budget` meri `work/common_briefing.json`,
role packety, capsules, claim basis, structured handoffs a raw sources
(`src/thesis_review_workflow/context_budget.py:26-74`). Je to uzitecne, ale
nezachyti vzdy nalozeny repo kontext: `AGENTS.md`, README, dlouhe skill texty,
session hook, developer instrukce a opakovane command-routing bloky.

Impact: round muze projit context-budget auditem, ale agent porad muze startovat
s prilis velkym nebo duplicitnim instrukcnim kontextem. To primo souvisi s tim,
na co se ptal tento audit: instrukcni duplicity a pipeline efektivita.

Recommended next action: rozsirit audit o repo-instruction mode, napr.
`scripts/audit-context-budget --repo-instructions`, ktery secte/porovna
`AGENTS.md`, README, docs routing sekce, skilly a hook texty, a oznaci duplicitni
nebo out-of-sync bloky.

### P2 - Plany nemaji automatickou stale-state kontrolu

Plan contract rika, ze aktivni plany maji status, progress a final audit
(`plans/README.md:39-55`) a hotove plany se maji archivovat
(`plans/README.md:23-31`). Stav repa ale ukazuje aktivni plan s dokoncenyma
slicema a neuzavrenym final auditem (`plans/token_efficiency_reuse_plan.md:3`,
`plans/token_efficiency_reuse_plan.md:828-844`,
`plans/token_efficiency_reuse_plan.md:1103-1105`).

Impact: problem neni jen jeden soubor. Chybi mechanicky check, ktery by rek:
"plan ma vsechny slices done/complete, ale status neni done a final audit neni
vyplneny". Bez nej se plan/TODO drift bude opakovat.

Recommended next action: pridat `scripts/check-plans` nebo rozsireni
`scripts/check-scripts`, ktere najde aktivni plan s dokoncenymi slices, `Ready to
commit` v historickem progressu po commitu, `Final Audit: Not started`, a TODO
polozky odkazujici na archivovany/dokonceny plan.

### P3 - Duplicitni validacni patterny zacinaji byt v konkretni casti codebase

`pants run :jscpd` ukazal mimo jine duplicity mezi:

- `opponent_closeout.py` a `supervisor_report_closeout.py`;
- `check_opponent_materials.py`, `check_figure_media_review.py`,
  `check_feedback_output.py` a `check_typography_formal.py`;
- `check_opponent_calibration_profile.py` a
  `check_supervisor_report_calibration_profile.py`;
- `claim_review_basis.py` a `evidence_capsules.py`.

Impact: cast duplicity je legitimni, protoze workflow artefakty jsou podobne.
Riziko je hlavne v validacich a closeoutech: male rozdily mohou casem znamenat,
ze supervisor a opponent pipeline bude stejny princip vynucovat jinak.

Recommended next action: nerefactoringovat plosne. Zalozit maly navazujici plan
jen pro validacni helpery s jasnym cilem: sdilet tvar kontroly tam, kde jsou
semanticky stejne, a ponechat explicitni rozdily tam, kde workflow potrebuje
odlisny kontrakt.

## Positive Controls

- `scripts/check-scripts` prosel a uz hlida Windows command-surface markery i ve
  skillech.
- `scripts/check-private` prosel, bez zjevneho presunu soukromych case dat do
  tracked prostoru.
- Token-efficiency prace uz zavedla `work/common_briefing.json`, reuse index,
  evidence capsules, claim-review basis, submitted-report capture, amendment
  records a context-budget audit. To jsou spravne systemove kroky; otevreny
  problem je hlavne jejich closeout, dokumentacni smireni a dalsi guardy proti
  driftu.

## Recommended Order

1. Uzavrit a archivovat `plans/token_efficiency_reuse_plan.md`.
2. Reconciliovat `TODO.md` proti tomu, co uz plan a commity opravdu dorucily.
3. Opravit `pants run :vulture` nalezy a aktualizovat `docs/dev-hygiene.md`.
4. Rozhodnout, jestli missing review role dostanou vlastni `.codex/agents/*`
   profily, nebo explicitni mapovani na existujici profily.
5. Pridat mechanicky `check-plans` / instruction-drift audit, aby se stale plan,
   stale TODO a skill-command-routing drift neopakovaly.
