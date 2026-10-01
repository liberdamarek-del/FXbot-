"""Market Path Archive (specification modules 86-94, 122, 124).

A separate SQLite file (data/market_path.sqlite3) next to the main database,
so that the potentially large price history can be rebuilt or trimmed on a
phone without ever touching the prediction ledger.

Three layers, strictly separated (RAW -> NORMALIZED -> VALIDATED, module 9):

raw_payloads   the exact bytes every source returned (module 124), with
               SHA-256, endpoint, retrieval time and parser version. The
               hash identifies the payload; the payload itself is kept, so a
               replay can rebuild the same canonical input set.
path_days      per instrument and UTC day: which payloads form the day, how
               many in-session minutes were expected and observed, and the
               coverage state (COMPLETE / PARTIAL / GAP / EMPTY).
market_path    normalized bid/ask OHLC bars (15min, 1h, 4h, 1d) built only
               from COMPLETE days. 1min and 5min are decoded on demand from
               the payloads (they would be too large to store as rows on a
               phone). Mid = (bid + ask) / 2 per field.

fetch_log      every acquisition attempt, successful or not (module 120:
               every attempt, endpoint, timestamp, response state, reason).

Rules:
- nothing is ever interpolated: a missing minute stays missing and a bar
  whose window is not complete is not built (modules 88, 122),
- only minutes inside the FX trading session are used (src/market_session),
- canonical rows are never updated in place; a different payload for the
  same endpoint is stored as a new payload (a new source observation, module
  87) and the day keeps pointing to the first valid one unless explicitly
  re-ingested,
- 4h and daily bars are aligned to the New York 17:00 close (the FX
  convention: five daily bars per week, every 4h bar is a full 4 hours);
  15min and 1h are aligned to the UTC clock.
"""

import sqlite3
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from typing import Iterable, NamedTuple

from src import raw_archive
from src.config import DATA_DIR
from src.market_session import is_fx_market_open, new_york_utc_offset
from src.raw_archive import FETCH_LOG_DDL, RAW_PAYLOADS_DDL, StoredPayload, now_iso

PATH_DB = DATA_DIR / "market_path.sqlite3"

UTC = timezone.utc
MINUTE = 60

STORED_TIMEFRAMES = ("15min", "1h", "4h", "1d")
ON_DEMAND_TIMEFRAMES = ("1min", "5min")
ALL_TIMEFRAMES = ON_DEMAND_TIMEFRAMES + STORED_TIMEFRAMES

TIMEFRAME_SECONDS = {
    "1min": 60,
    "5min": 300,
    "15min": 900,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
}
# 4h and 1d buckets follow the New York 17:00 close
NY_ALIGNED = ("4h", "1d")

DAY_STATES = ("COMPLETE", "PARTIAL", "GAP", "EMPTY", "PROVISIONAL")


class Bar(NamedTuple):
    ts: int              # bar open, epoch seconds UTC
    bo: float
    bh: float
    bl: float
    bc: float
    ao: float
    ah: float
    al: float
    ac: float
    volume: float
    active: int          # input bars with at least one tick (volume > 0)
    minutes: int         # in-session minutes the bar covers

    @property
    def mo(self) -> float:
        return (self.bo + self.ao) / 2

    @property
    def mh(self) -> float:
        return (self.bh + self.ah) / 2

    @property
    def ml(self) -> float:
        return (self.bl + self.al) / 2

    @property
    def mc(self) -> float:
        return (self.bc + self.ac) / 2

    @property
    def spread_close(self) -> float:
        return self.ac - self.bc

    @property
    def time(self) -> datetime:
        return datetime.fromtimestamp(self.ts, tz=UTC)


# ----------------------------------------------------------------------
# connection and schema
# ----------------------------------------------------------------------

_SCHEMA = (
    RAW_PAYLOADS_DDL,
    """
    CREATE INDEX IF NOT EXISTS ix_raw_payloads_lookup
    ON raw_payloads (instrument, kind, period_start)
    """,
    """
    CREATE TABLE IF NOT EXISTS path_days (
        instrument TEXT NOT NULL,
        day TEXT NOT NULL,
        source_id TEXT NOT NULL,
        state TEXT NOT NULL,
        bid_payload_id INTEGER,
        ask_payload_id INTEGER,
        expected_minutes INTEGER NOT NULL,
        observed_minutes INTEGER NOT NULL,
        active_minutes INTEGER NOT NULL DEFAULT 0,
        quality_state TEXT NOT NULL,
        segment_id TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        note TEXT,
        PRIMARY KEY (instrument, day, source_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS path_months (
        instrument TEXT NOT NULL,
        month TEXT NOT NULL,
        source_id TEXT NOT NULL,
        state TEXT NOT NULL,
        bid_payload_id INTEGER,
        ask_payload_id INTEGER,
        expected_hours INTEGER NOT NULL,
        observed_hours INTEGER NOT NULL,
        active_hours INTEGER NOT NULL DEFAULT 0,
        quality_state TEXT NOT NULL,
        segment_id TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        note TEXT,
        PRIMARY KEY (instrument, month, source_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS market_path (
        instrument TEXT NOT NULL,
        timeframe TEXT NOT NULL,
        ts INTEGER NOT NULL,
        bo REAL NOT NULL, bh REAL NOT NULL, bl REAL NOT NULL, bc REAL NOT NULL,
        ao REAL NOT NULL, ah REAL NOT NULL, al REAL NOT NULL, ac REAL NOT NULL,
        volume REAL NOT NULL,
        active INTEGER NOT NULL,
        minutes INTEGER NOT NULL,
        source_id TEXT NOT NULL,
        quality_state TEXT NOT NULL,
        segment_id TEXT NOT NULL,
        PRIMARY KEY (instrument, timeframe, ts, source_id)
    ) WITHOUT ROWID
    """,
    FETCH_LOG_DDL,
)


def get_path_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(PATH_DB, timeout=60)
    connection.row_factory = sqlite3.Row
    return connection


_initialized: set[str] = set()


def initialize_path_archive() -> None:
    key = str(PATH_DB)

    if key in _initialized and PATH_DB.exists():
        return

    with get_path_connection() as connection:
        connection.execute("PRAGMA journal_mode=WAL")

        for statement in _SCHEMA:
            connection.execute(statement)

        connection.commit()

    _initialized.add(key)


# ----------------------------------------------------------------------
# raw payloads and fetch log
# ----------------------------------------------------------------------

def store_payload(**fields) -> StoredPayload:
    """Store the exact payload in the archive (see src/raw_archive.py)."""
    initialize_path_archive()

    with get_path_connection() as connection:
        return raw_archive.store_payload(connection, **fields)


def load_payload(payload_id: int) -> tuple[bytes, str]:
    """Return (content, sha256) and verify the hash (module 124 replay)."""
    initialize_path_archive()

    with get_path_connection() as connection:
        return raw_archive.load_payload(connection, payload_id)


def log_fetch(
    source_id: str,
    endpoint: str,
    result: str,
    instrument: str | None = None,
    http_status: int | None = None,
    detail: str | None = None,
) -> None:
    initialize_path_archive()

    with get_path_connection() as connection:
        raw_archive.log_fetch(connection, source_id, endpoint, result, instrument, http_status, detail)


# ----------------------------------------------------------------------
# session helpers
# ----------------------------------------------------------------------

def day_start_ts(day: date) -> int:
    return int(datetime(day.year, day.month, day.day, tzinfo=UTC).timestamp())


@lru_cache(maxsize=4096)
def session_minutes_of_day(day: date) -> tuple[int, ...]:
    """Epoch seconds of every minute of the UTC day inside the FX session."""
    start = day_start_ts(day)
    minutes = []

    # the session changes state at most a few times per day; test hourly and
    # only go minute by minute inside hours that contain a boundary
    for hour in range(24):
        hour_start = start + hour * 3600
        first = is_fx_market_open(datetime.fromtimestamp(hour_start, tz=UTC))
        last = is_fx_market_open(datetime.fromtimestamp(hour_start + 3540, tz=UTC))

        if first and last:
            minutes.extend(range(hour_start, hour_start + 3600, MINUTE))
        elif first or last:
            for ts in range(hour_start, hour_start + 3600, MINUTE):
                if is_fx_market_open(datetime.fromtimestamp(ts, tz=UTC)):
                    minutes.append(ts)

    return tuple(minutes)


def is_session_minute(ts: int) -> bool:
    return is_fx_market_open(datetime.fromtimestamp(ts, tz=UTC))


def bucket_start(ts: int, timeframe: str) -> int:
    """Open time of the bar of `timeframe` that contains the minute `ts`."""
    size = TIMEFRAME_SECONDS[timeframe]

    if timeframe not in NY_ALIGNED:
        return ts - ts % size

    moment = datetime.fromtimestamp(ts, tz=UTC)
    # shift so that 17:00 New York becomes midnight of the shifted clock
    shift = int(new_york_utc_offset(moment).total_seconds()) + 7 * 3600
    shifted = ts + shift
    return shifted - shifted % size - shift


def trading_date(ts: int) -> date:
    """Trading date of the daily bar containing ts (New York 17:00 close)."""
    moment = datetime.fromtimestamp(ts, tz=UTC)
    shifted = moment + new_york_utc_offset(moment) + timedelta(hours=7)
    return shifted.date()


# ----------------------------------------------------------------------
# day index
# ----------------------------------------------------------------------

def set_day(
    *,
    instrument: str,
    day: date,
    source_id: str,
    state: str,
    bid_payload_id: int | None,
    ask_payload_id: int | None,
    expected_minutes: int,
    observed_minutes: int,
    active_minutes: int,
    quality_state: str,
    note: str | None = None,
) -> None:
    if state not in DAY_STATES:
        raise ValueError(f"state must be one of {DAY_STATES}")

    initialize_path_archive()
    segment_id = f"SEG-{source_id}-{instrument.replace('/', '')}-{day:%Y%m%d}"

    with get_path_connection() as connection:
        connection.execute(
            """
            INSERT INTO path_days (
                instrument, day, source_id, state, bid_payload_id,
                ask_payload_id, expected_minutes, observed_minutes,
                active_minutes, quality_state, segment_id, updated_at, note
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (instrument, day, source_id) DO UPDATE SET
                state = excluded.state,
                bid_payload_id = excluded.bid_payload_id,
                ask_payload_id = excluded.ask_payload_id,
                expected_minutes = excluded.expected_minutes,
                observed_minutes = excluded.observed_minutes,
                active_minutes = excluded.active_minutes,
                quality_state = excluded.quality_state,
                updated_at = excluded.updated_at,
                note = excluded.note
            WHERE path_days.state != 'COMPLETE'
            """,
            (
                instrument,
                day.isoformat(),
                source_id,
                state,
                bid_payload_id,
                ask_payload_id,
                expected_minutes,
                observed_minutes,
                active_minutes,
                quality_state,
                segment_id,
                now_iso(),
                note,
            ),
        )
        connection.commit()


def get_day(instrument: str, day: date, source_id: str) -> dict | None:
    initialize_path_archive()

    with get_path_connection() as connection:
        row = connection.execute(
            "SELECT * FROM path_days WHERE instrument = ? AND day = ? AND source_id = ?",
            (instrument, day.isoformat(), source_id),
        ).fetchone()

    return dict(row) if row else None


def list_days(
    instrument: str,
    start: date | None = None,
    end: date | None = None,
    source_id: str | None = None,
) -> list[dict]:
    initialize_path_archive()
    query = "SELECT * FROM path_days WHERE instrument = ?"
    params: list = [instrument]

    if start is not None:
        query += " AND day >= ?"
        params.append(start.isoformat())

    if end is not None:
        query += " AND day <= ?"
        params.append(end.isoformat())

    if source_id is not None:
        query += " AND source_id = ?"
        params.append(source_id)

    query += " ORDER BY day"

    with get_path_connection() as connection:
        return [dict(r) for r in connection.execute(query, params)]


# ----------------------------------------------------------------------
# minutes (decoded on demand from payloads)
# ----------------------------------------------------------------------

@lru_cache(maxsize=64)
def _decoded_day(instrument: str, day_iso: str, bid_id: int, ask_id: int) -> tuple[Bar, ...]:
    from src.sources.dukascopy import merge_sides, decode_minute_candles

    day = date.fromisoformat(day_iso)
    bid_content, _ = load_payload(bid_id)
    ask_content, _ = load_payload(ask_id)
    start = day_start_ts(day)
    bids = decode_minute_candles(bid_content, instrument, start)
    asks = decode_minute_candles(ask_content, instrument, start)
    session = set(session_minutes_of_day(day))
    return tuple(b for b in merge_sides(bids, asks) if b.ts in session)


@lru_cache(maxsize=32)
def _fxcm_week(instrument: str, payload_id: int) -> tuple[Bar, ...]:
    from src.sources.fxcm import decode_week, fill_week

    content, _ = load_payload(payload_id)
    return tuple(fill_week(*decode_week(content, instrument)))


def day_minutes(instrument: str, day: date, allow_provisional: bool = True) -> tuple[Bar, ...]:
    """In-session 1-minute bid/ask bars of one UTC day ((), when not stored).

    Canonical daily candles are preferred; the provisional tick-built
    minutes (current day, src/sources/dukascopy.py) are used only when no
    canonical day exists and allow_provisional is True. Only the canonical
    source (Dukascopy): this feeds the aggregates and the live series.
    """
    return day_minutes_with_source(instrument, day, allow_provisional, second_source=False)[0]


def day_minutes_with_source(
    instrument: str,
    day: date,
    allow_provisional: bool = True,
    second_source: bool = True,
) -> tuple[tuple[Bar, ...], str | None]:
    """(minutes, source_id) of one UTC day: Dukascopy 1-minute day, then -
    with second_source - the FXCM week file (src/sources/fxcm.py), then the
    provisional Dukascopy ticks. For path checks (outcome resolution) only."""
    from src.sources.dukascopy import SOURCE_M1, SOURCE_TICK, provisional_minutes

    record = get_day(instrument, day, SOURCE_M1)

    if record and record["bid_payload_id"] and record["ask_payload_id"]:
        bars = _decoded_day(
            instrument,
            day.isoformat(),
            int(record["bid_payload_id"]),
            int(record["ask_payload_id"]),
        )
        return bars, SOURCE_M1

    if second_source:
        from src.sources.fxcm import SOURCE_FXCM_M1, decode_day

        record = get_day(instrument, day, SOURCE_FXCM_M1)

        if record and record["state"] in ("COMPLETE", "PARTIAL") and record["bid_payload_id"]:
            return decode_day(instrument, day, int(record["bid_payload_id"])), SOURCE_FXCM_M1

    if allow_provisional:
        bars = provisional_minutes(instrument, day)
        return bars, (SOURCE_TICK if bars else None)

    return (), None


def iter_minutes(
    instrument: str,
    start_ts: int,
    end_ts: int,
    allow_provisional: bool = True,
) -> Iterable[Bar]:
    """Stored 1-minute bars with start_ts <= ts < end_ts, oldest first."""
    day = datetime.fromtimestamp(start_ts, tz=UTC).date()
    last_day = datetime.fromtimestamp(max(start_ts, end_ts - 1), tz=UTC).date()

    while day <= last_day:
        for bar in day_minutes(instrument, day, allow_provisional):
            if start_ts <= bar.ts < end_ts:
                yield bar

        day += timedelta(days=1)


def aggregate(
    minutes: Iterable[Bar],
    timeframe: str,
    require_complete: bool = True,
    unit_seconds: int = MINUTE,
) -> list[Bar]:
    """Aggregate in-session bars of `unit_seconds` (1-minute by default,
    3600 for hourly input) into `timeframe` bars.

    With require_complete, a bar is produced only when every in-session
    unit of its window is present (no guessing, module 122). The newest
    window of a live series is typically incomplete and therefore omitted.
    """
    if TIMEFRAME_SECONDS[timeframe] == unit_seconds:
        return list(minutes)

    if TIMEFRAME_SECONDS[timeframe] < unit_seconds:
        raise ValueError(f"cannot build {timeframe} from {unit_seconds} s bars")

    groups: dict[int, list[Bar]] = {}

    for bar in minutes:
        groups.setdefault(bucket_start(bar.ts, timeframe), []).append(bar)

    size = TIMEFRAME_SECONDS[timeframe]
    out = []

    for start in sorted(groups):
        parts = groups[start]

        if require_complete:
            expected = sum(
                1
                for ts in range(start, start + size, unit_seconds)
                if is_session_minute(ts)
            )

            if len(parts) != expected:
                continue

        out.append(
            Bar(
                ts=start,
                bo=parts[0].bo,
                bh=max(p.bh for p in parts),
                bl=min(p.bl for p in parts),
                bc=parts[-1].bc,
                ao=parts[0].ao,
                ah=max(p.ah for p in parts),
                al=min(p.al for p in parts),
                ac=parts[-1].ac,
                volume=sum(p.volume for p in parts),
                active=sum(p.active for p in parts),
                minutes=sum(p.minutes for p in parts),
            )
        )

    return out


# ----------------------------------------------------------------------
# hourly history (one payload per month and side)
# ----------------------------------------------------------------------

def month_start_ts(year: int, month: int) -> int:
    return int(datetime(year, month, 1, tzinfo=UTC).timestamp())


def next_month(year: int, month: int) -> tuple[int, int]:
    return (year + 1, 1) if month == 12 else (year, month + 1)


@lru_cache(maxsize=512)
def session_hours_of_month(year: int, month: int) -> tuple[int, ...]:
    """Epoch seconds of every in-session hour of the month (FX session
    boundaries fall on full UTC hours)."""
    start = month_start_ts(year, month)
    end = month_start_ts(*next_month(year, month))
    return tuple(ts for ts in range(start, end, 3600) if is_session_minute(ts))


def set_month(
    *,
    instrument: str,
    year: int,
    month: int,
    source_id: str,
    state: str,
    bid_payload_id: int | None,
    ask_payload_id: int | None,
    expected_hours: int,
    observed_hours: int,
    active_hours: int,
    quality_state: str,
    note: str | None = None,
) -> None:
    if state not in DAY_STATES:
        raise ValueError(f"state must be one of {DAY_STATES}")

    initialize_path_archive()
    label = f"{year:04d}-{month:02d}"
    segment_id = f"SEG-{source_id}-{instrument.replace('/', '')}-{year:04d}{month:02d}"

    with get_path_connection() as connection:
        connection.execute(
            """
            INSERT INTO path_months (
                instrument, month, source_id, state, bid_payload_id,
                ask_payload_id, expected_hours, observed_hours, active_hours,
                quality_state, segment_id, updated_at, note
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (instrument, month, source_id) DO UPDATE SET
                state = excluded.state,
                bid_payload_id = excluded.bid_payload_id,
                ask_payload_id = excluded.ask_payload_id,
                expected_hours = excluded.expected_hours,
                observed_hours = excluded.observed_hours,
                active_hours = excluded.active_hours,
                quality_state = excluded.quality_state,
                updated_at = excluded.updated_at,
                note = excluded.note
            WHERE path_months.state != 'COMPLETE'
            """,
            (instrument, label, source_id, state, bid_payload_id, ask_payload_id,
             expected_hours, observed_hours, active_hours, quality_state,
             segment_id, now_iso(), note),
        )
        connection.commit()


def get_month(instrument: str, year: int, month: int, source_id: str) -> dict | None:
    initialize_path_archive()

    with get_path_connection() as connection:
        row = connection.execute(
            "SELECT * FROM path_months WHERE instrument = ? AND month = ? AND source_id = ?",
            (instrument, f"{year:04d}-{month:02d}", source_id),
        ).fetchone()

    return dict(row) if row else None


@lru_cache(maxsize=64)
def _decoded_month(instrument: str, year: int, month: int, bid_id: int, ask_id: int) -> tuple[Bar, ...]:
    from src.sources.dukascopy import decode_hour_candles, merge_sides

    bid_content, _ = load_payload(bid_id)
    ask_content, _ = load_payload(ask_id)
    start = month_start_ts(year, month)
    bids = decode_hour_candles(bid_content, instrument, start)
    asks = decode_hour_candles(ask_content, instrument, start)
    session = set(session_hours_of_month(year, month))
    return tuple(b for b in merge_sides(bids, asks, unit_minutes=60) if b.ts in session)


def month_hours(instrument: str, year: int, month: int, source_id: str = "DUKASCOPY_H1") -> tuple[Bar, ...]:
    record = get_month(instrument, year, month, source_id)

    if not record or not record["bid_payload_id"] or not record["ask_payload_id"]:
        return ()

    return _decoded_month(instrument, year, month, int(record["bid_payload_id"]), int(record["ask_payload_id"]))


def rebuild_hourly_aggregates(
    instrument: str,
    first: tuple[int, int],
    last: tuple[int, int],
    source_id: str = "DUKASCOPY_H1",
) -> dict:
    """Store 1h / 4h / 1d bars built from COMPLETE monthly hour files.

    Deterministic and idempotent (INSERT OR IGNORE). A 4h/1d bar is built
    only when every in-session hour of its window is present.
    """
    initialize_path_archive()
    counts = {"1h": 0, "4h": 0, "1d": 0}
    hours: list[Bar] = []
    year, month = first
    # one month before: NY-aligned bars of the first day start the evening before
    y0, m0 = (year - 1, 12) if month == 1 else (year, month - 1)
    months = [(y0, m0)]

    while (year, month) <= last:
        months.append((year, month))
        year, month = next_month(year, month)

    months.append((year, month))

    for y, m in months:
        record = get_month(instrument, y, m, source_id)

        if record and record["state"] == "COMPLETE":
            hours.extend(month_hours(instrument, y, m, source_id))

    lower = month_start_ts(*first)
    upper = month_start_ts(*next_month(*last))
    rows = []

    for timeframe in ("1h", "4h", "1d"):
        for bar in aggregate(hours, timeframe, require_complete=True, unit_seconds=3600):
            if not (lower - 86400 <= bar.ts < upper):
                continue

            moment = datetime.fromtimestamp(bar.ts, tz=UTC)
            segment = f"SEG-{source_id}-{instrument.replace('/', '')}-{moment:%Y%m}"
            rows.append((instrument, timeframe, bar.ts, *bar[1:], source_id, "VALIDATED", segment))
            counts[timeframe] += 1

    with get_path_connection() as connection:
        connection.executemany(
            """
            INSERT OR IGNORE INTO market_path (
                instrument, timeframe, ts, bo, bh, bl, bc, ao, ah, al, ac,
                volume, active, minutes, source_id, quality_state, segment_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        connection.commit()

    return counts


def store_hourly_series(instrument: str, hours: list[Bar], source_id: str) -> dict:
    """Store 1h bars and the 4h / 1d bars built from them (complete windows
    only, NY aligned) under `source_id`. For a research archive whose
    canonical source is not Dukascopy (scripts/oos_fxcm.py)."""
    initialize_path_archive()
    counts = {"1h": 0, "4h": 0, "1d": 0}
    rows = []

    for timeframe in ("1h", "4h", "1d"):
        for bar in aggregate(hours, timeframe, require_complete=True, unit_seconds=3600):
            moment = datetime.fromtimestamp(bar.ts, tz=UTC)
            segment = f"SEG-{source_id}-{instrument.replace('/', '')}-{moment:%Y%m}"
            rows.append((instrument, timeframe, bar.ts, *bar[1:], source_id, "VALIDATED", segment))
            counts[timeframe] += 1

    with get_path_connection() as connection:
        connection.executemany(
            """
            INSERT OR IGNORE INTO market_path (
                instrument, timeframe, ts, bo, bh, bl, bc, ao, ah, al, ac,
                volume, active, minutes, source_id, quality_state, segment_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        connection.commit()

    return counts


# ----------------------------------------------------------------------
# stored aggregates
# ----------------------------------------------------------------------

def rebuild_aggregates(instrument: str, first_day: date, last_day: date, source_id: str = "DUKASCOPY_M1") -> dict:
    """(Re)build the stored 15min/1h/4h/1d bars from COMPLETE canonical days.

    Deterministic and idempotent: an existing bar is kept (INSERT OR
    IGNORE). A bar is only built when all of its minutes come from
    COMPLETE days, so a PARTIAL/GAP day never produces a (wrong) bar.
    """
    initialize_path_archive()
    counts = {tf: 0 for tf in STORED_TIMEFRAMES}

    # 4h/1d buckets start the evening before (New York close), so read one
    # day more on each side
    days = {d["day"]: d for d in list_days(instrument, first_day - timedelta(days=1), last_day + timedelta(days=1), source_id)}
    complete_days = {k for k, v in days.items() if v["state"] == "COMPLETE"}

    minutes: list[Bar] = []
    day = first_day - timedelta(days=1)

    while day <= last_day + timedelta(days=1):
        if day.isoformat() in complete_days:
            minutes.extend(day_minutes(instrument, day, allow_provisional=False))

        day += timedelta(days=1)

    if not minutes:
        return counts

    lower = day_start_ts(first_day)
    upper = day_start_ts(last_day + timedelta(days=1))
    rows = []

    for timeframe in STORED_TIMEFRAMES:
        for bar in aggregate(minutes, timeframe, require_complete=True):
            # NY-aligned bars of first_day open the evening before
            if not (lower - 86400 <= bar.ts < upper):
                continue

            segment = f"SEG-{source_id}-{instrument.replace('/', '')}-{datetime.fromtimestamp(bar.ts, tz=UTC):%Y%m%d}"
            rows.append((instrument, timeframe, bar.ts, *bar[1:], source_id, "VALIDATED", segment))
            counts[timeframe] += 1

    with get_path_connection() as connection:
        connection.executemany(
            """
            INSERT OR IGNORE INTO market_path (
                instrument, timeframe, ts, bo, bh, bl, bc, ao, ah, al, ac,
                volume, active, minutes, source_id, quality_state, segment_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        connection.commit()

    return counts


def load_bars(
    instrument: str,
    timeframe: str,
    start_ts: int | None = None,
    end_ts: int | None = None,
    limit: int | None = None,
    source_id: str = "DUKASCOPY_M1",
) -> list[Bar]:
    """Bars with start_ts <= ts < end_ts, oldest first.

    Stored timeframes come from market_path; 1min/5min are decoded from the
    payloads. `limit` keeps the newest `limit` bars.
    """
    if timeframe not in ALL_TIMEFRAMES:
        raise ValueError(f"unsupported timeframe {timeframe}")

    if timeframe in ON_DEMAND_TIMEFRAMES:
        if start_ts is None or end_ts is None:
            raise ValueError("1min/5min need an explicit start_ts and end_ts")

        bars = aggregate(iter_minutes(instrument, start_ts, end_ts), timeframe)
        return bars[-limit:] if limit else bars

    initialize_path_archive()
    query = (
        "SELECT ts, bo, bh, bl, bc, ao, ah, al, ac, volume, active, minutes "
        "FROM market_path WHERE instrument = ? AND timeframe = ? AND source_id = ?"
    )
    params: list = [instrument, timeframe, source_id]

    if start_ts is not None:
        query += " AND ts >= ?"
        params.append(start_ts)

    if end_ts is not None:
        query += " AND ts < ?"
        params.append(end_ts)

    if limit:
        query += " ORDER BY ts DESC LIMIT ?"
        params.append(limit)
    else:
        query += " ORDER BY ts"

    with get_path_connection() as connection:
        bars = [Bar(*row) for row in connection.execute(query, params)]

    if limit:
        bars.reverse()

    return bars


def archive_summary(instrument: str) -> dict:
    """Counts and ranges for the run certificate (module 113)."""
    initialize_path_archive()

    with get_path_connection() as connection:
        days = connection.execute(
            """
            SELECT state, COUNT(*) AS n, MIN(day) AS first, MAX(day) AS last
            FROM path_days WHERE instrument = ? AND source_id = 'DUKASCOPY_M1' GROUP BY state
            """,
            (instrument,),
        ).fetchall()
        second = connection.execute(
            """
            SELECT state, COUNT(*) AS n, MIN(day) AS first, MAX(day) AS last
            FROM path_days WHERE instrument = ? AND source_id = 'FXCM_M1' GROUP BY state
            """,
            (instrument,),
        ).fetchall()
        months = connection.execute(
            """
            SELECT state, COUNT(*) AS n, MIN(month) AS first, MAX(month) AS last
            FROM path_months WHERE instrument = ? GROUP BY state
            """,
            (instrument,),
        ).fetchall()
        bars = connection.execute(
            """
            SELECT timeframe, source_id, COUNT(*) AS n, MIN(ts) AS first, MAX(ts) AS last
            FROM market_path WHERE instrument = ? GROUP BY timeframe, source_id
            """,
            (instrument,),
        ).fetchall()

    return {
        "days": {r["state"]: {"n": r["n"], "first": r["first"], "last": r["last"]} for r in days},
        "days_fxcm": {r["state"]: {"n": r["n"], "first": r["first"], "last": r["last"]} for r in second},
        "months": {r["state"]: {"n": r["n"], "first": r["first"], "last": r["last"]} for r in months},
        "bars": {
            f"{r['timeframe']}/{r['source_id']}": {"n": r["n"], "first": r["first"], "last": r["last"]}
            for r in bars
        },
    }


def rebuild_all(instrument: str) -> dict:
    """Rebuild every stored aggregate of an instrument from its COMPLETE
    days and months (idempotent; used after an interrupted download)."""
    counts = {"months": 0, "days": 0}
    initialize_path_archive()

    with get_path_connection() as connection:
        months = [r["month"] for r in connection.execute(
            "SELECT month FROM path_months WHERE instrument = ? AND state = 'COMPLETE' ORDER BY month",
            (instrument,))]
        days = [r["day"] for r in connection.execute(
            "SELECT day FROM path_days WHERE instrument = ? AND state = 'COMPLETE' AND source_id = 'DUKASCOPY_M1' "
            "ORDER BY day",
            (instrument,))]

    years = sorted({m[:4] for m in months})

    for year in years:
        in_year = [m for m in months if m.startswith(year)]
        first = tuple(int(x) for x in in_year[0].split("-"))
        last = tuple(int(x) for x in in_year[-1].split("-"))
        rebuild_hourly_aggregates(instrument, first, last)
        counts["months"] += len(in_year)

    if days:
        start = date.fromisoformat(days[0])
        end = date.fromisoformat(days[-1])

        while start <= end:
            chunk_end = min(end, start + timedelta(days=29))
            rebuild_aggregates(instrument, start, chunk_end)
            start = chunk_end + timedelta(days=1)

        counts["days"] = len(days)

    return counts
