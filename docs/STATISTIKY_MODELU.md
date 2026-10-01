# Statistiky modelu FXBOT (V7.8.0)

Stav k 2026-10-01. Čísla z backtestu na reálných bid/ask cenách, 12 párů:
2016-09 – 2023-08 (FXCM, 127 810 rozhodnutí) a 2023-11 – 2026-09 (Dukascopy, 52 206 rozhodnutí).
Rozhodnutí = jeden pár v jednom 4hodinovém okamžiku.

## 1. Jak model rozhoduje – technika vs. fundamenty

Model **nemá číselné váhy** (Word, modul 50: „žádné magické číslo“). Má pořadí pravidel:

| Krok | Co rozhoduje | Role |
|---|---|---|
| Směr (BUY/SELL) | **technika na 100 %** – trend D1 a H4, momentum | bez technického směru se neobchoduje nikdy |
| Veto | fundamenty (sazby, carry, pozicování COT, riziko, komodity) | když je proti směru víc fundamentálních skupin než pro, obchod se ruší |
| Třída důvěry A/B/C | počet fundamentálních skupin ve shodě | A = ≥ 2 pro a nic proti; B = ≥ 1 pro; C = jen technika |
| Vstup, SL, TP | technika (úrovně, ATR) | pullback / retest / pokračování; R:R ≥ 1,5 po nákladech |

### Kolik rozhodnutí končí na které vrstvě

| Výsledek rozhodnutí | 2016–2023 | 2023–2026 |
|---|---|---|
| technika: trh bez trendu → neobchodovat | 36,7 % | 37,2 % |
| technika: D1/H4/momentum v rozporu | 6,6 % | 7,2 % |
| vstup / R:R / brány (technická poloha, náklady, stabilita) | 30,5 % | 32,0 % |
| **fundamenty proti → veto** | **15,1 %** | **13,5 %** |
| ostatní (teze z dřívějška trvá) | ~2,8 % | ~2,5 % |
| **obchod** | **8,3 %** | **7,6 %** |

Z důvodů „neobchodovat“ je tedy asi **83 % technických a 17 % fundamentálních**.
Fundamenty zruší **19–23 % obchodů**, které by dala samotná technika.

### Přidávají fundamenty něco?

| Směr z | edge proti náhodnému směru, 2016–2023 | 2023–2026 |
|---|---|---|
| technika + fundamentální veto (model) | −0,005 R (nevýznamné) | +0,022 R (nevýznamné) |
| jen technika | −0,001 R | +0,012 R |

Rozdíl je v obou obdobích ±0,01 R na rozhodnutí, tedy v rámci šumu: **fundamentální vrstva
ani nepomáhá, ani neškodí**. Třídy důvěry: A má úspěšnost 28 %, B 25–28 %, C 24–26 % – A
není spolehlivě lepší (kalibrace selhává).

## 2. Úspěšnost obchodů v procentech

| | 2016–2023 | 2023–2026 |
|---|---|---|
| úspěšných obchodů (zisk) | 23 % | 22 % |
| průměrný výsledek na obchod | −0,076 R | −0,063 R |
| profit factor | 0,90 | 0,92 |

R = násobek rizika do SL (−1 R = celý stop-loss). Nízká úspěšnost je daná tím, že cíl
(TP) je 1,5–3× dál než SL – i náhodný směr by tu měl úspěšnost kolem 25–30 %.

## 3. Pohyb se vstupem, SL, TP a dobou držení (`docs/GEOMETRIE.md`)

Zkoušeno **270 nastavení**: vstup hned / limit 0,25 / 0,5 ATR · SL 0,5–3 ATR(H4) ·
TP 0,5–4 ATR(H4) · držení 24 h / 3 dny / 5 dní. Nastavení se vybíralo na 2016–2021 a
ověřovalo na 2022–2026.

* **Ani jedno nastavení není ziskové** – ani na období výběru, ani na kontrole.
* Úspěšnost jde nastavit **od 17 % do 83 %**, výsledek ale zůstává záporný:

| vstup hned, 3 dny | TP 0,5 | TP 1 | TP 2 | TP 4 |
|---|---|---|---|---|
| SL 0,5 ATR | 48 % / −0,09 R | 32 % / −0,10 R | 21 % / −0,11 R | 17 % / −0,12 R |
| SL 1 ATR | 65 % / −0,04 R | 48 % / −0,06 R | 35 % / −0,07 R | 30 % / −0,10 R |
| SL 3 ATR | 80 % / −0,02 R | 65 % / −0,03 R | 51 % / −0,04 R | 46 % / −0,05 R |

(úspěšnost / průměr na obchod)

* Širší SL **nepomáhá** – stop-loss se neaktivuje „předčasně“, výsledek se jen rozloží jinak.
* Obrácený směr (prodat, když model říká koupit) **také není ziskový** v obou obdobích.

**Proč to nejde „naladit“:** když směr nemá výhodu, každé nastavení SL/TP jen mění
poměr mezi počtem výher a jejich velikostí. Průměr zůstane „nula minus náklady“.

## 4. Proč ChatGPT „dával zisky“

* **Série výher přichází náhodou často.** Při 20 obchodech a úspěšnosti 50 % je šance
  na ≥ 4 výhry za sebou **48 %** a na ≥ 5 výher **25 %**. S malým TP a velkým SL
  (úspěšnost 80 %) je šance na ≥ 8 výher za sebou **54 %** – a účet přitom ztrácí.
* Rozhodující není počet výher, ale **součet zisků a ztrát přes 100+ obchodů**.
* ChatGPT Word „vykládá“ volně (zprávy, kontext, odhad), kdežto bot ho plní doslova a
  nemůže se dívat do budoucnosti. Když k tomu přidáte vlastní úsudek (které signály vzít,
  kdy zavřít), je to jiný model – a ten může být lepší.

**Ověření:** pošlete mi seznam těch obchodů (datum a čas, pár, směr, vstup, SL, TP,
výsledek). Přepočítám je na skutečných cenách a porovnám s tím, co by v tu chvíli řekl bot
a co náhoda. Teprve to ukáže, jestli byla série štěstí, nebo dovednost.

## 5. Model v číslech

| | |
|---|---|
| Python kód celkem | 30 808 řádků (bez testů 24 258) |
| jádro rozhodování (`src/engine/`) | 14 souborů, 2 993 řádků; technika 295, fundamenty 455, rozhodnutí 452 |
| procedura běhu V7.8.0 (`src/v78/`) | 10 souborů, 2 733 řádků |
| fundamentální data (`src/fundamental/`) | 5 souborů, 1 182 řádků |
| zdroje cen (`src/sources/`) | 4 soubory, 1 101 řádků |
| statistika a učení (`src/stats/`) | 5 souborů, 854 řádků |
| skripty (backtest, výzkum, stahování) | 26 souborů, 4 854 řádků |
| testy | 47 souborů, 6 550 řádků (49 testů, vše PASS) |
| moduly z Wordu | 146: 110 implementováno, 27 částečně, 7 bez dostupných dat, 2 nahrazeno |
| parametry modelu | 42 |
| fundamentální řady | 32 (sazby 8 centrálních bank, 2/5/10leté výnosy, VIX, S&P 500, NASDAQ, HY spread, ropa, USD index, COT) – 104 457 pozorování |
| cenová data | Dukascopy 2023–2026: 310 824 svíček; FXCM 2013–2023: 1 051 684 svíček; FRED kurzy 13 měn 1971–2026 |
| páry | EUR/USD, USD/JPY, GBP/USD, USD/CHF, AUD/USD, USD/CAD, NZD/USD, EUR/JPY, GBP/JPY, EUR/GBP, EUR/CHF, AUD/JPY |

### Na co se model spoléhá

* **Cena (technika):** denní, 4hodinové a hodinové svíčky; EMA 20/50/200, ATR 14, RSI 14,
  efektivita trendu, swingové úrovně (podpora/odpor) a jejich životnost, šoky.
* **Fundamenty (veto + důvěra):** rozdíl sazeb a jeho změna (carry, přecenění), trend
  měnové politiky, pozicování spekulantů (CFTC), režim rizika (VIX, akcie, kreditní
  spread), komodity (CAD/AUD), kalendář událostí (jen živě, historii nemá).
* **Brány (tvrdá pravidla):** stav dat, R:R po nákladech, poloha vůči úrovni, „nehoň
  cenu“, šok, událost, spread, třída důvěry, režim, stabilita signálu.
