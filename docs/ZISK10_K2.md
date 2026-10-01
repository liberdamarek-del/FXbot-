# Zisk na obchod >= 10 % marze - kolo 2 (25 paru, 2012-2026, hodinova cesta)

_213840 systemu; cil kazdeho obchodu >= 0.333 % ceny; vysledky v % marze (paka 1:30) po spreadu, skluzu a swapu; vyber 2012-2022, test 2023-2026._

| vstup | systemu s dost obchody | prumer v testu | podil kladnych v testu |
|---|---|---|---|
| MARKET | 56835 | +0.9 % | 54% |
| LIMIT 0.5 | 51285 | +1.6 % | 59% |
| LIMIT 1.0 | 42900 | +2.2 % | 62% |

## A) Uspesnost >= 75 % a prumer >= 10 % marze v obou vyberovych obdobich

Splnuje: **14** systemu.

V testu 2023-26: zisk > 0 u 12 z 14 (s obchody), >= 10 % marze u 1, a k tomu uspesnost >= 75 % u 0.

| system | 2012-18 n / usp. / zisk | 2019-22 | **2023-26 (test)** |
|---|---|---|---|
| LIMIT 0.5 / D pod BB20(2) / SMA50 / carry souhlasi / denne | TP 1.5 ATR, SL 4 ATR, max 20 d | 65 / 75% / +20.6 % | 25 / 88% / +20.4 % | 20 / 70% / +9.3 % |
| LIMIT 0.5 / D pod BB20(2) / SMA50 / carry souhlasi / denne | TP 1.5 ATR, SL 3 ATR, max 20 d | 65 / 75% / +20.8 % | 25 / 84% / +19.0 % | 20 / 70% / +11.4 % |
| LIMIT 0.5 / D pod BB20(2) / SMA50 / carry souhlasi / denne | TP 1 ATR, SL 4 ATR, max 20 d | 65 / 80% / +13.6 % | 25 / 88% / +12.3 % | 20 / 75% / +4.0 % |
| MARKET / D pod BB20(2) / SMA50 / carry souhlasi / denne | TP 1 ATR, SL 3 ATR, max 20 d | 110 / 75% / +11.0 % | 68 / 91% / +16.3 % | 34 / 76% / +6.8 % |
| LIMIT 0.5 / D pod BB20(2) / SMA50 / carry souhlasi / denne | TP 1 ATR, SL 3 ATR, max 20 d | 65 / 80% / +14.0 % | 25 / 84% / +10.9 % | 20 / 75% / +6.0 % |
| MARKET / D RSI2<5 / tydenni SMA40 / sazby se rozchazeji / konec tydne | TP 0.75 ATR, SL 3 ATR, max 20 d | 36 / 89% / +10.8 % | 53 / 94% / +16.8 % | 32 / 88% / +5.7 % |
| LIMIT 0.5 / D RSI2<5 / tydenni SMA40 / carry >= 2 % / denne | TP 1 ATR, SL 3 ATR, max 20 d | 89 / 79% / +10.5 % | 28 / 86% / +15.5 % | 43 / 67% / -2.3 % |
| MARKET / D RSI2<5 / bez trendu / sazby se rozchazeji / konec tydne | TP 0.75 ATR, SL 3 ATR, max 20 d | 86 / 90% / +10.5 % | 114 / 89% / +11.9 % | 88 / 89% / +9.5 % |
| MARKET / D RSI2<5 / tydenni SMA40 / sazby se rozchazeji / konec tydne | TP 0.75 ATR, SL 3 ATR, max 10 d | 36 / 78% / +10.5 % | 53 / 89% / +13.5 % | 32 / 81% / +5.7 % |
| MARKET / D pod BB20(2) / SMA50 / carry souhlasi / denne | TP 1 ATR, SL 4 ATR, max 20 d | 110 / 75% / +10.4 % | 68 / 91% / +14.8 % | 34 / 76% / +4.8 % |
| LIMIT 0.5 / D RSI2<5 / SMA200 / carry >= 2 % / denne | TP 1 ATR, SL 3 ATR, max 20 d | 89 / 79% / +10.4 % | 29 / 83% / +13.3 % | 43 / 67% / -2.3 % |
| MARKET / D RSI2<5 / tydenni SMA40 / sazby se rozchazeji / konec tydne | TP 0.75 ATR, SL 1.5 ATR, max 20 d | 36 / 81% / +10.3 % | 53 / 81% / +10.2 % | 32 / 78% / +4.1 % |
| MARKET / D RSI2<5 / bez trendu / sazby se rozchazeji / konec tydne | TP 0.75 ATR, SL 3 ATR, max 10 d | 86 / 84% / +10.1 % | 114 / 84% / +11.2 % | 88 / 77% / +6.4 % |
| MARKET / D RSI2<5 / tydenni SMA40 / sazby se rozchazeji / konec tydne | TP 0.75 ATR, SL 4 ATR, max 10 d | 36 / 78% / +10.0 % | 53 / 89% / +12.8 % | 32 / 81% / +5.8 % |

## B) Prumer >= 10 % marze v obou obdobich - serazeno podle horsi uspesnosti

Splnuje: **123** systemu.

V testu 2023-26: zisk > 0 u 91 z 123 (s obchody), >= 10 % marze u 25, a k tomu uspesnost >= 75 % u 4.

| system | 2012-18 n / usp. / zisk | 2019-22 | **2023-26 (test)** |
|---|---|---|---|
| MARKET / D RSI2<5 / tydenni SMA40 / sazby se rozchazeji / konec tydne | TP 0.75 ATR, SL 3 ATR, max 20 d | 36 / 89% / +10.8 % | 53 / 94% / +16.8 % | 32 / 88% / +5.7 % |
| MARKET / D RSI2<5 / bez trendu / sazby se rozchazeji / konec tydne | TP 0.75 ATR, SL 3 ATR, max 20 d | 86 / 90% / +10.5 % | 114 / 89% / +11.9 % | 88 / 89% / +9.5 % |
| MARKET / D RSI2<5 / bez trendu / sazby se rozchazeji / konec tydne | TP 0.75 ATR, SL 3 ATR, max 10 d | 86 / 84% / +10.1 % | 114 / 84% / +11.2 % | 88 / 77% / +6.4 % |
| MARKET / D RSI2<5 / tydenni SMA40 / sazby se rozchazeji / konec tydne | TP 0.75 ATR, SL 1.5 ATR, max 20 d | 36 / 81% / +10.3 % | 53 / 81% / +10.2 % | 32 / 78% / +4.1 % |
| LIMIT 0.5 / D pod BB20(2) / SMA50 / carry souhlasi / denne | TP 1 ATR, SL 3 ATR, max 20 d | 65 / 80% / +14.0 % | 25 / 84% / +10.9 % | 20 / 75% / +6.0 % |
| LIMIT 0.5 / D pod BB20(2) / SMA50 / carry souhlasi / denne | TP 1 ATR, SL 4 ATR, max 20 d | 65 / 80% / +13.6 % | 25 / 88% / +12.3 % | 20 / 75% / +4.0 % |
| LIMIT 0.5 / D RSI2<5 / SMA200 / carry >= 2 % / denne | TP 1 ATR, SL 3 ATR, max 20 d | 89 / 79% / +10.4 % | 29 / 83% / +13.3 % | 43 / 67% / -2.3 % |
| LIMIT 0.5 / D RSI2<5 / tydenni SMA40 / carry >= 2 % / denne | TP 1 ATR, SL 3 ATR, max 20 d | 89 / 79% / +10.5 % | 28 / 86% / +15.5 % | 43 / 67% / -2.3 % |
| MARKET / D RSI2<5 / tydenni SMA40 / sazby se rozchazeji / konec tydne | TP 0.75 ATR, SL 3 ATR, max 10 d | 36 / 78% / +10.5 % | 53 / 89% / +13.5 % | 32 / 81% / +5.7 % |
| MARKET / D RSI2<5 / tydenni SMA40 / sazby se rozchazeji / konec tydne | TP 0.75 ATR, SL 4 ATR, max 10 d | 36 / 78% / +10.0 % | 53 / 89% / +12.8 % | 32 / 81% / +5.8 % |
| MARKET / D pod BB20(2) / SMA50 / carry souhlasi / denne | TP 1 ATR, SL 3 ATR, max 20 d | 110 / 75% / +11.0 % | 68 / 91% / +16.3 % | 34 / 76% / +6.8 % |
| MARKET / D pod BB20(2) / SMA50 / carry souhlasi / denne | TP 1 ATR, SL 4 ATR, max 20 d | 110 / 75% / +10.4 % | 68 / 91% / +14.8 % | 34 / 76% / +4.8 % |
| LIMIT 0.5 / D pod BB20(2) / SMA50 / carry souhlasi / denne | TP 1.5 ATR, SL 3 ATR, max 20 d | 65 / 75% / +20.8 % | 25 / 84% / +19.0 % | 20 / 70% / +11.4 % |
| LIMIT 0.5 / D pod BB20(2) / SMA50 / carry souhlasi / denne | TP 1.5 ATR, SL 4 ATR, max 20 d | 65 / 75% / +20.6 % | 25 / 88% / +20.4 % | 20 / 70% / +9.3 % |
| LIMIT 1.0 / D %R14<10 / SMA50 / carry souhlasi / konec tydne | TP 1.5 ATR, SL 3 ATR, max 10 d | 37 / 78% / +15.2 % | 21 / 71% / +10.7 % | 11 / 55% / +6.0 % |
| LIMIT 1.0 / D %R14<10 / SMA50 / carry souhlasi / konec tydne | TP 1.5 ATR, SL 4 ATR, max 10 d | 37 / 81% / +17.5 % | 21 / 71% / +11.3 % | 11 / 55% / +6.0 % |
| LIMIT 1.0 / D %R14<10 / SMA50 / carry souhlasi / konec tydne | TP 2 ATR, SL 3 ATR, max 10 d | 37 / 76% / +15.9 % | 21 / 71% / +16.8 % | 11 / 55% / +10.0 % |
| LIMIT 1.0 / D %R14<10 / SMA50 / carry souhlasi / konec tydne | TP 2 ATR, SL 4 ATR, max 10 d | 37 / 78% / +18.5 % | 21 / 71% / +17.4 % | 11 / 55% / +10.0 % |
| LIMIT 1.0 / D %R14<10 / SMA50 / carry souhlasi / konec tydne | TP 2 ATR, SL 4 ATR, max 20 d | 37 / 73% / +21.7 % | 21 / 71% / +15.8 % | 11 / 55% / +3.1 % |
| LIMIT 1.0 / D %R14<10 / SMA50 / carry souhlasi / konec tydne | TP 3 ATR, SL 3 ATR, max 10 d | 37 / 73% / +16.3 % | 21 / 71% / +24.8 % | 11 / 55% / +8.1 % |

## C) Uspesnost >= 75 % a zisk v obou obdobich - serazeno podle horsiho prumeru

Splnuje: **4931** systemu.

V testu 2023-26: zisk > 0 u 3104 z 4931 (s obchody), >= 10 % marze u 128, a k tomu uspesnost >= 75 % u 127.

| system | 2012-18 n / usp. / zisk | 2019-22 | **2023-26 (test)** |
|---|---|---|---|
| LIMIT 0.5 / D pod BB20(2) / SMA50 / carry souhlasi / denne | TP 1.5 ATR, SL 4 ATR, max 20 d | 65 / 75% / +20.6 % | 25 / 88% / +20.4 % | 20 / 70% / +9.3 % |
| LIMIT 0.5 / D pod BB20(2) / SMA50 / carry souhlasi / denne | TP 1.5 ATR, SL 3 ATR, max 20 d | 65 / 75% / +20.8 % | 25 / 84% / +19.0 % | 20 / 70% / +11.4 % |
| LIMIT 0.5 / D pod BB20(2) / SMA50 / carry souhlasi / denne | TP 1 ATR, SL 4 ATR, max 20 d | 65 / 80% / +13.6 % | 25 / 88% / +12.3 % | 20 / 75% / +4.0 % |
| MARKET / D pod BB20(2) / SMA50 / carry souhlasi / denne | TP 1 ATR, SL 3 ATR, max 20 d | 110 / 75% / +11.0 % | 68 / 91% / +16.3 % | 34 / 76% / +6.8 % |
| LIMIT 0.5 / D pod BB20(2) / SMA50 / carry souhlasi / denne | TP 1 ATR, SL 3 ATR, max 20 d | 65 / 80% / +14.0 % | 25 / 84% / +10.9 % | 20 / 75% / +6.0 % |
| MARKET / D RSI2<5 / tydenni SMA40 / sazby se rozchazeji / konec tydne | TP 0.75 ATR, SL 3 ATR, max 20 d | 36 / 89% / +10.8 % | 53 / 94% / +16.8 % | 32 / 88% / +5.7 % |
| LIMIT 0.5 / D RSI2<5 / tydenni SMA40 / carry >= 2 % / denne | TP 1 ATR, SL 3 ATR, max 20 d | 89 / 79% / +10.5 % | 28 / 86% / +15.5 % | 43 / 67% / -2.3 % |
| MARKET / D RSI2<5 / bez trendu / sazby se rozchazeji / konec tydne | TP 0.75 ATR, SL 3 ATR, max 20 d | 86 / 90% / +10.5 % | 114 / 89% / +11.9 % | 88 / 89% / +9.5 % |
| MARKET / D RSI2<5 / tydenni SMA40 / sazby se rozchazeji / konec tydne | TP 0.75 ATR, SL 3 ATR, max 10 d | 36 / 78% / +10.5 % | 53 / 89% / +13.5 % | 32 / 81% / +5.7 % |
| MARKET / D pod BB20(2) / SMA50 / carry souhlasi / denne | TP 1 ATR, SL 4 ATR, max 20 d | 110 / 75% / +10.4 % | 68 / 91% / +14.8 % | 34 / 76% / +4.8 % |
| LIMIT 0.5 / D RSI2<5 / SMA200 / carry >= 2 % / denne | TP 1 ATR, SL 3 ATR, max 20 d | 89 / 79% / +10.4 % | 29 / 83% / +13.3 % | 43 / 67% / -2.3 % |
| MARKET / D RSI2<5 / tydenni SMA40 / sazby se rozchazeji / konec tydne | TP 0.75 ATR, SL 1.5 ATR, max 20 d | 36 / 81% / +10.3 % | 53 / 81% / +10.2 % | 32 / 78% / +4.1 % |
| MARKET / D RSI2<5 / bez trendu / sazby se rozchazeji / konec tydne | TP 0.75 ATR, SL 3 ATR, max 10 d | 86 / 84% / +10.1 % | 114 / 84% / +11.2 % | 88 / 77% / +6.4 % |
| MARKET / D RSI2<5 / tydenni SMA40 / sazby se rozchazeji / konec tydne | TP 0.75 ATR, SL 4 ATR, max 10 d | 36 / 78% / +10.0 % | 53 / 89% / +12.8 % | 32 / 81% / +5.8 % |
| LIMIT 0.5 / D RSI2<5 / tydenni SMA40 / carry >= 2 % / denne | TP 1 ATR, SL 4 ATR, max 20 d | 89 / 80% / +10.0 % | 28 / 86% / +12.5 % | 43 / 70% / -2.6 % |
| LIMIT 0.5 / D RSI2<5 / SMA200 / carry >= 2 % / denne | TP 1 ATR, SL 4 ATR, max 20 d | 89 / 80% / +9.8 % | 29 / 83% / +9.8 % | 43 / 70% / -2.6 % |
| MARKET / D RSI2<5 / tydenni SMA40 / sazby se rozchazeji / konec tydne | TP 0.75 ATR, SL 2 ATR, max 20 d | 36 / 83% / +9.6 % | 53 / 91% / +13.6 % | 32 / 84% / +4.4 % |
| MARKET / D RSI2<5 / bez trendu / sazby se rozchazeji / konec tydne | TP 0.75 ATR, SL 2 ATR, max 20 d | 86 / 85% / +9.6 % | 114 / 87% / +11.5 % | 88 / 84% / +7.6 % |
| LIMIT 1.0 / D %R14<10 / bez trendu / sazby se rozchazeji / denne | TP 0.75 ATR, SL 4 ATR, max 20 d | 135 / 87% / +9.4 % | 140 / 90% / +10.6 % | 118 / 90% / +11.3 % |
| LIMIT 1.0 / D pod SMA5 o 1.5 ATR / SMA200 / denne | TP 0.75 ATR, SL 1.5 ATR, max 10 d | 54 / 78% / +9.3 % | 38 / 76% / +9.5 % | 32 / 75% / +6.5 % |

_vypocet 11 s_
