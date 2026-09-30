from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from src.database import get_connection


@dataclass(frozen=True)
class HistoricalBar:
    symbol: str
    timeframe: str
    bar_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    source: str


def _parse_bar(row) -> HistoricalBar:
    return HistoricalBar(
        symbol=row["symbol"],
        timeframe=row["timeframe"],
        bar_time=datetime.fromisoformat(row["bar_time"]),
        open=Decimal(row["open"]),
        high=Decimal(row["high"]),
        low=Decimal(row["low"]),
        close=Decimal(row["close"]),
        source=row["source"],
    )


def load_bars(
    symbol: str,
    timeframe: str,
    start: datetime,
    end: datetime,
    source: str = "TwelveData",
) -> list[HistoricalBar]:
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError(
            "start and end must contain timezone information"
        )

    if end < start:
        raise ValueError("end must be >= start")

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                symbol,
                timeframe,
                bar_time,
                open,
                high,
                low,
                close,
                source
            FROM raw_bars
            WHERE symbol = ?
              AND timeframe = ?
              AND source = ?
              AND bar_time >= ?
              AND bar_time <= ?
            ORDER BY bar_time ASC
            """,
            (
                symbol,
                timeframe,
                source,
                start.isoformat(),
                end.isoformat(),
            ),
        ).fetchall()

    bars = [_parse_bar(row) for row in rows]

    previous = None

    for bar in bars:
        if bar.bar_time.tzinfo is None:
            raise ValueError(
                "Historical bar timestamp must be timezone-aware"
            )

        if previous is not None and bar.bar_time <= previous:
            raise ValueError(
                "Historical bars are not strictly chronological"
            )

        previous = bar.bar_time

    return bars
