from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class Side(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass(frozen=True)
class Trade:
    side: Side
    entry_price: Decimal
    exit_price: Decimal
    quantity: Decimal
    gross_pnl: Decimal
    costs: Decimal
    net_pnl: Decimal


def calculate_trade(
    side: Side,
    entry_price: Decimal,
    exit_price: Decimal,
    quantity: Decimal,
    entry_cost: Decimal = Decimal("0"),
    exit_cost: Decimal = Decimal("0"),
) -> Trade:
    if entry_price <= 0:
        raise ValueError("entry_price must be > 0")

    if exit_price <= 0:
        raise ValueError("exit_price must be > 0")

    if quantity <= 0:
        raise ValueError("quantity must be > 0")

    if entry_cost < 0:
        raise ValueError("entry_cost must be >= 0")

    if exit_cost < 0:
        raise ValueError("exit_cost must be >= 0")

    if side == Side.LONG:
        gross_pnl = (
            exit_price - entry_price
        ) * quantity

    elif side == Side.SHORT:
        gross_pnl = (
            entry_price - exit_price
        ) * quantity

    else:
        raise ValueError(f"Unsupported side: {side}")

    costs = entry_cost + exit_cost
    net_pnl = gross_pnl - costs

    return Trade(
        side=side,
        entry_price=entry_price,
        exit_price=exit_price,
        quantity=quantity,
        gross_pnl=gross_pnl,
        costs=costs,
        net_pnl=net_pnl,
    )
