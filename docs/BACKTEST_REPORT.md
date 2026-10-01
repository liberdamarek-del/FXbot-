# Vyhodnoceni modelu na historii

_vygenerovano 2026-10-01 03:10 UTC_

- pary: EUR/USD, USD/JPY, GBP/USD, USD/CHF, AUD/USD, USD/CAD, NZD/USD, EUR/JPY, GBP/JPY, EUR/GBP, EUR/CHF, AUD/JPY
- rozhodnuti: 2023-11-29 .. 2026-09-29, kazdou H4 svicku; zahrati indikatoru 120 dni
- parametry (champion): `925094abd869c878`; naklady: spread z dat + 0.5 pip prirazka + 0.2 pip skluz na stranu
- ceny: Dukascopy BID/ASK (hodinove svicky; minutove kde jsou archivovane, jinak FXCM minuty jen pro poradi v nejasne hodine) - verejne ceny, ne ceny vaseho brokera
- udalostni vrstva (kalendar) VYPNUTA - volny kalendar nema historii

## 1. Model vs kontrola (modul 74)

| | predikci | vstupu | win | smer 24 h | E [R] | 95% IS | PF | max DD [R] | nezavislych | vzorek |
|---|---|---|---|---|---|---|---|---|---|---|
| model | 3958 | 1777 | 22 % | 51 % | -0.063 | -0.145 .. +0.019 | 0.92 | -206.4 | 883 | DLOUHODOBY BENCHMARK (n>=100) |
| anti-model (opacny smer) | 3958 | 1810 | 20 % | 49 % | -0.162 | -0.238 .. -0.085 | 0.79 | -314.3 | 889 | DLOUHODOBY BENCHMARK (n>=100) |

Na jedno rozhodnuti (neaktivovany limit = 0 R): model **-0.036 R**, nahodny smer (presne ocekavani = prumer modelu a anti-modelu) **-0.057 R**, n = 3745.
**Edge smeru vs nahoda (parovy test): +0.022 R (95% IS -0.006 .. +0.049) -> NEVYZNAMNY.**

- model: **poradi neznamo** u 109 obchodu (6 %; SL/TP a vstup ve stejne hodinove svicce bez minutovych dat). Meze E na obchod: **-0.120 R** (vse SL) .. **+0.091 R** (vse TP1); na rozhodnuti -0.054 .. +0.041 R. Neznamy vysledek se nehada (modul 61) - zuzi ho jen minutova data.
- anti-model: **poradi neznamo** u 118 obchodu (7 %; SL/TP a vstup ve stejne hodinove svicce bez minutovych dat). Meze E na obchod: **-0.216 R** (vse SL) .. **+0.016 R** (vse TP1); na rozhodnuti -0.099 .. +0.008 R. Neznamy vysledek se nehada (modul 61) - zuzi ho jen minutova data.
- model, cim byl vysledek rozhodnut: hodinove svicky 3537, 1 min FXCM (druhy zdroj, stejne udalosti) 302, 1 min Dukascopy 6

## 2. Kvalita smeru bez geometrie obchodu (modul 66)

Prumerny pohyb mid ceny ve smeru modelu (v ATR H1 v case rozhodnuti); nahodny smer = 0.

| horizont | pohyb [ATR] | 95% IS (optimisticky, prekryvy) | zasah | n |
|---|---|---|---|---|
| 24 h | -0.01 | -0.12 .. +0.10 | 51 % | 3899 |
| 72 h | -0.09 | -0.26 .. +0.08 | 50 % | 3958 |
| 120 h | -0.15 | -0.35 .. +0.04 | 50 % | 3958 |

## 3. Rozpad (modul 73) a kalibrace (modul 72)

### struktura

| | predikci | vstupu | win | smer 24 h | E [R] | 95% IS | PF | max DD [R] | nezavislych | vzorek |
|---|---|---|---|---|---|---|---|---|---|---|
| MIXED | 1335 | 566 | 24 % | 54 % | -0.011 | -0.158 .. +0.136 | 0.99 | -63.8 | 354 | DLOUHODOBY BENCHMARK (n>=100) |
| RANGE | 1401 | 649 | 23 % | 52 % | -0.013 | -0.153 .. +0.127 | 0.98 | -87.1 | 421 | DLOUHODOBY BENCHMARK (n>=100) |
| TREND | 1222 | 562 | 19 % | 48 % | -0.176 | -0.312 .. -0.039 | 0.77 | -91.3 | 308 | DLOUHODOBY BENCHMARK (n>=100) |

### volatilita

| | predikci | vstupu | win | smer 24 h | E [R] | 95% IS | PF | max DD [R] | nezavislych | vzorek |
|---|---|---|---|---|---|---|---|---|---|---|
| EXTREME | 302 | 122 | 26 % | 54 % | +0.119 | -0.191 .. +0.430 | 1.18 | -12.3 | 76 | SILNEJSI, OPATRNE (n 50-99) |
| HIGH | 734 | 346 | 22 % | 47 % | -0.074 | -0.263 .. +0.115 | 0.90 | -66.9 | 210 | DLOUHODOBY BENCHMARK (n>=100) |
| LOW | 1340 | 585 | 21 % | 52 % | -0.128 | -0.268 .. +0.012 | 0.83 | -90.4 | 347 | DLOUHODOBY BENCHMARK (n>=100) |
| NORMAL | 1582 | 724 | 23 % | 51 % | -0.037 | -0.166 .. +0.092 | 0.95 | -95.9 | 427 | DLOUHODOBY BENCHMARK (n>=100) |

### riziko

| | predikci | vstupu | win | smer 24 h | E [R] | 95% IS | PF | max DD [R] | nezavislych | vzorek |
|---|---|---|---|---|---|---|---|---|---|---|
| NEUTRAL | 3047 | 1362 | 22 % | 52 % | -0.056 | -0.151 .. +0.038 | 0.92 | -173.7 | 708 | DLOUHODOBY BENCHMARK (n>=100) |
| RISK_OFF | 276 | 123 | 28 % | 39 % | +0.105 | -0.202 .. +0.411 | 1.15 | -14.1 | 58 | SILNEJSI, OPATRNE (n 50-99) |
| RISK_ON | 635 | 292 | 21 % | 50 % | -0.166 | -0.358 .. +0.025 | 0.78 | -47.6 | 137 | DLOUHODOBY BENCHMARK (n>=100) |

### smer

| | predikci | vstupu | win | smer 24 h | E [R] | 95% IS | PF | max DD [R] | nezavislych | vzorek |
|---|---|---|---|---|---|---|---|---|---|---|
| BUY | 2539 | 1148 | 21 % | 53 % | -0.099 | -0.200 .. +0.002 | 0.87 | -172.6 | 643 | DLOUHODOBY BENCHMARK (n>=100) |
| SELL | 1419 | 629 | 24 % | 48 % | +0.002 | -0.137 .. +0.141 | 1.00 | -40.9 | 377 | DLOUHODOBY BENCHMARK (n>=100) |

### setup

| | predikci | vstupu | win | smer 24 h | E [R] | 95% IS | PF | max DD [R] | nezavislych | vzorek |
|---|---|---|---|---|---|---|---|---|---|---|
| BREAKOUT_RETEST | 1796 | 750 | 22 % | 52 % | -0.075 | -0.201 .. +0.050 | 0.90 | -85.4 | 473 | DLOUHODOBY BENCHMARK (n>=100) |
| CONTINUATION | 38 | 6 | 25 % | 45 % | +0.196 | -1.856 .. +2.248 | 1.29 | -3.1 | 5 | POUZE POPISNE (n<20) |
| PULLBACK | 2124 | 1021 | 22 % | 50 % | -0.055 | -0.163 .. +0.053 | 0.93 | -120.6 | 640 | DLOUHODOBY BENCHMARK (n>=100) |

### rozhodnuti

| | predikci | vstupu | win | smer 24 h | E [R] | 95% IS | PF | max DD [R] | nezavislych | vzorek |
|---|---|---|---|---|---|---|---|---|---|---|
| BUY NOW | 55 | 55 | 20 % | 55 % | -0.234 | -0.679 .. +0.211 | 0.72 | -20.2 | 53 | SILNEJSI, OPATRNE (n 50-99) |
| SELL NOW | 27 | 27 | 32 % | 41 % | +0.180 | -0.539 .. +0.900 | 1.26 | -7.2 | 25 | PREDBEZNE (n 20-49) |
| WAIT FOR BUY | 2484 | 1093 | 21 % | 53 % | -0.092 | -0.196 .. +0.012 | 0.88 | -156.6 | 623 | DLOUHODOBY BENCHMARK (n>=100) |
| WAIT FOR SELL | 1392 | 602 | 24 % | 48 % | -0.007 | -0.148 .. +0.135 | 0.99 | -49.8 | 369 | DLOUHODOBY BENCHMARK (n>=100) |

### par

| | predikci | vstupu | win | smer 24 h | E [R] | 95% IS | PF | max DD [R] | nezavislych | vzorek |
|---|---|---|---|---|---|---|---|---|---|---|
| AUD/JPY | 382 | 177 | 27 % | 51 % | +0.047 | -0.218 .. +0.311 | 1.07 | -15.7 | 138 | DLOUHODOBY BENCHMARK (n>=100) |
| AUD/USD | 260 | 121 | 20 % | 47 % | -0.177 | -0.484 .. +0.129 | 0.78 | -28.8 | 103 | DLOUHODOBY BENCHMARK (n>=100) |
| EUR/CHF | 205 | 103 | 14 % | 51 % | -0.356 | -0.643 .. -0.069 | 0.56 | -39.3 | 81 | SILNEJSI, OPATRNE (n 50-99) |
| EUR/GBP | 150 | 73 | 18 % | 52 % | -0.115 | -0.546 .. +0.317 | 0.85 | -26.1 | 60 | SILNEJSI, OPATRNE (n 50-99) |
| EUR/JPY | 392 | 163 | 21 % | 51 % | -0.089 | -0.351 .. +0.173 | 0.88 | -18.3 | 126 | DLOUHODOBY BENCHMARK (n>=100) |
| EUR/USD | 472 | 198 | 27 % | 45 % | +0.125 | -0.135 .. +0.384 | 1.18 | -23.8 | 148 | DLOUHODOBY BENCHMARK (n>=100) |
| GBP/JPY | 354 | 160 | 25 % | 53 % | +0.091 | -0.206 .. +0.388 | 1.13 | -21.1 | 121 | DLOUHODOBY BENCHMARK (n>=100) |
| GBP/USD | 420 | 182 | 25 % | 53 % | -0.016 | -0.268 .. +0.235 | 0.98 | -29.2 | 132 | DLOUHODOBY BENCHMARK (n>=100) |
| NZD/USD | 228 | 105 | 23 % | 50 % | -0.017 | -0.371 .. +0.337 | 0.98 | -15.7 | 80 | SILNEJSI, OPATRNE (n 50-99) |
| USD/CAD | 298 | 142 | 18 % | 54 % | -0.181 | -0.467 .. +0.106 | 0.77 | -25.6 | 106 | DLOUHODOBY BENCHMARK (n>=100) |
| USD/CHF | 308 | 141 | 20 % | 50 % | -0.172 | -0.460 .. +0.116 | 0.78 | -36.5 | 111 | DLOUHODOBY BENCHMARK (n>=100) |
| USD/JPY | 489 | 212 | 22 % | 55 % | -0.115 | -0.337 .. +0.108 | 0.85 | -29.7 | 155 | DLOUHODOBY BENCHMARK (n>=100) |

### duvera

| | predikci | vstupu | win | smer 24 h | E [R] | 95% IS | PF | max DD [R] | nezavislych | vzorek |
|---|---|---|---|---|---|---|---|---|---|---|
| A | 697 | 301 | 23 % | 54 % | -0.014 | -0.214 .. +0.187 | 0.98 | -39.5 | 204 | DLOUHODOBY BENCHMARK (n>=100) |
| B | 1257 | 591 | 24 % | 51 % | -0.013 | -0.156 .. +0.129 | 0.98 | -55.3 | 382 | DLOUHODOBY BENCHMARK (n>=100) |
| C | 2004 | 885 | 21 % | 50 % | -0.113 | -0.228 .. +0.002 | 0.85 | -131.3 | 535 | DLOUHODOBY BENCHMARK (n>=100) |

Kalibrace trid duvery: **CALIBRATION FAILURE**

## 4. Taxonomie chyb (modul 69)

| pocet | rodina: pripad |
|---|---|
| 2022 | entry: correct direction / wrong entry (too deep) |
| 416 | direction: wrong trade |
| 347 | TP: correct direction / poor TP or management |
| 274 | trigger: correct setup / bad trigger (failed retest) |
| 172 | timing: correct thesis / wrong timing |
| 156 | entry: no entry within horizon |
| 109 | data: sequence not provable at available granularity |
| 82 | TP: correct direction / TP too far for the horizon |
| 48 | noise: correct direction, SL almost hit (fragile win) |
| 29 | timing: thesis not confirmed within horizon |
| 4 | data: path gap |

Nejcastejsi duvody NEOBCHODOVAT:

- 19406x H4 bez trendu
- 4486x technicky SELL, ale fundamenty proti
- 3768x D1/H4/momentum si odporuji
- 2559x technicky BUY, ale fundamenty proti
- 355x cena je pod/nad H1 EMA20 proti smeru a zadna uroven v dosahu
- 266x cena je primo na urovni a NOW je blokovano
- 214x krehky signal a bez platneho cekaciho vstupu
- 157x R:R -0.17 po nakladech pod hranici 1.5
- 155x R:R -0.02 po nakladech pod hranici 1.5
- 147x R:R 0.00 po nakladech pod hranici 1.5

## 5. Ablace vrstev (modul 75)

| varianta | predikci | vstupu | E na obchod [R] | meze E (neznamo) | edge smeru vs nahoda [R/rozhodnuti] | 95% IS |
|---|---|---|---|---|---|---|
| FULL | 3958 | 1777 | -0.063 | -0.120 .. +0.091 | +0.022 | -0.006 .. +0.049 |
| BEZ FUNDAMENTU | 5129 | 2287 | -0.060 | -0.120 .. +0.102 | +0.012 | -0.012 .. +0.037 |
| BEZ NO-CHASE | 3949 | 1772 | -0.069 | -0.125 .. +0.083 | +0.019 | -0.008 .. +0.047 |
| R:R >= 1.0 | 5845 | 2620 | -0.072 | -0.131 .. +0.066 | +0.019 | -0.003 .. +0.041 |
| R:R >= 2.0 | 2230 | 998 | -0.073 | -0.122 .. +0.089 | +0.018 | -0.020 .. +0.056 |

## 6. Robustnost (modul 76)

| parametr | hodnota | obchodu | E [R] | meze E (neznamo) | edge smeru vs nahoda | 95% IS | znamenko E se otoci |
|---|---|---|---|---|---|---|---|
| entry_offset_atr | 0.2 | 1744 | -0.041 | -0.111 .. +0.152 | +0.027 | +0.001 .. +0.052 | ne |
| entry_offset_atr | 0.4 | 1625 | -0.047 | -0.101 .. +0.091 | +0.033 | +0.003 .. +0.062 | ne |
| stop_buffer_atr | 0.35 | 2004 | -0.076 | -0.154 .. +0.167 | +0.028 | +0.001 .. +0.054 | ne |
| stop_buffer_atr | 0.65 | 1478 | -0.035 | -0.082 .. +0.076 | +0.035 | +0.007 .. +0.062 | ne |
| max_tp1_atr | 2.5 | 1657 | -0.056 | -0.114 .. +0.088 | +0.023 | -0.003 .. +0.049 | ne |
| max_tp1_atr | 3.5 | 1667 | -0.049 | -0.108 .. +0.116 | +0.025 | -0.004 .. +0.053 | ne |
| trend_slope_atr | 0.1 | 1718 | -0.053 | -0.113 .. +0.106 | +0.023 | -0.004 .. +0.050 | ne |
| trend_slope_atr | 0.2 | 1619 | -0.066 | -0.123 .. +0.087 | +0.020 | -0.008 .. +0.048 | ne |
| broker_markup_pips | 0.0 | 1852 | -0.070 | -0.128 .. +0.090 | +0.019 | -0.007 .. +0.045 | ne |
| broker_markup_pips | 1.0 | 1503 | -0.066 | -0.119 .. +0.077 | +0.018 | -0.011 .. +0.047 | ne |
| near_level_atr | 0.45 | 1711 | -0.072 | -0.127 .. +0.071 | +0.023 | -0.004 .. +0.049 | ne |
| near_level_atr | 0.75 | 1613 | -0.064 | -0.123 .. +0.100 | +0.019 | -0.009 .. +0.047 | ne |

## 7. Walk-forward out-of-sample (modul 77)

| okno testu | vybrane parametry (jen z minulosti) | OOS E vybrane | OOS E vychozi |
|---|---|---|---|
| 2024-11-28 | {'stop_buffer_atr': 0.65} | -0.024 | -0.043 |
| 2025-02-26 | {'min_rr': 2.0} | -0.174 | -0.078 |
| 2025-05-27 | {'min_rr': 2.0} | -0.766 | -0.365 |
| 2025-08-25 | {'entry_offset_atr': 0.2} | -0.330 | -0.228 |
| 2025-11-23 | {'max_tp1_atr': 2.5} | -0.094 | -0.169 |
| 2026-02-21 | {'max_tp1_atr': 2.5} | +0.011 | +0.001 |
| 2026-05-22 | {'max_tp1_atr': 2.5} | -0.152 | -0.164 |

| | predikci | vstupu | win | smer 24 h | E [R] | 95% IS | PF | max DD [R] | nezavislych | vzorek |
|---|---|---|---|---|---|---|---|---|---|---|
| OOS walk-forward (vybrane) | 1957 | 873 | 20 % | 49 % | -0.167 | -0.277 .. -0.057 | 0.78 | -154.4 | 460 | DLOUHODOBY BENCHMARK (n>=100) |
| OOS vychozi parametry | 2168 | 1015 | 21 % | 47 % | -0.147 | -0.251 .. -0.044 | 0.81 | -156.1 | 508 | DLOUHODOBY BENCHMARK (n>=100) |

**Promotion gate: HOLD** - OOS rozdil expectancy neni statisticky vyznamny (95% IS obsahuje 0); OOS expectancy challengera neni kladna

## Zaver

Cisla vyse jsou historicky pokus na verejnych cenach s modelovanymi naklady. Rozhoduje jen out-of-sample dukaz a dopredne testovani zamcenych predikci; zadna zmena se neprovadi automaticky.

_vypocet trval 865 s_
