import time
from datetime import datetime, timezone

from src.collector import collect_bars
from src.logger import get_logger
from src.twelve_data import TwelveDataFeed

logger = get_logger("collector_test_loop")

SYMBOL = "USD/JPY"
TIMEFRAME = "1min"

CYCLES = 5
INTERVAL_SECONDS = 30
FETCH_LIMIT = 3


def main() -> int:
    feed = TwelveDataFeed(
        api_key="demo",
        timeout=10,
    )

    print("=" * 70)
    print("FXBOT CONTROLLED COLLECTOR TEST")
    print("=" * 70)
    print(f"SYMBOL:       {SYMBOL}")
    print(f"TIMEFRAME:    {TIMEFRAME}")
    print(f"CYCLES:       {CYCLES}")
    print(f"INTERVAL:     {INTERVAL_SECONDS}s")
    print(f"FETCH LIMIT:  {FETCH_LIMIT}")
    print("=" * 70)

    successes = 0
    failures = 0

    for cycle in range(1, CYCLES + 1):
        started = datetime.now(timezone.utc)

        print()
        print(
            f"[CYCLE {cycle}/{CYCLES}] "
            f"{started.isoformat()}"
        )

        try:
            result = collect_bars(
                feed=feed,
                symbol=SYMBOL,
                timeframe=TIMEFRAME,
                limit=FETCH_LIMIT,
            )

            if result:
                successes += 1
                print(f"[PASS] Cycle {cycle}")
            else:
                failures += 1
                print(f"[FAIL] Cycle {cycle}")

        except Exception as exc:
            failures += 1
            logger.exception(
                "COLLECTOR TEST EXCEPTION | %s: %s",
                type(exc).__name__,
                exc,
            )
            print(
                f"[FAIL] Cycle {cycle} | "
                f"{type(exc).__name__}: {exc}"
            )

        if cycle < CYCLES:
            print(
                f"Waiting {INTERVAL_SECONDS}s..."
            )
            time.sleep(INTERVAL_SECONDS)

    print()
    print("=" * 70)
    print("COLLECTOR TEST SUMMARY")
    print("=" * 70)
    print(f"CYCLES:    {CYCLES}")
    print(f"SUCCESS:   {successes}")
    print(f"FAILURES:  {failures}")

    if failures:
        print("RESULT: FAIL")
        return 1

    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
