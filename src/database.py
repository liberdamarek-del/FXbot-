import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from src.config import DATA_DIR


DB_PATH = DATA_DIR / "fxbot.sqlite3"


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS system_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                message TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS raw_bars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                bar_time TEXT NOT NULL,
                received_at TEXT NOT NULL,
                open TEXT NOT NULL,
                high TEXT NOT NULL,
                low TEXT NOT NULL,
                close TEXT NOT NULL,
                source TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ux_raw_bars_identity
            ON raw_bars(symbol, timeframe, bar_time, source)
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS collector_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                status TEXT NOT NULL,
                bars_saved INTEGER NOT NULL DEFAULT 0,
                bars_duplicate INTEGER NOT NULL DEFAULT 0,
                error_message TEXT,
                bars_fetched INTEGER NOT NULL DEFAULT 0,
                bars_closed INTEGER NOT NULL DEFAULT 0,
                bars_open_skipped INTEGER NOT NULL DEFAULT 0,
                bars_rejected INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        connection.commit()

    migrate_database()


# ----------------------------------------------------------------------
# Backup and additive schema migration
# ----------------------------------------------------------------------

BACKUP_DIR = DATA_DIR / "backups"

# Columns that were added to collector_runs after the first release of the
# table (collector audit). Older databases do not have them.
COLLECTOR_RUNS_ADDED_COLUMNS = (
    "bars_fetched",
    "bars_closed",
    "bars_open_skipped",
    "bars_rejected",
)


def backup_database(reason: str = "manual") -> Path:
    """Create a consistent, verified copy of the database.

    Uses the SQLite online backup API, so it is safe while other processes
    are writing. The copy is verified with PRAGMA integrity_check. Existing
    backups are never overwritten or deleted.
    """
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    safe_reason = "".join(
        ch if ch.isalnum() or ch in "-_" else "_" for ch in reason
    )

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target = BACKUP_DIR / f"fxbot_{safe_reason}_{stamp}.sqlite3"

    source = sqlite3.connect(DB_PATH)
    destination = sqlite3.connect(target)

    try:
        source.backup(destination)
        result = destination.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        destination.close()
        source.close()

    if result != "ok":
        raise RuntimeError(
            f"Backup integrity check failed: {target} ({result})"
        )

    return target


def _table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table})")
    }


def migrate_database() -> list[str]:
    """Apply additive schema migrations to an existing database.

    Only adds missing columns. Never drops or rewrites data. A verified
    backup is created before the first change. Safe to call repeatedly.
    Returns the list of applied changes (empty when nothing was needed).
    """
    with get_connection() as connection:
        columns = _table_columns(connection, "collector_runs")

    if not columns:
        return []

    missing = [
        name
        for name in COLLECTOR_RUNS_ADDED_COLUMNS
        if name not in columns
    ]

    if not missing:
        return []

    backup_database(reason="pre_migration")

    applied: list[str] = []

    with get_connection() as connection:
        for name in missing:
            connection.execute(
                f"ALTER TABLE collector_runs "
                f"ADD COLUMN {name} INTEGER NOT NULL DEFAULT 0"
            )
            applied.append(f"collector_runs.{name}")

        connection.commit()

    return applied
