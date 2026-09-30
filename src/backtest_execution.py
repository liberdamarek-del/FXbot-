from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from src.backtest_engine import BacktestContext
from src.position_simulator import PositionSimulator
from src.trade_simulator import Side, Trade


class Signal(str, Enum):
    HOLD = "HOLD"
    ENTER_LONG = "ENTER_LONG"
    ENTER_SHORT = "ENTER_SHORT"
    EXIT = "EXIT"


@dataclass(frozen=True)
class PendingSignal:
    signal: Signal
    signal_index: int


@dataclass(frozen=True)
class ExecutionResult:
    signal: Signal
    executed: bool
    trade: Trade | None = None


class BacktestExecution:
    def __init__(
        self,
        simulator: PositionSimulator,
    ):
        self.simulator = simulator
        self.pending_signal: PendingSignal | None = None

    def set_signal(
        self,
        signal: Signal,
        signal_index: int,
    ) -> None:
        if signal_index < 0:
            raise ValueError("signal_index must be >= 0")

        if self.pending_signal is not None:
            raise ValueError("pending signal already exists")

        self.pending_signal = PendingSignal(
            signal=signal,
            signal_index=signal_index,
        )

    def execute_pending(
        self,
        context: BacktestContext,
    ) -> ExecutionResult:
        pending = self.pending_signal

        if pending is None:
            return ExecutionResult(
                signal=Signal.HOLD,
                executed=False,
            )

        # A signal generated on bar N can only execute
        # on bar N+1 or later. This explicitly prevents
        # same-bar execution.
        if context.index <= pending.signal_index:
            return ExecutionResult(
                signal=pending.signal,
                executed=False,
            )

        signal = pending.signal
        self.pending_signal = None
        bar = context.current_bar

        if signal == Signal.HOLD:
            return ExecutionResult(
                signal=signal,
                executed=False,
            )

        if signal == Signal.ENTER_LONG:
            if self.simulator.is_open:
                return ExecutionResult(
                    signal=signal,
                    executed=False,
                )

            self.simulator.open(
                side=Side.LONG,
                entry_time=bar.bar_time,
                entry_price=bar.open,
            )

            return ExecutionResult(
                signal=signal,
                executed=True,
            )

        if signal == Signal.ENTER_SHORT:
            if self.simulator.is_open:
                return ExecutionResult(
                    signal=signal,
                    executed=False,
                )

            self.simulator.open(
                side=Side.SHORT,
                entry_time=bar.bar_time,
                entry_price=bar.open,
            )

            return ExecutionResult(
                signal=signal,
                executed=True,
            )

        if signal == Signal.EXIT:
            if not self.simulator.is_open:
                return ExecutionResult(
                    signal=signal,
                    executed=False,
                )

            trade = self.simulator.close(
                exit_time=bar.bar_time,
                exit_price=bar.open,
            )

            return ExecutionResult(
                signal=signal,
                executed=True,
                trade=trade,
            )

        raise ValueError(f"Unsupported signal: {signal}")
