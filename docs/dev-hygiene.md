# Developer Hygiene

Tyto kontroly hlídají růst a udržitelnost samotného workflow repozitáře. Jsou
určené pro vývojářské změny skriptů, helperů, skillů a testů. Nejsou součástí
case pipeline, `scripts/check-tooling`, `scripts/case-doctor`,
`scripts/opponent-closeout` ani žádného studentského nebo oponentského běhu.

## Cíle

```bash
pants run :vulture
pants run :jscpd
pants run :omen
```

- `:vulture` používá `vulture==2.16` a hledá pravděpodobně mrtvý Python kód v
  `.codex/hooks`, `scripts`, `src` a `tests` s minimální confidence `85`.
- `:jscpd` používá platform-aware Python/Pex wrapper, který volá
  `npx --yes jscpd@4.0.9` bez POSIX shell syntaxe, a hledá kopie přes stejné
  vývojové cesty. Baseline je zatím pod hranicí `5 %`, takže cíl může běžet bez
  blokování aktuálního stavu.
- `:omen` očekává nainstalované `omen` na `PATH`, explicitní `OMEN_BIN`, nebo
  lokální netrackovaný binár podle platformy v
  `.pants.d/dev-tools/omen/bin/` (`omen` nebo `omen.exe`). Také běží přes
  platform-aware Python/Pex wrapper. Spouští rychlý health overview přes
  `omen score`, `omen hotspot` a `omen deadcode`.

Omen konfigurace je v `omen.toml`. Záměrně ignoruje `cases/`, `dist/`, cache a
lokální virtuální prostředí, aby vývojářská analýza nikdy nelezla do soukromých
case dat ani generovaných výstupů. Toto pravidlo platí pro repo-dev target
`pants run :omen`; neznamená, že code-quality role nesmí cíleně spustit Omen
nad připraveným studentským kódem uvnitř ignorovaného case workspace.

## Kdy spouštět

Používejte je při větších změnách v repo toolingu, hlavně když:

- přibývá nový workflow helper nebo validator,
- upravujete více souvisejících CLI modulů,
- kopírujete existující smoke/validator pattern,
- máte podezření, že starší helper už není používán.

Omen má dvě vývojářské vrstvy:

- Omen MCP zkuste průběžně během slice jako rychlý, scopovaný advisory signál
  nad dotčenými Python moduly nebo balíky, pokud umí zamýšlený target skutečně
  analyzovat. Hodí se hlavně po změnách validátorů, CLI helperů,
  manifest/review-wave logiky, approval records a workflow orchestrace.
- `pants run :omen` používejte jako reprodukovatelný repo-level důkaz pro větší
  kódový slice nebo finální closeout. Výsledek lze zapsat do plánu nebo
  `Final Audit`; MCP průběžné kontroly jsou užitečné pro práci, ale samy o sobě
  nejsou stabilním closeout artefaktem.

Když plán, prompt, review nebo repo instrukce explicitně vyžaduje Omen, nestačí
ho jednou zkusit a pokračovat bez něj. Nejdřív opravte scope nebo lokální
tooling, zkuste konkrétnější modul/balík/root, případně použijte druhou vrstvu
Omenu (MCP vs. `pants run :omen`). Teprve potom smí closeout pokračovat bez
Omenu, a to jen se zapsaným konkrétním blockerem nebo typed limitation. U kódově
těžké repo-maintainer změny, kde byl Omen požadovaný gate, zastavte a vyžádejte
si rozhodnutí místo tiché náhrady jinými kontrolami.

Pokud Omen MCP vrátí nulové soubory nebo symboly pro neprázdný zamýšlený root,
nejde o důkaz dobré kvality. Nejprve upravte scope na konkrétní analyzovatelný
modul nebo balík; pokud ani to nepomůže, zapište tool/path-handling limitaci a
opřete closeout o jiné relevantní kontroly. Pokud byl Omen explicitní required
gate pro kódově těžkou změnu, platí stop-and-ask pravidlo z předchozího odstavce.

Výstupy jsou vývojářský signál. Pokud nástroj najde problém, opravte sdílený
design nebo zaznamenejte vědomou baseline; nepřidávejte výjimky jen proto, aby
kontrola ztichla.

## Aktuální baseline

Po refaktoringovém plánu z 2026-05-06 platí tato výchozí baseline; Omen byl
naposledy aktualizován samostatným během 2026-05-20:

- `pants run :vulture`: bez hlášení.
- `pants run :jscpd`: 4 klony, 94 duplicitních řádků, 0.74 % celkově.
- `pants run :omen`: grade A, score 91.02, 15 critical hotspotů a 15 high
  hotspotů.

Zbývající jscpd klony jsou opakované validační patterny mezi feedback,
figure/media, opponent-materials a typography/formal checkery. Nejsou zapojené
do case pipeline gates; řešit je má další konkrétní refaktoringový plán, ne
plošné ztišení nástroje.

## Lokální instalace Omenu

Omen není vendorizovaný ani automaticky instalovaný repozitářem. Upstream CLI se
instaluje mimo tracked repo, typicky přes GitHub release tarball. Upstream README
zmiňuje i Cargo instalaci:

```bash
cargo install omen-cli
```

Před instalací přes Cargo ověřte, že je balík dostupný v crates.io indexu, a
zkontrolujte požadovanou Rust verzi v upstream `Cargo.toml`.
Aktuální release se dá držet i jen lokálně pod
`.pants.d/dev-tools/omen/bin/omen` nebo
`.pants.d/dev-tools/omen/bin/omen.exe`, což je ignorovaná vývojářská cache.
Pokud `pants run :omen` hlásí, že `omen` nenašlo, nejde o chybu pipeline; je to
chybějící lokální vývojářský nástroj.
