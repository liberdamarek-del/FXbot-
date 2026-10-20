"""Ceny, naklady, signaly a denni indikatory zivého jadra (simulator, zive signaly, diagnostika, heuristiky).

Funkce a konstanty jsou PRESUNUTE DOSLOVNE z scripts/profit_lab2.py (R-048, architektura-v2, faze 1): zive jadro
tak uz neimportuje vyzkumne laby. `profit_lab2` je dnes jen vyzkumny lab, ktery si tyto nazvy bere odsud.
Vysledky musi zustat bit po bitu stejne (test_h1_core.py, zlaty zaklad na realnych datech).

Moduly jadra tento modul pouzivaji pod aliasem `P` (drive `import profit_lab2 as P`), proto se sem z `rates`
vyvazeji i sazby (monthly_rates, rate_at, curve_mom ...).
"""

import pickle
from datetime import date

import numpy as np

from src.instruments import get_instrument
from src.path_archive import trading_date

from . import paths
from .rates import (EXTEND_IDS, EXTENDED, LONG_IDS, RATE_IDS, curve_mom, monthly_long_rates,  # noqa: F401 (re-export)
                    monthly_rates, rate_at)
from .ta import ema, rolling_max, rolling_min, shift, true_range, weekly_aligned, wilder
from .ta import indicators as ta_indicators

OUT = paths.PROFIT2                                 # cache serii (series_*.pkl) a vystupy labu; testy ji presmeruji
LEVERAGE = 30                                       # major pairs (the research labs use it for every pair)
MIN_TP_PCT = 10.0 / LEVERAGE                         # 10 % of the margin at 1:30, in % of the price
ESMA_MAJORS = {"USD", "EUR", "JPY", "GBP", "CAD", "CHF"}


def leverage(pair: str) -> int:
    """Retail leverage of an EU broker (ESMA): 1:30 for pairs of two major currencies (USD, EUR, JPY, GBP, CAD,
    CHF), 1:20 for the other pairs (e.g. AUD/USD, NZD/USD, AUD/JPY). The margin of a position is notional /
    leverage, so % of the margin = % price move x leverage (audit 2026-10-04: 1:30 was used for all pairs)."""
    base, quote = pair.split("/")
    return 30 if base in ESMA_MAJORS and quote in ESMA_MAJORS else 20


HOLD_BARS = {5: 120, 10: 240, 20: 480}            # 120 hourly bars = one trading week
PERIODS = {"A": (date(2012, 1, 1), date(2018, 12, 31)), "B": (date(2019, 1, 1), date(2022, 12, 31)),
           "TEST": (date(2023, 1, 1), date(2026, 9, 30))}
MIN_HOURS = 20                                     # a trading day needs >= 20 valid hourly bars
# typical retail spread in pips (incl. broker markup) of the 12 live pairs, the same in all periods
# (until R-048 in scripts/research_signals.py, which now takes it from here)
SPREAD_PIPS_12 = {"EUR/USD": 0.8, "USD/JPY": 0.9, "GBP/USD": 1.2, "USD/CHF": 1.4, "AUD/USD": 1.0, "USD/CAD": 1.5,
                  "NZD/USD": 1.5, "EUR/JPY": 1.5, "GBP/JPY": 2.5, "EUR/GBP": 1.2, "EUR/CHF": 1.6, "AUD/JPY": 1.6}
SPREAD_PIPS = {**SPREAD_PIPS_12,                  # the 12 live pairs: one table
               "CAD/JPY": 2.0, "NZD/JPY": 2.2, "GBP/CHF": 2.6, "AUD/CAD": 2.0, "AUD/CHF": 2.0, "AUD/NZD": 2.5,
               "CAD/CHF": 2.2, "EUR/AUD": 2.2, "EUR/NZD": 3.5, "GBP/CAD": 3.2, "GBP/NZD": 4.5, "NZD/CAD": 2.6,
               "NZD/CHF": 2.6,
               # HistData pairs (BID only): typical retail spreads in pips of the instrument
               "USD/NOK": 40, "EUR/NOK": 40, "USD/SEK": 40, "EUR/SEK": 40, "USD/MXN": 60, "USD/ZAR": 100,
               "ZAR/JPY": 3.0, "USD/PLN": 30, "EUR/PLN": 25, "USD/HUF": 30, "EUR/HUF": 30, "USD/CZK": 20,
               "EUR/CZK": 15, "CHF/JPY": 2.5, "EUR/CAD": 2.5, "GBP/AUD": 3.0}
SLIPPAGE_PIPS = 0.4
FIN_MARKUP = 1.0                                   # % p.a. the broker keeps on each side of the swap


def half_spread(pair: str) -> float:
    """What one side of a trade (entry or exit) costs in price units: half the typical spread plus half the
    slippage. The one definition of the backtest (profit_deep.simulate), the live plan and the forward test
    (new in R-048; before, the same expression stood in each of them)."""
    return (SPREAD_PIPS[pair] / 2 + SLIPPAGE_PIPS / 2) * get_instrument(pair).pip


FIELDS = ("bo", "bh", "bl", "bc", "ao", "ah", "al", "ac")


def load_hourly(symbol: str) -> dict:
    """Hourly arrays of one pair: ts (bar open, UTC) and BID/ASK OHLC
    (FXCM; for the pairs FXCM does not publish the HistData BID series). (Was fxcm_universe.load.)"""
    path = paths.FXCM_H1 / f"{symbol.replace('/', '')}.npz"
    if not path.exists():
        path = paths.HISTDATA_H1 / f"{symbol.replace('/', '')}.npz"
    data = np.load(path)
    return {k: data[k] for k in ("ts",) + FIELDS}


def series(symbol: str) -> dict:
    """Hourly mid bars + the daily bars (New York close) built from them."""
    name = symbol.replace("/", "")
    cache = OUT / f"series_{name}.pkl"
    source = paths.FXCM_H1 / f"{name}.npz"
    if not source.exists():
        source = paths.HISTDATA_H1 / f"{name}.npz"
    # rebuilt when the hourly data are newer (the weekly download), else the learning would not see new weeks
    if cache.exists() and (not source.exists() or cache.stat().st_mtime >= source.stat().st_mtime):
        return pickle.loads(cache.read_bytes())
    H = load_hourly(symbol)
    ts = H["ts"]
    ho, hh, hl, hc = ((H["b" + k] + H["a" + k]) / 2 for k in "ohlc")
    hours = np.unique(ts // 3600 * 3600)
    td = {int(t): trading_date(int(t)) for t in hours}
    tdate = np.array([td[int(t)] for t in ts])
    days, first = np.unique(tdate, return_index=True)
    last = np.append(first[1:], len(ts)) - 1
    count = last - first + 1
    good = count >= MIN_HOURS
    days, first, last = days[good], first[good], last[good]
    o = ho[first]
    c = hc[last]
    h = np.array([hh[a:b + 1].max() for a, b in zip(first, last)])
    l_ = np.array([hl[a:b + 1].min() for a, b in zip(first, last)])
    out = {"ts": ts, "o": ho, "h": hh, "l": hl, "c": hc, "days": list(days), "first": first, "last": last,
           "do": o, "dh": h, "dl": l_, "dc": c, "close_ts": ts[last] + 3600}
    OUT.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(pickle.dumps(out))
    return out


# ----------------------------------------------------------------------
# signals
# ----------------------------------------------------------------------

def signal_defs() -> dict:
    d = {}
    for n, x in ((2, 5), (2, 10), (3, 15)):
        d[f"D RSI{n}<{x}"] = (lambda I, n=n, x=x: I[f"rsi{n}"] < x, lambda I, n=n, x=x: I[f"rsi{n}"] > 100 - x)
    d["D %R14<10"] = (lambda I: I["wr14"] < 10, lambda I: I["wr14"] > 90)
    d["D 3 dny dolu"] = (lambda I: I["down3"], lambda I: I["up3"])
    d["D pod SMA5 o 1.5 ATR"] = (lambda I: I["dist_sma5"] < -1.5, lambda I: I["dist_sma5"] > 1.5)
    d["D pod BB20(2)"] = (lambda I: I["bb20_2.0"] < 0, lambda I: I["bb20_2.0"] > 1)
    d["D Donchian20 pruraz"] = (lambda I: I["brk20"] > 0, lambda I: I["brk20"] < 0)
    d["D EMA20 x EMA50 cerstve"] = (lambda I: I["cross"] > 0, lambda I: I["cross"] < 0)
    for n, x in ((2, 10), (2, 20), (3, 30)):
        d[f"W RSI{n}<{x}"] = (lambda I, n=n, x=x: I[f"w_rsi{n}"] < x, lambda I, n=n, x=x: I[f"w_rsi{n}"] > 100 - x)
    d["W %R4<10"] = (lambda I: I["w_wr4"] < 10, lambda I: I["w_wr4"] > 90)
    d["W %R4<20"] = (lambda I: I["w_wr4"] < 20, lambda I: I["w_wr4"] > 80)
    d["W 52-tydenni maximum"] = (lambda I: I["w_close"] >= I["w_hi52"], lambda I: I["w_close"] <= I["w_lo52"])
    d["W 13-tydenni pruraz"] = (lambda I: I["w_brk13"] > 0, lambda I: I["w_brk13"] < 0)
    d["W trend SMA10>SMA40"] = (lambda I: (I["w_close"] > I["w_sma10"]) & (I["w_sma10"] > I["w_sma40v"]),
                                lambda I: (I["w_close"] < I["w_sma10"]) & (I["w_sma10"] < I["w_sma40v"]))
    d["W kazdy tyden"] = (lambda I: I["week_end"], lambda I: I["week_end"])
    return d


def indicators(s: dict, rates: dict, symbol: str) -> dict:
    o, h, l, c = s["do"], s["dh"], s["dl"], s["dc"]
    atr = wilder(true_range(h, l, c), 14)
    I = ta_indicators(o, h, l, c, atr)
    I["atr"] = atr
    wk = weekly_aligned(s["days"], o, h, l, c)
    I["w_sma40v"] = wk["w_sma40"].copy()
    I.update(wk)
    I["w_sma40"] = np.sign(c - wk["w_sma40"])
    prev_hi, prev_lo = shift(rolling_max(h, 20)), shift(rolling_min(l, 20))
    I["brk20"] = np.where(c > prev_hi, 1, np.where(c < prev_lo, -1, 0))
    e20, e50 = ema(c, 20), ema(c, 50)
    diff = np.sign(e20 - e50)
    I["cross"] = np.where(diff != shift(diff), diff, 0)
    # weekly 13-week breakout on completed weeks (high/low of the 13 weeks before the current one)
    keys = [tuple(d.isocalendar()[:2]) for d in s["days"]]
    whi, wlo, order = {}, {}, []
    for k, hi, lo in zip(keys, h, l):
        if k not in whi:
            order.append(k)
            whi[k], wlo[k] = hi, lo
        whi[k], wlo[k] = max(whi[k], hi), min(wlo[k], lo)
    Hh, Ll = np.array([whi[k] for k in order]), np.array([wlo[k] for k in order])
    ph, pl = shift(rolling_max(Hh, 13)), shift(rolling_min(Ll, 13))
    pos = {k: i for i, k in enumerate(order)}
    I["w_brk13"] = np.array([1 if c[j] > ph[pos[k]] else -1 if c[j] < pl[pos[k]] else 0 for j, k in enumerate(keys)])
    inst = get_instrument(symbol)
    known, now, known_3m = [], [], []
    for d in s["days"]:
        rb, rq = rate_at(rates[inst.base], d.year, d.month, 2), rate_at(rates[inst.quote], d.year, d.month, 2)
        known.append(np.nan if rb is None or rq is None else rb - rq)
        rb3, rq3 = rate_at(rates[inst.base], d.year, d.month, 5), rate_at(rates[inst.quote], d.year, d.month, 5)
        known_3m.append(np.nan if rb3 is None or rq3 is None else rb3 - rq3)
        nb, nq = rate_at(rates[inst.base], d.year, d.month, 1), rate_at(rates[inst.quote], d.year, d.month, 1)
        now.append(np.nan if nb is None or nq is None else nb - nq)
    I["carry"] = np.array(known)
    I["carry_fin"] = np.nan_to_num(np.array(now))
    I["rates_mom"] = np.array(known) - np.array(known_3m)
    return I
