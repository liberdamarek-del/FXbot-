"""Block B11 - off-hours provider bars: never stored, existing ones quarantined."""

import importlib.util
import os
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="fxbot_b11_")
os.environ["FXBOT_IGNORE_DOTENV"] = "1"
os.environ["BAR_SETTLE_SECONDS"] = "0"
os.environ["DATA_STATE_LAG_TOLERANCE_SECONDS"] = "120"

from src.data_update import bar_in_session, update_instrument
from src.database import BACKUP_DIR, get_connection, initialize_database
from src.gap_detector import detect_gaps, timeframe_delta
from src.models import RawBar
from src.resample import DERIVED_SOURCE, derive_timeframe
from src.storage import save_raw_bar, save_raw_bars

UTC = timezone.utc
ROOT = Path(__file__).resolve().parent
initialize_database()


def at(text):
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


def load_script():
    spec = importlib.util.spec_from_file_location("q", ROOT / "scripts" / "quarantine_offsession.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bar(symbol, when, tf="1min", source="TwelveData", price="1.1"):
    return RawBar(symbol, tf, when, when + timedelta(minutes=3), Decimal(price),
                  Decimal(price) + Decimal("0.1"), Decimal(price) - Decimal("0.1"), Decimal(price), source)


# ---------------------------------------------------------------- 1. session helper
m = timedelta(minutes=1)
assert bar_in_session(at("2026-09-25T20:59"), m) is True          # last Friday minute
assert bar_in_session(at("2026-09-25T21:00"), m) is False
assert bar_in_session(at("2026-09-26T21:34"), m) is False         # Saturday
assert bar_in_session(at("2026-09-27T20:59"), m) is False
assert bar_in_session(at("2026-09-27T21:00"), m) is True          # Sunday open
h4 = timeframe_delta("4h")
assert bar_in_session(at("2026-09-27T20:00"), h4) is True         # 4h bar containing the open
assert bar_in_session(at("2026-09-26T08:00"), h4) is False

# ---------------------------------------------------------------- 2. update never stores off-session bars
class Provider:
    """Like the observed provider: bars around the clock, including the weekend."""
    def __init__(self, now): self.now = now
    def _bars(self, symbol, tf, start, end):
        step, cur, out = timeframe_delta(tf), start, []
        while cur <= end:
            if cur <= self.now:
                out.append(bar(symbol, cur, tf))
            cur += step
        return list(reversed(out))
    def fetch_bars(self, symbol, timeframe="1min", limit=100):
        forming = self.now.replace(second=0, microsecond=0)
        return self._bars(symbol, timeframe, forming - timedelta(minutes=limit - 1), forming)
    def fetch_bars_range(self, symbol, timeframe, start, end):
        return self._bars(symbol, timeframe, start, end)

NOW = at("2026-09-28T00:30:30")                                   # Monday, weekend inside 5000 bars
r = update_instrument(Provider(NOW), "OFF/USD", "1min", now=NOW, initial_bars=3000)
assert r.offsession > 1400, r.offsession                          # the whole weekend was skipped
with get_connection() as c:
    rows = [datetime.fromisoformat(x[0]).astimezone(UTC) for x in c.execute(
        "SELECT bar_time FROM raw_bars WHERE symbol='OFF/USD'")]
assert rows and all(bar_in_session(t, m) for t in rows), "an off-session bar was stored"
assert r.saved + r.offsession + 1 >= r.fetched - 1                # accounting: fetched = saved + skipped (+ forming)
from src.data_update import format_report
assert "mimo obchodni dobu preskoceno" in format_report([r], NOW)

# ---------------------------------------------------------------- 3. quarantine of already stored bars
for sym in ("QQ/USD", "RR/USD"):
    ins = [at("2026-09-25T20:57") + timedelta(minutes=i) for i in range(3)]                     # Fri 20:57-20:59
    off = [at("2026-09-26T21:34") + timedelta(minutes=i) for i in range(40)]                    # Saturday
    off += [at("2026-09-27T20:50") + timedelta(minutes=i) for i in range(10)]                   # Sunday before the open
    ins += [at("2026-09-27T21:00") + timedelta(minutes=i) for i in range(3)]                    # Sunday open
    save_raw_bars([bar(sym, t) for t in ins + off])
save_raw_bar(bar("QQ/USD", at("2026-09-26T21:34"), tf="4h", source=DERIVED_SOURCE))            # derived: must survive
save_raw_bar(bar("QQ/USD", at("2026-09-26T12:00"), tf="1min", source="OtherSource"))          # other source: must survive

q = load_script()
dry = q.quarantine(apply=False)
assert dry["found"] == 100 and dry["moved"] == 0 and dry["per_symbol"] == {"QQ/USD": 50, "RR/USD": 50}, dry
with get_connection() as c:
    assert c.execute("SELECT COUNT(*) FROM raw_bars WHERE symbol='QQ/USD'").fetchone()[0] == 58     # 56 provider + derived + other
assert not BACKUP_DIR.exists() or not list(BACKUP_DIR.glob("*quarantine*")), "dry run must not back up or change anything"

done = q.quarantine(apply=True)
assert done["moved"] == 100 and done["backup"]
assert sqlite3.connect(done["backup"]).execute("PRAGMA integrity_check").fetchone()[0] == "ok"
with get_connection() as c:
    assert c.execute("SELECT COUNT(*) FROM raw_bars WHERE symbol='QQ/USD' AND source='TwelveData'").fetchone()[0] == 6      # only the in-session bars remain
    assert c.execute("SELECT COUNT(*) FROM raw_bars WHERE symbol='QQ/USD' AND source=?", (DERIVED_SOURCE,)).fetchone()[0] == 1
    assert c.execute("SELECT COUNT(*) FROM raw_bars WHERE symbol='QQ/USD' AND source='OtherSource'").fetchone()[0] == 1
    parked = c.execute("SELECT COUNT(*), MIN(reason) FROM raw_bars_offsession").fetchone()
    assert tuple(parked) == (100, "OUTSIDE_TRADING_SESSION"), tuple(parked)
    sample = c.execute("SELECT symbol, bar_time, open, close, source, quarantined_at FROM raw_bars_offsession "
                       "WHERE symbol='QQ/USD' ORDER BY bar_time LIMIT 1").fetchone()
    assert sample["open"] == "1.1" and sample["source"] == "TwelveData" and sample["quarantined_at"]

# idempotent
again = q.quarantine(apply=True)
assert again["found"] == 0 and again["moved"] == 0

# after the move the weekend is one clean MARKET_CLOSED gap, nothing missing
gaps = detect_gaps("QQ/USD", "1min", "TwelveData", 1000)
assert [g["status"] for g in gaps] == ["MARKET_CLOSED"], gaps

# 4. a failing move leaves everything as it was (count mismatch -> rollback)
save_raw_bars([bar("ZZ/USD", at("2026-09-26T22:00") + timedelta(minutes=i)) for i in range(5)])
original = q._ensure_table
def broken(connection):
    original(connection)
    connection.execute("CREATE TRIGGER IF NOT EXISTS t_stop BEFORE DELETE ON raw_bars BEGIN SELECT RAISE(IGNORE); END")
    return original(connection)
q._ensure_table = broken
try:
    q.quarantine(apply=True)
except RuntimeError:
    pass
else:
    raise AssertionError("mismatch not detected")
finally:
    q._ensure_table = original
with get_connection() as c:
    assert c.execute("SELECT COUNT(*) FROM raw_bars WHERE symbol='ZZ/USD'").fetchone()[0] == 5, "rollback failed"
    assert c.execute("SELECT COUNT(*) FROM raw_bars_offsession WHERE symbol='ZZ/USD'").fetchone()[0] == 0

print("=" * 60)
print("B11 OFF-SESSION BARS")
print("=" * 60)
print("SESSION HELPER (1min, 4h, EDGES): PASS")
print("UPDATE NEVER STORES OFF-SESSION BARS, COUNTS THEM: PASS")
print("QUARANTINE DRY RUN CHANGES NOTHING: PASS")
print("QUARANTINE MOVES ONLY PROVIDER BARS, BACKUP VERIFIED: PASS")
print("DERIVED AND OTHER-SOURCE BARS UNTOUCHED: PASS")
print("IDEMPOTENT, WEEKEND BECOMES ONE MARKET_CLOSED GAP: PASS")
print("FAILED MOVE ROLLS BACK COMPLETELY: PASS")
print("RESULT: PASS")
print("=" * 60)
