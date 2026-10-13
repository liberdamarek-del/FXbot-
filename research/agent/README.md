# Průběžný výzkum zlepšení agenta FXBOT (R-045, zadání uživatele 13. 10. 2026)

Cíl: systematicky hledat, ověřovat a měřit možnosti, jak zlepšit **řídicí vrstvu FXBOTu** (rutiny, dispečer, paměť
mezi sezeními, deník, sebehodnocení predikcí, experimentování a brána). Obchodní model samotný se mění jen přes
bránu (`scripts/self_learn.py`), nikdy z tohoto výzkumu přímo.

Běh: 3× týdně (út, čt, ne 07:23 Praha), nové krátké sezení přes dispečera. Strop: 12 webových dotazů nebo stažení,
25 volání nástrojů celkem, jeden hlavní směr + volitelně jeden průzkumný.

## Soubory (jen přidávat, zamítnuté nemazat)
| Soubor | Obsah |
|---|---|
| `ZDROJE.jsonl` | jeden řádek JSON na zjištění: `datum_behu, datum_zdroje, url, nazev, tvrzeni, citace (<= 25 slov), trida (A/B/C), duveryhodnost (1-5 + důvod), smer, vyuziti` |
| `NAVRHY.json` | seznam návrhů: `id, vytvoreno, smer, problem, reseni, naklad, rizika, zavislosti, metrika, zaklad_pro_srovnani, minimalni_vzorek, zkreslujici_vlivy, stav (novy/experiment/prijato/zamitnuto), duvod, zdroje[]` |
| `EXPERIMENTY.md` | plán, provedení, výsledek (i neúspěšný) |
| `SMERY.json` | výzkumné směry: `priorita (1-5), behu, prazdnych_za_sebou, nalezu, posledni_beh` |
| `DENIK.md` | jeden blok na běh (5-8 řádků) |
| `STAV.md` | otevřené otázky a navazující úkoly |

## Třídy zdroje
* **A** – funguje v praxi, doloženo kódem, měřením nebo provozní dokumentací.
* **B** – výzkumná hypotéza (článek/preprint s experimentem), v praxi neověřeno.
* **C** – názor, marketing, diskuse. Samo o sobě nikdy podklad pro návrh.

## Postup běhu
1. `git checkout main && git pull origin main`; přečíst `README.md`, `SMERY.json`, `STAV.md`, posledních 7 bloků
   `DENIK.md`, otevřené návrhy v `NAVRHY.json`; z `CLAUDE.md` a `docs/STAV_PROJEKTU.md` skutečné slabiny projektu
   (zdroj problémů pro návrhy; nehledat řešení pro neexistující problém).
2. Vybrat směr s nejvyšší prioritou (a jeden průzkumný s nejméně běhy). Směr se 3 prázdnými běhy za sebou: priorita
   se sníží o 1 a zařadí se na konec.
3. Hledat (WebSearch, primární zdroje přes WebFetch: arXiv, dokumentace, GitHub kód a issues). Fóra jen číst.
   Nic nepsat na web, nikoho nekontaktovat, neukládat přístupové údaje.
4. Každé zjištění do `ZDROJE.jsonl`. Co se nepodařilo stáhnout a přečíst, se nezapisuje jako zjištění (nebo jako
   NEOVĚŘENO bez citace). Duplicita (stejná URL nebo stejná myšlenka) = jen poznámka u existujícího řádku.
5. Užitečné převést do `NAVRHY.json` podle šablony. Bez předem dané metriky, základní verze a minimálního vzorku
   nesmí návrh dostat stav `experiment`.
6. Experiment: nejvýš jeden aktivní. Kontrolovaný (před/po s kontrolou nebo A/B), vratný, bez zásahu do brokera,
   bez obcházení brány. Úspěch na několika příkladech není důkaz. Korelaci nevydávat za příčinu.
7. Zapsat `DENIK.md`, `SMERY.json`, `STAV.md`. `git add research/ docs/` (nikdy `data/`), commit, push na `main`
   (při chybě sítě až 4× s čekáním 2, 4, 8, 16 s).
8. Report uživateli česky, 3-6 vět: nejdůležitější nový poznatek (nebo výslovně „nic nového“), ověřené zdroje,
   nejlepší nový nápad, doporučený experiment, míra jistoty (ověřeno / kvalifikovaný odhad / neověřeno), další krok.
   Totéž v jedné větě jako push notifikace (PushNotification, status proactive).

## Měřitelné základní hodnoty (zatím NEOVĚŘENO)
Spotřeba tokenů na běh se v `learning/provoz/posledni_beh.json` nezapisuje. Zaznamenává se čas, typ rutiny a výsledek
diagnostiky. První úkol v `NAVRHY.json` (N-001): navrhnout bezpečné měření provozu (doba běhu, počet volání nástrojů,
selhání), aby šlo další návrhy srovnávat.

## Pravidla
* Žádná změna obchodního modelu mimo bránu; žádná změna v `learning/heuristiky/predikce|vyhodnoceni`.
* Jen 12 párů; nepřidávat trhy.
* Nevymýšlet zdroje ani čísla. Chybějící údaj = NEOVĚŘENO.
