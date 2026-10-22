from datetime import datetime
from decimal import Decimal

from src.database import get_connection


VALID_EVENT_TYPES = {
    "OPEN",
    "CLOSE",
    "RISK_CHECK",
    "AMBIGUOUS",
}

VALID_SIDES = {
    "LONG",
    "SHORT",
}


def initialize_paper_audit() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS paper_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_time TEXT NOT NULL,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                event_type TEXT NOT NULL,
                side TEXT,
                price TEXT,
                quantity TEXT,
                stop_loss TEXT,
                take_profit TEXT,
                realized_pnl TEXT,
                reason TEXT
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_paper_events_lookup
            ON paper_events(symbol, timeframe, event_time)
            """
        )

        connection.commit()


def _validate_decimal(
    value: Decimal | None,
    name: str,
    positive: bool = False,
) -> None:
    if value is None:
        return

    if positive:
        if value <= 0:
            raise ValueError(f"{name} must be > 0")
    elif value < 0:
        raise ValueError(f"{name} must be >= 0")


def record_paper_event(
    event_time: datetime,
    symbol: str,
    timeframe: str,
    event_type: str,
    side: str | None = None,
    price: Decimal | None = None,
    quantity: Decimal | None = None,
    stop_loss: Decimal | None = None,
    take_profit: Decimal | None = None,
    realized_pnl: Decimal | None = None,
    reason: str | None = None,
) -> int:
    if event_time.tzinfo is None:
        raise ValueError("event_time must contain timezone information")

    if not symbol.strip():
        raise ValueError("symbol must not be empty")

    if not timeframe.strip():
        raise ValueError("timeframe must not be empty")

    if event_type not in VALID_EVENT_TYPES:
        raise ValueError(f"unsupported event_type: {event_type}")

    if side is not None and side not in VALID_SIDES:
        raise ValueError(f"unsupported side: {side}")

    _validate_decimal(price, "price", positive=True)
    _validate_decimal(quantity, "quantity", positive=True)
    _validate_decimal(stop_loss, "stop_loss", positive=True)
    _validate_decimal(take_profit, "take_profit", positive=True)

    if event_type in {"OPEN", "CLOSE"}:
        if side is None:
            raise ValueError(f"{event_type} event requires side")

        if price is None:
            raise ValueError(f"{event_type} event requires price")

        if quantity is None:
            raise ValueError(f"{event_type} event requires quantity")

    if event_type == "OPEN":
        if realized_pnl is not None:
            raise ValueError("OPEN event must not contain realized_pnl")

    if event_type == "CLOSE":
        if realized_pnl is None:
            raise ValueError("CLOSE event requires realized_pnl")

    initialize_paper_audit()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO paper_events (
                event_time,
                symbol,
                timeframe,
                event_type,
                side,
                price,
                quantity,
                stop_loss,
                take_profit,
                realized_pnl,
                reason
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_time.isoformat(),
                symbol,
                timeframe,
                event_type,
                side,
                str(price) if price is not None else None,
                str(quantity) if quantity is not None else None,
                str(stop_loss) if stop_loss is not None else None,
                str(take_profit) if take_profit is not None else None,
                str(realized_pnl) if realized_pnl is not None else None,
                reason,
            ),
        )

        connection.commit()
        return int(cursor.lastrowid)


def get_recent_paper_events(
    symbol: str,
    timeframe: str,
    limit: int = 100,
):
    if limit <= 0:
        raise ValueError("limit must be > 0")

    with get_connection() as connection:
        return connection.execute(
            """
            SELECT
                id,
                event_time,
                symbol,
                timeframe,
                event_type,
                side,
                price,
                quantity,
                stop_loss,
                take_profit,
                realized_pnl,
                reason
            FROM paper_events
            WHERE symbol = ? AND timeframe = ?
            ORDER BY event_time DESC, id DESC
            LIMIT ?
            """,
            (symbol, timeframe, limit),
        ).fetchall()
