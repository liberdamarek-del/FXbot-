# Martingale a další systémy z hazardu – výzkum 5. 10. 2026

_Otázka uživatele: co martingale a další systémy z hazardu? Je to hazard, ale třeba zvýší pravděpodobnost.
Výpočty: `scripts/hazard_lab.py` (teorie, Kelly, mřížkový robot na hodinových cenách FXCM 2012–2026) a kolo 27
samoučení (`portfolio_sim.Money`: velikost dalšího obchodu podle výsledků uzavřených obchodů účtu)._

## Odpověď v kostce

1. **Pravděpodobnost výhry zvýšit jdou, průměrný výsledek ne.** Martingale zvedne podíl ziskových sezení
   (u férové sázky z 46 % na 82 %). Výsledek vsazené koruny zůstane přesně stejný (0,000). Platí se za to
   vzácnou obrovskou ztrátou: nejhorší sezení −1 885 jednotek proti −40 u stálé sázky.
2. **S náklady je to horší.** Martingale vsadí víc peněz, a tak zaplatí i víc spreadu. U sázky s náklady
   5 % prodělá v průměru 4× víc než stálá sázka (−21 proti −5 jednotkám).
3. **Na skutečných obchodech modelu** (kolo 27, přes stejnou bránu) neprošel ani jeden z 5 systémů
   (martingale 2×, mírný martingale 1,5×, anti-martingale, d'Alembert, Fibonacci). V profilu max vypadal
   martingale v letech 2019–22 lépe, v letech 2023–26 ale propad vyskočil z 28 % na 42–55 %.
4. **Mřížkový (martingale) robot**, nejčastější „automat“ na měny, uzavíral koše ziskem v 99,6 % případů.
   Přesto 34 z 60 účtů skončilo zničených a 59 z 60 prošlo propadem aspoň 50 %. S martingale (×2) skončil
   v plusu jediný účet z 30.
5. **Kelly** (matematicky nejrychlejší růst) by na obchod chtěl 36–42 % účtu jako marži. Model dává 20 %
   na silný signál, ale až 9 obchodů najednou (88 % účtu vázáno). Sází tedy už teď odvážně, větší sázky by
   nepomohly.

## 1. Teorie (100 sázek na sezení, 100 000 sezení)

| Sázka | Systém | Sezení v zisku | Průměr | Na vsazenou jednotku | Nejhorší sezení | Propad ≥ 50 jednotek |
|---|---|---|---|---|---|---|
| férová (50 %) | stálá sázka | 46,1 % | +0,03 | 0,000 | −40 | 0,0 % |
| férová | martingale (×2, 7 kroků) | **81,9 %** | −0,15 | 0,000 | **−1 885** | 39,1 % |
| férová | d'Alembert | 59,9 % | +0,07 | 0,000 | −346 | 36,4 % |
| férová | Fibonacci | 70,5 % | −0,04 | 0,000 | −430 | 21,9 % |
| férová | anti-martingale (×2 po výhře) | 44,3 % | +0,09 | 0,000 | −70 | 5,3 % |
| s náklady 5 % | stálá sázka | 31,0 % | −4,98 | −0,050 | −47 | 0,0 % |
| s náklady 5 % | martingale | **81,1 %** | **−21,18** | −0,049 | −2 579 | 43,1 % |
| s náklady 5 % | Fibonacci | 61,4 % | −11,25 | −0,049 | −508 | 26,4 % |
| ruleta (18/37) | stálá sázka | 35,3 % | −2,74 | −0,027 | −50 | 0,0 % |
| ruleta | martingale | **78,5 %** | **−13,14** | −0,028 | −2 145 | 44,2 % |

Ve sloupci „na vsazenou jednotku“ vychází u každého systému totéž, je to matematická jistota (Doobova
věta o volitelném zastavení). Systém přerozdělí výsledky z „častá malá ztráta“ na „často malý zisk, občas
katastrofa“. Průměr nezmění, a protože se vsází víc, zaplatí víc nákladů.

## 2. Na obchodech našeho modelu (kolo 27, brána v3)

Velikost dalšího obchodu podle výsledků uzavřených obchodů účtu. Marže se vždy znovu vybírá na letech
výběru a test je na neviděných letech.

Šampion měsíčního profilu: 2019–22 **+53,0 % / propad 29 %**, 2023–26 **+28,2 % / 24 %**.

| Systém | Měsíční 2019–22 | 2023–26 | Max 2019–22 | Max 2023–26 | Brána |
|---|---|---|---|---|---|
| martingale ×2 (max 3× za sebou) | +54,2 % / 33 % | +28,9 % / 32 % | +62,7 % / 23 % | **+11,9 % / 55 %** | zamítnuto |
| mírný martingale ×1,5 | +58,0 % / 31 % | +29,1 % / 25 % | +66,8 % / 23 % | +14,5 % / 46 % | zamítnuto |
| anti-martingale ×1,5 po zisku | +55,0 % / 22 % | +22,0 % / 25 % | +62,4 % / 35 % | +25,5 % / 24 % | zamítnuto |
| d'Alembert | +56,6 % / 31 % | +29,8 % / 25 % | +66,2 % / 23 % | +19,3 % / 42 % | zamítnuto |
| Fibonacci | +58,7 % / 29 % | +28,0 % / 25 % | +67,8 % / 24 % | +13,7 % / 42 % | zamítnuto |

Šampion profilu max: 2019–22 +62,8 % / 24 %, 2023–26 +19,7 % / 28 %.

Proč to nevyjde: model vyhrává asi 88 % obchodů, ztráty jsou vzácné, ale velké (stop 4 ATR, asi −110 %
marže) a chodí ve shlucích. Celý trh se otočí najednou, ztratí několik párů v jednom týdnu. Martingale
zvětší sázku právě do takové série. V letech 2023–26 (rok 2024 −15 %) to zdvojnásobilo propad. Kde systém
v letech 2019–22 „pomohl“, šlo jen o přerozdělení štěstí mezi roky.

## 3. Kelly – kolik sázet, když výhoda existuje

Kelly je jediný „sázkový systém“, který dává matematický smysl: při skutečné výhodě maximalizuje dlouhodobý
růst.

| | Měsíční profil | Profil max |
|---|---|---|
| obchodů 2012–2022 | 393 | 393 |
| úspěšnost | 88,8 % | 87,0 % |
| průměr na obchod | +6,0 % marže | +5,8 % marže |
| nejhorší obchod | −169 % marže | −135 % marže |
| **Kelly: marže na obchod** | **36 % účtu** | **42 % účtu** |
| model: marže na stupeň | 20 / 20 / 4 / 4 % | 15 / 15 / 6 / 6 % |
| nejvíc otevřených obchodů / vázáno | 9 / 88 % účtu | 9 / 98 % účtu |

Kelly počítá s jedním obchodem po druhém. Model má ale často otevřeno několik obchodů najednou a ty spolu
souvisejí. Skutečná sázka je tedy blízko Kellyho hranice nebo nad ní. Větší sázky by zvedly propady víc
než výnos. Model už sází zhruba „půl až celého Kellyho“.

## 4. Mřížkový / martingale robot (hodinové FXCM 2012–2026)

* **Pravidla:**
  * Robot otevře koš (první pozice 2 % účtu jako marže). Každých 0,5 denního ATR proti němu přidá pozici:
    stejně velkou (×1, „průměrování“) nebo dvojnásobnou (×2, martingale), nejvýš 5 nebo 8 pozic.
  * Celý koš zavře při zisku 0,2 ATR.
  * Směr: vždy nákup, podle sazeb, nebo proti včerejšímu pohybu.
* **Účet a náklady:** broker účet zavře při úrovni marže 50 % (ESMA). Náklady retailové, **swap není
  započten** (koše držené roky by ho platily nebo dostávaly podle směru).

| | Variant | Účet na konci výš než na začátku | Zničeno (< 10 %) | Propad ≥ 50 % | Úspěšnost košů |
|---|---|---|---|---|---|
| celkem (5 párů × ×1/×2 × 5/8 pozic × 3 směry) | 60 | 14 | **34** | **59** | **99,6 %** |

* **Martingale ×2:** u 29 z 30 variant skončí účet pod polovinou, u 23 je zničený (< 10 %). Jediná
  varianta v plusu (+3 % ročně) měla propad 84 %. První nucené uzavření přišlo už v letech 2012–2015.
* **Průměrování ×1:** 13 z 30 variant skončí v plusu, ale všechny s propadem 41–95 %. Koš „čeká na návrat“
  až 14 let, 11 účtů je zničených.
* Těch 14 „úspěšných“ variant vydělalo jen díky dlouhému trendu, který šel náhodou jejich směrem
  (dolar proti jenu 2012–2024, AUD/USD podle sazeb). Kdo by si robota vybral podle minulosti, vybral by
  právě tyto. Proto reklamy na tyto roboty ukazují krásné křivky.

## 5. Další „systémy“ a co z nich dává smysl

| Systém | Co dělá | Pro náš model |
|---|---|---|
| martingale, d'Alembert, Fibonacci, Labouchère | zvětšuje sázku po ztrátě | ne: nemění průměr, zvětšuje propady (otestováno) |
| anti-martingale, pyramidování | zvětšuje sázku po zisku nebo do trendu | ne: otestováno (kolo 27, dříve přikupování R-024) |
| průměrování dolů, mřížka | přikupuje proti pohybu | ne: robot výše, dříve přikupování v obchodu |
| Kelly, zlomek Kellyho | velikost podle výhody | model už je blízko; větší sázky ne |
| brzda po ztrátách (menší sázka v propadu) | opak martingale | otestováno (R-024), zamítnuto |
| velikost podle volatility | stejné riziko na obchod | součást profilu max |

## Závěr

Systémy z hazardu nezvyšují výnos ani šanci na zbohatnutí. Zvyšují jen pravděpodobnost, že *jednotlivé
období* skončí malým ziskem, a platí se za to velkou ztrátou jednou za čas. U pákového obchodování
s nuceným uzavřením účtu to znamená reálné riziko ztráty všeho. Jediné, co výsledek mění, je skutečná výhoda
pravidla (u nás sazby + krátkodobý pokles) a rozumná velikost sázky (Kelly), a to model už má.
