# Developer Hygiene

Tyto kontroly hlídají růst a udržitelnost samotného workflow repozitáře. Jsou
určené pro vývojářské změny skriptů, helperů, skillů a testů. Nejsou součástí
case pipeline, `scripts/check-tooling`, `scripts/case-doctor`,
`scripts/opponent-closeout` ani žádného studentského nebo oponentského běhu.

## Cíle

```bash
pants run :vulture
pants run scripts:jscpd
pants run scripts:omen
```

- `:vulture` používá `vulture==2.16` a hledá pravděpodobně mrtvý Python kód v
  `.codex/hooks`, `scripts`, `src` a `tests` s minimální confidence `85`.
- `:jscpd` používá platform-aware Python/Pex wrapper, který volá
  `npx --yes jscpd@4.0.9` bez POSIX shell syntaxe, a hledá kopie přes stejné
  vývojové cesty. Baseline je zatím pod hranicí `5 %`, takže cíl může běžet bez
  blokování aktuálního stavu.
- `scripts:omen` očekává nainstalované `omen` na `PATH`, explicitní `OMEN_BIN`,
  nebo lokální netrackovaný binár podle platformy v
  `.pants.d/dev-tools/omen/bin/` (`omen` nebo `omen.exe`). Spouští runner
  `src/thesis_review_workflow/cli/omen_quality.py`, popsaný níže.

`scripts:omen` a `scripts:jscpd` jsou v `scripts/BUILD`, ne v kořenovém `BUILD`:
`pants run` u `pex_binary` definovaného v kořeni repozitáře, který není source
root, nenaimportuje vlastní balík (`No module named 'thesis_review_workflow'`).
`:vulture` v kořeni zůstává, protože spouští jen skript z requirementu.

## Omen runner

```bash
pants run scripts:omen
pants run scripts:omen -- complexity --focus src/thesis_review_workflow/<modul>.py
pants run scripts:omen -- --help
```

Bez argumentů běží `score`, `complexity`, `clones`, `satd`, `tdg` a `hotspot`
(volitelně i `churn`) v JSON režimu a tiskne krátký přehled: souhrnná čísla, pět
nejhorších položek každého analyzátoru a ratchety. Návrh je převzatý z
shaas-suite (`research/brick_smr/scripts/omen_quality.py`):

- **Prázdný výsledek není čistý výsledek.** Když `complexity`, `tdg`, `hotspot`
  nebo `churn` nevrátí žádný soubor, runner skončí chybou a nic nevypíše. Přesně
  takhle selhává Omen MCP nad tímto repozitářem.
- **Soukromá data.** Každá cesta v každém výstupu se kontroluje proti `cases/` a
  `dist/`; nález znamená chybu, ne varování.
- **Ratchety.** `THRESHOLDS` v runneru drží skóre, nejhorší a p90 cyklomatickou
  složitost, podíl duplicit a průměrné TDG skóre krok za hodnotou naměřenou
  2026-10-06. Zhoršení za ratchet vrátí nenulový exit. Když se kód zlepší,
  ratchet utáhněte; povolit ho jde jen se zapsaným důvodem tady.
- **Neběžící analyzátor nemá ratchet.** Při `pants run scripts:omen -- complexity`
  se kontrolují jen ratchety `complexity`; plný běh bez argumentů kontroluje všechny.
- **Historie.** `churn` čte git historii, ignoruje `exclude` a okno mu runner
  předává jako `--days 180`. Může proto uvést trackovaný veřejný `cases/README.md`;
  projde jen to, co povoluje `check_private.allowed_sensitive_tracked`. Prázdné okno
  u `hotspot`/`churn` není chyba, runner ho jen ohlásí.
- **`--focus <soubor>`** vypíše složitost všech funkcí v dotčeném modulu. Je to
  scoped kontrola během slice a funguje i tam, kde MCP vrací nulu. Soubor, který
  Omen neanalyzoval, je chyba, ne prázdný seznam.

Co Omen 4.24.2 tady neměří, i když vypíše číslo (naměřeno 2026-10-06):

- `deadcode` hlásí 0 položek a všech 3443 definic jako dosažitelných, protože pro
  Python nestaví call graph. Autoritou pro mrtvý kód je `pants run :vulture`;
  `deadcode` proto v runneru není.
- `smells` vidí mezi 217 komponentami 0 importních hran, takže jeho nula není
  důkaz a v runneru není. Složky skóre `coupling` a `smells` stojí na stejném
  prázdném grafu a runner je označí jako `NOT MEASURED`.
- Python v `.claude/hooks` a `.codex/hooks` Omen přeskakuje jako skryté adresáře.

Omen konfigurace je v `omen.toml`. Klíč musí být `exclude`: Omen 4.24.2 klíč
`exclude_patterns` tiše ignoruje (`tests/test_omen_quality.py` to hlídá). Stejně
bez účinku byly `[churn] since`/`top` a `[hotspot] top`, proto v konfiguraci nejsou.
Záměrně ignoruje `cases/`, `dist/`, cache a lokální virtuální prostředí, aby vývojářská analýza nikdy nelezla do soukromých
case dat ani generovaných výstupů. Toto pravidlo platí pro repo-dev target
`pants run scripts:omen`; neznamená, že code-quality role nesmí cíleně spustit Omen
nad připraveným studentským kódem uvnitř ignorovaného case workspace.

## Kdy spouštět

Používejte je při větších změnách v repo toolingu, hlavně když:

- přibývá nový workflow helper nebo validator,
- upravujete více souvisejících CLI modulů,
- kopírujete existující smoke/validator pattern,
- máte podezření, že starší helper už není používán.

Omen má dvě vývojářské vrstvy:

- Během slice použijte scopovaný signál nad dotčenými moduly:
  `pants run scripts:omen -- complexity --focus <soubor>`, nebo Omen MCP, pokud
  zamýšlený target skutečně analyzuje (nad tímto repozitářem 2026-10-06 vracel
  nulové soubory). Hodí se hlavně po změnách validátorů, CLI helperů,
  manifest/review-wave logiky, approval records a workflow orchestrace.
- `pants run scripts:omen` používejte jako reprodukovatelný repo-level důkaz pro větší
  kódový slice nebo finální closeout. Výsledek lze zapsat do plánu nebo
  `Final Audit`; MCP průběžné kontroly jsou užitečné pro práci, ale samy o sobě
  nejsou stabilním closeout artefaktem.

Když plán, prompt, review nebo repo instrukce explicitně vyžaduje Omen, nestačí
ho jednou zkusit a pokračovat bez něj. Nejdřív opravte scope nebo lokální
tooling, zkuste konkrétnější modul/balík/root, případně použijte druhou vrstvu
Omenu (MCP vs. `pants run scripts:omen`). Teprve potom smí closeout pokračovat bez
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

Po refaktoringovém plánu z 2026-05-06 platí tato výchozí baseline pro
`:vulture`; `scripts:jscpd` a `scripts:omen` byly naposledy měřeny 2026-10-06:

- `pants run :vulture`: bez hlášení.
- `pants run scripts:jscpd`: 19 klonů, 492 duplicitních řádků, 0.83 % celkově.
- `pants run scripts:omen`: grade A, score 90.16; nejhorší funkce cyklomatická
  složitost 81 (`agent_coverage.py::validate_coverage`), p90 8; duplicity
  10.2 %; TDG B+ (89.76); 0 critical a 9 high hotspotů. Jde o jiné měřítko než
  dřívější baseline 91.02: ten počítal hotspoty přes `omen hotspot` v textovém
  režimu.

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
Pokud `pants run scripts:omen` hlásí, že `omen` nenašlo, nejde o chybu pipeline; je to
chybějící lokální vývojářský nástroj.
