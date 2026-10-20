from datetime import datetime, timezone
from decimal import Decimal

from src.paper_audit import (
    get_recent_paper_events,
    initialize_paper_audit,
    record_paper_event,
)


T0 = datetime(2026, 9, 29, 10, 0, tzinfo=timezone.utc)

initialize_paper_audit()

event_id = record_paper_event(
    event_time=T0,
    symbol="EUR/USD",
    timeframe="1min",
    event_type="OPEN",
    side="LONG",
    price=Decimal("100"),
    quantity=Decimal("10"),
    stop_loss=Decimal("95"),
    take_profit=Decimal("110"),
)

assert event_id > 0

rows = get_recent_paper_events(
    symbol="EUR/USD",
    timeframe="1min",
    limit=10,
)

assert rows
row = rows[0]

assert row["event_type"] == "OPEN"
assert row["symbol"] == "EUR/USD"
assert row["timeframe"] == "1min"
assert row["side"] == "LONG"
assert row["price"] == "100"
assert row["quantity"] == "10"
assert row["stop_loss"] == "95"
assert row["take_profit"] == "110"
assert row["realized_pnl"] is None


close_id = record_paper_event(
    event_time=T0,
    symbol="EUR/USD",
    timeframe="1min",
    event_type="CLOSE",
    side="LONG",
    price=Decimal("110"),
    quantity=Decimal("10"),
    realized_pnl=Decimal("100"),
    reason="TAKE_PROFIT",
)

assert close_id > event_id

rows = get_recent_paper_events(
    symbol="EUR/USD",
    timeframe="1min",
    limit=10,
)

assert len(rows) >= 2

close_row = rows[0]

assert close_row["event_type"] == "CLOSE"
assert close_row["price"] == "110"
assert close_row["realized_pnl"] == "100"
assert close_row["reason"] == "TAKE_PROFIT"


print("=" * 60)
print("M4.8 PAPER TRADE AUDIT")
print("=" * 60)
print("AUDIT TABLE: PASS")
print("OPEN EVENT: PASS")
print("CLOSE EVENT: PASS")
print("PRICE/POSITION DATA: PASS")
print("SL/TP DATA: PASS")
print("REALIZED PNL: PASS")
print("EXIT REASON: PASS")
print("READBACK: PASS")
print("RESULT: PASS")
print("=" * 60)
