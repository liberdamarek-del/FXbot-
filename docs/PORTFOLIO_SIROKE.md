# Portfolio pravidel - realisticka simulace uctu

_Obchod po obchodu (hodinove BID/ASK, naklady, swap), slozene uroceni, nejvyse jedna pozice na par v celem portfoliu, soucet marzi otevrenych obchodu <= 100% uctu, vsechna vybrana pravidla se stejnou vahou (zadne ladeni vah). Vyber pravidel jen z minulosti._

## Vyber na 2012-2018: 37 pravidel

### marze 2% uctu na obchod

| obdobi | obchodu/rok | uspesnost | zisk/obchod (% marze) | ziskovych/mesic | mesicu s >= 2 ziskovymi | ziskovych mesicu | **rocne (slozene)** | max. propad |
|---|---|---|---|---|---|---|---|---|
| 2012-18 | 162 | 79% | +5.9 % | 10.5 | 99% | 71% | **+20.6%** | 9.8% |
| 2019-22 | 128 | 69% | +0.7 % | 7.2 | 80% | 61% | **+1.3%** | 13.3% |
| 2023-26 | 198 | 73% | +3.0 % | 11.8 | 91% | 64% | **+11.3%** | 27.7% |

### marze 3% uctu na obchod

| obdobi | obchodu/rok | uspesnost | zisk/obchod (% marze) | ziskovych/mesic | mesicu s >= 2 ziskovymi | ziskovych mesicu | **rocne (slozene)** | max. propad |
|---|---|---|---|---|---|---|---|---|
| 2012-18 | 162 | 79% | +5.9 % | 10.5 | 99% | 71% | **+32.1%** | 14.7% |
| 2019-22 | 128 | 69% | +0.7 % | 7.2 | 80% | 61% | **+1.6%** | 19.7% |
| 2023-26 | 198 | 73% | +3.0 % | 11.8 | 91% | 64% | **+16.5%** | 39.7% |

### marze 5% uctu na obchod

| obdobi | obchodu/rok | uspesnost | zisk/obchod (% marze) | ziskovych/mesic | mesicu s >= 2 ziskovymi | ziskovych mesicu | **rocne (slozene)** | max. propad |
|---|---|---|---|---|---|---|---|---|
| 2012-18 | 162 | 79% | +5.9 % | 10.5 | 99% | 71% | **+57.5%** | 24.4% |
| 2019-22 | 128 | 69% | +0.7 % | 7.2 | 80% | 61% | **+1.4%** | 31.8% |
| 2023-26 | 198 | 73% | +3.0 % | 11.8 | 91% | 64% | **+25.3%** | 59.8% |

### marze 8% uctu na obchod

| obdobi | obchodu/rok | uspesnost | zisk/obchod (% marze) | ziskovych/mesic | mesicu s >= 2 ziskovymi | ziskovych mesicu | **rocne (slozene)** | max. propad |
|---|---|---|---|---|---|---|---|---|
| 2012-18 | 162 | 79% | +5.9 % | 10.5 | 99% | 73% | **+101.8%** | 38.5% |
| 2019-22 | 126 | 69% | +0.5 % | 7.1 | 80% | 61% | **-3.1%** | 53.0% |
| 2023-26 | 197 | 73% | +3.0 % | 11.8 | 91% | 64% | **+34.4%** | 79.7% |

### marze 10% uctu na obchod

| obdobi | obchodu/rok | uspesnost | zisk/obchod (% marze) | ziskovych/mesic | mesicu s >= 2 ziskovymi | ziskovych mesicu | **rocne (slozene)** | max. propad |
|---|---|---|---|---|---|---|---|---|
| 2012-18 | 162 | 79% | +5.9 % | 10.5 | 99% | 73% | **+135.1%** | 48.2% |
| 2019-22 | 125 | 69% | +0.6 % | 7.1 | 80% | 61% | **-4.5%** | 57.8% |
| 2023-26 | 191 | 73% | +3.2 % | 11.4 | 91% | 62% | **+43.6%** | 81.7% |

Pravidla (poradi = priorita):

1. MARKET / D RSI2<10 / tydenni SMA40 / carry >= 2 % / konec tydne | TP 22 %, SL 60 % marze, max 10 d
2. MARKET / D RSI2<10 / SMA200 / carry >= 2 % / konec tydne | TP 15 %, SL 60 % marze, max 10 d
3. MARKET / D RSI2<10 / SMA50 / carry >= 2 % / konec tydne | TP 0.75 ATR, SL 4 ATR, max 10 d
4. MARKET / D RSI2<5 / bez trendu / sazby se rozchazeji / konec tydne | TP 10 %, SL 45 % marze, max 10 d
5. MARKET / D RSI2<10 / tydenni SMA40 / carry >= 2 % / denne | TP 15 %, SL 45 % marze, max 5 d
6. MARKET / D RSI2<5 / tydenni SMA40 / sazby se rozchazeji / konec tydne | TP 10 %, SL 60 % marze, max 20 d
7. MARKET / D RSI2<5 / bez trendu / carry >= 2 % / konec tydne | TP 15 %, SL 60 % marze, max 20 d
8. MARKET / D RSI2<10 / SMA200 / carry >= 2 % / denne | TP 15 %, SL 60 % marze, max 5 d
9. MARKET / D %R14<10 / tydenni SMA40 / carry >= 2 % / konec tydne | TP 22 %, SL 60 % marze, max 5 d
10. LIMIT 1.0 / D %R14<10 / bez trendu / sazby se rozchazeji / denne | TP 10 %, SL 60 % marze, max 5 d
11. LIMIT 0.5 / D pod BB20(2) / SMA50 / carry souhlasi / denne | TP 0.75 ATR, SL 4 ATR, max 20 d
12. MARKET / D RSI2<5 / SMA200 / sazby se rozchazeji / konec tydne | TP 10 %, SL 60 % marze, max 20 d
13. MARKET / D RSI2<5 / SMA50 / carry >= 2 % / denne | TP 10 %, SL 60 % marze, max 5 d
14. MARKET / D 3 dny dolu / bez trendu / carry >= 2 % / konec tydne | TP 0.75 ATR, SL 2 ATR, max 20 d
15. LIMIT 1.0 / D RSI2<10 / SMA50 / carry >= 2 % / denne | TP 10 %, SL 22 % marze, max 5 d
16. LIMIT 0.5 / D RSI3<15 / SMA50 / carry >= 2 % / denne | TP 10 %, SL 22 % marze, max 10 d
17. MARKET / D 3 dny dolu / SMA50 / carry >= 2 % / konec tydne | TP 0.75 ATR, SL 3 ATR, max 10 d
18. MARKET / D RSI3<15 / SMA50 / carry >= 2 % / denne | TP 10 %, SL 45 % marze, max 5 d
19. MARKET / D RSI3<15 / bez trendu / carry >= 2 % / konec tydne | TP 15 %, SL 60 % marze, max 5 d
20. MARKET / D %R14<10 / SMA50 / carry souhlasi / konec tydne | TP 0.75 ATR, SL 4 ATR, max 20 d
21. MARKET / D RSI2<10 / bez trendu / carry >= 2 % / konec tydne | TP 15 %, SL 60 % marze, max 5 d
22. MARKET / D %R14<10 / SMA200 / carry >= 2 % / konec tydne | TP 22 %, SL 45 % marze, max 5 d
23. MARKET / D %R14<10 / bez trendu / carry >= 2 % / konec tydne | TP 10 %, SL 60 % marze, max 5 d
24. LIMIT 1.0 / D RSI2<5 / bez trendu / sazby se rozchazeji / denne | TP 0.75 ATR, SL 2 ATR, max 10 d
25. LIMIT 0.5 / D %R14<10 / bez trendu / sazby se rozchazeji / denne | TP 1 ATR, SL 4 ATR, max 5 d
26. LIMIT 0.5 / D RSI2<10 / SMA50 / carry >= 2 % / denne | TP 15 %, SL 30 % marze, max 5 d
27. LIMIT 1.0 / D %R14<10 / SMA50 / carry souhlasi / konec tydne | TP 30 %, SL 45 % marze, max 10 d
28. LIMIT 1.0 / D %R14<10 / SMA50 / konec tydne | TP 22 %, SL 60 % marze, max 10 d
29. LIMIT 1.0 / D %R14<10 / SMA50 / carry souhlasi / denne | TP 0.75 ATR, SL 4 ATR, max 5 d
30. MARKET / D RSI3<15 / tydenni SMA40 / carry >= 2 % / denne | TP 22 %, SL 45 % marze, max 5 d
31. MARKET / D RSI3<15 / SMA200 / carry >= 2 % / konec tydne | TP 22 %, SL 60 % marze, max 20 d
32. MARKET / D RSI3<15 / tydenni SMA40 / carry >= 2 % / konec tydne | TP 22 %, SL 60 % marze, max 20 d
33. MARKET / W %R4<10 / bez trendu / carry >= 2 % / konec tydne | TP 15 %, SL 60 % marze, max 5 d
34. MARKET / D RSI3<15 / SMA200 / carry >= 2 % / denne | TP 22 %, SL 60 % marze, max 10 d
35. MARKET / D 3 dny dolu / SMA200 / carry >= 2 % / konec tydne | TP 22 %, SL 60 % marze, max 20 d
36. MARKET / D 3 dny dolu / tydenni SMA40 / carry >= 2 % / konec tydne | TP 22 %, SL 60 % marze, max 20 d
37. LIMIT 0.5 / D %R14<10 / SMA50 / carry souhlasi / konec tydne | TP 1 ATR, SL 3 ATR, max 20 d

## Vyber na 2012-2022: 56 pravidel

### marze 2% uctu na obchod

| obdobi | obchodu/rok | uspesnost | zisk/obchod (% marze) | ziskovych/mesic | mesicu s >= 2 ziskovymi | ziskovych mesicu | **rocne (slozene)** | max. propad |
|---|---|---|---|---|---|---|---|---|
| 2012-18 | 373 | 70% | +3.1 % | 21.5 | 100% | 67% | **+24.5%** | 10.9% |
| 2019-22 | 371 | 71% | +3.1 % | 21.7 | 100% | 73% | **+24.9%** | 13.5% |
| 2023-26 | 333 | 67% | +1.5 % | 18.2 | 93% | 58% | **+9.6%** | 26.7% |

### marze 3% uctu na obchod

| obdobi | obchodu/rok | uspesnost | zisk/obchod (% marze) | ziskovych/mesic | mesicu s >= 2 ziskovymi | ziskovych mesicu | **rocne (slozene)** | max. propad |
|---|---|---|---|---|---|---|---|---|
| 2012-18 | 373 | 70% | +3.1 % | 21.5 | 100% | 67% | **+38.0%** | 16.0% |
| 2019-22 | 371 | 71% | +3.1 % | 21.7 | 100% | 71% | **+38.7%** | 20.0% |
| 2023-26 | 333 | 67% | +1.5 % | 18.2 | 93% | 58% | **+13.9%** | 37.8% |

### marze 5% uctu na obchod

| obdobi | obchodu/rok | uspesnost | zisk/obchod (% marze) | ziskovych/mesic | mesicu s >= 2 ziskovymi | ziskovych mesicu | **rocne (slozene)** | max. propad |
|---|---|---|---|---|---|---|---|---|
| 2012-18 | 373 | 70% | +3.1 % | 21.5 | 100% | 67% | **+67.1%** | 26.6% |
| 2019-22 | 371 | 71% | +3.1 % | 21.7 | 100% | 71% | **+68.4%** | 32.2% |
| 2023-26 | 333 | 67% | +1.5 % | 18.2 | 93% | 58% | **+21.0%** | 56.2% |

### marze 8% uctu na obchod

| obdobi | obchodu/rok | uspesnost | zisk/obchod (% marze) | ziskovych/mesic | mesicu s >= 2 ziskovymi | ziskovych mesicu | **rocne (slozene)** | max. propad |
|---|---|---|---|---|---|---|---|---|
| 2012-18 | 365 | 70% | +3.1 % | 21.1 | 100% | 66% | **+112.9%** | 40.8% |
| 2019-22 | 355 | 71% | +2.7 % | 20.6 | 100% | 69% | **+89.4%** | 50.8% |
| 2023-26 | 324 | 67% | +1.6 % | 17.8 | 93% | 53% | **+28.6%** | 72.8% |

### marze 10% uctu na obchod

| obdobi | obchodu/rok | uspesnost | zisk/obchod (% marze) | ziskovych/mesic | mesicu s >= 2 ziskovymi | ziskovych mesicu | **rocne (slozene)** | max. propad |
|---|---|---|---|---|---|---|---|---|
| 2012-18 | 346 | 71% | +3.2 % | 20.1 | 100% | 66% | **+151.0%** | 49.0% |
| 2019-22 | 332 | 71% | +2.7 % | 19.2 | 100% | 67% | **+101.0%** | 59.2% |
| 2023-26 | 303 | 67% | +1.6 % | 16.7 | 93% | 51% | **+34.5%** | 73.5% |

Pravidla (poradi = priorita):

1. MARKET / D RSI2<5 / bez trendu / sazby se rozchazeji / konec tydne | TP 10 %, SL 45 % marze, max 10 d
2. MARKET / D RSI2<5 / tydenni SMA40 / sazby se rozchazeji / konec tydne | TP 10 %, SL 45 % marze, max 20 d
3. MARKET / D RSI2<5 / SMA200 / sazby se rozchazeji / konec tydne | TP 10 %, SL 45 % marze, max 20 d
4. MARKET / D RSI2<5 / SMA50 / sazby se rozchazeji / konec tydne | TP 10 %, SL 60 % marze, max 20 d
5. LIMIT 0.5 / D %R14<10 / bez trendu / sazby se rozchazeji / denne | TP 15 %, SL 60 % marze, max 5 d
6. LIMIT 0.5 / D pod BB20(2) / SMA50 / carry souhlasi / denne | TP 1.5 ATR, SL 3 ATR, max 20 d
7. MARKET / D pod BB20(2) / SMA50 / carry souhlasi / denne | TP 1 ATR, SL 3 ATR, max 20 d
8. LIMIT 1.0 / D %R14<10 / bez trendu / sazby se rozchazeji / denne | TP 0.75 ATR, SL 4 ATR, max 20 d
9. MARKET / D RSI3<15 / tydenni SMA40 / sazby se rozchazeji / konec tydne | TP 10 %, SL 45 % marze, max 20 d
10. LIMIT 1.0 / D 3 dny dolu / SMA50 / carry souhlasi / konec tydne | TP 0.75 ATR, SL 2 ATR, max 10 d
11. MARKET / D RSI3<15 / tydenni SMA40 / carry >= 2 % / denne | TP 0.75 ATR, SL 1 ATR, max 20 d
12. LIMIT 0.5 / D pod SMA5 o 1.5 ATR / SMA200 / denne | TP 10 %, SL 60 % marze, max 20 d
13. MARKET / D RSI2<10 / tydenni SMA40 / carry souhlasi / konec tydne | TP 10 %, SL 60 % marze, max 10 d
14. MARKET / D RSI2<10 / SMA200 / carry souhlasi / konec tydne | TP 10 %, SL 60 % marze, max 10 d
15. LIMIT 0.5 / D pod SMA5 o 1.5 ATR / tydenni SMA40 / denne | TP 10 %, SL 60 % marze, max 20 d
16. LIMIT 0.5 / D 3 dny dolu / SMA50 / carry souhlasi / konec tydne | TP 1 ATR, SL 4 ATR, max 10 d
17. LIMIT 1.0 / D %R14<10 / SMA50 / carry souhlasi / denne | TP 3 ATR, SL 3 ATR, max 5 d
18. LIMIT 1.0 / D %R14<10 / SMA50 / carry souhlasi / konec tydne | TP 15 %, SL 60 % marze, max 5 d
19. MARKET / D RSI3<15 / SMA200 / sazby se rozchazeji / konec tydne | TP 10 %, SL 45 % marze, max 10 d
20. MARKET / W %R4<10 / bez trendu / sazby se rozchazeji / konec tydne | TP 22 %, SL 22 % marze, max 5 d
21. MARKET / D %R14<10 / tydenni SMA40 / konec tydne | TP 0.75 ATR, SL 1 ATR, max 5 d
22. MARKET / D 3 dny dolu / bez trendu / carry >= 2 % / konec tydne | TP 0.75 ATR, SL 1.5 ATR, max 10 d
23. MARKET / D 3 dny dolu / bez trendu / sazby se rozchazeji / konec tydne | TP 22 %, SL 45 % marze, max 10 d
24. MARKET / D RSI3<15 / SMA200 / carry >= 2 % / denne | TP 0.75 ATR, SL 1 ATR, max 20 d
25. MARKET / D RSI2<5 / SMA200 / konec tydne | TP 10 %, SL 22 % marze, max 5 d
26. MARKET / W %R4<10 / tydenni SMA40 / carry >= 2 % / konec tydne | TP 22 %, SL 60 % marze, max 5 d
27. MARKET / D pod BB20(2) / bez trendu / sazby se rozchazeji / konec tydne | TP 0.75 ATR, SL 4 ATR, max 5 d
28. LIMIT 1.0 / D 3 dny dolu / tydenni SMA40 / carry souhlasi / konec tydne | TP 10 %, SL 60 % marze, max 10 d
29. MARKET / D 3 dny dolu / tydenni SMA40 / carry souhlasi / konec tydne | TP 10 %, SL 60 % marze, max 10 d
30. MARKET / D RSI2<5 / tydenni SMA40 / konec tydne | TP 10 %, SL 22 % marze, max 5 d
31. MARKET / D %R14<10 / tydenni SMA40 / carry souhlasi / konec tydne | TP 10 %, SL 15 % marze, max 10 d
32. MARKET / D %R14<10 / SMA200 / konec tydne | TP 22 %, SL 15 % marze, max 10 d
33. MARKET / D RSI3<15 / bez trendu / sazby se rozchazeji / konec tydne | TP 0.75 ATR, SL 4 ATR, max 10 d
34. MARKET / D RSI2<5 / tydenni SMA40 / carry >= 2 % / denne | TP 22 %, SL 45 % marze, max 10 d
35. MARKET / D %R14<10 / bez trendu / carry souhlasi / konec tydne | TP 15 %, SL 22 % marze, max 10 d
36. LIMIT 1.0 / D RSI2<10 / SMA50 / carry souhlasi / konec tydne | TP 0.75 ATR, SL 1.5 ATR, max 5 d
37. LIMIT 1.0 / D 3 dny dolu / SMA200 / carry souhlasi / konec tydne | TP 10 %, SL 60 % marze, max 10 d
38. MARKET / D RSI2<10 / tydenni SMA40 / carry >= 2 % / denne | TP 0.75 ATR, SL 1 ATR, max 10 d
39. MARKET / D 3 dny dolu / SMA200 / carry souhlasi / konec tydne | TP 10 %, SL 60 % marze, max 10 d
40. LIMIT 1.0 / D RSI2<10 / tydenni SMA40 / carry >= 2 % / denne | TP 10 %, SL 30 % marze, max 20 d
41. LIMIT 1.0 / D RSI2<5 / SMA50 / konec tydne | TP 0.75 ATR, SL 1 ATR, max 5 d
42. MARKET / W %R4<20 / tydenni SMA40 / carry >= 2 % / konec tydne | TP 22 %, SL 60 % marze, max 10 d
43. LIMIT 1.0 / D pod SMA5 o 1.5 ATR / SMA200 / denne | TP 10 %, SL 30 % marze, max 20 d
44. LIMIT 0.5 / D RSI2<5 / bez trendu / sazby se rozchazeji / konec tydne | TP 15 %, SL 45 % marze, max 5 d
45. LIMIT 1.0 / D pod SMA5 o 1.5 ATR / tydenni SMA40 / denne | TP 0.75 ATR, SL 1.5 ATR, max 10 d
46. MARKET / D %R14<10 / tydenni SMA40 / carry >= 2 % / konec tydne | TP 22 %, SL 15 % marze, max 10 d
47. MARKET / D %R14<10 / bez trendu / carry >= 2 % / konec tydne | TP 0.75 ATR, SL 1 ATR, max 10 d
48. MARKET / D pod SMA5 o 1.5 ATR / SMA50 / konec tydne | TP 10 %, SL 30 % marze, max 10 d
49. MARKET / W %R4<10 / SMA200 / carry >= 2 % / konec tydne | TP 22 %, SL 60 % marze, max 5 d
50. MARKET / W %R4<10 / tydenni SMA40 / konec tydne | TP 22 %, SL 45 % marze, max 5 d
51. MARKET / W %R4<10 / bez trendu / carry souhlasi / konec tydne | TP 15 %, SL 22 % marze, max 5 d
52. MARKET / W %R4<20 / SMA200 / carry >= 2 % / konec tydne | TP 22 %, SL 60 % marze, max 10 d
53. MARKET / D RSI2<10 / SMA200 / carry >= 2 % / denne | TP 0.75 ATR, SL 1 ATR, max 10 d
54. MARKET / D RSI3<15 / SMA200 / konec tydne | TP 10 %, SL 15 % marze, max 5 d
55. MARKET / D %R14<10 / bez trendu / sazby se rozchazeji / konec tydne | TP 22 %, SL 22 % marze, max 5 d
56. MARKET / D %R14<10 / SMA200 / carry souhlasi / konec tydne | TP 10 %, SL 15 % marze, max 10 d

_vypocet 23 s_
