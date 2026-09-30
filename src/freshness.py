from datetime import datetime, timezone

from src.database import get_connection
from src.logger import get_logger
from src.storage import get_recent_raw_bars

logger = get_logger("freshness")


def ensure_freshness_table() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS freshness_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                checked_at TEXT NOT NULL,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                source TEXT NOT NULL,
                latest_bar_time TEXT,
                age_seconds REAL,
                status TEXT NOT NULL
            )
            """
        )

        connection.commit()


def classify_age(
    age_seconds: float | None,
    fresh_threshold: float = 120.0,
    delayed_threshold: float = 300.0,
    stale_threshold: float = 900.0,
) -> str:

    if age_seconds is None:
        return "NO_DATA"

    if age_seconds <= fresh_threshold:
        return "FRESH"

    if age_seconds <= delayed_threshold:
        return "DELAYED"

    if age_seconds <= stale_threshold:
        return "STALE"

    return "STALE"


def check_freshness(
    symbol: str,
    timeframe: str = "1min",
    source: str = "TwelveData",
    fresh_threshold: float = 120.0,
    delayed_threshold: float = 300.0,
    stale_threshold: float = 900.0,
) -> dict:

    ensure_freshness_table()

    rows = get_recent_raw_bars(
        symbol=symbol,
        timeframe=timeframe,
        limit=100,
    )

    source_rows = [
        row for row in rows
        if row["source"] == source
    ]

    checked_at = datetime.now(timezone.utc)

    if not source_rows:
        status = "NO_DATA"
        latest_bar_time = None
        age_seconds = None

    else:
        latest_bar_time = source_rows[0]["bar_time"]

        latest_dt = datetime.fromisoformat(latest_bar_time)

        if latest_dt.tzinfo is None:
            latest_dt = latest_dt.replace(tzinfo=timezone.utc)

        age_seconds = (
            checked_at - latest_dt.astimezone(timezone.utc)
        ).total_seconds()

        status = classify_age(
            age_seconds=age_seconds,
            fresh_threshold=fresh_threshold,
            delayed_threshold=delayed_threshold,
            stale_threshold=stale_threshold,
        )

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO freshness_checks (
                checked_at,
                symbol,
                timeframe,
                source,
                latest_bar_time,
                age_seconds,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                checked_at.isoformat(),
                symbol,
                timeframe,
                source,
                latest_bar_time,
                age_seconds,
                status,
            ),
        )

        connection.commit()

    logger.info(
        "FRESHNESS CHECK | symbol=%s | timeframe=%s | "
        "latest=%s | age_seconds=%s | status=%s",
        symbol,
        timeframe,
        latest_bar_time,
        "None" if age_seconds is None else f"{age_seconds:.2f}",
        status,
    )

    return {
        "checked_at": checked_at,
        "symbol": symbol,
        "timeframe": timeframe,
        "source": source,
        "latest_bar_time": latest_bar_time,
        "age_seconds": age_seconds,
        "status": status,
    }


def get_recent_freshness_checks(
    symbol: str,
    timeframe: str = "1min",
    limit: int = 20,
):
    ensure_freshness_table()

    with get_connection() as connection:
        return connection.execute(
            """
            SELECT
                checked_at,
                symbol,
                timeframe,
                source,
                latest_bar_time,
                age_seconds,
                status
            FROM freshness_checks
            WHERE symbol = ?
              AND timeframe = ?
            ORDER BY checked_at DESC
            LIMIT ?
            """,
            (symbol, timeframe, limit),
        ).fetchall()
