"""FXCM public candle archive - second source of the 1-minute BID/ASK path
(modules 63, 108, 122, 136).

    https://candledata.fxcorporate.com/m1/{SYMBOL}/{YEAR}/{WEEK}.csv.gz

Published by FXCM for free download (github.com/fxcm/MarketData) and served
through a CDN. Verified from this project on 2026-10-01:

- gzip CSV: DateTime,BidOpen,BidHigh,BidLow,BidClose,AskOpen,AskHigh,AskLow,AskClose
  with DateTime = MM/DD/YYYY HH:MM:SS.fff in UTC (the week opens on Sunday
  21:00/22:00 UTC)
- one file = one trading week; a minute without a tick is absent
- the WEEK number is not consistent between years (2024-2025 files = ISO
  week of the Monday, 2026 files = one less). A day's file is therefore found
  by trying candidates and reading the timestamps inside; a file is never
  assumed to cover a day
- some weeks are not published (HTTP 404): 2024 weeks 1/35/51/52, 2025 weeks
  1/2/29/30, 2026 weeks 18-31; new weeks appear with about one week of lag

Role: the path when Dukascopy has no 1-minute day (its free datafeed
answered HTTP 429 for hours to the cloud runtime). FXCM is another
liquidity pool - prices differ by fractions of a pip - so:

- its days are never used for the canonical aggregates or the live series
  (one canonical source per series, module 9),
- its minutes decide an ambiguous Dukascopy hour only when they show the
  same events in that hour (cross-source refinement in
  src/engine/resolution.py); otherwise the order stays unknown.

A missing minute inside the week means no tick: it is filled FLAT from the
last close (volume 0, active 0), the same convention as Dukascopy. Before the
first tick of the file nothing is filled (nothing is known).
"""

import gzip
import os
from datetime import date, datetime, timedelta, timezone

from src.instruments import get_instrument
from src.path_archive import (
    Bar,
    get_day,
    is_session_minute,
    load_payload,
    log_fetch,
    session_minutes_of_day,
    set_day,
    store_payload,
)
from src.sources.dukascopy import SourceUnavailable, _check_price
from src.sources.http import FetchError, fetch

SOURCE_FXCM_M1 = "FXCM_M1"
SOURCE_FXCM_H1 = "FXCM_H1"
PARSER_VERSION = "fxcm-csv-1"
BASE_URL = os.getenv("FXCM_BASE_URL", "https://candledata.fxcorporate.com/m1")
HOURLY_URL = os.getenv("FXCM_HOURLY_URL", "https://candledata.fxcorporate.com/H1")
HEADER = "DateTime,BidOpen,BidHigh,BidLow,BidClose,AskOpen,AskHigh,AskLow,AskClose"
CLOSE_FILL_MINUTES = 60      # flat fill after the last tick only up to a session close this near
# FXCM files contain momentary crossed quotes (close/open ask below bid).
# Measured 2026-10-01 on 1.06 M EUR/USD + USD/CAD minutes 2016-2023: cross
# > 0.2 pip in 0.24-0.35 %, > 0.5 pip in 0.02 %, > 1 pip in 0.005 %, > 5 pip 0.
CROSS_TOLERANCE_PIPS = 1.0

UTC = timezone.utc


class FxcmUnavailable(SourceUnavailable):
    """The CDN did not deliver (after retries). Never replaced by a guess."""


def week_endpoint(symbol: str, year: int, week: int) -> str:
    return f"{symbol.replace('/', '')}/{year}/{week}.csv.gz"


def trading_monday(day: date) -> date | None:
    """Monday of the trading week that contains the UTC day (Sunday evening
    belongs to the next Monday; Saturday has no session)."""
    weekday = day.weekday()

    if weekday == 5:
        return None

    return day + timedelta(days=1) if weekday == 6 else day - timedelta(days=weekday)


def week_candidates(day: date) -> list[tuple[int, int]]:
    """(year, week) files that may hold the day, most likely first."""
    monday = trading_monday(day)

    if monday is None:
        return []

    iso_year, iso_week, _ = monday.isocalendar()
    candidates = [(iso_year, iso_week), (iso_year, iso_week - 1), (iso_year, iso_week + 1)]

    if monday.year != iso_year:              # week across New Year
        candidates += [(monday.year, 53), (monday.year, 52), (iso_year, 0)]

    out = []

    for year, week in candidates:
        if 0 <= week <= 53 and (year, week) not in out:
            out.append((year, week))

    return out


# ----------------------------------------------------------------------
# decoding (pure functions)
# ----------------------------------------------------------------------

def valid_bar(bar: Bar, pip: float) -> bool:
    """Each side a consistent OHLC candle; ask below bid only by a momentary
    cross of at most CROSS_TOLERANCE_PIPS (e.g. EUR/USD 2018-03-27 19:00:
    0.1 pip). The bar is accepted unchanged, never repaired; a larger cross
    makes the bar invalid (a hole)."""
    tolerance = CROSS_TOLERANCE_PIPS * pip + 1e-12
    return (
        bar.bl <= min(bar.bo, bar.bc) <= max(bar.bo, bar.bc) <= bar.bh
        and bar.al <= min(bar.ao, bar.ac) <= max(bar.ao, bar.ac) <= bar.ah
        and bar.ac >= bar.bc - tolerance
        and bar.ao >= bar.bo - tolerance
    )


def _stamp(text: str) -> int:
    # MM/DD/YYYY HH:MM:SS(.fff); manual slicing is ~10x faster than strptime
    moment = datetime(int(text[6:10]), int(text[0:2]), int(text[3:5]), int(text[11:13]), int(text[14:16]),
                      int(text[17:19]), tzinfo=UTC)
    return int(moment.timestamp())


def decode_week(content: bytes, symbol: str, step: int = 60) -> tuple[list[Bar], set[int]]:
    """(observed 1-minute bid/ask bars oldest first, minutes of invalid rows).

    A row with a price outside the plausibility range of the pair raises
    (wrong file/parser); an internally inconsistent candle (high below
    close, ask below bid) is dropped and its minute stays a hole - never
    repaired, never flat-filled."""
    instrument = get_instrument(symbol)
    lines = gzip.decompress(content).decode("ascii").splitlines()

    if not lines or lines[0].strip() != HEADER:
        raise ValueError(f"unexpected FXCM header: {lines[0][:80] if lines else '(empty)'}")

    bars: dict[int, Bar] = {}
    invalid: set[int] = set()

    for line in lines[1:]:
        if not line.strip():
            continue

        parts = line.split(",")

        if len(parts) != 9:
            raise ValueError(f"unexpected FXCM row: {line[:80]}")

        ts = _stamp(parts[0])

        if ts % step:
            raise ValueError(f"FXCM row not on a {step} s boundary: {parts[0]}")

        values = [_check_price(instrument, float(x)) for x in parts[1:]]
        bar = Bar(ts, *values, 0.0, 1, step // 60)

        if valid_bar(bar, instrument.pip):
            bars[ts] = bar
        else:
            invalid.add(ts)

    return [bars[k] for k in sorted(bars)], invalid - set(bars)


def fill_week(observed: list[Bar], invalid: set[int] = frozenset(), step: int = 60) -> list[Bar]:
    """Session minutes from the first observed minute to the end of the
    week: observed bars, and flat bars (volume 0, active 0) where no tick
    came. After the last tick the fill continues only when the session
    closes within CLOSE_FILL_MINUTES (otherwise the file may be cut short)."""
    if not observed:
        return []

    by_ts = {b.ts: b for b in observed}
    end = observed[-1].ts + step
    probe = end

    while is_session_minute(probe) and probe - end < CLOSE_FILL_MINUTES * 60:
        probe += 60

    if not is_session_minute(probe):
        end = probe

    out = []
    last = None

    for ts in range(observed[0].ts, end, step):
        if ts in by_ts:
            last = by_ts[ts]
            out.append(last)
        elif last is not None and ts not in invalid and is_session_minute(ts):
            out.append(Bar(ts, last.bc, last.bc, last.bc, last.bc, last.ac, last.ac, last.ac, last.ac, 0.0, 0,
                           step // 60))

    return out


def split_days(minutes: list[Bar]) -> dict[date, list[Bar]]:
    days: dict[date, list[Bar]] = {}

    for bar in minutes:
        days.setdefault(datetime.fromtimestamp(bar.ts, tz=UTC).date(), []).append(bar)

    return days


# ----------------------------------------------------------------------
# ingestion
# ----------------------------------------------------------------------

def fetch_week(symbol: str, year: int, week: int) -> list[date]:
    """Download one week file, store it with its hash and register every
    UTC day it covers. Returns the covered days ([] = not published)."""
    endpoint = week_endpoint(symbol, year, week)

    try:
        status, content, _ = fetch(f"{BASE_URL}/{endpoint}", retries=3, ok_statuses=(200, 404))
    except FetchError as exc:
        log_fetch(SOURCE_FXCM_M1, endpoint, "FAILED", symbol, None, str(exc))
        raise FxcmUnavailable(f"{endpoint}: {exc}") from exc

    if status == 404 or not content:
        log_fetch(SOURCE_FXCM_M1, endpoint, "NOT_FOUND", symbol, status)
        return []

    try:
        observed, invalid = decode_week(content, symbol)
    except (ValueError, OSError, EOFError) as exc:
        log_fetch(SOURCE_FXCM_M1, endpoint, "PARSE_ERROR", symbol, status, str(exc))
        return []

    if not observed:
        log_fetch(SOURCE_FXCM_M1, endpoint, "EMPTY", symbol, status)
        return []

    stored = store_payload(
        source_id=SOURCE_FXCM_M1, kind="M1_WEEK", endpoint=endpoint, instrument=symbol, side="BID+ASK",
        period_start=observed[0].ts, period_end=observed[-1].ts + 60, http_status=status, content=content,
        parser_version=PARSER_VERSION,
    )
    log_fetch(SOURCE_FXCM_M1, endpoint, "OK", symbol, status, f"{len(content)} B sha256={stored.sha256[:12]}")
    return register_week(symbol, stored.payload_id, observed, invalid)


def register_week(symbol: str, payload_id: int, observed: list[Bar], invalid: set[int]) -> list[date]:
    """Day states of one stored week file (a COMPLETE day is never downgraded)."""
    covered = []

    for day, bars in split_days(fill_week(observed, invalid)).items():
        expected = set(session_minutes_of_day(day))

        if not expected:
            continue

        present = [b for b in bars if b.ts in expected]
        state = "COMPLETE" if len(present) == len(expected) else "PARTIAL"
        set_day(instrument=symbol, day=day, source_id=SOURCE_FXCM_M1, state=state,
                bid_payload_id=payload_id, ask_payload_id=payload_id,
                expected_minutes=len(expected), observed_minutes=len(present),
                active_minutes=sum(b.active for b in present), quality_state="SIDE-CORRECT",
                note=None if state == "COMPLETE" else f"{len(expected) - len(present)} in-session minutes missing")
        covered.append(day)

    return covered


def reprocess(symbol: str) -> int:
    """Re-register the days of every stored week file (after a parser
    change) without downloading anything. Returns the number of files."""
    from src.path_archive import get_path_connection

    with get_path_connection() as connection:
        ids = [r[0] for r in connection.execute(
            "SELECT payload_id FROM raw_payloads WHERE source_id = ? AND instrument = ? ORDER BY period_start",
            (SOURCE_FXCM_M1, symbol))]

    for payload_id in ids:
        content, _ = load_payload(payload_id)
        register_week(symbol, payload_id, *decode_week(content, symbol))

    return len(ids)


def ingest_day(symbol: str, day: date, tried: set | None = None) -> str:
    """Make the FXCM path of one UTC day available. Returns its state:
    COMPLETE / PARTIAL / EMPTY (no session) / GAP (no published file covers it).

    `tried` remembers the week files already fetched in this process (a file
    covers several days; a 404 is not asked again)."""
    tried = tried if tried is not None else set()

    if not session_minutes_of_day(day):
        return "EMPTY"

    existing = get_day(symbol, day, SOURCE_FXCM_M1)

    if existing and existing["state"] == "COMPLETE":
        return "COMPLETE"

    for year, week in week_candidates(day):
        if (symbol, year, week) in tried:
            continue

        tried.add((symbol, year, week))

        if day in fetch_week(symbol, year, week):
            break

    record = get_day(symbol, day, SOURCE_FXCM_M1)
    return record["state"] if record else "GAP"


def decode_day(symbol: str, day: date, payload_id: int) -> tuple[Bar, ...]:
    """Session minutes of one UTC day from a stored week file (flat-filled)."""
    from src.path_archive import _fxcm_week

    session = set(session_minutes_of_day(day))
    return tuple(b for b in _fxcm_week(symbol, payload_id) if b.ts in session)


# ----------------------------------------------------------------------
# hourly candles: canonical series of a RESEARCH archive only
# ----------------------------------------------------------------------

def fetch_hour_week(symbol: str, year: int, week: int) -> list[Bar]:
    """One week of FXCM hourly BID/ASK candles (stored with its hash);
    [] = not published. Used as the canonical series only in a separate
    research archive (scripts/oos_fxcm.py), never next to Dukascopy."""
    endpoint = "H1/" + week_endpoint(symbol, year, week)

    try:
        status, content, _ = fetch(f"{HOURLY_URL}/{week_endpoint(symbol, year, week)}", retries=3,
                                   ok_statuses=(200, 404))
    except FetchError as exc:
        log_fetch(SOURCE_FXCM_H1, endpoint, "FAILED", symbol, None, str(exc))
        raise FxcmUnavailable(f"{endpoint}: {exc}") from exc

    if status == 404 or not content:
        log_fetch(SOURCE_FXCM_H1, endpoint, "NOT_FOUND", symbol, status)
        return []

    try:
        observed, invalid = decode_week(content, symbol, step=3600)
    except (ValueError, OSError, EOFError) as exc:
        log_fetch(SOURCE_FXCM_H1, endpoint, "PARSE_ERROR", symbol, status, str(exc))
        return []

    if not observed:
        return []

    stored = store_payload(
        source_id=SOURCE_FXCM_H1, kind="H1_WEEK", endpoint=endpoint, instrument=symbol, side="BID+ASK",
        period_start=observed[0].ts, period_end=observed[-1].ts + 3600, http_status=status, content=content,
        parser_version=PARSER_VERSION,
    )
    log_fetch(SOURCE_FXCM_H1, endpoint, "OK", symbol, status, f"{len(content)} B sha256={stored.sha256[:12]}")
    return fill_week(observed, invalid, step=3600)


def hour_weeks(symbol: str, first: date, last: date) -> tuple[list[Bar], list[date]]:
    """Hourly bars of every trading week whose Monday lies in [first, last]
    (each week file verified by its timestamps). Returns (bars, Mondays
    without a published file)."""
    monday = trading_monday(first) or first + timedelta(days=2)
    bars: dict[int, Bar] = {}
    missing = []
    fetched: set = set()

    while monday <= last:
        week_start = int(datetime(monday.year, monday.month, monday.day, tzinfo=UTC).timestamp()) - 2 * 3600 - 86400
        week_end = week_start + 6 * 86400
        found = False

        for year, week in week_candidates(monday):
            if (year, week) in fetched:
                continue

            fetched.add((year, week))
            got = fetch_hour_week(symbol, year, week)

            for bar in got:
                bars[bar.ts] = bar

            if any(week_start <= b.ts < week_end for b in got):
                found = True
                break

        if not found and not any(week_start <= ts < week_end for ts in bars):
            missing.append(monday)

        monday += timedelta(days=7)

    return [bars[k] for k in sorted(bars)], missing
