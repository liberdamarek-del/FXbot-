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

## Block E (2026-09-30): V7.8.0 implementation

| Area | State | Where |
|---|---|---|
| Module manifest 0-145, Word verification (146 headings in order) | HOTOVO | src/v78/manifest.py |
| Run procedure module 145 (16 steps), run state machine, trace 0-145 | HOTOVO | src/v78/run.py, runstate.py |
| Staged commit + read-back, run package, certificates | HOTOVO | src/v78/persist.py, report.py |
| Quote contract, freshness 2.0, skew, conflict/outlier, closed mode | HOTOVO | src/v78/quotes.py |
| Market Path Archive: bid/ask 1min (days) + 1h (months), hashes | HOTOVO | src/path_archive.py, src/sources/dukascopy.py |
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
| Tests E1-E6 incl. Word pre-change register T01-T14 | HOTOVO (47/47 PASS) | test_e*.py |

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

## Still open

| Sev | Item |
|---|---|
| HIGH | Live run with the user's Twelve Data key on the phone (NEOVERENO) |
| HIGH | Forward test 2-4 weeks: locked predictions resolved on future data |
| MEDIUM | Statistical evidence: backtest on >= 3 years once the archive is filled |
| MEDIUM | Broker bid/ask (OANDA practice or other API) - XTB has no public API |
| MEDIUM | broker_markup_pips 0.5 is an estimate of retail spread (compare with XTB) |
| LOW | holidays other than 25 Dec / 1 Jan not modelled |
| LOW | legacy modules (M3/M4 backtest/paper, TECH-0.1) kept; superseded by src/engine |

## Older blocks (A-D) - unchanged, still tested

A session/schema/migration, B data states/API budget/ledger, B2-B3.3 Twelve
Data updater/resample/off-session, C TECH-0.1 analysis, D resolver. All
their tests still pass. TECH-0.1 predictions in the ledger are audited by
the new resolver as well.
