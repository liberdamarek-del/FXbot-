"""Bridge between the weekly research (scripts/tydenni_analyza.py) and the trading model (user's request
2026-10-04: "připoj to do našeho modelu").

The research finds, per pair, daily technical conditions with a stable 5-day forward effect, and event days
(Fed / ECB / BoJ / BoE decisions, US NFP / CPI) on which a technical state predicted the direction. The model
can use them in three ways, each an experiment of the walk-forward gate (scripts/self_learn.py), never directly:

    filtr  - the model's Friday trade is skipped (or halved) when the research conditions active at the decision
             point against it on balance; "posila" also enlarges trades the research supports
    udalosti - add-on trades on event days: from the New York close before the event to the event day's close
               (stop 2 ATR), when the pair's technical state at that close is one the research confirmed

No look-ahead: for each test period of the gate the research selection uses only data whose outcome was known
before that period (split 0: selection to 2018 -> test 2019-2022; split 1: to 2022 -> test 2023-2026); live
signals use the selection on everything known before the decision. Conditions are kept only when ROBUST
(neighbouring settings keep the effect).
"""

import sys
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import indikatory as K  # noqa: E402
import profit_lab2 as P  # noqa: E402
import tydenni_analyza as T  # noqa: E402
from src.instruments import get_instrument  # noqa: E402

UTC = timezone.utc
SPLIT_ENDS = {0: date(2018, 12, 31), 1: date(2022, 12, 31)}      # selection ends of self_learn.SPLITS
TOP = 20
EVENTS = (("FED", "USD"), ("ECB", "EUR"), ("BOJ", "JPY"), ("BOE", "GBP"), ("US_NFP", "USD"), ("US_CPI", "USD"))
EVENT_MIN_N, EVENT_MIN_T = 15, 2.0
EVENT_SL_ATR = 2.0

_cache: dict = {}


def end_ts(d: date) -> int:
    return int(datetime(d.year, d.month, d.day, 23, 59, tzinfo=UTC).timestamp())


# ----------------------------------------------------------------------
# daily technical conditions
# ----------------------------------------------------------------------

def daily_bars(pair: str) -> dict:
    """Daily bars at the New York close of the model's own price series (FXCM hourly), with day labels."""
    if ("bars", pair) not in _cache:
        s = P.series(pair)
        _cache[("bars", pair)] = {"ts": s["ts"][s["first"]].astype(np.int64), "o": s["do"], "h": s["dh"], "l": s["dl"],
                                  "c": s["dc"], "close_ts": s["ts"][s["last"]].astype(np.int64) + 3600,
                                  "day": list(s["days"]), "sec": 86400}
    return _cache[("bars", pair)]


def daily_dataset(pair: str) -> "T.Dataset":
    if ("ds", pair) not in _cache:
        _cache[("ds", pair)] = T.Dataset(pair, "1D", daily_bars(pair), {}, {})
    return _cache[("ds", pair)]


def lock_on(ds: "T.Dataset", until_ts: int, robust_only: bool = True) -> list[tuple]:
    """The research selection on samples whose 5-day outcome was known by until_ts: (Cond, direction, t), the
    best ROBUST condition of each indicator family (eight MACD settings are one piece of information, one vote)."""
    sel = ds.t_end <= until_ts
    out, families = [], set()
    for r, d, t in T.select(ds, sel, ds.M, 4 * TOP, "year"):
        fam = T.family(ds.conds[r])
        if fam in families:
            continue
        if robust_only and T.robustness(ds, (r,), d, sel)["stav"] != "ROBUST":
            continue
        families.add(fam)
        out.append((ds.conds[r], d, t))
    return out


def locked(pair: str, until: date) -> list[tuple]:
    key = ("lock", pair, until)
    if key not in _cache:
        _cache[key] = lock_on(daily_dataset(pair), end_ts(until))
    return _cache[key]


def votes(pair: str, conds: list[tuple], bars: dict | None = None) -> dict:
    """{day: (directions of the locked conditions active at that day's close)} on the given daily bars."""
    bars = bars or daily_bars(pair)
    b = K.Builder(bars)
    acc = np.zeros((len(bars["c"]), 2), int)                      # [bullish, bearish] votes per day
    for cnd, d, _ in conds:
        m = b.mask(cnd)
        acc[m, 0 if d > 0 else 1] += 1
    return {day: (int(acc[i, 0]), int(acc[i, 1])) for i, day in enumerate(bars["day"])}


def tag_trades(lists: list[list[dict]], k: int) -> None:
    """For gate split k: research votes for / against each trade at its decision day (selection to SPLIT_ENDS[k])."""
    cache = {}
    for tl in lists:
        for t in tl:
            pair = t["pair"]
            if pair not in cache:
                cache[pair] = votes(pair, locked(pair, SPLIT_ENDS[k]))
            bull, bear = cache[pair].get(t["day"], (0, 0))
            t[f"vz{k}"] = (bull, bear) if t["side"] > 0 else (bear, bull)      # (supporting, opposing)


def filtered(lists: list[list[dict]], k: int, mode: str) -> list[list[dict]]:
    """Copies of the trade lists for split k: 'veto' drops trades the research opposes on balance, 'polovina'
    halves them, 'posila' halves them and enlarges (1.5x) trades it supports on balance."""
    if not all(f"vz{k}" in t for tl in lists for t in tl):
        tag_trades(lists, k)
    out = []
    for tl in lists:
        new = []
        for t in tl:
            sup, opp = t[f"vz{k}"]
            if opp > sup and mode == "veto":
                continue
            t2 = dict(t)
            if opp > sup and mode in ("polovina", "posila"):
                t2["size_mult"] = t2.get("size_mult", 1.0) * 0.5
            elif sup > opp and mode == "posila":
                t2["size_mult"] = t2.get("size_mult", 1.0) * 1.5
            new.append(t2)
        out.append(new)
    return out


# ----------------------------------------------------------------------
# event days x technical state
# ----------------------------------------------------------------------

def event_days(name: str) -> set:
    import fundamenty as F
    return {date.fromisoformat(x) for x in F.load_events().get(name, [])}


def event_rules(pairs: list[str], until: date) -> list[dict]:
    """(event, pair, state, direction) with a stable event-day effect on event days up to `until`."""
    key = ("rules", tuple(pairs), until)
    if key in _cache:
        return _cache[key]
    rules = []
    for pair in pairs:
        inst = get_instrument(pair)
        bars = daily_bars(pair)
        pos = {d: i for i, d in enumerate(bars["day"])}
        b = K.Builder(bars)
        masks = {lab: b.mask(K.Cond(*spec)) for lab, spec in T.EVENT_STATES}
        for name, ccy in EVENTS:
            if ccy not in (inst.base, inst.quote):
                continue
            idx = np.array(sorted(pos[d] for d in event_days(name) if d in pos and d <= until and pos[d] >= 1))
            if len(idx) < EVENT_MIN_N:
                continue
            ret = (bars["c"][idx] / bars["c"][idx - 1] - 1) * 100
            avg = float(np.mean(ret))                          # all event days: the state must beat them
            for lab, m in masks.items():
                st = m[idx - 1]
                if st.sum() < EVENT_MIN_N:
                    continue
                x = ret[st] - avg
                d = 1 if x.mean() > 0 else -1
                s = T.full_stats(x * d)
                if s["t"] >= EVENT_MIN_T:
                    rules.append({"udalost": name, "par": pair, "stav": lab, "smer": d, "n": s["n"], "t": s["t"],
                                  "prumer": s["prumer"]})
    _cache[key] = rules
    return rules


def event_trades(rules: list[dict]) -> list[dict]:
    """Add-on trades of the rules on ALL event days (the gate tests them only after the selection period):
    entry at the New York close before the event day, exit at the event day's close, stop EVENT_SL_ATR x ATR14."""
    trades, seen = {}, {}
    for r in rules:
        pair, side = r["par"], r["smer"]
        s = P.series(pair)
        inst = get_instrument(pair)
        half = (P.SPREAD_PIPS[pair] / 2 + P.SLIPPAGE_PIPS / 2) * inst.pip
        bars = daily_bars(pair)
        b = K.Builder(bars)
        state = b.mask(K.Cond(*dict(T.EVENT_STATES)[r["stav"]]))
        atr = K.atr(bars["h"], bars["l"], bars["c"], 14)
        pos = {d: i for i, d in enumerate(bars["day"])}
        for d in sorted(event_days(r["udalost"])):
            i = pos.get(d)
            if i is None or i < 15 or not state[i - 1] or np.isnan(atr[i - 1]):
                continue
            key = (pair, d)
            if key in seen:
                if seen[key] != side:                          # conflicting rules: no trade
                    trades.pop(key, None)
                continue
            seen[key] = side
            k0, k1 = s["last"][i - 1], s["last"][i]
            entry = s["c"][k0] + side * half
            stop = EVENT_SL_ATR * atr[i - 1]
            result, k_out, why = None, k1, "DEN"
            for j in range(k0 + 1, k1 + 1):
                adv = (entry - (s["l"][j] - half)) if side > 0 else ((s["h"][j] + half) - entry)
                if adv >= stop:
                    result, k_out, why = -stop, j, "SL"
                    break
            if result is None:
                result = (s["c"][k1] - half - entry) if side > 0 else (entry - (s["c"][k1] + half))
            pct = result / entry * 100
            trades[key] = {"pair": pair, "side": side, "day": bars["day"][i - 1], "entry": entry,
                           "t_in": int(s["ts"][k0]) + 3600, "t_out": int(s["ts"][k_out]) + 3600, "reason": why,
                           "price_pct": pct, "margin_pct": pct * P.LEVERAGE, "days": 1.0, "tp_pct": 0.0,
                           "sl_pct": stop / entry * 100 * P.LEVERAGE, "mfe_atr": 0.0, "marks": [],
                           "udalost": r["udalost"], "stav": r["stav"]}
    return sorted((t for k, t in trades.items() if k in seen), key=lambda t: t["t_in"])


def event_addon(pairs: list[str], k: int) -> list[dict]:
    key = ("addon", tuple(pairs), k)
    if key not in _cache:
        _cache[key] = event_trades(event_rules(pairs, SPLIT_ENDS[k]))
    return [dict(t) for t in _cache[key]]


# ----------------------------------------------------------------------
# live: the research view at a decision (selection on everything known before it), cached per data day
# ----------------------------------------------------------------------

LIVE_LOCK = PROJECT_ROOT / "data" / "research" / "tydenni" / "vyzkum_zamek.json"


def live_lock(pairs: list[str]) -> dict:
    """{pair: [(Cond, direction, t)], "_pravidla": event rules} selected on all price history the model has
    (FXCM, up to its last day); recomputed only when that history gets a new day."""
    import json
    marks = {p: P.series(p)["days"][-1].isoformat() for p in pairs}
    state = json.loads(LIVE_LOCK.read_text()) if LIVE_LOCK.exists() else {}
    changed = False
    out = {}
    for p in pairs:
        e = state.get(p)
        if not e or e.get("data_do") != marks[p]:
            conds = locked(p, date.fromisoformat(marks[p]))
            e = {"data_do": marks[p], "podminky": [[c.kind, list(c.params), c.tf, d, t] for c, d, t in conds]}
            state[p], changed = e, True
        out[p] = [(K.Cond(k, tuple(par), tf), d, t) for k, par, tf, d, t in e["podminky"]]
    mark = max(marks.values())
    if state.get("_pravidla_do") != mark:
        state["_pravidla"] = event_rules(list(pairs), date.fromisoformat(mark))
        state["_pravidla_do"], changed = mark, True
    out["_pravidla"] = state["_pravidla"]
    if changed:
        LIVE_LOCK.parent.mkdir(parents=True, exist_ok=True)
        LIVE_LOCK.write_text(json.dumps(state, indent=1, default=str))
    return out


def live_view(conds: list[tuple], bars: dict) -> dict | None:
    """The locked conditions active at the last bar of live daily bars ({o, h, l, c}) and the event states."""
    if len(bars["c"]) < 260:
        return None
    b = K.Builder(bars)
    active = [(c.key, d) for c, d, _ in conds if b.mask(c)[-1]]
    return {"pro_rust": [k for k, d in active if d > 0], "pro_pokles": [k for k, d in active if d < 0],
            "zamceno": len(conds), "stavy": [lab for lab, spec in T.EVENT_STATES if b.mask(K.Cond(*spec))[-1]]}
