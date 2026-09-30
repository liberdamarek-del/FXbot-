"""Data state of stored market bars.

Answers one question honestly: "Is the newest stored bar the bar that should
exist right now?" - taking the FX weekly session into account.

States (see project rules "never present old data as current"):

    CURRENT     the newest closed bar that should exist is stored
                (market open, within the provider publication lag)
    CLOSED      market is closed and the stored data ends at the last
                bar of the previous session - a LAST VALID SESSION SNAPSHOT,
                not a current price
    STALE       newer closed bars should exist but are not stored
    MISSING     nothing stored for this symbol/timeframe
    UNVERIFIED  the data cannot be trusted as a time reference (for example
                the newest bar lies in the future or is not closed yet)
    CONFLICT    reserved for disagreeing sources. Nothing produces it yet:
                the project currently has exactly one source.

Age is measured from the CLOSE of the newest stored bar, not from its
open time (a bar that opened 60 s ago is not yet finished).

The tolerance (default 240 s = 120 s settle delay before a bar is stored +
120 s provider publication lag) is PROVISIONAL and NEOVERENO for the real
feed; override with DATA_STATE_LAG_TOLERANCE_SECONDS.
"""

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

from src.database import get_connection
from src.gap_detector import timeframe_delta
from src.market_session import is_fx_market_open

DEFAULT_SOURCE = "TwelveData"

MAX_LOOKBACK = timedelta(days=5)


class DataState(str, Enum):
    CURRENT = "CURRENT"
    CLOSED = "CLOSED"
    STALE = "STALE"
    MISSING = "MISSING"
    UNVERIFIED = "UNVERIFIED"
    CONFLICT = "CONFLICT"


@dataclass(frozen=True)
class DataStatus:
    symbol: str
    timeframe: str
    state: DataState
    latest_bar_open: datetime | None
    expected_bar_open: datetime | None
    age_seconds: float | None
    missing_bars: int
    market_open: bool
    reason: str


def lag_tolerance_seconds() -> float:
    return float(os.getenv("DATA_STATE_LAG_TOLERANCE_SECONDS", "240"))


def _floor(moment: datetime, interval: timedelta) -> datetime:
    """Floor to the interval grid (bars are aligned to the UTC epoch)."""
    seconds = int(interval.total_seconds())
    stamp = int(moment.timestamp())
    return datetime.fromtimestamp(stamp - stamp % seconds, tz=timezone.utc)


def expected_last_bar_open(now: datetime, timeframe: str) -> datetime:
    """Open time of the newest bar that is CLOSED at `now` and belongs to
    an open market. Walks back over closed-market periods (weekend)."""
    if now.tzinfo is None:
        raise ValueError("now must contain timezone information")

    interval = timeframe_delta(timeframe)
    now = now.astimezone(timezone.utc)

    candidate = _floor(now, interval) - interval
    limit = now - MAX_LOOKBACK

    while candidate > limit:
        if is_fx_market_open(candidate):
            return candidate

        candidate -= interval

    return candidate


def count_expected_bars(
    first_open: datetime,
    last_open: datetime,
    interval: timedelta,
) -> int:
    """Number of bars in [first_open, last_open] that belong to open market."""
    if last_open < first_open:
        return 0

    count = 0
    current = first_open

    while current <= last_open:
        if is_fx_market_open(current):
            count += 1

        current += interval

    return count


def get_latest_bar_open(
    symbol: str,
    timeframe: str,
    source: str = DEFAULT_SOURCE,
) -> datetime | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT MAX(bar_time) AS latest
            FROM raw_bars
            WHERE symbol = ? AND timeframe = ? AND source = ?
            """,
            (symbol, timeframe, source),
        ).fetchone()

    if row is None or row["latest"] is None:
        return None

    latest = datetime.fromisoformat(row["latest"])

    if latest.tzinfo is None:
        latest = latest.replace(tzinfo=timezone.utc)

    return latest.astimezone(timezone.utc)


def get_earliest_bar_open(
    symbol: str,
    timeframe: str,
    source: str = DEFAULT_SOURCE,
) -> datetime | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT MIN(bar_time) AS earliest
            FROM raw_bars
            WHERE symbol = ? AND timeframe = ? AND source = ?
            """,
            (symbol, timeframe, source),
        ).fetchone()

    if row is None or row["earliest"] is None:
        return None

    earliest = datetime.fromisoformat(row["earliest"])

    if earliest.tzinfo is None:
        earliest = earliest.replace(tzinfo=timezone.utc)

    return earliest.astimezone(timezone.utc)


def classify(
    symbol: str,
    timeframe: str,
    latest_bar_open: datetime | None,
    now: datetime | None = None,
    tolerance_seconds: float | None = None,
) -> DataStatus:
    if now is None:
        now = datetime.now(timezone.utc)

    if now.tzinfo is None:
        raise ValueError("now must contain timezone information")

    now = now.astimezone(timezone.utc)

    if tolerance_seconds is None:
        tolerance_seconds = lag_tolerance_seconds()

    interval = timeframe_delta(timeframe)
    market_open = is_fx_market_open(now)
    expected = expected_last_bar_open(now, timeframe)

    def build(state, reason, age=None, missing=0):
        return DataStatus(
            symbol=symbol,
            timeframe=timeframe,
            state=state,
            latest_bar_open=latest_bar_open,
            expected_bar_open=expected,
            age_seconds=age,
            missing_bars=missing,
            market_open=market_open,
            reason=reason,
        )

    if latest_bar_open is None:
        return build(DataState.MISSING, "no bars stored")

    if latest_bar_open.tzinfo is None:
        return build(DataState.UNVERIFIED, "stored bar time has no timezone")

    latest_bar_open = latest_bar_open.astimezone(timezone.utc)
    latest_close = latest_bar_open + interval
    age = (now - latest_close).total_seconds()

    if latest_close > now:
        return build(
            DataState.UNVERIFIED,
            "newest stored bar is not closed yet or lies in the future",
            age=age,
        )

    if latest_bar_open == expected:
        if not market_open:
            return build(
                DataState.CLOSED,
                "market closed; last valid session snapshot",
                age,
            )

        # Market is open. Within continuous trading the newest closed bar
        # is younger than one interval (plus provider lag). A larger age
        # means the session has just re-opened and no bar of the new
        # session has closed yet - the stored bar is from the previous
        # session and must not be shown as current.
        if age <= interval.total_seconds() + tolerance_seconds:
            return build(DataState.CURRENT, "newest closed bar is stored", age)

        return build(
            DataState.CLOSED,
            "session just re-opened; newest bar belongs to the previous session",
            age,
        )

    if latest_bar_open > expected:
        # A bar exists after the last open-market bar (e.g. stored inside a
        # closed period). Not a time reference we can verify.
        return build(
            DataState.UNVERIFIED,
            "newest stored bar is outside the expected trading window",
            age,
        )

    missing = count_expected_bars(
        latest_bar_open + interval, expected, interval
    )

    # Provider publication lag: the OLDEST missing bar closed only a moment
    # ago (within the tolerance), so the data is merely "not published yet",
    # not overdue.
    first_missing_close = latest_bar_open + 2 * interval

    if (
        market_open
        and (now - first_missing_close).total_seconds() <= tolerance_seconds
    ):
        return build(
            DataState.CURRENT,
            "within provider publication lag",
            age,
            missing,
        )

    return build(
        DataState.STALE,
        f"{missing} closed bar(s) missing up to the expected bar",
        age,
        missing,
    )


def get_status(
    symbol: str,
    timeframe: str,
    source: str = DEFAULT_SOURCE,
    now: datetime | None = None,
) -> DataStatus:
    return classify(
        symbol=symbol,
        timeframe=timeframe,
        latest_bar_open=get_latest_bar_open(symbol, timeframe, source),
        now=now,
    )
