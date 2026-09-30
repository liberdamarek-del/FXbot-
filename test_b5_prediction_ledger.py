"""Block B5 - prediction ledger: locking, immutability, input-quality gate."""

import os
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="fxbot_b5_")

from src.database import get_connection
from src.prediction_ledger import (
    PredictionRejected,
    add_state,
    get_prediction,
    ledger_digest,
    list_predictions,
    lock_prediction,
    record_outcome,
)

UTC = timezone.utc
NOW = datetime(2026, 9, 30, 10, 0, 30, tzinfo=UTC)
T0 = datetime(2026, 9, 30, 10, 0, tzinfo=UTC)
PRICE_TIME = datetime(2026, 9, 30, 9, 59, tzinfo=UTC)


def buy(**overrides):
    args = dict(
        model_version="V7.8.0-test",
        t0=T0, instrument="USD/JPY", decision="WAIT FOR BUY",
        reference_price="157.20", price_source="TwelveData",
        price_timestamp=PRICE_TIME, data_state="CURRENT", data_quality="B",
        entry="157.10", entry_zone_low="157.05", entry_zone_high="157.15",
        stop_loss="156.80", tp1="157.60", tp2="158.00", tp3="158.40",
        primary_horizon="24h", thesis="Yield spread widening",
        counterforce="Intervention risk", invalidation="Close below 156.80",
        confidence="B", reasons=["spread", "trend"], inputs={"atr": "0.18"},
        now=NOW,
    )
    args.update(overrides)
    return lock_prediction(**args)


def rejected(**overrides):
    try:
        buy(**overrides)
    except PredictionRejected as exc:
        return str(exc)
    raise AssertionError(f"accepted but must be rejected: {overrides}")


# 1. a valid BUY is stored, gets an ID and the state NEW
pid = buy()
assert pid.startswith("P-20260930T100000Z-")
p = get_prediction(pid)
assert p["decision"] == "WAIT FOR BUY" and p["direction"] == "BUY"
assert p["stop_loss"] == "156.80" and p["data_state"] == "CURRENT"
assert p["current_state"] == "NEW" and len(p["states"]) == 1
assert p["reasons"] == '["spread", "trend"]'

# 2. valid SELL and NO TRADE
sell = buy(decision="SELL NOW", entry="157.20", entry_zone_low=None, entry_zone_high=None,
           stop_loss="157.60", tp1="156.80", tp2="156.40", tp3=None)
assert get_prediction(sell)["direction"] == "SELL"
no_trade = buy(decision="NO TRADE", stop_loss=None, tp1=None, tp2=None, tp3=None,
               entry=None, entry_zone_low=None, entry_zone_high=None,
               thesis=None, counterforce=None, invalidation=None)
assert get_prediction(no_trade)["direction"] == "NONE"

# 3. input-quality gate: only CURRENT data may produce a prediction
for state in ("STALE", "CLOSED", "MISSING", "UNVERIFIED", "CONFLICT"):
    assert state in rejected(data_state=state)

# 4. no post-T0 information, no future T0, no naive timestamps
assert "post-T0" in rejected(price_timestamp=T0 + timedelta(minutes=1))
assert "future" in rejected(t0=NOW + timedelta(minutes=5), price_timestamp=PRICE_TIME)
assert "timezone" in rejected(t0=datetime(2026, 9, 30, 10, 0))

# 5. level consistency
assert "below entry" in rejected(stop_loss="157.50")
assert "above entry" in rejected(tp1="157.00", tp2=None, tp3=None)
assert "ascending" in rejected(tp2="157.50", tp3="157.55", tp1="157.60")
assert "take profits must be below entry" in rejected(decision="SELL NOW", stop_loss="157.60", tp1="157.50", tp2=None, tp3=None, entry="157.20")
assert "required" in rejected(stop_loss=None)
assert "entry zone" in rejected(entry_zone_high=None)
assert "exceed" in rejected(entry_zone_low="157.30")

# 6. other validation
assert "thesis" in rejected(thesis="")
assert "invalidation" in rejected(invalidation=None)
assert "decision" in rejected(decision="BUY MAYBE")
assert "positive" in rejected(reference_price="-1")
assert "not a number" in rejected(reference_price="abc")
assert "bid must not exceed ask" in rejected(bid="157.25", ask="157.20")
assert "confidence" in rejected(confidence="Z")
assert "data_quality" in rejected(data_quality="E")

# rejected predictions left nothing behind
assert len(list_predictions()) == 3

# 7. IMMUTABILITY is enforced by the database itself
for statement in (
    "UPDATE predictions SET stop_loss = '1' WHERE prediction_id = '%s'" % pid,
    "UPDATE predictions SET thesis = 'rewritten'",
    "DELETE FROM predictions",
    "UPDATE prediction_states SET state = 'RESOLVED'",
    "DELETE FROM prediction_states",
):
    with get_connection() as connection:
        try:
            connection.execute(statement)
        except sqlite3.DatabaseError as exc:
            assert "immutable" in str(exc) or "append-only" in str(exc), str(exc)
        else:
            raise AssertionError(f"database allowed: {statement}")

assert get_prediction(pid)["stop_loss"] == "156.80"

# 8. appended state transitions and outcomes; history stays intact
add_state(pid, "WAITING", "price above entry zone", changed_at=T0 + timedelta(minutes=5))
add_state(pid, "TRIGGERED", "entry touched", changed_at=T0 + timedelta(hours=2))
record_outcome(pid, "SEQUENCE_UNKNOWN", path_coverage="PARTIAL",
               notes="TP1 and SL inside one 5min bar", recorded_at=T0 + timedelta(days=1))
record_outcome(pid, "TP1_BEFORE_SL", path_coverage="COMPLETE", r_multiple="1.6",
               mfe="0.90", mae="0.10", recorded_at=T0 + timedelta(days=2))

p = get_prediction(pid)
assert [s["state"] for s in p["states"]] == ["NEW", "WAITING", "TRIGGERED"]
assert p["current_state"] == "TRIGGERED"
assert [o["outcome_state"] for o in p["outcomes"]] == ["SEQUENCE_UNKNOWN", "TP1_BEFORE_SL"]
assert p["stop_loss"] == "156.80", "locked fields never change"

for bad in (lambda: add_state("P-none", "WAITING"),
            lambda: add_state(pid, "FLYING"),
            lambda: record_outcome("P-none", "UNRESOLVED"),
            lambda: record_outcome(pid, "WON"),
            lambda: record_outcome(pid, "PARTIAL", mfe="abc")):
    try:
        bad()
    except PredictionRejected:
        pass
    else:
        raise AssertionError("invalid follow-up accepted")

# 9. digest: reproducible, and follow-up records do not change locked data
digest = ledger_digest()
assert digest == ledger_digest() and len(digest) == 64
add_state(pid, "ACTIVE", "test")
assert ledger_digest() == digest
buy(instrument="EUR/USD", reference_price="1.1300", entry="1.1290", entry_zone_low=None,
    entry_zone_high=None, stop_loss="1.1250", tp1="1.1340", tp2=None, tp3=None)
assert ledger_digest() != digest

# 10. listing
assert len(list_predictions("EUR/USD")) == 1
assert len(list_predictions(limit=2)) == 2

print("=" * 60)
print("B5 PREDICTION LEDGER")
print("=" * 60)
print("VALID BUY / SELL / NO TRADE STORED: PASS")
print("ONLY CURRENT DATA CAN PRODUCE A PREDICTION: PASS")
print("NO POST-T0 INFORMATION / FUTURE T0: PASS")
print("LEVEL CONSISTENCY (SL / TP SIDES): PASS")
print("DATABASE-ENFORCED IMMUTABILITY: PASS")
print("APPEND-ONLY STATES AND OUTCOMES: PASS")
print("DIGEST REPRODUCIBLE: PASS")
print("RESULT: PASS")
print("=" * 60)
