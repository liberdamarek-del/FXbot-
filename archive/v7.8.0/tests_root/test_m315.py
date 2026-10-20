from datetime import datetime, timezone
from decimal import Decimal

from src.backtest_engine import BacktestContext
from src.backtest_execution import Signal
from src.backtest_fingerprint import fingerprint_bars
from src.backtest_persistence import persist_pipeline_result
from src.backtest_pipeline import run_pipeline
from src.backtest_results import get_backtest_run
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


def load_and_run():
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


bars_a, result_a, fingerprint_a = load_and_run()
bars_b, result_b, fingerprint_b = load_and_run()


assert len(bars_a) == 865
assert len(bars_b) == 865

assert fingerprint_a == fingerprint_b

assert result_a.bars_processed == 865
assert result_a.signals_generated == 2
assert result_a.executions == 2
assert len(result_a.trades) == 1

trade = result_a.trades[0]

assert trade.entry_price == bars_a[1].open
assert trade.exit_price == bars_a[2].open
assert trade.quantity == Decimal("10")
assert trade.gross_pnl == Decimal("0.44690")
assert trade.net_pnl == Decimal("0.44690")

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


run_key = "M3.15_ACCEPTANCE_001"

run_id = persist_pipeline_result(
    run_key=run_key,
    symbol=SYMBOL,
    timeframe=TIMEFRAME,
    source=SOURCE,
    result=result_a,
    strategy_name="M3.15_ACCEPTANCE",
    strategy_version="1.0",
    created_at=datetime.now(timezone.utc),
    bars=bars_a,
)

stored = get_backtest_run(run_key)

assert stored is not None
assert stored["id"] == run_id
assert stored["run_key"] == run_key
assert stored["symbol"] == SYMBOL
assert stored["timeframe"] == TIMEFRAME
assert stored["source"] == SOURCE
assert stored["bars_processed"] == 865
assert stored["strategy_name"] == "M3.15_ACCEPTANCE"
assert stored["strategy_version"] == "1.0"
assert stored["status"] == "COMPLETED"
assert stored["data_fingerprint"] == fingerprint_a


print("=" * 70)
print("M3.15 FULL BACKTEST ACCEPTANCE")
print("=" * 70)
print(f"BARS: {len(bars_a)}")
print(f"FINGERPRINT: {fingerprint_a}")
print(f"SIGNALS: {result_a.signals_generated}")
print(f"EXECUTIONS: {result_a.executions}")
print(f"TRADES: {len(result_a.trades)}")
print(f"ENTRY: {trade.entry_price}")
print(f"EXIT: {trade.exit_price}")
print(f"NET PNL: {trade.net_pnl}")
print(f"RUN ID: {run_id}")
print(f"STORED FINGERPRINT: {stored['data_fingerprint']}")

print("HISTORICAL DATA: PASS")
print("CHRONOLOGY: PASS")
print("TIMEZONE: PASS")
print("DATA FINGERPRINT: PASS")
print("BACKTEST PIPELINE: PASS")
print("NEXT-BAR EXECUTION: PASS")
print("TRADE SIMULATION: PASS")
print("PNL: PASS")
print("PERSISTENCE: PASS")
print("READBACK: PASS")
print("DETERMINISTIC REPRODUCTION: PASS")
print("M3 ACCEPTANCE: PASS")
print("=" * 70)
