# FIT Thesis Workflows

Human-first workflow pro vedení a oponování BP/DP prací s pomocí agentů.

Tento repozitář není aplikace pro studenty. Je to pracovní vrstva pro vedoucí,
oponenty a další hodnotitele, kteří chtějí přes chat s agentem zpracovat
odevzdané PDF, zdrojové soubory, kód, předchozí zpětné vazby a vlastní poznámky.

Typické použití není ruční volání skriptů. Typické použití je napsat agentovi:

```text
Přidej nový případ pro tuto BP. Přikládám zadání, PDF práce, zdrojový zip,
kód, moje poznámky a případně Theses.cz report podobnosti po odevzdání.
Připrav studentovi zpětnou vazbu, použij agenty, zkontroluj soulad textu s
kódem a kvalitu implementace a nálezy po review rovnou oprav.
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
   případně LaTeX/Overleaf zip, kód, starší feedback, Theses.cz report
   podobnosti po odevzdání, návrh posudku nebo vlastní poznámky.
3. Napište, jaký výstup chcete: studentskou zpětnou vazbu, formální posudek
   vedoucího, oponentské podklady, revizní diff, kontrolu kódu, kontrolu
   citací, nebo review hotového posudku.
4. Pokud má vzniknout finální výstup, nebo samostatná evidence, na kterou se
   budete spoléhat, napište výslovně `použij agenty`. Workflow to vyžaduje pro
   nezávislou review smyčku.
5. Agent si vyžádá chybějící kontext, založí nebo doplní case, zpracuje vstupy
   v ignorovaném workspace a uloží výstupy do aktivního roundu.

Case data pod `cases/` jsou ignorovaná gitem. Do repozitáře patří workflow,
skripty, šablony a profily, ne soukromé studentské materiály.

Agent si pod kapotou hlídá deterministické kroky pro aktuální materiály,
role-plan, role vlny, manifest, nezávislé review a closeout; operátor obvykle
jen řekne, co chce zpracovat a že má agent použít agenty.

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

Přikládám zadání, aktuální PDF práce, případně zdrojový zip, kód a Theses.cz
report podobnosti po odevzdání.
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
zdroje, kód a případně Theses.cz report podobnosti po odevzdání. Použij
agenty. Pokud je dostupný kód, zkontroluj soulad textu s kódem i kvalitu
implementace. Výstup má být interní evidence pro oponenta, ne studentský
feedback.
```

### Posudek vedoucího

```text
Připrav draft formálního posudku vedoucího pro IS. Přikládám zadání,
aktuální PDF práce, případně kód a svoje poznámky k aktivitě, samostatnosti,
komunikaci, dokončování, publikacím a navrhované známce/bodům. Použij agenty.
Předchozí feedback využij jen tam, kde je z něj a z revizí vidět reakce
studenta; pokud to průkazné není, opři procesní hodnocení o moje poznámky.
Pokud existuje moje historická kalibrace posudků vedoucího, použij ji pro styl
a míru detailu, ne jako důkaz o aktuálním studentovi.
```

U finálního posudku vedoucího stačí zadat cíl chatem, ale agent má držet
pevnou posloupnost: ověřit `check-supervisor-report-ready`, připravit
role-packets jen při explicitním `Použij agenty`, obnovit current-evidence a
finální materiality, vyřešit povinné next actions aktuálními artefakty,
review/synthesis pokrytím nebo typed limitation, vygenerovat trace a draft,
nechat projít nezávislý review pass, obnovit manifest přes `init-review-manifest
--run-checks`, potvrdit report pro IS a zavřít ho přes
`supervisor-report-closeout`. Čisté Theses.cz similarity evidence zůstává
interní a tiché, pokud strukturované posouzení nemá nevyřešený problém.

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
- jazyk práce (`cs`, `sk`, `en`, nebo `auto`), pokud ho nelze spolehlivě poznat z PDF,
- akademický rok a případný posunutý termín,
- fáze práce: raná kostra, pracovní verze, předfinální verze, finální kontrola,
- co chcete explicitně ověřit,
- co už nechcete v této fázi znovu otevírat,
- jazyk studentského feedbacku, pokud nemá být výchozí čeština,
- reviewer profile, pokud nemá být výchozí `default`.

U formálního posudku vedoucího navíc agent potřebuje explicitní vstup k tomu,
co z artefaktů nepozná spolehlivě: aktivita a samostatnost studenta, konzultace,
komunikace, připravenost, práce v závěrečné fázi, publikační nebo open-source
souvislosti, navrhovaná známka/body a neveřejný komentář pro studenta. Chybějící
předchozí feedback není negativní evidence; neprůkazný feedback nemá nahrazovat
vstup vedoucího.

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
- `notes/supervisor-report-operator-input.md` - vstup vedoucího pro formální
  posudek, včetně procesních a hodnoticích informací,
- `work/supervisor_report_feedback_history.json` - strukturované shrnutí
  použitelnosti předchozího feedbacku pro posudek,
- `work/supervisor_report_trace.json` - interní trace z evidence a vstupu
  vedoucího do položek FIT IS,
- `work/vedouci_posudek_draft.md` - pracovní draft posudku vedoucího,
- `outputs/vedouci_posudek_revidovany.md` - revidovaný draft posudku vedoucího,
- `work/supervisor_report_confirmation.json` - potvrzení vedoucího před
  vložením do IS,
- `outputs/revision_diff.md` - rozdíl proti předchozí verzi,
- `outputs/github_code_intake.md` - interní evidence GitHub repo/PR importu,
- `outputs/code_consistency.md` - interní kontrola souladu textu a kódu,
- `outputs/code_quality_review.md` - interní code-quality/design review,
- `work/literature/source_acquisition.json` - hashovaná cílená triáž a legální
  dohledání klíčových/podezřelých citačních zdrojů,
- `outputs/literature_citation_review.md` - interní kontrola literatury a citací,
- `outputs/figure_media_review.md` - interní kontrola obrázků, tabulek,
  screenshotů, výsledkových grafů a jejich změn mezi revizemi,
- `outputs/typography_formal_review.md` - interní pozdní kontrola typografie
  a formální stránky podle jazyka práce,
- `work/theses_similarity/intake.json` - strukturální import Theses.cz reportu
  podobnosti,
- `work/theses_similarity/assessment.json` - kontextové posouzení shod a
  syntézní akce připravené autorizovaným člověkem nebo agentem,
- `outputs/theses_similarity_review.md` - interní review Theses.cz reportu,
- `work/reviews/theses_similarity_review.json` - samostatný approval record pro
  finální evidenční použití Theses.cz review,
- `work/figure_media/visual_inventory.jsonl` - znovupoužitelný interní inventář
  vizuálních prvků a jejich popisů,
- `work/assignment_coverage_agent.json` - agentem nebo člověkem připravená
  strukturovaná mapa splnění bodů zadání,
- `work/evidence_requirements.json` - agentem nebo člověkem připravený
  strukturovaný přehled požadované, dostupné a slabé evidence,
- `work/quantitative_claims.json` - agentem nebo člověkem připravený
  strukturovaný handoff pro kvantitativní/result claimy, jednotky, baseline,
  praktický kontext a reprodukovatelnost,
- `work/media_presence_inventory.jsonl` - strukturální inventář nalezených
  media souborů podle cesty a přípony,
- `work/code_reproducibility.json` - statická klasifikace reprodukovatelnosti
  kódového podkladu bez spouštění studentského kódu,
- `work/supervisor_packets/*.md` - stručné role-specific podklady pro agentní
  vlny studentské zpětné vazby,
- `work/opponent_packets/*.md` - stručné role-specific podklady pro agentní
  review vlny,
- `work/reviews/*_review.json` - strukturovaný approval record nezávislého
  finálního review s hashem revidovaného artefaktu a review basis,
- `work/review_run_trace.json` - case-private stopa round-start, role-plan,
  role-wave, synthesis, independent-review, operator-delta a closeout fází,
- `work/operation_log.jsonl` - append-only provozní log nestandardních kroků,
  blokovaných/selhaných rolí, ručních fallbacků, korekcí a kalibračních
  rozhodnutí; slouží k rekonstrukci průběhu a není součástí manifest hash gate,
- `work/review_role_plan.json` - plán povinných rolí, role states, packet refs,
  reuse projekcí, typed limitations a bounded wave schedule před spawnutím
  agentů,
- `work/review_artifacts/*.json` - průběžné sidecary pro manifest registraci
  role-owned výstupů,
- `work/review_deltas/*.json` - hash-bound záznam post-review změn, námitek,
  typovaných výjimek a obecných workflow lessons po revidovaném výstupu,
- `work/review_manifest.json` - interní manifest vstupů, výstupů, helper checků,
  skillů, rolí agentů, review stavu, hashů výstupů a omezení,
- `work/agent_coverage.json` - interní role matrix pro povinné agentní role,
  jejich triggery, výstupní evidenci, agent/reviewer údaje a typované výjimky,
- `outputs/oponent_podklady.md` - draft interních oponentských podkladů,
- `outputs/oponent_podklady_revidovane.md` - revidované oponentské podklady,
- `work/opponent_report_trace.json` - strukturovaný, revidovaný trace z
  oponentských podkladů do položek FIT IS, otázek a ručních kontrol,
- `work/oponent_posudek_draft.md` - pracovní draft oponentského posudku podle
  položek FIT IS, včetně strukturovaných výběrů/bodů pro formulář a
  samostatného neveřejného komentáře pro studenta,
- `outputs/feedback_k_posudku.md` - review návrhu posudku.

Studentský feedback, formální posudek vedoucího a oponentské materiály nejsou
hotové jen proto, že vznikly. Musí projít nezávislou review smyčkou jiným
autorizovaným agentem. Po větší úpravě se výstup znovu bere jako draft.
U posudku vedoucího je navíc před vložením do IS potřeba výslovné potvrzení
známky, bodů, oficiálního textu i neveřejného komentáře pro studenta.

`work/oponent_posudek_draft.md` je jen most ze strukturovaného
`work/opponent_report_trace.json` do struktury IS. Helper do něj zapisuje hash
trace i zdrojových podkladů a nechává body/známku otevřené;
`scripts/check-opponent-report` projde až po lidské kalibraci konkrétních bodů a
známky a po ověření, že draft odpovídá aktuálnímu trace i
`outputs/oponent_podklady_revidovane.md`.
Součástí kalibrace je i sekce `## IS formulář (výběry a body)`: výběr
náročnosti zadání, rozsahu splnění zadání, rozsahu zprávy a bodů pro
prezentační úroveň, formální úpravu, práci s literaturou a realizační výstup.

`scripts/opponent-closeout <case-id> [round-id]` je finální oponentský gate
pro aktuální stav roundu. Zavře revidované podklady, report trace, manifest,
agent coverage a repo hygienu. Gate vždy vyžaduje validní
`work/opponent_report_trace.json`; pokud už existuje
`work/oponent_posudek_draft.md`, musí být nejdřív lidsky zkalibrovaný v bodech,
známce, výběrech/bodech IS formuláře a formulacích.
Pokud existují interní evidence `outputs/code_consistency.md`,
`outputs/code_quality_review.md` nebo `outputs/revision_diff.md`, manifest a
oponentní closeout vyžadují i jejich strukturální validátory.

Interní evidence jako `revision_diff.md`, `github_code_intake.md`, `code_consistency.md`,
`code_quality_review.md`, `literature_citation_review.md`,
`figure_media_review.md`, `typography_formal_review.md` nebo
`theses_similarity_review.md` je samostatně finální jen tehdy, když prošla
vlastní evidenční review smyčkou a verdikt je zapsaný. Pokud je použita jen jako
podklad pro studentský feedback, formální posudek vedoucího nebo oponentské
podklady, certifikuje ji až review dané syntézy, a to jen v rozsahu použitých
zjištění.

Po vytvoření nebo úpravě výstupů má agent obnovit `work/review_manifest.json`.
Manifest je uložený v ignorovaném round workspace, protože obsahuje case-specific
názvy souborů a workflow omezení. Review verdikt je svázaný s hashem výstupu;
když se Markdown po review změní, validátor to označí jako stale review.
Finální nebo odesílatelný výstup navíc potřebuje aktuální
`work/reviews/*_review.json`, který hashově váže revidovaný soubor i review
basis. Strict closeout nebere takový výstup jako hotový, dokud manifest
neobsahuje review status, reviewer roli, čas review, approval record a hash
přesně té verze souboru, která má být použita.

Pokud dostupné vstupy vyžadují specializované role, `init-review-manifest`
založí nebo obnoví generovaný `work/agent_coverage.json`. Zdroj pravdy pro
generator/reviewer údaje zůstává `work/review_manifest.json`; v coverage souboru
se ručně doplňují jen typované výjimky. `check-agent-coverage` hlídá,
že povinné role mají odpovídající výstupní evidenci, skill, zapsaného
role-specific agenta a u review rolí také reviewer údaje a hash kontrolované
verze. Chybějící roli je možné uzavřít jen konkrétní `typed_limitation`, ne
tichým přeskočením.

Detailní pořadí oponentských příprav, poradních helperů, role packetů,
evidenčních validátorů a manifest closeoutu je v
`docs/opponent-review-workflow.md`.

## Role a review smyčky

Pro větší práci má agent rozdělit role, typicky:

- text, struktura a splnění zadání,
- obrázky, tabulky, screenshoty, grafy, captiony a změny vizuální evidence,
- GitHub/PR intake, pokud je kód dostupný přes repo URL nebo upstream PR,
- soulad textu s kódem,
- kvalita kódu, design, runtime rizika a reprodukovatelnost,
- literatura a citace, pokud jsou pro daný round důležité,
- pozdní typografie a formální stránka, pokud jde o předfinální/final round,
- Theses.cz report podobnosti, pokud byl po odevzdání importován,
- kalibrace evidence a tvrzení,
- syntéza do finálního Markdownu.

Stabilní Codex agent role profily a jejich vazba na repo-local skilly jsou v
`docs/agent-profile-matrix.md`. To jsou `.codex/agents/*` profily pro spawnuté
workflow role; nejsou to case `Reviewer profile:` preference z `case.md`.

Paralelní review znamená pokrytí rolí, ne neomezený počet živých agentů.
Výchozí limit jsou nejvýš 2 současně běžící spawnutí workflow agenti; na stroji
s omezenou RAM má agent použít 1. Vyšší souběh vyžaduje nejdřív vědomou změnu
projektového Codex configu, ne jen rozhodnutí během běhu. Role se mohou běžet po
vlnách: příprava, text/code consistency, code quality plus
figure/literature/typography podle triggerů, kalibrace, syntéza a nakonec
nezávislé review jiným agentem. Přesná procedura je v
`docs/agent-scheduling.md`.

`work/supervisor_packets/*.md` a `work/opponent_packets/*.md` jsou interní
role handoffy, které zmenšují prompt a omezují drift mezi agenty. Nemění
povinné role, skill pravidla ani manifest/coverage kontrolu. Pokud agent tvrdí,
že očekávaný soubor zapsal, ale `scripts/check-review-wave` nebo jiný checker
říká opak, věřte souboru a checkeru: agent má artefakt opravit nebo znovu
vygenerovat, ne jen upravit závěrečnou zprávu v chatu.

Když je v roundu kód, supervisor feedback, formální posudek vedoucího a
oponentské podklady mají použít kontrolu souladu textu s kódem i kontrolu
kvality implementace, nebo výslovně říct, proč to z dostupných vstupů nešlo.

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
feedbacku: u českých a slovenských prací se hlídají mimo jiné jednoznakové
předložky/spojky na koncích řádků a LaTeX/`vlna` hinty, u anglických prací se
česko-slovenská pravidla nepoužívají a důraz je spíš na běžné editor/Overleaf
kontroly a ruční final proofread. Studentovi se neposílá auditní seznam všech
výskytů; do feedbacku patří shrnutý vzorec problému a doporučený postup opravy.

Pokud je po odevzdání dostupný Theses.cz report podobnosti, importuje se
explicitně do ignorovaného case workspace a posuzuje se samostatným interním
workflow. Čistý nebo vysvětlený report se ve studentském feedbacku ani posudcích
standardně nezmiňuje. Podezřelé, nevysvětlené nebo institucionálně důležité
shody musí nejdřív projít kontextovým review; procento podobnosti samo o sobě
není důkaz plagiátu, autorství ani důvod ke změně bodů. U druhého pokusu je
vysoká shoda s první verzí téhož studenta normální kandidát na self-overlap a
posuzuje se podle historie roundů a revizního diffu.

## Kdy požádat o diagnostiku

Skripty jsou hlavně guardy pro agenta. Ručně je obvykle volat nemusíte; můžete
agenta požádat například:

```text
Spusť readiness a privacy kontroly pro aktuální case a řekni mi, co chybí.
```

Všechny tvary `scripts/<tool>` v tomto README jsou Linux/dev zkratka a zároveň logický
název workflow příkazu. Na Windows nespouštějte ani neklikejte bezpříponové
`scripts/<tool>` soubory; Windows je může zkusit otevřít jako dokument a ukázat
dialog „Select an app“. Nejprve zabalte workflow nástroje přes
`scripts\package-workflow-tools.cmd` nebo `.\scripts\package-workflow-tools.ps1`
a potom používejte `dist\workflow-tools\bin\<tool>.cmd` nebo odpovídající
PowerShell launcher.

Základní diagnostika:

```bash
scripts/case-doctor <case-id>
scripts/check-supervisor-ready <case-id>
scripts/check-round-ready <case-id>
scripts/opponent-preflight <case-id>
scripts/check-private
```

`scripts/case-doctor <case-id> [round-id]` je read-only operator snapshot: shrne
aktivní round, readiness checky, deadline kalibraci, vstupy, extracty, kód,
výstupy, review manifest a předchozí feedback. Nenahrazuje finální gate checky,
jen rychle ukáže, co chybí nebo je stale před začátkem review.

Volný text práce, README, poznámek, zdrojáků nebo generovaných prose výstupů má
interpretovat agent/LLM a opřít výsledek o konkrétní důkazy. Deterministické
skripty mají pracovat hlavně se strukturovanými daty: metadaty, manifesty,
JSON/JSONL artefakty, hashi, cestami, příponami, sekcemi, tabulkami a schématy.
Pokud skript ještě používá keyword/regex nad holým textem, je to jen poradní
prompt pro ověření agentem nebo člověkem, ne verdikt, gate ani automatická
formulace do feedbacku nebo posudku. Aktuální audit hranice je v
`docs/raw-text-processing-audit.md`.

Poradní příprava pro oponentské review:

`scripts/check-assignment-coverage`, `scripts/check-evidence-presence` a
`scripts/check-evaluation-claims` spouštějte až po vytvoření příslušných
strukturovaných artefaktů autorizovaným agentem nebo člověkem.
Kvantitativní/result claimy vytváří skill
`thesis-quantitative-claims-review` do `work/quantitative_claims.json`;
syntéza čte nejdřív packetový `## Quantitative Claims Handoff` a plné výsledky
otevírá jen pro ověření materiálního tvrzení nebo kalibraci formulace. Pokud
text/code/figure agent najde důležitý metrický claim jen v prose, pošle ho do
tohoto skillu; deterministické skripty nemají rozšiřovat raw-text heuristiky.

```bash
scripts/check-assignment-coverage <case-id>
scripts/check-evidence-presence <case-id>
scripts/check-code-reproducibility <case-id>
scripts/check-evaluation-claims <case-id>
scripts/update-current-evidence-snapshot <case-id>
scripts/import-theses-report <case-id> /path/to/theses-report.pdf
scripts/check-theses-similarity-report <case-id>
scripts/check-review-materiality --workflow supervisor_feedback <case-id>
scripts/review-round-start --profile supervisor_feedback <case-id>
scripts/prepare-review-round --profile supervisor_feedback <case-id>
scripts/prepare-supervisor-packets <case-id>
scripts/check-review-materiality --workflow opponent_review <case-id>
scripts/review-round-start --profile opponent_materials <case-id>
scripts/prepare-review-round --profile opponent_materials <case-id>
scripts/prepare-opponent-packets <case-id>
scripts/check-review-wave --workflow supervisor_feedback --wave draft <case-id>
scripts/register-review-artifact <case-id> <round-id> outputs/code_quality_review.md --role code_quality
scripts/write-review-approval --profile supervisor-feedback --reviewer-agent <agent-id> <case-id>
scripts/review-round-closeout --profile supervisor_feedback <case-id>
scripts/record-review-delta --profile supervisor_feedback --type material_claim_delta --previous-artifact /path/to/reviewed-before.md --affected-section feedback.body --evidence-ref outputs/code_quality_review.md --rationale "operator challenged reviewed wording" <case-id>
```

`scripts/check-review-materiality` nepíše verdikty o kvalitě práce. Z
existujících strukturovaných artefaktů a explicitních vstupů vytvoří poradní
materiality index; jeho `next_actions` řeknou, že před syntézou chybí například
`outputs/github_code_intake.md`, `work/quantitative_claims.json` nebo
`outputs/theses_similarity_review.md`, případně že je potřeba zapsat typed
limitation. Packet generátory tyto akce zobrazují a wave gate je u
synthesis/final vln považuje za blokující, dokud nejsou vyřešené. Typed
limitation pro takovou akci patří do
`work/review_manifest.json` jako strukturovaný záznam s
`trigger: materiality_next_action`, `scope`, `type`, `required_for`,
`description`, `impact`, `status` a `accepted_by` nebo `reviewer_role`.

`scripts/record-workflow-operation <case-id> [round-id] --operation ... --status ...`
zapisuje stručnou událost do `work/operation_log.jsonl`. Používejte ho, když
část pipeline selže, je přeskočena, je nahrazena ručním/fallback krokem, nebo
když operátor kalibruje výklad nálezu. Log je záměrně oddělený od
`work/review_manifest.json`, aby další diagnostický zápis nerozbíjel hashově
uzavřený manifest. `case-doctor` ukazuje poslední události logu.

`scripts/write-review-approval` zapisuje pouze pass/approved záznam po skutečné
nezávislé kontrole. Pro kanonické profily vyplní správnou dvojici
reviewed-artifact/review-basis a hash binding; neřeší obsahovou kontrolu místo
review agenta.

Nový nebo navazující round má sdílenou deterministic kostru:
`review-round-start` potvrdí aktuální materiály a zapíše
`work/review_run_trace.json`; `prepare-review-round` vytvoří
`work/review_role_plan.json`, packet refs, role states a bounded wave schedule;
autorizovaní agenti běží podle tohoto plánu; `review-round-closeout` pak
zkontroluje role plan, manifest, coverage, approvals, unresolved deltas a
profilové gates. Workflow profily jako `supervisor_feedback`,
`supervisor_report`, `opponent_materials` nebo `opponent_report_review` nejsou
Codex agent profily z `.codex/agents/`.

Časté finální kontroly:

```bash
scripts/check-tooling <case-id>
scripts/check-feedback-language <case-id>
scripts/check-feedback-output <case-id>
scripts/check-opponent-materials <case-id>
scripts/check-opponent-report <case-id>
scripts/opponent-closeout <case-id>
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

Když closeout hlásí stale review hash, approval record nebo review-basis hash,
neopravujte hash ručně. Buď vraťte artefakt do draft stavu a spusťte nové
nezávislé review, nebo pro post-review opravu zapište strukturovanou deltu přes
`record-review-delta` s affected sections, evidence anchors, typovanou výjimkou
nebo reopening next action. U odesílatelných a standalone finálních artefaktů
musí approval record odpovídat aktuálnímu souboru, jinak je review neplatné.

Zakládací/importní helpery, pokud je nechcete nechat na agentovi:

```bash
scripts/bootstrap-case supervisor <case-id> current-review --work-type BP --academic-year 2025/2026 --thesis-pdf /path/to/thesis.pdf --assignment-pdf /path/to/assignment.pdf --code /path/to/code.zip
scripts/bootstrap-case opponent <case-id> opponent-review --work-type DP --thesis-pdf /path/to/thesis.pdf --assignment-pdf /path/to/assignment.pdf --code /path/to/code.zip
scripts/opponent-preflight <case-id>
scripts/new-case <case-id> BP first-review
scripts/import-round <case-id> current-review /path/to/thesis.pdf /path/to/code.zip
scripts/prepare-code-workspace <case-id>
scripts/draft-opponent-report <case-id>   # až po vytvoření work/opponent_report_trace.json
scripts/import-github-code <case-id> --pr-url https://github.com/owner/project/pull/123 --student-login <login>
scripts/import-github-code <case-id> --discover-prs owner/project --author <login>
scripts/import-theses-report <case-id> /path/to/theses-report.pdf
```

`bootstrap-case` je konverzační importní/preflight helper pro nový nebo
existující case. Přijme PDF práce, PDF zadání, LaTeX/Overleaf zdroje, kód nebo
lokální repo snapshot, starší feedback a operátorské poznámky; uloží je pod
ignorovaný round workspace, extrahuje PDF text, rozbalí zdroje do
`work/source/`, připraví kód přes `prepare-code-workspace`, vyplní draft
`case.md`/`notes/*` a na konci spustí příslušný readiness check plus
`case-doctor`. Automaticky extrahovaný text bere jen jako vodítko: zadání,
private notes a metadata musí před review potvrdit hodnotitel.

`scripts/opponent-preflight <case-id> [round-id]` před oponentským workflow
tvrdě hlídá opponent readiness, tooling, lokální code workspace a GitHub intake
pro GitHub odkazy nalezené v round notes. Statická reprodukovatelnost kódu běží
před syntézou, aby review agenti dostali férové omezení. Assignment coverage,
evidence requirements a quantitative claims vznikají až jako strukturované
výstupy příslušného agenta nebo člověka a potom se ověřují přes
`scripts/check-assignment-coverage`, `scripts/check-evidence-presence` a
`scripts/check-evaluation-claims`. Výstup `case-doctor` v preflightu zůstává
diagnostický snapshot: upozorní i na starší výstupy nebo supervisor-only gate,
ale sám o sobě neblokuje start oponentských agentů.

`prepare-code-workspace` rozbalí nebo zkopíruje pravděpodobné zdrojové archivy a
adresáře do ignorovaného `work/code/`, zapíše `work/code_workspace.md` a
`work/serena_roots.json` a navrhne levné smoke příkazy. Serena se má aktivovat
vždy nad jedním konkrétním code rootem z tohoto inventáře, ne nad celým
`cases/` ani nad celým roundem. Repo `.serena/project.yml` platí jen pro tento
workflow repozitář a záměrně ignoruje `cases/**`; kód studenta je samostatný
Serena projekt podle konkrétního rootu z `work/serena_roots.json`. Pokud je
potřeba přegenerovat celý `work/code/`, použijte `--refresh` jen po ověření, že
v něm nejsou ručně importované GitHub/code rooty, které by se tím smazaly.
Pro netriviální práci s kódem používejte Serena MCP jako výchozí symbolovou
navigaci, zejména u Pythonu. Pro jiné jazyky ji použijte tehdy, když má Serena
dostupný language server pro konkrétní bezpečně scopovaný root. Podrobnosti jsou
v `docs/serena-code-navigation.md`.

Omen má dvě oddělené role. Repo target `pants run :omen` je vývojářská hygiena
tohoto workflow repozitáře a záměrně neprochází `cases/`. Code-quality reviewer
ale může použít Omen jako volitelný case-local advisory signál nad připraveným
studentským rootem v `work/code/`. Pokud Omen MCP nad neprázdným rootem vrátí
nula souborů/funkcí, zapište to jako MCP/path limitation, ne jako signál o
kvalitě kódu. Když je dostupné CLI, preferujte spuštění z konkrétního
připraveného rootu a výsledek uložte do `work/code_quality_omen.json` nebo
`work/code_quality_omen.md`.

`scripts/check-tooling <case-id> [round-id]` je read-only preflight pro lokální
nástroje a konektory. Tvrdě selže jen na blokerech v aktuálním kontextu, např.
chybějící `pdftotext` u roundu s PDF bez extractu; GitHub CLI auth, Serena,
`pdf-reader-mcp` a jazykové/literační nástroje hlásí jako explicitní stav nebo
varování podle relevance pro daný round.

### Rychlé opakované běhy helperů

`pants run` nepoužívejte jako běžný runner workflow helperů; při opakovaném
spouštění je zbytečně pomalý. Pro opakované běhy helperů je primární zabalený
Python command surface v `dist/workflow-tools/bin/`. Po změně Python helperů,
nebo před delší sérií agentních kontrol, si připravte rozbalené PEX nástroje:

```bash
scripts/package-workflow-tools
dist/workflow-tools/bin/check-tooling <case-id>
dist/workflow-tools/bin/opponent-preflight <case-id>
dist/workflow-tools/bin/prepare-code-workspace <case-id>
dist/workflow-tools/bin/review-round-start --profile supervisor_feedback <case-id>
dist/workflow-tools/bin/prepare-review-round --profile supervisor_feedback <case-id>
dist/workflow-tools/bin/check-supervisor-report-ready <case-id>
dist/workflow-tools/bin/prepare-supervisor-report-packets --agents-authorized <case-id>
dist/workflow-tools/bin/init-review-manifest --run-checks <case-id> [round-id]
dist/workflow-tools/bin/review-round-closeout --profile supervisor_feedback <case-id> [round-id]
dist/workflow-tools/bin/record-review-delta --profile supervisor_feedback --type style_only --previous-artifact /path/to/reviewed-before.md --affected-section feedback.body --rationale "bounded wording correction" <case-id> [round-id]
dist/workflow-tools/bin/supervisor-report-closeout <case-id> [round-id]
```

Na Windows použijte `.cmd` nebo PowerShell launcher:

```bat
scripts\package-workflow-tools.cmd
dist\workflow-tools\bin\check-tooling.cmd <case-id>
dist\workflow-tools\bin\opponent-preflight.cmd <case-id>
dist\workflow-tools\bin\prepare-code-workspace.cmd <case-id>
dist\workflow-tools\bin\review-round-start.cmd --profile supervisor_feedback <case-id>
dist\workflow-tools\bin\prepare-review-round.cmd --profile supervisor_feedback <case-id>
dist\workflow-tools\bin\check-supervisor-report-ready.cmd <case-id>
dist\workflow-tools\bin\prepare-supervisor-report-packets.cmd --agents-authorized <case-id>
dist\workflow-tools\bin\init-review-manifest.cmd --run-checks <case-id> [round-id]
dist\workflow-tools\bin\check-agent-coverage.cmd <case-id> [round-id]
dist\workflow-tools\bin\check-review-manifest.cmd --require-complete <case-id> [round-id]
dist\workflow-tools\bin\review-round-closeout.cmd --profile supervisor_feedback <case-id> [round-id]
dist\workflow-tools\bin\record-review-delta.cmd --profile supervisor_feedback --type style_only --previous-artifact C:\path\to\reviewed-before.md --affected-section feedback.body --rationale "bounded wording correction" <case-id> [round-id]
dist\workflow-tools\bin\supervisor-report-closeout.cmd <case-id> [round-id]
```

```powershell
.\scripts\package-workflow-tools.ps1
.\dist\workflow-tools\bin\check-tooling.ps1 <case-id>
.\dist\workflow-tools\bin\opponent-preflight.ps1 <case-id>
.\dist\workflow-tools\bin\prepare-code-workspace.ps1 <case-id>
.\dist\workflow-tools\bin\review-round-start.ps1 --profile supervisor_feedback <case-id>
.\dist\workflow-tools\bin\prepare-review-round.ps1 --profile supervisor_feedback <case-id>
.\dist\workflow-tools\bin\check-supervisor-report-ready.ps1 <case-id>
.\dist\workflow-tools\bin\prepare-supervisor-report-packets.ps1 --agents-authorized <case-id>
.\dist\workflow-tools\bin\init-review-manifest.ps1 --run-checks <case-id> [round-id]
.\dist\workflow-tools\bin\check-agent-coverage.ps1 <case-id> [round-id]
.\dist\workflow-tools\bin\check-review-manifest.ps1 --require-complete <case-id> [round-id]
.\dist\workflow-tools\bin\review-round-closeout.ps1 --profile supervisor_feedback <case-id> [round-id]
.\dist\workflow-tools\bin\record-review-delta.ps1 --profile supervisor_feedback --type style_only --previous-artifact C:\path\to\reviewed-before.md --affected-section feedback.body --rationale "bounded wording correction" <case-id> [round-id]
.\dist\workflow-tools\bin\supervisor-report-closeout.ps1 <case-id> [round-id]
```

`scripts/package-workflow-tools` a jeho `.cmd`/`.ps1` varianty spustí jediné
serializované balení přes Pants, zapíšou rozbalené PEX adresáře do ignorovaného
`dist/workflow-tools/pex/` a vygenerují POSIX, `.cmd` a `.ps1` launchery do
`dist/workflow-tools/bin/`.
Launchery nastaví `PEX_ROOT` na repo-lokální `.pants.d/pex_root`, pokud už není
explicitně nastavený v prostředí, vyčistí `PYTHONPATH`, zachovají původní
caller cwd pro relativní importní cesty a vyžadují Python 3.12 stejně jako
Pants konfigurace repozitáře.
Pokud je potřeba použít konkrétní interpreter, nastavte `WORKFLOW_TOOLS_PYTHON`.
POSIX `scripts/*` wrappery zůstávají vývojářská zkratka v tomto checkoutu;
operátorské a agentní opakované běhy mají používat zabalené launchery. `dist/`
je cache/build výstup; po změně Python CLI nebo sdílených helper modulů balení
spusťte znovu.
Kategorie příkazů a hranice Windows důkazů jsou rozepsané v
`docs/workflow-command-surface.md`.

`check-supervisor-ready` je brána pro studentský feedback od vedoucího. Ověří
zadání a přidá deadline kalibraci. Formální posudek vedoucího má vlastní
navazující bránu `check-supervisor-report-ready`, která vyžaduje i reportový
vstup vedoucího. Draft posudku se po vytvoření strukturovaného trace generuje
příkazem `draft-supervisor-report` a kontroluje příkazem
`check-supervisor-report`. `prepare-supervisor-report-packets --agents-authorized`
obnoví current-evidence snapshot, spustí finální materiality pro
`supervisor_report` a vypíše jen role packets, které jsou podle strukturovaných
artefaktů nebo typed limitations stále potřeba. Po nezávislém review reportu
patří před IS ještě `confirm-supervisor-report` a potom
`supervisor-report-closeout`; closeout znovu obnoví current evidence, final
materiality, manifest/approval/coverage stav, final review wave, případné
hash-bound submitted-report/amendment záznamy a repo hygiene. `check-round-ready`
je obecnější brána pro oponentní a interní materiály bez supervisor deadline
kalibrace.

Pro odložené nebo srpnové obhajoby uveďte přesné datum do `case.md`:

```text
Deadline override: YYYY-MM-DD
```

## Reference pro agenty a údržbu

Workflow definují repo skills v `.agents/skills/`:

- `thesis-supervisor-feedback` - studentská zpětná vazba od vedoucího,
- `thesis-supervisor-feedback-review` - nezávislá kontrola před odesláním,
- `thesis-supervisor-report` - formální posudek vedoucího pro FIT IS,
- `thesis-supervisor-report-review` - nezávislé review posudku vedoucího,
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
- `thesis-theses-similarity-review` - interní interpretace Theses.cz reportu
  podobnosti v kontextu case a roundů,
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

Chybějící jazyk feedbacku znamená `cs`. `Thesis language` může být `cs`, `sk`,
`en` nebo `auto` a řídí jen kontroly textu práce, ne jazyk studentského
feedbacku. Slovenská práce se ve výstupu dál hlásí jako `sk`, ale typografická
pravidla sdílí česko-slovenskou rodinu kontrol.
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

Při větších úpravách samotného repo toolingu jsou k dispozici i volitelné
vývojářské kontroly:

```bash
pants run :vulture
pants run :jscpd
pants run :omen
```

Tyto cíle hlídají mrtvý kód, duplicity a obecné codebase health signály. Nejsou
součástí thesis case pipeline ani operátorských closeout gate; jejich scope a
lokální požadavky jsou v `docs/dev-hygiene.md`.

## Plánování větších změn

Větší workflow nebo tooling změny se mají plánovat v tracked souborech pod
`plans/`. Aktivní plán patří do `plans/*_plan.md`, hotový nebo nahrazený plán do
`plans/archive/`. `TODO.md` zůstává jen dlouhodobý seznam otevřené práce; detail
slice-by-slice postupu patří do plánu.

Plán má obsahovat cíl, auditní základ, scope, non-goals, malé implementační
slices, přesné ověřovací příkazy, průběžný stav a final audit. Kontrakt je v
`plans/README.md`.

Windows podpora je trvalý workflow kontrakt, ne jednorázový audit. Nové nebo
měněné operátorské příkazy musí mít Python/Pants/PEX povrch nebo native
`.cmd`/`.ps1` launcher, nepředpokládat WSL a používat Windows-aware cesty,
subprocess volání, dočasné soubory a UTF-8 textové I/O. `scripts/check-scripts`
kontroluje, že tento kontrakt zůstává v aktivních repo pravidlech a že balicí
entrypointy pro Windows nezmizely; při změně command surface spusťte i
`scripts/smoke-package-workflow-tools`.

Checklist pro nový workflow příkaz: přidejte POSIX wrapper pod `scripts/`, CLI
modul pod `src/thesis_review_workflow/cli/`, položku do
`WORKFLOW_COMMAND_MODULES`, `python_source` v `src/.../cli/BUILD`, shell source,
runtime dependency a `pex_binary(tags=["workflow-tool"])` v `scripts/BUILD`,
cílený smoke skript a balicí smoke pro `.cmd`/`.ps1` launchery.
Podrobnější kategorizace command surface je v
`docs/workflow-command-surface.md`.

Při změně deterministických validatorů spusťte i odpovídající smoke testy,
například:

```bash
scripts/smoke-feedback-output
scripts/smoke-opponent-materials
scripts/smoke-evaluation-claims
scripts/smoke-typography-formal
scripts/smoke-theses-similarity-report
scripts/smoke-github-code-intake
scripts/smoke-agent-coverage
scripts/smoke-opponent-report
scripts/smoke-opponent-closeout
scripts/smoke-tooling
scripts/smoke-package-workflow-tools
scripts/smoke-case-doctor
scripts/smoke-prepare-code-workspace
scripts/smoke-bootstrap-case
scripts/smoke-private
```

`WORKFLOW_MEMORY.md` obsahuje zkušenosti a rationale. Není to druhý instrukční
systém. Pokud se z něj stane aktivní pravidlo, promujte ho do README, skillu,
šablony, `AGENTS.md` nebo `TODO.md`.

`AGENTS.md` má zůstat krátký. Dlouhé postupy patří do skills a dokumentace.
