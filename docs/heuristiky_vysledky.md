# Heuristický model – registr pravidel (2026-10-24)

_Generuje `python scripts/heuristiky.py prepocet`. Data do 2026-09-30. Metodika: docs/HEURISTIKY.md. Výnosy jsou v % ceny po nákladech (spread + skluz), na jednu predikci._

## Stavy pravidel

| Časový rámec | Rozsah | AKTIVNÍ | SLABÁ | NEOVĚŘENÁ | NEFUNKČNÍ | OVERFIT/NESTABILNÍ |
|---|---|---|---|---|---|---|
| 1D | jednotlivé páry | 0 | 183 | 1283 | 1026 | 343 |
| 1D | všechny páry dohromady | 0 | 30 | 5 | 155 | 50 |
| 4H | jednotlivé páry | 0 | 196 | 59 | 1776 | 460 |
| 4H | všechny páry dohromady | 0 | 1 | 0 | 179 | 14 |

## Aktivní pravidla (0)

Žádné pravidlo neprošlo všemi testy.

## Podle typu heuristiky (jednotlivé páry, základní pravidla)

| Typ | Pravidel | Kladných 2019–26 | AKTIVNÍ | SLABÁ | NEFUNKČNÍ | OVERFIT/NESTABILNÍ | NEOVĚŘENÁ |
|---|---|---|---|---|---|---|---|
| trend a struktura | 768 | 23 % | 0 | 16 | 549 | 91 | 112 |
| podpora a odpor | 144 | 45 % | 0 | 20 | 70 | 28 | 26 |
| předchozí maxima a minima | 384 | 35 % | 0 | 31 | 258 | 68 | 27 |
| volatilita (ATR) | 672 | 37 % | 0 | 37 | 258 | 100 | 277 |
| oscilátory (RSI, MACD, Bollinger, stochastic) | 1152 | 40 % | 0 | 116 | 625 | 235 | 176 |
| momentum | 480 | 29 % | 0 | 25 | 330 | 81 | 44 |
| price action (svíčky) | 240 | 38 % | 0 | 28 | 131 | 46 | 35 |
| čas | 240 | 43 % | 0 | 22 | 118 | 54 | 46 |
| fundamenty | 200 | 37 % | 0 | 1 | 54 | 12 | 133 |
| reakce na události | 114 | 59 % | 0 | 11 | 20 | 12 | 71 |
| korelace mezi páry | 288 | 36 % | 0 | 12 | 95 | 38 | 143 |
| fundament + technika | 176 | 46 % | 0 | 2 | 13 | 2 | 159 |
| kombinace (tvoje příklady) | 288 | 20 % | 0 | 8 | 167 | 24 | 89 |

## Kalibrace pravděpodobností (predikce 2019–26)

Úspěšnost všech predikcí 48,2 %. Brierovo skóre (nižší = lepší): statistická 0.2505, heuristická 0.2733, hod mincí (50 %) 0.2500.

| Heuristický odhad | Predikcí | Čekal | Skutečnost |
|---|---|---|---|
| 30–40 % | 131467 | 32,4 % | 49,8 % |
| 40–45 % | 92824 | 40,0 % | 49,2 % |
| 45–50 % | 98138 | 45,0 % | 49,2 % |
| 50–55 % | 104980 | 50,0 % | 48,2 % |
| 55–60 % | 120512 | 55,0 % | 47,6 % |
| 60–65 % | 139011 | 60,0 % | 47,7 % |
| 65–70 % | 129607 | 65,0 % | 47,1 % |
| 70–80 % | 186679 | 72,6 % | 47,7 % |

## Shoda s hlavním modelem (obchody 2019–26)

| Heuristiky | Obchodů | Úspěšnost | Průměr % marže |
|---|---|---|---|
| SHODA | 175 | 90,9 % | +9,0 |
| BEZ NÁZORU | 261 | 89,3 % | +6,5 |
| PROTI | 131 | 90,1 % | +9,9 |

Shoda heuristik s hlavním modelem historicky NEPŘIDÁVALA hodnotu – důvěru v signál nezvyšuje. (p = 0.2969)

## Změny stavů (45)

- osc_rsi_mom-60-L|EURUSD|1D: OVERFIT/NESTABILNÍ → NEFUNKČNÍ (na novějších datech 2019–26 není lepší než náhodné vstupy ve stejném směru)
- mom_ts-60-S|EURUSD|1D: SLABÁ → NEFUNKČNÍ (na novějších datech 2019–26 po nákladech prodělává (průměr -0,004 %))
- tr_ma-50-L|GBPUSD|1D: OVERFIT/NESTABILNÍ → NEFUNKČNÍ (na novějších datech 2019–26 není lepší než náhodné vstupy ve stejném směru)
- vol_klid_pruraz-10-L|USDCHF|1D: OVERFIT/NESTABILNÍ → NEOVĚŘENÁ (nedostatečný historický vzorek (2012–18: 31, 2019–26: 29, potřeba 30))
- mm_pruraz-55-L|USDCAD|1D: OVERFIT/NESTABILNÍ → NEOVĚŘENÁ (nedostatečný historický vzorek (2012–18: 47, 2019–26: 29, potřeba 30))
- mm_falesny-20-S|USDCAD|1D: OVERFIT/NESTABILNÍ → SLABÁ (kladná, ale neprokázaná (p 2019–26 0,132, po korekci na počet pravidel q 1,00))
- komb-1-L|USDCAD|1D: OVERFIT/NESTABILNÍ → NEFUNKČNÍ (na novějších datech 2019–26 po nákladech prodělává (průměr -0,002 %))
- sr_odraz-100-L|NZDUSD|1D: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (funguje jen v letech 2019–26, v letech 2012–18 ne)
- osc_rsi_obrat-14-30-L|NZDUSD|1D: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (funguje jen v letech 2019–26, v letech 2012–18 ne)
- komb-2-L|NZDUSD|1D: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (funguje jen v letech 2019–26, v letech 2012–18 ne)
- mm_predchozi_falesny-L|EURJPY|1D: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (funguje jen v letech 2019–26, v letech 2012–18 ne)
- mom_rada_obrat-4-L|EURJPY|1D: SLABÁ → OVERFIT/NESTABILNÍ (walk-forward: kladných jen 3 z 7 let)
- pa_vnitrni-L|EURJPY|1D: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (funguje jen v letech 2019–26, v letech 2012–18 ne)
- osc_rsi_obrat-2-15-L|EURGBP|1D: NEFUNKČNÍ → SLABÁ (kladná, ale neprokázaná (p 2019–26 0,351, po korekci na počet pravidel q 1,00))
- pa_vnitrni-S|EURGBP|1D: OVERFIT/NESTABILNÍ → NEFUNKČNÍ (na novějších datech 2019–26 po nákladech prodělává (průměr -0,004 %))
- mm_predchozi-L|EURCHF|1D: NEFUNKČNÍ → SLABÁ (kladná, ale neprokázaná (p 2019–26 0,170, po korekci na počet pravidel q 1,00))
- osc_stoch-21-S|EURCHF|1D: SLABÁ → OVERFIT/NESTABILNÍ (walk-forward: kladných jen 4 z 10 let)
- osc_rsi_obrat-2-15-L|AUDJPY|1D: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (funguje jen v letech 2019–26, v letech 2012–18 ne)
- osc_rsi_obrat-14-25-L|EURUSD|4H: OVERFIT/NESTABILNÍ → NEFUNKČNÍ (na novějších datech 2019–26 po nákladech prodělává (průměr -0,006 %))
- osc_macd_x-19-39-9-S|EURUSD|4H: OVERFIT/NESTABILNÍ → NEFUNKČNÍ (na novějších datech 2019–26 po nákladech prodělává (průměr -0,001 %))
- osc_stoch-14-S|GBPUSD|4H: SLABÁ → NEFUNKČNÍ (na novějších datech 2019–26 po nákladech prodělává (průměr -0,001 %))
- pa_vnitrni-S|GBPUSD|4H: SLABÁ → OVERFIT/NESTABILNÍ (kladná jen ve 2 ze 4 období)
- kor_sila_pokr-6-S|GBPUSD|4H: OVERFIT/NESTABILNÍ → SLABÁ (kladná, ale neprokázaná (p 2019–26 0,237, po korekci na počet pravidel q 1,00))
- komb-3-S|AUDUSD|4H: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (kladná jen ve 2 ze 4 období)
- mm_predchozi_falesny-S|NZDUSD|4H: OVERFIT/NESTABILNÍ → NEFUNKČNÍ (na novějších datech 2019–26 po nákladech prodělává (průměr -0,001 %))
- vol_svicka_pokr-1-L|EURJPY|4H: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (kladná jen ve 2 ze 4 období)
- pa_kladivo-L|EURJPY|4H: SLABÁ → OVERFIT/NESTABILNÍ (walk-forward: kladných jen 5 z 11 let)
- cas_asie_pokr-1-L|EURJPY|4H: OVERFIT/NESTABILNÍ → SLABÁ (kladná, ale neprokázaná (p 2019–26 0,209, po korekci na počet pravidel q 1,00))
- tr_struktura-5-L|GBPJPY|4H: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (funguje jen v letech 2019–26, v letech 2012–18 ne)
- sr_odraz-50-L|GBPJPY|4H: OVERFIT/NESTABILNÍ → NEFUNKČNÍ (na novějších datech 2019–26 není lepší než náhodné vstupy ve stejném směru)
- komb-3-L|GBPJPY|4H: NEFUNKČNÍ → SLABÁ (kladná, ale neprokázaná (p 2019–26 0,493, po korekci na počet pravidel q 1,00))
- osc_rsi_obrat-14-25-L|EURGBP|4H: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (walk-forward: kladných jen 2 z 8 let)
- sr_odraz-20-S|EURCHF|4H: SLABÁ → OVERFIT/NESTABILNÍ (kladná jen ve 2 ze 4 období)
- vol_squeeze-15-S|EURCHF|4H: SLABÁ → OVERFIT/NESTABILNÍ (walk-forward: kladných jen 5 z 11 let)
- vol_squeeze-20-S|EURCHF|4H: SLABÁ → OVERFIT/NESTABILNÍ (walk-forward: kladných jen 5 z 11 let)
- vol_prehnani-2-L|EURCHF|4H: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (funguje jen v letech 2019–26, v letech 2012–18 ne)
- osc_bb_pokr-2.5-S|EURCHF|4H: OVERFIT/NESTABILNÍ → NEFUNKČNÍ (na novějších datech 2019–26 po nákladech prodělává (průměr -0,005 %))
- komb-4-S|EURCHF|4H: OVERFIT/NESTABILNÍ → NEFUNKČNÍ (na novějších datech 2019–26 po nákladech prodělává (průměr -0,006 %))
- osc_macd_x-19-39-9-S|AUDJPY|4H: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (funguje jen v letech 2019–26, v letech 2012–18 ne)
- osc_daleko-1.5-L|AUDJPY|4H: OVERFIT/NESTABILNÍ → NEFUNKČNÍ (na novějších datech 2019–26 po nákladech prodělává (průměr -0,001 %))
- vol_klid_pruraz-20-S|VSE|1D: OVERFIT/NESTABILNÍ → NEFUNKČNÍ (na novějších datech 2019–26 po nákladech prodělává (průměr -0,001 %))
- vol_prehnani-1.5-S|VSE|4H: SLABÁ → NEFUNKČNÍ (na novějších datech 2019–26 po nákladech prodělává (průměr -0,000 %))
- tr_pullback-30-L+vol=vysoká|USDJPY|4H: SLABÁ → NEFUNKČNÍ (na novějších datech 2019–26 není lepší než náhodné vstupy ve stejném směru)
- osc_rsi_obrat-2-5-L+vol=vysoká|EURJPY|4H: SLABÁ → NEFUNKČNÍ (na novějších datech 2019–26 není lepší než náhodné vstupy ve stejném směru)
- sr_odraz-20-S+trend=přechod|AUDJPY|4H: OVERFIT/NESTABILNÍ → NEFUNKČNÍ (na novějších datech 2019–26 po nákladech prodělává (průměr -0,002 %))
