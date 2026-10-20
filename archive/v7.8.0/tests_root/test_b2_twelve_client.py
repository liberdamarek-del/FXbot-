"""Block B2 - Twelve Data client: budget use, error handling, key redaction."""

import os
import tempfile
from datetime import datetime, timezone
from decimal import Decimal

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="fxbot_b2_")

import requests

import src.twelve_data as td
from src.rate_limiter import CreditBudget, ProviderRateLimited, RateLimitExceeded

UTC = timezone.utc
SECRET = "SECRETKEY123456"


class FakeResponse:
    def __init__(self, payload=None, status=200, raise_exc=None):
        self.payload = payload
        self.status_code = status
        self.raise_exc = raise_exc

    def raise_for_status(self):
        if self.raise_exc:
            raise self.raise_exc
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Error for url: {API}")

    def json(self):
        return self.payload


API = f"https://api.twelvedata.com/time_series?apikey={SECRET}"
calls = []
next_response = {"value": None}


def fake_get(url, params=None, timeout=None):
    calls.append({"url": url, "params": dict(params), "timeout": timeout})
    return next_response["value"]


td.requests.get = fake_get


def payload(symbol="USD/JPY", interval="1min", values=None, status="ok"):
    return {
        "meta": {"symbol": symbol, "interval": interval},
        "values": values if values is not None else [
            {"datetime": "2026-09-30 10:02:00", "open": "157.10", "high": "157.20",
             "low": "157.05", "close": "157.15"},
            {"datetime": "2026-09-30 10:01:00", "open": "157.00", "high": "157.12",
             "low": "156.95", "close": "157.10"},
        ],
        "status": status,
    }


class CountingBudget(CreditBudget):
    def __init__(self):
        super().__init__(per_minute=100, per_day=1000)
        self.acquired = 0

    def acquire(self, credits=1):
        self.acquired += credits
        super().acquire(credits)


budget = CountingBudget()
feed = td.TwelveDataFeed(api_key=SECRET, timeout=7, budget=budget)

# 1. fetch_bars: parameters, timezone-aware UTC bars, one credit
next_response["value"] = FakeResponse(payload())
bars = feed.fetch_bars("USD/JPY", "1min", 2)
assert budget.acquired == 1
assert calls[-1]["params"] == {
    "symbol": "USD/JPY", "interval": "1min", "outputsize": 2,
    "timezone": "UTC", "apikey": SECRET,
}
assert calls[-1]["timeout"] == 7
assert len(bars) == 2
assert bars[0].bar_time == datetime(2026, 9, 30, 10, 2, tzinfo=UTC)
assert bars[0].close == Decimal("157.15") and bars[0].source == "TwelveData"

# 2. range request and "no values" handling
next_response["value"] = FakeResponse(payload(values=[]))
assert feed.fetch_bars_range(
    "USD/JPY", "1min",
    datetime(2026, 9, 30, 10, 0, tzinfo=UTC), datetime(2026, 9, 30, 10, 5, tzinfo=UTC),
) == []
assert calls[-1]["params"]["start_date"] == "2026-09-30 10:00:00"
assert calls[-1]["params"]["end_date"] == "2026-09-30 10:05:00"

next_response["value"] = FakeResponse(payload(values=[]))
for method in (lambda: feed.fetch_bars("USD/JPY"), lambda: feed.fetch_latest_bar("USD/JPY")):
    try:
        method()
    except RuntimeError as exc:
        assert "no values" in str(exc)
    else:
        raise AssertionError("empty values accepted")

# 3. latest bar
next_response["value"] = FakeResponse(payload())
assert feed.fetch_latest_bar("USD/JPY").close == Decimal("157.15")

# 4. symbol / interval mismatch
for wrong in (payload(symbol="EUR/USD"), payload(interval="5min")):
    next_response["value"] = FakeResponse(wrong)
    try:
        feed.fetch_bars("USD/JPY", "1min", 2)
    except RuntimeError as exc:
        assert "mismatch" in str(exc)
    else:
        raise AssertionError("mismatch accepted")

# 5. provider rate limit (HTTP 429 and JSON code 429)
next_response["value"] = FakeResponse(status=429, payload={})
try:
    feed.fetch_bars("USD/JPY")
except ProviderRateLimited:
    pass
else:
    raise AssertionError("HTTP 429 not detected")

next_response["value"] = FakeResponse({"code": 429, "message": "limit", "status": "error"})
try:
    feed.fetch_bars("USD/JPY")
except ProviderRateLimited:
    pass
else:
    raise AssertionError("JSON 429 not detected")

# 6. API error payloads never leak the key
next_response["value"] = FakeResponse(
    {"code": 401, "message": f"bad key {SECRET}", "status": "error"}
)
try:
    feed.fetch_bars("USD/JPY")
except RuntimeError as exc:
    assert SECRET not in str(exc), str(exc)
    assert "***" in str(exc)
else:
    raise AssertionError("API error not raised")

# 7. network / HTTP errors: message redacted, no chained original exception
next_response["value"] = FakeResponse(raise_exc=requests.ConnectionError(f"failed {API}"))
try:
    feed.fetch_bars("USD/JPY")
except RuntimeError as exc:
    assert SECRET not in str(exc), str(exc)
    assert exc.__cause__ is None and exc.__suppress_context__ is True
else:
    raise AssertionError("network error not raised")

next_response["value"] = FakeResponse(status=500, payload={})
try:
    feed.fetch_bars("USD/JPY")
except RuntimeError as exc:
    assert SECRET not in str(exc), str(exc)
else:
    raise AssertionError("HTTP 500 not raised")

# 8. budget exhaustion stops BEFORE any HTTP call is made
tiny = CreditBudget(per_minute=5, per_day=1, provider="test-tiny")   # own counter
feed2 = td.TwelveDataFeed(api_key=SECRET, budget=tiny)
before = len(calls)
next_response["value"] = FakeResponse(payload())
feed2.fetch_bars("USD/JPY")           # uses the single daily credit
try:
    feed2.fetch_bars("USD/JPY")
except RateLimitExceeded:
    pass
else:
    raise AssertionError("daily budget ignored by the client")
assert len(calls) == before + 1, "second request must not reach the network"

# 9. construction has no side effects (lazy budget)
os.environ["TWELVE_DATA_CREDITS_PER_MINUTE"] = "8"
lazy = td.TwelveDataFeed(api_key="x")
assert lazy._budget is None

print("=" * 60)
print("B2 TWELVE DATA CLIENT")
print("=" * 60)
print("PARAMETERS / PARSING: PASS")
print("CREDIT RESERVED PER REQUEST: PASS")
print("EMPTY VALUES / MISMATCH: PASS")
print("PROVIDER 429 (HTTP AND JSON): PASS")
print("API KEY NEVER IN ERRORS: PASS")
print("BUDGET STOPS REQUEST BEFORE NETWORK: PASS")
print("RESULT: PASS")
print("=" * 60)
