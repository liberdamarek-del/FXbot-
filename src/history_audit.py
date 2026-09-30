from src.database import get_connection


def initialize_history_audit() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS history_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                cycle INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                status TEXT NOT NULL,
                gaps_found INTEGER NOT NULL DEFAULT 0,
                missing_gaps INTEGER NOT NULL DEFAULT 0,
                market_closed_gaps INTEGER NOT NULL DEFAULT 0,
                repair_candidates INTEGER NOT NULL DEFAULT 0,
                repaired INTEGER NOT NULL DEFAULT 0,
                failed INTEGER NOT NULL DEFAULT 0,
                skipped INTEGER NOT NULL DEFAULT 0,
                bars_saved INTEGER NOT NULL DEFAULT 0,
                bars_duplicate INTEGER NOT NULL DEFAULT 0,
                bars_rejected INTEGER NOT NULL DEFAULT 0,
                remaining_missing_gaps INTEGER NOT NULL DEFAULT 0,
                unprocessed_missing_gaps INTEGER NOT NULL DEFAULT 0,
                verification TEXT NOT NULL,
                error_message TEXT
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_history_runs_lookup
            ON history_runs(symbol, timeframe, started_at)
            """
        )

        connection.commit()


def start_history_run(
    cycle: int,
    symbol: str,
    timeframe: str,
    started_at: str,
) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO history_runs (
                started_at,
                cycle,
                symbol,
                timeframe,
                status,
                verification
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                started_at,
                cycle,
                symbol,
                timeframe,
                "RUNNING",
                "RUNNING",
            ),
        )

        connection.commit()
        return int(cursor.lastrowid)


def finish_history_run(
    run_id: int,
    finished_at: str,
    result: dict | None = None,
    error_message: str | None = None,
) -> None:
    result = result or {}

    verification = result.get("verification", "FAIL")
    status = "PASS" if verification == "PASS" else "FAIL"

    if error_message:
        status = "ERROR"
        verification = "ERROR"

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE history_runs
            SET finished_at = ?,
                status = ?,
                gaps_found = ?,
                missing_gaps = ?,
                market_closed_gaps = ?,
                repair_candidates = ?,
                repaired = ?,
                failed = ?,
                skipped = ?,
                bars_saved = ?,
                bars_duplicate = ?,
                bars_rejected = ?,
                remaining_missing_gaps = ?,
                unprocessed_missing_gaps = ?,
                verification = ?,
                error_message = ?
            WHERE id = ?
            """,
            (
                finished_at,
                status,
                int(result.get("gaps_found", 0)),
                int(result.get("missing_gaps", 0)),
                int(result.get("market_closed_gaps", 0)),
                int(result.get("repair_candidates", 0)),
                int(result.get("repaired", 0)),
                int(result.get("failed", 0)),
                int(result.get("skipped", 0)),
                int(result.get("bars_saved", 0)),
                int(result.get("bars_duplicate", 0)),
                int(result.get("bars_rejected", 0)),
                int(result.get("remaining_missing_gaps", 0)),
                int(result.get("unprocessed_missing_gaps", 0)),
                verification,
                error_message,
                run_id,
            ),
        )

        connection.commit()
