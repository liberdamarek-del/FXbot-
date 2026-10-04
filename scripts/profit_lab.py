"""Profit-per-trade search: every trade aims at >= 10 % of the margin at
leverage 1:30 (= a price move of >= 0.333 %), win rate as high as possible,
the result after costs as large as possible. Holding up to 4 weeks.

    python scripts/profit_lab.py      # -> docs/ZISK10.md (~5 min, needs numpy)

Systems = signal x trend filter x carry filter x decision rhythm (every day /
only at the week close) x entry (market / limit 0.5 / 1.0 ATR better) x exit
(TP 0.5-3 ATR, SL 1-4 ATR, max 5 / 10 / 20 days). A trade is taken only when
its TP is >= 0.333 % of the price.

Prices: daily mid OHLC (2013-2026, FXCM + Dukascopy), costs = typical retail
spread + 0.4 pip slippage, financing = 2y rate difference -/+ 1 % p.a. broker
markup per calendar day held. TP and SL on the same day = SL (conservative).
Result units: % of the margin = 30 x net price change in %.

Selection on 2014-2022 (both 2014-19 and 2020-22 must meet the conditions),
shown once on 2023-2026.
"""

import pickle
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import research_signals as RS  # noqa: E402  (loads .env first)
import strategy_mining as SM  # noqa: E402
import winrate_lab as W1  # noqa: E402
from src.instruments import get_instrument, parse_symbols  # noqa: E402
from src.path_archive import trading_date  # noqa: E402

LEVERAGE = 30
MIN_TP_PCT = 10.0 / LEVERAGE            # % price move for 10 % of the margin
DAYS = 20
TPS = (0.5, 0.75, 1.0, 1.5, 2.0, 3.0)
SLS = (1.0, 1.5, 2.0, 3.0, 4.0)
HOLDS = (5, 10, 20)
EXITS = [(tp, sl, hd) for tp in TPS for sl in SLS for hd in HOLDS]
ENTRIES = (("MARKET", 0.0), ("LIMIT 0.5", 0.5), ("LIMIT 1.0", 1.0))
PERIODS = {"A": (date(2014, 1, 1), date(2019, 12, 31)), "B": (date(2020, 1, 1), date(2022, 12, 31)),
           "TEST": (date(2023, 1, 1), date(2026, 9, 30))}


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
    state = {m: (SM.wilder(np.clip(d, 0, None), m), SM.wilder(np.clip(-d, 0, None), m)) for m in (2, 3)}
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


def signal_defs():
    d = {}
    # daily mean reversion
    for n, x in ((2, 5), (2, 10), (3, 15), (3, 20)):
        d[f"D RSI{n}<{x}"] = (lambda I, n=n, x=x: I[f"rsi{n}"] < x, lambda I, n=n, x=x: I[f"rsi{n}"] > 100 - x)
    for n, x in ((9, 5), (14, 10)):
        d[f"D %R{n}<{x}"] = (lambda I, n=n, x=x: I[f"wr{n}"] < x, lambda I, n=n, x=x: I[f"wr{n}"] > 100 - x)
    d["D 3 dny dolu"] = (lambda I: I["down3"], lambda I: I["up3"])
    d["D pod SMA5 o 1.5 ATR"] = (lambda I: I["dist_sma5"] < -1.5, lambda I: I["dist_sma5"] > 1.5)
    # weekly mean reversion (decided at the week close)
    for n, x in ((2, 10), (2, 20), (3, 20), (3, 30)):
        d[f"W RSI{n}<{x}"] = (lambda I, n=n, x=x: I[f"w_rsi{n}"] < x, lambda I, n=n, x=x: I[f"w_rsi{n}"] > 100 - x)
    d["W %R4<10"] = (lambda I: I["w_wr4"] < 10, lambda I: I["w_wr4"] > 90)
    d["W %R4<20"] = (lambda I: I["w_wr4"] < 20, lambda I: I["w_wr4"] > 80)
    # trend following
    d["D Donchian20 pruraz"] = (lambda I: I["brk20"] > 0, lambda I: I["brk20"] < 0)
    d["W 52-tydenni maximum"] = (lambda I: I["w_close"] >= I["w_hi52"], lambda I: I["w_close"] <= I["w_lo52"])
    d["D EMA20 x EMA50 cerstve"] = (lambda I: I["cross"] > 0, lambda I: I["cross"] < 0)
    return d


TRENDS = (None, "sma200", "w_sma40")
CARRY = (False, True)
RHYTHM = ("DEN", "TYDEN")


def build() -> dict:
    fund_rows = {(r["symbol"], r["day"]): r for r in pickle.loads(RS.SIGNALS_FILE.read_bytes())}
    defs = signal_defs()
    meta = [(en, s, t, cy, r) for en, _ in ENTRIES for s in defs for t in TRENDS for cy in CARRY for r in RHYTHM
            if not (s.startswith("W ") and r == "DEN")]
    O, V, D, P, M = [], [], [], [], []
    for symbol in parse_symbols(None):
        t0 = time.monotonic()
        bars, _ = RS.stitched_daily(symbol)
        dates = [trading_date(b.ts) for b in bars]
        o, h, l, c = (np.array([getattr(b, k) for b in bars]) for k in ("mo", "mh", "ml", "mc"))
        ts = np.array([b.ts for b in bars])
        atr = SM.wilder(SM.true_range(h, l, c), 14)
        I = W1.indicators(o, h, l, c, atr)
        I.update(weekly_aligned(dates, o, h, l, c))
        prev_hi, prev_lo = SM.shift(SM.rolling_max(h, 20)), SM.shift(SM.rolling_min(l, 20))
        I["brk20"] = np.where(c > prev_hi, 1, np.where(c < prev_lo, -1, 0))
        e20, e50 = SM.ema(c, 20), SM.ema(c, 50)
        diff = np.sign(e20 - e50)
        I["cross"] = np.where(diff != SM.shift(diff), diff, 0)
        I["w_sma40"] = np.sign(c - I["w_sma40"])
        carry = np.array([fund_rows.get((symbol, d), {}).get("CARRY") or 0.0 for d in dates])
        inst = get_instrument(symbol)
        half = (RS.SPREAD_PIPS[symbol] / 2 + RS.SLIPPAGE_PIPS / 2) * inst.pip      # per side
        gap = np.concatenate([[False], np.diff(ts) > 9 * 86400])
        base = np.array([i for i in range(260, len(c) - DAYS - 6)
                         if not np.isnan(atr[i]) and not gap[i + 1:i + DAYS + 7].any()])
        for en, k in ENTRIES:
            for side in (1, -1):
                a_all = atr[base]
                if k == 0:
                    idx, fill, entry = base, base, c[base] + side * half
                else:
                    level = c[base] - side * k * a_all
                    window = np.where(I["week_end"][base], 5, 1)
                    fill = np.full(len(base), -1)
                    for q in range(5, 0, -1):          # the earliest fill wins
                        hit = ((l[base + q] - half <= level) if side > 0 else (h[base + q] + half >= level)) & (q <= window)
                        fill = np.where(hit, base + q, fill)
                    ok = fill >= 0
                    idx, fill, entry = base[ok], fill[ok], level[ok]
                a_i = atr[idx]
                span = fill[:, None] + 1 + np.arange(DAYS)[None, :]
                hi, lo, cl = h[span], l[span], c[span]
                if side > 0:
                    fav, adv, close = hi - half - entry[:, None], entry[:, None] - (lo - half), cl - half - entry[:, None]
                else:
                    fav, adv, close = entry[:, None] - (lo + half), (hi + half) - entry[:, None], entry[:, None] - (cl + half)
                if k:   # fill day: adverse part after the fill counts, favourable not
                    adv0 = (entry - (l[fill] - half)) if side > 0 else ((h[fill] + half) - entry)
                    adv = np.maximum(adv, adv0[:, None])
                fav_c, adv_c = np.maximum.accumulate(fav, axis=1), np.maximum.accumulate(adv, axis=1)
                days_held = (ts[span] - ts[fill][:, None]) / 86400
                fin = (side * carry[idx] - 1.0)[:, None] / 100 / 365 * days_held * entry[:, None]
                res = np.empty((len(idx), len(EXITS)), dtype=np.float32)
                val = np.empty((len(idx), len(EXITS)), dtype=bool)
                rows = np.arange(len(idx))
                for e, (tp, sl, hd) in enumerate(EXITS):
                    TP, SL = tp * a_i, sl * a_i
                    val[:, e] = TP / entry * 100 >= MIN_TP_PCT
                    t_tp = (fav_c[:, :hd] < TP[:, None]).sum(axis=1)
                    t_sl = (adv_c[:, :hd] < SL[:, None]).sum(axis=1)
                    sl_hit = (t_sl < hd) & (t_sl <= t_tp)
                    tp_hit = (t_tp < hd) & ~sl_hit
                    pnl = close[:, hd - 1] + fin[:, hd - 1]
                    pnl = np.where(tp_hit, TP + fin[rows, np.minimum(t_tp, hd - 1)], pnl)
                    pnl = np.where(sl_hit, -SL + fin[rows, np.minimum(t_sl, hd - 1)], pnl)
                    res[:, e] = pnl / entry * 100 * LEVERAGE                # % of the margin
                if not len(idx):
                    continue
                O.append(res)
                V.append(val)
                D.extend(dates[i] for i in idx)
                P.extend([symbol] * len(idx))
                mask = np.zeros((len(meta), len(idx)), dtype=bool)
                Ii = {kk: vv[idx] for kk, vv in I.items()}
                for m, (en2, s, t, cy, r) in enumerate(meta):
                    if en2 != en:
                        continue
                    with np.errstate(invalid="ignore"):
                        cond = np.nan_to_num(defs[s][0 if side > 0 else 1](Ii)).astype(bool)
                        if t:
                            cond &= Ii[t] == side
                        if cy:
                            cond &= np.sign(carry[idx]) == side
                        if r == "TYDEN" or s.startswith("W "):
                            cond &= Ii["week_end"]
                    mask[m] = cond
                M.append(mask)
        print(f"{symbol}: {time.monotonic() - t0:.0f} s", flush=True)
    return {"O": np.vstack(O), "V": np.vstack(V), "dates": np.array(D), "pairs": np.array(P), "M": np.hstack(M),
            "meta": meta}


def stats(B, period):
    sel = np.array([period[0] <= d <= period[1] for d in B["dates"]], dtype=np.float32)
    Vf = B["V"].astype(np.float32) * sel[:, None]
    O = np.where(B["V"], B["O"], 0).astype(np.float32) * sel[:, None]
    Wn = ((B["O"] > 0) & B["V"]).astype(np.float32) * sel[:, None]
    O2 = O * O
    shape = (len(B["meta"]), len(EXITS))
    n, w, s, s2 = (np.zeros(shape) for _ in range(4))
    for a in range(0, len(B["meta"]), 128):
        Mf = B["M"][a:a + 128].astype(np.float32)
        n[a:a + 128], w[a:a + 128], s[a:a + 128], s2[a:a + 128] = Mf @ Vf, Mf @ Wn, Mf @ O, Mf @ O2
    with np.errstate(all="ignore"):
        e = s / n
        sd = np.sqrt(np.maximum(s2 / n - e * e, 0))
        return {"n": n, "win": w / n, "e": e, "t": e / (sd / np.sqrt(n))}


def name(B, m, ex):
    en, s, t, cy, r = B["meta"][m]
    tp, sl, hd = EXITS[ex]
    tr = {None: "bez trendu", "sma200": "trend SMA200", "w_sma40": "trend tydenni SMA40"}[t]
    return (f"{en} / {s} / {tr}{' / carry souhlasi' if cy else ''} / {'jen na konci tydne' if r == 'TYDEN' else 'denne'}"
            f" | TP {tp} ATR, SL {sl} ATR, max {hd} d")


def main() -> int:
    started = time.monotonic()
    B = build()
    print(f"vstupu {len(B['dates'])}, systemu {len(B['meta']) * len(EXITS)} | {time.monotonic() - started:.0f} s",
          flush=True)
    st = {p: stats(B, span) for p, span in PERIODS.items()}
    a, b, te = st["A"], st["B"], st["TEST"]
    f = SM._f
    years_a, years_b = 6.0, 3.0
    enough = (a["n"] >= 6 * years_a) & (b["n"] >= 6 * years_b)       # at least ~6 trades per year

    def table(mask, key, title, k=15):
        score = np.where(mask, key, -np.inf)
        order = np.argsort(-score, axis=None)[:k]
        lines = [f"## {title}", "", f"Splnuje: **{int(mask.sum())}** systemu.", "",
                 "| system | 2014-19 n / usp. / zisk na obchod | 2020-22 | **2023-26 (test)** | obchodu za rok |",
                 "|---|---|---|---|---|"]
        for flat in order:
            m, ex = np.unravel_index(flat, score.shape)
            if not np.isfinite(score[m, ex]):
                break
            cells = [f"{int(st[p]['n'][m, ex])} / {f(st[p]['win'][m, ex], '.0%')} / {f(st[p]['e'][m, ex], '+.1f')} %"
                     for p in ("A", "B", "TEST")]
            per_year = (a["n"][m, ex] + b["n"][m, ex] + te["n"][m, ex]) / 12.75
            lines.append(f"| {name(B, m, ex)} | " + " | ".join(cells) + f" | {per_year:.0f} |")
        return lines + [""]

    worst_e = np.minimum(a["e"], b["e"])
    worst_win = np.minimum(a["win"], b["win"])
    out = ["# Zisk na obchod >= 10 % marze (paka 1:30)", "",
           f"_{len(B['meta']) * len(EXITS)} systemu; kazdy obchod s cilem >= {MIN_TP_PCT:.3f} % ceny (= 10 % marze); "
           f"zisk v % marze po spreadu, skluzu a swapu; vyber 2014-2022, test 2023-2026._", ""]
    out += table(enough & (worst_win >= 0.75) & (worst_e > 0), worst_e,
                 "A) Uspesnost >= 75 % a zisk v obou vyberovych obdobich - serazeno podle horsiho prumerneho zisku")
    out += table(enough & (worst_e >= 10), worst_win,
                 "B) Prumerny zisk na obchod >= 10 % marze v obou obdobich - serazeno podle horsi uspesnosti")
    out += table(enough & (worst_e > 0), worst_e, "C) Nejvyssi prumerny zisk na obchod (bez podminky uspesnosti)")
    out += [f"_vypocet {time.monotonic() - started:.0f} s_"]
    (PROJECT_ROOT / "docs" / "ZISK10.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    pickle.dump({"meta": B["meta"]}, open(PROJECT_ROOT / "data" / "research" / "profit_meta.pkl", "wb"))
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
