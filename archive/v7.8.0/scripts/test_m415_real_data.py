from datetime import datetime, timezone
from decimal import Decimal

from src.database import get_connection
from src.historical_data import load_bars
from src.paper_session import run_and_persist_paper_session
from src.paper_session_audit import get_paper_session
from src.paper_trading import PaperTradingEngine
from src.trade_simulator import Side


SYMBOL = "USD/JPY"
TIMEFRAME = "1min"
SOURCE = "TwelveData"
LIMIT = 100
INITIAL_CASH = Decimal("1000000")
QUANTITY = Decimal("1")


def get_real_data_bounds():
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT bar_time
            FROM raw_bars
            WHERE symbol = ?
              AND timeframe = ?
              AND source = ?
            ORDER BY bar_time DESC
            LIMIT ?
            """,
            (SYMBOL, TIMEFRAME, SOURCE, LIMIT),
        ).fetchall()

    if len(rows) < 10:
        raise AssertionError(
            f"Too few stored bars: {len(rows)}"
        )

    times = [
        datetime.fromisoformat(row["bar_time"])
        for row in reversed(rows)
    ]

    if any(value.tzinfo is None for value in times):
        raise AssertionError("Stored bar timestamp is naive")

    return times[0], times[-1]


def run_one(bars, label):
    engine = PaperTradingEngine(
        initial_cash=INITIAL_CASH,
        quantity=QUANTITY,
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
    )

    engine.open_position(
        side=Side.LONG,
        entry_time=bars[0].bar_time,
        entry_price=bars[0].open,
    )

    session_key = (
        f"M4.15_{label}_"
        f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}"
    )

    result = run_and_persist_paper_session(
        bars=bars,
        engine=engine,
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        session_key=session_key,
        created_at=datetime.now(timezone.utc),
    )

    stored = get_paper_session(session_key)

    if stored is None:
        raise AssertionError("Paper session audit readback failed")

    if result.bars_processed != len(bars):
        raise AssertionError("bars_processed mismatch")

    if result.trades != 1:
        raise AssertionError(
            f"Expected 1 trade, got {result.trades}"
        )

    if not result.forced_close:
        raise AssertionError("Expected END_OF_DATA forced close")

    expected_pnl = bars[-1].close - bars[0].open

    if result.realized_pnl != expected_pnl:
        raise AssertionError(
            f"P&L mismatch: "
            f"expected {expected_pnl}, got {result.realized_pnl}"
        )

    expected_equity = INITIAL_CASH + expected_pnl

    if result.final_equity != expected_equity:
        raise AssertionError(
            f"Equity mismatch: "
            f"expected {expected_equity}, got {result.final_equity}"
        )

    if Decimal(stored["realized_pnl"]) != result.realized_pnl:
        raise AssertionError("Stored P&L mismatch")

    if Decimal(stored["final_equity"]) != result.final_equity:
        raise AssertionError("Stored equity mismatch")

    return result


def main():
    print("M4.15 REAL DATA END-TO-END")
    print("--------------------------------")

    start, end = get_real_data_bounds()

    bars = load_bars(
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        start=start,
        end=end,
        source=SOURCE,
    )

    if len(bars) < 10:
        raise AssertionError(
            f"Historical loader returned too few bars: {len(bars)}"
        )

    if bars[0].bar_time != start:
        raise AssertionError("Loader first boundary mismatch")

    if bars[-1].bar_time != end:
        raise AssertionError("Loader last boundary mismatch")

    for previous, current in zip(bars, bars[1:]):
        if current.bar_time <= previous.bar_time:
            raise AssertionError("Historical bars are not chronological")

        if current.bar_time.tzinfo is None:
            raise AssertionError("Historical bar timestamp is naive")

    print(f"REAL DATA LOAD: PASS ({len(bars)} bars)")
    print(f"FIRST BAR: {bars[0].bar_time.isoformat()}")
    print(f"LAST BAR:  {bars[-1].bar_time.isoformat()}")
    print(f"FIRST OPEN: {bars[0].open}")
    print(f"LAST CLOSE: {bars[-1].close}")

    result1 = run_one(bars, "A")
    result2 = run_one(bars, "B")

    if result1.bars_processed != result2.bars_processed:
        raise AssertionError("Determinism bars mismatch")

    if result1.trades != result2.trades:
        raise AssertionError("Determinism trade count mismatch")

    if result1.realized_pnl != result2.realized_pnl:
        raise AssertionError("Determinism P&L mismatch")

    if result1.final_equity != result2.final_equity:
        raise AssertionError("Determinism equity mismatch")

    print("SESSION EXECUTION: PASS")
    print("AUDIT PERSISTENCE: PASS")
    print("AUDIT READBACK: PASS")
    print("P&L CONSISTENCY: PASS")
    print("EQUITY CONSISTENCY: PASS")
    print("DETERMINISM: PASS")
    print("POSITION CLOSED: PASS")
    print("RESULT: PASS")


if __name__ == "__main__":
    main()
