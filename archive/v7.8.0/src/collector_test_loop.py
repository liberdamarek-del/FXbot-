import time

from src.collector import collect_once
from src.twelve_data import TwelveDataFeed


SYMBOL = "USD/JPY"
TIMEFRAME = "1min"
RUNS = 3
INTERVAL_SECONDS = 60


def main() -> None:
    feed = TwelveDataFeed("demo")

    for run in range(1, RUNS + 1):
        print(f"--- RUN {run}/{RUNS} ---")

        result = collect_once(
            feed,
            SYMBOL,
            TIMEFRAME,
        )

        print(f"RESULT: {result}")

        if run < RUNS:
            print(f"WAITING {INTERVAL_SECONDS}s...")
            time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
