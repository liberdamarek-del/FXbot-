from datetime import datetime, timezone

from src.bar_policy import is_closed_bar
from src.logger import get_logger
from src.storage import (
    finish_collector_run,
    save_raw_bar,
    start_collector_run,
)
from src.twelve_data import TwelveDataFeed
from src.validator import validate_raw_bar

logger = get_logger("collector")


def collect_bars(
    feed: TwelveDataFeed,
    symbol: str,
    timeframe: str = "1min",
    limit: int = 100,
) -> bool:
    started_at = datetime.now(timezone.utc).isoformat()

    run_id = start_collector_run(
        symbol,
        timeframe,
        started_at,
    )

    saved_count = 0
    duplicate_count = 0
    rejected_count = 0
    fetched_count = 0
    closed_count = 0
    skipped_open_count = 0

    try:
        bars = feed.fetch_bars(symbol, timeframe, limit)
        fetched_count = len(bars)

        now = datetime.now(timezone.utc)

        if bars:
            latest_bar = max(
                bars,
                key=lambda bar: bar.bar_time,
            )

            data_age_seconds = (
                now - latest_bar.bar_time
            ).total_seconds()

            logger.info(
                "DATA FRESHNESS | symbol=%s | timeframe=%s | "
                "latest_bar=%s | age_seconds=%.2f",
                symbol,
                timeframe,
                latest_bar.bar_time.isoformat(),
                data_age_seconds,
            )

        closed_bars = [
            bar
            for bar in bars
            if is_closed_bar(bar.bar_time, timeframe, now)
        ]

        closed_count = len(closed_bars)
        skipped_open_count = len(bars) - len(closed_bars)

        for bar in closed_bars:
            errors = validate_raw_bar(bar)

            if errors:
                rejected_count += 1

                logger.error(
                    "REJECTED | symbol=%s | timeframe=%s | bar_time=%s | errors=%s",
                    bar.symbol,
                    bar.timeframe,
                    bar.bar_time.isoformat(),
                    errors,
                )
                continue

            if save_raw_bar(bar):
                saved_count += 1

                logger.info(
                    "SAVED | symbol=%s | timeframe=%s | bar_time=%s | close=%s",
                    bar.symbol,
                    bar.timeframe,
                    bar.bar_time.isoformat(),
                    bar.close,
                )
            else:
                duplicate_count += 1

        finish_collector_run(
            run_id,
            datetime.now(timezone.utc).isoformat(),
            "SUCCESS",
            bars_saved=saved_count,
            bars_duplicate=duplicate_count,
            bars_fetched=fetched_count,
            bars_closed=closed_count,
            bars_open_skipped=skipped_open_count,
            bars_rejected=rejected_count,
        )

        logger.info(
            "COLLECTION COMPLETE | symbol=%s | timeframe=%s | "
            "fetched=%d | closed=%d | open_skipped=%d | "
            "rejected=%d | saved=%d | duplicate=%d",
            symbol,
            timeframe,
            fetched_count,
            closed_count,
            skipped_open_count,
            rejected_count,
            saved_count,
            duplicate_count,
        )

        return True

    except Exception as exc:
        logger.error(
            "COLLECTION FAILED | symbol=%s | timeframe=%s | %s: %s",
            symbol,
            timeframe,
            type(exc).__name__,
            exc,
        )

        finish_collector_run(
            run_id,
            datetime.now(timezone.utc).isoformat(),
            "FAILED",
            bars_saved=saved_count,
            bars_duplicate=duplicate_count,
            bars_fetched=fetched_count,
            bars_closed=closed_count,
            bars_open_skipped=skipped_open_count,
            bars_rejected=rejected_count,
            error_message=f"{type(exc).__name__}: {exc}",
        )

        return False


def collect_once(
    feed: TwelveDataFeed,
    symbol: str,
    timeframe: str = "1min",
) -> bool:
    return collect_bars(
        feed=feed,
        symbol=symbol,
        timeframe=timeframe,
        limit=1,
    )
