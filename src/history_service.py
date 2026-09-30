import os
import time
from datetime import datetime, timezone

from src.database import initialize_database
from src.history_audit import (
    finish_history_run,
    initialize_history_audit,
    start_history_run,
)
from src.history_manager import (
    DEFAULT_CHUNK_BARS,
    DEFAULT_GAP_LIMIT,
    DEFAULT_MAX_GAPS,
    build_instruments,
    check_and_repair,
)
from src.logger import get_logger
from src.twelve_data import TwelveDataFeed

logger = get_logger("history_service")

DEFAULT_INTERVAL_SECONDS = float(
    os.getenv("HISTORY_SERVICE_INTERVAL", "300")
)

CYCLES = int(
    os.getenv("HISTORY_SERVICE_CYCLES", "0")
)

MAX_INSTRUMENTS = int(
    os.getenv("HISTORY_MAX_INSTRUMENTS", "20")
)

API_KEY = os.getenv(
    "TWELVE_DATA_API_KEY",
    "demo",
)


def run_service() -> int:
    if DEFAULT_INTERVAL_SECONDS <= 0:
        raise ValueError(
            "HISTORY_SERVICE_INTERVAL must be > 0"
        )

    if CYCLES < 0:
        raise ValueError(
            "HISTORY_SERVICE_CYCLES must be >= 0"
        )

    instruments = build_instruments()

    if MAX_INSTRUMENTS <= 0:
        raise ValueError(
            "HISTORY_MAX_INSTRUMENTS must be > 0"
        )

    if len(instruments) > MAX_INSTRUMENTS:
        raise ValueError(
            "Configured instruments exceed "
            f"HISTORY_MAX_INSTRUMENTS={MAX_INSTRUMENTS}: "
            f"{len(instruments)}"
        )

    initialize_database()
    initialize_history_audit()

    feed = TwelveDataFeed(
        api_key=API_KEY,
        timeout=10,
    )

    logger.info(
        "HISTORY SERVICE START | instruments=%d | "
        "max_instruments=%d | interval=%.1fs | cycles=%d | "
        "gap_limit=%d | chunk_bars=%d | max_gaps=%d",
        len(instruments),
        MAX_INSTRUMENTS,
        DEFAULT_INTERVAL_SECONDS,
        CYCLES,
        DEFAULT_GAP_LIMIT,
        DEFAULT_CHUNK_BARS,
        DEFAULT_MAX_GAPS,
    )

    total_failures = 0
    cycle = 0

    try:
        while CYCLES == 0 or cycle < CYCLES:
            cycle += 1
            cycle_started_at = datetime.now(timezone.utc)
            cycle_failures = 0

            logger.info(
                "HISTORY SERVICE CYCLE START | "
                "cycle=%d | timestamp=%s",
                cycle,
                cycle_started_at.isoformat(),
            )

            for symbol, timeframe in instruments:
                started_at = datetime.now(timezone.utc)

                run_id = start_history_run(
                    cycle=cycle,
                    symbol=symbol,
                    timeframe=timeframe,
                    started_at=started_at.isoformat(),
                )

                try:
                    result = check_and_repair(
                        feed=feed,
                        symbol=symbol,
                        timeframe=timeframe,
                        source="TwelveData",
                        gap_limit=DEFAULT_GAP_LIMIT,
                        chunk_bars=DEFAULT_CHUNK_BARS,
                        max_gaps=DEFAULT_MAX_GAPS,
                    )

                    finish_history_run(
                        run_id=run_id,
                        finished_at=datetime.now(
                            timezone.utc
                        ).isoformat(),
                        result=result,
                    )

                    if result["verification"] == "PASS":
                        logger.info(
                            "HISTORY SERVICE ITEM PASS | "
                            "cycle=%d | symbol=%s | timeframe=%s | "
                            "missing=%d | repaired=%d | remaining=%d",
                            cycle,
                            symbol,
                            timeframe,
                            result["missing_gaps"],
                            result["repaired"],
                            result["remaining_missing_gaps"],
                        )
                    else:
                        cycle_failures += 1
                        total_failures += 1

                        logger.error(
                            "HISTORY SERVICE ITEM FAIL | "
                            "cycle=%d | symbol=%s | timeframe=%s | "
                            "remaining=%d",
                            cycle,
                            symbol,
                            timeframe,
                            result["remaining_missing_gaps"],
                        )

                except Exception as exc:
                    cycle_failures += 1
                    total_failures += 1

                    finish_history_run(
                        run_id=run_id,
                        finished_at=datetime.now(
                            timezone.utc
                        ).isoformat(),
                        result=None,
                        error_message=str(exc),
                    )

                    logger.exception(
                        "HISTORY SERVICE ITEM ERROR | "
                        "cycle=%d | symbol=%s | timeframe=%s | "
                        "error=%s",
                        cycle,
                        symbol,
                        timeframe,
                        exc,
                    )

            if cycle_failures == 0:
                logger.info(
                    "HISTORY SERVICE CYCLE SUCCESS | cycle=%d",
                    cycle,
                )
            else:
                logger.error(
                    "HISTORY SERVICE CYCLE FAILED | "
                    "cycle=%d | cycle_failures=%d | "
                    "total_failures=%d",
                    cycle,
                    cycle_failures,
                    total_failures,
                )

            if CYCLES == 0 or cycle < CYCLES:
                logger.info(
                    "HISTORY SERVICE WAIT | "
                    "next_cycle_in=%.1fs",
                    DEFAULT_INTERVAL_SECONDS,
                )
                time.sleep(DEFAULT_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        logger.info(
            "HISTORY SERVICE STOPPED BY USER | "
            "cycles=%d | failures=%d",
            cycle,
            total_failures,
        )
        return 0

    logger.info(
        "HISTORY SERVICE STOP | cycles=%d | failures=%d",
        cycle,
        total_failures,
    )

    return 0 if total_failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(run_service())
