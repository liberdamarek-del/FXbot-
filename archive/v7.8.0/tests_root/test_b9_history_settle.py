"""Block B9 - settle delay before storing a bar, deep history (--days), sizes."""

import os
import tempfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="fxbot_b9_")
os.environ.pop("BAR_SETTLE_SECONDS", None)
os.environ["DATA_STATE_LAG_TOLERANCE_SECONDS"] = "240"

from src.data_state import DataState, get_earliest_bar_open, get_status
from src.data_update import (
    DEFAULT_INITIAL_BARS,
    DEFAULT_MAX_BARS_PER_CALL,
    format_report,
    settle_seconds,
    update_instrument,
)
from src.database import get_connection, initialize_database
from src.gap_detector import timeframe_delta
from src.market_session import is_fx_market_open
from src.models import RawBar
from src.storage import save_raw_bar

UTC = timezone.utc
initialize_database()


def at(text):
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


class Provider:
    """Serves 1min bars for open-market minutes; can be limited in depth."""

    def __init__(self, now, oldest=None):
        self.now, self.oldest, self.calls = now, oldest, []

    def _bars(self, symbol, timeframe, start, end):
        interval, current, out = timeframe_delta(timeframe), start, []
        while current <= end:
            if (is_fx_market_open(current) and current <= self.now
                    and (self.oldest is None or current >= self.oldest)):
                out.append(RawBar(symbol, timeframe, current, self.now, Decimal("1.1"),
                                  Decimal("1.2"), Decimal("1.0"), Decimal("1.1"), "TwelveData"))
            current += interval
        return list(reversed(out))

    def fetch_bars(self, symbol, timeframe="1min", limit=100):
        self.calls.append(("latest", limit))
        forming = self.now.replace(second=0, microsecond=0)
        return self._bars(symbol, timeframe, forming - timedelta(days=8), forming)[:limit]

    def fetch_bars_range(self, symbol, timeframe, start, end):
        if end <= start:
            raise ValueError("end must be after start")
        self.calls.append(("range", start, end))
        return self._bars(symbol, timeframe, start, end)


def count(symbol):
    with get_connection() as c:
        return c.execute("SELECT COUNT(*) FROM raw_bars WHERE symbol=? AND timeframe='1min'", (symbol,)).fetchone()[0]


def newest(symbol):
    with get_connection() as c:
        return c.execute("SELECT MAX(bar_time) FROM raw_bars WHERE symbol=? AND timeframe='1min'", (symbol,)).fetchone()[0]


# ------------------------------------------------ 1. defaults
assert settle_seconds() == 120.0
assert DEFAULT_MAX_BARS_PER_CALL == 4500 and DEFAULT_MAX_BARS_PER_CALL <= 5000
assert DEFAULT_INITIAL_BARS == 5000

# ------------------------------------------------ 2. settle delay: a bar that closed only seconds ago is NOT stored
NOW = at("2026-09-30T10:05:30")
provider = Provider(NOW)
r = update_instrument(provider, "SET/USD", "1min", now=NOW, initial_bars=60)
# bars close at :01 .. ; settled = closed at least 120 s ago -> last stored opens 10:02 (closed 10:03:00, 150 s ago)
assert newest("SET/USD") == "2026-09-30T10:02:00+00:00", newest("SET/USD")
assert r.after.state == DataState.CURRENT, r.after           # 10:03/10:04 closed < 240 s ago: lag, not overdue
# 10:03 closed 10:04:00 -> only 90 s ago: not settled yet; 10:04 closed 30 s ago; 10:05 still forming
with get_connection() as c:
    assert c.execute("SELECT COUNT(*) FROM raw_bars WHERE symbol='SET/USD' AND bar_time>='2026-09-30T10:03:00+00:00'").fetchone()[0] == 0

# a little later the same bars settle and are picked up
LATER = at("2026-09-30T10:07:10")
provider = Provider(LATER)
r = update_instrument(provider, "SET/USD", "1min", now=LATER)
assert newest("SET/USD") == "2026-09-30T10:04:00+00:00", newest("SET/USD")    # 10:05 closed 10:06:00 = 70 s ago -> not yet
assert r.saved == 2 and r.calls == 1

# explicit override
provider = Provider(LATER)
r = update_instrument(provider, "SET/USD", "1min", now=LATER, settle_seconds_override=0)
assert newest("SET/USD") == "2026-09-30T10:06:00+00:00"

# ------------------------------------------------ 3. initial load has NO lower bound (weekend in the window)
os.environ["BAR_SETTLE_SECONDS"] = "0"
MON = at("2026-09-28T09:00:30")
provider = Provider(MON)
r = update_instrument(provider, "WKI/USD", "1min", now=MON, initial_bars=1500)
assert r.saved == 1499, r.saved                 # 1500 fetched (one still forming) reach back over the weekend
assert get_earliest_bar_open("WKI/USD", "1min") < at("2026-09-27T00:00"), "bars from before the weekend must be kept"

# ------------------------------------------------ 4. deep history
NOW2 = at("2026-09-30T12:00:30")
provider = Provider(NOW2)
update_instrument(provider, "HIS/USD", "1min", now=NOW2, initial_bars=300)
first_before = get_earliest_bar_open("HIS/USD", "1min")

provider = Provider(NOW2)
r = update_instrument(provider, "HIS/USD", "1min", now=NOW2, history_days=7, max_bars_per_call=3000)
earliest = get_earliest_bar_open("HIS/USD", "1min")
assert earliest <= at("2026-09-23T12:00") + timedelta(days=0, minutes=1), earliest
assert earliest < first_before
assert r.history_saved > 5000, r.history_saved
assert r.history_limit_reached is False
# every chunk lies in an open-market segment: no call for the weekend
for call in provider.calls:
    assert call[0] == "range"
    assert is_fx_market_open(call[1]) and is_fx_market_open(call[2]), call
# contiguous: no MISSING gap in what was stored (weekends = closed)
from src.gap_detector import detect_gaps
assert [g for g in detect_gaps("HIS/USD", "1min", "TwelveData", 20000) if g["status"] == "MISSING_DATA"] == []

# idempotent: asking again for the same depth costs nothing
provider = Provider(NOW2)
r = update_instrument(provider, "HIS/USD", "1min", now=NOW2, history_days=7, max_bars_per_call=3000)
assert provider.calls == [] and r.history_saved == 0

# ------------------------------------------------ 5. provider has less history than requested
NOW3 = at("2026-09-30T12:00:30")
provider = Provider(NOW3, oldest=at("2026-09-29T00:00"))
update_instrument(provider, "SHORT/USD", "1min", now=NOW3, initial_bars=300)
provider = Provider(NOW3, oldest=at("2026-09-29T00:00"))
r = update_instrument(provider, "SHORT/USD", "1min", now=NOW3, history_days=10, max_bars_per_call=3000)
assert r.history_limit_reached is True and r.error is None
assert get_earliest_bar_open("SHORT/USD", "1min") >= at("2026-09-29T00:00")
assert "poskytovatel nema starsi data" in format_report([r], NOW3)

# ------------------------------------------------ 6. call limit: nearest chunks first, rest reported
provider = Provider(NOW3)
update_instrument(provider, "CAP/USD", "1min", now=NOW3, initial_bars=300)
provider = Provider(NOW3)
r = update_instrument(provider, "CAP/USD", "1min", now=NOW3, history_days=30,
                      max_bars_per_call=1000, history_max_calls=3)
assert len(provider.calls) == 3, len(provider.calls)
assert r.history_skipped_bars > 0
assert r.history_saved == 3000, r.history_saved
# the stored history is contiguous with the existing data (nearest chunks were fetched)
assert [g for g in detect_gaps("CAP/USD", "1min", "TwelveData", 20000) if g["status"] == "MISSING_DATA"] == []
assert "nestazeno" in format_report([r], NOW3)

# ------------------------------------------------ 7. single-bar chunk in the history plan
os.environ["BAR_SETTLE_SECONDS"] = "0"
NOW4 = at("2026-09-30T12:00:30")
provider = Provider(NOW4)
save_raw_bar(RawBar("ONE/USD", "1min", at("2026-09-30T11:30"), NOW4, Decimal("1"), Decimal("2"), Decimal("1"), Decimal("1.5"), "TwelveData"))
r = update_instrument(provider, "ONE/USD", "1min", now=NOW4, history_days=1, max_bars_per_call=2)
assert r.error is None, r.error

print("=" * 60)
print("B9 SETTLE DELAY / DEEP HISTORY")
print("=" * 60)
print("DEFAULTS (SETTLE 120 s, 4500 BARS / CALL, 5000 INITIAL): PASS")
print("FRESHLY CLOSED BAR NOT STORED UNTIL SETTLED: PASS")
print("INITIAL LOAD KEEPS BARS ACROSS A WEEKEND: PASS")
print("DEEP HISTORY: CONTIGUOUS, NO WEEKEND CALLS, IDEMPOTENT: PASS")
print("PROVIDER HAS LESS HISTORY -> REPORTED: PASS")
print("CALL LIMIT -> NEAREST CHUNKS FIRST, REST REPORTED: PASS")
print("RESULT: PASS")
print("=" * 60)
