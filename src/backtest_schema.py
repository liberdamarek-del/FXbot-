from src.database import get_connection


def initialize_backtest_schema() -> None:
    with get_connection() as connection:
        columns = connection.execute(
            "PRAGMA table_info(backtest_runs)"
        ).fetchall()

        names = {row["name"] for row in columns}

        if "data_fingerprint" not in names:
            connection.execute(
                """
                ALTER TABLE backtest_runs
                ADD COLUMN data_fingerprint TEXT
                """
            )

        connection.commit()
