"""Report of the wide portfolio of rules (research lab; was the main() of scripts/portfolio_sim.py until R-048).

    python scripts/portfolio_report.py        # -> docs/PORTFOLIO_SIROKE.md   (needs `profit_lab2.py build`)

Candidates = systems of profit_lab2 with a positive monthly result and a monthly t >= 2 in each half of the
selection period; per rule family (entry x signal x trend x fundamental filter x rhythm) only its best exit. Every
family is simulated trade by trade (scripts/profit_deep.simulate) and the account simulation is
scripts/portfolio_sim.run_portfolio (the live core); this report is research only and moved out of portfolio_sim
so that the live core does not import portfolio_lab / annual_lab / profit_lab2 (architektura-v2, phase 1).
"""

import pickle
import sys
import time
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import portfolio_lab as PL  # noqa: E402
import portfolio_sim as PS  # noqa: E402
import profit_deep as D  # noqa: E402
import profit_lab2 as P  # noqa: E402

SHARES = (0.02, 0.03, 0.05, 0.08, 0.10)
SPANS = {"2012-18": (2012, 2018), "2019-22": (2019, 2022), "2023-26": (2023, 2026)}


def rule_of(c: dict, meta, exits) -> D.Rule:
    sname, trend, fund, rhythm = meta[c["m"]]
    kind, tp, sl, hd = exits[c["x"]]
    limit = dict(P.ENTRIES)[c["entry"]]
    return D.Rule(name=c["name"], signal=sname, weekly=rhythm == "TYDEN" or sname.startswith("W "), trend=trend,
                  fund=fund, limit_atr=limit, tp=tp, sl=sl, hold_days=hd, exit_kind=kind)


def families(cands: list[dict]) -> list[dict]:
    best = {}
    for c in cands:                                   # sorted by t, the first one per family wins
        best.setdefault((c["entry"], c["m"]), c)
    return list(best.values())


def table(trade_lists, share) -> list[str]:
    lines = []
    for label, yrs in SPANS.items():
        r = PS.run_portfolio(trade_lists, share, yrs)
        lines.append(f"| {label} | {r['n_year']:.0f} | {r['win']:.0%} | {r['e']:+.1f} % | {r['wins_month']:.1f} | "
                     f"{r['months_2wins']:.0%} | {r['months_pos']:.0%} | **{r['cagr']:+.1%}** | {r['max_dd']:.1%} |")
    return lines


HEAD = ["| obdobi | obchodu/rok | uspesnost | zisk/obchod (% marze) | ziskovych/mesic | mesicu s >= 2 ziskovymi | "
        "ziskovych mesicu | **rocne (slozene)** | max. propad |", "|---|---|---|---|---|---|---|---|---|"]


def main() -> int:
    started = time.monotonic()
    info = pickle.loads((P.OUT / "meta.pkl").read_bytes())
    out = ["# Portfolio pravidel - realisticka simulace uctu", "",
           "_Obchod po obchodu (hodinove BID/ASK, naklady, swap), slozene uroceni, nejvyse jedna pozice na par v celem "
           f"portfoliu, soucet marzi otevrenych obchodu <= {PS.MARGIN_CAP:.0%} uctu, vsechna vybrana pravidla se stejnou "
           "vahou (zadne ladeni vah). Vyber pravidel jen z minulosti._", ""]
    saved = {}
    for label, subs, sel_years in (("Vyber na 2012-2018", [(0, 42), (42, 84)], (2012, 2018)),
                                   ("Vyber na 2012-2022", [(0, 84), (84, 132)], (2012, 2022))):
        fams = families(PL.candidates(subs))
        rules = [rule_of(c, info["meta"], info["exits"]) for c in fams]
        trade_lists = [D.simulate(r) for r in rules]
        # keep families that are also positive trade by trade in every selection sub-period
        keep = []
        for r, tl in zip(rules, trade_lists):
            sub = [[t for t in tl if y0 <= t["day"].year <= y1] for (y0, y1) in
                   (((2012, 2015), (2016, 2018)) if sel_years[1] == 2018 else ((2012, 2018), (2019, 2022)))]
            if all(len(x) >= 10 and np.mean([t["margin_pct"] for t in x]) > 0 for x in sub):
                keep.append((r, tl))
        rules, trade_lists = [k[0] for k in keep], [k[1] for k in keep]
        saved[label] = rules
        print(f"{label}: {len(fams)} rodin, {len(rules)} kladnych obchod po obchodu, {time.monotonic() - started:.0f} s",
              flush=True)
        out += [f"## {label}: {len(rules)} pravidel", ""]
        for share in SHARES:
            out += [f"### marze {share:.0%} uctu na obchod", ""] + HEAD + table(trade_lists, share) + [""]
        out += ["Pravidla (poradi = priorita):", ""] + [f"{k + 1}. {r.name}" for k, r in enumerate(rules)] + [""]
    pickle.dump(saved, open(P.OUT / "portfolio_rules.pkl", "wb"))
    out += [f"_vypocet {time.monotonic() - started:.0f} s_"]
    (PROJECT_ROOT / "docs" / "PORTFOLIO_SIROKE.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
