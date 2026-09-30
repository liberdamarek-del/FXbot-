from src.database import get_connection
from src.models import RawBar


def save_raw_bar(bar: RawBar) -> bool:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO raw_bars (
                symbol,
                timeframe,
                bar_time,
                received_at,
                open,
                high,
                low,
                close,
                source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                bar.symbol,
                bar.timeframe,
                bar.bar_time.isoformat(),
                bar.received_at.isoformat(),
                str(bar.open),
                str(bar.high),
                str(bar.low),
                str(bar.close),
                bar.source,
            ),
        )

        connection.commit()

        return cursor.rowcount == 1


def save_raw_bars(bars) -> tuple[int, int]:
    """Store many bars in ONE transaction (much faster than one commit per bar).

    Duplicates are ignored exactly like save_raw_bar (nothing is overwritten).
    All-or-nothing: if anything fails, none of the bars is stored.
    Returns (saved, duplicate).
    """
    bars = list(bars)

    if not bars:
        return 0, 0

    saved = 0

    with get_connection() as connection:
        for bar in bars:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO raw_bars (
                    symbol,
                    timeframe,
                    bar_time,
                    received_at,
                    open,
                    high,
                    low,
                    close,
                    source
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    bar.symbol,
                    bar.timeframe,
                    bar.bar_time.isoformat(),
                    bar.received_at.isoformat(),
                    str(bar.open),
                    str(bar.high),
                    str(bar.low),
                    str(bar.close),
                    bar.source,
                ),
            )

            if cursor.rowcount == 1:
                saved += 1

        connection.commit()

    return saved, len(bars) - saved


def get_recent_raw_bars(
    symbol: str,
    timeframe: str = "1min",
    limit: int = 100,
):
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT symbol, timeframe, bar_time, received_at,
                   open, high, low, close, source
            FROM raw_bars
            WHERE symbol = ? AND timeframe = ?
            ORDER BY bar_time DESC
            LIMIT ?
            """,
            (symbol, timeframe, limit),
        ).fetchall()


def start_collector_run(
    symbol: str,
    timeframe: str,
    started_at: str,
) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO collector_runs (
                started_at,
                symbol,
                timeframe,
                status
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                started_at,
                symbol,
                timeframe,
                "RUNNING",
            ),
        )

        connection.commit()

        return cursor.lastrowid


def finish_collector_run(
    run_id: int,
    finished_at: str,
    status: str,
    bars_saved: int = 0,
    bars_duplicate: int = 0,
    bars_fetched: int = 0,
    bars_closed: int = 0,
    bars_open_skipped: int = 0,
    bars_rejected: int = 0,
    error_message: str | None = None,
) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE collector_runs
            SET finished_at = ?,
                status = ?,
                bars_saved = ?,
                bars_duplicate = ?,
                bars_fetched = ?,
                bars_closed = ?,
                bars_open_skipped = ?,
                bars_rejected = ?,
                error_message = ?
            WHERE id = ?
            """,
            (
                finished_at,
                status,
                bars_saved,
                bars_duplicate,
                bars_fetched,
                bars_closed,
                bars_open_skipped,
                bars_rejected,
                error_message,
                run_id,
            ),
        )

        connection.commit()
