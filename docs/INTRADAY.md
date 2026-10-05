# Obchodování v rámci dne (hodiny, minuty) – výzkum 5. 10. 2026

_Otázka uživatele: zkoušel jsi obchodování v rámci dne, hodinové nebo minutové? Proč existují modely, které to
dělají a vydělávají? Zkoušej, dokud na něco nepřijdeš, klidně uvolni pravidla._

Data a postup:

* **Data:**
  * hodinové BID/ASK svíčky FXCM 2012–2026 (12 párů modelu);
  * minutové BID/ASK svíčky FXCM 2016–2026 (12 párů, 6 996 týdenních souborů, `scripts/fxcm_m1.py`).
* **Náklady na každé straně obchodu:**
  * polovina z většího z obou spreadů: retailového (EUR/USD 0,8 pipu, jiné páry víc) a skutečného spreadu
    FXCM v dané hodině nebo minutě (v noci a při rolloveru je širší);
  * plus polovina skluzu 0,4 pipu.

  Jsou to stejné náklady jako u denního modelu.
* **Pravidlo „zisk ≥ 10 % marže na obchod“ je tu záměrně vypnuté** (krátké obchody mají malé zisky). Pozice
  se otevírá jen ze svíček, které se uzavřely před vstupem.
* **Výběr a test:**
  * hodiny: výběr 2012–2018, kontrola 2019–2022, test 2023–2026;
  * minuty: 2016–2019 / 2020–2022 / 2023–2026.
* **Strojové učení:** učí se vždy jen na minulých letech.

## Odpověď v kostce

1. **Ano, teď už je to vyzkoušené.**
   * 300 hodinových strategií v 9 rodinách;
   * 1 728 kombinací pár × hodina dne;
   * strojové učení (LightGBM, 30 ukazatelů, 4 horizonty, přeučení každý rok);
   * přes 80 minutových strategií v 5 rodinách.

   Po retailových nákladech **nevydělává ani jedna ve všech třech obdobích.**
2. **Výhoda přitom existuje, jen je menší než náklady.** Strojové učení každý rok předpovídá pohyb na hodinu
   dopředu lépe než náhoda. Před náklady dává +0,011 až +0,021 % na obchod, retailový obchod ale stojí
   0,011–0,028 % ceny. Noční „scalper“ má před náklady kladný výsledek ve všech obdobích (+0,2 až +0,9 pipu
   na obchod) a úspěšnost 61–73 %. Spread 0,8–1,6 pipu plus skluz ho ale převáží. Sezónnost hodin dne je
   skutečná: 683 z 1 728 kombinací je hrubě kladných v obou kontrolních obdobích, náhodou by jich bylo kolem 432.
3. **Proč na tom jiní vydělávají:** platí za obchod desetinu toho co retail, nebo na obchodech přímo
   vydělávají (kapitola 1). Stejná výhoda +1 až +2 pipy na obchod je pro banku zisk, pro retailový účet
   ztráta.
4. **Uvolnění pravidel denního modelu** (kolo 26, přes stejnou bránu, kapitola 5):
   * Zrušení minimálního cíle 10 % marže nic nezhorší, ale ani dost nezlepší.
   * Volnější vstup (RSI(2) < 10) nebo rozhodování každý den přidá obchody: až 5–7 ziskových měsíčně místo
     2–3. Roční výnos ale klesne zhruba na polovinu.
   * Bránou neprošlo nic. Šampion zůstává.
5. Ziskový systém v rámci dne by navíc musel obchodovat **automaticky**, desítky obchodů denně. Ručně to
   nejde a projekt k brokerovi obchody neposílá (jen čte).

## 1. Proč existují modely, které v rámci dne vydělávají

| Kdo | Na čem vydělává | Náklady | Lze to napodobit z retailového účtu? |
|---|---|---|---|
| tvůrci trhu (banky, velcí brokeři) | **spread**, který platí ostatní, a tok příkazů klientů (vidí, kam se trh tlačí) | záporné: spread inkasují | ne |
| vysokofrekvenční firmy (HFT) | rychlost v mikrosekundách, rozdíly cen mezi burzami a platformami, kolokace serverů | 0,05–0,2 pipu, rabaty | ne |
| kvantitativní fondy | statistické vzorce (sezónnost hodin, krátkodobé obraty, faktory měn), velký objem | 0,1–0,3 pipu | jen vzorce s pohybem mnohem větším než retailový spread |
| retailový obchodník | stejné vzorce | **1–3 pipy** (spread + skluz), u nočních hodin víc | vzorce v řádu 1 pipu nemají šanci |

* Dávají smysl i měření tohoto výzkumu. Hrubá výhoda strojového učení na 1 hodinu (+1 až +2 pipy)
  nebo nočního obratu (+0,5 pipu) je pro firmu s náklady 0,2 pipu čistý zisk na tisících obchodů ročně.
  Retailový účet ji odevzdá na spreadu.
* Komerční „roboti“, kteří slibují zisky z obchodování v rámci dne, obvykle ukazují testy bez reálných nákladů,
  přizpůsobené minulosti, nebo jen ty, kterým se zrovna dařilo. Brokeři v EU musí uvádět podíl retailových
  účtů, které na CFD prodělávají. Bývá zhruba 70–80 %.
* Kde retail šanci má: u **delšího držení** (dny až týdny), kdy je pohyb mnohonásobně větší než spread. Přesně
  to dělá denní model (cíl 0,75 ATR je zhruba 40–60 pipů proti nákladům 1–3 pipy).

## 2. Hodinové strategie (`scripts/intraday_lab.py`)

Rodiny strategií (vždy všechny varianty, nic vybrané ručně):

| Rodina | Ekonomický důvod | Variant | Kladné po nákladech ve všech 3 obdobích |
|---|---|---|---|
| hodina dne (sezónnost, směr z let 2012–18) | toky v různých seancích | 144 | 0 |
| šok v hodině > 2–4 ATR (sledovat / proti) | přestřelení, likvidita | 24 | 0 |
| víkendová mezera v pondělí | obrat po víkendu | 20 | 0 |
| carry podle směru sazeb v seanci | kladný úrok, stejný fundament jako model | 10 | 0 |
| průraz asijského rozpětí v Londýně (sledovat / proti) | otevření Londýna | 18 | 0 |
| momentum dne (pohyb od zavření NY do poledne → zbytek dne) | Gao a kol. 2018, Elaut a kol. 2018 | 48 | 0 |
| průraz včerejšího maxima nebo minima | stop příkazy nad úrovní | 4 | 0 |
| Gotobi u jenu (5., 10., … den, fixing v Tokiu 9:55) | dovozci kupují dolary | 8 | 0 (efekt menší než spread, po 2016 slábne) |
| hodinové poklesy ve směru sazeb (mechanismus denního modelu na hodinách) | jako denní model | 24 | 0 |
| **celkem** | | **300** | **0** |

**Hodina dne po párech** (1 728 kombinací pár × hodina × délka držení 1–8 h):

* hrubě kladných v obou kontrolních obdobích: 683, náhodou by jich bylo kolem 432;
* sezónnost je tedy skutečná, ale po nákladech kladných jen 12 a žádná s jistotou t > 2.

Příklad:

* EUR/JPY dlouhá pozice od 16:00 Londýna na 8 h: před náklady +0,047 / +0,028 / +0,014 % (klesá);
* po nákladech +0,032 / +0,013 / +0,002 %.

Typické náklady na celý obchod (tam i zpět, medián):

| | EUR/USD | USD/JPY | GBP/USD | USD/CAD | EUR/JPY | EUR/GBP | GBP/JPY | AUD/USD | USD/CHF | EUR/CHF | AUD/JPY | NZD/USD |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| % ceny | 0,011 | 0,012 | 0,012 | 0,015 | 0,015 | 0,019 | 0,019 | 0,019 | 0,019 | 0,019 | 0,023 | 0,028 |
| průměrný pohyb za hodinu % | 0,064 | 0,072 | 0,070 | 0,060 | 0,078 | 0,059 | 0,088 | 0,089 | 0,068 | 0,043 | 0,100 | 0,093 |

## 3. Strojové učení (`scripts/intraday_ml.py`)

* **Model a vstupy:** LightGBM, 30 vstupů. Patří mezi ně:
  * pohyby za 1–120 h, poloha v rozpětí;
  * RSI hodinové i denní, volatilita, spread;
  * hodina a den;
  * pohyb dolaru, eura a jenu proti ostatním;
  * změna sazeb a carry.
* **Cíl:** pohyb za 1, 4, 8, 24 h.
* **Učení:** každý rok 2016–2026 se model učí jen na předchozích letech. Práh obchodování se nastavuje na
  předchozím roce.

| Horizont | 2016–18 hrubě / čistě | 2019–22 hrubě / čistě | 2023–26 hrubě / čistě | Obchodů ročně |
|---|---|---|---|---|
| 1 h | +0,011 / **−0,009 %** | +0,016 / **−0,009 %** | +0,021 / **−0,013 %** | 420–1 370 |
| 4 h | +0,017 / **−0,001 %** | +0,015 / **−0,006 %** | +0,032 / **+0,011 %** (t 1,0) | 440–1 010 |
| 8 h | +0,030 / **+0,011 %** | +0,004 / **−0,016 %** | +0,039 / **+0,018 %** (t 1,2) | 410–820 |
| 24 h | +0,026 / **+0,006 %** | +0,025 / **+0,004 %** | +0,022 / **−0,002 %** | 330–670 |

* Hrubá výhoda je kladná v každém horizontu a téměř v každém roce, takže model něco skutečného vidí.
* Po nákladech zůstává kolem nuly a v žádném horizontu není jistě kladná ve všech obdobích.
* Při 30násobné páce dělá i 0,018 % ceny jen asi 0,5 % marže na obchod.
* Obchod jen tehdy, když předpovězený pohyb převýší náklady páru 1× nebo 2× (předem stanovené dvě úrovně,
  místo prahu z předchozího roku):

  | Práh | Horizont | 2016–18 čistě | 2019–22 čistě | 2023–26 čistě |
  |---|---|---|---|---|
  | 1× náklady | 4 h | −0,003 % | −0,009 % (t −2,8) | −0,014 % (t −3,7) |
  | 1× náklady | 8 h | −0,005 % | −0,012 % (t −3,1) | −0,005 % |
  | 1× náklady | 24 h | −0,009 % | −0,015 % (t −2,1) | −0,002 % |
  | 2× náklady | 4 h | +0,006 % (t 0,9) | −0,004 % | +0,004 % (t 0,4) |
  | 2× náklady | 8 h | +0,009 % (t 1,5) | −0,011 % | −0,001 % |
  | 2× náklady | 24 h | −0,009 % | −0,022 % (t −2,3) | +0,013 % (t 1,4) |

  Ani jedna úroveň není kladná ve všech třech obdobích.

## 4. Minutové strategie (`scripts/minute_lab.py`)

Minutové BID/ASK svíčky FXCM 2016–2026 (asi 3,8 milionu minut na pár).

| Rodina | Ekonomický důvod | Výsledek po nákladech | Před náklady |
|---|---|---|---|
| noční scalper (po zavření NY do 1:00 Londýna, návrat k 60minutovému průměru) | klidné hodiny, obraty | všech 9 variant záporných ve všech obdobích, úspěšnost 61–73 % | **kladný ve všech obdobích**, +0,002 až +0,009 % |
| kulatá čísla 00/50 (Osler 2003: příkazy na výběr zisku u kulatých čísel → odraz, stop příkazy za nimi → průraz) | shluky příkazů | vše záporné | kolem nuly |
| průraz rozpětí po otevření Londýna (15/30 min) | první hodina Londýna | vše záporné | +0,000 až +0,006 % |
| minutový šok > 4–8 ATR (sledovat / proti) | přestřelení | vše záporné | kolem nuly |
| NFP a CPI v 8:30 New York (pohyb prvních 1–5 minut sledovat / proti, držet 15–120 min) | reakce na zprávu | nic stabilního (jen asi 40 zpráv na období) | – |

* **Páry EUR/USD, USD/JPY, GBP/USD, USD/CHF:** 39 variant, po nákladech kladná ani jedna.
* **Noční scalper a zprávy navíc na EUR/GBP, EUR/CHF, USD/CAD a EUR/JPY** (klasické páry nočních robotů):
  * noční scalper: všech 9 variant záporných ve všech obdobích. Před náklady +0,006 až +0,015 %
    ve všech obdobích, úspěšnost 53–70 %.
  * zprávy: 1 z 24 variant kladná ve všech třech obdobích (CPI, proti pohybu prvních 5 minut, držet
    60 min, jen USD/CAD). Jistota je ale t 1,5 / 0,2 / 0,6 při 38–50 obchodech na období a u 24 variant
    by se taková jedna čekala i náhodou. Neprokázáno.

## 5. Uvolnění pravidel denního modelu (kolo 26, brána v3)

Šampion měsíčního profilu (živý čas): **2019–22 +53,0 % ročně, propad 29 %; 2023–26 +28,2 %, propad 24 %;
3,1 / 2,0 ziskového obchodu měsíčně**.

| Uvolnění | Měsíční profil 2019–22 | 2023–26 | Ziskových měsíčně | Brána |
|---|---|---|---|---|
| bez minimálního cíle 10 % marže (i malé cíle v klidných obdobích) | +56,2 % / 20 % | +28,6 % / 24 % | 3,4 / 2,1 | zamítnuto: v letech 2023–26 lepší jen o 2 % (nutných 10 %) |
| minimální cíl 5 % marže | stejné jako výše | | | zamítnuto (cíle pod 5 % se nevyskytují) |
| vstup už při RSI(2) < 10 (místo < 5) | +24,0 % / 25 % | +14,9 % / 16 % | 4,7 / 3,2 | zamítnuto: víc obchodů, poloviční výnos |
| RSI(2) < 10 a bez minimálního cíle | +22,1 % / 25 % | +15,9 % / 14 % | 5,1 / 3,4 | zamítnuto |
| rozhodovat každý den v 16:00 New York, ne jen v pátek | +22,4 % / 22 % | +15,6 % / 11 % | **6,6 / 5,2** | zamítnuto: víc ziskových obchodů, ale nižší výnos |

Profil max: všech 5 uvolnění je horších než šampion (např. bez minimálního cíle 2019–22 +42,9 % proti
+62,8 %).

Co z toho plyne:

* Přísnost pravidel model nebrzdí. Volnější vstupy přidají obchody, které jsou v průměru slabší, takže
  roční výnos klesne. Pravidlo minimálního cíle přitom vyřazuje jen málo obchodů a jeho zrušení nic nezhorší.
* Kdo chce **víc obchodů měsíčně za cenu nižšího výnosu**, může vzít variantu „každý den“:
  * 5–7 ziskových obchodů měsíčně;
  * asi +16–22 % ročně;
  * propad 11–22 %.

  Bránou neprošla, protože brána hlídá výnos na riziko, ne počet obchodů. Je to rozhodnutí pro uživatele.
  Živě by navíc vyžadovala denní vyhodnocení ve 22:00 a vstup každý den.

## 6. Závěr

* Obchodování v rámci dne na těchto 12 párech s retailovými náklady **nemá na datech 2012–2026 ověřitelnou
  výhodu**. Krátkodobé vzorce existují, ale jsou menší než spread. Proto na nich vydělávají ti, kdo spread
  inkasují nebo platí desetiny pipu.
* Denní model funguje, protože drží obchod dny a cílí na pohyby desetkrát až stokrát větší než náklady.
* Kdyby se změnily náklady (účet ECN s průměrným spreadem pod 0,3 pipu včetně provize) a obchody se zadávaly
  automaticky, stálo by za to znovu otestovat dvě rodiny: noční obrat a strojové učení na 1–4 h. Hrubou
  výhodu mají ve všech obdobích. Ověření se skutečnými náklady konkrétního účtu je **NEOVĚŘENO**.
