"""Round 2 of the high win-rate search: keep >= 75 % winners, raise the result.

    python scripts/winrate_lab2.py      # -> docs/USPESNOST75_K2.md (~5 min)

New against round 1 (scripts/winrate_lab.py):
    entry    MARKET (next hour after the close) | LIMIT 0.25 / 0.5 x ATR(D1)
             better than the close, valid 24 h
    exit     fixed TP + SL + time (as round 1) | Connors exit: first daily
             close above SMA5 (BUY; below for SELL) + SL, max 5 days
    signals  oversold oscillators and pairs of them (Williams %R + IBS,
             RSI2 + IBS)
    cost     none | only trades whose cost is <= 3 % of ATR(D1)

Selection on 2014-2022 only: a system must have >= 75 % winners in BOTH
2014-2019 and 2020-2022 (>= 150 trades each); ranked by the WORSE of its two
results (E in R). The best is shown once on 2023-2026.
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

import pivot_lab as PL  # noqa: E402  (loads .env first)
import strategy_mining as SM  # noqa: E402
import winrate_lab as W1  # noqa: E402
from research_signals import SIGNALS_FILE  # noqa: E402
from src.instruments import get_instrument, parse_symbols  # noqa: E402

HOURS = 120
ENTRIES = (("MARKET", 0.0), ("LIMIT 0.25", 0.25), ("LIMIT 0.5", 0.5))
FIXED = [(tp, sl, tm) for tp in (0.25, 0.4, 0.5, 0.75) for sl in (1.0, 1.5, 2.0, 3.0) for tm in (72, 120)]
CONNORS = [("SMA5", sl, 120) for sl in (1.0, 1.5, 2.0, 3.0)]
EXITS = FIXED + CONNORS
PERIODS = {"A": (date(2014, 1, 1), date(2019, 12, 31)), "B": (date(2020, 1, 1), date(2022, 12, 31)),
           "TEST": (date(2023, 1, 1), date(2026, 9, 30))}
TARGET = 0.75


def pair_entries(symbol: str, fund_rows: dict) -> list[dict]:
    data = PL.load(symbol)
    p = {k: np.array(v, dtype=float) for k, v in data["path"].items()}
    days = data["days"]
    o, h, l, c = (np.array([d[k] for d in days]) for k in ("o", "h", "l", "c"))
    close_t = np.array([d["close_t"] for d in days])
    dates = [d["date"] for d in days]
    pip = get_instrument(symbol).pip
    atr = SM.wilder(SM.true_range(h, l, c), 14)
    sma5 = SM.sma(c, 5)
    ts = p["ts"]
    j0 = np.searchsorted(ts, close_t)
    I = W1.indicators(o, h, l, c, atr)
    fund = W1.fundamental_agree(symbol, dates, fund_rows)
    slip, mark = W1.SLIPPAGE_PIPS * pip, W1.MARKUP_PIPS * pip
    out = []

    for entry_name, k in ENTRIES:
        for side, sign in (("BUY", 1), ("SELL", -1)):
            rows = []
            for i in range(250, len(days) - 6):
                a, j = atr[i], j0[i]
                if np.isnan(a) or j + HOURS + 24 >= len(ts) or ts[j] - close_t[i] > 4 * 86400:
                    continue
                if ts[min(j + HOURS + 23, len(ts) - 1)] - ts[j] > 10 * 86400:
                    continue
                mid = c[i]
                if k == 0:
                    fill, entry = j, (p["ao"][j] + slip if sign > 0 else p["bo"][j] - slip)
                else:
                    level = mid - sign * k * a
                    fill = None
                    for q in range(j, j + 24):
                        if (sign > 0 and p["al"][q] <= level) or (sign < 0 and p["bh"][q] >= level):
                            fill, entry = q, level
                            break
                    if fill is None:
                        continue
                J = np.arange(fill, fill + HOURS)
                if sign > 0:
                    fav, adv, cl = p["bh"][J] - entry, entry - p["bl"][J], p["bc"][J] - entry
                else:
                    fav, adv, cl = entry - p["al"][J], p["ah"][J] - entry, entry - p["ac"][J]
                if k:
                    fav = fav.copy()
                    fav[0] = 0.0                                   # fill hour: favourable part not counted
                # Connors exit: first daily close (i+1 .. i+5) beyond SMA5, at that hour's close
                conn = None
                for dd in range(1, 6):
                    if i + dd >= len(days):
                        break
                    beyond = c[i + dd] > sma5[i + dd] if sign > 0 else c[i + dd] < sma5[i + dd]
                    if beyond or dd == 5:
                        hour = int(np.searchsorted(ts, close_t[i + dd])) - 1 - fill
                        if 0 <= hour < HOURS:
                            conn = (hour, cl[hour] / a)
                        break
                rows.append({"i": i, "fav": np.maximum.accumulate(fav) / a, "adv": np.maximum.accumulate(adv) / a,
                             "close": cl / a, "cost": (slip + mark) / a, "conn": conn})
            out.append({"symbol": symbol, "entry": entry_name, "sign": sign, "rows": rows, "dates": dates, "I": I,
                        "fund": fund, "atr": atr, "pip": pip})
    return out


def outcomes(rows: list[dict]) -> np.ndarray:
    fav = np.array([r["fav"] for r in rows], dtype=np.float32)
    adv = np.array([r["adv"] for r in rows], dtype=np.float32)
    close = np.array([r["close"] for r in rows], dtype=np.float32)
    cost = np.array([r["cost"] for r in rows], dtype=np.float32)
    out = np.empty((len(rows), len(EXITS)), dtype=np.float32)
    for e, (tp, sl, tm) in enumerate(EXITS):
        t_sl = (adv < sl).sum(axis=1)
        if tp == "SMA5":
            hour = np.array([r["conn"][0] if r["conn"] else tm - 1 for r in rows])
            res = np.array([r["conn"][1] if r["conn"] else close[k, tm - 1] for k, r in enumerate(rows)]) - cost
            out[:, e] = np.where(t_sl <= hour, -sl - cost, res)
            continue
        t_tp = (fav < tp).sum(axis=1)
        res = close[:, tm - 1] - cost
        res = np.where((t_tp < tm) & (t_tp < t_sl), tp - cost, res)
        res = np.where((t_sl < tm) & (t_sl <= t_tp), -sl - cost, res)
        out[:, e] = res
    return out


def signal_defs():
    d = {}
    for n in (5, 9, 14):
        for x in (5, 10):
            d[f"%R{n}<{x}"] = (lambda I, n=n, x=x: I[f"wr{n}"] < x, lambda I, n=n, x=x: I[f"wr{n}"] > 100 - x)
    for n, x in ((2, 5), (2, 10), (3, 10), (3, 15)):
        d[f"RSI{n}<{x}"] = (lambda I, n=n, x=x: I[f"rsi{n}"] < x, lambda I, n=n, x=x: I[f"rsi{n}"] > 100 - x)
    d["%R9<10 + IBS<0.3"] = (lambda I: (I["wr9"] < 10) & (I["ibs"] < 0.3), lambda I: (I["wr9"] > 90) & (I["ibs"] > 0.7))
    d["RSI2<10 + IBS<0.3"] = (lambda I: (I["rsi2"] < 10) & (I["ibs"] < 0.3), lambda I: (I["rsi2"] > 90) & (I["ibs"] > 0.7))
    d["IBS<0.15"] = (lambda I: I["ibs"] < 0.15, lambda I: I["ibs"] > 0.85)
    return d


TRENDS = ("sma200", "sma100", None)
VOLS = ("gt30", None)
COSTS = (None, 0.03)


def main() -> int:
    started = time.monotonic()
    fund_rows = {(r["symbol"], r["day"]): r for r in pickle.loads(SIGNALS_FILE.read_bytes())}
    defs = signal_defs()
    meta = [(e, s, t, v, cst) for e, _ in ENTRIES for s in defs for t in TRENDS for v in VOLS for cst in COSTS]
    O, D, P, M = [], [], [], []
    for symbol in parse_symbols(None):
        t0 = time.monotonic()
        for block in pair_entries(symbol, fund_rows):
            rows = block["rows"]
            if not rows:
                continue
            O.append(outcomes(rows))
            idx = np.array([r["i"] for r in rows])
            D.extend(block["dates"][i] for i in idx)
            P.extend([symbol] * len(rows))
            I = {k: v[idx] for k, v in block["I"].items()}
            cost = np.array([r["cost"] for r in rows])
            mask = np.zeros((len(meta), len(rows)), dtype=bool)
            for m, (en, s, t, v, cst) in enumerate(meta):
                if en != block["entry"]:
                    continue
                with np.errstate(invalid="ignore"):
                    cond = np.nan_to_num(defs[s][0 if block["sign"] > 0 else 1](I)).astype(bool)
                    if t:
                        cond &= I[t] == block["sign"]
                    if v == "gt30":
                        cond &= I["atr_pct"] > 0.3
                    if cst:
                        cond &= cost <= cst
                mask[m] = cond
            M.append(mask)
        print(f"{symbol}: {time.monotonic() - t0:.0f} s", flush=True)
    B = {"O": np.vstack(O), "dates": np.array(D), "pairs": np.array(P), "M": np.hstack(M), "meta": meta}
    W1.EXITS[:] = EXITS                         # stats() of round 1 reads the exit list for the R units
    st = {k: W1.stats(B, span) for k, span in PERIODS.items()}
    a, b, te = st["A"], st["B"], st["TEST"]
    ok = (a["n"] >= 150) & (b["n"] >= 150) & (a["win"] >= TARGET) & (b["win"] >= TARGET)
    worst = np.where(ok, np.minimum(a["er"], b["er"]), -np.inf)
    order = np.argsort(-worst, axis=None)[:15]
    f = SM._f

    def name(m, e):
        en, s, t, v, cst = meta[m]
        tp, sl, tm = EXITS[e]
        ex = f"vystup pri zaveru za SMA5, SL {sl} ATR" if tp == "SMA5" else f"TP {tp} ATR, SL {sl} ATR"
        return (f"{en} / {s} / {('trend ' + t.upper()) if t else 'bez trendu'} / {'vol>30%' if v else 'vol libovolna'}"
                f"{' / naklady<=3% ATR' if cst else ''} | {ex}, max {tm // 24} d")

    out = ["# Uspesnost >= 75 % - kolo 2 (vyssi vysledek)", "",
           f"_{len(meta) * len(EXITS)} systemu; vyber jen na 2014-2022 (oba useky >= 75 % a >= 150 obchodu), poradi podle "
           f"horsiho z obou vysledku; 2023-2026 ukazano jen jednou._", "",
           f"Systemu s >= 75 % v obou usecich 2014-2019 i 2020-2022: **{int(ok.sum())}**, z toho kladnych v obou: "
           f"**{int((ok & (a['er'] > 0) & (b['er'] > 0)).sum())}**.", "",
           "| system | 2014-19 uspesnost / E[R] / n | 2020-22 | **2023-26 (test)** |", "|---|---|---|---|"]
    for flat in order:
        m, e = np.unravel_index(flat, worst.shape)
        if not np.isfinite(worst[m, e]):
            break
        cells = [f"{f(st[p]['win'][m, e], '.1%')} / {f(st[p]['er'][m, e], '+.3f')} / {int(st[p]['n'][m, e])}"
                 for p in ("A", "B", "TEST")]
        out.append(f"| {name(m, e)} | " + " | ".join(cells) + " |")
    # criterion closer to the goal: the highest WORSE win rate of 2014-19 / 2020-22 among systems
    # in profit in both (ties: the better worse result)
    robust = np.where(ok & (a["er"] > 0) & (b["er"] > 0), np.minimum(a["win"], b["win"]) + 1e-3 * worst, -np.inf)
    order2 = np.argsort(-robust, axis=None)[:10]
    out += ["", "## Vyber podle cile: nejvyssi horsi uspesnost (2014-19 / 2020-22), v zisku v obou", "",
            "| system | 2014-19 | 2020-22 | **2023-26 (test)** | 2014-26 celkem: n / uspesnost / E[R] / t |",
            "|---|---|---|---|---|"]
    for flat in order2:
        mm, ee = np.unravel_index(flat, robust.shape)
        if not np.isfinite(robust[mm, ee]):
            break
        idx_all = W1.trades_of(B, mm, ee, (date(2014, 1, 1), date(2026, 9, 30)))
        v = B["O"][idx_all, ee] / EXITS[ee][1]
        cells = [f"{f(st[p]['win'][mm, ee], '.1%')} / {f(st[p]['er'][mm, ee], '+.3f')} / {int(st[p]['n'][mm, ee])}"
                 for p in ("A", "B", "TEST")]
        out.append(f"| {name(mm, ee)} | " + " | ".join(cells) +
                   f" | {len(v)} / {(v > 0).mean():.1%} / {v.mean():+.3f} / {W1.clustered_t(B, idx_all, ee):+.1f} |")
    m, e = np.unravel_index(order2[0], robust.shape)
    out += ["", f"**Finalni system kola 2 (podle cile):** {name(m, e)}", "", "| rok | obchodu | uspesnost | E [R] |", "|---|---|---|---|"]
    sl = EXITS[e][1]
    for year in range(2014, 2027):
        idx = W1.trades_of(B, m, e, (date(year, 1, 1), date(year, 12, 31)))
        if len(idx):
            v = B["O"][idx, e]
            out.append(f"| {year} | {len(v)} | {(v > 0).mean():.1%} | {(v / sl).mean():+.3f} |")
    idx = W1.trades_of(B, m, e, PERIODS["TEST"])
    # systems with >= 75 % AND a profit in every period (uses 2023-26 too: only the forward test confirms)
    every = ok & (te["n"] >= 100) & (te["win"] >= TARGET) & (a["er"] > 0) & (b["er"] > 0) & (te["er"] > 0)
    out += ["", "## Systemy s >= 75 % a ziskem ve VSECH trech obdobich (pouziva i 2023-26 - potvrdi jen dopredny test)",
            "", f"Pocet: **{int(every.sum())}** z {every.size}.", "",
            "| system | 2014-26: obchodu / uspesnost / E[R] / t | nejhorsi propad [R] | obchodu za rok |", "|---|---|---|---|"]
    ranked = []
    for mm, ee in np.argwhere(every):
        idx_all = W1.trades_of(B, mm, ee, (date(2014, 1, 1), date(2026, 9, 30)))
        v = B["O"][idx_all, ee] / EXITS[ee][1]
        order_t = np.argsort(B["dates"][idx_all], kind="stable")
        eq = np.cumsum(v[order_t])
        dd = float((eq - np.maximum.accumulate(eq)).min())
        ranked.append((v.mean(), mm, ee, len(v), (v > 0).mean(), W1.clustered_t(B, idx_all, ee), dd))
    for mean, mm, ee, n, win, t, dd in sorted(ranked, reverse=True)[:10]:
        out.append(f"| {name(mm, ee)} | {n} / {win:.1%} / {mean:+.3f} / {t:+.1f} | {dd:+.1f} | {n / 12.75:.0f} |")
    if ranked:
        best = sorted(ranked, reverse=True)[0]
        (PROJECT_ROOT / "data" / "research" / "winrate_deploy.pkl").write_bytes(pickle.dumps(
            {"meta": meta[best[1]], "exit": EXITS[best[2]], "name": name(best[1], best[2])}))
    out += ["", f"t testu (tydenni shluky): {W1.clustered_t(B, idx, e):+.1f}; _vypocet {time.monotonic() - started:.0f} s_"]
    (PROJECT_ROOT / "docs" / "USPESNOST75_K2.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    (PROJECT_ROOT / "data" / "research" / "winrate_final2.pkl").write_bytes(pickle.dumps(
        {"meta": meta[m], "exit": EXITS[e], "name": name(m, e)}))
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
