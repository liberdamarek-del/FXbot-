"""How do the champion's trades do around news? (descriptive, no selection)

    python scripts/zpravy_lab.py        # -> docs/ZPRAVY.md

Every trade of the live champion (learning/champion_12_mesicne.json, all
tiers, 12 pairs, hourly path 2012-2026 with costs and swap) is tagged by the
news around its decision day (scripts/fundamenty.py): a scheduled central
bank decision of either currency in the decision week / in the next 7 or 14
days, a US NFP or CPI release in the decision week (USD pairs), a news-like
shock (an hour of the last two days moving > 0.5 / 0.75 ATR). Win rate and
average result per group and period. Descriptive only: a filter enters the
model only through the walk-forward gate (scripts/self_learn.py).
"""

import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import profit_deep as D  # noqa: E402
from src.instruments import DEFAULT_ACTIVE  # noqa: E402

PERIODS = {"2012-18": (2012, 2018), "2019-22": (2019, 2022), "2023-26": (2023, 2026)}


def stats(trades) -> str:
    if not trades:
        return "0 | - | -"
    x = np.array([t["margin_pct"] for t in trades])
    return f"{len(x)} | {np.mean(x > 0):.0%} | {x.mean():+.1f} %"


def main() -> int:
    cfg = json.loads((PROJECT_ROOT / "learning" / "champion_12_mesicne.json").read_text())["config"]
    pairs = list(DEFAULT_ACTIVE)
    trades = []
    for k, tier in enumerate(cfg["tiers"]):
        rule = replace(D.Rule("t"), **{**cfg["base"], **tier})
        for t in D.simulate(rule, pairs):
            t["tier"] = k
            trades.append(t)
    for t in trades:
        s, I = D.prepared(t["pair"], 2, 3, 0, "oecd")
        i = s["days"].index(t["day"])
        t["cb_week"] = bool(D.news(t["pair"], s, I, "cb_week")[i])
        t["cb_7"] = bool(D.news(t["pair"], s, I, "cb_ahead:7")[i])
        t["cb_14"] = bool(D.news(t["pair"], s, I, "cb_ahead:14")[i])
        t["us_data"] = bool(D.news(t["pair"], s, I, "us_data")[i])
        t["jump"] = float(D.news(t["pair"], s, I, "jump")[i])
    groups = [
        ("vsechny obchody", lambda t: True),
        ("centralni banka rozhodovala v tydnu vstupu", lambda t: t["cb_week"]),
        ("... nerozhodovala", lambda t: not t["cb_week"]),
        ("centralni banka rozhodne do 7 dni po vstupu", lambda t: t["cb_7"]),
        ("... nerozhodne do 7 dni", lambda t: not t["cb_7"]),
        ("centralni banka rozhodne do 14 dni po vstupu", lambda t: t["cb_14"]),
        ("USD par, v tydnu vstupu vysly NFP nebo CPI", lambda t: t["us_data"]),
        ("USD par, bez NFP / CPI v tydnu", lambda t: "USD" in t["pair"] and not t["us_data"]),
        ("zpravovy skok > 0.5 ATR za hodinu (posledni 2 dny)", lambda t: t["jump"] > 0.5),
        ("bez skoku (<= 0.5 ATR)", lambda t: t["jump"] <= 0.5),
        ("zpravovy skok > 0.75 ATR", lambda t: t["jump"] > 0.75),
    ]
    out = ["# Obchody modelu a zpravy", "",
           f"_Sampion {cfg['name']}, vsechny stupne, 12 paru, hodinova data 2012-2026 s naklady a swapem; "
           f"{len(trades)} obchodu. Zdroje terminu: scripts/fundamenty.py (Fed, ECB, BoJ, BoE od 2012; u BoE chybi "
           "8/2015-12/2016; US NFP a CPI z ALFRED). Bunka = obchodu | uspesnost | prumer % marze. Jen popis - "
           "do modelu se filtr dostane jen pres testovaci branu._", "",
           "| skupina | " + " | ".join(PERIODS) + " |", "|---|" + "---|" * len(PERIODS)]
    for name, f in groups:
        sel = [t for t in trades if f(t)]
        out.append(f"| {name} | " + " | ".join(stats([t for t in sel if a <= t["day"].year <= b])
                                               for a, b in PERIODS.values()) + " |")
    text = "\n".join(out) + "\n"
    (PROJECT_ROOT / "docs" / "ZPRAVY.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
