# Heuristický model – registr pravidel (2026-10-07)

_Generuje `python scripts/heuristiky.py prepocet`. Data do 2026-09-25. Metodika: docs/HEURISTIKY.md. Výnosy jsou v % ceny po nákladech (spread + skluz), na jednu predikci._

## Stavy pravidel

| Časový rámec | Rozsah | AKTIVNÍ | SLABÁ | NEOVĚŘENÁ | NEFUNKČNÍ | OVERFIT/NESTABILNÍ |
|---|---|---|---|---|---|---|
| 1D | jednotlivé páry | 0 | 182 | 1286 | 1029 | 338 |
| 1D | všechny páry dohromady | 0 | 30 | 5 | 155 | 50 |
| 4H | jednotlivé páry | 0 | 197 | 59 | 1779 | 456 |
| 4H | všechny páry dohromady | 0 | 1 | 0 | 179 | 14 |

## Aktivní pravidla (0)

Žádné pravidlo neprošlo všemi testy.

## Podle typu heuristiky (jednotlivé páry, základní pravidla)

| Typ | Pravidel | Kladných 2019–26 | AKTIVNÍ | SLABÁ | NEFUNKČNÍ | OVERFIT/NESTABILNÍ | NEOVĚŘENÁ |
|---|---|---|---|---|---|---|---|
| trend a struktura | 768 | 23 % | 0 | 16 | 549 | 91 | 112 |
| podpora a odpor | 144 | 45 % | 0 | 20 | 69 | 29 | 26 |
| předchozí maxima a minima | 384 | 35 % | 0 | 30 | 258 | 69 | 27 |
| volatilita (ATR) | 672 | 37 % | 0 | 37 | 259 | 99 | 277 |
| oscilátory (RSI, MACD, Bollinger, stochastic) | 1152 | 40 % | 0 | 116 | 626 | 232 | 178 |
| momentum | 480 | 29 % | 0 | 25 | 333 | 78 | 44 |
| price action (svíčky) | 240 | 38 % | 0 | 29 | 132 | 44 | 35 |
| čas | 240 | 43 % | 0 | 22 | 118 | 54 | 46 |
| fundamenty | 200 | 38 % | 0 | 1 | 54 | 12 | 133 |
| reakce na události | 114 | 59 % | 0 | 11 | 20 | 12 | 71 |
| korelace mezi páry | 288 | 36 % | 0 | 12 | 95 | 38 | 143 |
| fundament + technika | 176 | 46 % | 0 | 2 | 13 | 2 | 159 |
| kombinace (tvoje příklady) | 288 | 21 % | 0 | 8 | 168 | 22 | 90 |

## Kalibrace pravděpodobností (predikce 2019–26)

Úspěšnost všech predikcí 48,2 %. Brierovo skóre (nižší = lepší): statistická 0.2505, heuristická 0.2733, hod mincí (50 %) 0.2500.

| Heuristický odhad | Predikcí | Čekal | Skutečnost |
|---|---|---|---|
| 30–40 % | 131188 | 32,4 % | 49,9 % |
| 40–45 % | 92675 | 40,0 % | 49,3 % |
| 45–50 % | 97992 | 45,0 % | 49,2 % |
| 50–55 % | 104848 | 50,0 % | 48,2 % |
| 55–60 % | 120311 | 55,0 % | 47,6 % |
| 60–65 % | 138775 | 60,0 % | 47,7 % |
| 65–70 % | 129332 | 65,0 % | 47,0 % |
| 70–80 % | 186377 | 72,6 % | 47,6 % |

## Shoda s hlavním modelem (obchody 2019–26)

| Heuristiky | Obchodů | Úspěšnost | Průměr % marže |
|---|---|---|---|
| SHODA | 175 | 90,9 % | +9,0 |
| BEZ NÁZORU | 261 | 89,3 % | +6,5 |
| PROTI | 131 | 90,1 % | +9,9 |

Shoda heuristik s hlavním modelem historicky NEPŘIDÁVALA hodnotu – důvěru v signál nezvyšuje. (p = 0.2969)
