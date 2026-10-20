"""Block B4 - on-demand catch-up: minimal API use, weekend handling, safety."""

import os
import tempfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="fxbot_b4_")
os.environ["BAR_SETTLE_SECONDS"] = "0"      # settle delay is tested in test_b9
os.environ["DATA_STATE_LAG_TOLERANCE_SECONDS"] = "120"

from src.data_state import DataState, get_status
from src.data_update import format_report, update_all, update_instrument
from src.database import get_connection, initialize_database
from src.gap_detector import detect_gaps, timeframe_delta
from src.market_session import is_fx_market_open
from src.models import RawBar
from src.rate_limiter import RateLimitExceeded
from src.storage import save_raw_bar

UTC = timezone.utc
initialize_database()


def at(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


class FakeProvider:
    """Behaves like the real provider: bars only while the market is open,
    the still-forming bar is included, range end must be after start."""

    def __init__(self, now: datetime, fail_after: int | None = None, bad_bar: datetime | None = None):
        self.now = now
        self.calls = []
        self.fail_after = fail_after
        self.bad_bar = bad_bar

    def _bar(self, symbol, timeframe, open_time):
        base = Decimal("157") + Decimal(open_time.hour) / 10
        high, low = base + Decimal("0.2"), base - Decimal("0.2")
        if self.bad_bar and open_time == self.bad_bar:
            high, low = base - Decimal("1"), base + Decimal("1")       # invalid: high < low
        return RawBar(symbol, timeframe, open_time, self.now, base, high, low, base, "TwelveData")

    def _open_times(self, timeframe, start, end):
        interval = timeframe_delta(timeframe)
        current, out = start, []
        while current <= end:
            if is_fx_market_open(current) and current <= self.now:
                out.append(current)
            current += interval
        return out

    def _check(self):
        self.calls.append(1)
        if self.fail_after is not None and len(self.calls) > self.fail_after:
            raise RuntimeError("provider unavailable")

    def fetch_bars(self, symbol, timeframe="1min", limit=100):
        self._check()
        interval = timeframe_delta(timeframe)
        seconds = int(interval.total_seconds())
        stamp = int(self.now.timestamp())
        forming = datetime.fromtimestamp(stamp - stamp % seconds, tz=UTC)
        # like the real provider: the latest `limit` AVAILABLE bars, even if
        # they are days old (weekend) - so look back far enough
        times = self._open_times(timeframe, forming - timedelta(days=6), forming)
        return [self._bar(symbol, timeframe, t) for t in reversed(times[-limit:])]

    def fetch_bars_range(self, symbol, timeframe, start, end):
        self._check()
        if end <= start:
            raise ValueError("end must be after start")
        return [self._bar(symbol, timeframe, t) for t in reversed(self._open_times(timeframe, start, end))]


def stored(symbol, timeframe):
    with get_connection() as c:
        return c.execute(
            "SELECT COUNT(*) FROM raw_bars WHERE symbol=? AND timeframe=?", (symbol, timeframe)
        ).fetchone()[0]


# ---------------------------------------------------------------- 1. empty DB
NOW = at("2026-09-30T10:00:30")
provider = FakeProvider(NOW)
r = update_instrument(provider, "AAA/USD", "1min", now=NOW, initial_bars=60)
assert r.before.state == DataState.MISSING
assert r.after.state == DataState.CURRENT, r.after
assert r.calls == 1 and r.saved == 59, (r.calls, r.saved)
assert r.fetched == 60 and r.closed == 59       # the still-forming bar is fetched but NOT stored
assert stored("AAA/USD", "1min") == r.saved
assert get_status("AAA/USD", "1min", now=NOW).latest_bar_open == at("2026-09-30T09:59")

# ---------------------------------------------------------------- 2. already current -> ZERO calls
provider = FakeProvider(NOW)
r = update_instrument(provider, "AAA/USD", "1min", now=NOW)
assert r.calls == 0 and provider.calls == [], "no API credit may be spent when data is complete"
assert r.before.state == DataState.CURRENT and r.after.state == DataState.CURRENT
assert r.saved == 0

# ---------------------------------------------------------------- 3. catch up 30 minutes: ONE call
LATER = at("2026-09-30T10:30:30")
provider = FakeProvider(LATER)
r = update_instrument(provider, "AAA/USD", "1min", now=LATER)
assert r.before.state == DataState.STALE and r.before.missing_bars == 30, r.before
assert r.calls == 1 and r.saved == 30, (r.calls, r.saved)
assert r.after.state == DataState.CURRENT
assert r.remaining_gaps == 0
assert r.skipped_bars == 0

# idempotent: running again changes nothing and costs nothing
provider = FakeProvider(LATER)
r = update_instrument(provider, "AAA/USD", "1min", now=LATER)
assert r.calls == 0 and r.saved == 0

# ---------------------------------------------------------------- 4. single missing bar (start == end)
provider = FakeProvider(at("2026-09-30T10:31:30"))
r = update_instrument(provider, "AAA/USD", "1min", now=at("2026-09-30T10:31:30"))
assert r.error is None, r.error
assert r.calls == 1 and r.saved == 1, (r.calls, r.saved)

# ---------------------------------------------------------------- 5. weekend: nothing to fetch
SAT = at("2026-09-26T12:00:00")
provider = FakeProvider(SAT)
r = update_instrument(provider, "WKE/USD", "1min", now=SAT, initial_bars=30)
assert r.after.state == DataState.CLOSED, r.after
assert r.saved == 30
assert get_status("WKE/USD", "1min", now=SAT).latest_bar_open == at("2026-09-25T20:59")
provider = FakeProvider(SAT)
r = update_instrument(provider, "WKE/USD", "1min", now=SAT)
assert provider.calls == [] and r.after.state == DataState.CLOSED

# ---------------------------------------------------------------- 6. across the weekend: gap is MARKET_CLOSED, not MISSING
MON = at("2026-09-28T09:00:30")
provider = FakeProvider(MON)
r = update_instrument(provider, "WKE/USD", "1min", now=MON, max_bars_per_call=500, max_calls=10)
assert r.after.state == DataState.CURRENT, r.after
assert r.remaining_gaps == 0, r.remaining_gaps
gaps = detect_gaps("WKE/USD", "1min", "TwelveData", 1000)
assert [g["status"] for g in gaps] == ["MARKET_CLOSED"], gaps
assert r.calls == 2, r.calls          # 12h of Sunday evening + Monday = 720 bars -> 2 chunks

# ---------------------------------------------------------------- 7. call limit: newest first, older part reported
LONG = at("2026-09-30T10:00:30")
for minute in range(0, 3):
    save_raw_bar(RawBar("LIM/USD", "1min", at("2026-09-28T10:00") + timedelta(minutes=minute),
                        NOW, Decimal("1"), Decimal("2"), Decimal("1"), Decimal("1.5"), "TwelveData"))
provider = FakeProvider(LONG)
r = update_instrument(provider, "LIM/USD", "1min", now=LONG, max_bars_per_call=100, max_calls=3)
assert r.calls == 3, r.calls
assert r.skipped_bars > 0
assert r.after.state == DataState.CURRENT, "newest data must be fetched first"
assert r.remaining_gaps >= 1, "the untouched older part must stay visible as a gap"
assert r.saved == 300, r.saved

# ---------------------------------------------------------------- 8. provider failure is recorded, others continue
NOW2 = at("2026-09-30T11:00:30")
failing = FakeProvider(NOW2, fail_after=0)
rs = update_all(failing, [("AAA/USD", "1min"), ("LIM/USD", "1min")], now=NOW2)
assert all(x.error and "provider unavailable" in x.error for x in rs)
assert all(x.after.state == DataState.STALE for x in rs)
with get_connection() as c:
    failed = c.execute("SELECT COUNT(*) FROM collector_runs WHERE status='FAILED'").fetchone()[0]
assert failed == 2

# ---------------------------------------------------------------- 9. budget exhaustion is reported as such
class ExhaustedProvider(FakeProvider):
    def _check(self):
        raise RateLimitExceeded("daily API budget used up (720/720 credits, UTC day)")

r = update_instrument(ExhaustedProvider(NOW2), "AAA/USD", "1min", now=NOW2)
assert r.budget_exhausted is True and r.after.state == DataState.STALE

# ---------------------------------------------------------------- 10. invalid bar is rejected, others saved
NOW3 = at("2026-09-30T12:00:30")
bad = at("2026-09-30T11:30")
provider = FakeProvider(NOW3, bad_bar=bad)
r = update_instrument(provider, "AAA/USD", "1min", now=NOW3)
assert r.rejected == 1, r.rejected
with get_connection() as c:
    assert c.execute("SELECT COUNT(*) FROM raw_bars WHERE symbol='AAA/USD' AND bar_time=?",
                     (bad.isoformat(),)).fetchone()[0] == 0

# ---------------------------------------------------------------- 11. audit rows + report text
with get_connection() as c:
    runs = c.execute("SELECT * FROM collector_runs WHERE symbol='AAA/USD' AND status='SUCCESS'").fetchall()
    assert runs and all(row["bars_fetched"] >= row["bars_closed"] >= row["bars_saved"] + row["bars_duplicate"] + row["bars_rejected"] for row in runs)

report = format_report(rs, NOW2, {"day_used": 3, "day_limit": 720})
assert "API kredity dnes: 3/720" in report and "CHYBA" in report and "problem" in report

# ---------------------------------------------------------------- 12. guards
for kwargs in ({"max_bars_per_call": 1}, {"max_calls": 0}):
    try:
        update_instrument(FakeProvider(NOW), "AAA/USD", "1min", now=NOW, **kwargs)
    except ValueError:
        pass
    else:
        raise AssertionError(f"bad argument accepted: {kwargs}")

print("=" * 60)
print("B4 ON-DEMAND CATCH-UP")
print("=" * 60)
print("EMPTY DB INITIAL LOAD: PASS")
print("COMPLETE DATA = ZERO API CALLS: PASS")
print("30 MISSING BARS = ONE CALL: PASS")
print("SINGLE MISSING BAR: PASS")
print("WEEKEND = CLOSED, NO CALLS: PASS")
print("ACROSS WEEKEND: GAP IS MARKET_CLOSED: PASS")
print("CALL LIMIT: NEWEST FIRST, OLDER GAP REPORTED: PASS")
print("PROVIDER FAILURE / BUDGET / INVALID BAR: PASS")
print("AUDIT ROWS + REPORT: PASS")
print("RESULT: PASS")
print("=" * 60)
