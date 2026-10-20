"""Profit-per-trade search, round 2: >= 10 % of the margin per trade at 1:30
on a 25-pair universe (FXCM hourly BID/ASK 2012-2026, one source).

    python scripts/profit_lab2.py build    # outcomes of every entry x exit (~10 min) -> data/research/profit2/
    python scripts/profit_lab2.py report   # selection 2012-2022, test 2023-2026 -> docs/ZISK10_K2.md

Differences to profit_lab.py (round 1, 12 pairs, daily bars):
- 25 crosses of the 8 major currencies, 2012-2026 from FXCM only (scripts/fxcm_universe.py);
  since R-010 the build also covers the 16 HistData pairs (fxcm_universe.universe_all(); the
  report docs/ZISK10_K2.md was made on the 25 FXCM pairs);
- the trade path is resolved on hourly bars (TP and SL in the same hour = SL);
- exits in ATR multiples and in fixed % of the price (0.333 % = 10 % of the margin);
- carry = OECD 3-month interbank rate difference known two months back
  (monthly, the same series for 2012-2026; FRED IR3TIB01*), financing at the
  rate difference -/+ 1 % p.a. per calendar day held;
- costs = typical retail spread + 0.4 pip slippage (FXCM's own spreads are
  2-4x lower; ours are the conservative ones).

Selection on A = 2012-2018 and B = 2019-2022 (both must pass), the test
period 2023-2026 is shown once. Units: % of the margin = 30 x net % move.
"""

import pickle
import sys
import time
from datetime import date, timezone
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import fxcm_universe as U  # noqa: E402
import strategy_mining as SM  # noqa: E402
from src.core import market as core  # noqa: E402
# Since R-048 (architektura-v2, phase 1) the live core does not import this lab: prices, costs, rates, signals and
# the daily indicators live in src/core (market.py, rates.py, ta.py). This lab takes them from there.
from src.core.market import (ESMA_MAJORS, FIN_MARKUP, HOLD_BARS, LEVERAGE, MIN_HOURS, MIN_TP_PCT, PERIODS,  # noqa: E402,F401
                             SLIPPAGE_PIPS, SPREAD_PIPS, indicators, leverage, series, signal_defs)
from src.core.market import (EXTEND_IDS, EXTENDED, LONG_IDS, RATE_IDS, curve_mom, monthly_long_rates,  # noqa: E402,F401
                             monthly_rates, rate_at)
from src.instruments import get_instrument  # noqa: E402

UTC = timezone.utc


def __getattr__(name):                      # PEP 562: the lab scripts read profit_lab2.OUT; the one source is core.OUT
    if name == "OUT":
        return core.OUT
    raise AttributeError(name)


MAX_BARS = max(HOLD_BARS.values())
EXITS = ([("ATR", tp, sl, hd) for tp in (0.75, 1.0, 1.5, 2.0, 3.0, 4.0) for sl in (1.0, 1.5, 2.0, 3.0, 4.0)
          for hd in HOLD_BARS]
         + [("PCT", tp, sl, hd) for tp in (1 / 3, 0.5, 0.75, 1.0, 1.5) for sl in (0.5, 0.75, 1.0, 1.5, 2.0)
            for hd in HOLD_BARS])
ENTRIES = (("MARKET", 0.0), ("LIMIT 0.5", 0.5), ("LIMIT 1.0", 1.0))


# ----------------------------------------------------------------------
# signals
# ----------------------------------------------------------------------

TRENDS = (None, "sma50", "sma200", "w_sma40")
FUNDS = (None, "carry", "carry2", "rates_up")
RHYTHM = ("DEN", "TYDEN")


def fund_ok(I: dict, f: str | None, side: int) -> np.ndarray:
    with np.errstate(invalid="ignore"):
        if f is None:
            return np.ones(len(I["carry"]), dtype=bool)
        if f == "carry":
            return np.sign(I["carry"]) == side
        if f == "carry2":
            return side * I["carry"] >= 2.0
        return side * I["rates_mom"] >= 0.25


# ----------------------------------------------------------------------
# build: outcome of every (entry, side) x exit
# ----------------------------------------------------------------------

def meta_list() -> list:
    defs = signal_defs()
    return [(s, t, f, r) for s in defs for t in TRENDS for f in FUNDS for r in RHYTHM
            if not (s.startswith("W ") and r == "DEN")]


def build() -> int:
    started = time.monotonic()
    rates = monthly_rates()
    defs = signal_defs()
    meta = meta_list()
    blocks = {en: {"O": [], "V": [], "M": [], "dates": [], "pairs": [], "sides": []} for en, _ in ENTRIES}
    for symbol in U.universe_all():
        t0 = time.monotonic()
        s = series(symbol)
        I = indicators(s, rates, symbol)
        inst = get_instrument(symbol)
        half = (SPREAD_PIPS[symbol] / 2 + SLIPPAGE_PIPS / 2) * inst.pip
        ts, hh, hl, hc = s["ts"], s["h"], s["l"], s["c"]
        n_days = len(s["days"])
        close_ts = s["close_ts"]
        day_gap = np.concatenate([[0], (np.diff(close_ts) > 5 * 86400).astype(int)])
        gap_cum = np.cumsum(day_gap)
        hour_gap = np.concatenate([[0], (np.diff(ts) > 100 * 3600).astype(int)])
        hour_cum = np.cumsum(hour_gap)
        cand = []
        for i in range(260, n_days - 1):
            if np.isnan(I["atr"][i]) or gap_cum[i] != gap_cum[i - 5]:      # long lookbacks may span a hole
                continue
            start = s["last"][i] + 1
            if start + 120 + MAX_BARS + 1 >= len(ts) or hour_cum[start + 120 + MAX_BARS] != hour_cum[start]:
                continue
            cand.append(i)
        base = np.array(cand)
        start_h = s["last"][base] + 1
        for en, k in ENTRIES:
            for side in (1, -1):
                a_all = I["atr"][base]
                if k == 0:
                    keep = np.ones(len(base), dtype=bool)
                    fill = start_h - 1                                   # the decision close
                    entry = hc[fill] + side * half
                    first_path = start_h
                    adv0 = np.zeros(len(base))
                else:
                    level = s["dc"][base] - side * k * a_all
                    window = np.where(I["week_end"][base], 120, 24)
                    fill = np.full(len(base), -1)
                    for q in range(119, -1, -1):                         # earliest hour wins
                        j = start_h + q
                        hit = ((hl[j] - half <= level) if side > 0 else (hh[j] + half >= level)) & (q < window)
                        fill = np.where(hit, j, fill)
                    keep = fill >= 0
                    fill, level = fill[keep], level[keep]
                    entry = level
                    first_path = fill + 1
                    adv0 = (entry - (hl[fill] - half)) if side > 0 else ((hh[fill] + half) - entry)
                idx = base[keep]
                a_i = I["atr"][idx]
                span = first_path[:, None] + np.arange(MAX_BARS)[None, :]
                if side > 0:
                    fav = hh[span] - half - entry[:, None]
                    adv = entry[:, None] - (hl[span] - half)
                    close = hc[span] - half - entry[:, None]
                else:
                    fav = entry[:, None] - (hl[span] + half)
                    adv = (hh[span] + half) - entry[:, None]
                    close = entry[:, None] - (hc[span] + half)
                adv = np.maximum(adv, adv0[:, None])
                fav_c = np.maximum.accumulate(fav, axis=1).astype(np.float32)
                adv_c = np.maximum.accumulate(adv, axis=1).astype(np.float32)
                held = (ts[span] + 3600 - ts[fill][:, None]) / 86400
                fin = (side * I["carry_fin"][idx] - FIN_MARKUP)[:, None] / 100 / 365 * held * entry[:, None]
                res = np.empty((len(idx), len(EXITS)), dtype=np.float32)
                val = np.empty((len(idx), len(EXITS)), dtype=bool)
                rows = np.arange(len(idx))
                for e, (kind, tp, sl, hd) in enumerate(EXITS):
                    L = HOLD_BARS[hd]
                    if kind == "ATR":
                        TP, SL = tp * a_i, sl * a_i
                    else:
                        TP, SL = tp / 100 * entry, sl / 100 * entry
                    val[:, e] = TP / entry * 100 >= MIN_TP_PCT - 1e-9
                    t_tp = (fav_c[:, :L] < TP[:, None]).sum(axis=1)
                    t_sl = (adv_c[:, :L] < SL[:, None]).sum(axis=1)
                    sl_hit = (t_sl < L) & (t_sl <= t_tp)
                    tp_hit = (t_tp < L) & ~sl_hit
                    pnl = close[:, L - 1] + fin[:, L - 1]
                    pnl = np.where(tp_hit, TP + fin[rows, np.minimum(t_tp, L - 1)], pnl)
                    pnl = np.where(sl_hit, -SL + fin[rows, np.minimum(t_sl, L - 1)], pnl)
                    res[:, e] = pnl / entry * 100 * LEVERAGE
                Ii = {kk: vv[idx] for kk, vv in I.items()}
                mask = np.zeros((len(meta), len(idx)), dtype=bool)
                with np.errstate(invalid="ignore"):
                    trend_ok = {t: (np.ones(len(idx), dtype=bool) if t is None else Ii[t] == side) for t in TRENDS}
                    f_ok = {f: fund_ok(Ii, f, side) for f in FUNDS}
                    sig = {name: np.nan_to_num(fn[0 if side > 0 else 1](Ii)).astype(bool) for name, fn in defs.items()}
                for m, (sname, t, f, r) in enumerate(meta):
                    cond = sig[sname] & trend_ok[t] & f_ok[f]
                    if r == "TYDEN" or sname.startswith("W "):
                        cond = cond & Ii["week_end"]
                    mask[m] = cond
                b = blocks[en]
                b["O"].append(res)
                b["V"].append(val)
                b["M"].append(mask)
                b["dates"].extend(s["days"][i] for i in idx)
                b["pairs"].extend([symbol] * len(idx))
                b["sides"].extend([side] * len(idx))
        print(f"{symbol}: {len(base)} dni, {time.monotonic() - t0:.0f} s", flush=True)
    core.OUT.mkdir(parents=True, exist_ok=True)
    for en, _ in ENTRIES:
        b = blocks[en]
        np.savez(core.OUT / f"block_{en.replace(' ', '_')}.npz", O=np.vstack(b["O"]), V=np.vstack(b["V"]),
                 M=np.hstack(b["M"]), dates=np.array([d.toordinal() for d in b["dates"]]), pairs=np.array(b["pairs"]),
                 sides=np.array(b["sides"]))
    (core.OUT / "meta.pkl").write_bytes(pickle.dumps({"meta": meta, "exits": EXITS, "entries": ENTRIES}))
    print(f"build {time.monotonic() - started:.0f} s")
    return 0


# ----------------------------------------------------------------------
# report
# ----------------------------------------------------------------------

def load_block(en: str) -> dict:
    z = np.load(core.OUT / f"block_{en.replace(' ', '_')}.npz")
    return {k: z[k] for k in z.files}


def stats(B: dict, period: tuple, cols=None) -> dict:
    a, b = period[0].toordinal(), period[1].toordinal()
    sel = ((B["dates"] >= a) & (B["dates"] <= b)).astype(np.float32)
    V = B["V"] if cols is None else B["V"][:, cols]
    Oo = B["O"] if cols is None else B["O"][:, cols]
    Vf = V.astype(np.float32) * sel[:, None]
    O = np.where(V, Oo, 0).astype(np.float32) * sel[:, None]
    Wn = ((Oo > 0) & V).astype(np.float32) * sel[:, None]
    O2 = O * O
    shape = (B["M"].shape[0], V.shape[1])
    n, w, s, s2 = (np.zeros(shape) for _ in range(4))
    for k in range(0, shape[0], 64):
        Mf = B["M"][k:k + 64].astype(np.float32)
        n[k:k + 64], w[k:k + 64], s[k:k + 64], s2[k:k + 64] = Mf @ Vf, Mf @ Wn, Mf @ O, Mf @ O2
    with np.errstate(all="ignore"):
        e = s / n
        sd = np.sqrt(np.maximum(s2 / n - e * e, 0))
        return {"n": n, "win": w / n, "e": e, "t": e / (sd / np.sqrt(n))}


def describe(meta, m: int, ex: int, en: str) -> str:
    sname, t, f, r = meta[m]
    kind, tp, sl, hd = EXITS[ex]
    tr = {None: "bez trendu", "sma50": "SMA50", "sma200": "SMA200", "w_sma40": "tydenni SMA40"}[t]
    fu = {None: "", "carry": " / carry souhlasi", "carry2": " / carry >= 2 %", "rates_up": " / sazby se rozchazeji"}[f]
    rh = "konec tydne" if (r == "TYDEN" or sname.startswith("W ")) else "denne"
    if kind == "ATR":
        ex_s = f"TP {tp:g} ATR, SL {sl:g} ATR"
    else:
        ex_s = f"TP {tp * LEVERAGE:.0f} %, SL {sl * LEVERAGE:.0f} % marze"
    return f"{en} / {sname} / {tr}{fu} / {rh} | {ex_s}, max {hd} d"


def report() -> int:
    started = time.monotonic()
    info = pickle.loads((core.OUT / "meta.pkl").read_bytes())
    meta = info["meta"]
    rows_all = []
    summary = []
    for en, _ in ENTRIES:
        B = load_block(en)
        st = {p: stats(B, span) for p, span in PERIODS.items()}
        a, b, te = st["A"], st["B"], st["TEST"]
        enough = (a["n"] >= 35) & (b["n"] >= 20)
        worst_e, worst_w = np.minimum(a["e"], b["e"]), np.minimum(a["win"], b["win"])
        for label, mask, key in (
                ("A", enough & (worst_w >= 0.75) & (worst_e >= 10), worst_e),
                ("B", enough & (worst_e >= 10), worst_w),
                ("C", enough & (worst_w >= 0.75) & (worst_e > 0), worst_e),
                ("ALL", enough, worst_e)):
            ms, xs = np.nonzero(mask)
            for m, x in zip(ms, xs):
                rows_all.append((label, en, int(m), int(x), float(key[m, x]),
                                 *(float(st[p][k][m, x]) for p in ("A", "B", "TEST") for k in ("n", "win", "e", "t"))))
            if label == "ALL":
                summary.append((en, int(mask.sum()), float(np.nanmean(np.where(mask, te["e"], np.nan))),
                                float(np.nanmean(np.where(mask & (te["n"] > 0), te["e"] > 0, np.nan)))))
        print(f"{en}: {time.monotonic() - started:.0f} s", flush=True)
    pickle.dump(rows_all, open(core.OUT / "report_rows.pkl", "wb"))
    f = SM._f

    def table(label: str, title: str, k: int = 20) -> list[str]:
        rows = sorted((r for r in rows_all if r[0] == label), key=lambda r: -r[4])
        lines = [f"## {title}", "", f"Splnuje: **{len(rows)}** systemu.", ""]
        if rows:
            test_ok = [r for r in rows if r[13] > 0]
            hits = sum(1 for r in test_ok if r[15] >= 10)
            lines += [f"V testu 2023-26: zisk > 0 u {sum(1 for r in test_ok if r[15] > 0)} z {len(test_ok)} "
                      f"(s obchody), >= 10 % marze u {hits}, a k tomu uspesnost >= 75 % u "
                      f"{sum(1 for r in test_ok if r[15] >= 10 and r[14] >= 0.75)}.", ""]
        lines += ["| system | 2012-18 n / usp. / zisk | 2019-22 | **2023-26 (test)** |", "|---|---|---|---|"]
        for r in rows[:k]:
            cells = [f"{int(r[5 + 4 * j])} / {f(r[6 + 4 * j], '.0%')} / {f(r[7 + 4 * j], '+.1f')} %" for j in range(3)]
            lines.append(f"| {describe(meta, r[2], r[3], r[1])} | " + " | ".join(cells) + " |")
        return lines + [""]

    out = ["# Zisk na obchod >= 10 % marze - kolo 2 (25 paru, 2012-2026, hodinova cesta)", "",
           f"_{len(meta) * len(EXITS) * len(ENTRIES)} systemu; cil kazdeho obchodu >= {MIN_TP_PCT:.3f} % ceny; "
           f"vysledky v % marze (paka 1:30) po spreadu, skluzu a swapu; vyber 2012-2022, test 2023-2026._", ""]
    out += ["| vstup | systemu s dost obchody | prumer v testu | podil kladnych v testu |", "|---|---|---|---|"]
    out += [f"| {en} | {n} | {e:+.1f} % | {p:.0%} |" for en, n, e, p in summary] + [""]
    out += table("A", "A) Uspesnost >= 75 % a prumer >= 10 % marze v obou vyberovych obdobich")
    out += table("B", "B) Prumer >= 10 % marze v obou obdobich - serazeno podle horsi uspesnosti")
    out += table("C", "C) Uspesnost >= 75 % a zisk v obou obdobich - serazeno podle horsiho prumeru")
    out += [f"_vypocet {time.monotonic() - started:.0f} s_"]
    (PROJECT_ROOT / "docs" / "ZISK10_K2.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "build"
    raise SystemExit({"build": build, "report": report}[command]())
