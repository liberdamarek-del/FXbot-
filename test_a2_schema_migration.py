"""Block A2/A4 - schema for new databases, verified backup, additive migration."""

import os
import shutil
import sqlite3
import tempfile
from datetime import datetime, timezone

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="fxbot_a2_")

from src import database
from src.database import (
    BACKUP_DIR,
    COLLECTOR_RUNS_ADDED_COLUMNS,
    DB_PATH,
    backup_database,
    get_connection,
    initialize_database,
    migrate_database,
)
from src.storage import finish_collector_run, start_collector_run


def columns(table: str) -> set[str]:
    with get_connection() as connection:
        return {r["name"] for r in connection.execute(f"PRAGMA table_info({table})")}


def backups() -> list:
    return sorted(BACKUP_DIR.glob("*.sqlite3")) if BACKUP_DIR.exists() else []


# ------------------------------------------------------------------
# 1. NEW database: complete schema, collector audit works, no backup
# ------------------------------------------------------------------
initialize_database()

for name in COLLECTOR_RUNS_ADDED_COLUMNS:
    assert name in columns("collector_runs"), name

now = datetime.now(timezone.utc).isoformat()
run_id = start_collector_run("USD/JPY", "1min", now)
finish_collector_run(
    run_id, now, "SUCCESS",
    bars_saved=1, bars_fetched=3, bars_closed=2, bars_open_skipped=1,
)

with get_connection() as connection:
    row = connection.execute(
        "SELECT * FROM collector_runs WHERE id = ?", (run_id,)
    ).fetchone()
    assert row["bars_fetched"] == 3 and row["bars_open_skipped"] == 1

assert backups() == [], "fresh database must not create a backup"
assert migrate_database() == []

# ------------------------------------------------------------------
# 2. OLD database (collector_runs without audit columns): migration
# ------------------------------------------------------------------
DB_PATH.unlink()
if BACKUP_DIR.exists():
    shutil.rmtree(BACKUP_DIR)

old = sqlite3.connect(DB_PATH)
old.execute(
    """
    CREATE TABLE collector_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TEXT NOT NULL,
        finished_at TEXT,
        symbol TEXT NOT NULL,
        timeframe TEXT NOT NULL,
        status TEXT NOT NULL,
        bars_saved INTEGER NOT NULL DEFAULT 0,
        bars_duplicate INTEGER NOT NULL DEFAULT 0,
        error_message TEXT
    )
    """
)
old.execute(
    "INSERT INTO collector_runs (started_at, symbol, timeframe, status, bars_saved) "
    "VALUES ('2026-09-29T03:50:58+00:00', 'USD/JPY', '1min', 'SUCCESS', 7)"
)
old.commit()
old.close()

initialize_database()

for name in COLLECTOR_RUNS_ADDED_COLUMNS:
    assert name in columns("collector_runs"), name

with get_connection() as connection:
    row = connection.execute("SELECT * FROM collector_runs").fetchone()
    assert row["bars_saved"] == 7, "existing data must be preserved"
    assert row["bars_fetched"] == 0 and row["bars_rejected"] == 0

found = backups()
assert len(found) == 1, found
assert "pre_migration" in found[0].name

verify = sqlite3.connect(found[0])
assert verify.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
backup_cols = {r[1] for r in verify.execute("PRAGMA table_info(collector_runs)")}
assert "bars_fetched" not in backup_cols, "backup must hold the PRE-migration schema"
assert verify.execute("SELECT bars_saved FROM collector_runs").fetchone()[0] == 7
verify.close()

# idempotent: a second run changes nothing and creates no new backup
assert migrate_database() == []
initialize_database()
assert len(backups()) == 1

# ------------------------------------------------------------------
# 3. Manual backup + guard
# ------------------------------------------------------------------
manual = backup_database(reason="manual test/reason")
assert manual.exists() and "manual_test_reason" in manual.name
assert len(backups()) == 2

DB_PATH.unlink()
try:
    backup_database()
except FileNotFoundError:
    pass
else:
    raise AssertionError("backup of a missing database must fail")

print("=" * 60)
print("A2 SCHEMA / BACKUP / MIGRATION")
print("=" * 60)
print("NEW DATABASE FULL SCHEMA: PASS")
print("OLD DATABASE MIGRATION: PASS")
print("DATA PRESERVED: PASS")
print("BACKUP VERIFIED (PRE-MIGRATION SCHEMA): PASS")
print("IDEMPOTENT: PASS")
print("MANUAL BACKUP / MISSING DB GUARD: PASS")
print("RESULT: PASS")
print("=" * 60)
