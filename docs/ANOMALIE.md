# Zdokumentované jevy na měnovém trhu – přetestováno na našich datech

_Zdroje: Mueller, Tahbaz-Salehi, Vedolin (2017, Journal of Finance) – den FOMC; Krohn, Mueller, Whelan (2024, Journal of Finance) – fixingy; Breedon, Ranaldo (2013) – domácí hodiny; Lustig, Roussanov, Verdelhan (2014) – dolarový carry; Menkhoff a kol. (2012) – momentum a hodnota měn; analýzy bank (BofA, UBS, BNY) – vyvažování na konci měsíce. Data: 12 párů FXCM 2012–2026 (hodinové střední ceny), po nákladech (spread + skluz). Výnosy v % nominálu bez páky; × 30 = % marže._

## A. Den rozhodnutí centrální banky

| strategie | 2012-18 (obchodů / průměr / úspěšnost / t / Sharpe) | 2019-22 | 2023-26 | celkem |
|---|---|---|---|---|
| FOMC: proti dolaru (7 párů s USD), den rozhodnutí | 56 | +0.026 % | 45% | t +0.3 | Sharpe +0.12 | 31 | +0.161 % | 68% | t +1.8 | Sharpe +0.89 | 27 | +0.067 % | 56% | t +0.7 | Sharpe +0.36 | 114 | +0.073 % | 54% | t +1.3 | Sharpe +0.36 |
| ECB: EUR proti dolaru, den rozhodnutí | 68 | -0.076 % | 43% | t -0.7 | Sharpe -0.24 | 32 | -0.048 % | 47% | t -0.5 | Sharpe -0.23 | 27 | -0.013 % | 37% | t -0.1 | Sharpe -0.07 | 127 | -0.056 % | 43% | t -0.8 | Sharpe -0.21 |
| BOJ: JPY proti dolaru, den rozhodnutí | 80 | +0.101 % | 56% | t +0.9 | Sharpe +0.29 | 32 | +0.069 % | 56% | t +0.4 | Sharpe +0.21 | 27 | -0.409 % | 30% | t -2.1 | Sharpe -1.16 | 139 | -0.005 % | 51% | t -0.1 | Sharpe -0.02 |
| BOE: GBP proti dolaru, den rozhodnutí | 58 | +0.029 % | 50% | t +0.3 | Sharpe +0.13 | 32 | -0.051 % | 53% | t -0.3 | Sharpe -0.15 | 27 | -0.017 % | 48% | t -0.1 | Sharpe -0.07 | 117 | -0.003 % | 50% | t -0.0 | Sharpe -0.01 |
| FOMC: proti dolaru, den PŘED rozhodnutím | 56 | +0.033 % | 55% | t +0.8 | Sharpe +0.28 | 31 | -0.005 % | 52% | t -0.1 | Sharpe -0.04 | 27 | -0.076 % | 48% | t -0.8 | Sharpe -0.42 | 114 | -0.003 % | 53% | t -0.1 | Sharpe -0.02 |
| FOMC: proti dolaru, den PO rozhodnutí | 56 | -0.155 % | 43% | t -2.3 | Sharpe -0.89 | 31 | -0.074 % | 55% | t -0.7 | Sharpe -0.37 | 27 | +0.010 % | 48% | t +0.1 | Sharpe +0.06 | 114 | -0.094 % | 47% | t -1.9 | Sharpe -0.51 |
| pro srovnání: proti dolaru v ostatní dny (bez nákladů) | 1743 | -0.014 % | 48% | t -1.5 | Sharpe -0.58 | 1002 | -0.009 % | 50% | t -0.7 | Sharpe -0.35 | 832 | -0.003 % | 49% | t -0.2 | Sharpe -0.12 | 3577 | -0.010 % | 49% | t -1.5 | Sharpe -0.40 |

## B. Konec měsíce: vyvažování podle akcií

Signál 2 obchodní dny před koncem měsíce (zavření New York): výnos S&P 500 od začátku měsíce minus výnos domácího indexu měny. USA lepší → nákup měny proti dolaru, horší → prodej. Výstup v 16:00 Londýn posledního obchodního dne (fixing WM/R) nebo při zavření New York.

| strategie | 2012-18 (obchodů / průměr / úspěšnost / t / Sharpe) | 2019-22 | 2023-26 | celkem |
|---|---|---|---|---|
| 7 párů dohromady, vstup 2 d před koncem, výstup ve fixingu 16:00 Londýn | 85 | +0.001 % | 52% | t +0.0 | Sharpe +0.01 | 49 | +0.016 % | 55% | t +0.3 | Sharpe +0.15 | 42 | -0.032 % | 57% | t -0.7 | Sharpe -0.38 | 176 | -0.002 % | 54% | t -0.1 | Sharpe -0.02 |
| &nbsp;&nbsp;EUR/USD | 83 | -0.009 % | 48% | t -0.1 | Sharpe -0.04 | 48 | +0.022 % | 54% | t +0.3 | Sharpe +0.14 | 42 | +0.075 % | 62% | t +1.1 | Sharpe +0.59 | 173 | +0.020 % | 53% | t +0.4 | Sharpe +0.11 |
| &nbsp;&nbsp;USD/JPY | 83 | -0.053 % | 55% | t -0.5 | Sharpe -0.20 | 48 | -0.163 % | 38% | t -1.6 | Sharpe -0.78 | 42 | +0.053 % | 52% | t +0.4 | Sharpe +0.20 | 173 | -0.058 % | 50% | t -0.9 | Sharpe -0.23 |
| &nbsp;&nbsp;GBP/USD | 82 | +0.048 % | 55% | t +0.7 | Sharpe +0.27 | 48 | +0.013 % | 50% | t +0.1 | Sharpe +0.06 | 42 | -0.009 % | 60% | t -0.1 | Sharpe -0.06 | 172 | +0.024 % | 55% | t +0.5 | Sharpe +0.13 |
| &nbsp;&nbsp;USD/CHF | 83 | +0.034 % | 52% | t +0.4 | Sharpe +0.16 | 48 | +0.121 % | 62% | t +1.4 | Sharpe +0.72 | 42 | -0.084 % | 50% | t -1.0 | Sharpe -0.51 | 173 | +0.029 % | 54% | t +0.6 | Sharpe +0.15 |
| &nbsp;&nbsp;AUD/USD | 83 | -0.068 % | 47% | t -0.8 | Sharpe -0.32 | 48 | -0.096 % | 42% | t -0.8 | Sharpe -0.40 | 42 | -0.088 % | 48% | t -0.8 | Sharpe -0.41 | 173 | -0.080 % | 46% | t -1.4 | Sharpe -0.37 |
| &nbsp;&nbsp;USD/CAD | 83 | -0.004 % | 46% | t -0.1 | Sharpe -0.02 | 48 | +0.019 % | 50% | t +0.2 | Sharpe +0.11 | 42 | -0.001 % | 50% | t -0.0 | Sharpe -0.01 | 173 | +0.003 % | 48% | t +0.1 | Sharpe +0.02 |
| &nbsp;&nbsp;NZD/USD | 83 | +0.039 % | 51% | t +0.4 | Sharpe +0.15 | 48 | +0.118 % | 56% | t +1.0 | Sharpe +0.50 | 42 | -0.168 % | 48% | t -1.4 | Sharpe -0.72 | 173 | +0.011 % | 51% | t +0.2 | Sharpe +0.04 |
| 7 párů dohromady, vstup 1 d před koncem, výstup ve fixingu 16:00 Londýn | 85 | -0.018 % | 48% | t -0.7 | Sharpe -0.26 | 49 | -0.038 % | 45% | t -1.1 | Sharpe -0.54 | 42 | +0.021 % | 50% | t +0.5 | Sharpe +0.29 | 176 | -0.014 % | 48% | t -0.8 | Sharpe -0.20 |
| 7 párů dohromady, vstup 2 d před koncem, výstup při zavření NY | 85 | -0.012 % | 45% | t -0.3 | Sharpe -0.12 | 49 | -0.013 % | 45% | t -0.2 | Sharpe -0.11 | 42 | -0.024 % | 48% | t -0.5 | Sharpe -0.27 | 176 | -0.015 % | 45% | t -0.6 | Sharpe -0.15 |
| 7 párů dohromady, vstup 1 d před koncem, výstup při zavření NY | 85 | -0.032 % | 52% | t -1.2 | Sharpe -0.47 | 49 | -0.046 % | 45% | t -1.2 | Sharpe -0.59 | 42 | +0.025 % | 45% | t +0.6 | Sharpe +0.31 | 176 | -0.022 % | 48% | t -1.1 | Sharpe -0.30 |

## C. Hodinové vzorce

Dolar proti 7 měnám (průměr), výnos v daném okně každý obchodní den, po nákladech na jeden obchod (vstup + výstup). Časy jsou londýnské / tokijské místní.

| strategie | 2012-18 (obchodů / průměr / úspěšnost / t / Sharpe) | 2019-22 | 2023-26 | celkem |
|---|---|---|---|---|
| Londýn 14→16 h: koupit dolar před fixingem | 1802 | -0.016 % | 45% | t -4.1 | Sharpe -1.52 | 1034 | -0.017 % | 44% | t -2.7 | Sharpe -1.36 | 859 | -0.022 % | 44% | t -3.5 | Sharpe -1.91 | 3695 | -0.018 % | 45% | t -5.9 | Sharpe -1.55 |
| &nbsp;&nbsp;totéž bez nákladů | 1802 | -0.000 % | 50% | t -0.1 | Sharpe -0.04 | 1034 | -0.001 % | 48% | t -0.1 | Sharpe -0.06 | 859 | -0.005 % | 49% | t -0.7 | Sharpe -0.40 | 3695 | -0.001 % | 49% | t -0.5 | Sharpe -0.13 |
| Londýn 16→18 h: prodat dolar po fixingu | 1802 | -0.012 % | 43% | t -4.3 | Sharpe -1.61 | 1034 | -0.019 % | 42% | t -4.7 | Sharpe -2.31 | 859 | -0.018 % | 43% | t -4.4 | Sharpe -2.38 | 3695 | -0.015 % | 43% | t -7.6 | Sharpe -2.00 |
| &nbsp;&nbsp;totéž bez nákladů | 1802 | +0.004 % | 51% | t +1.5 | Sharpe +0.54 | 1034 | -0.003 % | 49% | t -0.7 | Sharpe -0.33 | 859 | -0.001 % | 48% | t -0.3 | Sharpe -0.15 | 3695 | +0.001 % | 50% | t +0.5 | Sharpe +0.12 |
| Londýn 16→20 h: prodat dolar po fixingu | 1796 | -0.009 % | 46% | t -2.1 | Sharpe -0.78 | 1034 | -0.017 % | 43% | t -2.9 | Sharpe -1.43 | 859 | -0.017 % | 45% | t -2.9 | Sharpe -1.57 | 3689 | -0.013 % | 45% | t -4.3 | Sharpe -1.13 |
| &nbsp;&nbsp;totéž bez nákladů | 1796 | +0.006 % | 51% | t +1.4 | Sharpe +0.54 | 1034 | -0.000 % | 49% | t -0.0 | Sharpe -0.02 | 859 | +0.000 % | 50% | t +0.1 | Sharpe +0.04 | 3689 | +0.003 % | 50% | t +1.0 | Sharpe +0.27 |
| Tokio 8→10 h: koupit dolar před fixingem 9:55 | 1799 | -0.013 % | 43% | t -6.5 | Sharpe -2.44 | 1033 | -0.011 % | 43% | t -3.4 | Sharpe -1.70 | 859 | -0.021 % | 40% | t -6.5 | Sharpe -3.52 | 3691 | -0.015 % | 42% | t -9.4 | Sharpe -2.46 |
| &nbsp;&nbsp;totéž bez nákladů | 1799 | +0.003 % | 52% | t +1.2 | Sharpe +0.46 | 1033 | +0.006 % | 52% | t +1.7 | Sharpe +0.85 | 859 | -0.004 % | 49% | t -1.3 | Sharpe -0.72 | 3691 | +0.002 % | 51% | t +1.1 | Sharpe +0.30 |
| Tokio 10→13 h: prodat dolar po fixingu | 1800 | -0.006 % | 47% | t -2.0 | Sharpe -0.75 | 1034 | -0.007 % | 47% | t -1.8 | Sharpe -0.89 | 859 | -0.017 % | 43% | t -4.2 | Sharpe -2.26 | 3693 | -0.009 % | 46% | t -4.4 | Sharpe -1.14 |
| &nbsp;&nbsp;totéž bez nákladů | 1800 | +0.010 % | 54% | t +3.5 | Sharpe +1.30 | 1034 | +0.010 % | 54% | t +2.8 | Sharpe +1.37 | 859 | -0.000 % | 50% | t -0.0 | Sharpe -0.00 | 3693 | +0.008 % | 53% | t +3.9 | Sharpe +1.02 |
| EUR/USD: prodat euro v evropských hodinách (Londýn 8→13 h) | 1796 | +0.017 % | 51% | t +2.7 | Sharpe +0.99 | 1034 | -0.001 % | 50% | t -0.1 | Sharpe -0.07 | 859 | -0.004 % | 49% | t -0.5 | Sharpe -0.29 | 3689 | +0.007 % | 50% | t +1.7 | Sharpe +0.44 |
| &nbsp;&nbsp;totéž bez nákladů | 1796 | +0.027 % | 53% | t +4.2 | Sharpe +1.58 | 1034 | +0.010 % | 52% | t +1.3 | Sharpe +0.62 | 859 | +0.007 % | 51% | t +0.9 | Sharpe +0.50 | 3689 | +0.017 % | 52% | t +4.2 | Sharpe +1.10 |
| EUR/USD: koupit euro v amerických hodinách (New York 8→16 h) | 1790 | +0.010 % | 51% | t +1.1 | Sharpe +0.42 | 1030 | -0.002 % | 47% | t -0.2 | Sharpe -0.09 | 857 | -0.002 % | 49% | t -0.1 | Sharpe -0.07 | 3677 | +0.004 % | 50% | t +0.7 | Sharpe +0.18 |
| &nbsp;&nbsp;totéž bez nákladů | 1790 | +0.020 % | 52% | t +2.2 | Sharpe +0.83 | 1030 | +0.009 % | 50% | t +0.8 | Sharpe +0.41 | 857 | +0.009 % | 51% | t +0.8 | Sharpe +0.45 | 3677 | +0.014 % | 51% | t +2.4 | Sharpe +0.63 |
| USD/JPY: koupit dolar v tokijských hodinách (Tokio 9→15 h) | 1798 | -0.032 % | 45% | t -4.7 | Sharpe -1.77 | 1034 | -0.016 % | 46% | t -2.1 | Sharpe -1.06 | 859 | -0.010 % | 49% | t -1.0 | Sharpe -0.54 | 3691 | -0.022 % | 46% | t -4.9 | Sharpe -1.28 |
| &nbsp;&nbsp;totéž bez nákladů | 1798 | -0.019 % | 48% | t -2.8 | Sharpe -1.07 | 1034 | -0.005 % | 49% | t -0.6 | Sharpe -0.31 | 859 | -0.001 % | 50% | t -0.1 | Sharpe -0.07 | 3691 | -0.011 % | 49% | t -2.4 | Sharpe -0.63 |
| GBP/USD: prodat libru v londýnských hodinách (8→13 h) | 1799 | -0.000 % | 50% | t -0.0 | Sharpe -0.02 | 1034 | -0.006 % | 49% | t -0.6 | Sharpe -0.29 | 859 | -0.011 % | 48% | t -1.4 | Sharpe -0.75 | 3692 | -0.004 % | 49% | t -0.9 | Sharpe -0.23 |
| &nbsp;&nbsp;totéž bez nákladů | 1799 | +0.011 % | 52% | t +1.4 | Sharpe +0.54 | 1034 | +0.006 % | 51% | t +0.6 | Sharpe +0.29 | 859 | +0.002 % | 51% | t +0.2 | Sharpe +0.10 | 3692 | +0.007 % | 52% | t +1.5 | Sharpe +0.38 |

## D. Dolarový carry a E. pořadí měn (měsíčně)

Výnos za měsíc včetně úrokového rozdílu (sazby OECD, zpoždění 2 měsíce) a nákladů.

| strategie | 2012-18 (obchodů / průměr / úspěšnost / t / Sharpe) | 2019-22 | 2023-26 | celkem |
|---|---|---|---|---|
| D. dolarový carry | 83 | -0.122 % | 53% | t -0.6 | Sharpe -0.23 | 48 | +0.112 % | 54% | t +0.4 | Sharpe +0.19 | 43 | +0.110 % | 56% | t +0.4 | Sharpe +0.19 | 174 | -0.000 % | 54% | t -0.0 | Sharpe -0.00 |
| carry (sazby) | 83 | -0.019 % | 48% | t -0.1 | Sharpe -0.03 | 48 | +0.023 % | 48% | t +0.1 | Sharpe +0.05 | 43 | +0.407 % | 65% | t +1.5 | Sharpe +0.81 | 174 | +0.098 % | 52% | t +0.6 | Sharpe +0.17 |
| momentum 3 měsíce | 80 | -0.388 % | 49% | t -1.5 | Sharpe -0.58 | 48 | -0.411 % | 44% | t -1.3 | Sharpe -0.64 | 43 | -0.021 % | 60% | t -0.1 | Sharpe -0.04 | 171 | -0.302 % | 50% | t -1.8 | Sharpe -0.48 |
| momentum 12 měsíců | 71 | -0.127 % | 52% | t -0.5 | Sharpe -0.22 | 48 | -0.111 % | 52% | t -0.3 | Sharpe -0.17 | 43 | +0.049 % | 58% | t +0.2 | Sharpe +0.11 | 162 | -0.075 % | 54% | t -0.5 | Sharpe -0.13 |
| hodnota (obrat 5 let) | 23 | -0.045 % | 43% | t -0.1 | Sharpe -0.09 | 48 | +0.291 % | 52% | t +0.9 | Sharpe +0.44 | 43 | -0.437 % | 33% | t -2.1 | Sharpe -1.11 | 114 | -0.051 % | 43% | t -0.3 | Sharpe -0.09 |
| E. kombinace carry + momentum 12 m + hodnota | 23 | -0.195 % | 43% | t -0.8 | Sharpe -0.54 | 48 | +0.068 % | 48% | t +0.5 | Sharpe +0.24 | 43 | +0.006 % | 51% | t +0.1 | Sharpe +0.03 | 114 | -0.008 % | 48% | t -0.1 | Sharpe -0.03 |
