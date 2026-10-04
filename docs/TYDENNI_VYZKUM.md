# Týdenní výzkum trhu – jak funguje

Každou sobotu (spolu s učením modelu) se provede úplný zpětný rozbor právě skončeného týdne
(`scripts/tydenni_analyza.py`). Výsledek: `docs/tydenni/<rok>-W<týden>.md`, archiv v `learning/tydenni/`.

## Tři druhy výsledků (nikdy se nemíchají)

| | otázka | z čeho |
|---|---|---|
| **A) deskriptivní** | Co se stalo? | ceny týdne: týden, dny, úseky dne (UTC), největší pohyby, události, ostatní trhy, korelace |
| **B) atribuční** | Co s pohybem v týdnu souviselo? | podmínky aktivní v týdnu vs. následující pohyb – jen souvislost, **ne předpověď** |
| **C) prediktivní** | Co mělo skutečnou předpovědní schopnost? | podmínky vybrané jen na starších datech a ověřené na pozdějších (out-of-sample, walk-forward) a na týdnu samotném |

## Data a jejich kontrola

- Ceny: Yahoo 15 min a 30 min (posledních 60 dní), 1 h (2 roky) a FXCM 1 h (2012–2026). 4H a 1D se skládají
  z hodinových barů (1D = newyorské zavření 17:00).
- Ostatní trhy: výnos US 10Y, futures na 2leté dluhopisy, zlato, ropa, měď, S&P 500, VIX, dolarový index.
- Události: kalendář ForexFactory (čas, měna, význam, odhad, předchozí hodnota) archivovaný od 30. 9. 2026.
  **Skutečné hodnoty** jen u amerických zpráv z ALFRED (data v den zveřejnění), ověřené shodou předchozí hodnoty;
  jinak NEOVĚŘENO. Překvapení = skutečnost − odhad (u nezaměstnanosti je vyšší hodnota pro měnu negativní).
- Před výpočtem kontrola: chybějící bary, duplicity, časy, špatné OHLC, mezery, víkendová data, extrémní skoky,
  shoda zdrojů (Yahoo 15 min vs 1 h, Yahoo vs FXCM). Vadná data se ukážou a pár se vynechá.

## Technické testy

Přes 800 nastavení: RSI 5–28 s prahy 20/80 … 40/60, SMA/EMA 5–200, MACD (5/8/12 × 17/21/26/34 × 5/9/12),
Bollinger (10–50 × 1,5–3,0), Stochastic (5–21 × 3/5), ATR 5–28, ADX 7–28 s prahy 20–35, na 15M, 30M, 1H, 4H, 1D
a stavy vyššího timeframe (např. 1H RSI > 50 + 4H cena nad EMA50 + ADX > 25). Kombinace postupně: nejlepší
jednotlivé → dvojice → trojice → čtveřice, každá složka z jiné rodiny indikátorů, minimální počet pozorování.

Výsledek je vždy forward pohyb za pevný horizont (15M: 1 h, 30M: 2 h, 1H: 4 h, 4H: 24 h, 1D: 5 dní), vzorky
se nepřekrývají. Podmínka se hodnotí podle toho, o kolik byl pohyb po ní **lepší než průměrný pohyb páru** ve stejném
období – jinak by „předpovídaly“ i podmínky, které jen kopírují dlouhý trend páru. U každé podmínky: počet pozorování, průměr, medián, směrodatná odchylka, úspěšnost, max zisk
a ztráta, t, poměr průměr/sd, korelace, počet období, kdy fungovala / selhala, a průměr v pipech po spreadu.

- **In-sample** 2012–2019 (u 15M/30M prvních 75 % z 60 dní) – tady se hledá.
- **Out-of-sample** 2020 – týden před analýzou – tady se ověřuje (výběr ho neviděl).
- **Walk-forward**: najdi na minulosti → zamkni → otestuj další rok (u 15M/30M týden) → posuň. Podíl zamčených
  podmínek, které pak fungovaly, kolem 50 % = výběr podle minulosti nemá předpovědní schopnost.
- **Týden jako nový test**: podmínky zamčené jen na datech, jejichž výsledek byl znám před začátkem týdne.
- **Robustnost**: každá složka posunutá na sousední nastavení (RSI13/15 vedle RSI14, EMA18/22 vedle EMA20,
  práh ±5 …). Drží-li ≥ 75 % sousedů směr a aspoň polovinu účinku: **ROBUST**, jinak **POSSIBLE OVERFIT**.
- **Režimy**: vysoká/nízká volatilita, trend/range (ADX), risk-on/off (VIX), rostoucí/klesající USD a výnosy –
  u každé ověřené podmínky výsledek v každém režimu; obrácený směr se vyznačí.
- Vzorek: N < 20 INSUFFICIENT SAMPLE, 20–50 slabá, 50–100 použitelná, > 100 silnější evidence (nastavitelné).

## Ochrana proti chybám

- **Žádný pohled do budoucnosti**: indikátor v čase t používá jen bary do t; vyšší timeframe až po zavření jeho
  baru; událost až po jejím čase; zamčený výběr se nezmění, když se změní ceny týdne (ověřeno testem F2).
- **Mnoho testů = náhodné „výhry“**: u každého páru a timeframe je uvedeno, kolik náhodných výsledků s |t| ≥ 3
  se dá čekat. Výsledek se nebere podle jednoho čísla, ale podle out-of-sample, walk-forward a robustnosti.
- Korelace a časová shoda se zprávou nejsou důkaz příčiny. Lead/lag mezi různými zdroji (spot FX vs futures)
  může být jen posun časových značek – takové výsledky jsou označeny TIMESTAMP UNVERIFIED.

## Dlouhodobý archiv

Každý týden se uloží výsledky zamčených podmínek, události s překvapením a reakcemi a technický stav v čase
zprávy. Po několika týdnech lze odpovědět např. „RSI14 + EMA20 fungovala posledních 20 týdnů u EUR/USD
v trendovém režimu“:

    python scripts/tydenni_analyza.py --dotaz "RSI14>50 & C>EMA20" --par EUR/USD --tf 1H --tydnu 20 --rezim trend

(týdenní výsledky z historie, směr vždy jen z dat před daným týdnem). Do obchodního modelu se nic nedostane
přímo – jen jako pokus přes testovací bránu učení.

## Napojení na model (od 4. 10. 2026)

- **Testovací brána:** výzkum se zkouší jako filtr obchodů modelu (vynechat / zmenšit obchod, proti kterému
  výzkumné podmínky páru převážně ukazují, nebo zvětšit obchod, který podporují) a jako doplňkové obchody v den
  zpráv (rozhodnutí Fed/ECB/BoJ/BoE, americké NFP a CPI), když technický stav páru odpovídá potvrzenému vzorci.
  Pro každé testovací období se výzkum vybírá jen z dat před ním. První test (4. 10.) neprošel: výnos na riziko
  se v jednom ze dvou období zhoršil. Opakuje se jednou za čtvrtletí s novými daty.
- **Na webu (informace):** sekce Týdenní výzkum trhu, u párů aktivní výzkumné podmínky, u signálů kolik
  podmínek je pro / proti, poznámka před zprávou, pro kterou výzkum našel vzorec.
- **Živý test:** u každého obchodu modelu se ukládá, zda byl výzkum pro, nebo proti. Po několika týdnech
  se ukáže, jestli obchody podporované výzkumem dopadají lépe.
