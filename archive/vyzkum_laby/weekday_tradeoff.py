"""Two questions of the user, answered on the F1 rule (docs/ZISK10_VYSLEDEK.md):
why only Friday, and is it better to have fewer trades with a bigger profit
or more trades with a smaller one.

    python scripts/weekday_tradeoff.py     # -> docs/DNY_A_POCET.md (~3 min)
"""

import sys
import time
from dataclasses import replace
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import portfolio_sim as PS  # noqa: E402
import profit_deep as D  # noqa: E402

BASE = D.FINALISTS[0]
SHARES = (0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10, 0.12, 0.15, 0.20)


def at_dd(trades, dd=0.20, years=(2012, 2022)):
    best = None
    for s in SHARES:
        r = PS.run_portfolio([trades], s, years)
        if r["max_dd"] <= dd:
            best = (s, r)
    return best


def line(label, trades) -> str:
    per = D.by_period(trades)
    five = PS.run_portfolio([trades], 0.05)
    best = at_dd(trades)
    s, _ = best if best else (0.0, None)
    full = PS.run_portfolio([trades], s) if s else five
    return (f"| {label} | {five['n_year']:.0f} | {five['win']:.0%} | {five['e']:+.1f} % | "
            f"{per['A']['e']:+.1f} / {per['B']['e']:+.1f} / {per['TEST']['e']:+.1f} % | {five['cagr']:+.1%} / "
            f"{five['max_dd']:.0%} | {s:.0%} -> **{full['cagr']:+.1%}** / {full['max_dd']:.0%} | {five['wins_month']:.1f} | "
            f"{five['months_2wins']:.0%} |")


HEAD = ["| varianta | obchodu/rok | uspesnost | zisk/obchod (% marze) | 2012-18 / 2019-22 / 2023-26 | rocne / propad "
        "pri marzi 5 % | marze pro propad <= 20 % (2012-22) -> rocne / propad 2012-26 | ziskovych/mesic | "
        "mesicu s >= 2 ziskovymi |", "|---|---|---|---|---|---|---|---|---|"]


def main() -> int:
    started = time.monotonic()
    out = ["# Proc patek a kolik obchodu", "",
           "_Pravidlo F1 (propad RSI(2) + rozchazejici se sazby, TP 0.75 ATR, SL 3 ATR, max 20 dni), 25 paru 2012-2026, "
           "obchod po obchodu, slozene uroceni, jedna pozice na par._", "",
           "## Den rozhodnuti", ""] + HEAD
    days = ["pondeli", "utery", "streda", "ctvrtek", "patek"]
    for d, name in enumerate(days):
        out.append(line(f"jen {name}", D.simulate(replace(BASE, weekday=d))))
    out.append(line("kazdy den", D.simulate(replace(BASE, weekly=False))))
    print(f"dny: {time.monotonic() - started:.0f} s", flush=True)
    out += ["", "## Vic obchodu s mensim ziskem, nebo mene s vetsim (uvolnovani prahu sazeb)", ""] + HEAD
    for thr in (0.4, 0.25, 0.15, 0.10, 0.05, 0.0):
        out.append(line(f"prah sazeb {thr:.2f} p.b.", D.simulate(replace(BASE, rates_thr=thr))))
    out += ["", f"_vypocet {time.monotonic() - started:.0f} s_"]
    (PROJECT_ROOT / "docs" / "DNY_A_POCET.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
