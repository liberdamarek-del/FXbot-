# Vyhodnoceni modelu na historii - OUT-OF-SAMPLE 2016-06 .. 2023-07 (FXCM, model tato data nevidel)

_vygenerovano 2026-10-01 03:28 UTC_

- pary: EUR/USD, USD/JPY, GBP/USD, USD/CHF, AUD/USD, USD/CAD, NZD/USD, EUR/JPY, GBP/JPY, EUR/GBP, EUR/CHF, AUD/JPY
- rozhodnuti: 2016-09-26 .. 2023-08-11, kazdou H4 svicku; zahrati indikatoru 120 dni
- parametry (champion): `925094abd869c878`; naklady: spread z dat + 0.5 pip prirazka + 0.2 pip skluz na stranu
- ceny: FXCM BID/ASK (hodinove svicky, minutove pro poradi v nejasne hodine; samostatny vyzkumny archiv) - verejne ceny, ne ceny vaseho brokera
- udalostni vrstva (kalendar) VYPNUTA - volny kalendar nema historii

## 1. Model vs kontrola (modul 74)

| | predikci | vstupu | win | smer 24 h | E [R] | 95% IS | PF | max DD [R] | nezavislych | vzorek |
|---|---|---|---|---|---|---|---|---|---|---|
| model | 10640 | 4906 | 23 % | 49 % | -0.076 | -0.123 .. -0.029 | 0.90 | -380.0 | 2611 | DLOUHODOBY BENCHMARK (n>=100) |
| anti-model (opacny smer) | 10640 | 4930 | 24 % | 51 % | -0.052 | -0.100 .. -0.005 | 0.93 | -356.1 | 2503 | DLOUHODOBY BENCHMARK (n>=100) |

Na jedno rozhodnuti (neaktivovany limit = 0 R): model **-0.035 R**, nahodny smer (presne ocekavani = prumer modelu a anti-modelu) **-0.030 R**, n = 10502.
**Edge smeru vs nahoda (parovy test): -0.005 R (95% IS -0.022 .. +0.012) -> NEVYZNAMNY.**

- model: **poradi neznamo** u 74 obchodu (2 %; SL/TP a vstup ve stejne hodinove svicce bez minutovych dat). Meze E na obchod: **-0.090 R** (vse SL) .. **-0.034 R** (vse TP1); na rozhodnuti -0.041 .. -0.016 R. Neznamy vysledek se nehada (modul 61) - zuzi ho jen minutova data.
- anti-model: **poradi neznamo** u 60 obchodu (1 %; SL/TP a vstup ve stejne hodinove svicce bez minutovych dat). Meze E na obchod: **-0.064 R** (vse SL) .. **-0.020 R** (vse TP1); na rozhodnuti -0.030 .. -0.009 R. Neznamy vysledek se nehada (modul 61) - zuzi ho jen minutova data.
- model, cim byl vysledek rozhodnut: hodinove svicky 9519, 1 min FXCM (stejny zdroj) 1043

## 2. Kvalita smeru bez geometrie obchodu (modul 66)

Prumerny pohyb mid ceny ve smeru modelu (v ATR H1 v case rozhodnuti); nahodny smer = 0.

| horizont | pohyb [ATR] | 95% IS (optimisticky, prekryvy) | zasah | n |
|---|---|---|---|---|
| 24 h | -0.08 | -0.15 .. -0.02 | 49 % | 10489 |
| 72 h | -0.17 | -0.27 .. -0.07 | 49 % | 10636 |
| 120 h | -0.22 | -0.35 .. -0.10 | 48 % | 10640 |

## 3. Rozpad (modul 73) a kalibrace (modul 72)

### struktura

| | predikci | vstupu | win | smer 24 h | E [R] | 95% IS | PF | max DD [R] | nezavislych | vzorek |
|---|---|---|---|---|---|---|---|---|---|---|
| MIXED | 2963 | 1374 | 24 % | 49 % | -0.077 | -0.165 .. +0.011 | 0.90 | -121.8 | 949 | DLOUHODOBY BENCHMARK (n>=100) |
| RANGE | 3622 | 1704 | 22 % | 50 % | -0.083 | -0.163 .. -0.003 | 0.89 | -166.6 | 1163 | DLOUHODOBY BENCHMARK (n>=100) |
| TREND | 4055 | 1828 | 23 % | 47 % | -0.068 | -0.145 .. +0.009 | 0.91 | -143.6 | 1044 | DLOUHODOBY BENCHMARK (n>=100) |

### volatilita

| | predikci | vstupu | win | smer 24 h | E [R] | 95% IS | PF | max DD [R] | nezavislych | vzorek |
|---|---|---|---|---|---|---|---|---|---|---|
| EXTREME | 857 | 391 | 24 % | 45 % | -0.041 | -0.206 .. +0.124 | 0.94 | -29.4 | 242 | DLOUHODOBY BENCHMARK (n>=100) |
| HIGH | 1678 | 734 | 22 % | 52 % | -0.134 | -0.252 .. -0.016 | 0.82 | -119.2 | 463 | DLOUHODOBY BENCHMARK (n>=100) |
| LOW | 4051 | 1837 | 23 % | 50 % | -0.069 | -0.146 .. +0.009 | 0.91 | -144.8 | 1139 | DLOUHODOBY BENCHMARK (n>=100) |
| NORMAL | 4054 | 1944 | 23 % | 47 % | -0.067 | -0.142 .. +0.007 | 0.91 | -152.2 | 1189 | DLOUHODOBY BENCHMARK (n>=100) |

### riziko

| | predikci | vstupu | win | smer 24 h | E [R] | 95% IS | PF | max DD [R] | nezavislych | vzorek |
|---|---|---|---|---|---|---|---|---|---|---|
| NEUTRAL | 8873 | 4117 | 23 % | 49 % | -0.088 | -0.139 .. -0.037 | 0.88 | -372.4 | 2217 | DLOUHODOBY BENCHMARK (n>=100) |
| RISK_OFF | 1427 | 613 | 26 % | 50 % | -0.027 | -0.159 .. +0.105 | 0.96 | -69.0 | 318 | DLOUHODOBY BENCHMARK (n>=100) |
| RISK_ON | 340 | 176 | 25 % | 49 % | +0.052 | -0.217 .. +0.322 | 1.07 | -24.9 | 106 | DLOUHODOBY BENCHMARK (n>=100) |

### smer

| | predikci | vstupu | win | smer 24 h | E [R] | 95% IS | PF | max DD [R] | nezavislych | vzorek |
|---|---|---|---|---|---|---|---|---|---|---|
| BUY | 5615 | 2591 | 23 % | 49 % | -0.086 | -0.150 .. -0.022 | 0.88 | -231.0 | 1562 | DLOUHODOBY BENCHMARK (n>=100) |
| SELL | 5025 | 2315 | 23 % | 48 % | -0.064 | -0.133 .. +0.004 | 0.91 | -171.6 | 1430 | DLOUHODOBY BENCHMARK (n>=100) |

### setup

| | predikci | vstupu | win | smer 24 h | E [R] | 95% IS | PF | max DD [R] | nezavislych | vzorek |
|---|---|---|---|---|---|---|---|---|---|---|
| BREAKOUT_RETEST | 5021 | 2159 | 25 % | 48 % | -0.002 | -0.074 .. +0.070 | 1.00 | -91.7 | 1432 | DLOUHODOBY BENCHMARK (n>=100) |
| CONTINUATION | 102 | 30 | 15 % | 51 % | -0.409 | -0.853 .. +0.036 | 0.48 | -11.9 | 28 | PREDBEZNE (n 20-49) |
| PULLBACK | 5517 | 2717 | 21 % | 49 % | -0.131 | -0.193 .. -0.069 | 0.83 | -366.6 | 1841 | DLOUHODOBY BENCHMARK (n>=100) |

### rozhodnuti

| | predikci | vstupu | win | smer 24 h | E [R] | 95% IS | PF | max DD [R] | nezavislych | vzorek |
|---|---|---|---|---|---|---|---|---|---|---|
| BUY NOW | 174 | 174 | 22 % | 51 % | -0.205 | -0.440 .. +0.031 | 0.75 | -49.8 | 161 | DLOUHODOBY BENCHMARK (n>=100) |
| SELL NOW | 133 | 132 | 22 % | 48 % | -0.231 | -0.486 .. +0.025 | 0.71 | -41.5 | 122 | DLOUHODOBY BENCHMARK (n>=100) |
| WAIT FOR BUY | 5441 | 2417 | 23 % | 49 % | -0.077 | -0.144 .. -0.011 | 0.90 | -196.3 | 1508 | DLOUHODOBY BENCHMARK (n>=100) |
| WAIT FOR SELL | 4892 | 2183 | 23 % | 48 % | -0.054 | -0.125 .. +0.017 | 0.93 | -163.2 | 1390 | DLOUHODOBY BENCHMARK (n>=100) |

### par

| | predikci | vstupu | win | smer 24 h | E [R] | 95% IS | PF | max DD [R] | nezavislych | vzorek |
|---|---|---|---|---|---|---|---|---|---|---|
| AUD/JPY | 809 | 402 | 19 % | 49 % | -0.174 | -0.328 .. -0.020 | 0.77 | -77.1 | 306 | DLOUHODOBY BENCHMARK (n>=100) |
| AUD/USD | 879 | 401 | 25 % | 47 % | -0.023 | -0.191 .. +0.144 | 0.97 | -41.6 | 326 | DLOUHODOBY BENCHMARK (n>=100) |
| EUR/CHF | 592 | 285 | 21 % | 49 % | -0.149 | -0.341 .. +0.044 | 0.81 | -52.7 | 224 | DLOUHODOBY BENCHMARK (n>=100) |
| EUR/GBP | 869 | 396 | 22 % | 45 % | -0.132 | -0.296 .. +0.033 | 0.83 | -68.0 | 319 | DLOUHODOBY BENCHMARK (n>=100) |
| EUR/JPY | 852 | 393 | 25 % | 48 % | -0.028 | -0.196 .. +0.141 | 0.96 | -44.6 | 309 | DLOUHODOBY BENCHMARK (n>=100) |
| EUR/USD | 1114 | 507 | 23 % | 49 % | -0.101 | -0.244 .. +0.042 | 0.86 | -61.4 | 387 | DLOUHODOBY BENCHMARK (n>=100) |
| GBP/JPY | 950 | 424 | 22 % | 49 % | -0.128 | -0.283 .. +0.027 | 0.83 | -66.0 | 340 | DLOUHODOBY BENCHMARK (n>=100) |
| GBP/USD | 967 | 438 | 20 % | 50 % | -0.180 | -0.328 .. -0.033 | 0.76 | -88.6 | 342 | DLOUHODOBY BENCHMARK (n>=100) |
| NZD/USD | 784 | 368 | 25 % | 50 % | -0.025 | -0.194 .. +0.145 | 0.97 | -22.9 | 290 | DLOUHODOBY BENCHMARK (n>=100) |
| USD/CAD | 937 | 420 | 24 % | 50 % | -0.019 | -0.186 .. +0.149 | 0.97 | -35.8 | 321 | DLOUHODOBY BENCHMARK (n>=100) |
| USD/CHF | 761 | 364 | 28 % | 50 % | +0.148 | -0.046 .. +0.342 | 1.21 | -17.4 | 286 | DLOUHODOBY BENCHMARK (n>=100) |
| USD/JPY | 1126 | 508 | 24 % | 50 % | -0.079 | -0.223 .. +0.065 | 0.89 | -60.8 | 376 | DLOUHODOBY BENCHMARK (n>=100) |

### duvera

| | predikci | vstupu | win | smer 24 h | E [R] | 95% IS | PF | max DD [R] | nezavislych | vzorek |
|---|---|---|---|---|---|---|---|---|---|---|
| A | 1521 | 697 | 25 % | 50 % | -0.036 | -0.160 .. +0.087 | 0.95 | -76.9 | 463 | DLOUHODOBY BENCHMARK (n>=100) |
| B | 3620 | 1672 | 23 % | 48 % | -0.105 | -0.184 .. -0.026 | 0.86 | -182.2 | 1097 | DLOUHODOBY BENCHMARK (n>=100) |
| C | 5499 | 2537 | 23 % | 49 % | -0.067 | -0.133 .. -0.001 | 0.91 | -203.7 | 1619 | DLOUHODOBY BENCHMARK (n>=100) |

Kalibrace trid duvery: **CALIBRATION FAILURE**

## 4. Taxonomie chyb (modul 69)

| pocet | rodina: pripad |
|---|---|
| 5333 | entry: correct direction / wrong entry (too deep) |
| 1150 | direction: wrong trade |
| 986 | TP: correct direction / poor TP or management |
| 800 | trigger: correct setup / bad trigger (failed retest) |
| 564 | timing: correct thesis / wrong timing |
| 398 | entry: no entry within horizon |
| 208 | TP: correct direction / TP too far for the horizon |
| 118 | noise: correct direction, SL almost hit (fragile win) |
| 74 | data: sequence not provable at available granularity |
| 72 | timing: thesis not confirmed within horizon |
| 3 | data: path gap |

Nejcastejsi duvody NEOBCHODOVAT:

- 46907x H4 bez trendu
- 9838x technicky SELL, ale fundamenty proti
- 9415x technicky BUY, ale fundamenty proti
- 8496x D1/H4/momentum si odporuji
- 735x cena je pod/nad H1 EMA20 proti smeru a zadna uroven v dosahu
- 675x cena je primo na urovni a NOW je blokovano
- 478x krehky signal a bez platneho cekaciho vstupu
- 337x R:R -0.17 po nakladech pod hranici 1.5
- 333x R:R -0.12 po nakladech pod hranici 1.5
- 323x R:R -0.04 po nakladech pod hranici 1.5

## 5. Ablace vrstev (modul 75)

| varianta | predikci | vstupu | E na obchod [R] | meze E (neznamo) | edge smeru vs nahoda [R/rozhodnuti] | 95% IS |
|---|---|---|---|---|---|---|
| FULL | 10640 | 4906 | -0.076 | -0.090 .. -0.034 | -0.005 | -0.022 .. +0.012 |
| BEZ FUNDAMENTU | 13112 | 6081 | -0.083 | -0.097 .. -0.039 | -0.001 | -0.017 .. +0.014 |
| BEZ NO-CHASE | 10615 | 4896 | -0.076 | -0.090 .. -0.035 | -0.005 | -0.022 .. +0.012 |
| R:R >= 1.0 | 14629 | 6616 | -0.077 | -0.091 .. -0.042 | -0.004 | -0.018 .. +0.010 |
| R:R >= 2.0 | 5757 | 2692 | -0.081 | -0.096 .. -0.030 | -0.021 | -0.046 .. +0.004 |

## Zaver

Cisla vyse jsou historicky pokus na verejnych cenach s modelovanymi naklady. Rozhoduje jen out-of-sample dukaz a dopredne testovani zamcenych predikci; zadna zmena se neprovadi automaticky.

_vypocet trval 349 s_
