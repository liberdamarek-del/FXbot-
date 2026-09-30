"""E7 - upgrade scenario: an existing Block A-D database (real Twelve Data
USD/JPY bars from the fixture, a TECH-0.1 prediction in the ledger) gets
the V7.8.0 run without any migration step. The old prediction is audited
by the new resolver (MODEL-PRICE: Twelve Data has no bid/ask), nothing
old is changed."""

import os
import tempfile
from datetime import datetime, timedelta, timezone

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="fxbot_e7_")
os.environ["FXBOT_IGNORE_DOTENV"] = "1"

from tests.seed import seed_database  # noqa: E402

from src.database import get_connection  # noqa: E402
from src.prediction_ledger import get_prediction, ledger_digest, lock_prediction  # noqa: E402
from src.v78.run import RunOptions, execute  # noqa: E402

UTC = timezone.utc
assert seed_database() == 865            # real USD/JPY 1min bars 2026-09-28 18:32 .. 09-29 08:56

# a TECH-0.1 prediction as Block C would have locked it (BUY NOW at 157.60)
t0 = datetime(2026, 9, 28, 20, 0, 30, tzinfo=UTC)
with get_connection() as c:
    row = c.execute("SELECT close FROM raw_bars WHERE symbol='USD/JPY' AND bar_time <= ? ORDER BY bar_time DESC LIMIT 1",
                    (t0.isoformat(),)).fetchone()
price = float(row["close"])
old_pid = lock_prediction(
    model_version="TECH-0.1", t0=t0, instrument="USD/JPY", decision="BUY NOW", reference_price=f"{price:.3f}",
    price_source="TwelveData 1min", price_timestamp=t0 - timedelta(seconds=30), data_state="CURRENT",
    data_quality="C", entry=f"{price:.3f}", stop_loss=f"{price - 0.30:.3f}", tp1=f"{price + 0.45:.3f}",
    tp2=f"{price + 0.60:.3f}", tp3=f"{price + 0.80:.3f}", primary_horizon="24h", thesis="t", counterforce="c",
    invalidation="i", now=t0,
)
digest_before = ledger_digest()

now = datetime(2026, 9, 29, 9, 3, 0, tzinfo=UTC)
result = execute(RunOptions(symbols=["USD/JPY"], fetch=False, lock=True, now=now))
assert result["state"].startswith("COMMITTED"), result.get("traceback") or result["state"]
assert old_pid in result["report"], "the old prediction is part of the due-outcome audit"
p = get_prediction(old_pid)
assert p["model_version"] == "TECH-0.1" and ledger_digest() == digest_before, "old locked fields untouched"
states = [s["state"] for s in p["states"]]
assert states[0] == "NEW" and "TRIGGERED" in states, states
if p["outcomes"]:
    assert "MODEL-PRICE" in p["outcomes"][-1]["path_coverage"], "Twelve Data minutes = model price layer"
assert "USD/JPY" in result["report"] and "12data" in result["report"]

print("=" * 60)
print("E7 UPGRADE FROM BLOCK A-D DATABASE")
print("=" * 60)
print("RUN ON EXISTING DATABASE WITHOUT MIGRATION STEP: PASS")
print("TECH-0.1 PREDICTION AUDITED, LOCKED FIELDS UNCHANGED: PASS")
print(f"OUTCOME: {p['outcomes'][-1]['outcome_state'] if p['outcomes'] else 'still open'}")
print("RESULT: PASS")
print("=" * 60)
