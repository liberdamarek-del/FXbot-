from datetime import datetime, timezone
from decimal import Decimal

from src.paper_trading import PaperTradingEngine
from src.trade_simulator import Side


T0 = datetime(2026, 9, 29, 10, 0, tzinfo=timezone.utc)
T1 = datetime(2026, 9, 29, 10, 1, tzinfo=timezone.utc)


# LONG TAKE PROFIT
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

assert engine.stop_loss == Decimal("95")
assert engine.take_profit == Decimal("110")

result = engine.check_risk_exit(
    T1,
    Decimal("110"),
)

assert result.triggered
assert result.reason == "TAKE_PROFIT"
assert result.trade is not None
assert result.trade.net_pnl == Decimal("100")
assert not engine.is_open
assert engine.account.cash == Decimal("10100")


# LONG STOP LOSS
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

result = engine.check_risk_exit(
    T1,
    Decimal("95"),
)

assert result.triggered
assert result.reason == "STOP_LOSS"
assert result.trade is not None
assert result.trade.net_pnl == Decimal("-50")
assert not engine.is_open
assert engine.account.cash == Decimal("9950")


# SHORT TAKE PROFIT
engine = PaperTradingEngine(
    initial_cash=Decimal("10000"),
    quantity=Decimal("10"),
)

engine.open_position(
    Side.SHORT,
    T0,
    Decimal("100"),
    stop_loss_distance=Decimal("5"),
    take_profit_distance=Decimal("10"),
)

result = engine.check_risk_exit(
    T1,
    Decimal("90"),
)

assert result.triggered
assert result.reason == "TAKE_PROFIT"
assert result.trade is not None
assert result.trade.net_pnl == Decimal("100")
assert not engine.is_open


# SHORT STOP LOSS
engine = PaperTradingEngine(
    initial_cash=Decimal("10000"),
    quantity=Decimal("10"),
)

engine.open_position(
    Side.SHORT,
    T0,
    Decimal("100"),
    stop_loss_distance=Decimal("5"),
    take_profit_distance=Decimal("10"),
)

result = engine.check_risk_exit(
    T1,
    Decimal("105"),
)

assert result.triggered
assert result.reason == "STOP_LOSS"
assert result.trade is not None
assert result.trade.net_pnl == Decimal("-50")
assert not engine.is_open


# NO TRIGGER
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

result = engine.check_risk_exit(
    T1,
    Decimal("105"),
)

assert not result.triggered
assert result.reason is None
assert result.trade is None
assert engine.is_open


print("=" * 60)
print("M4.5 AUTOMATIC SL/TP EXECUTION")
print("=" * 60)
print("LONG TAKE PROFIT: PASS")
print("LONG STOP LOSS: PASS")
print("SHORT TAKE PROFIT: PASS")
print("SHORT STOP LOSS: PASS")
print("NO FALSE TRIGGER: PASS")
print("POSITION CLOSED: PASS")
print("REALIZED PNL: PASS")
print("RESULT: PASS")
print("=" * 60)
