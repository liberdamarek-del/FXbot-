from datetime import datetime, timedelta

from src.logger import get_logger
from src.storage import save_raw_bar
from src.twelve_data import TwelveDataFeed
from src.validator import validate_raw_bar

logger = get_logger("backfill")


def backfill_range(
    feed: TwelveDataFeed,
    symbol: str,
    timeframe: str,
    start: datetime,
    end: datetime,
    limit: int = 500,
) -> dict:
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("start and end must contain timezone information")

    if end <= start:
        raise ValueError("end must be after start")

    if timeframe.endswith("min"):
        interval = timedelta(minutes=int(timeframe[:-3]))
    elif timeframe.endswith("h"):
        interval = timedelta(hours=int(timeframe[:-1]))
    else:
        raise ValueError(f"Unsupported timeframe: {timeframe}")

    expected = int((end - start) / interval) + 1

    if expected > limit:
        raise ValueError(
            f"Backfill range requires {expected} bars, limit is {limit}"
        )

    bars = feed.fetch_bars_range(
        symbol,
        timeframe,
        start,
        end,
    )

    saved = 0
    duplicate = 0
    rejected = 0

    for bar in bars:
        if not (start <= bar.bar_time <= end):
            continue

        errors = validate_raw_bar(bar)

        if errors:
            rejected += 1
            logger.error(
                "REJECTED | %s | %s | %s",
                symbol,
                bar.bar_time.isoformat(),
                errors,
            )
            continue

        if save_raw_bar(bar):
            saved += 1
        else:
            duplicate += 1

    return {
        "expected": expected,
        "received": len(bars),
        "saved": saved,
        "duplicate": duplicate,
        "rejected": rejected,
    }
