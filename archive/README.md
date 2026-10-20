# Archiv (R-048, architektura-v2, fáze 1)

Nic z toho se nemazalo: soubory se **přesunuly** (`git mv`, historie zůstala) a stav těsně před přesunem je označený
tagem `archiv-v7.8.0-pred-presunem`. Archivovaný kód se nespouští (jeho importy míří na staré cesty); slouží jako záznam.

## Proč

* **Kód V7.8.0** (původní analytický bot s databází, Twelve Data, sběrem dat, papírovým účtem a vlastním backtestem) živý
  systém od 1. 10. 2026 nepoužívá. Živé jádro (signály, simulátor, účet, diagnostika, heuristiky) na něm nezávisí:
  statická kontrola importů (`test_h1_core.py`) to hlídá.
* **Výzkumné laby, které nikdo nevolá**: skripty, které neimportuje ani nespouští žádná rutina ani živý nástroj. Jejich
  výsledky jsou popsané v `docs/` (např. `PIVOTY2.md`, `INTRADAY.md`, `HAZARD.md`, `ANOMALIE.md`, `OBCHODNIK.md`,
  `ZPRAVY.md`, `AUDIT_2026-10-02.md`); kód je tady, kdyby se rodina někdy znovu otevírala (CLAUDE.md: fronta nápadů říká,
  které se neopakují).
* **Zůstává na svém místě**: vše, co dosáhne živý systém nebo rutiny (`scripts/rutina.py` a nástroje, které volají),
  pět labů, na kterých stojí nástroje učení (`profit_lab`, `profit_lab2`, `winrate_lab`, `pivot_lab`, `strategy_mining`;
  živé jádro je ale už neimportuje), `src/broker/*` (potřebný pro fázi 4: demo účet) a testy živého systému.

## Jak obnovit

* Jeden soubor: `git mv archive/<cesta> <původní cesta>` (původní cesta je v tabulce níž).
* Celý původní strom: `git checkout archiv-v7.8.0-pred-presunem` (jen k prohlížení).
* `python fxbot.py <příkaz>` z V7.8.0: `python archive/v7.8.0/fxbot.py ...` nefunguje bez obnovení `src/` a `scripts/`.

## Co se přesunulo

### zdroj V7.8.0 (57)

| původní cesta | nová cesta |
|---|---|
| `src/backfill.py` | `archive/v7.8.0/src/backfill.py` |
| `src/backfill_missing_gaps.py` | `archive/v7.8.0/src/backfill_missing_gaps.py` |
| `src/backtest_engine.py` | `archive/v7.8.0/src/backtest_engine.py` |
| `src/backtest_execution.py` | `archive/v7.8.0/src/backtest_execution.py` |
| `src/backtest_fingerprint.py` | `archive/v7.8.0/src/backtest_fingerprint.py` |
| `src/backtest_persistence.py` | `archive/v7.8.0/src/backtest_persistence.py` |
| `src/backtest_pipeline.py` | `archive/v7.8.0/src/backtest_pipeline.py` |
| `src/backtest_report.py` | `archive/v7.8.0/src/backtest_report.py` |
| `src/backtest_results.py` | `archive/v7.8.0/src/backtest_results.py` |
| `src/backtest_runner.py` | `archive/v7.8.0/src/backtest_runner.py` |
| `src/backtest_schema.py` | `archive/v7.8.0/src/backtest_schema.py` |
| `src/bar_policy.py` | `archive/v7.8.0/src/bar_policy.py` |
| `src/collector.py` | `archive/v7.8.0/src/collector.py` |
| `src/collector_service.py` | `archive/v7.8.0/src/collector_service.py` |
| `src/collector_test_loop.py` | `archive/v7.8.0/src/collector_test_loop.py` |
| `src/data_feed_test.py` | `archive/v7.8.0/src/data_feed_test.py` |
| `src/data_feed_test_usdjpy.py` | `archive/v7.8.0/src/data_feed_test_usdjpy.py` |
| `src/data_state.py` | `archive/v7.8.0/src/data_state.py` |
| `src/data_update.py` | `archive/v7.8.0/src/data_update.py` |
| `src/engine/portfolio.py` | `archive/v7.8.0/src/engine/portfolio.py` |
| `src/freshness.py` | `archive/v7.8.0/src/freshness.py` |
| `src/fundamental/adapters.py` | `archive/v7.8.0/src/fundamental/adapters.py` |
| `src/fundamental_database.py` | `archive/v7.8.0/src/fundamental_database.py` |
| `src/fundamental_models.py` | `archive/v7.8.0/src/fundamental_models.py` |
| `src/gap_detector.py` | `archive/v7.8.0/src/gap_detector.py` |
| `src/historical_data.py` | `archive/v7.8.0/src/historical_data.py` |
| `src/history_audit.py` | `archive/v7.8.0/src/history_audit.py` |
| `src/history_manager.py` | `archive/v7.8.0/src/history_manager.py` |
| `src/history_service.py` | `archive/v7.8.0/src/history_service.py` |
| `src/intrabar_policy.py` | `archive/v7.8.0/src/intrabar_policy.py` |
| `src/logger.py` | `archive/v7.8.0/src/logger.py` |
| `src/models.py` | `archive/v7.8.0/src/models.py` |
| `src/paper_account.py` | `archive/v7.8.0/src/paper_account.py` |
| `src/paper_audit.py` | `archive/v7.8.0/src/paper_audit.py` |
| `src/paper_equity.py` | `archive/v7.8.0/src/paper_equity.py` |
| `src/paper_risk.py` | `archive/v7.8.0/src/paper_risk.py` |
| `src/paper_session.py` | `archive/v7.8.0/src/paper_session.py` |
| `src/paper_session_audit.py` | `archive/v7.8.0/src/paper_session_audit.py` |
| `src/paper_trading.py` | `archive/v7.8.0/src/paper_trading.py` |
| `src/position_simulator.py` | `archive/v7.8.0/src/position_simulator.py` |
| `src/rate_limiter.py` | `archive/v7.8.0/src/rate_limiter.py` |
| `src/resample.py` | `archive/v7.8.0/src/resample.py` |
| `src/resolver.py` | `archive/v7.8.0/src/resolver.py` |
| `src/storage.py` | `archive/v7.8.0/src/storage.py` |
| `src/tech_analysis.py` | `archive/v7.8.0/src/tech_analysis.py` |
| `src/trade_simulator.py` | `archive/v7.8.0/src/trade_simulator.py` |
| `src/twelve_data.py` | `archive/v7.8.0/src/twelve_data.py` |
| `src/update_service.py` | `archive/v7.8.0/src/update_service.py` |
| `src/v78/audit.py` | `archive/v7.8.0/src/v78/audit.py` |
| `src/v78/coverage.py` | `archive/v7.8.0/src/v78/coverage.py` |
| `src/v78/manifest.py` | `archive/v7.8.0/src/v78/manifest.py` |
| `src/v78/persist.py` | `archive/v7.8.0/src/v78/persist.py` |
| `src/v78/report.py` | `archive/v7.8.0/src/v78/report.py` |
| `src/v78/run.py` | `archive/v7.8.0/src/v78/run.py` |
| `src/v78/runstate.py` | `archive/v7.8.0/src/v78/runstate.py` |
| `src/v78/sources.py` | `archive/v7.8.0/src/v78/sources.py` |
| `src/validator.py` | `archive/v7.8.0/src/validator.py` |

### skript V7.8.0 (20)

| původní cesta | nová cesta |
|---|---|
| `scripts/analyze.py` | `archive/v7.8.0/scripts/analyze.py` |
| `scripts/backfill_all_gaps.py` | `archive/v7.8.0/scripts/backfill_all_gaps.py` |
| `scripts/backtest.py` | `archive/v7.8.0/scripts/backtest.py` |
| `scripts/backup_db.py` | `archive/v7.8.0/scripts/backup_db.py` |
| `scripts/collector_test_loop.py` | `archive/v7.8.0/scripts/collector_test_loop.py` |
| `scripts/download_history.py` | `archive/v7.8.0/scripts/download_history.py` |
| `scripts/export_package.py` | `archive/v7.8.0/scripts/export_package.py` |
| `scripts/freshness_check.py` | `archive/v7.8.0/scripts/freshness_check.py` |
| `scripts/health_check.py` | `archive/v7.8.0/scripts/health_check.py` |
| `scripts/quality_gate.py` | `archive/v7.8.0/scripts/quality_gate.py` |
| `scripts/quarantine_offsession.py` | `archive/v7.8.0/scripts/quarantine_offsession.py` |
| `scripts/resolve.py` | `archive/v7.8.0/scripts/resolve.py` |
| `scripts/review.py` | `archive/v7.8.0/scripts/review.py` |
| `scripts/run_updater.py` | `archive/v7.8.0/scripts/run_updater.py` |
| `scripts/set_api_key.py` | `archive/v7.8.0/scripts/set_api_key.py` |
| `scripts/signals_75.py` | `archive/v7.8.0/scripts/signals_75.py` |
| `scripts/signals_today.py` | `archive/v7.8.0/scripts/signals_today.py` |
| `scripts/update_data.py` | `archive/v7.8.0/scripts/update_data.py` |
| `scripts/update_fundamentals.py` | `archive/v7.8.0/scripts/update_fundamentals.py` |
| `scripts/verify_all.py` | `archive/v7.8.0/scripts/verify_all.py` |

### test V7.8.0 (43)

| původní cesta | nová cesta |
|---|---|
| `scripts/test_m415_real_data.py` | `archive/v7.8.0/scripts/test_m415_real_data.py` |
| `scripts/test_m51.py` | `archive/v7.8.0/scripts/test_m51.py` |
| `test_a1_market_session.py` | `archive/v7.8.0/tests_root/test_a1_market_session.py` |
| `test_a2_schema_migration.py` | `archive/v7.8.0/tests_root/test_a2_schema_migration.py` |
| `test_a3_paper_ambiguous.py` | `archive/v7.8.0/tests_root/test_a3_paper_ambiguous.py` |
| `test_b10_batch_storage.py` | `archive/v7.8.0/tests_root/test_b10_batch_storage.py` |
| `test_b11_offsession.py` | `archive/v7.8.0/tests_root/test_b11_offsession.py` |
| `test_b1_rate_limiter.py` | `archive/v7.8.0/tests_root/test_b1_rate_limiter.py` |
| `test_b2_twelve_client.py` | `archive/v7.8.0/tests_root/test_b2_twelve_client.py` |
| `test_b3_data_state.py` | `archive/v7.8.0/tests_root/test_b3_data_state.py` |
| `test_b4_data_update.py` | `archive/v7.8.0/tests_root/test_b4_data_update.py` |
| `test_b6_scripts.py` | `archive/v7.8.0/tests_root/test_b6_scripts.py` |
| `test_b7_update_service.py` | `archive/v7.8.0/tests_root/test_b7_update_service.py` |
| `test_b8_resample.py` | `archive/v7.8.0/tests_root/test_b8_resample.py` |
| `test_b9_history_settle.py` | `archive/v7.8.0/tests_root/test_b9_history_settle.py` |
| `test_c2_analysis.py` | `archive/v7.8.0/tests_root/test_c2_analysis.py` |
| `test_d1_resolver.py` | `archive/v7.8.0/tests_root/test_d1_resolver.py` |
| `test_e2_fundamentals.py` | `archive/v7.8.0/tests_root/test_e2_fundamentals.py` |
| `test_e3_engine.py` | `archive/v7.8.0/tests_root/test_e3_engine.py` |
| `test_e4_v78_pretests.py` | `archive/v7.8.0/tests_root/test_e4_v78_pretests.py` |
| `test_e5_run.py` | `archive/v7.8.0/tests_root/test_e5_run.py` |
| `test_e7_upgrade.py` | `archive/v7.8.0/tests_root/test_e7_upgrade.py` |
| `test_m310.py` | `archive/v7.8.0/tests_root/test_m310.py` |
| `test_m311.py` | `archive/v7.8.0/tests_root/test_m311.py` |
| `test_m312.py` | `archive/v7.8.0/tests_root/test_m312.py` |
| `test_m313.py` | `archive/v7.8.0/tests_root/test_m313.py` |
| `test_m314.py` | `archive/v7.8.0/tests_root/test_m314.py` |
| `test_m315.py` | `archive/v7.8.0/tests_root/test_m315.py` |
| `test_m39.py` | `archive/v7.8.0/tests_root/test_m39.py` |
| `test_m41.py` | `archive/v7.8.0/tests_root/test_m41.py` |
| `test_m410.py` | `archive/v7.8.0/tests_root/test_m410.py` |
| `test_m411.py` | `archive/v7.8.0/tests_root/test_m411.py` |
| `test_m412.py` | `archive/v7.8.0/tests_root/test_m412.py` |
| `test_m413.py` | `archive/v7.8.0/tests_root/test_m413.py` |
| `test_m414.py` | `archive/v7.8.0/tests_root/test_m414.py` |
| `test_m42.py` | `archive/v7.8.0/tests_root/test_m42.py` |
| `test_m43.py` | `archive/v7.8.0/tests_root/test_m43.py` |
| `test_m44.py` | `archive/v7.8.0/tests_root/test_m44.py` |
| `test_m45.py` | `archive/v7.8.0/tests_root/test_m45.py` |
| `test_m46.py` | `archive/v7.8.0/tests_root/test_m46.py` |
| `test_m47.py` | `archive/v7.8.0/tests_root/test_m47.py` |
| `test_m48.py` | `archive/v7.8.0/tests_root/test_m48.py` |
| `test_m49.py` | `archive/v7.8.0/tests_root/test_m49.py` |

### vyzkumny lab, nikdo ho nevola (15)

| původní cesta | nová cesta |
|---|---|
| `scripts/adaptive_lab.py` | `archive/vyzkum_laby/adaptive_lab.py` |
| `scripts/adaptive_today.py` | `archive/vyzkum_laby/adaptive_today.py` |
| `scripts/anomalie_lab.py` | `archive/vyzkum_laby/anomalie_lab.py` |
| `scripts/cross_market.py` | `archive/vyzkum_laby/cross_market.py` |
| `scripts/fxcm_m1.py` | `archive/vyzkum_laby/fxcm_m1.py` |
| `scripts/geometry_grid.py` | `archive/vyzkum_laby/geometry_grid.py` |
| `scripts/hazard_lab.py` | `archive/vyzkum_laby/hazard_lab.py` |
| `scripts/intraday_lab.py` | `archive/vyzkum_laby/intraday_lab.py` |
| `scripts/intraday_ml.py` | `archive/vyzkum_laby/intraday_ml.py` |
| `scripts/minute_lab.py` | `archive/vyzkum_laby/minute_lab.py` |
| `scripts/obchodnik_lab.py` | `archive/vyzkum_laby/obchodnik_lab.py` |
| `scripts/pivot_lab2.py` | `archive/vyzkum_laby/pivot_lab2.py` |
| `scripts/weekday_tradeoff.py` | `archive/vyzkum_laby/weekday_tradeoff.py` |
| `scripts/winrate_lab2.py` | `archive/vyzkum_laby/winrate_lab2.py` |
| `scripts/zpravy_lab.py` | `archive/vyzkum_laby/zpravy_lab.py` |

### cron telefonu pro V7.8.0 (1)

| původní cesta | nová cesta |
|---|---|
| `scripts/termux_schedule.sh` | `archive/v7.8.0/scripts/termux_schedule.sh` |

### seed testovaci DB V7.8.0 (1)

| původní cesta | nová cesta |
|---|---|
| `tests/seed.py` | `archive/v7.8.0/tests/seed.py` |

### fixture testu V7.8.0 (2)

| původní cesta | nová cesta |
|---|---|
| `tests/fixtures/usdjpy_1min_20260928T1832_20260929T0856.csv` | `archive/v7.8.0/tests/fixtures/usdjpy_1min_20260928T1832_20260929T0856.csv` |
| `tests/fixtures/usdjpy_5min_provider_20260929T0835_0850.csv` | `archive/v7.8.0/tests/fixtures/usdjpy_5min_provider_20260929T0835_0850.csv` |

### vstupni bod V7.8.0 (nahrazen novym fxbot.py jen s prikazem test) (1)

| původní cesta | nová cesta |
|---|---|
| `fxbot.py` | `archive/v7.8.0/fxbot.py` |

