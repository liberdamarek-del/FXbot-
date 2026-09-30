"""Technical analysis v1 (TECH-0.1): structure + volatility, NO macro layer.

Reads the derived 15min / 1h / 4h bars (built from in-session 1-minute bars),
classifies the trend, measures volatility, finds support / resistance from
confirmed swing points and builds ONE explainable setup per pair.

Follows the model specification where it is already implementable:
- data gate (modules 10, 16, 119): a proposal is only made when the 1-minute
  data are CURRENT, otherwise the decision is NO TRADE with the reason,
- R:R gate (module 55): at least 1:1.5 against the primary target TP1,
- SL from structure and ATR noise (module 53), TP from structure / ATR
  (module 54), TP3 is never used to make the R:R look better,
- no-chase (module 48): after a move of about 1 ATR or more in the bias
  direction no NOW is issued, only WAIT,
- decisions use the specified vocabulary (BUY NOW, SELL NOW, WAIT FOR BUY,
  WAIT FOR SELL, NO TRADE).

All numeric thresholds below are PROVISIONAL (NEOVERENO): they have not been
validated on out-of-sample data. This is a TECHNICAL proposal only - it is not
an investment recommendation and it knows nothing about macro events.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from src.data_state import DataState, get_status
from src.database import get_connection
from src.indicators import Level, atr, cluster_levels, ema, rsi, swing_points
from src.resample import DERIVED_SOURCE

MODEL_VERSION = "TECH-0.1"

TIMEFRAMES = ("4h", "1h", "15min")
# bars loaded per timeframe / minimum needed for a meaningful analysis
LOAD = {"4h": 150, "1h": 400, "15min": 500}
MINIMUM = {"4h": 60, "1h": 80, "15min": 80}
PIVOT_K = {"4h": 2, "1h": 3, "15min": 3}

EMA_FAST, EMA_SLOW, ATR_PERIOD, RSI_PERIOD = 20, 50, 14, 14
SLOPE_BARS = 5
TREND_SLOPE_ATR = 0.15          # EMA(20) must move >= 0.15 ATR over 5 bars
LEVEL_TOLERANCE_ATR = 0.25      # pivots within 0.25 ATR form one level
MIN_TOUCHES = 1                 # in a trend the last swing is the level
PROMINENCE_ATR = 0.8            # a pivot must stand out by 0.8 ATR (noise filter)
NEAR_SUPPORT_ATR = 0.6          # "price is at the level" (NOW) if within this
ENTRY_OFFSET_ATR = 0.3          # WAIT entry = level +/- 0.3 ATR
STOP_BUFFER_ATR = 0.5           # SL beyond the level by 0.5 ATR
TARGET_BUFFER_ATR = 0.1         # TP1 just before the opposing level
MAX_TP1_ATR = 3.0               # TP1 never further than 3 ATR from entry
MAX_LEVEL_DISTANCE_ATR = 4.0    # ignore levels further away than that
NO_CHASE_ATR = 1.0              # move of 1 ATR in bias direction = no NOW
MIN_RR = 1.5                    # specification default gate


@dataclass(frozen=True)
class Series:
    times: list
    opens: list
    highs: list
    lows: list
    closes: list


@dataclass
class TimeframeView:
    timeframe: str
    bars: int
    last_bar_open: datetime
    close: float
    atr: float
    atr_percentile: float
    rsi: float
    ema_fast: float
    ema_slow: float
    slope_atr: float
    trend: str                        # UP / DOWN / RANGE
    supports: list = field(default_factory=list)       # nearest first
    resistances: list = field(default_factory=list)    # nearest first
    recent_closes: list = field(default_factory=list)


@dataclass
class Setup:
    decision: str
    reasons: list
    bias: str = "NONE"                # BUY / SELL / NONE
    entry: float | None = None
    zone_low: float | None = None
    zone_high: float | None = None
    stop: float | None = None
    targets: list = field(default_factory=list)
    rr: float | None = None
    atr_unit: float | None = None


@dataclass
class Analysis:
    symbol: str
    now: datetime
    price: float | None
    price_bar_open: datetime | None
    data_state: str
    data_reason: str
    views: dict
    setup: Setup


# ----------------------------------------------------------------------
# loading
# ----------------------------------------------------------------------

def load_series(symbol: str, timeframe: str, limit: int, source: str = DERIVED_SOURCE) -> Series:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT bar_time, open, high, low, close
            FROM raw_bars
            WHERE symbol = ? AND timeframe = ? AND source = ?
            ORDER BY bar_time DESC
            LIMIT ?
            """,
            (symbol, timeframe, source, limit),
        ).fetchall()

    rows.reverse()

    return Series(
        times=[datetime.fromisoformat(r["bar_time"]).astimezone(timezone.utc) for r in rows],
        opens=[float(r["open"]) for r in rows],
        highs=[float(r["high"]) for r in rows],
        lows=[float(r["low"]) for r in rows],
        closes=[float(r["close"]) for r in rows],
    )


def last_price(symbol: str, source: str = "TwelveData") -> tuple[float, datetime] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT bar_time, close FROM raw_bars
            WHERE symbol = ? AND timeframe = '1min' AND source = ?
            ORDER BY bar_time DESC LIMIT 1
            """,
            (symbol, source),
        ).fetchone()

    if row is None:
        return None

    return float(row["close"]), datetime.fromisoformat(row["bar_time"]).astimezone(timezone.utc)


def decimals(symbol: str) -> int:
    return 3 if symbol.upper().endswith("/JPY") else 5


def quantize(symbol: str, value: float) -> Decimal:
    step = Decimal(1).scaleb(-decimals(symbol))
    return Decimal(str(value)).quantize(step, rounding=ROUND_HALF_UP)


# ----------------------------------------------------------------------
# per-timeframe analysis
# ----------------------------------------------------------------------

def classify_trend(close: float, fast: float, slow: float, slope_atr: float) -> str:
    if fast > slow and close > slow and slope_atr >= TREND_SLOPE_ATR:
        return "UP"

    if fast < slow and close < slow and slope_atr <= -TREND_SLOPE_ATR:
        return "DOWN"

    return "RANGE"


def analyze_timeframe(series: Series, timeframe: str) -> TimeframeView | None:
    n = len(series.closes)

    if n < MINIMUM[timeframe]:
        return None

    atrs = atr(series.highs, series.lows, series.closes, ATR_PERIOD)
    fast = ema(series.closes, EMA_FAST)
    slow = ema(series.closes, EMA_SLOW)
    rsis = rsi(series.closes, RSI_PERIOD)

    a = atrs[-1]
    f, s = fast[-1], slow[-1]

    if a is None or a <= 0 or f is None or s is None or fast[-1 - SLOPE_BARS] is None:
        return None

    close = series.closes[-1]
    slope = (f - fast[-1 - SLOPE_BARS]) / a
    history = [x for x in atrs[-200:] if x is not None]
    percentile = 100.0 * sum(1 for x in history if x < a) / len(history)

    highs, lows = swing_points(
        series.highs, series.lows, PIVOT_K[timeframe], PROMINENCE_ATR * a
    )
    tolerance = LEVEL_TOLERANCE_ATR * a
    high_levels = [l for l in cluster_levels(highs, tolerance) if l.touches >= MIN_TOUCHES]
    low_levels = [l for l in cluster_levels(lows, tolerance) if l.touches >= MIN_TOUCHES]
    levels = high_levels + low_levels

    supports = sorted((l for l in levels if l.price < close), key=lambda l: close - l.price)
    resistances = sorted((l for l in levels if l.price > close), key=lambda l: l.price - close)

    return TimeframeView(
        timeframe=timeframe,
        bars=n,
        last_bar_open=series.times[-1],
        close=close,
        atr=a,
        atr_percentile=percentile,
        rsi=rsis[-1] if rsis[-1] is not None else 50.0,
        ema_fast=f,
        ema_slow=s,
        slope_atr=slope,
        trend=classify_trend(close, f, s, slope),
        supports=supports,
        resistances=resistances,
        recent_closes=series.closes[-8:],
    )


# ----------------------------------------------------------------------
# setup
# ----------------------------------------------------------------------

def _no_trade(reason: str, bias: str = "NONE", atr_unit: float | None = None) -> Setup:
    return Setup(decision="NO TRADE", reasons=[reason], bias=bias, atr_unit=atr_unit)


def build_setup(
    price: float | None,
    v4: TimeframeView | None,
    v1: TimeframeView | None,
    v15: TimeframeView | None,
    data_state: str,
) -> Setup:
    if data_state != DataState.CURRENT.value:
        return _no_trade(f"data nejsou CURRENT (stav {data_state}) - navrh nelze vytvorit")

    if price is None or v4 is None or v1 is None or v15 is None:
        return _no_trade("nedostatek historie pro analyzu")

    t4, t1 = v4.trend, v1.trend

    if t4 == "UP" and t1 != "DOWN":
        bias = "BUY"
    elif t4 == "DOWN" and t1 != "UP":
        bias = "SELL"
    elif t4 == "RANGE":
        return _no_trade(f"4h bez trendu (1h {t1}) - cekat na strukturu")
    else:
        return _no_trade(f"1h ({t1}) proti trendu 4h ({t4}) - cekat na obrat")

    a = v1.atr
    sign = 1.0 if bias == "BUY" else -1.0
    reasons = [f"4h {t4}, 1h {t1}, ATR 1h {a:.{decimals_for(price)}f}"]

    # levels from 1h and 4h, nearest first, within reach
    own_side = v1.supports + v4.supports if bias == "BUY" else v1.resistances + v4.resistances
    other_side = v1.resistances + v4.resistances if bias == "BUY" else v1.supports + v4.supports

    own_side = [l for l in own_side if abs(price - l.price) <= MAX_LEVEL_DISTANCE_ATR * a]
    own_side.sort(key=lambda l: abs(price - l.price))

    if not own_side:
        return _no_trade(
            f"zadna {'podpora' if bias == 'BUY' else 'odpor'} v dosahu "
            f"{MAX_LEVEL_DISTANCE_ATR:.0f} ATR",
            bias,
            a,
        )

    level = own_side[0]
    reasons.append(
        f"{'podpora' if bias == 'BUY' else 'odpor'} {level.price:.{decimals_for(price)}f} "
        f"({level.touches}x)"
    )

    distance = sign * (price - level.price)          # >0: price on the trend side of the level
    recent = sign * (price - v15.recent_closes[-5]) / a  # move in bias direction over ~4 bars

    stop = level.price - sign * STOP_BUFFER_ATR * a
    near = 0.0 <= distance <= NEAR_SUPPORT_ATR * a

    if near and recent < NO_CHASE_ATR:
        decision = "BUY NOW" if bias == "BUY" else "SELL NOW"
        entry = price
        zone_a = level.price
        zone_b = price
    else:
        decision = "WAIT FOR BUY" if bias == "BUY" else "WAIT FOR SELL"
        entry = level.price + sign * ENTRY_OFFSET_ATR * a
        zone_a = level.price
        zone_b = level.price + sign * 2 * ENTRY_OFFSET_ATR * a

        if near and recent >= NO_CHASE_ATR:
            reasons.append(
                f"pohyb {recent:.1f} ATR ve smeru - NOW zakazano (no-chase), cekat na pullback"
            )

    if distance < 0:
        return _no_trade(
            f"cena je uz za {'podporou' if bias == 'BUY' else 'odporem'} - struktura porusena",
            bias,
            a,
        )

    risk = sign * (entry - stop)

    if risk <= 0:
        return _no_trade("neplatna vzdalenost SL", bias, a)

    # primary target TP1: just before the nearest opposing level, capped by ATR
    opposing = [l for l in other_side if sign * (l.price - entry) > 0]
    opposing.sort(key=lambda l: sign * (l.price - entry))
    cap = entry + sign * MAX_TP1_ATR * a

    if opposing:
        structural = opposing[0].price - sign * TARGET_BUFFER_ATR * a
        tp1 = min(structural, cap) if bias == "BUY" else max(structural, cap)
        tp1_source = "struktura" if tp1 == structural else "ATR"
    else:
        tp1 = entry + sign * MIN_RR * risk
        tp1_source = "ATR"

    rr = sign * (tp1 - entry) / risk

    if rr < MIN_RR - 1e-9:
        shown = math.floor(rr * 100) / 100
        return _no_trade(
            f"R:R {shown:.2f} pod hranici {MIN_RR} (cil TP1 {tp1_source})",
            bias,
            a,
        )

    # TP2 / TP3: next structure beyond TP1 if it is at least 0.5R further, else R multiples
    targets = [tp1]

    for multiple in (2.5, 3.5):
        previous = targets[-1]
        # R multiple, but always at least 0.5R beyond the previous target
        # (TP1 may have been capped at 3 ATR, which can exceed 2.5R)
        fallback = entry + sign * max(
            multiple * risk, sign * (previous - entry) + 0.5 * risk
        )
        beyond = [
            l.price - sign * TARGET_BUFFER_ATR * a
            for l in opposing[1:]
            if sign * ((l.price - sign * TARGET_BUFFER_ATR * a) - targets[-1]) >= 0.5 * risk
        ]
        candidate = beyond[0] if beyond else fallback

        if sign * (candidate - previous) <= 0:
            candidate = fallback

        targets.append(candidate)

    reasons.append(f"R:R {rr:.2f} (TP1 z {tp1_source})")

    return Setup(
        decision=decision,
        reasons=reasons,
        bias=bias,
        entry=entry,
        zone_low=min(zone_a, zone_b),
        zone_high=max(zone_a, zone_b),
        stop=stop,
        targets=targets,
        rr=rr,
        atr_unit=a,
    )


def decimals_for(price: float) -> int:
    return 3 if price > 20 else 5


# ----------------------------------------------------------------------
# whole-symbol analysis
# ----------------------------------------------------------------------

def analyze_symbol(symbol: str, now: datetime | None = None, refresh_derived: bool = True) -> Analysis:
    if now is None:
        now = datetime.now(timezone.utc)

    if refresh_derived:
        from src.resample import derive_symbol

        derive_symbol(symbol, ["15min", "1h", "4h"])

    status = get_status(symbol, "1min", now=now)
    price_row = last_price(symbol)
    views = {tf: analyze_timeframe(load_series(symbol, tf, LOAD[tf]), tf) for tf in TIMEFRAMES}

    price = price_row[0] if price_row else None
    setup = build_setup(price, views["4h"], views["1h"], views["15min"], status.state.value)

    return Analysis(
        symbol=symbol,
        now=now,
        price=price,
        price_bar_open=price_row[1] if price_row else None,
        data_state=status.state.value,
        data_reason=status.reason,
        views=views,
        setup=setup,
    )
