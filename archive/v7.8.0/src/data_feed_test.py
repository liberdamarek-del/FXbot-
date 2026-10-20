import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from logger import get_logger


API_URL = "https://api.twelvedata.com/time_series"

SYMBOL = "EUR/USD"
INTERVAL = "1min"

# Demo endpoint používáme pouze pro diagnostiku.
API_KEY = "demo"

SAMPLES = 10
SAMPLE_INTERVAL_SECONDS = 30
REQUEST_TIMEOUT_SECONDS = 10

logger = get_logger("feed_health")


def fetch_latest_bar():
    """Fetch the latest available 1-minute bar."""

    params = {
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "outputsize": 3,
        "timezone": "UTC",
        "apikey": API_KEY,
    }

    started = time.monotonic()

    response = requests.get(
        API_URL,
        params=params,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    request_duration = time.monotonic() - started

    response.raise_for_status()

    data = response.json()

    if data.get("status") != "ok":
        raise RuntimeError(f"API error: {data}")

    values = data.get("values")

    if not values:
        raise RuntimeError("API returned no values")

    latest = values[0]

    required = ("datetime", "open", "high", "low", "close")

    for field in required:
        if field not in latest:
            raise RuntimeError(f"Missing field: {field}")

    bar_time = datetime.strptime(
        latest["datetime"],
        "%Y-%m-%d %H:%M:%S",
    ).replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)

    age_seconds = (now - bar_time).total_seconds()

    return {
        "now": now,
        "bar_time": bar_time,
        "age_seconds": age_seconds,
        "request_seconds": request_duration,
        "bar": latest,
        "status_code": response.status_code,
    }


def main():
    logger.info(
        "Starting feed health test | symbol=%s interval=%s samples=%d",
        SYMBOL,
        INTERVAL,
        SAMPLES,
    )

    previous_bar_time = None
    successful = 0
    failed = 0
    ages = []
    request_times = []

    for sample in range(1, SAMPLES + 1):
        logger.info("Sample %d/%d", sample, SAMPLES)

        try:
            result = fetch_latest_bar()

            successful += 1
            ages.append(result["age_seconds"])
            request_times.append(result["request_seconds"])

            bar_time = result["bar_time"]

            if previous_bar_time is None:
                progression = "INITIAL"
            elif bar_time > previous_bar_time:
                progression = "ADVANCED"
            elif bar_time == previous_bar_time:
                progression = "UNCHANGED"
            else:
                progression = "REGRESSED"

            previous_bar_time = bar_time

            logger.info(
                "OK | bar=%s | age=%.1fs | request=%.3fs | progression=%s | close=%s",
                bar_time.isoformat(),
                result["age_seconds"],
                result["request_seconds"],
                progression,
                result["bar"]["close"],
            )

        except Exception as exc:
            failed += 1
            logger.error(
                "FAILED | %s: %s",
                type(exc).__name__,
                exc,
            )

        if sample < SAMPLES:
            time.sleep(SAMPLE_INTERVAL_SECONDS)

    print()
    print("========== FEED HEALTH SUMMARY ==========")
    print(f"Symbol:              {SYMBOL}")
    print(f"Interval:            {INTERVAL}")
    print(f"Samples:             {SAMPLES}")
    print(f"Successful:          {successful}")
    print(f"Failed:              {failed}")

    if ages:
        print(f"Min bar age:         {min(ages):.1f} s")
        print(f"Max bar age:         {max(ages):.1f} s")
        print(f"Average bar age:     {sum(ages) / len(ages):.1f} s")

    if request_times:
        print(f"Min request time:    {min(request_times):.3f} s")
        print(f"Max request time:    {max(request_times):.3f} s")
        print(
            f"Average request:     "
            f"{sum(request_times) / len(request_times):.3f} s"
        )

    print("==========================================")


if __name__ == "__main__":
    main()

