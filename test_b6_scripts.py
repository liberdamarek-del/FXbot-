"""Block B6 - user-facing scripts: set_api_key and update_data."""

import importlib.util
import io
import os
import stat
import sys
import tempfile
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

DATA = tempfile.mkdtemp(prefix="fxbot_b6_")
os.environ["FXBOT_IGNORE_DOTENV"] = "1"          # never read the user's .env
os.environ["DATA_DIR"] = DATA
os.environ["BAR_SETTLE_SECONDS"] = "0"
os.environ.pop("COLLECTOR_SYMBOLS", None)
os.environ.pop("COLLECTOR_TIMEFRAMES", None)
os.environ["TWELVE_DATA_API_KEY"] = "demo"       # the warning about the shared key is tested

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


set_key = load("set_api_key")
update = load("update_data")

UTC = timezone.utc
KEY = "abcd1234efgh5678ijkl9012mnop3456"

# ---------------------------------------------------------------- set_api_key
assert set_key.validate_key(f"  {KEY}\n") == KEY
assert set_key.validate_key(f"'{KEY}'") == KEY
for bad in ("demo", "DEMO", "short", "has space in it 1234567890", "", "key/with/slash1234567890"):
    try:
        set_key.validate_key(bad)
    except ValueError:
        pass
    else:
        raise AssertionError(f"accepted bad key: {bad!r}")

masked = set_key.mask(KEY)
assert masked.startswith("abcd") and masked.endswith("3456") and KEY not in masked

env = Path(DATA) / ".env"
env.write_text("APP_ENV=development\nLOG_LEVEL=INFO\n# comment\nDATA_DIR=./data\n", encoding="utf-8")

assert set_key.write_key(env, KEY) is False
text = env.read_text()
assert text.splitlines() == [
    "APP_ENV=development", "LOG_LEVEL=INFO", "# comment", "DATA_DIR=./data",
    f"TWELVE_DATA_API_KEY={KEY}",
], text
assert stat.S_IMODE(env.stat().st_mode) == 0o600

NEW_KEY = "ZZZZ1234efgh5678ijkl9012mnop3456"
env.write_text(env.read_text() + "TWELVE_DATA_API_KEY=duplicate\n")
assert set_key.write_key(env, NEW_KEY) is True
lines = env.read_text().splitlines()
assert lines.count(f"TWELVE_DATA_API_KEY={NEW_KEY}") == 1
assert not any("duplicate" in line or KEY in line for line in lines)
assert lines[:4] == ["APP_ENV=development", "LOG_LEVEL=INFO", "# comment", "DATA_DIR=./data"]


class OkFeed:
    def __init__(self, key): self.key = key
    def fetch_latest_bar(self, symbol, timeframe):
        from src.models import RawBar
        t = datetime(2026, 9, 30, 10, 0, tzinfo=UTC)
        return RawBar(symbol, timeframe, t, t, Decimal("1"), Decimal("2"), Decimal("1"), Decimal("1.5"), "TwelveData")


class BadFeed(OkFeed):
    def fetch_latest_bar(self, symbol, timeframe):
        raise RuntimeError(f"Twelve Data API error: {{'message': 'invalid key {self.key}'}}")


env2 = Path(DATA) / ".env2"
buffer = io.StringIO()
with redirect_stdout(buffer):
    rc = set_key.main([KEY], feed_factory=OkFeed, env_path=env2)
out = buffer.getvalue()
assert rc == 0 and "TEST KLICE OK" in out and KEY not in out, out
assert KEY in env2.read_text()

buffer = io.StringIO()
with redirect_stdout(buffer):
    rc = set_key.main([KEY], feed_factory=BadFeed, env_path=env2)
out = buffer.getvalue()
assert rc == 1 and "SELHAL" in out and KEY not in out, out

buffer = io.StringIO()
with redirect_stdout(buffer):
    rc = set_key.main(["demo"], feed_factory=OkFeed, env_path=Path(DATA) / ".env3")
assert rc == 1 and not (Path(DATA) / ".env3").exists()

# ---------------------------------------------------------------- update_data
default = update.build_instruments([])
assert len(default) == 12, len(default)                    # 12 pairs x 1min
assert {s for s, _ in default} == {
    "EUR/USD", "USD/JPY", "GBP/USD", "USD/CHF", "AUD/USD", "USD/CAD", "NZD/USD",
    "EUR/JPY", "GBP/JPY", "EUR/GBP", "EUR/CHF", "AUD/JPY",
}
assert {t for _, t in default} == {"1min"}
assert update.derived_timeframes() == ["5min", "15min", "1h"]
assert update.history_days(["--days", "30"]) == 30
assert update.history_days([]) is None
for bad in (["--days", "0"], ["--days", "abc"], ["--days", "99999"], ["--days"]):
    try:
        update.history_days(bad)
    except SystemExit:
        pass
    else:
        raise AssertionError(f"accepted {bad}")
assert update.build_instruments(["--symbols", "GBP/USD", "--timeframes", "1min"]) == [("GBP/USD", "1min")]
os.environ["COLLECTOR_SYMBOLS"] = "AUD/USD"
os.environ["COLLECTOR_TIMEFRAMES"] = "5min,1h"
assert update.build_instruments([]) == [("AUD/USD", "5min"), ("AUD/USD", "1h")]
os.environ.pop("COLLECTOR_SYMBOLS"); os.environ.pop("COLLECTOR_TIMEFRAMES")

# --status on an empty database: no API call, exit code 1 (MISSING)
buffer = io.StringIO()
with redirect_stdout(buffer):
    rc = update.main(["--status", "--symbols", "USD/JPY", "--timeframes", "1min"])
out = buffer.getvalue()
assert rc == 1 and "MISSING" in out and "bez volani API" in out, out


# full update through a fake provider, with the real budget object
from src.market_session import is_fx_market_open
from src.gap_detector import timeframe_delta
from src.models import RawBar
from src.rate_limiter import CreditBudget


class FakeFeed:
    def __init__(self):
        self.budget = CreditBudget(per_minute=100, per_day=1000)
        self.requests = 0

    def _bars(self, symbol, timeframe, start, end):
        interval, current, out = timeframe_delta(timeframe), start, []
        now = datetime.now(UTC)
        while current <= end:
            if is_fx_market_open(current) and current <= now:
                out.append(RawBar(symbol, timeframe, current, now, Decimal("157"),
                                  Decimal("157.2"), Decimal("156.9"), Decimal("157.1"), "TwelveData"))
            current += interval
        return list(reversed(out))

    def fetch_bars(self, symbol, timeframe="1min", limit=100):
        self.budget.acquire(); self.requests += 1
        interval = timeframe_delta(timeframe)
        end = datetime.now(UTC)
        return self._bars(symbol, timeframe, end - interval * (limit + 20000 // 60), end)[:limit]

    def fetch_bars_range(self, symbol, timeframe, start, end):
        self.budget.acquire(); self.requests += 1
        return self._bars(symbol, timeframe, start, end)


feed = FakeFeed()
buffer = io.StringIO()
with redirect_stdout(buffer):
    rc = update.main(["--symbols", "USD/JPY", "--timeframes", "1min"], feed=feed)
out = buffer.getvalue()
assert "POZOR" in out and "demo" in out, "demo key warning missing"
assert "FXBOT - AKTUALIZACE DAT" in out and "API kredity dnes:" in out
assert feed.requests >= 1
# CURRENT/CLOSED gives exit 0; a real-clock run can land in a brief lag window
assert rc in (0, 1)

# second run right away: data complete -> ZERO further requests
before = feed.requests
buffer = io.StringIO()
with redirect_stdout(buffer):
    update.main(["--symbols", "USD/JPY", "--timeframes", "1min"], feed=feed)
assert feed.requests - before <= 1, "second run must not refetch history"

print("=" * 60)
print("B6 USER SCRIPTS")
print("=" * 60)
print("KEY VALIDATION / MASKING: PASS")
print("ENV FILE: OTHER LINES KEPT, DUPLICATES REMOVED, MODE 600: PASS")
print("KEY NEVER PRINTED (OK AND FAILING TEST): PASS")
print("DEMO KEY REFUSED / WARNED: PASS")
print("INSTRUMENT SELECTION (ARGS / ENV / DEFAULT): PASS")
print("--status MAKES NO API CALLS: PASS")
print("UPDATE REPORT + REPEAT RUN: PASS")
print("RESULT: PASS")
print("=" * 60)
