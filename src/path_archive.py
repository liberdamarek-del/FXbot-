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

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from typing import Iterable, NamedTuple

from src.config import DATA_DIR
from src.market_session import is_fx_market_open, new_york_utc_offset

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
    active: int          # minutes with at least one tick (volume > 0)
    minutes: int         # in-session minutes the bar is built from

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
    """
    CREATE TABLE IF NOT EXISTS raw_payloads (
        payload_id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id TEXT NOT NULL,
        kind TEXT NOT NULL,
        endpoint TEXT NOT NULL,
        instrument TEXT,
        side TEXT,
        period_start INTEGER,
        period_end INTEGER,
        retrieved_at TEXT NOT NULL,
        http_status INTEGER,
        sha256 TEXT NOT NULL,
        size INTEGER NOT NULL,
        parser_version TEXT NOT NULL,
        content BLOB NOT NULL,
        UNIQUE (source_id, endpoint, sha256)
    )
    """,
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
    """
    CREATE TABLE IF NOT EXISTS fetch_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        attempted_at TEXT NOT NULL,
        source_id TEXT NOT NULL,
        endpoint TEXT NOT NULL,
        instrument TEXT,
        result TEXT NOT NULL,
        http_status INTEGER,
        detail TEXT
    )
    """,
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


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


# ----------------------------------------------------------------------
# raw payloads and fetch log
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class StoredPayload:
    payload_id: int
    sha256: str
    new: bool


def sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def store_payload(
    *,
    source_id: str,
    kind: str,
    endpoint: str,
    instrument: str | None,
    side: str | None,
    period_start: int | None,
    period_end: int | None,
    http_status: int | None,
    content: bytes,
    parser_version: str,
    retrieved_at: str | None = None,
) -> StoredPayload:
    """Store the exact payload (idempotent: same endpoint + same bytes = same row)."""
    initialize_path_archive()
    digest = sha256_hex(content)

    with get_path_connection() as connection:
        row = connection.execute(
            "SELECT payload_id FROM raw_payloads "
            "WHERE source_id = ? AND endpoint = ? AND sha256 = ?",
            (source_id, endpoint, digest),
        ).fetchone()

        if row is not None:
            return StoredPayload(int(row["payload_id"]), digest, False)

        cursor = connection.execute(
            """
            INSERT INTO raw_payloads (
                source_id, kind, endpoint, instrument, side, period_start,
                period_end, retrieved_at, http_status, sha256, size,
                parser_version, content
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_id,
                kind,
                endpoint,
                instrument,
                side,
                period_start,
                period_end,
                retrieved_at or now_iso(),
                http_status,
                digest,
                len(content),
                parser_version,
                sqlite3.Binary(content),
            ),
        )
        connection.commit()
        return StoredPayload(int(cursor.lastrowid), digest, True)


def load_payload(payload_id: int) -> tuple[bytes, str]:
    """Return (content, sha256) and verify the hash (module 124 replay)."""
    initialize_path_archive()

    with get_path_connection() as connection:
        row = connection.execute(
            "SELECT content, sha256 FROM raw_payloads WHERE payload_id = ?",
            (payload_id,),
        ).fetchone()

    if row is None:
        raise KeyError(f"payload {payload_id} not found")

    content = bytes(row["content"])

    if sha256_hex(content) != row["sha256"]:
        raise RuntimeError(
            f"payload {payload_id} hash mismatch - REPRODUCIBILITY INCOMPLETE"
        )

    return content, row["sha256"]


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
        connection.execute(
            """
            INSERT INTO fetch_log (
                attempted_at, source_id, endpoint, instrument, result,
                http_status, detail
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (now_iso(), source_id, endpoint, instrument, result, http_status,
             (detail or "")[:500]),
        )
        connection.commit()


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


def day_minutes(instrument: str, day: date, allow_provisional: bool = True) -> tuple[Bar, ...]:
    """In-session 1-minute bid/ask bars of one UTC day ((), when not stored).

    Canonical daily candles are preferred; the provisional tick-built
    minutes (current day, src/sources/dukascopy.py) are used only when no
    canonical day exists and allow_provisional is True.
    """
    from src.sources.dukascopy import SOURCE_M1, SOURCE_TICK, provisional_minutes

    record = get_day(instrument, day, SOURCE_M1)

    if record and record["bid_payload_id"] and record["ask_payload_id"]:
        return _decoded_day(
            instrument,
            day.isoformat(),
            int(record["bid_payload_id"]),
            int(record["ask_payload_id"]),
        )

    if allow_provisional:
        return provisional_minutes(instrument, day)

    return ()


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


def aggregate(minutes: Iterable[Bar], timeframe: str, require_complete: bool = True) -> list[Bar]:
    """Aggregate in-session 1-minute bars into `timeframe` bars.

    With require_complete, a bar is produced only when every in-session
    minute of its window is present (no guessing, module 122). The newest
    window of a live series is typically incomplete and therefore omitted.
    """
    if timeframe == "1min":
        return list(minutes)

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
                for ts in range(start, start + size, MINUTE)
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
                minutes=len(parts),
            )
        )

    return out


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
            FROM path_days WHERE instrument = ? GROUP BY state
            """,
            (instrument,),
        ).fetchall()
        bars = connection.execute(
            """
            SELECT timeframe, COUNT(*) AS n, MIN(ts) AS first, MAX(ts) AS last
            FROM market_path WHERE instrument = ? GROUP BY timeframe
            """,
            (instrument,),
        ).fetchall()

    return {
        "days": {r["state"]: {"n": r["n"], "first": r["first"], "last": r["last"]} for r in days},
        "bars": {r["timeframe"]: {"n": r["n"], "first": r["first"], "last": r["last"]} for r in bars},
    }
