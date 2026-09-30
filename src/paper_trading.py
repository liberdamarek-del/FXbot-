from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from src.paper_account import PaperAccount
from src.paper_equity import EquityState, calculate_equity
from src.paper_risk import calculate_risk_levels
from src.paper_audit import record_paper_event
from src.intrabar_policy import IntrabarExit, evaluate_intrabar_exit
from src.position_simulator import PositionSimulator
from src.trade_simulator import Side, Trade


@dataclass(frozen=True)
class PaperTradingState:
    position_open: bool
    side: Side | None
    entry_price: Decimal | None
    quantity: Decimal | None
    stop_loss: Decimal | None
    take_profit: Decimal | None
    cash: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    equity: Decimal


@dataclass(frozen=True)
class RiskExitResult:
    triggered: bool
    reason: str | None
    trade: Trade | None


class PaperTradingEngine:
    def __init__(
        self,
        initial_cash: Decimal,
        quantity: Decimal,
        entry_cost: Decimal = Decimal("0"),
        exit_cost: Decimal = Decimal("0"),
        symbol: str = "UNKNOWN",
        timeframe: str = "UNKNOWN",
    ):
        if not symbol.strip():
            raise ValueError("symbol must not be empty")

        if not timeframe.strip():
            raise ValueError("timeframe must not be empty")

        self.symbol = symbol
        self.timeframe = timeframe

        self.account = PaperAccount(initial_cash)

        self.position_simulator = PositionSimulator(
            quantity=quantity,
            entry_cost=entry_cost,
            exit_cost=exit_cost,
        )

        self.stop_loss: Decimal | None = None
        self.take_profit: Decimal | None = None

    @property
    def is_open(self) -> bool:
        return self.position_simulator.is_open

    def open_position(
        self,
        side: Side,
        entry_time: datetime,
        entry_price: Decimal,
        stop_loss_distance: Decimal | None = None,
        take_profit_distance: Decimal | None = None,
    ):
        if self.is_open:
            raise ValueError("position already open")

        levels = calculate_risk_levels(
            side=side,
            entry_price=entry_price,
            stop_loss_distance=stop_loss_distance,
            take_profit_distance=take_profit_distance,
        )

        position_value = entry_price * self.position_simulator.quantity

        self.account.reserve_cash(position_value)

        try:
            position = self.position_simulator.open(
                side=side,
                entry_time=entry_time,
                entry_price=entry_price,
            )
        except Exception:
            self.account.release_cash(position_value)
            raise

        self.stop_loss = levels.stop_loss
        self.take_profit = levels.take_profit

        record_paper_event(
            event_time=entry_time,
            symbol=self.symbol,
            timeframe=self.timeframe,
            event_type="OPEN",
            side=position.side.value,
            price=position.entry_price,
            quantity=position.quantity,
            stop_loss=self.stop_loss,
            take_profit=self.take_profit,
        )

        return position

    def close_position(
        self,
        exit_time: datetime,
        exit_price: Decimal,
        reason: str = "MANUAL_CLOSE",
    ) -> Trade:
        if not self.is_open:
            raise ValueError("no position is open")

        position = self.position_simulator.position

        if position is None:
            raise ValueError("internal position state is inconsistent")

        reserved = position.entry_price * position.quantity

        trade = self.position_simulator.close(
            exit_time=exit_time,
            exit_price=exit_price,
        )

        self.account.release_cash(reserved)
        self.account.apply_realized_pnl(trade.net_pnl)

        record_paper_event(
            event_time=exit_time,
            symbol=self.symbol,
            timeframe=self.timeframe,
            event_type="CLOSE",
            side=trade.side.value,
            price=trade.exit_price,
            quantity=trade.quantity,
            realized_pnl=trade.net_pnl,
            reason=reason,
        )

        self.stop_loss = None
        self.take_profit = None

        return trade

    def check_risk_exit(
        self,
        market_time: datetime,
        market_price: Decimal,
    ) -> RiskExitResult:
        if market_time.tzinfo is None:
            raise ValueError(
                "market_time must contain timezone information"
            )

        if market_price <= 0:
            raise ValueError("market_price must be > 0")

        position = self.position_simulator.position

        if position is None:
            return RiskExitResult(
                triggered=False,
                reason=None,
                trade=None,
            )

        if position.side == Side.LONG:
            if (
                self.stop_loss is not None
                and market_price <= self.stop_loss
            ):
                trade = self.close_position(
                    exit_time=market_time,
                    exit_price=market_price,
                    reason="STOP_LOSS",
                )

                return RiskExitResult(
                    triggered=True,
                    reason="STOP_LOSS",
                    trade=trade,
                )

            if (
                self.take_profit is not None
                and market_price >= self.take_profit
            ):
                trade = self.close_position(
                    exit_time=market_time,
                    exit_price=market_price,
                    reason="TAKE_PROFIT",
                )

                return RiskExitResult(
                    triggered=True,
                    reason="TAKE_PROFIT",
                    trade=trade,
                )

        elif position.side == Side.SHORT:
            if (
                self.stop_loss is not None
                and market_price >= self.stop_loss
            ):
                trade = self.close_position(
                    exit_time=market_time,
                    exit_price=market_price,
                    reason="STOP_LOSS",
                )

                return RiskExitResult(
                    triggered=True,
                    reason="STOP_LOSS",
                    trade=trade,
                )

            if (
                self.take_profit is not None
                and market_price <= self.take_profit
            ):
                trade = self.close_position(
                    exit_time=market_time,
                    exit_price=market_price,
                    reason="TAKE_PROFIT",
                )

                return RiskExitResult(
                    triggered=True,
                    reason="TAKE_PROFIT",
                    trade=trade,
                )

        else:
            raise ValueError(
                f"Unsupported side: {position.side}"
            )

        return RiskExitResult(
            triggered=False,
            reason=None,
            trade=None,
        )

    def check_ohlc_risk_exit(
        self,
        market_time: datetime,
        bar_open: Decimal,
        bar_high: Decimal,
        bar_low: Decimal,
    ):
        if market_time.tzinfo is None:
            raise ValueError(
                "market_time must contain timezone information"
            )

        position = self.position_simulator.position

        if position is None:
            return IntrabarExit.NONE

        levels = type(
            "RiskLevelsSnapshot",
            (),
            {
                "stop_loss": self.stop_loss,
                "take_profit": self.take_profit,
            },
        )()

        return evaluate_intrabar_exit(
            side=position.side,
            bar_open=bar_open,
            bar_high=bar_high,
            bar_low=bar_low,
            levels=levels,
        )

    def equity(
        self,
        market_price: Decimal,
    ) -> EquityState:
        return calculate_equity(
            cash=self.account.cash,
            position=self.position_simulator.position,
            market_price=market_price,
        )

    def state(
        self,
        market_price: Decimal,
    ) -> PaperTradingState:
        equity = self.equity(market_price)
        position = self.position_simulator.position

        return PaperTradingState(
            position_open=position is not None,
            side=position.side if position else None,
            entry_price=position.entry_price if position else None,
            quantity=position.quantity if position else None,
            stop_loss=self.stop_loss,
            take_profit=self.take_profit,
            cash=self.account.cash,
            realized_pnl=self.account.realized_pnl,
            unrealized_pnl=equity.unrealized_pnl,
            equity=equity.equity,
        )
