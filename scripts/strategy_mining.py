"""Strategy mining: hundreds of indicators in hundreds of settings, combined
with fundamental filters and a walk-forward machine-learning model - and an
honest answer whether anything beats the current model out of sample.

    python scripts/strategy_mining.py      # -> docs/STRATEGIE.md (~5 min, needs numpy)

1. LIBRARY: 250+ indicator settings on the daily and weekly chart (moving
   averages and crosses, MACD, ADX/DMI, Aroon, Parabolic SAR, Supertrend,
   Ichimoku, Donchian, Keltner, Bollinger, RSI, Stochastic, Williams %R, CCI,
   ROC, regression slope, Heikin-Ashi, candle patterns, pivots, streaks).
   Each gives a direction (+1 / -1 / 0) at the daily close.
2. x 6 FUNDAMENTAL FILTERS (none, carry agrees, rate momentum agrees, COT
   positioning not crowded against, risk regime agrees, the model's rule
   "at least one fundamental cluster for, none against") x both signs x
   holding 1 / 3 / 5 trading days = > 12 000 tested rules.
3. ENSEMBLE of the 20 best discovery rules (majority vote), pre-defined.
4. MACHINE LEARNING: L2 logistic regression on all indicator values and
   fundamentals, trained only on the years BEFORE the predicted year
   (expanding window), predicting the 5-day direction; trades when the
   probability is far enough from 50 %.
5. BASELINE: the V7.8.0 model's direction in exactly the same measurement.

Measurement: enter at the daily close, exit h days later at the close; net
= after a typical retail spread + slippage and the overnight financing, in
ATR(D1) units per trade; "uspesnost" = share of profitable trades. One
observation per day (pairs share the USD), every h-th day only (no overlap).

Protocol: rules are RANKED on 2016-09 .. 2021-12 only. The 30 best are then
shown on 2014-01 .. 2016-08 and 2022-01 .. 2026-09. Under pure chance about
0.6 of 30 would pass that check (measured by the same check on random
signals, printed in the report).
"""

import math
import pickle
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from research_signals import SIGNALS_FILE, SLIPPAGE_PIPS, SPREAD_PIPS, FINANCING_MARKUP, stitched_daily  # noqa: E402
from src.instruments import get_instrument, parse_symbols  # noqa: E402
from src.path_archive import trading_date  # noqa: E402

UTC = timezone.utc
PERIODS = {"EARLY": (date(2014, 1, 1), date(2016, 8, 31)), "CHOOSE": (date(2016, 9, 1), date(2021, 12, 31)),
           "HOLDOUT": (date(2022, 1, 1), date(2026, 9, 30))}
HORIZONS = (1, 3, 5)
MAX_GAP_DAYS = 9


# ----------------------------------------------------------------------
# indicator helpers (numpy, causal: value at i uses bars <= i)
# ----------------------------------------------------------------------

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
    d = np.diff(c, prepend=c[0])
    up, dn = wilder(np.clip(d, 0, None), n), wilder(np.clip(-d, 0, None), n)
    return 100 - 100 / (1 + up / np.where(dn == 0, 1e-12, dn))


def sign_of(x):
    s = np.sign(x)
    s[np.isnan(x)] = 0
    return s


def band(x, low, high):
    """+1 below low (oversold), -1 above high, else 0 (mean-reversion form)."""
    out = np.zeros(len(x))
    out[x < low] = 1
    out[x > high] = -1
    return out


def state_breakout(c, upper, lower):
    """Turtle state: +1 after a close above the upper channel until a close below the lower."""
    out = np.zeros(len(c))
    s = 0
    for i in range(len(c)):
        if not np.isnan(upper[i]) and c[i] > upper[i]:
            s = 1
        elif not np.isnan(lower[i]) and c[i] < lower[i]:
            s = -1
        out[i] = s
    return out


def psar(h, l, step, mx):
    n = len(h)
    out = np.zeros(n)
    trend, ep, af, sar = 1, h[0], step, l[0]
    for i in range(1, n):
        sar = sar + af * (ep - sar)
        if trend > 0:
            sar = min(sar, l[i - 1], l[max(0, i - 2)])
            if l[i] < sar:
                trend, sar, ep, af = -1, ep, l[i], step
            elif h[i] > ep:
                ep, af = h[i], min(mx, af + step)
        else:
            sar = max(sar, h[i - 1], h[max(0, i - 2)])
            if h[i] > sar:
                trend, sar, ep, af = 1, ep, h[i], step
            elif l[i] < ep:
                ep, af = l[i], min(mx, af + step)
        out[i] = trend
    return out


def supertrend(h, l, c, n, mult):
    a = wilder(true_range(h, l, c), n)
    mid = (h + l) / 2
    up_b, dn_b = mid + mult * a, mid - mult * a
    out = np.zeros(len(c))
    trend, fu, fl = 1, np.nan, np.nan
    for i in range(len(c)):
        if np.isnan(a[i]):
            continue
        fu = up_b[i] if np.isnan(fu) or up_b[i] < fu or c[i - 1] > fu else fu
        fl = dn_b[i] if np.isnan(fl) or dn_b[i] > fl or c[i - 1] < fl else fl
        if c[i] > fu:
            trend = 1
        elif c[i] < fl:
            trend = -1
        out[i] = trend
    return out


def dmi(h, l, c, n):
    up, dn = h - shift(h), shift(l) - l
    plus = np.where((up > dn) & (up > 0), up, 0.0)
    minus = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = wilder(true_range(h, l, c), n)
    pdi = 100 * wilder(np.nan_to_num(plus), n) / tr
    mdi = 100 * wilder(np.nan_to_num(minus), n) / tr
    dx = 100 * np.abs(pdi - mdi) / np.where(pdi + mdi == 0, 1e-12, pdi + mdi)
    return pdi, mdi, wilder(np.nan_to_num(dx), n)


def linreg_slope(c, n):
    out = np.full(len(c), np.nan)
    x = np.arange(n) - (n - 1) / 2
    denom = (x ** 2).sum()
    for i in range(n - 1, len(c)):
        out[i] = (x * c[i - n + 1:i + 1]).sum() / denom
    return out


# ----------------------------------------------------------------------
# library
# ----------------------------------------------------------------------

def library(o, h, l, c, week_close_aligned) -> tuple[dict, dict]:
    """(signals {name: -1/0/+1 array}, continuous features {name: array})."""
    S, F = {}, {}
    atr14 = wilder(true_range(h, l, c), 14)
    F["atr_pct"] = atr14 / c

    for n in (5, 8, 10, 13, 20, 21, 30, 34, 50, 55, 89, 100, 144, 150, 200):
        s, e = sma(c, n), ema(c, n)
        S[f"cena>SMA{n}"] = sign_of(c - s)
        S[f"cena>EMA{n}"] = sign_of(c - e)
        F[f"dist_sma{n}"] = (c - s) / atr14
        S[f"SMA{n} roste"] = sign_of(s - shift(s, 5))

    for a, b in ((5, 20), (10, 30), (10, 50), (20, 50), (20, 100), (50, 100), (50, 200), (30, 100), (5, 50), (5, 10),
                 (8, 21), (9, 21), (12, 26), (13, 48), (21, 55), (50, 150), (100, 200)):
        S[f"SMA{a}xSMA{b}"] = sign_of(sma(c, a) - sma(c, b))
        S[f"EMA{a}xEMA{b}"] = sign_of(ema(c, a) - ema(c, b))

    for f_, s_, g in ((12, 26, 9), (8, 17, 9), (5, 35, 5), (19, 39, 9), (24, 52, 18)):
        macd = ema(c, f_) - ema(c, s_)
        sig = ema(np.nan_to_num(macd), g)
        S[f"MACD{f_}/{s_}/{g} nad signalem"] = sign_of(macd - sig)
        S[f"MACD{f_}/{s_} nad nulou"] = sign_of(macd)
        F[f"macd_{f_}_{s_}"] = (macd - sig) / atr14

    for n in (10, 20, 40, 55, 100):
        S[f"Donchian{n} stav"] = state_breakout(c, shift(rolling_max(h, n)), shift(rolling_min(l, n)))
        hi, lo = rolling_max(h, n), rolling_min(l, n)
        F[f"range_pos{n}"] = (c - lo) / np.where(hi - lo == 0, np.nan, hi - lo) - 0.5
        S[f"poloha v pasmu {n}"] = band(F[f"range_pos{n}"], -0.4, 0.4)

    for n in (7, 14, 21):
        pdi, mdi, adx = dmi(h, l, c, n)
        F[f"di_{n}"] = (pdi - mdi) / 100
        for thr in (15, 20, 25, 30):
            S[f"DMI{n} ADX>{thr}"] = np.where(adx > thr, sign_of(pdi - mdi), 0)

    for n in (14, 25, 50):
        days_hi = n - 1 - np.array([np.argmax(h[max(0, i - n + 1):i + 1]) if i >= n - 1 else 0
                                    for i in range(len(h))])
        days_lo = n - 1 - np.array([np.argmin(l[max(0, i - n + 1):i + 1]) if i >= n - 1 else 0 for i in range(len(l))])
        aroon_up, aroon_dn = 100 * (n - days_hi) / n, 100 * (n - days_lo) / n
        S[f"Aroon{n}"] = sign_of(aroon_up - aroon_dn)

    for st, mx in ((0.02, 0.2), (0.01, 0.1), (0.03, 0.3), (0.015, 0.15)):
        S[f"PSAR {st}/{mx}"] = psar(h, l, st, mx)

    for n, m in ((10, 2), (10, 3), (14, 2), (14, 3), (20, 4), (7, 3)):
        S[f"Supertrend {n}/{m}"] = supertrend(h, l, c, n, m)

    tenkan = (rolling_max(h, 9) + rolling_min(l, 9)) / 2
    kijun = (rolling_max(h, 26) + rolling_min(l, 26)) / 2
    span_a, span_b = shift((tenkan + kijun) / 2, 26), shift((rolling_max(h, 52) + rolling_min(l, 52)) / 2, 26)
    top, bottom = np.fmax(span_a, span_b), np.fmin(span_a, span_b)
    S["Ichimoku nad mrakem"] = np.where(c > top, 1, np.where(c < bottom, -1, 0))
    S["Ichimoku tenkan x kijun"] = sign_of(tenkan - kijun)

    for n in (1, 2, 3, 5, 10, 20, 40, 60, 80, 120, 250):
        roc = (c - shift(c, n)) / (atr14 * math.sqrt(n))
        S[f"ROC{n}"] = sign_of(roc)
        F[f"roc{n}"] = roc

    for k in (1.0, 1.5, 2.0, 2.5):
        e20 = ema(c, 20)
        S[f"Keltner20 {k} pruraz"] = np.where(c > e20 + k * atr14, 1, np.where(c < e20 - k * atr14, -1, 0))

    for n in (5, 10, 20, 30, 50):
        sl = linreg_slope(c, n) / atr14
        S[f"regrese{n} sklon"] = sign_of(sl)
        F[f"slope{n}"] = sl

    # oscillators - mean-reversion form (+1 oversold); the search also tests the opposite sign
    for n in (2, 3, 4, 5, 7, 9, 14, 21, 28):
        r = rsi(c, n)
        F[f"rsi{n}"] = (r - 50) / 50
        for lo, hi in ((30, 70), (20, 80), (10, 90)):
            S[f"RSI{n} {lo}/{hi}"] = band(r, lo, hi)
        if n in (7, 14, 21):
            S[f"RSI{n} nad 50"] = sign_of(r - 50)
    for n in (5, 9, 14, 21):
        k_ = 100 * (c - rolling_min(l, n)) / np.where(rolling_max(h, n) - rolling_min(l, n) == 0, np.nan,
                                                      rolling_max(h, n) - rolling_min(l, n))
        F[f"stoch{n}"] = (k_ - 50) / 50
        d_ = sma(np.nan_to_num(k_, nan=50), 3)
        S[f"Stochastic{n} 20/80"] = band(d_, 20, 80)
        S[f"Stochastic{n} 10/90"] = band(d_, 10, 90)
        S[f"Williams%R{n} -80/-20"] = band(k_, 20, 80)
        S[f"Williams%R{n} -90/-10"] = band(k_, 10, 90)
    for n in (14, 20, 40):
        tp = (h + l + c) / 3
        md = sma(np.abs(tp - sma(tp, n)), n)
        cci = (tp - sma(tp, n)) / (0.015 * np.where(md == 0, np.nan, md))
        F[f"cci{n}"] = cci / 200
        for thr in (100, 200):
            S[f"CCI{n} +-{thr}"] = band(cci, -thr, thr)
    for n, k in ((20, 2.0), (20, 1.5), (10, 2.0), (50, 2.0), (20, 2.5), (10, 1.5), (10, 2.5), (50, 1.5), (50, 2.5)):
        m, sd = sma(c, n), np.sqrt(np.maximum(sma(c * c, n) - sma(c, n) ** 2, 0))
        pb = (c - (m - k * sd)) / np.where(sd == 0, np.nan, 2 * k * sd)
        F[f"bb{n}_{k}"] = pb - 0.5
        S[f"Bollinger{n}/{k}"] = band(pb, 0.0, 1.0)
    for k in (1.5, 2.0, 3.0):
        S[f"od SMA20 > {k} ATR"] = band((c - sma(c, 20)) / atr14, -k, k)
    up = np.concatenate([[0], (np.diff(c) > 0).astype(float)])
    for k in (2, 3, 4, 5, 6):
        run_up = np.array([np.all(up[max(0, i - k + 1):i + 1] == 1) for i in range(len(c))])
        run_dn = np.array([np.all(up[max(0, i - k + 1):i + 1] == 0) for i in range(len(c))])
        S[f"{k} dny za sebou"] = np.where(run_dn, 1, np.where(run_up, -1, 0))

    ha_c = (o + h + l + c) / 4
    ha_o = np.zeros(len(c))
    ha_o[0] = o[0]
    for i in range(1, len(c)):
        ha_o[i] = (ha_o[i - 1] + ha_c[i - 1]) / 2
    S["Heikin-Ashi barva"] = sign_of(ha_c - ha_o)
    S["Heikin-Ashi 2x stejne"] = np.where((ha_c > ha_o) & (shift(ha_c) > shift(ha_o)), 1,
                                          np.where((ha_c < ha_o) & (shift(ha_c) < shift(ha_o)), -1, 0))
    po, pc = shift(o), shift(c)
    S["pohlceni (engulfing)"] = np.where((c > o) & (pc < po) & (c >= po) & (o <= pc), 1,
                                         np.where((c < o) & (pc > po) & (c <= po) & (o >= pc), -1, 0))
    body = np.abs(c - o)
    rng = np.where(h - l == 0, np.nan, h - l)
    S["pin bar"] = np.where((np.fmin(o, c) - l > 2 * body) & (body / rng < 0.3), 1,
                            np.where((h - np.fmax(o, c) > 2 * body) & (body / rng < 0.3), -1, 0))
    inside = (shift(h) < shift(h, 2)) & (shift(l) > shift(l, 2))
    S["inside bar pruraz"] = np.where(inside & (c > shift(h)), 1, np.where(inside & (c < shift(l)), -1, 0))
    pp = (shift(h) + shift(l) + shift(c)) / 3
    S["nad dennim pivotem"] = sign_of(c - pp)

    # weekly chart (completed weeks + the current price)
    for n in (10, 20, 50):
        S[f"tyden: cena>SMA{n}"] = sign_of(c - week_close_aligned[f"sma{n}"])
    S["tyden: MACD12/26 nad signalem"] = week_close_aligned["macd"]
    S["tyden: ROC4"] = sign_of(c - week_close_aligned["close4"])
    S["tyden: ROC13"] = sign_of(c - week_close_aligned["close13"])
    S["tyden: nad pivotem"] = sign_of(c - week_close_aligned["pivot"])
    S["tyden: RSI14 nad 50"] = week_close_aligned["rsi"]
    S["tyden: Donchian10 stav"] = week_close_aligned["donchian"]
    return S, F


def weekly(days: list, c: np.ndarray, h: np.ndarray, l: np.ndarray) -> dict:
    keys = [tuple(d.isocalendar()[:2]) for d in days]
    wk_close, wk_h, wk_l, order = {}, {}, {}, []
    for k, ci, hi, li in zip(keys, c, h, l):
        if k not in wk_close:
            order.append(k)
            wk_h[k], wk_l[k] = hi, li
        wk_close[k] = ci
        wk_h[k], wk_l[k] = max(wk_h[k], hi), min(wk_l[k], li)
    closes = np.array([wk_close[k] for k in order])
    index = {k: i for i, k in enumerate(order)}
    sm = {n: sma(closes, n) for n in (10, 20, 50)}
    macd = ema(closes, 12) - ema(closes, 26)
    macd_sig = sign_of(macd - ema(np.nan_to_num(macd), 9))
    wrsi = sign_of(rsi(closes, 14) - 50)
    whi = np.array([wk_h[k] for k in order])
    wlo = np.array([wk_l[k] for k in order])
    wdon = state_breakout(closes, shift(rolling_max(whi, 10)), shift(rolling_min(wlo, 10)))
    out = {f"sma{n}": np.full(len(c), np.nan) for n in (10, 20, 50)}
    out.update({"macd": np.zeros(len(c)), "close4": np.full(len(c), np.nan), "close13": np.full(len(c), np.nan),
                "pivot": np.full(len(c), np.nan), "rsi": np.zeros(len(c)), "donchian": np.zeros(len(c))})
    for i, k in enumerate(keys):
        w = index[k] - 1            # last COMPLETED week
        if w < 0:
            continue
        for n in (10, 20, 50):
            out[f"sma{n}"][i] = sm[n][w]
        out["macd"][i] = macd_sig[w]
        out["rsi"][i] = wrsi[w]
        out["donchian"][i] = wdon[w]
        out["close4"][i] = closes[w - 3] if w >= 3 else np.nan
        out["close13"][i] = closes[w - 12] if w >= 12 else np.nan
        pk = order[w]
        out["pivot"][i] = (wk_h[pk] + wk_l[pk] + wk_close[pk]) / 3
    return out


# ----------------------------------------------------------------------
# panel
# ----------------------------------------------------------------------

def build_panel() -> dict:
    symbols = parse_symbols(None)
    fund_rows = {(r["symbol"], r["day"]): r for r in pickle.loads(SIGNALS_FILE.read_bytes())}
    per_pair, all_days = {}, set()

    for s in symbols:
        bars, _ = stitched_daily(s)
        days = [trading_date(b.ts) for b in bars]
        o, h, l, c = (np.array([getattr(b, k) for b in bars]) for k in ("mo", "mh", "ml", "mc"))
        ts = np.array([b.ts for b in bars])
        S, F = library(o, h, l, c, weekly(days, c, h, l))
        inst = get_instrument(s)
        cost = (SPREAD_PIPS[s] + SLIPPAGE_PIPS) * inst.pip
        atr14 = wilder(true_range(h, l, c), 14)
        gap = np.concatenate([[False], np.diff(ts) > MAX_GAP_DAYS * 86400])
        carry = np.array([fund_rows.get((s, d), {}).get("CARRY") or np.nan for d in days], dtype=float)
        targets = {}
        for hz in HORIZONS:
            fwd = np.full(len(c), np.nan)
            fwd[:-hz] = c[hz:] - c[:-hz]
            span = np.full(len(c), np.nan)
            span[:-hz] = (ts[hz:] - ts[:-hz]) / 86400
            bad = np.array([gap[i + 1:i + hz + 1].any() if i + hz < len(c) else True for i in range(len(c))])
            fin = np.nan_to_num(carry) / 100 * c * span / 365
            mark = FINANCING_MARKUP / 100 * c * span / 365
            long_ = (fwd - cost + fin - mark) / atr14
            short = (-fwd - cost - fin - mark) / atr14
            gross = fwd / atr14
            for arr in (long_, short, gross):
                arr[bad] = np.nan
            targets[hz] = (long_, short, gross)
        fund = {k: np.array([fund_rows.get((s, d), {}).get(k) if fund_rows.get((s, d), {}).get(k) is not None
                             else np.nan for d in days], dtype=float)
                for k in ("CARRY", "RATES_20D", "COT_Z", "RISK_VIX_1W", "POLICY_TREND", "LONG_RATES_20D")}
        per_pair[s] = {"days": days, "S": S, "F": F, "targets": targets, "fund": fund}
        all_days.update(days)
        print(f"{s}: {len(days)} dni, {len(S)} signalu", flush=True)

    dates = sorted(all_days)
    pos = {d: i for i, d in enumerate(dates)}
    P, D = len(symbols), len(dates)

    def matrix(get):
        m = np.full((P, D), np.nan)
        for p, s in enumerate(symbols):
            idx = [pos[d] for d in per_pair[s]["days"]]
            m[p, idx] = get(per_pair[s])
        return m

    names = list(per_pair[symbols[0]]["S"])
    fnames = list(per_pair[symbols[0]]["F"])
    panel = {"symbols": symbols, "dates": dates,
             "S": {n: matrix(lambda x, n=n: x["S"][n]) for n in names},
             "F": {n: matrix(lambda x, n=n: x["F"][n]) for n in fnames},
             "fund": {k: matrix(lambda x, k=k: x["fund"][k]) for k in per_pair[symbols[0]]["fund"]},
             "T": {hz: tuple(matrix(lambda x, hz=hz, j=j: x["targets"][hz][j]) for j in range(3)) for hz in HORIZONS}}
    return panel


def fundamental_filters(panel: dict) -> dict:
    f = panel["fund"]
    carry, rates, cot, risk, policy = (np.nan_to_num(f[k]) for k in ("CARRY", "RATES_20D", "COT_Z", "RISK_VIX_1W",
                                                                     "POLICY_TREND"))
    clusters = [sign_of(carry), sign_of(rates), sign_of(risk), sign_of(policy)]
    return {
        "bez filtru": None,
        "+carry": sign_of(carry),
        "+sazby 20d": sign_of(rates),
        "+COT ne proti": np.where(np.abs(cot) < 1.5, 0, -sign_of(cot)),   # crowded side = against
        "+riziko VIX": sign_of(risk),
        "+fundamenty (>=1 pro, 0 proti)": np.stack(clusters),
    }


_COLS: dict = {}


def _columns(dates: list, period, hz: int) -> list:
    """Every hz-th trading day of the period whose exit is still inside it."""
    key = (id(dates), period, hz)
    if key not in _COLS:
        first, last = period
        _COLS[key] = [i for i, d in enumerate(dates) if first <= d <= last][:-hz or None][::hz]
    return _COLS[key]


def evaluate(signal: np.ndarray, hz: int, period, panel, filt=None, sign=1.0) -> dict:
    long_, short, gross = panel["T"][hz]
    dates = panel["dates"]
    sig = signal * sign

    if filt is not None:
        if filt.ndim == 3:              # several clusters: >= 1 agrees, none against
            agree = (filt == sig[None]).sum(axis=0)
            against = (filt == -sig[None]).sum(axis=0)
            sig = np.where((agree >= 1) & (against == 0), sig, 0)
        else:
            sig = np.where(filt == 0, sig, np.where(filt == sig, sig, 0))

    cols = _columns(dates, period, hz)
    s = sig[:, cols]
    net = np.where(s > 0, long_[:, cols], np.where(s < 0, short[:, cols], np.nan))
    gr = np.where(s != 0, s * gross[:, cols], np.nan)
    net[np.isnan(gr)] = np.nan
    trades = int(np.sum(~np.isnan(net)))

    if trades < 50:
        return {"trades": trades}

    with np.errstate(all="ignore"):
        day = np.nanmean(net, axis=0)
        day_g = np.nanmean(gr, axis=0)
    day, day_g = day[~np.isnan(day)], day_g[~np.isnan(day_g)]
    t = day.mean() / (day.std(ddof=1) / math.sqrt(len(day))) if day.std() > 0 else 0.0
    return {"trades": trades, "win": float(np.sum(net > 0) / trades),
            "e": float(np.nanmean(net)), "t": float(t), "gross": float(np.nanmean(gr)), "days": len(day)}


def search(panel: dict) -> list:
    filters = fundamental_filters(panel)
    results = []
    first, last = PERIODS["CHOOSE"]
    middle = first + (last - first) / 2

    for name, sig in panel["S"].items():
        sig = np.nan_to_num(sig)
        for fname, filt in filters.items():
            for hz in HORIZONS:
                for sign in (1.0, -1.0):
                    r = evaluate(sig, hz, PERIODS["CHOOSE"], panel, filt, sign)
                    if r.get("e") is None:
                        continue
                    a = evaluate(sig, hz, (first, middle), panel, filt, sign)
                    b = evaluate(sig, hz, (middle + timedelta(days=1), last), panel, filt, sign)
                    results.append({"name": name, "filter": fname, "hz": hz, "sign": sign, "CHOOSE": r,
                                    "halves": (a.get("e"), b.get("e"))})
    return results


def check(panel, item) -> dict:
    filters = fundamental_filters(panel)
    sig = np.nan_to_num(panel["S"][item["name"]]) if item["name"] in panel["S"] else item["signal"]
    return {p: evaluate(sig, item["hz"], PERIODS[p], panel, filters[item["filter"]], item["sign"])
            for p in ("EARLY", "HOLDOUT")}


def null_pass_rate(panel, n=300, seed=1) -> float:
    """Share of RANDOM signals that pass the same out-of-sample check."""
    rng = np.random.default_rng(seed)
    shape = panel["S"][next(iter(panel["S"]))].shape
    passed = 0
    for _ in range(n):
        sig = rng.choice([-1.0, 1.0], size=shape)
        hz = int(rng.choice(HORIZONS))
        res = {p: evaluate(sig, hz, PERIODS[p], panel) for p in ("EARLY", "HOLDOUT")}
        passed += _passes(res)
    return passed / n


def _passes(res: dict) -> bool:
    return all((res[p].get("e") or -1) > 0 for p in ("EARLY", "HOLDOUT")) and \
        sum(res[p].get("t") or 0 for p in ("EARLY", "HOLDOUT")) / math.sqrt(2) >= 2.0


# ----------------------------------------------------------------------
# walk-forward machine learning (numpy logistic regression)
# ----------------------------------------------------------------------

def logistic(X, y, l2=1.0, iters=300, lr=0.5):
    w = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-np.clip(X @ w, -30, 30)))
        g = X.T @ (p - y) / len(y) + l2 * w / len(y)
        w -= lr * g
    return w


def ml_walk_forward(panel: dict) -> dict:
    hz = 5
    names = list(panel["F"]) + list(panel["fund"])
    mats = [panel["F"][n] for n in panel["F"]] + [np.nan_to_num(panel["fund"][k]) for k in panel["fund"]]
    X3 = np.stack(mats, axis=-1)                       # pairs x days x features
    long_, short, gross = panel["T"][hz]
    dates = np.array(panel["dates"])
    years = np.array([d.year for d in dates])
    results = {}
    thresholds = (0.0, 0.02, 0.05)
    collected = {thr: ([], [], {}) for thr in thresholds}

    for year in range(2016, 2027):
        train_cols = np.where(years < year)[0][:-hz]
        test_cols = np.where(years == year)[0][::hz]
        Xtr = X3[:, train_cols].reshape(-1, X3.shape[2])
        ytr = gross[:, train_cols].reshape(-1)
        ok = ~np.isnan(ytr) & ~np.isnan(Xtr).any(axis=1)
        Xtr, ytr = Xtr[ok], (ytr[ok] > 0).astype(float)
        # trained before `year`; stop the training targets before the year starts (no overlap)
        mu, sd = Xtr.mean(axis=0), Xtr.std(axis=0) + 1e-9
        Xtr = np.clip((Xtr - mu) / sd, -5, 5)
        w = logistic(np.column_stack([np.ones(len(Xtr)), Xtr]), ytr)
        Xte = X3[:, test_cols]
        flat = Xte.reshape(-1, Xte.shape[2])
        okt = ~np.isnan(flat).any(axis=1)
        prob = np.full(len(flat), np.nan)
        z = np.clip((flat[okt] - mu) / sd, -5, 5)
        prob[okt] = 1 / (1 + np.exp(-(np.column_stack([np.ones(okt.sum()), z]) @ w)))
        prob = prob.reshape(Xte.shape[:2])
        for thr in thresholds:
            all_net, all_gross, per_year = collected[thr]
            sig = np.where(prob > 0.5 + thr, 1, np.where(prob < 0.5 - thr, -1, 0))
            net = np.where(sig > 0, long_[:, test_cols], np.where(sig < 0, short[:, test_cols], np.nan))
            gr = np.where(sig != 0, sig * gross[:, test_cols], np.nan)
            net[np.isnan(gr)] = np.nan
            all_net.append(net)
            all_gross.append(gr)
            if np.sum(~np.isnan(net)):
                per_year[year] = (float(np.nanmean(net)), float(np.sum(net > 0) / np.sum(~np.isnan(net))),
                                  int(np.sum(~np.isnan(net))))

    for thr in thresholds:
        all_net, all_gross, per_year = collected[thr]
        net, gr = np.concatenate(all_net, axis=1), np.concatenate(all_gross, axis=1)
        with np.errstate(all="ignore"):
            day = np.nanmean(net, axis=0)
        day = day[~np.isnan(day)]
        results[thr] = {"trades": int(np.sum(~np.isnan(net))), "win": float(np.sum(net > 0) / np.sum(~np.isnan(net))),
                        "e": float(np.nanmean(net)), "gross": float(np.nanmean(gr)),
                        "t": float(day.mean() / (day.std(ddof=1) / math.sqrt(len(day)))), "years": per_year}
    return results


# ----------------------------------------------------------------------
# baseline: the V7.8.0 model's direction in the same measurement
# ----------------------------------------------------------------------

def model_signal(panel: dict) -> np.ndarray:
    research = PROJECT_ROOT / "data" / "research"
    sig = np.zeros((len(panel["symbols"]), len(panel["dates"])))
    pos = {d: i for i, d in enumerate(panel["dates"])}
    sym = {s: i for i, s in enumerate(panel["symbols"])}
    for name in ("decisions_early.pkl", "decisions_fxcm.pkl", "decisions_dukascopy.pkl"):
        path = research / name
        if not path.exists():
            continue
        for d in pickle.loads(path.read_bytes())["variants"]["MODEL"]["decisions"]:
            day = trading_date(d["t"] - 1)          # decision at an H4 close belongs to that trading day
            if day in pos:
                sig[sym[d["symbol"]], pos[day]] = 1.0 if d["direction"] == "BUY" else -1.0
    return sig


# ----------------------------------------------------------------------
# report
# ----------------------------------------------------------------------

def _f(x, fmt="+.3f"):
    return "-" if x is None else format(x, fmt)


def _cell(r: dict) -> str:
    return f"{r.get('trades', 0)} | {_f(r.get('win'), '.1%')} | {_f(r.get('e'))} | {_f(r.get('t'), '+.1f')}"


def main() -> int:
    started = time.monotonic()
    panel = build_panel()
    results = search(panel)
    tested = len(results)
    ranked = sorted([r for r in results if r["CHOOSE"]["trades"] >= 300 and all((x or -1) > 0 for x in r["halves"])],
                    key=lambda r: -r["CHOOSE"]["t"])
    top = ranked[:30]

    for item in top:
        item.update(check(panel, item))

    survivors = [r for r in top if _passes({p: r[p] for p in ("EARLY", "HOLDOUT")})]
    null_rate = null_pass_rate(panel)
    # ensemble of the 20 best discovery rules: sum of their (filtered, signed) votes
    filters = fundamental_filters(panel)
    votes = np.zeros_like(np.nan_to_num(panel["S"][top[0]["name"]]))
    for r in top[:20]:
        s = np.nan_to_num(panel["S"][r["name"]]) * r["sign"]
        f = filters[r["filter"]]
        if f is not None:
            if f.ndim == 3:
                agree, against = (f == s[None]).sum(axis=0), (f == -s[None]).sum(axis=0)
                s = np.where((agree >= 1) & (against == 0), s, 0)
            else:
                s = np.where(f == 0, s, np.where(f == s, s, 0))
        votes += s
    ens = {p: evaluate(sign_of(np.where(np.abs(votes) >= 5, votes, 0)), 5, PERIODS[p], panel)
           for p in ("CHOOSE", "EARLY", "HOLDOUT")}
    ml = ml_walk_forward(panel)
    base_sig = model_signal(panel)
    base = {hz: {p: evaluate(base_sig, hz, PERIODS[p], panel) for p in ("CHOOSE", "EARLY", "HOLDOUT")}
            for hz in HORIZONS}

    out = ["# Vytezovani strategii: stovky indikatoru x nastaveni x fundamenty", "",
           f"_{len(panel['S'])} nastaveni indikatoru x 6 fundamentalnich filtru x 2 smery x drzeni 1/3/5 dni = "
           f"**{tested} otestovanych pravidel**; 12 paru; vyber jen na 2016-09..2021-12; kontrola na 2014-16 a "
           f"2022-26. E = prumer na obchod v ATR(D1) po nakladech a swapu; uspesnost = podil ziskovych obchodu; "
           f"t > 2 = nepravdepodobne nahoda._", "",
           "## Vychozi stav: soucasny model V7.8.0 ve stejnem mereni", "",
           "| drzeni | 2016-21 obchodu | uspesnost | E | t | 2014-16 | | | | 2022-26 | | | |", "|---|" + "---|" * 12]
    for hz in HORIZONS:
        b = base[hz]
        out.append(f"| {hz} d | {_cell(b['CHOOSE'])} | {_cell(b['EARLY'])} | {_cell(b['HOLDOUT'])} |")

    out += ["", "## 30 nejlepsich pravidel z obdobi vyberu a jak dopadla potom", "",
            "| indikator | fundamentalni filtr | smer | drzeni | 2016-21 obchodu | uspesnost | E | t | 2014-16 obchodu | "
            "uspesnost | E | t | 2022-26 obchodu | uspesnost | E | t | prosel |", "|---|" + "---|" * 16]
    for r in top:
        ok = "**ANO**" if r in survivors else "ne"
        out.append(f"| {r['name']} | {r['filter']} | {'podle signalu' if r['sign'] > 0 else 'proti signalu'} | "
                   f"{r['hz']} d | {_cell(r['CHOOSE'])} | {_cell(r['EARLY'])} | {_cell(r['HOLDOUT'])} | {ok} |")

    out += ["", f"**Proslo kontrolou v obou dalsich obdobich: {len(survivors)} z 30.** Nahodne signaly projdou stejnou "
            f"kontrolou v {null_rate:.1%} pripadu, tj. cekane cislo cistou nahodou je {30 * null_rate:.1f} z 30.", "",
            "Pozn.: 2014-16 obsahuje sok SNB 15. 1. 2015 (EUR/CHF -30 % behem minut, ~40 ATR na jeden obchod); "
            "pravidla, ktera tehdy drzela CHF kratce, tam maji velky zaporny prumer.", "",
            "## Kombinace 20 nejlepsich (hlasovani, drzeni 5 dni)", "",
            "| obdobi | obchodu | uspesnost | E | t |", "|---|---|---|---|---|"]
    for p, label in (("CHOOSE", "2016-21 (vyber)"), ("EARLY", "2014-16"), ("HOLDOUT", "2022-26")):
        out.append(f"| {label} | {_cell(ens[p])} |")

    out += ["", "## Strojove uceni (logisticka regrese ze vsech indikatoru a fundamentu, uceni vzdy jen na minulych "
            "letech, drzeni 5 dni)", "",
            "| prah jistoty | obchodu | uspesnost | E | hruby smer | t |", "|---|---|---|---|---|---|"]
    for thr, r in ml.items():
        out.append(f"| {50 + thr * 100:.0f} % | {r['trades']} | {r['win']:.1%} | {r['e']:+.3f} | {r['gross']:+.3f} | "
                   f"{r['t']:+.1f} |")
    years = ml[0.02]["years"]
    out += ["", "Po letech (prah 52 %): " + ", ".join(f"{y}: {v[1]:.0%} / {v[0]:+.3f}" for y, v in years.items())]
    out += ["", f"_vypocet {time.monotonic() - started:.0f} s_"]
    (PROJECT_ROOT / "docs" / "STRATEGIE.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    (PROJECT_ROOT / "data" / "research" / "strategy_mining.pkl").write_bytes(
        pickle.dumps({"top": top, "survivors": survivors, "ml": ml, "base": base, "ens": ens, "null": null_rate,
                      "tested": tested}))
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
