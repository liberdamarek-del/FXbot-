"""Price series with causal indicators and point-in-time access.

A PriceSeries holds the CLOSED bars of one pair and timeframe (bid/ask
where the source provides them) and precomputes indicators once. Every
indicator value at index i uses bars 0..i only; `index_at(t)` returns the
newest bar that was closed at time t. The analysis therefore never sees a
bar that was still forming, and a backtest can walk through time by index
without recomputing anything and without look-ahead.

Swing pivots are only visible from their confirmation bar on
(src/indicators.swing_pivots).

Bars built from a source without bid/ask (Twelve Data mid prices) carry
side_correct=False; costs for them come from the typical spread of the
side-correct history (module 64, KNOWN-COST-ADJUSTED layer).
"""

import bisect
from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.indicators import atr, efficiency_ratio, ema, rolling_percentile, rsi, swing_pivots
from src.path_archive import TIMEFRAME_SECONDS, Bar

UTC = timezone.utc
SHOCK_BAR_ATR = 2.5          # a single bar of >= 2.5 ATR is a shock (level reset, module 48)


@dataclass
class PriceSeries:
    symbol: str
    timeframe: str
    ts: list[int]
    open: list[float]
    high: list[float]
    low: list[float]
    close: list[float]
    bid_close: list[float]
    ask_close: list[float]
    bid_high: list[float]
    bid_low: list[float]
    ask_high: list[float]
    ask_low: list[float]
    volume: list[float]
    side_correct: list[bool]
    pivot_k: int = 3
    pivot_prominence_atr: float = 0.8
    # indicators (filled by compute())
    ema20: list = field(default_factory=list)
    ema50: list = field(default_factory=list)
    ema200: list = field(default_factory=list)
    atr14: list = field(default_factory=list)
    rsi14: list = field(default_factory=list)
    er20: list = field(default_factory=list)
    atr_pct: list = field(default_factory=list)
    pivots: list = field(default_factory=list)          # (pivot_i, confirm_i, price, kind)
    shock: list = field(default_factory=list)           # bar range >= 2.5 x previous ATR
    _pivot_confirms: list = field(default_factory=list)

    @property
    def seconds(self) -> int:
        return TIMEFRAME_SECONDS[self.timeframe]

    def __len__(self) -> int:
        return len(self.ts)

    @classmethod
    def from_bars(cls, symbol: str, timeframe: str, bars: list[Bar], side_correct: list[bool] | None = None,
                  pivot_k: int = 3, pivot_prominence_atr: float = 0.8) -> "PriceSeries":
        bars = sorted(bars, key=lambda b: b.ts)
        series = cls(
            symbol=symbol,
            timeframe=timeframe,
            ts=[b.ts for b in bars],
            open=[b.mo for b in bars],
            high=[b.mh for b in bars],
            low=[b.ml for b in bars],
            close=[b.mc for b in bars],
            bid_close=[b.bc for b in bars],
            ask_close=[b.ac for b in bars],
            bid_high=[b.bh for b in bars],
            bid_low=[b.bl for b in bars],
            ask_high=[b.ah for b in bars],
            ask_low=[b.al for b in bars],
            volume=[b.volume for b in bars],
            side_correct=side_correct if side_correct is not None else [True] * len(bars),
            pivot_k=pivot_k,
            pivot_prominence_atr=pivot_prominence_atr,
        )
        series.compute()
        return series

    def compute(self) -> None:
        self.ema20 = ema(self.close, 20)
        self.ema50 = ema(self.close, 50)
        self.ema200 = ema(self.close, 200)
        self.atr14 = atr(self.high, self.low, self.close, 14)
        self.rsi14 = rsi(self.close, 14)
        self.er20 = efficiency_ratio(self.close, 20)
        self.atr_pct = rolling_percentile(self.atr14, 250)
        prominence = [None if a is None else self.pivot_prominence_atr * a for a in self.atr14]
        self.pivots = swing_pivots(self.high, self.low, self.pivot_k, prominence)
        self._pivot_confirms = [p[1] for p in self.pivots]
        self.shock = [False] + [
            bool(self.atr14[j - 1]) and self.high[j] - self.low[j] >= SHOCK_BAR_ATR * self.atr14[j - 1]
            for j in range(1, len(self.ts))
        ]

    # ------------------------------------------------------------------
    # point-in-time access
    # ------------------------------------------------------------------

    def index_at(self, t: int) -> int:
        """Index of the newest bar CLOSED at time t (-1 if none)."""
        # bar i is closed at ts[i] + seconds
        return bisect.bisect_right(self.ts, t - self.seconds) - 1

    def close_time(self, i: int) -> int:
        return self.ts[i] + self.seconds

    def pivots_known_at(self, i: int, lookback_bars: int | None = None) -> list[tuple]:
        """Pivots confirmed at or before bar i (optionally only recent ones)."""
        end = bisect.bisect_right(self._pivot_confirms, i)
        pivots = self.pivots[:end]

        if lookback_bars is not None:
            lower = i - lookback_bars
            pivots = [p for p in pivots if p[0] >= lower]

        return pivots

    def ret(self, i: int, bars: int) -> float | None:
        if i - bars < 0:
            return None

        return self.close[i] / self.close[i - bars] - 1.0

    def spread(self, i: int) -> float:
        return self.ask_close[i] - self.bid_close[i]

    def time(self, i: int) -> datetime:
        return datetime.fromtimestamp(self.ts[i], tz=UTC)


def merge_bars(preferred: list[Bar], fallback: list[Bar]) -> list[Bar]:
    """Union by bar time; a bar from `preferred` wins over `fallback`."""
    by_ts = {b.ts: b for b in fallback}
    by_ts.update({b.ts: b for b in preferred})
    return [by_ts[k] for k in sorted(by_ts)]
