"""OANDA v20 REST adapter - READ-ONLY (quotes + account summary).

Status: written against the public v20 documentation
(developer.oanda.com/rest-live-v20), NOT tested from this project because
no token is available here -> capability state ENV-UNVERIFIED until the
first successful run on your device (then RUNTIME-PASS is recorded).

Configuration (.env):
    FXBOT_BROKER=oanda
    OANDA_TOKEN=...                 personal access token
    OANDA_ACCOUNT_ID=...            e.g. 101-004-1234567-001
    OANDA_ENV=practice              practice (demo) or live

Only GET requests are made. The token is never written to logs or the
database.
"""

import os
from datetime import datetime, timezone

import requests

from src.broker.base import BrokerAdapter
from src.v78.quotes import QuoteObservation

UTC = timezone.utc
HOSTS = {"practice": "https://api-fxpractice.oanda.com", "live": "https://api-fxtrade.oanda.com"}


class OandaBroker(BrokerAdapter):
    source_id = "OANDA"

    def __init__(self, token: str, account_id: str, environment: str = "practice", timeout: float = 10):
        if environment not in HOSTS:
            raise ValueError("OANDA_ENV must be practice or live")

        self.token = token
        self.account_id = account_id
        self.host = HOSTS[environment]
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}", "Accept-Datetime-Format": "RFC3339"})

    @classmethod
    def from_env(cls) -> "OandaBroker":
        token = os.getenv("OANDA_TOKEN", "").strip()
        account = os.getenv("OANDA_ACCOUNT_ID", "").strip()

        if not token or not account:
            raise ValueError("OANDA_TOKEN and OANDA_ACCOUNT_ID must be set in .env")

        return cls(token, account, os.getenv("OANDA_ENV", "practice").strip().lower())

    def _get(self, path: str, params: dict | None = None) -> dict:
        try:
            response = self.session.get(f"{self.host}{path}", params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            # never leak the token
            raise RuntimeError(str(exc).replace(self.token, "***")) from None

    def instrument_map(self) -> dict[str, str]:
        return {}

    @staticmethod
    def to_oanda(symbol: str) -> str:
        return symbol.replace("/", "_")

    def quotes(self, symbols: list[str], now: datetime) -> list[QuoteObservation]:
        data = self._get(f"/v3/accounts/{self.account_id}/pricing",
                         {"instruments": ",".join(self.to_oanda(s) for s in symbols)})
        retrieval = datetime.now(UTC).timestamp()
        out = []

        for price in data.get("prices", []):
            symbol = price["instrument"].replace("_", "/")
            bids, asks = price.get("bids") or [], price.get("asks") or []

            try:
                source_ts = datetime.fromisoformat(price["time"].replace("Z", "+00:00")).timestamp()
            except (KeyError, ValueError):
                source_ts = None           # rejected by the contract check

            if not bids or not asks:
                continue

            bid, ask = float(bids[0]["price"]), float(asks[0]["price"])
            tradeable = price.get("tradeable", True)
            out.append(QuoteObservation(symbol, self.source_id, "BROKER_TRUTH", (bid + ask) / 2, source_ts, retrieval,
                                        bid=bid, ask=ask, feed_type="BROKER_BIDASK",
                                        note="" if tradeable else "not tradeable now",
                                        rejected=None if tradeable else "broker: instrument not tradeable"))

        return out

    def account(self) -> dict:
        data = self._get(f"/v3/accounts/{self.account_id}/summary").get("account", {})
        return {"balance": float(data.get("balance", 0.0)), "currency": data.get("currency"),
                "nav": float(data.get("NAV", 0.0)), "open_trades": data.get("openTradeCount")}
