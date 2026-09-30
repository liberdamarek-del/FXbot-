from datetime import datetime
from decimal import Decimal

from src.database import get_connection


def initialize_paper_session_audit() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS paper_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_key TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL,
                bars_processed INTEGER NOT NULL,
                trades INTEGER NOT NULL,
                realized_pnl TEXT NOT NULL,
                final_equity TEXT NOT NULL,
                stop_loss_exits INTEGER NOT NULL,
                take_profit_exits INTEGER NOT NULL,
                ambiguous_bars INTEGER NOT NULL,
                forced_close INTEGER NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_paper_sessions_lookup
            ON paper_sessions(symbol, timeframe, created_at)
            """
        )

        connection.commit()


def save_paper_session(
    session_key: str,
    created_at: datetime,
    symbol: str,
    timeframe: str,
    started_at: datetime,
    finished_at: datetime,
    bars_processed: int,
    trades: int,
    realized_pnl: Decimal,
    final_equity: Decimal,
    stop_loss_exits: int,
    take_profit_exits: int,
    ambiguous_bars: int,
    forced_close: bool,
) -> int:
    if not session_key.strip():
        raise ValueError("session_key must not be empty")

    if created_at.tzinfo is None:
        raise ValueError("created_at must contain timezone information")

    if started_at.tzinfo is None:
        raise ValueError("started_at must contain timezone information")

    if finished_at.tzinfo is None:
        raise ValueError("finished_at must contain timezone information")

    if finished_at < started_at:
        raise ValueError("finished_at must not be before started_at")

    if not symbol.strip():
        raise ValueError("symbol must not be empty")

    if not timeframe.strip():
        raise ValueError("timeframe must not be empty")

    if bars_processed < 0:
        raise ValueError("bars_processed must be >= 0")

    if trades < 0:
        raise ValueError("trades must be >= 0")

    if stop_loss_exits < 0:
        raise ValueError("stop_loss_exits must be >= 0")

    if take_profit_exits < 0:
        raise ValueError("take_profit_exits must be >= 0")

    if ambiguous_bars < 0:
        raise ValueError("ambiguous_bars must be >= 0")

    if stop_loss_exits + take_profit_exits > trades:
        raise ValueError("risk exits cannot exceed trades")

    initialize_paper_session_audit()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO paper_sessions (
                session_key,
                created_at,
                symbol,
                timeframe,
                started_at,
                finished_at,
                bars_processed,
                trades,
                realized_pnl,
                final_equity,
                stop_loss_exits,
                take_profit_exits,
                ambiguous_bars,
                forced_close
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_key,
                created_at.isoformat(),
                symbol,
                timeframe,
                started_at.isoformat(),
                finished_at.isoformat(),
                bars_processed,
                trades,
                str(realized_pnl),
                str(final_equity),
                stop_loss_exits,
                take_profit_exits,
                ambiguous_bars,
                int(forced_close),
            ),
        )

        connection.commit()
        return int(cursor.lastrowid)


def get_paper_session(session_key: str):
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT
                id,
                session_key,
                created_at,
                symbol,
                timeframe,
                started_at,
                finished_at,
                bars_processed,
                trades,
                realized_pnl,
                final_equity,
                stop_loss_exits,
                take_profit_exits,
                ambiguous_bars,
                forced_close
            FROM paper_sessions
            WHERE session_key = ?
            """,
            (session_key,),
        ).fetchone()
