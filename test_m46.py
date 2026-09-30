from decimal import Decimal

from src.intrabar_policy import (
    IntrabarExit,
    evaluate_intrabar_exit,
)
from src.paper_risk import RiskLevels
from src.trade_simulator import Side


levels = RiskLevels(
    stop_loss=Decimal("95"),
    take_profit=Decimal("110"),
)


# LONG: only SL touched
result = evaluate_intrabar_exit(
    side=Side.LONG,
    bar_open=Decimal("100"),
    bar_high=Decimal("105"),
    bar_low=Decimal("94"),
    levels=levels,
)

assert result == IntrabarExit.STOP_LOSS


# LONG: only TP touched
result = evaluate_intrabar_exit(
    side=Side.LONG,
    bar_open=Decimal("100"),
    bar_high=Decimal("111"),
    bar_low=Decimal("98"),
    levels=levels,
)

assert result == IntrabarExit.TAKE_PROFIT


# LONG: both touched -> ambiguous
result = evaluate_intrabar_exit(
    side=Side.LONG,
    bar_open=Decimal("100"),
    bar_high=Decimal("112"),
    bar_low=Decimal("94"),
    levels=levels,
)

assert result == IntrabarExit.AMBIGUOUS


# LONG: neither touched
result = evaluate_intrabar_exit(
    side=Side.LONG,
    bar_open=Decimal("100"),
    bar_high=Decimal("108"),
    bar_low=Decimal("97"),
    levels=levels,
)

assert result == IntrabarExit.NONE


short_levels = RiskLevels(
    stop_loss=Decimal("105"),
    take_profit=Decimal("90"),
)


# SHORT: only SL touched
result = evaluate_intrabar_exit(
    side=Side.SHORT,
    bar_open=Decimal("100"),
    bar_high=Decimal("106"),
    bar_low=Decimal("96"),
    levels=short_levels,
)

assert result == IntrabarExit.STOP_LOSS


# SHORT: only TP touched
result = evaluate_intrabar_exit(
    side=Side.SHORT,
    bar_open=Decimal("100"),
    bar_high=Decimal("103"),
    bar_low=Decimal("89"),
    levels=short_levels,
)

assert result == IntrabarExit.TAKE_PROFIT


# SHORT: both touched
result = evaluate_intrabar_exit(
    side=Side.SHORT,
    bar_open=Decimal("100"),
    bar_high=Decimal("106"),
    bar_low=Decimal("89"),
    levels=short_levels,
)

assert result == IntrabarExit.AMBIGUOUS


# No levels
result = evaluate_intrabar_exit(
    side=Side.LONG,
    bar_open=Decimal("100"),
    bar_high=Decimal("105"),
    bar_low=Decimal("95"),
    levels=RiskLevels(
        stop_loss=None,
        take_profit=None,
    ),
)

assert result == IntrabarExit.NONE


print("=" * 60)
print("M4.6 OHLC INTRABAR POLICY")
print("=" * 60)
print("LONG STOP LOSS: PASS")
print("LONG TAKE PROFIT: PASS")
print("LONG AMBIGUOUS BAR: PASS")
print("LONG NO TRIGGER: PASS")
print("SHORT STOP LOSS: PASS")
print("SHORT TAKE PROFIT: PASS")
print("SHORT AMBIGUOUS BAR: PASS")
print("NO LEVELS: PASS")
print("NO FALSE ORDER ASSUMPTION: PASS")
print("RESULT: PASS")
print("=" * 60)
