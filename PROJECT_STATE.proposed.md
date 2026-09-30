# FXBOT PROJECT STATE  (PROPOSED - review before replacing PROJECT_STATE.md)

Basis: audit of FXBOT_FULL_EXPORT (files up to 2026-09-29 16:56 UTC),
Block A stabilization (installed and verified on the device, 27/27 tests)
and Block B (data states, API budget, ledger foundation), verified in an
isolated test run 2026-09-30.
Status words: HOTOVO (verified) / ROZPRACOVÁNO / BLOKOVÁNO / NEOVĚŘENO.

## Project rules (unchanged)

- Broker/XTB integration: OUT OF SCOPE in the current phase
- Live order execution: OUT OF SCOPE in the current phase
- RAW DATA != VALIDATED DATA != TRADING SIGNAL
- Do not reopen completed modules without a concrete reason.
- QUICK CHECK after normal changes; FULL QUALITY GATE only at milestones.
- Preserve backups before structural changes. Never modify the production
  database without a verified backup (`python scripts/backup_db.py`).
- Tests run ONLY against an isolated temporary database:
  `python scripts/run_tests.py`

## Documented state vs actual code (diff found by the audit)

| Item | Old PROJECT_STATE | Actual |
|---|---|---|
| M2 next action "Implement History Manager" | open | history_manager, history_service, history_audit exist and ran (8 PASS runs) |
| M3 Backtest | NOT STARTED | 9 modules + tests m39-m315 exist |
| M4 Paper trading | NOT STARTED | 7 modules + tests m41-m414 exist |
| M5 | V7.x ADAPTER | code labels fundamental models/database as "M5.1" -> naming conflict, DECISION NEEDED |

## Modules

### M1 Data engine - ROZPRACOVÁNO
- HOTOVO: Twelve Data bar feed, RawBar model, validation, SQLite storage,
  deduplication, collector audit, scheduler with retry.
  Evidence: 121 collector runs, 0 failures; 884 stored bars, 0 gaps,
  0 duplicates, 0 invalid OHLC, integrity_check ok.
- HOTOVO (Block A): schema complete for new databases; additive migration
  with verified backup; services initialize the schema at start.
- HOTOVO (Block B): data states CURRENT / CLOSED / STALE / MISSING /
  UNVERIFIED computed from the expected last closed bar and the market
  session (weekend = CLOSED, never CURRENT); on-demand catch-up that spends
  no API credit when data is complete; API credit budget (per minute / per
  day, persistent, shared between processes); API key never written to
  errors, logs or the database.
- HOTOVO (Block B2/B3): default instruments = 12 pairs (7 majors + EUR/JPY,
  GBP/JPY, EUR/GBP, EUR/CHF, AUD/JPY), only 1min is downloaded. 5min / 15min /
  1h are derived locally from stored 1min bars (`src/resample.py`, source tag
  `Derived1min`, complete windows only, no API credit).
  Verified against real data: 3 of 4 provider 5min bars are identical to the
  derived ones; the 4th (fetched 12 s after its close) lacked its last minute
  -> bars are now stored only after a settle delay (`BAR_SETTLE_SECONDS`,
  default 120 s, provisional).
- HOTOVO (Block B2/B3): budget-paced continuous updater
  (`scripts/run_updater.py`): at most one API call per 120 s (720/day on the
  free plan), most overdue instrument first, 100-credit reserve for manual
  runs, no calls while the market is closed. With 12 instruments each one is
  refreshed about every 24 minutes; `scripts/update_data.py` makes all of them
  current in one run.
- HOTOVO (Block B3): one request returns up to 4500 bars (provider maximum
  5000); deep history via `update_data.py --days N` (nearest chunks first,
  weekends skipped, stops when the provider has nothing older).
- HOTOVO (Block B3.2): bars are stored in one transaction per batch
  (`save_raw_bars`); found on the real device (Termux) where a test that
  wrote ~58 000 single rows exceeded 300 s; now ~470 commits. The test runner
  reports the time of every test.
- HOTOVO (Block B3.3): the provider also delivers off-hours quotes (found on
  the real device: 1 406 one-minute bars Sat 21:34 - Sun 20:59 UTC in 10 pairs,
  real price movement, thin market). They are no longer stored; existing ones
  are moved (not deleted) to `raw_bars_offsession` by
  `scripts/quarantine_offsession.py`. Weekend boundary otherwise CONFIRMED on
  real data: last Friday bar 20:59 UTC, first Sunday bar 21:00 UTC (USD/JPY,
  4 weekends, exact to the minute).
- Provider facts (from its documentation, 2026-09-30): 1 credit per symbol
  per request; the batch endpoint bundles requests but charges the sum of
  their credits (no saving); on the free plan 8 credits/min and 800/day.
- ROZPRACOVÁNO / missing: bid/ask, fallback source (CONFLICT state exists
  but nothing produces it - only one source), holidays in the session rule.
- NEOVĚŘENO: live behaviour of the new client against the real API; how far
  back 1min history reaches on the free plan; the
  provider's exact day boundary for credits (UTC assumed, 90 % safety margin);
  provider publication lag (tolerance 120 s is provisional).
- NEOVĚŘENO: live download (not testable in the audit environment).

### M2 History - ROZPRACOVÁNO
- HOTOVO: history manager/service/audit, gap detection, safety limits.
- HOTOVO (Block A): market session follows New York 17:00 (DST aware);
  weekend gap is MARKET_CLOSED in summer and winter.
- NEOVĚŘENO: provider bar times around the real weekend boundary
  -> run `python scripts/check_weekend_boundary.py` after the first weekend.
- Known limitation: holidays (Christmas, New Year) are not modelled.
- Dead-code candidates (not imported by anything): backfill.py,
  backfill_missing_gaps.py (fails on a single missing bar), backtest_runner.py,
  data_feed_test*.py. Decision pending; nothing removed.

### M3 Backtest - ROZPRACOVÁNO
- HOTOVO: chronological engine without look-ahead (signal on bar N is
  executed at the open of bar N+1), pipeline, fingerprint, persistence, report.
- Missing: bid/ask and spread-based costs (costs are a flat number per trade),
  history is copied per bar (quadratic time), sample is only 14.4 hours.
- BLOKOVÁNO: any statistical conclusion (insufficient history).

### M4 Paper trading - ROZPRACOVÁNO
- HOTOVO: account, equity, SL/TP, audit, session, persistence
  (tests m41-m414 PASS on a clean database).
- HOTOVO (Block A): explicit `ambiguous_policy` for bars where SL and TP are
  both reachable; AMBIGUOUS events are always audited.
  Default is still the legacy behaviour `CONTINUE` -> DECISION NEEDED whether
  to switch the default to `CLOSE_UNRESOLVED`.
- Open: gap through stop is filled at the stop price (optimistic);
  `PaperAccount.apply_realized_pnl` changes state before validation;
  cash-style position model (no margin/leverage/spread).

### M5.1 Fundamental data (schemas only) - ROZPRACOVÁNO
- HOTOVO: models and SQLite tables (test m51 PASS).
- Missing: any collector; all six tables have 0 rows.

### Technical analysis v1 (TECH-0.1) - ROZPRACOVÁNO
- HOTOVO (Block C): indicators (EMA, ATR, RSI, swing points, level clusters),
  trend / volatility / support-resistance on 4h, 1h and 15min derived bars,
  one explainable setup per pair, Czech report (`scripts/analyze.py`), optional
  locking of actionable setups into the ledger (`--lock`, duplicates within 4 h
  skipped). Gates from the specification: data CURRENT only, R:R >= 1:1.5,
  SL from structure + ATR, TP1 from structure or ATR, no-chase at ~1 ATR.
- Verified on synthetic markets and 8 random markets; the ledger acts as oracle
  for every produced setup. NEOVĚŘENO: behaviour on the real data (first run on
  the device) and any statistical value; ALL thresholds are provisional.
- Missing: macro / fundamental layer, regime and causality, event risk,
  multi-setup ranking beyond R:R, bid/ask, Top-3 continuity, outcome resolver.

### Prediction resolver (Block D) - ROZPRACOVÁNO
- HOTOVO: `src/resolver.py`, `scripts/resolve.py`. Replays stored 1-minute bars
  after T0 (no hindsight); WAIT: entry touched / NOT_ACTIVATED; NOW: entry at
  the reference price; SL vs TP1 first; SL and TP1 in the same minute =
  SEQUENCE_UNKNOWN (never guessed); horizon end = EXPIRED / NOT_ACTIVATED;
  holes in the path = UNRESOLVED until repaired; data not up to the horizon =
  stays open. States and outcomes are appended once (idempotent).
- Real ledger on the device: 4 predictions locked 2026-09-30 11:06 UTC
  (USD/CHF, USD/CAD, EUR/GBP, AUD/JPY); first outcomes expected within hours.
- NEOVĚŘENO: results on real data; costs (mid prices, no spread/slippage);
  entry lag of 2-3 minutes; n < 20 closed predictions = descriptive only.
- Missing: performance statistics by dimension (modules 66-70), error
  taxonomy (69), confidence calibration (72), Top-3 continuity.

### Prediction ledger (foundation) - ROZPRACOVÁNO
- HOTOVO (Block B): locked predictions, immutability enforced by database
  triggers, append-only state history and outcomes, only CURRENT input data
  accepted, no post-T0 price, SL/TP side consistency, reproducible digest.
- Missing: no-instant-flip gate (module 139), Top-3 continuity (141),
  automatic path resolver (61/90), performance statistics (66-70).

### V7.x model / V7.8 adapter - BLOKOVÁNO
- V7.x exists only as the Word specification (modules 0-145), not as code.
- Prediction ledger (9 predictions), run state and market path archive
  mentioned in the Word are NOT part of the export.
- No adapter exists (DELEGATION_REQUIRED still applies).

## Open issues (from the audit, not yet fixed)

| Sev | Where | Issue |
|---|---|---|
| LOW | freshness.py | legacy module, superseded by data_state.py (kept, not removed) |
| INFO | collector_service.py | legacy 30 s polling kept but superseded by scripts/run_updater.py; warns when the plan cannot support it |
| MEDIUM | paper trading | see M4 open items |
| LOW | project | 19 backup files in src/scripts, empty file `=`, venv in export |

## Verification log

- 2026-09-30 Block A: installed on the device (Termux); `python scripts/run_tests.py`
  -> 27 checks, 0 failures (reported by the user).
- 2026-09-30 Block B..B3.3, C and D: 41 checks, 0 failures in isolated runs on the working
  tree and on a copy of the post-Block-A project; install, repeat-install,
  version-mismatch guard and rollback verified on that copy.
- NEOVĚŘENO: Block B on the real device; live download; personal API key.

## Next step

1. Register a personal Twelve Data key and run `python scripts/set_api_key.py`.
2. After the first full weekend of collected data:
   `python scripts/check_weekend_boundary.py`.
3. Block C: technical analysis features (ATR, trend, levels) on stored bars,
   then the first analytic engine behind an explicit adapter that writes to
   the ledger. Decisions still open: default `ambiguous_policy`, meaning of "M5".
