"""Broker adapter interface.

To add a broker, implement these methods in a new module and register it
in src/broker/__init__.py:from_env(). Everything else (snapshot, gates,
certificates) picks it up automatically:

- quotes(): return QuoteObservation objects with bid AND ask, the broker's
  own quote timestamp (UTC) and source_class "BROKER_TRUTH". A quote
  without a trustworthy timestamp must be returned with source_ts=None -
  the contract check then rejects it (module 117) instead of guessing.
- account(): balance and currency (for position sizing, module 57).
- instrument_map(): broker symbol names (e.g. "EUR_USD", "EURUSD").

Order methods are intentionally absent: live execution is out of scope.
"""

from abc import ABC, abstractmethod
from datetime import datetime


class BrokerAdapter(ABC):
    source_id = "BROKER"

    @abstractmethod
    def quotes(self, symbols: list[str], now: datetime) -> list:
        """-> list[src.v78.quotes.QuoteObservation] with bid/ask."""

    @abstractmethod
    def account(self) -> dict:
        """-> {"balance": float, "currency": str, ...}"""

    def instrument_map(self) -> dict[str, str]:
        return {}

    def capability_test(self, now: datetime) -> tuple[str, str]:
        """Runtime capability (module 125): (state, detail)."""
        try:
            observations = self.quotes(["EUR/USD"], now)
        except Exception as exc:
            return "RUNTIME-FAIL", f"{type(exc).__name__}: {exc}"

        valid = [o for o in observations if o.source_ts is not None and o.bid and o.ask]
        return ("RUNTIME-PASS", f"{len(valid)} quote(s)") if valid else ("RUNTIME-FAIL", "no valid quote")
