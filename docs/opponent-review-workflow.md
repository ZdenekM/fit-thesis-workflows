# Opponent Review Workflow

Tento dokument doplňuje chat-first postup v `README.md`. Popisuje, jak má agent
poskládat interní oponentské podklady z evidence, role-specific review a
closeout kontrol. Není to návod k ručnímu psaní finálního IS posudku.

`scripts/<tool>` v tomto dokumentu znamená logický workflow příkaz. Na Linux
checkoutu jsou POSIX wrappery v `scripts/` v pořádku; na Windows používejte po
zabalení workflow nástrojů odpovídající `.cmd` nebo `.ps1` launchery popsané
v `README.md`.

## Intake And Preflight

Začněte příkazem:

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

Tyto artefakty jsou poradní. Chybějící evidence je riziko nebo požadavek na
ruční ověření, ne automatický důkaz, že je tvrzení práce nepravdivé.

## Role Packets

Před spawnutím role-split agentů spusťte:

```bash
scripts/prepare-opponent-packets <case-id> [round-id]
```

Příkaz vytvoří `work/opponent_packets/*.md` pro role jako assignment/text, code
consistency, code quality, figure/media, literature, typography a synthesis.
Packet obsahuje autoritativní vstupy, dostupné work/output artefakty, očekávané
role-owned výstupy a známá omezení. Nenahrazuje skill ani evidence pravidla,
jen zmenšuje prompt drift mezi agenty.

Pokud se po vygenerování packetů změní zadání, evidence requirements,
reprodukovatelnost nebo výstupy interních review, packety přegenerujte.

## Evidence Outputs

Oponentská syntéza má podle dostupných vstupů používat samostatnou interní
evidenci:

- `outputs/revision_diff.md`
- `outputs/code_consistency.md`
- `outputs/code_quality_review.md`
- `outputs/github_code_intake.md`
- `outputs/literature_citation_review.md`
- `outputs/figure_media_review.md`
- `outputs/typography_formal_review.md`

Pro jádrové code/revision artefakty existují strukturální validátory:

```bash
scripts/check-revision-diff <case-id> [round-id]
scripts/check-code-consistency <case-id> [round-id]
scripts/check-code-quality-review <case-id> [round-id]
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

Pokud existuje `outputs/code_consistency.md`, `outputs/code_quality_review.md`
nebo `outputs/revision_diff.md`, manifest closeout vyžaduje příslušný
strukturální validátor jako passed helper check.

## Report Draft Boundary

`outputs/oponent_podklady_revidovane.md` jsou interní revidované podklady pro
oponenta. `scripts/draft-opponent-report` z nich může vytvořit
`work/oponent_posudek_draft.md`, ale tento draft není finální posudek.

`scripts/check-opponent-report` projde až po lidské kalibraci bodů, známky a
formulací. Nové evidence helpery mohou přidat důvody k ruční kontrole nebo
zastavení, ale nesmí automaticky posudek schválit.

Finální oponentský gate:

```bash
scripts/opponent-closeout <case-id> [round-id]
```

Closeout znovu projde revidované podklady, manifest, agent coverage, report
draft gate, pokud draft existuje, private-data kontrolu a skriptovou hygienu.
