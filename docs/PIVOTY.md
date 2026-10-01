# Pivoty + SMA 50: test vasi metody

_216 variant (vcetne kontrolnich s obracenym trendem); poradi jen podle 2016-09..2021-12; R = zisk / riziko do SL po nakladech; t = jistota (nad ~2 neni nahoda)._

## 15 nejlepsich podle obdobi vyberu - a jak dopadly v jinych letech

| varianta (filtr / vstup / pivot / drzeni) | 2016-21 obchodu | uspesnych | E [R] | t | 2014-16 obchodu | uspesnych | E [R] | t | 2022-26 obchodu | uspesnych | E [R] | t |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D1+W1 / BOUNCE_S1 / pivot WEEK / max 5 d | 1138 | 53% | +0.041 | +1.4 | 549 | 50% | -0.019 | -0.4 | 1069 | 54% | +0.015 | +0.5 |
| D1 / BOUNCE_S1 / pivot WEEK / max 5 d | 1502 | 52% | +0.032 | +1.3 | 749 | 49% | -0.039 | -1.0 | 1384 | 53% | +0.019 | +0.7 |
| D1+W1 / BOUNCE_S1 / pivot WEEK / max 1 d | 1296 | 50% | +0.012 | +0.6 | 630 | 50% | -0.037 | -1.2 | 1232 | 51% | -0.006 | -0.3 |
| D1 / BREAK_R1 / pivot MONTH / max 5 d | 975 | 51% | +0.009 | +0.4 | 478 | 48% | -0.034 | -1.1 | 875 | 47% | -0.025 | -1.0 |
| PIVOT / BREAK_R1 / pivot MONTH / max 5 d | 1060 | 50% | +0.008 | +0.3 | 524 | 47% | -0.048 | -1.7 | 951 | 47% | -0.022 | -0.9 |
| W1 / BOUNCE_S1 / pivot WEEK / max 5 d | 1548 | 50% | +0.005 | +0.2 | 747 | 50% | -0.006 | -0.1 | 1404 | 52% | +0.017 | +0.6 |
| NONE / BREAK_R1 / pivot MONTH / max 5 d | 1082 | 50% | +0.002 | +0.1 | 535 | 47% | -0.048 | -1.6 | 965 | 47% | -0.023 | -0.9 |
| PIVOT / BOUNCE_S1 / pivot WEEK / max 5 d | 1550 | 53% | -0.001 | -0.0 | 787 | 49% | -0.074 | -2.2 | 1363 | 55% | +0.026 | +1.0 |
| PIVOT / BOUNCE_S1 / pivot MONTH / max 1 d | 235 | 49% | -0.003 | -0.1 | 132 | 41% | -0.082 | -2.4 | 202 | 49% | -0.054 | -1.8 |
| PIVOT / BREAK_R1 / pivot MONTH / max 1 d | 1463 | 47% | -0.003 | -0.3 | 717 | 48% | -0.011 | -0.8 | 1324 | 45% | -0.024 | -2.0 |
| NONE / BREAK_R1 / pivot MONTH / max 1 d | 1484 | 47% | -0.007 | -0.6 | 733 | 47% | -0.014 | -0.9 | 1345 | 45% | -0.026 | -2.0 |
| W1 / BOUNCE_S1 / pivot WEEK / max 1 d | 1849 | 49% | -0.007 | -0.4 | 878 | 50% | -0.028 | -1.0 | 1665 | 51% | -0.013 | -0.7 |
| D1+W1 / BREAK_R1 / pivot MONTH / max 5 d | 668 | 49% | -0.007 | -0.3 | 318 | 50% | -0.019 | -0.5 | 621 | 47% | -0.035 | -1.4 |
| D1 / BOUNCE_S1 / pivot WEEK / max 1 d | 1759 | 49% | -0.008 | -0.5 | 868 | 49% | -0.050 | -1.9 | 1614 | 50% | -0.014 | -0.8 |
| D1 / BREAK_R1 / pivot MONTH / max 1 d | 1339 | 46% | -0.008 | -0.7 | 657 | 47% | -0.011 | -0.7 | 1226 | 44% | -0.031 | -2.5 |

Kladne ve vsech trech obdobich: **0 z 120** variant.

## Pomaha trendovy filtr SMA 50? (prumer E pres vstupy, pivoty a drzeni)

| filtr | 2014-16 | 2016-21 | 2022-26 | s obracenym trendem 2016-21 |
|---|---|---|---|---|
| NONE | -0.067 R | -0.054 R | -0.071 R | - |
| D1 | -0.065 R | -0.053 R | -0.071 R | -0.057 R |
| W1 | -0.057 R | -0.052 R | -0.075 R | -0.058 R |
| D1+W1 | -0.058 R | -0.054 R | -0.074 R | -0.058 R |
| PIVOT | -0.061 R | -0.047 R | -0.067 R | -0.092 R |

## Podle typu vstupu (prumer, 2016-21 / 2022-26)

| vstup | 2016-21 | 2022-26 | uspesnych 2016-21 |
|---|---|---|---|
| BOUNCE_P | -0.036 R | -0.043 R | 45% |
| BOUNCE_S1 | -0.036 R | -0.058 R | 49% |
| BREAK_R1 | -0.079 R | -0.107 R | 47% |
| MARKET | -0.057 R | -0.078 R | 54% |

## USD/JPY 1. 10. 2026 podle vaší metody (klasické pivoty + SMA 50)

Ceny Twelve Data (mid, denní svíčky v UTC – u brokera s uzávěrkou 17:00 New York se mohou
lišit o pár pipů), stav 06:54 UTC: **158,16**, dnešní rozpětí 157,33 – 158,40, ATR(D1) ≈ 1,05 JPY.

| úroveň | denní (z 30. 9.) | týdenní (z týdne 21. 9.) | měsíční (říjen, ze září) |
|---|---|---|---|
| R3 | 158,99 | 161,15 | 169,12 |
| R2 | 158,26 | 160,09 | 164,76 |
| R1 | 157,84 | **158,66** | 161,09 |
| P | 157,11 | **157,61** | **156,73** |
| S1 | 156,69 | 156,18 | 153,06 |
| S2 | 155,96 | 155,12 | 148,71 |

SMA 50: denní **157,52** (mírně klesá), týdenní **157,63** (roste). Cena je nad oběma a nad
týdenním i měsíčním P → podle vašich pravidel trend nahoru.

**Podle vašich pravidel pro long z 158,32 (není to doporučení; samotná metoda v testu výhodu neprokázala):**

* nejbližší odpor: **158,66** (týdenní R1), pak 159,00 (denní R3 a maximum minulého týdne 159,03), pak **160,09** (týdenní R2); 160,40 = zářijové maximum
* zóna podpory: **157,5 – 157,6** (SMA 50 D1, SMA 50 W1, týdenní P na jednom místě), pod ní 156,73 (měsíční P)
* **denní uzávěrka pod ~157,50** = cena pod SMA 50 i týdenním pivotem → podle vaší metody už trend nahoru neplatí
* stop-loss pod 157,50 je od vstupu ≈ 90 pipů, cíl 160,09 ≈ 177 pipů (R:R ≈ 1,9); cíl 158,66 je jen 34 pipů – horší poměr
* pozor: kolem **160** Japonsko historicky intervenovalo (2024: 160–162, propady o 4–5 JPY během hodin) a v září 2026 kurz spadl ze 160,40 na 152,38 – stop-loss je tu nutnost, ne volba

## Jak změřit váš „selský rozum“

Kód umí otestovat jen pevná pravidla; vaše rozhodování (co vidíte na grafu, kdy obchod
nevezmete) v nich není. Jediný poctivý test je zapisovat **každý** váš obchod předem a nechat
ho vyhodnotit:

```sh
python fxbot.py journal BUY USD/JPY 158.32 --sl 157.40 --tp 160.00 --time "2026-10-01 06:30" --horizon 120h --setup PIVOT_TREND --note "nad SMA50 D1+W1, nad tydennim P"
python fxbot.py run                      # vyhodnotí zapsané obchody na skutečných bid/ask cenách
python fxbot.py review --all --manual    # úspěšnost, průměr v R, a srovnání s náhodným směrem
```

Po ~30 obchodech je vidět směr, po ~100 je to průkazné. Když vaše obchody budou proti náhodě
významně lepší, máme důkaz, že ve vašem rozhodování je něco navíc – a teprve pak má smysl
hledat, *co přesně* to je, a dát to do bota.
