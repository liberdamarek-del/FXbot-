from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.historical_data import HistoricalBar
from src.paper_session import run_paper_session
from src.paper_trading import PaperTradingEngine
from src.trade_simulator import Side


UTC = timezone.utc


def bar(
    minute: int,
    open_price: str,
    high: str,
    low: str,
    close: str,
) -> HistoricalBar:
    return HistoricalBar(
        symbol="TEST/USD",
        timeframe="1min",
        bar_time=datetime(2026, 9, 29, 10, minute, tzinfo=UTC),
        open=Decimal(open_price),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        source="TEST",
    )


# ------------------------------------------------------------
# TEST 1 — TAKE PROFIT
# ------------------------------------------------------------

engine_tp = PaperTradingEngine(
    initial_cash=Decimal("10000"),
    quantity=Decimal("10"),
    symbol="TEST/USD",
    timeframe="1min",
)

engine_tp.open_position(
    entry_time=datetime(2026, 9, 29, 10, 0, tzinfo=UTC),
    entry_price=Decimal("100"),
    side=Side.LONG,
    take_profit_distance=Decimal("10"),
)

bars_tp = [
    bar(0, "100", "105", "99", "104"),
    bar(1, "104", "111", "103", "110"),
]

result_tp = run_paper_session(
    bars=bars_tp,
    engine=engine_tp,
    symbol="TEST/USD",
    timeframe="1min",
)

assert result_tp.bars_processed == 2
assert result_tp.trades == 1
assert result_tp.take_profit_exits == 1
assert result_tp.stop_loss_exits == 0
assert result_tp.ambiguous_bars == 0
assert result_tp.forced_close is False
assert result_tp.realized_pnl == Decimal("100")
assert result_tp.final_equity == Decimal("10100")
assert engine_tp.position_simulator.position is None


# ------------------------------------------------------------
# TEST 2 — STOP LOSS
# ------------------------------------------------------------

engine_sl = PaperTradingEngine(
    initial_cash=Decimal("10000"),
    quantity=Decimal("10"),
    symbol="TEST/USD",
    timeframe="1min",
)

engine_sl.open_position(
    entry_time=datetime(2026, 9, 29, 10, 0, tzinfo=UTC),
    entry_price=Decimal("100"),
    side=Side.LONG,
    stop_loss_distance=Decimal("5"),
)

bars_sl = [
    bar(0, "100", "103", "99", "101"),
    bar(1, "101", "102", "94", "95"),
]

result_sl = run_paper_session(
    bars=bars_sl,
    engine=engine_sl,
    symbol="TEST/USD",
    timeframe="1min",
)

assert result_sl.bars_processed == 2
assert result_sl.trades == 1
assert result_sl.stop_loss_exits == 1
assert result_sl.take_profit_exits == 0
assert result_sl.ambiguous_bars == 0
assert result_sl.forced_close is False
assert result_sl.realized_pnl == Decimal("-50")
assert result_sl.final_equity == Decimal("9950")
assert engine_sl.position_simulator.position is None


# ------------------------------------------------------------
# TEST 3 — AMBIGUOUS BAR
# ------------------------------------------------------------

engine_amb = PaperTradingEngine(
    initial_cash=Decimal("10000"),
    quantity=Decimal("10"),
    symbol="TEST/USD",
    timeframe="1min",
)

engine_amb.open_position(
    entry_time=datetime(2026, 9, 29, 10, 0, tzinfo=UTC),
    entry_price=Decimal("100"),
    side=Side.LONG,
    stop_loss_distance=Decimal("5"),
    take_profit_distance=Decimal("10"),
)

bars_amb = [
    bar(0, "100", "103", "99", "102"),
    bar(1, "102", "111", "94", "105"),
]

result_amb = run_paper_session(
    bars=bars_amb,
    engine=engine_amb,
    symbol="TEST/USD",
    timeframe="1min",
)

assert result_amb.bars_processed == 2
assert result_amb.ambiguous_bars == 1
assert result_amb.stop_loss_exits == 0
assert result_amb.take_profit_exits == 0
assert result_amb.trades == 1
assert result_amb.forced_close is True
assert result_amb.realized_pnl == Decimal("50")
assert result_amb.final_equity == Decimal("10050")
assert engine_amb.position_simulator.position is None


# ------------------------------------------------------------
# TEST 4 — END OF DATA
# ------------------------------------------------------------

engine_eod = PaperTradingEngine(
    initial_cash=Decimal("10000"),
    quantity=Decimal("10"),
    symbol="TEST/USD",
    timeframe="1min",
)

engine_eod.open_position(
    entry_time=datetime(2026, 9, 29, 10, 0, tzinfo=UTC),
    entry_price=Decimal("100"),
    side=Side.LONG,
)

bars_eod = [
    bar(0, "100", "102", "99", "101"),
    bar(1, "101", "104", "100", "103"),
]

result_eod = run_paper_session(
    bars=bars_eod,
    engine=engine_eod,
    symbol="TEST/USD",
    timeframe="1min",
)

assert result_eod.trades == 1
assert result_eod.forced_close is True
assert result_eod.realized_pnl == Decimal("30")
assert result_eod.final_equity == Decimal("10030")
assert engine_eod.position_simulator.position is None


print("=" * 60)
print("M4.12 PAPER SESSION TEST")
print("=" * 60)
print("TAKE PROFIT: PASS")
print("STOP LOSS: PASS")
print("AMBIGUOUS BAR: PASS")
print("END OF DATA: PASS")
print("TRADE COUNTS: PASS")
print("REALIZED P&L: PASS")
print("FINAL EQUITY: PASS")
print("POSITION CLOSED: PASS")
print("RESULT: PASS")
print("=" * 60)
