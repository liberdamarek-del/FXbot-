# Jak model zlepšovat, aby nebyl náhodný – postup a první výsledky

Stav k 2026-10-01. Navazuje na `docs/OOS_REPORT.md` (model V7.8.0 na 2016–2023 = náhoda).

## 1. Proč ne „ladit model, dokud nevyjde“

Každý pohled na výsledek a každá úprava je šance napasovat se na šum. Se 100 pokusy
vyjde čistě náhodou několik „výborných“ variant – a na nových datech zklamou.
Proto se zlepšování dělá **mimo model**, na jednoduchých signálech, s pevným protokolem,
a do modelu se smí dostat jen to, co projde.

## 2. Protokol (vynucený kódem)

| Krok | Co | Kde |
|---|---|---|
| 1 | Hypotézy a pravidla se **zapíší a commitnou dřív**, než se spočítá jediný výsledek | `ROUNDS` v `scripts/research_signals.py`, `scripts/research_factors.py` |
| 2 | **Objev** jen na jednom období (denní: 2016-09..2021-12; měsíční: 1990..2012) | `discover` |
| 3 | Kandidát musí projít přísnou hranicí (t ≥ 3 resp. 2,5 – zohledňuje počet testů), mít stejné znaménko v obou polovinách a kladný výsledek po nákladech | automaticky |
| 4 | Kandidáti se **zamknou** (soubor + SHA-256), nic se nepřidá | `data/research/candidates*.json` |
| 5 | **Potvrzení jednou** na datech, která výběr neviděl (denní: 2014–2016 a 2022–2026; měsíční: 2013–2026) | `confirm` |
| 6 | Jen potvrzený signál → návrh změny v `docs/CHANGE_LOG.md` → plný backtest modelu → **dopředný test** zamčených predikcí s párovou kontrolou proti náhodě | `fxbot.py review` |

Obchod ve výzkumu: vstup na denním závěru, výstup po 1/5/20 dnech; výsledek po nákladech
(typický retail spread + skluz) **a swapu** (rozdíl sazeb − 1 % p.a. přirážka). Statistika bez
překrývajících se obchodů; všechny páry jednoho dne = jedno pozorování (páry sdílejí USD).

## 3. Co jsme prohledali

| Kolo | Hypotézy | Testů | Výsledek |
|---|---|---|---|
| 1 | 23 standardních signálů: momentum 1–250 dní, vzdálenost od EMA, RSI, průrazy, carry, změny sazeb 2y/10y, trend politiky CB, COT pozicování, VIX/riziko, ropa (CAD) | 138 | **žádný kandidát** (nejlepší t = 1,2) |
| 2 | 6 podmíněných efektů z literatury: carry jen v klidném trhu, obrat po šoku volatility, momentum jen v čistém trendu, extrémy COT, šok sazeb, USD na konci měsíce | 36 | **žádný kandidát** (nejlepší t = 1,6) |
| 3 | Klasické měnové faktory, 13 měn, 1990–2026 (FRED): carry, momentum 1/3/12-1 měs., 5letý návrat (value), carry+momentum, dollar carry | 7 | 1990–2012 všechny kladné (carry +4,0 % p.a., value +4,2 %, carry+momentum +4,8 %, t = 2,93) → **2013–2026 nepotvrzeno** (−0,8 % p.a.; po retail nákladech −3,1 %) |

Podrobné tabulky: `docs/VYZKUM_OBJEVY_K1.md`, `_K2.md`, `_K3.md`, `docs/VYZKUM_POTVRZENI_K3.md`.
Kontrolní období denních kol (2014–2016, 2022–2026) zůstala **nedotčená** – nic nebylo
zamčeno, takže jsou dál k dispozici pro další kola.

## 4. Proč je to tak těžké – statistická síla

Na hranici t = 3 lze prokázat jen strategii s ročním Sharpe ratio (po nákladech):

| Délka dat | Potřebný Sharpe (t = 3) | (t = 2) |
|---|---|---|
| 5,5 roku (jedno období) | 1,28 | 0,86 |
| 12,7 roku | 0,84 | 0,56 |
| 30 let | 0,55 | 0,37 |

Známé měnové efekty mají Sharpe 0,3–0,7 **před** retail náklady. Na pár letech dat je
proto nelze odlišit od náhody – a model, který „vypadá dobře“ na 3 letech, je skoro jistě
napasovaný šum. To platí pro jakýkoli model, nejen pro tento.

## 5. Co může reálně pomoci (seřazeno podle naděje)

1. **Informace, kterou trh nemá hned v ceně – data, která sbíráme dopředu.**
   * *Sentiment retailových klientů* (podíl long/short u brokerů – OANDA, IG, Myfxbook).
     Historicky se choval kontrariánsky (dav se mýlí na extrémech). Zdarma není historie,
     ale přes váš účet ho lze **ukládat každou hodinu** a za 6–12 měsíců otestovat tímto protokolem.
   * *Překvapení v makrodatech* (skutečnost vs. konsenzus). Trh reaguje v minutách – pro
     retail jen jako filtr (neobchodovat proti čerstvému překvapení), ne jako signál.
2. **Delší a širší historie pro známé faktory.** Faktory po 2012 oslabily; mohou se vrátit
   (vyšší úrokové rozdíly od 2022). Sledovat je měsíčně (`research_factors.py`) a znovu
   potvrdit, než se použijí. S retail swapovou přirážkou ~1 % p.a. ale zbývá málo – u
   carry rozhoduje cena swapu u brokera (zjistit u vašeho brokera).
3. **Náklady jsou páka, kterou máte v ruce.** Kde je hrubá výhoda malá, rozhoduje spread
   a swap: broker s nízkými spready a férovými swapy může z nuly udělat malé plus –
   a z malého plusu větší.
4. **Řízení rizika místo směru.** Volatilita *je* předpověditelná (shlukuje se). Velikost
   pozice podle volatility nezlepší směr, ale sníží propady a zlepší poměr výnos/riziko
   čehokoli, co výhodu má.
5. **Seznam dalších kol k otestování** (každé zapsat předem do `ROUNDS`):
   sezónnost v rámci dne (měna oslabuje během „domácích“ obchodních hodin – Breedon & Ranaldo),
   týdenní obrat po velkém pohybu jen u nejlikvidnějších párů, kombinace sentimentu
   a pozicování COT.

Co **nepomůže**: přidávání dalších indikátorů na stejná cenová data, ladění parametrů
modelu na 2023–2026, vybírání „nejlepšího páru“ zpětně.

## 6. Spuštění

```sh
python scripts/research_signals.py extract            # tabulka signálů 2014-2026 (~10 s)
python scripts/research_signals.py discover --round N # objev nového kola (N z ROUNDS)
python scripts/research_signals.py confirm --round N  # jednorázové potvrzení
python scripts/research_factors.py fetch|discover|confirm   # měsíční faktory (FRED 1990-2026)
```

Potřebná data: `data/oos_fxcm` a `data/early_fxcm` (FXCM: `python scripts/oos_fxcm.py download` a `download --early`),
archiv Dukascopy, fundamenty. Nové kolo = nový zápis do `ROUNDS` a commit **před** spuštěním.
