# Heuristický model – registr pravidel (2026-10-11)

_Generuje `python scripts/heuristiky.py prepocet`. Data do 2026-10-02. Metodika: docs/HEURISTIKY.md. Výnosy jsou v % ceny po nákladech (spread + skluz), na jednu predikci._

## Stavy pravidel

| Časový rámec | Rozsah | AKTIVNÍ | SLABÁ | NEOVĚŘENÁ | NEFUNKČNÍ | OVERFIT/NESTABILNÍ |
|---|---|---|---|---|---|---|
| 1D | jednotlivé páry | 0 | 183 | 1282 | 1025 | 345 |
| 1D | všechny páry dohromady | 0 | 30 | 5 | 154 | 51 |
| 4H | jednotlivé páry | 0 | 199 | 59 | 1773 | 460 |
| 4H | všechny páry dohromady | 0 | 2 | 0 | 178 | 14 |

## Aktivní pravidla (0)

Žádné pravidlo neprošlo všemi testy.

## Podle typu heuristiky (jednotlivé páry, základní pravidla)

| Typ | Pravidel | Kladných 2019–26 | AKTIVNÍ | SLABÁ | NEFUNKČNÍ | OVERFIT/NESTABILNÍ | NEOVĚŘENÁ |
|---|---|---|---|---|---|---|---|
| trend a struktura | 768 | 23 % | 0 | 16 | 548 | 92 | 112 |
| podpora a odpor | 144 | 44 % | 0 | 21 | 70 | 27 | 26 |
| předchozí maxima a minima | 384 | 34 % | 0 | 30 | 258 | 69 | 27 |
| volatilita (ATR) | 672 | 38 % | 0 | 40 | 258 | 98 | 276 |
| oscilátory (RSI, MACD, Bollinger, stochastic) | 1152 | 40 % | 0 | 116 | 624 | 236 | 176 |
| momentum | 480 | 29 % | 0 | 26 | 329 | 81 | 44 |
| price action (svíčky) | 240 | 38 % | 0 | 28 | 132 | 45 | 35 |
| čas | 240 | 43 % | 0 | 21 | 118 | 55 | 46 |
| fundamenty | 200 | 37 % | 0 | 1 | 54 | 12 | 133 |
| reakce na události | 114 | 59 % | 0 | 11 | 20 | 12 | 71 |
| korelace mezi páry | 288 | 36 % | 0 | 12 | 95 | 38 | 143 |
| fundament + technika | 176 | 46 % | 0 | 2 | 13 | 2 | 159 |
| kombinace (tvoje příklady) | 288 | 22 % | 0 | 7 | 167 | 25 | 89 |

## Kalibrace pravděpodobností (predikce 2019–26)

Úspěšnost všech predikcí 48,2 %. Brierovo skóre (nižší = lepší): statistická 0.2505, heuristická 0.2732, hod mincí (50 %) 0.2500.

| Heuristický odhad | Predikcí | Čekal | Skutečnost |
|---|---|---|---|
| 30–40 % | 131644 | 32,4 % | 49,8 % |
| 40–45 % | 92974 | 40,0 % | 49,2 % |
| 45–50 % | 98267 | 45,0 % | 49,2 % |
| 50–55 % | 105100 | 50,0 % | 48,2 % |
| 55–60 % | 120678 | 55,0 % | 47,6 % |
| 60–65 % | 139215 | 60,0 % | 47,8 % |
| 65–70 % | 129748 | 65,0 % | 47,1 % |
| 70–80 % | 186959 | 72,6 % | 47,7 % |

## Shoda s hlavním modelem (obchody 2019–26)

| Heuristiky | Obchodů | Úspěšnost | Průměr % marže |
|---|---|---|---|
| SHODA | 175 | 90,9 % | +9,0 |
| BEZ NÁZORU | 261 | 89,3 % | +6,5 |
| PROTI | 134 | 90,3 % | +9,9 |

Shoda heuristik s hlavním modelem historicky NEPŘIDÁVALA hodnotu – důvěru v signál nezvyšuje. (p = 0.2819)

## Změny stavů (45)

- osc_rsi_mom-60-L|EURUSD|1D: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (funguje jen v letech 2019–26, v letech 2012–18 ne)
- mom_ts-60-S|EURUSD|1D: NEFUNKČNÍ → SLABÁ (kladná, ale neprokázaná (p 2019–26 0,359, po korekci na počet pravidel q 1,00))
- vol_klid_pruraz-10-L|USDCHF|1D: NEOVĚŘENÁ → OVERFIT/NESTABILNÍ (funguje jen v letech 2019–26, v letech 2012–18 ne)
- tr_ma-200-L|AUDUSD|1D: OVERFIT/NESTABILNÍ → NEFUNKČNÍ (na novějších datech 2019–26 po nákladech prodělává (průměr -0,011 %))
- mom_ts-10-S|AUDUSD|1D: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (walk-forward: kladných jen 5 z 11 let)
- mm_falesny-20-S|USDCAD|1D: SLABÁ → OVERFIT/NESTABILNÍ (kladná jen ve 2 ze 4 období)
- mm_predchozi-L|USDCAD|1D: OVERFIT/NESTABILNÍ → SLABÁ (kladná, ale neprokázaná (p 2019–26 0,309, po korekci na počet pravidel q 1,00))
- osc_rsi_mom-60-L|USDCAD|1D: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (funguje jen v letech 2019–26, v letech 2012–18 ne)
- osc_stoch-9-S|USDCAD|1D: OVERFIT/NESTABILNÍ → NEFUNKČNÍ (na novějších datech 2019–26 po nákladech prodělává (průměr -0,008 %))
- mom_ts-60-L|USDCAD|1D: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (funguje jen v letech 2019–26, v letech 2012–18 ne)
- komb-1-L|USDCAD|1D: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (kladná jen ve 2 ze 4 období)
- tr_struktura-5-S|NZDUSD|1D: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (funguje jen v letech 2019–26, v letech 2012–18 ne)
- sr_odraz-50-L|NZDUSD|1D: OVERFIT/NESTABILNÍ → NEFUNKČNÍ (na novějších datech 2019–26 po nákladech prodělává (průměr -0,012 %))
- sr_odraz-100-L|NZDUSD|1D: OVERFIT/NESTABILNÍ → NEFUNKČNÍ (na novějších datech 2019–26 po nákladech prodělává (průměr -0,017 %))
- osc_rsi_obrat-14-30-L|NZDUSD|1D: NEOVĚŘENÁ → OVERFIT/NESTABILNÍ (funguje jen v letech 2019–26, v letech 2012–18 ne)
- osc_rsi_mom-70-S|NZDUSD|1D: NEOVĚŘENÁ → NEFUNKČNÍ (na novějších datech 2019–26 po nákladech prodělává (průměr -0,074 %))
- komb-2-L|NZDUSD|1D: NEOVĚŘENÁ → OVERFIT/NESTABILNÍ (funguje jen v letech 2019–26, v letech 2012–18 ne)
- mm_falesny-10-L|EURJPY|1D: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (funguje jen v letech 2019–26, v letech 2012–18 ne)
- mom_ts-20-L|AUDJPY|1D: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (funguje jen v letech 2019–26, v letech 2012–18 ne)
- osc_macd_x-19-39-9-S|EURUSD|4H: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (funguje jen v letech 2019–26, v letech 2012–18 ne)
- vol_squeeze-15-L|USDJPY|4H: NEFUNKČNÍ → SLABÁ (kladná, ale neprokázaná (p 2019–26 0,499, po korekci na počet pravidel q 1,00))
- osc_rsi_obrat-14-35-L|GBPUSD|4H: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (funguje jen v letech 2019–26, v letech 2012–18 ne)
- osc_stoch-14-S|GBPUSD|4H: NEFUNKČNÍ → SLABÁ (kladná, ale neprokázaná (p 2019–26 0,225, po korekci na počet pravidel q 1,00))
- osc_rsi_obrat-2-5-L|AUDUSD|4H: OVERFIT/NESTABILNÍ → NEFUNKČNÍ (na novějších datech 2019–26 po nákladech prodělává (průměr -0,001 %))
- osc_rsi_obrat-2-10-L|AUDUSD|4H: SLABÁ → OVERFIT/NESTABILNÍ (funguje jen při přesném nastavení (sousední nastavení drží 0 z 2))
- mm_predchozi_falesny-S|USDCAD|4H: OVERFIT/NESTABILNÍ → NEFUNKČNÍ (na novějších datech 2019–26 po nákladech prodělává (průměr -0,000 %))
- vol_svicka_pokr-1-L|EURJPY|4H: OVERFIT/NESTABILNÍ → NEFUNKČNÍ (na novějších datech 2019–26 není lepší než náhodné vstupy ve stejném směru)
- vol_svicka_obrat-1.5-S|EURJPY|4H: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (walk-forward: kladných jen 2 z 6 let)
- pa_kladivo-L|EURJPY|4H: SLABÁ → OVERFIT/NESTABILNÍ (walk-forward: kladných jen 5 z 11 let)
- cas_asie_pokr-1-L|EURJPY|4H: SLABÁ → OVERFIT/NESTABILNÍ (walk-forward: kladných jen 4 z 9 let)
- sr_odraz-50-L|GBPJPY|4H: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (funguje jen v letech 2019–26, v letech 2012–18 ne)
- komb-3-L|GBPJPY|4H: SLABÁ → NEFUNKČNÍ (na novějších datech 2019–26 není lepší než náhodné vstupy ve stejném směru)
- osc_rsi_obrat-14-25-L|EURGBP|4H: OVERFIT/NESTABILNÍ → NEFUNKČNÍ (na novějších datech 2019–26 po nákladech prodělává (průměr -0,003 %))
- sr_odraz-20-S|EURCHF|4H: OVERFIT/NESTABILNÍ → SLABÁ (kladná, ale neprokázaná (p 2019–26 0,118, po korekci na počet pravidel q 1,00))
- vol_squeeze-15-S|EURCHF|4H: OVERFIT/NESTABILNÍ → SLABÁ (kladná, ale neprokázaná (p 2019–26 0,171, po korekci na počet pravidel q 1,00))
- vol_squeeze-20-S|EURCHF|4H: OVERFIT/NESTABILNÍ → SLABÁ (kladná, ale neprokázaná (p 2019–26 0,146, po korekci na počet pravidel q 1,00))
- osc_bb_pokr-2.5-S|EURCHF|4H: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (kladná jen ve 2 ze 4 období)
- komb-4-S|EURCHF|4H: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (funguje jen v letech 2019–26, v letech 2012–18 ne)
- tr_struktura-10-L|AUDJPY|4H: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (funguje jen v letech 2019–26, v letech 2012–18 ne)
- osc_macd_x-19-39-9-S|AUDJPY|4H: OVERFIT/NESTABILNÍ → NEFUNKČNÍ (na novějších datech 2019–26 po nákladech prodělává (průměr -0,000 %))
- osc_bb_pokr-2.5-L|AUDJPY|4H: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (funguje jen v letech 2019–26, v letech 2012–18 ne)
- f_sazby-0.25-L|VSE|1D: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (funguje jen v letech 2019–26, v letech 2012–18 ne)
- vol_prehnani-1.5-S|VSE|4H: NEFUNKČNÍ → SLABÁ (kladná, ale neprokázaná (p 2019–26 0,017, po korekci na počet pravidel q 1,00))
- tr_ma-100-L+trend=trend|USDJPY|4H: NEFUNKČNÍ → OVERFIT/NESTABILNÍ (walk-forward: kladných jen 5 z 11 let)
- osc_rsi_obrat-2-5-L+vol=vysoká|EURJPY|4H: NEFUNKČNÍ → SLABÁ (kladná, ale neprokázaná (p 2019–26 0,480, po korekci na počet pravidel q 1,00))
