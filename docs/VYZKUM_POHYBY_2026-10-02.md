# Výzkum: proč se trhy denně hýbou a jestli to jde předpovědět (2. 10. 2026)

Podrobné tabulky jsou v [PROC_SE_TRHY_HYBOU.md](PROC_SE_TRHY_HYBOU.md) (příčiny pohybů) a
[KRATKE_OKNO.md](KRATKE_OKNO.md) (krátkodobé ukazatele po párech). Data: 12 párů, hodinová FXCM 2012–2026,
k tomu zlato, stříbro, ropa WTI a Brent, měď, plyn, akcie USA / Evropa / Japonsko, VIX, americké výnosy,
dolarový index (Yahoo, denně od 2012), 2leté výnosy států (databáze fundamentů), termíny rozhodnutí
Fedu, ECB, BoJ a BoE a amerických zpráv NFP, CPI, HDP, maloobchod, PCE a PPI (ALFRED).

## Hlavní zjištění

1. **Jak velké jsou pohyby.** Průměrný denní rozsah (od minima k maximu) je 0,82 % ceny, tedy 24 % marže
   při páce 1:30. Od zavření do zavření se ale pár pohne v průměru jen o 0,40 % (12 % marže). Rozsah
   aspoň 1 % má čtvrtina dní (u AUD/JPY 45 %, u EUR/CHF 5 %). Pohyb zavření–zavření aspoň 1 % má jen
   7 % dní. Polovinu denního rozsahu tvoří „kmitání“ tam a zpět.
2. **Kdy se trh hýbe.** Nejsilnější hodiny jsou 08:00–11:00 New York (u nás 14–17 h): americké zprávy
   v 8:30 a 10:00 a zároveň se tehdy obchoduje v Londýně i New Yorku. Silná je i 3:00–4:00 New York
   (u nás 9–10 h), kdy otevírá Londýn a vycházejí evropská data. Nejklidnější je večer po zavření
   New Yorku.
3. **Zprávy.** Velké dny (5 % dní s největším pohybem) připadají na rozhodnutí centrální banky páru
   2,0–2,9× častěji než obyčejné dny. Na americkou zprávu o zaměstnanosti (NFP) 1,7× častěji, na CPI
   1,6× a na maloobchod 1,5×. HDP a PCE pohyb téměř nezvyšují (1,0×). I tak ale **70 % velkých dnů
   nemá žádnou plánovanou zprávu z tohoto seznamu**. Jsou to data jiných zemí, neplánované výroky
   (politici, guvernéři mimo zasedání), geopolitika a velké toky peněz. Největší jediná hodina dělá
   v mediánu 35 % pohybu velkého dne, zbytek se nasbírá postupně.
4. **Co se hýbe spolu s měnami ve stejný den.**
   - Akcie, VIX, zlato, ropa, měď a výnosy vysvětlí v průměru 26 % denních pohybů měn (AUD/JPY 43 %,
     AUD/USD 38 %, USD/JPY 37 %, EUR/CHF jen 5 %).
   - USD/JPY jde s americkými výnosy (korelace +0,49) a proti zlatu (−0,36).
   - AUD a NZD jdou s akciemi a mědí, CAD s akciemi a ropou.
   - Rozdíl 2letých výnosů obou zemí jde se svým párem u všech párů (+0,20 až +0,48). To je přesně to,
     co model sleduje přes sazby (pomaleji, měsíčně).
5. **Předpovídá dnešek zítřek?** Téměř ne. Dnešní změna zlata, ropy, mědi, výnosů a akcií má se
   zítřejším pohybem měny korelaci kolem 0, nejvýš ±0,10. Těch ±0,10 u akcií USA → EUR/USD, GBP/USD,
   USD/CHF, USD/JPY táhne hlavně rok 2020 (covid). Po nákladech na tom vydělat nejde, Sharpe v letech
   2012–18 a 2023–26 vyšel záporně. Předvídat jde **velikost** pohybu: po velkém dni přijde další velký
   s pravděpodobností 18 % místo běžných 10 %. **Směr** předvídat nejde.
6. **Krátkodobé ukazatele po párech (14 dní / měsíc / půl roku).** Otestoval jsem 64 ukazatelů na každém
   z 12 párů (technické, fundamentální, jiné trhy) se 4 dobami držení: 3 024 kombinací po nákladech.
   - **To, co fungovalo posledních 3–12 měsíců, nefunguje spolehlivě dalších 14 dní ani měsíc.**
     Korelace pořadí „posledně“ vs. „příště“ je prakticky nula (+0,01, t pod 2).
   - Strategie „vyber na každém páru nejlepší ukazatel za posledních 3 měsíců a obchoduj ho 14 dní“
     porazila náhodný výběr. Výnos je ale jen +1,2 % ceny ročně při velkém kolísání a v letech
     2013–18 byla ztrátová.
   - Nejstabilnější je výběr za 6 měsíců obchodovaný dalšího půl roku (Sharpe +0,28 / +0,20 / +0,28
     ve všech obdobích), ale tak slabý, že by model nezlepšil.
   - Pevných ukazatelů, které vyšly ve všech třech obdobích, je 34 z 3 024, zhruba tolik, kolik dá
     náhoda. Ekonomicky dávají smysl hlavně ty o **návratu ceny zpět**: EUR/GBP (obrat po 5 dnech,
     RSI(2), průraz 20 dní proti), EUR/USD (obrat po 1 dni) a „proti zprávě“ u EUR/USD, USD/CAD
     a AUD/USD (velký pohyb ve zprávový den se během 10–20 dní částečně vrací). To potvrzuje princip
     našeho modelu (nákup prudkého propadu).
7. **Váš nápad použitý na model.** Obchodovat pár jen tehdy, když mu pravidlo poslední 3 / 6 / 12
   měsíců vycházelo. Testovací brána to zamítla ve všech třech variantách: výnos klesl (2023–26
   z +19,8 % na +15,6 % / +12,2 % / +4,7 % ročně). Pár, kterému se nedařilo, se většinou zase vrátí.

## Co v modelu je a co ne

| | v modelu | otestováno |
|---|---|---|
| úrokové sazby (změna, rozdíl) | **ano**, hlavní filtr | ano, robustní |
| rozhodnutí centrálních bank (Fed, ECB, BoJ, BoE) | ne (upozornění na webu) | ano: obchody před rozhodnutím horší, vynechání snížilo výnos |
| americké zprávy NFP, CPI, HDP, maloobchod, PCE, PPI | ne (upozornění na webu) | ano: zvyšují pohyb, nejsou ziskový filtr |
| zlato, ropa, měď, plyn, akcie, VIX, americké výnosy | ne | ano: ve stejný den silné, na zítřek nic spolehlivého |
| pozice velkých hráčů (COT – banky, fondy) | ne | ano, zamítnuto |
| předpovědi bank a pojišťoven | ne | nelze: historie není zdarma k dispozici; studie dlouhodobě ukazují, že průměrné předpovědi kurzů na 1–12 měsíců nebývají lepší než odhad „kurz zůstane stejný“ |
| výroky politiků, geopolitika | ne | nelze plánovat dopředu; jsou ve zhruba 70 % velkých dnů bez plánované zprávy |
| data jiných zemí (např. britské CPI, australská zaměstnanost) | ne | zatím ne: termíny s historií chybí (kalendář sbíráme od 30. 9. 2026) |

## Závěr

Na denní pohyb o desítky procent marže nemá žádný zdroj spolehlivou předpověď **směru**. Zprávy
a ostatní trhy vysvětlují, **proč** se cena ten den pohnula, ale až potom, co se to stalo. Předem jde
poznat jen to, **kdy** bude trh divoký (zprávy, rozhodnutí centrálních bank, shlukování velkých dnů).
Modelu se proto nic nemění. Nejsilnější vzorec, návrat ceny po prudkém pohybu, už model využívá.

Další kroky: termíny zpráv dalších zemí (britské, kanadské, australské…), aby šlo otestovat i jejich
vliv. Pak hlídat, jestli se vztahy z této studie nezmění (týdenní učení).
