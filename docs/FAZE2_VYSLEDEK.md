# Fáze 2 – co zbyde z výsledků šampiona po korekci na vícenásobné testování

_Větev `architektura-v2-faze2`, 2026-10-20 (R-049). Čísla jsou z `learning/hygiena/faze2_vysledky.json`, plné tabulky v
`docs/FAZE2_TABULKY.md`, kontrola na 16 párech v `docs/KONTROLA_HISTDATA.md`. Šampioni, brána a živé signály se touto fází
NEZMĚNILY._

## 1. Verdikt (kritérium zastavení ze zadání)

**Šampion po korekci NEPROŠEL.** Podle pravidla ze zadání (počet pokusů = registr = 332) vychází DSR **0,87** (profil max) a
**0,86** (profil měsíční); hranice je 0,95. Prošel by až s měsíčním Sharpe 0,49 / 0,52 (roční 1,71 / 1,78), má 0,43 / 0,44 (roční 1,50 / 1,52).

DSR (Deflated Sharpe Ratio) říká: *s jakou pravděpodobností je skutečný Sharpe šampiona větší než to, co by z 332 pokusů vyšlo
nejlepší čistým štěstím*. Čím blíž 1, tím víc je výsledek skutečný.

| čtení vzorce | max | měsíční | co předpokládá |
|---|---|---|---|
| **podle zadání**: 332 pokusů, rozptyl Sharpe jako u čistého šumu | **0,872** | **0,861** | všech 332 pokusů je nezávislých a bez skutečné hodnoty |
| 332 pokusů, rozptyl Sharpe naměřený na variantách | 0,986 | 0,990 | pokusy jsou si podobné, ale je jich 332 |
| efektivní počet pokusů (28 / 12), rozptyl čistého šumu | 0,975 | 0,985 | pokusy jsou si podobné (korelace 0,77 / 0,84) |
| efektivní počet (28 / 12), rozptyl variant | 0,997 | 0,998 | totéž, nejmírnější čtení |

**Proč jsem mírnější čtení nepoužil k tomu, abych šampiona „zachránil“.**
1. Všechna mírnější čtení spoléhají na to, že registr obsahuje VŠECHNY pokusy. To není pravda: jen `profit_lab2` prohledal
   213 840 systémů, pivoty 1 080 variant a intradenní studie 300 variant, a nic z toho v logu učení (odkud registr vychází) není.
   Skutečný počet pokusů je **NEOVĚŘENO** a je větší než 332. Citlivost (tabulka v `FAZE2_TABULKY.md`): při 5 000 pokusech
   a rozptylu variant je DSR 0,96 (max) / 0,98 (měsíční), při 20 000 0,94 / 0,97, při 213 840 pokusech 0,90 / 0,95; s rozptylem
   čistého šumu klesá už při 1 000 pokusech pod 0,80.
2. „Varianty“ jsou pokusy z registru přehrané na DNEŠNÍM šampionovi s dnešními daty, ne původní pokusy. Rozptyl i korelace
   z nich jsou tedy odhad (**ODHAD**), ne měření původního hledání.
3. PBO (níže) a kontrola na jiných párech nepodporují, že ladění přidalo skutečnou hodnotu.

**Hrubý zbytek po korekci (ODHAD, řádový, ne předpověď):** při přísném čtení zhruba **+11 % ročně** (oba profily), při mírnějších
+20 až +33 %. V testovacím okně brány 2023–26 měl šampion +19,7 % (max) a +28,2 % (měsíční) ročně, propad 28 % / 24 % (okno
se ale použilo k výběru úprav, viz zmrazení R-047).

## 2. Co se změnilo v kódu

| Co | Stav |
|---|---|
| **Registr pokusů** `learning/registr_pokusu/registr.jsonl` – jen přidávání, řetězec otisků (jako deník heuristik); povinná pole: hypotéza, ekonomický důvod, parametry, data / test | HOTOVO/OVĚŘENO – 332 záznamů z `docs/UCENI_LOG.md` (144 různých jmen, 8 přijatých, 324 zamítnutých), řetězec v pořádku, `test_i1_hygiena.py` |
| `self_learn.py` nespustí neregistrovaný pokus a zapíše výsledek; pokus bez záznamu se nepočítá | HOTOVO/OVĚŘENO (zmrazení ale stejně nepouští žádný nový) |
| **DSR / PSR / PBO (CSCV)** v `src/core/statistika.py` | HOTOVO/OVĚŘENO – proti uzavřeným tvarům a simulaci; práh pro nový pokus vypíše `registr_pokusu.py souhrn` |
| **Trezor** dat od 2026-10-01 (`learning/trezor.json`, `docs/TREZOR.md`) | HOTOVO/OVĚŘENO – `market.series()` a `load_hourly()` je odřežou; otevřít jde jednou a jen s výslovným souhlasem uživatele; **trezor je zavřený**, této analýze skončila data 2026-09 |
| **Kontrola na 16 párech HistData** (`scripts/kontrola_histdata.py`) – jen report | HOTOVO/OVĚŘENO (viz bod 5); diagnostika upozorní, když se šampion změní a kontrola ne |
| Diagnostika: trezor, řetězec registru, kontrola HistData | HOTOVO/OVĚŘENO (jen hlásí, hlavní signály neblokuje) |

## 3. Jak se počítalo

Pozorování = **měsíc**. Řada = měsíční výnosy účtu ve dvou testovacích oknech brány (2019–22 s maržemi vybranými na 2012–18;
2023 až 2026-09 s maržemi vybranými na 2012–22) = 48 + 45 = 93 měsíců, přesně to, co brána viděla. Šampion: 93 měsíců, šikmost
0,03 / −0,21, špičatost 4,5 / 6,8, nejhorší měsíc −17,2 % / −22,4 %; Sharpe 5–95 % (bootstrap přes měsíce) 0,26–0,63 /
0,26–0,66: samotný vzorek 93 měsíců je dost dlouhý, aby ani pesimistický konec nebyl záporný. Slabé místo není šum vzorku, ale
výběr z mnoha pokusů na tomtéž vzorku.

Varianty: všech 144 jmen z `EXPERIMENTS` (do nich patří všech 332 záznamů registru) přehráno na dnešním šampionovi v obou
profilech (288 běhů). Do srovnání vstupuje **118** (max) a **72** (měsíční); mimo je 8 neproveditelných, 8 totožných se šampionem
(už v něm jsou, nebo nic nemění), 9 / 6 kopií jiné varianty a u měsíčního profilu 50 bez platných marží v druhém okně (tam by
řada byla jen 48 měsíců, nesrovnatelná).

## 4. PBO – pravděpodobnost přeúčelového ladění (CSCV)

PBO = jak často je varianta nejlepší v jedné půlce historie v druhé půlce horší než průměrná varianta. 0,5 = ladění je loterie;
výrazně pod 0,5 = nejlepší minulost předpovídá lepší budoucnost.

| profil | bloků 8 / 10 / 12 / 16 | rozptyl odhadu (S = 12) | variant lepších než šampion | medián variant (Sharpe) |
|---|---|---|---|---|
| max | 0,54 / 0,63 / 0,60 / 0,63 | 0,25–0,83 | 23 z 118 | 0,399 (šampion 0,432) |
| měsíční | 0,90 / 0,82 / 0,81 / 0,79 | 0,37–0,89 | 22 z 72 | 0,428 (šampion 0,438) |

Čtení: výběr „nejlepší minulý Sharpe mezi těmito variantami“ nepřinesl lepší než průměrnou variantu v dalším období.
Šampion je 80. percentil (max) a 69. percentil (měsíční) mezi svými variantami, tedy dobrý, ale ne výjimečný. Odhad PBO je hodně
rozkolísaný (**ODHAD**: 5% kvantil 0,25 / 0,37, medián 0,60 / 0,70). Všechny použité varianty mají kladný Sharpe (0,20–0,53 /
0,25–0,49) a kladný výnos v obou oknech – **okraj samotného pravidla se jeví jako kladný**, rozdíly mezi variantami jsou
převážně šum.

## 5. Základ vs. šampion a kontrola na jiných párech

| profil | řada | Sharpe měsíčně | 2019–22 ročně / propad | 2023–26 ročně / propad |
|---|---|---|---|---|
| max | základ CH-009 (bez přijatých změn) | 0,301 | +37,5 % / 30 % | +6,8 % / 24 % |
| max | šampion | 0,432 | +62,8 % / 24 % | +19,7 % / 28 % |
| měsíční | základ | 0,415 (jen 48 měsíců, druhé okno nemá platné marže) | +37,5 % / 30 % | – |
| měsíční | šampion | 0,438 | +53,0 % / 29 % | +28,2 % / 24 % |

Základ je statisticky kladný i sám (PSR 0,997 bez korekce), tedy základní okraj nevypadá jako úplný šum. Přírůstek 0,13 Sharpe
(max) vznikl ze 3 přijatých úprav vybraných z 332 pokusů na týchž oknech – právě té části, kterou výběr nejvíc nadhodnocuje.
Rozdíl 2023–26 (+6,8 % → +19,7 % ročně) proto není důkaz, že úpravy fungují.

**Kontrola na 16 párech HistData** (USD/NOK … GBP/AUD; nikdy se podle nich nevybíralo ani neladilo; stejné marže šampiona):

| | 16 HistData | 12 živých párů |
|---|---|---|
| úspěšnost obchodů | 77–81 % | 85–90 % |
| průměr obchodu (% marže) | −2,3 … +1,4 | +4,1 … +6,7 |
| roční výnos (3 období) | −11,5 % … −1,5 % | +19,7 % … +53,3 % |
| propad | 43–84 % | 18–28 % |

Na jiných párech okraj nepřetrvá: stejná vysoká úspěšnost, ale ztráty vyrovnají zisky a propady jsou hluboké. Omezení: HistData
jsou jen BID (ASK = BID), spready těchto párů jsou předpoklad (např. USD/ZAR 100, USD/NOK 40 pipů) – **NEOVĚŘENO**; páry mají
jinou dynamiku (vyšší spready, carry). Kontrola tedy nedokazuje, že model na 12 párech nefunguje, jen že se **nedá ukázat, že
funguje obecně**. Proč jsou živé páry právě těchto 12, jsem neověřil (**NEOVĚŘENO**; rozhodnutí uživatele z 2026-10-01).

## 6. Co je OVĚŘENO / ODHAD / NEOVĚŘENO

| | |
|---|---|
| **OVĚŘENO** | registr (332 záznamů, řetězec, 8 přijatých); trezor řeže data a otevření vyžaduje souhlas; vzorce DSR / PSR / PBO proti uzavřeným tvarům; DSR šampionů 0,872 / 0,861 při N = 332 a rozptylu čistého šumu; PBO 0,54–0,90; základ i varianty mají kladný Sharpe; výsledek na 16 párech HistData; šampioni a živé signály beze změny; 13 testů bez selhání na čistém klonu |
| **ODHAD** | efektivní počet nezávislých pokusů 28 / 12 (z korelace variant); zbytek výnosu po korekci (+11 % až +33 %); počet nových měsíců pro 95% jistotu; rozptyl odhadu PBO |
| **NEOVĚŘENO** | skutečný počet pokusů (log 332; laby profit_lab2 / pivoty / intradenní v něm nejsou); původní rozptyl Sharpe pokusů (varianty jsou přehrání na dnešních datech); spready a swapy 16 párů HistData; proč právě 12 živých párů; zda mírnější čtení DSR platí |

Kolik NOVÝCH měsíců (mimo trezor, jeden předem daný test) by stačilo na 95% jistotu, že skutečný Sharpe je kladný:
**18–21 měsíců**, kdyby byl skutečný Sharpe tak velký, jak jsme naměřili (0,43); **34–37**, kdyby byl 0,30; **164–172**, kdyby byl jen
0,13 (to, co zbude po přísné korekci). Papírové obchodování tedy malý okraj za rozumnou dobu nepotvrdí; pozná jen velké selhání.

## 7. Doporučení (rozhoduješ ty)

1. **Reálné peníze na tomto šampionovi ne.** Výsledek z historie nelze brát jako předpověď; plánuj řádově +10 % ročně hrubého
   zisku s propady kolem 25–30 % a s reálnou možností nuly.
2. **Fáze 3 (riziko portfolia): ano.** Je užitečná bez ohledu na šampiona – omezí škody, nepotřebuje žádný nový pokus o výkon.
3. **Fáze 4 (demo účet OANDA): jen s tvým souhlasem a po fázi 3.** Je to jediný způsob, jak získat opravdu nová data. Předem
   pevné meze zastavení musí počítat s tím, že malý okraj se neprokáže (bod 6): demo slouží hlavně k odhalení velkých rozdílů
   proti simulátoru (spread, skluz, čas vstupu) a k případnému zastavení.
4. **Fáze 5 (nové zdroje výnosu): odložit.** Dokud nevíme, jestli základ vůbec funguje mimo vzorek, další hledání zvyšuje počet
   pokusů a zhoršuje korekci. Pokud ano, tak nejvýš 4 předem zapsané vrstvy, každá jednou.
5. **Trezor neotvírat**, dokud nebude existovat jeden předem zapsaný test, na kterém se o něm rozhodne.

## 8. Příkazy

```
python fxbot.py test                              # 13 testů, bez data/
python scripts/registr_pokusu.py souhrn           # počet pokusů, řetězec, práh pro nový pokus
python scripts/trezor.py stav                     # trezor zavřený / otevřený
python scripts/faze2_analyza.py zprava            # tabulky z uložených řad (bez nové simulace)
python scripts/kontrola_histdata.py               # kontrola na 16 párech (potřebuje data HistData, ta nejsou v gitu)
```
