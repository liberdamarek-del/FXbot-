from datetime import datetime, timezone
from decimal import Decimal

from src.intrabar_policy import IntrabarExit
from src.paper_trading import PaperTradingEngine
from src.trade_simulator import Side


T0 = datetime(2026, 9, 29, 10, 0, tzinfo=timezone.utc)


engine = PaperTradingEngine(
    initial_cash=Decimal("10000"),
    quantity=Decimal("10"),
)

engine.open_position(
    Side.LONG,
    T0,
    Decimal("100"),
    stop_loss_distance=Decimal("5"),
    take_profit_distance=Decimal("10"),
)

# Only SL touched
result = engine.check_ohlc_risk_exit(
    T0,
    Decimal("100"),
    Decimal("105"),
    Decimal("94"),
)
assert result == IntrabarExit.STOP_LOSS
assert engine.is_open


# Only TP touched
result = engine.check_ohlc_risk_exit(
    T0,
    Decimal("100"),
    Decimal("111"),
    Decimal("98"),
)
assert result == IntrabarExit.TAKE_PROFIT
assert engine.is_open


# Both touched -> MUST remain ambiguous
result = engine.check_ohlc_risk_exit(
    T0,
    Decimal("100"),
    Decimal("112"),
    Decimal("94"),
)
assert result == IntrabarExit.AMBIGUOUS
assert engine.is_open


# Neither touched
result = engine.check_ohlc_risk_exit(
    T0,
    Decimal("100"),
    Decimal("108"),
    Decimal("97"),
)
assert result == IntrabarExit.NONE
assert engine.is_open


# No position
engine.close_position(
    T0,
    Decimal("100"),
)

result = engine.check_ohlc_risk_exit(
    T0,
    Decimal("100"),
    Decimal("112"),
    Decimal("94"),
)
assert result == IntrabarExit.NONE


print("=" * 60)
print("M4.7 PAPER ENGINE OHLC RISK INTEGRATION")
print("=" * 60)
print("SL DETECTION: PASS")
print("TP DETECTION: PASS")
print("AMBIGUOUS BAR PRESERVED: PASS")
print("NO FALSE EXIT: PASS")
print("NO POSITION: PASS")
print("POSITION REMAINS OPEN: PASS")
print("RESULT: PASS")
print("=" * 60)
