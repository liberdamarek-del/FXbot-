"""Technical multi-timeframe view TECH-0.2 (modules 42, 43, 45, 46, 48, 49).

Direction and entry are separate (module 45):
- DIRECTION comes from the daily and 4-hour structure (trend of EMA20/50,
  slope, and 20-day volatility-adjusted momentum),
- ENTRY LOCATION comes from the 1-hour structure (levels from confirmed
  swing pivots, EMA20 zone) and is evaluated in src/engine/decision.py.

Level lifetime (module 43): every level is FRESH (one touch), ACTIVE
(two or more touches), WEAKENED (tested four or more times, or broken and
reclaimed), BROKEN (closed through by more than half an ATR since), RESET
(inside the range of a later shock bar - event memory reset, module 48)
or EXPIRED (older than the lookback). Only FRESH and ACTIVE levels are used
for entries.

Everything is computed as of bar index i of each series (closed bars only).
"""

from dataclasses import dataclass, field

from src.engine.params import ModelParams
from src.engine.series import SHOCK_BAR_ATR, PriceSeries


@dataclass
class TechLevel:
    price: float
    touches: int
    first_index: int
    last_index: int
    timeframe: str
    source: str               # "H" (from highs) / "L" (from lows)
    state: str = "FRESH"
    broken_recently: bool = False


@dataclass
class TFView:
    timeframe: str
    index: int
    close: float
    atr: float
    atr_pct: float | None
    rsi: float | None
    ema20: float
    ema50: float
    ema200: float | None
    slope_atr: float
    trend: str                # UP / DOWN / RANGE
    er: float | None          # efficiency ratio (trendiness 0..1)
    structure: str            # HH_HL / LH_LL / MIXED / UNKNOWN
    levels: list = field(default_factory=list)


@dataclass
class TechnicalView:
    symbol: str
    t: int
    price: float
    d1: TFView | None
    h4: TFView | None
    h1: TFView | None
    momentum_z: float | None
    bias: str                 # BUY / SELL / NONE
    strength: int             # number of agreeing technical components (0..3)
    evidence: list = field(default_factory=list)       # (text, direction)
    notes: list = field(default_factory=list)
    shock: bool = False
    complete: bool = True

    def supports(self, timeframes=("1h", "4h")) -> list[TechLevel]:
        out = []

        for view in (self.h1, self.h4):
            if view and view.timeframe in timeframes:
                out += [l for l in view.levels if l.price < self.price]

        return sorted(out, key=lambda l: self.price - l.price)

    def resistances(self, timeframes=("1h", "4h")) -> list[TechLevel]:
        out = []

        for view in (self.h1, self.h4):
            if view and view.timeframe in timeframes:
                out += [l for l in view.levels if l.price > self.price]

        return sorted(out, key=lambda l: l.price - self.price)


def classify_trend(close: float, fast: float, slow: float, slope_atr: float, p: ModelParams) -> str:
    if fast > slow and close > slow and slope_atr >= p.trend_slope_atr:
        return "UP"

    if fast < slow and close < slow and slope_atr <= -p.trend_slope_atr:
        return "DOWN"

    return "RANGE"


def market_structure(pivots: list[tuple]) -> str:
    """Last two confirmed swing highs and lows: HH+HL = up structure."""
    highs = [p[2] for p in pivots if p[3] == "H"][-2:]
    lows = [p[2] for p in pivots if p[3] == "L"][-2:]

    if len(highs) < 2 or len(lows) < 2:
        return "UNKNOWN"

    if highs[1] > highs[0] and lows[1] > lows[0]:
        return "HH_HL"

    if highs[1] < highs[0] and lows[1] < lows[0]:
        return "LH_LL"

    return "MIXED"


def build_levels(series: PriceSeries, i: int, lookback: int, p: ModelParams) -> list[TechLevel]:
    """Cluster confirmed pivots into levels and assign lifetime states."""
    a = series.atr14[i]

    if a is None or a <= 0:
        return []

    pivots = series.pivots_known_at(i, lookback)
    tolerance = p.level_tolerance_atr * a
    ordered = sorted(pivots, key=lambda x: x[2])
    groups: list[list[tuple]] = []

    for pivot in ordered:
        if groups and pivot[2] - groups[-1][0][2] <= tolerance:
            groups[-1].append(pivot)
        else:
            groups.append([pivot])

    # shock bars after which older nearby levels are reset (module 43/48)
    shocks = [j for j in range(max(1, i - lookback), i + 1) if series.shock[j]]
    reach = p.max_level_distance_atr * a * 1.5
    close_now = series.close[i]
    levels = []

    for group in groups:
        price = sum(g[2] for g in group) / len(group)

        if abs(price - close_now) > reach:
            continue          # far away: irrelevant for entries, not evaluated

        first = min(g[0] for g in group)
        last = max(g[0] for g in group)
        level = TechLevel(price, len(group), first, last, series.timeframe,
                          "H" if sum(1 for g in group if g[3] == "H") >= len(group) / 2 else "L")

        # crossings of the level by closes after its last pivot
        crossings = 0
        side = series.close[last] > price

        for j in range(last + 1, i + 1):
            now_side = series.close[j] > price

            if now_side != side and abs(series.close[j] - price) > 0.5 * a:
                crossings += 1
                side = now_side

                if j >= i - 30:
                    level.broken_recently = True

        if any(s > last and series.low[s] <= price <= series.high[s] for s in shocks):
            level.state = "RESET"
        elif crossings >= 2 or level.touches >= 4:
            level.state = "WEAKENED"
        elif crossings == 1:
            # broken once: a broken resistance can serve as support (retest)
            level.state = "BROKEN"
        elif level.touches >= 2:
            level.state = "ACTIVE"
        else:
            level.state = "FRESH"

        levels.append(level)

    return levels


def timeframe_view(series: PriceSeries, i: int, lookback: int, p: ModelParams) -> TFView | None:
    if i < 60 or series.atr14[i] is None or series.ema50[i] is None or series.ema20[i - p.slope_bars] is None:
        return None

    a = series.atr14[i]
    slope = (series.ema20[i] - series.ema20[i - p.slope_bars]) / a
    pivots = series.pivots_known_at(i, lookback)

    return TFView(
        timeframe=series.timeframe,
        index=i,
        close=series.close[i],
        atr=a,
        atr_pct=series.atr_pct[i],
        rsi=series.rsi14[i],
        ema20=series.ema20[i],
        ema50=series.ema50[i],
        ema200=series.ema200[i],
        slope_atr=slope,
        trend=classify_trend(series.close[i], series.ema20[i], series.ema50[i], slope, p),
        er=series.er20[i],
        structure=market_structure(pivots),
        levels=build_levels(series, i, lookback, p) if series.timeframe in ("1h", "4h") else [],
    )


def momentum_z(d1: PriceSeries, i: int, days: int) -> float | None:
    """20-day return divided by the 20-day volatility of daily returns."""
    if i < days + 1:
        return None

    returns = [d1.close[j] / d1.close[j - 1] - 1.0 for j in range(i - days + 1, i + 1)]
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / max(1, len(returns) - 1)

    if variance <= 0:
        return None

    total = d1.close[i] / d1.close[i - days] - 1.0
    return total / (variance ** 0.5 * days ** 0.5)


def analyze(
    symbol: str,
    t: int,
    d1: PriceSeries,
    h4: PriceSeries,
    h1: PriceSeries,
    p: ModelParams,
    price: float | None = None,
) -> TechnicalView:
    """Technical view as of time t (only bars closed at t)."""
    i1, i4, id_ = h1.index_at(t), h4.index_at(t), d1.index_at(t)
    v1 = timeframe_view(h1, i1, p.level_lookback_h1, p) if i1 >= 0 else None
    v4 = timeframe_view(h4, i4, p.level_lookback_h4, p) if i4 >= 0 else None
    vd = timeframe_view(d1, id_, 250, p) if id_ >= 0 else None

    if price is None:
        price = h1.close[i1] if i1 >= 0 else None

    view = TechnicalView(symbol, t, price, vd, v4, v1, None, "NONE", 0)

    if price is None or v1 is None or v4 is None or vd is None:
        view.complete = False
        view.notes.append("nedostatek historie pro D1/H4/H1")
        return view

    view.momentum_z = momentum_z(d1, id_, p.momentum_days)
    view.shock = h1.shock[i1]

    votes = {"BUY": 0, "SELL": 0}

    for label, trend in (("D1", vd.trend), ("H4", v4.trend)):
        if trend == "UP":
            votes["BUY"] += 1
            view.evidence.append((f"{label} trend nahoru (EMA20>EMA50, sklon {getattr(vd if label == 'D1' else v4, 'slope_atr'):+.2f} ATR)", "BUY"))
        elif trend == "DOWN":
            votes["SELL"] += 1
            view.evidence.append((f"{label} trend dolu (EMA20<EMA50, sklon {getattr(vd if label == 'D1' else v4, 'slope_atr'):+.2f} ATR)", "SELL"))
        else:
            view.evidence.append((f"{label} bez trendu", "NONE"))

    if view.momentum_z is not None and abs(view.momentum_z) >= 1.0:
        direction = "BUY" if view.momentum_z > 0 else "SELL"
        votes[direction] += 1
        view.evidence.append((f"momentum {p.momentum_days} dni {view.momentum_z:+.1f} sigma", direction))

    # Direction needs the 4h trend and no opposing daily trend.
    if v4.trend == "UP" and vd.trend != "DOWN" and votes["SELL"] == 0:
        view.bias, view.strength = "BUY", votes["BUY"]
    elif v4.trend == "DOWN" and vd.trend != "UP" and votes["BUY"] == 0:
        view.bias, view.strength = "SELL", votes["SELL"]
    else:
        view.bias, view.strength = "NONE", 0

        if votes["BUY"] and votes["SELL"]:
            view.notes.append("D1/H4/momentum si odporuji - smer neurcen")
        elif v4.trend == "RANGE":
            view.notes.append("H4 bez trendu - smer neurcen")

    if view.shock:
        view.notes.append("posledni H1 svicka je sok (>= 2.5 ATR) - urovne v jejim rozsahu resetovany")

    return view


def recent_move_atr(h1: PriceSeries, i: int, price: float, bars: int, direction: str) -> float:
    """Move of the last `bars` H1 bars in the given direction, in ATR(H1)."""
    if i - bars < 0 or not h1.atr14[i]:
        return 0.0

    sign = 1.0 if direction == "BUY" else -1.0
    return sign * (price - h1.close[i - bars]) / h1.atr14[i]
