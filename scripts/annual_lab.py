"""Annual account return instead of profit per trade: which systems (and
which combinations) make the most per year at a limited drawdown, with at
least 2-3 winning trades a month. Uses the outcomes of profit_lab2 build
(25 pairs, 2012-2026, hourly path, costs, swap; every trade aims >= 10 %
of the margin at 1:30).

    python scripts/annual_lab.py          # -> docs/ROCNI_VYNOS.md

Account model (the same for every system): each trade ties up a fixed share
s of the account as margin, the account result of a trade = s x its result
in % of the margin. s is chosen so that the largest drawdown of the monthly
equity curve in the selection years 2012-2022 equals DD_TARGET, at most
S_MAX (margin of many open trades must fit into the account).
Selection on 2012-2018 and 2019-2022 (both must pass), test 2023-2026.
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

import profit_lab2 as P  # noqa: E402
import strategy_mining as SM  # noqa: E402

FIRST = date(2012, 1, 1)
MONTHS = (2026 - 2012) * 12 + 9                      # 2012-01 .. 2026-09
DD_TARGET = 0.20
S_MAX = 0.10
SEL = (0, (2022 - 2012 + 1) * 12)                    # month index range 2012-01 .. 2022-12
SPANS = {"A": (0, 7 * 12), "B": (7 * 12, 11 * 12), "TEST": (11 * 12, MONTHS)}


def month_index(ordinals: np.ndarray) -> np.ndarray:
    years = np.array([date.fromordinal(int(o)).year for o in ordinals])
    months = np.array([date.fromordinal(int(o)).month for o in ordinals])
    return (years - 2012) * 12 + months - 1


def monthly(B: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per system (meta x exit) and month: sum of results, trades, winners."""
    mi = month_index(B["dates"])
    V = B["V"]
    O = np.where(V, B["O"], 0).astype(np.float32)
    Vf = V.astype(np.float32)
    Wf = ((B["O"] > 0) & V).astype(np.float32)
    Mf = B["M"].astype(np.float32)
    shape = (Mf.shape[0], MONTHS, V.shape[1])
    S, N, W = (np.zeros(shape, dtype=np.float32) for _ in range(3))
    for k in range(MONTHS):
        rows = np.nonzero(mi == k)[0]
        if not len(rows):
            continue
        Mk = Mf[:, rows]
        S[:, k], N[:, k], W[:, k] = Mk @ O[rows], Mk @ Vf[rows], Mk @ Wf[rows]
    return S, N, W


def drawdown(curve_monthly: np.ndarray, axis: int = 1) -> np.ndarray:
    """Largest fall of the cumulative sum (same units as the input)."""
    cum = np.cumsum(curve_monthly, axis=axis)
    zero = np.zeros_like(np.take(cum, [0], axis=axis))
    cum = np.concatenate([zero, cum], axis=axis)
    peak = np.maximum.accumulate(cum, axis=axis)
    return (peak - cum).max(axis=axis)


def evaluate(S, N, W) -> dict:
    """Metrics with the account share chosen on the selection years."""
    a, b = SEL
    dd_sel = drawdown(S[:, a:b], axis=1) / 100                    # in units of 'margin share'
    share = np.minimum(S_MAX, DD_TARGET / np.maximum(dd_sel, 1e-9))
    out = {"share": share}
    for p, (x, y) in SPANS.items():
        years = (y - x) / 12
        s, n, w = S[:, x:y], N[:, x:y], W[:, x:y]
        tot_n = n.sum(axis=1)
        out[p] = {
            "n_year": tot_n / years,
            "e": np.where(tot_n > 0, s.sum(axis=1) / np.maximum(tot_n, 1), np.nan),
            "win": np.where(tot_n > 0, w.sum(axis=1) / np.maximum(tot_n, 1), np.nan),
            "annual": share * s.sum(axis=1) / 100 / years,                 # simple, not compounded
            "dd": share * drawdown(s, axis=1) / 100,
            "wins_month": w.sum(axis=1) / (y - x),
            "months_2wins": (w >= 2).mean(axis=1),
        }
    return out


def main() -> int:
    started = time.monotonic()
    info = pickle.loads((P.OUT / "meta.pkl").read_bytes())
    meta, exits = info["meta"], info["exits"]
    rows, cache = [], {}
    for en, _ in P.ENTRIES:
        B = P.load_block(en)
        S, N, W = monthly(B)
        ev = evaluate(S, N, W)
        a, b, te = ev["A"], ev["B"], ev["TEST"]
        ok = ((a["wins_month"] >= 2) & (b["wins_month"] >= 2) & (a["annual"] > 0) & (b["annual"] > 0)
              & (a["months_2wins"] >= 0.5) & (b["months_2wins"] >= 0.5))
        score = np.where(ok, np.minimum(a["annual"], b["annual"]), -np.inf)
        for flat in np.argsort(-score, axis=None)[:400]:
            m, x = np.unravel_index(flat, score.shape)
            if not np.isfinite(score[m, x]):
                break
            rows.append({"entry": en, "m": int(m), "x": int(x), "score": float(score[m, x]),
                         "share": float(ev["share"][m, x]),
                         **{f"{p}_{k}": float(ev[p][k][m, x]) for p in SPANS for k in ev[p]}})
            cache[(en, int(m), int(x))] = (S[m, :, x].copy(), N[m, :, x].copy(), W[m, :, x].copy())
        n_ok = int(ok.sum())
        print(f"{en}: {n_ok} systemu splnuje, {time.monotonic() - started:.0f} s", flush=True)
        rows.append({"entry": en, "summary": n_ok,
                     "test_mean": float(np.nanmean(np.where(ok, te["annual"], np.nan)))})
    pickle.dump({"rows": rows, "series": cache}, open(P.OUT / "annual_rows.pkl", "wb"))
    systems = sorted((r for r in rows if "m" in r), key=lambda r: -r["score"])
    f = SM._f
    out = ["# Rocni zhodnoceni uctu - jednotlive systemy", "",
           f"_Kazdy obchod vaze stejny podil uctu jako marzi; podil zvolen tak, aby nejvetsi propad 2012-2022 byl "
           f"{DD_TARGET:.0%} uctu (nejvyse {S_MAX:.0%} uctu na obchod). Podminky vyberu v 2012-18 i 2019-22: "
           f">= 2 ziskove obchody mesicne v prumeru, >= 2 v aspon polovine mesicu, zisk. Rocne = prosty soucet "
           f"(bez slozeneho uroceni)._", ""]
    for r in rows:
        if "summary" in r:
            out.append(f"* {r['entry']}: splnuje {r['summary']} systemu, prumerne rocne v testu {r['test_mean']:+.1%}")
    out += ["", "| system | marze/obchod | obchodu/rok | usp. | zisk/obchod | ziskovych/mesic | rocne 2012-18 | "
            "2019-22 | **2023-26** | propad 2023-26 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in systems[:40]:
        out.append(f"| {P.describe(meta, r['m'], r['x'], r['entry'])} | {r['share']:.1%} | {r['TEST_n_year']:.0f} | "
                   f"{f(r['TEST_win'], '.0%')} | {f(r['TEST_e'], '+.1f')} % | {r['TEST_wins_month']:.1f} | "
                   f"{r['A_annual']:+.0%} | {r['B_annual']:+.0%} | **{r['TEST_annual']:+.0%}** | {r['TEST_dd']:.0%} |")
    out += ["", f"_vypocet {time.monotonic() - started:.0f} s_"]
    (PROJECT_ROOT / "docs" / "ROCNI_VYNOS.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
