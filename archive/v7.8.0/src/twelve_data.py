from datetime import datetime, timezone
from decimal import Decimal

import requests

from src.models import RawBar
from src.rate_limiter import (
    CreditBudget,
    ProviderRateLimited,
)


API_URL = "https://api.twelvedata.com/time_series"

_REQUIRED_FIELDS = (
    "datetime",
    "open",
    "high",
    "low",
    "close",
)


class TwelveDataFeed:
    def __init__(
        self,
        api_key: str,
        timeout: int = 10,
        budget: CreditBudget | None = None,
    ):
        self.api_key = api_key
        self.timeout = timeout
        # None -> created lazily from the environment on the first request,
        # so constructing a feed never touches the database.
        self._budget = budget

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    @property
    def budget(self) -> CreditBudget:
        if self._budget is None:
            self._budget = CreditBudget.from_env()

        return self._budget

    def _redact(self, text: str) -> str:
        """Never let the API key reach logs or the database."""
        if self.api_key:
            text = text.replace(self.api_key, "***")

        return text

    def _request(self, params: dict) -> dict:
        """One rate-limited HTTP request. Returns the parsed JSON body.

        Every request first reserves credits in the shared budget (may wait
        up to about a minute; raises RateLimitExceeded when the daily budget
        is used up). Errors never contain the API key.
        """
        self.budget.acquire(1)

        full_params = dict(params)
        full_params["apikey"] = self.api_key

        try:
            response = requests.get(
                API_URL,
                params=full_params,
                timeout=self.timeout,
            )

            if response.status_code == 429:
                raise ProviderRateLimited(
                    "Twelve Data rate limit reached (HTTP 429)"
                )

            response.raise_for_status()
            data = response.json()

        except ProviderRateLimited:
            raise
        except requests.RequestException as exc:
            raise RuntimeError(
                self._redact(f"{type(exc).__name__}: {exc}")
            ) from None

        if data.get("code") == 429:
            raise ProviderRateLimited(
                self._redact(f"Twelve Data rate limit reached: {data}")
            )

        if data.get("status") != "ok":
            raise RuntimeError(
                self._redact(f"Twelve Data API error: {data}")
            )

        return data

    @staticmethod
    def _check_meta(data: dict, symbol: str, timeframe: str) -> None:
        meta = data.get("meta") or {}

        if meta.get("symbol") != symbol:
            raise RuntimeError(
                f"Twelve Data symbol mismatch: "
                f"requested={symbol}, returned={meta.get('symbol')}"
            )

        if meta.get("interval") != timeframe:
            raise RuntimeError(
                f"Twelve Data interval mismatch: "
                f"requested={timeframe}, returned={meta.get('interval')}"
            )

    @staticmethod
    def _parse_bar(
        value: dict,
        symbol: str,
        timeframe: str,
        received_at: datetime,
    ) -> RawBar:
        for field in _REQUIRED_FIELDS:
            if field not in value:
                raise RuntimeError(f"Missing field: {field}")

        bar_time = datetime.strptime(
            value["datetime"],
            "%Y-%m-%d %H:%M:%S",
        ).replace(tzinfo=timezone.utc)

        return RawBar(
            symbol=symbol,
            timeframe=timeframe,
            bar_time=bar_time,
            received_at=received_at,
            open=Decimal(value["open"]),
            high=Decimal(value["high"]),
            low=Decimal(value["low"]),
            close=Decimal(value["close"]),
            source="TwelveData",
        )

    # ------------------------------------------------------------------
    # public API (unchanged behaviour)
    # ------------------------------------------------------------------

    def fetch_bars(
        self,
        symbol: str,
        timeframe: str = "1min",
        limit: int = 100,
    ) -> list[RawBar]:
        if limit < 1:
            raise ValueError("limit must be >= 1")

        data = self._request(
            {
                "symbol": symbol,
                "interval": timeframe,
                "outputsize": limit,
                "timezone": "UTC",
            }
        )

        self._check_meta(data, symbol, timeframe)

        values = data.get("values")

        if not values:
            raise RuntimeError("Twelve Data returned no values")

        received_at = datetime.now(timezone.utc)

        return [
            self._parse_bar(value, symbol, timeframe, received_at)
            for value in values
        ]

    def fetch_bars_range(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> list[RawBar]:
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError("start and end must contain timezone information")

        if end <= start:
            raise ValueError("end must be after start")

        data = self._request(
            {
                "symbol": symbol,
                "interval": timeframe,
                "start_date": start.astimezone(timezone.utc).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "end_date": end.astimezone(timezone.utc).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "timezone": "UTC",
            }
        )

        self._check_meta(data, symbol, timeframe)

        values = data.get("values")

        if not values:
            return []

        received_at = datetime.now(timezone.utc)

        return [
            self._parse_bar(value, symbol, timeframe, received_at)
            for value in values
        ]

    def fetch_latest_bar(
        self,
        symbol: str,
        timeframe: str = "1min",
    ) -> RawBar:
        data = self._request(
            {
                "symbol": symbol,
                "interval": timeframe,
                "outputsize": 1,
                "timezone": "UTC",
            }
        )

        values = data.get("values")

        if not values:
            raise RuntimeError("Twelve Data returned no values")

        return self._parse_bar(
            values[0],
            symbol,
            timeframe,
            datetime.now(timezone.utc),
        )
