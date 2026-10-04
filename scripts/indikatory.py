"""Causal technical indicators and a parametric condition grid for the weekly
research (scripts/tydenni_analyza.py).

Every value at bar t uses only bars <= t (no look-ahead; test_f2 checks that
appending future bars never changes past values). A condition is a boolean
state of the market at the CLOSE of bar t, built from (kind, params), so its
neighbouring settings (RSI13 / RSI15 next to RSI14, EMA21 next to EMA20...)
can be built the same way for the robustness check.

Grid (user's specification 2026-10-04):
    RSI 5/7/9/14/21/28 x 20/80 25/75 30/70 35/65 40/60: oversold, overbought, return
        from oversold / overbought, > 50, < 50, simple divergence (RSI14 only)
    SMA and EMA 5/10/20/30/50/100/200: price above / below, slope, cross, distance > 1 ATR;
        EMA fast > slow and crosses (5/20, 10/30, 20/50, 50/200)
    MACD fast 5/8/12 x slow 17/21/26/34 x signal 5/9/12: crosses, histogram sign,
        histogram change, histogram far from zero (> 1 rolling sd)
    Bollinger 10/20/30/50 x 1.5/2.0/2.5/3.0: touch / break / return at both bands;
        width squeeze and expansion per period
    Stochastic 5/9/14/21 x smoothing 3/5: K > D, K < D, > 80, < 20, crosses
    ATR 5/10/14/21/28: high / low ATR % of price, rising / falling, breakout with rising ATR
    ADX 7/14/21/28 x 20/25/30/35: trend, no trend, trend with +DI / -DI; +DI > -DI
"""

from dataclasses import dataclass

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

RSI_N = (5, 7, 9, 14, 21, 28)
RSI_BANDS = ((20, 80), (25, 75), (30, 70), (35, 65), (40, 60))
MA_N = (5, 10, 20, 30, 50, 100, 200)
EMA_PAIRS = ((5, 20), (10, 30), (20, 50), (50, 200))
MACD_F, MACD_S, MACD_G = (5, 8, 12), (17, 21, 26, 34), (5, 9, 12)
BB_N, BB_K = (10, 20, 30, 50), (1.5, 2.0, 2.5, 3.0)
ST_N, ST_S = (5, 9, 14, 21), (3, 5)
ATR_N = (5, 10, 14, 21, 28)
ADX_N, ADX_T = (7, 14, 21, 28), (20, 25, 30, 35)


# ----------------------------------------------------------------------
# indicators (all causal, NaN during the warm-up)
# ----------------------------------------------------------------------

def sma(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        c = np.cumsum(np.insert(np.asarray(x, float), 0, 0.0))
        out[n - 1:] = (c[n:] - c[:-n]) / n
    return out


def ema(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full(len(x), np.nan)
    if len(x) < n:
        return out
    a = 2.0 / (n + 1)
    v = float(np.mean(x[:n]))                      # seeded with the first n values' mean
    out[n - 1] = v
    for i in range(n, len(x)):
        v += a * (x[i] - v)
        out[i] = v
    return out


def wilder(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full(len(x), np.nan)
    ok = np.where(~np.isnan(x))[0]
    if len(ok) < n:
        return out
    s = ok[0]
    if len(x) - s < n:
        return out
    v = float(np.mean(x[s:s + n]))
    out[s + n - 1] = v
    for i in range(s + n, len(x)):
        v += (x[i] - v) / n
        out[i] = v
    return out


def rsi(c: np.ndarray, n: int) -> np.ndarray:
    d = np.diff(c, prepend=np.nan)
    up, dn = wilder(np.where(np.isnan(d), np.nan, np.maximum(d, 0)), n), \
        wilder(np.where(np.isnan(d), np.nan, np.maximum(-d, 0)), n)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = 100 - 100 / (1 + up / dn)
    return np.where(dn == 0, 100.0, r)


def true_range(h, l, c) -> np.ndarray:
    pc = np.concatenate([[np.nan], c[:-1]])
    tr = np.nanmax(np.vstack([h - l, np.abs(h - pc), np.abs(l - pc)]), axis=0)
    tr[0] = h[0] - l[0]
    return tr


def atr(h, l, c, n: int) -> np.ndarray:
    return wilder(true_range(h, l, c), n)


def adx(h, l, c, n: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    up, dn = np.diff(h, prepend=np.nan), -np.diff(l, prepend=np.nan)
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    pdm[0] = mdm[0] = np.nan
    tr = true_range(h, l, c)
    tr[0] = np.nan
    a_tr, a_p, a_m = wilder(tr, n), wilder(pdm, n), wilder(mdm, n)
    with np.errstate(divide="ignore", invalid="ignore"):
        pdi, mdi = 100 * a_p / a_tr, 100 * a_m / a_tr
        dx = 100 * np.abs(pdi - mdi) / (pdi + mdi)
    return wilder(dx, n), pdi, mdi


def macd(c, f: int, s: int, g: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    m = ema(c, f) - ema(c, s)
    ok = ~np.isnan(m)
    sig = np.full(len(c), np.nan)
    if ok.sum() >= g:
        first = np.argmax(ok)
        sig[first:] = ema(m[first:], g)
    return m, sig, m - sig


def bollinger(c, n: int, k: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    mid = sma(c, n)
    sd = np.full(len(c), np.nan)
    if len(c) >= n:
        sd[n - 1:] = sliding_window_view(np.asarray(c, float), n).std(axis=1)
    up, dn = mid + k * sd, mid - k * sd
    with np.errstate(divide="ignore", invalid="ignore"):
        width = (up - dn) / mid
    return mid, up, dn, width


def stochastic(h, l, c, n: int, s: int) -> tuple[np.ndarray, np.ndarray]:
    hh, ll = rolling_max(h, n), rolling_min(l, n)
    with np.errstate(divide="ignore", invalid="ignore"):
        raw = np.where(hh > ll, (c - ll) / (hh - ll) * 100, 50.0)
    raw[np.isnan(hh)] = np.nan
    k = sma_nan(raw, s)
    return k, sma_nan(k, 3)


def sma_nan(x: np.ndarray, n: int) -> np.ndarray:
    """SMA that starts after the leading NaNs of x."""
    out = np.full(len(x), np.nan)
    ok = ~np.isnan(x)
    if ok.any():
        first = int(np.argmax(ok))
        out[first:] = sma(x[first:], n)
    return out


def rolling_max(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        out[n - 1:] = sliding_window_view(np.asarray(x, float), n).max(axis=1)
    return out


def rolling_min(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        out[n - 1:] = sliding_window_view(np.asarray(x, float), n).min(axis=1)
    return out


def shift(x: np.ndarray, k: int = 1) -> np.ndarray:
    out = np.full(len(x), np.nan)
    if k < len(x):
        out[k:] = x[:-k]
    return out


def rolling_rank(x: np.ndarray, w: int) -> np.ndarray:
    """Share of the last w values (current included) that are <= the current value."""
    out = np.full(len(x), np.nan)
    if len(x) >= w:
        win = sliding_window_view(np.asarray(x, float), w)
        cur = win[:, -1:]
        with np.errstate(invalid="ignore"):
            out[w - 1:] = (win <= cur).mean(axis=1)
        out[w - 1:][np.isnan(win).any(axis=1)] = np.nan
    return out


def rolling_std(x: np.ndarray, w: int) -> np.ndarray:
    out = np.full(len(x), np.nan)
    if len(x) >= w:
        out[w - 1:] = sliding_window_view(np.asarray(x, float), w).std(axis=1)
    return out


# ----------------------------------------------------------------------
# conditions
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class Cond:
    kind: str
    params: tuple
    tf: str = ""                                   # "" = the base timeframe, "4H" / "1D" = a higher one

    @property
    def key(self) -> str:
        p = self.params
        k = {
            "rsi_lt": lambda: f"RSI{p[0]}<{p[1]}", "rsi_gt": lambda: f"RSI{p[0]}>{p[1]}",
            "rsi_xup": lambda: f"RSI{p[0]} x^{p[1]}", "rsi_xdn": lambda: f"RSI{p[0]} xv{p[1]}",
            "rsi_bdiv": lambda: f"RSI{p[0]} bdiv", "rsi_sdiv": lambda: f"RSI{p[0]} sdiv",
            "px_gt": lambda: f"C>{p[0]}{p[1]}", "px_lt": lambda: f"C<{p[0]}{p[1]}",
            "slope_up": lambda: f"{p[0]}{p[1]} up", "slope_dn": lambda: f"{p[0]}{p[1]} dn",
            "px_xup": lambda: f"C x^{p[0]}{p[1]}", "px_xdn": lambda: f"C xv{p[0]}{p[1]}",
            "px_far_up": lambda: f"C>>{p[0]}{p[1]}", "px_far_dn": lambda: f"C<<{p[0]}{p[1]}",
            "ema_gt": lambda: f"EMA{p[0]}>EMA{p[1]}", "ema_lt": lambda: f"EMA{p[0]}<EMA{p[1]}",
            "ema_xup": lambda: f"EMA{p[0]} x^EMA{p[1]}", "ema_xdn": lambda: f"EMA{p[0]} xvEMA{p[1]}",
            "macd_xup": lambda: f"MACD{p[0]}/{p[1]}/{p[2]} x^", "macd_xdn": lambda: f"MACD{p[0]}/{p[1]}/{p[2]} xv",
            "macd_hpos": lambda: f"MACD{p[0]}/{p[1]}/{p[2]} H>0", "macd_hneg": lambda: f"MACD{p[0]}/{p[1]}/{p[2]} H<0",
            "macd_hup": lambda: f"MACD{p[0]}/{p[1]}/{p[2]} H up", "macd_hdn": lambda: f"MACD{p[0]}/{p[1]}/{p[2]} H dn",
            "macd_hfar_up": lambda: f"MACD{p[0]}/{p[1]}/{p[2]} H>>", "macd_hfar_dn": lambda: f"MACD{p[0]}/{p[1]}/{p[2]} H<<",
            "bb_tup": lambda: f"BB{p[0]}/{p[1]} tH", "bb_bup": lambda: f"BB{p[0]}/{p[1]} pH",
            "bb_rup": lambda: f"BB{p[0]}/{p[1]} nH", "bb_tdn": lambda: f"BB{p[0]}/{p[1]} tD",
            "bb_bdn": lambda: f"BB{p[0]}/{p[1]} pD", "bb_rdn": lambda: f"BB{p[0]}/{p[1]} nD",
            "bb_sqz": lambda: f"BB{p[0]} sqz", "bb_exp": lambda: f"BB{p[0]} exp",
            "st_kgd": lambda: f"ST{p[0]}/{p[1]} K>D", "st_kld": lambda: f"ST{p[0]}/{p[1]} K<D",
            "st_ob": lambda: f"ST{p[0]}/{p[1]} K>80", "st_os": lambda: f"ST{p[0]}/{p[1]} K<20",
            "st_xup": lambda: f"ST{p[0]}/{p[1]} x^", "st_xdn": lambda: f"ST{p[0]}/{p[1]} xv",
            "atr_hi": lambda: f"ATR{p[0]} vys", "atr_lo": lambda: f"ATR{p[0]} niz",
            "atr_up": lambda: f"ATR{p[0]} up", "atr_dn": lambda: f"ATR{p[0]} dn",
            "atr_brk_up": lambda: f"ATR{p[0]} brkH", "atr_brk_dn": lambda: f"ATR{p[0]} brkD",
            "adx_gt": lambda: f"ADX{p[0]}>{p[1]}", "adx_lt": lambda: f"ADX{p[0]}<{p[1]}",
            "adx_bull": lambda: f"ADX{p[0]}>{p[1]}+DI", "adx_bear": lambda: f"ADX{p[0]}>{p[1]}-DI",
            "di_bull": lambda: f"DI{p[0]}+", "di_bear": lambda: f"DI{p[0]}-",
        }[self.kind]()
        return f"{self.tf}:{k}" if self.tf else k


def grid() -> list[Cond]:
    """All single conditions of the user's specification (~840)."""
    g = []
    for n in RSI_N:
        for lo, hi in RSI_BANDS:
            g += [Cond("rsi_lt", (n, lo)), Cond("rsi_gt", (n, hi)), Cond("rsi_xup", (n, lo)), Cond("rsi_xdn", (n, hi))]
        g += [Cond("rsi_gt", (n, 50)), Cond("rsi_lt", (n, 50))]
    g += [Cond("rsi_bdiv", (14,)), Cond("rsi_sdiv", (14,))]
    for ma in ("SMA", "EMA"):
        for n in MA_N:
            g += [Cond(k, (ma, n)) for k in ("px_gt", "px_lt", "slope_up", "slope_dn", "px_xup", "px_xdn",
                                              "px_far_up", "px_far_dn")]
    for f, s in EMA_PAIRS:
        g += [Cond(k, (f, s)) for k in ("ema_gt", "ema_lt", "ema_xup", "ema_xdn")]
    for f in MACD_F:
        for s in MACD_S:
            for sg in MACD_G:
                g += [Cond(k, (f, s, sg)) for k in ("macd_xup", "macd_xdn", "macd_hpos", "macd_hneg", "macd_hup",
                                                    "macd_hdn", "macd_hfar_up", "macd_hfar_dn")]
    for n in BB_N:
        for k in BB_K:
            g += [Cond(x, (n, k)) for x in ("bb_tup", "bb_bup", "bb_rup", "bb_tdn", "bb_bdn", "bb_rdn")]
        g += [Cond("bb_sqz", (n,)), Cond("bb_exp", (n,))]
    for n in ST_N:
        for s in ST_S:
            g += [Cond(x, (n, s)) for x in ("st_kgd", "st_kld", "st_ob", "st_os", "st_xup", "st_xdn")]
    for n in ATR_N:
        g += [Cond(x, (n,)) for x in ("atr_hi", "atr_lo", "atr_up", "atr_dn", "atr_brk_up", "atr_brk_dn")]
    for n in ADX_N:
        for t in ADX_T:
            g += [Cond(x, (n, t)) for x in ("adx_gt", "adx_lt", "adx_bull", "adx_bear")]
        g += [Cond("di_bull", (n,)), Cond("di_bear", (n,))]
    return g


def mtf_grid(tf: str) -> list[Cond]:
    """States of a higher timeframe used next to the base timeframe's conditions (multi-timeframe combinations)."""
    return [Cond(k, p, tf) for k, p in (
        ("px_gt", ("EMA", 20)), ("px_lt", ("EMA", 20)), ("px_gt", ("EMA", 50)), ("px_lt", ("EMA", 50)),
        ("px_gt", ("SMA", 200)), ("px_lt", ("SMA", 200)), ("rsi_gt", (14, 50)), ("rsi_lt", (14, 50)),
        ("adx_bull", (14, 25)), ("adx_bear", (14, 25)), ("adx_lt", (14, 20)), ("macd_hpos", (12, 26, 9)),
        ("macd_hneg", (12, 26, 9)))]


def _step(n: int) -> int:
    return max(1, int(round(0.1 * n)))


def neighbors(c: Cond) -> list[Cond]:
    """The same condition with one parameter moved a small step (period +-10 % or +-1, threshold +-5,
    Bollinger k +-0.25): the robustness check of a result (ROBUST vs POSSIBLE OVERFIT)."""
    p, out = c.params, []

    def add(*params):
        out.append(Cond(c.kind, tuple(params), c.tf))
    if c.kind.startswith("rsi"):
        n = p[0]
        for d in (-_step(n), _step(n)):
            if n + d >= 2:
                add(n + d, *p[1:])
        if len(p) > 1:
            for d in (-5, 5):
                if 5 <= p[1] + d <= 95:
                    add(p[0], p[1] + d)
    elif c.kind in ("px_gt", "px_lt", "slope_up", "slope_dn", "px_xup", "px_xdn", "px_far_up", "px_far_dn"):
        for d in (-_step(p[1]), _step(p[1])):
            if p[1] + d >= 2:
                add(p[0], p[1] + d)
    elif c.kind.startswith("ema_"):
        for d in (-_step(p[0]), _step(p[0])):
            if 2 <= p[0] + d < p[1]:
                add(p[0] + d, p[1])
        for d in (-_step(p[1]), _step(p[1])):
            if p[1] + d > p[0]:
                add(p[0], p[1] + d)
    elif c.kind.startswith("macd"):
        for i in range(3):
            for d in (-_step(p[i]), _step(p[i])):
                q = list(p)
                q[i] += d
                if q[0] >= 2 and q[1] > q[0] and q[2] >= 2:
                    add(*q)
    elif c.kind in ("bb_sqz", "bb_exp"):
        for d in (-_step(p[0]), _step(p[0])):
            add(p[0] + d)
    elif c.kind.startswith("bb_"):
        for d in (-_step(p[0]), _step(p[0])):
            add(p[0] + d, p[1])
        for d in (-0.25, 0.25):
            if p[1] + d >= 1.0:
                add(p[0], round(p[1] + d, 2))
    elif c.kind.startswith("st_"):
        for d in (-_step(p[0]), _step(p[0])):
            if p[0] + d >= 3:
                add(p[0] + d, p[1])
        for d in (-1, 1):
            if p[1] + d >= 1:
                add(p[0], p[1] + d)
    elif c.kind.startswith("atr"):
        for d in (-_step(p[0]), _step(p[0])):
            if p[0] + d >= 2:
                add(p[0] + d)
    elif c.kind in ("adx_gt", "adx_lt", "adx_bull", "adx_bear"):
        for d in (-_step(p[0]), _step(p[0])):
            add(p[0] + d, p[1])
        for d in (-5, 5):
            add(p[0], p[1] + d)
    elif c.kind.startswith("di_"):
        for d in (-_step(p[0]), _step(p[0])):
            add(p[0] + d)
    return out


class Builder:
    """Computes condition masks on one bar series {o, h, l, c} with a cache of the indicators."""

    def __init__(self, bars: dict):
        self.o, self.h, self.l, self.c = (np.asarray(bars[k], float) for k in "ohlc")
        self._ind: dict = {}

    def ind(self, name: str, *args):
        key = (name, args)
        if key not in self._ind:
            o, h, l, c = self.o, self.h, self.l, self.c
            self._ind[key] = {
                "rsi": lambda: rsi(c, *args), "SMA": lambda: sma(c, *args), "EMA": lambda: ema(c, *args),
                "atr": lambda: atr(h, l, c, *args), "adx": lambda: adx(h, l, c, *args),
                "macd": lambda: macd(c, *args), "bb": lambda: bollinger(c, *args),
                "st": lambda: stochastic(h, l, c, *args),
            }[name]()
        return self._ind[key]

    def mask(self, cnd: Cond) -> np.ndarray:
        """Condition at each bar close; False during the warm-up (NaN comparisons)."""
        with np.errstate(invalid="ignore"):
            return np.nan_to_num(self._mask(cnd), nan=0).astype(bool)

    def _mask(self, cnd: Cond):
        k, p, c, h, l = cnd.kind, cnd.params, self.c, self.h, self.l
        prev = shift
        if k.startswith("rsi"):
            r = self.ind("rsi", p[0])
            if k == "rsi_lt":
                return r < p[1]
            if k == "rsi_gt":
                return r > p[1]
            if k == "rsi_xup":
                return (r > p[1]) & (prev(r) <= p[1])
            if k == "rsi_xdn":
                return (r < p[1]) & (prev(r) >= p[1])
            # simple divergence: a close below (above) every close 5-20 bars back while RSI stays above (below)
            # its lowest (highest) value of those bars
            lo_c, lo_r = shift(rolling_min(c, 16), 5), shift(rolling_min(r, 16), 5)
            hi_c, hi_r = shift(rolling_max(c, 16), 5), shift(rolling_max(r, 16), 5)
            return (c < lo_c) & (r > lo_r) if k == "rsi_bdiv" else (c > hi_c) & (r < hi_r)
        if k in ("px_gt", "px_lt", "slope_up", "slope_dn", "px_xup", "px_xdn", "px_far_up", "px_far_dn"):
            m = self.ind(p[0], p[1])
            if k == "px_gt":
                return c > m
            if k == "px_lt":
                return c < m
            if k == "slope_up":
                return m > shift(m, 5)
            if k == "slope_dn":
                return m < shift(m, 5)
            if k == "px_xup":
                return (c > m) & (prev(c) <= prev(m))
            if k == "px_xdn":
                return (c < m) & (prev(c) >= prev(m))
            a = self.ind("atr", 14)
            return (c - m) / a > 1 if k == "px_far_up" else (c - m) / a < -1
        if k.startswith("ema_"):
            f, s = self.ind("EMA", p[0]), self.ind("EMA", p[1])
            if k == "ema_gt":
                return f > s
            if k == "ema_lt":
                return f < s
            if k == "ema_xup":
                return (f > s) & (prev(f) <= prev(s))
            return (f < s) & (prev(f) >= prev(s))
        if k.startswith("macd"):
            m, sg, hist = self.ind("macd", *p)
            if k == "macd_xup":
                return (m > sg) & (prev(m) <= prev(sg))
            if k == "macd_xdn":
                return (m < sg) & (prev(m) >= prev(sg))
            if k == "macd_hpos":
                return hist > 0
            if k == "macd_hneg":
                return hist < 0
            if k == "macd_hup":
                return hist > prev(hist)
            if k == "macd_hdn":
                return hist < prev(hist)
            sd = rolling_std(np.nan_to_num(hist), 100)
            return hist > sd if k == "macd_hfar_up" else hist < -sd
        if k in ("bb_sqz", "bb_exp"):
            width = self.ind("bb", p[0], 2.0)[3]
            if k == "bb_sqz":
                return rolling_rank(width, 120) <= 0.2
            return (width > 1.2 * shift(width, 3)) & (rolling_rank(width, 120) > 0.5)
        if k.startswith("bb_"):
            _, up, dn, _ = self.ind("bb", p[0], p[1])
            return {"bb_tup": lambda: h >= up, "bb_bup": lambda: c > up,
                    "bb_rup": lambda: (c < up) & (prev(c) > prev(up)), "bb_tdn": lambda: l <= dn,
                    "bb_bdn": lambda: c < dn, "bb_rdn": lambda: (c > dn) & (prev(c) < prev(dn))}[k]()
        if k.startswith("st_"):
            kk, dd = self.ind("st", p[0], p[1])
            return {"st_kgd": lambda: kk > dd, "st_kld": lambda: kk < dd, "st_ob": lambda: kk > 80,
                    "st_os": lambda: kk < 20, "st_xup": lambda: (kk > dd) & (prev(kk) <= prev(dd)),
                    "st_xdn": lambda: (kk < dd) & (prev(kk) >= prev(dd))}[k]()
        if k.startswith("atr"):
            a = self.ind("atr", p[0])
            if k in ("atr_hi", "atr_lo"):
                rk = rolling_rank(a / c, 250)
                return rk > 0.8 if k == "atr_hi" else rk < 0.2
            if k == "atr_up":
                return a > shift(a, 5)
            if k == "atr_dn":
                return a < shift(a, 5)
            rising = a > shift(a, 5)
            if k == "atr_brk_up":
                return (c > shift(rolling_max(h, 20), 1)) & rising
            return (c < shift(rolling_min(l, 20), 1)) & rising
        if k in ("adx_gt", "adx_lt", "adx_bull", "adx_bear", "di_bull", "di_bear"):
            a, pdi, mdi = self.ind("adx", p[0])
            if k == "adx_gt":
                return a > p[1]
            if k == "adx_lt":
                return a < p[1]
            if k == "adx_bull":
                return (a > p[1]) & (pdi > mdi)
            if k == "adx_bear":
                return (a > p[1]) & (mdi > pdi)
            return pdi > mdi if k == "di_bull" else mdi > pdi
        raise ValueError(k)


# ----------------------------------------------------------------------
# timeframes
# ----------------------------------------------------------------------

def resample(bars: dict, seconds: int, base_seconds: int) -> dict:
    """Bars of a longer UTC-aligned timeframe; ts = start, close_ts = end of the last member bar."""
    ts = np.asarray(bars["ts"], np.int64)
    grp = ts // seconds
    idx = np.flatnonzero(np.diff(grp, prepend=grp[0] - 1))
    ends = np.append(idx[1:], len(ts)) - 1
    return {"ts": grp[idx] * seconds, "o": bars["o"][idx],
            "h": np.maximum.reduceat(bars["h"], idx), "l": np.minimum.reduceat(bars["l"], idx),
            "c": bars["c"][ends], "close_ts": ts[ends] + base_seconds}


def resample_days(bars: dict, base_seconds: int, day_of) -> dict:
    """Daily bars by a day label function (e.g. the New York 17:00 trading day)."""
    ts = np.asarray(bars["ts"], np.int64)
    labels = [day_of(int(t)) for t in ts]
    idx = [0] + [i for i in range(1, len(ts)) if labels[i] != labels[i - 1]]
    idx = np.array(idx)
    ends = np.append(idx[1:], len(ts)) - 1
    return {"ts": ts[idx], "o": bars["o"][idx], "h": np.maximum.reduceat(bars["h"], idx),
            "l": np.minimum.reduceat(bars["l"], idx), "c": bars["c"][ends], "close_ts": ts[ends] + base_seconds,
            "day": [labels[i] for i in idx]}


def align(higher_close_ts: np.ndarray, higher_mask: np.ndarray, base_close_ts: np.ndarray) -> np.ndarray:
    """Value of a higher-timeframe condition known at each base bar close: the last higher bar that CLOSED at or
    before it (no partial higher bar, no look-ahead)."""
    k = np.searchsorted(higher_close_ts, base_close_ts, side="right") - 1
    out = np.zeros(len(base_close_ts), bool)
    ok = k >= 0
    out[ok] = higher_mask[k[ok]]
    return out
