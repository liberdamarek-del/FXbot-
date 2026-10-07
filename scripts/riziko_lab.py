"""Risk per trade (user's request 2026-10-07): the champion's stop costs up to 15-38 % of the account on a strong
signal (20 % margin x a 4 ATR stop), its target only ~1-3 %. Can a trade risk at most 1-2 % of the account and still
earn, and does a better target / stop ratio help?

    python scripts/riziko_lab.py            # -> data/research/riziko/vysledky.json + table on stdout
    python scripts/riziko_lab.py --stupne   # the champion's trades sized by risk, tier weights walk-forward

Every trade is sized by its stop: margin = r x account / (stop in % of the margin), so hitting the stop costs r of the
account (a gap through the stop can cost more - reported as the worst trade). At most MAX_OPEN trades at once (open
risk <= MAX_OPEN x r). Families (the decision stays Friday 16:00 New York, the champion's rate tiers):
  pokles   the champion's entries (short pullback in the direction of the rate divergence), other exits
  pruraz   20-day breakout in the direction of the rate divergence (trend: small losses, bigger wins)
  tyden13  13-week breakout in the direction of the rate divergence
Walk-forward like the gate: exits chosen on 2012-2018 (test 2019-2022) and on 2012-2022 (test 2023-2026) by the
pre-registered score CAGR / max(drawdown, 5 %) at r = 2 % with >= 12 trades a year; the test years never choose.
"""

import copy
import itertools
import json
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import self_learn as SL  # noqa: E402

OUT = PROJECT_ROOT / "data" / "research" / "riziko"
MAX_OPEN = 6
RISKS = (0.01, 0.02)
SPLITS = (((2012, 2018), (2019, 2022)), ((2012, 2022), (2023, 2026)))
CHAMP = json.loads((PROJECT_ROOT / "learning" / "champion_12_mesicne.json").read_text())["config"]
RATE_TIERS = [{"fund": "rates_up+carry", "rates_thr": 0.25}, {"fund": "rates_up", "rates_thr": 0.25},
              {"fund": "rates_up", "rates_thr": 0.10}]

FAMILIES = {
    "pokles": dict(tp=(0.5, 0.75, 1.0, 1.5, 2.0, 3.0), sl=(0.75, 1.0, 1.5, 2.0, 3.0, 4.0), hold=(10, 20, 40)),
    "pruraz": dict(tp=(1.5, 2.0, 3.0, 4.0, 6.0), sl=(1.0, 1.5, 2.0, 3.0), hold=(20, 40)),
    "tyden13": dict(tp=(1.5, 2.0, 3.0, 4.0, 6.0), sl=(1.0, 1.5, 2.0, 3.0), hold=(20, 40)),
}


def config(family: str, tp: float, sl: float, hold: int) -> dict:
    cfg = copy.deepcopy(CHAMP)
    cfg["base"].update(tp=tp, sl=sl, hold_days=hold)
    if family != "pokles":                          # trend trades: no close in profit before a central bank decision
        cfg["base"]["signal"] = "D Donchian20 pruraz" if family == "pruraz" else "W 13-tydenni pruraz"
        cfg["base"]["exit_before_cb"] = ""
        cfg["tiers"] = copy.deepcopy(RATE_TIERS)
    return cfg


def sized(lists: list[list[dict]]) -> list[list[dict]]:
    out = []
    for tl in lists:
        new = []
        for t in tl:
            t = dict(t)
            t["size_factor"] = 100.0 / t["sl_pct"]      # margin x stop % = r of the account
            new.append(t)
        out.append(new)
    return out


def metrics(lists, r, years, cfg) -> dict:
    res = SL.PS.run_portfolio(lists, [r] * len(lists), years, None, None, None, MAX_OPEN)
    imp = np.array([fr * t["margin_pct"] for fr, t in zip(res["entry_frac"], res["trades"])])
    win, loss = imp[imp > 0], imp[imp <= 0]
    return {"cagr": res["cagr"], "dd": res["max_dd"], "n_year": res["n_year"], "win": float(np.mean(imp > 0)) if len(imp) else 0,
            "avg_win": float(win.mean()) if len(win) else 0.0, "avg_loss": float(loss.mean()) if len(loss) else 0.0,
            "worst": float(imp.min()) if len(imp) else 0.0, "wins_month": res["wins_month"],
            "score": res["cagr"] / max(res["max_dd"], 0.05)}


TIER_W = (1.0, 0.5, 0.3, 0.2, 0.1, 0.0)        # risk of a tier relative to the strongest tier (non-increasing)


def tier_weights(lists, r_max: float) -> dict:
    """The champion's entries and exits, each trade sized by its stop (risk = r_max x tier weight); the tier weights
    chosen on the selection years of each gate split by return per drawdown with >= 2 winning trades a month."""
    sized_lists = sized(lists)
    out = {}
    for sel, test in SPLITS:
        best = (-np.inf, None)
        for w in itertools.product(TIER_W, repeat=len(sized_lists) - 1):
            ws = (1.0,) + w
            if any(a < b for a, b in zip(ws, ws[1:])):
                continue
            res = SL.PS.run_portfolio(sized_lists, [r_max * x for x in ws], sel)
            if res["wins_month"] < 2.0:
                continue
            score = res["cagr"] / max(res["max_dd"], 0.02)
            if score > best[0]:
                best = (score, ws)
        ws = best[1]
        line = {}
        for yrs in (sel, test):
            res = SL.PS.run_portfolio(sized_lists, [r_max * x for x in ws], yrs)
            imp = np.array([fr * t["margin_pct"] for fr, t in zip(res["entry_frac"], res["trades"])])
            line[f"{yrs[0]}_{yrs[1]}"] = {"cagr": res["cagr"], "dd": res["max_dd"], "worst": float(imp.min()),
                                          "win": float(np.mean(imp > 0)), "wins_month": res["wins_month"],
                                          "n_year": res["n_year"], "max_used": res["max_used"]}
        out[f"{test[0]}"] = {"weights": ws, **line}
        t = line[f"{test[0]}_{test[1]}"]
        print(f"STUPNE r {r_max:.0%}: vyber {sel[0]}-{sel[1]} vahy {ws} | test {test[0]}-{test[1]}: {t['cagr']:+.1%} rocne, "
              f"propad {t['dd']:.0%}, nejhorsi obchod {t['worst']:+.1f} % uctu, uspesnost {t['win']:.0%}, "
              f"{t['wins_month']:.1f} ziskovych/mesic, {t['n_year']:.0f} obchodu/rok, marze max {t['max_used']:.0%} uctu",
              flush=True)
    return out


LIVE_RISKS = (0.02, 0.03, 0.05, 0.08, 0.10)
DEFAULT_RISK = 0.05                                 # the dashboard's default maximum loss of one trade (% of account)
LIVE_FILE = PROJECT_ROOT / "learning" / "riziko.json"


def main_tiers() -> int:
    """Walk-forward of the tier weights for every risk level, the live weights (chosen on 2012-2022 at the default
    risk) and the table of the unseen test years -> learning/riziko.json (signals_live, the dashboard)."""
    from datetime import date
    OUT.mkdir(parents=True, exist_ok=True)
    lists = SL.trade_lists(CHAMP)
    res = {f"{r}": tier_weights(lists, r) for r in LIVE_RISKS}
    (OUT / "stupne.json").write_text(json.dumps(res, indent=1))

    def row(m):
        return {"rocne": round(m["cagr"] * 100, 1), "propad": round(m["dd"] * 100, 1),
                "nejhorsi_obchod": round(m["worst"], 1), "uspesnost": round(m["win"] * 100), "ziskovych_mesicne":
                round(m["wins_month"], 1), "obchodu_rocne": round(m["n_year"]), "marze_max": round(m["max_used"] * 100)}
    live = {"sampion": CHAMP["name"], "vytvoreno": date.today().isoformat(), "vychozi_riziko": DEFAULT_RISK,
            "vahy": list(res[f"{DEFAULT_RISK}"]["2023"]["weights"]), "vybrano_na": "2012-2022",
            "tabulka": [{"riziko": r, "test_2019_22": row(res[f"{r}"]["2019"]["2019_2022"]),
                         "test_2023_26": row(res[f"{r}"]["2023"]["2023_2026"])} for r in LIVE_RISKS]}
    champ = json.loads((PROJECT_ROOT / "learning" / "champion_12_mesicne.json").read_text())
    orig = {}
    for k, (sel, test) in enumerate(SPLITS):                     # the champion's own margins, the same test years
        res_o = SL.run_pf(lists, champ["eval"][str(k)]["shares"], test, CHAMP)
        imp = np.array([fr * t["margin_pct"] for fr, t in zip(res_o["entry_frac"], res_o["trades"])])
        orig[f"test_{test[0]}_{test[1] % 100:02d}"] = {"rocne": round(res_o["cagr"] * 100, 1),
                                                       "propad": round(res_o["max_dd"] * 100, 1),
                                                       "nejhorsi_obchod": round(float(imp.min()), 1)}
    live["puvodni"] = {"marze": champ["eval"]["1"]["shares"], **orig}
    LIVE_FILE.write_text(json.dumps(live, indent=1, ensure_ascii=False))
    print(f"zapsano {LIVE_FILE}: vahy {live['vahy']}")
    return 0


def main() -> int:
    if "--stupne" in sys.argv:
        return main_tiers()
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for fam, grid in FAMILIES.items():
        for tp, sl, hold in itertools.product(grid["tp"], grid["sl"], grid["hold"]):
            cfg = config(fam, tp, sl, hold)
            lists = sized(SL.trade_lists(cfg))
            row = {"family": fam, "tp": tp, "sl": sl, "hold": hold}
            for r in RISKS:
                for yrs in ((2012, 2018), (2019, 2022), (2012, 2022), (2023, 2026)):
                    row[f"{r}_{yrs[0]}_{yrs[1]}"] = metrics(lists, r, yrs, cfg)
            rows.append(row)
            print(f"{fam} tp {tp} sl {sl} hold {hold}: 2012-18 {row['0.02_2012_2018']['cagr']:+.1%} / "
                  f"{row['0.02_2012_2018']['dd']:.0%}", flush=True)
    picks = {}
    for fam in list(FAMILIES) + ["vse"]:
        cand = [r for r in rows if fam in ("vse", r["family"])]
        for (sel, test) in SPLITS:
            key = f"0.02_{sel[0]}_{sel[1]}"
            ok = [r for r in cand if r[key]["n_year"] >= 12]
            best = max(ok, key=lambda r: r[key]["score"]) if ok else None
            picks[f"{fam}_{test[0]}"] = best and {k: best[k] for k in ("family", "tp", "sl", "hold")}
            if best:
                for rr in RISKS:
                    m = best[f"{rr}_{test[0]}_{test[1]}"]
                    print(f"VYBER {fam} (vyber {sel[0]}-{sel[1]}) -> {best['family']} tp {best['tp']} sl {best['sl']} "
                          f"hold {best['hold']} | test {test[0]}-{test[1]} r {rr:.0%}: {m['cagr']:+.1%} rocne, propad "
                          f"{m['dd']:.0%}, uspesnost {m['win']:.0%}, prum. zisk {m['avg_win']:+.2f} %, prum. ztrata "
                          f"{m['avg_loss']:+.2f} %, nejhorsi {m['worst']:+.2f} %, {m['n_year']:.0f} obchodu/rok, "
                          f"{m['wins_month']:.1f} ziskovych/mesic", flush=True)
    base = next(r for r in rows if r["family"] == "pokles" and (r["tp"], r["sl"], r["hold"]) == (0.75, 4.0, 20))
    for rr in RISKS:
        for test in ((2019, 2022), (2023, 2026)):
            m = base[f"{rr}_{test[0]}_{test[1]}"]
            print(f"SOUCASNA PRAVIDLA, riziko {rr:.0%}: {test[0]}-{test[1]} {m['cagr']:+.1%} rocne, propad {m['dd']:.0%}, "
                  f"uspesnost {m['win']:.0%}, nejhorsi {m['worst']:+.2f} %", flush=True)
    (OUT / "vysledky.json").write_text(json.dumps({"rows": rows, "picks": picks, "max_open": MAX_OPEN}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
