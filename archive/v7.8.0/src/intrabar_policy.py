from enum import Enum

from src.paper_risk import RiskLevels
from src.trade_simulator import Side


class IntrabarExit(str, Enum):
    NONE = "NONE"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    AMBIGUOUS = "AMBIGUOUS"


def evaluate_intrabar_exit(
    side: Side,
    bar_open,
    bar_high,
    bar_low,
    levels: RiskLevels,
) -> IntrabarExit:
    if bar_open <= 0:
        raise ValueError("bar_open must be > 0")

    if bar_high <= 0:
        raise ValueError("bar_high must be > 0")

    if bar_low <= 0:
        raise ValueError("bar_low must be > 0")

    if bar_high < bar_low:
        raise ValueError("bar_high must be >= bar_low")

    if bar_open < bar_low or bar_open > bar_high:
        raise ValueError(
            "bar_open must be inside bar high/low range"
        )

    if levels.stop_loss is None and levels.take_profit is None:
        return IntrabarExit.NONE

    if side == Side.LONG:
        stop_hit = (
            levels.stop_loss is not None
            and bar_low <= levels.stop_loss
        )

        target_hit = (
            levels.take_profit is not None
            and bar_high >= levels.take_profit
        )

    elif side == Side.SHORT:
        stop_hit = (
            levels.stop_loss is not None
            and bar_high >= levels.stop_loss
        )

        target_hit = (
            levels.take_profit is not None
            and bar_low <= levels.take_profit
        )

    else:
        raise ValueError(f"Unsupported side: {side}")

    if stop_hit and target_hit:
        return IntrabarExit.AMBIGUOUS

    if stop_hit:
        return IntrabarExit.STOP_LOSS

    if target_hit:
        return IntrabarExit.TAKE_PROFIT

    return IntrabarExit.NONE
