from datetime import datetime, timezone
from decimal import Decimal

from src.backtest_pipeline import run_pipeline
from src.backtest_persistence import persist_pipeline_result
from src.backtest_results import get_backtest_run
from src.backtest_engine import BacktestContext
from src.backtest_execution import Signal
from src.historical_data import load_bars


SYMBOL = "USD/JPY"
TIMEFRAME = "1min"
SOURCE = "TwelveData"
RUN_KEY = "M3.10_REAL_PIPELINE_001"


def strategy(context: BacktestContext) -> Signal:
    if context.index == 0:
        return Signal.ENTER_LONG

    if context.index == 1:
        return Signal.EXIT

    return Signal.HOLD


start = datetime(2026, 9, 28, 18, 32, tzinfo=timezone.utc)
end = datetime(2026, 9, 29, 8, 56, tzinfo=timezone.utc)

bars = load_bars(
    symbol=SYMBOL,
    timeframe=TIMEFRAME,
    start=start,
    end=end,
    source=SOURCE,
)

result = run_pipeline(
    bars=bars,
    strategy=strategy,
    quantity=Decimal("10"),
)

created_at = datetime.now(timezone.utc)

run_id = persist_pipeline_result(
    run_key=RUN_KEY,
    symbol=SYMBOL,
    timeframe=TIMEFRAME,
    source=SOURCE,
    result=result,
    strategy_name="M3.10_REAL_TEST",
    strategy_version="1.0",
    created_at=created_at,
)

stored = get_backtest_run(RUN_KEY)

print("=" * 70)
print("M3.10 PIPELINE -> SQLITE PERSISTENCE")
print("=" * 70)
print(f"RUN ID: {run_id}")
print(f"RUN KEY: {RUN_KEY}")
print(f"DB BARS: {len(bars)}")
print(f"PIPELINE BARS: {result.bars_processed}")
print(f"SIGNALS: {result.signals_generated}")
print(f"EXECUTIONS: {result.executions}")
print(f"TRADES: {len(result.trades)}")
print(f"STATUS: {stored['status'] if stored else 'NONE'}")

assert stored is not None
assert stored["run_key"] == RUN_KEY
assert stored["symbol"] == SYMBOL
assert stored["timeframe"] == TIMEFRAME
assert stored["source"] == SOURCE
assert stored["bars_processed"] == 865
assert stored["strategy_name"] == "M3.10_REAL_TEST"
assert stored["strategy_version"] == "1.0"
assert stored["status"] == "COMPLETED"
assert stored["started_at"] == bars[0].bar_time.isoformat()
assert stored["finished_at"] == bars[-1].bar_time.isoformat()

print("PIPELINE RESULT: PASS")
print("SQLITE PERSISTENCE: PASS")
print("READBACK: PASS")
print("METADATA: PASS")
print("RESULT: PASS")
print("=" * 70)
