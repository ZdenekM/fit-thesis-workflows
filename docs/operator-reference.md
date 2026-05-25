# Operator Reference

Tato stránka doplňuje hlavní `README.md`. Je určená pro situace, kdy už víte,
že chcete použít workflow, a potřebujete detailnější mapu výstupů, rolí nebo
diagnostiky. Nový vedoucí nebo oponent by měl začít v root `README.md`.

## Konverzační model

Primární rozhraní je chat s agentem. Prompt nemusí mít pevný formát: stačí říct,
jakou práci chcete zpracovat, jaký výstup očekáváte a kde jsou podklady. Agent
má rozlišit, jestli jde o průzkumnou otázku, pracovní draft, nebo finální
výstup vyžadující agentní review.

Pro finální studentskou zpětnou vazbu, posudky, oponentské podklady a
samostatnou interní evidenci napište v aktuálním požadavku výslovně
`použij agenty`. Bez toho má agent zastavit před sendable/final artefaktem a
vyžádat si autorizaci.

## Local RAG

Volitelný `mcp-local-rag` index slouží jen jako discovery vrstva pro rychlou
orientaci v Markdown dokumentaci, plánech, skills, profilech, case poznámkách a
generated Markdown výstupech. Není to evidence source pro posudek ani náhrada
za workflow kontroly; agent musí po nalezení kandidátního místa otevřít
autoritativní artefakt a citovat jeho cestu, sekci, stránku nebo řádek.
Databáze, model cache a retrieved private chunks musí zůstat mimo tracked
repozitář.

Při indexaci `cases/` nepoužívejte raw directory ingest bez explicitního scope
nebo exclude pravidel. Do RAG patří case metadata, `notes/`, `outputs/`, přímé
Markdown vstupy typu předchozí feedback, kurátorovaná GitHub intake shrnutí,
reviewer profily a operator-authored work summaries. Do RAG nepatří připravené
submitted-code workspaces, zejména `cases/**/work/code/**` a
`cases/**/work/submission_bundle/**`, raw GitHub intake diffy, patche, komentáře
nebo logy pod `inputs/github/**`, rozbalené odevzdané zdroje ve vnořených
`inputs/**` adresářích, `extracted/**` text práce ani jejich
vendor/dependency/build/cache dokumentace. Podrobnosti jsou v
`docs/local-rag-usage.md`.

`BASE_DIRS` neberte jako bezpečný file-level allowlist. Pokud v lokálním MCP
configu zůstává široký root typu `cases/`, jen zpřístupňuje cílené soubory; bulk
ingest musí pořád používat kurátorovaný scope nebo explicitní bezpečné subrooty.

Typický přínos je triage při širokých historických dotazech: když by přesné
vyhledání v Markdownu našlo desítky plánů, docs nebo skills, RAG má nejdřív
zúžit kandidáty na několik pravděpodobných zdrojů a teprve ty agent otevře
přímo.

## Case Layout

Lokální case workspace má tento tvar:

```text
cases/<case-id>/
  case.md
  current-round.txt
  rounds/
    <timestamp>-<label>/
      notes/
      inputs/
      extracted/
      work/
      outputs/
```

`cases/` je ignorované gitem. Vstupy zůstávají v `inputs/`, extrahovaný text v
`extracted/`, pracovní evidence a manifesty ve `work/` a lidsky čitelné výstupy
v `outputs/`.

Odevzdané PDF je autoritativní renderovaná verze práce. LaTeX/Overleaf zdroje
jsou pomocná vrstva pro diff, search a přesné evidence anchors. Agent nemá
LaTeX běžně kompilovat, pokud výslovně nechcete build diagnostiku nebo není
k dispozici renderované PDF.

## Další Prompt Příklady

### Jen Import A Příprava Kontextu

```text
Zatím jen založ case a importuj vstupy. Neprodukuj finální feedback. Vyplň
poznámky k zadání, rozbal kód pod work/code a řekni mi, co ještě chybí pro
studentskou zpětnou vazbu od vedoucího.
```

### Finální Kontrola Před Odevzdáním

```text
Pro aktuální round udělej finální kontrolu před odevzdáním. Priorita:
splnění zadání, technická pravdivost, chybějící soubory, výsledky,
README/reprodukovatelnost a obhajitelnost. Použij agenty a nálezy oprav ve
feedbacku.
```

### Revizní Diff

```text
Porovnej aktuální round s předchozí verzí práce. Zaměř se na to, co z minulé
zpětné vazby bylo vyřešeno, co zůstává a co je nové riziko. Použij agenty.
```

Pokud operátor říká, že student doplnil nebo změnil aktuální materiály, agent
má před draftingem ověřit, že case obsahuje odpovídající novější PDF, source zip
nebo code artefakt. Když nejnovější podklady v case tomu neodpovídají, má si
nové materiály vyžádat nebo review jasně označit jako provizorní.

### Kód Nebo PR Na GitHubu

```text
Student pracoval formou příspěvku do upstream projektu.
Upstream repo: https://github.com/owner/project
PR: https://github.com/owner/project/pull/123
GitHub login studenta: <login>
Nejdřív udělej GitHub code intake: metadata PR, diff, komentáře, review a CI
stav. Potom použij jen ověřené závěry pro soulad textu s kódem a code-quality
review. Použij agenty.
```

Pokud neznáte přesný seznam PR, uveďte upstream repo a autorův GitHub login.
Agent může použít read-only vyhledání PR podle autora a výsledek uložit jako
zmrazenou evidenci v case workspace.

Pokud je k dispozici submitted archive i GitHub zdroj, submitted archive je
autoritativní odevzdávka, pokud case nebo round notes výslovně neříkají, že
GitHub snapshot je odevzdaný zdroj. Pokud tyto dvě vrstvy nebyly porovnané, musí
to downstream review nést jako omezení.

## Výstupy

Nejběžnější výstupy:

- `outputs/feedback_student.md` - studentská zpětná vazba,
- `work/feedback_student_draft.md` - pracovní draft před nezávislým review,
- `outputs/revision_diff.md` - rozdíl proti předchozí verzi,
- `outputs/github_code_intake.md` - interní evidence GitHub repo/PR importu,
- `outputs/code_consistency.md` - interní kontrola souladu textu a kódu,
- `outputs/code_quality_review.md` - interní code-quality/design review,
- `outputs/literature_citation_review.md` - interní kontrola literatury a
  citací,
- `outputs/figure_media_review.md` - interní kontrola obrázků, tabulek,
  screenshotů, grafů a jejich změn mezi revizemi,
- `outputs/typography_formal_review.md` - interní pozdní kontrola typografie a
  formální stránky podle jazyka práce,
- `outputs/theses_similarity_review.md` - interní review Theses.cz reportu,
- `outputs/vedouci_posudek_revidovany.md` - revidovaný draft posudku vedoucího,
- `outputs/oponent_podklady_revidovane.md` - revidované oponentské podklady,
- `outputs/oponent_posudek_navrh.md` - čistý návrh oponentského posudku pro IS,
- `outputs/feedback_k_posudku.md` - review návrhu posudku.

Důležité interní sidecary ve `work/`:

- `work/review_manifest.json` - manifest vstupů, výstupů, helper checků,
  role agentů, review stavu, hashů a omezení,
- `work/agent_coverage.json` - coverage povinných agentních rolí,
- `work/review_run_trace.json` - round-start, role-plan, role-wave, synthesis,
  independent-review, operator-delta a closeout stopa,
- `work/operation_log.jsonl` - append-only provozní log nestandardních kroků,
  selhání, přeskočení, ručních fallbacků a kalibračních rozhodnutí,
- `work/reviews/*_review.json` - hash-bound approval záznamy pro finální nebo
  standalone evidenční použití,
- `work/review_deltas/*.json` - post-review opravy, námitky a typované výjimky,
- `work/quantitative_claims.json` - strukturované kvantitativní/result claimy,
  jednotky, baseline, praktický kontext a reprodukovatelnost,
- `work/theses_similarity/intake.json` a
  `work/theses_similarity/assessment.json` - import a kontextové posouzení
  Theses.cz reportu,
- `work/figure_media/visual_inventory.jsonl` - znovupoužitelný inventář
  vizuálních prvků,
- `work/code_reproducibility.json` - statická klasifikace reprodukovatelnosti
  kódového podkladu.

Studentský feedback, formální posudek vedoucího, oponentské materiály a návrh
oponentského posudku musí projít nezávislou review smyčkou. Po materiální úpravě
se výstup znovu bere jako draft a potřebuje nové review nebo strukturovanou
review deltu podle profilu.

## Povinné Gate Před Generováním

Před studentskou zpětnou vazbou od vedoucího agent spouští
`check-supervisor-ready <case-id> [round-id]`. Brána ověřuje zadání, deadline
kontext a reviewer profile. Před draftingem má také ověřit konfiguraci jazyka
feedbacku přes `check-feedback-language --config-only <case-id> [round-id]`.
Když některá brána selže, agent nemá psát sendable feedback a má si vyžádat
chybějící vstupy.

Před oponentskými podklady agent spouští `check-round-ready <case-id>
[round-id]` a podle kontextu navazující `opponent-preflight`. Tyto kontroly
nejsou jen diagnostika: určují, jestli je možné spustit role agenty bez
zamlčených materiálních omezení.

`case-doctor <case-id> [round-id]` zůstává read-only snapshot. Pomáhá se
zorientovat, ale nenahrazuje workflow gates ani finální closeout.

## Round Lifecycle

Normální agentní workflow nejde přímo od readiness checku k syntéze. Sdílená
kostra je:

1. `review-round-start --profile <workflow-profile> <case-id> [round-id]`
   zaregistruje aktuální materiály, obnoví evidence snapshot a zapíše
   `work/review_run_trace.json`.
2. `prepare-review-round --profile <workflow-profile> <case-id> [round-id]`
   připraví role packets a `work/review_role_plan.json`.
3. Parent agent spustí autorizované role agenty podle plánu a po hlavních
   vlnách použije příslušné `check-review-wave` gate.
4. Po syntéze a nezávislém review se workflow zavře přes
   `review-round-closeout --profile <workflow-profile> <case-id> [round-id]`
   nebo přes profilový closeout, který z něj vychází.

Přímé packet příkazy jako `prepare-opponent-packets` nebo
`prepare-supervisor-packets` jsou nižší helper vrstva. Nemají nahrazovat
`prepare-review-round`, pokud workflow skill nebo plán výslovně neříká jinak.

## Posudek Vedoucího

Formální posudek vedoucího má vlastní reportovou cestu. Nestačí jen napsat
Markdown draft.

1. Agent ověří `check-supervisor-report-ready <case-id> [round-id]`, včetně
   reportového vstupu vedoucího.
2. Role packets připraví jen po explicitním `použij agenty`; přitom obnoví
   current evidence a materiality pro `supervisor_report`.
3. Parent agent vytvoří `work/supervisor_report_trace.json` a pracovní draft.
4. Jiný autorizovaný agent provede nezávislé review posudku.
5. Před IS se obnoví manifest, potvrdí známka/body/oficiální text a neveřejný
   komentář a workflow se zavře přes `supervisor-report-closeout`.

Neprůkazný předchozí feedback nemá nahrazovat vstup vedoucího k aktivitě,
samostatnosti, komunikaci, konzultacím, dokončování nebo neveřejnému komentáři.

## Role A Review Smyčky

Pro větší práci se agentní review dělí podle rolí, typicky:

- text, struktura a splnění zadání,
- obrázky, tabulky, screenshoty, grafy, captiony a změny vizuální evidence,
- GitHub/PR intake, pokud je kód dostupný přes repo URL nebo upstream PR,
- soulad textu s kódem,
- kvalita kódu, design, runtime rizika a reprodukovatelnost,
- literatura a citace,
- pozdní typografie a formální stránka,
- Theses.cz report podobnosti,
- kvantitativní/result claimy,
- kalibrace evidence a tvrzení,
- syntéza do finálního Markdownu,
- nezávislé review finálního artefaktu.

Stabilní Codex agent role profily a jejich vazba na repo-local skilly jsou v
[Agent Profile Matrix](agent-profile-matrix.md). Paralelní review znamená
pokrytí rolí, ne neomezený počet živých agentů. Výchozí limit a wave sequencing
popisuje [Agent Scheduling](agent-scheduling.md).

Když je v roundu kód, supervisor feedback, formální posudek vedoucího a
oponentské podklady mají použít kontrolu souladu textu s kódem i kontrolu
kvality implementace. Pokud jedna z kontrol nejde provést, výstup má nést
konkrétní typed limitation.

## Specializované Evidence

GitHub/PR práce nejdřív potřebuje read-only GitHub intake. U upstream PR se
nehodnotí celý upstream projekt jako studentův výstup; baseline a rozsah práce
se posuzují podle PR diffů, commitů, testů, dokumentace, review diskuse, CI a
deklarovaného scope.

Kvantitativní, evaluační a výsledková tvrzení vyžadují sémantickou kontrolu
jednotek, škály, baseline, praktické velikosti efektu, reprodukovatelnosti a
přiměřenosti interpretace. Strukturovaný handoff vzniká přes
`thesis-quantitative-claims-review` do `work/quantitative_claims.json`.

Figure/media workflow vytváří interní inventář obrázků, tabulek, screenshotů,
grafů a jejich změn. Textový extract sám o sobě stačí na inventář a caption
claims; tvrzení o tom, co obrázek skutečně ukazuje, vyžaduje PDF detail/vision
kontrolu nebo source asset svázaný s renderovaným PDF. Volitelná vrstva je
popisaná v [PDF Detail Layer](pdf-detail-layer.md).

Theses.cz report podobnosti se importuje do ignorovaného case workspace a
posuzuje samostatně. Čistý nebo vysvětlený report se ve feedbacku ani posudku
standardně nezmiňuje. Podezřelé, nevysvětlené nebo institucionálně důležité
shody musí projít kontextovým review; procento podobnosti samo o sobě není
důkaz plagiátu.

## Diagnostika

Skripty jsou hlavně guardy pro agenta. Ručně je obvykle volat nemusíte. Typické
zadání v chatu:

```text
Spusť readiness a privacy kontroly pro aktuální case a řekni mi, co chybí.
```

Základní logické workflow příkazy:

```bash
scripts/case-doctor <case-id>
scripts/check-supervisor-ready <case-id>
scripts/check-round-ready <case-id>
scripts/opponent-preflight <case-id>
scripts/check-private
```

`case-doctor` je read-only snapshot. Ukáže aktivní round, readiness checky,
deadline kalibraci, vstupy, extracty, kód, výstupy, review manifest a předchozí
feedback. Nenahrazuje finální gate checky.

Časté finální kontroly:

```bash
scripts/check-feedback-output <case-id>
scripts/check-feedback-language <case-id>
scripts/check-opponent-materials <case-id>
scripts/check-opponent-report --mode canonical <case-id>
scripts/export-opponent-report <case-id>
scripts/check-opponent-report --mode clean <case-id>
scripts/check-code-consistency <case-id>
scripts/check-code-quality-review <case-id>
scripts/check-literature-citation-review <case-id>
scripts/check-revision-diff <case-id>
scripts/check-typography-formal <case-id>
scripts/check-theses-similarity-report <case-id>
scripts/init-review-manifest --run-checks <case-id>
scripts/check-agent-coverage <case-id>
scripts/check-review-manifest --require-complete <case-id>
```

Tvary `scripts/<tool>` jsou Linux/dev zkratka a zároveň logické názvy workflow
příkazů. Na Windows nejdřív zabalte nástroje přes
`scripts\package-workflow-tools.cmd` nebo `.\scripts\package-workflow-tools.ps1`
a potom používejte `dist\workflow-tools\bin\<tool>.cmd` nebo odpovídající
PowerShell launcher. Přesný command contract je v
[Workflow Command Surface](workflow-command-surface.md).

## Reviewer Profily A Jazyky

`case.md` typicky obsahuje:

```text
Thesis language: auto
Student feedback language: cs
Reviewer profile: default
```

Chybějící jazyk feedbacku znamená `cs`. `Thesis language` může být `cs`, `sk`,
`en` nebo `auto` a řídí kontroly textu práce, ne jazyk studentského feedbacku.
Slovenská práce se ve výstupu dál hlásí jako `sk`, ale typografická pravidla
sdílí česko-slovenskou rodinu kontrol.

Veřejný repozitář obsahuje jen `profiles/default.md`. Osobní preference patří
pod ignorované cesty:

```text
profiles/local/default.md
profiles/local/<profile-id>.md
```

Profily jsou preference, ne tvrdá workflow pravidla. Nemohou přepsat soukromí,
evidenční požadavky, readiness gate, jazyk výstupu ani povinnost říct, co nebylo
ověřeno. Podrobnosti jsou v [Profiles](../profiles/README.md).

## Podrobnější Workflow Reference

- [Opponent Review Workflow](opponent-review-workflow.md) - pořadí oponentské
  přípravy, role packetů, validátorů a closeoutu.
- [Workflow Command Surface](workflow-command-surface.md) - command categories,
  packaged launchers a Windows boundary.
- [Serena Code Navigation](serena-code-navigation.md) - práce s připravenými
  code roots a symbol-aware navigací.
- [Agent Scheduling](agent-scheduling.md) - role waves, handoff tvar a failure
  handling.
- [Agent Profile Matrix](agent-profile-matrix.md) - role profily, allowed writes
  a review separation.
