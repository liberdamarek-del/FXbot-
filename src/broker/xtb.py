"""XTB placeholder (module 11, V7.7.1 appendix G).

XTB announced that its xAPI service on the legacy hosts was deactivated
from 2025-03-14; no current public API for quotes is known to this
project. XTB prices are therefore NOT available to the model: the run
certificate says BROKER-BLOCKED and every price is a public MODEL-PRICE.

If XTB (or you) provide an official API later, implement quotes() and
account() here following src/broker/base.py - nothing else has to change.
"""

from datetime import datetime

from src.broker.base import BrokerAdapter


class XtbBroker(BrokerAdapter):
    source_id = "XTB"

    def quotes(self, symbols: list[str], now: datetime) -> list:
        raise NotImplementedError("XTB: no public quote API available (legacy xAPI deactivated 2025-03-14)")

    def account(self) -> dict:
        raise NotImplementedError("XTB: no public account API available")
