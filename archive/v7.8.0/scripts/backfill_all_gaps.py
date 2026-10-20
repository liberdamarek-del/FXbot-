from datetime import datetime, timedelta

from src.gap_detector import detect_gaps
from src.logger import get_logger
from src.storage import save_raw_bar
from src.twelve_data import TwelveDataFeed
from src.validator import validate_raw_bar

logger = get_logger("backfill_all_gaps")


def timeframe_delta(timeframe: str) -> timedelta:
    if timeframe.endswith("min"):
        return timedelta(minutes=int(timeframe[:-3]))

    if timeframe.endswith("h"):
        return timedelta(hours=int(timeframe[:-1]))

    raise ValueError(f"Unsupported timeframe: {timeframe}")


def expected_count(
    start: datetime,
    end: datetime,
    interval: timedelta,
) -> int:
    if end < start:
        return 0

    return int((end - start) / interval) + 1


def main() -> int:
    symbol = "USD/JPY"
    timeframe = "1min"
    source = "TwelveData"

    # Maximum number of expected bars handled in one API request.
    # This keeps large historical gaps under control.
    chunk_bars = 100

    feed = TwelveDataFeed(api_key="demo")

    gaps = detect_gaps(
        symbol=symbol,
        timeframe=timeframe,
        source=source,
        limit=5000,
    )

    missing_gaps = [
        gap
        for gap in gaps
        if gap["status"] == "MISSING_DATA"
    ]

    print("=" * 70)
    print("FXBOT FULL GAP BACKFILL")
    print("=" * 70)
    print(f"SYMBOL: {symbol}")
    print(f"TIMEFRAME: {timeframe}")
    print(f"MISSING GAPS: {len(missing_gaps)}")

    if not missing_gaps:
        print("RESULT: NOTHING_TO_BACKFILL")
        return 0

    interval = timeframe_delta(timeframe)

    total_expected = 0
    total_received = 0
    total_saved = 0
    total_duplicate = 0
    total_rejected = 0
    failed_chunks = 0

    for gap_number, gap in enumerate(missing_gaps, start=1):
        gap_start = datetime.fromisoformat(gap["from"]) + interval
        gap_end = datetime.fromisoformat(gap["to"]) - interval

        gap_expected = expected_count(
            gap_start,
            gap_end,
            interval,
        )

        print()
        print("-" * 70)
        print(
            f"GAP {gap_number}/{len(missing_gaps)} | "
            f"{gap_start.isoformat()} -> {gap_end.isoformat()} | "
            f"expected={gap_expected}"
        )

        current = gap_start

        gap_received = 0
        gap_saved = 0
        gap_duplicate = 0
        gap_rejected = 0

        while current <= gap_end:
            chunk_end = min(
                current + interval * (chunk_bars - 1),
                gap_end,
            )

            chunk_expected = expected_count(
                current,
                chunk_end,
                interval,
            )

            print(
                f"  FETCH {current.isoformat()} -> "
                f"{chunk_end.isoformat()} | "
                f"expected={chunk_expected}"
            )

            # Twelve Data requires end > start.
            # For a single-bar chunk, request one interval wider and
            # keep only the strictly requested bar below.
            fetch_end = chunk_end
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
                failed_chunks += 1
                print(
                    f"  [FAIL] API request: "
                    f"{type(exc).__name__}: {exc}"
                )
                break

            # Keep only bars strictly inside the missing interval.
            bars = [
                bar
                for bar in bars
                if current <= bar.bar_time <= chunk_end
            ]

            received = len(bars)
            gap_received += received

            if received != chunk_expected:
                failed_chunks += 1

                print(
                    f"  [FAIL] INCOMPLETE CHUNK | "
                    f"expected={chunk_expected} | "
                    f"received={received}"
                )

                logger.error(
                    "INCOMPLETE BACKFILL CHUNK | "
                    "symbol=%s | timeframe=%s | "
                    "start=%s | end=%s | "
                    "expected=%d | received=%d",
                    symbol,
                    timeframe,
                    current.isoformat(),
                    chunk_end.isoformat(),
                    chunk_expected,
                    received,
                )

                # Do not save a partial chunk.
                break

            for bar in bars:
                errors = validate_raw_bar(bar)

                if errors:
                    gap_rejected += 1
                    total_rejected += 1

                    print(
                        f"  [REJECTED] "
                        f"{bar.bar_time.isoformat()} | "
                        f"{errors}"
                    )
                    continue

                if save_raw_bar(bar):
                    gap_saved += 1
                    total_saved += 1
                else:
                    gap_duplicate += 1
                    total_duplicate += 1

            print(
                f"  [OK] received={received} | "
                f"saved={gap_saved} | "
                f"duplicate={gap_duplicate} | "
                f"rejected={gap_rejected}"
            )

            current = chunk_end + interval

        total_expected += gap_expected
        total_received += gap_received

        print(
            f"GAP RESULT | expected={gap_expected} | "
            f"received={gap_received} | "
            f"saved={gap_saved} | "
            f"duplicate={gap_duplicate} | "
            f"rejected={gap_rejected}"
        )

    print()
    print("=" * 70)
    print("BACKFILL SUMMARY")
    print("=" * 70)
    print(f"EXPECTED:   {total_expected}")
    print(f"RECEIVED:   {total_received}")
    print(f"SAVED:      {total_saved}")
    print(f"DUPLICATE:  {total_duplicate}")
    print(f"REJECTED:   {total_rejected}")
    print(f"FAILED CHUNKS: {failed_chunks}")

    if failed_chunks:
        print("RESULT: PARTIAL_FAILURE")
        return 1

    if total_received != total_expected:
        print("RESULT: INCOMPLETE")
        return 1

    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
