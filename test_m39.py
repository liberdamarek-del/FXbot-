from datetime import datetime
from decimal import Decimal

from src.backtest_engine import BacktestContext
from src.backtest_execution import Signal
from src.backtest_pipeline import run_pipeline
from src.database import get_connection
from src.historical_data import load_bars


SYMBOL = "USD/JPY"
TIMEFRAME = "1min"
SOURCE = "TwelveData"


with get_connection() as connection:
    row = connection.execute(
        """
        SELECT MIN(bar_time) AS first_bar,
               MAX(bar_time) AS last_bar,
               COUNT(*) AS count
        FROM raw_bars
        WHERE symbol = ?
          AND timeframe = ?
          AND source = ?
        """,
        (SYMBOL, TIMEFRAME, SOURCE),
    ).fetchone()


if row["count"] < 3:
    print("INSUFFICIENT HISTORICAL DATA: FAIL")
    raise SystemExit(1)


start = datetime.fromisoformat(row["first_bar"])
end = datetime.fromisoformat(row["last_bar"])


bars = load_bars(
    symbol=SYMBOL,
    timeframe=TIMEFRAME,
    start=start,
    end=end,
    source=SOURCE,
)


if len(bars) != row["count"]:
    print("READER COUNT MATCH: FAIL")
    raise SystemExit(1)


if bars[0].bar_time.tzinfo is None:
    print("TIMEZONE: FAIL")
    raise SystemExit(1)


def strategy(context: BacktestContext) -> Signal:
    if context.index == 0:
        return Signal.ENTER_LONG

    if context.index == 1:
        return Signal.EXIT

    return Signal.HOLD


result = run_pipeline(
    bars=bars,
    strategy=strategy,
    quantity=Decimal("1"),
)


if result.bars_processed != len(bars):
    print("BARS PROCESSED: FAIL")
    raise SystemExit(1)

if result.signals_generated != 2:
    print("SIGNALS GENERATED: FAIL")
    raise SystemExit(1)

if result.executions != 2:
    print("EXECUTIONS: FAIL")
    raise SystemExit(1)

if len(result.trades) != 1:
    print("TRADE COUNT: FAIL")
    raise SystemExit(1)


trade = result.trades[0]


if trade.entry_price != bars[1].open:
    print("REAL ENTRY OPEN: FAIL")
    raise SystemExit(1)

if trade.exit_price != bars[2].open:
    print("REAL EXIT OPEN: FAIL")
    raise SystemExit(1)


expected_pnl = bars[2].open - bars[1].open

if trade.gross_pnl != expected_pnl:
    print("REAL DATA PNL: FAIL")
    raise SystemExit(1)


print("=" * 70)
print("M3.9 REAL SQLITE -> BACKTEST PIPELINE")
print("=" * 70)
print(f"SYMBOL: {SYMBOL}")
print(f"TIMEFRAME: {TIMEFRAME}")
print(f"DB BARS: {row['count']}")
print(f"LOADED BARS: {len(bars)}")
print(f"FIRST BAR: {bars[0].bar_time.isoformat()}")
print(f"LAST BAR: {bars[-1].bar_time.isoformat()}")
print(f"ENTRY BAR OPEN: {bars[1].open}")
print(f"EXIT BAR OPEN: {bars[2].open}")
print(f"GROSS PNL: {trade.gross_pnl}")
print("SQLITE -> HISTORICAL BAR: PASS")
print("REAL DATA PIPELINE: PASS")
print("NEXT-BAR EXECUTION: PASS")
print("REAL ENTRY OPEN: PASS")
print("REAL EXIT OPEN: PASS")
print("REAL DATA PNL: PASS")
print("RESULT: PASS")
print("=" * 70)
