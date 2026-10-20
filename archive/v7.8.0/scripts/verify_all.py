from __future__ import annotations

import importlib
import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

PASS = 0
FAIL = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL

    if condition:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        FAIL += 1
        print(f"[FAIL] {name}")
        if detail:
            print(f"       {detail}")


print("=" * 70)
print("FXBOT REGRESSION VERIFICATION")
print("=" * 70)

# ------------------------------------------------------------------
# 1. Required project files
# ------------------------------------------------------------------

required_files = [
    "src/config.py",
    "src/database.py",
    "src/models.py",
    "src/validator.py",
    "src/storage.py",
    "src/logger.py",
    "src/twelve_data.py",
    "src/bar_policy.py",
    "src/market_session.py",
    "src/gap_detector.py",
    "src/backfill.py",
    "src/backfill_missing_gaps.py",
    "src/collector.py",
]

for relative in required_files:
    path = PROJECT_ROOT / relative
    check(
        f"FILE {relative}",
        path.exists(),
        "missing file",
    )


# ------------------------------------------------------------------
# 2. Python imports
# ------------------------------------------------------------------

modules = [
    "src.config",
    "src.database",
    "src.models",
    "src.validator",
    "src.storage",
    "src.logger",
    "src.twelve_data",
    "src.bar_policy",
    "src.market_session",
    "src.gap_detector",
    "src.backfill",
    "src.backfill_missing_gaps",
    "src.collector",
]

for module in modules:
    try:
        importlib.import_module(module)
        check(f"IMPORT {module}", True)
    except Exception as exc:
        check(
            f"IMPORT {module}",
            False,
            f"{type(exc).__name__}: {exc}",
        )


# ------------------------------------------------------------------
# 3. Core model / validator
# ------------------------------------------------------------------

try:
    from src.models import RawBar
    from src.validator import validate_raw_bar

    now = datetime.now(timezone.utc)

    valid_bar = RawBar(
        symbol="TEST",
        timeframe="1min",
        bar_time=now,
        received_at=now,
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100.5"),
        source="TEST",
    )

    errors = validate_raw_bar(valid_bar)

    check(
        "VALIDATOR valid bar",
        errors == [],
        str(errors),
    )

    invalid_bar = RawBar(
        symbol="TEST",
        timeframe="1min",
        bar_time=now,
        received_at=now,
        open=Decimal("102"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100"),
        source="TEST",
    )

    errors = validate_raw_bar(invalid_bar)

    check(
        "VALIDATOR rejects invalid bar",
        "open_outside_range" in errors,
        str(errors),
    )

except Exception as exc:
    check(
        "CORE validator test",
        False,
        f"{type(exc).__name__}: {exc}",
    )


# ------------------------------------------------------------------
# 4. Market session
# ------------------------------------------------------------------

try:
    from src.market_session import is_fx_market_open

    # Block A1: the weekly boundary is Friday/Sunday 17:00 New York time,
    # i.e. 21:00 UTC in summer (EDT) and 22:00 UTC in winter (EST).
    # The earlier cases assumed 22:00 UTC for September, which was wrong.
    cases = [
        ("2026-09-25T20:59:00+00:00", True),
        ("2026-09-25T21:00:00+00:00", False),
        ("2026-09-26T12:00:00+00:00", False),
        ("2026-09-27T20:59:00+00:00", False),
        ("2026-09-27T21:00:00+00:00", True),
        ("2026-09-28T02:00:00+00:00", True),
        ("2026-12-04T21:59:00+00:00", True),
        ("2026-12-04T22:00:00+00:00", False),
        ("2026-12-06T21:59:00+00:00", False),
        ("2026-12-06T22:00:00+00:00", True),
    ]

    for value, expected in cases:
        actual = is_fx_market_open(datetime.fromisoformat(value))
        check(
            f"SESSION {value}",
            actual == expected,
            f"expected={expected}, actual={actual}",
        )

except Exception as exc:
    check(
        "MARKET SESSION",
        False,
        f"{type(exc).__name__}: {exc}",
    )


# ------------------------------------------------------------------
# 5. Bar policy
# ------------------------------------------------------------------

try:
    from src.bar_policy import is_closed_bar

    closed = datetime.fromisoformat(
        "2026-09-29T05:51:00+00:00"
    )
    current = datetime.fromisoformat(
        "2026-09-29T05:53:00+00:00"
    )

    check(
        "BAR POLICY closed 1min bar",
        is_closed_bar(closed, "1min", current),
    )

except Exception as exc:
    check(
        "BAR POLICY",
        False,
        f"{type(exc).__name__}: {exc}",
    )


# ------------------------------------------------------------------
# 6. Database integrity
# ------------------------------------------------------------------

try:
    from src.database import initialize_database, get_connection

    initialize_database()

    with get_connection() as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type='table'
                """
            ).fetchall()
        }

        indexes = {
            row["name"]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type='index'
                """
            ).fetchall()
        }

        check(
            "DATABASE system_events table",
            "system_events" in tables,
        )

        check(
            "DATABASE raw_bars table",
            "raw_bars" in tables,
        )

        check(
            "DATABASE collector_runs table",
            "collector_runs" in tables,
        )

        check(
            "DATABASE unique raw bar index",
            "ux_raw_bars_identity" in indexes,
        )

        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(collector_runs)"
            ).fetchall()
        }

        required_audit_columns = {
            "bars_saved",
            "bars_duplicate",
            "bars_fetched",
            "bars_closed",
            "bars_open_skipped",
            "bars_rejected",
        }

        check(
            "DATABASE collector audit schema",
            required_audit_columns.issubset(columns),
            f"missing={required_audit_columns - columns}",
        )

except Exception as exc:
    check(
        "DATABASE integrity",
        False,
        f"{type(exc).__name__}: {exc}",
    )


# ------------------------------------------------------------------
# 7. Existing data sanity
# ------------------------------------------------------------------

try:
    with get_connection() as connection:
        raw_count = connection.execute(
            "SELECT COUNT(*) AS n FROM raw_bars"
        ).fetchone()["n"]

        collector_count = connection.execute(
            "SELECT COUNT(*) AS n FROM collector_runs"
        ).fetchone()["n"]

        check(
            "DATABASE raw bars exist",
            raw_count > 0,
            f"count={raw_count}",
        )

        check(
            "DATABASE collector history exists",
            collector_count > 0,
            f"count={collector_count}",
        )

except Exception as exc:
    check(
        "DATABASE data sanity",
        False,
        f"{type(exc).__name__}: {exc}",
    )


# ------------------------------------------------------------------
# 8. Latest collector audit
# ------------------------------------------------------------------

try:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM collector_runs
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()

        if row is None:
            check(
                "COLLECTOR latest audit",
                False,
                "no collector runs",
            )
        else:
            check(
                "COLLECTOR latest status",
                row["status"] in {"SUCCESS", "FAILED"},
                f"status={row['status']}",
            )

            check(
                "COLLECTOR fetched >= closed",
                row["bars_fetched"] >= row["bars_closed"],
                f"fetched={row['bars_fetched']} closed={row['bars_closed']}",
            )

            check(
                "COLLECTOR closed >= saved+duplicate+rejected",
                row["bars_closed"]
                >= row["bars_saved"]
                + row["bars_duplicate"]
                + row["bars_rejected"],
                (
                    f"closed={row['bars_closed']} "
                    f"saved={row['bars_saved']} "
                    f"duplicate={row['bars_duplicate']} "
                    f"rejected={row['bars_rejected']}"
                ),
            )

except Exception as exc:
    check(
        "COLLECTOR audit",
        False,
        f"{type(exc).__name__}: {exc}",
    )


# ------------------------------------------------------------------
# Final result
# ------------------------------------------------------------------

print("=" * 70)
print(f"PASS: {PASS}")
print(f"FAIL: {FAIL}")
print("=" * 70)

if FAIL:
    print("RESULT: FAIL")
    sys.exit(1)

print("RESULT: PASS")
