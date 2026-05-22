# Maintainer Reference

Tato stránka shrnuje údržbovou část workflow dokumentace. Není určená jako
první čtení pro vedoucího nebo oponenta; hlavní vstup zůstává root `README.md`.

## Zásady

- Udržujte root `README.md` jako stručný chat-first entrypoint pro potenciální
  uživatele.
- Dlouhé postupy patří do `.agents/skills/`, `docs/`, šablon nebo plánů.
- Active workflow rules patří do `AGENTS.md`; lessons a rationale do
  `WORKFLOW_MEMORY.md`; otevřená práce do `TODO.md`.
- Soukromá case data nepatří do gitu ani do tracked příkladů.
- Windows je podporovaný operator platform. Operator-facing příkazy musí mít
  Python/Pants/PEX surface nebo native `.cmd`/`.ps1` launchery.

## Soukromí A Git

Do gitu nepatří studentská PDF, zdrojové zipy, extrakty, kódové odevzdávky,
soukromé poznámky ani vygenerované case výstupy. Tyto věci mají zůstat pod
ignorovaným `cases/`.

Běžné hlášení problému z konkrétní práce zůstává v case workspace jako omezení,
sanitizovaný issue report, review delta nebo operation-log událost. Úpravy
tracked workflow souborů jsou maintainer práce a vyžadují výslovný souhlas v
aktuálním požadavku.

Před commitem workflow změn:

```bash
git status --short --untracked-files=all
git diff --check
scripts/check-private
scripts/check-scripts
```

## Developer Hygiene

Při větších úpravách samotného repo toolingu jsou k dispozici vývojářské
kontroly:

```bash
pants run :vulture
pants run :jscpd
pants run :omen
```

Tyto cíle hlídají mrtvý kód, duplicity a obecné codebase health signály. Nejsou
součástí thesis case pipeline ani operátorských closeout gate. Scope a aktuální
baseline jsou v [Developer Hygiene](dev-hygiene.md).

Omen má dvě oddělené role:

- `pants run :omen` je repo-maintainer hygiena a záměrně ignoruje `cases/`;
- code-quality reviewer může použít Omen jako volitelný case-local advisory
  signál nad připraveným studentským rootem v ignorovaném workspace.

## Plánování Větších Změn

Větší workflow nebo tooling změny se plánují v tracked souborech pod `plans/`.
Aktivní plán patří do `plans/*_plan.md`, hotový nebo nahrazený plán do
`plans/archive/`. `TODO.md` zůstává jen dlouhodobý seznam otevřené práce.

Plán má obsahovat cíl, auditní základ, scope, non-goals, malé implementační
slices, přesné ověřovací příkazy, průběžný stav a final audit. Kontrakt je v
[Plans](../plans/README.md).

## Workflow Příkazy

Checklist pro nový operator workflow příkaz:

- POSIX wrapper pod `scripts/`,
- CLI modul pod `src/thesis_review_workflow/cli/`,
- položka ve `WORKFLOW_COMMAND_MODULES`,
- `python_source` v `src/thesis_review_workflow/cli/BUILD`,
- runtime dependency v packaging konfiguraci,
- `pex_binary(tags=["workflow-tool"])` v `scripts/BUILD`,
- cílený smoke skript nebo pytest,
- balicí evidence pro `.cmd` a `.ps1` launchery.

`scripts/<tool>` v dokumentaci je Linux/dev zkratka a zároveň logický název
workflow příkazu. Na Windows se používají balené launchery v
`dist\workflow-tools\bin\`. Podrobnější kategorizace command surface je v
[Workflow Command Surface](workflow-command-surface.md).

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
```

Linuxové smoke testy umí pro Windows launchery ověřit hlavně strukturu a
generovaný obsah. Nejsou důkazem nativního Windows runtime chování v cmd nebo
PowerShellu. Pokud je změna citlivá na Windows cesty, subprocessy, dočasné
soubory nebo encoding, zapište Linux výsledek jako strukturální evidence a
nepředstírejte nativní Windows ověření bez skutečného Windows běhu.

## Dokumentační Hranice

Použijte tyto cílové soubory:

- `README.md` - stručný user-facing entrypoint a inspirační prompty,
- `docs/operator-reference.md` - delší operátorská reference a mapy výstupů,
- `docs/workflow-command-surface.md` - command kontrakty, launchery a Windows
  boundary,
- `docs/agent-scheduling.md` - concurrency, wave sequencing a subagent
  handoffy,
- `docs/agent-profile-matrix.md` - role profily, allowed writes a validators,
- `.agents/skills/*/SKILL.md` - role-specific workflow postupy,
- `profiles/README.md` - reviewer profile pravidla,
- `plans/README.md` - plánovací kontrakt.
