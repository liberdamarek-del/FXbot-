"""Building the D1 / H4 / H1 series of a pair from the archive.

Layers, in order of preference for the same bar time:
1. bars aggregated from canonical 1-minute days   (DUKASCOPY_M1, bid/ask)
2. bars aggregated from monthly hourly files      (DUKASCOPY_H1, bid/ask)
3. LIVE HEAD (only for the live run): minutes after the last canonical day
   from provisional hour tick files (bid/ask) and Twelve Data 1-minute
   bars (mid only -> side_correct=False, MODEL-PRICE).

Only complete windows become bars (a still-forming bar never enters the
analysis). The head never overwrites canonical history (module 121: live
data is never used to fabricate history and history is never relabelled
as current).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.engine.params import ModelParams
from src.engine.series import PriceSeries, merge_bars
from src.path_archive import Bar, aggregate, day_minutes, list_days, load_bars

UTC = timezone.utc


@dataclass
class PairSeries:
    symbol: str
    d1: PriceSeries
    h4: PriceSeries
    h1: PriceSeries
    head_minutes: int = 0          # minutes of live head used
    head_model_price: int = 0      # of which without bid/ask (Twelve Data)
    last_canonical_day: str | None = None
    h1_bars: list = None           # the H1 Bars (bid/ask) for outcome resolution


def _canonical(symbol: str, timeframe: str, start_ts: int | None, end_ts: int | None) -> list[Bar]:
    m1 = load_bars(symbol, timeframe, start_ts, end_ts, source_id="DUKASCOPY_M1")
    h1 = load_bars(symbol, timeframe, start_ts, end_ts, source_id="DUKASCOPY_H1") if timeframe in ("1h", "4h", "1d") else []
    return merge_bars(m1, h1)


MIN_CANONICAL_H1 = 1500        # below this the Twelve Data fallback is used for history
FALLBACK_DAYS = 120


def earliest_twelve_data_minute(symbol: str) -> int | None:
    from src.database import get_connection

    try:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT MIN(bar_time) AS first FROM raw_bars WHERE symbol = ? AND timeframe = '1min' "
                "AND source = 'TwelveData'", (symbol,)).fetchone()
    except Exception:
        return None

    return int(datetime.fromisoformat(row["first"]).timestamp()) if row and row["first"] else None


def twelve_data_minutes(symbol: str, start_ts: int, end_ts: int) -> list[Bar]:
    """Twelve Data 1-minute mid bars from the main database as Bars with
    bid = ask = mid (no spread information)."""
    from src.database import get_connection

    start = datetime.fromtimestamp(start_ts, tz=UTC).isoformat()
    end = datetime.fromtimestamp(end_ts, tz=UTC).isoformat()

    try:
        with get_connection() as connection:
            rows = connection.execute(
                "SELECT bar_time, open, high, low, close FROM raw_bars WHERE symbol = ? AND timeframe = '1min' "
                "AND source = 'TwelveData' AND bar_time >= ? AND bar_time < ? ORDER BY bar_time",
                (symbol, start, end),
            ).fetchall()
    except Exception:
        return []

    out = []

    for r in rows:
        ts = int(datetime.fromisoformat(r["bar_time"]).timestamp())
        o, h, l, c = (float(Decimal(r[k])) for k in ("open", "high", "low", "close"))
        out.append(Bar(ts, o, h, l, c, o, h, l, c, 0.0, 1, 1))

    return out


def live_head(symbol: str, after_ts: int, now_ts: int) -> tuple[list[Bar], set[int]]:
    """Minutes after `after_ts`: provisional ticks first, Twelve Data where
    no tick minute exists. Returns (minutes, set of model-price minute ts)."""
    minutes: dict[int, Bar] = {}
    day = datetime.fromtimestamp(after_ts, tz=UTC).date()
    last_day = datetime.fromtimestamp(now_ts, tz=UTC).date()

    while day <= last_day:
        for bar in day_minutes(symbol, day, allow_provisional=True):
            if after_ts <= bar.ts < now_ts:
                minutes[bar.ts] = bar
        day += timedelta(days=1)

    model_price = set()

    for bar in twelve_data_minutes(symbol, after_ts, now_ts):
        if bar.ts not in minutes and bar.ts + 60 <= now_ts:
            minutes[bar.ts] = bar
            model_price.add(bar.ts)

    return [minutes[k] for k in sorted(minutes)], model_price


def load_pair(symbol: str, p: ModelParams, now_ts: int | None = None, live: bool = False,
              start_ts: int | None = None) -> PairSeries:
    """D1/H4/H1 series of a pair. With live=True the head after the last
    canonical day is appended (bars closed before now_ts only)."""
    d1 = _canonical(symbol, "1d", start_ts, now_ts)
    h4 = _canonical(symbol, "4h", start_ts, now_ts)
    h1 = _canonical(symbol, "1h", start_ts, now_ts)
    sc = {"1d": None, "4h": None, "1h": None}
    head_count = head_model = 0
    last_day = None

    if live and now_ts is not None:
        days = [d for d in list_days(symbol, source_id="DUKASCOPY_M1") if d["state"] == "COMPLETE"]
        last_day = days[-1]["day"] if days else None
        last_bar = max((b.ts for b in h1), default=0)
        after = last_bar + 3600 if last_bar else now_ts - 3 * 86400

        if len(h1) < MIN_CANONICAL_H1:
            # little or no canonical BID/ASK history (e.g. Dukascopy throttled):
            # fall back to all stored Twelve Data minutes (mid, MODEL-PRICE) -
            # backfill ladder, module 136
            earliest = earliest_twelve_data_minute(symbol)

            if earliest is not None:
                after = min(after, max(earliest, now_ts - FALLBACK_DAYS * 86400))
        # the NY-aligned daily/4h bar that contains `after` must be rebuilt
        # from minutes as well, so start the head at the beginning of the
        # current daily bar
        from src.path_archive import bucket_start
        head_start = min(after, bucket_start(after, "1d"))
        minutes, model_price = live_head(symbol, head_start, now_ts)
        # canonical minutes of the same window (for bars that straddle)
        canonical_minutes = []
        day = datetime.fromtimestamp(head_start, tz=UTC).date()
        while day <= datetime.fromtimestamp(now_ts, tz=UTC).date():
            canonical_minutes += [b for b in day_minutes(symbol, day, allow_provisional=False) if b.ts >= head_start]
            day += timedelta(days=1)
        merged = {b.ts: b for b in minutes}
        merged.update({b.ts: b for b in canonical_minutes})
        window = [merged[k] for k in sorted(merged)]
        head_count = sum(1 for b in window if b.ts >= after)
        head_model = sum(1 for b in window if b.ts in model_price)

        for timeframe, target in (("1h", h1), ("4h", h4), ("1d", d1)):
            built = [b for b in aggregate(window, timeframe) if b.ts + _seconds(timeframe) <= now_ts]
            existing = {b.ts for b in target}
            extra = [b for b in built if b.ts not in existing]
            target.extend(extra)
            target.sort(key=lambda b: b.ts)
            flags = {b.ts: not any(m in model_price for m in range(b.ts, b.ts + _seconds(timeframe), 60)) for b in extra}
            sc[timeframe] = [flags.get(b.ts, True) for b in target]

    return PairSeries(
        symbol,
        PriceSeries.from_bars(symbol, "1d", d1, sc["1d"], p.pivot_k_d1, p.pivot_prominence_atr),
        PriceSeries.from_bars(symbol, "4h", h4, sc["4h"], p.pivot_k_h4, p.pivot_prominence_atr),
        PriceSeries.from_bars(symbol, "1h", h1, sc["1h"], p.pivot_k_h1, p.pivot_prominence_atr),
        head_count,
        head_model,
        last_day,
        h1,
    )


def _seconds(timeframe: str) -> int:
    return {"1h": 3600, "4h": 14400, "1d": 86400}[timeframe]


def minute_loader(symbol: str):
    """Callback for src/engine/resolution: archived 1-minute bars of a window."""
    def load(start_ts: int, end_ts: int) -> list[Bar]:
        out = []
        day = datetime.fromtimestamp(start_ts, tz=UTC).date()
        last = datetime.fromtimestamp(end_ts - 1, tz=UTC).date()

        while day <= last:
            out += [b for b in day_minutes(symbol, day, allow_provisional=False) if start_ts <= b.ts < end_ts]
            day += timedelta(days=1)

        return out

    return load
