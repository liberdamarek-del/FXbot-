"""Compare the market-session rule with the REAL weekend bars in the database.

The session rule (src/market_session.py) assumes the FX week runs from
Sunday 17:00 to Friday 17:00 New York time. Whether the data provider
publishes bars exactly in that window is NEOVERENO until real weekend data
has been collected. Run this script after the first full weekend:

    python scripts/check_weekend_boundary.py

For every gap longer than 6 hours between consecutive 1min bars it prints
the actual last bar before / first bar after the gap, what the rule
expects, and the deviation in minutes. Read-only.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import get_connection
from src.market_session import is_fx_market_open

MIN_GAP = timedelta(hours=6)
STEP = timedelta(minutes=1)


def expected_boundaries(gap_start: datetime, gap_end: datetime):
    """Rule-based (last open bar before the closure, first open bar after)."""
    current = gap_start

    # walk forward to the first minute the rule says is closed
    while is_fx_market_open(current) and current < gap_end:
        current += STEP

    expected_last = current - STEP

    # walk forward to the first minute the rule says is open again
    while not is_fx_market_open(current) and current < gap_end + timedelta(days=1):
        current += STEP

    return expected_last, current


def find_weekend_gaps(rows):
    times = [datetime.fromisoformat(r["bar_time"]) for r in rows]
    return [
        (a, b) for a, b in zip(times, times[1:]) if b - a > MIN_GAP
    ]


def main() -> int:
    with get_connection() as connection:
        groups = connection.execute(
            """
            SELECT DISTINCT symbol, source
            FROM raw_bars
            WHERE timeframe = '1min'
            ORDER BY symbol, source
            """
        ).fetchall()

        found_any = False

        for group in groups:
            rows = connection.execute(
                """
                SELECT bar_time FROM raw_bars
                WHERE symbol = ? AND timeframe = '1min' AND source = ?
                ORDER BY bar_time ASC
                """,
                (group["symbol"], group["source"]),
            ).fetchall()

            for last_bar, first_bar in find_weekend_gaps(rows):
                found_any = True
                exp_last, exp_first = expected_boundaries(last_bar, first_bar)

                d_last = int((last_bar - exp_last).total_seconds() // 60)
                d_first = int((first_bar - exp_first).total_seconds() // 60)

                verdict = (
                    "MATCH"
                    if d_last == 0 and d_first == 0
                    else "DEVIATION"
                )

                print(f"{group['symbol']} ({group['source']}) {verdict}")
                print(f"  actual   last bar : {last_bar.isoformat()}")
                print(f"  expected last bar : {exp_last.isoformat()}  (diff {d_last:+d} min)")
                print(f"  actual   first bar: {first_bar.isoformat()}")
                print(f"  expected first bar: {exp_first.isoformat()}  (diff {d_first:+d} min)")

    if not found_any:
        print("No gap longer than 6 hours found yet - no weekend in the data.")
        print("Run again after the first full weekend has been collected.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
