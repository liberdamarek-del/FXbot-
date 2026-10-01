# Dve skupiny trhu: plati pravidlo i tam, kde nebylo hledano?

_G1 = 25 paru FXCM (tady bylo nalezeno F1), G2 = 16 novych paru z HistData (NOK, SEK, MXN, ZAR, PLN, HUF, CZK, CHF/JPY, EUR/CAD, GBP/AUD). Zisk v % marze na obchod po nakladech a swapu._

## 1. Prenos: systemy vybrane na G1 (2012-2022, n >= 100, zisk >= 5 %, t >= 2) na novych trzich G2

| vstup | vybranych | prumer na G2 | podil kladnych na G2 | vsechny systemy: prumer na G2 | podil kladnych |
|---|---|---|---|---|---|
| MARKET | 911 | -0.5 % | 46% | -2.0 % | 21% |
| LIMIT 0.5 | 823 | +0.2 % | 52% | +0.3 % | 51% |
| LIMIT 1.0 | 934 | +0.5 % | 56% | -0.2 % | 42% |

## 2. Dvojite robustni: kladne s t >= 2.0 na G1 i G2 v 2012-2022 (n >= 60 v kazde)

Splnuje **1211** systemu. V testu 2023-2026: kladne na G1 u 782 z 1211, na G2 u 1084, na obou u 722.

| system | G1 2012-22 n / usp. / zisk / t | G2 2012-22 | **G1 2023-26** | **G2 2023-26** |
|---|---|---|---|---|
| LIMIT 0.5 / D 3 dny dolu / bez trendu / denne | TP 0.75 ATR, SL 4 ATR, max 20 d | 6839 / 81% / +1.9 % / 3.8 | 4369 / 82% / +3.1 % / 4.6 | 1588 / 81% / +2.3 % / 2.9 | 1183 / 83% / +5.2 % / 4.9 |
| LIMIT 0.5 / D RSI2<5 / bez trendu / sazby se rozchazeji / denne | TP 1 ATR, SL 4 ATR, max 10 d | 436 / 73% / +7.6 % / 3.9 | 453 / 76% / +8.6 % / 3.7 | 196 / 69% / +1.9 % / 0.8 | 158 / 69% / +8.5 % / 3.6 |
| LIMIT 0.5 / D RSI2<5 / bez trendu / sazby se rozchazeji / denne | TP 1 ATR, SL 4 ATR, max 20 d | 436 / 79% / +7.9 % / 3.6 | 453 / 78% / +8.8 % / 3.6 | 196 / 75% / +4.5 % / 1.8 | 158 / 78% / +7.3 % / 2.3 |
| LIMIT 0.5 / D %R14<10 / bez trendu / sazby se rozchazeji / denne | TP 0.75 ATR, SL 4 ATR, max 20 d | 721 / 84% / +6.1 % / 4.1 | 626 / 83% / +6.6 % / 3.6 | 304 / 85% / +6.9 % / 4.1 | 260 / 79% / +3.0 % / 1.2 |
| LIMIT 0.5 / D RSI2<5 / bez trendu / sazby se rozchazeji / denne | TP 0.75 ATR, SL 4 ATR, max 10 d | 431 / 79% / +6.2 % / 3.5 | 440 / 83% / +8.6 % / 4.2 | 191 / 76% / +2.0 % / 0.9 | 153 / 73% / +6.3 % / 3.0 |
| LIMIT 0.5 / D RSI2<5 / bez trendu / sazby se rozchazeji / denne | TP 1 ATR, SL 3 ATR, max 10 d | 436 / 72% / +6.8 % / 3.5 | 453 / 75% / +8.1 % / 3.6 | 196 / 69% / +2.4 % / 1.0 | 158 / 68% / +7.3 % / 3.0 |
| LIMIT 0.5 / D 3 dny dolu / bez trendu / konec tydne | TP 0.75 ATR, SL 4 ATR, max 20 d | 2060 / 83% / +3.2 % / 3.6 | 1266 / 83% / +4.3 % / 3.5 | 476 / 80% / +1.8 % / 1.2 | 351 / 81% / +3.9 % / 1.9 |
| MARKET / D %R14<10 / SMA200 / konec tydne | TP 15 %, SL 22 % marze, max 20 d | 832 / 67% / +2.1 % / 3.5 | 572 / 69% / +2.5 % / 3.5 | 218 / 62% / +0.1 % / 0.1 | 120 / 66% / +1.7 % / 1.0 |
| LIMIT 0.5 / D RSI2<5 / bez trendu / sazby se rozchazeji / konec tydne | TP 0.75 ATR, SL 4 ATR, max 5 d | 131 / 79% / +8.3 % / 3.5 | 132 / 80% / +11.9 % / 4.4 | 51 / 75% / +5.8 % / 1.6 | 43 / 65% / +6.7 % / 2.2 |
| MARKET / D %R14<10 / SMA200 / konec tydne | TP 15 %, SL 22 % marze, max 10 d | 832 / 66% / +2.1 % / 3.5 | 572 / 68% / +2.5 % / 3.5 | 218 / 62% / +0.0 % / 0.0 | 120 / 65% / +1.7 % / 1.1 |
| LIMIT 0.5 / D RSI2<5 / bez trendu / sazby se rozchazeji / denne | TP 0.75 ATR, SL 4 ATR, max 5 d | 431 / 73% / +5.3 % / 3.5 | 440 / 75% / +7.2 % / 3.9 | 191 / 70% / +0.8 % / 0.4 | 153 / 66% / +6.1 % / 3.5 |
| LIMIT 0.5 / D 3 dny dolu / bez trendu / denne | TP 1 ATR, SL 4 ATR, max 20 d | 7034 / 75% / +1.9 % / 3.4 | 4541 / 76% / +3.4 % / 4.5 | 1688 / 75% / +2.5 % / 2.8 | 1248 / 77% / +5.7 % / 4.8 |
| LIMIT 0.5 / D RSI2<5 / bez trendu / sazby se rozchazeji / denne | TP 0.75 ATR, SL 4 ATR, max 20 d | 431 / 84% / +6.6 % / 3.4 | 440 / 85% / +8.7 % / 4.1 | 191 / 83% / +4.3 % / 1.9 | 153 / 82% / +6.5 % / 2.6 |
| LIMIT 0.5 / D RSI2<5 / bez trendu / sazby se rozchazeji / denne | TP 1 ATR, SL 4 ATR, max 5 d | 436 / 68% / +6.3 % / 3.7 | 453 / 67% / +6.8 % / 3.4 | 196 / 63% / +1.5 % / 0.7 | 158 / 63% / +8.1 % / 4.2 |
| MARKET / D %R14<10 / SMA200 / konec tydne | TP 15 %, SL 22 % marze, max 5 d | 832 / 66% / +2.2 % / 3.6 | 572 / 66% / +2.4 % / 3.4 | 218 / 60% / -0.1 % / -0.1 | 120 / 62% / +1.3 % / 0.8 |
| LIMIT 0.5 / D 3 dny dolu / bez trendu / sazby se rozchazeji / denne | TP 1 ATR, SL 4 ATR, max 5 d | 736 / 66% / +4.4 % / 3.3 | 760 / 64% / +5.3 % / 3.4 | 361 / 63% / +1.9 % / 1.2 | 287 / 64% / +7.6 % / 5.0 |
| LIMIT 0.5 / D 3 dny dolu / bez trendu / sazby se rozchazeji / denne | TP 1 ATR, SL 2 ATR, max 5 d | 736 / 64% / +4.1 % / 3.3 | 760 / 62% / +4.7 % / 3.3 | 361 / 63% / +2.6 % / 1.9 | 287 / 64% / +7.1 % / 4.7 |
| LIMIT 0.5 / D 3 dny dolu / bez trendu / sazby se rozchazeji / denne | TP 0.75 ATR, SL 4 ATR, max 5 d | 724 / 72% / +4.0 % / 3.3 | 739 / 73% / +6.8 % / 5.1 | 349 / 69% / +1.3 % / 0.9 | 268 / 69% / +6.3 % / 4.4 |
| LIMIT 0.5 / D 3 dny dolu / tydenni SMA40 / denne | TP 0.75 ATR, SL 4 ATR, max 20 d | 2555 / 81% / +2.6 % / 3.3 | 1646 / 82% / +4.7 % / 4.6 | 610 / 77% / -0.6 % / -0.5 | 444 / 83% / +4.8 % / 2.6 |
| LIMIT 0.5 / D RSI2<5 / bez trendu / sazby se rozchazeji / denne | TP 1 ATR, SL 3 ATR, max 5 d | 436 / 67% / +5.6 % / 3.3 | 453 / 66% / +6.7 % / 3.5 | 196 / 63% / +2.5 % / 1.2 | 158 / 63% / +7.4 % / 3.7 |
| LIMIT 0.5 / D %R14<10 / bez trendu / sazby se rozchazeji / denne | TP 0.75 ATR, SL 3 ATR, max 20 d | 721 / 83% / +5.3 % / 3.7 | 626 / 82% / +5.9 % / 3.2 | 304 / 85% / +7.1 % / 4.4 | 260 / 79% / +3.1 % / 1.3 |
| LIMIT 0.5 / D 3 dny dolu / bez trendu / denne | TP 0.75 ATR, SL 3 ATR, max 20 d | 6839 / 79% / +1.5 % / 3.2 | 4369 / 80% / +2.4 % / 3.7 | 1588 / 79% / +1.5 % / 1.9 | 1183 / 82% / +5.4 % / 5.3 |
| MARKET / W %R4<10 / SMA200 / konec tydne | TP 10 %, SL 30 % marze, max 20 d | 741 / 81% / +1.9 % / 3.3 | 497 / 82% / +2.2 % / 3.2 | 195 / 73% / -1.4 % / -1.1 | 105 / 82% / +2.5 % / 1.7 |
| LIMIT 0.5 / D %R14<10 / bez trendu / sazby se rozchazeji / denne | TP 0.75 ATR, SL 2 ATR, max 10 d | 721 / 76% / +4.0 % / 3.2 | 626 / 75% / +5.0 % / 3.2 | 304 / 77% / +5.5 % / 3.8 | 260 / 72% / +3.4 % / 1.8 |
| LIMIT 0.5 / D 3 dny dolu / bez trendu / denne | TP 1.5 ATR, SL 4 ATR, max 20 d | 7073 / 66% / +2.2 % / 3.4 | 4647 / 66% / +2.8 % / 3.2 | 1698 / 67% / +4.0 % / 3.9 | 1276 / 65% / +4.2 % / 2.9 |
| LIMIT 0.5 / D 3 dny dolu / bez trendu / denne | TP 1 ATR, SL 3 ATR, max 20 d | 7034 / 73% / +1.6 % / 3.2 | 4541 / 74% / +2.6 % / 3.6 | 1688 / 73% / +1.6 % / 1.9 | 1248 / 77% / +5.9 % / 5.2 |
| LIMIT 0.5 / D 3 dny dolu / bez trendu / sazby se rozchazeji / denne | TP 1 ATR, SL 3 ATR, max 5 d | 736 / 65% / +4.2 % / 3.2 | 760 / 64% / +5.7 % / 3.9 | 361 / 63% / +2.2 % / 1.5 | 287 / 64% / +7.6 % / 5.0 |
| MARKET / W %R4<10 / tydenni SMA40 / konec tydne | TP 15 %, SL 30 % marze, max 20 d | 736 / 73% / +2.3 % / 3.2 | 489 / 75% / +3.1 % / 3.5 | 196 / 67% / -0.5 % / -0.3 | 110 / 73% / +2.2 % / 1.2 |
| MARKET / D %R14<10 / tydenni SMA40 / konec tydne | TP 15 %, SL 22 % marze, max 20 d | 829 / 67% / +2.3 % / 3.7 | 565 / 68% / +2.3 % / 3.1 | 219 / 63% / +0.1 % / 0.1 | 125 / 66% / +1.5 % / 1.0 |
| LIMIT 0.5 / D 3 dny dolu / SMA200 / denne | TP 0.75 ATR, SL 4 ATR, max 20 d | 2559 / 81% / +2.5 % / 3.1 | 1647 / 82% / +4.7 % / 4.5 | 604 / 76% / -0.8 % / -0.6 | 445 / 82% / +4.5 % / 2.5 |
| MARKET / D %R14<10 / tydenni SMA40 / konec tydne | TP 15 %, SL 22 % marze, max 10 d | 829 / 67% / +2.2 % / 3.7 | 565 / 67% / +2.3 % / 3.1 | 219 / 62% / +0.2 % / 0.1 | 125 / 65% / +1.6 % / 1.0 |
| LIMIT 0.5 / D %R14<10 / bez trendu / sazby se rozchazeji / denne | TP 10 %, SL 60 % marze, max 5 d | 738 / 84% / +2.5 % / 3.7 | 642 / 85% / +2.4 % / 3.1 | 317 / 79% / +1.3 % / 1.2 | 275 / 82% / +2.5 % / 2.3 |
| LIMIT 0.5 / D 3 dny dolu / bez trendu / denne | TP 0.75 ATR, SL 4 ATR, max 10 d | 6839 / 75% / +1.5 % / 3.3 | 4369 / 76% / +2.0 % / 3.1 | 1588 / 75% / +1.5 % / 2.1 | 1183 / 77% / +5.3 % / 5.8 |
| MARKET / W %R4<10 / SMA200 / konec tydne | TP 15 %, SL 45 % marze, max 20 d | 741 / 80% / +2.9 % / 3.3 | 497 / 81% / +3.2 % / 3.1 | 195 / 74% / -1.0 % / -0.5 | 105 / 79% / +2.0 % / 0.8 |
| MARKET / W %R4<10 / tydenni SMA40 / konec tydne | TP 10 %, SL 30 % marze, max 20 d | 736 / 81% / +2.0 % / 3.5 | 489 / 82% / +2.2 % / 3.1 | 196 / 74% / -0.9 % / -0.7 | 110 / 81% / +2.1 % / 1.4 |
| LIMIT 0.5 / D 3 dny dolu / SMA200 / denne | TP 0.75 ATR, SL 2 ATR, max 20 d | 2559 / 75% / +2.0 % / 3.1 | 1647 / 76% / +2.9 % / 3.2 | 604 / 72% / -0.1 % / -0.1 | 445 / 78% / +4.6 % / 3.1 |
| MARKET / W %R4<10 / tydenni SMA40 / konec tydne | TP 15 %, SL 30 % marze, max 5 d | 736 / 70% / +2.2 % / 3.1 | 489 / 71% / +2.6 % / 3.2 | 196 / 63% / -0.1 % / -0.1 | 110 / 65% / +1.2 % / 0.6 |
| LIMIT 0.5 / D 3 dny dolu / bez trendu / sazby se rozchazeji / denne | TP 0.75 ATR, SL 2 ATR, max 5 d | 724 / 71% / +3.5 % / 3.1 | 739 / 72% / +6.1 % / 4.8 | 349 / 68% / +1.8 % / 1.4 | 268 / 69% / +5.8 % / 4.1 |
| LIMIT 0.5 / D %R14<10 / bez trendu / sazby se rozchazeji / denne | TP 0.75 ATR, SL 3 ATR, max 5 d | 721 / 73% / +5.5 % / 5.0 | 626 / 69% / +4.4 % / 3.1 | 304 / 70% / +3.9 % / 2.9 | 260 / 66% / +3.8 % / 2.3 |
| LIMIT 0.5 / D RSI2<5 / SMA200 / denne | TP 1 ATR, SL 4 ATR, max 20 d | 1254 / 76% / +3.8 % / 3.1 | 784 / 77% / +6.5 % / 3.9 | 295 / 69% / -2.2 % / -1.0 | 213 / 77% / +4.6 % / 1.5 |

_vypocet 13 s_
