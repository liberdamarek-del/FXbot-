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
Round 10: `v3_zavrit_pred_cb_zisk` ACCEPTED in the monthly profile (live signals): 2019-22 +87.2 % / dd 19 %
(champion +72.8 % / 27 %), 2023-26 +39.5 % / dd 28 % (+20.9 % / 19 %); tier margins 20/20/6/5 %. Rejected:
margin cap 15 %, half size before a decision, 3 targets (0.75/1.0/1.5 and 0.75/1.5/3.0 ATR), no buying at a
20-day low, strong tier(s) evaluated every day (4+ wins a month but lower return per drawdown).
Live: signals_live adds to every plan the rule and the decisions of the pair's central banks in the next 4 weeks
(`plan.pred_rozhodnutim`); the forward test closes in profit at the NY close before a decision; the hourly update
warns about journal trades in profit before tomorrow's decision; dashboard shows both; pair_stats and
docs/SAMPION_12.md regenerated (strongest tier 97 % wins, +18.5 % of the margin at TP1).

## R-022 - round 11 (2026-10-02 evening): other profit-taking exits rejected

New simulator options `exit_before_us` (USD pairs: in profit at the NY close before NFP / CPI) and
`exit_friday_profit` (in profit at a Friday close). Both rejected in both profiles on top of the new
champions (monthly: 2019-22 +88.3 % / +79.2 % vs +87.2 %, 2023-26 +37.1 % / +36.6 % vs +39.5 %; return
per drawdown not better). The exit before central bank decisions stays the only accepted exit rule.

## R-023 - learning run 2026-10-02 17:40: exit also before SNB / RBA decisions - rejected

`scripts/fundamenty.py` now also downloads SNB (scheduled quarterly assessments 2012-2026, 59) and RBA
(monetary policy decisions 2012-2026, 153) dates; BoC history is not available from the site (only the
last ~4 years), RBNZ refuses (403). New option `cb_all` (exit before decisions of the 6 banks). Monthly
profile: 2019-22 +84.5 % (champion +87.2 %), 2023-26 +38.5 % (+39.5 %), same drawdowns - no gain; max
profile also lower. The exit before decisions stays limited to Fed, ECB, BoJ and BoE.

## R-024 - 2026-10-02 night: trader's review of the losers, rounds 13-17 (all rejected)

`scripts/obchodnik_lab.py` -> docs/OBCHODNIK.md: 17 features of the monthly champion's trades at the entry
(dip depth, trend, volatility, 2y yield moves, distance to decisions, VIX, close in the day's range, month...),
terciles per period. Only the rate change is consistently decisive (> 0.35 p.b.: 97-99 % wins, +0.14..+0.17 R in
all three periods) - already the model's tier filter. Scratch analyses: RSI(2) 5-10 already loses the edge even
with strong rates; Friday entries are the best weekday (Thursday second, Monday-Wednesday weak); the losers are
mostly same-currency clusters of one Friday (e.g. 2024-10-04 short USD after the NFP surprise).
New simulator options: `scale_addon` / cfg `scale_in` (scale-in order k ATR beyond the entry, stacked on the
base trade in portfolio_sim), `confirm_up` (enter at the first close in the trade direction), cfg `cluster`
(size / sqrt(same-currency signals of the day)), `tp_retrace` (target = share of the 5-day fall), `weekdays`,
`decay_days` / `decay_tp` (smaller target after N days); holding beyond 20 days.
Rejected in both profiles (gate v3): scale-in 1.5 / 2 ATR, confirmation entry, one bet per currency (monthly
2023-26 return/dd 1.55 vs 1.43 but 2019-22 3.94 vs 4.49), strongest tier rates >= 0.40, target 0.6 / 0.5 ATR,
stop 5 ATR (max profile 2023-26 2.09 vs 0.94 but 2019-22 2.72 vs 3.11), 30 days, retracement target,
Thursday + Friday, late smaller target (5/7/10 days), strongest tier: target 1.0 ATR, half at 1.5 ATR (monthly
2019-22 6.26 vs 4.49 but 2023-26 1.09 vs 1.43), + Donchian breakout (monthly 2023-26 1.71 vs 1.43 but 2019-22
4.28 vs 4.49), + 3 down days. No change to the live model.

## R-025 - 2026-10-02 late evening: rounds 18-21 and two studies (all rejected)

Options: confirm_src "oecd<N>" (rate change over another window), run_portfolio `brake` (smaller trades in an
account drawdown), Rule `close_stop` (stop only at NY closes + disaster stop). Rejected: strongest tier as a
trend trader (dips + breakouts, half to 1.5 ATR), 6 / 12-month rate confirmation, 6-month window, drawdown brake
5 / 10 / 15 %, stop on the daily close (1.25 / 1.5 / 2.0 x). Studies (docs/OBCHODNIK.md): BIS CPI inflation of the
8 currencies (`fundamenty.bis_cpi`, macro.json "cpi_bis") adds nothing to the rate filter; the weekend-gap fade
works only at the first Sunday quote (after 1 hour it loses) - not tradable; the move after central bank decisions
continued in 2012-18 and reversed in 2019-26 - unstable. No change to the live model.

## R-026 - Saturday learning 2026-10-03 (run 2026-10-04 03:30 UTC): round 23, unemployment data (all rejected)

Data: FXCM build (still ends 2026-09-25, the week files lag), fundamentals, FRED rates. New
`fundamenty.unemployment_extra()` fills the unemployment gaps (EUR = EU27 monthly from Eurostat, the euro area code
returns nothing; CHF and NZD quarterly from FRED) -> all 8 currencies. Options: confirm "acc" (the rate divergence
still widens), confirm "une" (6-month unemployment change in favour of the bought currency, no data = pass),
cfg `rates_size` (size by the rate change), trades carry "rm". Rejected: vol sizing in the monthly profile under
gate v3 (2023-26 return/dd 2.21 vs 1.43, but 2019-22 3.33 vs 4.49 and only 70 % of the return), size by the rate
change, accelerating divergence and the labour market for the weak tiers (too few wins a month in the monthly
profile, lower in max). No change to the live model.

## R-027 - 2026-10-04: weekly FX research module (user's specification)

New `scripts/indikatory.py` (causal indicators and an 804-setting condition grid: RSI 5-28 x 20/80..40/60, SMA/EMA
5-200, EMA crosses, MACD 5/8/12 x 17/21/26/34 x 5/9/12, Bollinger 10-50 x 1.5-3.0, Stochastic 5-21 x 3/5, ATR 5-28,
ADX 7-28 x 20-35; neighbouring settings for robustness; resampling and higher-timeframe alignment) and
`scripts/tydenni_analyza.py` (every Saturday, the last completed FX week): data quality first (missing bars,
duplicates, timestamps, OHLC, gaps, weekend / after-close bars, outliers, source sync Yahoo 15m vs 1h and Yahoo vs
FXCM); A) descriptive per pair (week OHLC, changes, max rise / fall from the open, drawdown / recovery, range,
volatility, ATR, up/down/sideways hours under 0.05/0.10/0.20/0.30 %, strongest / weakest day, largest 15m/30m/1h
move) and per day and UTC session (00-06 ... 22-24); events of the week (ForexFactory archive) with type, time
flags, US actual values from ALFRED (release-day vintage, verified against the previous first release), surprise
(actual - forecast, relative, sign by convention) and pair reactions before / +15m ... +24h; big hourly moves with
the events and cross-asset moves of the same hour; currency factor model (common vs individual move), correlations
and pairwise lead / lag on 15-minute bars with a timestamp-offset flag; B) attribution inside the week; C) predictive:
non-overlapping forward returns per timeframe (15M 1h, 30M 2h, 1H 4h, 4H 24h, 1D 5 days), in-sample 2012-2019 /
out-of-sample 2020 -> (15M/30M: 75/25 % of 60 days), staged combinations (one indicator family per component,
overlap filter), walk-forward (years / weeks), robustness (ROBUST / POSSIBLE OVERFIT), regimes (volatility, ADX,
VIX risk, dollar, US 2y), the week as a new test of conditions locked before it, the user's pre-registered
combinations, event days (Fed/ECB/BoJ/BoE, NFP, CPI 2012 ->) x technical state, surprise x technical state from the
growing archive; Czech report docs/tydenni/<week>.md, archive learning/tydenni/ and a query CLI (`--dotaz`).
Test F2 (no look-ahead in all 804 conditions, higher timeframe, locked set; samples; factors; quality; DST week;
neighbours; families). Saturday routine extended; docs/TYDENNI_VYZKUM.md describes the method. Research only.

## R-028 - 2026-10-04: the weekly research connected to the model (user's request)

`scripts/vyzkum_most.py`: per pair the research selects daily technical conditions with a 5-day effect (one per
indicator family, ROBUST only) and event-day rules (Fed / ECB / BoJ / BoE decisions, US NFP / CPI x technical state at
the previous close), each time only on data known before the period it is used in (gate split 0: to 2018, split 1:
to 2022; live: everything up to the model's last price day). Fix in the research statistics (also in the weekly report):
a condition is scored by its forward return ABOVE the pair's average of the same window, not by the raw return - the
raw return made conditions that merely followed a pair's long drift (e.g. EUR/USD 2014-15) look predictive.
self_learn: per-split trade lists (`split_lists`), add-on lists get their own margin grid (ADDON_STEPS) instead of
shrinking the tier grid. Round 24 through gate v3, all REJECTED: research veto (monthly profile: no feasible margins),
research half size (2019-22 return/dd 4.30 vs 4.49, 2023-26 1.10 vs 1.43), research boost/half (2023-26 1.73 vs 1.43
but 2019-22 3.89 vs 4.49), event-day add-on (4.3 instead of 3.4 winning trades a month, 2019-22 3.99 vs 4.49,
2023-26 1.50 vs 1.43); the max profile was worse in all four.
Live (information only, the rule is unchanged): signals_live adds per pair the research conditions active at the
current daily bar (`vyzkum`), every signal gets the research votes for / against, and the forward test stores them
(`vyzkum_pro`, `vyzkum_proti`) so live trades will show whether the research is right; the hourly update adds notes
for events in the next 3 days that match a confirmed event-day rule and a weekly research summary (`vyzkum_tyden`);
the dashboard has a new section "Týdenní výzkum trhu" and research notes at pairs, signals and model trades.
Hourly data for the live signals: 2 years (the daily research conditions need 250+ bars). Test F2 extended.

## R-029 - 2026-10-04: complete code audit (user's request; docs/AUDIT_2026-10-04.md)

Critical: the backtest and the learning decided and entered at the Friday 17:00 New York close, the live run decides
at 16:05 New York - 159 of 1,415 Friday RSI(2) extremes differ between 16:00 and the close. New simulator mode
`Rule.decide_h` (`profit_deep.prepared_live`: the decision day up to 16:00 New York, the earlier days with their full
closes; equal to the full series at decide_h=0 for all 42 indicators x 12 pairs, disk cache keyed by the data and the
indicator code); the champions have `decide_h: 1`, EVAL_VERSION 4; the live run decides from the Friday up to 16:00
New York whenever it runs after it (`decision_cut`), the forward test enters at that moment and price. Critical
(look-ahead, research only): `profit_lab.weekly_aligned` gave every day the whole week's close / high / low and
`week_end` read the next day's date - now causal (completed weeks + the week so far), week end = Friday.
High: leverage 1:30 for every pair - ESMA retail 1:20 for AUD/USD, NZD/USD, AUD/JPY (`profit_lab2.leverage`, used in
the simulator, the research bridge, live plans, the journal, the forward test and the dashboard); the forward test
had no costs / swap, checked the central bank exit before the stop and exited one hour late (now as `simulate`);
a stale rate counted as a zero change and let the weakest tier (threshold 0.0) signal both ways (now: no decision on
that pair); pair_stats measured TP2 / TP3 on other entries than the rule (now the same entries; labelled as an
in-sample frequency). Medium / low: RSI of a flat market 0 / 100 -> 50; Bollinger variance from running sums ->
per window; `champion_report` used its own copy of the trade lists -> `self_learn.trade_lists(cfg, change)`; one
spread table, one central bank map, one set of day names; research failure visible (`vyzkum_chyba`); stale-rate
warning text; dead gate-v1 constants and the outdated log header; unused imports; Yahoo data downloaded once per run.
Diagnostics: CHYBA when the champion's decision time differs from the live one or the champion uses an option the
live run does not implement (`live_unsupported`). Test F3 (52 tests pass).
Re-evaluated champions (leverage per pair + live decision time), the honest numbers: monthly 2019-22 +53.0 % a year
(dd 28.6 %), 2023-26 +28.2 % (dd 24.1 %) - before the audit +87.2 % / +39.5 %; the leverage alone accounts for
+86.8 % -> +68.1 % (2019-22), the decision time for +68.1 % -> +53.0 %. Profile max: +62.8 % / +19.7 %.
Round 25 (from the leverage fix) through gate v3, all REJECTED in both profiles: the same position volume for 1:20
pairs (1.5x margin), the minimum target in price instead of % of the margin, both.
Gate check with placebo candidates (no information): 10 % of the trades dropped at random 0 of 20 pass; random
position sizes (log-normal, sd 0.25) 1 of 20 pass in each profile - about 5 % of pure-noise sizing changes pass gate
v3 (the margin re-fit sometimes hits better test years). Ablation under the honest evaluation: only the exit in profit
before a central bank decision still passes the gate against the champion without it (both profiles); stop 4 ATR,
RSI(3) < 15 and vol sizing are better in one or both tests but below +10 % or mixed - the versions without them do
not pass either, so the champions stay. Live: the Friday decision from the day up to 16:00 New York whatever the run
time; the forward test records only signals published before the close; a tick after the Friday close no longer
creates a phantom Saturday bar; on the weekend the dashboard says the Friday signals can no longer be entered.

## R-030 - 2026-10-05: intraday (hourly / minute) research and loosened rules (user's question; docs/INTRADAY.md)

Hourly FXCM BID/ASK 2012-2026 (`scripts/intraday_lab.py`): 300 variants in 9 families (hour-of-day seasonality,
hourly shocks, weekend gaps, carry by session, Asian range breakout, intraday momentum, previous-day high / low,
Gotobi, hourly dips in the rate direction) with max(retail, real FXCM spread) + slippage and no minimum profit per
trade - none positive after costs in all three periods; per pair x hour (1,728 combinations) 683 are gross-positive
in both checks (chance ~432) but only 12 net-positive and none with t > 2. Walk-forward LightGBM on 30 hourly
features (`scripts/intraday_ml.py`, yearly retrain 2016-2026, threshold on the previous year): gross edge positive in
every horizon (1 h +0.011..+0.021 %, 4 h +0.015..+0.032 %, 8 h, 24 h ~+0.025 %), net around zero or negative.
Minute FXCM BID/ASK 2016-2026 (`scripts/fxcm_m1.py`, `scripts/minute_lab.py`; night scalper, round numbers
(Osler 2003), London open range, minute spikes, NFP / CPI): nothing robust after costs; the night scalper is
gross-positive in every period (+0.002..+0.015 %, 53-73 % wins) but loses the spread. Conclusion: short-term
patterns exist but are smaller than retail costs (1-3 pips); that is why banks / HFT (0.1-0.3 pip) earn on them.
Round 26 (loosened rules, gate v3), all REJECTED in both profiles: no minimum target (monthly 2019-22 +56.2 % / dd 20 %
vs +53.0 % / 29 %, 2023-26 +28.6 % vs +28.2 % - only +2 % return per drawdown), 5 % minimum target (identical),
RSI(2) < 10 (+24.0 % / +14.9 %), RSI(2) < 10 without the minimum (+22.1 % / +15.9 %), daily decisions (6.6 / 5.2
winning trades a month, +22.4 % / +15.6 %). Live: RSI thresholds are read from the champion's rule
(`signals_live.signal_parts`), min_tp_pct is supported live, diagnostics flag unsupported signals / daily tiers.

## R-031 - 2026-10-05: martingale and other gambling systems (user's question; docs/HAZARD.md)

`scripts/hazard_lab.py`: theory (100,000 sessions of 100 bets): martingale raises the share of winning sessions on a
fair bet from 46 % to 82 % at an unchanged result per unit staked (0.000) and a worst session of -1,885 vs -40 units;
with costs it loses 4x more than a flat stake (it stakes more). Kelly on the champion's 2012-2022 trades: 36 % (monthly)
/ 42 % (max) of the account as margin per trade vs the model's 20 % with up to 9 trades open (88-98 % of the account
tied up) - the model already bets near Kelly. Grid / martingale robot on hourly FXCM 2012-2026 (5 pairs x equal /
doubling x 5 / 8 levels x 3 directions, ESMA close-out at 50 % margin level, no swap): 99.6 % of the baskets closed
in profit, yet 34 of 60 accounts ended below 10 % and 59 of 60 had a drawdown >= 50 %; with doubling 29 of 30 ended
below half. `portfolio_sim.Money` (martingale / anti / d'Alembert / Fibonacci on the account's closed trades) and
`self_learn.run_pf` (one call for the account simulation, also used by champion_report). Round 27 through gate v3,
all REJECTED in both profiles: martingale 2x (max profile 2023-26 drawdown 55 % vs 28 %), martingale 1.5x,
anti-martingale, d'Alembert, Fibonacci. Test F3 extended.

## R-032 - 2026-10-05 learning run (morning): round 28 (all rejected)

Forward-looking rate expectations and year-end liquidity, through gate v3: 2-year yield differential change over 3
months as confirmation for the weak tiers / all tiers (monthly profile: no margins with >= 2 wins a month; max:
2023-26 +21.1 % / +3.8 %), a 2-month rate window instead of 3 (monthly: infeasible; max 2019-22 +30.1 %), no new
trade 15 December - 5 January (monthly: 2019-22 +52.8 % / dd 23 % vs +53.0 % / 29 %, 2023-26 +28.0 % / 24 % - return
per drawdown +23 % and -1 %; max: slightly worse in both). New rule option `skip_holidays` (simulator + live run).

## R-033 - 2026-10-05 learning run (noon): round 29 (all rejected)

Loser clusters and stale rate signals, through gate v3. New account options `max_obchodu` (at most N open trades at
once, at the same moment the stronger tier first) and `pauza_po_stopu` (no new trade in a pair for N days after the
account's trade there hit its stop) in `portfolio_sim.run_portfolio` / `self_learn.run_pf`, with a regression test
(test_f3_audit.py). Not in the live run (diagnostika.live_unsupported reports them) - only needed if one passes.
- at most 5 / 7 open trades: monthly 2019-22 +49.9 % / +52.4 % (champion +53.0 %), 2023-26 +27.8 % / +28.2 % at the
  same drawdowns; max 2023-26 +19.3 % / +19.7 % with dd 28 % (no gain in return per drawdown). Rejected.
- pause 2 / 4 weeks after a stop in the pair: monthly 2023-26 identical to the champion (the weekly signals almost
  never come back to a stopped pair within 4 weeks), 2019-22 +53.0 % / +51.6 %; max 2019-22 +64.5 % / +63.3 % but
  dd 27 % (return per drawdown below the champion), 2023-26 identical. Rejected.
- BoE dates 8/2015-12/2016 (ideas queue): the summary pages of those months are not at the URL scheme the collector
  uses and the site index lists none of them; still missing. Found: the 2015 minutes pages of June / July say "meeting
  ending 3 June / 8 July" (the vote day) and May 2015 "7 and 8 May"; the stored decision days 2015-05-08, 2015-06-03,
  2015-07-08 may be a day (May: a weekend) before the announcement - NEOVĚŘENO, not changed without a source of the
  announcement days.

## R-034 - 2026-10-05 learning run (afternoon): round 30 (all rejected)

Where the rate divergence comes from, through gate v3. New tier confirmations `confirm_src` "own" (the bought
currency's own OECD rate did not fall over the rule's window) and "both" (and the sold currency's did not rise), from
the per-currency change `extra(..., "rate_chg:base/quote")` (checked: base minus quote equals `rates_mom` exactly).
Not in the live run (diagnostika.live_unsupported reports `stupen.confirm_src`) - only needed if one passes.
- bought currency not cutting, weak tiers / all tiers: monthly profile infeasible (no margins with >= 2 wins a month);
  max 2019-22 +51.8 % / +30.1 % (champion +62.8 %), 2023-26 +21.5 % / +20.3 % (champion +19.7 %) - too few trades.
- both legs (bought not cutting, sold not hiking), weak tiers: monthly infeasible; max 2019-22 +57.2 % / dd 21 %
  (return per drawdown +3 %, needs +10 %), 2023-26 +17.3 % / dd 31 %. Rejected.

## R-035 - 2026-10-06 learning run (morning): round 31 (all rejected)

The pullback on a longer horizon and the end of the pullback, through gate v3. New rule option `rsi_exit` (close at a
New York close once the daily RSI(2) recovered above x, shorts below 100 - x) in `profit_deep.simulate`; the weekly
entry uses the existing `W RSI2<10` signal (weekly closes, the week ending at the Friday decision). Neither is in the
live run (diagnostika.live_unsupported reports them) - only needed if one passes.
- weekly RSI(2) < 10 as an extra entry, strong tiers / all tiers: many more, weaker trades; the margins fall to
  10 % / 2-5 %. Monthly 2019-22 +28.6 % / +26.5 % (champion +53.0 %), 2023-26 +18.7 % / +17.7 % at dd 17-19 %; max
  2019-22 +21.1 % (champion +62.8 %), 2023-26 all tiers +21.0 % at dd 13 % (return per drawdown 1.58 vs 0.70) - fails
  the 2019-22 split and the 85 % return condition. Rejected.
- exit once RSI(2) > 70: monthly infeasible (fewer winning trades a month), max 2019-22 +26.0 %, 2023-26 +13.8 % -
  the 0.75 ATR target already takes the reversion; closing earlier cuts the winners. Rejected.
