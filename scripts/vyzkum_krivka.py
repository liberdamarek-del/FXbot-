"""Research (2026-10-11, autonomous run): does the RELATIVE YIELD CURVE predict the 12 pairs?

Chen & Tsang (2013, Review of Economics and Statistics, "What does the yield curve tell us about exchange rate
predictability?"): the difference between two countries' yield curves (level, slope, curvature) predicts the
exchange rate 1-24 months ahead; a relatively steeper home curve is followed by a weaker home currency. The project
uses only the SHORT end (3-month rates, their 3-month change). This script asks two questions, separately for
2012-2018 (selection) and 2019-2026 (test), without look-ahead (monthly OECD data with the model's 2-month lag):

  A) monthly prediction: rank correlation of the relative slope / long-rate differential / their 3-month changes
     with the next 1 and 3 months of each pair (spot, FXCM New York closes), and the information beyond the
     short-rate change the model already uses (pooled OLS with both);
  B) the champion's own trades: do trades where the relative curve agrees with the trade earn more than trades
     where it disagrees - in both periods?

Data: FRED IRLTLT01xxM156N (OECD long-term government bond yields, monthly average; EUR = Germany) + the model's 3-month rates
(profit_lab2.monthly_rates). Output: docs/VYZKUM_KRIVKA.md. Information only - a finding reaches the model only
as a gate experiment.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import profit_lab2 as P  # noqa: E402
import research_factors as RF  # noqa: E402
from signals_live import fetch  # noqa: E402
from src.instruments import DEFAULT_ACTIVE, get_instrument  # noqa: E402

LONG_IDS = P.LONG_IDS          # OECD 10y yields; EUR = Germany (the euro area series lags by months)
LAG = 2                       # months, as the model's rates (OECD monthly averages are published with a delay)
WINDOW = 3                    # months of change, as the model's rate momentum
PERIODS = {"2012-18": (2012, 2018), "2019-26": (2019, 2026)}
OUT = PROJECT_ROOT / "docs" / "VYZKUM_KRIVKA.md"


def download() -> None:
    RF.FRED_DIR.mkdir(parents=True, exist_ok=True)
    for sid in LONG_IDS.values():
        _, content, _ = fetch(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}", retries=3)
        if content.startswith(b"observation_date"):
            (RF.FRED_DIR / f"{sid}.csv").write_bytes(content)


def long_rates() -> dict:
    return P.monthly_long_rates()


def signals(pair: str, y: int, m: int, short: dict, long_: dict) -> dict | None:
    """Relative curve of base minus quote known at the end of month (y, m)."""
    inst = get_instrument(pair)

    def at(lag):
        v = {}
        for c in (inst.base, inst.quote):
            s, l_ = P.rate_at(short[c], y, m, lag), P.rate_at(long_[c], y, m, lag)
            if s is None or l_ is None:
                return None
            v[c] = (s, l_)
        (sb, lb), (sq, lq) = v[inst.base], v[inst.quote]
        return {"short": sb - sq, "long": lb - lq, "slope": (lb - sb) - (lq - sq)}
    now, old = at(LAG), at(LAG + WINDOW)
    if now is None or old is None:
        return None
    return {**now, **{f"d_{k}": now[k] - old[k] for k in now}}


def month_closes(pair: str) -> dict:
    s = P.series(pair)
    out = {}
    for d, c in zip(s["days"], s["dc"]):
        out[(d.year, d.month)] = float(c)                  # the last New York close of the month
    return out


def spearman(x, y) -> float:
    if len(x) < 10:
        return float("nan")
    rx, ry = np.argsort(np.argsort(x)), np.argsort(np.argsort(y))
    return float(np.corrcoef(rx, ry)[0, 1])


def ols_t(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    X = np.column_stack([np.ones(len(y)), X])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    s2 = resid @ resid / max(1, len(y) - X.shape[1])
    cov = s2 * np.linalg.inv(X.T @ X)
    return beta[1:] / np.sqrt(np.diag(cov)[1:])


def part_a(short, long_) -> list[str]:
    rows = []
    for pair in DEFAULT_ACTIVE:
        mc = month_closes(pair)
        keys = sorted(mc)
        for i, (y, m) in enumerate(keys[:-3]):
            sig = signals(pair, y, m, short, long_)
            if sig is None:
                continue
            r1 = np.log(mc[keys[i + 1]] / mc[(y, m)]) * 100
            r3 = np.log(mc[keys[i + 3]] / mc[(y, m)]) * 100
            rows.append({"pair": pair, "y": y, **sig, "r1": r1, "r3": r3})
    out = ["## A) Předpověď na další 1 a 3 měsíce (všech 12 párů dohromady, měsíčně)", "",
           "Spearmanova korelace signálu s budoucím pohybem páru (kladná = signál ukazuje směr; |0,05| je u tohoto "
           "počtu měsíců na hranici náhody). `slope` = sklon křivky základní měny minus kótovací (10 let − 3 měsíce), "
           "`long` = rozdíl 10letých výnosů, `short` = rozdíl 3měsíčních sazeb (carry), `d_` = změna za 3 měsíce "
           "(`d_short` je to, co model už používá).", "",
           "| signál | období | měsíců | korelace 1 m | korelace 3 m | t navíc k d_short (1 m) |", "|---|---|---|---|---|---|"]
    for k in ("slope", "d_slope", "long", "d_long", "short", "d_short"):
        for name, (a, b) in PERIODS.items():
            sel = [r for r in rows if a <= r["y"] <= b]
            x = np.array([r[k] for r in sel])
            r1, r3 = np.array([r["r1"] for r in sel]), np.array([r["r3"] for r in sel])
            extra = "–" if k == "d_short" else f"{ols_t(np.column_stack([x, [r['d_short'] for r in sel]]), r1)[0]:+.2f}"
            out.append(f"| {k} | {name} | {len(sel)} | {spearman(x, r1):+.3f} | {spearman(x, r3):+.3f} | {extra} |")
    return out


def part_b(short, long_) -> list[str]:
    import self_learn as SLN
    seen = {}
    for prof in ("champion_12.json", "champion_12_mesicne.json"):
        cfg = json.loads((PROJECT_ROOT / "learning" / prof).read_text())["config"]
        for tier, tl in enumerate(SLN.trade_lists(cfg)):
            for t in tl:
                key = (prof, t["pair"], t["day"], t["side"])
                if key not in seen or tier < seen[key][0]:
                    seen[key] = (tier, t)
    out = ["", "## B) Obchody šampionů: pomáhá shoda s relativní křivkou?", "",
           "Obchod „souhlasí“, když signál ukazuje směrem obchodu (pro `slope` podle Chen & Tsang obráceně: strmější "
           "křivka základní měny = slabší základní měna). Výsledek = pohyb ceny v % ve směru obchodu po nákladech; "
           "úspěšnost = podíl ziskových obchodů.", "",
           "| profil | signál | období | souhlasí: obchodů / úspěšnost / průměr % | nesouhlasí: obchodů / úspěšnost / průměr % |",
           "|---|---|---|---|---|"]
    periods = {"2012-18": (2012, 2018), "2019-22": (2019, 2022), "2023-26": (2023, 2026)}
    for prof in ("champion_12.json", "champion_12_mesicne.json"):
        trades = [(tier, t) for (p, *_), (tier, t) in seen.items() if p == prof]
        for k, sign in (("slope", -1), ("d_slope", -1), ("d_long", 1), ("long", 1)):
            for name, (a, b) in periods.items():
                agg = defaultdict(list)
                for tier, t in trades:
                    d = t["day"]
                    if not a <= d.year <= b:
                        continue
                    sig = signals(t["pair"], d.year, d.month, short, long_)
                    if sig is None or sig[k] == 0:
                        continue
                    agg[sign * sig[k] * t["side"] > 0].append(float(t["price_pct"]))

                def cell(v):
                    v = np.array(v)
                    return f"{len(v)} / {np.mean(v > 0) * 100:.0f} % / {np.mean(v):+.2f}" if len(v) else "–"
                out.append(f"| {prof.replace('.json', '')} | {k} | {name} | {cell(agg[True])} | {cell(agg[False])} |")
    return out


def main(argv: list[str]) -> int:
    if "--bez-stazeni" not in argv:
        download()
    short, long_ = P.monthly_rates(), long_rates()
    for c, s in long_.items():
        print(c, min(s), max(s), len(s))
    lines = ["# Relativní výnosová křivka a 12 párů (výzkum 2026-10-11)", "",
             "_Autonomní průzkum. Hypotéza z literatury: Chen & Tsang (2013, Review of Economics and Statistics). "
             "Data: OECD dlouhodobé výnosy (FRED IRLTLT01, měsíčně) a 3měsíční sazby modelu, zpoždění 2 měsíce jako "
             "v modelu; ceny FXCM. 2012–18 = výběr, 2019–26 = test. Jen informace – do modelu jen přes bránu._", ""]
    lines += part_a(short, long_)
    lines += part_b(short, long_)
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
