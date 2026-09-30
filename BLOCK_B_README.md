# FXBOT Blok B – stavy dat, omezovač API, evidence predikcí

Vyžaduje nainstalovaný Blok A.

## Co je nové

| Soubor | Účel |
|---|---|
| src/rate_limiter.py | rozpočet API kreditů (za minutu / za den), sdílený mezi programy, přežije restart |
| src/twelve_data.py | (nahrazen) každé volání jde přes rozpočet; klíč se nikdy nedostane do chyb ani logů |
| src/data_state.py | stavy dat CURRENT / CLOSED / STALE / MISSING / UNVERIFIED (CONFLICT rezervován) |
| src/data_update.py | „dotažení“ dat: stáhne jen chybějící svíčky; kompletní data = 0 volání API |
| src/prediction_ledger.py | základ evidence predikcí: zapsaná predikce se nedá změnit ani smazat (hlídá to databáze) |
| scripts/update_data.py | příkaz pro uživatele: aktualizace + přehled stavu |
| scripts/set_api_key.py | bezpečné uložení vlastního klíče Twelve Data a jeho test |
| src/collector_service.py | (upraven) varování, když nastavený interval nevejde do denního rozpočtu |
| scripts/run_tests.py, test_b1 … test_b6 | rozšířené izolované testy |

## Použití

    python scripts/set_api_key.py        # jednou: uloží a otestuje vlastní klíč
    python scripts/update_data.py        # dotáhne chybějící data a ukáže stav
    python scripts/update_data.py --status   # jen stav, bez volání API

Vrácení zpět: `python …/apply_block_b.py --rollback backup_block_b_<časová_značka>`
