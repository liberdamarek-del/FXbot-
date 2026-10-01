# Zisk ≥ 10 % marže na obchod – výsledek hledání

Stav k 2026-10-01. Podrobné tabulky: `docs/ZISK10.md` (kolo 1), `docs/ZISK10_K2.md` (kolo 2),
`docs/ZISK10_OVERENI.md` (ověření finalistů obchod po obchodu).

## 1. Zadání a jak jsem ho počítal

* Páka 1:30 → **10 % marže = pohyb ceny 0,333 %** (marže = 1/30 objemu pozice).
* Každý obchod má cíl (TP) aspoň 10 % marže; po spreadu, skluzu a swapu musí být
  **průměrný zisk na obchod ≥ 10 % marže**, systém ziskový a úspěšnost co nejvyšší (dříve ≥ 75 %).
* Obchody nemusí být denně – rozhoduje se **jen jednou týdně (v pátek při závěru)**.

## 2. Data a postup

| | |
|---|---|
| trh | **25 měnových párů** = všechny kříže 8 hlavních měn, které FXCM zveřejňuje (chybí jen CHF/JPY, EUR/CAD, GBP/AUD) |
| ceny | hodinové BID/ASK svíčky FXCM **2012-01 až 2026-09**, jeden zdroj, 2,2 mil. hodin (`scripts/fxcm_universe.py`); vadné řádky (např. CAD/CHF a NZD/CHF 2012–14 mají ASK pod BID) = díry, nic se nedoplňuje odhadem |
| cesta obchodu | po hodinách; když TP i SL padnou ve stejné hodině, počítá se SL |
| náklady | běžný retailový spread (např. EUR/USD 0,8 pipu, GBP/NZD 4,5 pipu) + 0,4 pipu skluz; swap = rozdíl sazeb −/+ 1 % p.a. za každý den |
| sazby | OECD 3měsíční mezibankovní sazby (FRED), měsíční průměry, **použité až se zpožděním 2 měsíců** (tak, jak jsou v daný den opravdu známé) |
| hledání | **213 840 systémů** (signál × trend × fundamentální filtr × rytmus × vstup × výstup) – `scripts/profit_lab2.py` |
| výběr | jen na **2012–2018 (A)** a **2019–2022 (B)**, obě období musí splnit podmínky |
| test | **2023–2026** se při výběru nepoužil |

## 3. Nalezené pravidlo F1 („propad + rozcházející se sazby“)

**Každý pátek při denním závěru (17:00 New York = 23:00 Praha)** pro každý z 25 párů:

* **BUY**, když RSI(2) z denních závěrů < 5 **a** rozdíl sazeb (základní měna − kótovaná) se za 3 měsíce
  zvětšil aspoň o 0,25 p. b. (hodnota známá před 2 měsíci proti hodnotě před 5 měsíci);
* **SELL** zrcadlově: RSI(2) > 95 a rozdíl sazeb se zmenšil aspoň o 0,25 p. b.;
* vstup tržně při závěru (funguje i hodinu před závěrem), **TP = 0,75 × ATR(14)**, **SL = 3 × ATR(14)**,
  nejdéle 4 týdny (20 obchodních dní), pak zavřít;
* obchoduje se jen tehdy, když TP ≥ 0,333 % ceny (= 10 % marže), na jednom páru nejvýš jedna pozice.

Myšlenka: kupuje se krátký výprodej měny, jejíž centrální banka už několik měsíců zvyšuje sazby rychleji
než ta druhá (prodej zrcadlově).

| období | obchodů | úspěšnost | **zisk na obchod (% marže)** | t |
|---|---|---|---|---|
| 2012–2018 (výběr) | 79 | 90 % | **+10,8 %** | 2,9 |
| 2019–2022 (výběr) | 107 | 88 % | **+11,5 %** | 3,9 |
| **2023–2026 (test)** | 81 | 89 % | **+10,3 %** | 3,1 |
| celkem | 267 (≈ 20 za rok) | **89 %** | **+10,9 %** | 5,7 |

* Každý obchod míří na zisk aspoň 10 % marže; ziskový obchod přinese průměrně **+21 % marže**, ztrátový
  průměrně **−67 % marže**.
* Ziskové v 10 ze 14 let (ztrátové roky 2017, 2018, 2021, 2024 měly jen 1–11 obchodů); ziskové ve 20 z 25 párů;
  BUY +11,1 %, SELL +10,7 %. Nejvýš 2 ztráty po sobě.
* t = t-statistika se shlukováním po týdnech (obchody ze stejného týdne se nepočítají jako nezávislé).

### Kontroly – odkud zisk pochází

| varianta | 2012–18 | 2019–22 | 2023–26 |
|---|---|---|---|
| F1 | +10,8 % | +11,5 % | +10,3 % |
| stejný propad **bez** podmínky sazeb | +3,2 % | +1,1 % | +4,4 % |
| **jen** sazby, bez propadu (každý pátek) | −2,6 % | −2,3 % | +0,1 % |

Ani propad, ani sazby samy nestačí – zisk dělá teprve jejich kombinace.

### Odolnost (změny, které by neměly výsledek zničit)

| varianta | 2012–18 | 2019–22 | 2023–26 |
|---|---|---|---|
| rozhodnutí a vstup **1 h před závěrem** | +10,2 % | +14,9 % | +11,0 % |
| vstup až po víkendu (nedělní otevření) | +4,8 % | +10,5 % | +10,9 % |
| **náklady 2×** | +8,7 % | +10,8 % | +10,3 % |
| sazby známé až o 3 měsíce zpět | +10,0 % | +9,1 % | +9,4 % |
| změna sazeb za 6 měsíců místo 3 | +9,0 % | +8,3 % | +8,4 % |
| sazby centrálních bank (o 2 měsíce zpět) místo OECD | +7,0 % | +8,6 % | +11,3 % |
| i překrývající se obchody na stejném páru | +11,0 % | +11,8 % | +10,6 % |

**Co nefunguje:** s *aktuálními* denními výnosy 2letých dluhopisů místo opožděných sazeb výhoda mizí
(−0,2 / +5,1 / +1,0 %). Pravidlo tedy zachycuje **už probíhající rozcházení měnových politik**, ne očekávání
trhu – a je citlivé na to, jak se sazby měří. Proto ho beru jako silného kandidáta, ne jako jistotu.

## 4. Vyšší zisk na obchod (méně obchodů)

| profil | obchodů za rok | úspěšnost | zisk na obchod 2012–18 / 2019–22 / **2023–26** |
|---|---|---|---|
| **F1** základ | ≈ 20 | 89 % | +10,8 / +11,5 / **+10,3 %** |
| F6 = F1, jen když cíl ≥ 15 % marže (ATR ≥ 0,67 % ceny) | ≈ 16 | 89 % | +12,3 / +12,0 / **+12,4 %** |
| F5 = F1 + kladný carry ve směru obchodu | ≈ 10 | 90 % | +15,6 / +11,8 / **+13,4 %** |
| **F7** = F5, jen když cíl ≥ 15 % marže | ≈ 8 | 91 % | +18,2 / +12,7 / **+18,6 %** |

F5–F7 jsou zpřesnění F1, která jsem zkoušel až po pohledu na test, a F7 má třetinu obchodů z roku 2022 –
hlavním kandidátem proto zůstává F1.

## 5. Riziko a velikost pozice

* Je to systém „často malý zisk, občas velká ztráta“: 1 ztráta ≈ 3 zisky. Stop 3 ATR je průměrně
  **84 % marže**, po šocích i víc – nejhorší obchod **−174 % marže** (GBP/NZD, nákup v den výsledku
  referenda o brexitu 24. 6. 2016).
* Celé portfolio (25 párů, nejvýš 9 pozic současně), každý obchod váže X % účtu jako marži:

| marže na obchod | ročně (2013–2026) | největší propad účtu |
|---|---|---|
| 5 % účtu | +11 % | 10 % |
| 10 % účtu | +23 % | 19 % |
| 20 % účtu | +48 % | 36 % |

  Doporučení: **nejvýš 5–10 % účtu jako marže na jeden obchod** (při 10 % a 9 otevřených pozicích je
  vázáno 90 % účtu).

## 6. Jak moc tomu věřit

* Hledalo se ve 213 840 systémech. Systémy, které měly ≥ 10 % v obou výběrových obdobích, měly v testu
  2023–26 v průměru jen **+4 až +5 %** (všechny systémy +1,5 %) – výběr z mnoha pokusů výsledky nadsazuje. F1 v testu drží +10,3 %, ale **realisticky čekám +5 až +10 % marže na obchod**.
* Data FXCM chybí pro 2026-05 až 2026-08 a několik dalších týdnů (FXCM je nezveřejnilo) – obchody přes díru
  se nepočítají.
* Skutečný důkaz je až **dopředný test**: pravidlo F1 je od 2026-10-01 předem registrované jako vyzyvatel
  **CH-008** (`docs/CHANGE_LOG.md`), varianty F5/F7 se vyhodnocují vedle něj. Nic se neobchoduje skutečnými
  penězi, dokud dopředný test nepotvrdí výsledek.

## 7. Další krok

Zapojit F1 do bota: v pátek z hodinových dat 25 párů (Dukascopy na telefonu, FXCM jako záloha) a měsíčních
sazeb OECD spočítat signály, vypsat vstup/TP/SL a zamknout je do evidence predikcí; každý týden
vyhodnotit (`fxbot.py review`). Výpočty: `python scripts/profit_lab2.py build && python scripts/profit_lab2.py report`,
`python scripts/profit_deep.py`.
