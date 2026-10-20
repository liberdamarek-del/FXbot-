from decimal import Decimal

from src.paper_risk import (
    calculate_risk_levels,
    check_stop_loss,
    check_take_profit,
)
from src.trade_simulator import Side


long_levels = calculate_risk_levels(
    side=Side.LONG,
    entry_price=Decimal("100"),
    stop_loss_distance=Decimal("5"),
    take_profit_distance=Decimal("10"),
)

assert long_levels.stop_loss == Decimal("95")
assert long_levels.take_profit == Decimal("110")

assert check_stop_loss(
    Side.LONG,
    Decimal("95"),
    long_levels.stop_loss,
)

assert check_stop_loss(
    Side.LONG,
    Decimal("90"),
    long_levels.stop_loss,
)

assert not check_stop_loss(
    Side.LONG,
    Decimal("96"),
    long_levels.stop_loss,
)

assert check_take_profit(
    Side.LONG,
    Decimal("110"),
    long_levels.take_profit,
)

assert check_take_profit(
    Side.LONG,
    Decimal("120"),
    long_levels.take_profit,
)

assert not check_take_profit(
    Side.LONG,
    Decimal("109"),
    long_levels.take_profit,
)


short_levels = calculate_risk_levels(
    side=Side.SHORT,
    entry_price=Decimal("100"),
    stop_loss_distance=Decimal("5"),
    take_profit_distance=Decimal("10"),
)

assert short_levels.stop_loss == Decimal("105")
assert short_levels.take_profit == Decimal("90")

assert check_stop_loss(
    Side.SHORT,
    Decimal("105"),
    short_levels.stop_loss,
)

assert check_take_profit(
    Side.SHORT,
    Decimal("90"),
    short_levels.take_profit,
)

assert not check_stop_loss(
    Side.SHORT,
    Decimal("104"),
    short_levels.stop_loss,
)

assert not check_take_profit(
    Side.SHORT,
    Decimal("91"),
    short_levels.take_profit,
)


no_levels = calculate_risk_levels(
    side=Side.LONG,
    entry_price=Decimal("100"),
)

assert no_levels.stop_loss is None
assert no_levels.take_profit is None

assert not check_stop_loss(
    Side.LONG,
    Decimal("50"),
    None,
)

assert not check_take_profit(
    Side.LONG,
    Decimal("150"),
    None,
)


print("=" * 60)
print("M4.4 SL/TP ENGINE")
print("=" * 60)
print(f"LONG SL: {long_levels.stop_loss}")
print(f"LONG TP: {long_levels.take_profit}")
print(f"SHORT SL: {short_levels.stop_loss}")
print(f"SHORT TP: {short_levels.take_profit}")

print("LONG LEVELS: PASS")
print("SHORT LEVELS: PASS")
print("LONG STOP LOSS: PASS")
print("LONG TAKE PROFIT: PASS")
print("SHORT STOP LOSS: PASS")
print("SHORT TAKE PROFIT: PASS")
print("OPTIONAL LEVELS: PASS")
print("DECIMAL PRECISION: PASS")
print("RESULT: PASS")
print("=" * 60)
