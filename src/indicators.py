"""Technical indicators (pure functions, no database, no I/O).

All series functions return a list aligned with the input; positions where
the indicator is not yet defined hold None.
"""

from dataclasses import dataclass
from typing import Sequence


def ema(values: Sequence[float], period: int) -> list[float | None]:
    """Exponential moving average, seeded with the SMA of the first period."""
    if period < 1:
        raise ValueError("period must be >= 1")

    n = len(values)
    out: list[float | None] = [None] * n

    if n < period:
        return out

    k = 2.0 / (period + 1)
    previous = sum(values[:period]) / period
    out[period - 1] = previous

    for i in range(period, n):
        previous = values[i] * k + previous * (1.0 - k)
        out[i] = previous

    return out


def true_ranges(
    highs: Sequence[float], lows: Sequence[float], closes: Sequence[float]
) -> list[float]:
    if not (len(highs) == len(lows) == len(closes)):
        raise ValueError("highs, lows and closes must have the same length")

    if not highs:
        return []

    result = [highs[0] - lows[0]]

    for i in range(1, len(highs)):
        result.append(
            max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
        )

    return result


def atr(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    period: int = 14,
) -> list[float | None]:
    """Average True Range with Wilder smoothing."""
    if period < 1:
        raise ValueError("period must be >= 1")

    tr = true_ranges(highs, lows, closes)
    n = len(tr)
    out: list[float | None] = [None] * n

    if n <= period:
        return out

    previous = sum(tr[1 : period + 1]) / period
    out[period] = previous

    for i in range(period + 1, n):
        previous = (previous * (period - 1) + tr[i]) / period
        out[i] = previous

    return out


def rsi(closes: Sequence[float], period: int = 14) -> list[float | None]:
    """Relative Strength Index with Wilder smoothing."""
    if period < 1:
        raise ValueError("period must be >= 1")

    n = len(closes)
    out: list[float | None] = [None] * n

    if n <= period:
        return out

    gains = losses = 0.0

    for i in range(1, period + 1):
        change = closes[i] - closes[i - 1]
        gains += max(change, 0.0)
        losses += max(-change, 0.0)

    avg_gain = gains / period
    avg_loss = losses / period

    def value() -> float:
        if avg_loss == 0.0:
            return 50.0 if avg_gain == 0.0 else 100.0

        return 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)

    out[period] = value()

    for i in range(period + 1, n):
        change = closes[i] - closes[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(change, 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-change, 0.0)) / period
        out[i] = value()

    return out


def swing_points(
    highs: Sequence[float],
    lows: Sequence[float],
    k: int,
    min_prominence: float = 0.0,
) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
    """Confirmed swing highs and lows.

    A swing high is strictly higher than the k bars before it and at least as
    high as the k bars after it (so a plateau yields one pivot). The last k
    bars can never be pivots: they are not confirmed yet.

    min_prominence > 0 keeps only pivots that stand out: a swing high must
    exceed the lowest low of its window (k bars each side) by that amount, a
    swing low must be below the highest high of its window by that amount.
    This removes noise pivots.
    """
    if k < 1:
        raise ValueError("k must be >= 1")

    if len(highs) != len(lows):
        raise ValueError("highs and lows must have the same length")

    swing_highs: list[tuple[int, float]] = []
    swing_lows: list[tuple[int, float]] = []

    for i in range(k, len(highs) - k):
        if highs[i] > max(highs[i - k : i]) and highs[i] >= max(highs[i + 1 : i + k + 1]):
            if highs[i] - min(lows[i - k : i + k + 1]) >= min_prominence:
                swing_highs.append((i, highs[i]))

        if lows[i] < min(lows[i - k : i]) and lows[i] <= min(lows[i + 1 : i + k + 1]):
            if max(highs[i - k : i + k + 1]) - lows[i] >= min_prominence:
                swing_lows.append((i, lows[i]))

    return swing_highs, swing_lows


@dataclass(frozen=True)
class Level:
    price: float
    touches: int
    last_index: int


def cluster_levels(
    points: Sequence[tuple[int, float]], tolerance: float
) -> list[Level]:
    """Merge nearby pivot prices into levels.

    A cluster spans at most `tolerance` from its lowest to its highest price
    (no chaining). The level price is the mean; touches = number of pivots.
    """
    if tolerance <= 0:
        raise ValueError("tolerance must be > 0")

    ordered = sorted(points, key=lambda p: p[1])
    levels: list[Level] = []
    group: list[tuple[int, float]] = []

    def close() -> None:
        if group:
            prices = [p[1] for p in group]
            levels.append(
                Level(
                    price=sum(prices) / len(prices),
                    touches=len(group),
                    last_index=max(p[0] for p in group),
                )
            )

    for point in ordered:
        if group and point[1] - group[0][1] > tolerance:
            close()
            group = []

        group.append(point)

    close()
    return levels


def swing_pivots(
    highs: Sequence[float],
    lows: Sequence[float],
    k: int,
    prominence: Sequence[float | None],
) -> list[tuple[int, int, float, str]]:
    """Swing pivots with a per-bar prominence threshold.

    Same pivot rule as swing_points(), but the noise filter may change over
    time (prominence[i], e.g. a multiple of the ATR at bar i; None = pivot
    not evaluated). Returns (pivot_index, confirm_index, price, "H"/"L"),
    ordered by confirm_index. confirm_index = pivot_index + k is the first
    bar at whose CLOSE the pivot is known - using it earlier would be
    look-ahead.
    """
    if k < 1:
        raise ValueError("k must be >= 1")

    if not (len(highs) == len(lows) == len(prominence)):
        raise ValueError("highs, lows and prominence must have the same length")

    pivots: list[tuple[int, int, float, str]] = []

    for i in range(k, len(highs) - k):
        threshold = prominence[i]

        if threshold is None:
            continue

        window_low = min(lows[i - k : i + k + 1])
        window_high = max(highs[i - k : i + k + 1])

        if highs[i] > max(highs[i - k : i]) and highs[i] >= max(highs[i + 1 : i + k + 1]):
            if highs[i] - window_low >= threshold:
                pivots.append((i, i + k, highs[i], "H"))

        if lows[i] < min(lows[i - k : i]) and lows[i] <= min(lows[i + 1 : i + k + 1]):
            if window_high - lows[i] >= threshold:
                pivots.append((i, i + k, lows[i], "L"))

    pivots.sort(key=lambda p: (p[1], p[0]))
    return pivots


def efficiency_ratio(closes: Sequence[float], period: int) -> list[float | None]:
    """Kaufman efficiency ratio: |net move| / sum of |bar moves| over
    `period` bars. 1 = straight trend, near 0 = noise / range."""
    n = len(closes)
    out: list[float | None] = [None] * n

    for i in range(period, n):
        path = sum(abs(closes[j] - closes[j - 1]) for j in range(i - period + 1, i + 1))
        out[i] = abs(closes[i] - closes[i - period]) / path if path > 0 else 0.0

    return out


def rolling_percentile(values: Sequence[float | None], window: int) -> list[float | None]:
    """Percentile rank (0-100) of values[i] among the previous `window`
    defined values including itself. Causal (uses no later value)."""
    import bisect

    out: list[float | None] = [None] * len(values)
    ordered: list[float] = []
    history: list[float] = []

    for i, value in enumerate(values):
        if value is None:
            continue

        bisect.insort(ordered, value)
        history.append(value)

        if len(history) > window:
            old = history.pop(0)
            del ordered[bisect.bisect_left(ordered, old)]

        if len(history) >= min(window, 20):
            out[i] = 100.0 * bisect.bisect_left(ordered, value) / len(ordered)

    return out
