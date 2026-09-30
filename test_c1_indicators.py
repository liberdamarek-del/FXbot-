"""Block C1 - indicators against hand-computed values."""

import math

from src.indicators import Level, atr, cluster_levels, ema, rsi, swing_points, true_ranges


def close(a, b, tol=1e-9):
    return a is not None and abs(a - b) <= tol


# ---- EMA: seeded with SMA; a linear series lags by exactly one step for period 3
values = [float(i) for i in range(1, 11)]
e = ema(values, 3)
assert e[:2] == [None, None] and close(e[2], 2.0) and close(e[3], 3.0) and close(e[9], 9.0)
assert ema([1.0, 2.0], 3) == [None, None]
assert close(ema([5.0] * 30, 10)[-1], 5.0)

# ---- true range and ATR (Wilder), hand computed
highs, lows, closes = [10, 12, 11, 13], [9, 10, 9, 10], [9.5, 11, 10, 12.5]
assert true_ranges(highs, lows, closes) == [1, 2.5, 2, 3]
a = atr(highs, lows, closes, 2)
assert a[:2] == [None, None] and close(a[2], 2.25) and close(a[3], 2.625)
flat = atr([12.0] * 40, [10.0] * 40, [11.0] * 40, 14)
assert close(flat[-1], 2.0) and flat[13] is None and flat[14] is not None

# ---- RSI (Wilder): extremes and one hand computed value
assert close(rsi([float(i) for i in range(30)], 14)[-1], 100.0)
assert close(rsi([float(30 - i) for i in range(30)], 14)[-1], 0.0)
assert close(rsi([5.0] * 30, 14)[-1], 50.0)
r = rsi([1, 2, 3, 2, 3], 3)
assert r[:3] == [None, None, None]
assert close(r[3], 100 - 100 / (1 + 2.0), 1e-9)                 # avg gain 2/3, loss 1/3
assert close(r[4], 100 - 100 / (1 + 3.5), 1e-9)                 # gain 7/9, loss 2/9

# ---- swing points: strict on the left, plateau gives ONE pivot, last k bars unconfirmed
h = [1, 2, 3, 5, 3, 2, 1, 2, 4, 4, 2, 1, 2, 3]
l = [x - 0.5 for x in h]
sh, sl = swing_points(h, l, 2)
assert sh == [(3, 5), (8, 4)], sh                                 # 4,4 plateau -> first bar only
assert sl == [(6, 0.5), (11, 0.5)], sl
# prominence: the small middle peak (2.3) is only 0.8 above its window low and disappears at 1.0
h2 = [1, 2, 3, 2, 1, 2, 2.3, 2, 1, 2, 3, 2, 1]
l2 = [x - 0.5 for x in h2]
assert [i for i, _ in swing_points(h2, l2, 1)[0]] == [2, 6, 10]
assert [i for i, _ in swing_points(h2, l2, 1, min_prominence=1.0)[0]] == [2, 10]
assert swing_points(h, l, 2, min_prominence=0.0) == (sh, sl), "default keeps every pivot"
sh2, _ = swing_points(h, l, 3)
assert all(i <= len(h) - 4 for i, _ in sh2)

# ---- level clustering: spans, no chaining, mean price, touches, last index
levels = cluster_levels([(1, 1.00), (5, 1.01), (9, 1.02), (7, 1.50)], 0.03)
assert [(round(x.price, 4), x.touches, x.last_index) for x in levels] == [(1.01, 3, 9), (1.5, 1, 7)]
chained = cluster_levels([(0, 1.00), (1, 1.02), (2, 1.04), (3, 1.06)], 0.03)
assert [x.touches for x in chained] == [2, 2], "clusters must not chain"
assert cluster_levels([], 0.1) == []

# ---- guards
for bad in (lambda: ema([1.0], 0), lambda: atr([1], [1], [1], 0), lambda: rsi([1.0], 0),
            lambda: swing_points([1], [1], 0), lambda: swing_points([1, 2], [1], 1),
            lambda: cluster_levels([(0, 1.0)], 0), lambda: true_ranges([1], [1, 2], [1])):
    try:
        bad()
    except ValueError:
        pass
    else:
        raise AssertionError("bad argument accepted")

print("=" * 60)
print("C1 INDICATORS")
print("=" * 60)
print("EMA (SEED, LAG): PASS")
print("TRUE RANGE / ATR (HAND COMPUTED, CONSTANT RANGE): PASS")
print("RSI (EXTREMES, HAND COMPUTED WILDER STEPS): PASS")
print("SWING POINTS (STRICT LEFT, PLATEAU, UNCONFIRMED EDGE): PASS")
print("LEVEL CLUSTERS (NO CHAINING, MEAN, TOUCHES): PASS")
print("GUARDS: PASS")
print("RESULT: PASS")
print("=" * 60)
