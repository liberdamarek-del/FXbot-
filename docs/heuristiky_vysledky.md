# Heuristický model – registr pravidel (2026-11-14)

_Generuje `python scripts/heuristiky.py prepocet`. Data do 2026-09-30. Metodika: docs/HEURISTIKY.md. Výnosy jsou v % ceny po nákladech (spread + skluz), na jednu predikci._

## Stavy pravidel

| Časový rámec | Rozsah | AKTIVNÍ | SLABÁ | NEOVĚŘENÁ | NEFUNKČNÍ | OVERFIT/NESTABILNÍ |
|---|---|---|---|---|---|---|
| 1D | jednotlivé páry | 0 | 183 | 1285 | 1025 | 342 |
| 1D | všechny páry dohromady | 0 | 30 | 6 | 155 | 49 |
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
| reakce na události | 114 | 60 % | 0 | 11 | 19 | 11 | 73 |
| korelace mezi páry | 288 | 36 % | 0 | 12 | 95 | 38 | 143 |
| fundament + technika | 176 | 46 % | 0 | 2 | 13 | 2 | 159 |
| kombinace (tvoje příklady) | 288 | 20 % | 0 | 8 | 167 | 24 | 89 |

## Kalibrace pravděpodobností (predikce 2019–26)

Úspěšnost všech predikcí 48,2 %. Brierovo skóre (nižší = lepší): statistická 0.2505, heuristická 0.2733, hod mincí (50 %) 0.2500.

| Heuristický odhad | Predikcí | Čekal | Skutečnost |
|---|---|---|---|
| 30–40 % | 131451 | 32,4 % | 49,8 % |
| 40–45 % | 92803 | 40,0 % | 49,2 % |
| 45–50 % | 98111 | 45,0 % | 49,2 % |
| 50–55 % | 104980 | 50,0 % | 48,2 % |
| 55–60 % | 120490 | 55,0 % | 47,6 % |
| 60–65 % | 138984 | 60,0 % | 47,7 % |
| 65–70 % | 129594 | 65,0 % | 47,1 % |
| 70–80 % | 186689 | 72,6 % | 47,7 % |

## Shoda s hlavním modelem (obchody 2019–26)

| Heuristiky | Obchodů | Úspěšnost | Průměr % marže |
|---|---|---|---|
| SHODA | 175 | 90,9 % | +9,0 |
| BEZ NÁZORU | 261 | 89,3 % | +6,9 |
| PROTI | 130 | 87,7 % | +8,7 |

Shoda heuristik s hlavním modelem historicky NEPŘIDÁVALA hodnotu – důvěru v signál nezvyšuje. (p = 0.2959)

## Změny stavů (4)

- ud_cb_pokr-cb-L|GBPJPY|1D: NEFUNKČNÍ → NEOVĚŘENÁ (nedostatečný historický vzorek (2012–18: 24, 2019–26: 22, potřeba 30))
- ud_cb_obrat-cb-S|GBPJPY|1D: OVERFIT/NESTABILNÍ → NEOVĚŘENÁ (nedostatečný historický vzorek (2012–18: 24, 2019–26: 22, potřeba 30))
- ft_cb_extrem-L|VSE|1D: NEFUNKČNÍ → NEOVĚŘENÁ (nedostatečný historický vzorek (2012–18: 29, 2019–26: 29, potřeba 30))
- ft_cb_extrem-S|VSE|1D: OVERFIT/NESTABILNÍ → NEFUNKČNÍ (na novějších datech 2019–26 po nákladech prodělává (průměr -0,010 %))
