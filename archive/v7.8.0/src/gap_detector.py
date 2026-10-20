from datetime import datetime, timedelta

from src.market_session import is_fx_market_open
from src.storage import get_recent_raw_bars


def timeframe_delta(timeframe: str) -> timedelta:
    if timeframe.endswith("min"):
        minutes = int(timeframe[:-3])
        return timedelta(minutes=minutes)

    if timeframe.endswith("h"):
        hours = int(timeframe[:-1])
        return timedelta(hours=hours)

    raise ValueError(f"Unsupported timeframe: {timeframe}")


def gap_contains_open_market_time(
    start: datetime,
    end: datetime,
    interval: timedelta,
) -> bool:
    current = start + interval

    while current < end:
        if is_fx_market_open(current):
            return True

        current += interval

    return False


def detect_gaps(
    symbol: str,
    timeframe: str = "1min",
    source: str = "TwelveData",
    limit: int = 100,
) -> list[dict]:
    rows = get_recent_raw_bars(symbol, timeframe, limit)
    rows = [row for row in rows if row["source"] == source]
    rows = list(reversed(rows))

    if len(rows) < 2:
        return []

    interval = timeframe_delta(timeframe)
    gaps = []

    for previous, current in zip(rows, rows[1:]):
        previous_time = datetime.fromisoformat(previous["bar_time"])
        current_time = datetime.fromisoformat(current["bar_time"])

        difference = current_time - previous_time

        if difference > interval:
            missing = int(difference // interval) - 1

            market_open_inside = gap_contains_open_market_time(
                previous_time,
                current_time,
                interval,
            )

            gaps.append(
                {
                    "from": previous["bar_time"],
                    "to": current["bar_time"],
                    "missing_bars": missing,
                    "duration_seconds": int(
                        difference.total_seconds()
                    ),
                    "market_open_inside": market_open_inside,
                    "status": (
                        "MISSING_DATA"
                        if market_open_inside
                        else "MARKET_CLOSED"
                    ),
                }
            )

    return gaps
