"""Trader's review of the champion's trades: what did the losers have in common
at the entry? Features known at the Friday close, split into terciles, win rate
and average result per period (2012-18, 2019-22, 2023-26). A feature counts only
when the same tercile is better / worse in all three periods.

    python scripts/obchodnik_lab.py [--profile mesicne|max]

Research only: nothing here changes the model; consistent findings become
experiments for the walk-forward gate (scripts/self_learn.py).
"""

import json
import sys
from bisect import bisect_right
from datetime import date
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import fundamenty as F  # noqa: E402
import profit_deep as D  # noqa: E402
import self_learn as SLN  # noqa: E402
import vyzkum_data as V  # noqa: E402
from src.instruments import get_instrument  # noqa: E402

PERIODS = (("2012-18", 2012, 2018), ("2019-22", 2019, 2022), ("2023-26", 2023, 2026))


def yield_diff(pair: str, days: list) -> np.ndarray:
    """2y yield difference base - quote (GBP 5y) at the close of the previous day (known at the decision)."""
    ylds = D._cache.setdefault("ylds", V.yields())
    inst = get_instrument(pair)
    if inst.base not in ylds or inst.quote not in ylds:
        return np.full(len(days), np.nan)
    out = []
    for d in days:
        vals = []
        for c in (inst.base, inst.quote):
            keys = D._cache.setdefault(("ykeys", c), sorted(ylds[c]))
            k = bisect_right(keys, d) - 1                     # strictly before the decision day
            while k >= 0 and keys[k] >= d:
                k -= 1
            vals.append(ylds[c][keys[k]] if k >= 0 and (d - keys[k]).days <= 5 else np.nan)
        out.append(vals[0] - vals[1])
    return np.array(out)


def features(t: dict, tier: int) -> dict:
    pair, side = t["pair"], t["side"]
    s, I = D.prepared(pair, 2, 3)
    i = s["days"].index(t["day"])
    c, h, l, atr = s["dc"], s["dh"], s["dl"], I["atr"][i]
    key = ("ydiff", pair)
    if key not in D._cache:
        D._cache[key] = yield_diff(pair, s["days"])
    yd = D._cache[key]
    ev = F.load_events()
    inst = get_instrument(pair)
    banks = [F.CB_OF[x] for x in (inst.base, inst.quote) if x in F.CB_OF]
    nxt = min((date.fromisoformat(d) for b in banks for d in ev.get(b, []) if d > t["day"].isoformat()),
              default=None)
    prev = [date.fromisoformat(d) for b in banks for d in ev.get(b, []) if d <= t["day"].isoformat()]
    down = 0
    while i - down - 1 >= 0 and side * (c[i - down] - c[i - down - 1]) < 0:
        down += 1
    rng = h[i] - l[i]
    sma200 = np.mean(c[i - 199:i + 1])
    atr250 = np.nanmedian(I["atr"][i - 250:i])
    return {
        "tier": tier,
        "rsi2": I["rsi2"][i] if side > 0 else 100 - I["rsi2"][i],
        "pokles_1d_atr": side * (c[i] - c[i - 1]) / atr,
        "pokles_5d_atr": side * (c[i] - c[i - 5]) / atr,
        "trend_60d_atr": side * (c[i] - c[i - 60]) / atr,
        "od_sma200_atr": side * (c[i] - sma200) / atr,
        "volatilita_vs_rok": atr / atr250,
        "dnu_v_rade": down,
        "zavreni_v_ramci_dne": ((c[i] - l[i]) / rng if side > 0 else (h[i] - c[i]) / rng) if rng > 0 else np.nan,
        "sazby_mom": side * I["rates_mom"][i],
        "carry": side * I["carry"][i],
        "vix": I["vix"][i],
        "vynosy_5d_bp": side * (yd[i] - yd[i - 5]) * 100 if i >= 5 else np.nan,
        "vynosy_20d_bp": side * (yd[i] - yd[i - 20]) * 100 if i >= 20 else np.nan,
        "dni_do_rozhodnuti": (nxt - t["day"]).days if nxt else np.nan,
        "dni_od_rozhodnuti": (t["day"] - max(prev)).days if prev else np.nan,
        "mesic": t["day"].month,
    }


def table(rows: list[dict], name: str) -> list[str]:
    vals = np.array([r[name] for r in rows], float)
    ok = ~np.isnan(vals)
    if ok.sum() < 60:
        return []
    q1, q2 = np.nanquantile(vals, [1 / 3, 2 / 3])
    if q1 == q2:
        bins = [("<= " + f"{q1:.3g}", vals <= q1), ("> " + f"{q1:.3g}", vals > q1)]
    else:
        bins = [(f"<= {q1:.3g}", vals <= q1), (f"{q1:.3g}..{q2:.3g}", (vals > q1) & (vals <= q2)),
                (f"> {q2:.3g}", vals > q2)]
    out = [f"\n### {name}\n", "| tercil | " + " | ".join(f"{p} n / výhry / R" for p, *_ in PERIODS) + " |",
           "|---|" + "---|" * len(PERIODS)]
    per_bin = []
    for label, mask in bins:
        cells, rs = [], []
        for _, a, b in PERIODS:
            sel = [r for r, m in zip(rows, mask) if m and a <= r["year"] <= b]
            if not sel:
                cells.append("-")
                rs.append(np.nan)
                continue
            win = np.mean([r["win"] for r in sel]) * 100
            R = np.mean([r["R"] for r in sel])
            rs.append(R)
            cells.append(f"{len(sel)} / {win:.0f} % / {R:+.3f}")
        per_bin.append((label, rs))
        out.append(f"| {label} | " + " | ".join(cells) + " |")
    lo, hi = per_bin[0][1], per_bin[-1][1]
    if all(not np.isnan(x) and not np.isnan(y) for x, y in zip(lo, hi)):
        if all(x > y for x, y in zip(lo, hi)):
            out.append(f"\n**konzistentní: nízký tercil lepší ve všech obdobích** ({name})")
        elif all(x < y for x, y in zip(lo, hi)):
            out.append(f"\n**konzistentní: vysoký tercil lepší ve všech obdobích** ({name})")
    return out


def main(argv: list[str]) -> int:
    profile = argv[argv.index("--profile") + 1] if "--profile" in argv else "mesicne"
    cfg = json.loads(SLN.PROFILES[profile]["state"].read_text())["config"]
    lists = SLN.trade_lists(cfg)
    rows = []
    for tier, tl in enumerate(lists):
        for t in tl:
            f = features(t, tier)
            f.update({"pair": t["pair"], "year": t["day"].year, "win": t["margin_pct"] > 0,
                      "R": t["margin_pct"] / t["sl_pct"], "reason": t["reason"], "margin": t["margin_pct"]})
            rows.append(f)
    lines = [f"# Obchodníkův rozbor obchodů šampiona ({profile})\n",
             f"Obchodů (všechny stupně, bez překrývání v rámci stupně): {len(rows)}. R = výsledek v násobcích "
             "ztráty na stop lossu (−1 = celý stop).\n"]
    for _, a, b in PERIODS:
        sel = [r for r in rows if a <= r["year"] <= b]
        lines.append(f"- {a}-{b}: {len(sel)} obchodů, výhry {np.mean([r['win'] for r in sel]) * 100:.0f} %, "
                     f"průměr {np.mean([r['R'] for r in sel]):+.3f} R, stop loss {sum(r['reason'] == 'SL' for r in sel)}")
    names = [k for k in rows[0] if k not in ("pair", "year", "win", "R", "reason", "margin")]
    for name in names:
        lines += table(rows, name)
    losers = [r for r in rows if r["reason"] == "SL"]
    lines.append(f"\n## Stop lossy ({len(losers)})\n")
    lines.append("| rok | pár | stupeň | RSI2 | pokles 5d ATR | trend 60d ATR | výnosy 5d bp | VIX | dní do CB |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for r in sorted(losers, key=lambda r: r["year"]):
        lines.append(f"| {r['year']} | {r['pair']} | {r['tier']} | {r['rsi2']:.1f} | {r['pokles_5d_atr']:+.1f} | "
                     f"{r['trend_60d_atr']:+.1f} | {r['vynosy_5d_bp']:+.0f} | {r['vix']:.0f} | {r['dni_do_rozhodnuti']} |")
    out = PROJECT_ROOT / "docs" / "OBCHODNIK.md"
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(l for l in lines if l.startswith("**") or l.startswith("- ") or l.startswith("#")))
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
