from datetime import datetime, timezone

from src.database import get_connection
from src.gap_detector import detect_gaps


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def print_section(title: str) -> None:
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def main() -> int:
    print_section("FXBOT SYSTEM HEALTH CHECK")

    failures = 0
    warnings = 0

    # ------------------------------------------------------------
    # DATABASE
    # ------------------------------------------------------------
    print_section("DATABASE")

    try:
        with get_connection() as connection:
            connection.execute("SELECT 1").fetchone()

            tables = connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                ORDER BY name
                """
            ).fetchall()

            table_names = [row["name"] for row in tables]

            required_tables = {
                "raw_bars",
                "collector_runs",
                "system_events",
            }

            missing = required_tables - set(table_names)

            if missing:
                print(f"[FAIL] Missing tables: {sorted(missing)}")
                failures += 1
            else:
                print("[PASS] Required database tables")

    except Exception as exc:
        print(f"[FAIL] Database connection: {type(exc).__name__}: {exc}")
        return 1

    # ------------------------------------------------------------
    # RAW DATA
    # ------------------------------------------------------------
    print_section("RAW DATA")

    with get_connection() as connection:
        symbols = connection.execute(
            """
            SELECT
                symbol,
                timeframe,
                source,
                COUNT(*) AS count,
                MIN(bar_time) AS first_bar,
                MAX(bar_time) AS last_bar
            FROM raw_bars
            GROUP BY symbol, timeframe, source
            ORDER BY symbol, timeframe, source
            """
        ).fetchall()

    if not symbols:
        print("[FAIL] No raw bars found")
        failures += 1
    else:
        for row in symbols:
            last_bar = datetime.fromisoformat(row["last_bar"])
            age = (utc_now() - last_bar).total_seconds()

            print(
                f"[DATA] {row['symbol']} | "
                f"{row['timeframe']} | "
                f"{row['source']} | "
                f"bars={row['count']} | "
                f"first={row['first_bar']} | "
                f"last={row['last_bar']} | "
                f"age={age:.1f}s"
            )

            if age < 0:
                print("[FAIL] Latest bar is in the future")
                failures += 1

    # ------------------------------------------------------------
    # COLLECTOR HISTORY
    # ------------------------------------------------------------
    print_section("COLLECTOR")

    with get_connection() as connection:
        runs = connection.execute(
            """
            SELECT
                id,
                started_at,
                finished_at,
                symbol,
                timeframe,
                status,
                bars_fetched,
                bars_closed,
                bars_open_skipped,
                bars_saved,
                bars_duplicate,
                bars_rejected,
                error_message
            FROM collector_runs
            ORDER BY id DESC
            LIMIT 10
            """
        ).fetchall()

    if not runs:
        print("[FAIL] No collector runs found")
        failures += 1
    else:
        for run in runs:
            print(
                f"[RUN {run['id']}] "
                f"{run['symbol']} {run['timeframe']} | "
                f"{run['status']} | "
                f"fetched={run['bars_fetched']} | "
                f"closed={run['bars_closed']} | "
                f"saved={run['bars_saved']} | "
                f"duplicate={run['bars_duplicate']} | "
                f"rejected={run['bars_rejected']}"
            )

            if run["status"] == "FAILED":
                warnings += 1
                print(
                    f"[WARN] Collector run {run['id']} failed: "
                    f"{run['error_message']}"
                )

            if run["bars_closed"] > run["bars_fetched"]:
                print(f"[FAIL] Run {run['id']}: closed > fetched")
                failures += 1

            # Runs created before the collector audit schema was
            # introduced legitimately have zero values in the new
            # audit columns. Do not treat those historical runs as
            # inconsistent merely because they predate the schema.
            audit_fields_present = (
                run["bars_fetched"] > 0
                or run["bars_closed"] > 0
                or run["bars_open_skipped"] > 0
            )

            if audit_fields_present:
                accounted = (
                    run["bars_saved"]
                    + run["bars_duplicate"]
                    + run["bars_rejected"]
                )

                if accounted > run["bars_closed"]:
                    print(
                        f"[FAIL] Run {run['id']}: "
                        f"saved+duplicate+rejected > closed"
                    )
                    failures += 1
            else:
                print(
                    f"[INFO] Run {run['id']}: "
                    f"legacy audit record; detailed audit fields unavailable"
                )

    # ------------------------------------------------------------
    # GAP CHECK
    # ------------------------------------------------------------
    print_section("GAPS")

    gap_groups = []

    for row in symbols:
        key = (
            row["symbol"],
            row["timeframe"],
            row["source"],
        )

        if key in gap_groups:
            continue

        gap_groups.append(key)

        gaps = detect_gaps(
            symbol=row["symbol"],
            timeframe=row["timeframe"],
            source=row["source"],
            limit=1000,
        )

        missing_data = [
            gap for gap in gaps
            if gap["status"] == "MISSING_DATA"
        ]

        market_closed = [
            gap for gap in gaps
            if gap["status"] == "MARKET_CLOSED"
        ]

        print(
            f"[GAP] {row['symbol']} {row['timeframe']} "
            f"| total={len(gaps)} "
            f"| missing_data={len(missing_data)} "
            f"| market_closed={len(market_closed)}"
        )

        for gap in missing_data[:5]:
            print(
                f"  [MISSING] "
                f"{gap['from']} -> {gap['to']} | "
                f"missing={gap['missing_bars']}"
            )

        if len(missing_data) > 5:
            print(
                f"  ... {len(missing_data) - 5} "
                f"additional missing-data gaps"
            )

        if missing_data:
            warnings += 1

    # ------------------------------------------------------------
    # FINAL STATUS
    # ------------------------------------------------------------
    print_section("FINAL STATUS")

    print(f"FAILURES: {failures}")
    print(f"WARNINGS: {warnings}")

    if failures:
        print("RESULT: FAIL")
        return 1

    if warnings:
        print("RESULT: WARN")
        return 1

    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
