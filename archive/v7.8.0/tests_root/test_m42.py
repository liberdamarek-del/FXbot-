from datetime import datetime, timezone
from decimal import Decimal

from src.paper_equity import (
    calculate_equity,
    calculate_unrealized_pnl,
)
from src.position_simulator import Position
from src.trade_simulator import Side


ENTRY_TIME = datetime(
    2026, 9, 29, 10, 0,
    tzinfo=timezone.utc,
)


long_position = Position(
    side=Side.LONG,
    entry_time=ENTRY_TIME,
    entry_price=Decimal("100"),
    quantity=Decimal("10"),
)

short_position = Position(
    side=Side.SHORT,
    entry_time=ENTRY_TIME,
    entry_price=Decimal("100"),
    quantity=Decimal("10"),
)


assert calculate_unrealized_pnl(
    long_position,
    Decimal("105"),
) == Decimal("50")

assert calculate_unrealized_pnl(
    long_position,
    Decimal("95"),
) == Decimal("-50")

assert calculate_unrealized_pnl(
    short_position,
    Decimal("95"),
) == Decimal("50")

assert calculate_unrealized_pnl(
    short_position,
    Decimal("105"),
) == Decimal("-50")

assert calculate_unrealized_pnl(
    None,
    Decimal("105"),
) == Decimal("0")


long_equity = calculate_equity(
    cash=Decimal("10000"),
    position=long_position,
    market_price=Decimal("105"),
)

assert long_equity.cash == Decimal("10000")
assert long_equity.unrealized_pnl == Decimal("50")
assert long_equity.equity == Decimal("10050")


flat_equity = calculate_equity(
    cash=Decimal("10000"),
    position=None,
    market_price=Decimal("105"),
)

assert flat_equity.unrealized_pnl == Decimal("0")
assert flat_equity.equity == Decimal("10000")


print("=" * 60)
print("M4.2 EQUITY ENGINE")
print("=" * 60)
print(f"LONG UNREALIZED PNL: {long_equity.unrealized_pnl}")
print(f"LONG EQUITY: {long_equity.equity}")
print(f"FLAT EQUITY: {flat_equity.equity}")

print("LONG PNL: PASS")
print("SHORT PNL: PASS")
print("LOSS CALCULATION: PASS")
print("FLAT POSITION: PASS")
print("EQUITY CALCULATION: PASS")
print("DECIMAL PRECISION: PASS")
print("RESULT: PASS")
print("=" * 60)
