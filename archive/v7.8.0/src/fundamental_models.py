from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum


class DataQuality(str, Enum):
    RAW = "RAW"
    VALIDATED = "VALIDATED"
    VERIFIED = "VERIFIED"


class Impact(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    UNKNOWN = "UNKNOWN"


class EventType(str, Enum):
    ECONOMIC = "ECONOMIC"
    CENTRAL_BANK = "CENTRAL_BANK"
    YIELD = "YIELD"
    MARKET = "MARKET"
    NEWS = "NEWS"
    GEOPOLITICAL = "GEOPOLITICAL"
    POLITICAL = "POLITICAL"


@dataclass(frozen=True)
class DataMetadata:
    source: str
    published_at: datetime
    received_at: datetime
    quality: DataQuality = DataQuality.RAW

    def __post_init__(self):
        if not self.source.strip():
            raise ValueError("source must not be empty")
        if self.published_at.tzinfo is None:
            raise ValueError("published_at must contain timezone information")
        if self.received_at.tzinfo is None:
            raise ValueError("received_at must contain timezone information")
        if self.received_at < self.published_at:
            raise ValueError(
                "received_at cannot be earlier than published_at"
            )


@dataclass(frozen=True)
class MacroObservation:
    country: str
    indicator: str
    value: Decimal
    unit: str
    period: str
    metadata: DataMetadata
    actual: Decimal | None = None
    forecast: Decimal | None = None
    previous: Decimal | None = None
    revision: Decimal | None = None
    frequency: str | None = None
    event_type: EventType = EventType.ECONOMIC

    def __post_init__(self):
        if not self.country.strip():
            raise ValueError("country must not be empty")
        if not self.indicator.strip():
            raise ValueError("indicator must not be empty")
        if not self.unit.strip():
            raise ValueError("unit must not be empty")
        if not self.period.strip():
            raise ValueError("period must not be empty")
        if self.event_type != EventType.ECONOMIC:
            raise ValueError("MacroObservation must use ECONOMIC event_type")


@dataclass(frozen=True)
class CentralBankEvent:
    bank: str
    country: str
    event: str
    policy_rate: Decimal | None
    previous_rate: Decimal | None
    metadata: DataMetadata
    statement_tone: str | None = None
    guidance: str | None = None
    impact: Impact = Impact.UNKNOWN

    def __post_init__(self):
        if not self.bank.strip():
            raise ValueError("bank must not be empty")
        if not self.country.strip():
            raise ValueError("country must not be empty")
        if not self.event.strip():
            raise ValueError("event must not be empty")


@dataclass(frozen=True)
class YieldObservation:
    country: str
    instrument: str
    maturity: str
    yield_value: Decimal
    metadata: DataMetadata

    def __post_init__(self):
        if not self.country.strip():
            raise ValueError("country must not be empty")
        if not self.instrument.strip():
            raise ValueError("instrument must not be empty")
        if not self.maturity.strip():
            raise ValueError("maturity must not be empty")


@dataclass(frozen=True)
class MarketObservation:
    symbol: str
    value: Decimal
    unit: str
    metadata: DataMetadata

    def __post_init__(self):
        if not self.symbol.strip():
            raise ValueError("symbol must not be empty")
        if not self.unit.strip():
            raise ValueError("unit must not be empty")


@dataclass(frozen=True)
class NewsEvent:
    headline: str
    source_name: str
    metadata: DataMetadata
    summary: str | None = None
    url: str | None = None
    impact: Impact = Impact.UNKNOWN
    event_type: EventType = EventType.NEWS

    def __post_init__(self):
        if not self.headline.strip():
            raise ValueError("headline must not be empty")
        if not self.source_name.strip():
            raise ValueError("source_name must not be empty")
        if self.event_type not in {
            EventType.NEWS,
            EventType.POLITICAL,
        }:
            raise ValueError(
                "NewsEvent must use NEWS or POLITICAL event_type"
            )


@dataclass(frozen=True)
class GeopoliticalEvent:
    headline: str
    region: str
    metadata: DataMetadata
    event_subtype: str | None = None
    severity: Impact = Impact.UNKNOWN
    summary: str | None = None

    def __post_init__(self):
        if not self.headline.strip():
            raise ValueError("headline must not be empty")
        if not self.region.strip():
            raise ValueError("region must not be empty")
