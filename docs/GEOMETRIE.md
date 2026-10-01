# Geometrie obchodu: vstup, SL, TP, doba drzeni

_540 kombinaci; vyber na 2016-09 .. 2021-12 (FXCM), kontrola na 2022-01 .. 2026-09 (FXCM + Dukascopy). R = zisk / riziko do SL po nakladech. Uspesny = obchod se ziskem. edge = o kolik R na rozhodnuti je smer modelu lepsi nez opacny smer / 2 (nahodny smer = 0)._

## 10 nejlepsich nastaveni podle obdobi vyberu - a co udelala potom

| | | | | **2016-2021 (vyber)** | | | | **2022-2026 (kontrola)** | | | |
| vstup | SL [ATR H4] | TP [ATR H4] | drzeni | obchodu | uspesnych | E [R/obchod] | edge smeru vs nahoda (t) | obchodu | uspesnych | E [R/obchod] | edge smeru vs nahoda (t) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| MARKET | 3.0 | 0.5 | 120 h | 7920 | 83% | -0.019 | -0.002 (-0.2) | 6468 | 83% | -0.021 | +0.003 (+0.4) |
| MARKET | 3.0 | 0.5 | 72 h | 7920 | 80% | -0.020 | -0.002 (-0.3) | 6468 | 79% | -0.024 | +0.002 (+0.3) |
| LIMIT 0.25 | 3.0 | 0.5 | 24 h | 6680 | 70% | -0.020 | -0.001 (-0.3) | 5421 | 70% | -0.026 | +0.001 (+0.2) |
| LIMIT 0.5 | 3.0 | 0.5 | 120 h | 5578 | 83% | -0.021 | -0.007 (-1.4) | 4523 | 82% | -0.022 | +0.003 (+0.5) |
| LIMIT 0.25 | 3.0 | 0.5 | 120 h | 6680 | 83% | -0.022 | -0.004 (-0.7) | 5421 | 83% | -0.018 | +0.003 (+0.5) |
| MARKET | 3.0 | 0.5 | 24 h | 7920 | 72% | -0.022 | -0.002 (-0.4) | 6468 | 70% | -0.025 | +0.002 (+0.3) |
| LIMIT 0.5 | 3.0 | 0.5 | 24 h | 5578 | 69% | -0.022 | -0.004 (-1.0) | 4523 | 69% | -0.025 | +0.002 (+0.6) |
| MARKET | 2.0 | 0.5 | 120 h | 7920 | 79% | -0.023 | +0.002 (+0.2) | 6468 | 78% | -0.032 | +0.002 (+0.2) |
| LIMIT 0.25 | 3.0 | 0.5 | 72 h | 6680 | 79% | -0.023 | -0.004 (-0.8) | 5421 | 79% | -0.022 | +0.003 (+0.5) |
| MARKET | 2.0 | 0.5 | 72 h | 7920 | 77% | -0.023 | +0.003 (+0.3) | 6468 | 76% | -0.034 | +0.001 (+0.1) |

## Uspesnost vs. vysledek (vstup MARKET, drzeni 72 h, 2016-2021)

Ukazuje, ze procento uspesnych obchodu urcuje hlavne pomer SL/TP, ne kvalita predikce.

| SL \ TP | TP 0.5 | TP 1.0 | TP 1.5 | TP 2.0 | TP 3.0 | TP 4.0 |
|---|---|---|---|---|---|---|
| SL 0.5 | 48% / -0.09R | 32% / -0.10R | 24% / -0.10R | 21% / -0.11R | 18% / -0.12R | 17% / -0.12R |
| SL 1.0 | 65% / -0.04R | 48% / -0.06R | 40% / -0.06R | 35% / -0.07R | 31% / -0.09R | 30% / -0.10R |
| SL 1.5 | 73% / -0.03R | 57% / -0.04R | 48% / -0.05R | 43% / -0.06R | 39% / -0.07R | 38% / -0.08R |
| SL 2.0 | 77% / -0.02R | 62% / -0.03R | 53% / -0.04R | 48% / -0.05R | 44% / -0.06R | 42% / -0.06R |
| SL 3.0 | 80% / -0.02R | 65% / -0.03R | 56% / -0.04R | 51% / -0.04R | 47% / -0.05R | 46% / -0.05R |

## Technika samotna vs. technika + fundamenty (prumer pres vsech 270 nastaveni)

| smer z | edge 2016-2021 | edge 2022-2026 |
|---|---|---|
| model (technika + fundamentalni veto) | -0.0134 R | -0.0020 R |
| jen technika | -0.0026 R | -0.0126 R |

Kladny vysledek na obdobi vyberu: 0 z 270 nastaveni; z nich kladny i na kontrole: 0.
Nejlepsi nastaveni z vyberu: MARKET, SL 3.0, TP 0.5, 120 h -> kontrola E -0.021 R, uspesnost 83%.
