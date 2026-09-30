# FXBOT Blok B2 – všech 7 hlavních párů a setrné průběžné stahování

Vyžaduje nainstalovaný Blok A a Blok B.

## Co se mění

| Soubor | Změna |
|---|---|
| src/data_update.py | výchozí seznam = 7 hlavních párů (EUR/USD, USD/JPY, GBP/USD, USD/CHF, AUD/USD, USD/CAD, NZD/USD) × 1min, 5min |
| scripts/update_data.py | používá nový výchozí seznam |
| NOVÉ: src/update_service.py, scripts/run_updater.py | průběžná aktualizace setrná k limitu: nejvýš 1 volání API za 120 s (= 720 denně), vždy dotáhne všechny chybějící svíčky jednoho instrumentu, drží rezervu 100 kreditů na ruční spuštění, o víkendu nevolá |
| src/collector_service.py | varování odkazuje na nový nástroj |
| scripts/run_tests.py, test_b6, NOVÉ test_b7 | testy včetně simulace celého dne |

Starý `collector_service.py` (volá každých 30 s) zůstává, ale nepoužívejte ho na bezplatném plánu.

## Použití

    python scripts/update_data.py      # jednorázově: dotáhne vše chybějící (7 párů × 2 timeframe)
    python scripts/run_updater.py      # průběžně na pozadí, max. 1 volání / 120 s, Ctrl+C zastaví
    termux-wake-lock                   # (Android) před spuštěním, aby telefon Termux neuspal

Jiné páry nebo timeframe: `python scripts/update_data.py --symbols EUR/JPY,GBP/JPY --timeframes 1min`
nebo řádky `COLLECTOR_SYMBOLS=...` a `COLLECTOR_TIMEFRAMES=...` v souboru `.env`.

Vrácení zpět: `python …/apply_block_b2.py --rollback backup_block_b2_<časová_značka>`
