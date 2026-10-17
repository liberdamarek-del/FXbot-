# Heuristický model – registr pravidel (2026-10-17)

_Generuje `python scripts/heuristiky.py prepocet`. Data do 2026-10-09. Metodika: docs/HEURISTIKY.md. Výnosy jsou v % ceny po nákladech (spread + skluz), na jednu predikci._

## Stavy pravidel

| Časový rámec | Rozsah | AKTIVNÍ | SLABÁ | NEOVĚŘENÁ | NEFUNKČNÍ | OVERFIT/NESTABILNÍ |
|---|---|---|---|---|---|---|
| 1D | jednotlivé páry | 0 | 183 | 1281 | 1029 | 342 |
| 1D | všechny páry dohromady | 0 | 30 | 5 | 154 | 51 |
| 4H | jednotlivé páry | 0 | 201 | 59 | 1772 | 459 |
| 4H | všechny páry dohromady | 0 | 2 | 0 | 178 | 14 |

## Aktivní pravidla (0)

Žádné pravidlo neprošlo všemi testy.

## Podle typu heuristiky (jednotlivé páry, základní pravidla)

| Typ | Pravidel | Kladných 2019–26 | AKTIVNÍ | SLABÁ | NEFUNKČNÍ | OVERFIT/NESTABILNÍ | NEOVĚŘENÁ |
|---|---|---|---|---|---|---|---|
| trend a struktura | 768 | 23 % | 0 | 16 | 549 | 91 | 112 |
| podpora a odpor | 144 | 44 % | 0 | 21 | 70 | 27 | 26 |
| předchozí maxima a minima | 384 | 34 % | 0 | 29 | 259 | 70 | 26 |
| volatilita (ATR) | 672 | 37 % | 0 | 39 | 260 | 97 | 276 |
| oscilátory (RSI, MACD, Bollinger, stochastic) | 1152 | 40 % | 0 | 117 | 624 | 235 | 176 |
| momentum | 480 | 29 % | 0 | 27 | 329 | 80 | 44 |
| price action (svíčky) | 240 | 38 % | 0 | 30 | 131 | 44 | 35 |
| čas | 240 | 43 % | 0 | 21 | 118 | 55 | 46 |
| fundamenty | 200 | 37 % | 0 | 1 | 54 | 12 | 133 |
| reakce na události | 114 | 59 % | 0 | 11 | 20 | 12 | 71 |
| korelace mezi páry | 288 | 36 % | 0 | 11 | 95 | 39 | 143 |
| fundament + technika | 176 | 46 % | 0 | 2 | 13 | 2 | 159 |
| kombinace (tvoje příklady) | 288 | 21 % | 0 | 7 | 168 | 24 | 89 |

## Kalibrace pravděpodobností (predikce 2019–26)

Úspěšnost všech predikcí 48,2 %. Brierovo skóre (nižší = lepší): statistická 0.2505, heuristická 0.2732, hod mincí (50 %) 0.2500.

| Heuristický odhad | Predikcí | Čekal | Skutečnost |
|---|---|---|---|
| 30–40 % | 131894 | 32,4 % | 49,8 % |
| 40–45 % | 93250 | 40,0 % | 49,3 % |
| 45–50 % | 98492 | 45,0 % | 49,2 % |
| 50–55 % | 105356 | 50,0 % | 48,2 % |
| 55–60 % | 120945 | 55,0 % | 47,6 % |
| 60–65 % | 139674 | 60,0 % | 47,7 % |
| 65–70 % | 130075 | 65,0 % | 47,1 % |
| 70–80 % | 187363 | 72,6 % | 47,7 % |

## Shoda s hlavním modelem (obchody 2019–26)

| Heuristiky | Obchodů | Úspěšnost | Průměr % marže |
|---|---|---|---|
| SHODA | 175 | 90,9 % | +9,0 |
| BEZ NÁZORU | 261 | 89,3 % | +6,5 |
| PROTI | 134 | 90,3 % | +9,9 |

Shoda heuristik s hlavním modelem historicky NEPŘIDÁVALA hodnotu – důvěru v signál nezvyšuje. (p = 0.2819)

## Změny stavů (26)

- tr_ma-50-L|GBPUSD|1D: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (funguje jen v letech 2019–26, v letech 2012–18 ne)
- mm_pruraz-55-L|USDCAD|1D: NEOVĚŘENÁ → OVERFIT/NESTABILNÍ (funguje jen v letech 2019–26, v letech 2012–18 ne)
- tr_struktura-5-S|NZDUSD|1D: OVERFIT/NESTABILNÍ → NEFUNKČNÍ (na novějších datech 2019–26 není lepší než náhodné vstupy ve stejném směru)
- osc_rsi_obrat-14-30-L|NZDUSD|1D: OVERFIT/NESTABILNÍ → NEFUNKČNÍ (na novějších datech 2019–26 po nákladech prodělává (průměr -0,008 %))
- komb-2-L|NZDUSD|1D: OVERFIT/NESTABILNÍ → NEFUNKČNÍ (na novějších datech 2019–26 po nákladech prodělává (průměr -0,008 %))
- mm_predchozi_falesny-L|EURJPY|1D: OVERFIT/NESTABILNÍ → NEFUNKČNÍ (na novějších datech 2019–26 není lepší než náhodné vstupy ve stejném směru)
- mom_rada_obrat-4-L|EURJPY|1D: OVERFIT/NESTABILNÍ → SLABÁ (kladná, ale neprokázaná (p 2019–26 0,456, po korekci na počet pravidel q 1,00))
- osc_rsi_obrat-2-15-L|EURGBP|1D: SLABÁ → NEFUNKČNÍ (na novějších datech 2019–26 po nákladech prodělává (průměr -0,003 %))
- pa_vnitrni-S|EURGBP|1D: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (funguje jen v letech 2019–26, v letech 2012–18 ne)
- mm_predchozi-L|EURCHF|1D: SLABÁ → NEFUNKČNÍ (na novějších datech 2019–26 po nákladech prodělává (průměr -0,012 %))
- osc_stoch-21-S|EURCHF|1D: OVERFIT/NESTABILNÍ → SLABÁ (kladná, ale neprokázaná (p 2019–26 0,213, po korekci na počet pravidel q 1,00))
- osc_rsi_obrat-14-25-L|EURUSD|4H: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (funguje jen v letech 2019–26, v letech 2012–18 ne)
- vol_squeeze-15-L|USDJPY|4H: SLABÁ → NEFUNKČNÍ (na novějších datech 2019–26 není lepší než náhodné vstupy ve stejném směru)
- pa_vnitrni-S|GBPUSD|4H: OVERFIT/NESTABILNÍ → SLABÁ (kladná, ale neprokázaná (p 2019–26 0,168, po korekci na počet pravidel q 1,00))
- kor_sila_pokr-6-S|GBPUSD|4H: SLABÁ → OVERFIT/NESTABILNÍ (kladná jen ve 2 ze 4 období)
- osc_rsi_obrat-2-5-L|AUDUSD|4H: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (walk-forward: kladných jen 4 z 9 let)
- osc_rsi_obrat-2-10-L|AUDUSD|4H: OVERFIT/NESTABILNÍ → SLABÁ (kladná, ale neprokázaná (p 2019–26 0,063, po korekci na počet pravidel q 1,00))
- mm_predchozi_falesny-S|NZDUSD|4H: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (kladná jen ve 2 ze 4 období)
- pa_kladivo-L|EURJPY|4H: OVERFIT/NESTABILNÍ → SLABÁ (kladná, ale neprokázaná (p 2019–26 0,388, po korekci na počet pravidel q 1,00))
- tr_struktura-5-L|GBPJPY|4H: OVERFIT/NESTABILNÍ → NEFUNKČNÍ (na novějších datech 2019–26 není lepší než náhodné vstupy ve stejném směru)
- vol_prehnani-2-L|EURCHF|4H: OVERFIT/NESTABILNÍ → NEFUNKČNÍ (na novějších datech 2019–26 po nákladech prodělává (průměr -0,000 %))
- vol_klid_pruraz-20-S|VSE|1D: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (funguje jen v letech 2019–26, v letech 2012–18 ne)
- f_sazby-0.25-L|VSE|1D: OVERFIT/NESTABILNÍ → NEFUNKČNÍ (na novějších datech 2019–26 není lepší než náhodné vstupy ve stejném směru)
- tr_ma-100-L+trend=trend|USDJPY|4H: OVERFIT/NESTABILNÍ → NEFUNKČNÍ (na novějších datech 2019–26 není lepší než náhodné vstupy ve stejném směru)
- tr_pullback-30-L+vol=vysoká|USDJPY|4H: NEFUNKČNÍ → SLABÁ (kladná, ale neprokázaná (p 2019–26 0,452, po korekci na počet pravidel q 1,00))
- sr_odraz-20-S+trend=přechod|AUDJPY|4H: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (walk-forward: kladných jen 5 z 11 let)
