from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class RawBar:
    symbol: str
    timeframe: str
    bar_time: datetime
    received_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    source: str

    @property
    def age_seconds(self) -> float:
        return (self.received_at - self.bar_time).total_seconds()
