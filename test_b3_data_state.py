"""Block B3 - data states (CURRENT / CLOSED / STALE / MISSING / UNVERIFIED)."""

import os
import tempfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="fxbot_b3_")

# default tolerance is 240 s (120 s settle + 120 s provider lag); the
# scenarios below were designed for 120 s, so pin it for them
os.environ.pop("DATA_STATE_LAG_TOLERANCE_SECONDS", None)

from src.data_state import (
    lag_tolerance_seconds,
    DataState,
    classify,
    count_expected_bars,
    expected_last_bar_open,
    get_status,
)
from src.database import initialize_database
from src.models import RawBar
from src.storage import save_raw_bar

UTC = timezone.utc

assert lag_tolerance_seconds() == 240.0, "default tolerance = settle + provider lag"
os.environ["DATA_STATE_LAG_TOLERANCE_SECONDS"] = "120"
assert lag_tolerance_seconds() == 120.0


def at(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


def state(latest, now, tf="1min"):
    return classify("X/Y", tf, at(latest) if latest else None, at(now))


# ---- expected bar --------------------------------------------------
# Wednesday 10:00:30: newest CLOSED bar opened 09:59
assert expected_last_bar_open(at("2026-09-30T10:00:30"), "1min") == at("2026-09-30T09:59")
assert expected_last_bar_open(at("2026-09-30T10:00:00"), "1min") == at("2026-09-30T09:59")
assert expected_last_bar_open(at("2026-09-30T10:07:00"), "5min") == at("2026-09-30T10:00")
assert expected_last_bar_open(at("2026-09-30T10:07:00"), "1h") == at("2026-09-30T09:00")
# Saturday: last bar of the previous session (Friday 20:59Z in summer)
assert expected_last_bar_open(at("2026-09-26T12:00:00"), "1min") == at("2026-09-25T20:59")
assert expected_last_bar_open(at("2026-09-26T12:00:00"), "5min") == at("2026-09-25T20:55")
# winter Saturday
assert expected_last_bar_open(at("2026-12-05T12:00:00"), "1min") == at("2026-12-04T21:59")

# ---- CURRENT -------------------------------------------------------
assert state("2026-09-30T09:59", "2026-09-30T10:00:20").state == DataState.CURRENT
assert state("2026-09-30T09:59", "2026-09-30T10:00:59").state == DataState.CURRENT
# provider lag: newest closed bar (09:59) not stored yet, closed 60 s ago
s = state("2026-09-30T09:58", "2026-09-30T10:00:59")
assert s.state == DataState.CURRENT and "lag" in s.reason, s
s = state("2026-09-30T09:58", "2026-09-30T10:01:00")     # 09:59 closed 60 s ago
assert s.state == DataState.CURRENT, s
s = state("2026-09-30T09:58", "2026-09-30T10:02:00")     # exactly at tolerance
assert s.state == DataState.CURRENT, s
assert state("2026-09-30T09:58", "2026-09-30T10:02:01").state == DataState.STALE
# 5min bar
assert state("2026-09-30T10:00", "2026-09-30T10:07:00", "5min").state == DataState.CURRENT

# ---- STALE ---------------------------------------------------------
s = state("2026-09-30T09:40", "2026-09-30T10:00:20")
assert s.state == DataState.STALE and s.missing_bars == 19, s
s = state("2026-09-30T09:58", "2026-09-30T10:05:00")     # beyond the lag tolerance
assert s.state == DataState.STALE, s
assert s.age_seconds == (at("2026-09-30T10:05:00") - at("2026-09-30T09:59")).total_seconds()

# ---- CLOSED (weekend) - never CURRENT ------------------------------
s = state("2026-09-25T20:59", "2026-09-26T12:00")
assert s.state == DataState.CLOSED and s.market_open is False, s
s = state("2026-09-25T20:59", "2026-09-27T20:30")         # Sunday before the open
assert s.state == DataState.CLOSED, s
# weekend, but data ends earlier than the last bar of the session -> STALE
s = state("2026-09-25T18:00", "2026-09-26T12:00")
assert s.state == DataState.STALE, s
assert s.missing_bars == count_expected_bars(
    at("2026-09-25T18:01"), at("2026-09-25T20:59"), timedelta(minutes=1)
) == 179

# ---- session just re-opened: Friday data must NOT look current -----
s = state("2026-09-25T20:59", "2026-09-27T21:00:30")
assert s.market_open is True
assert s.state == DataState.CLOSED and "re-opened" in s.reason, s
# a minute later the first Sunday bar (21:00) has closed
assert state("2026-09-27T21:00", "2026-09-27T21:01:20").state == DataState.CURRENT

# ---- MISSING / UNVERIFIED -----------------------------------------
assert state(None, "2026-09-30T10:00").state == DataState.MISSING
assert state("2026-09-30T10:00", "2026-09-30T10:00:30").state == DataState.UNVERIFIED  # not closed yet
assert state("2026-09-30T10:30", "2026-09-30T10:00:30").state == DataState.UNVERIFIED  # future
assert classify("X/Y", "1min", datetime(2026, 9, 30, 9, 59), at("2026-09-30T10:00")).state == DataState.UNVERIFIED

# ---- guards --------------------------------------------------------
try:
    classify("X/Y", "1min", None, datetime(2026, 9, 30, 10, 0))
except ValueError:
    pass
else:
    raise AssertionError("naive now accepted")

# ---- database integration ------------------------------------------
initialize_database()


def bar(when):
    return RawBar("DB/TEST", "1min", when, when + timedelta(minutes=2),
                  Decimal("1"), Decimal("2"), Decimal("1"), Decimal("1.5"), "TwelveData")


assert get_status("DB/TEST", "1min", now=at("2026-09-30T10:00")).state == DataState.MISSING
for minute in range(0, 4):
    assert save_raw_bar(bar(at("2026-09-30T09:56") + timedelta(minutes=minute)))
st = get_status("DB/TEST", "1min", now=at("2026-09-30T10:00:20"))
assert st.state == DataState.CURRENT and st.latest_bar_open == at("2026-09-30T09:59"), st
st = get_status("DB/TEST", "1min", now=at("2026-09-30T10:30:00"))
assert st.state == DataState.STALE and st.missing_bars == 30, st

# CONFLICT is reserved, not produced yet
assert DataState.CONFLICT.value == "CONFLICT"

print("=" * 60)
print("B3 DATA STATES")
print("=" * 60)
print("EXPECTED LAST CLOSED BAR (INCL. WEEKEND): PASS")
print("CURRENT / PROVIDER LAG: PASS")
print("STALE + MISSING BAR COUNT: PASS")
print("WEEKEND = CLOSED, NEVER CURRENT: PASS")
print("SESSION RE-OPEN NOT SHOWN AS CURRENT: PASS")
print("MISSING / UNVERIFIED / GUARDS: PASS")
print("DATABASE INTEGRATION: PASS")
print("RESULT: PASS")
print("=" * 60)
