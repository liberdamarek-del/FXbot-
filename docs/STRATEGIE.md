# Vytezovani strategii: stovky indikatoru x nastaveni x fundamenty

## Zlepsilo se to? (shrnuti)

| | model V7.8.0 (5 dni) | 30 nejlepsich pravidel z vyberu (prumer) |
|---|---|---|
| 2016-21 (obdobi vyberu) | E -0.173, uspesnost 43.2 % | E +0.084, uspesnost 53.1 % (vybrano zde - zkreslene) |
| **2022-26 (kontrola)** | E +0.008, uspesnost 49.5 % | **E +0.056, uspesnost 52.2 %, kladnych 25 z 30** |
| **2014-16 (kontrola)** | E -0.121, uspesnost 49.7 % | E -0.296 (median -0.042), kladnych 9 z 30 |

* **Mirne zlepseni proti modelu v letech 2022-2026**, ale neprukazne (t kolem 0) a v letech 2014-2016 se
  neopakovalo. Zadne jednotlive pravidlo neproslo kontrolou v obou obdobich.
* Kombinace 20 nejlepsich i strojove uceni (logisticka regrese, uceni jen na minulosti) na novych letech
  nevydelaly; strojove uceni bylo dokonce horsi nez nahoda (47.5 %).
* **Spolecny vzorec nejlepsich pravidel:** vstup proti kratkodobemu prepaleni (Williams %R, Stochastic, RSI -
  preprodano/prekoupeno) jen ve smeru, ktery podporuji fundamenty / kdy pozicovani COT neni preplnene.
  Zapsano jako vyzyvatel CH-005 (docs/CHANGE_LOG.md) a sledovano dopredu: `python scripts/signals_today.py`.

_230 nastaveni indikatoru x 6 fundamentalnich filtru x 2 smery x drzeni 1/3/5 dni = **7846 otestovanych pravidel**; 12 paru; vyber jen na 2016-09..2021-12; kontrola na 2014-16 a 2022-26. E = prumer na obchod v ATR(D1) po nakladech a swapu; uspesnost = podil ziskovych obchodu; t > 2 = nepravdepodobne nahoda._

## Vychozi stav: soucasny model V7.8.0 ve stejnem mereni

| drzeni | 2016-21 obchodu | uspesnost | E | t | 2014-16 | | | | 2022-26 | | | |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 d | 4373 | 47.5% | -0.040 | -2.3 | 1772 | 47.3% | -0.033 | -0.8 | 3645 | 47.7% | -0.034 | -2.4 |
| 3 d | 1459 | 46.1% | -0.112 | -2.5 | 602 | 49.3% | -0.054 | +0.3 | 1250 | 48.8% | -0.035 | -0.5 |
| 5 d | 884 | 43.2% | -0.173 | -2.9 | 342 | 49.7% | -0.121 | -0.0 | 667 | 49.5% | +0.008 | +0.8 |

## 30 nejlepsich pravidel z obdobi vyberu a jak dopadla potom

| indikator | fundamentalni filtr | smer | drzeni | 2016-21 obchodu | uspesnost | E | t | 2014-16 obchodu | uspesnost | E | t | 2022-26 obchodu | uspesnost | E | t | prosel |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| DMI7 ADX>20 | +fundamenty (>=1 pro, 0 proti) | proti signalu | 5 d | 318 | 52.2% | +0.119 | +2.4 | 145 | 52.4% | +0.025 | -0.2 | 206 | 54.9% | +0.097 | +0.2 | ne |
| DMI7 ADX>15 | +fundamenty (>=1 pro, 0 proti) | proti signalu | 5 d | 360 | 52.5% | +0.107 | +2.1 | 168 | 52.4% | -0.974 | -1.0 | 232 | 54.3% | +0.132 | +0.5 | ne |
| Williams%R9 -90/-10 | +fundamenty (>=1 pro, 0 proti) | podle signalu | 1 d | 385 | 56.6% | +0.074 | +2.0 | 166 | 52.4% | +0.019 | +0.0 | 216 | 51.4% | +0.005 | -0.1 | ne |
| 4 dny za sebou | +carry | podle signalu | 3 d | 300 | 54.7% | +0.143 | +2.0 | 148 | 45.3% | -0.031 | -0.5 | 246 | 51.6% | +0.071 | -0.5 | ne |
| Williams%R9 -90/-10 | +COT ne proti | podle signalu | 5 d | 678 | 54.3% | +0.154 | +1.9 | 351 | 49.6% | -0.020 | +0.5 | 648 | 51.1% | +0.003 | -0.6 | ne |
| Stochastic14 10/90 | +COT ne proti | podle signalu | 5 d | 443 | 53.7% | +0.132 | +1.8 | 221 | 47.1% | -0.081 | -0.9 | 398 | 54.3% | +0.046 | -0.3 | ne |
| RSI5 30/70 | +riziko VIX | podle signalu | 5 d | 612 | 52.1% | +0.115 | +1.8 | 380 | 48.2% | -0.461 | -0.9 | 560 | 50.4% | +0.037 | -0.7 | ne |
| RSI3 20/80 | +riziko VIX | podle signalu | 5 d | 522 | 51.3% | +0.103 | +1.7 | 311 | 47.6% | -0.539 | -0.8 | 485 | 50.1% | +0.063 | -0.5 | ne |
| RSI5 20/80 | +riziko VIX | podle signalu | 3 d | 402 | 53.5% | +0.083 | +1.7 | 213 | 46.0% | -0.048 | -1.1 | 343 | 53.1% | +0.072 | +0.8 | ne |
| poloha v pasmu 100 | +sazby 20d | podle signalu | 3 d | 347 | 55.3% | +0.140 | +1.6 | 171 | 49.7% | -0.906 | -1.0 | 368 | 48.1% | -0.025 | +0.1 | ne |
| poloha v pasmu 10 | +fundamenty (>=1 pro, 0 proti) | podle signalu | 1 d | 379 | 54.9% | +0.052 | +1.6 | 156 | 53.2% | +0.037 | +0.2 | 216 | 50.0% | -0.005 | -0.2 | ne |
| tyden: nad pivotem | +fundamenty (>=1 pro, 0 proti) | proti signalu | 5 d | 399 | 49.6% | +0.088 | +1.5 | 157 | 52.9% | -1.019 | -0.9 | 243 | 56.0% | +0.259 | +1.1 | ne |
| RSI4 20/80 | +riziko VIX | podle signalu | 3 d | 587 | 53.2% | +0.077 | +1.5 | 321 | 46.7% | -0.045 | -1.0 | 510 | 51.6% | +0.024 | -0.3 | ne |
| RSI7 30/70 | +riziko VIX | podle signalu | 5 d | 414 | 53.6% | +0.124 | +1.5 | 270 | 49.3% | +0.019 | +0.1 | 380 | 51.1% | +0.031 | -0.6 | ne |
| poloha v pasmu 10 | +COT ne proti | podle signalu | 5 d | 673 | 54.1% | +0.149 | +1.4 | 359 | 48.7% | -0.065 | +0.4 | 644 | 51.1% | +0.003 | -0.9 | ne |
| Williams%R14 -90/-10 | +fundamenty (>=1 pro, 0 proti) | podle signalu | 1 d | 351 | 54.4% | +0.039 | +1.4 | 137 | 54.0% | +0.008 | -0.3 | 195 | 51.3% | +0.009 | +0.2 | ne |
| Williams%R5 -90/-10 | +fundamenty (>=1 pro, 0 proti) | podle signalu | 1 d | 418 | 56.9% | +0.063 | +1.3 | 181 | 53.0% | -0.017 | -0.9 | 247 | 50.2% | +0.001 | -0.1 | ne |
| poloha v pasmu 20 | +fundamenty (>=1 pro, 0 proti) | podle signalu | 1 d | 319 | 55.8% | +0.048 | +1.3 | 113 | 54.0% | -0.011 | -0.3 | 178 | 49.4% | -0.034 | -0.5 | ne |
| RSI7 30/70 | +riziko VIX | podle signalu | 3 d | 750 | 52.0% | +0.053 | +1.3 | 392 | 45.9% | -0.056 | -1.3 | 646 | 52.0% | +0.030 | -0.1 | ne |
| RSI3 20/80 | +fundamenty (>=1 pro, 0 proti) | podle signalu | 1 d | 492 | 53.7% | +0.040 | +1.2 | 231 | 53.2% | -0.846 | -1.0 | 294 | 56.8% | +0.054 | +0.9 | ne |
| Bollinger20/2.0 | +riziko VIX | podle signalu | 3 d | 361 | 51.5% | +0.021 | +1.2 | 169 | 47.9% | +0.072 | -0.6 | 294 | 55.1% | +0.058 | +0.3 | ne |
| RSI3 10/90 | +COT ne proti | podle signalu | 5 d | 319 | 53.0% | +0.047 | +1.2 | 172 | 50.6% | +0.005 | +0.1 | 267 | 54.7% | +0.093 | +0.1 | ne |
| CCI14 +-100 | +COT ne proti | podle signalu | 5 d | 748 | 51.9% | +0.040 | +1.2 | 396 | 49.7% | +0.008 | +0.5 | 622 | 52.1% | +0.003 | -1.2 | ne |
| Williams%R21 -90/-10 | +fundamenty (>=1 pro, 0 proti) | podle signalu | 1 d | 317 | 55.8% | +0.047 | +1.2 | 110 | 54.5% | -0.005 | -0.2 | 176 | 49.4% | -0.028 | -0.3 | ne |
| RSI3 10/90 | +riziko VIX | podle signalu | 3 d | 331 | 52.6% | +0.093 | +1.1 | 158 | 48.7% | +0.036 | -0.3 | 265 | 48.3% | -0.020 | -0.7 | ne |
| CCI40 +-100 | +riziko VIX | podle signalu | 5 d | 448 | 56.5% | +0.188 | +1.1 | 245 | 49.0% | -0.038 | +0.8 | 391 | 55.2% | +0.136 | -0.2 | ne |
| cena>EMA20 | +fundamenty (>=1 pro, 0 proti) | proti signalu | 5 d | 371 | 50.4% | +0.048 | +1.1 | 145 | 51.0% | -1.105 | -0.9 | 209 | 55.0% | +0.202 | +1.4 | ne |
| PSAR 0.02/0.2 | +fundamenty (>=1 pro, 0 proti) | proti signalu | 5 d | 378 | 47.9% | +0.062 | +1.1 | 172 | 56.4% | -0.834 | -0.8 | 242 | 49.6% | +0.071 | -0.6 | ne |
| ROC10 | +fundamenty (>=1 pro, 0 proti) | proti signalu | 5 d | 370 | 48.9% | +0.023 | +1.1 | 157 | 54.1% | -0.998 | -0.9 | 226 | 52.2% | +0.119 | +0.6 | ne |
| cena>SMA10 | +fundamenty (>=1 pro, 0 proti) | proti signalu | 5 d | 395 | 50.4% | +0.047 | +1.1 | 159 | 52.8% | -1.018 | -0.9 | 233 | 54.5% | +0.157 | +0.4 | ne |

**Proslo kontrolou v obou dalsich obdobich: 0 z 30.** Nahodne signaly projdou stejnou kontrolou v 0.0% pripadu, tj. cekane cislo cistou nahodou je 0.0 z 30.

Pozn.: 2014-16 obsahuje sok SNB 15. 1. 2015 (EUR/CHF -30 % behem minut, ~40 ATR na jeden obchod); pravidla, ktera tehdy drzela CHF kratce, tam maji velky zaporny prumer.

## Kombinace 20 nejlepsich (hlasovani, drzeni 5 dni)

| obdobi | obchodu | uspesnost | E | t |
|---|---|---|---|---|
| 2016-21 (vyber) | 459 | 51.2% | +0.093 | +1.4 |
| 2014-16 | 266 | 50.0% | -0.567 | -0.7 |
| 2022-26 | 389 | 52.2% | +0.107 | -0.2 |

## Strojove uceni (logisticka regrese ze vsech indikatoru a fundamentu, uceni vzdy jen na minulych letech, drzeni 5 dni)

| prah jistoty | obchodu | uspesnost | E | hruby smer | t |
|---|---|---|---|---|---|
| 50 % | 6617 | 47.5% | -0.089 | -0.041 | -2.9 |
| 52 % | 6524 | 47.5% | -0.091 | -0.043 | -3.0 |
| 55 % | 6381 | 47.4% | -0.095 | -0.048 | -3.1 |

Po letech (prah 52 %): 2016: 51% / +0.077, 2017: 47% / -0.058, 2018: 47% / -0.083, 2019: 45% / -0.181, 2020: 45% / -0.213, 2021: 49% / -0.062, 2022: 49% / +0.022, 2023: 52% / -0.013, 2024: 48% / -0.068, 2025: 43% / -0.272, 2026: 44% / -0.165

_vypocet 31 s_
