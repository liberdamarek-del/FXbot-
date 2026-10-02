# Krátkodobé ukazatele po párech: funguje to, co fungovalo posledně?

_12 párů, denní data 2012–2026 (3692 společných obchodních dní), 64 signálů (technické, fundamentální, jiné trhy) × doby držení 1, 5, 10, 20 dní = 3024 kombinací pár × signál × držení. Výsledky po nákladech (spread + skluz), rozhoduje se při zavření v New Yorku jen z toho, co je tehdy známé. Sharpe = roční výnos / roční kolísání (0,5 slušné, 1 výborné). Jen výzkum – do modelu nic nepřechází._

## 1. Pevné ukazatele za celé období (pro srovnání)

Kombinací se Sharpe > 0,3 ve všech třech obdobích: **34 z 3024** (náhodou by se čekalo zhruba 24–47).

| pár | signál | držení | Sharpe 2012-18 | 2019-22 | 2023-26 | průměr na den v % marže |
|---|---|---|---|---|---|---|
| AUD/USD | sp500 5 dní − | 20 d | +0.87 | +0.74 | +0.54 | +0.37 % |
| AUD/JPY | sp500 dnes − | 20 d | +0.76 | +0.62 | +0.52 | +0.20 % |
| USD/CAD | nikkei dnes + | 20 d | +0.71 | +0.53 | +0.44 | +0.11 % |
| EUR/GBP | obrat 5 dní | 5 d | +0.48 | +0.63 | +0.42 | +0.32 % |
| AUD/USD | us10y 5 dní − | 20 d | +0.49 | +0.41 | +0.50 | +0.23 % |
| EUR/GBP | průraz 20 dní obrat | 5 d | +0.41 | +0.51 | +0.71 | +0.14 % |
| EUR/USD | obrat 1 dní | 20 d | +0.56 | +0.74 | +0.41 | +0.11 % |
| AUD/USD | nikkei dnes − | 10 d | +0.80 | +0.56 | +0.39 | +0.22 % |
| EUR/GBP | RSI(2) obrat | 10 d | +0.47 | +0.39 | +0.49 | +0.10 % |
| EUR/USD | obrat 1 dní | 10 d | +0.39 | +0.87 | +0.58 | +0.15 % |
| EUR/GBP | obrat 60 dní | 5 d | +0.39 | +0.48 | +0.46 | +0.32 % |
| USD/CHF | obrat 120 dní | 1 d | +0.71 | +0.39 | +0.56 | +0.65 % |
| EUR/GBP | velký den – proti | 20 d | +0.37 | +0.49 | +0.42 | +0.02 % |
| GBP/USD | průraz 20 dní obrat | 10 d | +0.39 | +0.37 | +0.72 | +0.13 % |
| AUD/USD | sp500 5 dní − | 10 d | +0.86 | +0.35 | +0.64 | +0.43 % |
| EUR/USD | zpráva – proti | 10 d | +0.45 | +0.43 | +0.35 | +0.04 % |
| EUR/JPY | nikkei dnes + | 1 d | +0.37 | +0.36 | +0.35 | +0.39 % |
| USD/CAD | sp500 5 dní + | 20 d | +0.35 | +0.62 | +0.43 | +0.16 % |
| USD/CAD | sp500 dnes + | 20 d | +0.45 | +0.41 | +0.34 | +0.08 % |
| EUR/USD | nikkei dnes − | 20 d | +0.34 | +0.38 | +0.53 | +0.08 % |
| EUR/USD | nikkei dnes − | 10 d | +0.34 | +0.61 | +0.64 | +0.13 % |
| EUR/GBP | obrat 1 dní | 20 d | +0.34 | +0.45 | +0.93 | +0.08 % |
| EUR/CHF | obrat 1 dní | 10 d | +0.33 | +0.63 | +0.37 | +0.08 % |
| USD/CAD | zpráva – proti | 20 d | +0.41 | +0.52 | +0.32 | +0.03 % |
| AUD/USD | zpráva – proti | 20 d | +0.32 | +0.33 | +0.42 | +0.03 % |

## 2. Pokračuje to, co fungovalo posledně? (informační koeficient)

Pro každé datum: pořadí všech kombinací podle výsledku za posledních L dní a podle výsledku za dalších M dní. Korelace pořadí (IC) > 0 = co fungovalo, funguje dál; 0 = náhoda. t > 2 = spolehlivé.

| zpětné okno | dalších 14 dní | další měsíc | dalšího půl roku |
|---|---|---|---|
| 3 měsíce | -0.001 (t -0.2) | +0.001 (t +0.1) | -0.014 (t -0.7) |
| 6 měsíců | +0.007 (t +1.2) | +0.008 (t +1.1) | +0.038 (t +2.3) |
| 1 rok | +0.010 (t +1.9) | +0.012 (t +1.6) | +0.021 (t +1.4) |

## 3. Strategie „vyber nejlepší ukazatel za poslední období a obchoduj ho dál“

Pro každý pár zvlášť: každých M dní vyber kombinaci s nejlepším Sharpe za posledních L dní (jen když je > 1), obchoduj ji dalších M dní; 12 párů se stejnou vahou. Výsledek jen na datech, která výběr neviděl (2013–2026). Náhodný výběr = 500 běhů, kdy se místo nejlepší vybere náhodná kombinace téhož páru; p = podíl náhodných běhů, které dopadly stejně nebo lépe.

| zpětné okno | obnova | Sharpe | roční výnos (% ceny, bez páky) | dní v obchodu | 2013-18 | 2019-22 | 2023-26 | náhodný výběr (průměr) | p |
|---|---|---|---|---|---|---|---|---|---|
| 3 měsíce | 14 dní | **+0.47** | +1.2 % | 100% | -0.08 | +1.22 | +0.72 | -0.23 | 0.01 |
| 3 měsíce | měsíc | **+0.24** | +0.6 % | 100% | -0.14 | +0.55 | +0.60 | -0.22 | 0.04 |
| 3 měsíce | půl roku | **-0.13** | -0.3 % | 100% | -0.21 | +0.18 | -0.28 | -0.22 | 0.32 |
| 6 měsíců | 14 dní | **+0.27** | +0.6 % | 100% | -0.22 | +0.80 | +0.47 | -0.22 | 0.04 |
| 6 měsíců | měsíc | **+0.08** | +0.2 % | 100% | -0.24 | +0.40 | +0.24 | -0.22 | 0.13 |
| 6 měsíců | půl roku | **+0.27** | +0.6 % | 100% | +0.28 | +0.20 | +0.28 | -0.21 | 0.03 |
| 1 rok | 14 dní | **-0.16** | -0.4 % | 100% | -0.51 | +0.10 | +0.19 | -0.22 | 0.41 |
| 1 rok | měsíc | **-0.32** | -0.7 % | 100% | -0.64 | -0.51 | +0.44 | -0.22 | 0.64 |
| 1 rok | půl roku | **-0.13** | -0.3 % | 100% | -0.05 | -0.30 | -0.10 | -0.22 | 0.35 |

## 4. Po jednotlivých párech (výběr za posledních 6 měsíců, obnova každý měsíc)

| pár | Sharpe mimo vzorek | 2013-18 | 2019-22 | 2023-26 | nejčastěji vybraný signál |
|---|---|---|---|---|---|
| EUR/USD | **+0.14** | -0.01 | +0.11 | +0.60 | sp500 dnes + (1 d) (12×) |
| USD/JPY | **-0.19** | -0.19 | -0.33 | -0.13 | ropa_wti dnes + (1 d) (10×) |
| GBP/USD | **+0.07** | -0.43 | +0.55 | +0.40 | nikkei 5 dní + (1 d) (8×) |
| USD/CHF | **-0.10** | -0.14 | +0.22 | -0.42 | sp500 dnes − (1 d) (11×) |
| AUD/USD | **+0.04** | +0.01 | -0.04 | +0.20 | zpráva – proti (10 d) (8×) |
| USD/CAD | **+0.19** | +0.06 | +0.66 | -0.19 | ropa_wti dnes + (5 d) (8×) |
| NZD/USD | **+0.11** | -0.43 | +0.29 | +0.93 | obrat 1 dní (10 d) (7×) |
| EUR/JPY | **-0.03** | -0.07 | +0.00 | -0.02 | med dnes + (1 d) (10×) |
| GBP/JPY | **+0.28** | +0.03 | +0.53 | +0.57 | ropa_wti dnes + (1 d) (10×) |
| EUR/GBP | **+0.07** | -0.18 | +0.76 | -0.31 | sp500 dnes + (5 d) (7×) |
| EUR/CHF | **-0.07** | +0.39 | -1.06 | -0.82 | sp500 dnes − (10 d) (8×) |
| AUD/JPY | **-0.11** | -0.11 | -0.06 | -0.15 | ropa_wti dnes + (1 d) (8×) |

## 5. Celý vzorek najednou (nejlepších 5 kombinací ze všech párů)

| zpětné okno | obnova | Sharpe mimo vzorek | 2013-18 | 2019-22 | 2023-26 |
|---|---|---|---|---|---|
| 3 měsíce | 14 dní | **+0.36** | -0.20 | +1.03 | +0.67 |
| 3 měsíce | měsíc | **+0.16** | +0.06 | +0.12 | +0.40 |
| 3 měsíce | půl roku | **-0.23** | -0.49 | -0.35 | +0.33 |
| 6 měsíců | 14 dní | **+0.23** | -0.14 | +0.48 | +0.74 |
| 6 měsíců | měsíc | **+0.26** | +0.09 | +0.47 | +0.35 |
| 6 měsíců | půl roku | **+0.27** | +0.04 | +0.03 | +0.89 |
| 1 rok | 14 dní | **-0.13** | -0.37 | -0.10 | +0.31 |
| 1 rok | měsíc | **+0.06** | -0.28 | +0.01 | +0.73 |
| 1 rok | půl roku | **+0.04** | +0.31 | -0.31 | -0.05 |

## 6. Dnešní akcie USA → zítřejší měna (nález z analýzy pohybů)

| pár | signál | držení | Sharpe 2012-18 | 2019-22 | 2023-26 | průměr na den v % marže |
|---|---|---|---|---|---|---|
| EUR/USD | sp500 dnes + | 1 d | -0.16 | +1.04 | -0.40 | +0.093 % |
| USD/JPY | sp500 dnes − | 1 d | -0.33 | +0.95 | +0.07 | +0.104 % |
| GBP/USD | sp500 dnes + | 1 d | -0.27 | +0.94 | -0.34 | +0.098 % |
| USD/CHF | sp500 dnes − | 1 d | -0.16 | +1.42 | -0.24 | +0.183 % |
| AUD/USD | sp500 dnes + | 1 d | -0.92 | +0.26 | -0.35 | -0.504 % |

_výpočet 9 s_
