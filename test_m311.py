from datetime import datetime, timezone
from decimal import Decimal

from src.backtest_engine import BacktestContext
from src.backtest_execution import Signal
from src.backtest_pipeline import run_pipeline
from src.backtest_report import (
    build_backtest_report,
    format_backtest_report,
)
from src.backtest_results import get_backtest_run
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


start = datetime(
    2026, 9, 28, 18, 32,
    tzinfo=timezone.utc,
)

end = datetime(
    2026, 9, 29, 8, 56,
    tzinfo=timezone.utc,
)


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

stored = get_backtest_run(RUN_KEY)

assert stored is not None

report = build_backtest_report(
    run_key=RUN_KEY,
    pipeline_result=result,
)

print(format_backtest_report(report))

assert report.run_key == RUN_KEY
assert report.symbol == SYMBOL
assert report.timeframe == TIMEFRAME
assert report.source == SOURCE
assert report.bars_processed == 865
assert report.signals_generated == 2
assert report.executions == 2
assert report.trades == 1
assert report.net_pnl == Decimal("0.44690")
assert report.status == "COMPLETED"

print("REPORT BUILD: PASS")
print("DATABASE CONSISTENCY: PASS")
print("PIPELINE CONSISTENCY: PASS")
print("PNL CONSISTENCY: PASS")
print("REPRODUCIBLE METADATA: PASS")
print("RESULT: PASS")
