# Heuristický model (R-038, 7. 10. 2026)

_Podnět uživatele: přidat vedle hlavního modelu samostatnou heuristickou vrstvu, která nikdy nepředpokládá, že má
pravdu, každé pravidlo měří, sama se testuje, zhoršuje a vyřazuje nefunkční pravidla. Kód: `scripts/heuristiky.py`,
výsledky: `docs/heuristiky_vysledky.md` (generuje se každou sobotu), přehled: záložka **Heuristiky**._

## Odpověď v kostce

1. **Systém běží.** Knihovna má 57 typů heuristik ve 221 nastaveních. Každá platí pro 12 párů, pro denní svíčky
   (horizont 5 dní) a 4hodinové svíčky (horizont 24 h), zvlášť pro každý pár i pro všechny páry dohromady.
   Celkem je to 5 760 měřitelných pravidel. Jednou denně (po zavření denní svíčky) z nich vznikají živé predikce. Každá predikce se po svém
   horizontu sama vyhodnotí a nedá se zpětně změnit.
2. **První výsledek je poctivě negativní.** Žádné pravidlo neprošlo všemi testy (AKTIVNÍ 0). Na letech 2019–2026
   bylo „lepších než náhodné vstupy (p ≤ 0,05)“ 4,3 % pravidel, čistá náhoda by dala asi 5 %. Tři pravidla prošla
   i korekcí na počet testů, ale fungovala jen v letech 2019–2026, ne 2012–2018 (OVERFIT/NESTABILNÍ).
3. **Heuristický odhad nesedí.** Čím víc rodin heuristik souhlasí, tím je úspěšnost spíš nižší (při odhadu 70–80 %
   skutečně 47,6 %). Statistická pravděpodobnost z let 2012–18 předpovídala roky 2019–26 jen stejně dobře jako
   hod mincí.
4. **Shoda s hlavním modelem nic nepřidává.** Obchody hlavního modelu 2019–26 vyšly v 90,9 % při shodě
   heuristik a v 90,1 % při nesouhlasu (p = 0,30). Shoda proto důvěru v signál nezvyšuje.
5. **Hlavní model se nemění.** Heuristiky jsou informace. Do modelu se může dostat jen pravidlo, které později
   projde jako pokus testovací branou.

## 1. Co je pravidlo

Pravidlo je hypotéza se směrem určeným předem, například „RSI(2) < 10 → LONG na 5 dní“. Data směr nevybírají.
Kde má jedna podmínka dvě opačná čtení (pokračování / obrat), jsou to dvě samostatná pravidla.

| Typ | Příklady |
|---|---|
| trend a struktura | cena nad rostoucí SMA, křížení EMA, vyšší maxima a minima, ADX, pokles v trendu |
| podpora a odpor | dotek minima 20/50/100 svíček a zavření výš |
| předchozí maxima a minima | průraz maxima 10/20/55 svíček, falešný průraz, průraz loňského týdne / včerejška |
| volatilita | průraz po stažení Bollingera, velká svíčka (pokračování i obrat), přehnaný pohyb při vysoké volatilitě |
| oscilátory | RSI 2 / 14, MACD, stochastic, Bollinger, vzdálenost od SMA20 |
| momentum | změna za 10–60 dní, zrychlení MACD, řada zavření stejným směrem |
| price action | pohlcení, kladivo, vnitřní a vnější svíčka, odmítnutý knot |
| čas | konec měsíce, páteční týdenní pohyb, asijská seance, pondělní mezera |
| fundamenty | carry (rozdíl sazeb), změna sazeb za 3 měsíce, VIX (strach / klid) |
| reakce na události | den rozhodnutí Fed/ECB/BoJ/BoE, US NFP/CPI: pokračování, obrat, den před |
| korelace mezi páry | nejsilnější vs nejslabší měna z 12 párů, dohánění párů, které zaostaly |
| fundament + technika | carry + krátký pokles, sazby + trend, VIX + průraz, CB zítra + extrémní RSI |
| kombinace | tvoje předem zadané příklady z týdenního výzkumu |

U každého pravidla je uložené: ID, přesná podmínka, pár, časový rámec, indikátory s parametry, fundamentální
podmínka, směr, horizont, datum vzniku a výsledky z historie: počet případů, úspěchy, neúspěchy, úspěšnost a
úspěšnost náhodných vstupů, průměrný výnos, EV po nákladech (i v pipech), MFE, MAE, profit faktor. K tomu výsledky
2019–26 (OOS), walk-forward, 4 období, režimy, sousední nastavení, ostatní páry, stav a důvěryhodnost.

**Úspěch** = cena za horizont šla správným směrem i po nákladech (spread a skluz páru). Predikce jednoho pravidla
se nepřekrývají, nová vznikne až po vyhodnocení předchozí.

## 2. Jak se pravidlo testuje (proti náhodě)

| Test | Co ověřuje |
|---|---|
| 2012–2018 a 2019–2026 zvlášť | funguje v obou obdobích? |
| náhodné vstupy | je lepší než náhodný vstup ve stejném páru, období a směru? (z-test, u kandidátů i 2 000 náhodných permutací) |
| korekce na počet pravidel | při 5 760 pravidlech projde 5 % náhodou; falešné objevy drženy pod 10 % (Benjamini–Hochberg) |
| bootstrap | 90% interval průměrného výnosu 2019–26 musí být nad nulou |
| walk-forward po letech | pravidlo „zapnuté“ jen když předchozí roky vydělaly; vydělá pak i v dalším roce? |
| 4 období (2012–15, 16–18, 19–22, 23–26) | nevydělalo jen v jednom kusu historie? |
| sousední nastavení | funguje i při RSI 13/15 místo 14, prahu ±5…? Jinak podezření na přeučení |
| ostatní páry | funguje i jinde, nebo jen na jednom páru? |
| režimy | volatilita vysoká / nízká, trend / range |
| velikost vzorku | pod 30 případů v některém období = NEOVĚŘENO |

**Stavy:** AKTIVNÍ (prošlo vším), SLABÁ (kladné, neprokázané), NEOVĚŘENÁ (málo případů), NEFUNKČNÍ (na
novějších datech prodělává nebo není lepší než náhoda), OVERFIT/NESTABILNÍ (jen jedno období, jen přesné
nastavení, jen část párů). Nefunkční a nestabilní pravidla živé predikce nedávají, ale každou sobotu se přepočítají
s novými daty a mohou se vrátit. Pokud jsou živé výsledky pravidla výrazně horší, než čekala historie
(binomický test, p < 0,05, aspoň 20 živých predikcí), pravidlo klesne o stupeň. **Zlepšování:** k pravidlu, které
v letech 2012–18 fungovalo jen v jednom režimu, vznikne odvozené pravidlo „jen v tomto režimu“. Jeho důkaz je až
2019–26 a živě (180 takových pravidel).

## 3. Dvě pravděpodobnosti (nikdy se nemíchají)

* **STATISTICKÁ PRAVDĚPODOBNOST** = úspěšnost pravidla v letech 2019–2026 s 90% intervalem. Vedle je historická
  úspěšnost 2012–18 a velikost vzorku. Při malém vzorku se místo ní zobrazí „NEOVĚŘENO – nedostatečný historický
  vzorek“.
* **HEURISTICKÝ ODHAD (subjektivní)** = pravidlo palce bez historie: 50 % + 5 bodů za každou rodinu heuristik,
  která na páru teď ukazuje stejný směr, minus 5 za každou opačnou (30–80 %). Jak se ukázalo, je špatně
  kalibrovaný. Zobrazuje se, aby bylo vidět, kolik váží „pocit z grafu“ proti datům.

## 4. Živé predikce a sebehodnocení

* Predikce vzniká jen při čerstvě zavřené svíčce: denní do 6 h, 4h do 2 h po zavření. Vstupní cena je cena
  v okamžiku zápisu. Zmeškaná svíčka se zpětně nedopisuje.
* Od 8. 10. 2026 (R-041, kvůli limitu uživatele) běží aktualizace jen jednou denně, po–pá v 17:07 New York
  (obvykle 23:07 našeho času). Denní svíčky se tak berou všechny, ze šesti 4h svíček denně jen ta, která končí
  v 17:00 New York. Živý vzorek 4h pravidel proto roste asi 6× pomaleji a popisuje jen tuto svíčku. Vyhodnocení
  se nemění: počítá se z hodinových cen do konce horizontu, ne z času běhu, jen se zapíše až při další obnově.
* Zápis obsahuje čas, cenu, směr, cíl a práh (±0,5 × ATR14 × √horizont), stav pravidla, obě pravděpodobnosti,
  režim trhu a shodu s hlavním modelem. Zapisuje se do `learning/heuristiky/predikce/<den>.jsonl`.
* Po horizontu se jednou vyhodnotí do `vyhodnoceni/<den>.jsonl`: cena na konci, maximum, minimum, výsledek po
  nákladech, odchylka od očekávání, zda padl cíl nebo práh (a co dřív) a možné souvislosti (rozhodnutí CB, NFP, CPI
  během horizontu, neobvykle velký pohyb).
* Oba soubory tvoří řetězec otisků (SHA-256). Diagnostika při každé aktualizaci ověří, že nikdo nic nezměnil ani nesmazal
  a že žádná predikce není vyhodnocená dvakrát.
* Sebehodnocení: posledních 20 / 50 / 100 / 500 / všechny predikce. Sleduje úspěšnost, profit faktor, EV, chybu
  předpovědi, falešně pozitivní, nepředpovězené velké pohyby, MFE / MAE a Brierovo skóre obou pravděpodobností.
  Rozpad je podle páru, časového rámce, typu, režimu, stavu a shody s hlavním modelem.

## 5. Omezení (poctivě)

* Knihovna vznikla 7. 10. 2026 se znalostí běžných obchodních pouček a dřívějšího výzkumu projektu. Roky
  2019–2026 proto nejsou pro nápady úplně „neviděné“. **Skutečný test je až živý deník od 7. 10. 2026.**
* Historie je z FXCM (do 25. 9. 2026), živé ceny z Yahoo. Rozdíly jsou malé, ale existují.
* Živý vstup je o několik minut po zavření svíčky, historie počítá se zavírací cenou. Mezi hodinami se cíl
  a práh posuzují podle hodinových maxim a minim. Když padnou obojí v jedné hodině, pořadí je „NEJASNÉ“.
* Sazby OECD mají zpoždění 2 měsíce a VIX je z předchozího dne, stejně jako v modelu. Data BoE 2015 a BoC jsou
  NEOVĚŘENO / BLOKOVÁNO (viz STAV_PROJEKTU.md).

## 6. Provoz

| Kdy | Co |
|---|---|
| jednou denně po–pá 17:07 New York (aktualizace) | nové predikce, vyhodnocení skončených, sebehodnocení → stav `heuristiky` → přehled |
| sobota (po stažení dat) | `python scripts/heuristiky.py prepocet` – registr s novými daty, stavy, změny, `docs/heuristiky_vysledky.md` |
| kdykoli | `python scripts/heuristiky.py overeni` (deník), `python scripts/heuristiky.py pravidlo <ID>` (karta pravidla) |
