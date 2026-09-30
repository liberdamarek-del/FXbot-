from datetime import datetime, timezone
from decimal import Decimal

from src.paper_trading import PaperTradingEngine
from src.trade_simulator import Side


ENTRY_TIME = datetime(
    2026, 9, 29, 10, 0,
    tzinfo=timezone.utc,
)

EXIT_TIME = datetime(
    2026, 9, 29, 10, 5,
    tzinfo=timezone.utc,
)


engine = PaperTradingEngine(
    initial_cash=Decimal("10000"),
    quantity=Decimal("10"),
)


assert engine.account.cash == Decimal("10000")
assert not engine.is_open


position = engine.open_position(
    side=Side.LONG,
    entry_time=ENTRY_TIME,
    entry_price=Decimal("100"),
)

assert engine.is_open
assert position.entry_price == Decimal("100")
assert engine.account.reserved_cash == Decimal("1000")
assert engine.account.available_cash == Decimal("9000")


state_open = engine.state(
    market_price=Decimal("105"),
)

assert state_open.position_open
assert state_open.side == Side.LONG
assert state_open.entry_price == Decimal("100")
assert state_open.quantity == Decimal("10")
assert state_open.cash == Decimal("10000")
assert state_open.realized_pnl == Decimal("0")
assert state_open.unrealized_pnl == Decimal("50")
assert state_open.equity == Decimal("10050")


trade = engine.close_position(
    exit_time=EXIT_TIME,
    exit_price=Decimal("110"),
)

assert trade.side == Side.LONG
assert trade.entry_price == Decimal("100")
assert trade.exit_price == Decimal("110")
assert trade.quantity == Decimal("10")
assert trade.net_pnl == Decimal("100")

assert not engine.is_open
assert engine.account.reserved_cash == Decimal("0")
assert engine.account.cash == Decimal("10100")
assert engine.account.realized_pnl == Decimal("100")


state_closed = engine.state(
    market_price=Decimal("110"),
)

assert not state_closed.position_open
assert state_closed.unrealized_pnl == Decimal("0")
assert state_closed.equity == Decimal("10100")


print("=" * 60)
print("M4.3 PAPER TRADING ENGINE")
print("=" * 60)
print(f"ENTRY: {position.entry_price}")
print(f"UNREALIZED PNL: {state_open.unrealized_pnl}")
print(f"ENTRY EQUITY: {state_open.equity}")
print(f"EXIT: {trade.exit_price}")
print(f"REALIZED PNL: {trade.net_pnl}")
print(f"FINAL CASH: {engine.account.cash}")
print(f"FINAL EQUITY: {state_closed.equity}")

print("OPEN POSITION: PASS")
print("CASH RESERVATION: PASS")
print("UNREALIZED PNL: PASS")
print("EQUITY: PASS")
print("CLOSE POSITION: PASS")
print("REALIZED PNL: PASS")
print("RESERVATION RELEASE: PASS")
print("FINAL STATE: PASS")
print("RESULT: PASS")
print("=" * 60)
