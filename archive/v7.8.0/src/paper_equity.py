from dataclasses import dataclass
from decimal import Decimal

from src.position_simulator import Position
from src.trade_simulator import Side


@dataclass(frozen=True)
class EquityState:
    cash: Decimal
    unrealized_pnl: Decimal
    equity: Decimal


def calculate_unrealized_pnl(
    position: Position | None,
    market_price: Decimal,
) -> Decimal:
    if market_price <= 0:
        raise ValueError("market_price must be > 0")

    if position is None:
        return Decimal("0")

    if position.side == Side.LONG:
        return (market_price - position.entry_price) * position.quantity

    if position.side == Side.SHORT:
        return (position.entry_price - market_price) * position.quantity

    raise ValueError(f"Unsupported side: {position.side}")


def calculate_equity(
    cash: Decimal,
    position: Position | None,
    market_price: Decimal,
) -> EquityState:
    if cash < 0:
        raise ValueError("cash must be >= 0")

    unrealized_pnl = calculate_unrealized_pnl(
        position=position,
        market_price=market_price,
    )

    equity = cash + unrealized_pnl

    return EquityState(
        cash=cash,
        unrealized_pnl=unrealized_pnl,
        equity=equity,
    )
