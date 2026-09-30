# Testování, které musíme udělat spolu

Backtest na historii je jen pokus nad minulostí. Rozhodující jsou dvě věci, které
bez vašeho telefonu, klíče a času nejdou: **běh na vašem zařízení** a **dopředný
test** – predikce zamčené dopředu a vyhodnocené na cenách, které v době predikce
ještě neexistovaly.

Nic z toho neposílá obchody. Bot jen analyzuje, zamyká predikce a vyhodnocuje je.

---

## Fáze 1 – instalace a první běh (den 1, ~1 hodina)

```sh
python scripts/backup_db.py          # záloha stávající databáze
tar -xzf FXBOT_V78.tar.gz            # kód
tar -xzf FXBOT_V78_DATA.tar.gz       # historie bid/ask a fundamenty (ušetří dny stahování)
pip install -r requirements.txt
python fxbot.py test                 # musí skončit RESULT: PASS
python fxbot.py setkey               # klíč Twelve Data
python fxbot.py run                  # první živý běh
```

Pošlete mi:

1. poslední řádky `python fxbot.py test` (TESTS / FAILURES / RESULT),
2. celý výstup prvního `python fxbot.py run` (nebo soubor `data/runs/<RUN-ID>/report_cz.txt`),
3. jak dlouho běh trval (poslední řádek `beh trval … s`).

Co v tom hledám: ceny `FRESH`, `RUN COMPLETE`, certifikát bez `CRITICAL`,
stav kreditů Twelve Data, doba běhu na telefonu.

## Fáze 2 – stahování z vaší sítě (den 1–3, běží samo)

```sh
termux-wake-lock
python fxbot.py history --days 30            # minutová bid/ask data za posledních 30 dní
python fxbot.py history --status             # co je v archivu
```

Pošlete mi: řádek s rychlostí stahování (kolik dní/souborů za minutu) a jestli
se objevuje `server neodpovida`. Zde v cloudu server Dukascopy silně omezoval
(1–2 soubory/min, časté pauzy). Pokud je z vaší sítě rychlejší, stáhneme
minutová data pro celou historii – ta zpřesní backtest (viz „pořadí neznámo“
v `docs/BACKTEST_REPORT.md`).

## Fáze 3 – dopředný test (4 týdny, běží samo)

```sh
sh scripts/termux_schedule.sh        # běh každou hodinu v :07 (po–pá), fundamenty denně
```

Každý běh nejdřív vyhodnotí dřívější predikce na nových cenách a teprve potom
zamkne nové (modul 145). Nic se neupravuje zpětně.

Každý pátek večer:

```sh
python fxbot.py review --weekly
```

Po 4 týdnech:

```sh
python fxbot.py review --all
python fxbot.py backtest --walkforward
```

Pošlete mi výstupy. Klíčové řádky:

| Řádek | Co znamená |
|---|---|
| `KONTROLA SMERU ... edge ... VYZNAMNE KLADNY / NEVYZNAMNY / VYZNAMNE ZAPORNY` | Jestli směr modelu přidává něco proti náhodnému směru se stejnou geometrií obchodu. To je hlavní otázka. |
| `PORADI NEZNAMO ... meze E` | Kolik výsledků nešlo rozhodnout bez minutových dat (nehádá se). |
| `KALIBRACE` | Jestli třída důvěry A je opravdu lepší než B a C. |
| `KANDIDATI ZMEN` | Opakované chyby – návrhy změn. Nic se nemění samo. |

### Kdy je výsledek použitelný

* **méně než ~100 vyhodnocených rozhodnutí**: jen popis, žádný závěr (12 párů × 4 týdny
  obvykle dá 30–80 predikcí se směrem – proto spíš 6–8 týdnů),
* **edge `VYZNAMNE KLADNY` v dopředném testu i v backtestu**: model má smysl zkoušet
  dál (stále bez skutečných peněz),
* **`NEVYZNAMNY`**: model je zatím k nerozeznání od náhody – upravíme hypotézu
  přes changelog (`docs/CHANGE_LOG.md`) a test opakujeme,
* **`VYZNAMNE ZAPORNY`**: v modelu je systematická chyba – hledáme ji v taxonomii chyb.

Pravidlo projektu: žádná změna modelu se nepovýší automaticky. Změna projde
changelogem, backtestem na datech, která při návrhu nebyla použita, a dopředným
testem.

## Fáze 4 – broker (až po fázi 3)

1. Založte **OANDA practice** účet (zdarma, jen demo) a vytvořte API token.
2. Do `.env`: `FXBOT_BROKER=oanda`, `OANDA_TOKEN=…`, `OANDA_ACCOUNT_ID=…`, `OANDA_ENV=practice`.
3. `python fxbot.py run` – certifikát má místo `BROKER-BLOCKED` ukázat ověřené kotace.
4. Pošlete mi výstup; adaptér je napsaný podle dokumentace a nebyl nikdy spuštěn proti
   skutečnému účtu.

Pro XTB: jejich staré API bylo 14. 3. 2025 vypnuto. Pokud máte jiného brokera s API,
pošlete mi odkaz na jeho dokumentaci – nový adaptér je jeden soubor v `src/broker/`.

## Fáze 5 – spready vašeho brokera

Model počítá náklady jako spread z dat Dukascopy + **0,5 pip přirážka** + 0,2 pip
skluz na každou stranu (`broker_markup_pips`, `slippage_pips` v `src/engine/params.py`).
Pošlete mi několik snímků typického spreadu u vašeho brokera (EUR/USD, USD/JPY, GBP/JPY
v Londýně a v Asii). Změna nákladů je změna modelu – projde changelogem.
