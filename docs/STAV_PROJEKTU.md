# Stav projektu FXBOT – paměť systému

_Kdo na projektu pracuje (člověk i AI), čte tento soubor jako první a po každé významné změně ho upraví.
Stavy: **HOTOVO/OVĚŘENO** (funguje a ověřilo se testem nebo daty), **ROZPRACOVÁNO**, **BLOKOVÁNO** (chybí
zdroj nebo rozhodnutí), **NEOVĚŘENO** (předpoklad bez důkazu), **CHYBA** (známá chyba).
Podrobná historie změn: `docs/CHANGE_LOG.md`, pokusy učení: `docs/UCENI_LOG.md`._

Poslední revize: 2026-10-07 (R-037).

## 1. Účel

Model hledá na 12 měnových párech obchody s historicky vysokou šancí na zisk. Signály dává uživateli, ten
obchoduje sám. Projekt nikdy neposílá příkazy brokerovi a u brokera nic nemění.

## 2. Jak systém funguje (tok dat)

```
 DATA                       ROZHODOVÁNÍ                         VÝSTUP                ZPĚTNÁ VAZBA
 FXCM hodinové ceny ──┐
 FRED sazby ──────────┼─► simulátor (profit_deep) ─► účet (portfolio_sim) ─► brána učení (self_learn)
 rozhodnutí CB, makro ┤        ▲                                               │ šampion (learning/*.json)
 VIX, výnosy ─────────┘        │                                               ▼
                               │                          živé signály (signals_live, Yahoo ceny)
                               │                                               │
                               │                     diagnostika + stav (aktualizace.py) ─► přehled (web)
                               │                                               │
                               └──── forward test modelu (forward_trades.json) ◄┤
                                     deník uživatele (přehled → denik_uzivatele)◄┘
 týdenní výzkum (tydenni_analyza) ─► most do modelu (vyzkum_most) ─► pokusy přes bránu
```

Každá změna pravidel vzniká jako pokus, projde testem naslepo na neviděných letech (brána) a teprve pak jde do
živých signálů. Živý výpočet používá stejný kód a stejný čas rozhodnutí (pátek 16:00 New York) jako historie.

## 3. Moduly a stav

| Modul | Úloha | Stav | Čím ověřeno |
|---|---|---|---|
| Data cen (FXCM) | historie pro učení | HOTOVO/OVĚŘENO, viz bod 5 (zpoždění) | diagnostika „ceny“ |
| Sazby FRED, CB, makro | fundamenty bez pohledu do budoucna | HOTOVO/OVĚŘENO | audit R-029, testy |
| Simulátor + účet | obchody a účet se složeným úročením, propad i z otevřených obchodů | HOTOVO/OVĚŘENO | 52 testů (`python fxbot.py test`) |
| Brána učení v3 | změna jen při zlepšení na neviděných letech | HOTOVO/OVĚŘENO | audit R-029 (asi 5 % náhodných změn projde) |
| Šampioni (měsíční, max) | živá pravidla | HOTOVO/OVĚŘENO | test naslepo 2019–22 a 2023–26 |
| Živé signály | totéž co historie, pátek 16:00 NY | HOTOVO/OVĚŘENO | forward test = backtest (R-029) |
| Přehled + deník | signály, plán, deník uživatele | HOTOVO/OVĚŘENO | hodinové aktualizace |
| Forward test | skutečné obchody modelu od 2. 10. 2026 | ROZPRACOVÁNO | 2 obchody, závěr až po 4+ týdnech |
| Týdenní výzkum | popis a vysvětlení týdne, kandidáti na pokusy | HOTOVO/OVĚŘENO | archiv learning/tydenni |
| Velikost podle rizika | stop stojí nejvýš zvolené % účtu (výchozí 5 %) | HOTOVO/OVĚŘENO (R-037) | test naslepo 2019–22, 2023–26; test_f3_audit; přehled v prohlížeči |

## 4. Co se už zkoušelo (aby se to neopakovalo)

Seznam zamítnutých rodin je ve frontě nápadů v `CLAUDE.md` a v `docs/UCENI_LOG.md`. Souhrnné závěry:
intradenní a minutové obchodování (INTRADAY.md), systémy z hazardu (HAZARD.md), pivoty (PIVOTY2.md),
anomálie z literatury (ANOMALIE.md), mezitrhy (VYZKUM_POHYBY_2026-10-02.md).

## 5. Otevřené body

| Bod | Stav | Poznámka |
|---|---|---|
| Historie FXCM končí 25. 9. 2026 (12 dní) | NEOVĚŘENO | příčina (zpoždění týdenních souborů zdroje?) se ověří v sobotu po stažení; živé signály berou ceny z Yahoo |
| Páka u brokera uživatele pro AUD/NZD (počítáme 1:20) | NEOVĚŘENO | potvrdit u brokera |
| Rozhodování těsně před zavřením místo 16:00 | NEOVĚŘENO | posledních 10 minut dne nemáme v datech |
| Dny oznámení BoE 2015-05/06/07 | NEOVĚŘENO | uložený den může být den hlasování |
| BoE 8/2015–12/2016, BoC, RBNZ | BLOKOVÁNO | zdroj nedostupný |
| Intradenní strategie | BLOKOVÁNO | jen s ECN účtem (< 0,3 pipu) a automatickým zadáváním |
| Mezera přes víkend za stopem | OVĚŘENO (zanedbatelné v historii) | 1 z 31 stopů, o 4,5 % vzdálenosti stopu; budoucí krize NEOVĚŘENO |
| Forward test s velikostí podle rizika | ROZPRACOVÁNO | nové záznamy mají váhu stupně; vyhodnotit po 4+ týdnech |
| `scripts/pivot_lab.py` řádek 147: nedefinovaná proměnná `row_wk` | CHYBA (neaktivní výzkumný skript) | živý systém ho nepoužívá; rodina pivotů je uzavřená (R-014), oprava jen při jejím dalším použití |
| Chyby živého systému | žádná otevřená CHYBA | diagnostika 0 chyb, 52 testů prošlo |

## 6. Postup práce (pravidlo)

POZOROVAT → POCHOPIT → PROPOJIT INFORMACE → ANALYZOVAT → NAVRHNOUT → IMPLEMENTOVAT → OTESTOVAT → VYHODNOTIT.
Před změnou zjistit, které části systému změna ovlivní (simulátor, účet, brána, živé signály, přehled, forward
test, diagnostika). Po změně ověřit všechny dotčené části a testy. Chybějící údaje nedoplňovat odhadem
(NEOVĚŘENO). Výsledky forward testu a deníku jsou zpětná vazba pro další rozhodnutí.
