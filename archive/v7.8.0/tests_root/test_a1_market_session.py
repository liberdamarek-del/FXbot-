"""Block A1 - FX market session must follow New York 17:00 (DST aware)."""

import os
import tempfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal

# Isolated database for the gap-detection part.
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="fxbot_a1_")

from src.database import initialize_database
from src.gap_detector import detect_gaps
from src.market_session import is_fx_market_open, us_dst_bounds_utc
from src.models import RawBar
from src.storage import save_raw_bar

UTC = timezone.utc


def at(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


# ------------------------------------------------------------------
# 1. Weekly boundaries, summer (EDT, UTC-4): 21:00 UTC
# ------------------------------------------------------------------
cases = [
    ("2026-09-25T20:59", True),   # Friday, last open minute (summer)
    ("2026-09-25T21:00", False),  # Friday close 17:00 EDT
    ("2026-09-25T22:00", False),
    ("2026-09-26T12:00", False),  # Saturday
    ("2026-09-27T20:59", False),  # Sunday before open (summer)
    ("2026-09-27T21:00", True),   # Sunday open 17:00 EDT
    ("2026-09-27T21:59", True),   # was wrongly False with the 22:00 rule
    ("2026-09-28T02:00", True),
    # winter (EST, UTC-5): 22:00 UTC
    ("2026-12-04T21:59", True),
    ("2026-12-04T22:00", False),
    ("2026-12-06T21:59", False),
    ("2026-12-06T22:00", True),
    # DST start weekend 2026 (clocks change Sunday 2026-03-08)
    ("2026-03-06T21:59", True),   # Friday still EST: closes 22:00Z
    ("2026-03-06T22:00", False),
    ("2026-03-08T20:59", False),  # Sunday after switch: opens 21:00Z
    ("2026-03-08T21:00", True),
    # DST end weekend 2026 (clocks change Sunday 2026-11-01)
    ("2026-10-30T20:59", True),   # Friday still EDT: closes 21:00Z
    ("2026-10-30T21:00", False),
    ("2026-11-01T21:59", False),  # Sunday after switch: opens 22:00Z
    ("2026-11-01T22:00", True),
]

for text, expected in cases:
    actual = is_fx_market_open(at(text))
    assert actual == expected, f"{text}Z expected={expected} actual={actual}"

start, end = us_dst_bounds_utc(2026)
assert start == at("2026-03-08T07:00")
assert end == at("2026-11-01T06:00")

# aware timestamps in other timezones are converted correctly
prague_summer = datetime.fromisoformat("2026-09-27T23:00:00+02:00")  # 21:00Z
assert is_fx_market_open(prague_summer) is True

try:
    is_fx_market_open(datetime(2026, 9, 27, 21, 0))
except ValueError:
    pass
else:
    raise AssertionError("naive timestamp was not rejected")

# ------------------------------------------------------------------
# 2. Optional cross-check against the system tz database
# ------------------------------------------------------------------
zoneinfo_status = "SKIPPED (no tz database on this device)"
try:
    from zoneinfo import ZoneInfo

    ny = ZoneInfo("America/New_York")

    def reference(ts: datetime) -> bool:
        local = ts.astimezone(ny)
        minute = local.hour * 60 + local.minute
        if local.weekday() == 5:
            return False
        if local.weekday() == 6 and minute < 17 * 60:
            return False
        if local.weekday() == 4 and minute >= 17 * 60:
            return False
        return True

    ts = at("2024-01-01T00:00")
    stop = at("2032-01-01T00:00")
    checked = 0
    while ts < stop:
        assert is_fx_market_open(ts) == reference(ts), ts.isoformat()
        checked += 1
        ts += timedelta(minutes=15)
    zoneinfo_status = f"PASS ({checked} timestamps, 2024-2031)"
except Exception as exc:  # tz database not available
    if type(exc).__name__ not in {"ZoneInfoNotFoundError", "ImportError"}:
        raise

# ------------------------------------------------------------------
# 3. Gap detector: a normal summer weekend is MARKET_CLOSED, a real
#    hole inside the trading week is still MISSING_DATA
# ------------------------------------------------------------------
initialize_database()


def bar(symbol: str, when: datetime) -> RawBar:
    return RawBar(
        symbol=symbol,
        timeframe="1min",
        bar_time=when,
        received_at=when + timedelta(minutes=2),
        open=Decimal("1.1"),
        high=Decimal("1.2"),
        low=Decimal("1.0"),
        close=Decimal("1.1"),
        source="TEST",
    )


# Weekend only: last Friday bar 20:59Z, first Sunday bar 21:00Z (summer).
for when in (
    at("2026-09-25T20:58"),
    at("2026-09-25T20:59"),
    at("2026-09-27T21:00"),
    at("2026-09-27T21:01"),
):
    assert save_raw_bar(bar("TEST/WEEKEND", when))

# Real hole inside the trading week: 10:02, 10:03, 10:04 missing.
for when in (
    at("2026-09-28T10:00"),
    at("2026-09-28T10:01"),
    at("2026-09-28T10:05"),
):
    assert save_raw_bar(bar("TEST/HOLE", when))

weekend = detect_gaps("TEST/WEEKEND", "1min", "TEST", 1000)
assert len(weekend) == 1, weekend
assert weekend[0]["status"] == "MARKET_CLOSED", weekend
assert weekend[0]["missing_bars"] == 2880

hole = detect_gaps("TEST/HOLE", "1min", "TEST", 1000)
assert len(hole) == 1, hole
assert hole[0]["status"] == "MISSING_DATA", hole
assert hole[0]["missing_bars"] == 3

print("=" * 60)
print("A1 MARKET SESSION (DST)")
print("=" * 60)
print(f"BOUNDARY CASES: PASS ({len(cases)})")
print(f"DST BOUNDS 2026: PASS ({start.isoformat()} / {end.isoformat()})")
print(f"ZONEINFO CROSS-CHECK: {zoneinfo_status}")
print("WEEKEND GAP = MARKET_CLOSED: PASS")
print("MID-WEEK HOLE = MISSING_DATA: PASS")
print("RESULT: PASS")
print("=" * 60)
