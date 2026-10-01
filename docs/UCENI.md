# Jak se model sám učí – a co se zatím naučil

> **Od 2026-10-01 (rozhodnutí uživatele) se učí jen na 12 párech, které bot sleduje živě.** Aktuální
> šampion a jeho pravidla: **`docs/SAMPION_12.md`** (test 2023–26: +28,6 % ročně, propad 20 %,
> 2,2 ziskového obchodu měsíčně). Kontrola „funguje i jinde“: zvlášť na 7 párech s USD a na 5 křížích.
> Části níže o 41 párech jsou záznam předchozího kroku.

Stav k 2026-10-01. Deník všech pokusů: `docs/UCENI_LOG.md`. Kód: `scripts/self_learn.py`.

## 1. Proč 10 % na obchod ≠ 10 % na účet

Zisk 10 % se počítá z **marže obchodu**, ne z celého účtu. Příklad – účet 100 000 Kč, obchod váže 8 % účtu:

| | |
|---|---|
| marže obchodu | 8 000 Kč |
| objem pozice (páka 1:30) | 240 000 Kč |
| zisk +10 % marže | **+800 Kč = +0,8 % účtu** |
| průměrná ztráta (−67 % marže) | −5 360 Kč = −5,4 % účtu |

Roční výnos ≈ obchody za rok × průměrný zisk na obchod × podíl účtu na obchod. Vyšší výnos tedy dává buď
větší výhoda, nebo větší pozice. Větší pozice ale úměrně zvětšuje propady:

| velikost pozice proti CH-009 | ročně (2012–26) | max. propad | šance na propad ≥ 50 % za 10 let |
|---|---|---|---|
| 1× | +24 % | 19 % | 0 % |
| 1,5× | +36 % | 28 % | 0 % |
| 2× | +44 % | 37 % | 5 % |
| 3× | +49 % | 59 % | 68 % |

_(na 25 párech FXCM; nad 2× už výnos skoro neroste – nestačí marže a přibývá krachových drah)_

## 2. Nejdůležitější nové zjištění: test na trzích, které model nikdy neviděl

Stáhl jsem 16 dalších párů (HistData 2012–2026: NOK, SEK, MXN, ZAR, PLN, HUF, CZK, CHF/JPY, EUR/CAD,
GBP/AUD) a pustil na ně pravidla nalezená na 25 párech FXCM – bez jakékoli úpravy:

| pravidlo | 25 párů FXCM (kde bylo hledáno) 2023–26 | **16 nových párů** 2012–18 / 2019–22 / 2023–26 |
|---|---|---|
| F1 (pátek, RSI(2) + sazby) | +10,3 % na obchod | +8,3 / −0,8 / −2,4 % na obchod |
| CH-009 (4 stupně), ročně | +24,2 % | +0,2 % ročně (propad 56 %) / test −3,1 % |
| jen nejsilnější stupeň (sazby + carry) | +13,4 % na obchod | +0,4 / +3,6 / +6,2 % na obchod |

**Závěr:** dřívějších +24 % ročně platilo jen pro trhy, na kterých jsem hledal – část byla štěstí výběru.
Přežívá hlavně nejsilnější stupeň (páteční propad + rozcházející se sazby + carry ve směru obchodu).
Proto má učení od teď pravidlo navíc: **zlepšení musí fungovat i na trzích, kde nebylo hledáno.**

## 3. Jak samoučení funguje

1. **Šampion** = nejlepší dosavadní konfigurace (pravidla, stupně, velikosti, vesmír 41 párů).
2. **Pokus** = jedna změna (nový stupeň, filtr, výstup, velikost pozice, limit…).
3. Velikosti pozic se vždy vybírají **jen na starších datech** (propad ≤ 20 %) a hodnotí se na novějších,
   ve dvou kolech: výběr 2012–18 → test 2019–22, výběr 2012–22 → test 2023–26.
4. Pokus se přijme, jen když v **obou** testech zvýší roční výnos aspoň o 1 bod, propad zůstane v rozpočtu
   (≤ 23 %) a obchody v 2023–26 vydělávají **na obou skupinách trhů** (25 FXCM i 16 nových).
5. Dva profily:
   - **max** – nejvyšší roční výnos,
   - **měsíčně** – totéž, ale jen konfigurace s ≥ 2 ziskovými obchody měsíčně (a ≥ 2 v 70 % měsíců).
6. Každý pokus (přijatý i zamítnutý) se zapíše do `docs/UCENI_LOG.md`.

Zatím 23 pokusů v každém profilu, přijaty 2 (profil max): „jen nejsilnější stupeň“ a „velikost pozice podle
volatility“. Zamítnuty mj.: denní limitní stupně, filtr VIX, kratší držení, jiné cíle a stopy, limity na
jednu měnu, další signály – na novějších datech nepomohly nebo pomohly jen v jednom z testů.

## 4. Současní šampioni (41 párů, výsledky jen na datech, na kterých se nevybíralo)

| profil | pravidlo | test 2019–22 | **test 2023–26** | ziskových obchodů za měsíc |
|---|---|---|---|---|
| **max** | pátek: RSI(2) < 5 / > 95, sazby ≥ 0,25 p. b. + carry ve směru obchodu; TP 0,75 ATR, SL 3 ATR, max 20 dní; marže 10–12 % účtu × (84 % / stop obchodu v % marže), tj. menší pozice při širokém stopu | +22,9 % ročně, propad 22 % | **+19,1 % ročně, propad 20 %** | 1,4–1,9 |
| **měsíčně** | CH-009: 4 stupně podle síly sazeb, marže 6 / 3 / 3 / 0 % účtu | +17,8 %, propad 35 % | **+10,7 %, propad 21 %** | 4,5–9 |

Pro obojí najednou (≥ 20 % ročně **a** ≥ 2 ziskové obchody měsíčně) zatím model nenašel pravidlo, které
by obstálo na nových trzích i v čase. Učení hledá dál.

## 5. Co dál (učení pokračuje)

* Další fronta pokusů: potvrzení sazeb dvěma zdroji, pozicování spekulantů (COT), sezónnost (konec měsíce),
  rozložení vstupu (polovina hned, polovina limitem), výstup podle času po dosažení části cíle.
* Nová data: týdenní doplnění FXCM a HistData, měsíční sazby OECD – každé doplnění znamená nový,
  dosud neviděný kus testu.
* Skutečný důkaz zůstává dopředný test v evidenci predikcí; peníze až po něm.
