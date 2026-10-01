"""E8 - FXCM week files as the second 1-minute path source (no network).

Synthetic week files in the exact FXCM format are served by a fake HTTP
layer: parsing, flat fill of tick-less minutes (never of invalid rows), day
states, week-number search, separation from the canonical series, and the
cross-source refinement rule of the resolver.
"""

import gzip
import os
import tempfile
from datetime import date, datetime, timedelta, timezone

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="fxbot_e8_")
os.environ["FXBOT_IGNORE_DOTENV"] = "1"

from src import path_archive as pa  # noqa: E402
from src.engine.data import minute_loader  # noqa: E402
from src.engine.resolution import MinuteList, Plan, resolve  # noqa: E402
from src.sources import fxcm  # noqa: E402

UTC = timezone.utc
H = 3600


def ts_of(text: str) -> int:
    return int(datetime.fromisoformat(text).replace(tzinfo=UTC).timestamp())


def row(ts: int, bid: float, spread: float = 0.0001, low: float | None = None, high: float | None = None) -> str:
    low = bid if low is None else low
    high = bid if high is None else high
    stamp = datetime.fromtimestamp(ts, tz=UTC).strftime("%m/%d/%Y %H:%M:%S.000")
    b = (bid, high, low, bid)
    a = tuple(round(x + spread, 6) for x in b)
    return stamp + "," + ",".join(f"{x:.5f}" for x in b + a)


def week_file(rows: list[str]) -> bytes:
    return gzip.compress((fxcm.HEADER + "\n" + "\n".join(rows) + "\n").encode("ascii"))


# ---------------------------------------------------------------- 1. week number candidates
assert fxcm.week_candidates(date(2024, 1, 16))[0] == (2024, 3)       # verified: 2024/3 = 14-19 Jan 2024
assert (2026, 1) in fxcm.week_candidates(date(2026, 1, 6))          # verified: 2026/1 = 4-9 Jan 2026
assert fxcm.week_candidates(date(2024, 1, 14)) == fxcm.week_candidates(date(2024, 1, 15)), "Sunday = next week"
assert fxcm.week_candidates(date(2024, 1, 13)) == [], "Saturday has no session"

# ---------------------------------------------------------------- 2. decoding and flat fill
# trading week Sunday 2024-01-14 22:00 .. Friday 2024-01-19 22:00 UTC (winter)
open_ts = ts_of("2024-01-14T22:00:00")
close_ts = ts_of("2024-01-19T22:00:00")
rows = []
price = 1.09500

for ts in range(open_ts + 5 * 60, close_ts - 3 * 60, 60):        # first tick 22:05, last tick 21:56 Friday
    if (ts - open_ts) // 60 % 7 == 3:
        continue                                                     # tick-less minutes
    price += 0.00001 if (ts // 60) % 2 else -0.00001
    rows.append(row(ts, round(price, 5)))

bad_ts = ts_of("2024-01-16T10:00:00")
rows = [r for r in rows if not r.startswith(datetime.fromtimestamp(bad_ts, tz=UTC).strftime("%m/%d/%Y %H:%M"))]
rows.append(row(bad_ts, 1.0950, spread=-0.0005))                     # ask below bid: invalid
rows.sort(key=lambda r: datetime.strptime(r[:19], "%m/%d/%Y %H:%M:%S"))
content = week_file(rows)

observed, invalid = fxcm.decode_week(content, "EUR/USD")
assert invalid == {bad_ts} and bad_ts not in {b.ts for b in observed}
filled = fxcm.fill_week(observed, invalid)
by_ts = {b.ts: b for b in filled}
assert bad_ts not in by_ts, "an invalid row stays a hole - never repaired"
gap = open_ts + 3 * 60 + 7 * 60                                     # a tick-less minute after the first tick
assert by_ts[gap].active == 0 and by_ts[gap].bh == by_ts[gap].bl == by_ts[gap - 60].bc, "flat from the last close"
assert open_ts not in by_ts, "nothing before the first tick"
assert close_ts - 60 in by_ts, "after the last tick the session closes within the fill limit: filled to the close"

try:
    fxcm.decode_week(gzip.compress(b"Date,Open\n1,2\n"), "EUR/USD")
    raise AssertionError("wrong header must raise")
except ValueError:
    pass

try:
    fxcm.decode_week(week_file([row(open_ts + 600, 150.0)]), "EUR/USD")
    raise AssertionError("JPY-scale price for EUR/USD must raise")
except ValueError:
    pass

# ---------------------------------------------------------------- 3. ingestion with the week search (fake CDN)
served = {"EURUSD/2024/3.csv.gz": content}
calls = []


def fake_fetch(url, retries=3, ok_statuses=(200,), **kw):
    endpoint = url.split("/m1/", 1)[1]
    calls.append(endpoint)
    return (200, served[endpoint], url) if endpoint in served else (404, b"", url)


fxcm.fetch = fake_fetch
tried: set = set()
assert fxcm.ingest_day("EUR/USD", date(2024, 1, 16), tried) == "PARTIAL", "the invalid minute leaves the day PARTIAL"
assert fxcm.ingest_day("EUR/USD", date(2024, 1, 17), tried) == "COMPLETE"
assert calls == ["EURUSD/2024/3.csv.gz"], "one file covers the whole week"
assert fxcm.ingest_day("EUR/USD", date(2024, 1, 15), tried) == "COMPLETE" and len(calls) == 1
assert fxcm.ingest_day("EUR/USD", date(2024, 1, 14), tried) == "PARTIAL", "Sunday: minutes before the first tick"
assert fxcm.ingest_day("EUR/USD", date(2024, 1, 2), tried) == "GAP", "no published file: GAP, nothing invented"
assert fxcm.ingest_day("EUR/USD", date(2024, 1, 13), tried) == "EMPTY"

# separation from the canonical series (module 9)
day = date(2024, 1, 17)
assert pa.day_minutes("EUR/USD", day, allow_provisional=False) == (), "FXCM never in the canonical day"
bars, source = pa.day_minutes_with_source("EUR/USD", day, allow_provisional=False)
assert source == fxcm.SOURCE_FXCM_M1 and len(bars) == 1440
summary = pa.archive_summary("EUR/USD")
assert summary["days_fxcm"]["COMPLETE"]["n"] >= 3 and "COMPLETE" not in summary["days"]
pa.rebuild_all("EUR/USD")
assert not pa.load_bars("EUR/USD", "1h", ts_of("2024-01-15T00:00:00"), ts_of("2024-01-18T00:00:00")), \
    "no canonical bars from the second source"
loaded = minute_loader("EUR/USD")(ts_of("2024-01-17T10:00:00"), ts_of("2024-01-17T11:00:00"))
assert isinstance(loaded, MinuteList) and loaded.cross_source and loaded.source_id == "FXCM_M1" and len(loaded) == 60

# ---------------------------------------------------------------- 4. cross-source refinement rule
T0 = ts_of("2024-01-17T08:00:00")


def bar(ts, bid_low, bid_high, spread=0.0001, close=None):
    close = close if close is not None else (bid_low + bid_high) / 2
    return pa.Bar(ts, close, bid_high, bid_low, close, close + spread, bid_high + spread, bid_low + spread,
                  close + spread, 1, 1, 60)


plan = Plan("BUY", True, 1.1000, 1.0990, 1.1020, T0, T0 + 24 * H, 0.0)
coarse = [bar(T0, 1.0995, 1.1005, close=1.1000), bar(T0 + H, 1.0985, 1.1025)]   # hour 2: SL and TP both hit


def minutes(sl_at=None, tp_at=None):
    out = [bar(T0 + H + 60 * k, 1.1001, 1.1004) for k in range(60)]
    if tp_at is not None:
        out[tp_at] = bar(T0 + H + 60 * tp_at, 1.1010, 1.1025)
    if sl_at is not None:
        out[sl_at] = bar(T0 + H + 60 * sl_at, 1.0985, 1.0995)
    return out


def cross(bars):
    out = MinuteList(bars)
    out.cross_source, out.source_id = True, "FXCM_M1"
    return out


# the second source shows both events: its order decides, labelled
out = resolve(plan, coarse, H, T0 + 30 * H, minute_loader=lambda a, b: cross(minutes(sl_at=10, tp_at=40)))
assert out.outcome_state == "SL_BEFORE_TP1" and "FXCM_M1" in out.granularity and "FXCM_M1" in out.notes[-1]
# the second source shows only the SL: the sources disagree -> unknown, nothing guessed
out = resolve(plan, coarse, H, T0 + 30 * H, minute_loader=lambda a, b: cross(minutes(sl_at=10)))
assert out.outcome_state == "SEQUENCE_UNKNOWN"
# the same minutes from the canonical source decide as before
out = resolve(plan, coarse, H, T0 + 30 * H, minute_loader=lambda a, b: minutes(sl_at=10))
assert out.outcome_state == "SL_BEFORE_TP1" and out.granularity == "1min (upresneno)"

print("=" * 60)
print("E8 FXCM SECOND PATH SOURCE")
print("=" * 60)
print("WEEK NUMBER SEARCH (FILE CONTENT DECIDES): PASS")
print("DECODING, FLAT FILL, INVALID ROW = HOLE: PASS")
print("ONE FILE PER WEEK, GAP WITHOUT FILE: PASS")
print("NEVER CANONICAL (NO BARS, NOT IN LIVE SERIES): PASS")
print("CROSS-SOURCE REFINEMENT ONLY WITH THE SAME EVENTS: PASS")
print("RESULT: PASS")
print("=" * 60)
