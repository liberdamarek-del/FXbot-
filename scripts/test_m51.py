from datetime import datetime, timezone
from decimal import Decimal

from src.fundamental_models import (
    CentralBankEvent,
    DataMetadata,
    DataQuality,
    GeopoliticalEvent,
    Impact,
    MacroObservation,
    MarketObservation,
    NewsEvent,
    YieldObservation,
)
from src.fundamental_database import initialize_fundamental_database
from src.database import get_connection


NOW = datetime.now(timezone.utc)

metadata = DataMetadata(
    source="M5.1_TEST",
    published_at=NOW,
    received_at=NOW,
    quality=DataQuality.VERIFIED,
)

macro = MacroObservation(
    country="US",
    indicator="CPI",
    value=Decimal("3.1"),
    unit="percent",
    period="2026-09",
    metadata=metadata,
    actual=Decimal("3.1"),
    forecast=Decimal("3.2"),
    previous=Decimal("3.3"),
    revision=Decimal("0.0"),
    frequency="monthly",
)

central_bank = CentralBankEvent(
    bank="Federal Reserve",
    country="US",
    event="TEST_RATE_DECISION",
    policy_rate=Decimal("4.00"),
    previous_rate=Decimal("4.25"),
    metadata=metadata,
    statement_tone="TEST",
    guidance="TEST",
    impact=Impact.HIGH,
)

yield_observation = YieldObservation(
    country="US",
    instrument="Treasury",
    maturity="10Y",
    yield_value=Decimal("4.10"),
    metadata=metadata,
)

market = MarketObservation(
    symbol="BRENT",
    value=Decimal("72.50"),
    unit="USD/barrel",
    metadata=metadata,
)

news = NewsEvent(
    headline="M5.1 test headline",
    source_name="M5.1_TEST",
    metadata=metadata,
    summary="Test event",
    url="https://example.invalid/test",
    impact=Impact.MEDIUM,
)

geopolitical = GeopoliticalEvent(
    headline="M5.1 test geopolitical event",
    region="GLOBAL",
    event_subtype="TEST",
    severity=Impact.HIGH,
    summary="Test event",
    metadata=metadata,
)

objects = [
    macro,
    central_bank,
    yield_observation,
    market,
    news,
    geopolitical,
]

if len(objects) != 6:
    raise AssertionError("Expected six fundamental object types")

if any(obj.metadata.quality != DataQuality.VERIFIED for obj in objects):
    raise AssertionError("Metadata quality mismatch")

initialize_fundamental_database()

expected_tables = {
    "macro_observations",
    "central_bank_events",
    "yield_observations",
    "market_observations",
    "news_events",
    "geopolitical_events",
}

with get_connection() as connection:
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name IN (
              'macro_observations',
              'central_bank_events',
              'yield_observations',
              'market_observations',
              'news_events',
              'geopolitical_events'
          )
        """
    ).fetchall()

    actual_tables = {row["name"] for row in rows}

if actual_tables != expected_tables:
    raise AssertionError(
        f"Fundamental tables mismatch: {actual_tables}"
    )

# Validation checks must reject invalid timestamps and empty identity fields.
try:
    DataMetadata(
        source="",
        published_at=NOW,
        received_at=NOW,
    )
except ValueError:
    pass
else:
    raise AssertionError("Empty source was not rejected")

try:
    MacroObservation(
        country="US",
        indicator="CPI",
        value=Decimal("3.1"),
        unit="percent",
        period="2026-09",
        metadata=DataMetadata(
            source="TEST",
            published_at=NOW,
            received_at=NOW,
        ),
        event_type="CENTRAL_BANK",
    )
except ValueError:
    pass
else:
    raise AssertionError("Invalid macro event type was not rejected")

try:
    DataMetadata(
        source="TEST",
        published_at=NOW,
        received_at=NOW.replace(year=2025),
    )
except ValueError:
    pass
else:
    raise AssertionError("Invalid timestamp ordering was not rejected")

print("M5.1 MODEL TYPES: PASS")
print("M5.1 METADATA VALIDATION: PASS")
print("M5.1 SQLITE TABLES: PASS")
print("M5.1 INVALID INPUT REJECTION: PASS")
print("RESULT: PASS")
