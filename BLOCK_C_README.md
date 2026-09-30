# FXBOT Blok C – technická analýza (TECH-0.1)

Vyžaduje B3.3.

## Co je nové

| Soubor | Účel |
|---|---|
| src/indicators.py | EMA, ATR, RSI (Wilder), swingové body s filtrem výraznosti, shlukování úrovní |
| src/tech_analysis.py | analýza 4h / 1h / 15min z odvozených svíček: trend, volatilita, podpory a odpory, jeden návrh na pár |
| scripts/analyze.py | český výpis: přehled všech párů, TOP 3, detail jednoho páru, volitelně zamčení do evidence predikcí |
| test_c1, test_c2 | ruční výpočty indikátorů; pravidla návrhů; syntetické trhy; náhodné trhy, kde evidence predikcí kontroluje každý návrh |

## Pravidla (podle Wordu tam, kde jsou implementovatelná)

- návrh vznikne jen při datech **CURRENT**, jinak NEOBCHODOVAT s důvodem
- poměr rizika a zisku aspoň **1:1,5** proti TP1 (modul 55)
- SL za úrovní + 0,5 ATR, TP1 před protilehlou úrovní nebo z ATR (moduly 53, 54)
- **no-chase**: po pohybu kolem 1 ATR ve směru se nedává NOW, jen WAIT (modul 48)
- rozhodnutí: KOUPIT TED / PRODAT TED / CEKAT NA NAKUP / CEKAT NA PRODEJ / NEOBCHODOVAT

Všechny prahy jsou **provizorní** (nejsou ověřené mimo vzorek). Je to technický návrh bez makra
a bez zaruky, ne investiční doporučení.

## Použití

    python scripts/analyze.py                  # všechny páry + TOP 3
    python scripts/analyze.py --pair EUR/USD   # detail jednoho páru
    python scripts/analyze.py --lock           # navíc zamkne použitelné návrhy do evidence predikcí

Nejdřív `python scripts/update_data.py`, aby byla data CURRENT.

Vrácení zpět: `python …/apply_block_c.py --rollback backup_block_c_<časová_značka>`
