from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Callable

from src.historical_data import HistoricalBar


@dataclass(frozen=True)
class BacktestContext:
    index: int
    current_bar: HistoricalBar
    history: tuple[HistoricalBar, ...]


@dataclass(frozen=True)
class BacktestResult:
    bars_processed: int
    started_at: datetime | None
    finished_at: datetime | None


Strategy = Callable[[BacktestContext], None]


def run_backtest(
    bars: list[HistoricalBar],
    strategy: Strategy,
) -> BacktestResult:
    if not bars:
        return BacktestResult(
            bars_processed=0,
            started_at=None,
            finished_at=None,
        )

    previous_time = None

    for bar in bars:
        if bar.bar_time.tzinfo is None:
            raise ValueError(
                "Backtest bars must use timezone-aware timestamps"
            )

        if previous_time is not None and bar.bar_time <= previous_time:
            raise ValueError(
                "Backtest input must be strictly chronological"
            )

        previous_time = bar.bar_time

    for index, current_bar in enumerate(bars):
        # Only bars at or before the current bar are exposed.
        # Future bars are deliberately excluded.
        context = BacktestContext(
            index=index,
            current_bar=current_bar,
            history=tuple(bars[:index]),
        )

        strategy(context)

    return BacktestResult(
        bars_processed=len(bars),
        started_at=bars[0].bar_time,
        finished_at=bars[-1].bar_time,
    )
