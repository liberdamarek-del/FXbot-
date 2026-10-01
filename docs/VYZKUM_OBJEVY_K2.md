# Vyzkum signalu - kolo 2 - OBJEV (jen 2016-09 .. 2021-12)

_vygenerovano 2026-10-01 03:56 UTC; 36 testu (signal x smer x horizont)_

Obchod = vstup na dennim zaveru ve smeru signalu (trend) nebo proti nemu (proti), vystup po h obchodnich dnech. Jednotky: ATR(D1) na obchod. net = po nakladech (typicky retail spread + 0.4 pip skluz) a swapu (rozdil kratkych sazeb - 1 % p.a. prirazka); gross = jen pohyb mid ceny (nahodny smer = 0). t = prumer / chyba prumeru pres dny bez prekryvu.

Kandidat musi mit net t >= 3.0, kladny net v obou polovinach obdobi a kladny gross.

| signal | smer | h [dny] | dnu | obchodu | win | net | net t | gross | gross t | 1. pol. | 2. pol. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| RATES_SHOCK | proti | 20 | 40 | 138 | 53% | +0.566 | +1.57 | +0.710 | +1.99 | +0.122 | -0.284 |
| REVERSAL_AFTER_SHOCK | trend | 5 | 145 | 368 | 53% | +0.143 | +1.27 | +0.198 | +1.75 | +0.044 | +0.153 |
| MONTH_END_USD | proti | 5 | 35 | 245 | 58% | +0.251 | +1.16 | +0.292 | +1.35 | +0.519 | +0.475 |
| MONTH_END_USD | trend | 20 | 11 | 77 | 58% | +0.837 | +1.05 | +0.999 | +1.26 | - | - |
| COT_EXTREME | trend | 20 | 52 | 166 | 51% | +0.326 | +0.92 | +0.428 | +1.21 | +0.797 | -0.531 |
| COT_EXTREME | trend | 5 | 201 | 648 | 49% | +0.083 | +0.92 | +0.128 | +1.43 | +0.202 | +0.010 |
| REVERSAL_AFTER_SHOCK | proti | 20 | 43 | 116 | 52% | +0.080 | +0.20 | +0.213 | +0.54 | -0.122 | -0.939 |
| REVERSAL_AFTER_SHOCK | proti | 1 | 671 | 1664 | 49% | -0.005 | -0.20 | +0.026 | +1.13 | +0.001 | -0.010 |
| RATES_SHOCK | proti | 5 | 154 | 565 | 49% | -0.025 | -0.26 | +0.027 | +0.27 | -0.076 | -0.051 |
| MONTH_END_USD | proti | 1 | 187 | 1308 | 50% | -0.010 | -0.28 | +0.017 | +0.48 | -0.008 | -0.012 |
| MOM60_CLEAN_TREND | proti | 20 | 57 | 172 | 45% | -0.120 | -0.36 | +0.015 | +0.04 | +0.154 | +0.269 |
| MOM60_CLEAN_TREND | trend | 20 | 57 | 172 | 51% | -0.172 | -0.51 | -0.015 | -0.04 | -0.419 | -0.589 |
| MOM60_CLEAN_TREND | proti | 5 | 220 | 701 | 51% | -0.047 | -0.58 | +0.009 | +0.11 | -0.042 | -0.098 |
| CARRY_CALM | trend | 5 | 115 | 1375 | 50% | -0.036 | -0.64 | -0.012 | -0.22 | +0.034 | -0.054 |
| COT_EXTREME | trend | 1 | 1006 | 3234 | 49% | -0.011 | -0.66 | +0.019 | +1.12 | -0.002 | -0.017 |
| RATES_SHOCK | trend | 5 | 154 | 565 | 48% | -0.073 | -0.75 | -0.027 | -0.27 | -0.018 | -0.055 |
| CARRY_CALM | proti | 20 | 33 | 395 | 48% | -0.118 | -0.77 | +0.145 | +0.94 | -0.225 | -0.098 |
| MOM60_CLEAN_TREND | trend | 5 | 220 | 701 | 46% | -0.063 | -0.78 | -0.009 | -0.11 | -0.059 | -0.022 |
| REVERSAL_AFTER_SHOCK | trend | 20 | 43 | 116 | 46% | -0.345 | -0.88 | -0.213 | -0.54 | -0.128 | +0.667 |
| CARRY_CALM | trend | 20 | 33 | 395 | 48% | -0.162 | -1.04 | -0.145 | -0.94 | -0.030 | -0.223 |
| CARRY_CALM | proti | 5 | 115 | 1375 | 48% | -0.073 | -1.32 | +0.012 | +0.22 | -0.134 | -0.069 |
| MONTH_END_USD | proti | 20 | 11 | 77 | 39% | -1.096 | -1.37 | -0.999 | -1.26 | - | - |
| MONTH_END_USD | trend | 1 | 187 | 1308 | 47% | -0.048 | -1.39 | -0.017 | -0.48 | -0.047 | -0.050 |
| RATES_SHOCK | proti | 1 | 775 | 2732 | 48% | -0.027 | -1.48 | +0.002 | +0.11 | -0.015 | -0.044 |
| CARRY_CALM | trend | 1 | 575 | 6871 | 49% | -0.015 | -1.58 | +0.010 | +1.02 | -0.006 | -0.030 |
| MONTH_END_USD | trend | 5 | 35 | 245 | 40% | -0.351 | -1.62 | -0.292 | -1.35 | -0.615 | -0.590 |
| RATES_SHOCK | trend | 1 | 775 | 2732 | 47% | -0.030 | -1.63 | -0.002 | -0.11 | -0.038 | -0.018 |
| COT_EXTREME | proti | 20 | 52 | 166 | 45% | -0.599 | -1.71 | -0.428 | -1.21 | -1.046 | +0.248 |
| MOM60_CLEAN_TREND | trend | 1 | 1088 | 3472 | 48% | -0.030 | -1.88 | +0.002 | +0.11 | -0.047 | -0.011 |
| MOM60_CLEAN_TREND | proti | 1 | 1088 | 3472 | 47% | -0.034 | -2.10 | -0.002 | -0.11 | -0.011 | -0.058 |
| COT_EXTREME | proti | 5 | 201 | 648 | 48% | -0.189 | -2.12 | -0.128 | -1.43 | -0.300 | -0.126 |
| REVERSAL_AFTER_SHOCK | proti | 5 | 145 | 368 | 43% | -0.248 | -2.19 | -0.198 | -1.75 | -0.145 | -0.266 |
| RATES_SHOCK | trend | 20 | 40 | 138 | 43% | -0.830 | -2.27 | -0.710 | -1.99 | -0.371 | +0.003 |
| REVERSAL_AFTER_SHOCK | trend | 1 | 671 | 1664 | 47% | -0.057 | -2.47 | -0.026 | -1.13 | -0.058 | -0.056 |
| COT_EXTREME | proti | 1 | 1006 | 3234 | 48% | -0.052 | -3.10 | -0.019 | -1.12 | -0.055 | -0.052 |
| CARRY_CALM | proti | 1 | 575 | 6871 | 46% | -0.047 | -4.88 | -0.010 | -1.02 | -0.051 | -0.042 |

**Zamceni kandidati (0):** zadny

Soubor `data/research/candidates_r2.json`, SHA-256 `9e0093da0a77605e2ac743a4bbcf1486ccea548769778fb5c4924f1ce46944a0`. Potvrzeni: `python scripts/research_signals.py confirm --round 2` (jednou, na obdobich EARLY a HOLDOUT).
