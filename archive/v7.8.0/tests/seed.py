"""Seed an (isolated) test database with a frozen snapshot of real bars.

The fixture is a frozen copy of 865 real USD/JPY 1min bars
(2026-09-28T18:32Z .. 2026-09-29T08:56Z, source TwelveData) taken from the
production database, so that data-dependent tests (M3, M4.15, verify_all)
run identically on any device and never touch production data.

NEVER call this against the production database: scripts/run_tests.py
always points DATA_DIR at a temporary directory first.
"""

import csv
from datetime import datetime
from decimal import Decimal
from pathlib import Path

FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "usdjpy_1min_20260928T1832_20260929T0856.csv"
)


def seed_database() -> int:
    from src.database import initialize_database
    from src.models import RawBar
    from src.storage import (
        finish_collector_run,
        save_raw_bars,
        start_collector_run,
    )
    from src.validator import validate_raw_bar

    initialize_database()

    bars = []

    with open(FIXTURE, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            bar = RawBar(
                symbol=row["symbol"],
                timeframe=row["timeframe"],
                bar_time=datetime.fromisoformat(row["bar_time"]),
                received_at=datetime.fromisoformat(row["received_at"]),
                open=Decimal(row["open"]),
                high=Decimal(row["high"]),
                low=Decimal(row["low"]),
                close=Decimal(row["close"]),
                source=row["source"],
            )

            errors = validate_raw_bar(bar)

            if errors:
                raise RuntimeError(f"Invalid fixture bar: {errors}")

            bars.append(bar)

    saved, _ = save_raw_bars(bars)

    # One consistent collector audit record (verify_all expects history).
    run_id = start_collector_run(
        "USD/JPY", "1min", "2026-09-29T08:58:00+00:00"
    )
    finish_collector_run(
        run_id,
        "2026-09-29T08:58:01+00:00",
        "SUCCESS",
        bars_saved=saved,
        bars_duplicate=0,
        bars_fetched=saved,
        bars_closed=saved,
        bars_open_skipped=0,
        bars_rejected=0,
    )

    return saved
