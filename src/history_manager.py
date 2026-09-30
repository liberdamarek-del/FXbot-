import os
from datetime import datetime, timedelta

from src.database import initialize_database
from src.gap_detector import detect_gaps, timeframe_delta
from src.logger import get_logger
from src.storage import save_raw_bar
from src.twelve_data import TwelveDataFeed
from src.validator import validate_raw_bar

logger = get_logger("history_manager")

DEFAULT_SYMBOL = "USD/JPY"
DEFAULT_TIMEFRAME = "1min"
DEFAULT_SOURCE = "TwelveData"

DEFAULT_GAP_LIMIT = int(
    os.getenv("HISTORY_GAP_LIMIT", "1000")
)
DEFAULT_CHUNK_BARS = int(
    os.getenv("HISTORY_CHUNK_BARS", "100")
)
DEFAULT_MAX_GAPS = int(
    os.getenv("HISTORY_MAX_GAPS", "20")
)


def parse_list(value: str) -> list[str]:
    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]


def build_instruments() -> list[tuple[str, str]]:
    symbols_value = os.getenv(
        "COLLECTOR_SYMBOLS",
        os.getenv("COLLECTOR_SYMBOL", DEFAULT_SYMBOL),
    )

    timeframes_value = os.getenv(
        "COLLECTOR_TIMEFRAMES",
        os.getenv("COLLECTOR_TIMEFRAME", DEFAULT_TIMEFRAME),
    )

    symbols = parse_list(symbols_value)
    timeframes = parse_list(timeframes_value)

    if not symbols:
        raise ValueError(
            "COLLECTOR_SYMBOLS must contain at least one symbol"
        )

    if not timeframes:
        raise ValueError(
            "COLLECTOR_TIMEFRAMES must contain at least one timeframe"
        )

    return [
        (symbol, timeframe)
        for symbol in symbols
        for timeframe in timeframes
    ]


def expected_count(
    start: datetime,
    end: datetime,
    interval: timedelta,
) -> int:
    if end < start:
        return 0

    return int((end - start) / interval) + 1


def repair_gap(
    feed: TwelveDataFeed,
    symbol: str,
    timeframe: str,
    gap: dict,
    chunk_bars: int = DEFAULT_CHUNK_BARS,
) -> dict:
    if gap["status"] != "MISSING_DATA":
        return {
            "status": "SKIPPED",
            "reason": gap["status"],
            "expected": 0,
            "received": 0,
            "saved": 0,
            "duplicate": 0,
            "rejected": 0,
        }

    if chunk_bars <= 0:
        raise ValueError("chunk_bars must be > 0")

    interval = timeframe_delta(timeframe)

    gap_start = datetime.fromisoformat(
        gap["from"]
    ) + interval

    gap_end = datetime.fromisoformat(
        gap["to"]
    ) - interval

    expected = expected_count(
        gap_start,
        gap_end,
        interval,
    )

    received = 0
    saved = 0
    duplicate = 0
    rejected = 0

    current = gap_start

    while current <= gap_end:
        chunk_end = min(
            current + interval * (chunk_bars - 1),
            gap_end,
        )

        fetch_end = chunk_end

        # Twelve Data requires end > start.
        # For a single-bar request, request one interval wider
        # and keep only the requested bar.
        if current == chunk_end:
            fetch_end = chunk_end + interval

        try:
            bars = feed.fetch_bars_range(
                symbol,
                timeframe,
                current,
                fetch_end,
            )
        except Exception as exc:
            logger.error(
                "HISTORY BACKFILL API FAILURE | "
                "symbol=%s | timeframe=%s | "
                "start=%s | end=%s | error=%s",
                symbol,
                timeframe,
                current.isoformat(),
                fetch_end.isoformat(),
                exc,
            )

            return {
                "status": "FAILED",
                "reason": "API_ERROR",
                "expected": expected,
                "received": received,
                "saved": saved,
                "duplicate": duplicate,
                "rejected": rejected,
            }

        bars = [
            bar
            for bar in bars
            if current <= bar.bar_time <= chunk_end
        ]

        chunk_expected = expected_count(
            current,
            chunk_end,
            interval,
        )

        if len(bars) != chunk_expected:
            logger.error(
                "HISTORY BACKFILL INCOMPLETE | "
                "symbol=%s | timeframe=%s | "
                "start=%s | end=%s | "
                "expected=%d | received=%d",
                symbol,
                timeframe,
                current.isoformat(),
                chunk_end.isoformat(),
                chunk_expected,
                len(bars),
            )

            return {
                "status": "FAILED",
                "reason": "INCOMPLETE_CHUNK",
                "expected": expected,
                "received": received + len(bars),
                "saved": saved,
                "duplicate": duplicate,
                "rejected": rejected,
            }

        received += len(bars)

        for bar in bars:
            errors = validate_raw_bar(bar)

            if errors:
                rejected += 1

                logger.error(
                    "HISTORY BACKFILL REJECTED | "
                    "symbol=%s | timeframe=%s | "
                    "bar_time=%s | errors=%s",
                    symbol,
                    timeframe,
                    bar.bar_time.isoformat(),
                    errors,
                )

                continue

            if save_raw_bar(bar):
                saved += 1
            else:
                duplicate += 1

        current = chunk_end + interval

    if received != expected:
        return {
            "status": "FAILED",
            "reason": "COUNT_MISMATCH",
            "expected": expected,
            "received": received,
            "saved": saved,
            "duplicate": duplicate,
            "rejected": rejected,
        }

    if rejected:
        return {
            "status": "FAILED",
            "reason": "REJECTED_BARS",
            "expected": expected,
            "received": received,
            "saved": saved,
            "duplicate": duplicate,
            "rejected": rejected,
        }

    return {
        "status": "REPAIRED",
        "reason": "OK",
        "expected": expected,
        "received": received,
        "saved": saved,
        "duplicate": duplicate,
        "rejected": rejected,
    }


def check_and_repair(
    feed: TwelveDataFeed,
    symbol: str,
    timeframe: str = DEFAULT_TIMEFRAME,
    source: str = DEFAULT_SOURCE,
    gap_limit: int = DEFAULT_GAP_LIMIT,
    chunk_bars: int = DEFAULT_CHUNK_BARS,
    max_gaps: int = DEFAULT_MAX_GAPS,
) -> dict:
    if gap_limit <= 0:
        raise ValueError("gap_limit must be > 0")

    if max_gaps < 0:
        raise ValueError("max_gaps must be >= 0")

    gaps = detect_gaps(
        symbol=symbol,
        timeframe=timeframe,
        source=source,
        limit=gap_limit,
    )

    missing_gaps = [
        gap
        for gap in gaps
        if gap["status"] == "MISSING_DATA"
    ]

    market_closed_gaps = [
        gap
        for gap in gaps
        if gap["status"] == "MARKET_CLOSED"
    ]

    limited_missing_gaps = missing_gaps[:max_gaps]

    result = {
        "symbol": symbol,
        "timeframe": timeframe,
        "gaps_found": len(gaps),
        "missing_gaps": len(missing_gaps),
        "market_closed_gaps": len(market_closed_gaps),
        "repair_limit": max_gaps,
        "repair_candidates": len(limited_missing_gaps),
        "repaired": 0,
        "failed": 0,
        "skipped": len(market_closed_gaps),
        "bars_saved": 0,
        "bars_duplicate": 0,
        "bars_rejected": 0,
    }

    for gap_number, gap in enumerate(
        limited_missing_gaps,
        start=1,
    ):
        logger.info(
            "HISTORY GAP REPAIR | "
            "gap=%d/%d | symbol=%s | timeframe=%s | "
            "from=%s | to=%s | missing=%d",
            gap_number,
            len(limited_missing_gaps),
            symbol,
            timeframe,
            gap["from"],
            gap["to"],
            gap["missing_bars"],
        )

        repair = repair_gap(
            feed=feed,
            symbol=symbol,
            timeframe=timeframe,
            gap=gap,
            chunk_bars=chunk_bars,
        )

        result["bars_saved"] += repair["saved"]
        result["bars_duplicate"] += repair["duplicate"]
        result["bars_rejected"] += repair["rejected"]

        if repair["status"] == "REPAIRED":
            result["repaired"] += 1
        else:
            result["failed"] += 1

    remaining_gaps = detect_gaps(
        symbol=symbol,
        timeframe=timeframe,
        source=source,
        limit=gap_limit,
    )

    remaining_missing = [
        gap
        for gap in remaining_gaps
        if gap["status"] == "MISSING_DATA"
    ]

    result["remaining_missing_gaps"] = len(
        remaining_missing
    )

    result["unprocessed_missing_gaps"] = max(
        0,
        len(missing_gaps) - len(limited_missing_gaps),
    )

    result["verification"] = (
        "PASS"
        if not remaining_missing
        else "FAIL"
    )

    logger.info(
        "HISTORY INTEGRITY RESULT | "
        "symbol=%s | timeframe=%s | "
        "missing_before=%d | repaired=%d | "
        "failed=%d | remaining_missing=%d | "
        "verification=%s",
        symbol,
        timeframe,
        result["missing_gaps"],
        result["repaired"],
        result["failed"],
        result["remaining_missing_gaps"],
        result["verification"],
    )

    return result


def check_all(
    feed: TwelveDataFeed,
    instruments: list[tuple[str, str]] | None = None,
    source: str = DEFAULT_SOURCE,
    gap_limit: int = DEFAULT_GAP_LIMIT,
    chunk_bars: int = DEFAULT_CHUNK_BARS,
    max_gaps: int = DEFAULT_MAX_GAPS,
) -> dict:
    if instruments is None:
        instruments = build_instruments()

    results = []

    for symbol, timeframe in instruments:
        logger.info(
            "HISTORY INTEGRITY CHECK | "
            "symbol=%s | timeframe=%s",
            symbol,
            timeframe,
        )

        result = check_and_repair(
            feed=feed,
            symbol=symbol,
            timeframe=timeframe,
            source=source,
            gap_limit=gap_limit,
            chunk_bars=chunk_bars,
            max_gaps=max_gaps,
        )

        results.append(result)

    failed = [
        result
        for result in results
        if result["verification"] != "PASS"
    ]

    summary = {
        "instruments": len(results),
        "passed": len(results) - len(failed),
        "failed": len(failed),
        "results": results,
        "verification": (
            "PASS"
            if not failed
            else "FAIL"
        ),
    }

    logger.info(
        "HISTORY GLOBAL RESULT | "
        "instruments=%d | passed=%d | failed=%d | "
        "verification=%s",
        summary["instruments"],
        summary["passed"],
        summary["failed"],
        summary["verification"],
    )

    return summary


def main() -> int:
    initialize_database()

    feed = TwelveDataFeed(
        api_key=os.getenv(
            "TWELVE_DATA_API_KEY",
            "demo",
        ),
        timeout=10,
    )

    result = check_all(feed)

    print("=" * 70)
    print("FXBOT M2 HISTORY MANAGER")
    print("=" * 70)

    for item in result["results"]:
        print(
            f'{item["symbol"]} | '
            f'{item["timeframe"]} | '
            f'missing={item["missing_gaps"]} | '
            f'repaired={item["repaired"]} | '
            f'remaining={item["remaining_missing_gaps"]} | '
            f'verification={item["verification"]}'
        )

    print("-" * 70)
    print(
        f'INSTRUMENTS: {result["instruments"]} | '
        f'PASSED: {result["passed"]} | '
        f'FAILED: {result["failed"]}'
    )
    print(f'RESULT: {result["verification"]}')
    print("=" * 70)

    return 0 if result["verification"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
