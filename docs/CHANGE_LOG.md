# Change log (modules 80, 95, 126, 144)

Every material model change is recorded here BEFORE it can be adopted,
and in the database (`src/stats/registry.py`, table `change_log`) on the
machine where it is tested. Nothing is adopted without out-of-sample
evidence; a change that only looks better in one run is not adopted.

## CH-001 - trade geometry in H4 ATR units (instead of H1)

| Field | Value |
|---|---|
| Date | 2026-09-30 |
| Symptom | Real-data backtest 2026-06-10..09-29 (12 pairs, 345 predictions): SL hit after a median of 2 h; 47 % of stopped trades first moved >= 0.5 R in the right direction, 30 % >= 1 R; win rate 19 %, expectancy -0.20 R |
| Root cause (hypothesis) | Direction is decided on D1/H4, but entry offset, SL buffer and TP cap are measured in H1 ATR -> the stop sits inside H1 noise |
| Old rule | geometry in ATR(H1) (`atr_timeframe="1h"`) |
| Proposed rule | geometry in ATR(H4) (`atr_timeframe="4h"`) |
| Affected modules | 52, 53, 54, 55 |
| Expected benefit | fewer noise stop-outs |
| Failure modes | wider SL -> fewer trades pass R:R 1.5; entries further from the level |
| Tests | same-data comparison vs champion AND vs its own placebo; walk-forward OOS when >= 3 years of history are archived |
| Result (3.5 months, not OOS) | challenger 209 predictions, E -0.16 R, but its placebo E +0.00 R -> worse than random direction; champion E -0.20 R vs placebo -0.25 R |
| Proof class | C (expected predictive improvement, no OOS evidence) |
| Decision | HOLD - stays a CHALLENGER option, champion unchanged |
| Rollback target | default parameters (`atr_timeframe="1h"`) |

## Observations waiting for more data (not change candidates yet)

- 179 of 345 WAIT predictions reached TP1 without returning to the entry
  ("correct direction / entry too deep", module 69). Candidate parameter:
  `entry_offset_atr`. Tested only by walk-forward.
- Direction accuracy over 24 h: 58 % (model) vs 51 % (placebo) on 81
  independent situations - descriptive only (sample guard, module 70).

## CH-002 - swing horizon (H4 geometry + 72 h horizon)

| Field | Value |
|---|---|
| Date | 2026-09-30 |
| Root cause (hypothesis) | the fundamental clusters (20-day rate repricing, weekly positioning, carry) act over days to weeks, the trade horizon is 24 h |
| Proposed rule | `--set atr_timeframe=4h --set horizon_hours=72` |
| Result (4.5 months, not OOS) | paired edge vs random direction -0.030 R/decision (95 % CI -0.147..+0.087), not significant |
| Proof class / decision | C / HOLD |

## CH-003 - confirmed entry (module 52: ENTRY ZONE + TRIGGER + CONFIRMATION)

| Field | Value |
|---|---|
| Date | 2026-09-30 |
| Symptom | pullback limit entries were often run over: the level broke, SL hit, the move came later |
| Proposed rule | WAIT entry only after the zone was touched AND an H1 bar closed back beyond the entry level; the level failing first = no trade (`--set entry_mode=confirm`) |
| Result (4.5 months, not OOS) | win rate 26 % (champion 20 %), but E per decision -0.099 R vs random -0.067 R; paired edge -0.032 R (95 % CI -0.092..+0.028), not significant |
| Proof class / decision | C / HOLD |

## Method note: paired anti-model control (2026-09-30)

A single seeded random-direction placebo varied by about +-0.25 R between
seeds. Every backtest now also resolves the ANTI-MODEL (same decision and
geometry, opposite direction). A random direction is exactly the 50/50
mix of both, so the edge of the model's direction is tested PAIRED on the
same decisions: d = (R_model - R_anti) / 2. Proof class B (measurement).

## Method note: unknown sequence was a selection bias (2026-10-01)

With hourly bars only, 12 % of the model's trades ended SEQUENCE_UNKNOWN
(entry and SL/TP1, or SL and TP1, inside one hour) and were excluded from
the expectancy. Their possible effect was shown as bounds (-0.145 .. +0.694 R
per trade). After the FXCM 1-minute path (below) resolved half of them,
the 2.5-year expectancy moved from +0.116 R to -0.066 R per trade: the
excluded hours were mostly losers (a limit entry run over within the same
hour). The paired direction edge did not change (+0.022 -> +0.018 R per
decision, not significant). Lesson: an E that excludes unknowns is not
evidence; only the paired edge and the bounds are reported as results.

## D-001 - second 1-minute path source (data layer, not a model change)

| Field | Value |
|---|---|
| Date | 2026-10-01 |
| Symptom | Dukascopy free datafeed answered HTTP 429 for > 6 h to the cloud runtime; 1-minute days for ambiguous hours could not be fetched |
| Change | FXCM public week files (1-minute BID+ASK, `src/sources/fxcm.py`) as second path source |
| Guard | never used for the canonical bars or the live series (module 9); its minutes decide an ambiguous Dukascopy hour only when they show the same events (fill/SL/TP1) in that hour, otherwise SEQUENCE_UNKNOWN stays |
| Measured agreement | week 2026-09-21..25, 12 pairs: median mid difference 0.05-0.20 pip, hourly BID high/low within 0.5 pip in 59-97 % of hours (worst GBP/JPY) |
| Effect | model trades with unknown order 12 % -> 6 % |
| Predictions affected | none (only outcome resolution); proof class B (measurement) |

## Result R-001 - out-of-sample test of the champion (2026-10-01)

| Field | Value |
|---|---|
| Data | FXCM BID/ASK, 12 pairs, decisions 2016-09-26 .. 2023-08-11 (never used for any design or parameter choice), fundamentals point-in-time, event layer ablated; `python scripts/oos_fxcm.py evaluate --quick` -> docs/OOS_REPORT.md |
| Model | 10 640 predictions, E -0.076 R per trade (95 % CI -0.123 .. -0.029), unknown order 2 % (bounds -0.090 .. -0.034) |
| Paired direction edge vs random | -0.005 R per decision (95 % CI -0.022 .. +0.012): none |
| Direction only (mid move in model direction) | 24 h -0.08, 72 h -0.17, 120 h -0.22 ATR (overlapping, optimistic CI excludes 0) |
| In-sample 2023-11 .. 2026-09 (docs/BACKTEST_REPORT.md) | edge +0.022 R (-0.006 .. +0.049), E -0.063 R; walk-forward choice worse than default |
| Conclusion | the V7.8.0 rules as implemented have no demonstrable direction edge; after costs they lose. Proof class A (OOS measurement). Champion stays the reference for forward testing only - not for real trades |
| Next | new hypotheses only via this log, designed on 2023-2026 and tested on 2016-2023 (or the reverse), then forward |

## Result R-002 - signal research rounds 1-3 (2026-10-01)

Protocol and results: docs/VYZKUM_POSTUP.md (rules committed before each round).

| Round | Tested | Discovery | Confirmation |
|---|---|---|---|
| 1 | 23 standard technical/fundamental signals x 2 directions x 1/5/20 days, 12 pairs, 2016-09..2021-12 | 0 of 138 (best t 1.2) | - (control periods untouched) |
| 2 | 6 conditional literature effects | 0 of 36 (best t 1.6) | - (control periods untouched) |
| 3 | 7 currency factors, 13 currencies, FRED 1990-2012 | CARRY_MOM3 (+4.8 % p.a., t 2.93) | 2013-2026: -0.8 % p.a. gross, -3.1 % retail -> NOT confirmed |

No change of the model is proposed. Power: on 5.5 years t >= 3 needs an annual
Sharpe >= 1.28; documented FX effects have 0.3-0.7. Next candidates (to be
written into ROUNDS before testing): retail sentiment collected forward,
intraday seasonality, factor premia after the 2022 rate divergence.

## Result R-003 - trade geometry grid (2026-10-01)

`scripts/geometry_grid.py` -> docs/GEOMETRIE.md. The model's decisions (2016-2026)
re-played with 270 geometries (entry market / limit 0.25 / 0.5 ATR(H4), SL 0.5-3,
TP 0.5-4 ATR(H4), holding 24/72/120 h), chosen on 2016-2021, shown on 2022-2026.
No geometry is profitable in either period; win rate ranges 17-83 % with the
expectancy always negative; paired direction edge |t| <= 2 everywhere; the reversed
direction is not profitable either. Technical-only direction: same (edge +-0.01 R).
No change proposed. (A first version weighted weeks equally in the edge and showed
a spurious -0.05 R "edge"; fixed to a per-decision mean with week-clustered error.)

## Result R-004 - the user's method: classic pivots + SMA 50 (2026-10-01)

`scripts/pivot_lab.py` -> docs/PIVOTY.md: 216 variants (pivots of the previous day /
week / month; entries bounce at P, bounce at S1, break of R1, market; filters none /
SMA50 D1 / SMA50 W1 / both / pivot side, each also reversed as control; holding 1 or
5 days), ranked on 2016-09..2021-12, shown on 2014-2016 and 2022-2026. None positive
in all three periods; best ranked +0.041 R -> -0.019 / +0.015 R. SMA50 filters add
~0.004 R over their reversal; the pivot-side filter ~0.045 R, still negative overall.
New: `fxbot.py journal` records the user's own trades in the ledger (MANUAL), resolved
and reviewed (`review --manual`) with the paired control - to measure discretionary skill.

## Result R-005 - strategy mining (2026-10-01)

`scripts/strategy_mining.py` -> docs/STRATEGIE.md: 230 indicator settings (daily +
weekly chart) x 6 fundamental filters x both signs x holding 1/3/5 days = 7 846 rules,
ranked on 2016-09..2021-12. 0 of the best 30 passed both control periods (random
signals: 0 %). Best 30 on 2022-2026: mean +0.056 ATR/trade, 52.2 % winners (model
V7.8.0: -0.035..+0.008, 48-49 %) - not significant, not repeated on 2014-2016. Top-20
vote and walk-forward logistic regression: negative out of sample.

## CH-005 - CHALLENGER "FUND_DIP" (pre-registered 2026-10-01, forward test only)

| Field | Value |
|---|---|
| Source | the common pattern of the best mined rules (R-005) - selected after seeing 2016-2026, so ONLY a forward test can confirm it |
| Rule | direction = fundamentals (>= 1 cluster of carry / 20-day rates / VIX risk / policy trend for, none against); enter at the daily close when Williams %R(9) <= -90 for BUY (>= -10 for SELL) |
| Exit | after 5 trading days; protective SL 3 x ATR(D1), TP 3 x ATR(D1) (beyond the tested time-exit rule) |
| Tool | `python scripts/signals_today.py [--lock]` - today's state and the trigger price per pair; `--lock` records triggered signals in the ledger as CHALLENGER-FUND-DIP |
| Promotion | only if the forward paired edge vs random is significant after >= 100 trades (`review`) |
