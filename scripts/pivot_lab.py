"""Pivot lab: the user's method - classic pivot points + simple moving
average 50 on the daily / weekly chart - tested in many settings.

    python scripts/pivot_lab.py test     # all variants -> docs/PIVOTY.md (~3 min)

Rules (one position per pair and variant, decided at the daily close, run on
the hourly BID/ASK path, held at most 1 or 5 trading days):

    pivots  classic from the previous DAY / WEEK / MONTH (mid H, L, C):
            P = (H+L+C)/3, R1 = 2P-L, S1 = 2P-H, R2 = P+(H-L), S2 = P-(H-L)
    filter  NONE | D1: close vs SMA50 daily | W1: close vs SMA50 weekly |
            D1+W1 both | PIVOT: close vs the pivot P | and each one REVERSED
            (the control: the same trades with the trend read the other way)
    entry   BOUNCE_P   long: limit at P (price above P),  SL S1, TP R1
            BOUNCE_S1  long: limit at S1 (price above S1), SL S2, TP P
            BREAK_R1   long: stop at R1 (price below R1),  SL P,  TP R2
            MARKET     long: next open when price above P, SL S1, TP R1
            (short = mirrored; entry window 1 day for daily pivots, 5 days otherwise)

Costs: bid/ask of the path + 0.2 pip slippage per side + 0.5 pip markup; SL
and TP in the same hour count as SL. R = result / risk to SL.

Protocol: variants are RANKED on 2016-09 .. 2021-12 only; the report then
shows what the best of them did on 2014-01 .. 2016-08 and 2022-01 .. 2026-09.
"""

import math
import multiprocessing
import os
import pickle
import sqlite3
import sys
from datetime import date, datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from research_signals import ARCHIVES, DUKASCOPY_FROM, stitched_daily  # noqa: E402
from src.instruments import get_instrument, parse_symbols  # noqa: E402
from src.path_archive import trading_date  # noqa: E402

UTC = timezone.utc
H = 3600
PERIODS = {"EARLY": (date(2014, 1, 1), date(2016, 8, 31)), "CHOOSE": (date(2016, 9, 1), date(2021, 12, 31)),
           "HOLDOUT": (date(2022, 1, 1), date(2026, 9, 30))}
FILTERS = ("NONE", "D1", "W1", "D1+W1", "PIVOT")
ENTRIES = ("BOUNCE_P", "BOUNCE_S1", "BREAK_R1", "MARKET")
PIVOTS = ("DAY", "WEEK", "MONTH")
HOLDS = (1, 5)
SLIPPAGE_PIPS = 0.2
MARKUP_PIPS = 0.5
SMA = 50


def _hourly(db: Path, symbol: str, sources: tuple) -> dict:
    if not db.exists():
        return {}

    connection = sqlite3.connect(db)
    marks = ",".join("?" * len(sources))

    try:
        rows = connection.execute(
            f"SELECT ts, bo, bh, bl, bc, ao, ah, al, ac, source_id FROM market_path WHERE instrument = ? "
            f"AND timeframe = '1h' AND source_id IN ({marks}) ORDER BY ts", (symbol, *sources)).fetchall()
    finally:
        connection.close()

    out = {}

    for row in rows:                       # later sources in `sources` win on the same hour
        if row[0] not in out or sources.index(row[9]) > sources.index(out[row[0]][9]):
            out[row[0]] = row

    return out


def load(symbol: str) -> dict:
    daily, _ = stitched_daily(symbol)
    early = _hourly(ARCHIVES["early"], symbol, ("FXCM_H1",))
    oos = _hourly(ARCHIVES["oos"], symbol, ("FXCM_H1",))
    duka = _hourly(ARCHIVES["main"], symbol, ("DUKASCOPY_H1", "DUKASCOPY_M1"))
    first_oos = min(oos) if oos else DUKASCOPY_FROM
    hours = {**{k: v for k, v in early.items() if k < first_oos}, **{k: v for k, v in oos.items() if k < DUKASCOPY_FROM},
             **{k: v for k, v in duka.items() if k >= DUKASCOPY_FROM}}
    ts = sorted(hours)
    path = {name: [hours[t][k] for t in ts] for k, name in enumerate(("ts", "bo", "bh", "bl", "bc", "ao", "ah", "al",
                                                                        "ac"))}
    days = [{"ts": b.ts, "close_t": b.ts + 86400, "date": trading_date(b.ts), "o": b.mo, "h": b.mh, "l": b.ml,
             "c": b.mc} for b in daily]
    return {"symbol": symbol, "path": path, "days": days}


def _periods(days: list[dict]) -> dict:
    """HLC per period key and the key of each day for DAY / WEEK / MONTH."""
    keyfn = {"DAY": lambda d: d["date"], "WEEK": lambda d: tuple(d["date"].isocalendar()[:2]),
             "MONTH": lambda d: (d["date"].year, d["date"].month)}
    out = {}

    for name, fn in keyfn.items():
        hlc, order = {}, []

        for d in days:
            k = fn(d)
            if k not in hlc:
                hlc[k] = [d["h"], d["l"], d["c"]]
                order.append(k)
            else:
                hlc[k][0], hlc[k][1], hlc[k][2] = max(hlc[k][0], d["h"]), min(hlc[k][1], d["l"]), d["c"]

        previous = {order[i]: order[i - 1] for i in range(1, len(order))}
        out[name] = ([fn(d) for d in days], hlc, previous)

    return out


def pivots(h: float, l: float, c: float) -> dict:
    p = (h + l + c) / 3
    return {"P": p, "R1": 2 * p - l, "S1": 2 * p - h, "R2": p + (h - l), "S2": p - (h - l)}


def prepare(data: dict) -> dict:
    """Per day i (decision at its close): pivots valid for day i+1, SMA trends."""
    days = data["days"]
    per = _periods(days)
    closes = [d["c"] for d in days]
    week_keys = per["WEEK"][0]
    weekly_close, week_order = {}, []

    for d, k in zip(days, week_keys):
        if k not in weekly_close:
            week_order.append(k)
        weekly_close[k] = d["c"]

    rows = []

    for i in range(len(days) - 1):
        row = {"i": i, "t": days[i]["close_t"], "date": days[i]["date"], "close": closes[i]}

        for name, (keys, hlc, previous) in per.items():
            prev = previous.get(keys[i + 1])
            row[name] = pivots(*hlc[prev]) if prev is not None and prev != keys[i + 1] else None

        row["d1"] = None if i < SMA else (1 if closes[i] > sum(closes[i - SMA + 1:i + 1]) / SMA else -1)
        wk = week_order.index(week_keys[i]) if i == 0 or week_keys[i] != week_keys[i - 1] else row_wk
        row_wk = wk
        done = [weekly_close[k] for k in week_order[max(0, wk - SMA + 1):wk]]
        row["w1"] = None if len(done) < SMA - 1 else (1 if closes[i] > (sum(done) + closes[i]) / SMA else -1)
        rows.append(row)

    return rows


def direction(row: dict, flt: str, pivot: dict) -> int | None:
    """+1 long only, -1 short only, 0 both, None no trade."""
    base = flt.replace("~", "")
    value = {"NONE": 0, "D1": row["d1"], "W1": row["w1"],
             "D1+W1": row["d1"] if row["d1"] is not None and row["d1"] == row["w1"] else None,
             "PIVOT": 1 if row["close"] > pivot["P"] else -1}[base]

    if value is None:
        return None

    return -value if flt.startswith("~") else value


def plan(row: dict, entry: str, side: int, pv: dict):
    """(kind, level, stop, target) for one side or None."""
    c = row["close"]
    P, R1, S1, R2, S2 = pv["P"], pv["R1"], pv["S1"], pv["R2"], pv["S2"]
    # mirrored names for shorts: support <-> resistance
    lvl = {"P": P, "S1": S1 if side > 0 else R1, "S2": S2 if side > 0 else R2,
           "R1": R1 if side > 0 else S1, "R2": R2 if side > 0 else S2}
    above = lambda x: (c > x) if side > 0 else (c < x)

    if entry == "BOUNCE_P" and above(lvl["P"]):
        return "LIMIT", lvl["P"], lvl["S1"], lvl["R1"]
    if entry == "BOUNCE_S1" and above(lvl["S1"]):
        return "LIMIT", lvl["S1"], lvl["S2"], lvl["P"]
    if entry == "BREAK_R1" and not above(lvl["R1"]):
        return "STOP", lvl["R1"], lvl["P"], lvl["R2"]
    if entry == "MARKET" and above(lvl["P"]):
        return "MARKET", None, lvl["S1"], lvl["R1"]
    return None


def simulate(path: dict, start: int, side: int, kind: str, level, stop: float, target: float, window_h: int,
             hold_h: int, pip: float):
    """(R, exit_ts) or None when not filled."""
    import bisect

    ts = path["ts"]
    j = bisect.bisect_left(ts, start)
    buy = side > 0
    slip, cost = SLIPPAGE_PIPS * pip, MARKUP_PIPS * pip

    if j >= len(ts) or ts[j] - start > 4 * 86400:
        return None

    fill = entry = None

    if kind == "MARKET":
        fill, entry = j, (path["ao"][j] + slip if buy else path["bo"][j] - slip)
    else:
        for k in range(j, len(ts)):
            if ts[k] >= start + window_h * H:
                break
            if kind == "LIMIT" and ((buy and path["al"][k] <= level) or (not buy and path["bh"][k] >= level)):
                fill, entry = k, level
                break
            if kind == "STOP" and ((buy and path["ah"][k] >= level) or (not buy and path["bl"][k] <= level)):
                fill, entry = k, level + (slip if buy else -slip)
                break

    if fill is None:
        return None

    sign = 1 if buy else -1
    risk = sign * (entry - stop)

    if risk <= 0 or sign * (target - entry) <= 0:
        return None

    end = ts[fill] + hold_h * H

    for k in range(fill, len(ts)):
        if ts[k] >= end:
            break

        low = path["bl"][k] if buy else path["al"][k]
        high = path["bh"][k] if buy else path["ah"][k]
        sl_hit = low <= stop if buy else high >= stop
        tp_hit = (high >= target if buy else low <= target) and not (k == fill and kind != "MARKET")

        if sl_hit:
            return (sign * (stop - entry) - slip - cost) / risk, ts[k]
        if tp_hit:
            return (sign * (target - entry) - cost) / risk, ts[k]

    last = max(fill, min(len(ts), bisect.bisect_left(ts, end)) - 1)
    close = path["bc"][last] if buy else path["ac"][last]
    return (sign * (close - entry) - slip - cost) / risk, ts[last]


_PAIRS: list = []


def run_variant(variant: tuple) -> dict:
    flt, entry, pivot_name, hold = variant
    trades = []

    for pair in _PAIRS:
        pip = get_instrument(pair["symbol"]).pip
        busy_until = 0

        for row in pair["rows"]:
            pv = row[pivot_name]

            if pv is None or row["t"] < busy_until:
                continue

            side_rule = direction(row, flt, pv)

            if side_rule is None:
                continue

            for side in ((1, -1) if side_rule == 0 else (side_rule,)):
                p = plan(row, entry, side, pv)

                if p is None:
                    continue

                window = 24 if pivot_name == "DAY" else 5 * 24
                result = simulate(pair["path"], row["t"], side, p[0], p[1], p[2], p[3], window, hold * 24,
                                  pip)

                if result is not None:
                    trades.append((pair["symbol"], row["date"], side, result[0]))
                    busy_until = max(busy_until, result[1])
                    break

    return {"variant": variant, **{name: _stats([t for t in trades if per[0] <= t[1] <= per[1]])
                                   for name, per in PERIODS.items()}}


def _stats(trades: list) -> dict:
    if len(trades) < 30:
        return {"n": len(trades)}

    r = [t[3] for t in trades]
    mean = sum(r) / len(r)
    weeks: dict = {}

    for t in trades:
        k = tuple(t[1].isocalendar()[:2])
        weeks[k] = weeks.get(k, 0.0) + (t[3] - mean)

    se = math.sqrt(sum(v * v for v in weeks.values())) / len(r)
    gain, loss = sum(x for x in r if x > 0), -sum(x for x in r if x < 0)
    return {"n": len(r), "win": sum(1 for x in r if x > 0) / len(r), "e": mean, "t": mean / se if se else 0.0,
            "pf": gain / loss if loss else None, "total": sum(r)}


def _f(x, fmt="+.3f"):
    return "-" if x is None else format(x, fmt)


def test() -> None:
    global _PAIRS
    for symbol in parse_symbols(None):
        data = load(symbol)
        _PAIRS.append({"symbol": symbol, "path": data["path"], "rows": prepare(data)})
        print(f"{symbol}: {len(data['days'])} dni, {len(data['path']['ts'])} hodin", flush=True)

    filters = FILTERS + tuple("~" + f for f in FILTERS if f != "NONE")
    variants = [(f, e, p, h) for f in filters for e in ENTRIES for p in PIVOTS for h in HOLDS]

    with multiprocessing.get_context("fork").Pool(os.cpu_count() or 1) as pool:
        results = pool.map(run_variant, variants, chunksize=2)

    (PROJECT_ROOT / "data" / "research" / "pivot_lab.pkl").write_bytes(pickle.dumps(results))
    report(results)


def report(results: list) -> None:
    normal = [r for r in results if not r["variant"][0].startswith("~") and r["CHOOSE"].get("e") is not None
              and r["CHOOSE"]["n"] >= 100]
    ranked = sorted(normal, key=lambda r: -r["CHOOSE"]["e"])
    name = lambda v: f"{v[0]} / {v[1]} / pivot {v[2]} / max {v[3]} d"
    cell = lambda s: (f"{s.get('n', 0)} | {_f(s.get('win'), '.0%')} | {_f(s.get('e'), '+.3f')} | "
                      f"{_f(s.get('t'), '+.1f')}")
    out = ["# Pivoty + SMA 50: test vasi metody", "",
           f"_{len(results)} variant (vcetne kontrolnich s obracenym trendem); poradi jen podle 2016-09..2021-12; "
           "R = zisk / riziko do SL po nakladech; t = jistota (nad ~2 neni nahoda)._", "",
           "## 15 nejlepsich podle obdobi vyberu - a jak dopadly v jinych letech", "",
           "| varianta (filtr / vstup / pivot / drzeni) | 2016-21 obchodu | uspesnych | E [R] | t | 2014-16 obchodu | "
           "uspesnych | E [R] | t | 2022-26 obchodu | uspesnych | E [R] | t |", "|---|" + "---|" * 12]

    for r in ranked[:15]:
        out.append(f"| {name(r['variant'])} | {cell(r['CHOOSE'])} | {cell(r['EARLY'])} | {cell(r['HOLDOUT'])} |")

    robust = [r for r in normal if all((r[p].get("e") or -1) > 0 for p in PERIODS)]
    out += ["", f"Kladne ve vsech trech obdobich: **{len(robust)} z {len(normal)}** variant"
            + (": " + "; ".join(f"{name(r['variant'])} (E {r['CHOOSE']['e']:+.3f} / {r['EARLY']['e']:+.3f} / "
                                f"{r['HOLDOUT']['e']:+.3f})" for r in robust[:8]) if robust else "") + "."]
    out += ["", "## Pomaha trendovy filtr SMA 50? (prumer E pres vstupy, pivoty a drzeni)", "",
            "| filtr | 2014-16 | 2016-21 | 2022-26 | s obracenym trendem 2016-21 |", "|---|---|---|---|---|"]

    for flt in FILTERS:
        row = [flt]

        for f in (flt, "~" + flt):
            if f == "~NONE":
                continue
            for p in (PERIODS if f == flt else ("CHOOSE",)):
                es = [r[p]["e"] for r in results if r["variant"][0] == f and r[p].get("e") is not None]
                row.append(f"{sum(es) / len(es):+.3f} R" if es else "-")

        out.append("| " + " | ".join(row + (["-"] if flt == "NONE" else [])) + " |")

    out += ["", "## Podle typu vstupu (prumer, 2016-21 / 2022-26)", "", "| vstup | 2016-21 | 2022-26 | uspesnych 2016-21 |",
            "|---|---|---|---|"]

    for entry in ENTRIES:
        sel = [r for r in normal if r["variant"][1] == entry]
        a = [r["CHOOSE"]["e"] for r in sel]
        b = [r["HOLDOUT"]["e"] for r in sel if r["HOLDOUT"].get("e") is not None]
        w = [r["CHOOSE"]["win"] for r in sel]
        out.append(f"| {entry} | {sum(a) / len(a):+.3f} R | {sum(b) / len(b):+.3f} R | {sum(w) / len(w):.0%} |")

    (PROJECT_ROOT / "docs" / "PIVOTY.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test()
    else:
        print(__doc__)
