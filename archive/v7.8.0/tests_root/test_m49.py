from datetime import datetime, timezone
from decimal import Decimal

from src.paper_audit import get_recent_paper_events
from src.paper_trading import PaperTradingEngine
from src.trade_simulator import Side


T0 = datetime(2026, 9, 29, 10, 0, tzinfo=timezone.utc)
T1 = datetime(2026, 9, 29, 10, 1, tzinfo=timezone.utc)


engine = PaperTradingEngine(
    initial_cash=Decimal("10000"),
    quantity=Decimal("10"),
    symbol="EUR/USD",
    timeframe="1min",
)

engine.open_position(
    Side.LONG,
    T0,
    Decimal("100"),
    stop_loss_distance=Decimal("5"),
    take_profit_distance=Decimal("10"),
)

trade = engine.close_position(
    T1,
    Decimal("110"),
)

assert trade.net_pnl == Decimal("100")

rows = get_recent_paper_events(
    symbol="EUR/USD",
    timeframe="1min",
    limit=10,
)

assert len(rows) >= 2

close_event = rows[0]
open_event = rows[1]

assert close_event["event_type"] == "CLOSE"
assert close_event["side"] == "LONG"
assert close_event["price"] == "110"
assert close_event["quantity"] == "10"
assert close_event["realized_pnl"] == "100"
assert close_event["reason"] == "MANUAL_CLOSE"

assert open_event["event_type"] == "OPEN"
assert open_event["side"] == "LONG"
assert open_event["price"] == "100"
assert open_event["quantity"] == "10"
assert open_event["stop_loss"] == "95"
assert open_event["take_profit"] == "110"


print("=" * 60)
print("M4.9 ENGINE -> AUDIT INTEGRATION")
print("=" * 60)
print("OPEN AUDIT: PASS")
print("CLOSE AUDIT: PASS")
print("SIDE/PRICE/QUANTITY: PASS")
print("SL/TP AUDIT: PASS")
print("REALIZED PNL AUDIT: PASS")
print("EXIT REASON: PASS")
print("DATABASE READBACK: PASS")
print("RESULT: PASS")
print("=" * 60)
