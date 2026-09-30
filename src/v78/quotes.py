"""Live quote contract, atomic T0 snapshot, freshness, conflicts
(modules 10-13, 110, 111, 117-120, 132-135, 143).

A quote observation is valid only with: instrument, source, source
timestamp in UTC, retrieval timestamp, computed age, market state, feed
type and observation class (module 117). Bid/ask are optional: without
them the value is MODEL-PRICE and can never silently become an execution
quote.

Freshness (module 119) is the measured age, never a score:
    LIVE 0-60 s, FRESH 61-300 s, CONDITIONAL 301-900 s, REJECTED > 900 s.
Exact NOW needs LIVE/FRESH. A historical bar is never relabelled as
current; when the market is closed the newest value is shown as
LAST VALID SESSION SNAPSHOT (module 134).

Canonical choice per pair (failover, module 111, 120): broker quote
(bid/ask) -> Twelve Data newest 1-minute close -> nothing (DATA-BLOCKED).
Dukascopy hour ticks are a DELAYED_REFERENCE: spread and cross-check,
never NOW. Conflicting sources are never averaged (module 13, 133).
"""

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from src.instruments import get_instrument
from src.market_session import is_fx_market_open

UTC = timezone.utc

OBSERVATION_CLASSES = (
    "API_STREAM", "API_SNAPSHOT", "WEB_TICKER_EXPLICIT_TIME", "WEB_TICKER_TIME_ONLY", "RENDERED_SNAPSHOT",
    "BROKER_PAGE", "BROKER_TRUTH", "DELAYED_REFERENCE", "DAILY_OFFICIAL", "HISTORICAL",
)
NOW_ELIGIBLE_CLASSES = ("API_STREAM", "API_SNAPSHOT", "BROKER_TRUTH", "BROKER_PAGE")


def freshness(age_seconds: float | None) -> str:
    if age_seconds is None:
        return "REJECTED"
    if age_seconds <= 60:
        return "LIVE"
    if age_seconds <= 300:
        return "FRESH"
    if age_seconds <= 900:
        return "CONDITIONAL"
    return "REJECTED"


def market_state(now: datetime) -> str:
    """OPEN / CLOSED / PRE-OPEN / HOLIDAY (module 134). Holidays: only
    25 Dec and 1 Jan are flagged (thin or closed at most brokers)."""
    utc = now.astimezone(UTC)

    if (utc.month, utc.day) in ((12, 25), (1, 1)):
        return "HOLIDAY"

    if is_fx_market_open(utc):
        return "OPEN"

    if is_fx_market_open(utc + timedelta(minutes=60)):
        return "PRE-OPEN"

    return "CLOSED"


@dataclass
class QuoteObservation:
    symbol: str
    source_id: str
    source_class: str
    mid: float
    source_ts: float | None           # epoch seconds UTC of the quote (bar close for bars)
    retrieval_ts: float
    bid: float | None = None
    ask: float | None = None
    feed_type: str = "MID_BAR_CLOSE"
    note: str = ""
    rejected: str | None = None

    def age(self, now_ts: float) -> float | None:
        return None if self.source_ts is None else max(0.0, now_ts - self.source_ts)

    @property
    def has_bid_ask(self) -> bool:
        return self.bid is not None and self.ask is not None

    def to_dict(self, now_ts: float) -> dict:
        return {
            "symbol": self.symbol, "source": self.source_id, "class": self.source_class,
            "bid": self.bid, "ask": self.ask, "mid": self.mid,
            "source_time": _iso(self.source_ts), "retrieval_time": _iso(self.retrieval_ts),
            "age_s": self.age(now_ts), "freshness": freshness(self.age(now_ts)),
            "feed": self.feed_type, "note": self.note, "rejected": self.rejected,
        }


def _iso(ts: float | None) -> str | None:
    return None if ts is None else datetime.fromtimestamp(ts, tz=UTC).isoformat()


def validate(observation: QuoteObservation) -> str | None:
    """Contract check (module 117). Returns the rejection reason or None."""
    instrument = get_instrument(observation.symbol)

    if observation.source_ts is None:
        return "chybi casova znacka zdroje"

    if observation.source_ts > observation.retrieval_ts + 5:
        return "casova znacka v budoucnosti (TIMEZONE-UNRESOLVED)"

    if not (instrument.min_price <= observation.mid <= instrument.max_price):
        return "cena mimo rozsah instrumentu (identita nepotvrzena)"

    if observation.has_bid_ask and observation.bid > observation.ask:
        return "bid > ask"

    if observation.source_class not in OBSERVATION_CLASSES:
        return f"neznama trida pozorovani {observation.source_class}"

    return None


@dataclass
class PairQuote:
    symbol: str
    market: str
    canonical: QuoteObservation | None
    freshness: str
    data_state: str            # LIVE / FRESH / CONDITIONAL / REJECTED / LAST_VALID_SESSION / DATA-BLOCKED / DATA-CONFLICT
    execution: str             # EXECUTABLE / MODEL-PRICE / BROKER-BLOCKED / DATA-BLOCKED
    observations: list = field(default_factory=list)
    spread_reference: float | None = None
    spread_source: str | None = None
    notes: list = field(default_factory=list)

    @property
    def now_eligible(self) -> bool:
        return (self.market == "OPEN" and self.canonical is not None
                and self.data_state in ("LIVE", "FRESH"))


def conflict_check(observations: list[QuoteObservation], pip: float, window_s: float = 120.0,
                   threshold_pips: float = 5.0, volatility_pips: float = 0.0) -> tuple[list[QuoteObservation], str | None]:
    """Outlier / conflict gate (module 133). Compares only contemporaneous
    observations (source times within window_s). >= 3 observations: one
    that is far from the median of the others - more than the threshold
    AND more than 3x the dispersion of the others - is rejected. Exactly 2
    that disagree -> CONFLICT. The threshold grows with volatility
    (3x the recent 1-minute range when given). Never averages."""
    threshold_pips = max(threshold_pips, 3.0 * volatility_pips)
    timed = [o for o in observations if o.source_ts is not None and o.rejected is None]

    if len(timed) < 2:
        return observations, None

    newest = max(o.source_ts for o in timed)
    contemporaneous = [o for o in timed if newest - o.source_ts <= window_s]

    if len(contemporaneous) < 2:
        return observations, None

    if len(contemporaneous) >= 3:
        for o in contemporaneous:
            others = [x.mid for x in contemporaneous if x is not o]
            centre = statistics.median(others)
            spread_others = max(others) - min(others)

            deviation = abs(o.mid - centre) / pip

            if deviation > threshold_pips and deviation > 3.0 * max(spread_others / pip, 1.0):
                o.rejected = f"outlier: {deviation:.1f} pip od shluku ostatnich zdroju"

        return observations, None

    a, b = contemporaneous
    difference = abs(a.mid - b.mid) / pip

    if difference > threshold_pips:
        return observations, (f"DATA-CONFLICT: {a.source_id} vs {b.source_id} rozdil {difference:.1f} pip "
                              f"(casovy odstup {abs(a.source_ts - b.source_ts):.0f} s)")

    return observations, None


def build_pair_quote(symbol: str, observations: list[QuoteObservation], now: datetime,
                     spread_reference: tuple[float, str] | None = None) -> PairQuote:
    instrument = get_instrument(symbol)
    now_ts = now.timestamp()
    market = market_state(now)

    for observation in observations:
        observation.rejected = observation.rejected or validate(observation)

    observations, conflict = conflict_check(observations, instrument.pip)
    usable = [o for o in observations if o.rejected is None]
    broker = [o for o in usable if o.source_class in ("BROKER_TRUTH", "BROKER_PAGE") and o.has_bid_ask]
    api = [o for o in usable if o.source_class in ("API_STREAM", "API_SNAPSHOT")]
    reference = [o for o in usable if o.source_class == "DELAYED_REFERENCE"]
    notes = []

    canonical = None

    for group in (broker, api):
        fresh = sorted(group, key=lambda o: o.age(now_ts))

        if fresh:
            canonical = fresh[0]
            break

    if canonical is None and reference:
        # only a delayed reference: shown, never NOW (module 111: never relabel)
        canonical = sorted(reference, key=lambda o: o.age(now_ts))[0]
        notes.append("jen zpozdena reference (Dukascopy ticky) - LIVE CENA NEOVERENA")

    if canonical is None:
        return PairQuote(symbol, market, None, "REJECTED", "DATA-BLOCKED", "DATA-BLOCKED", observations,
                         notes=["zadny platny zdroj kotace"])

    age = canonical.age(now_ts)
    fresh_state = freshness(age)

    if conflict:
        data_state = "DATA-CONFLICT"
        notes.append(conflict)
    elif market != "OPEN":
        data_state = "LAST_VALID_SESSION"
        notes.append(f"trh {market}: posledni platna kotace relace, ne aktualni cena")
    elif canonical.source_class not in NOW_ELIGIBLE_CLASSES:
        data_state = "REJECTED" if fresh_state == "REJECTED" else "CONDITIONAL"
    else:
        data_state = fresh_state

    if canonical.source_class in ("BROKER_TRUTH", "BROKER_PAGE") and canonical.has_bid_ask:
        execution = "EXECUTABLE" if data_state in ("LIVE", "FRESH") else "BROKER-BLOCKED"
    elif data_state in ("LIVE", "FRESH"):
        execution = "MODEL-PRICE"
        notes.append("bez bid/ask ze ziveho zdroje: vstup over u brokera (MODEL-PRICE)")
    else:
        execution = "DATA-BLOCKED"

    quote = PairQuote(symbol, market, canonical, fresh_state, data_state, execution, observations, notes=notes)

    if canonical.has_bid_ask:
        quote.spread_reference, quote.spread_source = canonical.ask - canonical.bid, canonical.source_id
    elif spread_reference:
        quote.spread_reference, quote.spread_source = spread_reference

    return quote


@dataclass
class Snapshot:
    t0: datetime
    start: datetime
    end: datetime
    pairs: dict
    max_skew_s: float | None
    skew_state: str
    market: str
    consistency: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        now_ts = self.t0.timestamp()
        return {
            "t0": self.t0.isoformat(), "snapshot_start": self.start.isoformat(), "snapshot_end": self.end.isoformat(),
            "max_cross_pair_skew_s": self.max_skew_s, "skew_state": self.skew_state, "market": self.market,
            "consistency": self.consistency,
            "pairs": {
                s: {
                    "data_state": q.data_state, "freshness": q.freshness, "execution": q.execution,
                    "canonical": q.canonical.to_dict(now_ts) if q.canonical else None,
                    "observations": [o.to_dict(now_ts) for o in q.observations],
                    "spread_reference": q.spread_reference, "spread_source": q.spread_source,
                    "notes": q.notes,
                }
                for s, q in self.pairs.items()
            },
        }


def skew_state(pairs: dict) -> tuple[float | None, str]:
    """Cross-pair skew of the canonical source times (module 118)."""
    times = [q.canonical.source_ts for q in pairs.values()
             if q.canonical is not None and q.canonical.source_ts is not None
             and q.canonical.source_class in NOW_ELIGIBLE_CLASSES]

    if len(times) < 2:
        return None, "N/A"

    skew = max(times) - min(times)

    if skew <= 10:
        return skew, "SYNCHRONIZED"
    if skew <= 60:
        return skew, "CONDITIONAL"
    return skew, "NOT_SYNCHRONIZED"


def source_consistency(a_bars, b_bars, pip: float) -> dict | None:
    """Compare two sources on the same minutes (module 13, 143): median and
    95th percentile of |close difference| in pips. Never averaged into a
    price - only measured."""
    b_by_ts = {bar.ts: bar for bar in b_bars}
    diffs = sorted(abs(bar.mc - b_by_ts[bar.ts].mc) / pip for bar in a_bars if bar.ts in b_by_ts)

    if len(diffs) < 10:
        return None

    p95 = diffs[min(len(diffs) - 1, int(0.95 * len(diffs)))]
    median = diffs[len(diffs) // 2]
    # thresholds from the first real comparison (2026-09-30): Twelve Data vs
    # Dukascopy mid differ by ~1 pip median, ~5 pip p95 on USD/JPY - normal
    # feed differences; the V7.8.0 failure case was > 100 pips
    state = "CONSISTENT" if median <= 2.0 and p95 <= 8.0 else "SOURCE_DRIFT"
    return {"minutes": len(diffs), "median_pips": round(median, 2), "p95_pips": round(p95, 2), "state": state}
