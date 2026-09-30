from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from src.trade_simulator import Side, Trade, calculate_trade


@dataclass(frozen=True)
class Position:
    side: Side
    entry_time: datetime
    entry_price: Decimal
    quantity: Decimal


class PositionSimulator:
    def __init__(
        self,
        quantity: Decimal,
        entry_cost: Decimal = Decimal("0"),
        exit_cost: Decimal = Decimal("0"),
    ):
        if quantity <= 0:
            raise ValueError("quantity must be > 0")

        if entry_cost < 0:
            raise ValueError("entry_cost must be >= 0")

        if exit_cost < 0:
            raise ValueError("exit_cost must be >= 0")

        self.quantity = quantity
        self.entry_cost = entry_cost
        self.exit_cost = exit_cost
        self.position: Position | None = None

    def open(
        self,
        side: Side,
        entry_time: datetime,
        entry_price: Decimal,
    ) -> Position:
        if entry_time.tzinfo is None:
            raise ValueError(
                "entry_time must contain timezone information"
            )

        if self.position is not None:
            raise ValueError("position already open")

        position = Position(
            side=side,
            entry_time=entry_time,
            entry_price=entry_price,
            quantity=self.quantity,
        )

        self.position = position
        return position

    def close(
        self,
        exit_time: datetime,
        exit_price: Decimal,
    ) -> Trade:
        if exit_time.tzinfo is None:
            raise ValueError(
                "exit_time must contain timezone information"
            )

        if self.position is None:
            raise ValueError("no position is open")

        if exit_time < self.position.entry_time:
            raise ValueError(
                "exit_time must not be before entry_time"
            )

        trade = calculate_trade(
            side=self.position.side,
            entry_price=self.position.entry_price,
            exit_price=exit_price,
            quantity=self.position.quantity,
            entry_cost=self.entry_cost,
            exit_cost=self.exit_cost,
        )

        self.position = None
        return trade

    @property
    def is_open(self) -> bool:
        return self.position is not None
