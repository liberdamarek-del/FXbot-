from datetime import datetime, timedelta

from src.gap_detector import detect_gaps
from src.logger import get_logger
from src.storage import save_raw_bar
from src.twelve_data import TwelveDataFeed
from src.validator import validate_raw_bar

logger = get_logger("backfill_missing_gaps")


def timeframe_delta(timeframe: str) -> timedelta:
    if timeframe.endswith("min"):
        return timedelta(minutes=int(timeframe[:-3]))

    if timeframe.endswith("h"):
        return timedelta(hours=int(timeframe[:-1]))

    raise ValueError(f"Unsupported timeframe: {timeframe}")


def expected_bar_count(
    start: datetime,
    end: datetime,
    interval: timedelta,
) -> int:
    return int((end - start) / interval) + 1


def backfill_missing_gaps(
    feed: TwelveDataFeed,
    symbol: str,
    timeframe: str = "1min",
    source: str = "TwelveData",
    limit: int = 100,
    gap_limit: int = 10,
) -> dict:
    gaps = detect_gaps(
        symbol=symbol,
        timeframe=timeframe,
        source=source,
        limit=limit if limit > 100 else 100,
    )

    selected = [
        gap
        for gap in gaps
        if gap["status"] == "MISSING_DATA"
        and gap["missing_bars"] <= gap_limit
    ]

    skipped = [
        gap
        for gap in gaps
        if gap["status"] == "MISSING_DATA"
        and gap["missing_bars"] > gap_limit
    ]

    interval = timeframe_delta(timeframe)

    saved = 0
    duplicate = 0
    rejected = 0
    expected_total = 0
    received_total = 0
    incomplete_gaps = 0

    for gap in selected:
        start = datetime.fromisoformat(gap["from"]) + interval
        end = datetime.fromisoformat(gap["to"]) - interval

        expected = expected_bar_count(
            start,
            end,
            interval,
        )

        bars = feed.fetch_bars_range(
            symbol,
            timeframe,
            start,
            end,
        )

        received = len(bars)

        expected_total += expected
        received_total += received

        if received != expected:
            incomplete_gaps += 1

            logger.error(
                "INCOMPLETE BACKFILL | symbol=%s | timeframe=%s | "
                "start=%s | end=%s | expected=%d | received=%d",
                symbol,
                timeframe,
                start.isoformat(),
                end.isoformat(),
                expected,
                received,
            )

            continue

        for bar in bars:
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
        "gaps_found": len(gaps),
        "gaps_selected": len(selected),
        "gaps_skipped": len(skipped),
        "expected_bars": expected_total,
        "received_bars": received_total,
        "incomplete_gaps": incomplete_gaps,
        "saved": saved,
        "duplicate": duplicate,
        "rejected": rejected,
        "skipped_gaps": skipped,
    }
