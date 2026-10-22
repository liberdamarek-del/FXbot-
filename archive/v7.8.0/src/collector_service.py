import os
import time
from datetime import datetime, timezone

from src.collector import collect_bars
from src.database import initialize_database
from src.logger import get_logger
from src.rate_limiter import CreditBudget
from src.twelve_data import TwelveDataFeed

logger = get_logger("collector_service")

DEFAULT_SYMBOL = "USD/JPY"
DEFAULT_TIMEFRAME = "1min"

FETCH_LIMIT = int(os.getenv("COLLECTOR_FETCH_LIMIT", "3"))

DEFAULT_POLL_INTERVAL_SECONDS = float(
    os.getenv("COLLECTOR_POLL_INTERVAL", "30")
)

RETRY_ATTEMPTS = int(
    os.getenv("COLLECTOR_RETRY_ATTEMPTS", "3")
)
RETRY_BASE_SECONDS = float(
    os.getenv("COLLECTOR_RETRY_BASE", "5")
)

CYCLES = int(os.getenv("COLLECTOR_CYCLES", "0"))
API_KEY = os.getenv("TWELVE_DATA_API_KEY", "demo")


def parse_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


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


def parse_poll_intervals() -> dict[str, float]:
    value = os.getenv("COLLECTOR_POLL_INTERVALS", "").strip()

    if not value:
        return {}

    intervals: dict[str, float] = {}

    for item in value.split(","):
        item = item.strip()

        if not item:
            continue

        if "=" not in item:
            raise ValueError(
                "COLLECTOR_POLL_INTERVALS entries must use timeframe=seconds"
            )

        timeframe, seconds_value = item.split("=", 1)
        timeframe = timeframe.strip()

        if not timeframe:
            raise ValueError(
                "COLLECTOR_POLL_INTERVALS contains an empty timeframe"
            )

        try:
            seconds = float(seconds_value.strip())
        except ValueError as exc:
            raise ValueError(
                f"Invalid poll interval for timeframe={timeframe}: "
                f"{seconds_value}"
            ) from exc

        if seconds <= 0:
            raise ValueError(
                f"Poll interval must be > 0 for timeframe={timeframe}"
            )

        intervals[timeframe] = seconds

    return intervals


def get_poll_interval(
    timeframe: str,
    intervals: dict[str, float],
) -> float:
    return intervals.get(
        timeframe,
        DEFAULT_POLL_INTERVAL_SECONDS,
    )


def collect_with_retry(feed, symbol, timeframe, limit):
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        logger.info(
            "COLLECTION ATTEMPT | attempt=%d/%d | "
            "symbol=%s | timeframe=%s",
            attempt,
            RETRY_ATTEMPTS,
            symbol,
            timeframe,
        )

        result = collect_bars(
            feed=feed,
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
        )

        if result:
            return True

        if attempt < RETRY_ATTEMPTS:
            delay = RETRY_BASE_SECONDS * (2 ** (attempt - 1))

            logger.warning(
                "COLLECTION RETRY WAIT | delay=%.2fs | "
                "symbol=%s | timeframe=%s",
                delay,
                symbol,
                timeframe,
            )

            time.sleep(delay)

    logger.error(
        "COLLECTION RETRIES EXHAUSTED | symbol=%s | timeframe=%s",
        symbol,
        timeframe,
    )

    return False


def run_service():
    # Create/upgrade the schema (idempotent, backs up before any migration).
    initialize_database()

    instruments = build_instruments()
    poll_intervals = parse_poll_intervals()

    feed = TwelveDataFeed(
        api_key=API_KEY,
        timeout=10,
    )

    logger.info(
        "COLLECTOR SERVICE START | instruments=%d | "
        "default_poll_interval=%.1fs | fetch_limit=%d | cycles=%d",
        len(instruments),
        DEFAULT_POLL_INTERVAL_SECONDS,
        FETCH_LIMIT,
        CYCLES,
    )

    planned_calls_per_day = sum(
        86400 / get_poll_interval(timeframe, poll_intervals)
        for _, timeframe in instruments
    )
    daily_budget = CreditBudget.from_env().per_day

    if planned_calls_per_day > daily_budget:
        logger.warning(
            "API BUDGET WARNING | planned_calls_per_day=%.0f | "
            "daily_budget=%d | polling will be throttled and the daily "
            "budget will run out; use scripts/run_updater.py (paced, "
            "max. 1 call per 120 s) or scripts/update_data.py instead",
            planned_calls_per_day,
            daily_budget,
        )

    for symbol, timeframe in instruments:
        interval = get_poll_interval(
            timeframe,
            poll_intervals,
        )

        logger.info(
            "COLLECTOR INSTRUMENT | symbol=%s | "
            "timeframe=%s | poll_interval=%.1fs",
            symbol,
            timeframe,
            interval,
        )

    next_run: dict[tuple[str, str], float] = {}

    now_monotonic = time.monotonic()

    for instrument in instruments:
        next_run[instrument] = now_monotonic

    cycle = 0
    failures = 0

    try:
        while CYCLES == 0 or cycle < CYCLES:
            cycle += 1

            cycle_started_at = datetime.now(timezone.utc)

            logger.info(
                "SERVICE CYCLE START | cycle=%d | timestamp=%s",
                cycle,
                cycle_started_at.isoformat(),
            )

            cycle_failures = 0

            for symbol, timeframe in instruments:
                instrument = (symbol, timeframe)
                current_monotonic = time.monotonic()

                if current_monotonic < next_run[instrument]:
                    continue

                success = collect_with_retry(
                    feed=feed,
                    symbol=symbol,
                    timeframe=timeframe,
                    limit=FETCH_LIMIT,
                )

                interval = get_poll_interval(
                    timeframe,
                    poll_intervals,
                )

                if success:
                    logger.info(
                        "SERVICE ITEM SUCCESS | cycle=%d | "
                        "symbol=%s | timeframe=%s | "
                        "next_poll_in=%.1fs",
                        cycle,
                        symbol,
                        timeframe,
                        interval,
                    )
                else:
                    cycle_failures += 1
                    failures += 1

                    logger.error(
                        "SERVICE ITEM FAILED | cycle=%d | "
                        "symbol=%s | timeframe=%s | "
                        "cycle_failures=%d",
                        cycle,
                        symbol,
                        timeframe,
                        cycle_failures,
                    )

                next_run[instrument] = time.monotonic() + interval

            if cycle_failures == 0:
                logger.info(
                    "SERVICE CYCLE SUCCESS | cycle=%d",
                    cycle,
                )
            else:
                logger.error(
                    "SERVICE CYCLE FAILED | cycle=%d | "
                    "cycle_failures=%d | total_failures=%d",
                    cycle,
                    cycle_failures,
                    failures,
                )

            if CYCLES == 0 or cycle < CYCLES:
                current_monotonic = time.monotonic()

                next_due = min(next_run.values())
                sleep_seconds = max(
                    0.1,
                    next_due - current_monotonic,
                )

                logger.info(
                    "SERVICE WAIT | next_poll_in=%.1fs",
                    sleep_seconds,
                )

                time.sleep(sleep_seconds)

    except KeyboardInterrupt:
        logger.info(
            "COLLECTOR SERVICE STOPPED BY USER | "
            "cycles=%d | failures=%d",
            cycle,
            failures,
        )
        return 0

    logger.info(
        "COLLECTOR SERVICE STOP | cycles=%d | failures=%d",
        cycle,
        failures,
    )

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(run_service())
