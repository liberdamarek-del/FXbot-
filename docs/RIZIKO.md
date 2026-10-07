# Riziko jednoho obchodu – výzkum a nové nastavení velikosti (R-037, 7. 10. 2026)

_Podnět uživatele: cíl (take profit) je 12–15 % marže, stop loss až 60–80 % marže. Při marži 20 % účtu by jeden
obchod mohl vzít skoro 20 % účtu. Úkol: vymyslet něco lepšího. Výpočty: `scripts/riziko_lab.py`
(`--stupne` pro nové nastavení), data FXCM 2012–2026, stejná pravidla vstupu i výstupu jako živý model._

## Odpověď v kostce

1. **Problém byl ve velikosti obchodu, ne v signálu.** Původní model dával silným signálům pevnou marži 20 % účtu.
   Když měl pár zrovna velké výkyvy, byl stop daleko a jeden obchod mohl vzít až 38 % účtu. Nejhorší skutečný
   obchod v letech 2019–2026 vzal 19,6 % účtu.
2. **Nové nastavení (živě od 7. 10. 2026):** velikost obchodu se počítá ze vzdálenosti stop lossu. Při stopu
   ztratíš nejvýš zvolené procento účtu (výchozí 5 %). Silné signály mají celé riziko, slabší 30 % z něj. Signály
   samotné (kdy, kam, cíle, stop) se nemění.
3. **Poměr výnosu a propadu zůstal stejný nebo je lepší** (v letech 2023–2026 1,3–1,4 proti 1,17 u původního
   modelu). Menší riziko ale znamená menší roční výnos: při 5 % na obchod asi 8–10 % ročně místo 28–53 %.
4. **Lepší poměr cíle a stopu nefunguje.** Trendové obchody s cílem větším než stop (cíl 1,5–2× stop) a těsnější
   stopy u současného vstupu jsme poctivě otestovali. Na letech, které při výběru neviděly, prodělávaly nebo
   vydělávaly méně. Model vydělává právě tím, že vyhrává často (86–90 %) malé částky. Teď ale víš dopředu, kolik
   nejvýš může vzít jedna ztráta.

## 1. Jak to bylo (původní velikost: marže 20 / 20 / 4 / 4 % účtu)

Změřeno na skutečných obchodech šampiona měsíčního profilu, v % celého účtu:

| Roky | Obchodů | Úspěšnost | Průměrný zisk | Průměrná ztráta | Nejhorší obchod | Ztráty horší než −10 % |
|---|---|---|---|---|---|---|
| 2012–2018 | 223 | 88 % | +1,21 % | −3,12 % | −6,7 % | 0 |
| 2019–2026 | 274 | 88 % | +1,69 % | −4,15 % | −19,6 % | 2 |

Stop loss silného signálu stál při vstupu až 38 % účtu (marže 20 % × stop 4 ATR, který byl při velkých výkyvech až
190 % marže). Profil max (velikost podle výkyvů, marže 15 %): nejhorší obchod −13,3 % účtu.

## 2. Co nefungovalo: lepší poměr cíle a stopu

Každý obchod riskuje stejné procento účtu (1 % nebo 2 %). Výstupy vybrané jen na letech výběru, výsledky jsou
z let, které výběr neviděl (stejný postup jako brána učení):

| Rodina | Výstup vybraný na historii | 2019–2022 (riziko 2 %) | 2023–2026 (riziko 2 %) |
|---|---|---|---|
| současná pravidla (cíl 0,75 ATR, stop 4 ATR) | – | +6,5 % ročně, propad 7 % | +3,2 %, propad 7 % |
| současný vstup, jiné výstupy (108 variant) | cíl 0,75, stop 3, 40 dní | +9,9 %, propad 7 % | +0,1 %, propad 11 % |
| průraz 20 dní ve směru sazeb (trend) | cíl 1,5–2 ATR, stop 1 ATR | +6,8 %, propad 21 % (úspěšnost 50 %) | −1,5 %, propad 22 % (33 %) |
| průraz 13 týdnů ve směru sazeb | cíl 1,5–2 ATR, stop 1 ATR | +0,2 %, propad 20 % | −7,1 %, propad 27 % |

Těsnější stopy (0,75–2 ATR) u současného vstupu přidaly ztrátové obchody víc, než ubraly na jejich velikosti.
Trendové obchody mají „hezčí“ poměr cíle a stopu, ale úspěšnost jen 27–50 % a v letech 2023–2026 prodělaly.

## 3. Co funguje: velikost podle stop lossu, silnější signál = větší riziko

Marže obchodu = zvolené riziko × váha stupně ÷ (stop v % marže). Při stopu se tak ztratí přesně riziko × váha
účtu. Váhy stupňů (silný, silný, střední, slabý) se vybraly jen na letech výběru podle výnosu na propad, s aspoň
2 ziskovými obchody měsíčně. Na letech 2012–2022 vyšlo (1; 1; 0,3; 0,3) a to platí živě.

| Nejvyšší ztráta 1 obchodu | 2019–2022 ročně | propad | 2023–2026 ročně | propad | nejhorší obchod | marže najednou max |
|---|---|---|---|---|---|---|
| 2 % účtu | +4,9 % | 2 % | +3,0 % | 2 % | −2,0 % | 13 % účtu |
| 3 % | +7,1 % | 3 % | +4,6 % | 3 % | −3,0 % | 19 % |
| **5 % (výchozí)** | **+9,6 %** | **6 %** | **+7,7 %** | **6 %** | **−5,0 %** | 27 % |
| 8 % | +15,8 % | 9 % | +12,4 % | 9 % | −8,0 % | 43 % |
| 10 % | +20,0 % | 11 % | +15,7 % | 12 % | −10,0 % | 54 % |
| původní model (marže 20 %) | +53,0 % | 29 % | +28,2 % | 24 % | −19,6 % | – |

Úspěšnost se nemění (90 % / 86 %), 2–3 ziskové obchody měsíčně, 29–43 obchodů ročně.

## 4. Proč je cíl pořád menší než stop

Model sází na to, že se krátký prudký pohyb proti směru sazeb vrátí. To se stává často, ale jen o kus (cíl 0,75 ATR).
Když se nevrátí, jde obvykle o skutečnou změnu (zprávy, centrální banka) a cena jde daleko. Stop 4 ATR dává
obchodu prostor. Těsnější stop zavíral i obchody, které by se vrátily (bod 2). Průměrně: 9 obchodů vydělá malou
částku, 1 prodělá větší. Teď je ta větší ztráta pevně omezená tvou volbou.

## 5. Co se změnilo v systému

| Část | Změna |
|---|---|
| `scripts/riziko_lab.py --stupne` | výběr vah stupňů walk-forward, tabulka pro přehled → `learning/riziko.json` |
| `signals_live.py` | u každého páru váha stupně, u signálu velikost a ztráta při stopu v % účtu (výchozí riziko); stav `riziko` |
| přehled | pole „Nejvyšší ztráta jednoho obchodu“, karta signálu ukazuje marži, ztrátu při stopu a zisk na cílech v % účtu a v Kč, tabulka „Co čekat“; „Zapsat podle signálu“ vyplní marži podle rizika |
| forward test | nové záznamy mají váhu stupně a stop v % marže (pozdější vyhodnocení s velikostí podle rizika) |
| diagnostika | kontrola, že `riziko.json` patří k živému šampionovi (jinak VAROVÁNÍ) |
| testy | `test_f3_audit.py`: stop stojí přesně zvolené procento účtu |

Po každé změně šampiona měsíčního profilu se musí spustit `python scripts/riziko_lab.py --stupne` (váhy a tabulka).

## 6. Omezení (poctivě)

* **Mezera přes víkend** může zavřít obchod hůř než na stopu. Simulátor bere výstup na stopu. Ověřeno: z 31 stop
  lossů šampiona 2012–2026 otevřela hodina za stopem jen jednou (USD/CAD 8. 1. 2016), o 4,5 % vzdálenosti stopu.
  V historii je to zanedbatelné, ve skutečnosti to ale může být víc (NEOVĚŘENO pro budoucí krize).
* **Nejmenší obchod u brokera je 0,01 lotu.** U malých účtů a malého rizika vyjde třetina pozice pod tuto mez.
  Přehled na to upozorní a doporučí jednu pozici s cílem TP1.
* Váhy stupňů jsou vybrané na historii. Skutečný důkaz dá až forward test.
