# Fáze 2: tabulky DSR a PBO (generováno `scripts/faze2_analyza.py zprava`)

_Registr: 332 pokusů, poslední otisk `a0186065c31ad59f`; trezor od 2026-10-01 zavřený, data do 2026-09. Pozorování = měsíc (93 měsíců: 2019-01 až 2022-12 a 2023-01 až 2026-09). DSR = pravděpodobnost, že skutečný Sharpe je větší než nejlepší ze N pokusů, který by vyšel čistým šumem._

## max: CH-009 (12 paru) + velikost_podle_volatility + signal_i_rsi3 + zavrit_pred_cb_zisk

Sharpe měsíční 0.432 (roční 1.50), šikmost 0.03, špičatost 4.47, průměr měsíčně +3.01%, směrodatná odchylka 6.97%, nejhorší měsíc -17.2%; Sharpe 5–95% (bootstrap) 0.26–0.63.

| počet pokusů N | práh SR0 (měsíčně) | DSR |
|---|---|---|
| 1 | 0.000 | 1.000 |
| 10 | 0.164 | 0.992 |
| 30 | 0.216 | 0.973 |
| 100 | 0.264 | 0.934 |
| 288 | 0.301 | 0.880 |
| 332 | 0.305 | 0.872 |
| 1000 | 0.339 | 0.796 |
| 5000 | 0.384 | 0.664 |

Odhad efektivního počtu nezávislých pokusů (Bailey, López de Prado 2014): 118 použitelných variant, průměrná korelace jejich měsíčních řad 0.77 → **28** nezávislých pokusů; rozptyl Sharpe variant 0.0040 (čistý šum by dal 0.0109); Sharpe variant 5/50/95 %: 0.28 / 0.40 / 0.48.

| čtení | N | rozptyl | SR0 | DSR | zbývá ročně (hrubě) |
|---|---|---|---|---|---|
| nominálně 332, rozptyl čistého šumu (pravidlo zadání) | 332 | 1/(T-1) | 0.305 | **0.872** | +11.1% |
| nominálně 332, rozptyl variant | 332 | 0.0040 | 0.185 | **0.986** | +22.7% |
| efektivní N, rozptyl čistého šumu | 28 | 1/(T-1) | 0.213 | **0.975** | +19.9% |
| efektivní N, rozptyl variant | 28 | 0.0040 | 0.129 | **0.997** | +28.5% |

Jak se verdikt mění se skutečným počtem pokusů (ten neznám: registr jich eviduje 332, jen `profit_lab2` prohledal 213 840 systémů):

| N pokusů | 12 | 30 | 100 | 332 | 1000 | 5000 | 20000 | 213840 |
|---|---|---|---|---|---|---|---|---|
| DSR, rozptyl čistého šumu | 0.990 | 0.973 | 0.934 | 0.872 | 0.796 | 0.664 | 0.543 | 0.350 |
| DSR, rozptyl variant | 0.998 | 0.996 | 0.993 | 0.986 | 0.979 | 0.962 | 0.944 | 0.901 |

Kolik NOVÝCH měsíců dat (mimo trezor, jeden předem daný test) by stačilo na 95% jistotu, že skutečný Sharpe je kladný: 18 měsíců, kdyby byl skutečný Sharpe jako naměřený (0.43); 34 měsíců, kdyby byl 0,30; 172 měsíců, kdyby byl jen takový, jaký zbývá po korekci (0.13).


Aby DSR při N = 332 dosáhl 0,95, musel by měsíční Sharpe být aspoň 0.493 (roční 1.71); sampion má 0.432.

## mesicne: CH-009 (12 paru) + stop_4_atr + signal_i_rsi3 + v3_zavrit_pred_cb_zisk

Sharpe měsíční 0.438 (roční 1.52), šikmost -0.21, špičatost 6.81, průměr měsíčně +3.02%, směrodatná odchylka 6.89%, nejhorší měsíc -22.4%; Sharpe 5–95% (bootstrap) 0.26–0.66.

| počet pokusů N | práh SR0 (měsíčně) | DSR |
|---|---|---|
| 1 | 0.000 | 1.000 |
| 10 | 0.164 | 0.988 |
| 30 | 0.216 | 0.965 |
| 100 | 0.264 | 0.923 |
| 288 | 0.301 | 0.870 |
| 332 | 0.305 | 0.861 |
| 1000 | 0.339 | 0.790 |
| 5000 | 0.384 | 0.669 |

Odhad efektivního počtu nezávislých pokusů (Bailey, López de Prado 2014): 72 použitelných variant, průměrná korelace jejich měsíčních řad 0.84 → **12** nezávislých pokusů; rozptyl Sharpe variant 0.0028 (čistý šum by dal 0.0109); Sharpe variant 5/50/95 %: 0.29 / 0.43 / 0.47.

| čtení | N | rozptyl | SR0 | DSR | zbývá ročně (hrubě) |
|---|---|---|---|---|---|
| nominálně 332, rozptyl čistého šumu (pravidlo zadání) | 332 | 1/(T-1) | 0.305 | **0.861** | +11.5% |
| nominálně 332, rozptyl variant | 332 | 0.0028 | 0.154 | **0.990** | +26.1% |
| efektivní N, rozptyl čistého šumu | 12 | 1/(T-1) | 0.174 | **0.985** | +24.2% |
| efektivní N, rozptyl variant | 12 | 0.0028 | 0.088 | **0.998** | +33.1% |

Jak se verdikt mění se skutečným počtem pokusů (ten neznám: registr jich eviduje 332, jen `profit_lab2` prohledal 213 840 systémů):

| N pokusů | 12 | 30 | 100 | 332 | 1000 | 5000 | 20000 | 213840 |
|---|---|---|---|---|---|---|---|---|
| DSR, rozptyl čistého šumu | 0.985 | 0.965 | 0.923 | 0.861 | 0.790 | 0.669 | 0.558 | 0.381 |
| DSR, rozptyl variant | 0.998 | 0.996 | 0.994 | 0.990 | 0.985 | 0.977 | 0.968 | 0.947 |

Kolik NOVÝCH měsíců dat (mimo trezor, jeden předem daný test) by stačilo na 95% jistotu, že skutečný Sharpe je kladný: 21 měsíců, kdyby byl skutečný Sharpe jako naměřený (0.44); 37 měsíců, kdyby byl 0,30; 164 měsíců, kdyby byl jen takový, jaký zbývá po korekci (0.13).


Aby DSR při N = 332 dosáhl 0,95, musel by měsíční Sharpe být aspoň 0.515 (roční 1.78); sampion má 0.438.

## Základ (CH-009 bez přijatých změn) proti dnešnímu šampionovi

Co k pravidlu, jak bylo předem zapsané (`self_learn.START`), přidaly přijaté pokusy. Stejná dvě okna brany, marže se vybírají stejným walk-forward postupem. PSR(0) = pravděpodobnost, že skutečný Sharpe je kladný, bez korekce na počet pokusů.

| profil | řada | měsíců | Sharpe měsíčně | PSR(0) | 2019–22 ročně / propad | 2023–26 ročně / propad |
|---|---|---|---|---|---|---|
| max | základ CH-009 | 93 | 0.301 | 0.997 | +37.5% / 30% | +6.8% / 24% |
| max | šampion | 93 | 0.432 | 1.000 | +62.8% / 24% | +19.7% / 28% |
| mesicne | základ CH-009 | 48 | 0.415 | 0.996 | +37.5% / 30% | bez platných marží (okno chybí) |
| mesicne | šampion | 93 | 0.438 | 1.000 | +53.0% / 29% | +28.2% / 24% |

## Výsledky jednotlivých pokusů aplikovaných na šampiona — max

144 pokusů z registru (`EXPERIMENTS`), každý jako změna dnešního šampiona. Do srovnání vstupuje 118; mimo: 8 nelze na šampiona použít, 0 nemá platné marže v jednom z oken (řada by byla kratší, nesrovnatelná), 8 dává přesně řadu šampiona (už je v něm, nebo nic nemění), 9 je kopie jiné varianty, 1 neobchoduje. Z porovnaných má 2 DSR(N = 332) ≥ 0,95. Top 12 podle měsíčního Sharpe (DSR podle zadání, N = 332):

| pokus | Sharpe měsíčně | DSR (N = 332) | ročně 2023–26 |
|---|---|---|---|
| silny_dve_casti | 0.527 | 0.978 | +31.8% |
| cil_06_atr | 0.523 | 0.959 | +24.1% |
| vix_bez_skoku | 0.487 | 0.950 | +16.4% |
| stop_4_atr | 0.487 | 0.931 | +27.0% |
| r32_vol_extrem_80 | 0.479 | 0.925 | +21.4% |
| stop_3_na_zavreni_2 | 0.479 | 0.922 | +25.0% |
| silny_i_pruraz | 0.478 | 0.925 | +28.6% |
| stop_na_zavreni_125 | 0.477 | 0.927 | +24.6% |
| stop_na_zavreni_15 | 0.465 | 0.903 | +24.5% |
| silny_cil_1_atr | 0.459 | 0.926 | +18.8% |
| stop_5_atr | 0.458 | 0.858 | +24.9% |
| vyzkum_udalosti | 0.454 | 0.900 | +25.9% |

## Výsledky jednotlivých pokusů aplikovaných na šampiona — mesicne

144 pokusů z registru (`EXPERIMENTS`), každý jako změna dnešního šampiona. Do srovnání vstupuje 72; mimo: 8 nelze na šampiona použít, 50 nemá platné marže v jednom z oken (řada by byla kratší, nesrovnatelná), 8 dává přesně řadu šampiona (už je v něm, nebo nic nemění), 6 je kopie jiné varianty, 0 neobchoduje. Z porovnaných má 0 DSR(N = 332) ≥ 0,95. Top 12 podle měsíčního Sharpe (DSR podle zadání, N = 332):

| pokus | Sharpe měsíčně | DSR (N = 332) | ročně 2023–26 |
|---|---|---|---|
| v3_velikost_podle_volatility | 0.487 | 0.931 | +27.0% |
| silny_i_pruraz | 0.481 | 0.942 | +30.5% |
| r27_fibonacci | 0.480 | 0.939 | +28.0% |
| r27_martingale_15x | 0.475 | 0.935 | +29.1% |
| r32_konec_teze_sazby | 0.473 | 0.935 | +26.4% |
| r26_bez_min_cile | 0.470 | 0.929 | +28.6% |
| r27_dalembert | 0.462 | 0.913 | +29.8% |
| r25_objem_i_cil | 0.460 | 0.901 | +29.1% |
| silny_dve_casti | 0.458 | 0.907 | +27.2% |
| prah_sazeb_015 | 0.457 | 0.916 | +18.7% |
| r25_min_cil_v_cene | 0.455 | 0.901 | +28.2% |
| pozdni_cil_10d_025 | 0.454 | 0.901 | +28.6% |

## PBO (CSCV) — max

Strategií: 119 (sampion + varianty registru použité na sampiona), 93 měsíců. Variant lepších než sampion (podle Sharpe): 23; Sharpe sampiona 0.432, medián variant 0.399, nejlepší varianta 0.527.

| bloků S | kombinací | PBO |
|---|---|---|
| 8 | 70 | **0.54** |
| 10 | 252 | **0.63** |
| 12 | 924 | **0.60** |
| 16 | 12870 | **0.63** |

Kolísání odhadu PBO (S = 12, 60 přeskupení měsíců uvnitř bloků): 5 % 0.25, medián 0.60, 95 % 0.83.

## PBO (CSCV) — mesicne

Strategií: 73 (sampion + varianty registru použité na sampiona), 93 měsíců. Variant lepších než sampion (podle Sharpe): 22; Sharpe sampiona 0.438, medián variant 0.428, nejlepší varianta 0.487.

| bloků S | kombinací | PBO |
|---|---|---|
| 8 | 70 | **0.90** |
| 10 | 252 | **0.82** |
| 12 | 924 | **0.81** |
| 16 | 12870 | **0.79** |

Kolísání odhadu PBO (S = 12, 60 přeskupení měsíců uvnitř bloků): 5 % 0.37, medián 0.70, 95 % 0.89.

