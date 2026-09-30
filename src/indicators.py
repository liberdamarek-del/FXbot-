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
