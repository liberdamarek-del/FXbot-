"""Source register with runtime capability states (modules 9, 116, 125, 129).

"The provider says it exists" is not "this environment retrieved it"
(module 125). Every source has a documented capability and a RUNTIME state
that only changes when this installation actually tested it:

    DOC-PASS        documented, not tested here
    RUNTIME-PASS    tested here: HTTP ok, parsed, expected fields, timestamps
    RUNTIME-FAIL    tested here and failed (reason stored)
    ENV-UNVERIFIED  cannot be tested from this runtime
    KEY-REQUIRED    needs credentials the user has not configured
    DEPRECATED      documented as switched off
    DISABLED        deliberately not used (reason stored)

Permitted use follows the observation class (module 132): only API or
broker sources with explicit timestamps can become a canonical NOW quote.
"""

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from src.database import get_connection

UTC = timezone.utc
CAPABILITY_STATES = ("DOC-PASS", "RUNTIME-PASS", "RUNTIME-FAIL", "ENV-UNVERIFIED", "KEY-REQUIRED",
                     "DEPRECATED", "DISABLED")


@dataclass
class SourceEntry:
    source_id: str
    source_class: str        # module 132 observation class
    coverage: str
    timestamp_semantics: str
    access: str
    permitted_use: str
    state: str = "DOC-PASS"
    detail: str = ""
    tested_at: str | None = None


REGISTER = (
    SourceEntry("TWELVE_DATA", "API_SNAPSHOT", "12 active FX pairs, 1min OHLC mid", "bar open UTC (timezone=UTC)",
                "API key (free plan 800 credits/day)", "live head + NOW reference (MODEL-PRICE, no bid/ask)",
                "KEY-REQUIRED"),
    SourceEntry("DUKASCOPY_M1", "HISTORICAL", "FX pairs, 1min BID+ASK per UTC day", "offset from UTC day start",
                "keyless public files", "canonical history, side-correct outcomes"),
    SourceEntry("DUKASCOPY_H1", "HISTORICAL", "FX pairs, 1h BID+ASK per month", "offset from UTC month start",
                "keyless public files", "long history for D1/H4/H1 analysis"),
    SourceEntry("DUKASCOPY_TICK", "DELAYED_REFERENCE", "FX pairs, ticks per finished hour", "ms from UTC hour start",
                "keyless public files", "provisional current-day path, spread reference (never NOW)"),
    SourceEntry("FXCM_M1", "HISTORICAL", "FX pairs, 1min BID+ASK per trading week (~1 week lag)",
                "UTC timestamps in the file", "keyless public CDN files (github.com/fxcm/MarketData)",
                "second path source: outcome checks where Dukascopy has no day; never canonical series",
                detail="RUNTIME-PASS 2026-10-01; some weeks not published (404)"),
    SourceEntry("FRED", "DAILY_OFFICIAL", "US yields, VIX, equities, credit, oil", "observation date",
                "keyless CSV", "fundamental evidence (point-in-time with lag)"),
    SourceEntry("ECB", "DAILY_OFFICIAL", "euro area AAA yield curve", "observation date", "keyless API", "fundamentals"),
    SourceEntry("MOF", "DAILY_OFFICIAL", "JGB yields", "observation date (JST)", "keyless CSV", "fundamentals"),
    SourceEntry("BOE", "DAILY_OFFICIAL", "gilt par yields", "observation date", "keyless CSV", "fundamentals"),
    SourceEntry("BOC", "DAILY_OFFICIAL", "Canada yields", "observation date", "keyless API", "fundamentals"),
    SourceEntry("RBA", "DAILY_OFFICIAL", "Australia yields", "observation date", "keyless CSV", "fundamentals"),
    SourceEntry("BIS", "DAILY_OFFICIAL", "policy rates of 8 central banks", "effective date", "keyless API", "fundamentals"),
    SourceEntry("CFTC", "DAILY_OFFICIAL", "TFF positioning, weekly", "report date (Tuesday)", "keyless API", "fundamentals"),
    SourceEntry("FF_CALENDAR", "WEB_SNAPSHOT", "economic calendar, current week", "scheduled time with UTC offset",
                "keyless JSON", "event risk gate"),
    # documented in the V7.8.0 source register, not usable from this code base
    SourceEntry("OANDA", "API_STREAM", "bid/ask + UTC time + candles", "explicit UTC", "token required",
                "primary candidate once a token is configured (src/broker/)", "KEY-REQUIRED"),
    SourceEntry("SAXO", "API_STREAM", "bid/ask stream + history", "explicit UTC", "credentials required",
                "candidate", "KEY-REQUIRED"),
    SourceEntry("FXCM", "API_STREAM", "aggregated bid/offer + history", "explicit UTC", "entitlement required",
                "candidate", "KEY-REQUIRED"),
    SourceEntry("IG", "API_STREAM", "streaming bid/ask", "explicit UTC", "login/token required", "candidate",
                "KEY-REQUIRED"),
    SourceEntry("LIVE_RATES", "API_STREAM", "bid/ask ms timestamps", "explicit", "key required (keyless test failed)",
                "candidate", "KEY-REQUIRED", "V7.7.1 appendix G: keyless request returned Invalid Authentication"),
    SourceEntry("ALPHA_VANTAGE", "API_HISTORY", "FX intraday", "explicit", "premium function", "optional",
                "KEY-REQUIRED"),
    SourceEntry("INVESTING_STREAMING", "WEB_TICKER_TIME_ONLY", "bid/ask + time per row", "time only, zone implicit",
                "web page", "context only", "DISABLED", "no web scraping (module 130 not implemented)"),
    SourceEntry("TRADINGVIEW", "WEB_TICKER", "price/status", "depends on entitlement", "web page", "context only",
                "DISABLED", "no web scraping"),
    SourceEntry("GOOGLE_FINANCE", "WEB_SNAPSHOT", "quote, delay up to 20 min", "page time", "web page", "sanity only",
                "DISABLED", "no web scraping"),
    SourceEntry("YAHOO_FINANCE", "WEB_SNAPSHOT", "quote/history", "page time", "web/API", "cross-check only",
                "RUNTIME-FAIL", "HTTP 429 from this runtime (2026-09-30)"),
    SourceEntry("XTB_XSTATION", "BROKER_TRUTH", "execution prices of the user's broker", "platform", "user account",
                "execution truth only via a broker adapter (src/broker/)", "ENV-UNVERIFIED",
                "legacy xAPI hosts deactivated 2025-03-14; no current public API"),
    SourceEntry("ECB_REFERENCE", "DAILY_OFFICIAL", "euro reference rates", "daily 16:00 CET", "keyless",
                "historical reference only"),
)


def initialize_register() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS source_register (
                source_id TEXT PRIMARY KEY,
                entry TEXT NOT NULL,
                state TEXT NOT NULL,
                detail TEXT,
                tested_at TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS source_capability_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                state TEXT NOT NULL,
                detail TEXT,
                tested_at TEXT NOT NULL,
                run_id TEXT
            )
            """
        )

        for entry in REGISTER:
            connection.execute(
                "INSERT OR IGNORE INTO source_register (source_id, entry, state, detail, tested_at) VALUES (?, ?, ?, ?, ?)",
                (entry.source_id, json.dumps(asdict(entry)), entry.state, entry.detail, entry.tested_at),
            )

        connection.commit()


def record_capability(source_id: str, state: str, detail: str = "", run_id: str | None = None) -> None:
    """Store the result of a real runtime test (module 125)."""
    if state not in CAPABILITY_STATES:
        raise ValueError(f"capability state must be one of {CAPABILITY_STATES}")

    initialize_register()
    tested = datetime.now(UTC).isoformat()

    with get_connection() as connection:
        connection.execute("UPDATE source_register SET state = ?, detail = ?, tested_at = ? WHERE source_id = ?",
                           (state, detail[:300], tested, source_id))
        connection.execute("INSERT INTO source_capability_log (source_id, state, detail, tested_at, run_id) "
                           "VALUES (?, ?, ?, ?, ?)", (source_id, state, detail[:300], tested, run_id))
        connection.commit()


def register_state() -> list[dict]:
    initialize_register()

    with get_connection() as connection:
        return [dict(r) for r in connection.execute(
            "SELECT source_id, state, detail, tested_at FROM source_register ORDER BY source_id")]


def register_version() -> str:
    """Hash of the register content (part of the run manifest, module 99)."""
    import hashlib

    return hashlib.sha256(json.dumps(register_state(), sort_keys=True).encode()).hexdigest()[:16]


def twelve_data_key() -> str | None:
    key = os.getenv("TWELVE_DATA_API_KEY", "").strip()
    return key or None
