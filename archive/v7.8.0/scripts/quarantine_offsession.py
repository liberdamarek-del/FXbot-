"""Move stored provider bars that lie OUTSIDE the trading session out of raw_bars.

    python scripts/quarantine_offsession.py            # dry run: only counts, changes nothing
    python scripts/quarantine_offsession.py --apply    # verified backup, then move

Why: the provider also delivers off-hours quotes (Saturday / Sunday before the
open). They are thin, wildly ranged and would distort ATR, trend and levels.
Nothing is deleted: the bars are MOVED into the table `raw_bars_offsession`
(same columns plus quarantined_at) in one transaction after a verified
database backup, so they can be inspected or restored. Bars derived from
1-minute data (source Derived1min) and bars inside the session are never
touched. Safe to run repeatedly.
"""

import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data_update import bar_in_session  # noqa: E402
from src.database import (  # noqa: E402
    backup_database,
    get_connection,
    initialize_database,
)
from src.gap_detector import timeframe_delta  # noqa: E402

PROVIDER_SOURCE = "TwelveData"
TIMEFRAMES = ("1min", "5min")
CHUNK = 500


def find_offsession() -> list[tuple[int, str, str, str]]:
    """(id, symbol, timeframe, bar_time) of stored provider bars outside the session."""
    intervals = {tf: timeframe_delta(tf) for tf in TIMEFRAMES}
    found = []

    with get_connection() as connection:
        cursor = connection.execute(
            """
            SELECT id, symbol, timeframe, bar_time
            FROM raw_bars
            WHERE source = ? AND timeframe IN (?, ?)
            """,
            (PROVIDER_SOURCE, *TIMEFRAMES),
        )

        for row in cursor:
            bar_time = datetime.fromisoformat(row["bar_time"]).astimezone(timezone.utc)

            if not bar_in_session(bar_time, intervals[row["timeframe"]]):
                found.append((row["id"], row["symbol"], row["timeframe"], row["bar_time"]))

    return found


def _ensure_table(connection) -> list[str]:
    columns = [
        r["name"]
        for r in connection.execute("PRAGMA table_info(raw_bars)")
        if r["name"] != "id"
    ]

    connection.execute(
        "CREATE TABLE IF NOT EXISTS raw_bars_offsession ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        + ", ".join(f"{name} TEXT" for name in columns)
        + ", quarantined_at TEXT NOT NULL, reason TEXT NOT NULL)"
    )

    return columns


def quarantine(apply: bool = False) -> dict:
    initialize_database()
    found = find_offsession()
    per_symbol = Counter(symbol for _, symbol, _, _ in found)
    result = {"found": len(found), "per_symbol": dict(per_symbol), "moved": 0, "backup": None}

    if not apply or not found:
        return result

    result["backup"] = str(backup_database(reason="before_quarantine_offsession"))
    ids = [item[0] for item in found]
    stamp = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        connection.execute("BEGIN IMMEDIATE")

        try:
            columns = _ensure_table(connection)
            names = ", ".join(columns)
            inserted = deleted = 0

            for start in range(0, len(ids), CHUNK):
                part = ids[start:start + CHUNK]
                marks = ",".join("?" * len(part))

                cursor = connection.execute(
                    f"INSERT INTO raw_bars_offsession ({names}, quarantined_at, reason) "
                    f"SELECT {names}, ?, 'OUTSIDE_TRADING_SESSION' FROM raw_bars "
                    f"WHERE id IN ({marks})",
                    [stamp, *part],
                )
                inserted += cursor.rowcount

                cursor = connection.execute(
                    f"DELETE FROM raw_bars WHERE id IN ({marks})", part
                )
                deleted += cursor.rowcount

            if not (inserted == deleted == len(ids)):
                raise RuntimeError(
                    f"count mismatch: found {len(ids)}, copied {inserted}, removed {deleted}"
                )

            connection.execute("COMMIT")

        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise

    result["moved"] = len(ids)
    return result


def main(argv: list[str]) -> int:
    apply = "--apply" in argv
    result = quarantine(apply=apply)

    print("=" * 60)
    print("FXBOT - BARY MIMO OBCHODNI DOBU")
    print("=" * 60)
    print(f"nalezeno: {result['found']}")

    for symbol, count in sorted(result["per_symbol"].items()):
        print(f"  {symbol}: {count}")

    if not result["found"]:
        print("Nic k presunuti.")
    elif not apply:
        print("\nTOTO JE ZKOUSKA - nic se nezmenilo.")
        print("Presun provedes: python scripts/quarantine_offsession.py --apply")
    else:
        print(f"\nPRESUNUTO do raw_bars_offsession: {result['moved']}")
        print(f"zaloha databaze: {result['backup']}")

    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
