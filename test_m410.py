from datetime import datetime, timezone
from decimal import Decimal

from src.paper_audit import get_recent_paper_events
from src.paper_trading import PaperTradingEngine
from src.trade_simulator import Side


T0 = datetime(2026, 9, 29, 10, 0, tzinfo=timezone.utc)
T1 = datetime(2026, 9, 29, 10, 1, tzinfo=timezone.utc)


# AUTOMATIC TAKE PROFIT
engine = PaperTradingEngine(
    initial_cash=Decimal("10000"),
    quantity=Decimal("10"),
    symbol="TEST/TP",
    timeframe="1min",
)

engine.open_position(
    Side.LONG,
    T0,
    Decimal("100"),
    stop_loss_distance=Decimal("5"),
    take_profit_distance=Decimal("10"),
)

result = engine.check_risk_exit(T1, Decimal("110"))

assert result.triggered
assert result.reason == "TAKE_PROFIT"
assert result.trade is not None
assert result.trade.net_pnl == Decimal("100")
assert not engine.is_open

rows = get_recent_paper_events("TEST/TP", "1min", 10)

assert len(rows) >= 2
close_event = rows[0]

assert close_event["event_type"] == "CLOSE"
assert close_event["reason"] == "TAKE_PROFIT"
assert close_event["price"] == "110"
assert close_event["realized_pnl"] == "100"


# AUTOMATIC STOP LOSS
engine = PaperTradingEngine(
    initial_cash=Decimal("10000"),
    quantity=Decimal("10"),
    symbol="TEST/SL",
    timeframe="1min",
)

engine.open_position(
    Side.LONG,
    T0,
    Decimal("100"),
    stop_loss_distance=Decimal("5"),
    take_profit_distance=Decimal("10"),
)

result = engine.check_risk_exit(T1, Decimal("95"))

assert result.triggered
assert result.reason == "STOP_LOSS"
assert result.trade is not None
assert result.trade.net_pnl == Decimal("-50")
assert not engine.is_open

rows = get_recent_paper_events("TEST/SL", "1min", 10)

assert len(rows) >= 2
close_event = rows[0]

assert close_event["event_type"] == "CLOSE"
assert close_event["reason"] == "STOP_LOSS"
assert close_event["price"] == "95"
assert close_event["realized_pnl"] == "-50"


print("=" * 60)
print("M4.10 AUTOMATIC SL/TP AUDIT")
print("=" * 60)
print("AUTOMATIC TAKE PROFIT: PASS")
print("TAKE PROFIT REASON: PASS")
print("TAKE PROFIT PRICE/P&L: PASS")
print("AUTOMATIC STOP LOSS: PASS")
print("STOP LOSS REASON: PASS")
print("STOP LOSS PRICE/P&L: PASS")
print("POSITION CLOSED: PASS")
print("DATABASE READBACK: PASS")
print("RESULT: PASS")
print("=" * 60)
