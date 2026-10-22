"""Povinna kontrola na 16 parech HistData (R-049, zadani architektura-v2 faze 2): jak by se sampion choval na jinych mena-
ch, ktere nikdy nevybiral ani neladil. Je to REPORT, ne kriterium vyberu: nic se podle ni nemeni, marze sampiona se
nepocitaji znovu (pouziji se marze sampiona k dnesku) a vysledek nevstupuje do brany.

    python scripts/kontrola_histdata.py            # -> docs/KONTROLA_HISTDATA.md, learning/hygiena/histdata_kontrola.json

Data: scripts/histdata_universe.py (HistData.com, 1 minuta BID -> hodiny; ASK = BID, spread paru se pricita na obou
stranach z market.SPREAD_PIPS). 16 paru: USD/NOK, EUR/NOK, USD/SEK, EUR/SEK, USD/MXN, USD/ZAR, ZAR/JPY, USD/PLN, EUR/PLN,
USD/HUF, EUR/HUF, USD/CZK, EUR/CZK, CHF/JPY, EUR/CAD, GBP/AUD. Data od 2026-10-01 jsou v trezoru. Pro srovnani se na
STEJNYCH marzich pocita i 12 zivych paru.
"""

from __future__ import annotations

import copy
import json
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import histdata_universe as HU  # noqa: E402
import self_learn as SL  # noqa: E402
from src.core import market as P  # noqa: E402

OUT_JSON = PROJECT_ROOT / "learning" / "hygiena" / "histdata_kontrola.json"
OUT_DOC = PROJECT_ROOT / "docs" / "KONTROLA_HISTDATA.md"
SPANS = {"2012-2018": (2012, 2018), "2019-2022": (2019, 2022), "2023-2026-09": (2023, 2026)}


def _summary(r: dict) -> dict:
    return {"obchodu_rocne": float(r["n_year"]), "uspesnost": float(r["win"]), "prumer_proc_marze": float(r["e"]),
            "rocne": float(r["cagr"]), "propad": float(r["max_dd"]), "ziskovych_mesicne": float(r["wins_month"])}


def run_group(profile: str, pairs: list[str], shares: list[float]) -> dict:
    SL.PROFILE = SL.PROFILES[profile]
    cfg = copy.deepcopy(json.loads(SL.PROFILES[profile]["state"].read_text())["config"])
    cfg["pary"] = pairs
    lists = SL.trade_lists(cfg)
    spans = {label: _summary(SL.run_pf(lists, shares, years, cfg)) for label, years in SPANS.items()}
    per_pair = {}
    for pair in pairs:
        trades = [t for tl in lists for t in tl if t["pair"] == pair]
        x = [t["margin_pct"] for t in trades]
        per_pair[pair] = {"obchodu": len(x), "uspesnost": float(np.mean([v > 0 for v in x])) if x else None,
                          "prumer_proc_marze": float(np.mean(x)) if x else None,
                          "data_do": P.series(pair)["days"][-1].isoformat()}
    return {"obdobi": spans, "po_parech": per_pair, "obchodu_celkem": sum(len(tl) for tl in lists)}


def main() -> int:
    missing = [p for p in HU.PAIRS if not (HU.ROOT / f"{HU.code(p)}.npz").exists()]
    if missing:
        print(f"chybi data HistData pro {missing}: python scripts/histdata_universe.py download && ... build", file=sys.stderr)
        return 2
    started = time.monotonic()
    result = {"vytvoreno": date.today().isoformat(), "pary_histdata": list(HU.PAIRS), "profily": {}}
    for profile in SL.PROFILES:
        state = json.loads(SL.PROFILES[profile]["state"].read_text())
        shares = list(state["eval"]["1"]["shares"])                  # the champion's own margins, never re-fitted here
        live12 = SL.symbols_of({"universe": "12"})
        result["profily"][profile] = {"nazev": state["config"]["name"], "marze": shares,
                                      "hist16": run_group(profile, list(HU.PAIRS), shares),
                                      "zivych12": run_group(profile, live12, shares)}
        print(f"{profile}: {time.monotonic() - started:.0f} s", flush=True)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    OUT_DOC.write_text(render(result), encoding="utf-8")
    print(f"zapsano {OUT_DOC.relative_to(PROJECT_ROOT)}")
    return 0


def render(res: dict) -> str:
    lines = ["# Kontrola na 16 párech HistData (povinná, jen report)", "",
             f"_Vytvořeno {res['vytvoreno']} (`scripts/kontrola_histdata.py`). Šampion se stejnými maržemi jako dnes, žádné nové"
             " ladění ani výběr; není to kritérium brány. Data HistData jsou jen BID (ASK = BID, spread páru se přičítá na"
             " obou stranách), páka 1:20 pro nehlavní páry, data od 2026-10-01 jsou v trezoru. Pro srovnání jsou na stejných"
             " maržích i 12 živých párů._", ""]
    for profile, d in res["profily"].items():
        lines += [f"## Profil {profile}: {d['nazev']}", "", f"Marže šampiona (stupně): {d['marze']}", "",
                  "| období | skupina | obchodů / rok | úspěšnost | průměr (% marže) | ročně | propad | ziskových / měsíc |",
                  "|---|---|---|---|---|---|---|---|"]
        for label in SPANS:
            for grp, name in (("hist16", "16 HistData"), ("zivych12", "12 živých")):
                s = d[grp]["obdobi"][label]
                lines.append(f"| {label} | {name} | {s['obchodu_rocne']:.0f} | {s['uspesnost']:.0%} | "
                             f"{s['prumer_proc_marze']:+.1f} | {s['rocne']:+.1%} | {s['propad']:.0%} | {s['ziskovych_mesicne']:.1f} |")
        lines += ["", "Po párech (celé období, jen obchody šampiona):", "", "| pár | obchodů | úspěšnost | průměr (% marže) | data do |",
                  "|---|---|---|---|---|"]
        for pair, s in d["hist16"]["po_parech"].items():
            lines.append(f"| {pair} | {s['obchodu']} | " + ("-" if s["uspesnost"] is None else f"{s['uspesnost']:.0%}") + " | "
                         + ("-" if s["prumer_proc_marze"] is None else f"{s['prumer_proc_marze']:+.1f}") + f" | {s['data_do']} |")
        lines.append("")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
