# FXBOT PROJECT STATE

## Project rules

- Broker/XTB integration: OUT OF SCOPE
- Live order execution: OUT OF SCOPE
- RAW DATA != VALIDATED DATA != TRADING SIGNAL
- Do not reopen completed modules without a concrete reason.
- QUICK CHECK after normal changes.
- FULL QUALITY GATE only at logical milestones, integrations, or high-risk changes.
- Do not repeatedly retest unchanged modules.
- Preserve backups before structural changes.
- Development has priority over repetitive validation.

---

# M1 — DATA ENGINE

## Status
IN PROGRESS — FINALIZATION

## Completed

- [x] Twelve Data feed
- [x] RawBar model
- [x] Raw data validation
- [x] SQLite database
- [x] Raw bar storage
- [x] Raw bar deduplication
- [x] Collector audit
- [x] Market session detection
- [x] Gap detection
- [x] Backfill
- [x] Single-bar backfill fix
- [x] Multi-pair collector
- [x] Multi-timeframe collector
- [x] Per-timeframe scheduler
- [x] Retry mechanism
- [x] Graceful collector shutdown

## Validation evidence

- [x] Python syntax checks
- [x] Regression suite: 45/45 PASS
- [x] Multi-pair/multi-timeframe functional test
- [x] Per-timeframe scheduler functional test
- [x] Full gap backfill previously verified
- [x] Quality Gate previously passed after gap repair

## Known limitations

- Freshness thresholds are provisional.
- Twelve Data bar timestamp is not a true source publication timestamp.
- Android/Termux suspension can create collection gaps.
- Current CYCLES value represents scheduler iterations, not full instrument passes.

## Remaining

- [ ] M1 final acceptance
- [ ] PROJECT_STATE maintained from this point onward

---

# M2 — HISTORY

## Status
IN PROGRESS

## Objective

Create an automatic history integrity layer above the existing
collector, gap detector and backfill components.

## Completed

- [x] History manager
- [x] Automatic gap scan
- [x] Automatic missing-data repair
- [x] Multi-pair repair
- [x] Multi-timeframe repair
- [x] Repair limits / safety guards
- [x] Post-backfill verification
- [x] Backfill audit
- [x] History acceptance test

## Design constraints

- Do not rewrite collector logic unnecessarily.
- Do not duplicate gap detection logic.
- Do not duplicate backfill logic unnecessarily.
- Never repair MARKET_CLOSED gaps.
- Never treat partial backfill as successful.
- Backfill must remain idempotent.
- A failed repair must remain visible.
- History repair must not silently alter trading logic.

---

# M3 — BACKTEST

## Status
NOT STARTED

- [ ] Historical data reader
- [ ] Deterministic backtest engine
- [ ] No-look-ahead protection
- [ ] Transaction/cost model
- [ ] Result storage
- [ ] Reproducible backtest report

---

# M4 — PAPER TRADING

## Status
NOT STARTED

- [ ] Simulated positions
- [ ] Entry/exit
- [ ] SL/TP
- [ ] P/L
- [ ] Risk management
- [ ] Position audit
- [ ] Paper-trading engine

---

# M5 — V7.x ADAPTER

## Status
NOT STARTED

- [ ] V7.8 input adapter
- [ ] Signal interface
- [ ] Model/version identification
- [ ] No modification of V7.8 logic unless explicitly justified

---

# M6 — ERROR ANALYSIS

## Status
NOT STARTED

- [ ] Prediction vs actual
- [ ] Deviation
- [ ] Error classification
- [ ] Statistical evaluation
- [ ] Failure analysis
- [ ] Prediction ledger integration

---

# M7 — CONTROLLED LEARNING

## Status
NOT STARTED

- [ ] Long-term learning framework
- [ ] Controlled experiments
- [ ] Out-of-sample validation
- [ ] No autonomous strategy promotion
- [ ] No autonomous live trading

---

# Development policy

## QUICK CHECK

Use after normal isolated changes:

1. syntax
2. import
3. targeted functional test

## FULL QUALITY GATE

Use only:

- milestone completion
- major integration
- database/schema changes
- high-risk architectural changes
- release/acceptance

## Current next action

Implement M2 History Manager.

Do not spend another development cycle repeating already-validated
M1 tests unless the M2 implementation changes their relevant code.
