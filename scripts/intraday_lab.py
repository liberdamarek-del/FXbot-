"""Intraday (hourly) strategy research on FXCM hourly BID/ASK 2012-2026 (user's question 2026-10-05: "did you try
intraday / hourly trading - why do such models exist and earn?").

    python scripts/intraday_lab.py [--pary vse]      # -> data/research/intraday/results.pkl, printed tables

Every trade enters at the OPEN of an hourly bar and exits at the open of a later bar (or at a target / stop on
the way), with the retail costs of the live model: half of max(retail spread, the bar's real FXCM spread) plus
half the slippage on each side (the real spread counts when it is wider - rollover, holidays). No minimum profit
per trade (the 10 %-of-margin rule of the daily model is dropped here on purpose: short trades are small).
Signals use only bars that closed before the entry. Selection only on 2012-2018 (A), check on 2019-2022 (B),
test 2023-2026 (C), and on the 13 FXCM pairs the live model does not trade (other markets).

Families (each a handful of parameters, all variants reported, nothing hand-picked):
    hod      hold the pair from London hour h for k hours, side = sign of the A-period mean (seasonality)
    asia     breakout of the Asian range (00-07 London) during London hours: follow or fade, exit 16 London / 17 NY
    mom      intraday momentum: move from the New York close to London hour s -> same / opposite side until 16 NY
    shock    an hour that moved > k x the hourly ATR: follow or fade for 1-12 hours
    gap      Monday open gap after the weekend: fade or follow for k hours
    pdhl     the previous day's high / low broken: follow or fade until the New York close
    carryh   the side of the model's rate momentum (no fitting) held in a fixed session
"""

import pickle
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import fxcm_universe as U  # noqa: E402
import profit_lab2 as P  # noqa: E402
from src.instruments import DEFAULT_ACTIVE, get_instrument  # noqa: E402

OUT = PROJECT_ROOT / "data" / "research" / "intraday"
PERIODS = {"A": (2012, 2018), "B": (2019, 2022), "C": (2023, 2026)}
H = 3600


class Pair:
    """Hourly bars of one pair with local hours, trading days, costs and a causal hourly ATR."""

    def __init__(self, symbol: str):
        d = U.load(symbol)
        inst = get_instrument(symbol)
        self.symbol, self.pip = symbol, inst.pip
        self.ts = d["ts"].astype(np.int64)
        self.o = (d["bo"] + d["ao"]) / 2
        self.h = (d["bh"] + d["ah"]) / 2
        self.l = (d["bl"] + d["al"]) / 2
        self.c = (d["bc"] + d["ac"]) / 2
        retail = P.SPREAD_PIPS[symbol] * inst.pip
        slip = P.SLIPPAGE_PIPS * inst.pip
        self.cost_o = np.maximum(retail, d["ao"] - d["bo"]) / 2 + slip / 2       # per side, at the bar open
        self.cost_c = np.maximum(retail, d["ac"] - d["bc"]) / 2 + slip / 2       # per side, at the bar close
        t = pd.to_datetime(self.ts, unit="s", utc=True)
        lon, ny = t.tz_convert("Europe/London"), t.tz_convert("America/New_York")
        self.lon_h = np.asarray(lon.hour)
        self.ny_h = np.asarray(ny.hour)
        self.wd = np.asarray(lon.weekday)
        self.day = np.asarray((ny + pd.Timedelta(hours=7)).normalize().tz_localize(None).values.astype("datetime64[D]"))
        self.year = np.asarray(t.year)
        rng = self.h - self.l
        self.atr_h = pd.Series(rng).shift(1).rolling(24 * 20, min_periods=24 * 5).mean().to_numpy()   # causal
        n = len(self.ts)
        idx = np.arange(n)
        last17 = np.maximum.accumulate(np.where(self.ny_h == 17, idx, -1))
        self.prev_ny17 = np.append(-1, last17[:-1])                   # the latest bar opening 17:00 NY before k
        self.next_ny = {}
        for hh in (16, 17):
            nxt = np.where(self.ny_h == hh, idx, n)
            nxt = np.minimum.accumulate(nxt[::-1])[::-1]               # first bar >= k opening at hh NY
            self.next_ny[hh] = np.append(nxt[1:], n)                   # strictly after k

    def contiguous(self, i: np.ndarray, j: np.ndarray) -> np.ndarray:
        ok = (j < len(self.ts)) & (i >= 0)
        jj = np.minimum(j, len(self.ts) - 1)
        return ok & (self.ts[jj] - self.ts[np.maximum(i, 0)] == (jj - i) * H)


def fixed_trades(p: Pair, entry: np.ndarray, exit_: np.ndarray, side: np.ndarray) -> dict:
    """Enter at the open of bar `entry`, leave at the open of bar `exit_` (no target / stop)."""
    ok = p.contiguous(entry, exit_) & (exit_ > entry)
    e, x, s = entry[ok], exit_[ok], side[ok]
    px_in = p.o[e] + s * p.cost_o[e]
    px_out = p.o[x] - s * p.cost_o[x]
    ret = s * (px_out - px_in) / px_in * 100
    gross = s * (p.o[x] - p.o[e]) / p.o[e] * 100
    return {"pair": p.symbol, "i": e, "ret": ret, "gross": gross, "year": p.year[e], "day": p.day[e],
            "hours": (x - e).astype(float)}


def bracket_trades(p: Pair, entry: np.ndarray, side: np.ndarray, tp: np.ndarray, sl: np.ndarray,
                   max_h: int) -> dict:
    """Enter at the open of `entry`; target / stop distances in price on the mid path (costs on both sides,
    stop first when both are touched in one hour); otherwise out at the open after `max_h` hours."""
    ok = p.contiguous(entry, entry + max_h)
    e, s, tp, sl = entry[ok], side[ok], tp[ok], sl[ok]
    px_in = p.o[e] + s * p.cost_o[e]
    res = np.empty(len(e))
    held = np.empty(len(e))
    for n, (k, sd, a, b) in enumerate(zip(e, s, tp, sl)):
        out = None
        for j in range(k, k + max_h):
            adv = (px_in[n] - (p.l[j] - p.cost_c[j])) if sd > 0 else ((p.h[j] + p.cost_c[j]) - px_in[n])
            fav = ((p.h[j] - p.cost_c[j]) - px_in[n]) if sd > 0 else (px_in[n] - (p.l[j] + p.cost_c[j]))
            if adv >= b:
                out, hh = -b, j - k + 1
                break
            if fav >= a:
                out, hh = a, j - k + 1
                break
        if out is None:
            x = k + max_h
            out, hh = sd * ((p.o[x] - sd * p.cost_o[x]) - px_in[n]), max_h
        res[n] = out / px_in[n] * 100
        held[n] = hh
    gross = res + 0.0
    return {"pair": p.symbol, "i": e, "ret": res, "gross": gross, "year": p.year[e], "day": p.day[e], "hours": held}


def merge(parts: list[dict]) -> dict:
    keys = ("ret", "gross", "year", "day", "hours", "i")
    out = {k: np.concatenate([x[k] for x in parts]) if parts else np.array([]) for k in keys}
    out["pair"] = np.concatenate([np.full(len(x["ret"]), x["pair"]) for x in parts]) if parts else np.array([])
    return out


def stats(tr: dict, period: str) -> dict:
    lo, hi = PERIODS[period]
    m = (tr["year"] >= lo) & (tr["year"] <= hi)
    r = tr["ret"][m]
    if len(r) < 30:
        return {"n": len(r), "mean": np.nan, "t": np.nan, "win": np.nan, "gross": np.nan, "per_year": len(r) / (hi - lo + 1)}
    # t-statistic with the trades of one day summed (several pairs / overlapping hours on one day are not independent)
    days = tr["day"][m]
    _, inv = np.unique(days, return_inverse=True)
    daily = np.bincount(inv, weights=r)
    t = daily.mean() / (daily.std(ddof=1) / np.sqrt(len(daily))) if daily.std() > 0 else 0.0
    return {"n": len(r), "mean": float(r.mean()), "t": float(t), "win": float((r > 0).mean()),
            "gross": float(tr["gross"][m].mean()), "per_year": len(r) / (hi - lo + 1),
            "hours": float(tr["hours"][m].mean())}


# ----------------------------------------------------------------------
# families
# ----------------------------------------------------------------------

def bars_at(p: Pair, lon_hour: int) -> np.ndarray:
    """Index of the bar opening at London `lon_hour` on each weekday (Monday-Friday)."""
    return np.where((p.lon_h == lon_hour) & (p.wd < 5))[0]


def fam_hod(pairs, sides=None):
    """Hold from London hour h for k hours; the side of each (pair, h, k) is the sign of its A-period gross mean."""
    out = {}
    for h in range(24):
        for k in (1, 2, 3, 4, 6, 8):
            parts, fitted = [], {}
            for p in pairs:
                e = bars_at(p, h)
                tr = fixed_trades(p, e, e + k, np.ones(len(e)))
                a = (tr["year"] <= 2018)
                key = (p.symbol, h, k)
                sd = sides[key] if sides is not None else (1.0 if tr["gross"][a].mean() > 0 else -1.0)
                fitted[key] = sd
                parts.append(fixed_trades(p, e, e + k, np.full(len(e), sd)))
            out[f"hod h{h:02d} k{k}"] = (merge(parts), fitted)
    return out


def fam_asia(pairs):
    out = {}
    for mode in ("follow", "fade"):
        for exit_h in (12, 16, 21):
            for width in ("all", "narrow", "wide"):
                parts = []
                for p in pairs:
                    rows = []
                    starts = bars_at(p, 0)
                    for s0 in starts:
                        if not p.contiguous(np.array([s0]), np.array([s0 + 7]))[0]:
                            continue
                        hi, lo = p.h[s0:s0 + 7].max(), p.l[s0:s0 + 7].min()
                        atr = p.atr_h[s0 + 7]
                        if np.isnan(atr):
                            continue
                        w = (hi - lo) / (atr * 24 ** 0.5)
                        if (width == "narrow" and w > 0.6) or (width == "wide" and w < 0.9):
                            continue
                        last = s0 + exit_h                               # the bar opening at London exit_h
                        for j in range(s0 + 7, min(s0 + 12, last)):     # London 07-11: first close beyond the range
                            if p.c[j] > hi or p.c[j] < lo:
                                side = (1 if p.c[j] > hi else -1) * (1 if mode == "follow" else -1)
                                rows.append((j + 1, last, side))
                                break
                    if rows:
                        e, x, sd = (np.array(v) for v in zip(*rows))
                        parts.append(fixed_trades(p, e, x, sd.astype(float)))
                out[f"asia {mode} exit{exit_h} {width}"] = (merge(parts), None)
    return out


def fam_mom(pairs):
    """Move from the New York close (17:00 NY) to London hour s -> trade the rest of the day until NY 16 / 17."""
    out = {}
    for s in (8, 10, 12, 14):
        for mode in ("follow", "fade"):
            for thr in (0.0, 0.5, 1.0):
                for exit_ny in (16, 17):
                    parts = []
                    for p in pairs:
                        e = bars_at(p, s)
                        j0 = p.prev_ny17[e]                              # the last NY close before the entry
                        x = p.next_ny[exit_ny][e]
                        ok = (j0 >= 0) & (x > e) & (x - e < 16)
                        ok &= p.contiguous(np.maximum(j0, 0), e)
                        e, j0, x = e[ok], j0[ok], x[ok]
                        move = p.o[e] - p.o[j0]
                        scale = p.atr_h[e] * 24 ** 0.5 * 0.5             # about half a daily ATR
                        m = (np.abs(move) >= thr * scale) & (move != 0) & ~np.isnan(scale)
                        side = np.sign(move[m]) * (1 if mode == "follow" else -1)
                        parts.append(fixed_trades(p, e[m], x[m], side))
                    out[f"mom s{s} {mode} thr{thr} exitNY{exit_ny}"] = (merge(parts), None)
    return out


def fam_shock(pairs):
    out = {}
    for k in (2.0, 3.0, 4.0):
        for mode in ("follow", "fade"):
            for hold in (1, 3, 6, 12):
                parts = []
                for p in pairs:
                    r = p.c - p.o
                    big = np.where((np.abs(r) > k * p.atr_h) & (p.wd < 5))[0]
                    big = big[big + 1 + hold < len(p.ts)]
                    side = np.sign(r[big]) * (1 if mode == "follow" else -1)
                    parts.append(fixed_trades(p, big + 1, big + 1 + hold, side))
                out[f"shock {k}atr {mode} {hold}h"] = (merge(parts), None)
    return out


def fam_gap(pairs):
    out = {}
    for mode in ("fade", "follow"):
        for hold in (1, 3, 6, 12, 24):
            for thr in (0.0, 0.3):
                parts = []
                for p in pairs:
                    gaps = np.where(np.diff(p.ts) > 24 * H)[0] + 1            # first bar after a weekend / holiday
                    gaps = gaps[(gaps + hold + 2 < len(p.ts)) & ((p.wd[gaps] == 6) | (p.wd[gaps] == 0))]
                    g = p.o[gaps] - p.c[gaps - 1]
                    atr = p.atr_h[gaps]
                    m = np.abs(g) > thr * atr * 24 ** 0.5
                    e = gaps[m] + 1                                            # after the first hour (spreads wide)
                    side = -np.sign(g[m]) * (1 if mode == "fade" else -1)
                    parts.append(fixed_trades(p, e, e + hold, side))
                out[f"gap {mode} {hold}h thr{thr}"] = (merge(parts), None)
    return out


def fam_pdhl(pairs):
    out = {}
    for mode in ("follow", "fade"):
        for start in (7, 12):
            parts = []
            for p in pairs:
                rows = []
                days, first = np.unique(p.day, return_index=True)
                last = np.append(first[1:], len(p.ts)) - 1
                for d in range(1, len(days)):
                    a0, a1 = first[d - 1], last[d - 1]
                    b0, b1 = first[d], last[d]
                    if a1 - a0 < 18 or b1 - b0 < 18:
                        continue
                    hi, lo = p.h[a0:a1 + 1].max(), p.l[a0:a1 + 1].min()
                    for j in range(b0, b1):
                        if p.lon_h[j] < start or p.ny_h[j] >= 16:
                            continue
                        if p.c[j] > hi or p.c[j] < lo:
                            side = (1 if p.c[j] > hi else -1) * (1 if mode == "follow" else -1)
                            if j + 1 <= b1:
                                rows.append((j + 1, b1, side))
                            break
                if rows:
                    e, x, sd = (np.array(v) for v in zip(*rows))
                    parts.append(fixed_trades(p, e, x, sd.astype(float)))
            out[f"pdhl {mode} from{start}"] = (merge(parts), None)
    return out


def fam_carryh(pairs):
    """The model's rate momentum (OECD 3m rate difference change over 3 months, known with a 2-month lag) decides
    the side; the pair is held in one session. No fitting."""
    rates = P.monthly_rates()
    out = {}
    sessions = {"asia 00-07": (0, 7), "london 07-12": (7, 5), "overlap 12-16": (12, 4), "ny 16-21": (16, 5),
                "day 07-21": (7, 14)}
    for name, (h, k) in sessions.items():
        for thr in (0.0, 0.25):
            parts = []
            for p in pairs:
                inst = get_instrument(p.symbol)
                e = bars_at(p, h)
                side = np.zeros(len(e))
                for n, k0 in enumerate(e):
                    y, mth = int(p.year[k0]), int(str(p.day[k0])[5:7])
                    v = [P.rate_at(rates[c], y, mth, lag) for c in (inst.base, inst.quote) for lag in (2, 5)]
                    if None in v:
                        continue
                    mom = (v[0] - v[2]) - (v[1] - v[3])
                    if abs(mom) >= thr and mom != 0:
                        side[n] = np.sign(mom)
                m = side != 0
                parts.append(fixed_trades(p, e[m], e[m] + k, side[m]))
            out[f"carryh {name} thr{thr}"] = (merge(parts), None)
    return out


def gotobi_days(days: np.ndarray) -> np.ndarray:
    """Japanese settlement days: the 5th, 10th, ..., 25th and the month's last business day, moved to the previous
    business day when they fall on a weekend (the 'gotobi' importer dollar demand at the 9:55 Tokyo fix)."""
    d = pd.to_datetime(days)
    out = np.zeros(len(d), bool)
    cal = pd.bdate_range(d.min() - pd.Timedelta(days=40), d.max() + pd.Timedelta(days=40))
    targets = set()
    for y, m in {(x.year, x.month) for x in cal}:
        for dd in (5, 10, 15, 20, 25):
            t = pd.Timestamp(y, m, dd)
            while t.weekday() >= 5:
                t -= pd.Timedelta(days=1)
            targets.add(t)
        last = pd.Timestamp(y, m, 1) + pd.offsets.MonthEnd(0)
        while last.weekday() >= 5:
            last -= pd.Timedelta(days=1)
        targets.add(last)
    out[:] = [x in targets for x in d.normalize()]
    return out


def fam_gotobi(pairs):
    """USD/JPY (and the JPY crosses) on gotobi days: buy before the 9:55 Tokyo fix (00:55 UTC) / sell after it.
    Tokyo has no daylight saving: the hours are UTC."""
    out = {}
    for name, (h0, k, side) in {"pred fixem 23-01 UTC": (23, 2, 1.0), "pred fixem 00-01 UTC": (0, 1, 1.0),
                                "po fixu 01-03 UTC": (1, 2, -1.0), "po fixu 01-05 UTC": (1, 4, -1.0)}.items():
        for days_kind in ("gotobi", "ostatni"):
            parts = []
            for p in pairs:
                if "JPY" not in p.symbol:
                    continue
                utc_h = (p.ts // H) % 24
                e = np.where((utc_h == h0) & (p.wd < 5 if h0 != 23 else p.wd < 4 + 3))[0]
                # the Tokyo date of the fix: the UTC date of the hour 00-01 UTC
                fix_day = ((p.ts[e] + (24 - h0) % 24 * H if h0 == 23 else p.ts[e]) // 86400).astype("datetime64[D]")
                g = gotobi_days(fix_day)
                e = e[g] if days_kind == "gotobi" else e[~g]
                sd = side if p.symbol.split("/")[1] == "JPY" else -side
                parts.append(fixed_trades(p, e, e + k, np.full(len(e), sd)))
            out[f"gotobi {name} {days_kind}"] = (merge(parts), None)
    return out


def rsi_h(c: np.ndarray, n: int) -> np.ndarray:
    import strategy_mining as SM
    return SM.rsi(c, n)


def fam_ratesdip(pairs):
    """Hourly dips in the direction the rate momentum favours (the daily model's mechanism on the hourly chart):
    hourly RSI(n) below x (above 100 - x for a sell) while the OECD rate momentum >= thr in the trade direction.
    Exit after k hours. One trade at a time per pair."""
    rates = P.monthly_rates()
    out = {}
    for n, x in ((2, 5), (2, 10), (3, 10)):
        for thr in (0.1, 0.25):
            for k in (4, 12, 24, 48):
                parts = []
                for p in pairs:
                    inst = get_instrument(p.symbol)
                    r = rsi_h(p.c, n)
                    months = sorted({(int(y), int(str(dd)[5:7])) for y, dd in zip(p.year[::24], p.day[::24])})
                    mom = {}
                    for y, m in months:
                        v = [P.rate_at(rates[c], y, m, lag) for c in (inst.base, inst.quote) for lag in (2, 5)]
                        mom[(y, m)] = None if None in v else (v[0] - v[2]) - (v[1] - v[3])
                    ym = [(int(y), int(str(dd)[5:7])) for y, dd in zip(p.year, p.day)]
                    mm = np.array([np.nan if mom.get(t) is None else mom[t] for t in ym])
                    buy = (r < x) & (mm >= thr)
                    sell = (r > 100 - x) & (mm <= -thr)
                    cand = np.where((buy | sell) & (p.wd < 5))[0]
                    rows, busy = [], -1
                    for i in cand:
                        if i + 1 <= busy:
                            continue
                        rows.append((i + 1, i + 1 + k, 1.0 if buy[i] else -1.0))
                        busy = i + 1 + k
                    if rows:
                        e, xx, sd = (np.array(v) for v in zip(*rows))
                        parts.append(fixed_trades(p, e, xx, sd))
                out[f"ratesdip rsi{n}<{x} thr{thr} {k}h"] = (merge(parts), None)
    return out


FAMILIES = {"hod": fam_hod, "asia": fam_asia, "mom": fam_mom, "shock": fam_shock, "gap": fam_gap, "pdhl": fam_pdhl,
            "carryh": fam_carryh, "gotobi": fam_gotobi, "ratesdip": fam_ratesdip}


def main(argv: list[str]) -> int:
    started = time.monotonic()
    live = [Pair(s) for s in DEFAULT_ACTIVE]
    others = [Pair(s) for s in U.universe() if s not in DEFAULT_ACTIVE]
    which = [f for f in FAMILIES if f in argv] or list(FAMILIES)
    results = {}
    for fam in which:
        t0 = time.monotonic()
        res = FAMILIES[fam](live)
        for name, (tr, fitted) in res.items():
            if fam == "hod":
                tr_o = None
            else:
                tr_o = merge([x for x in [FAMILIES[fam]([p])[name][0] for p in others] if len(x["ret"])]) \
                    if "--jine" in argv else None
            row = {p: stats(tr, p) for p in PERIODS}
            row["other"] = stats(tr_o, "C") if tr_o is not None else None
            results[name] = row
        print(f"{fam}: {len(res)} variant, {time.monotonic() - t0:.0f} s", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"results_{'_'.join(which)}.pkl").write_bytes(pickle.dumps(results))
    rows = sorted(results.items(), key=lambda kv: -np.nan_to_num(kv[1]["A"]["t"], nan=-9))
    print(f"{'varianta':38} | A n / prumer % / t / win | B | C")
    for name, r in rows[:40]:
        cells = [f"{r[p]['n']:5d} {r[p]['mean']:+.4f} t{r[p]['t']:+.1f} {r[p]['win']:.0%}" if r[p]["n"] >= 30
                 else f"{r[p]['n']:5d}" for p in PERIODS]
        print(f"{name:38} | " + " | ".join(cells))
    allpos = [n for n, r in results.items() if all(r[p]["n"] >= 30 and r[p]["mean"] > 0 for p in PERIODS)]
    print(f"kladne ve vsech trech obdobich po nakladech: {len(allpos)} z {len(results)}: {allpos[:20]}")
    print(f"{time.monotonic() - started:.0f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
