# FXBOT – implementace FX MASTER MODEL V7.8.0

FXBOT dělá **technickou i fundamentální analýzu 12 měnových párů nad reálnými daty**
a řídí se pravidly z Wordu `docs/FX_MASTER_MODEL_V7.8.0.docx` (moduly 0–145).
Výstupem každého běhu je český report: ověřené ceny, stav dat, audit dřívějších
predikcí, Top‑3 návrhy (KOUPIT/PRODAT TEĎ, ČEKAT NA NÁKUP/PRODEJ, NEOBCHODOVAT)
s hypotézami a protiargumenty, a certifikát běhu.

> **Nejde o investiční doporučení.** Model je CHALLENGER bez statistického důkazu
> výkonnosti. Obchodování přes skutečného brokera je podle pravidel projektu
> mimo rozsah – bot analyzuje, zamyká predikce a vyhodnocuje je.

---

## 1. Instalace

### Termux (Android)

```sh
pkg install python
cd ~/fxbot                       # složka projektu (u vás je to zároveň venv)
python scripts/backup_db.py      # záloha stávající databáze (pokud existuje)
tar -xzf FXBOT_V78.tar.gz        # rozbalí kód; data/ a .env zůstanou beze změny
pip install -r requirements.txt  # jen requests + python-dotenv (žádné další knihovny)
python fxbot.py test             # izolované testy – nikdy nesahají na vaše data
```

Volitelně rozbalte i `FXBOT_V78_DATA.tar.gz` (stažená historie bid/ask a fundamentů),
ať ji telefon nemusí stahovat znovu.

### PC (Linux / Windows / macOS)

Python ≥ 3.10, pak stejné příkazy (`pip install -r requirements.txt`).

## 2. První spuštění

```sh
python fxbot.py setkey                        # uloží a otestuje váš klíč Twelve Data
python fxbot.py fundamentals --years 12       # sazby, výnosy, riziko, pozicování (~2 min)
python fxbot.py history --hourly-years 3 --days 60   # historie bid/ask (Dukascopy)
python fxbot.py run                           # první běh V7.8.0
```

Stahování historie může trvat dlouho (server Dukascopy omezuje frekvenci);
dá se kdykoli přerušit a spustit znovu – pokračuje tam, kde skončil.
Na telefonu před dlouhým stahováním: `termux-wake-lock`.

Když Dukascopy nejde stáhnout, použije analýza jako náhradu minutovou historii
z Twelve Data (jen střední ceny, bez bid/ask): `python scripts/update_data.py --days 100`
(denní indikátory potřebují aspoň ~60 obchodních dní; stojí asi 32 kreditů na pár,
volný plán má 800 kreditů denně – pro 12 párů to zvládne za jeden den).

## 3. Denní použití

```sh
python fxbot.py run            # stáhne jen chybějící data, vyhodnotí staré predikce, analyzuje
python fxbot.py run --no-lock  # jen analýza, nic se nezamyká do evidence
python fxbot.py run --offline  # bez stahování (jen uložená data)
python fxbot.py report         # znovu vypíše poslední report
python fxbot.py status         # stav dat, archivu, evidence, registru modelu a zdrojů
python fxbot.py review --weekly  # týdenní revize zamčených predikcí vč. kontroly směru proti náhodě
python fxbot.py resolve        # jen vyhodnotí otevřené predikce
python fxbot.py paper          # papírový účet spočtený z evidence predikcí
```

Automaticky každou hodinu (dopředné testování na telefonu):

```sh
pkg install cronie termux-services      # jednou; pak Termux restartovat
sh scripts/termux_schedule.sh           # běh každou hodinu v :07 (po–pá) + fundamenty denně
sh scripts/termux_schedule.sh --remove  # zrušit
```

S aplikací Termux:API (`pkg install termux-api`) přijde upozornění, když model zamkne novou predikci
(`python fxbot.py run --notify`). Výstupy plánovaných běhů: `data/cron_run.log`, `python fxbot.py report`.

Co znamenají části reportu:

| Sekce | Význam (modul) |
|---|---|
| KRITICKÉ BLOKACE | co brání rozhodnutí NOW – nikdy se neschovává (7, 84) |
| CENY | pár, bid/ask/mid, zdroj, čas zdroje, stáří, stav LIVE/FRESH/CONDITIONAL/REJECTED, zda je cena exekuční (135) |
| DATA A CESTA | pokrytí cenové cesty od minulého oficiálního běhu, mezery a jejich závažnost (123) |
| AUDIT SPLATNÝCH PREDIKCÍ | výsledky dřívějších predikcí na minutové cestě, bid/ask správně (61, 62, 81) |
| MEZIBĚHOVÁ DELTA | co se stalo s cenou mezi běhy, překřížení zamčených úrovní, události (92, 106) |
| TOP‑3 | návrhy s hypotézami H1/H2/H3, důkazy PRO/PROTI, invalidací, branami a stavem teze (37, 45–58, 141) |
| CO MODEL PŘEHLÉDL? | kontrolní seznam selhání (85) |
| CERTIFIKÁTY | RUN COMPLETION + DATA PIPELINE (113, 128) |

Bez živého zdroje s bid/ask je každá cena **modelová** (`model-cena`) a certifikát hlásí
`BROKER-BLOCKED`. Před vstupem vždy ověřte kotaci u svého brokera.

## 4. Jak model rozhoduje (zkráceně)

1. **Data**: jen uzavřené svíčky, jen hodnoty, které byly v daném čase veřejně známé.
   Chybějící data se nikdy nedopočítávají (GAP / NEOVĚŘENO).
2. **Směr** (≠ vstup, modul 45): struktura D1 + H4 (EMA20/50, sklon, momentum)
   musí souhlasit a fundamenty jí nesmí odporovat.
3. **Fundamenty** po nezávislých klastrech (modul 36): přecenění sazeb (změna 2letého
   diferenciálu), carry vůči volatilitě, pozicování CFTC (přeplněnost = protisíla),
   rizikový režim × *změřená* citlivost páru na akcie, ropa u CAD, riziko intervence u JPY,
   ekonomický kalendář.
4. **Třída důkazu** A/B/C (není to pravděpodobnost): C nikdy nedostane NOW.
5. **Vstup**: pullback k aktivní úrovni, retest proražené úrovně nebo pokračování u EMA20 H1;
   SL za úrovní, TP1 před protilehlou úrovní, **R:R ≥ 1,5 po nákladech** (spread + přirážka
   brokera + skluz).
6. **Brány NOW**: poloha u úrovně, no‑chase, šok, událost s vysokým dopadem, spread,
   ověřená živá cena, režim. Jakékoli selhání = jen ČEKAT.
7. **Top‑3** s faktorovou koncentrací (EUR/USD long + GBP/USD long = jedna sázka proti USD).
8. **Teze se neotáčí okamžitě** (modul 139): otevřená teze BUY nemůže přejít v SELL bez
   invalidace.
9. Každá predikce se **zamkne** (nelze ji změnit ani smazat) a později se vyhodnotí.

Všechny prahy jsou na jednom místě: `src/engine/params.py` (provizorní, NEOVĚŘENO).

## 5. Backtest a „trénování“

```sh
python fxbot.py backtest                       # celý model na uložené historii bid/ask
python fxbot.py backtest --from 2025-01-01 --to 2026-09-01 --symbols EUR/USD,USD/JPY
python fxbot.py backtest --ablation            # co přidává která vrstva (75)
python fxbot.py backtest --robustness          # citlivost na parametry (76)
python fxbot.py backtest --walkforward         # parametry vybrané jen z minulosti, test na budoucnosti (77)
```

Backtest používá **stejný kód** jako živý běh a je porovnán s **placebem** (stejná
rozhodnutí a geometrie obchodu, náhodný směr). Jen rozdíl proti placebu říká, jestli
směr modelu něco přidává.

„Učení“ je řízené (moduly 78–80, 126, 144):

* každá sada parametrů je v registru (`CHAMPION` / `CHALLENGER` / `CANDIDATE` …),
* změna se nejdřív zapíše do changelogu s kořenovou příčinou, testy a plánem návratu,
* povýšení nastane jen s dostatečným **out‑of‑sample** důkazem (≥ 100 obchodů,
  statisticky významně lepší, horší drawdown ne) – **nikdy automaticky**,
* report navrhuje „kandidáty změn“ z chyb (taxonomie modulu 69), ale nic sám nemění.

## 6. Připojení brokera

Rozhraní je v `src/broker/base.py`. Adaptér vrací kotace **bid/ask s časem brokera**;
tím se cena stane exekuční (`EXEKUCNI`) a certifikát přestane hlásit BROKER-BLOCKED.

* **OANDA** (`src/broker/oanda.py`): v `.env` nastavte
  `FXBOT_BROKER=oanda`, `OANDA_TOKEN=…`, `OANDA_ACCOUNT_ID=…`, `OANDA_ENV=practice`.
  Jen čtení (kotace, zůstatek). *Napsáno podle dokumentace, netestováno – otestujeme spolu.*
* **XTB**: staré xAPI bylo vypnuto 14. 3. 2025, veřejná náhrada není známa → `src/broker/xtb.py`
  je připravené místo.
* Nový broker: zkopírujte `oanda.py`, implementujte `quotes()` a `account()`,
  zaregistrujte v `src/broker/__init__.py`. Nic dalšího se měnit nemusí.

## 7. Zdroje dat (všechny bez placení)

| Zdroj | Co dává | Použití |
|---|---|---|
| Twelve Data (váš klíč) | 1min OHLC mid, živě | živá cena NOW (modelová), čelo cesty |
| Dukascopy | 1min a 1h **BID+ASK** historie, hodinové ticky | kanonická historie, vyhodnocení bid/ask, spread |
| FXCM (veřejné týdenní soubory) | 1min **BID+ASK** po týdnech, zpoždění ~1 týden | druhý zdroj cesty: vyhodnocení tam, kde Dukascopy den chybí; nikdy ne pro analýzu |
| BIS | sazby 8 centrálních bank | carry, trend politiky |
| FRED, ECB, MoF, BoE, BoC, RBA | 2/5/10leté výnosy, VIX, S&P 500, HY spread, ropa | přecenění sazeb, riziko, komodity |
| CFTC | pozicování (Traders in Financial Futures) | přeplněnost |
| ForexFactory feed | týdenní kalendář | event gate |

Každá stažená odpověď se ukládá i s hashem SHA‑256 (reprodukovatelnost, modul 124).
Neověřené zdroje z registru ve Wordu (webové tickery apod.) se **nescrapují** (modul 130
vědomě neimplementován) – stav všech zdrojů ukáže `python fxbot.py status`.

## 8. Co je a není implementováno

`python fxbot.py verify-model --list` vypíše všech 146 modulů se stavem:
**110 IMPLEMENTED, 27 PARTIAL, 7 NOT_AVAILABLE, 2 SUPERSEDED** (tabulka: `docs/MODULY.md`).
Nedostupné (není bezplatný strojově čitelný zdroj): opce (26), toky/fixingy (27),
fiskál/cla (28), Čína (29), geopolitika (32), webové tickery (130), renderované
widgety (131). Tyto moduly mají v každém běhu stav N/A s důvodem – nic se tiše nepřeskakuje.

## 9. Struktura

```
fxbot.py                 jediný vstupní bod
src/v78/                 procedura běhu V7.8.0, manifest, kotace, pokrytí, audit, certifikáty
src/engine/              technika, fundamenty, režim, rozhodnutí, Top-3, teze, backtest
src/fundamental/         úložiště point-in-time, katalog řad, adaptéry, kalendář
src/sources/             Dukascopy, HTTP klient
src/stats/               statistiky, taxonomie chyb, validace, registr modelu
src/broker/              rozhraní brokera, papírový účet, OANDA, XTB
src/path_archive.py      archiv cenové cesty (data/market_path.sqlite3)
src/prediction_ledger.py neměnná evidence predikcí (data/fxbot.sqlite3)
docs/                    Word se specifikací
test_*.py                testy (python fxbot.py test)
```

Data: `data/fxbot.sqlite3` (evidence, běhy, Twelve Data), `data/market_path.sqlite3`
(historie bid/ask), `data/fundamentals.sqlite3`, `data/runs/<RUN-ID>/` (artefakty každého běhu).

## 10. Co musíme otestovat spolu

Podrobný postup krok za krokem (co spustit, kdy a co mi poslat): **`docs/TESTOVANI_SPOLU.md`**.
Tohle nejde ověřit bez vašeho zařízení a účtů:

1. **Živý běh s vaším klíčem Twelve Data** – ceny FRESH, zamknutí predikcí, výdrž limitu kreditů.
2. **Výkon na telefonu** – doba běhu `fxbot.py run` a `backtest` v Termuxu.
3. **Stahování z Dukascopy z vaší sítě** – zda je rychlejší než zde (zde silné omezení).
4. **Dopředné testování 2–4 týdny** – teprve zamčené predikce vyhodnocené na budoucích
   datech jsou skutečný důkaz (backtest je jen historický pokus).
5. **Broker** – pokud chcete exekuční ceny: OANDA practice účet (zdarma) nebo jiný
   broker s API; XTB zatím nemá veřejné API.
6. **Rozdíl spreadů** – přirážka `broker_markup_pips` (0,5 pip) je odhad pro retail
   brokera; porovnáme se skutečnými spready vašeho brokera.

## 11. Řešení problémů

| Problém | Řešení |
|---|---|
| `ModuleNotFoundError: lzma` (Termux) | `pkg install xz-utils` a znovu `pkg install python` |
| `server neodpovida ... pauza` při stahování | server Dukascopy omezuje frekvenci; nechte běžet, pokračuje sám |
| `server limit pozadavku` (HTTP 429) | Dukascopy vás dočasně blokuje (pauzy se samy prodlužují až na 30 min). Minutová data pro vyhodnocení lze vzít z FXCM: `python fxbot.py history --source fxcm --days 60` |
| `LIVE CENA NEOVERENA` u všech párů | chybí klíč Twelve Data (`python fxbot.py setkey`) nebo je trh zavřený |
| `KEY-REQUIRED` u TWELVE_DATA | klíč není v `.env` |
| běh je pomalý | `python fxbot.py run --symbols EUR/USD,USD/JPY` (méně párů) |
| chci začít znovu s historií | smažte `data/market_path.sqlite3` (evidence predikcí v `data/fxbot.sqlite3` zůstane) |
| test selže | `python fxbot.py test` vypíše, který; testy nikdy nesahají na `data/` |
