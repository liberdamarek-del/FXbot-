"""High win-rate system search: >= 75 % winning trades AND the best possible
result after costs, chosen on old data and confirmed on newer data.

    python scripts/winrate_lab.py      # -> docs/USPESNOST75.md (~5-10 min, needs numpy)

Systems = entry signal x trend filter x fundamental filter x volatility
filter x exit (TP, SL, time):

    entries   mean reversion at the daily close (New York 17:00): RSI 2-4,
              Williams %R, Stochastic, Bollinger %B, IBS, down-day streaks,
              distance below SMA5, below the Keltner band (short = mirrored)
    trend     none | close vs SMA200 | SMA100 | SMA50 (trade only with it)
    fund.     none | fundamentals agree (>= 1 cluster for, none against)
    volat.    none | ATR percentile < 80 % | > 30 %
    exit      TP 0.25-1.0 x ATR(D1), SL 0.75-4 x ATR(D1), time 1 / 3 / 5 days

Every trade is played on the hourly BID/ASK path from the next hour after
the close (BUY at ASK, exits at BID), + 0.2 pip slippage per side + 0.5 pip
markup; TP and SL in the same hour = SL (conservative). Results in ATR(D1)
and R (= per unit of risk to SL).

Protocol: TRAIN 2014-2019 ranks the systems (>= 300 trades, win >= 75 %,
best E); the 100 best go to VALID 2020-2022; the best of those that keep
win >= 75 % is the FINAL system, shown once on TEST 2023-2026. A second
variant re-learns every year on the trailing 4 years (adaptive).
"""

import math
import pickle
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import pivot_lab as PL  # noqa: E402  (loads .env first)
import strategy_mining as SM  # noqa: E402
from research_signals import RISK_BETA, SIGNALS_FILE  # noqa: E402
from src.instruments import get_instrument, parse_symbols  # noqa: E402

UTC = timezone.utc
HOURS = 120
TPS = (0.25, 0.4, 0.5, 0.75, 1.0)
SLS = (0.75, 1.0, 1.5, 2.0, 3.0, 4.0)
TIMES = (24, 72, 120)
EXITS = [(tp, sl, tm) for tp in TPS for sl in SLS for tm in TIMES]
PERIODS = {"TRAIN": (date(2014, 1, 1), date(2019, 12, 31)), "VALID": (date(2020, 1, 1), date(2022, 12, 31)),
           "TEST": (date(2023, 1, 1), date(2026, 9, 30))}
SLIPPAGE_PIPS, MARKUP_PIPS = 0.2, 0.5
TARGET_WIN = 0.75


# ----------------------------------------------------------------------
# entries: excursion profiles of every (pair, day, direction)
# ----------------------------------------------------------------------

def entries_for_pair(symbol: str, fund_rows: dict) -> dict:
    data = PL.load(symbol)
    path = {k: np.array(v, dtype=float) for k, v in data["path"].items()}
    days = data["days"]
    o, h, l, c = (np.array([d[k] for d in days]) for k in ("o", "h", "l", "c"))
    close_t = np.array([d["close_t"] for d in days])
    dates = [d["date"] for d in days]
    pip = get_instrument(symbol).pip
    atr = SM.wilder(SM.true_range(h, l, c), 14)
    ts = path["ts"]
    j = np.searchsorted(ts, close_t)
    ok = (np.arange(len(days)) >= 250) & ~np.isnan(atr) & (j + HOURS < len(ts))
    jj = np.where(ok, j, 0)
    ok &= (ts[np.minimum(jj, len(ts) - 1)] - close_t <= 4 * 86400)
    ok &= (ts[np.minimum(jj + HOURS - 1, len(ts) - 1)] - ts[jj] <= 9 * 86400)    # no hole in the path
    idx = np.where(ok)[0]
    J = j[idx][:, None] + np.arange(HOURS)[None, :]
    a = atr[idx][:, None]
    slip, cost = SLIPPAGE_PIPS * pip, MARKUP_PIPS * pip
    out = {}

    for side, sign in (("BUY", 1), ("SELL", -1)):
        if sign > 0:
            entry = path["ao"][j[idx]] + slip
            fav = (path["bh"][J] - entry[:, None]) / a
            adv = (entry[:, None] - path["bl"][J]) / a
            close = (path["bc"][J] - entry[:, None]) / a
        else:
            entry = path["bo"][j[idx]] - slip
            fav = (entry[:, None] - path["al"][J]) / a
            adv = (path["ah"][J] - entry[:, None]) / a
            close = (entry[:, None] - path["ac"][J]) / a
        out[side] = {"fav": np.maximum.accumulate(fav, axis=1).astype(np.float32),
                     "adv": np.maximum.accumulate(adv, axis=1).astype(np.float32),
                     "close": close[:, [t - 1 for t in TIMES]].astype(np.float32),
                     "cost": ((slip + cost) / atr[idx]).astype(np.float32)}

    ind = indicators(o, h, l, c, atr)
    fund = fundamental_agree(symbol, [dates[i] for i in idx], fund_rows)
    return {"symbol": symbol, "dates": [dates[i] for i in idx], "close": c[idx],
            "ind": {k: v[idx] for k, v in ind.items()}, "fund": fund, "sides": out}


def indicators(o, h, l, c, atr) -> dict:
    out = {"atr_pct": np.array([np.nan] * len(c))}
    from numpy.lib.stride_tricks import sliding_window_view
    pct = np.full(len(c), np.nan)
    if len(c) >= 250:                                    # shorter history: no percentile yet
        w = sliding_window_view(atr, 250)
        pct[249:] = (w <= w[:, -1:]).mean(axis=1)
    out["atr_pct"] = pct
    for n in (2, 3, 4):
        out[f"rsi{n}"] = SM.rsi(c, n)
    for n in (5, 9, 14):
        hh, ll = SM.rolling_max(h, n), SM.rolling_min(l, n)
        out[f"wr{n}"] = 100 * (c - ll) / np.where(hh - ll == 0, np.nan, hh - ll)       # 0 = lowest, 100 = highest
    for n in (5, 14):
        k = out.get(f"wr{n}", None)
        out[f"stoch{n}"] = SM.sma(np.nan_to_num(k if k is not None else
                                                100 * (c - SM.rolling_min(l, n)) /
                                                np.where(SM.rolling_max(h, n) - SM.rolling_min(l, n) == 0, np.nan,
                                                         SM.rolling_max(h, n) - SM.rolling_min(l, n)), nan=50), 3)
    for n, k in ((20, 2.0), (20, 1.5), (10, 2.0)):
        m = SM.sma(c, n)
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
    out["dist_sma5"] = (c - SM.sma(c, 5)) / atr
    out["kelt"] = (c - SM.ema(c, 20)) / atr
    for n in (50, 100, 200):
        out[f"sma{n}"] = np.sign(c - SM.sma(c, n))
    return out


def fundamental_agree(symbol: str, dates: list, fund_rows: dict) -> dict:
    """+1 / -1 / 0: fundamentals favour BUY / SELL / neither (>= 1 cluster, none against)."""
    out = np.zeros(len(dates))
    for k, d in enumerate(dates):
        r = fund_rows.get((symbol, d))
        if not r:
            continue
        signs = [np.sign(r[x]) for x in ("CARRY", "RATES_20D", "RISK_VIX_1W", "POLICY_TREND") if r.get(x)]
        pro, con = sum(1 for s in signs if s > 0), sum(1 for s in signs if s < 0)
        out[k] = 1 if pro and not con else -1 if con and not pro else 0
    return out


def signal_defs():
    """name -> (long condition, short condition) on the indicator dict."""
    d = {}
    for n in (2, 3, 4):
        for x in (5, 10, 15, 20, 25, 30):
            d[f"RSI{n}<{x}"] = (lambda I, n=n, x=x: I[f"rsi{n}"] < x, lambda I, n=n, x=x: I[f"rsi{n}"] > 100 - x)
    for n in (5, 9, 14):
        for x in (5, 10, 20):
            d[f"%R{n}<{x}"] = (lambda I, n=n, x=x: I[f"wr{n}"] < x, lambda I, n=n, x=x: I[f"wr{n}"] > 100 - x)
    for n in (5, 14):
        for x in (10, 20):
            d[f"Stoch{n}<{x}"] = (lambda I, n=n, x=x: I[f"stoch{n}"] < x, lambda I, n=n, x=x: I[f"stoch{n}"] > 100 - x)
    for key in ("bb20_2.0", "bb20_1.5", "bb10_2.0"):
        d[f"Bollinger {key[2:]} pod pasmem"] = (lambda I, k=key: I[k] < 0, lambda I, k=key: I[k] > 1)
    for x in (0.1, 0.2):
        d[f"IBS<{x}"] = (lambda I, x=x: I["ibs"] < x, lambda I, x=x: I["ibs"] > 1 - x)
    for k in (2, 3, 4):
        d[f"{k} dny dolu"] = (lambda I, k=k: I[f"down{k}"], lambda I, k=k: I[f"up{k}"])
    for k in (0.5, 1.0, 1.5):
        d[f"pod SMA5 o {k} ATR"] = (lambda I, k=k: I["dist_sma5"] < -k, lambda I, k=k: I["dist_sma5"] > k)
    for k in (1.0, 1.5, 2.0):
        d[f"pod Keltner {k}"] = (lambda I, k=k: I["kelt"] < -k, lambda I, k=k: I["kelt"] > k)
    return d


TRENDS = (None, "sma200", "sma100", "sma50")
FUNDS = (False, True)
VOLS = (None, "lt80", "gt30")


# ----------------------------------------------------------------------
# outcomes and masks
# ----------------------------------------------------------------------

def outcomes(side: dict) -> np.ndarray:
    """pnl in ATR(D1) per entry for every exit (entries x exits)."""
    fav, adv, close, cost = side["fav"], side["adv"], side["close"], side["cost"]
    out = np.empty((fav.shape[0], len(EXITS)), dtype=np.float32)
    for e, (tp, sl, tm) in enumerate(EXITS):
        t_tp = (fav < tp).sum(axis=1)                   # first hour reaching TP (HOURS = never)
        t_sl = (adv < sl).sum(axis=1)
        k = TIMES.index(tm)
        res = close[:, k] - cost                         # time exit at the hour close
        hit_tp = (t_tp < tm) & (t_tp < t_sl)             # same hour -> SL (conservative)
        hit_sl = (t_sl < tm) & (t_sl <= t_tp)
        res = np.where(hit_tp, tp - cost, res)
        res = np.where(hit_sl, -sl - cost, res)
        out[:, e] = res
    return out


def build() -> dict:
    fund_rows = {(r["symbol"], r["day"]): r for r in pickle.loads(SIGNALS_FILE.read_bytes())}
    defs = signal_defs()
    masks_meta = [(s, t, f, v) for s in defs for t in TRENDS for f in FUNDS for v in VOLS]
    O, D, P, M = [], [], [], []
    for symbol in parse_symbols(None):
        started = time.monotonic()
        e = entries_for_pair(symbol, fund_rows)
        I = e["ind"]
        for side, sign in (("BUY", 1), ("SELL", -1)):
            O.append(outcomes(e["sides"][side]))
            D.extend(e["dates"])
            P.extend([symbol] * len(e["dates"]))
            rows = np.zeros((len(masks_meta), len(e["dates"])), dtype=bool)
            for m, (s, t, f, v) in enumerate(masks_meta):
                with np.errstate(invalid="ignore"):
                    cond = np.nan_to_num(defs[s][0 if sign > 0 else 1](I)).astype(bool)
                    if t:
                        cond &= I[t] == sign
                    if f:
                        cond &= e["fund"] == sign
                    if v == "lt80":
                        cond &= I["atr_pct"] < 0.8
                    elif v == "gt30":
                        cond &= I["atr_pct"] > 0.3
                rows[m] = cond
            M.append(rows)
        print(f"{symbol}: {len(e['dates'])} dni | {time.monotonic() - started:.0f} s", flush=True)
    return {"O": np.vstack(O), "dates": np.array(D), "pairs": np.array(P), "M": np.hstack(M), "meta": masks_meta}


def stats(B: dict, period: tuple, extra: np.ndarray | None = None) -> dict:
    """win, E (ATR), E (R), n for every (mask, exit)."""
    sel = np.array([period[0] <= d <= period[1] for d in B["dates"]])
    if extra is not None:
        sel &= extra
    O = B["O"]
    W = (O > 0).astype(np.float32) * sel[:, None]
    R = O / np.array([sl for _, sl, _ in EXITS], dtype=np.float32)[None, :]
    S = np.where(sel[:, None], O, 0).astype(np.float32)
    SR = np.where(sel[:, None], R, 0).astype(np.float32)
    n_all = np.zeros((len(B["meta"]), len(EXITS)), dtype=np.float64)
    wins, sums, sumr = n_all.copy(), n_all.copy(), n_all.copy()
    for a in range(0, len(B["meta"]), 128):
        Mf = B["M"][a:a + 128].astype(np.float32)
        n_all[a:a + 128] = (Mf @ sel.astype(np.float32))[:, None]
        wins[a:a + 128] = Mf @ W
        sums[a:a + 128] = Mf @ S
        sumr[a:a + 128] = Mf @ SR
    with np.errstate(all="ignore"):
        return {"n": n_all, "win": wins / n_all, "e": sums / n_all, "er": sumr / n_all}


def trades_of(B: dict, m: int, e: int, period: tuple) -> np.ndarray:
    sel = B["M"][m] & np.array([period[0] <= d <= period[1] for d in B["dates"]])
    return np.where(sel)[0]


def clustered_t(B: dict, idx: np.ndarray, e: int) -> float:
    vals = B["O"][idx, e]
    if len(vals) < 20:
        return 0.0
    mean = vals.mean()
    weeks = {}
    for d, v in zip(B["dates"][idx], vals):
        k = tuple(d.isocalendar()[:2])
        weeks[k] = weeks.get(k, 0.0) + (v - mean)
    se = math.sqrt(sum(x * x for x in weeks.values())) / len(vals)
    return float(mean / se) if se else 0.0


def describe(B, m, e) -> str:
    s, t, f, v = B["meta"][m]
    tp, sl, tm = EXITS[e]
    parts = [s, {None: "bez trendu", "sma200": "s trendem SMA200", "sma100": "s trendem SMA100",
                 "sma50": "s trendem SMA50"}[t], "fundamenty souhlasi" if f else "bez fundamentu",
             {None: "", "lt80": "volatilita < 80. percentil", "gt30": "volatilita > 30. percentil"}[v]]
    return " / ".join(p for p in parts if p) + f" | TP {tp} ATR, SL {sl} ATR, max {tm // 24} d"


def main() -> int:
    started = time.monotonic()
    B = build()
    print(f"vstupu {len(B['dates'])}, systemu {len(B['meta']) * len(EXITS)} | {time.monotonic() - started:.0f} s",
          flush=True)
    st = {p: stats(B, span) for p, span in PERIODS.items()}
    tr, va, te = st["TRAIN"], st["VALID"], st["TEST"]
    ok = (tr["n"] >= 300) & (tr["win"] >= TARGET_WIN)
    cand = np.argwhere(ok)
    cand = cand[np.argsort(-tr["er"][ok])][:100]
    keep = [(m, e) for m, e in cand if va["n"][m, e] >= 100 and va["win"][m, e] >= TARGET_WIN]
    final = max(keep, key=lambda x: va["er"][x]) if keep else tuple(cand[0])
    systems_75 = int(ok.sum())
    positive_75 = int((ok & (tr["er"] > 0)).sum())

    # adaptive: every year re-learn on the trailing 4 years
    yearly = []
    for year in range(2018, 2027):
        span = (date(year - 4, 1, 1), date(year - 1, 12, 31))
        s = stats(B, span)
        good = (s["n"] >= 200) & (s["win"] >= TARGET_WIN)
        if not good.any():
            continue
        m, e = np.unravel_index(np.argmax(np.where(good, s["er"], -np.inf)), good.shape)
        idx = trades_of(B, m, e, (date(year, 1, 1), date(year, 12, 31)))
        vals = B["O"][idx, e]
        yearly.append((year, describe(B, m, e), len(vals), float((vals > 0).mean()) if len(vals) else None,
                       float(vals.mean()) if len(vals) else None, float((vals / EXITS[e][1]).mean()) if len(vals) else None))

    f = SM._f
    m, e = final
    out = ["# Hledani systemu s uspesnosti >= 75 %", "",
           f"_{len(B['meta'])} kombinaci vstupu x {len(EXITS)} vystupu = **{len(B['meta']) * len(EXITS)} systemu**; "
           f"{len(B['dates'])} moznych vstupu (12 paru x den x smer, 2014-2026) prehranych na hodinovych bid/ask "
           f"svickach s naklady. Vyber 2014-2019, potvrzeni 2020-2022, finalni test 2023-2026 (jen jednou)._", "",
           f"Systemu s uspesnosti >= 75 % na 2014-2019 (>= 300 obchodu): **{systems_75}**, z toho v zisku po nakladech: "
           f"**{positive_75}**.", "",
           "## Finalni system", "", f"**{describe(B, m, e)}**", "",
           "| obdobi | obchodu | uspesnost | E [ATR/obchod] | E [R/obchod] | t (tydenni shluky) |", "|---|---|---|---|---|---|"]
    for p, label in (("TRAIN", "2014-2019 (vyber)"), ("VALID", "2020-2022 (potvrzeni)"), ("TEST", "2023-2026 (test)")):
        idx = trades_of(B, m, e, PERIODS[p])
        out.append(f"| {label} | {int(st[p]['n'][m, e])} | {f(st[p]['win'][m, e], '.1%')} | {f(st[p]['e'][m, e], '+.3f')} | "
                   f"{f(st[p]['er'][m, e], '+.3f')} | {clustered_t(B, idx, e):+.1f} |")
    out += ["", "Po letech (finalni system):", "", "| rok | obchodu | uspesnost | E [ATR] |", "|---|---|---|---|"]
    for year in range(2014, 2027):
        idx = trades_of(B, m, e, (date(year, 1, 1), date(year, 12, 31)))
        if len(idx):
            v = B["O"][idx, e]
            out.append(f"| {year} | {len(v)} | {(v > 0).mean():.1%} | {v.mean():+.3f} |")
    out += ["", "Po parech 2020-2026 (finalni system):", "", "| par | obchodu | uspesnost | E [ATR] |", "|---|---|---|---|"]
    idx_all = trades_of(B, m, e, (date(2020, 1, 1), date(2026, 9, 30)))
    for pair in parse_symbols(None):
        v = B["O"][idx_all[B["pairs"][idx_all] == pair], e]
        if len(v):
            out.append(f"| {pair} | {len(v)} | {(v > 0).mean():.1%} | {v.mean():+.3f} |")
    out += ["", "## 10 nejlepsich z vyberu (>= 75 % na 2014-2019) a jak dopadly pozdeji", "",
            "| system | 2014-19 uspesnost / E[R] | 2020-22 uspesnost / E[R] | 2023-26 uspesnost / E[R] |", "|---|---|---|---|"]
    for mm, ee in cand[:10]:
        cells = [f"{f(st[p]['win'][mm, ee], '.0%')} / {f(st[p]['er'][mm, ee], '+.3f')} (n {int(st[p]['n'][mm, ee])})"
                 for p in ("TRAIN", "VALID", "TEST")]
        out.append(f"| {describe(B, mm, ee)} | " + " | ".join(cells) + " |")
    out += ["", "## Adaptivni varianta: kazdy rok preuceni na poslednich 4 letech", "",
            "| rok | vybrany system | obchodu | uspesnost | E [ATR] | E [R] |", "|---|---|---|---|---|---|"]
    allv = []
    for year, desc, n, win, ea, er in yearly:
        out.append(f"| {year} | {desc} | {n} | {f(win, '.1%')} | {f(ea, '+.3f')} | {f(er, '+.3f')} |")
    out += ["", f"_vypocet {time.monotonic() - started:.0f} s_"]
    (PROJECT_ROOT / "docs" / "USPESNOST75.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    (PROJECT_ROOT / "data" / "research" / "winrate_final.pkl").write_bytes(pickle.dumps(
        {"final": (int(m), int(e)), "meta": B["meta"][m], "exit": EXITS[e], "yearly": yearly}))
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
