from datetime import datetime

from src.backtest_engine import (
    BacktestContext,
    BacktestResult,
    run_backtest,
)
from src.historical_data import load_bars


def run_historical_backtest(
    symbol: str,
    timeframe: str,
    start: datetime,
    end: datetime,
    strategy,
    source: str = "TwelveData",
) -> BacktestResult:
    bars = load_bars(
        symbol=symbol,
        timeframe=timeframe,
        start=start,
        end=end,
        source=source,
    )

    return run_backtest(
        bars=bars,
        strategy=strategy,
    )
