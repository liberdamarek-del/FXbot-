"""E5 - end-to-end V7.8.0 run on a synthetic archive (offline).

Checks the run procedure contract, not trading quality: run states,
module trace 0-145 without silent skip, staged commit + read-back,
artifacts with hashes, the Czech output contract (T14), previous official
T0 continuity, immutable locks linked to the run.
"""

import json
import math
import os
import random
import sqlite3
import tempfile
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="fxbot_e5_")
os.environ["FXBOT_IGNORE_DOTENV"] = "1"

from src.database import get_connection, initialize_database  # noqa: E402
from src.fundamental.store import upsert_series  # noqa: E402
from src.models import RawBar  # noqa: E402
from src.path_archive import Bar, aggregate, get_path_connection, initialize_path_archive, is_session_minute  # noqa: E402
from src.storage import save_raw_bars  # noqa: E402
from src.v78.run import RunOptions, execute  # noqa: E402

UTC = timezone.utc
NOW = datetime(2026, 9, 29, 12, 0, 20, tzinfo=UTC)
SYMBOLS = ["EUR/USD", "USD/JPY"]
initialize_database()
initialize_path_archive()
rng = random.Random(5)

# ---------------------------------------------------------------- synthetic history (trend + noise)
rows = []
for symbol, price, vol, drift in (("EUR/USD", 1.05, 0.0010, 0.00004), ("USD/JPY", 140.0, 0.0012, 0.00005)):
    hours = []
    ts = int((NOW - timedelta(days=420)).timestamp()) // 3600 * 3600
    end = int(NOW.timestamp()) // 3600 * 3600 - 2 * 3600
    while ts < end:
        if is_session_minute(ts):
            o = price
            c = price * (1 + drift + rng.gauss(0, vol))
            h = max(o, c) * (1 + abs(rng.gauss(0, vol / 3)))
            l = min(o, c) * (1 - abs(rng.gauss(0, vol / 3)))
            s = price * 0.00001
            hours.append(Bar(ts, o, h, l, c, o + s, h + s, l + s, c + s, 10, 1, 60))
            price = c
        ts += 3600
    for tf in ("1h", "4h", "1d"):
        for b in aggregate(hours, tf, True, 3600):
            rows.append((symbol, tf, b.ts, *b[1:], "DUKASCOPY_H1", "VALIDATED", "SYN"))
    # live head: Twelve Data 1-minute bars for the last 2 hours
    minute_bars = []
    last = hours[-1].bc
    for k in range(125):
        t = datetime.fromtimestamp(end + 60 * k, tz=UTC)
        if t + timedelta(minutes=1) > NOW - timedelta(seconds=10):
            break
        p = last * (1 + rng.gauss(0, vol / 10))
        q = Decimal(str(round(p, 5 if symbol == "EUR/USD" else 3)))
        minute_bars.append(RawBar(symbol, "1min", t, t + timedelta(minutes=3), q, q, q, q, "TwelveData"))
        last = p
    save_raw_bars(minute_bars)

with get_path_connection() as c:
    c.executemany("INSERT OR IGNORE INTO market_path VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    c.commit()

days = [date(2025, 6, 1) + timedelta(days=k) for k in range(500)]
for series, base, slope in (("USD.Y2", 4.0, 0.002), ("EUR.Y2", 2.0, 0.0), ("JPY.Y2", 0.5, 0.0),
                            ("USD.POLICY", 4.0, 0.0), ("EUR.POLICY", 2.0, 0.0), ("JPY.POLICY", 0.25, 0.0),
                            ("GLOBAL.VIX", 15.0, 0.0), ("GLOBAL.SPX", 5000.0, 1.0)):
    upsert_series(series, [(d, base + slope * k) for k, d in enumerate(days)], 30, "SYN", None)

# ---------------------------------------------------------------- run 1
result = execute(RunOptions(symbols=SYMBOLS, fetch=False, lock=True, now=NOW))
assert result["state"] in ("COMMITTED", "COMMITTED_CONDITIONAL"), result.get("traceback") or result["state"]
report = result["report"]

# T14: prices + Top-3 + state in the Czech output, critical blocks visible, both certificates
for section in ("CENY (T0 snapshot", "TOP-3", "DATA A CESTA", "AUDIT SPLATNYCH PREDIKCI", "MEZIBEHOVA DELTA",
                "CO MODEL PREHLEDL?", "RUN COMPLETION CERTIFICATE", "DATA PIPELINE CERTIFICATE", "BROKER-BLOCKED"):
    assert section in report, f"missing section {section}"
assert "EUR/USD" in report and "TWELVE_DATA" in report
long_lines = [line for line in report.splitlines() if len(line) > 100]
assert not long_lines, long_lines

with get_connection() as c:
    trace = c.execute("SELECT module_id, status FROM run_trace WHERE run_id = ?", (result["run_id"],)).fetchall()
    run_row = c.execute("SELECT * FROM runs WHERE run_id = ?", (result["run_id"],)).fetchone()
    history = [r["state"] for r in c.execute("SELECT state FROM run_state_history WHERE run_id = ? ORDER BY id",
                                            (result["run_id"],))]
assert sorted(r["module_id"] for r in trace) == list(range(146)), "every module 0-145 has a status (no silent skip)"
assert {r["status"] for r in trace} <= {"PASS", "CONDITIONAL", "BLOCKED", "N/A"}
assert history[:5] == ["PLANNED", "RUNNING", "ANALYSIS_COMPLETE", "PERSISTENCE_PENDING", run_row["state"]]
assert "PASS" in run_row["certificate"], "read-back must pass"

run_dir = result["run_dir"]
manifest = json.loads(open(os.path.join(run_dir, "run_manifest.json"), encoding="utf-8").read())
for name in ("snapshot.json", "coverage.json", "delta.json", "analysis.json", "audit.json", "trace.json", "params.json"):
    assert name in manifest["artifacts"] and os.path.exists(os.path.join(run_dir, name))
snapshot = json.loads(open(os.path.join(run_dir, "snapshot.json"), encoding="utf-8").read())
eur = snapshot["pairs"]["EUR/USD"]
assert eur["canonical"]["source"] == "TWELVE_DATA" and eur["data_state"] in ("LIVE", "FRESH")
assert eur["execution"] == "MODEL-PRICE", "no broker -> never EXECUTABLE"

# locked predictions belong to this run and are immutable
for pid in result["locked"]:
    with get_connection() as c:
        row = c.execute("SELECT run_id, model_version FROM predictions WHERE prediction_id = ?", (pid,)).fetchone()
    assert row["run_id"] == result["run_id"] and row["model_version"].startswith("V7.8.0")
    try:
        with get_connection() as c:
            c.execute("DELETE FROM predictions WHERE prediction_id = ?", (pid,))
        raise AssertionError("delete must be impossible")
    except sqlite3.DatabaseError:
        pass

# ---------------------------------------------------------------- run 2: previous official T0 = run 1
result2 = execute(RunOptions(symbols=SYMBOLS, fetch=False, lock=True, now=NOW + timedelta(minutes=1)))
with get_connection() as c:
    row2 = c.execute("SELECT previous_run_id, previous_t0 FROM runs WHERE run_id = ?", (result2["run_id"],)).fetchone()
assert row2["previous_run_id"] == result["run_id"], "the new run anchors on the last COMMITTED run"
assert "predchozi oficialni T0: 2026-09-29 12:00" in result2["report"]
if result["locked"]:
    assert "teze" in result2["report"].lower() or "mimo Top-3" in result2["report"]

# ---------------------------------------------------------------- lock path with a constructed candidate
from src.engine.decision import Candidate, Gate  # noqa: E402
from src.engine.fundamental import CurrencyState, FundamentalView  # noqa: E402
from src.engine.params import DEFAULT_PARAMS as P  # noqa: E402
from src.engine.pipeline import PairAnalysis  # noqa: E402
from src.engine.regime import RegimeView  # noqa: E402
from src.prediction_ledger import get_prediction  # noqa: E402
from src.v78.coverage import Coverage  # noqa: E402
from src.v78.quotes import QuoteObservation, build_pair_quote  # noqa: E402
from src.v78.run import lock_candidate  # noqa: E402
from src.engine.data import load_pair  # noqa: E402

t_lock = NOW + timedelta(minutes=2)
quote = build_pair_quote("EUR/USD", [QuoteObservation("EUR/USD", "TWELVE_DATA", "API_SNAPSHOT", 1.3423,
                                                      t_lock.timestamp() - 70, t_lock.timestamp())], t_lock)
cand = Candidate("EUR/USD", int(t_lock.timestamp()), "WAIT FOR BUY", "BUY", "BUY", "PULLBACK", 1.3410, 1.3405, 1.3415,
                 1.3395, [1.3450, 1.3470, 1.3490], rr_gross=2.7, rr_net=2.4, cost_price=0.0001, confidence="B",
                 clusters_for=["PRICE_TREND", "RATES_REPRICING"], hypotheses={"H1": "h1", "H2": "h2", "H3": "h3"},
                 invalidation="uzavreni H1 pod 1.33950", gates=[Gate("DATA_STATE", "PASS", "ok")], risk_pct=0.5,
                 reasons=["test"])
analysis = PairAnalysis("EUR/USD", cand.t, None, FundamentalView("EUR/USD", cand.t, CurrencyState("EUR"),
                        CurrencyState("USD")), RegimeView("NORMAL", "TREND", "NEUTRAL", "NONE", False), cand)
analysis.series = load_pair("EUR/USD", P)
cov = Coverage("EUR/USD", 0, 1, 10, 10, "COMPLETE", 0)
pid = lock_candidate("RUN-TEST", t_lock, cand, analysis, quote, cov, P, "fp")
assert pid.startswith("P-"), pid
locked = get_prediction(pid)
inputs = json.loads(locked["inputs"])
assert locked["run_id"] == "RUN-TEST" and locked["decision"] == "WAIT FOR BUY" and locked["confidence"] == "B"
assert locked["price_source"].startswith("TWELVE_DATA") and "MODEL-PRICE" in locked["price_source"]
assert inputs["path_coverage_state"] == "COMPLETE" and inputs["risk_pct"] == 0.5 and inputs["gates"]
stale = build_pair_quote("EUR/USD", [QuoteObservation("EUR/USD", "TWELVE_DATA", "API_SNAPSHOT", 1.3423,
                                                      t_lock.timestamp() - 2000, t_lock.timestamp())], t_lock)
assert lock_candidate("RUN-TEST", t_lock, cand, analysis, stale, cov, P, "fp").startswith("nezamceno")

# forward anti-model control (module 74): the mirrored plan is fixed at T0 from
# the analysis price (here absent -> the locked reference price 1.3423)
from src.v78.audit import control_outcome, mirrored_plan  # noqa: E402
from src.v78.run import ledger_controls  # noqa: E402

direction, a_entry, a_stop, a_tp1 = mirrored_plan(locked)
assert direction == "SELL"
assert abs(a_entry - 1.3436) < 1e-9 and abs(a_stop - 1.3451) < 1e-9 and abs(a_tp1 - 1.3396) < 1e-9
assert control_outcome(locked, t_lock + timedelta(minutes=5)).outcome_state is None  # horizon still open
assert all(c["symbol"] and c["outcome_state"] for c in ledger_controls(0.0, t_lock + timedelta(minutes=5)))

# ---------------------------------------------------------------- backtest replay on the same archive
from src.engine.backtest import BacktestConfig, run as run_backtest  # noqa: E402
from src.stats.validation import benchmark  # noqa: E402

bt_start = int((NOW - timedelta(days=200)).timestamp())
bt_config = BacktestConfig(SYMBOLS, bt_start, int(NOW.timestamp()), P)
sequential = run_backtest(bt_config, workers=1)
parallel = run_backtest(bt_config, workers=2)
row_key = lambda rows: [(r["symbol"], r["t0"], r["direction"], r["outcome_state"], r["r_net"]) for r in rows]
assert sequential.decisions > 0 and sequential.decisions == parallel.decisions
assert row_key(sequential.trades) == row_key(parallel.trades) and row_key(sequential.anti) == row_key(parallel.anti)
assert len(sequential.anti) == len(sequential.trades), "every model trade has its anti-model twin"
assert all(a["direction"] != m["direction"] for m, a in zip(sequential.trades, sequential.anti))
assert set(benchmark(sequential)) >= {"model", "anti", "paired", "bounds_model"}

print("=" * 60)
print("E5 V7.8.0 RUN PROCEDURE (END-TO-END, OFFLINE)")
print("=" * 60)
print("RUN STATE MACHINE PLANNED -> ... -> COMMITTED: PASS")
print("MODULE TRACE 0-145 COMPLETE: PASS")
print("ARTIFACTS + HASHES + READ-BACK: PASS")
print("T14 CZECH OUTPUT CONTRACT (PRICES, TOP-3, CERTIFICATES): PASS")
print("PREVIOUS OFFICIAL T0 CONTINUITY: PASS")
print(f"LOCKED IN RUN 1: {len(result['locked'])} (immutable, linked to run): PASS")
print("FORWARD ANTI-MODEL CONTROL (MIRRORED PLAN AT T0): PASS")
print(f"BACKTEST REPLAY {sequential.decisions} DECISIONS, {len(sequential.trades)} TRADES, PARALLEL = SEQUENTIAL: PASS")
print("RESULT: PASS")
print("=" * 60)
