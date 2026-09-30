"""E6 - statistics with sample guard, error taxonomy, calibration, model
registry, change log (pre-change gate) and promotion gate."""

import os
import sqlite3
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="fxbot_e6_")
os.environ["FXBOT_IGNORE_DOTENV"] = "1"

from src.database import get_connection, initialize_database  # noqa: E402
from src.engine.params import DEFAULT_PARAMS as P  # noqa: E402
from src.stats import registry as R  # noqa: E402
from src.stats.errors import classify, taxonomy_table  # noqa: E402
from src.stats.performance import calibration, max_drawdown, sample_class, summarize, wilson  # noqa: E402
from src.stats.validation import difference  # noqa: E402

initialize_database()


def trade(state, r=None, t0=0, conf="B", mfe=None, mae=None, notes="", fwd=None, cluster=None, setup="PULLBACK"):
    return {"outcome_state": state, "r_net": r, "r_model": r, "t0": t0, "confidence": conf, "mfe_r": mfe,
            "mae_r": mae, "notes": notes, "fwd_move_atr": fwd, "event_cluster": cluster or f"c{t0}",
            "triggered": state not in ("NOT_ACTIVATED",), "setup_type": setup}


# ---------------------------------------------------------------- summary numbers
trades = [trade("TP1_BEFORE_SL", 2.0, 1, fwd=1.0), trade("SL_BEFORE_TP1", -1.0, 2, fwd=-0.5),
          trade("SL_BEFORE_TP1", -1.0, 3, fwd=0.2), trade("TP1_BEFORE_SL", 2.0, 4, fwd=2.0),
          trade("EXPIRED", 0.5, 5, fwd=0.3), trade("NOT_ACTIVATED", None, 6, notes="TP1 dosazen bez vstupu", fwd=1.0),
          trade("SEQUENCE_UNKNOWN", None, 7)]
s = summarize(trades)
assert s.predictions == 7 and s.binary == 4 and s.wins == 2 and s.win_rate == 0.5
assert abs(s.expectancy - 0.5) < 1e-9 and abs(s.profit_factor - 4.5 / 2) < 1e-9
assert s.direction_n == 6 and abs(s.direction_accuracy - 5 / 6) < 1e-9, "forward move measure"
assert s.not_activated == 1 and s.sequence_unknown == 1 and s.losing_streak == 2
assert max_drawdown([2, -1, -1, 2, 0.5]) == -2
assert sample_class(19).startswith("POUZE") and sample_class(20).startswith("PREDBEZNE") and sample_class(100).startswith("DLOUHO")
low, high = wilson(5, 10)
assert 0.2 < low < 0.3 and 0.7 < high < 0.8

# effective sample: two predictions of the same cluster count once
same = [trade("TP1_BEFORE_SL", 1.5, 1, cluster="day1:-USD"), trade("TP1_BEFORE_SL", 1.5, 2, cluster="day1:-USD")]
assert summarize(same).effective_n == 1

# ---------------------------------------------------------------- calibration
cal_trades = ([trade("TP1_BEFORE_SL", 1.5, k, conf="A") for k in range(15)] + [trade("SL_BEFORE_TP1", -1, k, conf="A") for k in range(10)]
              + [trade("TP1_BEFORE_SL", 1.5, k, conf="C") for k in range(5)] + [trade("SL_BEFORE_TP1", -1, k, conf="C") for k in range(20)])
assert calibration(cal_trades)["verdict"] == "KALIBRACE OK"
flipped = [dict(t, confidence="C" if t["confidence"] == "A" else "A") for t in cal_trades]
assert calibration(flipped)["verdict"] == "CALIBRATION FAILURE"

# ---------------------------------------------------------------- error taxonomy
assert classify(trade("SL_BEFORE_TP1", -1, mfe=1.2))["family"] == "TP"
assert classify(trade("SL_BEFORE_TP1", -1, mfe=0.6))["family"] == "timing"
assert classify(trade("SL_BEFORE_TP1", -1, mfe=0.1))["family"] == "direction"
assert classify(trade("SL_BEFORE_TP1", -1, mfe=0.1, setup="BREAKOUT_RETEST"))["family"] == "trigger"
assert classify(trade("NOT_ACTIVATED", notes="TP1 dosazen bez vstupu"))["family"] == "entry"
assert classify(trade("SEQUENCE_UNKNOWN"))["family"] == "data"
assert classify(trade("TP1_BEFORE_SL", 2.0, mae=0.3)) is None
assert list(taxonomy_table([trade("SL_BEFORE_TP1", -1, mfe=1.2)] * 3).values()) == [3]

# ---------------------------------------------------------------- registry + change log
fp = R.ensure_baseline(P)
assert R.champion()["fingerprint"] == fp and "ZADNY" in R.champion()["note"]
assert R.ensure_baseline(P.with_changes(min_rr=2.0)) == fp, "only one champion"
challenger = P.with_changes(entry_offset_atr=0.4)
R.register(challenger, "wf-candidate", "CHALLENGER")
assert {e["status"] for e in R.entries()} == {"CHAMPION", "CHALLENGER"}

complete = R.ChangeRecord("CH-001", "TP1 often missed by a few pips", "TP1 too far in ranges", "max_tp1_atr 3.0",
                          "max_tp1_atr 2.5", [54, 55], "H1 ATR", "more TP1 hits", "lower R per win", "none known",
                          "walk-forward + robustness", "params fingerprint " + fp, "C")
assert R.log_change(complete) == "SAFE TO TEST"
incomplete = R.ChangeRecord("CH-002", "x", "", "a", "b", [1], "", "", "", "", "", "", "C")
assert R.log_change(incomplete) == "HOLD"
assert R.log_change(R.ChangeRecord("CH-003", "x", "y", "a", "b", [1], "", "z", "f", "", "t", "r", "Z")) == "REJECT"
try:
    with get_connection() as c:
        c.execute("DELETE FROM change_log")
    raise AssertionError("change log must be append-only")
except sqlite3.DatabaseError:
    pass

# ---------------------------------------------------------------- promotion gate
few = summarize([trade("TP1_BEFORE_SL", 2.0, k) for k in range(30)])
base = summarize([trade("SL_BEFORE_TP1", -1.0, k) for k in range(30)])
decision, reasons = R.promotion_gate(few, base, difference(few, base))
assert decision == "HOLD" and any("malo OOS" in r for r in reasons), "never promote on a small sample"
many_c = summarize([trade("TP1_BEFORE_SL" if k % 2 else "SL_BEFORE_TP1", 2.0 if k % 2 else -1.0, k, cluster=f"c{k}")
                    for k in range(300)])
many_b = summarize([trade("TP1_BEFORE_SL" if k % 3 == 0 else "SL_BEFORE_TP1", 2.0 if k % 3 == 0 else -1.0, k,
                          cluster=f"c{k}") for k in range(300)])
decision, reasons = R.promotion_gate(many_c, many_b, difference(many_c, many_b))
assert decision == "PROMOTE", reasons
R.set_status(challenger.fingerprint, "CHAMPION", "test promotion")
assert R.champion()["fingerprint"] == challenger.fingerprint
assert any(e["fingerprint"] == fp and e["status"] == "RETIRED" for e in R.entries())

print("=" * 60)
print("E6 STATISTICS, TAXONOMY, REGISTRY")
print("=" * 60)
print("FORECAST ACCURACY vs TRADE PERFORMANCE, SAMPLE GUARD, CI: PASS")
print("EFFECTIVE SAMPLE (EVENT CLUSTERS): PASS")
print("CALIBRATION OK / FAILURE: PASS")
print("ERROR TAXONOMY: PASS")
print("REGISTRY: ONE CHAMPION, BASELINE WITHOUT EVIDENCE: PASS")
print("CHANGE LOG: PRE-CHANGE GATE, APPEND-ONLY: PASS")
print("PROMOTION GATE: HOLD ON SMALL SAMPLE, PROMOTE ON STRONG OOS: PASS")
print("RESULT: PASS")
print("=" * 60)
