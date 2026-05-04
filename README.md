# FIT Thesis Workflows

Human-first workflow pro vedení a oponování BP/DP prací s pomocí agentů.

Tento repozitář není aplikace pro studenty. Je to pracovní vrstva pro vedoucí,
oponenty a další hodnotitele, kteří chtějí přes chat s agentem zpracovat
odevzdané PDF, zdrojové soubory, kód, předchozí zpětné vazby a vlastní poznámky.

Typické použití není ruční volání skriptů. Typické použití je napsat agentovi:

```text
Přidej nový případ pro tuto BP. Přikládám zadání, PDF práce, zdrojový zip,
kód a moje poznámky. Připrav studentovi zpětnou vazbu, použij agenty,
zkontroluj soulad textu s kódem a kvalitu implementace a nálezy po review
rovnou oprav.
```

Výsledkem má být použitelný Markdown pro vedoucího nebo oponenta, ne jen
seznam interních poznámek.

Když se při konkrétní práci ukáže problém, který se bude pravděpodobně opakovat
i u dalších prací, agent ho má po dokončení výstupu nabídnout k promítnutí do
workflow. Typicky nejde o case-specifickou věc, ale o obecnou kontrolu, šablonu,
skill pravidlo nebo TODO pro budoucí helper.

## Nejrychlejší cesta

1. Otevřete chat s agentem v tomto repozitáři.
2. Přiložte nebo uveďte cesty k souborům: zadání, aktuální PDF práce,
   případně LaTeX/Overleaf zip, kód, starší feedback, návrh posudku nebo
   vlastní poznámky.
3. Napište, jaký výstup chcete: studentskou zpětnou vazbu, oponentské podklady,
   revizní diff, kontrolu kódu, kontrolu citací, nebo review hotového posudku.
4. Pokud má vzniknout finální výstup, nebo samostatná evidence, na kterou se
   budete spoléhat, napište výslovně `použij agenty`. Workflow to vyžaduje pro
   nezávislou review smyčku.
5. Agent si vyžádá chybějící kontext, založí nebo doplní case, zpracuje vstupy
   v ignorovaném workspace a uloží výstupy do aktivního roundu.

Case data pod `cases/` jsou ignorovaná gitem. Do repozitáře patří workflow,
skripty, šablony a profily, ne soukromé studentské materiály.

## Co napsat agentovi

Níže jsou copy-paste recepty. První tři pokrývají nejběžnější práci; další
příklady jsou pro speciálnější situace.

### Nová studentská zpětná vazba

```text
Přidej nový případ pro práci.

Typ: BP/DP
Akademický rok: 2025/2026
Deadline: standard / YYYY-MM-DD
Jazyk feedbacku: cs/en
Reviewer profile: default
Téma: <stručně>
Moje poznámky k zadání: <co student měl dělat, kontext laboratoře, omezení>

Přikládám zadání, aktuální PDF práce, případně zdrojový zip a kód.
Zpracuj studentskou zpětnou vazbu, použij agenty. Pokud je dostupný kód,
zkontroluj soulad textu s kódem i kvalitu implementace. Výsledný feedback
napiš tak, abych ho mohl poslat studentovi s minimální úpravou.
```

Pokud některý řádek nevíte, nechte ho prázdný nebo napište `nevím`. Agent má
říct, jestli je to skutečný blocker.

### Aktuální revize se starší zpětnou vazbou

```text
Tady je aktuální stav práce a předchozí zpětná vazba. Založ nový round ve
stávajícím case, porovnej posun od minule a připrav studentovi krátký
final-sprint feedback. Použij agenty, dej jim dost času, nálezy z review oprav.
```

### Oponentské podklady

```text
Připrav interní oponentské podklady pro tuto BP/DP. Přikládám zadání, PDF,
zdroje a kód. Použij agenty. Pokud je dostupný kód, zkontroluj soulad textu
s kódem i kvalitu implementace. Výstup má být interní evidence pro oponenta,
ne studentský feedback.
```

## Další příklady

### Jen import a příprava kontextu

```text
Zatím jen založ case a importuj vstupy. Neprodukuj finální feedback. Vyplň
poznámky k zadání, rozbal kód pod work/code a řekni mi, co ještě chybí pro
studentskou zpětnou vazbu od vedoucího.
```

### Finální kontrola před odevzdáním

```text
Pro aktuální round udělej finální kontrolu před odevzdáním. Priorita:
splnění zadání, technická pravdivost, chybějící soubory, výsledky,
README/reprodukovatelnost a obhajitelnost. Použij agenty a nálezy oprav ve
feedbacku.
```

### Revizní diff

```text
Porovnej aktuální round s předchozí verzí práce. Zaměř se na to, co z minulé
zpětné vazby bylo vyřešeno, co zůstává a co je nové riziko. Použij agenty.
```

### Review vlastního posudku

```text
Tady je můj draft oponentského posudku. Zkontroluj férovost, oporu v důkazech,
tón, konzistenci bodů/známky, pokrytí zadání a otázky k obhajobě. Použij
agenty. Nálezy rovnou promítni do revidované verze nebo mi vrať blokující
připomínky.
```

### Samostatná kontrola kódu

```text
Udělej samostatný review kódu pro aktuální round. Odděl nesoulad textu s kódem,
design/runtime rizika a nice-to-have zlepšení. Použij agenty.
```

### Kód nebo PR na GitHubu

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

## Co agent potřebuje vědět

Čím konkrétnější zadání dostane, tím méně bude muset hádat. Nejvíc pomáhá:

- oficiální zadání nebo jeho věrné shrnutí,
- vaše neveřejné poznámky ke kontextu práce,
- zda jde o BP nebo DP,
- jazyk práce (`cs`, `en`, nebo `auto`), pokud ho nelze spolehlivě poznat z PDF,
- akademický rok a případný posunutý termín,
- fáze práce: raná kostra, pracovní verze, předfinální verze, finální kontrola,
- co chcete explicitně ověřit,
- co už nechcete v této fázi znovu otevírat,
- jazyk studentského feedbacku, pokud nemá být výchozí čeština,
- reviewer profile, pokud nemá být výchozí `default`.

Chybějící jazyk feedbacku znamená `cs`. Chybějící reviewer profile znamená
`default`. Agent se má zastavit hlavně tehdy, když chybí zadání, termínový
kontext, validní profile soubor, nebo jiné podklady nutné pro požadovaný výstup.

## Co se děje pod kapotou

Repo používá lokální case workspace:

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

Vstupy zůstávají v ignorovaném `cases/`. PDF text se extrahuje do `extracted/`,
zdrojové zippy a kód se pro inspekci rozbalují pod `work/`.

Odevzdané PDF je autoritativní renderovaná verze práce. LaTeX/Overleaf zipy jsou
pomocná vrstva pro hledání, diff a přesnou evidenci. Agent nemá LaTeX běžně
kompilovat, pokud výslovně nechcete build diagnostiku nebo nemáte k dispozici
renderované PDF.

### Volitelná PDF detail vrstva

Pro běžné textové review stačí `pdftotext -layout`. Pokud chcete používat
cílenou analýzu obrázků, tabulek, layoutu nebo nejasných PDF míst, hodí se
volitelný `pdf-reader-mcp`. Není to hard dependency celého workflow; bez něj má
agent použít dostupný textový extract, source assety svázané s renderovaným PDF
a zapsat omezení.

`pdf-reader-mcp` vyžaduje Node.js 22 nebo novější. Instalace pro Codex:

```bash
codex mcp add pdf-reader -- npx @sylphx/pdf-reader-mcp
```

Po instalaci stačí v chatu říct, že má agent udělat figure/media review nebo
zkontrolovat konkrétní stránky/obrázky. Podrobnější pravidla jsou v
`docs/pdf-detail-layer.md`.

## Výstupy

Nejběžnější výstupy jsou:

- `outputs/feedback_student.md` - studentská zpětná vazba,
- `work/feedback_student_draft.md` - pracovní draft před nezávislým review,
- `outputs/revision_diff.md` - rozdíl proti předchozí verzi,
- `outputs/github_code_intake.md` - interní evidence GitHub repo/PR importu,
- `outputs/code_consistency.md` - interní kontrola souladu textu a kódu,
- `outputs/code_quality_review.md` - interní code-quality/design review,
- `outputs/literature_citation_review.md` - interní kontrola literatury a citací,
- `outputs/figure_media_review.md` - interní kontrola obrázků, tabulek,
  screenshotů, výsledkových grafů a jejich změn mezi revizemi,
- `outputs/typography_formal_review.md` - interní pozdní kontrola typografie
  a formální stránky podle jazyka práce,
- `work/figure_media/visual_inventory.jsonl` - znovupoužitelný interní inventář
  vizuálních prvků a jejich popisů,
- `work/review_manifest.json` - interní manifest vstupů, výstupů, helper checků,
  skillů, rolí agentů, review stavu, hashů výstupů a omezení,
- `work/agent_coverage.json` - interní role matrix pro povinné agentní role,
  jejich triggery, výstupní evidenci, agent/reviewer údaje a typované výjimky,
- `outputs/oponent_podklady.md` - draft interních oponentských podkladů,
- `outputs/oponent_podklady_revidovane.md` - revidované oponentské podklady,
- `work/oponent_posudek_draft.md` - pracovní draft oponentského posudku podle
  položek FIT IS,
- `outputs/feedback_k_posudku.md` - review návrhu posudku.

Studentský feedback a oponentské materiály nejsou hotové jen proto, že vznikly.
Musí projít nezávislou review smyčkou jiným autorizovaným agentem. Po větší
úpravě se výstup znovu bere jako draft.

`work/oponent_posudek_draft.md` je jen most z revidovaných podkladů do struktury
IS. Helper do něj zapisuje hash zdrojových podkladů a nechává body/známku
otevřené; `scripts/check-opponent-report` projde až po lidské kalibraci
konkrétních bodů a známky a po ověření, že draft odpovídá aktuálním
`outputs/oponent_podklady_revidovane.md`.

Interní evidence jako `revision_diff.md`, `github_code_intake.md`, `code_consistency.md`,
`code_quality_review.md`, `literature_citation_review.md`,
`figure_media_review.md` nebo `typography_formal_review.md` je samostatně
finální jen tehdy, když prošla vlastní evidenční review smyčkou a verdikt je
zapsaný. Pokud je použita jen jako podklad pro studentský feedback nebo
oponentské podklady, certifikuje ji až review dané syntézy, a to jen v rozsahu
použitých zjištění.

Po vytvoření nebo úpravě výstupů má agent obnovit `work/review_manifest.json`.
Manifest je uložený v ignorovaném round workspace, protože obsahuje case-specific
názvy souborů a workflow omezení. Review verdikt je svázaný s hashem výstupu;
když se Markdown po review změní, validátor to označí jako stale review. Strict
closeout nebere finální nebo odesílatelný výstup jako hotový, dokud manifest
neobsahuje review status, reviewer roli, čas review a hash přesně té verze
souboru, která má být použita.

Pokud dostupné vstupy vyžadují specializované role, `scripts/init-review-manifest`
založí nebo obnoví generovaný `work/agent_coverage.json`. Zdroj pravdy pro
generator/reviewer údaje zůstává `work/review_manifest.json`; v coverage souboru
se ručně doplňují jen typované výjimky. `scripts/check-agent-coverage` hlídá,
že povinné role mají odpovídající výstupní evidenci, skill, zapsaného
role-specific agenta a u review rolí také reviewer údaje a hash kontrolované
verze. Chybějící roli je možné uzavřít jen konkrétní `typed_limitation`, ne
tichým přeskočením.

## Role a review smyčky

Pro větší práci má agent rozdělit role, typicky:

- text, struktura a splnění zadání,
- obrázky, tabulky, screenshoty, grafy, captiony a změny vizuální evidence,
- GitHub/PR intake, pokud je kód dostupný přes repo URL nebo upstream PR,
- soulad textu s kódem,
- kvalita kódu, design, runtime rizika a reprodukovatelnost,
- literatura a citace, pokud jsou pro daný round důležité,
- pozdní typografie a formální stránka, pokud jde o předfinální/final round,
- kalibrace evidence a tvrzení,
- syntéza do finálního Markdownu.

Když je v roundu kód, supervisor feedback a oponentské podklady mají použít
kontrolu souladu textu s kódem i kontrolu kvality implementace, nebo výslovně
říct, proč to z dostupných vstupů nešlo.

Když je kód dostupný přes GitHub repo nebo PR, agent má nejdřív udělat read-only
GitHub intake. U PR-based prací nesmí hodnotit celý upstream projekt jako
studentův výstup; upstream je baseline a kontext, studentův rozsah se posuzuje
podle PR diffů, commitů, testů/dokumentace, review diskuse, CI a deklarovaného
scope.

Když práce obsahuje měření, metriky, výsledky experimentů nebo uživatelské
hodnocení, agent má zkontrolovat jednotky, baseline, praktickou velikost efektu,
reprodukovatelnost a přiměřenost interpretace. Skriptový guard pro tyto případy
je uveden níže.

Když práce obsahuje důležité obrázky, screenshoty, diagramy nebo výsledkové
grafy, samostatný figure/media workflow vytvoří interní inventář a krátké
znovupoužitelné popisy. Inventář může znovu použít drahou vizuální analýzu
mezi roundy jen při shodě hashe source assetu nebo PDF cropu a verze analýzy;
claim alignment se znovu použije jen při shodném vizuálu i textovém kontextu.
Vizuální tvrzení smějí vzniknout jen po konkrétní PDF-detail/vision kontrole
nebo po kontrole source assetu svázaného s finálním PDF; textový extract sám o
sobě stačí pouze na inventář, caption claims a `not_verifiable` alignment.

U předfinálních a finálních roundů může agent udělat samostatnou typografickou
a formální kontrolu. Pravidla se kalibrují podle jazyka práce, ne podle jazyka
feedbacku: u českých prací se hlídají mimo jiné jednoznakové předložky/spojky
na koncích řádků a LaTeX/`vlna` hinty, u anglických prací se česká pravidla
nepoužívají a důraz je spíš na běžné editor/Overleaf kontroly a ruční final
proofread. Studentovi se neposílá auditní seznam všech výskytů; do feedbacku
patří shrnutý vzorec problému a doporučený postup opravy.

## Kdy požádat o diagnostiku

Skripty jsou hlavně guardy pro agenta. Ručně je obvykle volat nemusíte; můžete
agenta požádat například:

```text
Spusť readiness a privacy kontroly pro aktuální case a řekni mi, co chybí.
```

Základní diagnostika:

```bash
scripts/case-doctor <case-id>
scripts/check-supervisor-ready <case-id>
scripts/check-round-ready <case-id>
scripts/check-private
```

`scripts/case-doctor <case-id> [round-id]` je read-only operator snapshot: shrne
aktivní round, readiness checky, deadline kalibraci, vstupy, extracty, kód,
výstupy, review manifest a předchozí feedback. Nenahrazuje finální gate checky,
jen rychle ukáže, co chybí nebo je stale před začátkem review.

Časté finální kontroly:

```bash
scripts/check-tooling <case-id>
scripts/check-feedback-language <case-id>
scripts/check-feedback-output <case-id>
scripts/check-opponent-materials <case-id>
scripts/check-opponent-report <case-id>
scripts/check-evaluation-claims <case-id>
scripts/check-typography-formal <case-id>
scripts/init-review-manifest --run-checks <case-id>
scripts/check-agent-coverage <case-id>
scripts/check-review-manifest --require-complete <case-id>
```

Zakládací/importní helpery, pokud je nechcete nechat na agentovi:

```bash
scripts/new-case <case-id> BP first-review
scripts/import-round <case-id> current-review /path/to/thesis.pdf /path/to/code.zip
scripts/prepare-code-workspace <case-id>
scripts/draft-opponent-report <case-id>
scripts/import-github-code <case-id> --pr-url https://github.com/owner/project/pull/123 --student-login <login>
scripts/import-github-code <case-id> --discover-prs owner/project --author <login>
```

`prepare-code-workspace` rozbalí nebo zkopíruje pravděpodobné zdrojové archivy a
adresáře do ignorovaného `work/code/`, zapíše `work/code_workspace.md` a
`work/serena_roots.json` a navrhne levné smoke příkazy. Serena se má aktivovat
vždy nad jedním konkrétním code rootem z tohoto inventáře, ne nad celým
`cases/` ani nad celým roundem. Repo `.serena/project.yml` platí jen pro tento
workflow repozitář a záměrně ignoruje `cases/**`; kód studenta je samostatný
Serena projekt podle konkrétního rootu z `work/serena_roots.json`. Pokud je
potřeba přegenerovat celý `work/code/`, použijte `--refresh` jen po ověření, že
v něm nejsou ručně importované GitHub/code rooty, které by se tím smazaly.

`scripts/check-tooling <case-id> [round-id]` je read-only preflight pro lokální
nástroje a konektory. Tvrdě selže jen na blokerech v aktuálním kontextu, např.
chybějící `pdftotext` u roundu s PDF bez extractu; GitHub CLI auth, Serena,
`pdf-reader-mcp` a jazykové/literační nástroje hlásí jako explicitní stav nebo
varování podle relevance pro daný round.

`check-supervisor-ready` je brána pro studentský feedback od vedoucího. Ověří
zadání a přidá deadline kalibraci. `check-round-ready` je obecnější brána pro
oponentní a interní materiály bez supervisor deadline kalibrace.

Pro odložené nebo srpnové obhajoby uveďte přesné datum do `case.md`:

```text
Deadline override: YYYY-MM-DD
```

## Reference pro agenty a údržbu

Workflow definují repo skills v `.agents/skills/`:

- `thesis-supervisor-feedback` - studentská zpětná vazba od vedoucího,
- `thesis-supervisor-feedback-review` - nezávislá kontrola před odesláním,
- `thesis-revision-diff` - porovnání dvou verzí,
- `thesis-github-code-intake` - read-only GitHub repo/PR import a PR
  contribution evidence,
- `thesis-code-consistency` - soulad práce s kódem a reprodukovatelností,
- `thesis-code-quality-review` - kvalita implementace a designu,
- `thesis-literature-citation-review` - literatura, zdroje a citace,
- `thesis-figure-media-review` - obrázky, tabulky, screenshoty, grafy,
  vizuální evidence, kontext tvrzení a změny mezi roundy,
- `thesis-typography-formal-review` - pozdní typografie a formální stránka
  podle jazyka práce,
- `thesis-opponent-materials` - interní podklady pro oponenta,
- `thesis-opponent-materials-review` - review oponentských podkladů,
- `thesis-opponent-report-review` - review draftu posudku.

Jako operátor obvykle nemusíte znát přesný obsah skillů. Stačí agentovi říct,
jaký výstup chcete a že má použít agenty. Přesné workflow si má dohledat sám.

## Reviewer profily

`case.md` obsahuje:

```text
Thesis language: auto
Student feedback language: cs
Reviewer profile: default
```

Chybějící jazyk feedbacku znamená `cs`. `Thesis language` může být `cs`, `en`
nebo `auto` a řídí jen kontroly textu práce, ne jazyk studentského feedbacku.
Jazyk práce v intake poznámkách neřídí jazyk feedbacku.

Veřejný repozitář obsahuje jen `profiles/default.md`. Osobní preference patří
pod ignorované cesty:

```text
profiles/local/default.md
profiles/local/<profile-id>.md
```

Profily jsou preference, ne tvrdá workflow pravidla. Nemohou přepsat soukromí,
evidenční požadavky, readiness gate, jazyk výstupu ani povinnost říct, co nebylo
ověřeno.

## Soukromí a git

Do gitu nepatří studentská PDF, zdrojové zipy, extrakty, kódové odevzdávky,
soukromé poznámky ani vygenerované case výstupy. Tyto věci mají zůstat pod
ignorovaným `cases/`.

Před commitem workflow změn:

```bash
git status --short --untracked-files=all
git diff --check
scripts/check-private
scripts/check-scripts
```

Při změně deterministických validatorů spusťte i odpovídající smoke testy,
například:

```bash
scripts/smoke-feedback-output
scripts/smoke-opponent-materials
scripts/smoke-evaluation-claims
scripts/smoke-typography-formal
scripts/smoke-github-code-intake
scripts/smoke-agent-coverage
scripts/smoke-opponent-report
scripts/smoke-tooling
scripts/smoke-case-doctor
scripts/smoke-prepare-code-workspace
scripts/smoke-private
```

`WORKFLOW_MEMORY.md` obsahuje zkušenosti a rationale. Není to druhý instrukční
systém. Pokud se z něj stane aktivní pravidlo, promujte ho do README, skillu,
šablony, `AGENTS.md` nebo `TODO.md`.

`AGENTS.md` má zůstat krátký. Dlouhé postupy patří do skills a dokumentace.
