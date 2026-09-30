"""Point-in-time storage of fundamental series (modules 4, 15, 77).

Every observation carries `available_at`: the moment the value was
publicly known. A backtest asking "what did we know at time t" gets only
observations with available_at <= t, so a later release can never leak
into an earlier decision.

available_at is derived from the observation date plus a per-series
publication lag (src/fundamental/catalog.py). The lags are deliberately
conservative (a value is treated as known later rather than earlier).

Revisions (module 15): the first value seen for an observation date is
kept. When a later download shows a different value, the change is
appended to series_revisions with the time it was seen; point-in-time
reads apply a revision only from that time on. LIMITATION: history loaded
for the first time today carries today's vintage (revisions made before
today are not visible). Market series (yields, rates, prices) are not
revised; macro releases (CPI, unemployment) can be.
"""

import bisect
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache

from src import raw_archive
from src.config import DATA_DIR
from src.raw_archive import FETCH_LOG_DDL, RAW_PAYLOADS_DDL, StoredPayload, now_iso

FUND_DB = DATA_DIR / "fundamentals.sqlite3"
UTC = timezone.utc

_SCHEMA = (
    RAW_PAYLOADS_DDL,
    FETCH_LOG_DDL,
    """
    CREATE TABLE IF NOT EXISTS series_obs (
        series_id TEXT NOT NULL,
        obs_date TEXT NOT NULL,
        value REAL NOT NULL,
        available_at INTEGER NOT NULL,
        source_id TEXT NOT NULL,
        payload_id INTEGER,
        first_seen_at TEXT NOT NULL,
        PRIMARY KEY (series_id, obs_date)
    ) WITHOUT ROWID
    """,
    """
    CREATE TABLE IF NOT EXISTS series_revisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        series_id TEXT NOT NULL,
        obs_date TEXT NOT NULL,
        old_value REAL NOT NULL,
        new_value REAL NOT NULL,
        seen_at INTEGER NOT NULL,
        payload_id INTEGER
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_series_revisions
    ON series_revisions (series_id, obs_date)
    """,
    """
    CREATE TABLE IF NOT EXISTS cot_reports (
        currency TEXT NOT NULL,
        report_date TEXT NOT NULL,
        contract_code TEXT NOT NULL,
        open_interest REAL NOT NULL,
        dealer_long REAL, dealer_short REAL,
        asset_mgr_long REAL, asset_mgr_short REAL,
        lev_money_long REAL, lev_money_short REAL,
        available_at INTEGER NOT NULL,
        payload_id INTEGER,
        PRIMARY KEY (currency, report_date)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS calendar_events (
        event_id TEXT PRIMARY KEY,
        currency TEXT NOT NULL,
        title TEXT NOT NULL,
        scheduled_at INTEGER NOT NULL,
        impact TEXT NOT NULL,
        forecast TEXT,
        previous TEXT,
        actual TEXT,
        source_id TEXT NOT NULL,
        first_seen_at INTEGER NOT NULL,
        last_seen_at INTEGER NOT NULL,
        payload_id INTEGER
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_calendar_time
    ON calendar_events (scheduled_at)
    """,
    """
    CREATE TABLE IF NOT EXISTS calendar_changes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id TEXT NOT NULL,
        field TEXT NOT NULL,
        old_value TEXT,
        new_value TEXT,
        seen_at INTEGER NOT NULL
    )
    """,
)


def get_fund_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(FUND_DB, timeout=60)
    connection.row_factory = sqlite3.Row
    return connection


_initialized: set[str] = set()


def initialize_fundamentals() -> None:
    key = str(FUND_DB)

    if key in _initialized and FUND_DB.exists():
        return

    with get_fund_connection() as connection:
        connection.execute("PRAGMA journal_mode=WAL")

        for statement in _SCHEMA:
            connection.execute(statement)

        connection.commit()

    _initialized.add(key)


def store_payload(**fields) -> StoredPayload:
    initialize_fundamentals()

    with get_fund_connection() as connection:
        return raw_archive.store_payload(connection, **fields)


def log_fetch(source_id: str, endpoint: str, result: str, instrument: str | None = None,
              http_status: int | None = None, detail: str | None = None) -> None:
    initialize_fundamentals()

    with get_fund_connection() as connection:
        raw_archive.log_fetch(connection, source_id, endpoint, result, instrument, http_status, detail)


def available_at_for(obs_date: date, lag_hours: float) -> int:
    start = datetime(obs_date.year, obs_date.month, obs_date.day, tzinfo=UTC)
    return int((start + timedelta(hours=lag_hours)).timestamp())


@dataclass
class UpsertResult:
    inserted: int = 0
    unchanged: int = 0
    revised: int = 0


def upsert_series(
    series_id: str,
    rows: list[tuple[date, float]],
    lag_hours: float,
    source_id: str,
    payload_id: int | None,
    seen_at: datetime | None = None,
) -> UpsertResult:
    """Insert new observations; record changed values as revisions."""
    initialize_fundamentals()
    seen = int((seen_at or datetime.now(UTC)).timestamp())
    result = UpsertResult()

    with get_fund_connection() as connection:
        existing = {
            r["obs_date"]: r["value"]
            for r in connection.execute(
                "SELECT obs_date, value FROM series_obs WHERE series_id = ?", (series_id,)
            )
        }
        last_revision = {
            (r["obs_date"]): r["new_value"]
            for r in connection.execute(
                "SELECT obs_date, new_value FROM series_revisions WHERE series_id = ? ORDER BY id",
                (series_id,),
            )
        }
        inserts = []
        revisions = []

        for obs_date, value in rows:
            key = obs_date.isoformat()

            if key not in existing:
                inserts.append((series_id, key, value, available_at_for(obs_date, lag_hours),
                                source_id, payload_id, now_iso()))
                existing[key] = value
                continue

            current = last_revision.get(key, existing[key])

            if abs(current - value) > 1e-9 * max(1.0, abs(value)):
                revisions.append((series_id, key, current, value, seen, payload_id))
                last_revision[key] = value
            else:
                result.unchanged += 1

        connection.executemany(
            "INSERT OR IGNORE INTO series_obs (series_id, obs_date, value, available_at, "
            "source_id, payload_id, first_seen_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            inserts,
        )
        connection.executemany(
            "INSERT INTO series_revisions (series_id, obs_date, old_value, new_value, seen_at, payload_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            revisions,
        )
        connection.commit()

    result.inserted = len(inserts)
    result.revised = len(revisions)
    load_series.cache_clear()
    return result


# ----------------------------------------------------------------------
# point-in-time reading
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class Observation:
    obs_date: date
    value: float
    available_at: int


class PointInTimeSeries:
    """All observations of one series, queryable as of any moment.

    Rows are ordered by (available_at, obs_date); with a constant lag per
    series both orders agree, so both can be searched with bisect."""

    def __init__(self, series_id: str, rows: list[tuple], revisions: list[tuple]):
        self.series_id = series_id
        self._rows = sorted(rows, key=lambda r: (r[2], r[0]))
        self._times = [r[2] for r in self._rows]
        self._dates = [date.fromisoformat(r[0]) for r in self._rows]
        self._ords = [d.toordinal() for d in self._dates]
        self._revisions: dict[str, list[tuple[int, float]]] = {}

        for obs_date, new_value, seen_at in revisions:
            self._revisions.setdefault(obs_date, []).append((seen_at, new_value))

    def __len__(self) -> int:
        return len(self._rows)

    def _value(self, index: int, t: int) -> float:
        row = self._rows[index]
        value = row[1]

        if self._revisions:
            for seen_at, new_value in self._revisions.get(row[0], ()):
                if seen_at <= t:
                    value = new_value

        return value

    def _observation(self, index: int, t: int) -> Observation:
        return Observation(self._dates[index], self._value(index, t), self._rows[index][2])

    def asof(self, t: int) -> Observation | None:
        """Newest observation that was publicly known at time t."""
        index = bisect.bisect_right(self._times, t) - 1
        return None if index < 0 else self._observation(index, t)

    def history(self, t: int, count: int) -> list[Observation]:
        """The last `count` observations known at time t, oldest first."""
        end = bisect.bisect_right(self._times, t)
        return [self._observation(k, t) for k in range(max(0, end - count), end)]

    def asof_date(self, t: int, obs_on_or_before: date) -> Observation | None:
        """Value for the latest observation date <= obs_on_or_before known at t."""
        end = bisect.bisect_right(self._times, t)

        if end == 0:
            return None

        index = bisect.bisect_right(self._ords, obs_on_or_before.toordinal(), 0, end) - 1
        return None if index < 0 else self._observation(index, t)

    def last(self) -> Observation | None:
        return self.asof(2**62)


@lru_cache(maxsize=256)
def load_series(series_id: str) -> PointInTimeSeries:
    initialize_fundamentals()

    with get_fund_connection() as connection:
        rows = [
            (r["obs_date"], r["value"], r["available_at"])
            for r in connection.execute(
                "SELECT obs_date, value, available_at FROM series_obs WHERE series_id = ?",
                (series_id,),
            )
        ]
        revisions = [
            (r["obs_date"], r["new_value"], r["seen_at"])
            for r in connection.execute(
                "SELECT obs_date, new_value, seen_at FROM series_revisions WHERE series_id = ? ORDER BY id",
                (series_id,),
            )
        ]

    return PointInTimeSeries(series_id, rows, revisions)


def series_summary() -> list[dict]:
    initialize_fundamentals()

    with get_fund_connection() as connection:
        return [
            dict(r)
            for r in connection.execute(
                "SELECT series_id, COUNT(*) AS n, MIN(obs_date) AS first, MAX(obs_date) AS last, "
                "MAX(available_at) AS last_available, MAX(first_seen_at) AS last_download "
                "FROM series_obs GROUP BY series_id ORDER BY series_id"
            )
        ]
