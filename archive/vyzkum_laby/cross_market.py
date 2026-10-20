"""Cross-market validation: a rule counts only if it works on two separate
groups of markets AND later in time.

    python scripts/cross_market.py        # -> docs/DVA_TRHY.md (needs profit_lab2 build on 41 pairs)

Groups: G1 = the 25 FXCM pairs (where F1 / CH-008 was found), G2 = the 16
HistData pairs (Scandinavian, central European and emerging currencies,
CHF/JPY, EUR/CAD, GBP/AUD) - never used for any earlier choice.
1. Transfer test: systems chosen on G1 2012-2022 -> how they do on G2.
2. Double-robust choice: positive with t >= T_MIN on G1 2012-2022 AND on
   G2 2012-2022 (and >= MIN_N trades in each) -> test on 2023-2026 in both groups.
Units: % of the margin per trade at 1:30, after costs and swap.
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

import fxcm_universe as U  # noqa: E402
import histdata_universe as H  # noqa: E402
import profit_lab2 as P  # noqa: E402

SEL = (date(2012, 1, 1), date(2022, 12, 31))
TEST = (date(2023, 1, 1), date(2026, 9, 30))
T_MIN = 2.0
MIN_N = 60


def subset(B: dict, rows: np.ndarray) -> dict:
    return {"O": B["O"][rows], "V": B["V"][rows], "M": B["M"][:, rows], "dates": B["dates"][rows]}


def main() -> int:
    started = time.monotonic()
    info = pickle.loads((P.OUT / "meta.pkl").read_bytes())
    meta = info["meta"]
    g1, g2 = set(U.universe()), set(H.PAIRS)
    out = ["# Dve skupiny trhu: plati pravidlo i tam, kde nebylo hledano?", "",
           "_G1 = 25 paru FXCM (tady bylo nalezeno F1), G2 = 16 novych paru z HistData (NOK, SEK, MXN, ZAR, PLN, HUF, CZK, "
           "CHF/JPY, EUR/CAD, GBP/AUD). Zisk v % marze na obchod po nakladech a swapu._", ""]
    transfer, robust = [], []
    for en, _ in P.ENTRIES:
        B = P.load_block(en)
        r1 = np.flatnonzero(np.isin(B["pairs"], list(g1)))
        r2 = np.flatnonzero(np.isin(B["pairs"], list(g2)))
        G1, G2 = subset(B, r1), subset(B, r2)
        s = {("G1", "sel"): P.stats(G1, SEL), ("G1", "test"): P.stats(G1, TEST),
             ("G2", "sel"): P.stats(G2, SEL), ("G2", "test"): P.stats(G2, TEST)}
        # 1. transfer: chosen on G1 2012-2022 only
        a = s[("G1", "sel")]
        chosen = (a["n"] >= 100) & (a["e"] >= 5) & (a["t"] >= T_MIN)
        everything = a["n"] >= 100
        g2e = s[("G2", "sel")]["e"]
        transfer.append((en, int(chosen.sum()), float(np.nanmean(np.where(chosen, g2e, np.nan))),
                         float(np.nanmean(np.where(chosen & (s[("G2", "sel")]["n"] > 0), g2e > 0, np.nan))),
                         float(np.nanmean(np.where(everything, g2e, np.nan))),
                         float(np.nanmean(np.where(everything & (s[("G2", "sel")]["n"] > 0), g2e > 0, np.nan)))))
        # 2. double robust
        ok = np.ones_like(a["e"], dtype=bool)
        for g in ("G1", "G2"):
            st = s[(g, "sel")]
            ok &= (st["n"] >= MIN_N) & (st["e"] > 0) & (st["t"] >= T_MIN)
        for m, x in zip(*np.nonzero(ok)):
            robust.append({"entry": en, "m": int(m), "x": int(x), "name": P.describe(meta, int(m), int(x), en),
                           **{f"{g}_{p}_{k}": float(s[(g, p)][k][m, x]) for g in ("G1", "G2") for p in ("sel", "test")
                              for k in ("n", "win", "e", "t")}})
        print(f"{en}: {int(ok.sum())} dvojite robustnich, {time.monotonic() - started:.0f} s", flush=True)
    out += ["## 1. Prenos: systemy vybrane na G1 (2012-2022, n >= 100, zisk >= 5 %, t >= 2) na novych trzich G2", "",
            "| vstup | vybranych | prumer na G2 | podil kladnych na G2 | vsechny systemy: prumer na G2 | podil kladnych |",
            "|---|---|---|---|---|---|"]
    out += [f"| {en} | {n} | {e:+.1f} % | {p:.0%} | {e0:+.1f} % | {p0:.0%} |" for en, n, e, p, e0, p0 in transfer] + [""]
    robust.sort(key=lambda r: -min(r["G1_sel_t"], r["G2_sel_t"]))
    pos_both = [r for r in robust if r["G1_test_n"] > 0 and r["G2_test_n"] > 0]
    out += [f"## 2. Dvojite robustni: kladne s t >= {T_MIN} na G1 i G2 v 2012-2022 (n >= {MIN_N} v kazde)", "",
            f"Splnuje **{len(robust)}** systemu. V testu 2023-2026: kladne na G1 u "
            f"{sum(1 for r in pos_both if r['G1_test_e'] > 0)} z {len(pos_both)}, na G2 u "
            f"{sum(1 for r in pos_both if r['G2_test_e'] > 0)}, na obou u "
            f"{sum(1 for r in pos_both if r['G1_test_e'] > 0 and r['G2_test_e'] > 0)}.", "",
            "| system | G1 2012-22 n / usp. / zisk / t | G2 2012-22 | **G1 2023-26** | **G2 2023-26** |", "|---|---|---|---|---|"]
    for r in robust[:40]:
        cells = [f"{int(r[f'{g}_{p}_n'])} / {r[f'{g}_{p}_win']:.0%} / {r[f'{g}_{p}_e']:+.1f} % / {r[f'{g}_{p}_t']:.1f}"
                 for g, p in (("G1", "sel"), ("G2", "sel"), ("G1", "test"), ("G2", "test"))]
        out.append(f"| {r['name']} | " + " | ".join(cells) + " |")
    out += ["", f"_vypocet {time.monotonic() - started:.0f} s_"]
    pickle.dump(robust, open(P.OUT / "robust_rows.pkl", "wb"))
    (PROJECT_ROOT / "docs" / "DVA_TRHY.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
