"""Path coverage certificate and between-run delta (modules 88, 92, 106,
123, 137).

The between-run path is reconstructed from the finest verified layers:
canonical 1-minute days (bid/ask) -> provisional hour ticks (bid/ask) ->
Twelve Data 1-minute (mid). Missing minutes are never filled.

Coverage states (module 123):
    COMPLETE    every in-session minute present
    PARTIAL     >= 95 % present and no gap longer than 30 minutes
    UNRESOLVED  more missing
    BLOCKED     nothing at all

Gap severity (module 88): CRITICAL when the gap overlaps a critical window
(an open prediction's life, or the last hour before T0), MATERIAL when
longer than 30 minutes, otherwise INFO.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from src.engine.data import twelve_data_minutes
from src.path_archive import Bar, day_minutes_with_source, is_session_minute

UTC = timezone.utc


def path_minutes(symbol: str, start_ts: int, end_ts: int) -> tuple[list[Bar], dict[int, str]]:
    """Minutes in [start_ts, end_ts) from the best layer each; source per minute."""
    minutes: dict[int, Bar] = {}
    source: dict[int, str] = {}
    day = datetime.fromtimestamp(start_ts, tz=UTC).date()
    last_day = datetime.fromtimestamp(max(start_ts, end_ts - 1), tz=UTC).date()

    while day <= last_day:
        # Dukascopy day, else the FXCM week file, else provisional Dukascopy ticks
        canonical, layer = day_minutes_with_source(symbol, day, allow_provisional=True, second_source=True)

        for bar in canonical:
            if start_ts <= bar.ts < end_ts:
                minutes[bar.ts] = bar
                source[bar.ts] = layer

        day += timedelta(days=1)

    for bar in twelve_data_minutes(symbol, start_ts, end_ts):
        if bar.ts not in minutes:
            minutes[bar.ts] = bar
            source[bar.ts] = "TWELVE_DATA"

    ordered = [minutes[k] for k in sorted(minutes)]
    return ordered, source


@dataclass
class Gap:
    start: int
    end: int
    minutes: int
    severity: str

    def to_dict(self) -> dict:
        return {"start": datetime.fromtimestamp(self.start, tz=UTC).isoformat(),
                "end": datetime.fromtimestamp(self.end, tz=UTC).isoformat(),
                "minutes": self.minutes, "severity": self.severity}


@dataclass
class Coverage:
    symbol: str
    start: int
    end: int
    expected: int
    observed: int
    state: str
    max_gap_minutes: int
    gaps: list = field(default_factory=list)
    layers: dict = field(default_factory=dict)

    @property
    def ratio(self) -> float:
        return self.observed / self.expected if self.expected else 1.0

    def to_dict(self) -> dict:
        return {"symbol": self.symbol, "start": datetime.fromtimestamp(self.start, tz=UTC).isoformat(),
                "end": datetime.fromtimestamp(self.end, tz=UTC).isoformat(), "expected": self.expected,
                "observed": self.observed, "ratio": round(self.ratio, 4), "state": self.state,
                "max_gap_minutes": self.max_gap_minutes, "layers": self.layers,
                "gaps": [g.to_dict() for g in self.gaps[:20]], "gap_count": len(self.gaps)}


def coverage(symbol: str, start_ts: int, end_ts: int, critical_windows: list[tuple[int, int]] | None = None,
             bars: list[Bar] | None = None, sources: dict | None = None) -> Coverage:
    if bars is None:
        bars, sources = path_minutes(symbol, start_ts, end_ts)

    present = {b.ts for b in bars}
    first = start_ts - start_ts % 60 + (60 if start_ts % 60 else 0)
    expected = observed = 0
    gaps: list[Gap] = []
    gap_start = None

    for ts in range(first, end_ts - 60 + 1, 60):
        if not is_session_minute(ts):
            continue

        expected += 1

        if ts in present:
            observed += 1

            if gap_start is not None:
                gaps.append(Gap(gap_start, ts, (ts - gap_start) // 60, "INFO"))
                gap_start = None
        elif gap_start is None:
            gap_start = ts

    if gap_start is not None:
        gaps.append(Gap(gap_start, end_ts, (end_ts - gap_start) // 60, "INFO"))

    windows = list(critical_windows or []) + [(end_ts - 3600, end_ts)]

    for gap in gaps:
        if any(gap.start < w_end and gap.end > w_start for w_start, w_end in windows):
            gap.severity = "CRITICAL"
        elif gap.minutes > 30:
            gap.severity = "MATERIAL"

    max_gap = max((g.minutes for g in gaps), default=0)

    if expected == 0:
        state = "COMPLETE"          # closed market: nothing expected
    elif observed == 0:
        state = "BLOCKED"
    elif observed == expected:
        state = "COMPLETE"
    elif observed / expected >= 0.95 and max_gap <= 30:
        state = "PARTIAL"
    else:
        state = "UNRESOLVED"

    layers: dict[str, int] = {}

    for ts in present:
        layer = (sources or {}).get(ts, "?")
        layers[layer] = layers.get(layer, 0) + 1

    return Coverage(symbol, start_ts, end_ts, expected, observed, state, max_gap, gaps, layers)


def between_run_delta(
    symbol: str,
    start_ts: int,
    end_ts: int,
    pip: float,
    atr_h1: float | None,
    locked: list[dict] | None = None,
    events: list | None = None,
    bars: list[Bar] | None = None,
) -> dict:
    """What happened between the previous official T0 and the new T0
    (module 92/106) - an input of the current analysis."""
    if bars is None:
        bars, _ = path_minutes(symbol, start_ts, end_ts)

    out = {"symbol": symbol, "from": datetime.fromtimestamp(start_ts, tz=UTC).isoformat(),
           "to": datetime.fromtimestamp(end_ts, tz=UTC).isoformat(), "minutes": len(bars)}

    if not bars:
        out["state"] = "NO_PATH"
        return out

    first, last = bars[0], bars[-1]
    high = max(bars, key=lambda b: b.mh)
    low = min(bars, key=lambda b: b.ml)
    change = last.mc - first.mo
    out.update({
        "start": first.mo, "end": last.mc, "high": high.mh, "low": low.ml,
        "high_time": high.time.isoformat(), "low_time": low.time.isoformat(),
        "change_pips": round(change / pip, 1),
        "range_pips": round((high.mh - low.ml) / pip, 1),
        "change_atr_h1": round(change / atr_h1, 2) if atr_h1 else None,
    })

    # session transitions: gaps between consecutive stored minutes that
    # contain closed-market time (weekend)
    transitions = 0

    for a, b in zip(bars, bars[1:]):
        if b.ts - a.ts > 60 and not all(is_session_minute(t) for t in range(a.ts + 60, b.ts, 3600)):
            transitions += 1

    out["session_transitions"] = transitions

    crossings = []

    for prediction in locked or []:
        levels = [("entry", prediction.get("entry")), ("SL", prediction.get("stop_loss")), ("TP1", prediction.get("tp1"))]

        for name, level in levels:
            if level is None:
                continue

            level = float(level)
            hit = next((b for b in bars if b.ml <= level <= b.mh), None)

            if hit is not None:
                crossings.append({"prediction_id": prediction["prediction_id"], "level": name, "price": level,
                                  "first_cross": hit.time.isoformat()})

    out["locked_level_crossings"] = crossings
    out["events"] = [{"currency": e.currency, "title": e.title, "time": e.time.isoformat(), "impact": e.impact}
                     for e in (events or [])]
    return out
