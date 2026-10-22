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
RUN_KEY = "M3.13_FINGERPRINT_001"

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

run_id = persist_pipeline_result(
    run_key=RUN_KEY,
    symbol=SYMBOL,
    timeframe=TIMEFRAME,
    source=SOURCE,
    result=result,
    strategy_name="M3.13_FINGERPRINT_TEST",
    strategy_version="1.0",
    created_at=datetime.now(timezone.utc),
    bars=bars,
)

stored = get_backtest_run(RUN_KEY)

assert stored is not None
assert run_id == stored["id"]

assert stored["run_key"] == RUN_KEY
assert stored["symbol"] == SYMBOL
assert stored["timeframe"] == TIMEFRAME
assert stored["source"] == SOURCE

assert stored["bars_processed"] == 865
assert stored["strategy_name"] == "M3.13_FINGERPRINT_TEST"
assert stored["strategy_version"] == "1.0"
assert stored["status"] == "COMPLETED"

assert stored["data_fingerprint"] == fingerprint
assert len(stored["data_fingerprint"]) == 64

print("=" * 70)
print("M3.13 BACKTEST DATA FINGERPRINT PERSISTENCE")
print("=" * 70)
print(f"RUN ID: {run_id}")
print(f"BARS: {len(bars)}")
print(f"FINGERPRINT: {fingerprint}")
print(f"STORED FINGERPRINT: {stored['data_fingerprint']}")

print("SCHEMA MIGRATION: PASS")
print("PIPELINE INTEGRATION: PASS")
print("FINGERPRINT GENERATION: PASS")
print("FINGERPRINT PERSISTENCE: PASS")
print("FINGERPRINT READBACK: PASS")
print("DATA IDENTITY: PASS")
print("RESULT: PASS")
print("=" * 70)
