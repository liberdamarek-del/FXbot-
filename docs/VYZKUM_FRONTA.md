# Fronta průzkumu (autonomní režim, rozhodnutí uživatele 11. 10. 2026)

Uživatel chce, aby systém sám zkoumal, hledal nové souvislosti a zkoušel nápady. Kvůli týdennímu limitu se průzkum
nedělá v samostatných bězích, ale **jako jeden ohraničený krok na konci každého učení** (středa a sobota).

## Pravidla

1. **Za jedno učení nejvýš jeden krok.** Krok je jedna položka níže nebo její část. Má nejvýš asi 15 volání nástrojů
   a nejvýš 10 minut výpočtu. Pokud se nevejde, rozdělí se a pokračuje se příště.
2. **Fakta, hypotézy a možnosti se nemíchají.**
   * Každé tvrzení z webu má zdroj.
   * Chybějící data jsou NEOVĚŘENO a nic se nedoplňuje.
   * Do modelu se nápad dostane jen jako pokus přes bránu. Bránu nepovolovat a parametry neladit podle výsledku.
   * **Od 20. 10. 2026 (R-047) je zmrazení nových pokusů:** nález se zapíše do deníku, ale pokus přes bránu se nezakládá,
     dokud uživatel zmrazení nezruší.
3. **Web se jen čte.**
   * Na veřejná fóra ani do chatů se nic nepíše.
   * Nic se nezakládá a nikdo se nevydává za člověka.
   * Žádný hromadný provoz: stahují se jen data, která projekt potřebuje, ze zdrojů určených ke stažení.
4. **Každý krok se zapíše do části „Deník“ níže.** Zápis obsahuje datum, co se dělalo, výsledek a co dál. Neúspěch se
   zapisuje stejně jako úspěch. V souhrnu pro uživatele stačí jedna věta.
5. **Pořadí určuje očekávaný přínos pro model a cena.** Fronta se smí přeuspořádat a doplnit, ale s důvodem.

## Fronta (od nejvyšší priority)

| # | Co | Proč | Stav |
|---|---|---|---|
| 1 | Rozdíl cen Yahoo (živě) a FXCM (historie) v páteční 16:00 New York u 12 párů | Model se testuje na FXCM a živě rozhoduje podle Yahoo. Rozdíl blízko hranice RSI může změnit signál. | ROZPRACOVÁNO – 1. krok hotov 2026-10-17 (úroveň cen), zbývá dopad na RSI(2) a signál |
| 2 | Přehled živého testu modelu (od 2. 11. 2026, po 4+ týdnech) | Obchody modelu proti očekávání z historie: úspěšnost, průměr a doba držení. Jde o jediná opravdu nová data. | čeká na datum |
| 3 | Ekonomická překvapení (skutečnost proti očekávání), nejdřív zjistit, zda existuje zdarma ověřitelný historický zdroj | Literatura: překvapení vysvětlují velkou část čtvrtletních pohybů měn (Stavrakeva & Tang 2020). Kalendář projektu má forecast/actual jen od 10/2026. | čeká |
| 4 | Sledování literatury jednou za čtvrtletí (nové práce o předvídatelnosti měn, o slábnutí anomálií) | Hutchinson a kol. 2022: zveřejněné anomálie po zveřejnění slábnou. | příště 2027-01 |
| 5 | Relativní výnosová křivka znovu, jen na datech po 10/2026 (R-043) | Ve 2023–26 snížila propad, ve 2019–22 škodila. Možná nový režim, nebo náhoda. | 2027-04 |

## Deník

* **2026-10-11 (R-043):**
  * Literatura: Hutchinson a kol. 2022 (anomálie po zveřejnění slábnou), Chen & Tsang 2013 (výnosová křivka).
  * Test relativní výnosové křivky (docs/VYZKUM_KRIVKA.md) a kolo 34. Brána ho zamítla.
  * Zjištění: obchody, u kterých rozdíl sazeb táhne krátký konec křivky, vycházely lépe v letech 2012–18 a 2023–26,
    v letech 2019–22 stejně.
* **2026-10-17 (R-046):** položka 1, krok 1 – `scripts/yahoo_vs_fxcm.py`, hodinové zavření Yahoo proti FXCM (střed bid/ask), překryv asi 9 800 hodin (2 roky), 84 pátečních barů 15:00 New York na pár.
  * Výsledek: většina párů se liší o méně než 0,01 % ceny (medián). EUR/USD, AUD/USD a NZD/USD mají stálý posun Yahoo nad FXCM o ca 0,03 % (v obou polovinách období stejný, tedy ne náhoda). GBP/USD, USD/CHF, JPY páry bez posunu. Nejhorší páteční odchylka 0,07 % (AUD/USD).
  * Příčina posunu NEOVĚŘENO (jiný zdroj kotace Yahoo; dohadovat se nedá). Posun úrovně sám RSI(2) téměř nemění; zbývá změřit, kolikrát by rozdíl obrátil signál (srovnání RSI(2) z obou zdrojů v pátek 16:00 NY) – příští krok.
* **2026-10-24 (sobotní učení):** položka 1, krok 2 – srovnání RSI(2) z Yahoo a FXCM (střed bid/ask) v 80 pátečních rozhodnutích 16:00 NY na pár (2 roky překryvu, denní svíčky složené z hodinových, jednorázový skript, nezapsán do repozitáře).
  * Výsledek: medián rozdílu RSI(2) 0,3–2,5 bodu, u EUR/CHF, EUR/GBP a USD/CHF nejvyšší; maximum až 31 bodů (AUD/JPY). Hranici 10 nebo 15 převrátilo celkem 34 případů z asi 960 pátků na pár (EUR/USD, USD/JPY, GBP/USD 0; EUR/GBP 8, EUR/CHF 6, EUR/JPY 5) – při dvou hranicích a obou směrech se jeden pátek může započítat dvakrát.
  * Omezení: skladba denní svíčky a časové zarovnání se mohou lišit od živého kódu; použité hranice 10/15 jsou přibližné, ne přesné prahy šampiona. Dopad na zisk NEOVĚŘENO. Na pokus přes bránu se nesahá (zmrazení R-047).
  * Další krok: změřit s přesnými prahy šampiona a skutečnými signály; jinak položku uzavřít.
