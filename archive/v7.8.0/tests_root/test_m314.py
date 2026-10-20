from datetime import datetime, timezone
from decimal import Decimal

from src.backtest_engine import BacktestContext
from src.backtest_execution import Signal
from src.backtest_fingerprint import fingerprint_bars
from src.backtest_pipeline import run_pipeline
from src.historical_data import load_bars


SYMBOL = "USD/JPY"
TIMEFRAME = "1min"
SOURCE = "TwelveData"

START = datetime(
    2026, 9, 28, 18, 32,
    tzinfo=timezone.utc,
)

END = datetime(
    2026, 9, 29, 8, 56,
    tzinfo=timezone.utc,
)


def strategy(context: BacktestContext) -> Signal:
    if context.index == 0:
        return Signal.ENTER_LONG

    if context.index == 1:
        return Signal.EXIT

    return Signal.HOLD


def run_once():
    bars = load_bars(
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        start=START,
        end=END,
        source=SOURCE,
    )

    result = run_pipeline(
        bars=bars,
        strategy=strategy,
        quantity=Decimal("10"),
    )

    fingerprint = fingerprint_bars(bars)

    return bars, result, fingerprint


bars_a, result_a, fingerprint_a = run_once()
bars_b, result_b, fingerprint_b = run_once()


assert len(bars_a) == 865
assert len(bars_b) == 865

assert fingerprint_a == fingerprint_b

assert result_a.bars_processed == result_b.bars_processed
assert result_a.signals_generated == result_b.signals_generated
assert result_a.executions == result_b.executions

assert len(result_a.trades) == len(result_b.trades)

for trade_a, trade_b in zip(result_a.trades, result_b.trades):
    assert trade_a.side == trade_b.side
    assert trade_a.entry_price == trade_b.entry_price
    assert trade_a.exit_price == trade_b.exit_price
    assert trade_a.quantity == trade_b.quantity
    assert trade_a.gross_pnl == trade_b.gross_pnl
    assert trade_a.costs == trade_b.costs
    assert trade_a.net_pnl == trade_b.net_pnl


net_pnl_a = sum(
    (trade.net_pnl for trade in result_a.trades),
    Decimal("0"),
)

net_pnl_b = sum(
    (trade.net_pnl for trade in result_b.trades),
    Decimal("0"),
)

assert net_pnl_a == net_pnl_b


print("=" * 70)
print("M3.14 DETERMINISTIC BACKTEST REPRODUCTION")
print("=" * 70)
print(f"BARS RUN A: {result_a.bars_processed}")
print(f"BARS RUN B: {result_b.bars_processed}")
print(f"FINGERPRINT A: {fingerprint_a}")
print(f"FINGERPRINT B: {fingerprint_b}")
print(f"SIGNALS A/B: {result_a.signals_generated}/{result_b.signals_generated}")
print(f"EXECUTIONS A/B: {result_a.executions}/{result_b.executions}")
print(f"TRADES A/B: {len(result_a.trades)}/{len(result_b.trades)}")
print(f"NET PNL A/B: {net_pnl_a}/{net_pnl_b}")

print("INPUT DATA IDENTITY: PASS")
print("BAR COUNT: PASS")
print("SIGNAL DETERMINISM: PASS")
print("EXECUTION DETERMINISM: PASS")
print("TRADE DETERMINISM: PASS")
print("PNL DETERMINISM: PASS")
print("RESULT: PASS")
print("=" * 70)
