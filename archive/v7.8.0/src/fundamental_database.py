from src.database import get_connection


def initialize_fundamental_database() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS macro_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                country TEXT NOT NULL,
                indicator TEXT NOT NULL,
                value TEXT NOT NULL,
                unit TEXT NOT NULL,
                period TEXT NOT NULL,
                source TEXT NOT NULL,
                published_at TEXT NOT NULL,
                received_at TEXT NOT NULL,
                quality TEXT NOT NULL,
                actual TEXT,
                forecast TEXT,
                previous TEXT,
                revision TEXT,
                frequency TEXT,
                created_at TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS central_bank_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bank TEXT NOT NULL,
                country TEXT NOT NULL,
                event TEXT NOT NULL,
                policy_rate TEXT,
                previous_rate TEXT,
                source TEXT NOT NULL,
                published_at TEXT NOT NULL,
                received_at TEXT NOT NULL,
                quality TEXT NOT NULL,
                statement_tone TEXT,
                guidance TEXT,
                impact TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS yield_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                country TEXT NOT NULL,
                instrument TEXT NOT NULL,
                maturity TEXT NOT NULL,
                yield_value TEXT NOT NULL,
                source TEXT NOT NULL,
                published_at TEXT NOT NULL,
                received_at TEXT NOT NULL,
                quality TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS market_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                value TEXT NOT NULL,
                unit TEXT NOT NULL,
                source TEXT NOT NULL,
                published_at TEXT NOT NULL,
                received_at TEXT NOT NULL,
                quality TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS news_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                headline TEXT NOT NULL,
                source_name TEXT NOT NULL,
                summary TEXT,
                url TEXT,
                source TEXT NOT NULL,
                published_at TEXT NOT NULL,
                received_at TEXT NOT NULL,
                quality TEXT NOT NULL,
                impact TEXT NOT NULL,
                event_type TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS geopolitical_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                headline TEXT NOT NULL,
                region TEXT NOT NULL,
                event_subtype TEXT,
                severity TEXT NOT NULL,
                summary TEXT,
                source TEXT NOT NULL,
                published_at TEXT NOT NULL,
                received_at TEXT NOT NULL,
                quality TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_macro_lookup
            ON macro_observations(country, indicator, period, published_at)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_central_bank_lookup
            ON central_bank_events(bank, country, published_at)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_yield_lookup
            ON yield_observations(country, instrument, maturity, published_at)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_market_observation_lookup
            ON market_observations(symbol, published_at)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_news_lookup
            ON news_events(published_at, source_name)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_geopolitical_lookup
            ON geopolitical_events(published_at, region)
            """
        )

        connection.commit()
