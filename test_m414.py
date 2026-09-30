from datetime import datetime, timezone
from decimal import Decimal

from src.historical_data import HistoricalBar
from src.paper_session import run_and_persist_paper_session
from src.paper_session_audit import get_paper_session
from src.paper_trading import PaperTradingEngine
from src.trade_simulator import Side


UTC = timezone.utc


def make_bar(minute: int, open_price: str, high: str, low: str, close: str):
    return HistoricalBar(
        symbol="TEST/USD",
        timeframe="1min",
        bar_time=datetime(2026, 9, 29, 11, minute, tzinfo=UTC),
        open=Decimal(open_price),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        source="TEST",
    )


engine = PaperTradingEngine(
    initial_cash=Decimal("10000"),
    quantity=Decimal("10"),
    symbol="TEST/USD",
    timeframe="1min",
)

engine.open_position(
    entry_time=datetime(2026, 9, 29, 11, 0, tzinfo=UTC),
    entry_price=Decimal("100"),
    side=Side.LONG,
    take_profit_distance=Decimal("10"),
)

bars = [
    make_bar(0, "100", "105", "99", "104"),
    make_bar(1, "104", "111", "103", "110"),
]

session_key = "M4.14_INTEGRATION_TEST"

result = run_and_persist_paper_session(
    bars=bars,
    engine=engine,
    symbol="TEST/USD",
    timeframe="1min",
    session_key=session_key,
    created_at=datetime(2026, 9, 29, 11, 2, tzinfo=UTC),
)

assert result.bars_processed == 2
assert result.trades == 1
assert result.take_profit_exits == 1
assert result.realized_pnl == Decimal("100")
assert result.final_equity == Decimal("10100")
assert result.forced_close is False

stored = get_paper_session(session_key)

assert stored is not None
assert stored["session_key"] == session_key
assert stored["symbol"] == "TEST/USD"
assert stored["timeframe"] == "1min"
assert stored["bars_processed"] == 2
assert stored["trades"] == 1
assert stored["realized_pnl"] == "100"
assert stored["final_equity"] == "10100"
assert stored["stop_loss_exits"] == 0
assert stored["take_profit_exits"] == 1
assert stored["ambiguous_bars"] == 0
assert stored["forced_close"] == 0

assert engine.position_simulator.position is None

print("=" * 60)
print("M4.14 SESSION -> AUDIT INTEGRATION")
print("=" * 60)
print("SESSION EXECUTION: PASS")
print("SESSION RESULT: PASS")
print("AUDIT PERSISTENCE: PASS")
print("AUDIT READBACK: PASS")
print("P&L CONSISTENCY: PASS")
print("EQUITY CONSISTENCY: PASS")
print("POSITION CLOSED: PASS")
print("RESULT: PASS")
print("=" * 60)
