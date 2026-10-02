# Proč se měnové páry denně hýbou

_12 párů, hodinová data FXCM 2012–2026 (střední ceny), denní svíčka končí v 17:00 New York. % marže = pohyb ceny × 30 (páka 1:30). Zprávy: rozhodnutí Fedu, ECB, BoJ, BoE a americké zprávy NFP, CPI, HDP, maloobchod, PCE, PPI (termíny z ALFRED). Jen popis, do modelu nic nepřechází._

## 1. Jak velké jsou denní pohyby

| pár | průměrný denní pohyb (zavření–zavření) | průměrný denní rozsah (max–min) | dní s rozsahem ≥ 1 % | dní s pohybem ≥ 1 % | rozsah v % marže |
|---|---|---|---|---|---|
| EUR/USD | 0.36 % | 0.73 % | 17% | 5% | 22 % |
| USD/JPY | 0.41 % | 0.81 % | 24% | 8% | 24 % |
| GBP/USD | 0.39 % | 0.79 % | 21% | 6% | 24 % |
| USD/CHF | 0.38 % | 0.76 % | 18% | 5% | 23 % |
| AUD/USD | 0.47 % | 0.96 % | 37% | 10% | 29 % |
| USD/CAD | 0.33 % | 0.66 % | 13% | 3% | 20 % |
| NZD/USD | 0.49 % | 1.01 % | 41% | 11% | 30 % |
| EUR/JPY | 0.42 % | 0.87 % | 28% | 8% | 26 % |
| GBP/JPY | 0.47 % | 0.97 % | 35% | 11% | 29 % |
| EUR/GBP | 0.32 % | 0.67 % | 14% | 4% | 20 % |
| EUR/CHF | 0.22 % | 0.47 % | 5% | 1% | 14 % |
| AUD/JPY | 0.53 % | 1.08 % | 45% | 14% | 33 % |

Všech 12 párů: průměrný pohyb zavření–zavření **0.40 %** (= 12 % marže), průměrný denní rozsah **0.82 %** (= 24 % marže); rozsah aspoň 1 % má 25% dní, pohyb zavření–zavření aspoň 1 % jen 7% dní.

Průměrný denní rozsah podle let (%):

| pár | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EUR/USD | 0.84 | 0.73 | 0.57 | 1.13 | 0.83 | 0.69 | 0.72 | 0.49 | 0.75 | 0.53 | 0.98 | 0.72 | 0.56 | 0.73 | 0.58 |
| USD/JPY | 0.71 | 1.11 | 0.69 | 0.77 | 1.12 | 0.81 | 0.64 | 0.53 | 0.69 | 0.53 | 1.03 | 0.95 | 0.93 | 0.91 | 0.76 |
| GBP/USD | 0.61 | 0.71 | 0.54 | 0.81 | 1.10 | 0.80 | 0.81 | 0.78 | 1.02 | 0.66 | 1.11 | 0.81 | 0.61 | 0.69 | 0.64 |
| USD/CHF | 0.82 | 0.85 | 0.64 | 1.21 | 0.80 | 0.69 | 0.65 | 0.54 | 0.70 | 0.61 | 0.88 | 0.79 | 0.67 | 0.79 | 0.76 |
| AUD/USD | 0.88 | 0.97 | 0.83 | 1.24 | 1.15 | 0.78 | 0.83 | 0.69 | 1.19 | 0.88 | 1.29 | 1.06 | 0.83 | 0.89 | 0.89 |
| USD/CAD | 0.64 | 0.59 | 0.62 | 0.92 | 0.91 | 0.70 | 0.68 | 0.49 | 0.73 | 0.68 | 0.80 | 0.60 | 0.46 | 0.54 | 0.46 |
| NZD/USD | 0.98 | 1.11 | 0.89 | 1.35 | 1.21 | 0.90 | 0.85 | 0.74 | 1.14 | 0.93 | 1.28 | 1.06 | 0.84 | 0.93 | 0.92 |
| EUR/JPY | 1.10 | 1.19 | 0.70 | 1.03 | 1.06 | 0.78 | 0.79 | 0.60 | 0.79 | 0.55 | 1.09 | 0.90 | 0.87 | 0.76 | 0.63 |
| GBP/JPY | 0.94 | 1.13 | 0.76 | 0.92 | 1.53 | 0.97 | 0.91 | 0.90 | 1.03 | 0.71 | 1.17 | 0.94 | 0.93 | 0.80 | 0.68 |
| EUR/GBP | 0.60 | 0.67 | 0.55 | 0.97 | 1.06 | 0.77 | 0.61 | 0.71 | 0.85 | 0.53 | 0.77 | 0.52 | 0.39 | 0.47 | 0.34 |
| EUR/CHF | 0.17 | 0.45 | 0.19 | 0.85 | 0.48 | 0.46 | 0.50 | 0.42 | 0.42 | 0.38 | 0.73 | 0.53 | 0.54 | 0.51 | 0.43 |
| AUD/JPY | 1.13 | 1.30 | 0.87 | 1.22 | 1.50 | 0.87 | 0.97 | 0.85 | 1.25 | 0.88 | 1.30 | 1.05 | 1.02 | 1.03 | 0.92 |

## 2. V kterou hodinu se trh hýbe nejvíc

Průměrný pohyb za hodinu vůči průměru dne (1,0 = průměr), čas New York (u nás +6 h):

| hodina (New York) | 00 | 01 | 02 | 03 | 04 | 05 | 06 | 07 | 08 | 09 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| síla pohybu | 0.7 | 0.8 | 1.1 | 1.4 | 1.3 | 1.1 | 1.0 | 1.1 | 1.6 | 1.5 | 1.7 | 1.2 | 1.0 | 0.9 | 0.9 | 0.8 | 0.6 | 0.5 | 0.7 | 0.8 | 1.0 | 0.9 | 0.8 | 0.6 |

Nejsilnější hodiny: 10:00–11:00 New York (u nás 16:00), 08:00–09:00 New York (u nás 14:00), 09:00–10:00 New York (u nás 15:00), 03:00–04:00 New York (u nás 09:00). 08:30 New York = americké zprávy (NFP, CPI, HDP, maloobchod), 10:00 = další americká data, 14:00 = Fed, 02:00–04:00 = otevření Londýna a evropská data.

## 3. Největší dny: kolik z nich způsobily plánované zprávy

Velký den = 5 % dní s největším pohybem zavření–zavření u daného páru.

| pár | velký den od | velkých dní se zprávou | všech dní se zprávou | lift |
|---|---|---|---|---|
| EUR/USD | 0.99 % (30 % marže) | 46% | 32% | 1.5× |
| USD/JPY | 1.19 % (36 % marže) | 44% | 32% | 1.4× |
| GBP/USD | 1.07 % (32 % marže) | 49% | 32% | 1.6× |
| USD/CHF | 1.03 % (31 % marže) | 35% | 29% | 1.2× |
| AUD/USD | 1.25 % (38 % marže) | 41% | 29% | 1.4× |
| USD/CAD | 0.89 % (27 % marže) | 33% | 29% | 1.1× |
| NZD/USD | 1.30 % (39 % marže) | 45% | 29% | 1.5× |
| EUR/JPY | 1.19 % (36 % marže) | 22% | 7% | 3.1× |
| GBP/JPY | 1.33 % (40 % marže) | 15% | 7% | 2.3× |
| EUR/GBP | 0.91 % (27 % marže) | 13% | 6% | 2.3× |
| EUR/CHF | 0.64 % (19 % marže) | 5% | 3% | 1.6× |
| AUD/JPY | 1.45 % (43 % marže) | 10% | 4% | 2.6× |

Všech 12 párů dohromady (lift = kolikrát častěji je zpráva ve velkém dni než v obyčejném):

| zpráva | ve velkých dnech | ve všech dnech | lift |
|---|---|---|---|
| centrální banka páru | 11.4% | 4.8% | 2.4× |
| Fed | 3.5% | 1.8% | 2.0× |
| ECB | 2.9% | 1.1% | 2.6× |
| BoJ | 3.6% | 1.3% | 2.9× |
| BoE | 1.8% | 0.8% | 2.3× |
| USA: NFP | 4.6% | 2.8% | 1.7× |
| USA: CPI | 4.6% | 2.9% | 1.6× |
| USA: HDP | 3.2% | 3.1% | 1.0× |
| USA: maloobchod | 4.2% | 2.8% | 1.5× |
| USA: PCE | 2.8% | 2.7% | 1.0× |
| USA: PPI | 3.4% | 2.9% | 1.2× |
| jakákoli plánovaná zpráva | 29.8% | 19.8% | 1.5× |

Ve které hodině se ve velkých dnech stal největší hodinový pohyb (čas New York):

| hodina | podíl velkých dní |
|---|---|
| jiná hodina | 26% |
| 02:00–06:00 (Evropa) | 26% |
| 19:00–01:00 (Asie) | 15% |
| 08:00–09:00 (US data 8:30) | 14% |
| 10:00–11:00 (US data 10:00) | 13% |
| 07:00–08:00 (ECB 7:45) | 4% |
| 14:00–15:00 (Fed) | 3% |

Největší jediná hodina dělá u velkých dnů v mediánu **35%** celodenního pohybu (zbytek se nasbírá postupně během dne).

## 4. Co se hýbe spolu se měnami ve stejný den

Korelace denního pohybu páru se stejnodenní změnou jiných trhů (1 = vždy stejně, −1 = vždy opačně, 0 = žádný vztah). R² = jakou část denních pohybů páru vysvětlí všechny trhy dohromady.

| pár | akcie USA (S&P 500) | strach (VIX) | zlato | ropa WTI | med | US 10letý výnos | akcie Japonsko | akcie Evropa | rozdíl 2letých výnosů páru | R² všech |
|---|---|---|---|---|---|---|---|---|---|---|
| EUR/USD | +0.07 | +0.01 | +0.30 | +0.01 | +0.21 | -0.21 | +0.00 | -0.00 | +0.31 | **20%** |
| USD/JPY | +0.21 | -0.25 | -0.36 | +0.05 | -0.05 | +0.49 | +0.18 | +0.21 | +0.48 | **37%** |
| GBP/USD | +0.24 | -0.14 | +0.24 | +0.07 | +0.25 | -0.13 | +0.08 | +0.21 | +0.24 | **22%** |
| USD/CHF | +0.05 | -0.11 | -0.32 | +0.01 | -0.14 | +0.29 | -0.01 | +0.06 | +0.32 | **18%** |
| AUD/USD | +0.43 | -0.33 | +0.33 | +0.09 | +0.39 | -0.11 | +0.12 | +0.28 | +0.21 | **38%** |
| USD/CAD | -0.42 | +0.34 | -0.23 | -0.18 | -0.33 | +0.02 | -0.08 | -0.30 | +0.27 | **35%** |
| NZD/USD | +0.33 | -0.25 | +0.33 | +0.05 | +0.32 | -0.18 | +0.08 | +0.21 | +0.22 | **28%** |
| EUR/JPY | +0.27 | -0.25 | -0.10 | +0.05 | +0.14 | +0.31 | +0.19 | +0.22 | +0.27 | **20%** |
| GBP/JPY | +0.38 | -0.33 | -0.11 | +0.10 | +0.17 | +0.31 | +0.22 | +0.35 | +0.29 | **27%** |
| EUR/GBP | -0.22 | +0.18 | +0.03 | -0.08 | -0.09 | -0.07 | -0.10 | -0.26 | +0.23 | **13%** |
| EUR/CHF | +0.13 | -0.13 | -0.09 | +0.02 | +0.04 | +0.15 | -0.01 | +0.07 | +0.10 | **5%** |
| AUD/JPY | +0.55 | -0.49 | +0.00 | +0.12 | +0.30 | +0.30 | +0.25 | +0.42 | +0.20 | **43%** |

V průměru vysvětlí stejnodenní pohyb akcií, VIX, zlata, ropy, mědi a výnosů **26%** denních pohybů měn. Zbytek jsou zprávy a toky specifické pro danou měnu (a náhoda).

## 5. Předpovídá dnešek zítřek?

Korelace dnešní změny trhu se ZÍTŘEJŠÍM pohybem páru (poslední sloupec = dnešní pohyb páru). Hodnoty kolem ±0,05 jsou prakticky nula.

| pár | akcie USA (S&P 500) | strach (VIX) | zlato | ropa WTI | med | US 10letý výnos | akcie Japonsko | akcie Evropa | rozdíl 2letých výnosů páru | sám pár |
|---|---|---|---|---|---|---|---|---|---|---|
| EUR/USD | +0.10 | -0.06 | +0.04 | +0.01 | +0.02 | -0.02 | +0.04 | +0.05 | +0.02 | -0.01 |
| USD/JPY | -0.10 | +0.08 | -0.02 | -0.01 | +0.01 | +0.03 | +0.02 | -0.04 | +0.01 | -0.01 |
| GBP/USD | +0.10 | -0.09 | +0.04 | +0.04 | +0.04 | -0.03 | +0.08 | +0.09 | +0.03 | +0.04 |
| USD/CHF | -0.11 | +0.07 | -0.04 | -0.02 | +0.02 | +0.01 | +0.00 | -0.04 | +0.02 | -0.03 |
| AUD/USD | +0.06 | -0.06 | +0.01 | +0.02 | +0.02 | -0.01 | +0.06 | +0.05 | +0.03 | -0.01 |
| USD/CAD | -0.02 | +0.01 | -0.03 | -0.01 | +0.00 | +0.04 | -0.01 | -0.00 | +0.04 | -0.00 |
| NZD/USD | +0.05 | -0.05 | +0.03 | +0.04 | +0.02 | -0.03 | +0.04 | +0.02 | +0.02 | -0.01 |
| EUR/JPY | -0.02 | +0.03 | +0.02 | +0.00 | +0.03 | +0.01 | +0.05 | +0.01 | -0.02 | -0.02 |
| GBP/JPY | -0.00 | -0.01 | +0.02 | +0.03 | +0.04 | +0.00 | +0.07 | +0.04 | -0.00 | +0.04 |
| EUR/GBP | -0.02 | +0.05 | -0.01 | -0.04 | -0.03 | +0.01 | -0.05 | -0.05 | +0.01 | +0.03 |
| EUR/CHF | -0.04 | +0.03 | -0.01 | -0.01 | +0.04 | -0.00 | +0.04 | +0.01 | +0.00 | -0.06 |
| AUD/JPY | -0.03 | +0.01 | +0.00 | +0.01 | +0.03 | +0.01 | +0.07 | +0.02 | +0.04 | -0.01 |

Shlukování: po velkém dni (horních 10 %) přijde další velký den s pravděpodobností **18%** (běžně 10%); korelace velikosti dnešního a zítřejšího pohybu +0.14. Velikost pohybu se tedy předvídat dá (klidné a divoké období), směr skoro ne.

