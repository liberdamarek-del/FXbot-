"""Block B8 - deriving 5min / 15min / 1h from stored 1-minute bars."""

import csv
import os
import tempfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="fxbot_b8_")

from src.database import get_connection, initialize_database
from src.models import RawBar
from src.resample import DERIVED_SOURCE, derive_symbol, derive_timeframe
from src.storage import save_raw_bar

UTC = timezone.utc
ROOT = Path(__file__).resolve().parent
initialize_database()


def at(text):
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


def minute(symbol, when, o, h, l, c, received=None):
    return RawBar(symbol, "1min", when, received or when + timedelta(minutes=3),
                  Decimal(o), Decimal(h), Decimal(l), Decimal(c), "TwelveData")


def derived(symbol, tf):
    with get_connection() as c:
        return c.execute(
            "SELECT * FROM raw_bars WHERE symbol=? AND timeframe=? AND source=? ORDER BY bar_time",
            (symbol, tf, DERIVED_SOURCE),
        ).fetchall()


# ---------------------------------------------------------------- 1. OHLC of one window
# 10:00 .. 10:04: open of the FIRST minute, close of the LAST, extreme high/low
data = [("10:00", "1.10", "1.13", "1.09", "1.12"),
        ("10:01", "1.12", "1.14", "1.11", "1.13"),
        ("10:02", "1.13", "1.15", "1.05", "1.06"),   # lowest low
        ("10:03", "1.06", "1.20", "1.06", "1.18"),   # highest high
        ("10:04", "1.18", "1.19", "1.16", "1.17")]
for t, o, h, l, c in data:
    assert save_raw_bar(minute("AAA/USD", at(f"2026-09-30T{t}"), o, h, l, c))

r = derive_timeframe("AAA/USD", "5min")
assert (r.created, r.incomplete, r.pending) == (1, 0, 0), r
bar = derived("AAA/USD", "5min")[0]
assert bar["bar_time"] == "2026-09-30T10:00:00+00:00"
assert (bar["open"], bar["high"], bar["low"], bar["close"]) == ("1.10", "1.20", "1.05", "1.17")
assert bar["source"] == DERIVED_SOURCE and bar["timeframe"] == "5min"
assert datetime.fromisoformat(bar["received_at"]) == at("2026-09-30T10:07"), "received_at = latest component"

# ---------------------------------------------------------------- 2. idempotent
again = derive_timeframe("AAA/USD", "5min")
assert (again.created, again.existing) == (0, 1)
assert len(derived("AAA/USD", "5min")) == 1

# ---------------------------------------------------------------- 3. incomplete window is NEVER turned into a bar
for m in (5, 6, 8, 9):                                      # 10:07 missing
    assert save_raw_bar(minute("AAA/USD", at(f"2026-09-30T10:{m:02d}"), "1.2", "1.3", "1.1", "1.2"))
for m in range(10, 14):                                     # newest window 10:10.. has only 4 of 5
    assert save_raw_bar(minute("AAA/USD", at(f"2026-09-30T10:{m}"), "1.2", "1.3", "1.1", "1.2"))
r = derive_timeframe("AAA/USD", "5min")
assert r.created == 0 and r.incomplete == 1 and r.pending == 1, r
assert len(derived("AAA/USD", "5min")) == 1, "no partial bar may exist"

# the hole gets filled later (backfill) -> the window is picked up automatically
assert save_raw_bar(minute("AAA/USD", at("2026-09-30T10:07"), "1.2", "1.35", "1.1", "1.2"))
r = derive_timeframe("AAA/USD", "5min")
assert r.created == 1 and r.incomplete == 0, r
late = [b for b in derived("AAA/USD", "5min") if b["bar_time"].startswith("2026-09-30T10:05")][0]
assert late["high"] == "1.35"

# ---------------------------------------------------------------- 4. 15min and 1h
for m in range(14, 60):                                     # complete the hour 10:xx
    save_raw_bar(minute("AAA/USD", at(f"2026-09-30T10:{m:02d}"), "1.2", "1.3", "1.1", "1.2"))
for m in range(0, 5):                                       # 10:00-10:04 exist already
    pass
res = {x.timeframe: x for x in derive_symbol("AAA/USD", ["5min", "15min", "1h"])}
assert res["1h"].created == 1, res["1h"]
assert res["15min"].created == 4, res["15min"]
hour = derived("AAA/USD", "1h")[0]
assert hour["bar_time"] == "2026-09-30T10:00:00+00:00" and hour["open"] == "1.10"
assert hour["high"] == "1.35" and hour["low"] == "1.05"

# ---------------------------------------------------------------- 5. weekend: windows at the session edges
# Friday last bars 20:55-20:59 (summer) form a COMPLETE 5min window; 21:00.. is closed
for m in range(55, 60):
    save_raw_bar(minute("WK/USD", at(f"2026-09-25T20:{m}"), "1", "2", "1", "1.5"))
for m in range(0, 5):
    save_raw_bar(minute("WK/USD", at(f"2026-09-27T21:0{m}"), "1", "2", "1", "1.5"))   # Sunday open
r = derive_timeframe("WK/USD", "5min")
assert r.created == 2 and r.incomplete == 0, r
times = [b["bar_time"] for b in derived("WK/USD", "5min")]
assert times == ["2026-09-25T20:55:00+00:00", "2026-09-27T21:00:00+00:00"], times

# ---------------------------------------------------------------- 5b. history starting inside a window is an EDGE, not a hole
for m in (2, 3, 4, 5, 6, 7, 8, 9):                                   # data begins at 10:02
    assert save_raw_bar(minute("EDGE/USD", at(f"2026-09-30T10:{m:02d}"), "1", "2", "1", "1.5"))
r = derive_timeframe("EDGE/USD", "5min")
assert (r.created, r.edge, r.incomplete) == (1, 1, 0), r            # only 10:05 is complete
assert [b["bar_time"][11:16] for b in derived("EDGE/USD", "5min")] == ["10:05"]
# older bars arrive later (deep history): a normal run does NOT go back that far ...
for m in (0, 1):
    assert save_raw_bar(minute("EDGE/USD", at(f"2026-09-30T10:{m:02d}"), "1", "2", "1", "1.5"))
# make the derived start clearly later than the raw start, like after a long run
for m in range(10, 40):
    save_raw_bar(minute("EDGE/USD", at(f"2026-09-30T10:{m:02d}"), "1", "2", "1", "1.5"))
derive_timeframe("EDGE/USD", "5min")
assert derived("EDGE/USD", "5min")[0]["bar_time"][11:16] in ("10:00", "10:05")
# ... but a full scan builds everything, including the older window
from src.resample import FULL_SCAN
derive_timeframe("EDGE/USD", "5min", since=FULL_SCAN)
assert derived("EDGE/USD", "5min")[0]["bar_time"][11:16] == "10:00"
assert len(derived("EDGE/USD", "5min")) == 8                         # 10:00 .. 10:35

# ---------------------------------------------------------------- 6. guards
for bad in ("1min", "7min"):
    try:
        derive_timeframe("AAA/USD", bad)
    except ValueError:
        pass
    else:
        raise AssertionError(f"{bad} accepted")
assert derive_timeframe("NONE/USD", "5min").created == 0
try:
    derive_timeframe("AAA/USD", "5min", since=datetime(2026, 9, 30, 10, 0))
except ValueError:
    pass
else:
    raise AssertionError("naive since accepted")

# ---------------------------------------------------------------- 7. provider bars are untouched
with get_connection() as c:
    assert c.execute("SELECT COUNT(*) FROM raw_bars WHERE source='TwelveData' AND timeframe!='1min'").fetchone()[0] == 0

# ---------------------------------------------------------------- 8. REAL DATA: derived vs the provider's own 5min bars
# Fixture 1 = 865 real 1min bars, fixture 2 = the 4 real 5min bars of the provider.
import sys
sys.path.insert(0, str(ROOT))
from tests.seed import seed_database

seed_database()

rows = list(csv.DictReader(open(ROOT / "tests/fixtures/usdjpy_5min_provider_20260929T0835_0850.csv", newline="")))
assert len(rows) == 4
derive_timeframe("USD/JPY", "5min")
mine = {b["bar_time"]: b for b in derived("USD/JPY", "5min")}
assert len(mine) > 150, len(mine)

same, different = [], []
for row in rows:
    d = mine[row["bar_time"]]
    ok = all(Decimal(d[k]) == Decimal(row[k]) for k in ("open", "high", "low", "close"))
    (same if ok else different).append(row["bar_time"][11:16])

# three provider bars agree exactly with the derived ones; the 08:45 bar was
# fetched only 12 s after it closed and lacks its last minute (08:49)
assert same == ["08:35", "08:40", "08:50"], (same, different)
assert different == ["08:45"], different
provider_0845 = [r for r in rows if r["bar_time"].startswith("2026-09-29T08:45")][0]
mine_0845 = mine[provider_0845["bar_time"]]
assert (Decimal(mine_0845["open"]), Decimal(mine_0845["high"])) == (Decimal(provider_0845["open"]), Decimal(provider_0845["high"]))
with get_connection() as c:
    last_minute = c.execute("SELECT low, close FROM raw_bars WHERE symbol='USD/JPY' AND timeframe='1min' "
                            "AND source='TwelveData' AND bar_time='2026-09-29T08:49:00+00:00'").fetchone()
assert Decimal(mine_0845["close"]) == Decimal(last_minute["close"]), "derived close = close of 08:49"
assert Decimal(mine_0845["low"]) <= Decimal(last_minute["low"])
assert Decimal(provider_0845["close"]) != Decimal(mine_0845["close"]), "provider bar lacked minute 08:49"

print("=" * 60)
print("B8 DERIVED TIMEFRAMES")
print("=" * 60)
print("OHLC OF A WINDOW: PASS")
print("IDEMPOTENT: PASS")
print("INCOMPLETE WINDOW NEVER BECOMES A BAR, LATE FILL PICKED UP: PASS")
print("15min AND 1h: PASS")
print("SESSION EDGES (FRIDAY CLOSE / SUNDAY OPEN): PASS")
print("HISTORY START INSIDE A WINDOW = EDGE, FULL SCAN AFTER DEEP HISTORY: PASS")
print("SEPARATE SOURCE TAG, PROVIDER DATA UNTOUCHED: PASS")
print("REAL DATA: 3 OF 4 PROVIDER 5min BARS IDENTICAL, 4th WAS PRELIMINARY: PASS")
print("RESULT: PASS")
print("=" * 60)
