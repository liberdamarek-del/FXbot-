"""Report of the current self-learning champion on the 12 live pairs:
year by year, robustness, random reshuffles - with the tier margins fitted
on 2012-2022 only.

    python scripts/champion_report.py [--profile max|mesicne]   # -> docs/SAMPION_12.md
"""

import json
import sys
from dataclasses import replace
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import portfolio_sim as PS  # noqa: E402
import portfolio_tiers as PT  # noqa: E402
import self_learn as SL  # noqa: E402


def describe(cfg: dict, shares) -> list[str]:
    b = cfg["base"]
    when = ("v 16:00 New York (22:00 Praha), hodinu pred dennim zaverem" if b.get("decide_h") == 1
            else "pri dennim zaveru (23:00 Praha)" if not b.get("decide_h") else f"{b['decide_h']} h pred dennim zaverem")
    lines = [f"* rozhodnuti a vstup v patek {when}, {len(SL.symbols_of(cfg))} paru; "
             f"TP {b['tp']} x ATR(14), SL {b['sl']} x ATR(14), nejdele {b['hold_days']} obchodnich dni; "
             "jedna pozice na par"]
    names = {"rates_up+carry": "sazby se rozchazeji >= {t} p.b. + kladny carry", "rates_up": "sazby se rozchazeji >= {t} p.b."}
    for tier, s in zip(cfg["tiers"], shares):
        sig = tier.get("signal", b["signal"]).replace("D ", "").replace("|", " nebo ")
        lines.append(f"* signal {sig} (SELL zrcadlove), {names[tier['fund']].format(t=tier['rates_thr'])} -> "
                     f"marze **{s:.0%} uctu**")
    if cfg["sizing"] == "vol":
        lines.append("* marze se nasobi 84 % / (stop obchodu v % marze), v mezich 0.5-2x: siroky stop = mensi pozice")
    return lines


def main(argv: list[str]) -> int:
    profile = argv[argv.index("--profile") + 1] if "--profile" in argv else "max"
    SL.PROFILE = SL.PROFILES[profile]
    state = json.loads(SL.PROFILES[profile]["state"].read_text())
    cfg = state["config"]
    shares = list(state["eval"]["1"]["shares"])                 # fitted on 2012-2022
    lists = SL.trade_lists(cfg)
    out = [f"# Sampion samouceni - 12 paru (profil {profile})", "", f"_{cfg['name']}. Velikosti vybrane jen na 2012-2022 "
           "(max. propad <= 20 %); roky 2023-2026 jsou test. Obchod po obchodu na hodinovych strednich cenach FXCM, spread + skluz, "
           "swap, slozene uroceni._", "", "## Pravidla", ""] + describe(cfg, shares) + [""]
    out += ["## Vysledky", "", "| obdobi | obchodu/rok | uspesnost | zisk/obchod (% marze) | ziskovych/mesic | "
            "mesicu s >= 2 ziskovymi | **rocne** | max. propad | max. vazana marze |", "|---|---|---|---|---|---|---|---|---|"]
    for label, yrs in (("2012-2022 (vyber)", (2012, 2022)), ("**2023-2026 (test)**", (2023, 2026)),
                       ("cele 2012-2026", (2012, 2026))):
        r = PS.run_portfolio(lists, shares, yrs, cfg.get("max_ccy"), cfg.get("brake"))
        out.append(f"| {label} | {r['n_year']:.0f} | {r['win']:.0%} | {r['e']:+.1f} % | {r['wins_month']:.1f} | "
                   f"{r['months_2wins']:.0%} | **{r['cagr']:+.1%}** | {r['max_dd']:.1%} | {r['max_used']:.0%} |")
    out += ["", "| rok | " + " | ".join(str(y) for y in range(2013, 2027)) + " |", "|---" * 15 + "|"]
    years = [PS.run_portfolio(lists, shares, (y, y), cfg.get("max_ccy"), cfg.get("brake")) for y in range(2013, 2027)]
    out += ["| vynos | " + " | ".join(f"{r['equity'] - 1:+.0%}" for r in years) + " |",
            "| obchodu | " + " | ".join(str(len(r["trades"])) for r in years) + " |",
            "| propad | " + " | ".join(f"{r['max_dd']:.0%}" for r in years) + " |", ""]
    full = PS.run_portfolio(lists, shares, (2012, 2026), cfg.get("max_ccy"), cfg.get("brake"))
    (d50, d95, d99), (c5, c50, c95) = PT.bootstrap_dd(full["month_returns"])
    out += [f"Nejhorsi mesic {min(full['month_returns']):+.1%}. Nahodne preskladane mesice (4 000 desetiletych drah): "
            f"propad median {d50:.0%}, v 5 % drah >= {d95:.0%}, v 1 % >= {d99:.0%}; rocne 5. / 50. / 95. percentil "
            f"{c5:+.0%} / {c50:+.0%} / {c95:+.0%}.", ""]
    out += ["## Odolnost (stejne velikosti)", "", "| zmena | 2012-2022 rocne / propad | 2023-2026 rocne / propad |",
            "|---|---|---|"]
    for label, change in (("naklady 2x", lambda r: replace(r, cost_x=2.0)),
                          ("rozhodnuti a vstup az pri patecnim zaveru (17:00 New York, jen srovnani)",
                           lambda r: replace(r, decide_h=0)),
                          ("rozhodnuti a vstup o hodinu driv (15:00 New York)", lambda r: replace(r, decide_h=r.decide_h + 1)),
                          ("vstup az po vikendu", lambda r: replace(r, delay_h=r.decide_h + 1)),
                          ("sazby centralnich bank (o 2 mesice zpet) misto OECD", lambda r: replace(r, rates_src="policylag")),
                          ("polovicni velikosti pozic", None)):
        if change is None:
            vl, sh = lists, [x / 2 for x in shares]
        else:
            vl, sh = SL.trade_lists(cfg, change), shares
        a, b = (PS.run_portfolio(vl, sh, yrs, cfg.get("max_ccy"), cfg.get("brake")) for yrs in ((2012, 2022), (2023, 2026)))
        out.append(f"| {label} | {a['cagr']:+.1%} / {a['max_dd']:.0%} | {b['cagr']:+.1%} / {b['max_dd']:.0%} |")
    (PROJECT_ROOT / "docs" / "SAMPION_12.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
