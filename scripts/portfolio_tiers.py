"""Tiered portfolio of the 'Friday dip + rate divergence' rule: the stronger
the fundamental tailwind, the bigger the position. Goal: the highest annual
account return at a limited drawdown, with >= 2 winning trades a month.

    python scripts/portfolio_tiers.py      # -> docs/PORTFOLIO_STUPNE.md (~5 min)

Tiers (one rule each, scripts/profit_deep.Rule; decision at the Friday close,
RSI(2) < 5 dip / > 95 rally, TP 0.75 ATR, SL 3 ATR, max 20 days):
  T1 rate divergence >= 0.25 pp and carry in the trade direction
  T2 rate divergence >= 0.25 pp                      (= F1 / CH-008)
  T3 rate divergence >= 0.10 pp
  T4 rate divergence >= 0 pp (only the direction)
A trade belongs to the highest tier it qualifies for (one position per pair).
Margin per tier chosen on 2012-2022 (coarse grid, largest annual return with
max drawdown <= 20 %), 2023-2026 is the test.
"""

import itertools
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import portfolio_sim as PS  # noqa: E402
import profit_deep as D  # noqa: E402

BASE = D.FINALISTS[0]
TIERS = {"T1 sazby >= 0.25 p.b. + carry": replace(BASE, fund="rates_up+carry"),
         "T2 sazby >= 0.25 p.b. (F1)": BASE,
         "T3 sazby >= 0.10 p.b.": replace(BASE, rates_thr=0.10),
         "T4 sazby >= 0 p.b.": replace(BASE, rates_thr=0.0)}
GRID = ((0.04, 0.06, 0.08, 0.10, 0.12, 0.15, 0.20), (0, 0.04, 0.06, 0.08, 0.10, 0.12, 0.15),
        (0, 0.02, 0.03, 0.04, 0.05, 0.06), (0, 0.01, 0.02, 0.03))
DD_MAX = 0.20
SEL, TEST = (2012, 2022), (2023, 2026)


def tier_lists(variant=None) -> list[list[dict]]:
    return [D.simulate(variant(r) if variant else r) for r in TIERS.values()]


def choose(lists) -> list[tuple]:
    out = []
    for sh in itertools.product(*GRID):
        if not all(a >= b for a, b in zip(sh, sh[1:])):
            continue
        r = PS.run_portfolio(lists, list(sh), SEL)
        if r["max_dd"] <= DD_MAX:
            out.append((r["cagr"], sh, r))
    return sorted(out, key=lambda x: -x[0])


def bootstrap_dd(month_returns: list[float], years: int = 10, runs: int = 4000, block: int = 3) -> tuple:
    """Max drawdown distribution of `years` long paths from resampled blocks of months."""
    rng = np.random.default_rng(7)
    r = np.array(month_returns)
    n = years * 12
    dds, finals = [], []
    for _ in range(runs):
        idx = np.concatenate([np.arange(s, s + block) % len(r) for s in rng.integers(0, len(r), n // block + 1)])[:n]
        eq = np.cumprod(1 + r[idx])
        peak = np.maximum.accumulate(np.concatenate([[1.0], eq]))[1:]
        dds.append((1 - eq / peak).max())
        finals.append(eq[-1] ** (1 / years) - 1)
    return np.percentile(dds, [50, 95, 99]), np.percentile(finals, [5, 50, 95])


def row(label, r) -> str:
    return (f"| {label} | {r['n_year']:.0f} | {r['win']:.0%} | {r['e']:+.1f} % | {r['wins_month']:.1f} | "
            f"{r['months_2wins']:.0%} | {r['months_pos']:.0%} | **{r['cagr']:+.1%}** | {r['max_dd']:.1%} | "
            f"{r['max_used']:.0%} / {r['max_open']} |")


HEAD = ["| obdobi | obchodu/rok | uspesnost | zisk/obchod (% marze) | ziskovych obchodu/mesic | mesicu s >= 2 "
        "ziskovymi | ziskovych mesicu | **rocne (slozene)** | max. propad | max. vazana marze / pozic |",
        "|---|---|---|---|---|---|---|---|---|---|"]


def main() -> int:
    started = time.monotonic()
    lists = tier_lists()
    ranked = choose(lists)
    cagr, sh, _ = ranked[0]
    out = ["# Odstupnovane portfolio: patecni propad + rozchazejici se sazby", "",
           "_Obchod po obchodu na hodinovych BID/ASK FXCM 2012-2026 (25 paru), naklady + swap, slozene uroceni, "
           "jedna pozice na par, soucet marzi <= 100 % uctu. Velikosti stupnu vybrane jen na 2012-2022 "
           f"(nejvyssi rocni vynos pri propadu <= {DD_MAX:.0%}); 2023-2026 = test._", "",
           "## Stupne", ""]
    out += [f"* **{name}** - marze **{s:.0%} uctu** na obchod; {len(tl)} obchodu 2013-2026"
            for (name, tl), s in zip(zip(TIERS, lists), sh)] + [""]
    out += ["## Vysledek zvolenych velikosti", ""] + HEAD
    for label, yrs in (("2012-2022 (vyber)", SEL), ("**2023-2026 (test)**", TEST), ("cele 2012-2026", (2012, 2026))):
        out.append(row(label, PS.run_portfolio(lists, list(sh), yrs)))
    out += ["", "Dalsi nejlepsi velikosti z vyberu (pro kontrolu, ze nejde o nahodu jedne kombinace):", "",
            "| marze T1 / T2 / T3 / T4 | 2012-2022 rocne / propad | 2023-2026 rocne / propad |", "|---|---|---|"]
    for c, s2, r in ranked[:6]:
        te = PS.run_portfolio(lists, list(s2), TEST)
        out.append(f"| {' / '.join(f'{x:.0%}' for x in s2)} | {r['cagr']:+.1%} / {r['max_dd']:.0%} | "
                   f"{te['cagr']:+.1%} / {te['max_dd']:.0%} |")
    # single tiers for comparison
    out += ["", "## Srovnani: jednotlive stupne samostatne (stejna pravidla velikosti, propad <= 20 % na 2012-2022)", "",
            "| pravidlo | obchodu/rok | zisk/obchod | marze | 2012-2022 rocne / propad | 2023-2026 rocne / propad | "
            "mesicu s >= 2 ziskovymi |", "|---|---|---|---|---|---|---|"]
    for k, name in enumerate(TIERS):
        best = None
        for s in (0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10, 0.12, 0.15, 0.20):
            sh1 = [0.0] * len(TIERS)
            sh1[k] = s
            r = PS.run_portfolio(lists, sh1, SEL)
            if r["max_dd"] <= DD_MAX:
                best = (s, sh1, r)
        if best:
            s, sh1, r = best
            te = PS.run_portfolio(lists, sh1, TEST)
            out.append(f"| {name} | {r['n_year']:.0f} | {r['e']:+.1f} % | {s:.0%} | {r['cagr']:+.1%} / {r['max_dd']:.0%} | "
                       f"{te['cagr']:+.1%} / {te['max_dd']:.0%} | {r['months_2wins']:.0%} |")
    # year by year
    out += ["", "## Rok po roku (zvolene velikosti)", "",
            "| rok | obchodu | uspesnost | vynos roku | propad v roce | ziskovych obchodu/mesic | mesicu s >= 2 ziskovymi |",
            "|---|---|---|---|---|---|---|"]
    for y in range(2013, 2027):
        r = PS.run_portfolio(lists, list(sh), (y, y))
        out.append(f"| {y} | {len(r['trades'])} | {r['win']:.0%} | {r['equity'] - 1:+.1%} | {r['max_dd']:.1%} | "
                   f"{r['wins_month']:.1f} | {r['months_2wins']:.0%} |")
    full = PS.run_portfolio(lists, list(sh), (2012, 2026))
    worst_month = min(full["month_returns"])
    (dd50, dd95, dd99), (c5, c50, c95) = bootstrap_dd(full["month_returns"])
    out += ["", f"Nejhorsi mesic: {worst_month:+.1%}. Nahodne preskladane mesice (4 000 desetiletych drah): propad "
            f"median {dd50:.0%}, v 5 % drah >= {dd95:.0%}, v 1 % drah >= {dd99:.0%}; rocni vynos 5. / 50. / 95. percentil "
            f"{c5:+.0%} / {c50:+.0%} / {c95:+.0%}.", ""]
    # robustness
    variants = [("naklady 2x", lambda r: replace(r, cost_x=2.0)),
                ("rozhodnuti a vstup 1 h pred patecnim zaverem", lambda r: replace(r, early_h=1)),
                ("vstup az po vikendu (nedelni otevreni)", lambda r: replace(r, delay_h=1)),
                ("sazby CB o 2 mesice zpet misto OECD", lambda r: replace(r, rates_src="policylag")),
                ("sazby zname o 3 mesice zpet", lambda r: replace(r, rates_lag=3)),
                ("cil >= 15 % marze (jen volatilnejsi trhy)", lambda r: replace(r, min_tp_pct=0.5))]
    out += ["## Odolnost (stejne velikosti stupnu)", "", "| varianta | 2012-2022 rocne / propad | 2023-2026 rocne / propad |",
            "|---|---|---|"]
    for label, fn in variants:
        vl = tier_lists(fn)
        a, b = PS.run_portfolio(vl, list(sh), SEL), PS.run_portfolio(vl, list(sh), TEST)
        out.append(f"| {label} | {a['cagr']:+.1%} / {a['max_dd']:.0%} | {b['cagr']:+.1%} / {b['max_dd']:.0%} |")
        print(f"{label}: {time.monotonic() - started:.0f} s", flush=True)
    out += ["", f"_vypocet {time.monotonic() - started:.0f} s_"]
    (PROJECT_ROOT / "docs" / "PORTFOLIO_STUPNE.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
