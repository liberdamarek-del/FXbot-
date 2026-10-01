# Uspesnost >= 75 % - kolo 2 (vyssi vysledek)

## Shrnuti

**Cil splnen v backtestu:** 331 systemu z 16 848 ma >= 75 % uspesnych obchodu a zisk po nakladech ve vsech
trech obdobich (2014-19, 2020-22, 2023-26). Nasazeny system CH-007 "75+":

**limitni nakup 0.5 ATR pod uzaverkou, kdyz RSI(3) < 15 a cena je nad SMA200 (prodej zrcadlove), volatilita
nad 30. percentilem; TP 0.4 ATR, SL 2.0 ATR, max 5 dni** - 2014-2026: 479 obchodu, **83.3 % uspesnych**,
+0.045 R na obchod (t +2.5), nejhorsi propad -7.7 R, asi 38 obchodu rocne.

Pozor: (1) vysoka uspesnost je dana malym cilem a velkym stop-lossem - zisk na obchod je maly (+0.045 R,
tj. pri riziku 1 % uctu asi +1.7 % rocne); (2) system byl vybran se znalosti vsech obdobi, nezavisle ho
potvrdi az dopredny test (`python fxbot.py signals75 --lock`, automaticky denne, vyhodnoceni `review --all`).

_16848 systemu; vyber jen na 2014-2022 (oba useky >= 75 % a >= 150 obchodu), poradi podle horsiho z obou vysledku; 2023-2026 ukazano jen jednou._

Systemu s >= 75 % v obou usecich 2014-2019 i 2020-2022: **4049**, z toho kladnych v obou: **850**.

| system | 2014-19 uspesnost / E[R] / n | 2020-22 | **2023-26 (test)** |
|---|---|---|---|
| LIMIT 0.25 / %R5<10 / trend SMA200 / vol>30% | TP 0.4 ATR, SL 1.0 ATR, max 5 d | 75.3% / +0.060 / 515 | 76.3% / +0.066 / 384 | 71.4% / +0.012 / 276 |
| LIMIT 0.25 / %R5<10 / trend SMA200 / vol>30% / naklady<=3% ATR | TP 0.4 ATR, SL 1.0 ATR, max 5 d | 75.3% / +0.060 / 515 | 76.3% / +0.066 / 384 | 71.4% / +0.012 / 276 |
| LIMIT 0.25 / %R5<10 / trend SMA200 / vol>30% | TP 0.5 ATR, SL 1.5 ATR, max 5 d | 75.5% / +0.054 / 515 | 76.8% / +0.069 / 384 | 71.7% / +0.013 / 276 |
| LIMIT 0.25 / %R5<10 / trend SMA200 / vol>30% / naklady<=3% ATR | TP 0.5 ATR, SL 1.5 ATR, max 5 d | 75.5% / +0.054 / 515 | 76.8% / +0.069 / 384 | 71.7% / +0.013 / 276 |
| LIMIT 0.25 / %R5<10 / trend SMA200 / vol>30% / naklady<=3% ATR | TP 0.5 ATR, SL 2.0 ATR, max 5 d | 77.7% / +0.053 / 515 | 78.9% / +0.061 / 384 | 72.8% / +0.015 / 276 |
| LIMIT 0.25 / %R5<10 / trend SMA200 / vol>30% | TP 0.5 ATR, SL 2.0 ATR, max 5 d | 77.7% / +0.053 / 515 | 78.9% / +0.061 / 384 | 72.8% / +0.015 / 276 |
| LIMIT 0.5 / %R5<10 / trend SMA200 / vol>30% / naklady<=3% ATR | TP 0.4 ATR, SL 1.5 ATR, max 5 d | 79.9% / +0.042 / 284 | 81.1% / +0.047 / 227 | 75.8% / +0.017 / 157 |
| LIMIT 0.5 / %R5<10 / trend SMA200 / vol>30% | TP 0.4 ATR, SL 1.5 ATR, max 5 d | 79.9% / +0.042 / 284 | 81.1% / +0.047 / 227 | 75.8% / +0.017 / 157 |
| LIMIT 0.5 / RSI2<5 / trend SMA200 / vol libovolna | TP 0.4 ATR, SL 1.5 ATR, max 5 d | 80.8% / +0.041 / 291 | 80.6% / +0.040 / 165 | 78.4% / +0.022 / 162 |
| LIMIT 0.5 / %R5<10 / trend SMA200 / vol>30% / naklady<=3% ATR | TP 0.4 ATR, SL 2.0 ATR, max 5 d | 82.0% / +0.040 / 284 | 83.7% / +0.051 / 227 | 77.1% / +0.014 / 157 |
| LIMIT 0.5 / %R5<10 / trend SMA200 / vol>30% | TP 0.4 ATR, SL 2.0 ATR, max 5 d | 82.0% / +0.040 / 284 | 83.7% / +0.051 / 227 | 77.1% / +0.014 / 157 |
| LIMIT 0.5 / RSI2<5 / trend SMA200 / vol libovolna | TP 0.4 ATR, SL 2.0 ATR, max 5 d | 82.5% / +0.039 / 291 | 84.2% / +0.071 / 165 | 79.6% / +0.002 / 162 |
| LIMIT 0.5 / RSI2<5 / trend SMA200 / vol libovolna / naklady<=3% ATR | TP 0.4 ATR, SL 1.5 ATR, max 5 d | 80.6% / +0.039 / 288 | 80.6% / +0.040 / 165 | 78.4% / +0.022 / 162 |
| LIMIT 0.5 / RSI2<5 / trend SMA200 / vol libovolna / naklady<=3% ATR | TP 0.4 ATR, SL 2.0 ATR, max 5 d | 82.3% / +0.038 / 288 | 84.2% / +0.071 / 165 | 79.6% / +0.002 / 162 |
| LIMIT 0.5 / RSI3<15 / trend SMA200 / vol libovolna | TP 0.4 ATR, SL 1.5 ATR, max 5 d | 80.2% / +0.038 / 410 | 81.3% / +0.051 / 219 | 79.5% / +0.029 / 224 |

## Vyber podle cile: nejvyssi horsi uspesnost (2014-19 / 2020-22), v zisku v obou

| system | 2014-19 | 2020-22 | **2023-26 (test)** | 2014-26 celkem: n / uspesnost / E[R] / t |
|---|---|---|---|---|
| LIMIT 0.5 / RSI3<15 / trend SMA200 / vol>30% | TP 0.25 ATR, SL 3.0 ATR, max 5 d | 88.6% / +0.004 / 202 | 90.6% / +0.033 / 160 | 83.8% / -0.017 / 117 | 479 / 88.1% / +0.008 / +0.7 |
| LIMIT 0.5 / RSI2<10 / trend SMA200 / vol>30% | TP 0.25 ATR, SL 3.0 ATR, max 5 d | 88.7% / +0.008 / 310 | 88.6% / +0.016 / 245 | 83.2% / -0.023 / 179 | 734 / 87.3% / +0.003 / +0.3 |
| LIMIT 0.5 / RSI2<10 / trend SMA200 / vol>30% / naklady<=3% ATR | TP 0.25 ATR, SL 3.0 ATR, max 5 d | 88.6% / +0.008 / 307 | 88.6% / +0.016 / 245 | 83.2% / -0.023 / 179 | 731 / 87.3% / +0.003 / +0.3 |
| LIMIT 0.5 / RSI3<15 / trend SMA200 / vol>30% / naklady<=3% ATR | TP 0.25 ATR, SL 3.0 ATR, max 5 d | 88.4% / +0.003 / 199 | 90.6% / +0.033 / 160 | 83.8% / -0.017 / 117 | 476 / 88.0% / +0.008 / +0.7 |
| LIMIT 0.5 / RSI3<15 / trend SMA200 / vol libovolna | TP 0.25 ATR, SL 3.0 ATR, max 5 d | 88.3% / +0.003 / 410 | 90.4% / +0.032 / 219 | 84.4% / -0.013 / 224 | 853 / 87.8% / +0.006 / +0.7 |
| LIMIT 0.5 / RSI2<10 + IBS<0.3 / trend SMA200 / vol>30% | TP 0.25 ATR, SL 3.0 ATR, max 5 d | 88.3% / +0.004 / 222 | 88.4% / +0.005 / 181 | 82.5% / -0.036 / 120 | 523 / 87.0% / -0.005 / -0.4 |
| LIMIT 0.5 / RSI2<10 + IBS<0.3 / trend SMA200 / vol>30% / naklady<=3% ATR | TP 0.25 ATR, SL 3.0 ATR, max 5 d | 88.2% / +0.004 / 221 | 88.4% / +0.005 / 181 | 82.5% / -0.036 / 120 | 522 / 87.0% / -0.005 / -0.4 |
| LIMIT 0.5 / RSI3<15 / trend SMA200 / vol libovolna / naklady<=3% ATR | TP 0.25 ATR, SL 3.0 ATR, max 5 d | 88.2% / +0.003 / 407 | 90.4% / +0.032 / 219 | 84.4% / -0.013 / 224 | 850 / 87.8% / +0.006 / +0.7 |
| LIMIT 0.5 / RSI3<15 / trend SMA200 / vol>30% | TP 0.25 ATR, SL 2.0 ATR, max 5 d | 88.1% / +0.014 / 202 | 90.6% / +0.059 / 160 | 83.8% / -0.023 / 117 | 479 / 87.9% / +0.020 / +1.3 |
| LIMIT 0.5 / RSI2<5 / trend SMA200 / vol libovolna | TP 0.25 ATR, SL 3.0 ATR, max 5 d | 88.0% / +0.002 / 291 | 89.7% / +0.033 / 165 | 84.6% / -0.009 / 162 | 618 / 87.5% / +0.008 / +0.7 |

**Finalni system kola 2 (podle cile):** LIMIT 0.5 / RSI3<15 / trend SMA200 / vol>30% | TP 0.25 ATR, SL 3.0 ATR, max 5 d

| rok | obchodu | uspesnost | E [R] |
|---|---|---|---|
| 2014 | 16 | 100.0% | +0.079 |
| 2015 | 57 | 80.7% | -0.068 |
| 2016 | 42 | 97.6% | +0.061 |
| 2017 | 18 | 100.0% | +0.081 |
| 2018 | 45 | 86.7% | -0.010 |
| 2019 | 24 | 79.2% | -0.008 |
| 2020 | 73 | 90.4% | +0.011 |
| 2021 | 28 | 89.3% | +0.027 |
| 2022 | 59 | 91.5% | +0.063 |
| 2023 | 8 | 100.0% | +0.081 |
| 2024 | 48 | 72.9% | -0.100 |
| 2025 | 30 | 83.3% | -0.009 |
| 2026 | 31 | 96.8% | +0.077 |

## Systemy s >= 75 % a ziskem ve VSECH trech obdobich (pouziva i 2023-26 - potvrdi jen dopredny test)

Pocet: **331** z 16848.

| system | 2014-26: obchodu / uspesnost / E[R] / t | nejhorsi propad [R] | obchodu za rok |
|---|---|---|---|
| LIMIT 0.5 / RSI3<15 / trend SMA200 / vol>30% | TP 0.4 ATR, SL 1.5 ATR, max 5 d | 479 / 81.0% / +0.046 / +1.9 | -12.0 | 38 |
| LIMIT 0.5 / RSI3<15 / trend SMA200 / vol>30% | TP 0.4 ATR, SL 2.0 ATR, max 5 d | 479 / 83.3% / +0.045 / +2.5 | -7.7 | 38 |
| LIMIT 0.5 / RSI3<15 / trend SMA200 / vol>30% / naklady<=3% ATR | TP 0.4 ATR, SL 1.5 ATR, max 5 d | 476 / 80.9% / +0.045 / +1.8 | -12.0 | 37 |
| LIMIT 0.5 / RSI3<15 / trend SMA200 / vol>30% | TP 0.5 ATR, SL 2.0 ATR, max 5 d | 479 / 78.1% / +0.044 / +2.0 | -8.9 | 38 |
| LIMIT 0.5 / RSI3<15 / trend SMA200 / vol>30% / naklady<=3% ATR | TP 0.4 ATR, SL 2.0 ATR, max 5 d | 476 / 83.2% / +0.044 / +2.4 | -7.7 | 37 |
| LIMIT 0.5 / RSI3<15 / trend SMA200 / vol>30% / naklady<=3% ATR | TP 0.5 ATR, SL 2.0 ATR, max 5 d | 476 / 77.9% / +0.043 / +2.0 | -8.9 | 37 |
| LIMIT 0.5 / %R14<10 / trend SMA200 / vol>30% / naklady<=3% ATR | TP 0.5 ATR, SL 2.0 ATR, max 5 d | 574 / 77.7% / +0.042 / +1.8 | -10.1 | 45 |
| LIMIT 0.5 / %R14<10 / trend SMA200 / vol>30% | TP 0.5 ATR, SL 2.0 ATR, max 5 d | 574 / 77.7% / +0.042 / +1.8 | -10.1 | 45 |
| MARKET / %R9<5 / trend SMA100 / vol>30% / naklady<=3% ATR | TP 0.4 ATR, SL 1.5 ATR, max 5 d | 641 / 79.1% / +0.041 / +1.9 | -9.7 | 50 |
| MARKET / %R9<5 / trend SMA100 / vol>30% | TP 0.4 ATR, SL 1.5 ATR, max 5 d | 641 / 79.1% / +0.041 / +1.9 | -9.7 | 50 |

t testu (tydenni shluky): -0.6; _vypocet 27 s_
