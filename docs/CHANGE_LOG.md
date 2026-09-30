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
