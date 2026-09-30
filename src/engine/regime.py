"""Regime and change-point diagnosis (modules 40, 41, 73).

Per pair as of time t:
    volatility   LOW / NORMAL / HIGH / EXTREME  (percentile of daily ATR
                 over the last 250 days)
    structure    TREND / RANGE / MIXED          (20-day efficiency ratio)
    risk         RISK_ON / RISK_OFF / NEUTRAL / UNKNOWN (fundamental view)
    event        EVENT (high-impact event within 24 h) / NONE / UNKNOWN
    transition   True when several independent layers change together
                 (volatility expansion AND a daily trend flip, or a shock
                 bar) - one bad trade or one week is never a change-point.

The label is used for regime-specific performance statistics (module 73)
and for the proof burden of setups (module 40).
"""

from dataclasses import dataclass, field

from src.engine.series import PriceSeries


@dataclass
class RegimeView:
    volatility: str
    structure: str
    risk: str
    event: str
    transition: bool
    notes: list = field(default_factory=list)

    @property
    def label(self) -> str:
        return f"{self.structure}/{self.volatility}/{self.risk}" + ("/TRANSITION" if self.transition else "")


def diagnose(d1: PriceSeries, h1: PriceSeries, t: int, risk: str, events_24h: int | None) -> RegimeView:
    i = d1.index_at(t)
    notes = []

    if i < 60 or d1.atr14[i] is None:
        return RegimeView("UNKNOWN", "UNKNOWN", risk, "UNKNOWN", False, ["kratka historie D1"])

    pct = d1.atr_pct[i]

    if pct is None:
        volatility = "UNKNOWN"
    elif pct >= 95:
        volatility = "EXTREME"
    elif pct >= 75:
        volatility = "HIGH"
    elif pct < 25:
        volatility = "LOW"
    else:
        volatility = "NORMAL"

    er = d1.er20[i]

    if er is None:
        structure = "UNKNOWN"
    elif er >= 0.35:
        structure = "TREND"
    elif er <= 0.20:
        structure = "RANGE"
    else:
        structure = "MIXED"

    # change-point: short/long volatility ratio AND a daily EMA cross recently
    ranges5 = [d1.high[j] - d1.low[j] for j in range(i - 4, i + 1)]
    ranges60 = [d1.high[j] - d1.low[j] for j in range(i - 59, i + 1)]
    ratio = (sum(ranges5) / 5) / (sum(ranges60) / 60) if sum(ranges60) > 0 else 1.0
    crossed = any(
        d1.ema20[j] is not None and d1.ema50[j] is not None and d1.ema20[j - 1] is not None
        and d1.ema50[j - 1] is not None
        and (d1.ema20[j] - d1.ema50[j]) * (d1.ema20[j - 1] - d1.ema50[j - 1]) < 0
        for j in range(i - 4, i + 1)
    )
    ih = h1.index_at(t)
    shock = ih >= 0 and any(h1.shock[j] for j in range(max(0, ih - 5), ih + 1))
    transition = (ratio >= 1.8 and crossed) or (shock and ratio >= 1.5)

    if ratio >= 1.5:
        notes.append(f"volatilita 5 dni / 60 dni = {ratio:.1f}x")

    if crossed:
        notes.append("D1 EMA20/50 se v poslednich 5 dnech prekrizily")

    if shock:
        notes.append("sokova H1 svicka v poslednich 6 hodinach")

    if events_24h is None:
        event = "UNKNOWN"
    else:
        event = "EVENT" if events_24h > 0 else "NONE"

    return RegimeView(volatility, structure, risk, event, transition, notes)
