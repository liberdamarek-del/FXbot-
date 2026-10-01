# Nejvyšší roční zhodnocení účtu – výsledek

> **Oprava (2026-10-01, později týž den):** na 16 nových párech, které model nikdy neviděl, CH-009
> nefunguje (2012–22 +0,2 % ročně, 2023–26 −3,1 %). Níže uvedených +24 % ročně platí jen pro 25 párů
> FXCM, na kterých se hledalo. Aktuální, poctivější čísla a samoučení: **`docs/UCENI.md`**.

Stav k 2026-10-01. Data: hodinové BID/ASK ceny FXCM 2012–2026, 25 párů, náklady (spread + skluz),
swap, složené úročení, nejvýš jedna pozice na pár, součet marží ≤ 100 % účtu. Velikosti a pravidla
vybrané jen na letech 2012–2022, roky **2023–2026 jsou test**. Podrobné tabulky:
`docs/DNY_A_POCET.md`, `docs/PORTFOLIO_STUPNE.md`, `docs/PORTFOLIO_SIROKE.md`, `docs/ROCNI_VYNOS.md`.

## 1. Proč se otevírá v pátek, a ne třeba ve středu

Stejné pravidlo (propad RSI(2) + rozcházející se sazby) jsem pustil pro každý den zvlášť:

| rozhodnutí | obchodů/rok | zisk na obchod 2012–18 / 2019–22 / 2023–26 | ročně při propadu ≤ 20 % |
|---|---|---|---|
| pondělí | 16 | −10,9 / +0,6 / +5,2 % | −0,2 % |
| úterý | 19 | −0,8 / +7,7 / +0,6 % | +2,3 % |
| středa | 17 | −6,1 / +14,0 / +7,2 % | +1,8 % |
| čtvrtek | 19 | +11,0 / −1,1 / +3,8 % | +2,3 % |
| **pátek** | 20 | **+10,8 / +11,5 / +10,3 %** | **+23,2 %** |
| každý den | 49 | +1,3 / +3,6 / +5,8 % | +3,3 % |

Výhoda je téměř celá v pátku: před víkendem obchodníci uzavírají riziko a cena „přestřelí“; část
návratu přijde už s nedělním otevřením. **Otevírá se v pátek, ale zavírá se kterýkoli den** – obchod
trvá v mediánu 4–5 dní (průměr 8) a 79 % cílů padne v pondělí až středu. Trendové strategie (průrazy, klouzavé
průměry) jsem zkoušel taky – po nákladech byly ve všech obdobích ztrátové.

## 2. 20 obchodů × 10 %, nebo 40 obchodů × 7 %?

Roční výnos ≈ **počet obchodů × zisk na obchod × podíl účtu vázaný na obchod**. Spočítáno na skutečných
obchodech (pravidlo F1 postupně uvolněné, aby obchodovalo víc):

| obchodů/rok | zisk na obchod | **stejná velikost** (marže 5 % účtu): ročně / propad | **stejné riziko** (propad ≤ 20 %): ročně |
|---|---|---|---|
| 20 | +10,9 % | +11,3 % / 10 % | **+23,2 %** (marže 10 %) |
| 30 | +9,1 % | +14,2 % / 17 % | +14,2 % |
| 39 | +7,9 % | +15,8 % / 24 % | +15,8 % (ale propad 24 %) |
| 76 | +5,5 % | +21,1 % / 32 % | +8,4 % |

* Při **stejné velikosti pozice** vydělá víc obchodů víc (40 × 7 % > 20 × 10 %).
* Ale propad roste rychleji než zisk (víc současně otevřených pozic, které padnou najednou). Při **stejném
  riziku** vyhrává 20 × 10 %, protože unese dvojnásobnou pozici.
* Rozhoduje tedy **zisk na jednotku rizika**. Nejlepší je obojí zkombinovat: nejsilnější obchody velkou
  pozicí, slabší malou – tím přibudou obchody (a ziskové měsíce) bez růstu propadu.

## 3. Řešení: odstupňované portfolio (vyzyvatel CH-009)

**Každý pátek při denním závěru** (23:00 Praha, funguje i hodinu předem) pro každý z 25 párů:

* RSI(2) < 5 → kandidát na **BUY**, RSI(2) > 95 → kandidát na **SELL**;
* velikost podle sazeb (změna rozdílu sazeb za 3 měsíce, známá se zpožděním 2 měsíců, ve směru obchodu):

| stupeň | podmínka sazeb | marže na obchod |
|---|---|---|
| silný | změna ≥ 0,25 p. b. (s carry i bez) | **8 % účtu** |
| střední | změna ≥ 0,10 p. b. | **3 % účtu** |
| slabý | změna ≥ 0 (jen správný směr) | **2 % účtu** |
| – | sazby proti obchodu | neobchodovat |

* TP = 0,75 × ATR(14), SL = 3 × ATR(14), nejdéle 20 obchodních dní; jen když TP ≥ 0,333 % ceny (každý
  ziskový obchod ≥ 10 % marže).
* Pojistka (samooprava): stupeň, jehož uzavřené obchody za posledních 24 měsíců skončily ve ztrátě, se
  vypne, a zapne se, až se vrátí do zisku. Historicky skoro nezasáhla (+23,0 % místo +23,7 % ročně).

| období | obchodů/rok | úspěšnost | ziskových obchodů za měsíc | měsíců s ≥ 2 ziskovými | **ročně** | max. propad |
|---|---|---|---|---|---|---|
| 2012–2022 (výběr) | 80 | 85 % | 5,6 | 89 % | **+23,5 %** | 19 % |
| **2023–2026 (test)** | 63 | 85 % | 4,3 | 80 % | **+24,2 %** | 16 % |
| celé 2012–2026 | 76 | 85 % | 5,3 | 87 % | **+23,7 %** | 19 % |

Rok po roku: 2013 +8 %, 2014 +23 %, 2015 +27 %, 2016 +60 %, 2017 −2 %, 2018 +8 %, 2019 +45 %, 2020 +35 %,
2021 +14 %, 2022 +30 %, 2023 +70 %, **2024 −10 %**, 2025 +18 %, 2026 (do září) +11 %.
Nejhorší měsíc −19 %.

**Odolnost** (stejné velikosti, ročně 2012–22 / 2023–26):

| změna | 2012–2022 | 2023–2026 |
|---|---|---|
| náklady 2× | +19,9 % | +22,8 % |
| rozhodnutí a vstup hodinu před pátečním závěrem | +22,8 % | +19,1 % |
| vstup až po víkendu | +18,6 % (propad 34 %) | +28,0 % |
| sazby centrálních bank místo OECD | +17,9 % | +31,0 % |
| sazby známé až o 3 měsíce později | +18,1 % | +19,4 % |

Náhodné přeházení měsíců (4 000 desetiletých drah): propad v polovině případů do 19 %, v 5 % případů
28 % a víc, v 1 % 32 % a víc; roční výnos v 90 % drah mezi +14 % a +34 %.

## 4. Co jsem zkoušel a zamítl

| pokus | v minulosti | v testu | proč zamítnuto |
|---|---|---|---|
| 56 statisticky nejlepších pravidel z 213 840 dohromady | +25 % ročně | +10 % ročně, propad 27 % | většina vybraných pravidel je šum, ředí výhodu |
| váhy pravidel „optimalizované“ na minulosti | nesmyslně vysoké | propady přes 100 % | čisté přeučení |
| vlastní TP/SL pro každý stupeň | +37 % ročně | +16 %, propad 25 % | přeučení – horší než jednoduchá verze |
| trend (průrazy, klouzavé průměry) | ztráta | ztráta | po nákladech nefunguje |
| jiné dny než pátek | +2 % ročně | – | výhoda je v pátku |

## 5. Rizika – čtěte prosím

* **Je to agresivní.** Marže 8 % účtu při páce 1:30 = pozice o objemu 2,4× účtu; najednou až 14 pozic
  a 78 % účtu vázaného v marži. Jeden ztrátový obchod silného stupně = průměrně −6,7 % účtu.
  Poloviční velikosti (4 / 1,5 / 1 %) dají +11,5 % ročně při propadu 10 % (test 2023–26: +11,8 %, propad 8 %).
* Výběr z mnoha pokusů výsledky nadsazuje – **realisticky čekám +10 až +20 % ročně** při propadech
  20–30 %, ne jistých +24 %. Byl i ztrátový rok (2024 −10 %).
* Víkendové mezery: pozice se drží přes víkend (je to v datech započítané, ale páteční spready u brokera
  bývají širší).
* Skutečný důkaz je až dopředný test. Pravidla i velikosti jsou od 2026-10-01 předem registrované jako
  **CH-009** (`docs/CHANGE_LOG.md`).

## 6. Jak se bude model dál zlepšovat

1. Každý pátek signály → zápis do neměnné evidence predikcí → automatické vyhodnocení (dopředný test).
2. Každý měsíc přepočet výsledků stupňů na klouzavých datech; pojistka vypíná stupně, které přestanou
   vydělávat.
3. Každý nový nápad (jiný signál, filtr, výstup) se nejdřív zaregistruje, otestuje postupně (výběr na
   minulosti → test na novějších datech) a do portfolia se přidá, jen když **zvýší roční výnos při
   stejném propadu i v testu**. Tímhle sítem už neprošly: širší portfolio, trend, ladění výstupů.
4. Další krok implementace: příkaz v botu, který v pátek spočítá signály pro 25 párů (data Dukascopy
   na telefonu, sazby OECD jednou měsíčně), vypíše vstup, TP, SL a velikost pozice a zapíše je do evidence.

Výpočty: `python scripts/weekday_tradeoff.py`, `python scripts/portfolio_tiers.py`,
`python scripts/portfolio_sim.py`, `python scripts/annual_lab.py` (potřebují `profit_lab2.py build`).
