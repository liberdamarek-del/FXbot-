"""Technicke stavebni kameny zivého jadra: kauzalni indikatory v numpy (hodnota v bode i pouziva jen svicky <= i).

Funkce jsou PRESUNUTE DOSLOVNE z vyzkumnych labu (R-048, architektura-v2, faze 1), aby zive jadro nemuselo importovat
laby: sma ... rsi z scripts/strategy_mining.py, weekly_aligned z scripts/profit_lab.py, indicators z
scripts/winrate_lab.py. Vysledky musi zustat bit po bitu stejne (test_h1_core.py, zlaty zaklad).
"""

import numpy as np


def sma(x, n):
    """Simple moving average; NaN where the window has a gap."""
    valid = ~np.isnan(x)
    c = np.cumsum(np.insert(np.where(valid, x, 0.0), 0, 0.0))
    k = np.cumsum(np.insert(valid.astype(float), 0, 0.0))
    out = np.full(len(x), np.nan)
    full = (k[n:] - k[:-n]) == n
    out[n - 1:] = np.where(full, (c[n:] - c[:-n]) / n, np.nan)
    return out


def ema(x, n):
    out = np.full(len(x), np.nan)
    a = 2.0 / (n + 1)
    v = x[0]
    for i in range(len(x)):
        v = a * x[i] + (1 - a) * v
        out[i] = v
    out[:n - 1] = np.nan
    return out


def wilder(x, n):
    out = np.full(len(x), np.nan)
    if len(x) <= n:
        return out
    v = np.nanmean(x[1:n + 1])
    out[n] = v
    for i in range(n + 1, len(x)):
        v = (v * (n - 1) + x[i]) / n
        out[i] = v
    return out


def rolling_max(x, n):
    from numpy.lib.stride_tricks import sliding_window_view
    out = np.full(len(x), np.nan)
    out[n - 1:] = sliding_window_view(x, n).max(axis=1)
    return out


def rolling_min(x, n):
    from numpy.lib.stride_tricks import sliding_window_view
    out = np.full(len(x), np.nan)
    out[n - 1:] = sliding_window_view(x, n).min(axis=1)
    return out


def shift(x, k=1):
    out = np.full(len(x), np.nan)
    out[k:] = x[:-k]
    return out


def true_range(h, l, c):
    pc = shift(c)
    return np.nanmax(np.vstack([h - l, np.abs(h - pc), np.abs(l - pc)]), axis=0)


def rsi(c, n):
    """Wilder RSI. No movement at all over the window (up = down = 0, e.g. a stuck price feed) is 50 (neutral),
    not 0: a flat price is neither oversold nor overbought (audit 2026-10-04: 0 gave a false BUY signal)."""
    d = np.diff(c, prepend=c[0])
    up, dn = wilder(np.clip(d, 0, None), n), wilder(np.clip(-d, 0, None), n)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = 100 - 100 / (1 + up / np.where(dn == 0, 1e-12, dn))
    return np.where((up == 0) & (dn == 0), 50.0, r)


def weekly_aligned(dates, o, h, l, c):
    """Weekly indicators known at each day: completed weeks + the current week up to that day (its close so far,
    its high / low so far). On the week's last day this equals the completed week. week_end = Friday (the live
    model decides only at the Friday close). Audit 2026-10-04: before, every day of a week got the week's FINAL
    close / high / low (look-ahead on Monday-Thursday) and week_end looked at the next day's date."""
    keys = [tuple(d.isocalendar()[:2]) for d in dates]
    n = len(keys)
    order, wc, wh, wl = [], {}, {}, {}
    for k, ci, hi, li in zip(keys, c, h, l):
        if k not in wc:
            order.append(k)
            wh[k], wl[k] = hi, li
        wc[k], wh[k], wl[k] = ci, max(wh[k], hi), min(wl[k], li)
    C = np.array([wc[k] for k in order])                      # completed-week values (used only for earlier weeks)
    Hh = np.array([wh[k] for k in order])
    Ll = np.array([wl[k] for k in order])
    pos = {k: i for i, k in enumerate(order)}
    d = np.diff(C, prepend=C[0])
    state = {m: (wilder(np.clip(d, 0, None), m), wilder(np.clip(-d, 0, None), m)) for m in (2, 3)}
    out = {name: np.full(n, np.nan) for name in ("w_rsi2", "w_rsi3", "w_sma10", "w_sma20", "w_sma40", "w_hi52",
                                                  "w_lo52", "w_wr4")}
    run_h = run_l = None
    for i, k in enumerate(keys):
        p = pos[k]
        if i == 0 or keys[i - 1] != k:
            run_h, run_l = h[i], l[i]
        run_h, run_l = max(run_h, h[i]), min(run_l, l[i])
        ci = c[i]
        if p >= 1:
            for m in (2, 3):
                ag, al = state[m][0][p - 1], state[m][1][p - 1]
                if not (np.isnan(ag) or np.isnan(al)):
                    delta = ci - C[p - 1]
                    g, q = (ag * (m - 1) + max(delta, 0.0)) / m, (al * (m - 1) + max(-delta, 0.0)) / m
                    out[f"w_rsi{m}"][i] = 50.0 if g == 0 and q == 0 else 100.0 if q == 0 else 100 - 100 / (1 + g / q)
        for m in (10, 20, 40):
            if p >= m - 1:
                out[f"w_sma{m}"][i] = (C[p - m + 1:p].sum() + ci) / m
        if p >= 51:
            out["w_hi52"][i] = max(Hh[p - 51:p].max(), run_h)
            out["w_lo52"][i] = min(Ll[p - 51:p].min(), run_l)
        if p >= 3:
            hh4, ll4 = max(Hh[p - 3:p].max(), run_h), min(Ll[p - 3:p].min(), run_l)
            out["w_wr4"][i] = 100 * (ci - ll4) / (hh4 - ll4) if hh4 > ll4 else np.nan
    out["week_end"] = np.array([dd.weekday() == 4 for dd in dates])
    out["w_close"] = np.asarray(c, float).copy()
    return out


def indicators(o, h, l, c, atr) -> dict:
    out = {"atr_pct": np.array([np.nan] * len(c))}
    from numpy.lib.stride_tricks import sliding_window_view
    pct = np.full(len(c), np.nan)
    if len(c) >= 250:                                    # shorter history: no percentile yet
        w = sliding_window_view(atr, 250)
        pct[249:] = (w <= w[:, -1:]).mean(axis=1)
    out["atr_pct"] = pct
    for n in (2, 3, 4):
        out[f"rsi{n}"] = rsi(c, n)
    for n in (5, 9, 14):
        hh, ll = rolling_max(h, n), rolling_min(l, n)
        out[f"wr{n}"] = 100 * (c - ll) / np.where(hh - ll == 0, np.nan, hh - ll)       # 0 = lowest, 100 = highest
    for n in (5, 14):
        k = out.get(f"wr{n}", None)
        out[f"stoch{n}"] = sma(np.nan_to_num(k if k is not None else
                                                100 * (c - rolling_min(l, n)) /
                                                np.where(rolling_max(h, n) - rolling_min(l, n) == 0, np.nan,
                                                         rolling_max(h, n) - rolling_min(l, n)), nan=50), 3)
    for n, k in ((20, 2.0), (20, 1.5), (10, 2.0)):
        m = sma(c, n)
        sd = np.full(len(c), np.nan)
        if len(c) >= n:                                  # per window: E[c^2] - E[c]^2 on running sums cancels
            sd[n - 1:] = sliding_window_view(c, n).std(axis=1)   # digits and depends on where the series starts
        out[f"bb{n}_{k}"] = (c - (m - k * sd)) / np.where(sd == 0, np.nan, 2 * k * sd)
    out["ibs"] = (c - l) / np.where(h - l == 0, np.nan, h - l)
    down = np.concatenate([[0], (np.diff(c) < 0).astype(int)])
    up = np.concatenate([[0], (np.diff(c) > 0).astype(int)])
    for k in (2, 3, 4):
        out[f"down{k}"] = np.array([down[max(0, i - k + 1):i + 1].sum() == k for i in range(len(c))])
        out[f"up{k}"] = np.array([up[max(0, i - k + 1):i + 1].sum() == k for i in range(len(c))])
    out["dist_sma5"] = (c - sma(c, 5)) / atr
    out["kelt"] = (c - ema(c, 20)) / atr
    for n in (50, 100, 200):
        out[f"sma{n}"] = np.sign(c - sma(c, n))
    return out
