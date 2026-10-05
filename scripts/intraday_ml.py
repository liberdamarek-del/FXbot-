"""Machine learning on hourly FX data (user's question 2026-10-05): can a model of the kind that "trades intraday
and earns" find an edge after retail costs on our 12 pairs?

    python scripts/intraday_ml.py [--horizonty 1,4,8,24]     # -> data/research/intraday/ml.pkl + printed tables

Model: LightGBM regression of the forward return over h hours (in units of the hourly ATR) from ~30 causal
features at each hourly close: past returns 1-120 h, position in the 24 h / 120 h range, hourly RSI(2/14), the
daily RSI(2) of the last completed day, volatility regime, spread, London hour and weekday, the USD / EUR / JPY
factor moves of the last 1-24 h (all 12 pairs), and the model's monthly rate momentum and carry (2-month lag).
Walk-forward: for every test year Y (2016-2026) the model learns on 2012..Y-2, picks the trading threshold
(quantile of |prediction| with the best net result) on Y-1, then learns again on 2012..Y-1 and trades Y.
Trades: the bar after the decision opens the trade, exit at the open h hours later, one trade per pair at a time,
retail costs as intraday_lab (max(retail, real FXCM spread) / 2 + slippage / 2 per side).
"""

import pickle
import sys
import time
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import intraday_lab as L  # noqa: E402
import profit_lab2 as P  # noqa: E402
import strategy_mining as SM  # noqa: E402
from src.instruments import DEFAULT_ACTIVE, get_instrument  # noqa: E402

QUANTILES = (0.5, 0.8, 0.9, 0.95, 0.98)


def features(p: L.Pair, factors: dict, rates: dict) -> tuple[np.ndarray, list]:
    c, h, l = p.c, p.h, p.l
    atr = p.atr_h
    n = len(c)
    f, names = [], []

    def add(name, v):
        names.append(name)
        f.append(np.asarray(v, float))

    for k in (1, 2, 3, 6, 12, 24, 72, 120):
        prev = np.concatenate([np.full(k, np.nan), c[:-k]])
        add(f"ret{k}", (c - prev) / atr)
    for w in (24, 120):
        hi = SM.rolling_max(h, w)
        lo = SM.rolling_min(l, w)
        add(f"pos{w}", (c - lo) / np.where(hi - lo == 0, np.nan, hi - lo))
    add("rsi2", SM.rsi(c, 2))
    add("rsi14", SM.rsi(c, 14))
    add("vol", (h - l) / atr)
    add("volreg", atr / np.concatenate([np.full(480, np.nan), atr[:-480]]))
    add("spread", p.cost_c / atr)
    add("hour_sin", np.sin(2 * np.pi * p.lon_h / 24))
    add("hour_cos", np.cos(2 * np.pi * p.lon_h / 24))
    add("weekday", p.wd)
    # daily RSI(2) of the last completed New York day
    days, first = np.unique(p.day, return_index=True)
    last = np.append(first[1:], n) - 1
    rsi_d = SM.rsi(c[last], 2)
    pos = np.searchsorted(days, p.day) - 1
    add("rsi2_den", np.where(pos >= 0, rsi_d[np.maximum(pos, 0)], np.nan))
    for name, (fts, fv) in factors.items():
        k = np.searchsorted(fts, p.ts, side="right") - 1              # the factor value at this bar's close
        for lag in (1, 6, 24):
            idx = np.maximum(k - lag, 0)
            add(f"{name}{lag}", np.where(k - lag >= 0, fv[np.maximum(k, 0)] - fv[idx], np.nan))
    inst = get_instrument(p.symbol)
    ym = (p.year * 12 + np.array([int(str(d)[5:7]) for d in p.day]) - 1)
    mom = np.full(n, np.nan)
    carry = np.full(n, np.nan)
    for key in np.unique(ym):
        y, m = divmod(int(key), 12)
        v = [P.rate_at(rates[cc], y, m + 1, lag) for cc in (inst.base, inst.quote) for lag in (2, 5)]
        if None not in v:
            sel = ym == key
            mom[sel] = (v[0] - v[2]) - (v[1] - v[3])
            carry[sel] = v[0] - v[2]
    add("rate_mom", mom)
    add("carry", carry)
    return np.column_stack(f), names


def currency_factors(pairs: list) -> dict:
    """Cumulative hourly log moves of USD, EUR and JPY against the other currencies of the 12 pairs (mean over
    the pairs that contain them), on the union of hourly timestamps."""
    allts = np.unique(np.concatenate([p.ts for p in pairs]))
    out = {}
    for ccy in ("USD", "EUR", "JPY"):
        acc = np.zeros(len(allts))
        cnt = np.zeros(len(allts))
        for p in pairs:
            base, quote = p.symbol.split("/")
            if ccy not in (base, quote):
                continue
            r = np.log(p.c / p.o) * (1 if base == ccy else -1)
            k = np.searchsorted(allts, p.ts)
            acc[k] += r
            cnt[k] += 1
        out[ccy] = (allts + 3600, np.cumsum(np.where(cnt > 0, acc / np.maximum(cnt, 1), 0.0)))
    return out


COST_K = None                              # --naklady k: trade when the predicted move > k x the round-trip cost


def trades_from(p: L.Pair, pred: np.ndarray, rows: np.ndarray, thr: float, hzn: int) -> dict:
    """Trade when |prediction| >= thr (or, with COST_K, when the predicted price move exceeds COST_K x the pair's
    round-trip cost at the entry): enter at the next bar's open, exit h hours later; one trade at a time."""
    take, busy = [], -1
    for i, v in zip(rows, pred):
        if i + 1 <= busy or i + 1 >= len(p.ts):
            continue
        if COST_K is not None:
            if not abs(v) * p.atr_h[i] > COST_K * 2 * p.cost_o[i + 1]:
                continue
        elif abs(v) < thr:
            continue
        take.append((i + 1, np.sign(v)))
        busy = i + 1 + hzn
    if not take:
        return L.merge([])
    e, s = (np.array(x) for x in zip(*take))
    return L.fixed_trades(p, e, e + hzn, s.astype(float))


def main(argv: list[str]) -> int:
    import lightgbm as lgb
    started = time.monotonic()
    global COST_K
    hz = [int(x) for x in argv[argv.index("--horizonty") + 1].split(",")] if "--horizonty" in argv else [1, 4, 8, 24]
    if "--naklady" in argv:
        COST_K = float(argv[argv.index("--naklady") + 1])
    pairs = [L.Pair(s) for s in DEFAULT_ACTIVE]
    rates = P.monthly_rates()
    fac = currency_factors(pairs)
    data = []
    for p in pairs:
        X, names = features(p, fac, rates)
        data.append((p, X))
    print(f"vlastnosti: {len(names)}, {time.monotonic() - started:.0f} s", flush=True)
    results = {}
    for hzn in hz:
        per_year = {}
        for Y in range(2016, 2027):
            def build(y_lo, y_hi):
                Xs, ys = [], []
                for p, X in data:
                    m = (p.year >= y_lo) & (p.year <= y_hi)
                    idx = np.where(m)[0]
                    idx = idx[idx + 1 + hzn < len(p.ts)]
                    idx = idx[p.contiguous(idx + 1, idx + 1 + hzn)]
                    target = (p.o[idx + 1 + hzn] - p.o[idx + 1]) / p.atr_h[idx]
                    ok = np.isfinite(target)
                    Xs.append(X[idx[ok]])
                    ys.append(np.clip(target[ok], -5, 5))
                return np.vstack(Xs), np.concatenate(ys)

            params = dict(objective="regression", learning_rate=0.05, num_leaves=31, min_data_in_leaf=500,
                          feature_fraction=0.8, bagging_fraction=0.7, bagging_freq=1, lambda_l2=10.0, verbose=-1,
                          num_threads=3, seed=Y)
            Xa, ya = build(2012, Y - 2)
            model = lgb.train(params, lgb.Dataset(Xa, ya), num_boost_round=200)
            # threshold on Y-1 (not seen by this model), by the net result of the trades
            best = (-np.inf, None)
            preds_v = []
            for p, X in data:
                rows = np.where(p.year == Y - 1)[0]
                preds_v.append((p, rows, model.predict(X[rows])))
            allabs = np.concatenate([np.abs(v) for _, _, v in preds_v])
            for q in QUANTILES:
                thr = float(np.quantile(allabs, q))
                tr = L.merge([t for t in (trades_from(p, v, rows, thr, hzn) for p, rows, v in preds_v) if len(t["ret"])])
                if len(tr["ret"]) >= 50 and tr["ret"].sum() > best[0]:
                    best = (tr["ret"].sum(), q)
            q = best[1] if best[1] is not None else 0.95
            Xb, yb = build(2012, Y - 1)
            model = lgb.train(params, lgb.Dataset(Xb, yb), num_boost_round=200)
            preds = []
            for p, X in data:
                rows = np.where(p.year == Y - 1)[0]
                preds.append(np.abs(model.predict(X[rows])))
            thr = float(np.quantile(np.concatenate(preds), q))       # the same quantile, set on Y-1 predictions
            parts = []
            for p, X in data:
                rows = np.where(p.year == Y)[0]
                if not len(rows):
                    continue
                t = trades_from(p, model.predict(X[rows]), rows, thr, hzn)
                if len(t["ret"]):
                    parts.append(t)
            tr = L.merge(parts)
            per_year[Y] = {"q": q, "n": len(tr["ret"]), "mean": float(tr["ret"].mean()) if len(tr["ret"]) else np.nan,
                           "gross": float(tr["gross"].mean()) if len(tr["ret"]) else np.nan,
                           "win": float((tr["ret"] > 0).mean()) if len(tr["ret"]) else np.nan, "trades": tr}
            print(f"h{hzn} {Y}: kvantil {q}, obchodu {per_year[Y]['n']}, cisty prumer {per_year[Y]['mean']:+.4f} %, "
                  f"hruby {per_year[Y]['gross']:+.4f} %, uspesnost {per_year[Y]['win']:.0%} | {time.monotonic() - started:.0f} s",
                  flush=True)
        allt = L.merge([v["trades"] for v in per_year.values() if len(v["trades"]["ret"])])
        results[hzn] = {"per_year": {y: {k: v for k, v in r.items() if k != "trades"} for y, r in per_year.items()},
                        "trades": {k: allt[k] for k in ("pair", "year", "ret", "gross", "i")},
                        "B": L.stats(allt, "B"), "C": L.stats(allt, "C"),
                        "A16": L.stats({**allt}, "A")}
        print(f"h{hzn}: 2016-18 {results[hzn]['A16']}\n      2019-22 {results[hzn]['B']}\n      2023-26 {results[hzn]['C']}", flush=True)
    L.OUT.mkdir(parents=True, exist_ok=True)
    (L.OUT / f"ml{'' if COST_K is None else f'_k{COST_K}'}.pkl").write_bytes(pickle.dumps(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
