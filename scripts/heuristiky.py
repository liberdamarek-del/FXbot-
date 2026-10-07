"""Heuristic model (user's request 2026-10-07, R-038): a separate information and prediction layer next to the main
model. It never assumes its own conclusions are true: every heuristic is a measurable hypothesis that is tested,
compared, degraded, improved and retired by data.

    python scripts/heuristiky.py prepocet          # rebuild the rule registry from the FXCM history (weekly, Saturday)
    python scripts/heuristiky.py zive              # live step alone (downloads prices; normally from aktualizace.py)
    python scripts/heuristiky.py overeni           # verify the prediction ledger (hash chain, one evaluation each)
    python scripts/heuristiky.py pravidlo <ID>     # one rule's card

Rules. A template (e.g. "RSI(2) < 10 -> LONG") is applied to each of the 12 pairs on two timeframes: 1D bars (New York
17:00 close, horizon 5 days) and 4H bars (New York aligned 17-21-01-05-09-13, horizon 24 h). A rule fires at a bar close
when its condition holds; it then predicts the direction for the horizon. A rule has at most one open prediction at a
time (history and live alike), so its samples never overlap. Result = the direction at the horizon after costs
(spread + slippage of the pair): SUCCESS when the net return is > 0.

Evidence (no look-ahead: indicators use closed bars, rates have the model's two-month lag, VIX the previous day):
  * in-sample 2012-2018 and out-of-sample 2019 -> (the template and its direction were set before looking at either);
  * walk-forward by years (the rule is "on" in a year only when its earlier years were positive);
  * four time blocks, volatility and trend regimes, neighbouring parameters, the other pairs;
  * test against random entries (same pair, period, direction, sample size): z-test for every rule, Monte Carlo
    permutation + bootstrap interval for the candidates; Benjamini-Hochberg false discovery rate across all rules.
Statuses: AKTIVNÍ, SLABÁ, NEOVĚŘENÁ, NEFUNKČNÍ, OVERFIT/NESTABILNÍ (rules in `classify`). Live results can only degrade a
rule (live significantly worse than its out-of-sample record).

Two probabilities, never mixed: STATISTICKÁ PRAVDĚPODOBNOST = the rule's out-of-sample win rate (history);
HEURISTICKÝ ODHAD = a subjective rule of thumb (confluence of the families: 50 % + 5 points per family that agrees
minus per family that disagrees, 30-80 %) that uses no history. Both are checked against reality (calibration).

Live predictions are append-only (learning/heuristiky/predikce/<day>.jsonl, a hash chain); each is evaluated once after its
horizon (vyhodnoceni/*.jsonl). Nothing is edited back. The heuristic layer is information only: it never changes the
main model's signals; a heuristic can reach the model only as an experiment of the walk-forward gate.
"""

import gzip
import hashlib
import json
import math
import sys
import time
import warnings
from bisect import bisect_left
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import indikatory as K  # noqa: E402
from src.instruments import DEFAULT_ACTIVE, get_instrument  # noqa: E402

UTC = timezone.utc
NY = ZoneInfo("America/New_York")
DIR = PROJECT_ROOT / "learning" / "heuristiky"
REGISTRY = DIR / "pravidla.json.gz"
STATUS_LOG = DIR / "stavy_log.jsonl"
LIVE_STATE = DIR / "zive.json"
PRED_DIR = DIR / "predikce"
EVAL_DIR = DIR / "vyhodnoceni"
REPORT = PROJECT_ROOT / "docs" / "heuristiky_vysledky.md"

# timeframe: horizon in bars, Czech label, longest calendar span of the horizon, latest live recording after the close
TFS = {"1D": {"H": 5, "label": "5 dní", "span": 12 * 86400, "delay": 6 * 3600, "min_hours": 18},
       "4H": {"H": 6, "label": "24 h", "span": 4 * 86400, "delay": 2 * 3600, "min_hours": 3}}
IS_END_YEAR = 2018
BLOCKS = ((2012, 2015), (2016, 2018), (2019, 2022), (2023, 2026))
WF_FIRST = 2016
WARM = 250                      # bars before the first prediction (indicator warm-up, ATR rank window)
MIN_N = 30                      # predictions in-sample and out-of-sample before a rule is judged
TARGET_K = 0.5                  # target / threshold = 0.5 x ATR14 x sqrt(horizon) from the entry
FDR_Q = 0.10
PERM_DRAWS = 2000
LIVE_MIN_N = 20                 # live predictions before live results may degrade a rule
LIVE_BARS = {"1D": 1100, "4H": 3200}   # bars kept for the live masks (indicator warm-up included)
STATUSES = ("AKTIVNÍ", "SLABÁ", "NEOVĚŘENÁ", "NEFUNKČNÍ", "OVERFIT/NESTABILNÍ")
ISSUING = ("AKTIVNÍ", "SLABÁ", "NEOVĚŘENÁ")         # retired rules (NEFUNKČNÍ, OVERFIT) issue no live predictions
TYP_CZ = {"trend": "trend a struktura", "podpora_odpor": "podpora a odpor", "max_min": "předchozí maxima a minima",
          "volatilita": "volatilita (ATR)", "oscilatory": "oscilátory (RSI, MACD, Bollinger, stochastic)",
          "momentum": "momentum", "price_action": "price action (svíčky)", "cas": "čas", "fundament": "fundamenty",
          "udalosti": "reakce na události", "korelace": "korelace mezi páry", "fund_tech": "fundament + technika",
          "kombinace": "kombinace (tvoje příklady)"}
RISK_SCORE = {"AUD": 1, "NZD": 1, "JPY": -1, "CHF": -1}        # risk currencies vs safe havens (a-priori)
CURRENCIES = ("USD", "EUR", "JPY", "GBP", "CHF", "AUD", "CAD", "NZD")


# ----------------------------------------------------------------------
# bars: New York aligned 1D / 4H from hourly bars (the same function for the FXCM history and the live Yahoo prices)
# ----------------------------------------------------------------------

def _ny_parts(ts: np.ndarray) -> tuple[list, np.ndarray]:
    """Trading date (New York 17:00 close) and the hour of the trading day (0 = 17:00 New York) of hourly opens."""
    days, hours = [], np.empty(len(ts), int)
    cache: dict = {}
    for k, t in enumerate(ts.tolist()):
        key = t // 3600
        if key not in cache:
            loc = datetime.fromtimestamp(key * 3600, tz=NY)
            shifted = loc + timedelta(hours=7)
            cache[key] = (shifted.date(), (loc.hour - 17) % 24)
        d, hr = cache[key]
        days.append(d)
        hours[k] = hr
    return days, hours


def bar_end(day: date, tf: str, bucket: int) -> int:
    """Scheduled end of a bar: 17:00 New York of the trading day (1D) or of the 4-hour bucket."""
    start = datetime(day.year, day.month, day.day, 17, tzinfo=NY) - timedelta(days=1)
    hours = 24 if tf == "1D" else 4 * (bucket + 1)
    return int((start + timedelta(hours=hours)).timestamp())


def bars_tf(hb: dict, tf: str, now: int | None = None) -> dict:
    """Bars of the timeframe from hourly bars {ts, o, h, l, c}; weekend trading days dropped, bars with too few hours
    dropped (except the last), only complete bars (scheduled end <= now) when now is given."""
    ts = np.asarray(hb["ts"], np.int64)
    days, hours = _ny_parts(ts)
    bucket = hours // 4 if tf == "4H" else np.zeros(len(ts), int)
    keys = [(d, int(b)) for d, b in zip(days, bucket)]
    idx = [0] + [i for i in range(1, len(ts)) if keys[i] != keys[i - 1]]
    idx = np.array(idx, np.int64)
    ends = np.append(idx[1:], len(ts)) - 1
    cnt = ends - idx + 1
    out = {"o": np.asarray(hb["o"], float)[idx], "h": np.maximum.reduceat(np.asarray(hb["h"], float), idx),
           "l": np.minimum.reduceat(np.asarray(hb["l"], float), idx), "c": np.asarray(hb["c"], float)[ends],
           "ts": ts[idx], "last_ts": ts[ends]}
    out["day"] = [keys[i][0] for i in idx]
    out["bucket"] = np.array([keys[i][1] for i in idx])
    out["end_ts"] = np.array([bar_end(d, tf, int(b)) for d, b in zip(out["day"], out["bucket"])], np.int64)
    keep = np.array([d.weekday() < 5 for d in out["day"]])
    keep &= (cnt >= TFS[tf]["min_hours"]) | (np.arange(len(idx)) == len(idx) - 1)
    if now is not None:
        keep &= out["end_ts"] <= now
        last = np.flatnonzero(keep)
        if len(last) and out["last_ts"][last[-1]] + 3600 < out["end_ts"][last[-1]]:
            keep[last[-1]] = False                              # its last hour is not in the data yet
    return {k: ([x for x, m in zip(v, keep) if m] if isinstance(v, list) else v[keep]) for k, v in out.items()}


# ----------------------------------------------------------------------
# context: indicators and point-in-time fundamentals of one pair on one timeframe
# ----------------------------------------------------------------------

class Ctx:
    def __init__(self, pair: str, tf: str, bars: dict, aux: dict):
        self.pair, self.tf, self.bars = pair, tf, bars
        self.H = TFS[tf]["H"]
        self.o, self.h, self.l, self.c = (np.asarray(bars[k], float) for k in "ohlc")
        self.n = len(self.c)
        self.b = K.Builder(bars)
        self.atr = self.b.ind("atr", 14)
        self.day = bars["day"]
        self.aux = aux
        inst = get_instrument(pair)
        self.base, self.quote, self.pip = inst.base, inst.quote, inst.pip

    def ind(self, name: str, *args):
        return self.b.ind(name, *args)


def _nan_false(x) -> np.ndarray:
    with np.errstate(invalid="ignore"):
        return np.nan_to_num(np.asarray(x, float), nan=0).astype(bool)


def _sh(x, k=1):
    x = np.asarray(x, float)
    return x.copy() if k == 0 else K.shift(x, k)


def _rmax(x, n):
    return K.rolling_max(np.asarray(x, float), n)


def _rmin(x, n):
    return K.rolling_min(np.asarray(x, float), n)


def risk_sign(pair: str) -> int:
    b, q = pair.split("/")
    return int(np.sign(RISK_SCORE.get(b, 0) - RISK_SCORE.get(q, 0)))


def _period_groups(x: Ctx) -> np.ndarray:
    """Group index of the previous-period levels: ISO week for 1D bars, trading day for 4H bars."""
    keys = [d.isocalendar()[:2] for d in x.day] if x.tf == "1D" else list(x.day)
    g = np.zeros(x.n, int)
    for i in range(1, x.n):
        g[i] = g[i - 1] + (keys[i] != keys[i - 1])
    return g


def _prev_period(x: Ctx) -> tuple[np.ndarray, np.ndarray]:
    g = _period_groups(x)
    m = g.max() + 1 if x.n else 0
    hi = np.full(m, np.nan)
    lo = np.full(m, np.nan)
    np.fmax.at(hi, g, x.h)
    np.fmin.at(lo, g, x.l)
    ph = np.where(g > 0, hi[np.maximum(g - 1, 0)], np.nan)
    pl = np.where(g > 0, lo[np.maximum(g - 1, 0)], np.nan)
    return ph, pl


def _down_before(x: Ctx, side: int) -> np.ndarray:
    """A move against the side over the three bars before (the context of a reversal pattern)."""
    c1, c4 = _sh(x.c, 1), _sh(x.c, 4)
    return _nan_false(c1 < c4) if side > 0 else _nan_false(c1 > c4)


# ----------------------------------------------------------------------
# template library: (key, typ, logic, timeframes, variants, neighbour mode, mask(x, side, *p), text(side, *p))
# ----------------------------------------------------------------------

def m_tr_ma(x, s, n):
    m = x.ind("SMA", n)
    up = m > _sh(m, 5)
    return _nan_false((x.c > m) & up) if s > 0 else _nan_false((x.c < m) & (m < _sh(m, 5)))


def m_tr_ema_x(x, s, f, sl):
    a, b = x.ind("EMA", f), x.ind("EMA", sl)
    if s > 0:
        return _nan_false((a > b) & (_sh(a) <= _sh(b)))
    return _nan_false((a < b) & (_sh(a) >= _sh(b)))


def m_tr_struktura(x, s, k):
    hh, hp = _rmax(x.h, k), _sh(_rmax(x.h, k), k)
    ll, lp = _rmin(x.l, k), _sh(_rmin(x.l, k), k)
    return _nan_false((hh > hp) & (ll > lp)) if s > 0 else _nan_false((hh < hp) & (ll < lp))


def m_tr_adx(x, s, thr):
    a, p, m = x.ind("adx", 14)
    return _nan_false((a > thr) & (p > m)) if s > 0 else _nan_false((a > thr) & (m > p))


def m_tr_pullback(x, s, lvl):
    m, r = x.ind("SMA", 100), x.ind("rsi", 3)
    if s > 0:
        return _nan_false((x.c > m) & (m > _sh(m, 5)) & (r < lvl))
    return _nan_false((x.c < m) & (m < _sh(m, 5)) & (r > 100 - lvl))


def m_sr_odraz(x, s, n):
    a = x.atr
    if s > 0:
        lvl = _sh(_rmin(x.l, n - 1), 2)
        return _nan_false((x.l <= lvl + 0.2 * a) & (x.c > lvl) & (x.c > x.o))
    lvl = _sh(_rmax(x.h, n - 1), 2)
    return _nan_false((x.h >= lvl - 0.2 * a) & (x.c < lvl) & (x.c < x.o))


def m_mm_pruraz(x, s, n):
    return _nan_false(x.c > _sh(_rmax(x.h, n))) if s > 0 else _nan_false(x.c < _sh(_rmin(x.l, n)))


def m_mm_falesny(x, s, n):
    if s < 0:
        lvl = _sh(_rmax(x.h, n))
        return _nan_false((x.h > lvl) & (x.c < lvl))
    lvl = _sh(_rmin(x.l, n))
    return _nan_false((x.l < lvl) & (x.c > lvl))


def m_mm_predchozi(x, s):
    ph, pl = _prev_period(x)
    return _nan_false(x.c > ph) if s > 0 else _nan_false(x.c < pl)


def m_mm_predchozi_falesny(x, s):
    ph, pl = _prev_period(x)
    return _nan_false((x.h > ph) & (x.c < ph)) if s < 0 else _nan_false((x.l < pl) & (x.c > pl))


def m_vol_squeeze(x, s, n):
    _, up, dn, width = x.ind("bb", n, 2.0)
    sq = _nan_false(K.rolling_rank(width, 120) <= 0.2).astype(float)
    recent = _nan_false(_sh(_rmax(sq, 5)) >= 1)
    return recent & (_nan_false(x.c > up) if s > 0 else _nan_false(x.c < dn))


def m_vol_svicka_pokr(x, s, k):
    a = _sh(x.atr)
    return _nan_false(x.c - x.o >= k * a) if s > 0 else _nan_false(x.o - x.c >= k * a)


def m_vol_svicka_obrat(x, s, k):
    a = _sh(x.atr)
    return _nan_false(x.o - x.c >= k * a) if s > 0 else _nan_false(x.c - x.o >= k * a)


def m_vol_prehnani(x, s, k):
    hi = _nan_false(K.rolling_rank(x.atr / x.c, 250) >= 0.7)
    mv = (x.c - _sh(x.c, 5)) / x.atr
    return hi & (_nan_false(mv <= -k) if s > 0 else _nan_false(mv >= k))


def m_vol_klid_pruraz(x, s, n):
    lo = _nan_false(K.rolling_rank(x.atr / x.c, 250) <= 0.2)
    return lo & m_mm_pruraz(x, s, n)


def m_osc_rsi_obrat(x, s, n, lvl):
    r = x.ind("rsi", n)
    return _nan_false(r < lvl) if s > 0 else _nan_false(r > 100 - lvl)


def m_osc_rsi_mom(x, s, lvl):
    r = x.ind("rsi", 14)
    return _nan_false(r > lvl) if s > 0 else _nan_false(r < 100 - lvl)


def m_osc_macd_x(x, s, f, sl, g):
    m, sg, _ = x.ind("macd", f, sl, g)
    if s > 0:
        return _nan_false((m > sg) & (_sh(m) <= _sh(sg)))
    return _nan_false((m < sg) & (_sh(m) >= _sh(sg)))


def m_osc_macd_nula(x, s):
    m, _, _ = x.ind("macd", 12, 26, 9)
    return _nan_false((m > 0) & (_sh(m) <= 0)) if s > 0 else _nan_false((m < 0) & (_sh(m) >= 0))


def m_osc_stoch(x, s, n):
    k, d = x.ind("st", n, 3)
    if s > 0:
        return _nan_false((k > d) & (_sh(k) <= _sh(d)) & (_sh(k) < 25))
    return _nan_false((k < d) & (_sh(k) >= _sh(d)) & (_sh(k) > 75))


def m_osc_bb_obrat(x, s, k):
    _, up, dn, _ = x.ind("bb", 20, k)
    return _nan_false(x.c < dn) if s > 0 else _nan_false(x.c > up)


def m_osc_bb_pokr(x, s, k):
    _, up, dn, _ = x.ind("bb", 20, k)
    return _nan_false(x.c > up) if s > 0 else _nan_false(x.c < dn)


def m_osc_daleko(x, s, k):
    d = (x.c - x.ind("SMA", 20)) / x.atr
    return _nan_false(d < -k) if s > 0 else _nan_false(d > k)


def m_mom_ts(x, s, n):
    d = (x.c - _sh(x.c, n)) / x.atr
    return _nan_false(d >= 1.0) if s > 0 else _nan_false(d <= -1.0)


def m_mom_zrychleni(x, s):
    _, _, hst = x.ind("macd", 12, 26, 9)
    if s > 0:
        return _nan_false((hst > 0) & (hst > _sh(hst)) & (_sh(hst) > _sh(hst, 2)) & (_sh(hst, 2) > _sh(hst, 3)))
    return _nan_false((hst < 0) & (hst < _sh(hst)) & (_sh(hst) < _sh(hst, 2)) & (_sh(hst, 2) < _sh(hst, 3)))


def _run(x, k, up: bool) -> np.ndarray:
    ok = np.ones(x.n, bool)
    for j in range(k):
        a, b = _sh(x.c, j), _sh(x.c, j + 1)
        ok &= _nan_false(a > b) if up else _nan_false(a < b)
    return ok


def m_mom_rada_pokr(x, s, k):
    return _run(x, k, s > 0)


def m_mom_rada_obrat(x, s, k):
    return _run(x, k, s < 0)


def m_pa_pohlceni(x, s):
    o1, c1 = _sh(x.o), _sh(x.c)
    if s > 0:
        m = (x.c > x.o) & (c1 < o1) & (x.c >= o1) & (x.o <= c1)
    else:
        m = (x.c < x.o) & (c1 > o1) & (x.c <= o1) & (x.o >= c1)
    return _nan_false(m) & _down_before(x, s)


def m_pa_kladivo(x, s):
    body, rng = np.abs(x.c - x.o), x.h - x.l
    if s > 0:
        wick = np.minimum(x.o, x.c) - x.l
    else:
        wick = x.h - np.maximum(x.o, x.c)
    m = (wick >= 2 * body) & (wick >= 0.6 * rng) & (rng >= 0.8 * x.atr)
    return _nan_false(m) & _down_before(x, s)


def m_pa_vnitrni(x, s):
    h1, l1, h2, l2 = _sh(x.h), _sh(x.l), _sh(x.h, 2), _sh(x.l, 2)
    inside = (h1 < h2) & (l1 > l2)
    return _nan_false(inside & (x.c > h1)) if s > 0 else _nan_false(inside & (x.c < l1))


def m_pa_vnejsi(x, s):
    h1, l1 = _sh(x.h), _sh(x.l)
    outside = (x.h > h1) & (x.l < l1)
    m = outside & (x.c > h1) if s > 0 else outside & (x.c < l1)
    return _nan_false(m) & _down_before(x, s)


def m_pa_knot(x, s):
    rng = x.h - x.l
    if s > 0:
        return _nan_false((x.l <= _rmin(x.l, 20)) & (x.c >= x.l + 0.6 * rng) & (rng > 0))
    return _nan_false((x.h >= _rmax(x.h, 20)) & (x.c <= x.h - 0.6 * rng) & (rng > 0))


def _weekdays_left_in_month(d: date) -> int:
    k, nxt = 0, d + timedelta(days=1)
    while nxt.month == d.month:
        k += nxt.weekday() < 5
        nxt += timedelta(days=1)
    return k


def m_cas_konec_mesice(x, s):
    return np.array([_weekdays_left_in_month(d) <= 1 for d in x.day], bool)


def m_cas_tyden(x, s, k, cont: bool):
    fri = np.array([d.weekday() == 4 for d in x.day], bool)
    mv = (x.c - _sh(x.c, 5)) / x.atr
    up, dn = _nan_false(mv >= k), _nan_false(mv <= -k)
    want = (up if s > 0 else dn) if cont else (dn if s > 0 else up)
    return fri & want


def m_cas_asie(x, s, k, cont: bool):
    end_asia = x.bars["bucket"] == 1
    mv = (x.c - _sh(x.c, 2)) / _sh(x.atr, 2)
    up, dn = _nan_false(mv >= k), _nan_false(mv <= -k)
    return end_asia & ((up if s > 0 else dn) if cont else (dn if s > 0 else up))


def m_cas_mezera(x, s):
    first = (x.bars["bucket"] == 0) & np.array([d.weekday() == 0 for d in x.day], bool)
    gap = (x.o - _sh(x.c)) / _sh(x.atr)
    return first & (_nan_false(gap <= -0.3) if s > 0 else _nan_false(gap >= 0.3))


def m_f_carry(x, s, thr):
    cr = x.aux["carry"]
    return _nan_false(cr >= thr) if s > 0 else _nan_false(cr <= -thr)


def m_f_sazby(x, s, thr):
    mo = x.aux["mom"]
    return _nan_false(mo >= thr) if s > 0 else _nan_false(mo <= -thr)


def m_f_riskoff(x, s, lvl):
    return _nan_false(x.aux["vix"] >= lvl)


def m_f_vix_skok(x, s, k):
    v = x.aux["vix"]
    return _nan_false(v / _sh(v, 5) - 1 >= k)


def m_f_riskon(x, s, lvl):
    return _nan_false(x.aux["vix"] <= lvl)


def _event_move(x, kind: str, s: int, cont: bool) -> np.ndarray:
    ev = x.aux[kind]
    mv = (x.c - _sh(x.c)) / _sh(x.atr)
    up, dn = _nan_false(mv >= 0.5), _nan_false(mv <= -0.5)
    return ev & ((up if s > 0 else dn) if cont else (dn if s > 0 else up))


def m_ud_pokr(x, s, kind):
    return _event_move(x, kind, s, True)


def m_ud_obrat(x, s, kind):
    return _event_move(x, kind, s, False)


def m_ud_pred(x, s, kind):
    eve = x.aux[kind + "_eve"]
    mv = (x.c - _sh(x.c, 5)) / x.atr
    return eve & (_nan_false(mv <= -1.0) if s > 0 else _nan_false(mv >= 1.0))


def m_kor_sila(x, s, n, cont: bool):
    rb, rq = x.aux[f"rank{n}"]
    strong_base = _nan_false((rb == 1) & (rq == 8))
    strong_quote = _nan_false((rb == 8) & (rq == 1))
    return (strong_base if s > 0 else strong_quote) if cont else (strong_quote if s > 0 else strong_base)


def m_kor_dohaneni(x, s, n):
    gap = x.aux[f"gap{n}"]                       # base minus quote strength measured on the OTHER pairs (ATR units)
    own = (x.c - _sh(x.c, n)) / x.atr
    return _nan_false((gap >= 1.0) & (own <= 0)) if s > 0 else _nan_false((gap <= -1.0) & (own >= 0))


def m_ft_carry_pokles(x, s, lvl):
    r, cr = x.ind("rsi", 2), x.aux["carry"]
    return _nan_false((cr >= 1.0) & (r < lvl)) if s > 0 else _nan_false((cr <= -1.0) & (r > 100 - lvl))


def m_ft_sazby_trend(x, s, n):
    m, mo = x.ind("SMA", n), x.aux["mom"]
    return _nan_false((mo >= 0.25) & (x.c > m)) if s > 0 else _nan_false((mo <= -0.25) & (x.c < m))


def m_ft_riskoff_pruraz(x, s):
    return _nan_false(x.aux["vix"] >= 25) & m_mm_pruraz(x, s, 20)


def m_ft_cb_extrem(x, s):
    r = x.ind("rsi", 14)
    return x.aux["cb_eve"] & (_nan_false(r < 30) if s > 0 else _nan_false(r > 70))


KOMB = {   # the user's pre-registered examples (scripts/tydenni_analyza.PREREGISTERED), conventional reading
    1: ((("rsi_gt", (14, 50)), ("px_gt", ("EMA", 20))), (("rsi_lt", (14, 50)), ("px_lt", ("EMA", 20))),
        "RSI14 > 50 a cena nad EMA20", "RSI14 < 50 a cena pod EMA20"),
    2: ((("rsi_lt", (14, 30)), ("px_lt", ("SMA", 50))), (("rsi_gt", (14, 70)), ("px_gt", ("SMA", 50))),
        "RSI14 < 30 a cena pod SMA50 (přeprodáno)", "RSI14 > 70 a cena nad SMA50 (překoupeno)"),
    3: ((("adx_bull", (14, 25)), ("macd_hpos", (12, 26, 9))), (("adx_bear", (14, 25)), ("macd_hneg", (12, 26, 9))),
        "ADX14 > 25 s +DI a MACD nad signálem", "ADX14 > 25 s −DI a MACD pod signálem"),
    4: ((("bb_sqz", (20,)), ("atr_up", (14,)), ("px_gt", ("EMA", 20))),
        (("bb_sqz", (20,)), ("atr_up", (14,)), ("px_lt", ("EMA", 20))),
        "Bollinger stažené, ATR roste, cena nad EMA20", "Bollinger stažené, ATR roste, cena pod EMA20"),
    5: ((("rsi_lt", (14, 30)), ("bb_bdn", (20, 2.0)), ("adx_lt", (14, 20))),
        (("rsi_gt", (14, 70)), ("bb_bup", (20, 2.0)), ("adx_lt", (14, 20))),
        "RSI14 < 30, pod dolním Bollingerem, ADX14 < 20", "RSI14 > 70, nad horním Bollingerem, ADX14 < 20"),
    6: ((("rsi_gt", (14, 50)), ("px_gt", ("EMA", 50)), ("adx_gt", (14, 25))),
        (("rsi_lt", (14, 50)), ("px_lt", ("EMA", 50)), ("adx_gt", (14, 25))),
        "RSI14 > 50, cena nad EMA50, ADX14 > 25", "RSI14 < 50, cena pod EMA50, ADX14 > 25"),
}


def m_komb(x, s, k):
    m = np.ones(x.n, bool)
    for kind, p in KOMB[k][0 if s > 0 else 1]:
        m &= x.b.mask(K.Cond(kind, p))
    return m


@dataclass(frozen=True)
class Family:
    key: str
    typ: str
    logika: str                 # "pokračování" / "obrat" / "fundament" / "čas"
    tfs: tuple
    variants: dict              # tf -> list of parameter tuples
    nb: str                     # neighbour mode: "grid", "list", "none"
    fn: object
    text: object                # (side, *params) -> Czech condition
    ind: object                 # (*params) -> list of indicators with parameters
    fund: object = None         # (side, *params) -> fundamental condition text
    side_of_pair: bool = False  # direction set per pair (risk sign) instead of LONG + SHORT


def _both(v):
    return {"1D": v, "4H": v}


def _lr(s):
    return "LONG" if s > 0 else "SHORT"


_LIB: list = []


def library() -> list[Family]:
    if not _LIB:
        _LIB.extend(_library())
    return _LIB


def _family(key: str) -> Family:
    return next(f for f in library() if f.key == key)


def _library() -> list[Family]:
    """The hypotheses. Each has its direction fixed in advance (LONG/SHORT mirror versions); where trader lore gives
    two opposite readings of one condition (continuation vs reversal), both are separate hypotheses."""
    up = lambda s, a, b: a if s > 0 else b                                             # noqa: E731
    F = Family
    return [
        F("tr_ma", "trend", "pokračování", ("1D", "4H"), _both([(20,), (50,), (100,), (200,)]), "grid", m_tr_ma,
          lambda s, n: up(s, f"cena nad SMA{n} a SMA{n} roste", f"cena pod SMA{n} a SMA{n} klesá"),
          lambda n: [f"SMA({n})"]),
        F("tr_ema_x", "trend", "pokračování", ("1D", "4H"), _both([(10, 30), (20, 50), (50, 200)]), "list", m_tr_ema_x,
          lambda s, f, sl: up(s, f"EMA{f} právě překřížila EMA{sl} nahoru", f"EMA{f} právě překřížila EMA{sl} dolů"),
          lambda f, sl: [f"EMA({f})", f"EMA({sl})"]),
        F("tr_struktura", "trend", "pokračování", ("1D", "4H"), _both([(5,), (10,), (20,)]), "grid", m_tr_struktura,
          lambda s, k: up(s, f"vyšší maximum i minimum než předchozích {k} svíček", f"nižší maximum i minimum než předchozích {k} svíček"),
          lambda k: [f"maxima/minima {k} svíček"]),
        F("tr_adx", "trend", "pokračování", ("1D", "4H"), _both([(20,), (25,), (30,)]), "grid", m_tr_adx,
          lambda s, t: up(s, f"ADX14 > {t} a +DI nad −DI", f"ADX14 > {t} a −DI nad +DI"), lambda t: ["ADX(14)", "DI(14)"]),
        F("tr_pullback", "trend", "obrat v trendu", ("1D", "4H"), _both([(10,), (20,), (30,)]), "grid", m_tr_pullback,
          lambda s, v: up(s, f"rostoucí SMA100, cena nad ní a RSI3 < {v} (pokles v trendu)",
                          f"klesající SMA100, cena pod ní a RSI3 > {100 - v} (růst v trendu dolů)"),
          lambda v: ["SMA(100)", "RSI(3)"]),
        F("sr_odraz", "podpora_odpor", "obrat", ("1D", "4H"), _both([(20,), (50,), (100,)]), "grid", m_sr_odraz,
          lambda s, n: up(s, f"svíčka se dotkla podpory (minimum {n} svíček) a zavřela výš",
                          f"svíčka se dotkla odporu (maximum {n} svíček) a zavřela níž"),
          lambda n: [f"podpora/odpor {n} svíček", "ATR(14)"]),
        F("mm_pruraz", "max_min", "pokračování", ("1D", "4H"), _both([(10,), (20,), (55,)]), "grid", m_mm_pruraz,
          lambda s, n: up(s, f"zavření nad maximem předchozích {n} svíček", f"zavření pod minimem předchozích {n} svíček"),
          lambda n: [f"maximum/minimum {n} svíček"]),
        F("mm_falesny", "max_min", "obrat", ("1D", "4H"), _both([(10,), (20,), (55,)]), "grid", m_mm_falesny,
          lambda s, n: up(s, f"falešný průraz minima {n} svíček (pod něj a zpět)", f"falešný průraz maxima {n} svíček (nad něj a zpět)"),
          lambda n: [f"maximum/minimum {n} svíček"]),
        F("mm_predchozi", "max_min", "pokračování", ("1D", "4H"), _both([()]), "none", m_mm_predchozi,
          lambda s: up(s, "zavření nad maximem předchozího období (týden u 1D, den u 4H)",
                       "zavření pod minimem předchozího období (týden u 1D, den u 4H)"), lambda: ["předchozí týden/den"]),
        F("mm_predchozi_falesny", "max_min", "obrat", ("1D", "4H"), _both([()]), "none", m_mm_predchozi_falesny,
          lambda s: up(s, "falešný průraz minima předchozího období", "falešný průraz maxima předchozího období"),
          lambda: ["předchozí týden/den"]),
        F("vol_squeeze", "volatilita", "pokračování", ("1D", "4H"), _both([(15,), (20,), (30,)]), "grid", m_vol_squeeze,
          lambda s, n: up(s, f"po stažení Bollingerových pásem ({n}) zavření nad horním pásmem",
                          f"po stažení Bollingerových pásem ({n}) zavření pod dolním pásmem"),
          lambda n: [f"Bollinger({n}, 2)", "šířka pásem 120"]),
        F("vol_svicka_pokr", "volatilita", "pokračování", ("1D", "4H"), _both([(1.0,), (1.5,), (2.0,)]), "grid",
          m_vol_svicka_pokr, lambda s, k: up(s, f"velká rostoucí svíčka (≥ {k:g} ATR) – pokračování", f"velká klesající svíčka (≥ {k:g} ATR) – pokračování"),
          lambda k: ["ATR(14)"]),
        F("vol_svicka_obrat", "volatilita", "obrat", ("1D", "4H"), _both([(1.0,), (1.5,), (2.0,)]), "grid",
          m_vol_svicka_obrat, lambda s, k: up(s, f"velká klesající svíčka (≥ {k:g} ATR) – obrat", f"velká rostoucí svíčka (≥ {k:g} ATR) – obrat"),
          lambda k: ["ATR(14)"]),
        F("vol_prehnani", "volatilita", "obrat", ("1D", "4H"), _both([(1.5,), (2.0,), (3.0,)]), "grid", m_vol_prehnani,
          lambda s, k: up(s, f"vysoká volatilita a pád o ≥ {k:g} ATR za 5 svíček", f"vysoká volatilita a růst o ≥ {k:g} ATR za 5 svíček"),
          lambda k: ["ATR(14)", "pořadí ATR 250"]),
        F("vol_klid_pruraz", "volatilita", "pokračování", ("1D", "4H"), _both([(10,), (20,)]), "grid", m_vol_klid_pruraz,
          lambda s, n: up(s, f"nízká volatilita a průraz maxima {n} svíček", f"nízká volatilita a průraz minima {n} svíček"),
          lambda n: ["ATR(14)", "pořadí ATR 250", f"maximum/minimum {n}"]),
        F("osc_rsi_obrat", "oscilatory", "obrat", ("1D", "4H"),
          _both([(2, 5), (2, 10), (2, 15), (14, 25), (14, 30), (14, 35)]), "grid", m_osc_rsi_obrat,
          lambda s, n, v: up(s, f"RSI{n} < {v}", f"RSI{n} > {100 - v}"), lambda n, v: [f"RSI({n})"]),
        F("osc_rsi_mom", "oscilatory", "pokračování", ("1D", "4H"), _both([(60,), (65,), (70,)]), "grid", m_osc_rsi_mom,
          lambda s, v: up(s, f"RSI14 > {v} (síla pokračuje)", f"RSI14 < {100 - v} (slabost pokračuje)"), lambda v: ["RSI(14)"]),
        F("osc_macd_x", "oscilatory", "pokračování", ("1D", "4H"), _both([(8, 21, 5), (12, 26, 9), (19, 39, 9)]), "list",
          m_osc_macd_x, lambda s, f, sl, g: up(s, f"MACD({f},{sl},{g}) překřížil signál nahoru", f"MACD({f},{sl},{g}) překřížil signál dolů"),
          lambda f, sl, g: [f"MACD({f},{sl},{g})"]),
        F("osc_macd_nula", "oscilatory", "pokračování", ("1D", "4H"), _both([()]), "none", m_osc_macd_nula,
          lambda s: up(s, "MACD(12,26,9) překřížil nulu nahoru", "MACD(12,26,9) překřížil nulu dolů"), lambda: ["MACD(12,26,9)"]),
        F("osc_stoch", "oscilatory", "obrat", ("1D", "4H"), _both([(9,), (14,), (21,)]), "grid", m_osc_stoch,
          lambda s, n: up(s, f"stochastic({n},3) pod 25 překřížil signál nahoru", f"stochastic({n},3) nad 75 překřížil signál dolů"),
          lambda n: [f"stochastic({n},3)"]),
        F("osc_bb_obrat", "oscilatory", "obrat", ("1D", "4H"), _both([(2.0,), (2.5,), (3.0,)]), "grid", m_osc_bb_obrat,
          lambda s, k: up(s, f"zavření pod dolním Bollingerem (20, {k:g})", f"zavření nad horním Bollingerem (20, {k:g})"),
          lambda k: [f"Bollinger(20, {k:g})"]),
        F("osc_bb_pokr", "oscilatory", "pokračování", ("1D", "4H"), _both([(2.0,), (2.5,)]), "grid", m_osc_bb_pokr,
          lambda s, k: up(s, f"zavření nad horním Bollingerem (20, {k:g}) – pokračování", f"zavření pod dolním Bollingerem (20, {k:g}) – pokračování"),
          lambda k: [f"Bollinger(20, {k:g})"]),
        F("osc_daleko", "oscilatory", "obrat", ("1D", "4H"), _both([(1.5,), (2.0,), (2.5,)]), "grid", m_osc_daleko,
          lambda s, k: up(s, f"cena ≥ {k:g} ATR pod SMA20", f"cena ≥ {k:g} ATR nad SMA20"), lambda k: ["SMA(20)", "ATR(14)"]),
        F("mom_ts", "momentum", "pokračování", ("1D", "4H"), {"1D": [(10,), (20,), (60,)], "4H": [(6,), (30,), (120,)]},
          "grid", m_mom_ts, lambda s, n: up(s, f"cena o ≥ 1 ATR výš než před {n} svíčkami", f"cena o ≥ 1 ATR níž než před {n} svíčkami"),
          lambda n: [f"změna {n} svíček", "ATR(14)"]),
        F("mom_zrychleni", "momentum", "pokračování", ("1D", "4H"), _both([()]), "none", m_mom_zrychleni,
          lambda s: up(s, "histogram MACD kladný a 3 svíčky roste", "histogram MACD záporný a 3 svíčky klesá"),
          lambda: ["MACD(12,26,9)"]),
        F("mom_rada_pokr", "momentum", "pokračování", ("1D", "4H"), _both([(3,), (4,), (5,)]), "grid", m_mom_rada_pokr,
          lambda s, k: up(s, f"{k} zavření za sebou výš – pokračování", f"{k} zavření za sebou níž – pokračování"), lambda k: []),
        F("mom_rada_obrat", "momentum", "obrat", ("1D", "4H"), _both([(3,), (4,), (5,)]), "grid", m_mom_rada_obrat,
          lambda s, k: up(s, f"{k} zavření za sebou níž – obrat", f"{k} zavření za sebou výš – obrat"), lambda k: []),
        F("pa_pohlceni", "price_action", "obrat", ("1D", "4H"), _both([()]), "none", m_pa_pohlceni,
          lambda s: up(s, "býčí pohlcení po poklesu", "medvědí pohlcení po růstu"), lambda: []),
        F("pa_kladivo", "price_action", "obrat", ("1D", "4H"), _both([()]), "none", m_pa_kladivo,
          lambda s: up(s, "kladivo (dlouhý spodní knot) po poklesu", "padající hvězda (dlouhý horní knot) po růstu"),
          lambda: ["ATR(14)"]),
        F("pa_vnitrni", "price_action", "pokračování", ("1D", "4H"), _both([()]), "none", m_pa_vnitrni,
          lambda s: up(s, "průraz vnitřní svíčky nahoru", "průraz vnitřní svíčky dolů"), lambda: []),
        F("pa_vnejsi", "price_action", "obrat", ("1D", "4H"), _both([()]), "none", m_pa_vnejsi,
          lambda s: up(s, "vnější svíčka po poklesu zavřela nad předchozím maximem", "vnější svíčka po růstu zavřela pod předchozím minimem"),
          lambda: []),
        F("pa_knot", "price_action", "obrat", ("1D", "4H"), _both([()]), "none", m_pa_knot,
          lambda s: up(s, "nové minimum 20 svíček odmítnuto (zavření v horní části)", "nové maximum 20 svíček odmítnuto (zavření v dolní části)"),
          lambda: []),
        F("cas_konec_mesice", "cas", "čas", ("1D",), {"1D": [()]}, "none", m_cas_konec_mesice,
          lambda s: up(s, "poslední dva obchodní dny měsíce – růst", "poslední dva obchodní dny měsíce – pokles"), lambda: []),
        F("cas_tyden_pokr", "cas", "pokračování", ("1D",), {"1D": [(1.0,), (2.0,)]}, "grid",
          lambda x, s, k: m_cas_tyden(x, s, k, True),
          lambda s, k: up(s, f"pátek: týden vzrostl o ≥ {k:g} ATR – pokračování", f"pátek: týden klesl o ≥ {k:g} ATR – pokračování"),
          lambda k: ["ATR(14)"]),
        F("cas_tyden_obrat", "cas", "obrat", ("1D",), {"1D": [(1.0,), (2.0,)]}, "grid",
          lambda x, s, k: m_cas_tyden(x, s, k, False),
          lambda s, k: up(s, f"pátek: týden klesl o ≥ {k:g} ATR – obrat", f"pátek: týden vzrostl o ≥ {k:g} ATR – obrat"),
          lambda k: ["ATR(14)"]),
        F("cas_asie_pokr", "cas", "pokračování", ("4H",), {"4H": [(0.5,), (1.0,)]}, "grid",
          lambda x, s, k: m_cas_asie(x, s, k, True),
          lambda s, k: up(s, f"asijská seance (23–07 h našeho času) vzrostla o ≥ {k:g} ATR – pokračování",
                          f"asijská seance klesla o ≥ {k:g} ATR – pokračování"), lambda k: ["ATR(14)"]),
        F("cas_asie_obrat", "cas", "obrat", ("4H",), {"4H": [(0.5,), (1.0,)]}, "grid",
          lambda x, s, k: m_cas_asie(x, s, k, False),
          lambda s, k: up(s, f"asijská seance klesla o ≥ {k:g} ATR – obrat", f"asijská seance vzrostla o ≥ {k:g} ATR – obrat"),
          lambda k: ["ATR(14)"]),
        F("cas_mezera", "cas", "obrat", ("4H",), {"4H": [()]}, "none", m_cas_mezera,
          lambda s: up(s, "pondělní mezera dolů ≥ 0,3 ATR – zaplnění", "pondělní mezera nahoru ≥ 0,3 ATR – zaplnění"),
          lambda: ["ATR(14)"]),
        F("f_carry", "fundament", "fundament", ("1D",), {"1D": [(0.5,), (1.0,), (2.0,)]}, "grid", m_f_carry,
          lambda s, t: up(s, f"úroková sazba první měny vyšší o ≥ {t:g} p.b. (carry)", f"úroková sazba druhé měny vyšší o ≥ {t:g} p.b. (carry)"),
          lambda t: [], lambda s, t: f"rozdíl 3M sazeb {'≥' if s > 0 else '≤'} {s * t:+g} p.b. (OECD, se zpožděním 2 měsíce)"),
        F("f_sazby", "fundament", "fundament", ("1D",), {"1D": [(0.1,), (0.25,), (0.5,)]}, "grid", m_f_sazby,
          lambda s, t: up(s, f"rozdíl sazeb za 3 měsíce vzrostl o ≥ {t:g} p.b.", f"rozdíl sazeb za 3 měsíce klesl o ≥ {t:g} p.b."),
          lambda t: [], lambda s, t: f"změna rozdílu sazeb za 3 měsíce {'≥' if s > 0 else '≤'} {s * t:+g} p.b."),
        F("f_riskoff", "fundament", "fundament", ("1D",), {"1D": [(20,), (25,), (30,)]}, "grid", m_f_riskoff,
          lambda s, v: f"strach na trzích: VIX ≥ {v} → bezpečné měny (JPY, CHF) sílí", lambda v: ["VIX"],
          lambda s, v: f"VIX předchozího dne ≥ {v}", True),
        F("f_vix_skok", "fundament", "fundament", ("1D",), {"1D": [(0.2,), (0.4,)]}, "grid", m_f_vix_skok,
          lambda s, k: f"VIX za 5 dní vzrostl o ≥ {k * 100:.0f} % → bezpečné měny sílí", lambda k: ["VIX"],
          lambda s, k: f"VIX +{k * 100:.0f} % za 5 dní", True),
        F("f_riskon", "fundament", "fundament", ("1D",), {"1D": [(12,), (14,)]}, "grid", m_f_riskon,
          lambda s, v: f"klid na trzích: VIX ≤ {v} → rizikové měny (AUD, NZD) sílí", lambda v: ["VIX"],
          lambda s, v: f"VIX předchozího dne ≤ {v}", True),
        F("ud_cb_pokr", "udalosti", "pokračování", ("1D",), {"1D": [("cb",)]}, "none", m_ud_pokr,
          lambda s, k: up(s, "den rozhodnutí centrální banky, pár vzrostl o ≥ 0,5 ATR – pokračování",
                          "den rozhodnutí centrální banky, pár klesl o ≥ 0,5 ATR – pokračování"),
          lambda k: ["ATR(14)"], lambda s, k: "den rozhodnutí Fed/ECB/BoJ/BoE měny páru"),
        F("ud_cb_obrat", "udalosti", "obrat", ("1D",), {"1D": [("cb",)]}, "none", m_ud_obrat,
          lambda s, k: up(s, "den rozhodnutí centrální banky, pár klesl o ≥ 0,5 ATR – obrat",
                          "den rozhodnutí centrální banky, pár vzrostl o ≥ 0,5 ATR – obrat"),
          lambda k: ["ATR(14)"], lambda s, k: "den rozhodnutí Fed/ECB/BoJ/BoE měny páru"),
        F("ud_cb_pred", "udalosti", "obrat", ("1D",), {"1D": [("cb",)]}, "none", m_ud_pred,
          lambda s, k: up(s, "den před rozhodnutím CB, pár za 5 dní klesl o ≥ 1 ATR – obrat",
                          "den před rozhodnutím CB, pár za 5 dní vzrostl o ≥ 1 ATR – obrat"),
          lambda k: ["ATR(14)"], lambda s, k: "zítra rozhoduje Fed/ECB/BoJ/BoE měny páru"),
        F("ud_us_pokr", "udalosti", "pokračování", ("1D",), {"1D": [("us",)]}, "none", m_ud_pokr,
          lambda s, k: up(s, "den zpráv NFP/CPI, pár vzrostl o ≥ 0,5 ATR – pokračování", "den zpráv NFP/CPI, pár klesl o ≥ 0,5 ATR – pokračování"),
          lambda k: ["ATR(14)"], lambda s, k: "den zveřejnění US NFP nebo CPI"),
        F("ud_us_obrat", "udalosti", "obrat", ("1D",), {"1D": [("us",)]}, "none", m_ud_obrat,
          lambda s, k: up(s, "den zpráv NFP/CPI, pár klesl o ≥ 0,5 ATR – obrat", "den zpráv NFP/CPI, pár vzrostl o ≥ 0,5 ATR – obrat"),
          lambda k: ["ATR(14)"], lambda s, k: "den zveřejnění US NFP nebo CPI"),
        F("ud_us_pred", "udalosti", "obrat", ("1D",), {"1D": [("us",)]}, "none", m_ud_pred,
          lambda s, k: up(s, "den před NFP/CPI, pár za 5 dní klesl o ≥ 1 ATR – obrat", "den před NFP/CPI, pár za 5 dní vzrostl o ≥ 1 ATR – obrat"),
          lambda k: ["ATR(14)"], lambda s, k: "zítra US NFP nebo CPI"),
        F("kor_sila_pokr", "korelace", "pokračování", ("1D", "4H"), {"1D": [(5,), (20,)], "4H": [(6,), (30,)]}, "grid",
          lambda x, s, n: m_kor_sila(x, s, n, True),
          lambda s, n: up(s, f"první měna nejsilnější a druhá nejslabší z 8 (za {n} svíček) – pokračování",
                          f"první měna nejslabší a druhá nejsilnější z 8 (za {n} svíček) – pokračování"),
          lambda n: [f"síla měn z 12 párů, {n} svíček"]),
        F("kor_sila_obrat", "korelace", "obrat", ("1D", "4H"), {"1D": [(5,), (20,)], "4H": [(6,), (30,)]}, "grid",
          lambda x, s, n: m_kor_sila(x, s, n, False),
          lambda s, n: up(s, f"první měna nejslabší a druhá nejsilnější z 8 (za {n} svíček) – obrat",
                          f"první měna nejsilnější a druhá nejslabší z 8 (za {n} svíček) – obrat"),
          lambda n: [f"síla měn z 12 párů, {n} svíček"]),
        F("kor_dohaneni", "korelace", "pokračování", ("1D", "4H"), {"1D": [(5,), (20,)], "4H": [(6,), (30,)]}, "grid",
          m_kor_dohaneni,
          lambda s, n: up(s, f"na ostatních párech je první měna o ≥ 1 ATR silnější, tento pár zaostal ({n} svíček) – dohnání",
                          f"na ostatních párech je první měna o ≥ 1 ATR slabší, tento pár zaostal ({n} svíček) – dohnání"),
          lambda n: [f"síla měn z ostatních párů, {n} svíček"]),
        F("ft_carry_pokles", "fund_tech", "obrat v trendu", ("1D",), {"1D": [(5,), (10,), (20,)]}, "grid", m_ft_carry_pokles,
          lambda s, v: up(s, f"carry ≥ 1 p.b. ve prospěch první měny a RSI2 < {v}", f"carry ≥ 1 p.b. ve prospěch druhé měny a RSI2 > {100 - v}"),
          lambda v: ["RSI(2)"], lambda s, v: f"rozdíl sazeb {'≥ +1' if s > 0 else '≤ −1'} p.b."),
        F("ft_sazby_trend", "fund_tech", "pokračování", ("1D",), {"1D": [(20,), (50,), (100,)]}, "grid", m_ft_sazby_trend,
          lambda s, n: up(s, f"sazby rostou ve prospěch první měny a cena nad SMA{n}", f"sazby rostou ve prospěch druhé měny a cena pod SMA{n}"),
          lambda n: [f"SMA({n})"], lambda s, n: f"změna rozdílu sazeb za 3 měsíce {'≥ +0,25' if s > 0 else '≤ −0,25'} p.b."),
        F("ft_riskoff_pruraz", "fund_tech", "pokračování", ("1D",), {"1D": [()]}, "none", m_ft_riskoff_pruraz,
          lambda s: up(s, "VIX ≥ 25 a průraz maxima 20 dní", "VIX ≥ 25 a průraz minima 20 dní"),
          lambda: ["VIX", "maximum/minimum 20"], lambda s: "VIX předchozího dne ≥ 25"),
        F("ft_cb_extrem", "fund_tech", "obrat", ("1D",), {"1D": [()]}, "none", m_ft_cb_extrem,
          lambda s: up(s, "zítra rozhoduje CB a RSI14 < 30", "zítra rozhoduje CB a RSI14 > 70"),
          lambda: ["RSI(14)"], lambda s: "zítra rozhoduje Fed/ECB/BoJ/BoE měny páru"),
        F("komb", "kombinace", "kombinace", ("1D", "4H"), _both([(k,) for k in KOMB]), "none", m_komb,
          lambda s, k: KOMB[k][2 if s > 0 else 3], lambda k: []),
    ]


def tpl_id(fam: Family, params: tuple, side: int) -> str:
    return "-".join([fam.key] + [f"{p:g}" if isinstance(p, float) else str(p) for p in params] + ["L" if side > 0 else "S"])


def applicable(fam: Family, pair: str, tf: str, params: tuple) -> list[int]:
    """Sides of the template on the pair (risk templates: one side by the pair's risk sign; events: the pair must
    have a currency of the event)."""
    if tf not in fam.tfs:
        return []
    b, q = pair.split("/")
    if fam.key.startswith("ud_cb") or fam.key == "ft_cb_extrem":
        if not ({b, q} & {"USD", "EUR", "JPY", "GBP"}):
            return []
    if fam.key.startswith("ud_us") and "USD" not in (b, q):
        return []
    if fam.side_of_pair:
        rs = risk_sign(pair)
        if not rs:
            return []
        return [-rs] if fam.key in ("f_riskoff", "f_vix_skok") else [rs]
    if fam.key == "ft_riskoff_pruraz":
        rs = risk_sign(pair)
        return [-rs] if rs else []
    return [1, -1]


def neighbours(fam: Family, tf: str, params: tuple) -> list[tuple]:
    vs = fam.variants.get(tf, [])
    if fam.nb == "none" or params not in vs:
        return []
    if fam.nb == "list":
        i = vs.index(params)
        return [vs[j] for j in (i - 1, i + 1) if 0 <= j < len(vs)]
    out = []
    for pos in range(len(params)):
        same = sorted({v[pos] for v in vs if all(v[q] == params[q] for q in range(len(params)) if q != pos)})
        i = same.index(params[pos])
        for j in (i - 1, i + 1):
            if 0 <= j < len(same):
                out.append(tuple(same[j] if q == pos else params[q] for q in range(len(params))))
    return out


def describe(fam: Family, params: tuple, side: int) -> dict:
    return {"podminka": fam.text(side, *params), "indikatory": fam.ind(*params),
            "fundament": fam.fund(side, *params) if fam.fund else None}


# ----------------------------------------------------------------------
# auxiliary data: rates, VIX, events, currency strength
# ----------------------------------------------------------------------

def load_fund() -> dict:
    """Point-in-time inputs shared by all pairs: monthly rates, VIX by day, event days."""
    import fundamenty as F
    import profit_lab2 as P
    import research_factors as RF
    out = {"rates": None, "vix": ([], []), "events": {}}
    try:
        out["rates"] = P.monthly_rates()
    except Exception as exc:                                  # missing data stays missing (NEOVĚŘENO)
        print(f"heuristiky: sazby nedostupne ({type(exc).__name__})", file=sys.stderr)
    try:
        rows = RF._csv("VIXCLS")
        out["vix"] = ([d for d, _ in rows], [v for _, v in rows])
    except Exception as exc:
        print(f"heuristiky: VIX nedostupny ({type(exc).__name__})", file=sys.stderr)
    ev = F.load_events()
    days = {k: {date.fromisoformat(d) for d in ev.get(k, [])} for k in ("FED", "ECB", "BOJ", "BOE", "US_NFP", "US_CPI")}
    try:                                                      # upcoming NFP / CPI from the calendar archive
        from src.fundamental.calendar import events_between
        now = int(time.time())
        for e in events_between(now - 40 * 86400, now + 14 * 86400, ("USD",), "High"):
            name = {"Non-Farm Employment Change": "US_NFP", "CPI m/m": "US_CPI"}.get(e.title)
            if name:
                days[name].add(datetime.fromtimestamp(e.scheduled_at, tz=NY).date())
    except Exception:
        pass
    out["events"] = days
    return out


def _next_weekday(d: date) -> date:
    return d + timedelta(days=3 if d.weekday() == 4 else 1)


def pair_aux(pair: str, bars: dict, fund: dict) -> dict:
    import fundamenty as F
    import profit_lab2 as P
    n = len(bars["c"])
    b, q = pair.split("/")
    carry, mom = np.full(n, np.nan), np.full(n, np.nan)
    rates = fund["rates"]
    if rates and b in rates and q in rates:
        memo = {}
        for i, d in enumerate(bars["day"]):
            key = (d.year, d.month)
            if key not in memo:
                kb, kq = (P.rate_at(rates[x], d.year, d.month, 2) for x in (b, q))
                ob, oq = (P.rate_at(rates[x], d.year, d.month, 5) for x in (b, q))
                cr = None if kb is None or kq is None else kb - kq
                mo = None if cr is None or ob is None or oq is None else cr - (ob - oq)
                memo[key] = (np.nan if cr is None else cr, np.nan if mo is None else mo)
            carry[i], mom[i] = memo[key]
    vix = np.full(n, np.nan)
    vd, vv = fund["vix"]
    for i, d in enumerate(bars["day"]):
        k = bisect_left(vd, d) - 1                              # the last VIX close strictly before the bar's day
        if k >= 0 and (d - vd[k]).days <= 5:
            vix[i] = vv[k]
    ev = fund["events"]
    cb = set().union(*[ev.get(F.CB_OF[c], set()) for c in (b, q) if c in F.CB_OF]) if {b, q} & set(F.CB_OF) else set()
    us = (ev.get("US_NFP", set()) | ev.get("US_CPI", set())) if "USD" in (b, q) else set()
    days = bars["day"]
    return {"carry": carry, "mom": mom, "vix": vix,
            "cb": np.array([d in cb for d in days], bool), "cb_eve": np.array([_next_weekday(d) in cb for d in days], bool),
            "us": np.array([d in us for d in days], bool), "us_eve": np.array([_next_weekday(d) in us for d in days], bool)}


def add_strength(all_bars: dict, auxes: dict, tf: str) -> None:
    """Currency strength from the 12 pairs (mean ATR-normalised change, sign by the currency's side), its rank of 8
    for the pair's currencies, and the base-minus-quote gap measured on the OTHER pairs; aligned by bar end."""
    windows = [v[0] for v in _family("kor_sila_pokr").variants[tf]]
    pairs = list(all_bars)
    for n in windows:
        moves = {}
        for p in pairs:
            B = all_bars[p]
            a = K.atr(B["h"], B["l"], B["c"], 14)
            moves[p] = (B["end_ts"], (B["c"] - _sh(B["c"], n)) / a)
        for p in pairs:
            ends = all_bars[p]["end_ts"]
            parts = {c: [] for c in CURRENCIES}
            others = {c: [] for c in CURRENCIES}
            for q in pairs:
                e, mv = moves[q]
                k = np.searchsorted(e, ends, side="right") - 1
                val = np.where(k >= 0, mv[np.maximum(k, 0)], np.nan)
                val = np.where((k >= 0) & (e[np.maximum(k, 0)] == ends), val, np.nan)   # the same bar only
                qb, qq = q.split("/")
                parts[qb].append(val)
                parts[qq].append(-val)
                if q != p:
                    others[qb].append(val)
                    others[qq].append(-val)
            with np.errstate(invalid="ignore"), warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                S = np.vstack([np.nanmean(np.vstack(parts[c]), axis=0) if parts[c] else np.full(len(ends), np.nan)
                               for c in CURRENCIES])
                So = {c: (np.nanmean(np.vstack(others[c]), axis=0) if others[c] else np.full(len(ends), np.nan))
                      for c in CURRENCIES}
            complete = ~np.isnan(S).any(axis=0)
            rank = np.full(S.shape, np.nan)
            order = (-np.nan_to_num(S, nan=-1e9)).argsort(axis=0).argsort(axis=0) + 1.0
            rank[:, complete] = order[:, complete]
            pb, pq = p.split("/")
            auxes[p][f"rank{n}"] = (rank[CURRENCIES.index(pb)], rank[CURRENCIES.index(pq)])
            auxes[p][f"gap{n}"] = So[pb] - So[pq]


# ----------------------------------------------------------------------
# outcomes and predictions
# ----------------------------------------------------------------------

def cost_pct(pair: str, price: np.ndarray) -> np.ndarray:
    """Round trip: the spread plus slippage of the pair (as the backtest and the forward test)."""
    import profit_lab2 as P
    pip = get_instrument(pair).pip
    return (P.SPREAD_PIPS[pair] + P.SLIPPAGE_PIPS) * pip / price * 100


def outcomes(x: Ctx) -> dict:
    H, c, n = x.H, x.c, x.n
    gross = np.full(n, np.nan)
    hi = np.full(n, np.nan)
    lo = np.full(n, np.nan)
    if n > H:
        from numpy.lib.stride_tricks import sliding_window_view
        gross[:n - H] = (c[H:] / c[:n - H] - 1) * 100
        hi[:n - H] = sliding_window_view(x.h[1:], H).max(axis=1)[:n - H]
        lo[:n - H] = sliding_window_view(x.l[1:], H).min(axis=1)[:n - H]
    end = x.bars["end_ts"]
    span = np.full(n, np.inf)
    if n > H:
        span[:n - H] = end[H:] - end[:n - H]
    valid = (span <= TFS[x.tf]["span"]) & np.isfinite(gross) & np.isfinite(x.atr) & (np.arange(n) >= WARM)
    ath = x.atr * math.sqrt(H) / c * 100
    rk = K.rolling_rank(x.atr / c, 250)
    adx = x.ind("adx", 14)[0]
    vol = np.where(rk >= 0.7, "vysoká", np.where(rk <= 0.3, "nízká", "střední"))
    trend = np.where(adx >= 25, "trend", np.where(adx <= 20, "range", "přechod"))
    year = np.array([d.year for d in x.day])
    return {"gross": gross, "up_mfe": (hi / c - 1) * 100, "up_mae": (1 - lo / c) * 100, "valid": valid, "ath": ath,
            "cost": cost_pct(x.pair, c), "vol": vol, "trend": trend, "year": year, "pips": c / 100 / x.pip}


def take(mask: np.ndarray, valid: np.ndarray, H: int) -> np.ndarray:
    """Predictions of a rule: bars where it fires, at most one open prediction at a time (no overlap)."""
    out, nxt = [], -1
    for i in np.flatnonzero(mask & valid).tolist():
        if i >= nxt:
            out.append(i)
            nxt = i + H
    return np.array(out, np.int64)


def pred_arrays(o: dict, idx: np.ndarray, side: int) -> dict:
    g = o["gross"][idx] * side
    net = g - o["cost"][idx]
    mfe = o["up_mfe"][idx] if side > 0 else o["up_mae"][idx]
    mae = o["up_mae"][idx] if side > 0 else o["up_mfe"][idx]
    return {"idx": idx, "g": g, "net": net, "mfe": mfe, "mae": mae, "ath": o["ath"][idx], "year": o["year"][idx],
            "vol": o["vol"][idx], "trend": o["trend"][idx], "pips": net * o["pips"][idx]}


def base_stats(o: dict, H: int) -> dict:
    """Random-entry reference per period: all valid bars (forward return of the long side) - mean, sd, win rates."""
    out = {}
    for per, sel in (("is", o["year"] <= IS_END_YEAR), ("oos", o["year"] > IS_END_YEAR)):
        m = o["valid"] & sel
        g = o["gross"][m]
        cst = o["cost"][m]
        if len(g) < 50:
            out[per] = None
            continue
        out[per] = {"mean": float(np.mean(g)), "sd": float(np.std(g, ddof=1)), "n": int(len(g)),
                    "win_l": float(np.mean(g - cst > 0)), "win_s": float(np.mean(-g - cst > 0)),
                    "ev_l": float(np.mean(g - cst)), "ev_s": float(np.mean(-g - cst)), "pool": np.flatnonzero(m)}
    return out


# ----------------------------------------------------------------------
# statistics
# ----------------------------------------------------------------------

def _phi_sf(z: float) -> float:
    return 0.5 * math.erfc(z / math.sqrt(2))


def summary(a: dict, sel: np.ndarray) -> dict:
    net = a["net"][sel]
    n = len(net)
    if n == 0:
        return {"n": 0}
    pos, neg = net[net > 0].sum(), -net[net < 0].sum()
    ath = a["ath"][sel]
    return {"n": int(n), "uspechy": int((net > 0).sum()), "neuspechy": int((net <= 0).sum()),
            "win": float(np.mean(net > 0)), "ev": float(np.mean(net)), "ev_pips": float(np.mean(a["pips"][sel])),
            "median": float(np.median(net)), "hruby": float(np.mean(a["g"][sel])),
            "mfe": float(np.mean(a["mfe"][sel])), "mae": float(np.mean(a["mae"][sel])),
            "mfe_atr": float(np.mean(a["mfe"][sel] / ath)), "mae_atr": float(np.mean(a["mae"][sel] / ath)),
            "pf": float(pos / neg) if neg > 0 else None,
            "cil": float(np.mean(a["mfe"][sel] >= TARGET_K * ath)), "prah": float(np.mean(a["mae"][sel] >= TARGET_K * ath)),
            "sd": float(np.std(net, ddof=1)) if n > 1 else 0.0}


def add_test(s: dict, g: np.ndarray, side: int, mu: np.ndarray, sd: np.ndarray) -> None:
    """Excess over random entries of the same pair / period / direction and its one-sided z-test (mu, sd: per
    prediction the mean and sd of the long-side forward return of all valid bars of its pair and period)."""
    if not s.get("n"):
        return
    var = sd ** 2
    exc = g - mu * side
    z = float(exc.sum() / math.sqrt(var.sum())) if var.sum() > 0 else 0.0
    s["prevyseni"] = float(exc.mean())
    s["z"] = z
    s["p"] = _phi_sf(z)


def wilson(k: int, n: int, z: float = 1.645) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def bh_qvalues(p: list[float]) -> list[float]:
    m = len(p)
    if not m:
        return []
    order = np.argsort(p)
    q = np.empty(m)
    prev = 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        prev = min(prev, p[i] * m / rank)
        q[i] = prev
    return q.tolist()


def walk_forward(a: dict) -> dict:
    yrs = sorted(set(a["year"].tolist()))
    tested, pos, vals = 0, 0, []
    for y in yrs:
        if y < WF_FIRST:
            continue
        prior = a["year"] < y
        cur = a["year"] == y
        if prior.sum() < MIN_N or a["net"][prior].mean() <= 0 or cur.sum() < 3:
            continue
        v = float(a["net"][cur].mean())
        tested += 1
        pos += v > 0
        vals.append(v)
    return {"let": tested, "kladnych": pos, "prumer": float(np.mean(vals)) if vals else None,
            "podil": pos / tested if tested else None}


def blocks(a: dict) -> list:
    out = []
    for y0, y1 in BLOCKS:
        sel = (a["year"] >= y0) & (a["year"] <= y1)
        out.append(float(a["net"][sel].mean()) if sel.sum() >= 10 else None)
    return out


def regimes(a: dict, sel: np.ndarray | None = None) -> dict:
    sel = np.ones(len(a["net"]), bool) if sel is None else sel
    out = {}
    for dim in ("vol", "trend"):
        part = {}
        for v in np.unique(a[dim][sel]) if sel.any() else []:
            m = sel & (a[dim] == v)
            if m.sum() >= 10:
                net = a["net"][m]
                sd = float(np.std(net, ddof=1)) if m.sum() > 1 else 0.0
                part[str(v)] = {"n": int(m.sum()), "ev": float(net.mean()), "win": float(np.mean(net > 0)),
                                "t": float(net.mean() / sd * math.sqrt(m.sum())) if sd > 0 else 0.0}
        out["volatilita" if dim == "vol" else "trend"] = part
    return out


def regime_note(rg: dict) -> str | None:
    notes = []
    for dim, part in rg.items():
        good = [v for v, s in part.items() if s["n"] >= MIN_N and s["ev"] > 0]
        bad = [v for v, s in part.items() if s["n"] >= MIN_N and s["ev"] <= 0]
        if good and bad:
            notes.append(f"{dim}: funguje jen při {', '.join(good)}")
    return "; ".join(notes) or None


# ----------------------------------------------------------------------
# registry
# ----------------------------------------------------------------------

def _round(v, nd=4):
    if isinstance(v, float):
        return None if not math.isfinite(v) else round(v, nd)
    if isinstance(v, dict):
        return {k: _round(x, nd) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_round(x, nd) for x in v]
    if isinstance(v, (np.floating,)):
        return _round(float(v), nd)
    if isinstance(v, (np.integer,)):
        return int(v)
    return v


KEEP = {"is": ("n", "uspechy", "neuspechy", "win", "ev", "ev_pips", "hruby", "mfe", "mae", "pf", "base_win", "prevyseni", "p"),
        "oos": ("n", "uspechy", "neuspechy", "win", "win_ci", "ev", "ev_pips", "hruby", "mfe", "mae", "mfe_atr", "mae_atr",
                "pf", "cil", "prah", "base_win", "prevyseni", "z", "p", "q", "p_perm", "ci"),
        "vse": ("n", "win", "ev", "mfe", "mae")}


def compact(r: dict) -> dict:
    """The stored rule: the user's fields (counts, win rate, average return, MFE, MAE, EV, out-of-sample,
    walk-forward, stability, credibility) without working values; regimes as [n, EV, win rate]."""
    r = dict(r)
    for per, keys in KEEP.items():
        if isinstance(r.get(per), dict):
            r[per] = {k: r[per][k] for k in keys if k in r[per]}
    r["rezimy"] = {dim: {v: [s["n"], s["ev"], s["win"]] for v, s in part.items()} for dim, part in (r.get("rezimy") or {}).items()}
    r.pop("cil_prah", None)
    r.pop("horizont_baru", None)
    return _round(r)


def load_history_hourly(pair: str) -> dict:
    import profit_lab2 as P
    s = P.series(pair)
    return {"ts": np.asarray(s["ts"], np.int64), "o": s["o"], "h": s["h"], "l": s["l"], "c": s["c"]}


def build_contexts(hourly: dict, tf: str, fund: dict, now: int | None = None, keep: int | None = None) -> dict:
    bars = {}
    for p, hb in hourly.items():
        B = bars_tf(hb, tf, now)
        if keep and len(B["c"]) > keep:
            B = {k: (v[-keep:] if isinstance(v, list) else v[-keep:]) for k, v in B.items()}
        bars[p] = B
    auxes = {p: pair_aux(p, B, fund) for p, B in bars.items()}
    add_strength(bars, auxes, tf)
    return {p: Ctx(p, tf, bars[p], auxes[p]) for p in bars}


def rule_masks(x: Ctx) -> list[tuple]:
    """(family, params, side, template id, mask) of every template applicable to the pair and timeframe."""
    out = []
    for fam in library():
        for params in fam.variants.get(x.tf, []):
            for side in applicable(fam, x.pair, x.tf, params):
                out.append((fam, params, side, tpl_id(fam, params, side), fam.fn(x, side, *params)))
    return out


def confluence(x: Ctx, masks: list[tuple]) -> np.ndarray:
    """Net direction of the families at each bar (sum over families of the sign of long minus short templates
    firing). The HEURISTIC estimate of a prediction = 50 + 5 x side x this, clipped to 30-80 %: a subjective rule of
    thumb that uses no history (its calibration is measured, never assumed)."""
    fams = sorted({f.typ for f, *_ in masks})
    tot = np.zeros(x.n)
    for t in fams:
        acc = np.zeros(x.n)
        for f, _, side, _, m in masks:
            if f.typ == t:
                acc += side * m
        tot += np.sign(acc)
    return tot


def heur_estimate(conf: float, side: int) -> int:
    return int(min(80, max(30, 50 + 5 * side * conf)))


def previous_registry() -> dict:
    if not REGISTRY.exists():
        return {}
    with gzip.open(REGISTRY, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def _cz(v: float, nd: int) -> str:
    return f"{v:.{nd}f}".replace(".", ",")


def classify(r: dict) -> tuple[str, str]:
    """Status of a rule and the reason (order matters: sample, new data, period stability, parameters, time, pairs,
    proof)."""
    i, o = r.get("is") or {}, r.get("oos") or {}
    if i.get("n", 0) < MIN_N or o.get("n", 0) < MIN_N:
        return "NEOVĚŘENÁ", f"nedostatečný historický vzorek (2012–18: {i.get('n', 0)}, 2019–26: {o.get('n', 0)}, potřeba {MIN_N})"
    if o["ev"] <= 0:
        return "NEFUNKČNÍ", f"na novějších datech 2019–26 po nákladech prodělává (průměr {_cz(o['ev'], 3)} %)"
    if o.get("prevyseni", 0) <= 0:
        return "NEFUNKČNÍ", "na novějších datech 2019–26 není lepší než náhodné vstupy ve stejném směru"
    if i["ev"] <= 0 or i.get("prevyseni", 0) <= 0:
        return "OVERFIT/NESTABILNÍ", "funguje jen v letech 2019–26, v letech 2012–18 ne"
    nb = r.get("sousede") or {}
    if nb.get("celkem", 0) >= 2 and nb["podil"] < 0.5:
        return "OVERFIT/NESTABILNÍ", f"funguje jen při přesném nastavení (sousední nastavení drží {nb['drzi']} z {nb['celkem']})"
    wf = r.get("wf") or {}
    if wf.get("let", 0) >= 3 and wf["podil"] < 0.5:
        return "OVERFIT/NESTABILNÍ", f"walk-forward: kladných jen {wf['kladnych']} z {wf['let']} let"
    bl = [b for b in r.get("bloky", []) if b is not None]
    if len(bl) >= 3 and sum(b > 0 for b in bl) < len(bl) - 1:
        return "OVERFIT/NESTABILNÍ", f"kladná jen ve {sum(b > 0 for b in bl)} ze {len(bl)} období"
    pr = r.get("pary") or {}
    if r["par"] == "VŠE" and pr.get("celkem", 0) >= 4 and pr["podil"] < 0.5:
        return "OVERFIT/NESTABILNÍ", f"funguje jen na části párů ({pr['kladnych']} z {pr['celkem']})"
    proven = (i.get("p", 1) <= 0.10 and o.get("p", 1) <= 0.05 and o.get("q", 1) <= FDR_Q
              and o.get("p_perm", 1) <= 0.05 and (o.get("ci") or [0])[0] > 0)
    if proven:
        return "AKTIVNÍ", f"prokázaná na novějších datech (p {_cz(o['p'], 4)}, po korekci na počet pravidel q {_cz(o['q'], 3)})"
    return "SLABÁ", f"kladná, ale neprokázaná (p 2019–26 {_cz(o.get('p', 1), 3)}, po korekci na počet pravidel q {_cz(o.get('q', 1), 2)})"


def credibility(r: dict) -> str:
    st = r["stav"]
    if st == "AKTIVNÍ":
        o = r["oos"]
        nb = r.get("sousede") or {}
        bl = [b for b in r.get("bloky", []) if b is not None]
        pr = r.get("pary") or {}
        strong = (o["n"] >= 200 and sum(b > 0 for b in bl) >= 3 and (nb.get("celkem", 0) < 2 or nb["podil"] >= 0.75)
                  and (pr.get("celkem", 0) < 4 or pr["podil"] >= 0.6))
        return "VYSOKÁ" if strong else "STŘEDNÍ"
    return {"SLABÁ": "NÍZKÁ", "NEOVĚŘENÁ": "NEOVĚŘENO"}.get(st, "ŽÁDNÁ")


def _perm_and_boot(arr_list: list[tuple[dict, np.ndarray, dict]], side: int, rng) -> tuple[float, list]:
    """Monte Carlo permutation (random entry bars of the same pairs and period, stratified by pair counts) and the
    bootstrap 90 % interval of the out-of-sample mean net return."""
    obs, null = [], np.zeros(PERM_DRAWS)
    total = 0
    for a, sel, (o, base) in arr_list:
        g = a["g"][sel]
        k = len(g)
        if not k:
            continue
        total += k
        obs.append(g)
        pool = o["gross"][base["pool"]] * side
        draws = rng.integers(0, len(pool), size=(PERM_DRAWS, k))
        null += pool[draws].sum(axis=1)
    g = np.concatenate(obs)
    p_perm = float((1 + np.sum(null / total >= g.mean())) / (PERM_DRAWS + 1))
    net = np.concatenate([a["net"][sel] for a, sel, _ in arr_list])
    boot = net[rng.integers(0, len(net), size=(PERM_DRAWS, len(net)))].mean(axis=1)
    return p_perm, [float(np.percentile(boot, 5)), float(np.percentile(boot, 95))]


def rule_record(rid, fam, params, side, pair, tf, arrays: list, created: dict) -> dict:
    """Statistics of one rule from its prediction arrays [(arrays, outcome, base)] (one entry per pair)."""
    a = {k: np.concatenate([x[0][k] for x in arrays]) for k in ("g", "net", "mfe", "mae", "ath", "year", "vol", "trend", "pips")}
    pair_of = np.concatenate([np.full(len(x[0]["net"]), j) for j, x in enumerate(arrays)])
    rec = {"id": rid, "sablona": tpl_id(fam, params, side), "rodina": fam.key, "typ": fam.typ, "logika": fam.logika,
           "par": pair, "tf": tf, "smer": _lr(side), "horizont": TFS[tf]["label"], "horizont_baru": TFS[tf]["H"],
           "parametry": list(params), **describe(fam, params, side),
           "vytvoreno": created.get(rid, date.today().isoformat())}
    for per, sel in (("is", a["year"] <= IS_END_YEAR), ("oos", a["year"] > IS_END_YEAR)):
        s = summary(a, sel)
        if s.get("n"):
            bs = [arrays[j][2].get(per) for j in range(len(arrays))]
            mu = np.array([b["mean"] if b else 0.0 for b in bs])[pair_of[sel]]
            sd = np.array([b["sd"] if b else 1e9 for b in bs])[pair_of[sel]]
            add_test(s, a["g"][sel], side, mu, sd)
            bw = [arrays[j][2].get(per) for j in range(len(arrays))]
            ws = [(b["win_l"] if side > 0 else b["win_s"], int((pair_of[sel] == j).sum())) for j, b in enumerate(bw) if b]
            tot = sum(w for _, w in ws)
            s["base_win"] = sum(v * w for v, w in ws) / tot if tot else None
            if per == "oos":
                s["win_ci"] = list(wilson(s["uspechy"], s["n"]))
        rec[per] = s
    rec["vse"] = summary(a, np.ones(len(a["net"]), bool))
    rec["ocekavany_vynos"] = rec["vse"].get("ev")
    rec["wf"] = walk_forward(a)
    rec["bloky"] = blocks(a)
    rec["rezimy"] = regimes(a)
    rec["rezim_poznamka"] = regime_note(rec["rezimy"])
    return rec


def build_registry(verbose: bool = True) -> dict:
    t0 = time.monotonic()
    fund = load_fund()
    pairs = list(DEFAULT_ACTIVE)
    hourly = {p: load_history_hourly(p) for p in pairs}
    prev = previous_registry()
    created = {r["id"]: r["vytvoreno"] for r in prev.get("pravidla", [])}
    rng = np.random.default_rng(20261007)
    rules, store, calib, firing = [], {}, [], {}
    data_to = None
    for tf in TFS:
        ctxs = build_contexts(hourly, tf, fund)
        for p, x in ctxs.items():
            o = outcomes(x)
            base = base_stats(o, x.H)
            masks = rule_masks(x)
            conf = confluence(x, masks)
            data_to = max(data_to or x.day[-1], x.day[-1])
            firing[(p, tf)] = (x.bars["end_ts"], masks)
            for fam, params, side, tid, m in masks:
                idx = take(m, o["valid"], x.H)
                a = pred_arrays(o, idx, side)
                a["conf"] = conf[idx]
                store[(tid, p, tf)] = (fam, params, side, a, o, base)
            # derived rules (improvement): a rule restricted to the regime in which it worked in 2012-2018 only
        if verbose:
            print(f"  {tf}: masky a predikce {time.monotonic() - t0:.0f} s", flush=True)
    # pair-level rules
    for (tid, p, tf), (fam, params, side, a, o, base) in store.items():
        rid = f"{tid}|{p.replace('/', '')}|{tf}"
        rec = rule_record(rid, fam, params, side, p, tf, [(a, o, base)], created)
        rules.append(rec)
    by_id = {r["id"]: r for r in rules}
    # neighbours and other pairs (pair level)
    for r in rules:
        fam = _family(r["rodina"])
        side = 1 if r["smer"] == "LONG" else -1
        nbs = neighbours(fam, r["tf"], tuple(r["parametry"]))
        vals = []
        for nb in nbs:
            nr = by_id.get(f"{tpl_id(fam, nb, side)}|{r['par'].replace('/', '')}|{r['tf']}")
            if nr and (nr.get("oos") or {}).get("n", 0) >= 10:
                vals.append(nr["oos"]["ev"] > 0)
        r["sousede"] = {"celkem": len(vals), "drzi": int(sum(vals)), "podil": sum(vals) / len(vals) if vals else None}
        same = [by_id.get(f"{r['sablona']}|{q.replace('/', '')}|{r['tf']}") for q in pairs]
        ok = [s["oos"]["ev"] > 0 for s in same if s and (s.get("oos") or {}).get("n", 0) >= 20]
        r["pary"] = {"celkem": len(ok), "kladnych": int(sum(ok)), "podil": sum(ok) / len(ok) if ok else None}
    # pooled rules (all pairs)
    pooled = {}
    for (tid, p, tf), v in store.items():
        pooled.setdefault((tid, tf), []).append((p, v))
    for (tid, tf), items in pooled.items():
        fam, params, side = items[0][1][:3]
        arrays = [(v[3], v[4], v[5]) for _, v in items]
        rec = rule_record(f"{tid}|VSE|{tf}", fam, params, side, "VŠE", tf, arrays, created)
        vals = []
        for nb in neighbours(fam, tf, params):
            sub = pooled.get((tpl_id(fam, nb, side), tf))
            if sub:
                net = np.concatenate([v[3]["net"][v[3]["year"] > IS_END_YEAR] for _, v in sub])
                if len(net) >= 10:
                    vals.append(net.mean() > 0)
        rec["sousede"] = {"celkem": len(vals), "drzi": int(sum(vals)), "podil": sum(vals) / len(vals) if vals else None}
        pr = [by_id[f"{tid}|{p.replace('/', '')}|{tf}"] for p, _ in items]
        ok = [s["oos"]["ev"] > 0 for s in pr if (s.get("oos") or {}).get("n", 0) >= 20]
        rec["pary"] = {"celkem": len(ok), "kladnych": int(sum(ok)), "podil": sum(ok) / len(ok) if ok else None}
        rules.append(rec)
        by_id[rec["id"]] = rec
    # derived rules: regime restriction chosen on 2012-2018 only, judged on 2019 ->
    derived = []
    for (tid, p, tf), (fam, params, side, a, o, base) in list(store.items()):
        sel_is = a["year"] <= IS_END_YEAR
        if sel_is.sum() < 100:
            continue
        rg = regimes(a, sel_is)
        for dim, key in (("volatilita", "vol"), ("trend", "trend")):
            part = rg.get(dim, {})
            good = [v for v, s in part.items() if s["n"] >= MIN_N and s["ev"] > 0 and s["t"] >= 2.0]
            rest_bad = [v for v, s in part.items() if s["n"] >= MIN_N and s["ev"] <= 0]
            if len(good) != 1 or not rest_bad:
                continue
            v = good[0]
            full_mask = next(m for f, pp, sd, t2, m in firing[(p, tf)][1] if t2 == tid)
            m2 = full_mask & (o[key] == v)
            idx = take(m2, o["valid"], TFS[tf]["H"])
            a2 = pred_arrays(o, idx, side)
            rid = f"{tid}+{key}={v}|{p.replace('/', '')}|{tf}"
            rec = rule_record(rid, fam, params, side, p, tf, [(a2, o, base)], created)
            rec["podminka"] += f" a režim {dim}: {v}"
            rec["puvod"] = f"odvozeno z {tid} (režim vybraný jen na letech 2012–18)"
            rec["rezim_filtr"] = [key, v]
            rec["sousede"] = {"celkem": 0, "drzi": 0, "podil": None}
            rec["pary"] = by_id[f"{tid}|{p.replace('/', '')}|{tf}"]["pary"]
            derived.append(rec)
            store[(f"{tid}+{key}={v}", p, tf)] = (fam, params, side, a2, o, base)
    rules += derived
    by_id.update({r["id"]: r for r in derived})
    if verbose:
        print(f"  pravidel {len(rules)} (odvozených {len(derived)}), statistiky {time.monotonic() - t0:.0f} s", flush=True)
    # false discovery rate over every judged rule, then permutation + bootstrap for the candidates
    judged = [r for r in rules if (r.get("oos") or {}).get("n", 0) >= MIN_N and "p" in r["oos"]]
    for r, q in zip(judged, bh_qvalues([r["oos"]["p"] for r in judged])):
        r["oos"]["q"] = q
    chance = {"posouzeno": len(judged), "p05": sum(r["oos"]["p"] <= 0.05 for r in judged),
              "q10": sum(r["oos"]["q"] <= FDR_Q for r in judged)}
    for r in judged:
        o_ = r["oos"]
        if not (o_["p"] <= 0.05 and o_["q"] <= FDR_Q and o_["ev"] > 0):
            continue
        side = 1 if r["smer"] == "LONG" else -1
        key = r["id"].split("|")[0]
        items = ([(p, store[(key, p, r["tf"])]) for p in pairs if (key, p, r["tf"]) in store] if r["par"] == "VŠE"
                 else [(r["par"], store[(key, r["par"], r["tf"])])])
        arr = [(v[3], v[3]["year"] > IS_END_YEAR, (v[4], v[5]["oos"])) for _, v in items if v[5].get("oos")]
        o_["p_perm"], o_["ci"] = _perm_and_boot(arr, side, rng)
    # live results and statuses
    live = live_by_rule()
    prev_status = {r["id"]: r.get("stav") for r in prev.get("pravidla", [])}
    changes = []
    for r in rules:
        st, why = classify(r)
        lv = live.get(r["id"])
        if lv:
            r["zive"] = lv
            if lv["n"] >= LIVE_MIN_N and st in ("AKTIVNÍ", "SLABÁ") and (r.get("oos") or {}).get("win"):
                p_low = binom_cdf(lv["uspechy"], lv["n"], r["oos"]["win"])
                lv["p_horsi"] = p_low
                if p_low < 0.05:
                    st, why = ("SLABÁ" if st == "AKTIVNÍ" else "NEFUNKČNÍ"), (
                        f"živě výrazně horší než historie ({lv['uspechy']} z {lv['n']} proti očekávaným "
                        f"{r['oos']['win'] * 100:.0f} %)")
        r["stav"], r["duvod"] = st, why
        r["duveryhodnost"] = credibility(r)
        old = prev_status.get(r["id"])
        if old != st:
            changes.append({"den": date.today().isoformat(), "id": r["id"], "z": old, "na": st, "duvod": why})
    # calibration of the two probabilities on 2019 -> (pair-level base rules; statistical = 2012-18 win rate)
    cal = calibration(rules, store)
    agree = main_model_agreement(rules, store, firing)
    reg = {"vytvoreno": datetime.now(UTC).isoformat(timespec="minutes"), "data_do": data_to.isoformat() if data_to else None,
           "metodika": {"is": f"2012–{IS_END_YEAR}", "oos": f"{IS_END_YEAR + 1}–", "min_n": MIN_N, "fdr_q": FDR_Q,
                        "cil_prah": f"cíl a práh ±{TARGET_K:g} × ATR14 × √horizont od vstupu",
                        "horizonty": {tf: v["label"] for tf, v in TFS.items()}},
           "nahoda": chance, "kalibrace": _round(cal), "hlavni_model": _round(agree),
           "pravidla": [compact(r) for r in rules]}
    DIR.mkdir(parents=True, exist_ok=True)
    with gzip.open(REGISTRY, "wt", encoding="utf-8") as fh:
        json.dump(reg, fh, ensure_ascii=False, separators=(",", ":"))
    if changes and prev:
        with STATUS_LOG.open("a", encoding="utf-8") as fh:
            for c in changes:
                fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    write_report(reg, changes if prev else [])
    if verbose:
        cnt = {s: sum(r["stav"] == s for r in rules) for s in STATUSES}
        print(f"registr: {len(rules)} pravidel {cnt} | zmen stavu {len(changes) if prev else 0} | "
              f"{time.monotonic() - t0:.0f} s")
    return reg


def binom_cdf(k: int, n: int, p: float) -> float:
    """P(X <= k) for X ~ Binomial(n, p)."""
    p = min(max(p, 1e-9), 1 - 1e-9)
    return float(sum(math.comb(n, j) * p ** j * (1 - p) ** (n - j) for j in range(k + 1)))


def calibration(rules: list[dict], store: dict) -> dict:
    """Do the probabilities match reality on 2019 -> ? Statistical = the rule's 2012-18 win rate (known before),
    heuristic = the confluence rule of thumb. Buckets and Brier scores (lower = better)."""
    by_id = {r["id"]: r for r in rules}
    st_p, he_p, hit = [], [], []
    for (tid, p, tf), (fam, params, side, a, o, base) in store.items():
        if "+" in tid or "conf" not in a:
            continue
        r = by_id.get(f"{tid}|{p.replace('/', '')}|{tf}")
        if not r or (r.get("is") or {}).get("n", 0) < MIN_N:
            continue
        sel = a["year"] > IS_END_YEAR
        if not sel.any():
            continue
        st_p.append(np.full(sel.sum(), r["is"]["win"]))
        he_p.append(np.clip(50 + 5 * side * a["conf"][sel], 30, 80) / 100)
        hit.append((a["net"][sel] > 0).astype(float))
    if not hit:
        return {}
    st_p, he_p, hit = np.concatenate(st_p), np.concatenate(he_p), np.concatenate(hit)

    def buckets(prob, edges):
        out = []
        for lo, hi in zip(edges[:-1], edges[1:]):
            m = (prob >= lo) & (prob < hi)
            if m.sum() >= 50:
                out.append({"od": lo, "do": hi, "n": int(m.sum()), "ocekavano": float(prob[m].mean()),
                            "skutecnost": float(hit[m].mean())})
        return out
    return {"n": int(len(hit)), "uspesnost": float(hit.mean()),
            "brier_stat": float(np.mean((st_p - hit) ** 2)), "brier_heur": float(np.mean((he_p - hit) ** 2)),
            "brier_mince": float(np.mean((0.5 - hit) ** 2)),
            "stat": buckets(st_p, [0, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 1.01]),
            "heur": buckets(he_p, [0.3, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.8001])}


def main_model_agreement(rules: list[dict], store: dict, firing: dict) -> dict:
    """Does agreement of the heuristics with the main model's trades add value? Main model = the monthly champion's
    trades 2019 -> (all tiers with a share). Heuristics counted = pair-level base rules that were good on 2012-18
    alone (profit after costs, p <= 0.05) - no knowledge of 2019 ->. Votes by family at the last bar that closed
    before the trade's entry; SHODA / PROTI / BEZ NÁZORU by the net families."""
    try:
        import self_learn as SLR
        champ = json.loads((PROJECT_ROOT / "learning" / "champion_12_mesicne.json").read_text())
        lists = SLR.trade_lists(champ["config"])
        shares = champ["eval"]["1"]["shares"]
    except Exception as exc:
        return {"chyba": f"obchody hlavního modelu nedostupné ({type(exc).__name__})"}
    good = {}
    for r in rules:
        i = r.get("is") or {}
        if r["par"] != "VŠE" and "+" not in r["id"] and i.get("n", 0) >= MIN_N and i["ev"] > 0 and i.get("p", 1) <= 0.05:
            good[(r["sablona"], r["par"], r["tf"])] = (r["typ"], 1 if r["smer"] == "LONG" else -1)
    rows = []
    for tl, sh in zip(lists, shares):
        if sh <= 0:
            continue
        for t in tl:
            if t["day"].year <= IS_END_YEAR:
                continue
            votes = {}
            for tf in TFS:
                ends, masks = firing.get((t["pair"], tf), (None, None))
                if ends is None:
                    continue
                k = int(np.searchsorted(ends, t["t_in"], side="right") - 1)
                if k < 0:
                    continue
                for fam, params, side, tid, m in masks:
                    g = good.get((tid, t["pair"], tf))
                    if g and m[k]:
                        votes[g[0]] = votes.get(g[0], 0) + side * t["side"]
            net = sum(np.sign(v) for v in votes.values())
            rows.append(("SHODA" if net > 0 else "PROTI" if net < 0 else "BEZ NÁZORU", t["margin_pct"] > 0, t["margin_pct"]))
    if not rows:
        return {"chyba": "žádné obchody 2019–26"}
    cats = {}
    for c in ("SHODA", "BEZ NÁZORU", "PROTI"):
        x = [r for r in rows if r[0] == c]
        if x:
            cats[c] = {"n": len(x), "uspesnost": float(np.mean([r[1] for r in x])), "prumer_marze": float(np.mean([r[2] for r in x]))}
    # permutation test: is the SHODA group better than the rest by chance?
    p = None
    lab = np.array([r[0] == "SHODA" for r in rows])
    val = np.array([r[2] for r in rows])
    if 10 <= lab.sum() <= len(lab) - 10:
        obs = val[lab].mean() - val[~lab].mean()
        rng = np.random.default_rng(7)
        null = np.array([(lambda pm: val[pm].mean() - val[~pm].mean())(rng.permutation(lab)) for _ in range(PERM_DRAWS)])
        p = float((1 + np.sum(null >= obs)) / (PERM_DRAWS + 1))
    adds = bool(p is not None and p <= 0.05 and cats.get("SHODA", {}).get("prumer_marze", -1e9) > cats.get("PROTI", {}).get("prumer_marze", 1e9))
    return {"obchodu": len(rows), "skupiny": cats, "p": p, "pridava_hodnotu": adds,
            "zaver": ("Shoda heuristik s hlavním modelem historicky přidávala hodnotu." if adds else
                      "Shoda heuristik s hlavním modelem historicky NEPŘIDÁVALA hodnotu – důvěru v signál nezvyšuje.")}


# ----------------------------------------------------------------------
# prediction ledger (append-only, hash chain) and live evaluation
# ----------------------------------------------------------------------

def _hash(rec: dict, prev: str) -> str:
    body = json.dumps({k: v for k, v in rec.items() if k != "hash"}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256((prev + body).encode("utf-8")).hexdigest()


def _read_chain(folder: Path) -> list[dict]:
    out = []
    for f in sorted(folder.glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(json.loads(line))
    return out


def _append(folder: Path, recs: list[dict], month: str) -> None:
    if not recs:
        return
    folder.mkdir(parents=True, exist_ok=True)
    prev = ""
    for f in sorted(folder.glob("*.jsonl"), reverse=True):
        lines = [x for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]
        if lines:
            prev = json.loads(lines[-1])["hash"]
            break
    with (folder / f"{month}.jsonl").open("a", encoding="utf-8") as fh:
        for r in recs:
            r["hash_pred"] = prev
            r["hash"] = _hash(r, prev)
            prev = r["hash"]
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def verify_ledger() -> dict:
    """Integrity: every record's hash matches its content and the previous record (no edit, no deletion inside the
    chain); every evaluation belongs to a prediction and is the only one for it."""
    problems = []
    preds, evals = _read_chain(PRED_DIR), _read_chain(EVAL_DIR)
    for name, chain in (("predikce", preds), ("vyhodnoceni", evals)):
        prev = ""
        for k, r in enumerate(chain):
            if r.get("hash_pred") != prev or _hash(r, prev) != r.get("hash"):
                problems.append(f"{name}: záznam {k + 1} ({r.get('id')}) nesedí s řetězcem – byl změněn nebo smazán záznam před ním")
                break
            prev = r["hash"]
    ids = {p["id"] for p in preds}
    seen = set()
    for e in evals:
        if e["id"] not in ids:
            problems.append(f"vyhodnocení bez predikce: {e['id']}")
        if e["id"] in seen:
            problems.append(f"predikce vyhodnocena dvakrát: {e['id']}")
        seen.add(e["id"])
    return {"predikci": len(preds), "vyhodnoceno": len(evals), "problemy": problems}


def live_by_rule() -> dict:
    preds = {p["id"]: p for p in _read_chain(PRED_DIR)}
    out = {}
    for e in _read_chain(EVAL_DIR):
        if e.get("vysledek") not in ("ÚSPĚCH", "NEÚSPĚCH"):
            continue
        rid = preds.get(e["id"], {}).get("pravidlo")
        if not rid:
            continue
        s = out.setdefault(rid, {"n": 0, "uspechy": 0, "soucet": 0.0})
        s["n"] += 1
        s["uspechy"] += e["vysledek"] == "ÚSPĚCH"
        s["soucet"] += e["vynos_proc"]
    for s in out.values():
        s["ev"] = s.pop("soucet") / s["n"]
    return out


def live_hourly(cache: dict | None = None) -> dict:
    """Hourly prices per pair for the live step: the FXCM history followed by Yahoo (the signals' download, reused)."""
    import signals_live as SLV
    import tydenni_analyza as T
    out = {}
    for p in DEFAULT_ACTIVE:
        try:
            recent = (cache or {}).get(p) or SLV.yahoo_hourly(SLV.YAHOO[p], "2y")
            hb, _ = T.history_1h(p, recent)
            keep = hb["ts"] >= int(time.time()) - 5 * 365 * 86400
            out[p] = {k: (v[keep] if isinstance(v, np.ndarray) and len(v) == len(keep) else v) for k, v in hb.items()}
        except Exception as exc:
            print(f"heuristiky: {p} ceny nedostupne ({type(exc).__name__})", file=sys.stderr)
    return out


def _reason(side: int, net: float, ath: float, first: str | None, events: list[str], exp: float | None) -> str:
    parts = [f"cena šla {'podle předpovědi' if net > 0 else 'proti předpovědi'} ({net:+.2f} % po nákladech)"]
    if abs(net) > 2 * TARGET_K * ath:
        parts.append("pohyb byl neobvykle velký (víc než typický pohyb za horizont)")
    if first == "PRÁH":
        parts.append("nejdřív zasáhla práh proti směru")
    elif first == "CÍL":
        parts.append("nejdřív dosáhla cíle")
    if events:
        parts.append("během horizontu: " + ", ".join(events))
    if exp is not None:
        parts.append(f"historie čekala {exp:+.2f} %")
    return "; ".join(parts) + ". Možné souvislosti, ne prokázané příčiny."


def _events_between(pair: str, d0: date, d1: date, fund: dict) -> list[str]:
    import fundamenty as F
    b, q = pair.split("/")
    names = {"FED": "rozhodnutí Fedu", "ECB": "rozhodnutí ECB", "BOJ": "rozhodnutí BoJ", "BOE": "rozhodnutí BoE",
             "US_NFP": "US NFP", "US_CPI": "US CPI"}
    out = []
    for key, label in names.items():
        ccy = "USD" if key.startswith("US_") else next((c for c, k in F.CB_OF.items() if k == key), None)
        if ccy not in (b, q):
            continue
        for d in sorted(fund["events"].get(key, set())):
            if d0 <= d <= d1:
                out.append(f"{label} {d.day}. {d.month}.")
    return out


def main_model_view(state: dict | None) -> dict:
    """Main model: open forward-test trades and this week's signals per pair (direction +1 / -1)."""
    out = {}
    try:
        fw = json.loads((PROJECT_ROOT / "learning" / "forward_trades.json").read_text())
        for t in fw:
            if t.get("stav") == "otevreny":
                out[t["par"]] = 1 if t["smer"] == "KOUPIT" else -1
    except Exception:
        pass
    for s in (state or {}).get("signaly", []):
        out[s["par"]] = 1 if s["smer"] == "KOUPIT" else -1
    return out


def issues(r: dict, pooled: dict | None) -> bool:
    """Does the rule issue live predictions? Not when retired (NEFUNKČNÍ, OVERFIT/NESTABILNÍ); an unverified pair rule
    (too few cases on its pair) only when the same template on all pairs together is not retired either."""
    if r["stav"] not in ISSUING:
        return False
    return r["stav"] != "NEOVĚŘENÁ" or not pooled or pooled["stav"] in ISSUING


def live(state: dict | None = None, cache: dict | None = None, now: int | None = None, hourly: dict | None = None) -> dict:
    """The live step (every hourly update): new predictions at freshly closed bars, evaluation of predictions whose
    horizon ended, self-evaluation and the dashboard section. Returns stav["heuristiky"]."""
    now = int(time.time()) if now is None else now
    if not REGISTRY.exists():
        return {"chyba": "Registr pravidel ještě není spočítaný (python scripts/heuristiky.py prepocet) – NEOVĚŘENO."}
    reg = previous_registry()
    rules = {r["id"]: r for r in reg["pravidla"]}
    fund = load_fund()
    hourly = hourly if hourly is not None else live_hourly(cache)
    st = json.loads(LIVE_STATE.read_text()) if LIVE_STATE.exists() else {"posledni_svicka": {}, "zmeskano": 0}
    preds = _read_chain(PRED_DIR)
    done = {e["id"] for e in _read_chain(EVAL_DIR)}
    open_ = [p for p in preds if p["id"] not in done]
    open_rules = {p["pravidlo"] for p in open_}
    mm = main_model_view(state)
    new, evals, now_view = [], [], {}
    month = datetime.fromtimestamp(now, tz=UTC).strftime("%Y-%m-%d")       # one file per day (small git commits)
    bars_by = {}
    for tf in TFS:
        ctxs = build_contexts(hourly, tf, fund, now, LIVE_BARS[tf])
        for p, x in ctxs.items():
            if x.n < WARM + 5:
                continue
            bars_by[(p, tf)] = x
            masks = rule_masks(x)
            conf = confluence(x, masks)
            k = x.n - 1
            end = int(x.bars["end_ts"][k])
            key = f"{p}|{tf}"
            fresh = st["posledni_svicka"].get(key) != end
            on_time = now - end <= TFS[tf]["delay"]
            if fresh and not on_time and key in st["posledni_svicka"]:
                st["zmeskano"] = st.get("zmeskano", 0) + 1          # an update was missed: no back-dating
            if fresh:
                st["posledni_svicka"][key] = end
            o = outcomes(x)
            reg_k = {"volatilita": str(o["vol"][k]), "trend": str(o["trend"][k])}
            entry = float(hourly[p]["c"][-1])
            ath = float(o["ath"][k])
            firing = []
            for fam, params, side, tid, m in masks:
                for rid in (f"{tid}|{p.replace('/', '')}|{tf}",) + tuple(
                        r for r in (f"{tid}+vol={reg_k['volatilita']}|{p.replace('/', '')}|{tf}",
                                    f"{tid}+trend={reg_k['trend']}|{p.replace('/', '')}|{tf}") if r in rules):
                    r = rules.get(rid)
                    if not r or not m[k]:
                        continue
                    firing.append((r, side))
            now_view[(p, tf)] = {"cas": end, "firing": [(r["id"], s) for r, s in firing], "conf": float(conf[k])}
            if not (fresh and on_time):
                continue
            pooled_of = lambda r: rules.get(f"{r['sablona']}|VSE|{tf}")                    # noqa: E731
            for r, side in firing:
                if not issues(r, pooled_of(r)) or r["id"] in open_rules:
                    continue
                oos = r.get("oos") or {}
                stat_p = oos.get("win") if oos.get("n", 0) >= MIN_N else None
                pl = pooled_of(r) or {}
                rec = {"id": f"{r['id']}@{end}", "pravidlo": r["id"], "sablona": r["sablona"], "typ": r["typ"],
                       "par": p, "tf": tf, "smer": r["smer"], "vytvoreno": datetime.fromtimestamp(now, tz=UTC).isoformat(timespec="minutes"),
                       "cas": now, "cas_svicky": end, "cena": round(entry, 6), "horizont_baru": TFS[tf]["H"],
                       "horizont": TFS[tf]["label"],
                       "cil": round(entry * (1 + side * TARGET_K * ath / 100), 6),
                       "prah": round(entry * (1 - side * TARGET_K * ath / 100), 6), "atr_h_proc": round(ath, 4),
                       "ocekavany_vynos_proc": r.get("ocekavany_vynos"),
                       "stat_pravdepodobnost": stat_p, "heur_odhad": heur_estimate(conf[k], side),
                       "stav_pravidla": r["stav"], "duveryhodnost": r["duveryhodnost"],
                       "vse_pary": {"stav": pl.get("stav"), "win_oos": (pl.get("oos") or {}).get("win")},
                       "rezim": reg_k, "hlavni_model": (None if p not in mm else "SHODA" if mm[p] == side else "PROTI"),
                       "registr": reg["vytvoreno"]}
                new.append(rec)
                open_rules.add(r["id"])
    # evaluation of predictions whose horizon has ended
    for pr in open_:
        x = bars_by.get((pr["par"], pr["tf"]))
        if x is None:
            continue
        ends = x.bars["end_ts"]
        after = np.flatnonzero(ends > pr["cas_svicky"])
        if len(after) < pr["horizont_baru"]:
            if now - pr["cas"] > 40 * 86400:
                evals.append({"id": pr["id"], "vyhodnoceno": datetime.fromtimestamp(now, tz=UTC).isoformat(timespec="minutes"),
                              "vysledek": "NEOVĚŘENO", "duvod": "chybí ceny pro celý horizont"})
            continue
        j = after[pr["horizont_baru"] - 1]
        hb = hourly[pr["par"]]
        win = (hb["ts"] >= pr["cas"] // 3600 * 3600) & (hb["ts"] + 3600 <= ends[j])
        if not win.any():
            continue
        side = 1 if pr["smer"] == "LONG" else -1
        exit_px = float(x.c[j])
        hh, ll = float(hb["h"][win].max()), float(hb["l"][win].min())
        gross = side * (exit_px / pr["cena"] - 1) * 100
        net = gross - float(cost_pct(pr["par"], np.array([pr["cena"]]))[0])
        mfe = ((hh / pr["cena"] - 1) if side > 0 else (1 - ll / pr["cena"])) * 100
        mae = ((1 - ll / pr["cena"]) if side > 0 else (hh / pr["cena"] - 1)) * 100
        hit_t = (hh >= pr["cil"]) if side > 0 else (ll <= pr["cil"])
        hit_s = (ll <= pr["prah"]) if side > 0 else (hh >= pr["prah"])
        first = None
        if hit_t or hit_s:
            for hi_, lo_ in zip(hb["h"][win], hb["l"][win]):
                t_ = (hi_ >= pr["cil"]) if side > 0 else (lo_ <= pr["cil"])
                s_ = (lo_ <= pr["prah"]) if side > 0 else (hi_ >= pr["prah"])
                if t_ and s_:
                    first = "NEJASNÉ"
                    break
                if t_ or s_:
                    first = "CÍL" if t_ else "PRÁH"
                    break
        d0 = datetime.fromtimestamp(pr["cas"], tz=NY).date()
        d1 = x.day[j]
        exp = pr.get("ocekavany_vynos_proc")
        evals.append({"id": pr["id"], "vyhodnoceno": datetime.fromtimestamp(now, tz=UTC).isoformat(timespec="minutes"),
                      "konec": int(ends[j]), "cena_konec": round(exit_px, 6), "max": round(hh, 6), "min": round(ll, 6),
                      "hruby_proc": round(gross, 4), "vynos_proc": round(net, 4), "mfe_proc": round(mfe, 4),
                      "mae_proc": round(mae, 4), "vysledek": "ÚSPĚCH" if net > 0 else "NEÚSPĚCH",
                      "cil_zasazen": bool(hit_t), "prah_zasazen": bool(hit_s), "prvni": first,
                      "odchylka_proc": None if exp is None else round(net - exp, 4),
                      "duvod": _reason(side, net, pr["atr_h_proc"], first, _events_between(pr["par"], d0, d1, fund), exp)})
    _append(PRED_DIR, new, month)
    _append(EVAL_DIR, evals, month)
    DIR.mkdir(parents=True, exist_ok=True)
    LIVE_STATE.write_text(json.dumps(st, indent=1, ensure_ascii=False))
    return dashboard(reg, now_view, bars_by, mm, state, len(new), len([e for e in evals if e.get("vysledek") != "NEOVĚŘENO"]))


# ----------------------------------------------------------------------
# self-evaluation and the dashboard section
# ----------------------------------------------------------------------

def window_stats(rows: list[tuple[dict, dict]]) -> dict:
    """rows: (prediction, evaluation) of evaluated predictions, oldest first."""
    if not rows:
        return {"n": 0}
    net = np.array([e["vynos_proc"] for _, e in rows])
    pos, neg = net[net > 0].sum(), -net[net < 0].sum()
    hit = (net > 0).astype(float)
    sp = np.array([p["stat_pravdepodobnost"] if p.get("stat_pravdepodobnost") is not None else np.nan for p, _ in rows])
    hp = np.array([p["heur_odhad"] / 100 for p, _ in rows])
    dev = [abs(e["odchylka_proc"]) for _, e in rows if e.get("odchylka_proc") is not None]
    ok = ~np.isnan(sp)
    return {"n": len(rows), "uspesnost": float(hit.mean()), "pf": float(pos / neg) if neg > 0 else None,
            "ev": float(net.mean()), "chyba": float(np.mean(dev)) if dev else None,
            "falesne_pozitivni": int((net <= 0).sum()),
            "mfe": float(np.mean([e["mfe_proc"] for _, e in rows])), "mae": float(np.mean([e["mae_proc"] for _, e in rows])),
            "brier_stat": float(np.mean((sp[ok] - hit[ok]) ** 2)) if ok.any() else None,
            "brier_heur": float(np.mean((hp - hit) ** 2))}


def false_negatives(bars_by: dict, preds: list[dict], since: int) -> dict:
    """Missed moves since the live start: horizon windows starting at each closed bar with a move > the typical
    move (ATR14 x sqrt(horizon)) and no live prediction in that direction made at that bar."""
    made = {}
    for p in preds:
        made.setdefault((p["par"], p["tf"], p["cas_svicky"]), set()).add(1 if p["smer"] == "LONG" else -1)
    big = miss = 0
    for (p, tf), x in bars_by.items():
        H = TFS[tf]["H"]
        ends = x.bars["end_ts"]
        for i in np.flatnonzero(ends >= since):
            if i + H >= x.n:
                break
            mv = (x.c[i + H] / x.c[i] - 1) * 100
            ath = x.atr[i] * math.sqrt(H) / x.c[i] * 100
            if abs(mv) > ath:
                big += 1
                miss += int(np.sign(mv)) not in made.get((p, tf, int(ends[i])), set())
    return {"velkych_pohybu": big, "nepredpovezeno": miss, "podil": miss / big if big else None}


def _card(p: dict, r: dict | None) -> dict:
    """An open live prediction for the dashboard: the frozen values of the prediction and the rule's record now."""
    i, o = ((r or {}).get("is") or {}), ((r or {}).get("oos") or {})
    return {"id": p["id"], "par": p["par"], "tf": p["tf"], "smer": p["smer"], "horizont": p["horizont"], "cas": p["cas"],
            "cena": p["cena"], "cil": p["cil"], "prah": p["prah"], "heur_odhad": p["heur_odhad"],
            "stat_pravdepodobnost": p["stat_pravdepodobnost"], "stav_pri_vzniku": p["stav_pravidla"],
            "stav": (r or {}).get("stav", "není v registru"), "duvod": (r or {}).get("duvod"),
            "duveryhodnost": (r or {}).get("duveryhodnost", "ŽÁDNÁ"), "podminka": (r or {}).get("podminka", p["pravidlo"]),
            "typ": TYP_CZ.get(p["typ"], p["typ"]), "pravidlo": p["pravidlo"], "win_hist": i.get("win"), "n_is": i.get("n", 0),
            "win_oos": o.get("win"), "win_ci": o.get("win_ci"), "n_oos": o.get("n", 0), "ev_oos": o.get("ev"),
            "base_win_oos": o.get("base_win"), "vse_pary": p.get("vse_pary"), "hlavni_model": p.get("hlavni_model"),
            "rezim": p.get("rezim")}


def dashboard(reg: dict, now_view: dict, bars_by: dict, mm: dict, state: dict | None, n_new: int, n_eval: int) -> dict:
    rules = {r["id"]: r for r in reg["pravidla"]}
    preds = _read_chain(PRED_DIR)
    evals = {e["id"]: e for e in _read_chain(EVAL_DIR)}
    done = [(p, evals[p["id"]]) for p in preds if p["id"] in evals and evals[p["id"]].get("vysledek") in ("ÚSPĚCH", "NEÚSPĚCH")]
    done.sort(key=lambda pe: pe[1].get("konec", 0))
    open_ = [p for p in preds if p["id"] not in evals]
    # open live predictions (frozen when made) with the rule's record now; rules firing now by status
    order = {s: k for k, s in enumerate(STATUSES)}
    cred = {"VYSOKÁ": 0, "STŘEDNÍ": 1, "NÍZKÁ": 2, "NEOVĚŘENO": 3, "ŽÁDNÁ": 4}
    shown = [_card(p, rules.get(p["pravidlo"])) for p in open_]
    shown.sort(key=lambda c: (order.get(c["stav"], 9), cred.get(c["duveryhodnost"], 9), -(c["ev_oos"] or -9), -c["cas"]))
    firing_now = {s: 0 for s in STATUSES}
    for v in now_view.values():
        for rid, _ in v["firing"]:
            firing_now[rules[rid]["stav"]] += 1
    windows = {}
    for w in (20, 50, 100, 500):
        if len(done) >= w:
            windows[str(w)] = window_stats(done[-w:])
    windows["vse"] = window_stats(done)

    def split(keyf):
        out = {}
        for p, e in done:
            out.setdefault(keyf(p), []).append((p, e))
        return {k: window_stats(v) for k, v in out.items()}
    started = min([p["cas"] for p in preds], default=None)
    pr_rules = [r for r in reg["pravidla"] if "+" not in r["id"]]
    counts = {}
    for r in reg["pravidla"]:
        c = counts.setdefault(f"{r['tf']}|{'VŠE' if r['par'] == 'VŠE' else 'páry'}", {s: 0 for s in STATUSES})
        c[r["stav"]] += 1
    by_type = {}
    for r in pr_rules:
        if r["par"] == "VŠE":
            continue
        t = by_type.setdefault(TYP_CZ.get(r["typ"], r["typ"]), {"pravidel": 0, **{s: 0 for s in STATUSES}, "ev": []})
        t["pravidel"] += 1
        t[r["stav"]] += 1
        if (r.get("oos") or {}).get("n", 0) >= MIN_N:
            t["ev"].append(r["oos"]["ev"])
    for t in by_type.values():
        ev = t.pop("ev")
        t["kladnych_oos"] = float(np.mean(np.array(ev) > 0)) if ev else None
    best = sorted([r for r in reg["pravidla"] if r["stav"] == "AKTIVNÍ"], key=lambda r: -r["oos"]["ev"])
    weak = sorted([r for r in reg["pravidla"] if r["stav"] == "SLABÁ" and r["par"] == "VŠE"], key=lambda r: -r["oos"]["ev"])

    def row(r):
        i, o = r.get("is") or {}, r.get("oos") or {}
        return {"id": r["id"], "podminka": r["podminka"], "typ": TYP_CZ.get(r["typ"], r["typ"]), "par": r["par"], "tf": r["tf"],
                "smer": r["smer"], "n_is": i.get("n"), "win_is": i.get("win"), "n_oos": o.get("n"), "win_oos": o.get("win"),
                "base_win_oos": o.get("base_win"), "ev_oos": o.get("ev"), "q": o.get("q"), "stav": r["stav"],
                "duvod": r["duvod"], "duveryhodnost": r["duveryhodnost"]}
    changes = []
    if STATUS_LOG.exists():
        changes = [json.loads(x) for x in STATUS_LOG.read_text(encoding="utf-8").splitlines()[-30:] if x.strip()]
    # main model's live signals: heuristic votes now (information only)
    signals = []
    for s in (state or {}).get("signaly", []):
        side = 1 if s["smer"] == "KOUPIT" else -1
        pro = proti = 0
        for tf in TFS:
            for rid, sd in now_view.get((s["par"], tf), {}).get("firing", []):
                if rules[rid]["stav"] in ("AKTIVNÍ", "SLABÁ"):
                    pro += sd == side
                    proti += sd != side
        signals.append({"par": s["par"], "smer": s["smer"], "pro": pro, "proti": proti})
    fw = []
    try:
        fw = json.loads((PROJECT_ROOT / "learning" / "forward_trades.json").read_text())
    except Exception:
        pass
    closed = [t for t in fw if t.get("stav") == "uzavreny"]
    ledger = verify_ledger()
    return {
        "registr": {"vytvoreno": reg["vytvoreno"], "data_do": reg["data_do"], "pravidel": len(reg["pravidla"]),
                    "pocty": counts, "metodika": reg["metodika"], "nahoda": reg.get("nahoda")},
        "predikce": shown[:60], "otevrene": len(open_),
        "otevrene_podle_stavu": {s: sum(c["stav"] == s for c in shown) for s in STATUSES},
        "plati_ted": firing_now, "nove": n_new, "vyhodnocene_ted": n_eval,
        "posledni_vyhodnocene": [{"par": p["par"], "tf": p["tf"], "smer": p["smer"], "pravidlo": p["pravidlo"],
                                  "stav_pravidla": p["stav_pravidla"], "vysledek": e["vysledek"], "vynos_proc": e["vynos_proc"],
                                  "duvod": e["duvod"], "konec": e.get("konec")} for p, e in done[-15:][::-1]],
        "sebehodnoceni": {"okna": windows, "od": started,
                          "podle_paru": split(lambda p: p["par"]), "podle_tf": split(lambda p: p["tf"]),
                          "podle_typu": split(lambda p: TYP_CZ.get(p["typ"], p["typ"])),
                          "podle_volatility": split(lambda p: p["rezim"]["volatilita"]),
                          "podle_trendu": split(lambda p: p["rezim"]["trend"]),
                          "podle_stavu": split(lambda p: p["stav_pravidla"]),
                          "podle_hlavniho_modelu": split(lambda p: p.get("hlavni_model") or "bez obchodu"),
                          "falesne_negativni": false_negatives(bars_by, preds, started) if started else None},
        "kalibrace": reg.get("kalibrace"),
        "hlavni_model": {"historie": reg.get("hlavni_model"), "signaly": signals,
                         "zive_model": {"uzavrenych": len(closed), "ziskovych": sum(t.get("vysledek_proc_marze", 0) > 0 for t in closed)},
                         "zive_heuristiky": windows.get("vse")},
        "typy": by_type,
        "aktivni": [row(r) for r in best[:40]], "slabe_vse": [row(r) for r in weak[:20]],
        "zmeny_stavu": changes[::-1],
        "kontrola_deniku": {"problemy": ledger["problemy"], "predikci": ledger["predikci"], "vyhodnoceno": ledger["vyhodnoceno"],
                            "zmeskano": json.loads(LIVE_STATE.read_text()).get("zmeskano", 0) if LIVE_STATE.exists() else 0},
    }


# ----------------------------------------------------------------------
# report
# ----------------------------------------------------------------------

def _pct(v, nd=1):
    return "–" if v is None else f"{v * 100:.{nd}f} %".replace(".", ",")


def _num(v, nd=3):
    return "–" if v is None else f"{v:+.{nd}f}".replace(".", ",")


def write_report(reg: dict, changes: list[dict]) -> None:
    R = reg["pravidla"]
    lines = [f"# Heuristický model – registr pravidel ({reg['vytvoreno'][:10]})", "",
             f"_Generuje `python scripts/heuristiky.py prepocet`. Data do {reg['data_do']}. Metodika: docs/HEURISTIKY.md. "
             "Výnosy jsou v % ceny po nákladech (spread + skluz), na jednu predikci._", "",
             "## Stavy pravidel", "", "| Časový rámec | Rozsah | " + " | ".join(STATUSES) + " |",
             "|---|---|" + "---|" * len(STATUSES)]
    for tf in TFS:
        for scope in ("páry", "VŠE"):
            rs = [r for r in R if r["tf"] == tf and (r["par"] == "VŠE") == (scope == "VŠE")]
            lines.append(f"| {tf} | {'jednotlivé páry' if scope == 'páry' else 'všechny páry dohromady'} | "
                         + " | ".join(str(sum(r["stav"] == s for r in rs)) for s in STATUSES) + " |")
    act = sorted([r for r in R if r["stav"] == "AKTIVNÍ"], key=lambda r: -r["oos"]["ev"])
    lines += ["", f"## Aktivní pravidla ({len(act)})", ""]
    if act:
        lines += ["| Pravidlo | Pár | TF | Směr | Win 2012–18 | Win 2019–26 (náhodně) | Vzorek | Průměr 2019–26 | q | Důvěryhodnost |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        for r in act[:60]:
            i, o = r["is"], r["oos"]
            lines.append(f"| {r['podminka']} | {r['par']} | {r['tf']} | {r['smer']} | {_pct(i['win'])} | {_pct(o['win'])} "
                         f"({_pct(o.get('base_win'))}) | {i['n']} + {o['n']} | {_num(o['ev'])} % | {o.get('q', 1):.3f} | {r['duveryhodnost']} |")
    else:
        lines.append("Žádné pravidlo neprošlo všemi testy.")
    lines += ["", "## Podle typu heuristiky (jednotlivé páry, základní pravidla)", "",
              "| Typ | Pravidel | Kladných 2019–26 | AKTIVNÍ | SLABÁ | NEFUNKČNÍ | OVERFIT/NESTABILNÍ | NEOVĚŘENÁ |", "|---|---|---|---|---|---|---|---|"]
    for t, label in TYP_CZ.items():
        rs = [r for r in R if r["typ"] == t and r["par"] != "VŠE" and "+" not in r["id"]]
        if not rs:
            continue
        ev = [r["oos"]["ev"] for r in rs if (r.get("oos") or {}).get("n", 0) >= MIN_N]
        lines.append(f"| {label} | {len(rs)} | {_pct(float(np.mean(np.array(ev) > 0)) if ev else None, 0)} | "
                     + " | ".join(str(sum(r["stav"] == s for r in rs)) for s in ("AKTIVNÍ", "SLABÁ", "NEFUNKČNÍ", "OVERFIT/NESTABILNÍ", "NEOVĚŘENÁ")) + " |")
    cal = reg.get("kalibrace") or {}
    if cal:
        lines += ["", "## Kalibrace pravděpodobností (predikce 2019–26)", "",
                  f"Úspěšnost všech predikcí {_pct(cal['uspesnost'])}. Brierovo skóre (nižší = lepší): statistická "
                  f"{cal['brier_stat']:.4f}, heuristická {cal['brier_heur']:.4f}, hod mincí (50 %) {cal['brier_mince']:.4f}.", "",
                  "| Heuristický odhad | Predikcí | Čekal | Skutečnost |", "|---|---|---|---|"]
        for b in cal["heur"]:
            lines.append(f"| {b['od'] * 100:.0f}–{b['do'] * 100:.0f} % | {b['n']} | {_pct(b['ocekavano'])} | {_pct(b['skutecnost'])} |")
    mm = reg.get("hlavni_model") or {}
    if mm.get("skupiny"):
        lines += ["", "## Shoda s hlavním modelem (obchody 2019–26)", "", "| Heuristiky | Obchodů | Úspěšnost | Průměr % marže |",
                  "|---|---|---|---|"]
        for c, s in mm["skupiny"].items():
            lines.append(f"| {c} | {s['n']} | {_pct(s['uspesnost'])} | {s['prumer_marze']:+.1f} |".replace(".", ","))
        lines += ["", f"{mm['zaver']} (p = {mm['p'] if mm['p'] is not None else '–'})"]
    if changes:
        lines += ["", f"## Změny stavů ({len(changes)})", ""]
        lines += [f"- {c['id']}: {c['z'] or 'nové'} → {c['na']} ({c['duvod']})" for c in changes[:80]]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def card_text(rid: str) -> str:
    reg = previous_registry()
    r = next((x for x in reg.get("pravidla", []) if x["id"] == rid), None)
    if not r:
        return f"pravidlo {rid} v registru není"
    return json.dumps(r, indent=1, ensure_ascii=False)


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "zive"
    if cmd == "prepocet":
        build_registry()
        return 0
    if cmd == "overeni":
        v = verify_ledger()
        print(json.dumps(v, indent=1, ensure_ascii=False))
        return 1 if v["problemy"] else 0
    if cmd == "pravidlo" and len(argv) > 1:
        print(card_text(argv[1]))
        return 0
    if cmd == "zive":
        out = live()
        print(json.dumps({k: out.get(k) for k in ("otevrene", "nove", "vyhodnocene_ted", "plati_ted", "chyba")}, ensure_ascii=False))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
