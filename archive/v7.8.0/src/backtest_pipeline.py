from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Callable

from src.backtest_engine import BacktestContext
from src.backtest_execution import (
    BacktestExecution,
    ExecutionResult,
    Signal,
)
from src.historical_data import HistoricalBar
from src.position_simulator import PositionSimulator
from src.trade_simulator import Trade


Strategy = Callable[[BacktestContext], Signal]


@dataclass(frozen=True)
class PipelineResult:
    bars_processed: int
    signals_generated: int
    executions: int
    trades: tuple[Trade, ...]
    started_at: datetime | None
    finished_at: datetime | None


def run_pipeline(
    bars: list[HistoricalBar],
    strategy: Strategy,
    quantity: Decimal,
    entry_cost: Decimal = Decimal("0"),
    exit_cost: Decimal = Decimal("0"),
) -> PipelineResult:
    if not bars:
        return PipelineResult(
            bars_processed=0,
            signals_generated=0,
            executions=0,
            trades=tuple(),
            started_at=None,
            finished_at=None,
        )

    simulator = PositionSimulator(
        quantity=quantity,
        entry_cost=entry_cost,
        exit_cost=exit_cost,
    )

    execution = BacktestExecution(simulator)

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

    signals_generated = 0
    executions = 0
    trades: list[Trade] = []

    for index, current_bar in enumerate(bars):
        context = BacktestContext(
            index=index,
            current_bar=current_bar,
            history=tuple(bars[:index]),
        )

        # First execute a signal generated on an earlier bar.
        execution_result: ExecutionResult = execution.execute_pending(
            context
        )

        if execution_result.executed:
            executions += 1

            if execution_result.trade is not None:
                trades.append(execution_result.trade)

        # Then evaluate the current bar and generate a new signal.
        signal = strategy(context)

        if not isinstance(signal, Signal):
            raise ValueError(
                "Strategy must return a Signal"
            )

        if signal != Signal.HOLD:
            execution.set_signal(
                signal=signal,
                signal_index=index,
            )
            signals_generated += 1

    return PipelineResult(
        bars_processed=len(bars),
        signals_generated=signals_generated,
        executions=executions,
        trades=tuple(trades),
        started_at=bars[0].bar_time,
        finished_at=bars[-1].bar_time,
    )
