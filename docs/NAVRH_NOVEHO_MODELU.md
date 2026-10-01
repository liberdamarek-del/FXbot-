# Návrh: FX MODEL 2.0 místo 146 modulů

Stav k 2026-10-01. Vychází z implementace všech 146 modulů V7.8.0 a z testů na datech
2013–2026 (docs/OOS_REPORT.md, STRATEGIE.md, ADAPTIVNI.md).

## 1. Co je na V7.8.0 špatně

| Problém | Příklad | Důsledek |
|---|---|---|
| **Předpovídání je jen malá část** | ze 146 modulů rozhoduje o směru a vstupu asi 15 (42–46, 50–59); zbytek je evidence, certifikáty, kontrola zdrojů, procedury běhu | text roste, výsledek se nezlepšuje |
| **Pevný postup analytika místo učení** | pravidla „trend D1/H4 + fundamentální veto + pullback“ jsou napsaná jednou provždy | když trh změní chování, model to nepozná; test: 2016–2023 žádná výhoda |
| **Vrstvení verzí** | tři finální procedury (83, 128, 145), dvě verze čerstvosti dat (10/119), konfliktů zdrojů (13/120), pokrytí cesty (88/123), release brány (115, 127) | rozpory, duplicitní kontroly |
| **Moduly bez dat** | opce (26), toky (27), fiskál (28), Čína (29), geopolitika (32), web tickery (130, 131) | 7 modulů trvale „N/A“ |
| **Neověřitelné úvahy** | kauzální řetězce (34), druhý řád (35), očekávání trhu (19), kauzální uvažování (6) | stroj je umí jen popsat, ne změřit; v testu nic nepřidaly |
| **Váhy bez dat** | třídy důvěry A/B/C podle počtu souhlasných skupin | kalibrace selhala (A není lepší než C) |

Dobré a ponechané: zákaz zpětného pohledu (4), neměnná evidence predikcí (60), vyhodnocení
na bid/ask s náklady (12, 62–64), kontrola proti náhodě (74), změny jen přes changelog (80).

## 2. Nová struktura: 12 modulů v 5 vrstvách

| Vrstva | Modul 2.0 | Obsah | Nahrazuje V7.8.0 | V kódu už je |
|---|---|---|---|---|
| **A. Data** | A1 Ceny | bid/ask historie a živá data, zdroje a záložní zdroje, mezery, hash | 8–15, 86–94, 108–111, 116–124, 129, 132–137 | `src/path_archive.py`, `src/sources/` |
| | A2 Fundamenty | sazby, výnosy, pozicování, riziko, komodity, kalendář – vždy k datu zveřejnění | 15, 18, 20–25, 30, 31, 33, 47 | `src/fundamental/` |
| | A3 Brána kvality | data musí být čerstvá, úplná, konzistentní – jinak se neobchoduje | 5, 10, 16, 119, 125, 133, 134 | `src/v78/quotes.py`, `coverage.py` |
| **B. Signály** | B1 Knihovna indikátorů | stovky parametrizovaných technických pravidel (D1, W1, H4) | 42–44, 46, 49 | `scripts/strategy_mining.py` |
| | B2 Fundamentální rysy | carry, změna sazeb, COT, riziko, politika CB jako čísla a filtry | 17, 21–25, 31, 36, 39 | `scripts/research_signals.py` |
| **C. Učení** | C1 Hodnocení pravidel | každé pravidlo = obchody po nákladech a swapu, proti náhodě | 61–65, 74, 142 | `src/engine/backtest.py`, `scripts/*_lab.py` |
| | C2 Adaptivní výběr | pravidelné přeučení (co měsíc), klouzavé okno, vyřazení pravidel, která přestala fungovat | 40, 41, 73, 77, 79 | `scripts/adaptive_today.py` |
| | C3 Ověření a povýšení | výběr jen z minulosti, test na nevidaných datech, ochrana proti mnoha testům, champion/challenger | 70–72, 75–78, 95–98, 126, 143, 144 | `src/stats/` |
| **D. Obchod** | D1 Vstup, výstup, riziko | velikost pozice podle volatility, SL/TP, max. expozice, stop při intervenci/události | 48, 51–58, 64 | `src/engine/decision.py`, `portfolio.py` |
| | D2 Výstup pro uživatele | dnešní signály, vstupní ceny, česká zpráva | 7, 84, 135, 141 | `src/v78/report.py`, `signals_today.py` |
| **E. Záznam** | E1 Evidence a dopředný test | zamčení predikce, automatické vyhodnocení, revize, deník uživatele | 4, 60–62, 66–69, 81, 82, 138–140 | `src/prediction_ledger.py`, `review.py`, `journal` |
| | E2 Provoz | plánování, opakovatelnost běhu, broker | 2, 99–107, 112–114, 145 | `fxbot.py`, `src/broker/` |

**Vypustit:** 83, 128 (staré procedury běhu), 115, 127 (release brány starých verzí), 6, 19, 34, 35
(neměřitelné úvahy – nechat jen jako text ve zprávě), 26–29, 32, 130, 131 (bez dat – vrátit, až bude
zdroj), 1, 3, 50 (nahrazuje je C1–C3: rozhoduje měření, ne pořadí argumentů).

## 3. Zásady 2.0 (místo 146 modulů jedna stránka)

1. **O tom, co platí, rozhoduje trh, ne text.** Pravidla jsou data (indikátor, nastavení, filtr, držení),
   ne próza.
2. **Vše se měří proti náhodě a po nákladech.** Výsledek bez srovnání s náhodným směrem se nepočítá.
3. **Model se učí pořád.** Každý měsíc přeučení na posledních 2–3 letech; pravidlo, které přestane
   fungovat, samo vypadne.
4. **Výběr jen z minulosti.** Rozhodnutí v čase T smí znát jen data před T – v backtestu i živě.
5. **Povýšení jen s důkazem dopředu.** Vyzyvatel (challenger) běží vedle championa; povýší se až po
   ~100 dopředných obchodech s průkazně lepším výsledkem.
6. **Člověk je zdroj dat.** Ruční obchody v deníku se vyhodnocují stejně jako modelové.

## 4. Stav a další krok

* Vrstvy A, C1, C3, E jsou hotové a otestované; B a C2 existují jako výzkumné nástroje a běží denně
  jako vyzyvatel CH-006 (`python fxbot.py adaptive --lock`, automaticky v Termuxu).
* V7.8.0 zůstává jako champion a reference; jeho rozhodovací logika se v 2.0 stane jednou „rodinou
  pravidel“ v knihovně B1 – bude soutěžit se stovkami dalších.
* Přechod na 2.0 jako hlavní model: až dopředný test CH-006 (nebo jiného vyzyvatele) průkazně porazí
  V7.8.0 i náhodu. Do té doby se nic neobchoduje skutečnými penězi.
