"""Derive longer timeframes from stored 1-minute bars.

Only the 1-minute bars are downloaded (they cost API credits). 5min, 15min,
1h ... are built locally from them and cost nothing.

Rules:
- a derived bar is created ONLY when every 1-minute bar of its window that
  belongs to an open market is stored ("complete window"). A partial window
  is never turned into a bar and never guessed; it is counted as
  `incomplete` (a hole in the 1-minute data) or `pending` (the newest window,
  still waiting for its last minutes),
- open = open of the first minute, close = close of the last minute,
  high = highest high, low = lowest low,
- derived bars are stored in raw_bars with their own source tag
  (`Derived1min`), so they can never be confused with, or overwrite, bars
  delivered by the provider; provenance stays visible,
- deriving is idempotent: existing derived bars are kept as they are.

Why derived bars are preferred: a provider bar fetched right after it closed
can be preliminary (observed: a 5-minute bar fetched 12 s after the close
lacked its last minute and had a wrong low and close). Derived bars are built
from 1-minute bars that already passed the settle delay.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.database import get_connection
from src.gap_detector import timeframe_delta
from src.market_session import is_fx_market_open
from src.models import RawBar
from src.storage import save_raw_bars
from src.validator import validate_raw_bar

# Only timeframes that align cleanly with hours are allowed.
SUPPORTED_TARGETS = ("5min", "10min", "15min", "30min", "1h", "2h", "4h")

DERIVED_SOURCE = "Derived1min"
SOURCE_TIMEFRAME = "1min"
PROVIDER_SOURCE = "TwelveData"

# When no explicit start is given, windows are re-checked this far before the
# newest derived bar, so a late-filled hole in the 1-minute data is picked up.
# After OLDER history was added (update_data.py --days), pass `since` far in
# the past (FULL_SCAN) so the older windows are built as well.
LOOKBACK = timedelta(days=2)
FULL_SCAN = datetime(2000, 1, 1, tzinfo=timezone.utc)


@dataclass
class DeriveResult:
    symbol: str
    timeframe: str
    created: int = 0
    existing: int = 0
    incomplete: int = 0     # windows with holes in the 1-minute data
    pending: int = 0        # newest window still waiting for its minutes
    edge: int = 0           # oldest window: the stored history starts inside it
    rejected: int = 0
    first_bar: datetime | None = None
    last_bar: datetime | None = None


def _floor(moment: datetime, interval: timedelta) -> datetime:
    seconds = int(interval.total_seconds())
    stamp = int(moment.timestamp())
    return datetime.fromtimestamp(stamp - stamp % seconds, tz=timezone.utc)


def _bounds(symbol: str, timeframe: str, source: str):
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT MIN(bar_time) AS first, MAX(bar_time) AS last
            FROM raw_bars
            WHERE symbol = ? AND timeframe = ? AND source = ?
            """,
            (symbol, timeframe, source),
        ).fetchone()

    if row is None or row["first"] is None:
        return None, None

    return (
        datetime.fromisoformat(row["first"]).astimezone(timezone.utc),
        datetime.fromisoformat(row["last"]).astimezone(timezone.utc),
    )


def derive_timeframe(
    symbol: str,
    target_timeframe: str,
    since: datetime | None = None,
    source: str = PROVIDER_SOURCE,
    derived_source: str = DERIVED_SOURCE,
    source_timeframe: str = SOURCE_TIMEFRAME,
) -> DeriveResult:
    """Build the missing derived bars of one symbol and timeframe."""
    if target_timeframe not in SUPPORTED_TARGETS:
        raise ValueError(
            f"{target_timeframe} is not supported; use one of "
            f"{', '.join(SUPPORTED_TARGETS)}"
        )

    step = timeframe_delta(source_timeframe)
    target = timeframe_delta(target_timeframe)

    if target <= step or target % step != timedelta(0):
        raise ValueError(
            f"{target_timeframe} cannot be derived from {source_timeframe}"
        )

    per_window = int(target / step)
    result = DeriveResult(symbol=symbol, timeframe=target_timeframe)

    first_minute, last_minute = _bounds(symbol, source_timeframe, source)

    if first_minute is None:
        return result

    if since is None:
        _, last_derived = _bounds(symbol, target_timeframe, derived_source)
        since = (
            max(first_minute, last_derived - LOOKBACK)
            if last_derived is not None
            else first_minute
        )

    if since.tzinfo is None:
        raise ValueError("since must contain timezone information")

    window_start = _floor(max(since, first_minute), target)

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT bar_time, received_at, open, high, low, close
            FROM raw_bars
            WHERE symbol = ? AND timeframe = ? AND source = ?
              AND bar_time >= ?
            ORDER BY bar_time ASC
            """,
            (symbol, source_timeframe, source, window_start.isoformat()),
        ).fetchall()

        existing = {
            datetime.fromisoformat(r["bar_time"]).astimezone(timezone.utc)
            for r in connection.execute(
                """
                SELECT bar_time FROM raw_bars
                WHERE symbol = ? AND timeframe = ? AND source = ?
                  AND bar_time >= ?
                """,
                (symbol, target_timeframe, derived_source, window_start.isoformat()),
            )
        }

    windows: dict[datetime, dict[datetime, object]] = {}

    for row in rows:
        minute = datetime.fromisoformat(row["bar_time"]).astimezone(timezone.utc)
        windows.setdefault(_floor(minute, target), {})[minute] = row

    newest_window = _floor(last_minute, target)
    oldest_window = _floor(first_minute, target)
    new_bars: list[RawBar] = []

    for window in sorted(windows):
        minutes = windows[window]
        expected = [
            window + step * k
            for k in range(per_window)
            if is_fx_market_open(window + step * k)
        ]

        if not expected:
            continue

        if window in existing:
            result.existing += 1
            continue

        missing = [m for m in expected if m not in minutes]

        if missing:
            if window == oldest_window and all(m < first_minute for m in missing):
                # the stored history simply begins inside this window: not a
                # hole (it is completed automatically if older bars arrive)
                result.edge += 1
            elif window == newest_window:
                result.pending += 1
            else:
                result.incomplete += 1
            continue

        parts = [minutes[m] for m in expected]

        bar = RawBar(
            symbol=symbol,
            timeframe=target_timeframe,
            bar_time=window,
            received_at=max(
                datetime.fromisoformat(p["received_at"]) for p in parts
            ),
            open=Decimal(parts[0]["open"]),
            high=max(Decimal(p["high"]) for p in parts),
            low=min(Decimal(p["low"]) for p in parts),
            close=Decimal(parts[-1]["close"]),
            source=derived_source,
        )

        if validate_raw_bar(bar):
            result.rejected += 1
            continue

        new_bars.append(bar)

    saved, duplicate = save_raw_bars(new_bars)
    result.created += saved
    result.existing += duplicate

    if new_bars and saved:
        result.first_bar = new_bars[0].bar_time
        result.last_bar = new_bars[-1].bar_time

    return result


def derive_symbol(
    symbol: str,
    target_timeframes: list[str],
    since: datetime | None = None,
    **kwargs,
) -> list[DeriveResult]:
    return [
        derive_timeframe(symbol, timeframe, since=since, **kwargs)
        for timeframe in target_timeframes
    ]
