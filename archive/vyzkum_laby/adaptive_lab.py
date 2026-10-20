"""Adaptive rule selection: the model re-learns which rules work, every
month / quarter / half-year / year, and drops the ones that stopped working.

    python scripts/adaptive_lab.py        # -> docs/ADAPTIVNI.md (~2 min, needs numpy)

Rules = 230 indicator settings x 6 fundamental filters x 2 signs x holding
1 / 3 / 5 days (scripts/strategy_mining.py) = 8 280 rules. For every rule the
daily result (mean over the pairs that trade that day, after costs and
financing, ATR(D1) units) is known when its trades are closed.

Meta-model: at the first trading day of each period (every P months) rank
all rules by the t-value of their results in the trailing W months (only
trades already closed at that moment), keep the best K with a positive
mean, trade exactly those until the next re-selection. Grid: P in 1/3/6/12,
W in 6/12/24/36, K in 1/5/20/50 = 64 meta-models, all evaluated on
2017-01 .. 2026-09, where every decision used only the past.

Persistence test (does a rule that worked recently keep working?): every
month, rules are put in 10 groups by their trailing-12-month t-value; the
report shows the next month's result of each group.
"""

import math
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import strategy_mining as SM  # noqa: E402

EVAL = (date(2017, 1, 1), date(2026, 9, 30))
SPLIT = date(2022, 1, 1)                    # meta-model chosen on 2017-2021, shown on 2022-2026
PERIODS_M = (1, 3, 6, 12)
WINDOWS_M = (6, 12, 24, 36)
KS = (1, 5, 20, 50)
MIN_DAYS = 20


def rule_matrix(panel: dict) -> tuple[np.ndarray, list, np.ndarray]:
    """(rules x days daily results, rule descriptions, horizon per rule)."""
    filters = SM.fundamental_filters(panel)
    rows, names, hz_of = [], [], []

    for name, raw in panel["S"].items():
        base = np.nan_to_num(raw)
        for fname, filt in filters.items():
            for sign in (1.0, -1.0):
                sig = base * sign
                if filt is not None:
                    if filt.ndim == 3:
                        agree, against = (filt == sig[None]).sum(axis=0), (filt == -sig[None]).sum(axis=0)
                        sig = np.where((agree >= 1) & (against == 0), sig, 0)
                    else:
                        sig = np.where(filt == 0, sig, np.where(filt == sig, sig, 0))
                for hz in SM.HORIZONS:
                    long_, short, _ = panel["T"][hz]
                    net = np.where(sig > 0, long_, np.where(sig < 0, short, np.nan))
                    with np.errstate(all="ignore"):
                        rows.append(np.nanmean(net, axis=0).astype(np.float32))
                    names.append((name, fname, "podle" if sign > 0 else "proti", hz))
                    hz_of.append(hz)

    return np.vstack(rows), names, np.array(hz_of)


def month_starts(dates: list) -> list[int]:
    out, seen = [], set()
    for i, d in enumerate(dates):
        if (d.year, d.month) not in seen:
            seen.add((d.year, d.month))
            out.append(i)
    return out


class Rolling:
    """Trailing statistics of every rule from prefix sums (NaN = no trade)."""

    def __init__(self, X: np.ndarray):
        valid = ~np.isnan(X)
        v = np.where(valid, X, 0.0).astype(np.float64)
        z = np.zeros((X.shape[0], 1))
        self.s = np.hstack([z, np.cumsum(v, axis=1)])
        self.q = np.hstack([z, np.cumsum(v * v, axis=1)])
        self.n = np.hstack([z, np.cumsum(valid, axis=1)])

    def stats(self, start: np.ndarray | int, end: np.ndarray):
        """mean, sd, count over days [start, end) per rule (end may differ per rule)."""
        idx = np.arange(self.s.shape[0])
        start = np.broadcast_to(np.maximum(start, 0), end.shape)
        end = np.maximum(end, start)
        n = self.n[idx, end] - self.n[idx, start]
        s = self.s[idx, end] - self.s[idx, start]
        q = self.q[idx, end] - self.q[idx, start]
        with np.errstate(all="ignore"):
            mean = s / n
            var = np.maximum(q / n - mean ** 2, 0) * n / np.maximum(n - 1, 1)
        return mean, np.sqrt(var), n


def scores(roll: Rolling, hz: np.ndarray, T: int, window_days: int):
    end = T - hz                                  # trades entered before T - h are closed at T
    mean, sd, n = roll.stats(T - window_days, end)
    with np.errstate(all="ignore"):
        t = mean / (sd / np.sqrt(np.maximum(n / hz, 1)))
    t[(n < MIN_DAYS) | ~np.isfinite(t)] = -np.inf
    return t, mean


def meta(X, roll, hz, dates, starts, P, W, K):
    """Daily results of the meta-model and the number of rules traded per period."""
    out = np.full(len(dates), np.nan)
    first = next(i for i, d in enumerate(dates) if d >= EVAL[0])
    rebal = [s for s in starts if s >= first][::P]
    picked = []

    for j, T in enumerate(rebal):
        t, mean = scores(roll, hz, T, int(W * 21))
        order = np.argsort(-t)[:K]
        sel = order[(t[order] > -np.inf) & (mean[order] > 0)]
        picked.append(sel)
        end = rebal[j + 1] if j + 1 < len(rebal) else len(dates)
        if len(sel):
            with np.errstate(all="ignore"):
                out[T:end] = np.nanmean(X[sel, T:end], axis=0)
    return out, picked


def summarize(daily: np.ndarray, dates: list, span) -> dict:
    mask = np.array([span[0] <= d <= span[1] for d in dates]) & ~np.isnan(daily)
    vals = daily[mask]
    if len(vals) < 50:
        return {"days": len(vals)}
    weeks: dict = {}
    for d, v in zip(np.array(dates)[mask], vals):
        k = tuple(d.isocalendar()[:2])
        weeks[k] = weeks.get(k, 0.0) + v
    w = np.array(list(weeks.values()))
    t = w.mean() / (w.std(ddof=1) / math.sqrt(len(w))) if w.std() > 0 else 0.0
    return {"days": len(vals), "e": float(vals.mean()), "pos_days": float((vals > 0).mean()), "t": float(t),
            "per_year": float(vals.mean() * 252)}


def persistence(X, roll, hz, dates, starts) -> list:
    """Next-month result by decile of the trailing-12-month t-value."""
    first = next(i for i, d in enumerate(dates) if d >= EVAL[0])
    rebal = [s for s in starts if s >= first]
    sums = [[] for _ in range(10)]

    for j, T in enumerate(rebal[:-1]):
        t, _ = scores(roll, hz, T, 12 * 21)
        ok = np.isfinite(t)
        idx = np.where(ok)[0]
        if len(idx) < 100:
            continue
        ranks = np.argsort(np.argsort(t[idx]))
        dec = (ranks * 10 // len(idx)).astype(int)
        end = rebal[j + 1]
        with np.errstate(all="ignore"):
            nxt = np.nanmean(X[idx, T:end], axis=1)
        for k in range(10):
            vals = nxt[dec == k]
            vals = vals[~np.isnan(vals)]
            if len(vals):
                sums[k].append(float(vals.mean()))
    return [(k + 1, float(np.mean(v)), float(np.mean(np.array(v) > 0))) for k, v in enumerate(sums) if v]


def main() -> int:
    started = time.monotonic()
    panel = SM.build_panel()
    X, names, hz = rule_matrix(panel)
    dates = panel["dates"]
    roll = Rolling(X)
    starts = month_starts(dates)
    print(f"pravidel {len(names)}, dni {len(dates)} | {time.monotonic() - started:.0f} s", flush=True)

    grid = []
    for P in PERIODS_M:
        for W in WINDOWS_M:
            for K in KS:
                daily, picked = meta(X, roll, hz, dates, starts, P, W, K)
                grid.append({"P": P, "W": W, "K": K, "daily": daily, "picked": picked,
                             "A": summarize(daily, dates, (EVAL[0], date(2021, 12, 31))),
                             "B": summarize(daily, dates, (SPLIT, EVAL[1])),
                             "ALL": summarize(daily, dates, EVAL)})
    pers = persistence(X, roll, hz, dates, starts)
    base_sig = SM.model_signal(panel)
    base = {}
    for h in SM.HORIZONS:
        long_, short, _ = panel["T"][h]
        net = np.where(base_sig > 0, long_, np.where(base_sig < 0, short, np.nan))
        with np.errstate(all="ignore"):
            series = np.nanmean(net, axis=0)
        base[h] = {k: summarize(series, dates, span) for k, span in
                   (("A", (EVAL[0], date(2021, 12, 31))), ("B", (SPLIT, EVAL[1])), ("ALL", EVAL))}

    f = SM._f
    cell = lambda r: f"{_e(r)} | {f(r.get('pos_days'), '.0%')} | {f(r.get('t'), '+.1f')}"
    out = ["# Adaptivni model: pravidla se pravidelne preucuji", "",
           f"_{len(names)} pravidel (230 indikatoru x 6 fundamentalnich filtru x 2 smery x drzeni 1/3/5 dni); "
           f"64 variant uceni; vse 2017-01 .. 2026-09, kazde rozhodnuti jen z minulosti. E = prumerny vysledek "
           f"obchodniho dne v ATR(D1) po nakladech; kladne dny = podil dni v zisku; t > 2 = nepravdepodobne nahoda._", "",
           "## Funguje to, co fungovalo posledni rok, i dalsi mesic?", "",
           "Pravidla rozdelena kazdy mesic do 10 skupin podle vysledku za poslednich 12 mesicu; vysledek v dalsim mesici:", "",
           "| skupina (1 = nejhorsi, 10 = nejlepsi za posledni rok) | prumer dalsi mesic [ATR] | mesicu v plusu |",
           "|---|---|---|"]
    out += [f"| {k} | {m:+.4f} | {p:.0%} |" for k, m, p in pers]
    best_a = max(grid, key=lambda g: g["A"].get("t", -9))
    pos_b = sum(1 for g in grid if (g["B"].get("e") or -1) > 0)
    sig_b = sum(1 for g in grid if (g["B"].get("t") or 0) >= 2)
    out += ["", "## 64 variant uceni (preuceni co P mesicu, okno W mesicu, K nejlepsich pravidel)", "",
            f"Kladnych na 2022-26: **{pos_b} z 64**; s t >= 2: **{sig_b} z 64**.", "",
            "| P | W | K | 2017-21 E | kladne dny | t | 2022-26 E | kladne dny | t | za rok 2017-26 [ATR] |",
            "|---|---|---|---|---|---|---|---|---|---|"]
    for g in sorted(grid, key=lambda g: -(g["ALL"].get("t") or -9)):
        out.append(f"| {g['P']} | {g['W']} | {g['K']} | {cell(g['A'])} | {cell(g['B'])} | "
                   f"{f(g['ALL'].get('per_year'), '+.2f')} |")
    out += ["", f"Varianta vybrana podle 2017-21: P {best_a['P']}, W {best_a['W']}, K {best_a['K']} -> 2022-26: "
            f"{cell(best_a['B'])}.", "",
            "## Pro srovnani: soucasny model V7.8.0 (stejne mereni)", "",
            "| drzeni | 2017-21 E | kladne dny | t | 2022-26 E | kladne dny | t |", "|---|---|---|---|---|---|---|"]
    out += [f"| {h} d | {cell(base[h]['A'])} | {cell(base[h]['B'])} |" for h in SM.HORIZONS]
    last = best_a["picked"][-1] if best_a["picked"] else []
    out += ["", f"## Co by vybrana varianta obchodovala ted (posledni preuceni)", ""]
    out += [f"- {names[i][0]} / {names[i][1]} / {names[i][2]} signalu / {names[i][3]} d" for i in last[:20]] or ["- nic"]
    out += ["", f"_vypocet {time.monotonic() - started:.0f} s_"]
    (PROJECT_ROOT / "docs" / "ADAPTIVNI.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0


def _e(r: dict) -> str:
    return "-" if r.get("e") is None else f"{r['e']:+.4f}"


if __name__ == "__main__":
    raise SystemExit(main())
