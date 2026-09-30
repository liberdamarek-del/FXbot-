from dataclasses import dataclass
from decimal import Decimal

from src.trade_simulator import Side


@dataclass(frozen=True)
class RiskLevels:
    stop_loss: Decimal | None
    take_profit: Decimal | None


def calculate_risk_levels(
    side: Side,
    entry_price: Decimal,
    stop_loss_distance: Decimal | None = None,
    take_profit_distance: Decimal | None = None,
) -> RiskLevels:
    if entry_price <= 0:
        raise ValueError("entry_price must be > 0")

    if stop_loss_distance is not None and stop_loss_distance <= 0:
        raise ValueError("stop_loss_distance must be > 0")

    if take_profit_distance is not None and take_profit_distance <= 0:
        raise ValueError("take_profit_distance must be > 0")

    stop_loss = None
    take_profit = None

    if side == Side.LONG:
        if stop_loss_distance is not None:
            stop_loss = entry_price - stop_loss_distance

        if take_profit_distance is not None:
            take_profit = entry_price + take_profit_distance

    elif side == Side.SHORT:
        if stop_loss_distance is not None:
            stop_loss = entry_price + stop_loss_distance

        if take_profit_distance is not None:
            take_profit = entry_price - take_profit_distance

    else:
        raise ValueError(f"Unsupported side: {side}")

    if stop_loss is not None and stop_loss <= 0:
        raise ValueError("stop_loss must be > 0")

    if take_profit is not None and take_profit <= 0:
        raise ValueError("take_profit must be > 0")

    return RiskLevels(
        stop_loss=stop_loss,
        take_profit=take_profit,
    )


def check_stop_loss(
    side: Side,
    market_price: Decimal,
    stop_loss: Decimal | None,
) -> bool:
    if market_price <= 0:
        raise ValueError("market_price must be > 0")

    if stop_loss is None:
        return False

    if side == Side.LONG:
        return market_price <= stop_loss

    if side == Side.SHORT:
        return market_price >= stop_loss

    raise ValueError(f"Unsupported side: {side}")


def check_take_profit(
    side: Side,
    market_price: Decimal,
    take_profit: Decimal | None,
) -> bool:
    if market_price <= 0:
        raise ValueError("market_price must be > 0")

    if take_profit is None:
        return False

    if side == Side.LONG:
        return market_price >= take_profit

    if side == Side.SHORT:
        return market_price <= take_profit

    raise ValueError(f"Unsupported side: {side}")
