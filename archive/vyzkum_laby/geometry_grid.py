"""Trade geometry grid: does another entry / stop-loss / take-profit / holding
time turn the model's direction into a profit? (modules 52-55, 74-77)

    python scripts/geometry_grid.py collect          # model decisions 2023-2026 (Dukascopy archive)
    python scripts/geometry_grid.py collect --fxcm   # model decisions 2016-2023 (FXCM research archive)
    python scripts/geometry_grid.py collect --early  # model decisions 2013-2016 (FXCM early archive)
    python scripts/geometry_grid.py grid             # 270 geometries x (model, technical only) -> docs/GEOMETRIE.md

The expensive part (the full technical + fundamental analysis at every H4
close) runs once per archive and stores each decision's direction; every
geometry then re-plays the same decisions on the hourly BID/ASK path:

    entry   MARKET (open of the next hour, ASK for BUY) or LIMIT k x ATR(H4)
            back against the direction, valid 24 h
    SL / TP s x ATR(H4) / p x ATR(H4) from the fill
    horizon 24 h, 72 h, 120 h (then closed at the hour close)

Costs: bid/ask of the path + 0.2 pip slippage per side + 0.5 pip markup.
SL and TP in the same hour count as SL (conservative, the same for the
model and its control). Every geometry is also played in the OPPOSITE
direction: edge = (model - opposite) / 2 = what the direction adds over a
random direction. Geometry is CHOSEN on 2016-09 .. 2021-12 and SHOWN on
2022-01 .. 2026-09 (never chosen there).
"""

import bisect
import math
import multiprocessing
import os
import pickle
import sys
from datetime import date, datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FXCM = "--fxcm" in sys.argv
EARLY = "--early" in sys.argv       # 2013-2016 (data/early_fxcm, hourly only)

if FXCM or EARLY:
    os.environ["DATA_DIR"] = "data/early_fxcm" if EARLY else "data/oos_fxcm"
    os.environ["FXBOT_CANONICAL_SOURCE"] = "fxcm"

sys.path.insert(0, str(PROJECT_ROOT))

from src.engine.backtest import BacktestConfig, run  # noqa: E402  (loads .env first)
from src.engine.data import load_pair  # noqa: E402
from src.engine.params import DEFAULT_PARAMS  # noqa: E402
from src.instruments import get_instrument, parse_symbols  # noqa: E402

UTC = timezone.utc
H = 3600
RESEARCH = PROJECT_ROOT / "data" / "research"
CHOOSE = (date(2016, 9, 1), date(2021, 12, 31))
SHOW = (date(2022, 1, 1), date(2026, 9, 30))
ENTRIES = (("MARKET", 0.0), ("LIMIT 0.25", 0.25), ("LIMIT 0.5", 0.5))
STOPS = (0.5, 1.0, 1.5, 2.0, 3.0)
TARGETS = (0.5, 1.0, 1.5, 2.0, 3.0, 4.0)
HORIZONS = (24, 72, 120)
SLIPPAGE_PIPS = 0.2
MARKUP_PIPS = 0.5


# ----------------------------------------------------------------------
# collect: model decisions once per archive
# ----------------------------------------------------------------------

def collect() -> None:
    RESEARCH.mkdir(parents=True, exist_ok=True)
    p = DEFAULT_PARAMS
    symbols = parse_symbols(None)
    pre = {s: load_pair(s, p) for s in symbols}
    available = [s for s in symbols if len(pre[s].h1) >= 500]
    start = min(pre[s].h1.ts[0] for s in available) + 120 * 86400
    end = max(pre[s].h1.ts[-1] for s in available)
    out = {"paths": {}, "variants": {}}

    for s in available:
        bars = pre[s].h1_bars
        out["paths"][s] = {"ts": [b.ts for b in bars], "bo": [b.bo for b in bars], "bh": [b.bh for b in bars],
                           "bl": [b.bl for b in bars], "bc": [b.bc for b in bars], "ao": [b.ao for b in bars],
                           "ah": [b.ah for b in bars], "al": [b.al for b in bars], "ac": [b.ac for b in bars]}

    for label, use_fundamentals in (("MODEL", True), ("TECHNIKA", False)):
        result = run(BacktestConfig(available, start, end, p, use_fundamentals=use_fundamentals, placebo_seed=None),
                     pre)
        decisions = []

        for trade in result.trades:
            series = pre[trade["symbol"]]
            i4 = series.h4.index_at(trade["t0"])
            decisions.append({k: trade[k] for k in ("symbol", "direction", "decision", "confidence",
                                                    "setup_type", "outcome_state", "r_net")}
                             | {"t": trade["t0"], "atr4": series.h4.atr14[i4] if i4 >= 0 else None})

        out["variants"][label] = {"decisions": decisions, "n_decisions": result.decisions,
                                  "no_trade_reasons": result.no_trade_reasons, "gate_failures": result.gate_failures}
        print(f"{label}: {result.decisions} rozhodnuti, {len(decisions)} obchodu se smerem", flush=True)

    name = "decisions_early.pkl" if EARLY else "decisions_fxcm.pkl" if FXCM else "decisions_dukascopy.pkl"
    (RESEARCH / name).write_bytes(pickle.dumps(out))
    print(f"ulozeno {RESEARCH / name}")


# ----------------------------------------------------------------------
# grid: re-play the decisions with other geometries
# ----------------------------------------------------------------------

_DATA: dict = {}


def simulate(path: dict, d: dict, direction: str, entry_k: float, stop: float, target: float, horizon: int,
             pip: float) -> float | None:
    """R multiple of one trade (None = limit not filled = no trade)."""
    a = d["atr4"]
    ts = path["ts"]
    j = bisect.bisect_left(ts, d["t"])

    if not a or j >= len(ts) or ts[j] - d["t"] > 4 * H:
        return None

    buy = direction == "BUY"
    sign = 1.0 if buy else -1.0
    slip = SLIPPAGE_PIPS * pip
    end_t = d["t"] + horizon * H
    mid0 = (path["bo"][j] + path["ao"][j]) / 2

    if entry_k == 0:
        entry = (path["ao"][j] if buy else path["bo"][j]) + sign * slip
        fill = j
    else:
        level = mid0 - sign * entry_k * a
        fill = None

        for k in range(j, len(ts)):
            if ts[k] >= d["t"] + 24 * H:
                break
            if (buy and path["al"][k] <= level) or (not buy and path["bh"][k] >= level):
                fill, entry = k, level
                break

        if fill is None:
            return None

    sl = entry - sign * stop * a
    tp = entry + sign * target * a
    risk = stop * a
    cost = MARKUP_PIPS * pip

    for k in range(fill, len(ts)):
        if ts[k] >= end_t:
            break

        low = path["bl"][k] if buy else path["al"][k]
        high = path["bh"][k] if buy else path["ah"][k]
        sl_hit = low <= sl if buy else high >= sl
        tp_hit = (high >= tp if buy else low <= tp) and not (k == fill and entry_k > 0)

        if sl_hit:                                   # incl. SL and TP in one hour (conservative)
            return (sign * (sl - entry) - slip - cost) / risk

        if tp_hit:
            return (sign * (tp - entry) - cost) / risk

    last = min(bisect.bisect_left(ts, end_t), len(ts)) - 1

    if last < fill:
        return None

    close = path["bc"][last] if buy else path["ac"][last]
    return (sign * (close - entry) - slip - cost) / risk


def _in(d: dict, period: tuple) -> bool:
    day = datetime.fromtimestamp(d["t"], tz=UTC).date()
    return period[0] <= day <= period[1]


def evaluate(job: tuple) -> dict:
    variant, entry, stop, target, horizon = job
    label, entry_k = entry
    rows = {"CHOOSE": [], "SHOW": []}

    for archive in _DATA.values():
        for d in archive["variants"][variant]["decisions"]:
            period = "CHOOSE" if _in(d, CHOOSE) else "SHOW" if _in(d, SHOW) else None

            if period is None or d["symbol"] not in archive["paths"]:
                continue

            pip = get_instrument(d["symbol"]).pip
            path = archive["paths"][d["symbol"]]
            opposite = "SELL" if d["direction"] == "BUY" else "BUY"
            rows[period].append((d, simulate(path, d, d["direction"], entry_k, stop, target, horizon, pip),
                                 simulate(path, d, opposite, entry_k, stop, target, horizon, pip)))

    return {"variant": variant, "entry": label, "stop": stop, "target": target, "horizon": horizon,
            **{period: _stats(r) for period, r in rows.items()}}


def _stats(rows: list) -> dict:
    trades = [m for _, m, _ in rows if m is not None]

    if len(trades) < 30:
        return {"n": len(rows), "trades": len(trades)}

    wins = sum(1 for r in trades if r > 0)
    gain = sum(r for r in trades if r > 0)
    loss = -sum(r for r in trades if r < 0)
    # paired edge per decision; its standard error is clustered by week
    # (trades of one week overlap and all pairs share the USD)
    pairs = [(d["t"] // (7 * 86400), ((m or 0.0) - (o or 0.0)) / 2) for d, m, o in rows]
    edge = sum(x for _, x in pairs) / len(pairs)
    sums: dict = {}

    for week, x in pairs:
        sums[week] = sums.get(week, 0.0) + (x - edge)

    se = math.sqrt(sum(v * v for v in sums.values())) / len(pairs)
    anti = [o for _, _, o in rows if o is not None]
    return {"n": len(rows), "trades": len(trades), "win": wins / len(trades), "e": sum(trades) / len(trades),
            "pf": gain / loss if loss else None, "edge": edge, "edge_t": edge / se if se else 0.0,
            "anti_trades": len(anti), "anti_win": sum(1 for r in anti if r > 0) / len(anti) if anti else None,
            "anti_e": sum(anti) / len(anti) if anti else None}


def grid() -> None:
    for name in ("decisions_fxcm.pkl", "decisions_dukascopy.pkl"):
        if (RESEARCH / name).exists():
            _DATA[name] = pickle.loads((RESEARCH / name).read_bytes())

    jobs = [(v, e, s, t, h) for v in ("MODEL", "TECHNIKA") for e in ENTRIES for s in STOPS for t in TARGETS
            for h in HORIZONS]

    with multiprocessing.get_context("fork").Pool(os.cpu_count() or 1) as pool:
        results = pool.map(evaluate, jobs, chunksize=4)

    (RESEARCH / "geometry_grid.pkl").write_bytes(pickle.dumps(results))
    report(results)


def _f(x, fmt="+.3f"):
    return "-" if x is None else format(x, fmt)


def report(results: list[dict]) -> None:
    model = [r for r in results if r["variant"] == "MODEL" and r["CHOOSE"].get("e") is not None]
    ranked = sorted(model, key=lambda r: -r["CHOOSE"]["e"])
    head = ("| vstup | SL [ATR H4] | TP [ATR H4] | drzeni | obchodu | uspesnych | E [R/obchod] | edge smeru vs nahoda "
            "(t) | obchodu | uspesnych | E [R/obchod] | edge smeru vs nahoda (t) |")
    sep = "|---|---|---|---|---|---|---|---|---|---|---|---|"

    def line(r):
        c, s = r["CHOOSE"], r["SHOW"]
        return (f"| {r['entry']} | {r['stop']} | {r['target']} | {r['horizon']} h | {c['trades']} | "
                f"{_f(c.get('win'), '.0%')} | {_f(c.get('e'))} | {_f(c.get('edge'))} ({_f(c.get('edge_t'), '+.1f')}) | "
                f"{s['trades']} | {_f(s.get('win'), '.0%')} | {_f(s.get('e'))} | "
                f"{_f(s.get('edge'))} ({_f(s.get('edge_t'), '+.1f')}) |")

    out = ["# Geometrie obchodu: vstup, SL, TP, doba drzeni", "",
           f"_{len(results)} kombinaci; vyber na 2016-09 .. 2021-12 (FXCM), kontrola na 2022-01 .. 2026-09 "
           "(FXCM + Dukascopy). R = zisk / riziko do SL po nakladech. Uspesny = obchod se ziskem. "
           "edge = o kolik R na rozhodnuti je smer modelu lepsi nez opacny smer / 2 (nahodny smer = 0)._", "",
           "## 10 nejlepsich nastaveni podle obdobi vyberu - a co udelala potom", "",
           "| | | | | **2016-2021 (vyber)** | | | | **2022-2026 (kontrola)** | | | |", head, sep]
    out += [line(r) for r in ranked[:10]]
    best = ranked[0]
    out += ["", "## Uspesnost vs. vysledek (vstup MARKET, drzeni 72 h, 2016-2021)", "",
            "Ukazuje, ze procento uspesnych obchodu urcuje hlavne pomer SL/TP, ne kvalita predikce.", "",
            "| SL \\ TP | " + " | ".join(f"TP {t}" for t in TARGETS) + " |", "|---|" + "---|" * len(TARGETS)]

    for s in STOPS:
        cells = []
        for t in TARGETS:
            r = next(x for x in results if x["variant"] == "MODEL" and x["entry"] == "MARKET" and x["stop"] == s
                     and x["target"] == t and x["horizon"] == 72)["CHOOSE"]
            cells.append(f"{_f(r.get('win'), '.0%')} / {_f(r.get('e'), '+.2f')}R")
        out.append(f"| SL {s} | " + " | ".join(cells) + " |")

    edges = lambda variant, period: [r[period]["edge"] for r in results
                                     if r["variant"] == variant and r[period].get("edge") is not None]
    out += ["", "## Technika samotna vs. technika + fundamenty (prumer pres vsech 270 nastaveni)", "",
            "| smer z | edge 2016-2021 | edge 2022-2026 |", "|---|---|---|"]

    for variant, label in (("MODEL", "model (technika + fundamentalni veto)"), ("TECHNIKA", "jen technika")):
        a, b = edges(variant, "CHOOSE"), edges(variant, "SHOW")
        out.append(f"| {label} | {sum(a) / len(a):+.4f} R | {sum(b) / len(b):+.4f} R |")

    positive = sum(1 for r in model if r["CHOOSE"]["e"] > 0)
    still = sum(1 for r in model if r["CHOOSE"]["e"] > 0 and (r["SHOW"].get("e") or -1) > 0)
    out += ["", f"Kladny vysledek na obdobi vyberu: {positive} z {len(model)} nastaveni; z nich kladny i na kontrole: "
            f"{still}.", f"Nejlepsi nastaveni z vyberu: {best['entry']}, SL {best['stop']}, TP {best['target']}, "
            f"{best['horizon']} h -> kontrola E {_f(best['SHOW'].get('e'))} R, "
            f"uspesnost {_f(best['SHOW'].get('win'), '.0%')}."]
    (PROJECT_ROOT / "docs" / "GEOMETRIE.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("collect", "grid"):
        print(__doc__)
        return 1

    collect() if argv[0] == "collect" else grid()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
