"""Dukascopy historical bid/ask adapter (modules 63, 108, 122, 136).

Public, keyless HTTP files (verified from this project on 2026-09-30):

    {base}/{CODE}/{YYYY}/{MM0}/{DD}/BID_candles_min_1.bi5   one UTC day of
    {base}/{CODE}/{YYYY}/{MM0}/{DD}/ASK_candles_min_1.bi5   1-minute candles
    {base}/{CODE}/{YYYY}/{MM0}/{DD}/{HH}h_ticks.bi5          one hour of ticks

MM0 is the month counted from ZERO (January = 00). The files are LZMA
compressed arrays of big-endian records:

    candles: uint32 seconds-from-day-start, uint32 open, uint32 close,
             uint32 low, uint32 high (integer points), float32 volume
    ticks:   uint32 milliseconds-from-hour-start, uint32 ask, uint32 bid,
             float32 ask volume, float32 bid volume

Prices are integer points: price = points / scale (1e5, or 1e3 for JPY
quotes; see src/instruments.py). A decoded price outside the plausibility
range of the pair raises an error - a scale mistake is never stored as a
price (module 5).

What this source is (module 11, 132): a public ECN/aggregated quote history
with separate BID and ASK sides - HISTORICAL class. It is NOT the price of
the user's broker. It allows side-correct outcome checks (module 12, 62:
BUY enters at ASK and exits at BID) at the level PUBLIC EXECUTABLE /
SIDE-CORRECT, never BROKER-VERIFIED.

Availability: a day file exists after the UTC day has ended; hour tick
files exist after the hour has ended (observed delay: well under one hour).
The current day is therefore built PROVISIONALLY from hour tick files and
replaced by the canonical day file once it exists (the provisional minutes
are never mixed into stored aggregates).

Politeness: requests are sequential with a minimum pause, 429/5xx are
retried with exponential backoff. The server answered HTTP 429/503 during
the first tests when requests came too fast.
"""

import lzma
import os
import struct
import threading
import time
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache

import requests

from src.instruments import get_instrument
from src.path_archive import (
    Bar,
    day_start_ts,
    get_day,
    get_month,
    month_start_ts,
    next_month,
    session_hours_of_month,
    set_month,
    get_path_connection,
    initialize_path_archive,
    load_payload,
    log_fetch,
    session_minutes_of_day,
    set_day,
    store_payload,
)

SOURCE_M1 = "DUKASCOPY_M1"
SOURCE_H1 = "DUKASCOPY_H1"
SOURCE_TICK = "DUKASCOPY_TICK"
PARSER_VERSION = "duka-bi5-1"
BASE_URL = os.getenv("DUKASCOPY_BASE_URL", "https://datafeed.dukascopy.com/datafeed")
USER_AGENT = "Mozilla/5.0 (fxbot historical research)"

MIN_PAUSE = float(os.getenv("DUKASCOPY_MIN_PAUSE", "1.0"))
MAX_RETRIES = int(os.getenv("DUKASCOPY_MAX_RETRIES", "8"))
CONNECT_TIMEOUT = float(os.getenv("DUKASCOPY_CONNECT_TIMEOUT", "6"))
TIMEOUT = float(os.getenv("DUKASCOPY_READ_TIMEOUT", "12"))

UTC = timezone.utc
_CANDLE = struct.Struct(">5if")
_TICK = struct.Struct(">3I2f")


class SourceUnavailable(RuntimeError):
    """The source did not deliver (after retries). Never replaced by a guess."""


# ----------------------------------------------------------------------
# decoding (pure functions)
# ----------------------------------------------------------------------

def _decompress(content: bytes) -> bytes:
    if not content:
        return b""

    return lzma.decompress(content)


def _check_price(instrument, value: float) -> float:
    if not (instrument.min_price <= value <= instrument.max_price):
        raise ValueError(
            f"{instrument.symbol}: decoded price {value} outside the "
            f"plausibility range - scale/parser error, not stored"
        )

    return value


def decode_minute_candles(content: bytes, symbol: str, day_start: int) -> list[tuple]:
    """-> [(ts, open, high, low, close, volume)] for one side of one day."""
    instrument = get_instrument(symbol)
    scale = instrument.dukascopy_scale
    raw = _decompress(content)

    if len(raw) % _CANDLE.size:
        raise ValueError("candle payload length is not a multiple of 24 bytes")

    out = []

    for seconds, o, c, low, high, volume in _CANDLE.iter_unpack(raw):
        if seconds % 60 or not (0 <= seconds < 86400):
            raise ValueError(f"unexpected candle offset {seconds}")

        values = [_check_price(instrument, x / scale) for x in (o, high, low, c)]
        out.append((day_start + seconds, *values, float(volume)))

    return out


def decode_hour_candles(content: bytes, symbol: str, month_start: int) -> list[tuple]:
    """-> [(ts, open, high, low, close, volume)] for one side of one month."""
    instrument = get_instrument(symbol)
    scale = instrument.dukascopy_scale
    raw = _decompress(content)

    if len(raw) % _CANDLE.size:
        raise ValueError("candle payload length is not a multiple of 24 bytes")

    out = []

    for seconds, o, c, low, high, volume in _CANDLE.iter_unpack(raw):
        if seconds % 3600 or not (0 <= seconds < 32 * 86400):
            raise ValueError(f"unexpected hour candle offset {seconds}")

        values = [_check_price(instrument, x / scale) for x in (o, high, low, c)]
        out.append((month_start + seconds, *values, float(volume)))

    return out


def decode_ticks(content: bytes, symbol: str, hour_start: int) -> list[tuple]:
    """-> [(epoch_seconds_float, bid, ask, bid_volume, ask_volume)]."""
    instrument = get_instrument(symbol)
    scale = instrument.dukascopy_scale
    raw = _decompress(content)

    if len(raw) % _TICK.size:
        raise ValueError("tick payload length is not a multiple of 20 bytes")

    out = []

    for millis, ask, bid, ask_volume, bid_volume in _TICK.iter_unpack(raw):
        if millis >= 3_600_000:
            raise ValueError(f"unexpected tick offset {millis}")

        out.append(
            (
                hour_start + millis / 1000.0,
                _check_price(instrument, bid / scale),
                _check_price(instrument, ask / scale),
                float(bid_volume),
                float(ask_volume),
            )
        )

    return out


def valid_minute(bar: Bar) -> bool:
    return (
        bar.bl <= min(bar.bo, bar.bc) <= max(bar.bo, bar.bc) <= bar.bh
        and bar.al <= min(bar.ao, bar.ac) <= max(bar.ao, bar.ac) <= bar.ah
        and bar.ac >= bar.bc
        and bar.ao >= bar.bo
    )


def merge_sides(bids: list[tuple], asks: list[tuple], unit_minutes: int = 1) -> list[Bar]:
    """Join the BID and ASK candles of the same period. Invalid candles
    (inconsistent OHLC, ask below bid) are dropped, never repaired."""
    ask_by_ts = {row[0]: row for row in asks}
    out = []

    for ts, bo, bh, bl, bc, bvol in bids:
        other = ask_by_ts.get(ts)

        if other is None:
            continue

        _, ao, ah, al, ac, avol = other
        bar = Bar(ts, bo, bh, bl, bc, ao, ah, al, ac, bvol + avol,
                  1 if (bvol + avol) > 0 else 0, unit_minutes)

        if valid_minute(bar):
            out.append(bar)

    return out


def ticks_to_minutes(ticks: list[tuple], minutes: list[int], previous: tuple | None = None) -> list[Bar]:
    """Build 1-minute bid/ask bars from ticks for the given minute starts.

    A minute without ticks is a flat bar at the last known bid/ask with zero
    volume - the same convention as the provider's own candles (the quote
    did not change). Before the first known quote nothing is produced
    (no invention).
    """
    by_minute: dict[int, list[tuple]] = {}

    for tick in ticks:
        by_minute.setdefault(int(tick[0]) // 60 * 60, []).append(tick)

    last = previous      # (bid, ask)
    out = []

    for ts in minutes:
        group = by_minute.get(ts)

        if group:
            bids = [t[1] for t in group]
            asks = [t[2] for t in group]
            volume = sum(t[3] + t[4] for t in group)
            bar = Bar(ts, bids[0], max(bids), min(bids), bids[-1],
                      asks[0], max(asks), min(asks), asks[-1], volume, 1, 1)
            last = (bids[-1], asks[-1])
        elif last is not None:
            b, a = last
            bar = Bar(ts, b, b, b, b, a, a, a, a, 0.0, 0, 1)
        else:
            continue

        if valid_minute(bar):
            out.append(bar)

    return out


# ----------------------------------------------------------------------
# HTTP
# ----------------------------------------------------------------------

# One keep-alive session per thread: a new TLS handshake per file took
# 7-15 s through the network proxy, a reused connection about 0.2 s.
_local = threading.local()
_retries = [0]          # retries since start (diagnostics for the downloader)
_retry_reasons: dict[str, int] = {}


def _session() -> requests.Session:
    session = getattr(_local, "session", None)

    if session is None:
        session = requests.Session()
        session.headers["User-Agent"] = USER_AGENT
        _local.session = session
        _local.last_request = 0.0

    return session


def _get(url: str) -> tuple[int, bytes]:
    """GET with pacing and retries. Returns (status, content) for 200/404.

    Measured behaviour through the network proxy: most requests take about
    0.2 s, but roughly one in four stalls (connection reset / HTTP 503) for
    10-120 s. A short timeout plus a fresh connection recovers much faster
    than waiting; the backoff still grows when the server keeps refusing.
    """
    delay = 1.0
    session = _session()
    error = "no attempt"

    for attempt in range(MAX_RETRIES):
        wait = MIN_PAUSE - (time.monotonic() - _local.last_request)

        if wait > 0:
            time.sleep(wait)

        _local.last_request = time.monotonic()

        try:
            response = session.get(url, timeout=(CONNECT_TIMEOUT, TIMEOUT))
        except requests.RequestException as exc:
            error = f"{type(exc).__name__}"
            status = None
            # a broken keep-alive connection: start a fresh session
            _local.session = None
            session = _session()
        else:
            status = response.status_code

            if status in (200, 404):
                return status, response.content

            error = f"HTTP {status}"

        _retries[0] += 1
        _retry_reasons[error] = _retry_reasons.get(error, 0) + 1

        if attempt + 1 < MAX_RETRIES:
            time.sleep(delay)
            delay = min(delay * 2, 30)

    raise SourceUnavailable(f"{url}: {error} after {MAX_RETRIES} attempts")


def day_endpoint(symbol: str, day: date, side: str) -> str:
    code = get_instrument(symbol).dukascopy_code
    return f"{code}/{day.year:04d}/{day.month - 1:02d}/{day.day:02d}/{side}_candles_min_1.bi5"


def hour_endpoint(symbol: str, day: date, hour: int) -> str:
    code = get_instrument(symbol).dukascopy_code
    return f"{code}/{day.year:04d}/{day.month - 1:02d}/{day.day:02d}/{hour:02d}h_ticks.bi5"


# ----------------------------------------------------------------------
# ingestion
# ----------------------------------------------------------------------

def day_is_final(day: date, now: datetime) -> bool:
    """A day file can only be complete after the UTC day has ended."""
    return now >= datetime(day.year, day.month, day.day, tzinfo=UTC) + timedelta(days=1, minutes=30)


def ingest_day(symbol: str, day: date, now: datetime | None = None, force: bool = False) -> str:
    """Download and store both sides of one UTC day. Returns the day state.

    COMPLETE  every in-session minute present on both sides
    PARTIAL   some in-session minutes missing (kept, never filled)
    EMPTY     no in-session minute on this day (weekend)
    GAP       the provider has no file (yet) for an in-session day
    """
    now = now or datetime.now(UTC)
    expected = session_minutes_of_day(day)

    if not expected:
        set_day(instrument=symbol, day=day, source_id=SOURCE_M1, state="EMPTY",
                bid_payload_id=None, ask_payload_id=None, expected_minutes=0,
                observed_minutes=0, active_minutes=0, quality_state="VALIDATED",
                note="no trading session on this UTC day")
        return "EMPTY"

    existing = get_day(symbol, day, SOURCE_M1)

    if existing and existing["state"] == "COMPLETE" and not force:
        return "COMPLETE"

    if not day_is_final(day, now):
        return "PENDING"

    payload_ids = {}

    for side in ("BID", "ASK"):
        endpoint = day_endpoint(symbol, day, side)

        try:
            status, content = _get(f"{BASE_URL}/{endpoint}")
        except SourceUnavailable as exc:
            log_fetch(SOURCE_M1, endpoint, "FAILED", symbol, None, str(exc))
            raise

        if status == 404 or not content:
            log_fetch(SOURCE_M1, endpoint, "NOT_FOUND" if status == 404 else "EMPTY", symbol, status)
            set_day(instrument=symbol, day=day, source_id=SOURCE_M1, state="GAP",
                    bid_payload_id=payload_ids.get("BID"), ask_payload_id=None,
                    expected_minutes=len(expected), observed_minutes=0, active_minutes=0,
                    quality_state="UNRESOLVED", note=f"{side} file not available (HTTP {status})")
            return "GAP"

        start = day_start_ts(day)
        # decode before storing: a payload that cannot be parsed is logged,
        # not archived as canonical
        try:
            decode_minute_candles(content, symbol, start)
        except (ValueError, lzma.LZMAError) as exc:
            log_fetch(SOURCE_M1, endpoint, "PARSE_ERROR", symbol, status, str(exc))
            set_day(instrument=symbol, day=day, source_id=SOURCE_M1, state="GAP",
                    bid_payload_id=None, ask_payload_id=None, expected_minutes=len(expected),
                    observed_minutes=0, active_minutes=0, quality_state="UNRESOLVED",
                    note=f"{side} payload could not be parsed: {exc}")
            return "GAP"

        stored = store_payload(
            source_id=SOURCE_M1, kind="M1_DAY", endpoint=endpoint, instrument=symbol,
            side=side, period_start=start, period_end=start + 86400, http_status=status,
            content=content, parser_version=PARSER_VERSION,
        )
        log_fetch(SOURCE_M1, endpoint, "OK", symbol, status, f"{len(content)} B sha256={stored.sha256[:12]}")
        payload_ids[side] = stored.payload_id

    from src.path_archive import _decoded_day  # local: cache lives there

    bars = _decoded_day(symbol, day.isoformat(), payload_ids["BID"], payload_ids["ASK"])
    observed = len(bars)
    active = sum(b.active for b in bars)
    state = "COMPLETE" if observed == len(expected) else "PARTIAL"

    set_day(instrument=symbol, day=day, source_id=SOURCE_M1, state=state,
            bid_payload_id=payload_ids["BID"], ask_payload_id=payload_ids["ASK"],
            expected_minutes=len(expected), observed_minutes=observed, active_minutes=active,
            quality_state="SIDE-CORRECT",
            note=None if state == "COMPLETE" else f"{len(expected) - observed} in-session minutes missing")
    return state


def month_endpoint(symbol: str, year: int, month: int, side: str) -> str:
    code = get_instrument(symbol).dukascopy_code
    return f"{code}/{year:04d}/{month - 1:02d}/{side}_candles_hour_1.bi5"


def ingest_month(symbol: str, year: int, month: int, now: datetime | None = None, force: bool = False) -> str:
    """Download both sides of one month of hourly candles (long history).

    The file exists only after the month has ended. States as for days.
    """
    from src.path_archive import _decoded_month

    now = now or datetime.now(UTC)
    expected = session_hours_of_month(year, month)
    existing = get_month(symbol, year, month, SOURCE_H1)

    if existing and existing["state"] == "COMPLETE" and not force:
        return "COMPLETE"

    if now.timestamp() < month_start_ts(*next_month(year, month)) + 3600:
        return "PENDING"

    payload_ids = {}
    start = month_start_ts(year, month)
    end = month_start_ts(*next_month(year, month))

    for side in ("BID", "ASK"):
        endpoint = month_endpoint(symbol, year, month, side)

        try:
            status, content = _get(f"{BASE_URL}/{endpoint}")
        except SourceUnavailable as exc:
            log_fetch(SOURCE_H1, endpoint, "FAILED", symbol, None, str(exc))
            raise

        if status == 404 or not content:
            log_fetch(SOURCE_H1, endpoint, "NOT_FOUND" if status == 404 else "EMPTY", symbol, status)
            set_month(instrument=symbol, year=year, month=month, source_id=SOURCE_H1, state="GAP",
                      bid_payload_id=None, ask_payload_id=None, expected_hours=len(expected),
                      observed_hours=0, active_hours=0, quality_state="UNRESOLVED",
                      note=f"{side} file not available (HTTP {status})")
            return "GAP"

        try:
            decode_hour_candles(content, symbol, start)
        except (ValueError, lzma.LZMAError) as exc:
            log_fetch(SOURCE_H1, endpoint, "PARSE_ERROR", symbol, status, str(exc))
            set_month(instrument=symbol, year=year, month=month, source_id=SOURCE_H1, state="GAP",
                      bid_payload_id=None, ask_payload_id=None, expected_hours=len(expected),
                      observed_hours=0, active_hours=0, quality_state="UNRESOLVED",
                      note=f"{side} payload could not be parsed: {exc}")
            return "GAP"

        stored = store_payload(
            source_id=SOURCE_H1, kind="H1_MONTH", endpoint=endpoint, instrument=symbol,
            side=side, period_start=start, period_end=end, http_status=status,
            content=content, parser_version=PARSER_VERSION,
        )
        log_fetch(SOURCE_H1, endpoint, "OK", symbol, status, f"{len(content)} B sha256={stored.sha256[:12]}")
        payload_ids[side] = stored.payload_id

    bars = _decoded_month(symbol, year, month, payload_ids["BID"], payload_ids["ASK"])
    observed = len(bars)
    state = "COMPLETE" if observed == len(expected) else "PARTIAL"
    set_month(instrument=symbol, year=year, month=month, source_id=SOURCE_H1, state=state,
              bid_payload_id=payload_ids["BID"], ask_payload_id=payload_ids["ASK"],
              expected_hours=len(expected), observed_hours=observed,
              active_hours=sum(b.active for b in bars), quality_state="SIDE-CORRECT",
              note=None if state == "COMPLETE" else f"{len(expected) - observed} in-session hours missing")
    return state


def ingest_provisional_hours(symbol: str, day: date, now: datetime | None = None) -> int:
    """Fetch the finished hours of a day that has no canonical day file yet.

    Returns the number of newly stored hour payloads. Hours that are not
    finished are never requested (an open bar is not a completed bar).
    """
    now = now or datetime.now(UTC)
    start = day_start_ts(day)
    session = session_minutes_of_day(day)

    if not session:
        return 0

    stored_new = 0

    with get_path_connection() as connection:
        have = {
            row["period_start"]
            for row in connection.execute(
                "SELECT period_start FROM raw_payloads WHERE instrument = ? AND kind = 'TICK_HOUR' "
                "AND period_start >= ? AND period_start < ?",
                (symbol, start, start + 86400),
            )
        }

    session_hours = sorted({(ts - start) // 3600 for ts in session})

    for hour in session_hours:
        hour_start = start + hour * 3600

        if hour_start in have:
            continue

        # the hour must be over (plus a small publication margin)
        if now.timestamp() < hour_start + 3600 + 120:
            break

        endpoint = hour_endpoint(symbol, day, hour)

        try:
            status, content = _get(f"{BASE_URL}/{endpoint}")
        except SourceUnavailable as exc:
            log_fetch(SOURCE_TICK, endpoint, "FAILED", symbol, None, str(exc))
            break

        if status == 404:
            log_fetch(SOURCE_TICK, endpoint, "NOT_FOUND", symbol, status)
            break

        try:
            decode_ticks(content, symbol, hour_start)
        except (ValueError, lzma.LZMAError) as exc:
            log_fetch(SOURCE_TICK, endpoint, "PARSE_ERROR", symbol, status, str(exc))
            break

        store_payload(
            source_id=SOURCE_TICK, kind="TICK_HOUR", endpoint=endpoint, instrument=symbol,
            side="BIDASK", period_start=hour_start, period_end=hour_start + 3600,
            http_status=status, content=content, parser_version=PARSER_VERSION,
        )
        log_fetch(SOURCE_TICK, endpoint, "OK", symbol, status, f"{len(content)} B")
        stored_new += 1

    _provisional_cache.cache_clear()
    return stored_new


@lru_cache(maxsize=32)
def _provisional_cache(symbol: str, day_iso: str, payload_key: tuple) -> tuple[Bar, ...]:
    day = date.fromisoformat(day_iso)
    start = day_start_ts(day)
    session = session_minutes_of_day(day)
    out: list[Bar] = []
    previous = None

    for hour_start, payload_id in payload_key:
        content, _ = load_payload(payload_id)
        ticks = decode_ticks(content, symbol, hour_start)
        minutes = [ts for ts in session if hour_start <= ts < hour_start + 3600]
        bars = ticks_to_minutes(ticks, minutes, previous)

        if bars:
            previous = (bars[-1].bc, bars[-1].ac)

        out.extend(bars)

    return tuple(out)


def provisional_minutes(symbol: str, day: date) -> tuple[Bar, ...]:
    """Minutes of a day built from stored hour tick files (PROVISIONAL).

    Only a contiguous run of hours from the start of the day's session is
    used, so a missing hour is never bridged.
    """
    start = day_start_ts(day)
    initialize_path_archive()

    with get_path_connection() as connection:
        rows = connection.execute(
            "SELECT period_start, MAX(payload_id) AS pid FROM raw_payloads "
            "WHERE instrument = ? AND kind = 'TICK_HOUR' AND period_start >= ? AND period_start < ? "
            "GROUP BY period_start ORDER BY period_start",
            (symbol, start, start + 86400),
        ).fetchall()

    session = session_minutes_of_day(day)

    if not rows or not session:
        return ()

    first_hour = session[0] - session[0] % 3600
    key = []
    expected_hour = first_hour

    for row in rows:
        if row["period_start"] != expected_hour:
            break

        key.append((row["period_start"], int(row["pid"])))
        expected_hour += 3600

    return _provisional_cache(symbol, day.isoformat(), tuple(key))
