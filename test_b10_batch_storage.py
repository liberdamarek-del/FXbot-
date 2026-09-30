"""Block B10 - batch storage: one transaction, same result, all-or-nothing."""

import os
import tempfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="fxbot_b10_")

import src.database as database
import src.storage as storage
from src.database import get_connection, initialize_database
from src.models import RawBar
from src.storage import save_raw_bar, save_raw_bars

UTC = timezone.utc
initialize_database()
T0 = datetime(2026, 9, 30, 8, 0, tzinfo=UTC)


def bar(symbol, i, close="1.5"):
    t = T0 + timedelta(minutes=i)
    return RawBar(symbol, "1min", t, t + timedelta(minutes=3), Decimal("1"), Decimal("2"),
                  Decimal("1"), Decimal(close), "TwelveData")


def rows(symbol):
    with get_connection() as c:
        return [tuple(r) for r in c.execute(
            "SELECT bar_time, received_at, open, high, low, close, source FROM raw_bars "
            "WHERE symbol=? ORDER BY bar_time", (symbol,))]


# 1. empty batch
assert save_raw_bars([]) == (0, 0)

# 2. counts: new, duplicate, mixed; generators accepted
assert save_raw_bars(bar("B/USD", i) for i in range(100)) == (100, 0)
assert save_raw_bars([bar("B/USD", i) for i in range(100)]) == (0, 100)
assert save_raw_bars([bar("B/USD", i) for i in range(50, 150)]) == (50, 50)
assert len(rows("B/USD")) == 150

# 3. identical result to the one-by-one function
for i in range(150):
    save_raw_bar(bar("S/USD", i))
assert rows("S/USD") == [
    tuple(r) for r in rows("B/USD")
], "batch and single inserts must store identical rows"

# 4. nothing is overwritten (same key, different values)
assert save_raw_bars([bar("B/USD", 0, close="1.9")]) == (0, 1)
assert rows("B/USD")[0][5] == "1.5"

# 5. all-or-nothing: a broken element in the middle stores NOTHING
class Broken:
    symbol = "X/USD"

before = len(rows("A/USD"))
try:
    save_raw_bars([bar("A/USD", 1), bar("A/USD", 2), Broken(), bar("A/USD", 3)])
except AttributeError:
    pass
else:
    raise AssertionError("broken element accepted")
assert len(rows("A/USD")) == before == 0, "partial batch must be rolled back"

# 6. THE performance property: one commit for a whole batch
commits = {"n": 0}
original = storage.get_connection


def counting():
    connection = original()
    connection.set_trace_callback(
        lambda statement: commits.__setitem__(
            "n", commits["n"] + statement.strip().upper().startswith("COMMIT")
        )
    )
    return connection


storage.get_connection = counting
try:
    assert save_raw_bars([bar("C/USD", i) for i in range(2000)]) == (2000, 0)
    assert commits["n"] == 1, f"{commits['n']} commits for 2000 bars"

    commits["n"] = 0
    for i in range(20):
        save_raw_bar(bar("D/USD", i))
    assert commits["n"] == 20, "the single-bar function commits per bar (unchanged)"
finally:
    storage.get_connection = original

print("=" * 60)
print("B10 BATCH STORAGE")
print("=" * 60)
print("COUNTS (NEW / DUPLICATE / MIXED / EMPTY): PASS")
print("IDENTICAL TO ONE-BY-ONE INSERTS: PASS")
print("NEVER OVERWRITES: PASS")
print("ALL-OR-NOTHING: PASS")
print("ONE COMMIT FOR 2000 BARS: PASS")
print("RESULT: PASS")
print("=" * 60)
