"""Deep check of the round-2 finalists (docs/ZISK10_K2.md): trade-by-trade
simulation on hourly bars with one open position per pair, per year / per
pair, week-clustered t, delayed entry, rate-signal variants, portfolio.

    python scripts/profit_deep.py           # -> docs/ZISK10_OVERENI.md
"""

import hashlib
import os
import pickle
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import json

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import fxcm_universe as U  # noqa: E402
import profit_lab2 as P  # noqa: E402
from src.instruments import get_instrument  # noqa: E402

UTC = timezone.utc


@dataclass(frozen=True)
class Rule:
    name: str
    signal: str = "D RSI2<5"          # key of profit_lab2.signal_defs()
    weekly: bool = True               # decide only at the week close
    weekday: int = -1                 # 0-4 = decide only on this weekday's close (overrides weekly)
    weekdays: tuple = ()              # decide only on these weekdays' closes (overrides weekday and weekly)
    trend: str | None = None
    fund: str | None = "rates_up"
    rates_lag: int = 2                # months: rate known at the decision
    rates_window: int = 3             # months of the rate-difference change
    rates_thr: float = 0.25           # percentage points
    limit_atr: float = 0.0            # 0 = market at the close
    tp: float = 0.75                  # ATR
    sl: float = 3.0                   # ATR
    hold_days: int = 20
    delay_h: int = 0                  # execute this many hours after the close
    one_per_pair: bool = True
    min_tp_pct: float = P.MIN_TP_PCT                  # minimum target in % of the price at 1:30 (= 10 % of the margin)
    min_tp_price: bool = False        # True: the same minimum price move for every pair (1:20 pairs: < 10 % of the margin)
    early_h: int = 0                  # decide and enter this many hours before the daily close (every day cut)
    decide_h: int = 0                 # live timing: decide and enter this many hours before the decision day's close,
                                      # earlier days keep their full closes (the live run at 16:05 New York = 1)
    cost_x: float = 1.0               # spread + slippage multiplier
    rates_src: str = "oecd"           # "oecd" = monthly 3m interbank (FRED), "y2" = daily 2y yields (fundamentals DB)
    max_sl_margin: float = 1e9        # skip trades whose stop is wider than this % of the margin
    exit_kind: str = "ATR"            # "ATR" = tp/sl in ATR multiples, "PCT" = tp/sl in % of the price
    max_vix: float = 1e9              # no new trade when the VIX close of the decision day is above this
    max_vix_rise: float = 1e9         # ... or when it rose more than this (points) over 5 trading days
    be_atr: float = 0.0               # > 0: after a favourable move of be_atr x ATR the stop moves to the entry
    stall_days: int = 0               # > 0: close at the end of this trading day if the trade is not in profit
    confirm_src: str = ""             # second rate measure that must point the same way ("policylag")
    max_cot: float = 1e9              # skip when speculators are crowded in the trade direction (COT z-score diff)
    # news (scripts/fundamenty.py: scheduled central bank decisions FED/ECB/BOJ/BOE, US NFP / CPI release days)
    skip_cb_week: bool = False        # skip when either currency's central bank decided in the last 5 days
    skip_cb_ahead: int = 0            # skip when either currency's central bank decides within this many days
    skip_us_data: bool = False        # USD pairs: skip when NFP or CPI was released in the last 5 days
    max_jump_atr: float = 1e9         # skip when an hour of the last 2 days moved > x ATR (a news shock)
    min_jump_atr: float = 0.0         # only when such a shock happened
    cb_size: float = 1.0              # position size factor when a central bank of either currency decides within 7 days
    cb_week_size: float = 1.0         # position size factor when a central bank of either currency decided this week
    risk_contra: int = 0              # > 0: buy risk (AUD, NZD, CAD vs JPY, CHF) only after the S&P 500 fell over this
                                      # many days, sell it only after it rose (docs/KRATKE_OKNO.md)
    exit_before_cb: str = ""          # "vzdy" / "zisk": close at the NY close before a decision of either currency's
                                      # central bank (always / only when in profit); "fed_long_usd": only long-USD trades
                                      # before an FOMC decision (Mueller, Tahbaz-Salehi, Vedolin 2017: USD falls on FOMC days)
    vix_size: bool = False            # size factor 17 / VIX of the decision day, 0.5-1.5 (Moreira, Muir 2017)
    tp_parts: tuple = ()              # split the position into equal parts with these targets (ATR), e.g. (0.75, 1.0, 1.5)
    rsi_exit: float = 0.0             # > 0: close at a NY close once RSI(2) recovered above this (shorts: below 100 - x)
    exit_before_us: bool = False      # USD pairs: close in profit at the NY close before a US NFP / CPI release
    cb_all: bool = False              # exit_before_cb also before SNB (CHF) and RBA (AUD) decisions
    exit_friday_profit: bool = False  # close in profit at a Friday NY close (weekend gap risk), not on the entry day
    knife_days: int = 0               # > 0: do not buy a close that is the lowest of this many days (sell: highest)
    confirm_up: int = 0               # > 0: wait for the first NY close in the trade direction within this many trading
                                      # days after the signal and enter there (a trader's "wait until it turns")
    close_stop: float = 0.0           # > 0: the stop counts only at New York closes (a wick does not stop the trade);
                                      # intraday only a disaster stop at close_stop x the stop distance
    cb_tight: float = 0.0             # > 0: a trade in loss at the NY close before a decision of either currency's
                                      # central bank gets its stop tightened to this many ATR beyond that close
    decay_days: int = 0               # > 0: after this many trading days the target drops to decay_tp x ATR
    decay_tp: float = 0.0             # (a trader takes a smaller profit when the bounce is late)
    skip_holidays: bool = False       # no new trade from 15 December to 5 January (thin year-end market, wide spreads)
    tp_retrace: float = 0.0           # > 0: target = this share of the last 5 days' move against the trade
                                      # (0.5-1.5 ATR) instead of the fixed tp (a deeper fall, a bigger bounce)


_cache: dict = {}


def series_early(symbol: str, early: int) -> dict:
    """Daily bars that end `early` hours before the New York close: what is
    known at that moment (every day is cut the same way)."""
    s = dict(P.series(symbol))
    if not early:
        return s
    first, last = s["first"], s["last"] - early
    s["last"] = last
    s["dc"] = s["c"][last]
    s["dh"] = np.array([s["h"][a:b + 1].max() for a, b in zip(first, last)])
    s["dl"] = np.array([s["l"][a:b + 1].min() for a, b in zip(first, last)])
    s["close_ts"] = s["ts"][last] + 3600
    return s


SIM_START = 260                       # first decision day of simulate (a year of indicator history)
LIVE_WINDOW = 1000                    # days of history for the live-timing indicators (equal to the full series to 1e-9)
KNOWN_AT_DECISION = {"carry", "carry_fin", "rates_mom", "vix", "vix_rise", "week_end"}


def prepared_live(symbol: str, lag: int, window: int, src: str, cut: int, weekdays: tuple):
    """Indicators as the live run sees them `cut` hours before the close of each decision day (weekday in
    `weekdays`): the earlier days with their full closes, the decision day up to that hour (its high / low so
    far, its price at that hour as the close). Other days and the monthly / daily known inputs (rates, carry,
    VIX, the week end) are unchanged. Exact: every indicator is causal (tests) and LIVE_WINDOW days of history
    reproduce the full-series values (to < 1e-10, floating point)."""
    key = ("live", symbol, lag, window, src, cut, weekdays)
    if key not in _cache:
        s, I = prepared(symbol, lag, window, 0, src)
        J = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in I.items()}
        for k, (rows, values) in _live_rows(symbol, s, cut, weekdays).items():
            J[k][rows] = values
        _cache[key] = (s, J)
    return _cache[key]


def _live_rows(symbol: str, s: dict, cut: int, weekdays: tuple) -> dict:
    """{indicator: (decision-day rows, values)} of the price-based indicators at `cut` hours before the close;
    cached on disk, valid for the same price data and the same indicator code (hash of its source files)."""
    path = P.OUT / f"live_{symbol.replace('/', '')}_{cut}_{''.join(map(str, weekdays))}.pkl"
    code = b"".join((PROJECT_ROOT / "scripts" / f).read_bytes()
                    for f in ("profit_lab2.py", "profit_lab.py", "winrate_lab.py", "strategy_mining.py"))
    stamp = (hashlib.sha256(code).hexdigest(), LIVE_WINDOW, SIM_START, len(s["ts"]), int(s["ts"][-1]),
             float(s["c"][-1]), len(s["days"]))
    if path.exists():
        saved = pickle.loads(path.read_bytes())
        if saved["stamp"] == stamp:
            return saved["rows"]
    rates = _cache.setdefault("rates", P.monthly_rates())        # only for the call; rate keys are not taken
    found = defaultdict(lambda: ([], []))
    for i, d in enumerate(s["days"]):
        a, b = s["first"][i], s["last"][i] - cut
        if i < SIM_START or d.weekday() not in weekdays or b < a:
            continue
        lo = max(0, i - LIVE_WINDOW)
        pre = {"do": s["do"][lo:i + 1], "days": s["days"][lo:i + 1],
               "dh": np.append(s["dh"][lo:i], s["h"][a:b + 1].max()),
               "dl": np.append(s["dl"][lo:i], s["l"][a:b + 1].min()),
               "dc": np.append(s["dc"][lo:i], s["c"][b])}
        for k, v in P.indicators(pre, rates, symbol).items():
            if k not in KNOWN_AT_DECISION and isinstance(v, np.ndarray) and v.shape == (i + 1 - lo,):
                found[k][0].append(i)
                found[k][1].append(v[-1])
    rows = {k: (np.array(r, int), np.array(v)) for k, (r, v) in found.items()}
    P.OUT.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{os.getpid()}.tmp")                 # parallel learning runs: never a half-written file
    tmp.write_bytes(pickle.dumps({"stamp": stamp, "rows": rows}))
    os.replace(tmp, path)
    return rows


def y2_rates(symbol: str, close_ts: np.ndarray, window_months: int, lag_months: int = 0,
             kind: str = "short") -> tuple[np.ndarray, np.ndarray]:
    """Point-in-time difference of the short rates (2y yields; GBP 5y, CHF/NZD
    policy rate - src/fundamental/catalog.SHORT_RATE) at each close and its
    change over `window_months`."""
    import research_signals as RS
    from src.fundamental.catalog import SHORT_RATE
    fund = _cache.setdefault("fund", RS.Fundamentals())
    inst = get_instrument(symbol)
    back = int(window_months * 30.4 * 86400)
    lag = int(lag_months * 30.4 * 86400)
    ids = {c: (SHORT_RATE[c][0] if kind == "short" else f"{c}.POLICY") for c in (inst.base, inst.quote)}

    def diff(t):
        b, q = (fund.value(ids[c], int(t)) for c in (inst.base, inst.quote))
        return np.nan if b is None or q is None else b - q
    now = np.array([diff(t - lag) for t in close_ts])
    old = np.array([diff(t - lag - back) for t in close_ts])
    return now, now - old


def vix_on(days) -> tuple[np.ndarray, np.ndarray]:
    """VIX close (FRED VIXCLS, 16:15 New York, known at the 17:00 FX close) of
    each trading day and its change over the last 5 VIX closes."""
    import bisect

    import research_factors as RF
    if "vix" not in _cache:
        rows = RF._csv("VIXCLS")
        _cache["vix"] = ([d for d, _ in rows], np.array([v for _, v in rows]))
    dates, values = _cache["vix"]
    level, rise = [], []
    for d in days:
        k = bisect.bisect_right(dates, d) - 1
        level.append(values[k] if k >= 0 else np.nan)
        rise.append(values[k] - values[k - 5] if k >= 5 else np.nan)
    return np.array(level), np.array(rise)


def extra(symbol: str, s: dict, I: dict, what: str, rule) -> np.ndarray:
    """Lazily computed inputs: a second rate measure (confirm:<src>) or the
    COT crowding difference (base minus quote speculator z-score, 0 for USD)."""
    if what in I:
        return I[what]
    if what == "confirm:acc":                           # the rate divergence still widens: 3-month change now
        now = prepared(symbol, rule.rates_lag, 3, rule.early_h)[1]["rates_mom"]          # minus 3 months before
        before = prepared(symbol, rule.rates_lag + 3, 3, rule.early_h)[1]["rates_mom"]
        I[what] = now - before
    elif what == "confirm:une":                         # labour market: base unemployment falls vs the quote's
        I[what] = np.nan_to_num(unemployment_change(symbol, s["days"]))              # (6 months; no data = pass)
    elif what.startswith("rate_chg:"):                  # one currency's own OECD rate change (lag, window as the rule)
        rates = _cache.setdefault("rates", P.monthly_rates())
        inst = get_instrument(symbol)
        ccy = inst.base if what.endswith(":base") else inst.quote
        out = []
        for d in s["days"]:
            now = P.rate_at(rates[ccy], d.year, d.month, rule.rates_lag)
            old = P.rate_at(rates[ccy], d.year, d.month, rule.rates_lag + rule.rates_window)
            out.append(np.nan if now is None or old is None else now - old)
        I[what] = np.array(out)
    elif what.startswith("confirm:oecd"):                 # OECD rate difference change over another window (months)
        I[what] = prepared(symbol, rule.rates_lag, int(what.split("oecd")[1]), rule.early_h)[1]["rates_mom"]
    elif what.startswith("confirm:"):
        src = what.split(":", 1)[1]
        lag = rule.rates_lag if src.endswith("lag") else 0
        kind = "policy" if src.startswith("policy") else "short"
        I[what] = y2_rates(symbol, s["close_ts"], rule.rates_window, lag, kind)[1]
    elif what == "cot":
        import research_signals as RS
        fund = _cache.setdefault("fund", RS.Fundamentals())
        inst = get_instrument(symbol)

        def z(ccy, t):
            v = fund.currency(ccy, int(t))["cot_z"]
            return np.nan if v is None else v
        I[what] = np.array([z(inst.base, t) - z(inst.quote, t) for t in s["close_ts"]])
    return I[what]


def unemployment_change(symbol: str, days) -> np.ndarray:
    """-(6-month change of the base unemployment rate - that of the quote) known at each day (monthly data with a
    2-month lag, quarterly CHF / NZD with 4 months): > 0 = the base economy's labour market improves relatively."""
    import bisect

    import fundamenty as F
    une = _cache.setdefault("une", json.loads((F.MACRO / "macro.json").read_text())["unemployment"])
    inst = get_instrument(symbol)

    def at(ccy, y, m):
        series = une.get(ccy)
        if not series:
            return None
        lag = 4 if ccy in F.UNEMPLOYMENT_QUARTERLY else 2
        m -= lag
        while m <= 0:
            y, m = y - 1, m + 12
        keys = _cache.setdefault(("une_keys", ccy), sorted(series))
        k = bisect.bisect_right(keys, f"{y}-{m:02d}") - 1
        return series[keys[k]] if k >= 0 and int(keys[k][:4]) * 12 + int(keys[k][5:7]) >= y * 12 + m - 3 else None

    out = []
    for d in days:
        y0, m0 = (d.year, d.month - 6) if d.month > 6 else (d.year - 1, d.month + 6)
        vals = [at(inst.base, d.year, d.month), at(inst.base, y0, m0), at(inst.quote, d.year, d.month),
                at(inst.quote, y0, m0)]
        out.append(np.nan if None in vals else -((vals[0] - vals[1]) - (vals[2] - vals[3])))
    return np.array(out)


# months without a source for a central bank (scripts/fundamenty.py could not read them): no filter there
EVENT_GAPS = {"BOE": ("2015-08-01", "2016-12-31")}
RISK_SCORE = {"AUD": 1, "NZD": 1, "CAD": 1, "JPY": -1, "CHF": -1}     # textbook risk / safe-haven currencies


def _event_dates(names) -> list:
    import fundamenty as F
    ev = _cache.setdefault("events", F.load_events())
    return sorted({date.fromisoformat(d) for n in names for d in ev.get(n, [])})


def news(symbol: str, s: dict, I: dict, what: str) -> np.ndarray:
    """Lazily computed news inputs per decision day (see Rule)."""
    import bisect
    if what in I:
        return I[what]
    inst = get_instrument(symbol)
    import fundamenty as F
    banks = [F.CB_OF[c] for c in (inst.base, inst.quote) if c in F.CB_OF]
    days = s["days"]
    if what.startswith("cb_"):
        dates = _event_dates(banks)
        out = []                                              # EVENT_GAPS months count as no decision
        for d in days:
            if what == "cb_week":
                lo, hi = d - timedelta(days=4), d
            else:
                lo, hi = d + timedelta(days=1), d + timedelta(days=int(what.split(":")[1]))
            k = bisect.bisect_left(dates, lo)
            out.append(k < len(dates) and dates[k] <= hi)
        I[what] = np.array(out)
    elif what == "us_data":
        dates = _event_dates(["US_NFP", "US_CPI"]) if "USD" in (inst.base, inst.quote) else []
        out = []
        for d in days:
            k = bisect.bisect_left(dates, d - timedelta(days=4))
            out.append(k < len(dates) and dates[k] <= d)
        I[what] = np.array(out)
    elif what.startswith("sp500:"):
        import vyzkum_data as V
        k = int(what.split(":")[1])
        ser = _cache.setdefault("sp500", V.yahoo_daily("^GSPC"))
        keys = sorted(ser)
        out = np.full(len(days), np.nan)
        for i, d in enumerate(days):                          # last S&P close on or before the FX day
            j = bisect.bisect_right(keys, d) - 1
            if j >= k:
                out[i] = ser[keys[j]] / ser[keys[j - k]] - 1
        I[what] = out
    elif what == "next_us":
        dates = set(_event_dates(["US_NFP", "US_CPI"])) if "USD" in (inst.base, inst.quote) else set()
        I[what] = np.array([i + 1 < len(days) and days[i + 1] in dates for i in range(len(days))])
    elif what in ("next_decision", "next_fed", "next_decision_all"):
        if what == "next_decision_all":
            banks = [F.CB_OF_ALL[c] for c in (inst.base, inst.quote) if c in F.CB_OF_ALL]
        dates = set(_event_dates(["FED"] if what == "next_fed" else banks))
        I[what] = np.array([i + 1 < len(days) and days[i + 1] in dates for i in range(len(days))])
    elif what == "jump":
        rng = s["h"] - s["l"]
        first = s["first"]
        out = np.full(len(days), np.nan)
        for i in range(1, len(days)):
            out[i] = rng[first[i - 1]:s["last"][i] + 1].max() / I["atr"][i]
        I[what] = out
    return I[what]


def prepared(symbol: str, lag: int, window: int, early: int = 0, src: str = "oecd"):
    key = (symbol, lag, window, early, src)
    if key not in _cache:
        s = series_early(symbol, early)
        rates = _cache.setdefault("rates", P.monthly_rates())
        I = P.indicators(s, rates, symbol)
        inst = get_instrument(symbol)
        known, old = [], []
        for d in s["days"]:
            rb, rq = (P.rate_at(rates[c], d.year, d.month, lag) for c in (inst.base, inst.quote))
            ob, oq = (P.rate_at(rates[c], d.year, d.month, lag + window) for c in (inst.base, inst.quote))
            known.append(np.nan if rb is None or rq is None else rb - rq)
            old.append(np.nan if ob is None or oq is None else ob - oq)
        I["carry"] = np.array(known)
        I["rates_mom"] = np.array(known) - np.array(old)
        I["vix"], I["vix_rise"] = vix_on(s["days"])
        if src == "y2":
            I["carry"], I["rates_mom"] = y2_rates(symbol, s["close_ts"], window)
        elif src == "y2lag":
            I["carry"], I["rates_mom"] = y2_rates(symbol, s["close_ts"], window, lag)
        elif src == "policy":
            I["carry"], I["rates_mom"] = y2_rates(symbol, s["close_ts"], window, 0, "policy")
        elif src == "policylag":
            I["carry"], I["rates_mom"] = y2_rates(symbol, s["close_ts"], window, lag, "policy")
        _cache[key] = (s, I)
    return _cache[key]


def fomc_addon(symbols) -> list[dict]:
    """Add-on trades (Mueller, Tahbaz-Salehi, Vedolin 2017): short USD against each currency from the New
    York close before a scheduled FOMC decision to the close of the decision day (docs/ANOMALIE.md)."""
    fed = set(_event_dates(["FED"]))
    trades = []
    for symbol in symbols:
        inst = get_instrument(symbol)
        if "USD" not in (inst.base, inst.quote):
            continue
        s = P.series(symbol)
        side = -1 if inst.base == "USD" else 1
        half = (P.SPREAD_PIPS[symbol] / 2 + P.SLIPPAGE_PIPS / 2) * inst.pip
        for i in range(1, len(s["days"])):
            if s["days"][i] not in fed:
                continue
            k0, k1 = s["last"][i - 1], s["last"][i]
            entry = s["c"][k0] + side * half
            out = s["c"][k1] - side * half
            pct = side * (out - entry) / entry * 100
            trades.append({"pair": symbol, "side": side, "day": s["days"][i - 1], "entry": entry,
                           "t_in": int(s["ts"][k0]) + 3600, "t_out": int(s["ts"][k1]) + 3600, "reason": "FOMC",
                           "price_pct": pct, "margin_pct": pct * P.leverage(symbol), "days": 1.0, "tp_pct": 0.0,
                           "sl_pct": 84.0, "mfe_atr": 0.0, "marks": []})
    return sorted(trades, key=lambda t: t["t_in"])


def scale_addon(base: list[dict], k_atr: float, tp_atr: float = 0.75, sl_atr: float = 4.0, hold_days: int = 20,
                exit_before_cb: str = "zisk") -> list[dict]:
    """Scale-in (a trader averages a good dip down): for every base trade a limit order k_atr x ATR beyond its
    entry, valid while the base trade is open; filled -> a second position with its own target tp_atr x ATR,
    the same stop price and time limit as the base trade and the same exit in profit before a central bank
    decision. Flagged "stack": the account takes it only together with its base trade."""
    out = []
    for t in base:
        pair, side = t["pair"], t["side"]
        s, I = prepared(pair, 2, 3)
        inst = get_instrument(pair)
        half = (P.SPREAD_PIPS[pair] / 2 + P.SLIPPAGE_PIPS / 2) * inst.pip
        ts, hh, hl, hc = s["ts"], s["h"], s["l"], s["c"]
        i = s["days"].index(t["day"])
        atr = I["atr"][i]
        k_in = int(np.searchsorted(ts, t["t_in"]))
        end = min(k_in + P.HOLD_BARS.get(hold_days, 24 * hold_days), int(np.searchsorted(ts, t["t_out"] - 3600)))
        level = t["entry"] - side * k_atr * atr
        fill = next((j for j in range(k_in + 1, end + 1)
                     if (hl[j] + half <= level if side > 0 else hh[j] - half >= level)), None)
        if fill is None:
            continue
        TP, SL = tp_atr * atr, (sl_atr - k_atr) * atr
        is_close = np.zeros(len(ts), bool)
        is_close[s["last"]] = True
        cb_next = news(pair, s, I, "next_decision") if exit_before_cb else None
        day_of = np.searchsorted(s["last"], np.arange(len(ts)))
        entry, reason, exit_k, result, best, marks = level, "CAS", end, None, 0.0, []
        for j in range(fill, end + 1):
            adv = (entry - (hl[j] - half)) if side > 0 else ((hh[j] + half) - entry)
            fav = (hh[j] - half - entry) if side > 0 else (entry - (hl[j] + half))
            if adv >= SL:
                reason, exit_k, result = "SL", j, -SL
                break
            if j > fill and fav >= TP:
                reason, exit_k, result = "TP", j, TP
                break
            best = max(best, fav)
            if is_close[j]:
                now_close = (hc[j] - half - entry) if side > 0 else (entry - (hc[j] + half))
                marks.append((int(ts[j]) + 3600, now_close / entry * 100))
                if exit_before_cb == "zisk" and j > fill and cb_next[day_of[j]] and now_close > 0:
                    reason, exit_k, result = "CB", j, now_close
                    break
        if result is None:
            result = (hc[end] - half - entry) if side > 0 else (entry - (hc[end] + half))
        held = (ts[exit_k] + 3600 - ts[fill]) / 86400
        fin = (side * I["carry_fin"][i] - P.FIN_MARKUP) / 100 / 365 * held * entry
        pct = (result + fin) / entry * 100
        out.append({"pair": pair, "side": side, "day": t["day"], "entry": entry, "t_in": int(ts[fill]),
                    "t_out": int(ts[exit_k]) + 3600, "reason": reason, "price_pct": pct,
                    "margin_pct": pct * P.leverage(pair), "days": held, "tp_pct": TP / entry * 100 * P.leverage(pair),
                    "sl_pct": SL / entry * 100 * P.leverage(pair), "mfe_atr": best / atr,
                    "marks": [(m, v * P.leverage(pair)) for m, v in marks if m < int(ts[exit_k]) + 3600],
                    "size_factor": t.get("size_factor", 1.0), "stack": True, "base": (pair, t["t_in"])})
    return out


def simulate(rule: Rule, symbols=None) -> list[dict]:
    defs = P.signal_defs()
    trades = []
    if rule.decide_h and (rule.early_h or rule.limit_atr or rule.knife_days or rule.confirm_up or rule.tp_retrace):
        raise NotImplementedError("decide_h: these options use the decision day's full close")
    decision_days = (rule.weekdays or ((rule.weekday,) if rule.weekday >= 0 else (4,) if rule.weekly else tuple(range(7))))
    for symbol in symbols or U.universe():
        if rule.decide_h:
            s, I = prepared_live(symbol, rule.rates_lag, rule.rates_window, rule.rates_src, rule.decide_h,
                                 tuple(decision_days))
        else:
            s, I = prepared(symbol, rule.rates_lag, rule.rates_window, rule.early_h, rule.rates_src)
        inst = get_instrument(symbol)
        half = (P.SPREAD_PIPS[symbol] / 2 + P.SLIPPAGE_PIPS / 2) * inst.pip * rule.cost_x
        lev = P.leverage(symbol)
        min_tp = rule.min_tp_pct * (1.0 if rule.min_tp_price else P.LEVERAGE / lev)   # same % of the margin by default
        ts, hh, hl, hc = s["ts"], s["h"], s["l"], s["c"]
        L = P.HOLD_BARS.get(rule.hold_days, 24 * rule.hold_days)
        busy_until = -1
        is_close = np.zeros(len(ts), bool)
        is_close[s["last"]] = True                              # New York close bars: daily marks
        if rule.exit_before_cb:
            cb_next = news(symbol, s, I, "next_fed" if rule.exit_before_cb == "fed_long_usd"
                           else "next_decision_all" if rule.cb_all else "next_decision")
        if rule.exit_before_us:
            us_next = news(symbol, s, I, "next_us")
        if rule.exit_before_cb or rule.exit_before_us or rule.exit_friday_profit:
            day_of = np.searchsorted(s["last"], np.arange(len(ts)))
        names = rule.signal.split("|")
        signal = {sd: np.logical_or.reduce([np.nan_to_num(defs[nm][0 if sd > 0 else 1](I)).astype(bool)
                                            for nm in names]) for sd in (1, -1)}
        for i in range(SIM_START, len(s["days"]) - 1):
            if rule.weekdays:
                if s["days"][i].weekday() not in rule.weekdays:
                    continue
            elif rule.weekday >= 0:
                if s["days"][i].weekday() != rule.weekday:
                    continue
            elif rule.weekly and not I["week_end"][i]:
                continue
            if rule.skip_holidays:
                d = s["days"][i]
                if (d.month == 12 and d.day >= 15) or (d.month == 1 and d.day <= 5):
                    continue
            atr = I["atr"][i]
            if np.isnan(atr):
                continue
            for side in (1, -1):
                if not signal[side][i]:
                    continue
                if rule.trend and I[rule.trend][i] != side:
                    continue
                if I["vix"][i] > rule.max_vix or I["vix_rise"][i] > rule.max_vix_rise:
                    continue
                if rule.confirm_src in ("own", "both"):     # the bought currency's rate not falling (both: and the
                    db, dq = extra(symbol, s, I, "rate_chg:base", rule), extra(symbol, s, I, "rate_chg:quote", rule)
                    bought, sold = (db[i], dq[i]) if side > 0 else (dq[i], db[i])     # sold one's not rising)
                    if not (bought >= 0 and (rule.confirm_src == "own" or sold <= 0)):
                        continue
                elif rule.confirm_src and not (side * extra(symbol, s, I, "confirm:" + rule.confirm_src, rule)[i] >= 0):
                    continue
                if rule.max_cot < 1e9 and side * extra(symbol, s, I, "cot", rule)[i] > rule.max_cot:
                    continue
                if rule.skip_cb_week and news(symbol, s, I, "cb_week")[i]:
                    continue
                if rule.skip_cb_ahead and news(symbol, s, I, f"cb_ahead:{rule.skip_cb_ahead}")[i]:
                    continue
                if rule.skip_us_data and news(symbol, s, I, "us_data")[i]:
                    continue
                if rule.max_jump_atr < 1e9 and not news(symbol, s, I, "jump")[i] <= rule.max_jump_atr:
                    continue
                if rule.min_jump_atr and not news(symbol, s, I, "jump")[i] >= rule.min_jump_atr:
                    continue
                if rule.knife_days and i >= rule.knife_days:
                    window = s["dc"][i - rule.knife_days:i]
                    if (side > 0 and s["dc"][i] < window.min()) or (side < 0 and s["dc"][i] > window.max()):
                        continue
                if rule.risk_contra:
                    risk = RISK_SCORE.get(inst.base, 0) - RISK_SCORE.get(inst.quote, 0)
                    sp = news(symbol, s, I, f"sp500:{rule.risk_contra}")[i]
                    if risk and not (side * risk * sp <= 0):       # NaN (no S&P close) also skips
                        continue
                if rule.fund == "rates_up" and not (side * I["rates_mom"][i] >= rule.rates_thr):
                    continue
                if rule.fund == "carry" and not (np.sign(I["carry"][i]) == side):
                    continue
                if rule.fund == "carry2" and not (side * I["carry"][i] >= 2.0):
                    continue
                if rule.fund == "rates_or_carry" and not (side * I["rates_mom"][i] >= rule.rates_thr
                                                          or np.sign(I["carry"][i]) == side):
                    continue
                if rule.fund == "rates_up+carry" and not (side * I["rates_mom"][i] >= rule.rates_thr
                                                          and np.sign(I["carry"][i]) == side):
                    continue
                k0 = s["last"][i] - rule.decide_h + rule.delay_h
                if rule.confirm_up:
                    turn = next((m for m in range(1, rule.confirm_up + 1) if i + m < len(s["days"])
                                 and side * (s["dc"][i + m] - s["dc"][i + m - 1]) > 0), None)
                    if turn is None:
                        continue
                    k0 = s["last"][i + turn] + rule.delay_h
                if rule.one_per_pair and k0 <= busy_until:
                    continue
                if k0 + 121 + L >= len(ts) or ts[k0 + 120 + L] - ts[k0] > ((L + 120) / 120 * 7 + 4) * 86400:
                    continue                                    # data hole ahead: outcome unknown
                if rule.limit_atr:
                    level = s["dc"][i] - side * rule.limit_atr * atr
                    window = 120 if rule.weekly else 24
                    fill = next((j for j in range(k0 + 1, k0 + 1 + window)
                                 if (hl[j] - half <= level if side > 0 else hh[j] + half >= level)), None)
                    if fill is None:
                        continue
                    entry, first = level, fill + 1
                    adv0 = (entry - (hl[fill] - half)) if side > 0 else ((hh[fill] + half) - entry)
                else:
                    fill = k0
                    entry, first, adv0 = hc[k0] + side * half, k0 + 1, 0.0
                if rule.exit_kind == "PCT":
                    TP, SL = rule.tp / 100 * entry, rule.sl / 100 * entry
                else:
                    TP, SL = rule.tp * atr, rule.sl * atr
                    if rule.tp_retrace and i >= 5:
                        TP = float(np.clip(rule.tp_retrace * side * (s["dc"][i - 5] - s["dc"][i]), 0.5 * atr, 1.5 * atr))
                if TP / entry * 100 < min_tp - 1e-9 or SL / entry * 100 * lev > rule.max_sl_margin:
                    continue
                # the position may be split into parts with their own targets (rule.tp_parts, in ATR); one part = TP
                parts = [x * atr for x in rule.tp_parts] if rule.tp_parts else [TP]
                n_parts = len(parts)
                part_res, part_exit = [None] * n_parts, [None] * n_parts
                reason, exit_k = "CAS", first + L - 1
                stop, best = SL, 0.0
                marks = []                                       # (NY close ts, open result in % of the price)

                def close_open(value, k, why):
                    for q in range(n_parts):
                        if part_res[q] is None:
                            part_res[q], part_exit[q] = value, k
                    return why
                for j in range(first, first + L):
                    fav = (hh[j] - half - entry) if side > 0 else (entry - (hl[j] + half))
                    adv = (entry - (hl[j] - half)) if side > 0 else ((hh[j] + half) - entry)
                    if j == first:
                        adv = max(adv, adv0)
                    if rule.close_stop and stop == SL:
                        if adv >= SL * rule.close_stop:
                            reason = close_open(-SL * rule.close_stop, j, "SL")
                            break
                        if is_close[j]:
                            on_close = (entry - (hc[j] - half)) if side > 0 else ((hc[j] + half) - entry)
                            if on_close >= SL:
                                reason = close_open(-on_close, j, "SL")
                                break
                    elif adv >= stop:
                        reason = close_open(-stop, j, "SL" if stop == SL else "BE")
                        break
                    late = rule.decay_days and j >= first + rule.decay_days * 24
                    for q in range(n_parts):
                        target = min(parts[q], rule.decay_tp * atr) if late else parts[q]
                        if part_res[q] is None and fav >= target:
                            part_res[q], part_exit[q] = target, j
                    if all(x is not None for x in part_res):
                        reason = "TP"
                        break
                    best = max(best, fav)
                    if is_close[j]:
                        now_close = (hc[j] - half - entry) if side > 0 else (entry - (hc[j] + half))
                        whole = sum(now_close if x is None else x for x in part_res) / n_parts
                        marks.append((int(ts[j]) + 3600, whole / entry * 100))
                        usd_long = (inst.base == "USD") == (side > 0) and "USD" in (inst.base, inst.quote)
                        if rule.exit_before_cb and j > first and cb_next[day_of[j]] and \
                                (rule.exit_before_cb == "vzdy" or (rule.exit_before_cb == "zisk" and now_close > 0)
                                 or (rule.exit_before_cb == "fed_long_usd" and usd_long)):
                            reason = close_open(now_close, j, "CB")
                            break
                        if rule.rsi_exit and j > first:          # the pullback has reverted: the edge is used up
                            r2 = I["rsi2"][day_of[j]]
                            if (side > 0 and r2 > rule.rsi_exit) or (side < 0 and r2 < 100 - rule.rsi_exit):
                                reason = close_open(now_close, j, "RSI")
                                break
                        if rule.cb_tight and j > first and cb_next[day_of[j]] and now_close <= 0:
                            stop = min(stop, -now_close + rule.cb_tight * atr)
                        if now_close > 0 and j > first and (
                                (rule.exit_before_us and us_next[day_of[j]])
                                or (rule.exit_friday_profit and s["days"][day_of[j]].weekday() == 4)):
                            reason = close_open(now_close, j, "EVENT")
                            break
                    if rule.be_atr and best >= rule.be_atr * atr:
                        stop = 0.0                               # from the next hour: out at the entry price
                    if rule.stall_days and j == first + rule.stall_days * 24 - 1:
                        now = (hc[j] - half - entry) if side > 0 else (entry - (hc[j] + half))
                        if now <= 0:
                            reason = close_open(now, j, "STALL")
                            break
                if any(x is None for x in part_res):             # time exit of what is still open
                    close_open((hc[exit_k] - half - entry) if side > 0 else (entry - (hc[exit_k] + half)), exit_k, reason)
                result = float(np.mean(part_res))
                exit_k = max(part_exit)
                held = float(np.mean([(ts[k] + 3600 - ts[fill]) / 86400 for k in part_exit]))
                fin = (side * I["carry_fin"][i] - P.FIN_MARKUP) / 100 / 365 * held * entry
                pct = (result + fin) / entry * 100
                trades.append({"pair": symbol, "side": side, "day": s["days"][i], "entry": entry,
                               "t_in": int(ts[fill]), "t_out": int(ts[exit_k]) + 3600, "reason": reason,
                               "price_pct": pct, "margin_pct": pct * lev, "days": held,
                               "tp_pct": TP / entry * 100 * lev, "sl_pct": SL / entry * 100 * lev,
                               "mfe_atr": best / atr,               # best move for the trade before its exit
                               "rm": float(side * I["rates_mom"][i]),   # rate-difference change for the trade
                               "marks": [(m, v * lev) for m, v in marks if m < int(ts[exit_k]) + 3600],
                               "size_factor": (rule.cb_size if rule.cb_size != 1.0 and news(symbol, s, I, "cb_ahead:7")[i]
                                               else 1.0)
                               * (rule.cb_week_size if rule.cb_week_size != 1.0 and news(symbol, s, I, "cb_week")[i]
                                  else 1.0)
                               * (float(np.clip(17.0 / I["vix"][i], 0.5, 1.5)) if rule.vix_size and I["vix"][i] > 0
                                  else 1.0)})
                busy_until = exit_k
    return sorted(trades, key=lambda t: t["t_in"])


def summary(trades: list[dict]) -> dict:
    if not trades:
        return {"n": 0}
    x = np.array([t["margin_pct"] for t in trades])
    weeks = defaultdict(float)
    for t, v in zip(trades, x):
        weeks[tuple(t["day"].isocalendar()[:2])] += v - x.mean()
    se = np.sqrt(sum(v * v for v in weeks.values())) / len(x)
    return {"n": len(x), "win": float((x > 0).mean()), "e": float(x.mean()), "t": float(x.mean() / se) if se else 0,
            "worst": float(x.min()), "tp_share": sum(t["reason"] == "TP" for t in trades) / len(x),
            "days": float(np.mean([t["days"] for t in trades]))}


def fmt(sm: dict) -> str:
    if not sm["n"]:
        return "0"
    return f"{sm['n']} / {sm['win']:.0%} / {sm['e']:+.1f} % (t {sm['t']:.1f})"


def by_period(trades):
    return {p: summary([t for t in trades if a <= t["day"] <= b]) for p, (a, b) in P.PERIODS.items()}


def portfolio(trades: list[dict], margin_share: float) -> dict:
    """Each trade ties up margin_share of the current equity (as margin);
    the account result of a trade = margin_share x its % of the margin."""
    events = sorted([(t["t_in"], 0, k) for k, t in enumerate(trades)] + [(t["t_out"], 1, k) for k, t in enumerate(trades)])
    equity, peak, max_dd, open_now, max_open = 1.0, 1.0, 0.0, {}, 0
    yearly = defaultdict(lambda: [None, None])
    for when, kind, k in events:
        year = datetime.fromtimestamp(when, tz=UTC).year
        if yearly[year][0] is None:
            yearly[year][0] = equity
        if kind == 0:
            open_now[k] = equity * margin_share
            max_open = max(max_open, len(open_now))
        else:
            stake = open_now.pop(k)
            equity += stake * trades[k]["margin_pct"] / 100
            peak = max(peak, equity)
            max_dd = max(max_dd, 1 - equity / peak)
        yearly[year][1] = equity
    years = (trades[-1]["t_out"] - trades[0]["t_in"]) / 86400 / 365.25
    return {"final": equity, "cagr": equity ** (1 / years) - 1 if equity > 0 else -1, "max_dd": max_dd,
            "max_open": max_open, "yearly": {y: v[1] / v[0] - 1 for y, v in sorted(yearly.items())}}


FINALISTS = [
    Rule("F1 tydenni RSI2<5 + sazby (trh, TP 0.75 / SL 3 ATR, 20 d)"),
    Rule("F2 denni %R14<10 + sazby (limit 1 ATR, TP 0.75 / SL 4 ATR, 20 d)", signal="D %R14<10", weekly=False,
         limit_atr=1.0, tp=0.75, sl=4.0),
    Rule("F3 tydenni RSI3<15 + sazby (trh, TP 0.75 / SL 3 ATR, 20 d)", signal="D RSI3<15"),
    Rule("F4 tydenni RSI2<5 + sazby (trh, TP 1 / SL 3 ATR, 20 d)", tp=1.0),
    Rule("F5 tydenni RSI2<5 + sazby + carry (trh, TP 0.75 / SL 3 ATR, 20 d)", fund="rates_up+carry"),
    Rule("F6 = F1, jen kdyz cil >= 15 % marze", min_tp_pct=0.5),
    Rule("F7 = F5, jen kdyz cil >= 15 % marze", fund="rates_up+carry", min_tp_pct=0.5),
]


def main() -> int:
    started = time.monotonic()
    out = ["# Overeni finalistu kola 2 (zisk >= 10 % marze na obchod)", "",
           "_Obchod po obchodu na hodinovych BID/ASK svickach FXCM 2012-2026, 25 paru, vzdy nejvyse jedna otevrena "
           "pozice na par, naklady = retail spread + 0.4 pip skluz, swap podle rozdilu sazeb -/+ 1 % p.a.; vysledky v % "
           "marze pri pace 1:30; t = t-statistika se shlukovanim po tydnech._", ""]
    all_trades = {}
    for rule in FINALISTS:
        trades = simulate(rule)
        all_trades[rule.name] = trades
        per = by_period(trades)
        sm = summary(trades)
        out += [f"## {rule.name}", "",
                f"Celkem {fmt(sm)}; TP zasazen u {sm['tp_share']:.0%}, prumerne drzeni {sm['days']:.1f} dne, "
                f"cil obchodu prumerne {np.mean([t['tp_pct'] for t in trades]):.0f} % marze, stop "
                f"{np.mean([t['sl_pct'] for t in trades]):.0f} % marze, nejhorsi obchod {sm['worst']:.0f} % marze.", "",
                "| obdobi | n / uspesnost / zisk na obchod |", "|---|---|"]
        out += [f"| {p} | {fmt(per[p])} |" for p in P.PERIODS] + [""]
        years = sorted({t["day"].year for t in trades})
        out += ["| rok | " + " | ".join(str(y) for y in years) + " |", "|---" * (len(years) + 1) + "|"]
        ys = [summary([t for t in trades if t["day"].year == y]) for y in years]
        out += ["| n | " + " | ".join(str(y["n"]) for y in ys) + " |",
                "| uspesnost | " + " | ".join(f"{y['win']:.0%}" for y in ys) + " |",
                "| zisk/obchod | " + " | ".join(f"{y['e']:+.0f}" for y in ys) + " |", ""]
        pairs = defaultdict(list)
        for t in trades:
            pairs[t["pair"]].append(t)
        pos = sum(1 for v in pairs.values() if summary(v)["e"] > 0)
        out += [f"Paru se ziskem: {pos} z {len(pairs)}; BUY {fmt(summary([t for t in trades if t['side'] > 0]))}, "
                f"SELL {fmt(summary([t for t in trades if t['side'] < 0]))}.", ""]
        # robustness variants
        variants = [("rozhodnuti a vstup 1 h pred zaverem", replace(rule, early_h=1)),
                    ("rozhodnuti a vstup 2 h pred zaverem", replace(rule, early_h=2)),
                    ("vstup o 1 h pozdeji", replace(rule, delay_h=1)),
                    ("vstup o 3 h pozdeji", replace(rule, delay_h=3)),
                    ("sazby zname az o 3 mesice zpet", replace(rule, rates_lag=3)),
                    ("zmena sazeb za 6 mesicu", replace(rule, rates_window=6)),
                    ("prah zmeny sazeb 0.1 p.b.", replace(rule, rates_thr=0.1)),
                    ("prah zmeny sazeb 0.5 p.b.", replace(rule, rates_thr=0.5)),
                    ("i prekryvajici se obchody", replace(rule, one_per_pair=False)),
                    ("naklady 2x", replace(rule, cost_x=2.0)),
                    ("stop nejvyse 100 % marze (jinak neobchodovat)", replace(rule, max_sl_margin=100)),
                    ("sazby = denni vynosy 2y (od 2014)", replace(rule, rates_src="y2")),
                    ("sazby = vynosy 2y o 2 mesice zpet", replace(rule, rates_src="y2lag")),
                    ("sazby = sazby centralnich bank", replace(rule, rates_src="policy")),
                    ("sazby = sazby CB o 2 mesice zpet", replace(rule, rates_src="policylag")),
                    ("cil >= 15 % marze (0.5 % ceny)", replace(rule, min_tp_pct=0.5)),
                    ("cil >= 20 % marze (0.667 % ceny)", replace(rule, min_tp_pct=2 / 3)),
                    ("+ carry souhlasi", replace(rule, fund="rates_up+carry")),
                    ("bez podminky sazeb (kontrola)", replace(rule, fund=None)),
                    ("jen sazby, bez propadu (kontrola)", replace(rule, signal="W kazdy tyden"))]
        out += ["| varianta | 2012-18 | 2019-22 | 2023-26 |", "|---|---|---|---|"]
        for label, v in variants:
            pv = by_period(simulate(v))
            out.append(f"| {label} | " + " | ".join(fmt(pv[p]) for p in P.PERIODS) + " |")
        out += [""]
        out += ["| marze na obchod (podil uctu) | konecny ucet (z 1.0) | rocne | max. propad | max. soucasne otevrenych |",
                "|---|---|---|---|---|"]
        for share in (0.05, 0.10, 0.20):
            pf = portfolio(trades, share)
            out.append(f"| {share:.0%} | {pf['final']:.2f} | {pf['cagr']:+.1%} | {pf['max_dd']:.1%} | {pf['max_open']} |")
        out += [""]
        print(f"{rule.name}: {time.monotonic() - started:.0f} s", flush=True)
    out += [f"_vypocet {time.monotonic() - started:.0f} s_"]
    (PROJECT_ROOT / "docs" / "ZISK10_OVERENI.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    import pickle
    (P.OUT / "deep_trades.pkl").write_bytes(pickle.dumps(all_trades))
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
