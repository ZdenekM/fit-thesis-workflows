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
  lokální netrackovaný binár v `.pants.d/dev-tools/omen/bin/omen`. Také běží
  přes platform-aware Python/Pex wrapper. Spouští rychlý health overview přes
  `omen score`, `omen hotspot` a `omen deadcode`.

Omen konfigurace je v `omen.toml`. Záměrně ignoruje `cases/`, `dist/`, cache a
lokální virtuální prostředí, aby vývojářská analýza nikdy nelezla do soukromých
case dat ani generovaných výstupů.

## Kdy spouštět

Spouštějte je při větších změnách v repo toolingu, hlavně když:

- přibývá nový workflow helper nebo validator,
- upravujete více souvisejících CLI modulů,
- kopírujete existující smoke/validator pattern,
- máte podezření, že starší helper už není používán.

Výstupy jsou vývojářský signál. Pokud nástroj najde problém, opravte sdílený
design nebo zaznamenejte vědomou baseline; nepřidávejte výjimky jen proto, aby
kontrola ztichla.

## Lokální instalace Omenu

Omen není vendorizovaný ani automaticky instalovaný repozitářem. Upstream CLI se
instaluje mimo tracked repo, typicky přes GitHub release tarball. Upstream README
zmiňuje i Cargo instalaci:

```bash
cargo install omen-cli
```

Před instalací přes Cargo ověřte, že je balík dostupný v crates.io indexu, a
zkontrolujte požadovanou Rust verzi v upstream `Cargo.toml`.
Aktuální release se dá držet i jen lokálně pod `.pants.d/dev-tools/omen/bin/omen`,
což je ignorovaná vývojářská cache. Pokud `pants run :omen` hlásí, že `omen`
nenašlo, nejde o chybu pipeline; je to chybějící lokální vývojářský nástroj.
