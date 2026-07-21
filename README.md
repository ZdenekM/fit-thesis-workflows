# FIT Thesis Workflows

Konverzační workflow pro vedoucí a oponenty BP/DP prací.

Tento repozitář není studentská aplikace, runbook skriptů ani stroj na posudky.
Je to pracovní vrstva pro vedoucí a oponenty: pomáhá rychleji projít zadání,
PDF práce, zdroje, kód, starší zpětnou vazbu, Theses.cz report nebo vlastní
poznámky a připravit kvalitní podklady pro další odborné rozhodování.

Podporuje dvě odlišné situace. Vedoucímu může pomáhat průběžně během semestru
nebo celého akademického roku: kontrolovat postup, porovnávat revize, odhalovat
rizika v textu i kódu a formulovat zpětnou vazbu, která studentovi reálně pomůže
práci zlepšit. Oponentovi pomáhá hlavně při jednorázovém závěrečném zhodnocení:
rychle získat přehled, ověřit problematická tvrzení, připravit otázky a podklady
pro férový posudek.

Cílem je ušetřit čas na mechanické kontrole a lépe nasměrovat pozornost
hodnotitele: co si ověřit v práci, kde doplnit vlastní znalost kontextu, co je
potřeba férově kalibrovat a jak studentovi dát co nejužitečnější zpětnou vazbu.
Agent může připravit návrh textu, ale odpovědnost za hodnocení, finální výběr
argumentů a rozhodnutí zůstává na vedoucím nebo oponentovi.

Agent se používá jako chat. Příklady níže jsou inspirace, ne povinný styl
promptu. Můžete psát stručně, průběžně doplňovat materiály, ptát se na detaily
konkrétní práce a nechat agenta, aby si vyžádal chybějící kontext.

Workflow je stavěné tak, aby šlo provozovat s nástrojem, který máte: **Codex**,
**Claude**, nebo obojím (jeden připraví, druhý nezávisle zkontroluje). Obě
varianty pokrývají většinu review rolí. Codex umí všechny; Claude aktuálně 12
z nich (příprava kódu z GitHubu, získávání zdrojů k citacím a příprava
oponentských podkladů zatím jedou na Codexu). U finálních posudkových review
provede podpisové/hashové kroky u Claude nadřazená (parent) session a review
agent píše jen svůj vlastní výstup. Claude review běží na Linuxu/macOS; na
Windows použijte Codex. Automatický výběr nástroje a jeho vynucení se ještě
dolaďuje (vývojově), takže zatím nástroj zvolte v chatu.

## Nejrychlejší cesta

1. Otevřete chat s agentem v tomto repozitáři.
2. Přiložte soubory nebo napište cesty k nim: zadání, aktuální PDF práce,
   zdrojový zip, kód, starší feedback, Theses.cz report, návrh posudku nebo
   vlastní poznámky.
3. Řekněte, co chcete získat: studentskou zpětnou vazbu, formální posudek
   vedoucího, oponentské podklady, revizní diff, kontrolu kódu, kontrolu citací
   nebo review hotového posudku.
4. Pokud má vzniknout finální nebo odesílatelný výstup, nebo samostatná interní
   evidence, na kterou se budete spoléhat, napište výslovně `použij agenty`.
   Workflow tím spustí nezávislou kontrolu více rolí.
5. Agent si doplní chybějící kontext, založí nebo aktualizuje case, zpracuje
   vstupy v ignorovaném workspace a uloží výstupy do aktivního roundu.

Case data pod `cases/` jsou gitignored. Do repozitáře patří workflow, skripty,
šablony a profily, ne studentská PDF, zdrojové zipy, extrakty, kódové
odevzdávky, soukromé poznámky ani generované case výstupy.

## Co můžete napsat

Nemusíte kopírovat přesný formát. Klidně napište jen cíl a přiložte materiály.
Agent se má pokusit vyčíst typ práce, téma, rok a další metadata z podkladů a
doptat se jen na to, co chybí nebo není spolehlivé. Delší příklady pomáhají
hlavně tehdy, když chcete agentovi rovnou předat fázi práce, vlastní poznámky
nebo kalibraci výstupu.

### Studentská zpětná vazba

```text
Připrav studentovi zpětnou vazbu k aktuální verzi BP/DP.

Přikládám zadání, PDF práce, případně zdrojový zip, kód a Theses.cz report.
Moje poznámky k práci a zadání jsou: <kontext, omezení, co si mám podle tebe
ověřit, co už nechci znovu otevírat>.

Použij agenty. Pokud je dostupný kód, zkontroluj soulad textu s kódem i kvalitu
implementace. Výsledný feedback napiš tak, abych ho mohl poslat studentovi s
minimální úpravou.
```

Pokud chcete, můžete doplnit i jazyk feedbacku, nestandardní deadline nebo
reviewer profile. Když je nedoplníte, agent je má zkusit zjistit z case a
podkladů; pokud to nejde, řekne, co je skutečný blocker.

### Navazující revize

```text
Tady je aktuální verze práce a předchozí zpětná vazba. Založ nový round ve
stávajícím case, porovnej posun od minule a připrav krátký final-sprint
feedback. Použij agenty, dej jim dost času a nálezy z review oprav.
```

Pokud říkáte, že student něco nově doplnil nebo změnil, agent má nejdřív ověřit,
že v case opravdu existují novější odpovídající podklady. Jinak se má doptat,
nebo jasně označit výstup jako provizorní.

### Oponentské podklady

```text
Připrav interní oponentské podklady pro tuto BP/DP. Přikládám zadání, PDF,
zdroje, kód a případně Theses.cz report podobnosti po odevzdání. Použij agenty.
Pokud je dostupný kód, zkontroluj soulad textu s kódem i kvalitu implementace.
Výstup má být interní evidence pro oponenta, ne studentský feedback.
```

### Posudek vedoucího

```text
Připrav draft formálního posudku vedoucího pro IS. Přikládám zadání, aktuální
PDF práce, případně kód a svoje poznámky k aktivitě, samostatnosti, komunikaci,
dokončování, publikacím a navrhované známce/bodům. Použij agenty.
Předchozí feedback využij jen tam, kde je z něj a z revizí vidět reakce
studenta; pokud to průkazné není, opři procesní hodnocení o moje poznámky.
```

### Zpětná vazba z oponentského posudku

```text
Mám oponentský posudek k práci, kterou jsem vedl. Přidej ho do case jako
postmortem vstup, porovnej oprávněné výtky s tím, co student dostal v dřívější
zpětné vazbě, a navrhni, které typy problémů máme příště hlídat lépe.

Použij agenty. Posudek je zatím draft sdílený oponentem ke konzultaci /
oficiální neveřejná kopie / veřejně dostupný posudek.
```

### Review vlastního posudku

```text
Tady je můj draft oponentského posudku. Zkontroluj férovost, oporu v důkazech,
tón, konzistenci bodů/známky, pokrytí zadání a otázky k obhajobě. Použij
agenty. Nálezy promítni jen způsobem, který zachová vazbu na podklady a review,
nebo mi vrať blokující připomínky, pokud by bylo potřeba návrh přepracovat ručně.
```

### Samostatná otázka nebo dílčí kontrola

```text
Podívej se jen na kapitolu evaluace a řekni mi, jestli metriky a závěry
odpovídají tomu, co je v kódu a v README.
```

```text
Udělej samostatný review kódu pro aktuální round. Odděl nesoulad textu s kódem,
design/runtime rizika a nice-to-have zlepšení. Použij agenty.
```

## Co agent potřebuje

Agent se má nejdřív opřít o přiložené podklady a existující case metadata.
Čím konkrétnější vstup dostane, tím méně se ale bude muset doptávat. Nejvíc
pomáhá:

- oficiální zadání nebo jeho věrné shrnutí,
- aktuální PDF práce; odevzdané PDF je autoritativní renderovaná verze,
- zdrojový zip nebo LaTeX/Overleaf export, pokud je užitečný pro diff a hledání,
- kód, repo nebo PR, pokud práce obsahuje implementaci,
- starší feedback a informace, co se od minule změnilo,
- oponentský posudek k práci, kterou jste vedli, pokud má sloužit jako
  postmortem vstup pro budoucí zlepšení supervisor workflow,
- vaše neveřejné poznámky ke kontextu, aktivitě, samostatnosti a komunikaci,
- fáze práce: pracovní verze, předfinální verze, finální kontrola, posudek,
- požadovaný výstup,
- jazyk studentského feedbacku, pokud nemá být výchozí čeština,
- nestandardní deadline nebo reviewer profile, pokud neplynou z case.

U formálního posudku vedoucího agent z artefaktů spolehlivě nepozná aktivitu,
samostatnost, průběh konzultací, komunikaci, dokončování nebo neveřejný komentář
pro studenta. Tyto věci je potřeba dodat jako poznámky vedoucího.

## Co vznikne

Výstupy se ukládají do aktuálního roundu v ignorovaném case workspace, typicky
pod `cases/<case-id>/rounds/<round>/outputs/`. Agent má v závěru uvést přesnou
cestu. Běžné výstupy jsou například:

- `outputs/feedback_student.md` - studentská zpětná vazba,
- `outputs/vedouci_posudek_revidovany.md` - revidovaný návrh posudku vedoucího,
- `outputs/oponent_podklady_revidovane.md` - revidované interní podklady
  oponenta,
- `outputs/oponent_posudek_navrh.md` - čistý návrh oponentského posudku pro IS,
- `outputs/feedback_k_posudku.md` - review návrhu posudku,
- `outputs/revision_diff.md`, `outputs/code_consistency.md`,
  `outputs/code_quality_review.md`, `outputs/literature_citation_review.md`,
  `outputs/figure_media_review.md`, `outputs/typography_formal_review.md` a
  `outputs/theses_similarity_review.md` - interní evidence podle potřeby roundu.

Odesílatelné výstupy nejsou hotové jen tím, že vznikly. Pro finální použití
mají projít nezávislou review smyčkou; technické záznamy o review zůstávají v
ignorovaném `work/` workspace.

## Jak agent pracuje

Agent používá jeden case s historií roundů. U navazujících revizí má přečíst
předchozí feedback, rozlišit vyřešené, částečně vyřešené a stále platné body a
neopakovat staré připomínky mechanicky.

U code-backed prací se mají pro supervisor feedback, posudky vedoucího a
oponentské podklady použít dvě oddělené kontroly: soulad textu s kódem a kvalita
implementace/designu. Pokud to z dostupných vstupů nejde, agent má omezení říct
explicitně.

Před generováním má agent spustit povinné readiness gate pro daný typ výstupu:
studentská zpětná vazba používá `check-supervisor-ready` a kontrolu nastavení
jazyka feedbacku, oponentské materiály `check-round-ready` nebo navazující
oponentní preflight a formální posudek vedoucího vlastní reportovou bránu. Pokud
gate selže, agent má zastavit a říct, co chybí. Podrobnější lifecycle roundu je
v [Operator Reference](docs/operator-reference.md).

Když konkrétní práce ukáže vzorec problému, který se pravděpodobně bude opakovat
i jinde, agent má nejdřív dokončit aktuální výstup a potom navrhnout, jestli se
má lesson promítnout do workflow dokumentace, skillu, šablony nebo TODO.

## Když chcete diagnostiku

Skripty jsou hlavně guardy pro agenta, ne běžný uživatelský interface. Můžete
napsat například:

```text
Spusť readiness a privacy kontroly pro aktuální case a řekni mi, co chybí.
```

V Linux/dev checkoutu se v dokumentaci používají tvary `scripts/<tool>` jako
logické názvy workflow příkazů. Na Windows nespouštějte ani neklikejte bezpříponové
`scripts/<tool>` soubory; nejdřív se balí workflow nástroje a pak se používají
launchery `dist\workflow-tools\bin\<tool>.cmd` nebo
`.\dist\workflow-tools\bin\<tool>.ps1`, například
`dist\workflow-tools\bin\init-review-manifest.cmd` nebo
`.\dist\workflow-tools\bin\init-review-manifest.ps1`. Detaily jsou v
[Workflow Command Surface](docs/workflow-command-surface.md).

## Další reference

- [Operator Reference](docs/operator-reference.md) - podrobnější mapy výstupů,
  povinných gate, reportových flow, diagnostiky a méně častých workflow
  situací.
- [Workflow Command Surface](docs/workflow-command-surface.md) - přesný kontrakt
  helperů, balení a Windows launcherů.
- [Agent Scheduling](docs/agent-scheduling.md) a
  [Agent Profile Matrix](docs/agent-profile-matrix.md) - role agentů,
  review oddělení a validační pravidla.
- [PDF Detail Layer](docs/pdf-detail-layer.md) - volitelná detailní práce s PDF,
  obrázky a layoutem.
- [Local RAG Usage](docs/local-rag-usage.md) - volitelná discovery vrstva pro
  historickou orientaci v Markdown dokumentaci, plánech, skills a case
  výstupech.
- [Profiles](profiles/README.md) - reviewer profily a soukromé lokální
  preference.
- [Maintainer Reference](docs/maintainer-reference.md) - údržba workflow
  dokumentace, plánů, soukromí a developer hygiene.
