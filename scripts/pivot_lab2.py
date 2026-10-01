"""Pivot lab 2: the user's method as he trades it (2026-10-01: shorts at the
daily pivot P / R2, e.g. EUR/CHF 0.947, GBP/CHF 1.107, USD/JPY 158.33) -
fading classic pivot levels with or without the SMA 50 - tested on every
day of 2012-2026 for the 12 live pairs, trade by trade on hourly BID/ASK.

    python scripts/pivot_lab2.py          # -> docs/PIVOTY2.md, data/research/pivot2/

Levels  classic pivots of the previous DAY / WEEK / MONTH (mid H, L, C):
        P=(H+L+C)/3, R1=2P-L, S1=2P-H, R2=P+(H-L), S2=P-(H-L), R3=H+2(P-L), S3=L-2(H-P)
Setup   SELL at P / R1 / R2 when the period opens below the level (resistance),
        BUY at P / S1 / S2 when it opens above (support); one trade per level,
        side and period
Entry   LIMIT at the level (the first touch), or POTVRZENI: after the touch the
        first hourly close back on the other side of the level (at that close)
Exit    TP at the next level toward the pivot (SELL R2->R1, R1->P, P->S1) or
        0.5 / 1.0 x ATR(14); SL at the next level beyond (SELL P->R1, R1->R2,
        R2->R3) or 1.0 x ATR; time: end of the pivot period or a fixed
        5 / 10 / 20 trading days (DAY / WEEK / MONTH)
Filter  none | SMA50 daily with the trade | SMA50 daily AGAINST the trade
        (as on 2026-10-01) | SMA50 weekly with the trade | the Friday model's
        rate divergence with the trade
Costs   retail spread + slippage (profit_lab2.SPREAD_PIPS), swap; TP and SL in
        the same hour = SL; the fill hour's adverse move counts.
Units   % of the margin at 1:30 (= 30 x the net price move in %).

Protocol: the variants are ranked on 2012-2018 only and shown on 2019-2022
and 2023-2026; then ranked on 2012-2022 and shown on 2023-2026, and checked
separately on the 7 USD pairs and the 5 crosses.
"""

import itertools
import pickle
import sys
import time
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import profit_lab2 as P  # noqa: E402
import strategy_mining as SM  # noqa: E402
from src.instruments import DEFAULT_ACTIVE, get_instrument  # noqa: E402

OUT = PROJECT_ROOT / "data" / "research" / "pivot2"
TFS = ("DEN", "TYDEN", "MESIC")
FIXED_BARS = {"DEN": 120, "TYDEN": 240, "MESIC": 480}
LEVELS = ("P", "1", "2")
MODES = ("LIMIT", "POTVRZENI")
TP_KINDS = ("uroven", "0.5ATR", "1.0ATR")
SL_KINDS = ("uroven", "1.0ATR")
TIMES = ("konec obdobi", "pevne")
FILTERS = ("zadny", "SMA50 s obchodem", "SMA50 proti obchodu", "SMA50 tydenni s obchodem", "sazby s obchodem")
SPANS = {"2012-18": (date(2012, 1, 1), date(2018, 12, 31)), "2019-22": (date(2019, 1, 1), date(2022, 12, 31)),
         "2023-26": (date(2023, 1, 1), date(2026, 9, 30))}


def pivots(h, l, c):
    p = (h + l + c) / 3
    return {"P": p, "R1": 2 * p - l, "S1": 2 * p - h, "R2": p + (h - l), "S2": p - (h - l),
            "R3": h + 2 * (p - l), "S3": l - 2 * (h - p)}


def level_triplet(pv: dict, side: int, k: str):
    """(entry level, TP level, SL level) for a setup."""
    if side < 0:
        return {"P": ("P", "S1", "R1"), "1": ("R1", "P", "R2"), "2": ("R2", "R1", "R3")}[k]
    return {"P": ("P", "R1", "S1"), "1": ("S1", "P", "S2"), "2": ("S2", "S1", "S3")}[k]


def periods(s: dict, tf: str) -> list:
    """(day index of the period's first day, last day index, pivot source day indices)."""
    days = s["days"]
    if tf == "DEN":
        keys = list(range(len(days)))
    elif tf == "TYDEN":
        keys = [tuple(d.isocalendar()[:2]) for d in days]
    else:
        keys = [(d.year, d.month) for d in days]
    groups, order = defaultdict(list), []
    for i, k in enumerate(keys):
        if k not in groups:
            order.append(k)
        groups[k].append(i)
    out = []
    for prev, cur in zip(order, order[1:]):
        out.append((groups[cur][0], groups[cur][-1], groups[prev]))
    return out


def build_pair(symbol: str, rates: dict) -> list:
    """All fills of all setups of one pair, with the path statistics needed for every exit."""
    s = P.series(symbol)
    I = P.indicators(s, rates, symbol)
    inst = get_instrument(symbol)
    half = (P.SPREAD_PIPS[symbol] / 2 + P.SLIPPAGE_PIPS / 2) * inst.pip
    ts, ho, hh, hl, hc = s["ts"], s["o"], s["h"], s["l"], s["c"]
    dh, dl, dc = s["dh"], s["dl"], s["dc"]
    atr = I["atr"]
    sma50 = SM.sma(dc, 50)
    wk_sma = I["w_sma40v"]          # weekly SMA (40 weeks in profit_lab2) - only its side is used below
    # weekly SMA50 on completed weeks
    wkeys = [tuple(d.isocalendar()[:2]) for d in s["days"]]
    wclose, worder = {}, []
    for k, c in zip(wkeys, dc):
        if k not in wclose:
            worder.append(k)
        wclose[k] = c
    wc = np.array([wclose[k] for k in worder])
    wsma = SM.sma(wc, 50)
    wpos = {k: i for i, k in enumerate(worder)}
    wsma_prev = np.array([wsma[wpos[k] - 1] if wpos[k] >= 1 else np.nan for k in wkeys])
    del wk_sma
    hour_gap = np.concatenate([[0], (np.diff(ts) > 100 * 3600).astype(int)])
    gap_cum = np.cumsum(hour_gap)
    fills = []
    for tf in TFS:
        for first_day, last_day, src in periods(s, tf):
            d0 = first_day - 1                          # decision day: the last day before the period
            if d0 < 260 or np.isnan(atr[d0]):
                continue
            a, b = s["first"][first_day], s["last"][last_day]
            if gap_cum[b] != gap_cum[a]:
                continue
            pv = pivots(dh[src].max(), dl[src].min(), dc[src[-1]])
            open_px = ho[a]
            for side, k in itertools.product((1, -1), LEVELS):
                lv, tpl, sll = level_triplet(pv, side, k)
                X = pv[lv]
                if (side < 0 and not open_px < X) or (side > 0 and not open_px > X):
                    continue
                seg_h, seg_l = hh[a:b + 1], hl[a:b + 1]
                touch = (seg_h - half >= X) if side < 0 else (seg_l + half <= X)
                if not touch.any():
                    continue
                f0 = a + int(np.argmax(touch))
                for mode in MODES:
                    if mode == "LIMIT":
                        fill, entry = f0, X
                        adv0 = ((hh[f0] + half) - X) if side < 0 else (X - (hl[f0] - half))
                    else:
                        back = (hc[f0:b + 1] < X) if side < 0 else (hc[f0:b + 1] > X)
                        if not back.any():
                            continue
                        fill = f0 + int(np.argmax(back))
                        entry = (hc[fill] - half) if side < 0 else (hc[fill] + half)
                        adv0 = 0.0
                    fills.append({
                        "pair": symbol, "tf": tf, "level": k, "mode": mode, "side": side,
                        "day": s["days"][first_day], "fill": fill, "end_period": b, "entry": entry, "adv0": adv0,
                        "tp_level": pv[tpl], "sl_level": pv[sll], "atr": float(atr[d0]),
                        "f_sma": np.sign(dc[d0] - sma50[d0]) if not np.isnan(sma50[d0]) else 0.0,
                        "f_wsma": np.sign(dc[d0] - wsma_prev[d0]) if not np.isnan(wsma_prev[d0]) else 0.0,
                        "f_rates": np.sign(I["rates_mom"][d0]) if not np.isnan(I["rates_mom"][d0]) else 0.0,
                        "carry": float(I["carry_fin"][d0]), "half": half})
    return fills, (ts, hh, hl, hc)


def outcomes(fills: list, path, tf: str) -> np.ndarray:
    """Result (% of the margin) of every fill for every exit (tp kind x sl kind x time)."""
    ts, hh, hl, hc = path
    n = len(fills)
    exits = list(itertools.product(TP_KINDS, SL_KINDS, TIMES))
    res = np.full((n, len(exits)), np.nan, dtype=np.float32)
    if not n:
        return res
    W = FIXED_BARS[tf]
    maxw = max(W, max(f["end_period"] - f["fill"] for f in fills) + 1)
    start = np.array([f["fill"] + 1 for f in fills])
    span = np.minimum(start[:, None] + np.arange(maxw)[None, :], len(ts) - 1)
    side = np.array([f["side"] for f in fills], dtype=float)
    entry = np.array([f["entry"] for f in fills])
    half = np.array([f["half"] for f in fills])
    H, Lw, C = hh[span], hl[span], hc[span]
    fav = np.where(side[:, None] > 0, H - half[:, None] - entry[:, None], entry[:, None] - (Lw + half[:, None]))
    adv = np.where(side[:, None] > 0, entry[:, None] - (Lw - half[:, None]), (H + half[:, None]) - entry[:, None])
    close = np.where(side[:, None] > 0, C - half[:, None] - entry[:, None], entry[:, None] - (C + half[:, None]))
    adv = np.maximum(adv, np.array([f["adv0"] for f in fills])[:, None])
    fav_c, adv_c = np.maximum.accumulate(fav, axis=1), np.maximum.accumulate(adv, axis=1)
    held = (ts[span] + 3600 - ts[np.array([f["fill"] for f in fills])][:, None]) / 86400
    fin = (side * np.array([f["carry"] for f in fills]) - P.FIN_MARKUP)[:, None] / 100 / 365 * held * entry[:, None]
    atr = np.array([f["atr"] for f in fills])
    tp_lv = np.array([f["tp_level"] for f in fills])
    sl_lv = np.array([f["sl_level"] for f in fills])
    rows = np.arange(n)
    for e, (tpk, slk, tk) in enumerate(exits):
        TP = side * (tp_lv - entry) if tpk == "uroven" else float(tpk.split("ATR")[0]) * atr
        SL = side * (entry - sl_lv) if slk == "uroven" else float(slk.split("ATR")[0]) * atr
        L = (np.array([f["end_period"] - f["fill"] for f in fills]) if tk == "konec obdobi" else np.full(n, W))
        L = np.clip(L, 1, maxw)
        ok = (TP > 0) & (SL > 0)
        idx = np.arange(maxw)[None, :]
        within = idx < L[:, None]
        t_tp = np.where(within & (fav_c >= TP[:, None]), idx, maxw).min(axis=1)
        t_sl = np.where(within & (adv_c >= SL[:, None]), idx, maxw).min(axis=1)
        sl_hit = (t_sl < L) & (t_sl <= t_tp)
        tp_hit = (t_tp < L) & ~sl_hit
        last = L - 1
        pnl = close[rows, last] + fin[rows, last]
        pnl = np.where(tp_hit, TP + fin[rows, np.minimum(t_tp, maxw - 1)], pnl)
        pnl = np.where(sl_hit, -SL + fin[rows, np.minimum(t_sl, maxw - 1)], pnl)
        res[:, e] = np.where(ok, pnl / entry * 100 * P.LEVERAGE, np.nan)
    return res


def build() -> dict:
    rates = P.monthly_rates()
    rows, res_all = [], []
    t0 = time.monotonic()
    for symbol in DEFAULT_ACTIVE:
        fills, path = build_pair(symbol, rates)
        for tf in TFS:
            sub = [f for f in fills if f["tf"] == tf]
            res_all.append(outcomes(sub, path, tf))
            rows.extend(sub)
        print(f"{symbol}: {len(fills)} vstupu, {time.monotonic() - t0:.0f} s", flush=True)
    keep = ("pair", "tf", "level", "mode", "side", "day", "f_sma", "f_wsma", "f_rates", "atr", "entry")
    meta = {k: np.array([r[k] for r in rows]) for k in keep}
    meta["tp_pct"] = np.array([abs(r["tp_level"] - r["entry"]) / r["entry"] * 100 for r in rows])
    data = {"meta": meta, "res": np.vstack(res_all), "exits": list(itertools.product(TP_KINDS, SL_KINDS, TIMES))}
    OUT.mkdir(parents=True, exist_ok=True)
    pickle.dump(data, open(OUT / "pivot2.pkl", "wb"))
    return data


def filter_mask(meta: dict, name: str) -> np.ndarray:
    side = meta["side"]
    if name == "zadny":
        return np.ones(len(side), dtype=bool)
    if name == "SMA50 s obchodem":
        return meta["f_sma"] == side
    if name == "SMA50 proti obchodu":
        return meta["f_sma"] == -side
    if name == "SMA50 tydenni s obchodem":
        return meta["f_wsma"] == side
    return meta["f_rates"] == side


def summary(x: np.ndarray, days: np.ndarray) -> dict:
    if len(x) == 0:
        return {"n": 0, "win": np.nan, "e": np.nan, "t": np.nan}
    by = defaultdict(float)
    m = x.mean()
    for d, v in zip(days, x):
        by[d] += v - m
    se = np.sqrt(sum(v * v for v in by.values())) / len(x)
    return {"n": len(x), "win": float((x > 0).mean()), "e": float(m), "t": float(m / se) if se > 0 else 0.0}


def evaluate(data: dict) -> list:
    meta, res, exits = data["meta"], data["res"], data["exits"]
    days = meta["day"]
    span_masks = {k: (days >= a) & (days <= b) for k, (a, b) in SPANS.items()}
    usd = np.array(["USD" in p for p in meta["pair"]])
    variants = []
    for tf, lv, mode, flt in itertools.product(TFS, LEVELS, MODES, FILTERS):
        base = (meta["tf"] == tf) & (meta["level"] == lv) & (meta["mode"] == mode) & filter_mask(meta, flt)
        for e, ex in enumerate(exits):
            col = res[:, e]
            ok = base & ~np.isnan(col)
            v = {"tf": tf, "level": lv, "mode": mode, "filter": flt, "exit": ex}
            for k, sm in span_masks.items():
                sel = ok & sm
                v[k] = summary(col[sel], days[sel])
            sel = ok & span_masks["2023-26"]
            v["2023-26 USD"] = summary(col[sel & usd], days[sel & usd])
            v["2023-26 krize"] = summary(col[sel & ~usd], days[sel & ~usd])
            v["tp10"] = summary(col[ok & (meta["tp_pct"] >= 1 / 3)], days[ok & (meta["tp_pct"] >= 1 / 3)])
            variants.append(v)
    return variants


def name(v: dict) -> str:
    lv = {"P": "P", "1": "R1/S1", "2": "R2/S2"}[v["level"]]
    tpk, slk, tk = v["exit"]
    return (f"{v['tf']} pivot {lv} / {v['mode']} / {v['filter']} / TP {tpk}, SL {slk}, {tk}")


def cell(s: dict) -> str:
    if not s["n"]:
        return "0"
    return f"{s['n']} / {s['win']:.0%} / {s['e']:+.1f} % (t {s['t']:.1f})"


def main() -> int:
    started = time.monotonic()
    path = OUT / "pivot2.pkl"
    data = pickle.load(open(path, "rb")) if path.exists() and "--rebuild" not in sys.argv else build()
    variants = evaluate(data)
    pickle.dump(variants, open(OUT / "variants.pkl", "wb"))
    out = ["# Pivoty 2: tvoje metoda na 12 parech, kazdy den 2012-2026", "",
           f"_{len(variants)} variant (pivot den/tyden/mesic x uroven P/R1/R2 x vstup limit/potvrzeni x filtr SMA50 x "
           "cil x stop x drzeni), obchod po obchodu na hodinovych BID/ASK FXCM, retail spread + skluz + swap. "
           "Zisk v % marze pri pace 1:30; n / uspesnost / prumer na obchod (t = jistota, nad ~2 neni nahoda, "
           "shlukovano po dnech)._", ""]
    enough = [v for v in variants if v["2012-18"]["n"] >= 200 and v["2019-22"]["n"] >= 100]
    pos_all = [v for v in enough if all(v[k]["e"] > 0 for k in SPANS)]
    out += [f"Variant s dost obchody: {len(enough)}; kladnych ve vsech trech obdobich: **{len(pos_all)}**; "
            f"prumer vsech variant: " + " / ".join(f"{np.nanmean([v[k]['e'] for v in enough]):+.1f} %" for k in SPANS)
            + " (2012-18 / 2019-22 / 2023-26).", ""]
    head = "| varianta | 2012-18 | 2019-22 | **2023-26** | 2023-26 USD pary | 2023-26 krize |"
    for title, key in (("A) Vyber podle 2012-2018 (10 nejlepsich) - jak dopadly pozdeji", lambda v: v["2012-18"]["e"]),
                       ("B) Vyber podle 2012-2022 (horsi z obou obdobi) - jak dopadly v 2023-2026",
                        lambda v: min(v["2012-18"]["e"], v["2019-22"]["e"]))):
        top = sorted(enough, key=key, reverse=True)[:10]
        out += [f"## {title}", "", head, "|---|---|---|---|---|---|"]
        out += [f"| {name(v)} | {cell(v['2012-18'])} | {cell(v['2019-22'])} | **{cell(v['2023-26'])}** | "
                f"{cell(v['2023-26 USD'])} | {cell(v['2023-26 krize'])} |" for v in top]
        out += [""]
    # by dimension
    out += ["## Prumer podle jednotlivych voleb (vsechny varianty s dost obchody)", "",
            "| volba | 2012-18 | 2019-22 | 2023-26 |", "|---|---|---|---|"]
    for dim, vals in (("tf", TFS), ("level", LEVELS), ("mode", MODES), ("filter", FILTERS)):
        for val in vals:
            vs = [v for v in enough if v[dim] == val]
            if vs:
                out.append(f"| {dim}: {val} | " + " | ".join(f"{np.nanmean([v[k]['e'] for v in vs]):+.1f} %" for k in SPANS) + " |")
    out += ["", "## Pripad 2026-10-01 (tvoje vstupy): denni pivot, short na P / R2 proti SMA50", "",
            head, "|---|---|---|---|---|---|"]
    mine = [v for v in variants if v["tf"] == "DEN" and v["level"] in ("P", "2") and v["filter"] in ("zadny", "SMA50 proti obchodu")
            and v["mode"] == "LIMIT" and v["exit"][1] == "uroven"]
    for v in sorted(mine, key=lambda v: v["2012-18"]["e"], reverse=True)[:8]:
        out.append(f"| {name(v)} | {cell(v['2012-18'])} | {cell(v['2019-22'])} | **{cell(v['2023-26'])}** | "
                   f"{cell(v['2023-26 USD'])} | {cell(v['2023-26 krize'])} |")
    out += ["", f"_vypocet {time.monotonic() - started:.0f} s_"]
    (PROJECT_ROOT / "docs" / "PIVOTY2.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
