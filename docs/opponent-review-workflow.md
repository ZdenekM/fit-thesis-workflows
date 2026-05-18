# Opponent Review Workflow

Tento dokument doplňuje chat-first postup v `README.md`. Popisuje, jak má agent
poskládat interní oponentské podklady z evidence, role-specific review a
closeout kontrol. Není to návod k ručnímu psaní finálního IS posudku.

`scripts/<tool>` v tomto dokumentu znamená logický workflow příkaz. Na Linux
checkoutu jsou POSIX wrappery v `scripts/` v pořádku; na Windows používejte po
zabalení workflow nástrojů odpovídající `.cmd` nebo `.ps1` launchery popsané
v `README.md`. Bezpříponové `scripts/<tool>` soubory na Windows nespouštějte
ani neotvírejte kliknutím; Windows je může zkusit otevřít jako dokument.

## Intake And Preflight

V optimalizovaném roundu začněte sdílenou deterministic hranicí:

```bash
scripts/review-round-start --profile opponent_materials <case-id> [round-id]
scripts/prepare-review-round --profile opponent_materials <case-id> [round-id]
```

První příkaz potvrdí aktuální materiály, import/extract/code workspace a zapíše
`work/review_run_trace.json`. Druhý příkaz připraví role packets a
`work/review_role_plan.json`; agenti se spawnují až podle tohoto plánu. Hodnota
`opponent_materials` je workflow/operator surface mapovaná na canonical
materiality profil `opponent_review`, ne Codex agent profile.

Nižší profilový preflight zůstává dostupný a používá se přímo nebo delegovaně
ze shared path:

```bash
scripts/opponent-preflight <case-id> [round-id]
```

Preflight tvrdě kontroluje opponent readiness, reviewer profil, tooling, lokální
code workspace a GitHub intake pro GitHub odkazy nalezené v round notes. Zároveň
spouští před-agentní evidence helpery, pokud mají v daném roundu relevantní
vstupy:

- `scripts/check-code-reproducibility` zapisuje
  `work/code_reproducibility.json`. Jde o statickou klasifikaci dostupného kódu,
  dependency souborů, entrypointů, README instrukcí a případné už dříve
  autorizované run evidence. Studentský kód nespouští.
Evidence requirements jsou výjimka z před-agentního preflightu:
`work/evidence_requirements.json` musí připravit autorizovaný evidence agent nebo
člověk jako strukturovaný přehled požadované a dostupné evidence. Potom spusťte
`scripts/check-evidence-presence`; skript artefakt jen ověřuje a zapíše
strukturální `work/media_presence_inventory.jsonl` podle cest a přípon
nalezených souborů.
Assignment coverage je výjimka z před-agentního preflightu: `work/assignment_coverage_agent.json`
musí připravit autorizovaný text/assignment agent nebo člověk jako strukturovanou
mapu bodů zadání proti dostupné evidenci. Potom spusťte
`scripts/check-assignment-coverage`; skript artefakt jen ověřuje, nevyvozuje
splnění zadání z volného textu a nerozhoduje známku.
Kvantitativní/result claimy jsou stejný typ semantického handoffu:
`work/quantitative_claims.json` připraví autorizovaný
`thesis-quantitative-claims-review` agent nebo člověk, potom spusťte
`scripts/check-evaluation-claims`. Deterministické skripty nerozšiřujte o
raw-text heuristiky pro význam metrik; prose-only metrické claimy má do tohoto
skillu směrovat textový, code nebo figure/media agent.

Theses.cz report podobnosti se importuje jen explicitně přes
`scripts/import-theses-report <case-id> [round-id] REPORT.pdf`. Strukturální
import a `scripts/check-theses-similarity-report` nevydávají verdikt o
plagiátu, autorství ani bodech; podezřelé nebo nevysvětlené shody posuzuje
autorizovaný `thesis-theses-similarity-review` agent v kontextu zadání,
aktuální práce a předchozích roundů. Čistý, očekávaný self-overlap nebo
vysvětlený report má zůstat v oponentské syntéze tichý.

Tyto artefakty jsou poradní. Chybějící evidence je riziko nebo požadavek na
ruční ověření, ne automatický důkaz, že je tvrzení práce nepravdivé.

## Role Packets

Před spawnutím role-split agentů spusťte:

```bash
scripts/prepare-opponent-packets <case-id> [round-id]
```

Příkaz vytvoří `work/opponent_packets/*.md` pro role jako assignment/text, code
consistency, code quality, figure/media, literature, typography, Theses.cz
similarity a synthesis.
Packet obsahuje autoritativní vstupy, dostupné work/output artefakty, očekávané
role-owned výstupy a známá omezení. Nenahrazuje skill ani evidence pravidla,
jen zmenšuje prompt drift mezi agenty. Packet generation snižuje opakované
čtení kontextu, ale nesnižuje povinné role, nezávislé review ani manifest
coverage.

Pokud se po vygenerování packetů změní zadání, evidence requirements,
reprodukovatelnost nebo výstupy interních review, packety přegenerujte.
Po každé hlavní vlně použijte odpovídající `scripts/check-review-wave` profil.
Když agent tvrdí, že artefakt zapsal, ale gate ho nenajde nebo odmítne,
rozhoduje file systém a checker.

## Evidence Outputs

Oponentská syntéza má podle dostupných vstupů používat samostatnou interní
evidenci:

- `outputs/revision_diff.md`
- `outputs/code_consistency.md`
- `outputs/code_quality_review.md`
- `outputs/github_code_intake.md`
- `work/quantitative_claims.json`
- `outputs/literature_citation_review.md`
- `outputs/figure_media_review.md`
- `outputs/typography_formal_review.md`
- `outputs/theses_similarity_review.md`
- `work/theses_similarity/assessment.json`
- `outputs/reference_report_comparison.md`
- `outputs/opponent_reading_packet.md`

Pro jádrové code/revision artefakty existují strukturální validátory:

```bash
scripts/check-revision-diff <case-id> [round-id]
scripts/check-code-consistency <case-id> [round-id]
scripts/check-code-quality-review <case-id> [round-id]
scripts/check-literature-citation-review <case-id> [round-id]
scripts/check-evaluation-claims <case-id> [round-id]
scripts/check-theses-similarity-report <case-id> [round-id]
```

Validátory hlídají tvar, konkrétní evidence odkazy, omezení, review status,
placeholdery a úniky interních absolutních cest. Nejsou to judgment enginy.

## Provenance

Po dokončení dílčího výstupu ho lze zapsat průběžně:

```bash
scripts/register-review-artifact <case-id> <round-id> outputs/code_quality_review.md --role code_quality
```

Helper zapisuje do `work/review_manifest.json` hash artefaktu a pro výstupní
review artefakty i generator/reviewer role, review basis, použitou evidenci,
checky, omezení a informaci, zda syntéza používá konkrétní findings. Pro
operator-only work artefakty zapisuje užší podpůrný záznam s hashem a metadaty.
Tím odpadá ruční rekonstrukce manifestu až po skončení všech agentů.

Po vzniku nebo změně revidovaných podkladů obnovte manifest:

```bash
scripts/init-review-manifest --run-checks <case-id> [round-id]
scripts/check-agent-coverage <case-id> [round-id]
scripts/check-review-manifest --require-complete <case-id> [round-id]
```

Nezávislé finální review se do closeoutu nepřenáší jen závěrečnou zprávou
agenta. Review agent nebo člověk zapíše strukturovaný approval record pod
`work/reviews/*_review.json`, typicky
`work/reviews/opponent_materials_review.json` pro
`outputs/oponent_podklady_revidovane.md` a
`work/reviews/opponent_report_review.json` pro review posudku. Záznam musí
obsahovat verdict, počet blokujících nálezů, reviewer roli, hash revidovaného
artefaktu, hash review basis, pozorované kontroly a omezení. `init-review-manifest`
ho automaticky sesbírá jako supporting work artefakt a propíše aktuální review
metadata do manifestu; pozdější úprava revidovaného artefaktu nebo review basis
pak spadne jako stale hash.
Pro `opponent_report_review` musí observed checks obsahovat
`check-opponent-report:canonical`, `check-opponent-report:clean` a
`check-review-wave.opponent-report.draft`; finální
`check-review-wave --workflow opponent_report_review --wave final` běží až nad
hotovým approval recordem, takže se do approval recordu nezapisuje jako jeho
vstupní podmínka.

Approval record se neuzavírá ruční opravou hashe. Po materiální úpravě znovu
spusťte review nebo zapište explicitní typovanou výjimku a omezení.
Když se změní jen operator notes nebo approval record a common briefing hlásí
stale hash, spusťte `scripts/refresh-round-hashes <case-id> [round-id]`.
Tento helper obnovuje jen deterministické hash-bound pomocné artefakty a nesmí
nahrazovat review deltu ani novou nezávislou kontrolu.

Pokud existuje `outputs/code_consistency.md`, `outputs/code_quality_review.md`,
`outputs/revision_diff.md` nebo manifestem registrované
`work/quantitative_claims.json`, manifest closeout vyžaduje příslušný
strukturální validátor jako passed helper check.
Kalibrační výstupy `outputs/reference_report_comparison.md` a
`outputs/opponent_reading_packet.md` jsou internal-only, ale closeout pro ně
vyžaduje vlastní nezávislý review záznam a aktuální reviewed hash; nesmí být jen
implicitně pokryté pozdější syntézou.

Po přečtení podkladů a draftu může oponent zapsat připomínky do
`notes/opponent-report-operator-feedback.md`. Autorizovaný agent nebo člověk je
potom převede do `work/opponent_report_revision_request.json`: typovaného
požadavku na revizi, který hashem váže původní připomínky, revidované podklady,
snapshot původního trace, snapshot původního draftu posudku, kalibrační
use/advisory artefakt, srovnání s profilem a reading packet. Snapshoty patří do
`work/opponent_report_revision_sources/`, aby pozdější přepsání aktivního trace
nebo draftu nezneplatnilo záznam toho, co oponent skutečně četl.
Deterministické kontroly pracují jen s touto strukturou, ne s významem volného
textu v poznámkách.

Když se připomínky použijí, agent nebo člověk upraví
`work/opponent_report_trace.json` a zapíše do něj `calibration_context`.
Ten hashem váže přesné vstupní kalibrační a revizní artefakty, které vedly k
úpravě trace. Potom se draft znovu vygeneruje přes
`scripts/draft-opponent-report --force <case-id> [round-id]`, ověří přes
`scripts/check-opponent-report --mode canonical <case-id> [round-id]` a
vyexportuje přes `scripts/export-opponent-report <case-id> [round-id]`.
Před považováním clean návrhu za sendable obnovte manifest, spusťte
coverage/manifest kontroly a nezávislé review oponentského posudku.

Po lidském dofinalizování a nezávislém review posudku může oponent případ
označit jako kandidáta pro budoucí rozšíření soukromé kalibrace pomocí
`work/opponent_calibration_refresh_eligibility.json`. Tento marker hashem váže
revidované podklady, přijatý trace, finalizovaný draft, review posudku,
snapshot finalizačního manifestu pod
`work/opponent_calibration_refresh_sources/review_manifest.json` a souhlas
oponenta. Snapshot se pořizuje před tím, než se samotný eligibility marker
začne sbírat do aktivního manifestu. Nesmí kopírovat data ani měnit kalibrační
profil; pozdější refresh profilu zůstává samostatný autorizovaný workflow krok.

## Report Draft Boundary

`outputs/oponent_podklady_revidovane.md` jsou interní revidované podklady pro
oponenta. Než z nich vznikne draft posudku, autorizovaný agent nebo člověk musí
připravit `work/opponent_report_trace.json`: strukturované mapování položek FIT
IS, otázek k obhajobě, ručních kontrol a nejistot na aktuální revidované
podklady. `scripts/draft-opponent-report` pak z tohoto trace vytvoří
trace-bound `work/oponent_posudek_draft.md`, ale tento draft není finální
posudek.

`scripts/check-opponent-report --mode canonical` projde až po lidské kalibraci
bodů, známky a formulací. Ověřuje strukturální tvar draftu, hash trace, hash
revidovaných podkladů a bezpečnost veřejného textu; neporovnává volný text
materiálů a posudku tokenově. `scripts/export-opponent-report` potom vytvoří
`outputs/oponent_posudek_navrh.md`, odstraní pouze source metadata, úvodní
statusové řádky a privátní checklist a spustí i clean kontrolu. Report-review
agenti mají číst clean návrh jako primární text.

Finální oponentský gate:

```bash
scripts/review-round-start --profile opponent_report_review <case-id> [round-id]
scripts/prepare-review-round --profile opponent_report_review <case-id> [round-id]
scripts/check-review-wave --workflow opponent_report --wave draft <case-id> [round-id]
scripts/check-review-wave --workflow opponent_report_review --wave final <case-id> [round-id]
scripts/review-round-closeout --profile opponent_report_review <case-id> [round-id]

scripts/review-round-closeout --profile opponent_materials <case-id> [round-id]
scripts/opponent-closeout <case-id> [round-id]
```

`review-round-closeout` je shared closeout: ověří role plan, manifest, coverage,
approval records, unresolved `work/review_deltas/*.json` a profile gate. Před
změnou manifestu kontroluje, že `work/review_run_trace.json` a
`work/review_role_plan.json` patří ke stejnému profilu; při přechodu z
`opponent_materials` na `opponent_report_review` je proto potřeba spustit
profilový start a prepare krok znovu. Pro oponentské materiály potom deleguje
profilové kontroly do `opponent-closeout`,
který znovu projde revidované podklady, report trace, případný report draft,
manifest, agent coverage, private-data kontrolu a skriptovou hygienu.

## Opponent-Facing Boundary

Oponentské podklady a posudek nesmí do prose pro oponenta nebo IS propouštět
interní packet paths, manifest hashe, private URLs, raw PR metadata,
review-thread detaily, raw Theses.cz report URLs/source internals, lokální
workspace cesty ani stav generated draftu. Používejte je pouze jako interní
evidenci a do report-facing textu převádějte jen věcné závěry, jistotu,
omezení a ruční kontroly. Podobnostní report zmiňujte jen tehdy, když
`outputs/theses_similarity_review.md` nese materiální nevyřešený nebo
institucionálně potřebný závěr; čisté a vysvětlené reporty zůstávají tiché.
