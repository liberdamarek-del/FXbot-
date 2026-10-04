"""F2 - weekly FX research (scripts/indikatory.py, scripts/tydenni_analyza.py); no network.

No look-ahead: every condition of the grid at bar t is the same whether or not later bars exist; a higher
timeframe enters only after its bar closed; the week's locked conditions do not change when the prices of
the week (and later) change. Also: forward returns / non-overlapping samples, the currency factor model,
parsing of calendar values and surprise signs, data quality counts, the FX week in both DST regimes, the
neighbour settings of the robustness check and one-indicator-family combinations.
"""

import os
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="fxbot_f2_")
os.environ["FXBOT_IGNORE_DOTENV"] = "1"
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import numpy as np  # noqa: E402

import indikatory as K  # noqa: E402
import tydenni_analyza as T  # noqa: E402

UTC = timezone.utc
rng = np.random.default_rng(7)


def walk(n: int, start_ts: int = 1_600_000_000, sec: int = 3600) -> dict:
    c = 1.1 * np.exp(np.cumsum(rng.normal(0, 0.002, n)))
    o = np.concatenate([[c[0]], c[:-1]])
    h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, 0.001, n)))
    l = np.minimum(o, c) * (1 - np.abs(rng.normal(0, 0.001, n)))
    ts = start_ts // sec * sec + np.arange(n, dtype=np.int64) * sec
    return {"ts": ts, "o": o, "h": h, "l": l, "c": c, "close_ts": ts + sec, "sec": sec}


# ---------------------------------------------------------------- no look-ahead in any grid condition
full = walk(1500)
cut = {k: (v[:1200] if isinstance(v, np.ndarray) else v) for k, v in full.items()}
bf, bc = K.Builder(full), K.Builder(cut)
grid = K.grid()
assert len(grid) > 800 and len({g.key for g in grid}) == len(grid)
for g in grid:
    a, b = bf.mask(g)[:1200], bc.mask(g)
    assert np.array_equal(a, b), g.key
for n in (5, 14, 28):                                             # indicator values too
    assert np.allclose(K.rsi(full["c"], n)[:1200], K.rsi(cut["c"], n), equal_nan=True)
    assert np.allclose(K.adx(full["h"], full["l"], full["c"], n)[0][:1200],
                       K.adx(cut["h"], cut["l"], cut["c"], n)[0], equal_nan=True)

# ---------------------------------------------------------------- higher timeframe only after its close
h4 = K.resample(full, 14400, 3600)
assert np.all(h4["close_ts"] - h4["ts"] <= 14400)
m = np.zeros(len(h4["ts"]), bool)
m[3] = True                                                       # the 4th 4-hour bar is "on"
al = K.align(h4["close_ts"], m, full["close_ts"])
on = np.where(al)[0]
assert len(on) and full["close_ts"][on[0]] >= h4["close_ts"][3]  # visible from its close, not before
assert not al[np.searchsorted(full["close_ts"], h4["close_ts"][3]) - 1]

# ---------------------------------------------------------------- forward returns, samples, locked set
ds = T.Dataset("EUR/USD", "1H", full, {}, {})
assert np.all(np.diff(ds.idx) >= ds.H)                            # forward windows do not overlap
assert np.allclose(ds.fwd, (full["c"][ds.idx + ds.H] / full["c"][ds.idx] - 1) * 100)
assert np.all(ds.t_end > ds.t)
t0 = int(full["close_ts"][1100])
before = ds.t_end <= t0
lock_a = T.select(ds, before, ds.M, 20, "year")
changed = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in full.items()}
k0 = np.searchsorted(changed["ts"], t0)
for k in "ohlc":
    changed[k][k0:] = changed[k][k0:] * np.linspace(1.0, 1.3, len(changed[k]) - k0)   # a different future
ds_b = T.Dataset("EUR/USD", "1H", changed, {}, {})
lock_b = T.select(ds_b, ds_b.t_end <= t0, ds_b.M, 20, "year")
assert [(r, d) for r, d, _ in lock_a] == [(r, d) for r, d, _ in lock_b]

# ---------------------------------------------------------------- currency factors
hours = 200
f = {c: rng.normal(0, 0.1, hours) for c in ("USD", "EUR", "JPY", "GBP")}
pairs = ("EUR/USD", "USD/JPY", "GBP/USD", "EUR/JPY", "GBP/JPY", "EUR/GBP")
rets = {p: f[p.split("/")[0]] - f[p.split("/")[1]] for p in pairs}
res = T.currency_factors(rets)
mean = np.mean([f[c] for c in f], axis=0)
for c in f:
    assert abs(res["meny"][c] - float((f[c] - mean).sum())) < 1e-9
for p in pairs:
    assert res["pary"][p]["r2_spolecny"] > 0.999999 and abs(res["pary"][p]["individualni_pct"]) < 1e-9

# ---------------------------------------------------------------- calendar values, surprise sign
assert T.parse_value("0.3%") == (0.3, 1) and T.parse_value("225K") == (225.0, 0)
assert T.parse_value("-1.2B") == (-1.2, 1) and T.parse_value("<0.1%") == (None, 0) and T.parse_value(None) == (None, 0)
assert T.event_type("Unemployment Rate") == "nezaměstnanost" and "nezaměstnanost" in T.LOWER_IS_BETTER
assert T.event_type("ISM Manufacturing PMI") == "ISM" and T.event_type("Non-Farm Employment Change") == "NFP"
assert T.event_type("Federal Funds Rate") == "rozhodnutí o sazbách"
assert T.classify(0.08, 0.10) == "SIDEWAYS" and T.classify(0.08, 0.05) == "UP" and T.classify(-0.3, 0.2) == "DOWN"

# ---------------------------------------------------------------- data quality counts
raw = walk(130, start_ts=T.week_bounds(date(2026, 9, 28))[0])
raw["ts_raw"] = np.concatenate([raw["ts"][:50], raw["ts"][49:50], raw["ts"][60:]])      # duplicate + 10-hour gap
for k in "ohlc":
    raw[k] = np.concatenate([raw[k][:50], raw[k][49:50], raw[k][60:]])
raw["h"][5] = raw["l"][5] * 0.99                                  # high below low
raw["ts"] = raw["ts_raw"].copy()
raw["missing_values"] = 0
t0w, t1w = T.week_bounds(date(2026, 9, 28))
q = T.quality(raw, t0w, t1w, "test")
assert q["duplicity"] == 1 and q["spatne_ohlc"] == 1 and q["chybi"] >= 10 and q["mezery"][0][1] == 10, q

# ---------------------------------------------------------------- FX week in summer and winter time
s0, s1 = T.week_bounds(date(2026, 9, 28))
assert datetime.fromtimestamp(s0, tz=UTC).hour == 21 and datetime.fromtimestamp(s1, tz=UTC).hour == 21
w0, w1 = T.week_bounds(date(2026, 12, 7))
assert datetime.fromtimestamp(w0, tz=UTC).hour == 22 and (w1 - w0) == 5 * 86400

# ---------------------------------------------------------------- neighbours and indicator families
nb = {c.key for c in K.neighbors(K.Cond("rsi_lt", (14, 30)))}
assert {"RSI13<30", "RSI15<30", "RSI14<25", "RSI14<35"} <= nb
nb = {c.key for c in K.neighbors(K.Cond("px_gt", ("EMA", 200)))}
assert nb == {"C>EMA180", "C>EMA220"}
i_macd = [i for i, c in enumerate(ds.conds) if c.kind == "macd_hpos"][:2]
i_rsi = [i for i, c in enumerate(ds.conds) if c.key == "RSI14>50"][0]
assert not T.distinct(ds, tuple(i_macd))                          # two MACD settings = one family
assert T.family(ds.conds[i_macd[0]]) != T.family(ds.conds[i_rsi])

print("=" * 60)
print("F2 WEEKLY RESEARCH")
print("=" * 60)
print("NO LOOK-AHEAD: 800+ CONDITIONS, INDICATORS, HIGHER TIMEFRAME, LOCKED SET: PASS")
print("FORWARD RETURNS, NON-OVERLAPPING SAMPLES: PASS")
print("CURRENCY FACTORS, CALENDAR VALUES, SURPRISE SIGN, SIDEWAYS THRESHOLDS: PASS")
print("DATA QUALITY COUNTS, FX WEEK (DST), NEIGHBOURS, INDICATOR FAMILIES: PASS")
print("RESULT: PASS")
print("=" * 60)
