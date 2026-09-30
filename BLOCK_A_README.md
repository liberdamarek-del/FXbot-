# FXBOT Blok A – stabilizace základu

Co se mění (jen tyto soubory, nic dalšího):

| Soubor | Změna |
|---|---|
| src/market_session.py | otevření/zavření trhu podle 17:00 New York (letní čas) |
| src/database.py | úplné schéma pro nové DB, záloha (`backup_database`), aditivní migrace |
| src/collector_service.py, history_service.py, history_manager.py | při startu se vytvoří/upgraduje schéma |
| src/paper_session.py | volitelná politika `ambiguous_policy` + audit události AMBIGUOUS (výchozí chování beze změny) |
| scripts/verify_all.py | kontrolní časy trhu opraveny na letní/zimní čas |
| NOVÉ: scripts/run_tests.py, tests/, test_a1..a3 | izolované testy na dočasné databázi |
| NOVÉ: scripts/backup_db.py, scripts/check_weekend_boundary.py, requirements.txt | zálohování, kontrola víkendové hranice, závislosti |
| NOVÉ: PROJECT_STATE.proposed.md | návrh nového stavu projektu (původní PROJECT_STATE.md se nepřepisuje) |

Instalace v Termuxu (ze složky projektu, kde je `src/`):

    python /cesta/FXBOT_BLOCK_A/apply_block_a.py --check   # zkouška, nic nemění
    python /cesta/FXBOT_BLOCK_A/apply_block_a.py           # instalace
    python scripts/run_tests.py                            # ověření

Vrácení zpět: `python /cesta/FXBOT_BLOCK_A/apply_block_a.py --rollback backup_block_a_<časová_značka>`

Instalace před změnou ověří, že se soubory shodují s exportem z 29. 9., zálohuje databázi
a původní soubory. Když se cokoli liší, nic nezmění.
