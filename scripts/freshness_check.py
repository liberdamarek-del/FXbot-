import os
import sys

from src.freshness import check_freshness


SYMBOL = os.getenv("COLLECTOR_SYMBOL", "USD/JPY")
TIMEFRAME = os.getenv("COLLECTOR_TIMEFRAME", "1min")
SOURCE = os.getenv("COLLECTOR_SOURCE", "TwelveData")


def main() -> int:
    result = check_freshness(
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        source=SOURCE,
    )

    print("=" * 70)
    print("FXBOT FRESHNESS CHECK")
    print("=" * 70)
    print(f"SYMBOL:       {result['symbol']}")
    print(f"TIMEFRAME:    {result['timeframe']}")
    print(f"SOURCE:       {result['source']}")
    print(f"LATEST BAR:   {result['latest_bar_time']}")
    print(f"AGE SECONDS:  {result['age_seconds']}")
    print(f"STATUS:       {result['status']}")
    print("=" * 70)

    if result["status"] == "NO_DATA":
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
