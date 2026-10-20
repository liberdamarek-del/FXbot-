"""Synteticky scenar zivého jadra (bez data/): ceny, sazby, VIX a udalosti z generatoru s pevnym semenem.

Pouziva ho test_h1_core.py. Scenar spocita vystupy cele cesty zive jadro -> indikatory -> simulator -> ucet a vrati
je jako slovnik; test je porovna se zlatym zakladem `tests/fixtures/jadro_zlaty.json`, ktery vznikl STARYM kodem
(pred presunem do src/core, R-048). Pole se porovnavaji otiskem sha256 jejich bajtu, cisla presne (float.hex).

Generator nepouziva zadnou funkci libm (exp, log): nahodna cisla jsou cela (rng.integers) a ceny scitane, takze
data jsou stejna na kazdem stroji. Scenar dostane `F` = jmenny prostor s moduly jadra (viz test_h1_core.py).
"""

from __future__ import annotations

import contextlib
import hashlib
import json
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone

import numpy as np

UTC = timezone.utc
SYMBOLS = ("EUR/USD", "AUD/JPY")
WEEKS = 208                                   # 4 roky obchodnich tydnu od nedele 2012-12-30
START = int(datetime(2012, 12, 30, 22, tzinfo=UTC).timestamp())

# pravidla sampionu k 2026-10-20 (opsana, aby test nezavisel na pozdejsi zmene sampiona)
BASE_MAX = {"signal": "D RSI2<5", "weekly": True, "tp": 0.75, "sl": 3.0, "hold_days": 20, "exit_before_cb": "zisk",
            "decide_h": 1}
RULES = {
    "max_stupen0": {**BASE_MAX, "fund": "rates_up+carry", "rates_thr": 0.25, "signal": "D RSI2<5|D RSI3<15"},
    "max_stupen3": {**BASE_MAX, "fund": "rates_up", "rates_thr": 0.0},
    "mesicne_stupen2": {**BASE_MAX, "sl": 4.0, "fund": "rates_up", "rates_thr": 0.1},
    "denni_bez_decide_h": {"signal": "D RSI2<10", "weekly": False, "fund": "rates_up", "rates_thr": 0.0, "hold_days": 10,
                           "exit_before_cb": "zisk"},
    "limitni_vstup": {"signal": "D RSI2<10", "weekly": False, "fund": None, "limit_atr": 0.5},
    "procentni_vystup": {"signal": "D RSI2<10", "weekly": False, "fund": None, "exit_kind": "PCT", "tp": 0.5, "sl": 1.0,
                         "min_tp_pct": 0.0},
    "casti_cile": {"signal": "D RSI2<10", "weekly": False, "fund": None, "tp_parts": (0.75, 1.0)},
}
FULL = ("max_stupen0", "max_stupen3", "mesicne_stupen2")     # tyto obchody se ukladaji cele, ostatni otiskem


# ---------------------------------------------------------------- otisky
def canon(x):
    if isinstance(x, (np.floating, float)):
        return float(x).hex()
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.bool_):
        return bool(x)
    if isinstance(x, np.ndarray):
        return [canon(v) for v in x.tolist()]
    if isinstance(x, (date, datetime)):
        return x.isoformat()
    if isinstance(x, dict):
        return {str(k): canon(v) for k, v in sorted(x.items(), key=lambda kv: str(kv[0]))}
    if isinstance(x, (list, tuple, set)):
        return [canon(v) for v in (sorted(x, key=str) if isinstance(x, set) else x)]
    return x


def otisk(obj) -> str:
    return hashlib.sha256(json.dumps(canon(obj), sort_keys=True).encode()).hexdigest()


def otisk_pole(a) -> str:
    a = np.asarray(a)
    if a.dtype == object:
        return otisk(a.tolist())
    return hashlib.sha256(str((a.dtype.str, a.shape)).encode() + np.ascontiguousarray(a).tobytes()).hexdigest()


# ---------------------------------------------------------------- syntetická data
def zapis_data(F, tmp, symbols=SYMBOLS) -> None:
    """FRED csv (sazby, dlouhe vynosy, VIX) a hodinove svicky paru v presnem formatu, ktery ctou funkce jadra."""
    fred = tmp / "fred"
    fred.mkdir(parents=True, exist_ok=True)
    ids = sorted({i for v in F.P.RATE_IDS.values() for i in v} | set(F.P.EXTEND_IDS.values()) | set(F.P.LONG_IDS.values()))
    for n, sid in enumerate(ids):
        rng = np.random.default_rng(1000 + n)
        value, rows = 2.0, []
        last = date(2017, 12, 1)
        if sid == "IR3TIB01GBM156N":                      # 3m rada koncici driv: zbytek dopocte prodlouzeni (EXTEND_IDS)
            last = date(2016, 3, 1)
        for k in range(120):                              # 2008-01 .. 2017-12
            d = date(2008 + k // 12, k % 12 + 1, 1)
            if d > last:
                break
            value = round(value + 0.25 * int(rng.integers(-1, 2)), 2)
            rows.append(f"{d.isoformat()},{'.' if k % 41 == 7 else value}")
        (fred / f"{sid}.csv").write_text("observation_date," + sid + "\n" + "\n".join(rows) + "\n")
    rng = np.random.default_rng(7)
    vix, day, rows = 18.0, date(2008, 1, 1), []
    while day <= date(2017, 12, 31):
        if day.weekday() < 5:
            vix = min(max(vix + int(rng.integers(-100, 101)) / 100.0, 9.0), 45.0)
            rows.append(f"{day.isoformat()},{round(vix, 2)}")
        day += timedelta(days=1)
    (fred / "VIXCLS.csv").write_text("observation_date,VIXCLS\n" + "\n".join(rows) + "\n")
    folder = tmp / "fxcm_h1"
    folder.mkdir(parents=True, exist_ok=True)
    base_ts = (START + 604800 * np.arange(WEEKS)[:, None] + 3600 * np.arange(120)[None, :]).ravel()   # ne 22:00 .. pa 21:00 UTC
    for n, symbol in enumerate(symbols):
        rng = np.random.default_rng(50 + n)
        jpy = symbol.endswith("JPY")
        sigma, spread, price = (0.32, 0.008, 90.0) if jpy else (0.0032, 0.00008, 1.3)
        steps = rng.integers(-1000, 1001, len(base_ts)).astype(float) / 1000.0 * sigma
        mid = np.empty(len(steps) + 1)
        mid[0] = price
        for i, step in enumerate(steps):                   # navrat k cene (AR): ceny zustanou kladne, RSI(2) casto extremni
            mid[i + 1] = mid[i] + step - 0.0005 * (mid[i] - price)
        o, c = mid[:-1], mid[1:]
        h = np.maximum(o, c) + rng.integers(0, 500, len(o)).astype(float) / 1000.0 * sigma
        l_ = np.minimum(o, c) - rng.integers(0, 500, len(o)).astype(float) / 1000.0 * sigma
        half = spread / 2
        np.savez(folder / f"{symbol.replace('/', '')}.npz", ts=base_ts.astype(np.int64),
                 bo=o - half, bh=h - half, bl=l_ - half, bc=c - half, ao=o + half, ah=h + half, al=l_ + half, ac=c + half)


@contextlib.contextmanager
def dirs_core(tmp):
    """Presmeruje cesty src/core (FRED, hodinove svicky, cache serii) do docasne slozky: testy bez data/."""
    from src.core import market, paths
    old = (paths.FRED_DIR, paths.FXCM_H1, paths.HISTDATA_H1, market.OUT)
    paths.FRED_DIR, paths.FXCM_H1, paths.HISTDATA_H1, market.OUT = (tmp / "fred", tmp / "fxcm_h1", tmp / "histdata_h1",
                                                                   tmp / "profit2")
    market.EXTENDED.clear()
    try:
        yield
    finally:
        paths.FRED_DIR, paths.FXCM_H1, paths.HISTDATA_H1, market.OUT = old


def udalosti() -> dict:
    """Terminy rozhodnuti centralnich bank a US dat (vsedni dny 2013-2016) misto learning/udalosti_historie.json."""
    out = {}
    for n, name in enumerate(("FED", "ECB", "BOJ", "BOE", "US_NFP", "US_CPI")):
        rng = np.random.default_rng(300 + n)
        days = sorted({date(2013, 1, 1) + timedelta(days=int(k)) for k in rng.integers(0, 1460, 40)})
        out[name] = [d.isoformat() for d in days if d.weekday() < 5]
    return out


# ---------------------------------------------------------------- scenar
def vypocitej(F, tmp) -> dict:
    """Vsechny vystupy cesty zive jadro -> simulator -> ucet. `F` = jmenny prostor: ta, P, SM, D, PS, dirs(tmp)."""
    out = {}
    # 1. technicke stavebni kameny na pevnych polich
    rng = np.random.default_rng(5)
    x = 100 + np.cumsum(rng.integers(-1000, 1001, 500).astype(float) / 1000.0)
    hi = x + rng.integers(0, 1000, 500).astype(float) / 1000.0
    lo = x - rng.integers(0, 1000, 500).astype(float) / 1000.0
    gap = x.copy()
    gap[100:110] = np.nan
    tr = F.ta.true_range(hi, lo, x)
    out["ta"] = {k: otisk_pole(v) for k, v in {
        "rsi2": F.ta.rsi(x, 2), "rsi14": F.ta.rsi(x, 14), "tr": tr, "wilder": F.ta.wilder(tr, 14), "ema": F.ta.ema(x, 20),
        "sma": F.ta.sma(x, 10), "sma_gap": F.ta.sma(gap, 10), "rmax": F.ta.rolling_max(x, 20),
        "rmin": F.ta.rolling_min(x, 20), "shift": F.ta.shift(x), "shift3": F.ta.shift(x, 3),
        "rsi_flat": F.ta.rsi(np.full(30, 1.25), 2)}.items()}
    days = [date(2024, 1, 1) + timedelta(days=k) for k in range(700) if (date(2024, 1, 1) + timedelta(days=k)).weekday() < 5]
    n = len(days)
    c = 1.1 + np.cumsum(rng.integers(-1000, 1001, n).astype(float) / 1000.0 * 0.004)
    o = np.concatenate([[c[0]], c[:-1]])
    h, l_ = np.maximum(o, c) * 1.001, np.minimum(o, c) * 0.999
    out["weekly_aligned"] = {k: otisk_pole(v) for k, v in F.ta.weekly_aligned(days, o, h, l_, c).items()}
    atr = F.ta.wilder(F.ta.true_range(h, l_, c), 14)
    out["daily_indicators"] = {k: otisk_pole(v) for k, v in F.ta.indicators(o, h, l_, c, atr).items()}
    # 2. sazby, krivka, serie a indikatory ze souboru v docasne slozce
    with F.dirs(tmp):
        zapis_data(F, tmp)
        F.D._cache.clear()
        rates = F.P.monthly_rates()
        long_ = F.P.monthly_long_rates()
        out["rates"] = otisk({c_: {f"{k[0]}-{k[1]}": v for k, v in s.items()} for c_, s in rates.items()})
        out["rates_extended"] = dict(F.P.EXTENDED)
        out["long_rates"] = otisk({c_: {f"{k[0]}-{k[1]}": v for k, v in s.items()} for c_, s in long_.items()})
        out["curve_mom"] = otisk([F.P.curve_mom(rates, long_, b, q, y, m, 2, 3) for (b, q) in (("EUR", "USD"), ("AUD", "JPY"))
                                  for y in (2014, 2015, 2016) for m in (1, 6, 12)])
        out["rate_at"] = otisk([F.P.rate_at(rates["USD"], y, m, lag) for y in (2013, 2015, 2016) for m in (1, 7, 12)
                                for lag in (0, 2, 5)])
        out["leverage"] = {p: F.P.leverage(p) for p in ("EUR/USD", "AUD/USD", "AUD/JPY", "NZD/USD", "GBP/JPY")}
        defs = F.P.signal_defs()
        out["signal_names"] = sorted(defs)
        out["series"], out["indicators"], out["signals"] = {}, {}, {}
        for symbol in SYMBOLS:
            s = F.P.series(symbol)
            out["series"][symbol] = {k: otisk_pole(v) if isinstance(v, np.ndarray) else otisk(v) for k, v in s.items()}
            I = F.P.indicators(s, rates, symbol)
            out["indicators"][symbol] = {k: otisk_pole(v) for k, v in I.items()}
            with np.errstate(invalid="ignore"):
                out["signals"][symbol] = {name: [otisk_pole(np.nan_to_num(fn[0](I)).astype(bool)),
                                                 otisk_pole(np.nan_to_num(fn[1](I)).astype(bool))]
                                          for name, fn in defs.items()}
        # 3. simulator (vsechny volby pravidla, ktere maji cestu pres indikatory) a ucet
        F.D._cache.clear()
        F.D._cache["events"] = udalosti()
        trades = {}
        for name, fields in RULES.items():
            rule = replace(F.D.Rule(name), **fields)
            trades[name] = F.D.simulate(rule, list(SYMBOLS))
        out["trades"] = {name: ({"n": len(t), "hash": otisk(t), "all": canon(t)} if name in FULL
                                else {"n": len(t), "hash": otisk(t), "first": canon(t[:3])})
                         for name, t in trades.items()}
        pf = {}
        for label, names, shares in (("max", ("max_stupen0", "max_stupen3"), [0.15, 0.06]),
                                     ("mesicne", ("mesicne_stupen2", "max_stupen0"), [0.2, 0.04])):
            r = F.PS.run_portfolio([[dict(t) for t in trades[nm]] for nm in names], shares, (2013, 2016))
            pf[label] = {"n": len(r["trades"]), "hash": otisk({k: v for k, v in r.items() if k != "trades"}),
                         "equity": r["equity"], "max_dd": r["max_dd"], "cagr": r["cagr"]}
        out["portfolio"] = pf
        F.D._cache.clear()
    return canon(out)
