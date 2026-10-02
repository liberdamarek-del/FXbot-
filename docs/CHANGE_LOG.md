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

## Result R-006 / CH-006 - adaptive rule selection (2026-10-01)

`scripts/adaptive_lab.py` -> docs/ADAPTIVNI.md: 8 280 rules, 64 meta-models (re-learn every
1/3/6/12 months on the trailing 6/12/24/36 months, trade the best 1/5/20/50 rules),
2017-01..2026-09, every decision from the past only. Persistence: the best decile of
the trailing year is the least bad next month (-0.017 vs -0.03..-0.04 ATR) - real but
smaller than costs. 21 of 64 meta-models positive on 2022-2026, 6 positive in both
halves (all: best single rule of the last 24-36 months), none with t >= 2. The meta-model
chosen on 2017-2021 (monthly, 36 months, best rule): 2022-2026 +0.0225 ATR/day (t 0.4)
vs V7.8.0 -0.04 (t -2.3). Deployed as CHALLENGER CH-006 (`fxbot.py adaptive --lock`,
daily in Termux); promotion only after a significant forward result.

## Result R-007 / CH-007 "75+" - high win-rate system (2026-10-01)

`scripts/winrate_lab.py` (97 200 systems) and `scripts/winrate_lab2.py` (16 848 systems; limit entries,
Connors exit, signal pairs, cost filter) on hourly BID/ASK 2014-2026 with costs. Round 1 (chosen on
2014-2019): RSI2<5/SMA200, 78.8 / 82.9 / 73.4 % winners. Round 2: 331 systems keep >= 75 % winners and
a profit in 2014-19, 2020-22 AND 2023-26. Deployed: LIMIT 0.5 ATR below the close, RSI(3) < 15, close
above SMA(200), ATR above its 30th percentile; TP 0.4 / SL 2.0 ATR, max 5 days (mirrored for SELL):
479 trades, 83.3 % winners, +0.045 R per trade, t +2.5, max drawdown -7.7 R. Chosen with knowledge of
all periods -> forward test (`fxbot.py signals75 --lock`, daily) is the independent proof. Note: the
win rate comes from the small TP / wide SL; the expectancy per trade is small.

## Result R-008 - profit per trade >= 10 % of the margin at 1:30 (2026-10-01)

Round 1 (`scripts/profit_lab.py`, 12 pairs, daily bars, 43 740 systems, docs/ZISK10.md): the >= 75 %
systems chosen on 2014-2022 failed on 2023-26. Round 2 (`scripts/profit_lab2.py`, 213 840 systems):
25 crosses of the 8 majors, FXCM hourly BID/ASK 2012-01..2026-09 from one source
(`scripts/fxcm_universe.py`, raw week files + sha256 manifest), the trade path resolved hourly,
carry / rate momentum from OECD 3m interbank rates known two months back. Selection on 2012-18 AND
2019-22, test 2023-26 (docs/ZISK10_K2.md). Trade-by-trade check with one position per pair
(`scripts/profit_deep.py`, docs/ZISK10_OVERENI.md). Finalist F1 (weekly RSI(2) dip + rate
divergence): 267 trades, 89 % winners, +10.9 % of the margin per trade (t 5.7, week-clustered);
2012-18 / 2019-22 / 2023-26 = +10.8 / +11.5 / +10.3 %. Controls: the dip alone +3.2 / +1.1 / +4.4 %,
the rate filter alone -2.6 / -2.3 / +0.1 %. Fails with current 2y yields instead of lagged realized
rates. Selection bias: systems with >= 10 % in both selection periods averaged +4..5 % in the test.
Summary for the user: docs/ZISK10_VYSLEDEK.md.

## CH-008 - CHALLENGER "SAZBY+PROPAD" (pre-registered 2026-10-01, forward test only)

Universe: the 25 pairs of `scripts/fxcm_universe.universe()`. Decision once a week at the Friday
New York close (or up to 1 h before it). Rate difference D(m) = OECD 3m interbank rate of the base
minus the quote currency (FRED IR3TIB01*M156N; JPY before 2002 INTDSRJPM193N), monthly, the value of
month m-2 for a decision in month m; momentum = D(m-2) - D(m-5).
* BUY when RSI(2) of the daily closes < 5 and momentum >= +0.25 pp; SELL when RSI(2) > 95 and
  momentum <= -0.25 pp.
* Market entry, TP = 0.75 x ATR(14) daily, SL = 3 x ATR(14), close after 20 trading days; only when
  TP >= 0.333 % of the price (10 % of the margin at 1:30); at most one position per pair.
* Variants evaluated alongside (chosen after seeing the test period, lower evidence): F5 = + carry
  D(m-2) in the trade direction; F7 = F5 with TP >= 0.5 % of the price.
* Success criterion of the forward test: after >= 50 trades the mean result >= +5 % of the margin with
  a week-clustered t >= 2 and winners >= 80 %; otherwise rejected. No promotion, no real money before.

## Result R-009 - annual account return instead of profit per trade (2026-10-01)

Questions of the user: why only Friday, 20 trades x 10 % or 40 trades x 7 %, the largest annual
return with >= 2-3 winning trades a month. Account simulation trade by trade with compounding, one
position per pair, margin cap 100 % (`scripts/portfolio_sim.py`). Weekday split of F1
(`scripts/weekday_tradeoff.py`, docs/DNY_A_POCET.md): only Friday works (+10.8 / +11.5 / +10.3 %
per trade; Monday-Thursday -11..+14 %, unstable). Trade-off (rate threshold 0.40 .. 0): at the same
margin more trades earn more (20/yr +11 %, 76/yr +21 % a year at 5 %), at the same drawdown (<= 20 %)
fewer, better trades win (+23 % vs +8 %). Rejected: 56 statistically selected rules combined
(2012-22 +25 %, 2023-26 +10 % a year, drawdown 27 %), fitted weights (overfit), per-tier exits
(2012-22 +37 %, 2023-26 +16 %), trend following (losses), other weekdays. Accepted: tiered sizing
(`scripts/portfolio_tiers.py`, docs/PORTFOLIO_STUPNE.md), sizes chosen on 2012-2022:
2012-22 +23.5 % a year, drawdown 19 %; 2023-26 +24.2 %, drawdown 16 %; 76 trades a year, 85 %
winners, 5.3 winning trades a month, 87 % of months with >= 2. Summary: docs/ROCNI_VYNOS_VYSLEDEK.md.

## CH-009 - CHALLENGER "SAZBY+PROPAD STUPNE" (pre-registered 2026-10-01, forward test only)

The CH-008 rule (Friday close, RSI(2) < 5 / > 95, TP 0.75 ATR, SL 3 ATR, 20 days, TP >= 0.333 % of the
price, one position per pair) for all trades whose 3-month rate-difference change (OECD 3m, lag 2
months) is in the trade direction, sized by its size: >= 0.25 pp -> margin 8 % of the equity;
>= 0.10 pp -> 3 %; >= 0 -> 2 %; total margin <= 100 % of the equity. Safety switch: a tier whose
closed trades of the last 24 months sum to a loss (>= 5 trades) is off until the sum is positive.
Success criterion of the forward test: after 12 months or >= 60 trades the account return >= +8 %
a year with a drawdown <= 25 %; otherwise rejected. No real money before.

## Result R-010 - test on never-seen markets and the self-learning loop (2026-10-01)

Data D-002: HistData.com 1-minute BID 2012-01..2026-09 for 16 pairs FXCM does not publish (USD/NOK,
EUR/NOK, USD/SEK, EUR/SEK, USD/MXN, USD/ZAR, ZAR/JPY, USD/PLN, EUR/PLN, USD/HUF, EUR/HUF, USD/CZK,
EUR/CZK, CHF/JPY, EUR/CAD, GBP/AUD) -> hourly arrays (`scripts/histdata_universe.py`; timestamps
are New York local time WITH daylight saving although the site says EST - measured against FXCM
EUR/USD 2018: median 0.1-0.2 pip). OECD 3m rates for PLN, HUF, CZK added (TRY has none after 2008).
Result: on the 16 new pairs F1 earns +8.3 / -0.8 / -2.4 % per trade (2012-18 / 2019-22 / 2023-26),
CH-009 +0.2 % a year 2012-22 (drawdown 56 %) and -3.1 % in 2023-26: the CH-008 / CH-009 results on
the 25 FXCM pairs were partly selection luck. Systems chosen on the FXCM pairs average ~0 % on the
new pairs (`scripts/cross_market.py`, docs/DVA_TRHY.md). Only the strongest tier (rates >= 0.25 pp
+ carry) stays positive on both groups.
Self-learning loop `scripts/self_learn.py` (docs/UCENI.md, docs/UCENI_LOG.md): champion +
experiments, tier margins re-fitted on selection years only, walk-forward 2012-18 -> 2019-22 and
2012-22 -> 2023-26, gate = higher annual return in both tests by >= 1 pp, drawdown within the 20 %
budget + 3 pp, positive trades in 2023-26 on both market groups. Profile "max": accepted "strongest
tier only" and "volatility sizing" -> tests +22.9 % (dd 22 %) and +19.1 % (dd 20 %) a year, 1.4-1.9
winners a month. Profile "mesicne" (>= 2 winners a month): CH-009 on 41 pairs stays champion ->
+17.8 % (dd 35 %) / +10.7 % (dd 21 %). Rejected 21 other experiments (daily limit tiers, VIX filter,
holding, targets, stops, currency limits, signals). Note: every experiment reuses the same test
years, so a part of every accepted gain is luck; the forward test decides.

## Result R-011 - self-learning on the 12 live pairs only (2026-10-01, user's decision)

`scripts/self_learn.py` now uses the 12 DEFAULT_ACTIVE pairs (FXCM hourly 2012-2026); group gate
inside them: 7 USD pairs vs 5 crosses. Accepted on top of CH-009: volatility sizing and the
RSI(3) < 15 signal in the strongest tier (profile max); stop 4 ATR + RSI(3) (profile mesicne).
Champion max (docs/SAMPION_12.md, `scripts/champion_report.py`), margins fitted on 2012-2022
(20 / 20 / 3 / 3 % of the equity): test 2019-22 +74.2 % a year (dd 25 %), test 2023-26 +28.6 %
(dd 20 %), 32-44 trades a year, 2.2-3.3 winners a month. Weak point: with CB policy rates instead of
OECD rates 2012-22 drawdown 53 %. Earlier evidence (R-010): rules of this family did not transfer
to other markets - the forward test decides.

## R-012 - learning round 3, live signals and the dashboard (2026-10-01)

Round 3 (12 pairs, both profiles): break-even stop (0.5 / 0.6 ATR), stall exit (5 / 10 days), second
rate measure confirmation (CB policy rates), COT crowding filter, SMA200 trend for weak tiers, more
signals for weak / second tier - none improved both walk-forward tests; champions unchanged.
Live: `scripts/signals_live.py` (Yahoo hourly, checked against FXCM: median 0.3-3 pips; FRED rates
with the backtest's 2-month lag) -> dashboard https://claude.ai/artifact/9Z9eEZr8Ni6uVBa4zrmwuU
(`web/prehled.html`, db: `stav/aktualni` written by Claude, `denik` = user's journal), model forward
test in `learning/forward_trades.json`. Learning state moved to `learning/` (tracked). Weekly
routines: Friday signals, Saturday learning (CLAUDE.md).

## R-013 - trade plan with three targets and probabilities on the dashboard (2026-10-01)

`scripts/pair_stats.py` now gives, per tier and pair (12 pairs, hourly path 2012-2026, SL 4 ATR,
20 days, only trades with TP1 >= 10 % of the margin): probability of reaching TP1 (0.75 ATR, the
model's target), TP2 (1.0 ATR) and TP3 (1.5 ATR) before the stop, from each trade's best move
(simulator records `mfe_atr`), and the average result of a position closed at each target; shrunk
toward the tier average (20 pseudo-trades). Strongest tier: 96 / 89 / 68 %, averages +17.1 / +21.5 /
+19.0 % of the margin. `signals_live.py` adds a plan (entry, TP1-TP3, SL, probabilities) to every
signal and a conditional plan (entry = trigger price) to every pair; the dashboard shows the
probability of success, the plan, a 3-part split and a section with plans for the pairs ready to
enter. Descriptive statistics only - the model's own rule still closes at TP1 (TP2/TP3 as single
targets were rejected by the walk-forward gate, "tp_1_atr").

## R-014 - the user's pivot method + SMA50, tested on every day (2026-10-01)

`scripts/pivot_lab2.py` (docs/PIVOTY2.md): 12 live pairs, FXCM hourly 2012-2026, retail costs and
swap; classic pivots of the previous day / week / month; fades at P, R1/S1, R2/S2 (the user's
entries of 2026-10-01 were at the daily P and R2), limit or confirmation entry, filters none /
SMA50 with / SMA50 against / weekly SMA50 / rate divergence, TP at the next level or 0.5 / 1.0 ATR,
SL at the next level or 1 ATR, time to the period end or 5 / 10 / 20 days: 1,080 variants (960 with
enough trades). Average result -0.8 % of the margin per trade in each of 2012-18, 2019-22, 2023-26;
9 variants positive in all three periods, none with t > 1.3; the best walk-forward choices
(monthly R1/S1, confirmation, SMA50 against) end at +1.4 % (t 0.4) and below in 2023-26, negative
on the crosses. SMA50 against the trade is the least bad filter (-0.1 / -0.4 / -0.4 %). Not added to
the model. Earlier: R-004 (216 variants) - same conclusion.

## R-015 - code audit, fixes and diagnostics (2026-10-02)

Full audit in docs/AUDIT_2026-10-02.md (Czech): done / in progress / dead code, findings by severity,
the fundamentals question, improvement plan. Fixed today (no change of the trading rule or sizes):
- C1 `signals_live.py`: a run on a Friday before the close took the unfinished daily bar as the
  Friday decision (2026-10-02 03:55 UTC produced 2 false signals, EUR/CHF and EUR/JPY, removed
  from the forward test, never published). New `decision_ready()`: signal only when the hourly data
  reach Friday 15:00 New York or later.
- H1 `profit_lab2.series`: the price cache was never rebuilt, the weekly learning would not have
  seen new data; now rebuilt when the hourly file is newer.
- H2 GBP OECD 3m rate stale since 2026-01 (change counted as 0, crash from 2027-03): warnings in
  stav.json (`varovani`, per pair, per currency `zastarale`) and on the dashboard; None-safe.
  Replacement source still to be tested through the gate.
- M1 `self_learn.py`: the champion is re-evaluated when the data reach a new day (`data_do`),
  so candidate and champion are compared on the same data; stale docstring / constant removed.
- New `scripts/diagnostika.py` (read-only health check) and `test_f1_live_model.py` (decision time,
  rates, cache, simulator, account); suite 50/50 PASS.
Open: H3 drawdown measured only at exits (mark-to-market 24-36 % vs 20-26 %), M2-M8 (see audit).

## R-016 - news, fresh rates, honest drawdown, hourly updates and learning 3x a day (2026-10-02)

User's requests: updates every 30 min and learning several times a day, all fundamentals, fresh rates.
- Rates: the OECD 3-month series that stop or lag are continued by the change of the OECD immediate rate
  (`profit_lab2.EXTEND_IDS`; GBP = SONIA monthly average, from 2026-02; JPY from 2026-08). GBP 2012-2026:
  3-month changes correlate 0.88 with the 3-month series, same sign in 90 % of moves >= 0.1. Backtest before
  the extension unchanged. Dashboard notes the substitute.
- Drawdown (audit H3): `portfolio_sim.mtm_drawdown` values open trades at every New York close (simulator
  records daily marks); fit and gate use it. Champions re-evaluated (EVAL_VERSION 2): monthly profile
  2019-22 +72.8 % / dd 27 %, 2023-26 +20.9 % / dd 19 %, tier margins 12/12/6/5 % (were 15/15/6/6).
- Gate: in addition at least as good as the champion in >= 3 of the 4 two-year blocks of the tests
  (many more experiments a week). Champion re-evaluated whenever prices, rate months or the evaluation change.
- News data: `scripts/fundamenty.py` - scheduled decisions Fed 2012-2027, ECB 2012-2028, BoJ 2012-2027,
  BoE 2012-2026 (8/2015-12/2016 missing), US NFP and CPI release dates (ALFRED) -> learning/udalosti_historie.json;
  OECD CPI / unemployment (incomplete, not used yet). docs/ZPRAVY.md: champion trades entered <= 7 days
  before a decision of either currency's central bank earned +6.5 / +2.2 / +4.1 % of the margin vs
  +10.0 / +16.0 / +7.2 % without (2012-18 / 2019-22 / 2023-26).
- Round 4 experiments (both profiles), all rejected: skip 5 / 7 / 10 days before a decision, weak tiers
  only, US NFP/CPI week, news shock > 0.75 ATR (fewer trades -> lower annual return; the monthly profile
  then misses 2 wins a month); half size before a decision (monthly profile: 2019-22 +73.0 % at dd 20 %
  vs +72.8 % at 27 %, 2023-26 +29.6 % vs +20.9 % - failed the >= 1 pp gain in 2019-22).
- Live: `scripts/aktualizace.py` (diagnostics, signals, ForexFactory week calendar, next central bank
  decisions, the user's journal from the dashboard - snapshot not in git); dashboard section "Zprávy a
  centrální banky", per-pair warnings (high-impact news in 24 h, central bank within 7 days), SL/TP alerts
  in the journal, phone layout fix. Friday decision only from 16:00 New York (hourly runs on Friday).
- Routines: hourly updates on weekdays (the platform's minimum interval is 1 hour - 30 min was refused),
  learning on weekdays 07:40 / 12:40 / 17:40 Prague + Saturday with data downloads, Friday signals 16:05 NY.

## R-017 - learning run 2026-10-02 morning (round 5, both profiles): nothing accepted

- `zpravy_po_rozhodnuti_vetsi` (1.5x size when a central bank of either currency decided in the entry week):
  monthly 2019-22 +64.5 % (champion +72.8 %), 2023-26 +26.2 % (+20.9 %); max 2019-22 dd 34 % - rejected.
- `slabe_stupne_s_carry` (weak tiers only with positive carry): too few trades (monthly profile no valid
  sizes; max 2019-22 +54.2 %) - rejected.
- `zpravy_pred_polovina_po_vetsi` (half size before a decision, 1.5x after): monthly 2019-22 +60.4 % at dd 17 %,
  2023-26 +27.4 %; max 2019-22 +74.3 % but dd 39 % - rejected.
New Rule field `cb_week_size` (profit_deep). Champions unchanged.

## R-018 - research: why the pairs move daily, short-window indicators per pair (2026-10-02)

User's request: why the markets move ~1 % a day (tens of % of the margin), which news, gold / oil /
institutions / politicians, per-pair and whole-sample tests, validity over 14 days / month / half year.
- `scripts/vyzkum_data.py` (Yahoo daily 2012-: gold, silver, WTI, Brent, copper, gas, S&P 500, Euro Stoxx,
  Nikkei, VIX, US 10y/5y/3m, dollar index; ALFRED release dates NFP, CPI, GDP, retail sales, PCE, PPI),
  `scripts/pohyby_lab.py` -> docs/PROC_SE_TRHY_HYBOU.md, `scripts/kratke_okno_lab.py` -> docs/KRATKE_OKNO.md,
  summary docs/VYZKUM_POHYBY_2026-10-02.md.
- Daily range 0.82 % (24 % of the margin), close-to-close 0.40 %; busiest hours 08-11 New York.
  Top-5 % days: central bank decision 2.0-2.9x, NFP 1.7x, CPI 1.6x, retail 1.5x more often than ordinary
  days, but 70 % of them without a scheduled event from the list. Same-day other markets explain 26 % of
  daily moves (AUD/JPY 43 %); next-day correlations ~0 (S&P -> USD pairs +-0.10 driven by 2020, negative
  after costs in 2012-18 and 2023-26).
- 3,024 pair x signal x holding combos: rank persistence (IC) ~0 for 14 days / month; best walk-forward
  choice (3 months -> 14 days) Sharpe +0.47 but +1.2 % of the price a year and negative 2013-18;
  34 combos stable in all periods ~ chance (mean reversion on EUR/GBP, EUR/USD, fading news moves).
- Gate (round 6): trade a pair only while the rule worked on it in the last 3 / 6 / 12 months - all rejected
  (2023-26 +15.6 / +12.2 / +4.7 % vs +19.8 %). New `recent` option in self_learn. Nothing enters the model.

## R-019 - learning run 2026-10-02 noon (round 7): exit before a central bank decision ACCEPTED in profile "max"

New simulator options: `exit_before_cb` ("zisk" / "vzdy": close at the New York close of the day before a
scheduled Fed/ECB/BoJ/BoE decision of either currency - only when in profit / always), `risk_contra`
(risk currencies only against the k-day S&P 500 move), tiers limited to some pairs (`pairs`).
- `zavrit_pred_cb_zisk`: profile max ACCEPTED - 2019-22 +81.0 % (champion +71.1 %), dd 26 % (26 %);
  2023-26 +26.0 % (+19.8 %), dd 28 % (27 %); better in all 4 two-year blocks. Profile mesicne (live signals)
  rejected only on the drawdown: 2019-22 +87.2 % (+72.8 %) dd 19 %, 2023-26 +39.5 % (+20.9 %) but dd 28 %
  > 23 % allowed (sizes fitted on 2012-22 are larger). Live signals (mesicne champion) unchanged.
- `zavrit_pred_cb_vzdy`: rejected (closing losing trades too costs). `riziko_proti_akciim_5d`: rejected
  (fewer trades; mesicne no valid sizes). `eurgbp_navrat_stupen`: rejected.

## R-020 - literature anomalies re-tested; learning rounds 8-9 (2026-10-02 afternoon)

User: keep testing, search the internet and GitHub for what others found. Sources (web search):
Mueller, Tahbaz-Salehi, Vedolin (2017, J. Finance) FOMC-day dollar weakness; Krohn, Mueller, Whelan
(2024, J. Finance) dollar demand at the fixes; Breedon, Ranaldo (2013) home-hours depreciation; Lustig,
Roussanov, Verdelhan (2014) dollar carry; Menkhoff et al. momentum / value; bank notes (BofA, UBS, BNY)
on month-end rebalancing; awesome-systematic-trading (GitHub): median replication Sharpe 0.37.
`scripts/anomalie_lab.py` -> docs/ANOMALIE.md (12 pairs 2012-2026, costs): FOMC day short USD +0.073 %
of the price per event, positive in all three periods but t 1.3; intraday fix / home-hours patterns real
before costs in 2012-22 (Tokyo post-fix t 3.9) but gone in 2023-26 and below the spread; month-end
rebalancing, dollar carry, momentum, value, their combination ~0.
Gate, both profiles (new: `fomc_addon` add-on list, `vix_size`, `exit_before_cb="fed_long_usd"`,
`max_share` cap): FOMC add-on, VIX-managed size, exit long-USD before FOMC, exit-in-profit for strong
tiers only, exit-in-profit with margin <= 15 % / 12 % - all rejected. Closest: monthly profile, exit in
profit before a decision + margin <= 15 %: 2019-22 +65.5 % at dd 17 % (champion +72.8 % at 27 %),
2023-26 +29.6 % at dd 22 % (+20.9 % at 19 %) - better return per drawdown in both tests but lower
return in 2019-22, so rejected by the gate; not adopted without the user's decision.

## R-021 - gate v3: return per risk (user's decision 2026-10-02 evening), trader-logic options

The user gave a free hand to change the rules. The gate now compares return per drawdown (CAGR / max dd,
mark-to-market) instead of raw return at a refitted size: in BOTH tests >= +10 % better, >= 85 % of the
champion's return, drawdown <= 30 %, the profile's wins a month, >= 3 of 4 two-year blocks at least as good
(per drawdown), positive average trade in both market groups 2023-26 (EVAL_VERSION 3; champions re-evaluated).
Simulator: `tp_parts` (position split into parts with own targets), `knife_days` (no buy at an N-day low).
Round 10 (in progress): `v3_zavrit_pred_cb_zisk` ACCEPTED in the monthly profile (live signals): 2019-22
+87.2 % / dd 19 % (champion +72.8 % / 27 %), 2023-26 +39.5 % / dd 28 % (+20.9 % / 19 %).
