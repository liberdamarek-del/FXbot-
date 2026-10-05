"""Minute-level FX strategies on FXCM 1-minute BID/ASK 2016-2026 (user's question 2026-10-05).

    python scripts/minute_lab.py [rodina ...]     # night, news, orb, round, spike  -> printed tables + pickle

Every trade: a market entry at the open of a minute bar (buy at the ask, sell at the bid) plus the retail markup
(max(0, retail spread - the real FXCM spread) / 2 + slippage / 2 per side), target / stop checked on the BID/ASK
minute path (stop first when both are touched in one minute), time exit at the open N minutes later. Families
with an economic reason (literature in docs/INTRADAY.md):
    night   quiet-hours mean reversion ("night scalper"): after the New York close, fade a move of k x the
            minute ATR away from the 60-minute mean, small target, wide stop, out before 06:00 London
    news    US NFP / CPI at 8:30 New York: follow (or fade) the first 1-5 minutes for 15-120 minutes
    orb     London open range (08:00-08:15 / 08:30 London): breakout follow with the range as stop
    round   round numbers (Osler 2003): take-profit orders cluster at 00 / 50 levels -> price bounces there;
            stop orders cluster just beyond -> a cross runs further: fade the first touch / follow a cross
    spike   a minute that moved > k x the minute ATR: fade or follow for 5-60 minutes
Selection only on 2016-2019 (A), check 2020-2022 (B), test 2023-2026 (C).
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

import fxcm_m1 as M  # noqa: E402
import profit_lab2 as P  # noqa: E402
from src.instruments import DEFAULT_ACTIVE, get_instrument  # noqa: E402

OUT = PROJECT_ROOT / "data" / "research" / "intraday"
PERIODS = {"A": (2016, 2019), "B": (2020, 2022), "C": (2023, 2026)}
MIN = 60


class Minutes:
    def __init__(self, pair: str, years=range(2016, 2027)):
        d = M.load(pair, years)
        inst = get_instrument(pair)
        self.pair, self.pip = pair, inst.pip
        self.ts = d["ts"]
        for k in ("bo", "bh", "bl", "bc", "ao", "ah", "al", "ac"):
            setattr(self, k, d[k])
        retail = P.SPREAD_PIPS[pair] * inst.pip
        slip = P.SLIPPAGE_PIPS * inst.pip
        self.mark = np.maximum(0.0, retail - (d["ao"] - d["bo"])) / 2 + slip / 2        # extra per side at the open
        self.mid = (d["bo"] + d["ao"]) / 2
        t = pd.to_datetime(self.ts, unit="s", utc=True)
        lon, ny = t.tz_convert("Europe/London"), t.tz_convert("America/New_York")
        self.lon_min = np.asarray(lon.hour * 60 + lon.minute)
        self.ny_min = np.asarray(ny.hour * 60 + ny.minute)
        self.wd = np.asarray(lon.weekday)
        self.year = np.asarray(t.year)
        self.date_ny = np.asarray(ny.normalize().tz_localize(None).values.astype("datetime64[D]"))
        rng = (d["bh"] + d["ah"]) / 2 - (d["bl"] + d["al"]) / 2
        self.atr = pd.Series(rng).shift(1).rolling(1440 * 5, min_periods=1440).mean().to_numpy()

    def window(self, i: np.ndarray, n: int) -> tuple[np.ndarray, np.ndarray]:
        """Exit bar index n minutes after each entry (the first bar at or after entry + n min) and whether the
        window is usable: minutes without any quote are simply absent in FXCM files (no trade happened), but
        a hole of more than 30 minutes or an exit more than 10 minutes late (weekend, outage) is not."""
        x = np.searchsorted(self.ts, self.ts[np.minimum(i, len(self.ts) - 1)] + n * MIN)
        ok = (x < len(self.ts)) & (i < len(self.ts))
        xx = np.minimum(x, len(self.ts) - 1)
        ok &= self.ts[xx] - self.ts[np.minimum(i, len(self.ts) - 1)] <= n * MIN + 600
        gap = np.diff(self.ts) > 30 * MIN
        cg = np.concatenate([[0], np.cumsum(gap)])
        ok &= cg[xx] == cg[np.minimum(i, len(self.ts) - 1)]
        return xx, ok


def bracket(m: Minutes, entry: np.ndarray, side: np.ndarray, tp: np.ndarray, sl: np.ndarray, nmax: int) -> dict:
    """Entry at the open of `entry`; target / stop distances in price from the entry fill; exits on the BID (long)
    or ASK (short) path; time exit at the open nmax minutes later. Only windows without data holes."""
    entry = entry[entry < len(m.ts)]
    side, tp, sl = side[:len(entry)], tp[:len(entry)], sl[:len(entry)]
    xs, ok = m.window(entry, nmax)
    e, s, tp, sl, xs = entry[ok], side[ok], tp[ok], sl[ok], xs[ok]
    res = np.empty(len(e))
    cost = np.empty(len(e))
    for n, (k, sd, a, b, x) in enumerate(zip(e, s, tp, sl, xs)):
        if sd > 0:
            px = m.ao[k] + m.mark[k]
            lo, hi = m.bl[k:x], m.bh[k:x]
            stop = np.nonzero(lo - m.mark[k] <= px - b)[0]
            take = np.nonzero(hi - m.mark[k] >= px + a)[0]
        else:
            px = m.bo[k] - m.mark[k]
            lo, hi = m.al[k:x], m.ah[k:x]
            stop = np.nonzero(hi + m.mark[k] >= px + b)[0]
            take = np.nonzero(lo + m.mark[k] <= px - a)[0]
        span = x - k
        js = stop[0] if len(stop) else span
        jt = take[0] if len(take) else span
        if js <= jt and js < span:
            out = -b
        elif jt < span:
            out = a
        else:
            out = ((m.bo[x] - m.mark[x]) - px) if sd > 0 else (px - (m.ao[x] + m.mark[x]))
        res[n] = out / px * 100
        cost[n] = ((m.ao[k] - m.bo[k]) + 2 * m.mark[k]) / px * 100            # round trip at the entry spread
    return {"ret": res, "year": m.year[e], "day": m.date_ny[e], "pair": np.full(len(e), m.pair), "cost": cost}


def merge(parts):
    if not parts:
        return {"ret": np.array([]), "year": np.array([], int), "day": np.array([], "datetime64[D]"), "pair": np.array([]),
                "cost": np.array([])}
    return {k: np.concatenate([x[k] for x in parts]) for k in ("ret", "year", "day", "pair", "cost")}


def stats(tr, period):
    lo, hi = PERIODS[period]
    msk = (tr["year"] >= lo) & (tr["year"] <= hi)
    r = tr["ret"][msk]
    if len(r) < 30:
        return {"n": len(r), "mean": np.nan, "t": np.nan, "win": np.nan}
    _, inv = np.unique(tr["day"][msk], return_inverse=True)
    daily = np.bincount(inv, weights=r)
    t = daily.mean() / (daily.std(ddof=1) / np.sqrt(len(daily))) if daily.std() > 0 else 0.0
    return {"n": len(r), "mean": float(r.mean()), "t": float(t), "win": float((r > 0).mean()),
            "gross": float((r + tr["cost"][msk]).mean())}


def one_per(entries: np.ndarray, gap: int) -> np.ndarray:
    """At most one entry per `gap` minutes (no overlapping trades of one rule on one pair)."""
    keep, last = [], -10 ** 9
    for e in entries:
        if e - last >= gap:
            keep.append(e)
            last = e
    return np.array(keep, int)


# ----------------------------------------------------------------------
# families
# ----------------------------------------------------------------------

def fam_night(ms):
    out = {}
    for k in (1.5, 2.5, 4.0):
        for tp_atr, sl_atr in ((1.0, 6.0), (2.0, 8.0), (3.0, 12.0)):
            parts = []
            for m in ms:
                mean60 = pd.Series(m.mid).rolling(60).mean().shift(1).to_numpy()
                dev = (m.mid - mean60) / m.atr
                # after the NY close and the rollover spike (17:15 NY) until 01:00 London, Monday-Thursday nights
                quiet = (((m.ny_min >= 17 * 60 + 15) | (m.lon_min < 60)) & (m.wd <= 3)) | ((m.lon_min < 60) & (m.wd <= 4) & (m.wd >= 1))
                cand = np.nonzero(quiet & (np.abs(dev) > k))[0]
                cand = one_per(cand, 120)
                side = -np.sign(dev[cand])
                parts.append(bracket(m, cand, side, tp_atr * m.atr[cand], sl_atr * m.atr[cand], 240))
            out[f"night dev{k} tp{tp_atr} sl{sl_atr}"] = merge(parts)
    return out


def fam_news(ms):
    import json
    ev = json.loads((PROJECT_ROOT / "learning" / "udalosti_historie.json").read_text())
    days = {"NFP": set(ev.get("US_NFP", [])), "CPI": set(ev.get("US_CPI", []))}
    out = {}
    for kind, dset in days.items():
        for first in (1, 5):
            for hold in (15, 60, 120):
                for mode in ("follow", "fade"):
                    parts = []
                    for m in ms:
                        if "USD" not in m.pair:
                            continue
                        rel = np.nonzero((m.ny_min == 8 * 60 + 30) & np.isin(m.date_ny.astype(str), list(dset)))[0]
                        rel = rel[rel + first + hold + 1 < len(m.ts)]
                        move = m.mid[rel + first] - m.mid[rel]
                        e = rel + first
                        side = np.sign(move) * (1 if mode == "follow" else -1)
                        okm = side != 0
                        big = np.full(okm.sum(), 1e9)
                        parts.append(bracket(m, e[okm], side[okm], big, big, hold))
                    out[f"news {kind} first{first}m {mode} {hold}m"] = merge(parts)
    return out


def fam_orb(ms):
    out = {}
    for rng_min in (15, 30):
        for tp_mult in (1.0, 2.0):
            parts = []
            for m in ms:
                starts = np.nonzero((m.lon_min == 8 * 60) & (m.wd < 5))[0]
                rows = []
                for s in starts:
                    if not m.window(np.array([s]), rng_min + 240)[1][0]:
                        continue
                    hi = m.bh[s:s + rng_min].max()
                    lo = m.bl[s:s + rng_min].min()
                    w = hi - lo
                    seg = m.mid[s + rng_min:s + rng_min + 180]
                    up = np.nonzero(seg > hi)[0]
                    dn = np.nonzero(seg < lo)[0]
                    j = min(up[0] if len(up) else 10 ** 6, dn[0] if len(dn) else 10 ** 6)
                    if j >= 10 ** 6:
                        continue
                    rows.append((s + rng_min + j + 1, 1.0 if len(up) and up[0] == j else -1.0, w))
                if rows:
                    e, sd, w = (np.array(v) for v in zip(*rows))
                    parts.append(bracket(m, e.astype(int), sd, tp_mult * w, w, 240))
            out[f"orb {rng_min}m tp{tp_mult}x"] = merge(parts)
    return out


def fam_round(ms):
    out = {}
    for level in (100, 50):                       # pips between round levels: 00 only, or 00 and 50
        for mode, tp, sl in (("fade", 10, 15), ("fade", 5, 10), ("follow", 15, 10), ("follow", 10, 5)):
            parts = []
            for m in ms:
                step = level * m.pip
                ref = np.floor(m.mid / step) * step
                prev = np.concatenate([[np.nan], m.mid[:-1]])
                prev_ref = np.floor(prev / step) * step
                if mode == "fade":
                    # the first touch of a level coming from 10+ pips away within the last 60 minutes
                    lvl_up = ref + step
                    touch_up = (m.bh + m.ah) / 2 >= lvl_up - 1 * m.pip
                    far = pd.Series(m.mid).rolling(60).min().shift(1).to_numpy() <= lvl_up - 10 * m.pip
                    cand_s = np.nonzero(touch_up & far)[0] + 1      # sell after the minute that touched from below
                    lvl_dn = ref
                    touch_dn = (m.bl + m.al) / 2 <= lvl_dn + 1 * m.pip
                    far_d = pd.Series(m.mid).rolling(60).max().shift(1).to_numpy() >= lvl_dn + 10 * m.pip
                    cand_b = np.nonzero(touch_dn & far_d)[0] + 1
                    cand = np.concatenate([cand_s, cand_b])
                    side = np.concatenate([-np.ones(len(cand_s)), np.ones(len(cand_b))])
                else:
                    cross_up = (ref > prev_ref)                      # the close crossed a level upwards
                    cross_dn = (ref < prev_ref)
                    cand = np.concatenate([np.nonzero(cross_up)[0] + 1, np.nonzero(cross_dn)[0] + 1])
                    side = np.concatenate([np.ones(cross_up.sum()), -np.ones(cross_dn.sum())])
                order = np.argsort(cand)
                cand, side = cand[order], side[order]
                keep = np.isin(cand, one_per(cand, 60))
                cand, side = cand[keep], side[keep]
                cand = np.minimum(cand, len(m.ts) - 1)
                parts.append(bracket(m, cand, side, np.full(len(cand), tp * m.pip), np.full(len(cand), sl * m.pip), 240))
            out[f"round {level}p {mode} tp{tp} sl{sl}"] = merge(parts)
    return out


def fam_spike(ms):
    out = {}
    for k in (4.0, 6.0, 8.0):
        for mode in ("fade", "follow"):
            for hold in (5, 15, 60):
                parts = []
                for m in ms:
                    r = (m.bc + m.ac) / 2 - m.mid
                    cand = np.nonzero((np.abs(r) > k * m.atr) & (m.wd < 5))[0] + 1
                    cand = one_per(cand[cand < len(m.ts)], hold)
                    side = np.sign(r[cand - 1]) * (1 if mode == "follow" else -1)
                    big = np.full(len(cand), 1e9)
                    parts.append(bracket(m, cand, side, big, big, hold))
                out[f"spike {k}atr {mode} {hold}m"] = merge(parts)
    return out


FAMILIES = {"night": fam_night, "news": fam_news, "orb": fam_orb, "round": fam_round, "spike": fam_spike}


def main(argv: list[str]) -> int:
    started = time.monotonic()
    which = [f for f in FAMILIES if f in argv] or list(FAMILIES)
    pairs = [a for a in argv if "/" in a] or list(DEFAULT_ACTIVE)
    ms = []
    for p in pairs:
        try:
            ms.append(Minutes(p))
            print(f"{p}: {len(ms[-1].ts)} minut", flush=True)
        except (ValueError, FileNotFoundError) as exc:
            print(f"{p}: data nejsou ({exc})", flush=True)
    results = {}
    for fam in which:
        t0 = time.monotonic()
        for name, tr in FAMILIES[fam](ms).items():
            results[name] = {p: stats(tr, p) for p in PERIODS}
        print(f"{fam}: {time.monotonic() - t0:.0f} s", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"minute_{'_'.join(which)}.pkl").write_bytes(pickle.dumps(results))
    rows = sorted(results.items(), key=lambda kv: -np.nan_to_num(kv[1]["A"]["t"], nan=-9))
    for name, r in rows:
        cells = [f"{r[p]['n']:6d} {r[p]['mean']:+.4f} (hr {r[p]['gross']:+.4f}) t{r[p]['t']:+.1f} {r[p]['win']:.0%}" if r[p]["n"] >= 30
                 else f"{r[p]['n']:6d}" for p in PERIODS]
        print(f"{name:34} | " + " | ".join(cells))
    allpos = [n for n, r in results.items() if all(r[p]["n"] >= 30 and r[p]["mean"] > 0 for p in PERIODS)]
    print(f"kladne ve vsech trech obdobich po nakladech: {len(allpos)} z {len(results)}: {allpos}")
    print(f"{time.monotonic() - started:.0f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
