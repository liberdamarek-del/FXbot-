# Relativní výnosová křivka a 12 párů (výzkum 2026-10-11)

_Autonomní průzkum. Hypotéza z literatury: Chen & Tsang (2013, Review of Economics and Statistics). Data: OECD dlouhodobé výnosy (FRED IRLTLT01, měsíčně) a 3měsíční sazby modelu, zpoždění 2 měsíce jako v modelu; ceny FXCM. 2012–18 = výběr, 2019–26 = test. Jen informace – do modelu jen přes bránu._

## A) Předpověď na další 1 a 3 měsíce (všech 12 párů dohromady, měsíčně)

Spearmanova korelace signálu s budoucím pohybem páru (kladná = signál ukazuje směr; |0,05| je u tohoto počtu měsíců na hranici náhody). `slope` = sklon křivky základní měny minus kótovací (10 let − 3 měsíce), `long` = rozdíl 10letých výnosů, `short` = rozdíl 3měsíčních sazeb (carry), `d_` = změna za 3 měsíce (`d_short` je to, co model už používá).

| signál | období | měsíců | korelace 1 m | korelace 3 m | t navíc k d_short (1 m) |
|---|---|---|---|---|---|
| slope | 2012-18 | 1008 | +0.072 | +0.105 | +2.52 |
| slope | 2019-26 | 1068 | +0.023 | +0.064 | +0.93 |
| d_slope | 2012-18 | 1008 | -0.002 | +0.027 | -0.00 |
| d_slope | 2019-26 | 1068 | -0.017 | +0.020 | +0.17 |
| long | 2012-18 | 1008 | +0.023 | +0.034 | +0.10 |
| long | 2019-26 | 1068 | +0.058 | +0.079 | +1.18 |
| d_long | 2012-18 | 1008 | +0.023 | +0.078 | -0.00 |
| d_long | 2019-26 | 1068 | -0.041 | +0.003 | +0.17 |
| short | 2012-18 | 1008 | -0.046 | -0.068 | -1.73 |
| short | 2019-26 | 1068 | +0.037 | +0.035 | +0.65 |
| d_short | 2012-18 | 1008 | -0.004 | +0.015 | – |
| d_short | 2019-26 | 1068 | -0.028 | -0.003 | – |

## B) Obchody šampionů: pomáhá shoda s relativní křivkou?

Obchod „souhlasí“, když signál ukazuje směrem obchodu (pro `slope` podle Chen & Tsang obráceně: strmější křivka základní měny = slabší základní měna). Výsledek = pohyb ceny v % ve směru obchodu po nákladech; úspěšnost = podíl ziskových obchodů.

| profil | signál | období | souhlasí: obchodů / úspěšnost / průměr % | nesouhlasí: obchodů / úspěšnost / průměr % |
|---|---|---|---|---|
| champion_12 | slope | 2012-18 | 89 / 87 % / +0.18 | 135 / 84 % / +0.20 |
| champion_12 | slope | 2019-22 | 84 / 88 % / +0.28 | 87 / 91 % / +0.26 |
| champion_12 | slope | 2023-26 | 37 / 95 % / +0.42 | 69 / 80 % / -0.04 |
| champion_12 | d_slope | 2012-18 | 140 / 86 % / +0.23 | 84 / 83 % / +0.13 |
| champion_12 | d_slope | 2019-22 | 113 / 90 % / +0.27 | 58 / 88 % / +0.27 |
| champion_12 | d_slope | 2023-26 | 71 / 89 % / +0.23 | 35 / 77 % / -0.10 |
| champion_12 | d_long | 2012-18 | 122 / 87 % / +0.25 | 102 / 83 % / +0.12 |
| champion_12 | d_long | 2019-22 | 115 / 90 % / +0.30 | 56 / 88 % / +0.21 |
| champion_12 | d_long | 2023-26 | 76 / 84 % / +0.09 | 30 / 87 % / +0.20 |
| champion_12 | long | 2012-18 | 132 / 86 % / +0.27 | 92 / 84 % / +0.08 |
| champion_12 | long | 2019-22 | 88 / 90 % / +0.31 | 83 / 89 % / +0.23 |
| champion_12 | long | 2023-26 | 46 / 85 % / +0.19 | 60 / 85 % / +0.07 |
| champion_12_mesicne | slope | 2012-18 | 88 / 90 % / +0.22 | 136 / 87 % / +0.23 |
| champion_12_mesicne | slope | 2019-22 | 84 / 88 % / +0.22 | 87 / 92 % / +0.28 |
| champion_12_mesicne | slope | 2023-26 | 37 / 95 % / +0.51 | 69 / 81 % / -0.01 |
| champion_12_mesicne | d_slope | 2012-18 | 141 / 89 % / +0.30 | 83 / 86 % / +0.10 |
| champion_12_mesicne | d_slope | 2019-22 | 113 / 91 % / +0.25 | 58 / 88 % / +0.25 |
| champion_12_mesicne | d_slope | 2023-26 | 71 / 89 % / +0.25 | 35 / 80 % / +0.02 |
| champion_12_mesicne | d_long | 2012-18 | 122 / 89 % / +0.22 | 102 / 87 % / +0.23 |
| champion_12_mesicne | d_long | 2019-22 | 115 / 91 % / +0.30 | 56 / 88 % / +0.15 |
| champion_12_mesicne | d_long | 2023-26 | 76 / 86 % / +0.16 | 30 / 87 % / +0.20 |
| champion_12_mesicne | long | 2012-18 | 133 / 88 % / +0.28 | 91 / 88 % / +0.16 |
| champion_12_mesicne | long | 2019-22 | 88 / 91 % / +0.34 | 83 / 89 % / +0.15 |
| champion_12_mesicne | long | 2023-26 | 46 / 87 % / +0.22 | 60 / 85 % / +0.13 |
