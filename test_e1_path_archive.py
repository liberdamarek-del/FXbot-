"""E1 - Market Path Archive and the Dukascopy adapter (no network).

Synthetic payloads in the exact Dukascopy format are served by a fake HTTP
layer, so parsing, validation, day states, hashes, aggregation and the
New York alignment are checked deterministically.
"""

import lzma
import os
import struct
import tempfile
from datetime import date, datetime, timedelta, timezone

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="fxbot_e1_")
os.environ["FXBOT_IGNORE_DOTENV"] = "1"

from src import path_archive as pa  # noqa: E402
from src.raw_archive import sha256_hex  # noqa: E402
from src.sources import dukascopy as duka  # noqa: E402

UTC = timezone.utc


def candles(day_start: int, prices: dict[int, tuple], scale=100000, step=60) -> bytes:
    """prices: offset_seconds -> (open, high, low, close, volume)."""
    raw = b"".join(
        struct.pack(">5if", off, round(o * scale), round(c * scale), round(l * scale), round(h * scale), v)
        for off, (o, h, l, c, v) in sorted(prices.items())
    )
    return lzma.compress(raw, format=lzma.FORMAT_ALONE)


def flat_day(base: float, spread: float = 0.0, missing: set | None = None, bump: dict | None = None):
    bid, ask = {}, {}
    for minute in range(1440):
        if missing and minute in missing:
            continue
        price = base + 0.00001 * (minute % 7)
        o, h, l, c = price, price + 0.00005, price - 0.00005, price
        if bump and minute in bump:
            o, h, l, c = bump[minute]
        bid[minute * 60] = (o, h, l, c, 1.0)
        ask[minute * 60] = (o + spread, h + spread, l + spread, c + spread, 1.0)
    return bid, ask


# ---------------------------------------------------------------- fake HTTP
SERVED: dict[str, tuple[int, bytes]] = {}


def fake_get(url: str):
    key = url.split("/datafeed/")[-1]
    return SERVED.get(key, (404, b""))


duka._get = fake_get
NOW = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)

# ---------------------------------------------------------------- 1. complete day
day = date(2026, 9, 29)                                   # Tuesday: 1440 session minutes
start = pa.day_start_ts(day)
bid, ask = flat_day(1.13000, 0.00002)
SERVED[duka.day_endpoint("EUR/USD", day, "BID")] = (200, candles(start, bid))
SERVED[duka.day_endpoint("EUR/USD", day, "ASK")] = (200, candles(start, ask))
assert duka.day_endpoint("EUR/USD", day, "BID") == "EURUSD/2026/08/29/BID_candles_min_1.bi5", "month is zero-based"
assert duka.ingest_day("EUR/USD", day, NOW) == "COMPLETE"
minutes = pa.day_minutes("EUR/USD", day)
assert len(minutes) == 1440 and minutes[0].ts == start and abs(minutes[0].ac - minutes[0].bc - 0.00002) < 1e-9
assert duka.ingest_day("EUR/USD", day, NOW) == "COMPLETE"          # idempotent, no second download needed

# ---------------------------------------------------------------- 2. weekend and pending days
assert duka.ingest_day("EUR/USD", date(2026, 9, 26), NOW) == "EMPTY"   # Saturday
assert duka.ingest_day("EUR/USD", date(2026, 9, 30), NOW) == "PENDING"  # the day is not over

# ---------------------------------------------------------------- 3. missing side -> GAP, never filled
day_gap = date(2026, 9, 28)
SERVED[duka.day_endpoint("EUR/USD", day_gap, "BID")] = (200, candles(pa.day_start_ts(day_gap), bid))
assert duka.ingest_day("EUR/USD", day_gap, NOW) == "GAP"
assert pa.day_minutes("EUR/USD", day_gap, allow_provisional=False) == ()

# ---------------------------------------------------------------- 4. missing minutes -> PARTIAL, no bar over the hole
day_part = date(2026, 9, 24)
bid_p, ask_p = flat_day(1.13000, 0.00002, missing={600, 601})       # 10:00 and 10:01 missing
sp = pa.day_start_ts(day_part)
SERVED[duka.day_endpoint("EUR/USD", day_part, "BID")] = (200, candles(sp, bid_p))
SERVED[duka.day_endpoint("EUR/USD", day_part, "ASK")] = (200, candles(sp, ask_p))
assert duka.ingest_day("EUR/USD", day_part, NOW) == "PARTIAL"
bars_1h = pa.aggregate(pa.day_minutes("EUR/USD", day_part), "1h")
assert sp + 10 * 3600 not in {b.ts for b in bars_1h}, "an incomplete hour must not become a bar"
assert len(bars_1h) == 23

# ---------------------------------------------------------------- 5. scale / parser errors are never stored
day_bad = date(2026, 9, 23)
bad_bid = {k: (v[0] * 1000, v[1] * 1000, v[2] * 1000, v[3] * 1000, 1.0) for k, v in bid.items()}  # wrong scale
SERVED[duka.day_endpoint("EUR/USD", day_bad, "BID")] = (200, candles(pa.day_start_ts(day_bad), bad_bid))
SERVED[duka.day_endpoint("EUR/USD", day_bad, "ASK")] = (200, candles(pa.day_start_ts(day_bad), ask))
assert duka.ingest_day("EUR/USD", day_bad, NOW) == "GAP"

# ---------------------------------------------------------------- 6. inconsistent minute (ask < bid) dropped, not repaired
day_inv = date(2026, 9, 22)
bid_i, ask_i = flat_day(1.13000, 0.00002)
ask_i[300] = (1.12000, 1.12001, 1.11999, 1.12000, 1.0)                # ask far below bid
si = pa.day_start_ts(day_inv)
SERVED[duka.day_endpoint("EUR/USD", day_inv, "BID")] = (200, candles(si, bid_i))
SERVED[duka.day_endpoint("EUR/USD", day_inv, "ASK")] = (200, candles(si, ask_i))
assert duka.ingest_day("EUR/USD", day_inv, NOW) == "PARTIAL"
assert si + 300 not in {b.ts for b in pa.day_minutes("EUR/USD", day_inv)}

# ---------------------------------------------------------------- 7. payload hash / replay
record = pa.get_day("EUR/USD", day, duka.SOURCE_M1)
content, digest = pa.load_payload(record["bid_payload_id"])
assert sha256_hex(content) == digest
with pa.get_path_connection() as c:
    c.execute("UPDATE raw_payloads SET content = ? WHERE payload_id = ?", (b"tampered", record["bid_payload_id"]))
    c.commit()
try:
    pa.load_payload(record["bid_payload_id"])
    raise AssertionError("tampered payload must be detected")
except RuntimeError as exc:
    assert "REPRODUCIBILITY INCOMPLETE" in str(exc)
with pa.get_path_connection() as c:
    c.execute("UPDATE raw_payloads SET content = ? WHERE payload_id = ?", (content, record["bid_payload_id"]))
    c.commit()

# ---------------------------------------------------------------- 8. New York alignment (summer and winter)
summer = int(datetime(2026, 9, 29, 12, 0, tzinfo=UTC).timestamp())
assert datetime.fromtimestamp(pa.bucket_start(summer, "1d"), tz=UTC) == datetime(2026, 9, 28, 21, 0, tzinfo=UTC)
assert datetime.fromtimestamp(pa.bucket_start(summer, "4h"), tz=UTC) == datetime(2026, 9, 29, 9, 0, tzinfo=UTC)
winter = int(datetime(2026, 1, 13, 12, 0, tzinfo=UTC).timestamp())
assert datetime.fromtimestamp(pa.bucket_start(winter, "1d"), tz=UTC) == datetime(2026, 1, 12, 22, 0, tzinfo=UTC)
assert pa.trading_date(summer) == date(2026, 9, 29)
assert pa.bucket_start(summer, "1h") == summer

# ---------------------------------------------------------------- 9. stored aggregates only from COMPLETE days
counts = pa.rebuild_aggregates("EUR/USD", date(2026, 9, 22), date(2026, 9, 29))
h1 = pa.load_bars("EUR/USD", "1h")
assert all(pa.trading_date(b.ts) for b in h1)
assert not any(sp <= b.ts < sp + 86400 for b in h1), "a PARTIAL day never produces stored bars"
assert any(start <= b.ts < start + 86400 for b in h1)
assert counts["1h"] == 24

# ---------------------------------------------------------------- 10. ticks -> minutes (flat, never invented)
hour = int(datetime(2026, 9, 30, 9, 0, tzinfo=UTC).timestamp())
ticks = [(hour + 125.5, 1.1300, 1.1302, 1, 1), (hour + 130.0, 1.1301, 1.1303, 1, 1)]
bars = duka.ticks_to_minutes(ticks, [hour + 60 * k for k in range(5)])
assert [b.ts for b in bars] == [hour + 120, hour + 180, hour + 240], "no bar before the first tick"
assert bars[0].bh == 1.1301 and bars[1].volume == 0.0 and bars[1].bc == 1.1301

# ---------------------------------------------------------------- 11. monthly hourly candles
month_start = pa.month_start_ts(2026, 8)
hours = {h * 3600: (1.15, 1.1502, 1.1498, 1.1501, 1.0) for h in range(31 * 24)}
SERVED[duka.month_endpoint("EUR/USD", 2026, 8, "BID")] = (200, candles(month_start, hours))
SERVED[duka.month_endpoint("EUR/USD", 2026, 8, "ASK")] = (200, candles(month_start, {k: (v[0] + 0.0001, v[1] + 0.0001, v[2] + 0.0001, v[3] + 0.0001, 1.0) for k, v in hours.items()}))
assert duka.ingest_month("EUR/USD", 2026, 8, NOW) == "COMPLETE"
assert duka.ingest_month("EUR/USD", 2026, 9, NOW) == "PENDING"
counts = pa.rebuild_hourly_aggregates("EUR/USD", (2026, 8), (2026, 8))
assert counts["1h"] == len(pa.session_hours_of_month(2026, 8)) and counts["1d"] >= 20
assert all(b.minutes == 1440 or b.minutes < 1440 for b in pa.load_bars("EUR/USD", "1d", source_id="DUKASCOPY_H1"))

print("=" * 60)
print("E1 MARKET PATH ARCHIVE + DUKASCOPY")
print("=" * 60)
print("DECODE / COMPLETE / EMPTY / PENDING / GAP / PARTIAL: PASS")
print("NO INTERPOLATION, INVALID MINUTES DROPPED: PASS")
print("PAYLOAD HASH REPLAY + TAMPER DETECTION: PASS")
print("NEW YORK ALIGNMENT SUMMER/WINTER: PASS")
print("AGGREGATES ONLY FROM COMPLETE DAYS: PASS")
print("TICKS -> MINUTES WITHOUT INVENTION: PASS")
print("MONTHLY HOURLY CANDLES: PASS")
print("RESULT: PASS")
print("=" * 60)
