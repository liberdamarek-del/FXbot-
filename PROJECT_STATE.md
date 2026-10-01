# FXBOT PROJECT STATE

Replaces the old PROJECT_STATE.md and PROJECT_STATE.proposed.md (both
kept in git history). Status words: HOTOVO (verified) / ROZPRACOVANO /
BLOKOVANO / NEOVERENO.

## Project rules (unchanged)

- Broker/XTB order execution: OUT OF SCOPE (read-only broker adapters only)
- RAW DATA != VALIDATED DATA != TRADING SIGNAL
- No hindsight, no fabrication, no forced trade.
- Tests run ONLY against an isolated temporary database: `python fxbot.py test`
- Never modify the production database without a verified backup
  (`python scripts/backup_db.py`).
- A material model change goes through the change log + OOS gate
  (src/stats/registry.py); nothing is promoted automatically.

## Block E (2026-09-30 .. 10-01): V7.8.0 implementation

| Area | State | Where |
|---|---|---|
| Module manifest 0-145, Word verification (146 headings in order) | HOTOVO | src/v78/manifest.py |
| Run procedure module 145 (16 steps), run state machine, trace 0-145 | HOTOVO | src/v78/run.py, runstate.py |
| Staged commit + read-back, run package, certificates | HOTOVO | src/v78/persist.py, report.py |
| Quote contract, freshness 2.0, skew, conflict/outlier, closed mode | HOTOVO | src/v78/quotes.py |
| Market Path Archive: bid/ask 1min (days) + 1h (months), hashes | HOTOVO | src/path_archive.py, src/sources/dukascopy.py |
| Second 1-minute path source FXCM (outcome checks only, D-001) | HOTOVO | src/sources/fxcm.py |
| Out-of-sample research archive 2016-2023 (FXCM canonical) | HOTOVO | scripts/oos_fxcm.py |
| Forward-test review with paired anti-model control | HOTOVO | scripts/review.py, src/v78/audit.py |
| Parallel backtest (per pair, identical results, Termux fallback) | HOTOVO | src/engine/backtest.py |
| Coverage certificate, between-run delta | HOTOVO | src/v78/coverage.py |
| Fundamentals point-in-time: 8 keyless sources, revisions, calendar | HOTOVO | src/fundamental/ |
| Technical D1/H4/H1, level lifetime, setups | HOTOVO | src/engine/technical.py |
| Evidence clusters, hypotheses, gates, costs, Top-3, concentration | HOTOVO | src/engine/decision.py, portfolio.py |
| Thesis state machine, no-instant-flip, hysteresis | HOTOVO | src/engine/thesis.py |
| Side-correct resolver (bid/ask, 1min refinement, coverage) | HOTOVO | src/engine/resolution.py, src/v78/audit.py |
| Backtest replay + placebo, ablation, robustness, walk-forward | HOTOVO (code) | src/engine/backtest.py, src/stats/validation.py |
| Registry champion/challenger, change log, promotion gate | HOTOVO | src/stats/registry.py |
| Broker interface, paper account, OANDA quotes | HOTOVO / OANDA NEOVERENO | src/broker/ |
| One CLI | HOTOVO | fxbot.py |
| Tests E1-E8 incl. Word pre-change register T01-T14 | HOTOVO (49/49 PASS) | test_e*.py |

Manifest: 110 IMPLEMENTED, 27 PARTIAL, 7 NOT_AVAILABLE (26 options, 27 flows,
28 fiscal, 29 China, 32 geopolitics, 130 web tickers, 131 rendered widgets),
2 SUPERSEDED (83, 128).

## Verified facts (2026-09-30, from this project)

- Dukascopy datafeed: 1min BID/ASK day files, 1h month files, hour tick
  files; month index zero-based; files appear after the day/hour ends.
  Through the cloud proxy the server throttled heavily (~1-2 files/min);
  keep-alive connections are essential. Speed on the user's network: NEOVERENO.
- Dukascopy 1h candles == 1h aggregated from its 1min candles (checked on
  overlapping days).
- Fundamental sources RUNTIME-PASS: BIS, FRED, ECB, MoF, BoE, BoC, RBA, CFTC,
  ForexFactory weekly feed. RUNTIME-FAIL / not usable: SNB daily yields
  (cube stopped 2025-07), RBNZ (403), Yahoo (429), Stooq (blocked).
- Twelve Data /quote has last_quote_at (timestamped) but no bid/ask.
- 2026-10-01: Dukascopy answered HTTP 429 for > 6 h to the cloud runtime
  (no published limits). The downloader now doubles its pause up to 30 min.
- FXCM public candle files (candledata.fxcorporate.com, m1 and H1, 2012+):
  week numbering differs between years (file content decides), some weeks
  missing, ~1 week publication lag, momentary crossed quotes (> 1 pip in
  0.005 % of minutes). Agreement with Dukascopy: median mid difference
  0.05-0.20 pip; FXCM H1 = aggregated FXCM M1 in 99.6 % of hours.

## Results on real data (2026-10-01)

| Period | Predictions | E per trade | Paired direction edge vs random |
|---|---|---|---|
| 2023-11 .. 2026-09 (Dukascopy, in-sample) | 3 958 | -0.063 R | +0.022 R (95 % CI -0.006 .. +0.049), not significant |
| 2016-09 .. 2023-08 (FXCM, out-of-sample) | 10 640 | -0.076 R (CI -0.123 .. -0.029) | -0.005 R (CI -0.022 .. +0.012), none |

The implemented V7.8.0 model is NOT profitable and shows no direction edge
out of sample (docs/CHANGE_LOG.md R-001). The software (data, analysis,
locking, resolution, statistics) is complete; the trading hypothesis is not.

Profit search (R-008, docs/ZISK10_VYSLEDEK.md): 25-pair FXCM hourly universe 2012-2026
(scripts/fxcm_universe.py), 213 840 systems (scripts/profit_lab2.py), trade-by-trade check
(scripts/profit_deep.py). F1 = weekly RSI(2) dip + OECD rate divergence (lagged 2 months):
267 trades, 89 % winners, +10.9 % of the margin per trade at 1:30; test 2023-26 +10.3 %.
Pre-registered as CH-008 (forward test only; signal script not written yet).
Annual return (R-009, docs/ROCNI_VYNOS_VYSLEDEK.md): only the Friday decision works; tiered sizing
by rate divergence (8 / 3 / 2 % margin, scripts/portfolio_tiers.py): 2012-22 +23.5 % a year,
2023-26 +24.2 %, drawdown 16-19 %, 76 trades a year. Pre-registered as CH-009.

Never-seen markets (R-010, docs/UCENI.md): 16 HistData pairs (scripts/histdata_universe.py); CH-009
fails there (+0.2 % a year 2012-22, -3.1 % 2023-26). Self-learning loop scripts/self_learn.py
(walk-forward + cross-market gate): champion "max" +19.1 % a year in 2023-26 (dd 20 %), champion
"mesicne" +10.7 % (dd 21 %).

## Still open

| Sev | Item |
|---|---|
| HIGH | Live run with the user's Twelve Data key on the phone (NEOVERENO) |
| HIGH | Forward test 2-4 weeks: locked predictions resolved on future data |
| HIGH | New, pre-registered hypotheses (change log) tested OOS 2016-2023 before any forward use |
| HIGH | CH-008 weekly signals in the bot (25 pairs at the Friday close, OECD rates monthly) + ledger lock |
| MEDIUM | Broker bid/ask (OANDA practice or other API) - XTB has no public API |
| MEDIUM | broker_markup_pips 0.5 is an estimate of retail spread (compare with XTB) |
| LOW | holidays other than 25 Dec / 1 Jan not modelled |
| LOW | legacy modules (M3/M4 backtest/paper, TECH-0.1) kept; superseded by src/engine |

## Older blocks (A-D) - unchanged, still tested

A session/schema/migration, B data states/API budget/ledger, B2-B3.3 Twelve
Data updater/resample/off-session, C TECH-0.1 analysis, D resolver. All
their tests still pass. TECH-0.1 predictions in the ledger are audited by
the new resolver as well.
