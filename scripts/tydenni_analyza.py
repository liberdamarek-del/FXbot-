"""Weekly FX research (user's specification 2026-10-04): a complete look back at the week that just ended.

    python scripts/tydenni_analyza.py                       # last completed week, the 12 live pairs
    python scripts/tydenni_analyza.py --tyden 2026-09-28    # the week of this Monday
    python scripts/tydenni_analyza.py --pary EUR/USD,USD/JPY   (or --pary vse: every pair with data)
    python scripts/tydenni_analyza.py --rychle              # without the walk-forward of combinations
    python scripts/tydenni_analyza.py --dotaz "RSI14>50 & C>EMA20" --par EUR/USD --tf 1H --tydnu 20 [--rezim trend]

Three results that are never mixed up (section headings of the report say which one):
    A) DESCRIPTIVE - what happened (prices, days, sessions, events, correlations of the week)
    B) ATTRIBUTION - what was statistically associated with the moves INSIDE the week (no prediction)
    C) PREDICTIVE  - what had forecasting power: conditions chosen only on data before the week (in-sample),
                     then tested on later data (out-of-sample, walk-forward), and the week itself as a new test

No look-ahead: indicators at a bar close use only bars up to it (scripts/indikatory.py, tested), a higher
timeframe enters only after its bar closed, an event only after its time, forward returns are the outcome only,
and the week's locked conditions are chosen on samples whose forward window ended before the week started.
Missing / unreliable inputs are labelled (NEOVĚŘENO, TIMESTAMP UNVERIFIED, FUNDAMENT UNVERIFIED,
INSUFFICIENT SAMPLE, POSSIBLE OVERFIT) - nothing is estimated in their place. Data quality is checked first.

Sources: Yahoo Finance (FX 15m / 30m for 60 days, 1h for 730 days; US 10y yield, 2y note futures, gold, oil,
copper, S&P 500 futures, VIX, dollar index), FXCM hourly 2012-2026 (scripts/fxcm_universe.py), the
ForexFactory week feed archived since 2026-09-30 (time, currency, impact, forecast, previous - no actual),
actual values of US releases from ALFRED (the vintage of the release day, checked against the feed's previous
value), central bank decision dates and US release dates (scripts/fundamenty.py), VIX / US 2y from FRED.

Output: docs/tydenni/<YYYY-Www>.md (Czech report), learning/tydenni/<YYYY-Www>.json.gz (archive),
learning/tydenni/udalosti.jsonl (events with surprise and reactions, grows every week). Research only:
nothing here changes the trading model (that goes only through the walk-forward gate of self_learn.py).
"""

import gzip
import itertools
import json
import re
import sys
import time
from bisect import bisect_right
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import indikatory as K  # noqa: E402

UTC = timezone.utc
NY = ZoneInfo("America/New_York")
ARCHIVE = PROJECT_ROOT / "learning" / "tydenni"
REPORTS = PROJECT_ROOT / "docs" / "tydenni"
CACHE = PROJECT_ROOT / "data" / "research" / "tydenni"
DAYS_CZ = ("pondělí", "úterý", "středa", "čtvrtek", "pátek", "sobota", "neděle")

CONFIG = {
    "sideways_pct": (0.05, 0.10, 0.20, 0.30),          # |change| <= x % = SIDEWAYS (several definitions)
    "main_sideways_pct": 0.10,
    "sample_labels": ((20, "INSUFFICIENT SAMPLE"), (50, "slabá evidence"), (100, "použitelná evidence"),
                      (10 ** 9, "silnější evidence")),
    "min_n_select": {"15M": 60, "30M": 40, "1H": 100, "4H": 60, "1D": 40},
    "top_k": 20,                                         # locked single conditions per pair and timeframe
    "pool": 30, "top_pairs": 15, "top_triples": 10, "top_quads": 5,
    "stability_min": 0.6,                                # share of years (weeks) with the same sign
    "robust_share": 0.75,                                # neighbours that keep the sign with >= half the effect
    "buckets_utc": ((0, 6), (6, 9), (9, 12), (12, 15), (15, 18), (18, 22), (22, 24)),
    "reaction_minutes": (15, 30, 60, 240, 720, 1440),
    "big_move_x": 2.0,                                   # hourly move >= x * median |1h move| of the last 20 days
}

# timeframe: (seconds, forward horizon in bars, higher timeframes for multi-timeframe states)
TF = {"15M": (900, 4, ("1H", "4H")), "30M": (1800, 4, ("1H", "4H")), "1H": (3600, 4, ("4H", "1D")),
      "4H": (14400, 6, ("1D",)), "1D": (86400, 5, ())}
HORIZON_CZ = {"15M": "1 h", "30M": "2 h", "1H": "4 h", "4H": "24 h", "1D": "5 dní"}
CROSS = {"US10Y": "^TNX", "US2Y_fut": "ZT=F", "zlato": "GC=F", "ropa": "CL=F", "měď": "HG=F", "S&P500_fut": "ES=F",
         "VIX": "^VIX", "dolar_index": "DX-Y.NYB"}
LEVEL_ASSETS = {"US10Y", "VIX"}                        # change in points (yield in %), others in %


# ----------------------------------------------------------------------
# time
# ----------------------------------------------------------------------

def week_bounds(monday: date) -> tuple[int, int]:
    """FX week: Sunday 17:00 New York -> Friday 17:00 New York."""
    start = datetime(monday.year, monday.month, monday.day, 17, tzinfo=NY) - timedelta(days=1)
    end = datetime(monday.year, monday.month, monday.day, 17, tzinfo=NY) + timedelta(days=4)
    return int(start.timestamp()), int(end.timestamp())


def last_completed_monday(now: datetime) -> date:
    d = now.astimezone(NY).date()
    monday = d - timedelta(days=d.weekday())
    if week_bounds(monday)[1] > now.timestamp():
        monday -= timedelta(days=7)
    return monday


def week_label(monday: date) -> str:
    y, w, _ = monday.isocalendar()
    return f"{y}-W{w:02d}"


def iso_week(ts: int) -> str:
    """Label of the FX week containing ts (the Sunday evening belongs to the next Monday's week)."""
    d = datetime.fromtimestamp(ts + 7 * 3600, tz=NY).date()       # Sunday 17:00 NY -> Monday
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def utc_str(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=UTC).strftime("%a %d.%m. %H:%M UTC")


# ----------------------------------------------------------------------
# data
# ----------------------------------------------------------------------

def yahoo_symbol(pair: str) -> str:
    import signals_live as SL
    if pair in SL.YAHOO:
        return SL.YAHOO[pair]
    base, quote = pair.split("/")
    return f"{quote}=X" if base == "USD" else f"{base}{quote}=X"


_yahoo_cache: dict = {}


def yahoo(symbol: str, interval: str, span: str) -> dict:
    """Raw Yahoo bars (ts = bar start). Rows with a missing value are counted, not repaired."""
    key = (symbol, interval, span)
    if key in _yahoo_cache:
        return _yahoo_cache[key]
    from src.sources.http import fetch
    _, content, _ = fetch(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval={interval}&range={span}",
                          retries=4)
    r = json.loads(content)["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    ts = np.array(r.get("timestamp", []), np.int64)
    arr = {k: np.array([np.nan if v is None else v for v in q.get(k, [])], float) for k in ("open", "high", "low", "close")}
    sec = {"15m": 900, "30m": 1800, "1h": 3600}[interval]
    out = {"ts_raw": ts.copy(), "missing_values": int(np.isnan(np.vstack(list(arr.values()))).any(axis=0).sum()),
           "sec": sec}
    ok = ~np.isnan(np.vstack(list(arr.values()))).any(axis=0)
    ts = ts[ok] // sec * sec                                       # the last bar carries the current minute
    out.update({"ts": ts, "o": arr["open"][ok], "h": arr["high"][ok], "l": arr["low"][ok], "c": arr["close"][ok]})
    out["close_ts"] = out["ts"] + sec
    _yahoo_cache[key] = out
    time.sleep(0.3)
    return out


def dedupe(b: dict) -> dict:
    """Sorted bars, the last row of duplicated timestamps kept (the duplicates are reported by quality())."""
    order = np.argsort(b["ts"], kind="stable")
    ts = b["ts"][order]
    keep = np.append(ts[1:] != ts[:-1], True)
    sel = order[keep]
    out = {k: b[k][sel] for k in ("ts", "o", "h", "l", "c")}
    out["close_ts"] = out["ts"] + b["sec"]
    out["sec"] = b["sec"]
    return out


def window(b: dict, t0: int, t1: int) -> dict:
    m = (b["ts"] >= t0) & (b["ts"] < t1)
    out = {k: b[k][m] for k in ("ts", "o", "h", "l", "c", "close_ts")}
    out["sec"] = b["sec"]
    return out


def history_1h(pair: str, recent: dict) -> tuple[dict, int]:
    """FXCM hourly history (2012 ->) followed by Yahoo hourly bars after its last bar; returns the series and
    the first timestamp taken from Yahoo (the source join)."""
    import profit_lab2 as P
    try:
        s = P.series(pair)
        ts, o, h, l, c = (np.asarray(s[k]) for k in ("ts", "o", "h", "l", "c"))
    except Exception:
        ts = o = h = l = c = np.array([])
    join = int(ts[-1]) + 3600 if len(ts) else 0
    m = recent["ts"] >= join
    out = {"ts": np.concatenate([ts.astype(np.int64), recent["ts"][m]]),
           "o": np.concatenate([o, recent["o"][m]]), "h": np.concatenate([h, recent["h"][m]]),
           "l": np.concatenate([l, recent["l"][m]]), "c": np.concatenate([c, recent["c"][m]]), "sec": 3600}
    out["close_ts"] = out["ts"] + 3600
    return out, join


def cut(b: dict, t1: int) -> dict:
    """Bars that closed by t1 (also the day labels of daily bars)."""
    m = np.asarray(b["close_ts"]) <= t1
    return {k: (v[m] if isinstance(v, np.ndarray) else [x for x, keep in zip(v, m) if keep] if isinstance(v, list) else v)
            for k, v in b.items()}


def pip(pair: str) -> float:
    return 0.01 if pair.endswith("JPY") else 0.0001


def spread_pips(pair: str) -> float | None:
    import profit_lab2 as P
    return P.SPREAD_PIPS.get(pair)


# ----------------------------------------------------------------------
# 0. data quality
# ----------------------------------------------------------------------

def quality(raw: dict, t0: int, t1: int, name: str) -> dict:
    """Missing bars, duplicates, timestamps, OHLC validity, gaps, weekend bars, stale bars, outliers in [t0, t1)."""
    sec = raw["sec"]
    ts_all = raw["ts_raw"]
    in_w = (ts_all >= t0) & (ts_all < t1)
    ts_w = ts_all[in_w]
    dup = int(len(ts_w) - len(np.unique(ts_w)))
    misaligned = int(np.sum(ts_w % sec != 0))
    b = window(dedupe(raw), t0, t1)
    expected = (t1 - t0) // sec
    present = len(b["ts"])
    head = int(np.sum(b["ts"] < t0 + 3 * 3600))                     # the source may open the week up to 2 h later
    miss_inside = int((expected - 3 * 3600 // sec) - (present - head))
    o, h, l, c = b["o"], b["h"], b["l"], b["c"]
    bad = int(np.sum((h < np.maximum(o, c) - 1e-12) | (l > np.minimum(o, c) + 1e-12) | (l <= 0) | (h < l)))
    stale = int(np.sum((h - l) == 0))
    after = (ts_all >= t1) & (ts_all < t1 + 2 * 86400)          # between the Friday close and the Sunday open
    late_friday = int(np.sum(after & (ts_all < t1 + 3 * 3600)))    # the source's session ends up to 2 h later
    weekend = int(np.sum(after) - late_friday)
    gaps = []
    if present > 1:
        dt = np.diff(b["ts"])
        for k in np.where(dt > sec)[0]:
            gaps.append((int(b["ts"][k]) + sec, int(dt[k] // sec - 1)))
    r = np.diff(np.log(c)) if present > 2 else np.array([])
    outliers = []
    if len(r) > 20:
        mad = np.median(np.abs(r - np.median(r))) * 1.4826
        if mad > 0:
            for k in np.where(np.abs(r) > 10 * mad)[0]:
                outliers.append((int(b["ts"][k + 1]), float(r[k] * 100)))
    miss = expected - present
    state = "OK"
    if present == 0 or miss_inside > 0.2 * expected or bad > 0.01 * max(present, 1):
        state = "CHYBA"
    elif miss_inside > 0.03 * expected or dup or misaligned or weekend or len(outliers) or stale > 0.1 * max(present, 1):
        state = "VAROVÁNÍ"
    return {"zdroj": name, "stav": state, "ocekavano": int(expected), "baru": int(present), "chybi": int(miss),
            "po_zavreni": late_friday, "chybi_uvnitr": max(miss_inside, 0),
            "duplicity": dup, "spatny_cas": misaligned, "spatne_ohlc": bad, "nulovy_rozsah": stale,
            "vikend": weekend, "chybejici_hodnoty": raw["missing_values"],
            "mezery": sorted(gaps, key=lambda g: -g[1])[:5], "outliery": outliers[:5]}


def sync_check(a: dict, b: dict, pair: str) -> dict:
    """Median / max close difference in pips of two sources on common bar closes."""
    common, ia, ib = np.intersect1d(a["close_ts"], b["close_ts"], return_indices=True)
    if len(common) < 10:
        return {"spolecnych": int(len(common)), "stav": "NEOVĚŘENO"}
    d = np.abs(a["c"][ia] - b["c"][ib]) / pip(pair)
    state = "OK" if np.median(d) <= 3 else "VAROVÁNÍ" if np.median(d) <= 10 else "CHYBA"
    return {"spolecnych": int(len(common)), "median_pips": round(float(np.median(d)), 2),
            "max_pips": round(float(np.max(d)), 1), "stav": state}


# ----------------------------------------------------------------------
# A) descriptive
# ----------------------------------------------------------------------

def classify(change_pct: float, thr: float) -> str:
    return "SIDEWAYS" if abs(change_pct) <= thr else "UP" if change_pct > 0 else "DOWN"


def extremes(c: np.ndarray) -> dict:
    """Largest peak->trough drop and trough->peak rise on closes (in %)."""
    peak, trough, dd, rec = c[0], c[0], 0.0, 0.0
    for x in c:
        peak, trough = max(peak, x), min(trough, x)
        dd, rec = min(dd, x / peak - 1), max(rec, x / trough - 1)
    return {"max_drawdown_pct": dd * 100, "max_recovery_pct": rec * 100}


def week_stats(pair: str, b15: dict | None, b30: dict | None, b1: dict, d1: dict) -> dict:
    """Weekly figures of one pair from the finest reliable bars of the week."""
    fine = b15 if b15 is not None and len(b15["c"]) else b1
    o, h, l, c = fine["o"][0], fine["h"].max(), fine["l"].min(), fine["c"][-1]
    chg = (c / o - 1) * 100
    r1 = np.diff(np.log(b1["c"])) if len(b1["c"]) > 2 else np.array([0.0])
    out = {"open": o, "high": h, "low": l, "close": c, "zmena_abs": c - o, "zmena_pct": chg,
           "zmena_pips": (c - o) / pip(pair), "max_rust_od_open_pct": (h / o - 1) * 100,
           "max_pokles_od_open_pct": (l / o - 1) * 100, "rozsah_pct": (h - l) / o * 100,
           "volatilita_tyden_pct": float(np.std(r1) * np.sqrt(len(r1)) * 100),
           "volatilita_rocni_pct": float(np.std(r1) * np.sqrt(24 * 260) * 100),
           "atr14_d1_pips": float(K.atr(d1["h"], d1["l"], d1["c"], 14)[-1] / pip(pair)) if len(d1["c"]) > 15 else None,
           "atr14_h1_pips": float(K.atr(b1["h"], b1["l"], b1["c"], 14)[-1] / pip(pair)) if len(b1["c"]) > 15 else None,
           "klasifikace": {f"{t:.2f}": classify(chg, t) for t in CONFIG["sideways_pct"]}}
    out.update(extremes(fine["c"]))
    counts = {}
    for t in CONFIG["sideways_pct"]:
        rr = (b1["c"] / b1["o"] - 1) * 100
        counts[f"{t:.2f}"] = {"up": int(np.sum(rr > t)), "down": int(np.sum(rr < -t)), "sideways": int(np.sum(np.abs(rr) <= t))}
    out["hodiny_up_down_sideways"] = counts
    for name, b in (("15m", b15), ("30m", b30), ("1h", b1)):
        if b is None or not len(b["c"]):
            out[f"nejvetsi_{name}"] = "NEOVĚŘENO (data nejsou)"
            continue
        mv = (b["c"] / b["o"] - 1) * 100
        k = int(np.argmax(np.abs(mv)))
        out[f"nejvetsi_{name}"] = {"cas": utc_str(int(b["ts"][k])), "pct": float(mv[k]),
                                   "pips": float((b["c"][k] - b["o"][k]) / pip(pair))}
    return out


def day_stats(pair: str, fine: dict, b1: dict) -> list[dict]:
    """Per UTC day of the week (Sunday evening = the market opening): OHLC, change, range, volatility,
    trend, largest move and the part of the day (UTC buckets) where the move came from."""
    out = []
    days = sorted({datetime.fromtimestamp(int(t), tz=UTC).date() for t in fine["ts"]})
    for d in days:
        t0 = int(datetime(d.year, d.month, d.day, tzinfo=UTC).timestamp())
        m = (fine["ts"] >= t0) & (fine["ts"] < t0 + 86400)
        if m.sum() < 2:
            continue
        o, h, l, c = fine["o"][m][0], fine["h"][m].max(), fine["l"][m].min(), fine["c"][m][-1]
        r = np.diff(np.log(np.concatenate([[fine["o"][m][0]], fine["c"][m]])))
        mv = (fine["c"][m] / fine["o"][m] - 1) * 100
        k = int(np.argmax(np.abs(mv)))
        buckets = []
        total_abs = float(np.sum(np.abs(r))) or 1e-12
        for a, b in CONFIG["buckets_utc"]:
            mb = m & (fine["ts"] >= t0 + a * 3600) & (fine["ts"] < t0 + b * 3600)
            if not mb.any():
                buckets.append({"usek": f"{a:02d}-{b:02d}", "zmena_pct": None, "rozsah_pct": None, "podil_aktivity": 0.0})
                continue
            bo, bc = fine["o"][mb][0], fine["c"][mb][-1]
            rb = np.diff(np.log(np.concatenate([[bo], fine["c"][mb]])))
            buckets.append({"usek": f"{a:02d}-{b:02d}", "zmena_pct": (bc / bo - 1) * 100,
                            "rozsah_pct": (fine["h"][mb].max() - fine["l"][mb].min()) / bo * 100,
                            "podil_aktivity": float(np.sum(np.abs(rb)) / total_abs)})
        chg = (c / o - 1) * 100
        main = [x for x in buckets if x["zmena_pct"] is not None]
        drive = max(main, key=lambda x: (x["zmena_pct"] or 0) * np.sign(chg)) if main and chg else None
        out.append({"den": d.isoformat(), "nazev": DAYS_CZ[d.weekday()], "open": o,
                    "poznamka": "otevření trhu (jen večer)" if d.weekday() == 6 else "", "high": h, "low": l, "close": c,
                    "zmena_pct": chg, "zmena_pips": (c - o) / pip(pair), "rozsah_pct": (h - l) / o * 100,
                    "volatilita_pct": float(np.std(r) * np.sqrt(len(r)) * 100),
                    "trend": {f"{t:.2f}": classify(chg, t) for t in CONFIG["sideways_pct"]},
                    "nejvetsi_pohyb": {"cas": utc_str(int(fine["ts"][m][k])), "pct": float(mv[k])},
                    "useky": buckets, "hlavni_usek": drive["usek"] if drive else None,
                    "nejaktivnejsi_usek": max(main, key=lambda x: x["podil_aktivity"])["usek"] if main else None})
    return out


# ----------------------------------------------------------------------
# fundamentals of the week
# ----------------------------------------------------------------------

EVENT_TYPES = (
    ("rozhodnutí o sazbách", ("Rate Decision", "Cash Rate", "Policy Rate", "Official Bank Rate", "Funds Rate",
                              "Refinancing Rate", "Overnight Rate", "Monetary Policy Statement", "Policy Assessment")),
    ("zápis z jednání", ("Minutes",)), ("projev / tisková konference", ("Speaks", "Speech", "Testifies", "Press Conference")),
    ("NFP", ("Non-Farm",)), ("nezaměstnanost", ("Unemployment", "Claimant Count", "Jobless")),
    ("mzdy", ("Earnings", "Wage", "Labor Cost")), ("zaměstnanost", ("Employment", "ADP", "JOLTS", "Job")),
    ("inflační očekávání", ("Inflation Expectations",)), ("PCE", ("PCE",)), ("CPI", ("CPI",)), ("PPI", ("PPI",)),
    ("HDP", ("GDP",)), ("ISM", ("ISM",)), ("PMI", ("PMI",)), ("maloobchod", ("Retail Sales",)),
    ("spotřebitelská důvěra", ("Consumer Confidence", "Consumer Sentiment", "GfK")),
    ("aukce dluhopisů", ("Auction", "Bond")), ("obchodní bilance", ("Trade Balance", "Current Account")),
    ("bydlení", ("Housing", "Home Sales", "Building", "Pending", "HPI")),
    ("průmysl / objednávky", ("Industrial", "Manufacturing", "Factory", "Durable", "Production")),
)
LOWER_IS_BETTER = ("nezaměstnanost",)            # conventional reading: higher value = weaker currency
FRED_ACTUALS = {                                 # FF title -> (FRED id, transform, decimals); US only
    "Non-Farm Employment Change": ("PAYEMS", "diff", 0), "Unemployment Rate": ("UNRATE", "level", 1),
    "CPI m/m": ("CPIAUCSL", "pct", 1), "Core CPI m/m": ("CPILFESL", "pct", 1), "CPI y/y": ("CPIAUCNS", "yoy", 1),
    "Core PCE Price Index m/m": ("PCEPILFE", "pct", 1), "PPI m/m": ("PPIFIS", "pct", 1),
    "Retail Sales m/m": ("RSAFS", "pct", 1), "Core Retail Sales m/m": ("RSFSXMV", "pct", 1),
    "Average Hourly Earnings m/m": ("CES0500000003", "pct", 1), "Unemployment Claims": ("ICSA", "thousands", 0),
    "Advance GDP q/q": ("A191RL1Q225SBEA", "level", 1), "Prelim GDP q/q": ("A191RL1Q225SBEA", "level", 1),
    "Final GDP q/q": ("A191RL1Q225SBEA", "level", 1),
}


def event_type(title: str) -> str:
    for name, keys in EVENT_TYPES:
        if any(k.lower() in title.lower() for k in keys):
            return name
    return "ostatní"


def parse_value(text) -> tuple[float | None, int]:
    """'0.3%' -> (0.3, 1); '225K' -> (225, 0); '-1.2B' -> (-1.2, 1); '<0.1%' / '' -> (None, 0)."""
    if text is None:
        return None, 0
    m = re.fullmatch(r"\s*(-?\d+(?:\.(\d+))?)\s*([%KMBT])?\s*", str(text))
    if not m:
        return None, 0
    return float(m.group(1)), len(m.group(2) or "")


def alfred_actual(title: str, release_day: date) -> dict | None:
    """Actual value of a US release = the newest period of the ALFRED vintage of the release day; the check
    value = the newest period of the vintage of the day before (what the calendar showed as 'previous' before
    the release, i.e. the previous first release, not its later revision)."""
    if title not in FRED_ACTUALS:
        return None
    sid, how, dec = FRED_ACTUALS[title]
    from src.sources.http import fetch

    def vintage(day):
        _, content, _ = fetch(f"https://alfred.stlouisfed.org/graph/alfredgraph.csv?id={sid}&vintage_date={day}",
                              retries=2)
        rows = [line.split(",") for line in content.decode().strip().splitlines()[1:]]
        return [(d, float(v)) for d, v in rows if v not in (".", "")]

    def newest(vals):
        i = len(vals) - 1
        cur = vals[i][1]
        if how == "diff":
            return cur - vals[i - 1][1]
        if how == "pct":
            return (cur / vals[i - 1][1] - 1) * 100
        if how == "yoy":
            return (cur / vals[i - 12][1] - 1) * 100
        if how == "thousands":
            return cur / 1000
        return cur
    try:
        now, before = vintage(release_day), vintage(release_day - timedelta(days=1))
    except Exception as exc:
        return {"chyba": f"{type(exc).__name__}"}
    if len(now) < 14 or len(before) < 14:
        return None
    return {"obdobi": now[-1][0], "obdobi_pred": before[-1][0], "actual": round(newest(now), dec),
            "previous": round(newest(before), dec), "fred": sid, "nove_obdobi": now[-1][0] > before[-1][0]}


def week_events(t0: int, t1: int, currencies: set) -> list[dict]:
    from src.fundamental.calendar import events_between
    out = []
    for e in events_between(t0 - 6 * 3600, t1, tuple(sorted(currencies)), "Low"):
        if e.impact == "Holiday":
            continue
        kind = event_type(e.title)
        local = datetime.fromtimestamp(e.scheduled_at, tz=NY)
        flags = []
        if kind == "projev / tisková konference":
            flags.append("TIMESTAMP UNVERIFIED (čas začátku projevu, ne okamžik reakce)")
        if local.hour == 0 and local.minute == 0:
            flags.append("TIMESTAMP UNVERIFIED (celodenní / předběžný termín)")
        if e.currency == "JPY" and kind == "rozhodnutí o sazbách":
            flags.append("TIMESTAMP UNVERIFIED (BoJ nemá pevný čas oznámení)")
        fc, dec_f = parse_value(e.forecast)
        pv, _ = parse_value(e.previous)
        ev = {"cas": e.scheduled_at, "cas_text": utc_str(e.scheduled_at), "mena": e.currency, "udalost": e.title,
              "typ": kind, "vyznam": e.impact, "forecast": e.forecast, "previous": e.previous, "actual": None,
              "actual_stav": "NEOVĚŘENO (zdroj skutečné hodnoty není)", "surprise": None, "surprise_rel": None,
              "surprise_trida": "NEOVĚŘENO", "priznaky": flags}
        if e.currency == "USD" and e.title in FRED_ACTUALS and e.scheduled_at <= time.time():
            a = alfred_actual(e.title, local.date())
            if a and "actual" in a:
                ok = (pv is not None and a["nove_obdobi"]
                      and abs(a["previous"] - pv) <= 0.5 * 10 ** -max(dec_f, FRED_ACTUALS[e.title][2]) + 1e-9)
                ev["actual"] = a["actual"]
                ev["actual_overeno"] = bool(ok)
                ev["actual_stav"] = (f"ověřeno (ALFRED {a['fred']}, období {a['obdobi']}, předchozí první zveřejnění "
                                     f"{a['previous']} = kalendář {e.previous})" if ok
                                     else f"NEOVĚŘENO (ALFRED {a['fred']} {a['obdobi']}: předchozí {a['previous']} vs "
                                          f"kalendář {e.previous})")
                if ok and fc is not None:
                    s = a["actual"] - fc
                    unit = 0.5 * 10 ** -max(dec_f, FRED_ACTUALS[e.title][2])
                    ev["surprise"] = round(s, 4)
                    ev["surprise_rel"] = round(s / abs(fc), 4) if abs(fc) >= 0.5 else None
                    sign = -1 if kind in LOWER_IS_BETTER else 1
                    ev["surprise_trida"] = ("≈ 0" if abs(s) < unit + 1e-9 else
                                            "pozitivní pro měnu" if s * sign > 0 else "negativní pro měnu")
        out.append(ev)
    return out


def price_at(b: dict, t: int) -> float | None:
    """Close of the last bar that ended at or before t (None when the bar is older than 30 minutes)."""
    k = np.searchsorted(b["close_ts"], t, side="right") - 1
    if k < 0 or t - b["close_ts"][k] > 1800:
        return None
    return float(b["c"][k])


EVENT_STATES_1H = (("1H C>EMA50", ("px_gt", ("EMA", 50))), ("1H C<EMA50", ("px_lt", ("EMA", 50))),
                   ("1H RSI14>50", ("rsi_gt", (14, 50))), ("1H RSI14<50", ("rsi_lt", (14, 50))),
                   ("1H ADX14>25", ("adx_gt", (14, 25))), ("1H ADX14<20", ("adx_lt", (14, 20))))


def reactions(ev: dict, pair: str, b15: dict, b1h: dict | None = None) -> dict:
    """Pair move before and after an event (% of the price; in the event currency's direction too) and the
    technical state of the last hourly bar closed before the event."""
    base, quote = pair.split("/")
    sign = 1 if ev["mena"] == base else -1 if ev["mena"] == quote else 0
    t = ev["cas"]
    p0, pre = price_at(b15, t), price_at(b15, t - 3600)
    out = {"par": pair, "smer_meny": sign}
    if b1h is not None:
        k = np.searchsorted(b1h["close_ts"], t, side="right") - 1
        if k >= 200:
            b = K.Builder({x: b1h[x][:k + 1] for x in "ohlc"})
            out["stav"] = [lab for lab, spec in EVENT_STATES_1H if b.mask(K.Cond(*spec))[-1]]
    if p0 is None:
        out["stav"] = "NEOVĚŘENO (chybí cena v čase události)"
        return out
    out["pred_1h_pct"] = None if pre is None else (p0 / pre - 1) * 100
    for mins in CONFIG["reaction_minutes"]:
        p = price_at(b15, t + mins * 60)
        out[f"po_{mins}m_pct"] = None if p is None else (p / p0 - 1) * 100
    return out


# ----------------------------------------------------------------------
# cross-pair factors, correlations, lead-lag
# ----------------------------------------------------------------------

def aligned_returns(series: dict[str, dict]) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    common = None
    for b in series.values():
        common = b["close_ts"] if common is None else np.intersect1d(common, b["close_ts"])
    out = {}
    for name, b in series.items():
        idx = np.searchsorted(b["close_ts"], common)
        out[name] = np.diff(np.log(b["c"][idx])) * 100
    return common[1:], out


def currency_factors(rets: dict[str, np.ndarray]) -> dict:
    """Least squares r_pair = f_base - f_quote per hour (sum of factors = 0): common currency factors and the
    individual remainder of every pair."""
    pairs = list(rets)
    ccys = sorted({c for p in pairs for c in p.split("/")})
    X = np.zeros((len(pairs), len(ccys)))
    for i, p in enumerate(pairs):
        b, q = p.split("/")
        X[i, ccys.index(b)], X[i, ccys.index(q)] = 1, -1
    R = np.vstack([rets[p] for p in pairs])                    # pairs x hours
    F = np.linalg.pinv(X) @ R                                   # currencies x hours (minimum norm: sum = 0)
    fit = X @ F
    single = {c: sum(1 for p in pairs if c in p.split("/")) for c in ccys}
    out = {"meny": {c: float(F[k].sum()) for k, c in enumerate(ccys)}, "pary": {}}
    for i, p in enumerate(pairs):
        ss = float(np.sum((R[i] - R[i].mean()) ** 2)) or 1e-12
        b, q = p.split("/")
        out["pary"][p] = {"spolecny_faktor_pct": float(fit[i].sum()), "individualni_pct": float((R[i] - fit[i]).sum()),
                          "r2_spolecny": float(1 - np.sum((R[i] - fit[i]) ** 2) / ss),
                          "poznamka": ("faktor nelze oddělit od individuálního pohybu (měna jen v jednom páru)"
                                       if min(single[b], single[q]) == 1 else "")}
    return out


def corr_label(r: float) -> str:
    a = abs(r)
    return "silná" if a >= 0.7 else "střední" if a >= 0.4 else "slabá" if a >= 0.2 else "žádná"


def correlations(rets: dict[str, np.ndarray]) -> dict:
    names = list(rets)
    M = np.corrcoef(np.vstack([rets[n] for n in names]))
    return {"nazvy": names, "matice": np.round(M, 3).tolist()}


def bar_returns(b: dict) -> dict:
    """{bar close ts: log return in %} only for bars whose previous bar is present (no returns across gaps)."""
    cts, c = b["close_ts"], b["c"]
    ok = np.diff(cts) == b["sec"]
    return {"t": cts[1:][ok], "r": (np.diff(np.log(c)) * 100)[ok]}


def lead_lag(series: dict[str, dict], targets: list[str], max_lag: int = 4) -> list[dict]:
    """corr(r_A[t], r_B[t + k bars]) for k = 1..max_lag, each pair of series on its own common bars (markets have
    different hours); kept when |r| > 3/sqrt(N) and larger than the reverse direction. Correlation, not causation."""
    rets = {k: bar_returns(v) for k, v in series.items()}
    out = []
    for a, ra in rets.items():
        for b in targets:
            if a == b or b not in rets:
                continue
            rb = rets[b]
            sec = series[b]["sec"]
            for k in range(1, max_lag + 1):
                _, ia, ib = np.intersect1d(ra["t"], rb["t"] - k * sec, return_indices=True)
                _, ja, jb = np.intersect1d(rb["t"], ra["t"] - k * sec, return_indices=True)
                if len(ia) < 100 or len(ja) < 100:
                    continue
                r = np.corrcoef(ra["r"][ia], rb["r"][ib])[0, 1]
                rev = np.corrcoef(rb["r"][ja], ra["r"][jb])[0, 1]
                if np.isfinite(r) and abs(r) > 3 / np.sqrt(len(ia)) and abs(r) > abs(rev):
                    _, ka, kb = np.intersect1d(ra["t"], rb["t"], return_indices=True)
                    r0 = float(np.corrcoef(ra["r"][ka], rb["r"][kb])[0, 1]) if len(ka) > 30 else float("nan")
                    out.append({"vede": a, "nasleduje": b, "zpozdeni_baru": k, "r": float(r), "r_obracene": float(rev),
                                "r_soucasne": r0, "n": int(len(ia)),
                                "posun_casu": bool(np.isfinite(r0) and k == 1 and abs(r) >= 0.5 * abs(r0) and abs(r) > 0.1)})
    return sorted(out, key=lambda x: -abs(x["r"]))


# ----------------------------------------------------------------------
# C) predictive engine
# ----------------------------------------------------------------------

def sample_label(n: int) -> str:
    for limit, text in CONFIG["sample_labels"]:
        if n < limit:
            return text
    return CONFIG["sample_labels"][-1][1]


def full_stats(x: np.ndarray) -> dict:
    """Statistics of signed forward returns (in % of the price)."""
    n = len(x)
    if n == 0:
        return {"n": 0, "vzorek": sample_label(0)}
    sd = float(np.std(x, ddof=1)) if n > 1 else 0.0
    return {"n": int(n), "prumer": float(np.mean(x)), "median": float(np.median(x)), "sd": sd,
            "hit": float(np.mean(x > 0)), "max_ztrata": float(np.min(x)), "max_zisk": float(np.max(x)),
            "t": float(np.mean(x) / sd * np.sqrt(n)) if sd > 0 else 0.0,
            "sharpe": float(np.mean(x) / sd) if sd > 0 else 0.0, "vzorek": sample_label(n)}


class Dataset:
    """One pair on one timeframe: sampled condition masks (forward windows that do not overlap), forward returns,
    period labels and regimes; the Builder stays for neighbours and the week's full-resolution masks."""

    def __init__(self, pair: str, tf: str, bars: dict, higher: dict[str, dict], regimes_daily: dict):
        sec, H, _ = TF[tf]
        self.pair, self.tf, self.H, self.bars = pair, tf, H, bars
        self.builder = K.Builder(bars)
        self.higher = {k: (K.Builder(v), v) for k, v in higher.items()}
        c, cts = bars["c"], bars["close_ts"]
        n = len(c)
        start = (n - 1 - H) % H if n > H else 0
        idx = np.arange(start, n - H, H)
        span = cts[np.minimum(idx + H, n - 1)] - cts[idx]
        limit = H * sec * 2 if tf != "1D" else 9 * 86400
        idx = idx[span <= limit]
        self.idx = idx
        self.fwd = (c[idx + H] / c[idx] - 1) * 100
        self.t = cts[idx]                                         # decision time = bar close
        self.t_end = cts[idx + H]                                  # outcome known at
        self.year = np.array([datetime.fromtimestamp(int(t), tz=UTC).year for t in self.t])
        self.week = np.array([iso_week(int(t)) for t in self.t])
        self.conds = K.grid() + [x for h in TF[tf][2] if h in higher for x in K.mtf_grid(h)]
        self.keys = [x.key for x in self.conds]
        self.tail = min(n, 1200)                                  # full-resolution masks of the last bars (the week)
        rows, tails = [], []
        for x in self.conds:
            m = self.mask_full(x)
            rows.append(m[idx])
            tails.append(m[n - self.tail:])
        self.M = np.vstack(rows) if len(idx) else np.zeros((len(self.conds), 0), bool)
        self.Mtail = np.vstack(tails)
        self._nb: dict = {}
        self.regime = self._regimes(regimes_daily)

    def mask_full(self, cnd: K.Cond) -> np.ndarray:
        if not cnd.tf:
            return self.builder.mask(cnd)
        b, hb = self.higher[cnd.tf]
        return K.align(hb["close_ts"], b.mask(K.Cond(cnd.kind, cnd.params)), self.bars["close_ts"])

    def sampled(self, cnd: K.Cond) -> np.ndarray:
        if cnd.key in self.keys:
            return self.M[self.keys.index(cnd.key)]
        if cnd.key not in self._nb:
            self._nb[cnd.key] = self.mask_full(cnd)[self.idx]
        return self._nb[cnd.key]

    def _regimes(self, daily: dict) -> dict:
        """Regime labels known at each sample time (the previous day's daily values; base-timeframe ATR / ADX)."""
        b = self.builder
        a = b.ind("atr", 14)[self.idx] / self.bars["c"][self.idx]
        med = np.full(len(self.idx), np.nan)
        atr_pct = b.ind("atr", 14) / self.bars["c"]
        roll = np.full(len(atr_pct), np.nan)
        if len(atr_pct) > 250:
            from numpy.lib.stride_tricks import sliding_window_view
            roll[249:] = np.nanmedian(sliding_window_view(atr_pct, 250), axis=1)
        med = roll[self.idx]
        adx = b.ind("adx", 14)[0][self.idx]
        reg = {"volatilita": np.where(a >= 1.25 * med, "vysoká", np.where(a <= 0.8 * med, "nízká", "střední")),
               "trend": np.where(adx >= 25, "trend", np.where(adx <= 20, "range", "přechod"))}
        days = [datetime.fromtimestamp(int(t), tz=UTC).date() for t in self.t]
        for name, series in daily.items():                     # {date: label} of the previous known day
            keys = series["_keys"]
            lab = []
            for d in days:
                k = bisect_right(keys, d - timedelta(days=1)) - 1
                lab.append(series[keys[k]] if k >= 0 else "NEOVĚŘENO")
            reg[name] = np.array(lab)
        return reg

    # aggregates ------------------------------------------------------
    def agg(self, sel: np.ndarray, M: np.ndarray | None = None) -> dict:
        M = self.M if M is None else M
        f = self.fwd[sel]
        Ms = M[:, sel].astype(np.float32)
        return {"n": Ms.sum(1), "s1": Ms @ f.astype(np.float32), "s2": Ms @ (f ** 2).astype(np.float32),
                "pos": Ms @ (f > 0).astype(np.float32), "neg": Ms @ (f < 0).astype(np.float32)}

    def per_period(self, sel: np.ndarray, M: np.ndarray | None = None, by: str = "year") -> dict:
        labels = self.year if by == "year" else self.week
        out = {}
        for p in np.unique(labels[sel]):
            out[p] = self.agg(sel & (labels == p), M)
        return out


def t_stats(a: dict, base: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    """Mean forward return when the condition holds MINUS the average of all samples of the same window (the
    pair's drift: a condition is predictive only when it beats it) and its t-statistic."""
    n = np.maximum(a["n"], 1)
    mean = a["s1"] / n
    var = np.maximum(a["s2"] / n - mean ** 2, 1e-12) * n / np.maximum(n - 1, 1)
    return mean - base, (mean - base) / np.sqrt(var) * np.sqrt(n)


def stability(periods: dict, direction: np.ndarray, bases: dict, min_n: int = 5) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Share of periods (with >= min_n samples) in which the condition beat that period's average in the given
    direction; counts."""
    good = np.zeros(len(direction))
    total = np.zeros(len(direction))
    for p, a in periods.items():
        ok = a["n"] >= min_n
        m = a["s1"] / np.maximum(a["n"], 1) - bases[p]
        total += ok
        good += ok & (np.sign(m) == direction)
    return np.where(total > 0, good / np.maximum(total, 1), 0), good, total - good


def base_of(ds: "Dataset", sel: np.ndarray) -> float:
    return float(np.mean(ds.fwd[sel])) if sel.any() else 0.0


def excess(ds: "Dataset", s: np.ndarray, window: np.ndarray, direction: int) -> np.ndarray:
    """Forward returns of the samples s above the average of the window they belong to, in the signal's direction."""
    return (ds.fwd[s] - base_of(ds, window)) * direction


def select(ds: Dataset, sel: np.ndarray, M: np.ndarray, top: int, period: str = "year") -> list[tuple[int, int, float]]:
    """In-sample choice: n >= min, beats the average in the same direction in >= stability_min of the periods,
    ranked by |t| of the excess over the average. Returns (row, direction, t). Only in-sample samples are used."""
    a = ds.agg(sel, M)
    mean, t = t_stats(a, base_of(ds, sel))
    direction = np.sign(mean)
    labels = ds.year if period == "year" else ds.week
    bases = {p: base_of(ds, sel & (labels == p)) for p in np.unique(labels[sel])}
    st, _, _ = stability(ds.per_period(sel, M, period), direction, bases)
    ok = (a["n"] >= CONFIG["min_n_select"][ds.tf]) & (st >= CONFIG["stability_min"]) & np.isfinite(t)
    rows = np.where(ok)[0]
    rows = rows[np.argsort(-np.abs(t[rows]))][:top]
    return [(int(r), int(direction[r]), float(t[r])) for r in rows]


def family(c: K.Cond) -> str:
    """Indicator family: a combination takes at most one condition of each (MACD 12/26/9 next to MACD 12/34/9 is
    the same information, not a combination)."""
    k = c.kind
    fam = ("rsi" if k.startswith("rsi") else "macd" if k.startswith("macd") else "bb" if k.startswith("bb") else
           "st" if k.startswith("st_") else "atr" if k.startswith("atr") else "adx" if k.startswith(("adx", "di_")) else "ma")
    return f"{c.tf}:{fam}"


def distinct(ds: Dataset, rows: tuple) -> bool:
    fams = [family(ds.conds[r]) for r in rows]
    if len(set(fams)) < len(fams):
        return False
    for a, b in itertools.combinations(rows, 2):                # nearly the same bars active = no new information
        ma, mb = ds.M[a], ds.M[b]
        union = np.sum(ma | mb)
        if union and np.sum(ma & mb) / union > 0.7:
            return False
    return True


def combos(ds: Dataset, sel: np.ndarray, period: str = "year") -> dict:
    """Staged search: singles -> pairs of the best singles -> triples from the best pairs -> quadruples.
    Each stage keeps only stable combinations with enough samples (in-sample only); components come from
    different indicator families."""
    pool = [r for r, _, _ in select(ds, sel, ds.M, CONFIG["pool"], period)]
    out = {"single": [(x,) for x in pool]}

    def stage(cands: list[tuple]) -> list[tuple]:
        cands = [c for c in dict.fromkeys(tuple(sorted(c)) for c in cands) if distinct(ds, c)]
        if not cands:
            return []
        M = np.vstack([np.logical_and.reduce([ds.M[i] for i in c]) for c in cands])
        picked = select(ds, sel, M, len(cands), period)
        return [(cands[r], d, t) for r, d, t in picked]
    pairs = stage(list(itertools.combinations(pool, 2)))
    out["pair"] = pairs[:CONFIG["top_pairs"]]
    triples = stage([p + (x,) for p, _, _ in out["pair"] for x in pool if x not in p])
    out["triple"] = triples[:CONFIG["top_triples"]]
    quads = stage([p + (x,) for p, _, _ in out["triple"] for x in pool if x not in p])
    out["quad"] = quads[:CONFIG["top_quads"]]
    out["tests"] = len(ds.conds) + len(list(itertools.combinations(pool, 2))) + len(out["pair"]) * len(pool) \
        + len(out["triple"]) * len(pool)                   # every single screened + every combination tried
    return out


def combo_key(ds: Dataset, rows: tuple) -> str:
    return " & ".join(ds.keys[r] for r in rows)


def combo_mask(ds: Dataset, rows: tuple) -> np.ndarray:
    return np.logical_and.reduce([ds.M[r] for r in rows])


def robustness(ds: Dataset, rows: tuple, direction: int, sel: np.ndarray) -> dict:
    """Every component moved to its neighbouring settings one at a time: ROBUST when >= robust_share of the
    neighbours keep the sign with at least half of the in-sample effect, else POSSIBLE OVERFIT."""
    base = combo_mask(ds, rows)
    avg = base_of(ds, sel)
    m0 = (float(np.mean(ds.fwd[sel & base])) - avg) * direction if (sel & base).any() else 0.0
    held, total, examples = 0, 0, []
    for pos, r in enumerate(rows):
        for nb in K.neighbors(ds.conds[r]):
            m = ds.sampled(nb)
            for q, r2 in enumerate(rows):
                if q != pos:
                    m = m & ds.M[r2]
            s = sel & m
            if s.sum() < 10:
                continue
            e = (float(np.mean(ds.fwd[s])) - avg) * direction
            total += 1
            ok = e > 0 and e >= 0.5 * m0
            held += ok
            if len(examples) < 4:
                examples.append(f"{nb.key}: {'drží' if ok else 'nedrží'}")
    if total < 2:
        return {"stav": "NEOVĚŘENO (málo sousedních nastavení)", "drzi": held, "celkem": total, "priklady": examples}
    return {"stav": "ROBUST" if held / total >= CONFIG["robust_share"] else "POSSIBLE OVERFIT", "drzi": held,
            "celkem": total, "priklady": examples}


def regime_split(ds: Dataset, mask: np.ndarray, direction: int, sel: np.ndarray) -> dict:
    out = {}
    for name, lab in ds.regime.items():
        part = {}
        for v in np.unique(lab):
            if v in ("NEOVĚŘENO", "přechod", "střední"):
                continue
            s = sel & mask & (lab == v)
            if s.sum() >= 20:
                x = excess(ds, s, sel & (lab == v), direction)
                part[v] = {"n": int(s.sum()), "prumer": float(np.mean(x)), "hit": float(np.mean(x > 0))}
        vals = [p["prumer"] for p in part.values()]
        if len(vals) == 2 and min(p["n"] for p in part.values()) >= 50 and vals[0] * vals[1] < 0:
            part["obrat"] = "v jednom režimu funguje opačně"
        if part:
            out[name] = part
    return out


def describe(ds: Dataset, rows: tuple, direction: int, sel_is: np.ndarray, sel_oos: np.ndarray | None,
             period: str = "year") -> dict:
    mask = combo_mask(ds, rows)
    x_is = excess(ds, sel_is & mask, sel_is, direction)
    out = {"podminka": combo_key(ds, rows), "smer": "růst" if direction > 0 else "pokles",
           "in_sample": full_stats(x_is), "prumer_paru_is": base_of(ds, sel_is)}
    if sel_oos is not None:
        out["out_of_sample"] = full_stats(excess(ds, sel_oos & mask, sel_oos, direction))
        out["prumer_paru_oos"] = base_of(ds, sel_oos)
    labels = ds.year if period == "year" else ds.week
    worked = failed = 0
    both = sel_is | (sel_oos if sel_oos is not None else sel_is)
    for p in np.unique(labels[both]):
        s = (labels == p) & mask & both
        if s.sum() >= 5:
            if (np.mean(ds.fwd[s]) - base_of(ds, (labels == p) & both)) * direction > 0:
                worked += 1
            else:
                failed += 1
    out["obdobi_fungovala"], out["obdobi_selhala"] = worked, failed
    c = np.corrcoef(mask[sel_is].astype(float), ds.fwd[sel_is])[0, 1] if 0 < mask[sel_is].sum() < sel_is.sum() else np.nan
    out["korelace"] = None if not np.isfinite(c) else float(c * direction)
    sp = spread_pips(ds.pair)
    if out["in_sample"]["n"]:
        move_pips = out["in_sample"]["prumer"] / 100 * float(np.median(ds.bars["c"])) / pip(ds.pair)
        out["prumer_pips"] = move_pips
        out["po_nakladech"] = None if sp is None else move_pips - sp
    return out


def walk_forward(ds: Dataset, period: str, with_combos: bool) -> dict:
    """Find on the past -> lock -> test the next period -> move the window (expanding). Years for 1H/4H/1D,
    weeks for the 60-day 15M/30M histories."""
    labels = ds.year if period == "year" else ds.week
    folds = sorted(set(labels))
    first_test = 4 if period == "year" else 4
    res = {"singles": [], "combos": []}
    for k in range(first_test, len(folds)):
        test = folds[k]
        sel_is = ds.t_end < ds.t[labels == test].min() if (labels == test).any() else None
        if sel_is is None or sel_is.sum() < 100:
            continue
        sel_oos = labels == test
        locked = select(ds, sel_is, ds.M, CONFIG["top_k"], period)
        vals = []
        avg = base_of(ds, sel_oos)
        for r, d, _ in locked:
            s = sel_oos & ds.M[r]
            if s.sum() >= 5:
                vals.append((float(np.mean(ds.fwd[s])) - avg) * d)
        if vals:
            res["singles"].append({"obdobi": str(test), "zamceno": len(locked), "testovano": len(vals),
                                   "prumer": float(np.mean(vals)), "podil_kladnych": float(np.mean(np.array(vals) > 0))})
        if with_combos:
            found = combos(ds, sel_is, period)
            vals = []
            for kind in ("pair", "triple", "quad"):
                for rows, d, _ in found[kind]:
                    s = sel_oos & combo_mask(ds, rows)
                    if s.sum() >= 5:
                        vals.append((float(np.mean(ds.fwd[s])) - avg) * d)
            if vals:
                res["combos"].append({"obdobi": str(test), "testovano": len(vals), "prumer": float(np.mean(vals)),
                                      "podil_kladnych": float(np.mean(np.array(vals) > 0))})
    for kind in ("singles", "combos"):
        f = res[kind]
        res[f"{kind}_souhrn"] = None if not f else {
            "obdobi": len(f), "kladnych_obdobi": sum(x["prumer"] > 0 for x in f),
            "prumer": float(np.mean([x["prumer"] for x in f])),
            "podil_kladnych_podminek": float(np.mean([x["podil_kladnych"] for x in f]))}
    return res


PREREGISTERED = (                                         # the user's examples, tested every week as they are
    ("RSI14>50 & C>EMA20", (("rsi_gt", (14, 50)), ("px_gt", ("EMA", 20)))),
    ("RSI14<50 & C<EMA20", (("rsi_lt", (14, 50)), ("px_lt", ("EMA", 20)))),
    ("RSI14<30 & C<SMA50", (("rsi_lt", (14, 30)), ("px_lt", ("SMA", 50)))),
    ("RSI14>70 & C>SMA50", (("rsi_gt", (14, 70)), ("px_gt", ("SMA", 50)))),
    ("ADX14>25 & +DI & MACD bullish", (("adx_bull", (14, 25)), ("macd_hpos", (12, 26, 9)))),
    ("ADX14>25 & -DI & MACD bearish", (("adx_bear", (14, 25)), ("macd_hneg", (12, 26, 9)))),
    ("BB squeeze & ATR roste & C>EMA20", (("bb_sqz", (20,)), ("atr_up", (14,)), ("px_gt", ("EMA", 20)))),
    ("BB squeeze & ATR roste & C<EMA20", (("bb_sqz", (20,)), ("atr_up", (14,)), ("px_lt", ("EMA", 20)))),
    ("RSI14<30 & pod dolním BB & ADX14<20", (("rsi_lt", (14, 30)), ("bb_bdn", (20, 2.0)), ("adx_lt", (14, 20)))),
    ("RSI14>70 & nad horním BB & ADX14<20", (("rsi_gt", (14, 70)), ("bb_bup", (20, 2.0)), ("adx_lt", (14, 20)))),
    ("RSI14>50 & 4H C>EMA50 & ADX14>25", (("rsi_gt", (14, 50)), ("px_gt", ("EMA", 50), "4H"), ("adx_gt", (14, 25)))),
    ("RSI14<50 & 4H C<EMA50 & ADX14>25", (("rsi_lt", (14, 50)), ("px_lt", ("EMA", 50), "4H"), ("adx_gt", (14, 25)))),
)


def prereg_mask(ds: Dataset, parts) -> np.ndarray | None:
    m = np.ones(len(ds.idx), bool)
    for part in parts:
        tf = part[2] if len(part) > 2 else ""
        if tf and tf not in ds.higher:
            return None
        m &= ds.sampled(K.Cond(part[0], part[1], tf))
    return m


def analyze_dataset(ds: Dataset, week: tuple[int, int], with_wf: bool, with_wf_combos: bool) -> dict:
    """C) predictive results of one pair / timeframe and the week as a new out-of-sample test."""
    t0, t1 = week
    period = "year" if ds.tf in ("1H", "4H", "1D") else "week"
    before = ds.t_end <= t0                                     # outcome known before the week started
    in_week = (ds.t >= t0) & (ds.t_end <= t1)
    out = {"vzorku": int(len(ds.idx)), "horizont": HORIZON_CZ[ds.tf], "od": utc_str(int(ds.t[0])) if len(ds.t) else None}
    # static split: search on the first part, check on the later part (both before the week)
    if period == "year":
        split = before & (ds.year <= 2019)
        later = before & (ds.year >= 2020)
    else:
        cut = np.quantile(ds.t[before], 0.75) if before.any() else 0
        split, later = before & (ds.t_end <= cut), before & (ds.t > cut)
    static = combos(ds, split, period) if split.sum() >= 200 else None
    rep = []
    if static:
        for kind in ("single", "pair", "triple", "quad"):
            for item in static[kind][:8 if kind == "single" else 5]:
                rows, d = (item, int(np.sign(t_stats(ds.agg(split, combo_mask(ds, item)[None, :]),
                                                     base_of(ds, split))[0][0]))) \
                    if kind == "single" else (item[0], item[1])
                desc = describe(ds, rows, d, split, later, period)
                desc["rad"] = kind
                desc["robustnost"] = robustness(ds, rows, d, split)
                oos = desc["out_of_sample"]
                desc["obstala_oos"] = bool(oos["n"] >= 20 and oos["prumer"] > 0 and oos["t"] >= 2)
                desc["rezimy"] = regime_split(ds, combo_mask(ds, rows), d, split | later)
                desc["tyden"] = full_stats(excess(ds, in_week & combo_mask(ds, rows), in_week, d))
                rep.append(desc)
        out["testu_in_sample"] = static["tests"]
        out["ocekavane_nahodne_t3"] = round(static["tests"] * 0.0027, 1)
    out["vitezove"] = rep
    # the week's locked set: chosen on everything known before the week, then the week as a new test
    locked = select(ds, before, ds.M, CONFIG["top_k"], period)
    week_rows = []
    for r, d, t in locked:
        s = in_week & ds.M[r]
        x = excess(ds, s, in_week, d)
        week_rows.append({"podminka": ds.keys[r], "smer": d, "t_in_sample": t, "tyden": full_stats(x)})
    out["zamceno_pro_tyden"] = week_rows
    found = combos(ds, before, period) if before.sum() >= 200 else None
    lc = []
    if found:
        for kind in ("pair", "triple", "quad"):
            for rows, d, t in found[kind]:
                s = in_week & combo_mask(ds, rows)
                lc.append({"podminka": combo_key(ds, rows), "rad": kind, "smer": d, "t_in_sample": t,
                           "tyden": full_stats(excess(ds, s, in_week, d))})
    out["zamcene_kombinace_tyden"] = lc
    # every single condition inside the week (attribution, not prediction) - compact archive rows
    a = ds.agg(in_week)
    mean, _ = t_stats(a, base_of(ds, in_week))
    out["tyden_vsechny"] = {ds.keys[i]: [int(a["n"][i]), round(float(mean[i]), 5),
                                         round(float(a["pos"][i] / max(a["n"][i], 1)), 3)]
                            for i in range(len(ds.keys)) if a["n"][i] > 0}
    pre = []
    for name, parts in PREREGISTERED:
        m = prereg_mask(ds, parts)
        if m is None:
            continue
        early, late = before & (ds.year <= 2019), before & (ds.year >= 2020)
        pre.append({"podminka": name, "historie_pred_tydnem": full_stats(excess(ds, before & m, before, 1)),
                    "historie_do_2019": full_stats(excess(ds, early & m, early, 1)) if period == "year" else None,
                    "historie_od_2020": full_stats(excess(ds, late & m, late, 1)) if period == "year" else None,
                    "tyden": full_stats(excess(ds, in_week & m, in_week, 1))})
    out["predregistrovane"] = pre
    if with_wf:
        out["walk_forward"] = walk_forward(ds, period, with_wf_combos)
    return out


def attribution_week(ds: Dataset, week: tuple[int, int]) -> dict:
    """B) inside the week: conditions active at the bar close vs. the move over the next horizon (all bars,
    overlapping). Association only - not a forecast."""
    t0, t1 = week
    c, cts = ds.bars["c"], ds.bars["close_ts"]
    H, n = ds.H, len(c)
    k = np.where((cts > t0) & (cts <= t1))[0]
    k = k[(k + H < n) & (k >= n - ds.tail)]
    k = k[cts[k + H] <= t1 + 3600]
    if len(k) < 10:
        return {"stav": "INSUFFICIENT SAMPLE"}
    f = (c[k + H] / c[k] - 1) * 100
    rows = []
    for i, key in enumerate(ds.keys):
        m = ds.Mtail[i][k - (n - ds.tail)]
        if 10 <= m.sum() <= len(k) - 10:
            rows.append((key, int(m.sum()), float(np.mean(f[m]) - np.mean(f[~m]))))
    rows.sort(key=lambda x: -x[2])
    return {"baru": int(len(k)), "s_rustem": rows[:5], "s_poklesem": rows[-5:][::-1]}


# ----------------------------------------------------------------------
# fundamentals + technicals (history 2012 ->, daily resolution)
# ----------------------------------------------------------------------

EVENT_STATES = (("C>EMA50", ("px_gt", ("EMA", 50))), ("C<EMA50", ("px_lt", ("EMA", 50))),
                ("C>SMA200", ("px_gt", ("SMA", 200))), ("C<SMA200", ("px_lt", ("SMA", 200))),
                ("RSI14>50", ("rsi_gt", (14, 50))), ("RSI14<50", ("rsi_lt", (14, 50))),
                ("RSI14<30", ("rsi_lt", (14, 30))), ("RSI14>70", ("rsi_gt", (14, 70))),
                ("ADX14>25 +DI", ("adx_bull", (14, 25))), ("ADX14>25 -DI", ("adx_bear", (14, 25))),
                ("ADX14<20", ("adx_lt", (14, 20))), ("MACD H>0", ("macd_hpos", (12, 26, 9))),
                ("MACD H<0", ("macd_hneg", (12, 26, 9))), ("BB20 squeeze", ("bb_sqz", (20,))))


def event_technical(pair: str, d1: dict) -> list[dict]:
    """Days of a central bank decision (Fed, ECB, BoJ, BoE) or a US NFP / CPI release: technical state at the
    previous New York close -> move of the event day in the pair's direction. Daily resolution avoids unreliable
    intraday times; no surprise sign (consensus history is not available) - only whether a state predicted the
    direction of the event day. Search 2012-2019, check 2020 ->."""
    import fundamenty as F
    ev = F.load_events()
    base, quote = pair.split("/")
    names = [(n, c) for n, c in (("FED", "USD"), ("ECB", "EUR"), ("BOJ", "JPY"), ("BOE", "GBP"), ("US_NFP", "USD"),
                                 ("US_CPI", "USD")) if c in (base, quote)]
    days = d1["day"]
    pos = {d: i for i, d in enumerate(days)}
    b = K.Builder(d1)
    masks = {lab: b.mask(K.Cond(*spec)) for lab, spec in EVENT_STATES}
    out = []
    for name, ccy in names:
        idx = [pos[date.fromisoformat(x)] for x in ev.get(name, []) if date.fromisoformat(x) in pos]
        idx = np.array([i for i in idx if i >= 1])
        if len(idx) < 20:
            continue
        ret = (d1["c"][idx] / d1["c"][idx - 1] - 1) * 100
        yrs = np.array([days[i].year for i in idx])
        for lab, m in masks.items():
            st = m[idx - 1]                                    # state at the previous close (known before)
            a, bb = st & (yrs <= 2019), st & (yrs >= 2020)
            if a.sum() < 8 or bb.sum() < 5:
                continue
            base_is, base_oos = float(np.mean(ret[yrs <= 2019])), float(np.mean(ret[yrs >= 2020]))
            d = np.sign(np.mean(ret[a]) - base_is) or 1
            s_is, s_oos = full_stats((ret[a] - base_is) * d), full_stats((ret[bb] - base_oos) * d)
            out.append({"udalost": name, "mena": ccy, "stav": lab, "smer": "růst páru" if d > 0 else "pokles páru",
                        "in_sample": s_is, "out_of_sample": s_oos,
                        "obstalo": bool(s_is["t"] >= 2 and s_oos["t"] >= 2 and s_oos["n"] >= 10),
                        "slabe": bool(s_is["t"] >= 2 and 1 <= s_oos["t"] < 2 and s_oos["n"] >= 10),
                        "vse_dny_udalosti": full_stats(ret)})
    return out


def surprise_stats(path: Path) -> list[dict]:
    """From the growing event archive: reaction after positive vs negative surprises per event type and pair
    (in the event currency's direction)."""
    if not path.exists():
        return []
    rows = [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    groups = defaultdict(list)
    for e in rows:
        if e.get("surprise_trida") not in ("pozitivní pro měnu", "negativní pro měnu"):
            continue
        sign = 1 if e["surprise_trida"] == "pozitivní pro měnu" else -1
        for r in e.get("reakce", []):
            v = r.get("po_60m_pct")
            if v is not None and r.get("smer_meny"):
                groups[(e["typ"], e["mena"], r["par"])].append(v * r["smer_meny"] * sign)
    out = []
    for (kind, ccy, pair), xs in groups.items():
        x = np.array(xs)
        out.append({"typ": kind, "mena": ccy, "par": pair, "n": len(x), "vzorek": sample_label(len(x)),
                    "prumer_ve_smeru_prekvapeni": float(np.mean(x)), "hit": float(np.mean(x > 0))})
    return sorted(out, key=lambda r: -r["n"])


def surprise_tech(path: Path) -> list[dict]:
    """Archive: reaction 1 h after a positive / negative surprise split by the hourly technical state at the
    event time (e.g. USD surprise + EUR/USD under EMA50)."""
    if not path.exists():
        return []
    groups = defaultdict(list)
    for e in (json.loads(x) for x in path.read_text().splitlines() if x.strip()):
        if e.get("surprise_trida") not in ("pozitivní pro měnu", "negativní pro měnu"):
            continue
        sign = 1 if e["surprise_trida"] == "pozitivní pro měnu" else -1
        for r in e.get("reakce", []):
            v = r.get("po_60m_pct")
            if v is None or not r.get("smer_meny"):
                continue
            for st in r.get("stav", []):
                groups[(e["typ"], r["par"], st)].append(v * r["smer_meny"] * sign)
    out = [{"typ": k[0], "par": k[1], "stav": k[2], "n": len(v), "vzorek": sample_label(len(v)),
            "prumer": float(np.mean(v))} for k, v in groups.items()]
    return sorted(out, key=lambda r: -r["n"])


# ----------------------------------------------------------------------
# regimes (daily labels) and the week's market regime
# ----------------------------------------------------------------------

def daily_regimes() -> dict:
    """{name: {date: label}} from daily data known at that day's close: VIX 5-day change (risk), dollar index
    and US 2y 20-day change."""
    import research_factors as RF
    import vyzkum_data as V
    out = {}
    try:
        vix = RF._csv("VIXCLS")
        lab = {}
        for k in range(5, len(vix)):
            lab[vix[k][0]] = "risk-off" if vix[k][1] - vix[k - 5][1] > 0 else "risk-on"
        out["riziko"] = lab
    except Exception:
        pass
    try:
        dx = V.yahoo_daily("DX-Y.NYB")
        keys = sorted(dx)
        out["usd"] = {date.fromisoformat(k) if isinstance(k, str) else k:
                      ("USD roste" if dx[k] > dx[keys[i - 20]] else "USD klesá") for i, k in enumerate(keys) if i >= 20}
    except Exception:
        pass
    try:
        y = V.yields()["USD"]
        keys = sorted(y)
        out["vynosy"] = {k: ("výnosy rostou" if y[k] > y[keys[i - 20]] else "výnosy klesají")
                         for i, k in enumerate(keys) if i >= 20}
    except Exception:
        pass
    norm = {}
    for name, v in out.items():
        d = {}
        for k, lab in v.items():
            if isinstance(k, str):
                k = date.fromisoformat(k[:10])
            elif isinstance(k, datetime):
                k = k.date()
            elif not isinstance(k, date):
                continue
            d[k] = lab
        d["_keys"] = sorted(d)
        norm[name] = d
    return norm


# ----------------------------------------------------------------------
# report
# ----------------------------------------------------------------------

def f2(x, nd=2, suffix=""):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "NEOVĚŘENO"
    return f"{x:+.{nd}f}{suffix}" if isinstance(x, (int, float)) else str(x)


def st_line(s: dict) -> str:
    if not s or not s.get("n"):
        return "n = 0 (INSUFFICIENT SAMPLE)"
    return (f"n {s['n']} ({s['vzorek']}), nad průměrem páru ve směru signálu {s['prumer']:+.3f} %, medián {s['median']:+.3f} %, sd {s['sd']:.3f}, "
            f"úspěšnost {s['hit'] * 100:.0f} %, max zisk {s['max_zisk']:+.2f} %, max ztráta {s['max_ztrata']:+.2f} %, "
            f"t {s['t']:+.1f}")


def fmt_actual(e: dict) -> str:
    if e.get("actual") is None:
        return "NEOVĚŘENO"
    return f"{e['actual']:g}" if e.get("actual_overeno") else f"{e['actual']:g} (NEOVĚŘENO)"


def write_report(R: dict) -> str:
    L = []
    w = R["tyden"]
    L += [f"# WEEKLY FX RESEARCH – týden {w['label']} ({w['od']} – {w['do']})", "",
          f"_Vytvořeno {R['vytvoreno']} UTC. Páry: {', '.join(R['pary'])}. Tři druhy výsledků se nemíchají: "
          "**A) DESKRIPTIVNÍ** (co se stalo), **B) ATRIBUČNÍ** (co s tím v týdnu souviselo – není to předpověď), "
          "**C) PREDIKTIVNÍ** (co mělo předpovědní schopnost na datech, která výběr neviděl). Časy v UTC._", ""]
    # 0 data quality
    L += ["## 0. Kvalita dat (kontrola před výpočtem)", "",
          "| pár | zdroj | stav | barů / očekáváno | chybí | duplicity | špatné OHLC | nulový rozsah | víkend | po pátečním zavření | outliery |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for pair, qs in R["kvalita"].items():
        for q in qs:
            if "zdroj" not in q:
                continue
            L.append(f"| {pair} | {q['zdroj']} | {q['stav']} | {q['baru']} / {q['ocekavano']} | {q['chybi']} | "
                     f"{q['duplicity']} | {q['spatne_ohlc']} | {q['nulovy_rozsah']} | {q['vikend']} | {q.get('po_zavreni', 0)} | "
                     f"{len(q['outliery'])} |")
    L += ["", "Synchronizace zdrojů (medián rozdílu zavíracích cen v pipech): "
          + "; ".join(f"{p}: {s.get('yahoo_15m_vs_1h', {}).get('median_pips', 'NEOVĚŘENO')} (15m vs 1h), "
                      f"{s.get('yahoo_vs_fxcm', {}).get('median_pips', 'NEOVĚŘENO')} (Yahoo vs FXCM)"
                      for p, s in R["synchronizace"].items()), ""]
    if R["vynechano"]:
        L += ["**Vynecháno kvůli vadným datům:** " + ", ".join(R["vynechano"]), ""]
    # 1 what happened
    L += ["## 1. Co se stalo (A – deskriptivní)", "",
          f"| pár | týden % | směr (±{CONFIG['main_sideways_pct']:.2f} %) | rozsah % | volatilita týdne % | nejsilnější den | nejslabší den |",
          "|---|---|---|---|---|---|---|"]
    for pair, P_ in R["pary_vysledky"].items():
        ws, ds_ = P_["tyden"], P_["dny"]
        wd = [d for d in ds_ if d["nazev"] not in ("neděle", "sobota")]
        strong = max(wd, key=lambda d: d["zmena_pct"]) if wd else None
        weak = min(wd, key=lambda d: d["zmena_pct"]) if wd else None
        main_cls = ws["klasifikace"]["%.2f" % CONFIG["main_sideways_pct"]]
        L.append(f"| {pair} | {ws['zmena_pct']:+.2f} | {main_cls} | {ws['rozsah_pct']:.2f} | {ws['volatilita_tyden_pct']:.2f} | "
                 f"{strong['nazev'] + ' ' + format(strong['zmena_pct'], '+.2f') if strong else '-'} | "
                 f"{weak['nazev'] + ' ' + format(weak['zmena_pct'], '+.2f') if weak else '-'} |")
    L += ["", "Jak se mění klasifikace podle hranice SIDEWAYS:", "",
          "| pár | " + " | ".join(f"±{t:.2f} %" for t in CONFIG["sideways_pct"]) + " |",
          "|---|" + "---|" * len(CONFIG["sideways_pct"])]
    for pair, P_ in R["pary_vysledky"].items():
        L.append(f"| {pair} | " + " | ".join(P_["tyden"]["klasifikace"][f"{t:.2f}"] for t in CONFIG["sideways_pct"]) + " |")
    # factors
    fac = R.get("faktory")
    if fac:
        L += ["", "### Společné měnové faktory vs individuální pohyb párů (hodinové výnosy týdne)", "",
              "Faktor měny = její týdenní pohyb proti koši ostatních měn (odhad z párů, součet = 0). "
              "Pohyb páru ≈ faktor základní měny − faktor kótovací měny + individuální zbytek.", "",
              "| měna | faktor týdne % |", "|---|---|"]
        for c, v in sorted(fac["meny"].items(), key=lambda x: -x[1]):
            L.append(f"| {c} | {v:+.2f} |")
        L += ["", "| pár | ze společných faktorů % | individuální % | podíl vysvětlený společnými faktory | poznámka |",
              "|---|---|---|---|---|"]
        for p, v in fac["pary"].items():
            L.append(f"| {p} | {v['spolecny_faktor_pct']:+.2f} | {v['individualni_pct']:+.2f} | {v['r2_spolecny'] * 100:.0f} % | {v['poznamka']} |")
    cor = R.get("korelace_tyden")
    if cor:
        names = cor["nazvy"]
        strong = []
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                r = cor["matice"][i][j]
                if abs(r) >= 0.4:
                    strong.append((abs(r), f"{names[i]} – {names[j]}: {r:+.2f} ({corr_label(r)})"))
        L += ["", "### Korelace hodinových výnosů v týdnu (korelace ≠ kauzalita)", "",
              "Silné a střední dvojice: " + ("; ".join(x for _, x in sorted(strong, reverse=True)[:20]) or "žádné"), ""]
    if R.get("lead_lag"):
        L += ["### Lead / lag (15minutové výnosy, posledních 60 dní; korelace ≠ kauzalita)", "",
              "_Zdroje mají různé burzy a agregaci času (spot FX vs futures): TIMESTAMP UNVERIFIED na úrovni minut._", "",
              "| vede | následuje | zpoždění | r | r obráceně | r současně | N | poznámka |", "|---|---|---|---|---|---|---|---|"]
        for x in R["lead_lag"][:12]:
            note = ("TIMESTAMP UNVERIFIED – pravděpodobně posunuté časové značky zdroje, ne skutečný předstih"
                    if x.get("posun_casu") else "")
            L.append(f"| {x['vede']} | {x['nasleduje']} | {x['zpozdeni_baru'] * 15} min | {x['r']:+.3f} | {x['r_obracene']:+.3f} | "
                     f"{f2(x.get('r_soucasne'), 3)} | {x['n']} | {note} |")
        L.append("")
    if R.get("trhy"):
        L += ["### Ostatní trhy v týdnu", "", "| trh | změna týdne |", "|---|---|"]
        for k, v in R["trhy"].items():
            L.append(f"| {k} | {v} |")
        L.append("")
    # 2 each pair
    L += ["## 2. Každý pár zvlášť", ""]
    for pair, P_ in R["pary_vysledky"].items():
        ws = P_["tyden"]
        L += [f"### {pair}", "",
              f"Týden: open {ws['open']:.5g}, high {ws['high']:.5g}, low {ws['low']:.5g}, close {ws['close']:.5g}; "
              f"změna {ws['zmena_pips']:+.1f} pipů ({ws['zmena_pct']:+.2f} %); max růst od otevření {ws['max_rust_od_open_pct']:+.2f} %, "
              f"max pokles od otevření {ws['max_pokles_od_open_pct']:+.2f} %; max drawdown {ws['max_drawdown_pct']:.2f} %, "
              f"max recovery {ws['max_recovery_pct']:+.2f} %; rozsah {ws['rozsah_pct']:.2f} %; volatilita týdne "
              f"{ws['volatilita_tyden_pct']:.2f} % (ročně {ws['volatilita_rocni_pct']:.1f} %); ATR14 denní "
              f"{ws['atr14_d1_pips'] or 0:.1f} pipů, hodinové {ws['atr14_h1_pips'] or 0:.1f} pipů.",
              "Hodiny up / down / sideways podle hranice: " + "; ".join(
                  f"±{t}: {v['up']}/{v['down']}/{v['sideways']}" for t, v in ws["hodiny_up_down_sideways"].items()),
              "Největší pohyb: " + "; ".join(
                  f"{n}: " + (x if isinstance(x, str) else f"{x['pct']:+.2f} % ({x['cas']})")
                  for n, x in (("15 min", ws["nejvetsi_15m"]), ("30 min", ws["nejvetsi_30m"]), ("1 h", ws["nejvetsi_1h"]))), ""]
        L += ["| den | open | high | low | close | změna % | rozsah % | volatilita % | trend ±0.10 | největší pohyb | hlavní úsek | nejaktivnější úsek |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for d in P_["dny"]:
            L.append(f"| {d['nazev']}{' (otevření)' if d['poznamka'] else ''} {d['den'][5:]} | {d['open']:.5g} | {d['high']:.5g} | {d['low']:.5g} | {d['close']:.5g} | "
                     f"{d['zmena_pct']:+.2f} | {d['rozsah_pct']:.2f} | {d['volatilita_pct']:.2f} | {d['trend']['0.10']} | "
                     f"{d['nejvetsi_pohyb']['pct']:+.2f} % {d['nejvetsi_pohyb']['cas'][-9:]} | {d['hlavni_usek'] or '-'} | "
                     f"{d['nejaktivnejsi_usek'] or '-'} |")
        L.append("")
        moves = P_.get("velke_pohyby", [])
        if moves:
            L.append("**Významné hodinové pohyby a časově související události** (časová shoda ≠ prokázaná příčina):")
            for m in moves:
                L.append(f"- {m['cas']}: {m['pct']:+.2f} % – " + ("; ".join(m["udalosti"]) if m["udalosti"]
                                                                   else "bez události v kalendáři (FUNDAMENT UNVERIFIED)")
                         + (f"; současně: {', '.join(m['trhy'])}" if m["trhy"] else ""))
            L.append("")
        evs = P_.get("udalosti", [])
        if evs:
            L += ["**Fundamentální události a reakce páru** (v % ceny; „ve směru měny“ = kladné, když měna události posílila):", "",
                  "| čas | měna | událost | význam | forecast | actual | surprise | před 1 h | +15m | +30m | +1h | +4h | +12h | +24h |",
                  "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
            for e in evs[:25]:
                r = e["reakce_paru"]
                sg = r.get("smer_meny") or 1
                cells = [f2(None if r.get(f"po_{m}m_pct") is None else r[f"po_{m}m_pct"] * sg, 2)
                         for m in CONFIG["reaction_minutes"]]
                L.append(f"| {e['cas_text']} | {e['mena']} | {e['udalost']}{' ⚠' if e['priznaky'] else ''} | {e['vyznam']} | "
                         f"{e['forecast'] or '-'} | {fmt_actual(e)} | "
                         f"{e['surprise_trida']} | {f2(None if r.get('pred_1h_pct') is None else r['pred_1h_pct'] * sg, 2)} | "
                         + " | ".join(cells) + " |")
            L.append("")
        tech = P_.get("technika", {})
        if tech:
            L.append("**Technický stav (na začátku → na konci týdne):** " + "; ".join(f"{k}: {v}" for k, v in tech.items()))
            L.append("")
        att = P_.get("atribuce", {})
        if att.get("s_rustem"):
            L += ["**B) Atribuce v týdnu (1H, co souviselo s následujícím 4h pohybem – není to předpověď):**",
                  "- s růstem: " + "; ".join(f"{k} (n {n}, {v:+.3f} %)" for k, n, v in att["s_rustem"]),
                  "- s poklesem: " + "; ".join(f"{k} (n {n}, {v:+.3f} %)" for k, n, v in att["s_poklesem"]), ""]
        lk = P_.get("prediktivni", {}).get("1H", {})
        rows = [x for x in lk.get("zamceno_pro_tyden", []) + lk.get("zamcene_kombinace_tyden", []) if x["tyden"]["n"]]
        if rows:
            rows.sort(key=lambda x: -x["tyden"]["prumer"])
            L += ["**C) Podmínky zamčené před týdnem (1H, horizont 4 h) – jak dopadly v týdnu:**",
                  "- nejlepší: " + "; ".join(f"{x['podminka']} ({'↑' if x['smer'] > 0 else '↓'}, n {x['tyden']['n']}, "
                                            f"{x['tyden']['prumer']:+.3f} %, {x['tyden']['vzorek']})" for x in rows[:3]),
                  "- nejhorší: " + "; ".join(f"{x['podminka']} ({'↑' if x['smer'] > 0 else '↓'}, n {x['tyden']['n']}, "
                                             f"{x['tyden']['prumer']:+.3f} %, {x['tyden']['vzorek']})" for x in rows[-3:][::-1]),
                  f"- co fungovalo: {sum(x['tyden']['prumer'] > 0 for x in rows)} z {len(rows)} podmínek; "
                  f"nefungovalo: {sum(x['tyden']['prumer'] <= 0 for x in rows)}", ""]
    # 3 fundamental winners
    L += ["## 3. FUNDAMENTAL WINNERS", "",
          "### Nejsilnější reakce týdne (1 h po události, ve směru měny, v násobcích hodinového ATR)", ""]
    fw = R.get("fund_winners", [])
    if fw:
        L += ["| událost | měna | pár | surprise | reakce 1 h % | v ATR |", "|---|---|---|---|---|---|"]
        for x in fw[:12]:
            L.append(f"| {x['udalost']} ({x['cas']}) | {x['mena']} | {x['par']} | {x['surprise']} | {x['reakce']:+.3f} | {x['atr']:+.2f} |")
    else:
        L.append("Žádné reakce s ověřeným časem a cenou.")
    L += ["", "### Překvapení vs reakce (archiv událostí – roste každý týden)", ""]
    ss = R.get("surprise_stats", [])
    if ss:
        L += ["| typ | měna | pár | n | vzorek | průměr ve směru překvapení % | úspěšnost |", "|---|---|---|---|---|---|---|"]
        for x in ss[:20]:
            L.append(f"| {x['typ']} | {x['mena']} | {x['par']} | {x['n']} | {x['vzorek']} | {x['prumer_ve_smeru_prekvapeni']:+.3f} | {x['hit'] * 100:.0f} % |")
    else:
        L.append("INSUFFICIENT SAMPLE – skutečné hodnoty s konsenzem máme zatím jen pro americká data od 30. 9. 2026.")
    # 4/5 technical and combination winners
    tests = [f"{p} {tf}: {res['testu_in_sample']} testů → náhodou čekáme ~{res['ocekavane_nahodne_t3']} s |t| ≥ 3"
             for p, P_ in R["pary_vysledky"].items() for tf, res in P_.get("prediktivni", {}).items()
             if res.get("testu_in_sample")]
    L += ["", "## Počet testů (ochrana proti náhodným výhrám)", "", "; ".join(tests), ""]
    for title, kinds in (("## 4. TECHNICAL WINNERS (C – prediktivní)", ("single",)),
                         ("## 5. COMBINATION WINNERS (C – prediktivní)", ("pair", "triple", "quad"))):
        L += ["", title, "",
              "_Hledáno jen na 2012–2019 (in-sample), ověřeno na 2020 – týden před analýzou (out-of-sample); 15M/30M: "
              "prvních 75 % z 60 dní / zbytek. Uvedeno jen to, co v out-of-sample drželo směr (t ≥ 2), s robustností "
              "sousedních nastavení. Mnoho testů = některé „výhry“ jsou náhoda; očekávaný počet náhodných t ≥ 3 je u každého "
              "páru uveden._", ""]
        any_ = False
        for pair, P_ in R["pary_vysledky"].items():
            for tf, res in P_.get("prediktivni", {}).items():
                for x in res.get("vitezove", []):
                    if x["rad"] in kinds and x.get("obstala_oos"):
                        any_ = True
                        L.append(f"- **{pair} {tf}** {x['podminka']} → {x['smer']} za {res['horizont']} | "
                                 f"{x['robustnost']['stav']} ({x['robustnost']['drzi']}/{x['robustnost']['celkem']} sousedů) | "
                                 f"IS: {st_line(x['in_sample'])} | OOS: {st_line(x['out_of_sample'])} | období fungovala "
                                 f"{x['obdobi_fungovala']}, selhala {x['obdobi_selhala']} | po nákladech "
                                 f"{f2(x.get('po_nakladech'), 1)} pipů | týden: {st_line(x['tyden'])}")
        if not any_:
            L.append("Žádná podmínka neobstála v out-of-sample.")
        L.append("")
    # walk-forward summary
    L += ["### Walk-forward (najdi → zamkni → otestuj další období → posuň okno)", "",
          "| pár | TF | období | kladných období | průměr zamčených singlů % | podíl kladných podmínek | kombinace: kladných období / průměr % |",
          "|---|---|---|---|---|---|---|"]
    for pair, P_ in R["pary_vysledky"].items():
        for tf, res in P_.get("prediktivni", {}).items():
            wf = res.get("walk_forward") or {}
            s, c = wf.get("singles_souhrn"), wf.get("combos_souhrn")
            if s:
                L.append(f"| {pair} | {tf} | {s['obdobi']} | {s['kladnych_obdobi']} | {s['prumer']:+.4f} | "
                         f"{s['podil_kladnych_podminek'] * 100:.0f} % | "
                         + (f"{c['kladnych_obdobi']}/{c['obdobi']}, {c['prumer']:+.4f}" if c else "-") + " |")
    L += ["", "_Podíl kladných podmínek kolem 50 % = výběr podle minulosti nemá předpovědní schopnost._", ""]
    # 6 fundamental + technical
    L += ["## 6. FUNDAMENT + TECHNIKA", "",
          "_Dny rozhodnutí Fed/ECB/BoJ/BoE a amerických NFP/CPI (2012 →), technický stav v předchozím newyorském zavření "
          "→ pohyb dne události ve směru páru. Bez znaménka překvapení (historie konsenzu není k dispozici). "
          "Hledáno 2012–2019, ověřeno 2020 →._", ""]
    ft = [x for P_ in R["pary_vysledky"].values() for x in P_.get("fund_tech", []) if x["obstalo"] or x.get("slabe")]
    if ft:
        L += ["| pár | událost | technický stav | směr | potvrzení OOS | IS | OOS |", "|---|---|---|---|---|---|---|"]
        for x in sorted(ft, key=lambda x: -x["out_of_sample"]["t"])[:20]:
            L.append(f"| {x['par']} | {x['udalost']} | {x['stav']} | {x['smer']} | "
                     f"{'silné (t ≥ 2)' if x['obstalo'] else 'slabé (t 1–2)'} | {st_line(x['in_sample'])} | "
                     f"{st_line(x['out_of_sample'])} |")
    else:
        L.append("Žádná kombinace události a technického stavu neobstála v out-of-sample.")
    n_ft = sum(len(P_.get("fund_tech", [])) for P_ in R["pary_vysledky"].values())
    L += ["", f"Testováno {n_ft} kombinací událost × pár × stav; při čisté náhodě by zhruba {n_ft * 0.023 * 0.023:.1f} "
          f"prošlo silným potvrzením a ~{n_ft * 0.023 * 0.14:.0f} slabým.", ""]
    st = R.get("surprise_tech", [])
    L += ["### Překvapení + technický stav (archiv, roste každý týden)", ""]
    if st:
        L += ["| typ | pár | stav při zprávě | n | vzorek | reakce 1 h ve směru překvapení % |", "|---|---|---|---|---|---|"]
        for x in st[:20]:
            L.append(f"| {x['typ']} | {x['par']} | {x['stav']} | {x['n']} | {x['vzorek']} | {x['prumer']:+.3f} |")
    else:
        L.append("INSUFFICIENT SAMPLE")
    L.append("")
    # 7 failed
    L += ["## 7. FAILED SIGNALS", "", "Předregistrované kombinace (vaše příklady, testované vždy stejně) – pohyb za 4 h nad průměrem "
          "páru ve stejném období (kladné = pár po signálu rostl víc než obvykle), historie před týdnem vs týden (1H):", "",
          "| pár | kombinace | do 2019: n / průměr % | od 2020: n / průměr % | týden: n / průměr % |", "|---|---|---|---|---|"]
    for pair, P_ in R["pary_vysledky"].items():
        for x in P_.get("prediktivni", {}).get("1H", {}).get("predregistrovane", []):
            a, b, c = x["historie_do_2019"] or {}, x["historie_od_2020"] or {}, x["tyden"]
            L.append(f"| {pair} | {x['podminka']} | {a.get('n', 0)} / {f2(a.get('prumer'), 3)} | {b.get('n', 0)} / "
                     f"{f2(b.get('prumer'), 3)} | {c.get('n', 0)} / {f2(c.get('prumer'), 3)} |")
    failed = []
    for pair, P_ in R["pary_vysledky"].items():
        for tf, res in P_.get("prediktivni", {}).items():
            for x in res.get("zamceno_pro_tyden", []) + res.get("zamcene_kombinace_tyden", []):
                if x["tyden"]["n"] >= 5 and x["tyden"]["prumer"] < 0:
                    failed.append((x["tyden"]["prumer"], f"{pair} {tf} {x['podminka']} ({'↑' if x['smer'] > 0 else '↓'}): "
                                                         f"n {x['tyden']['n']}, {x['tyden']['prumer']:+.3f} %"))
    L += ["", "Zamčené podmínky, které v týdnu selhaly nejvíc: " + ("; ".join(x for _, x in sorted(failed)[:15]) or "žádné"), ""]
    # 8 regime
    rg = R.get("rezim", {})
    L += ["## 8. REGIME", "", "Režim trhu v týdnu: " + ", ".join(f"**{v}**" for v in rg.get("stitky", [])), "",
          "; ".join(f"{k}: {v}" for k, v in rg.get("podklady", {}).items()), ""]
    reg_lines = []
    for pair, P_ in R["pary_vysledky"].items():
        for tf, res in P_.get("prediktivni", {}).items():
            for x in res.get("vitezove", []):
                if not x.get("obstala_oos"):
                    continue
                for name, part in x.get("rezimy", {}).items():
                    for lab, v in part.items():
                        if lab in rg.get("stitky_klice", []) and isinstance(v, dict):
                            reg_lines.append(f"- {pair} {tf} {x['podminka']} ({x['smer']}) v režimu „{lab}“: n {v['n']}, "
                                             f"{v['prumer']:+.3f} %, úspěšnost {v['hit'] * 100:.0f} %")
                    if part.get("obrat"):
                        reg_lines.append(f"- {pair} {tf} {x['podminka']}: {name} – {part['obrat']}")
    L += ["Jak si v režimech tohoto týdne historicky vedly podmínky, které obstály v out-of-sample:", ""] + (reg_lines[:25] or ["- žádné"]) + [""]
    # 9 archive
    L += ["## 9. Archiv a dlouhodobé poznatky", "", R.get("archiv_text", ""), ""]
    return "\n".join(L)


# ----------------------------------------------------------------------
# archive and query
# ----------------------------------------------------------------------

def _round(x):
    if isinstance(x, float):
        return round(x, 5)
    if isinstance(x, dict):
        return {k: _round(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_round(v) for v in x]
    if hasattr(x, "item"):
        return _round(x.item())
    return x


def slim(R: dict) -> dict:
    """The week's archive without what is stored elsewhere or can be recomputed: events (udalosti.jsonl), the
    week's rows of every single condition (--dotaz recomputes them from history), regime splits only of
    OOS-confirmed results. Kept: the locked conditions and combinations with their week result (the true
    forward record), the pre-registered combinations, winners, walk-forward, descriptive figures."""
    out = {k: v for k, v in R.items() if k != "udalosti_vse"}
    pv = {}
    for pair, P_ in R["pary_vysledky"].items():
        q = dict(P_)
        q["prediktivni"] = {}
        for tf, res in P_.get("prediktivni", {}).items():
            r = dict(res)
            r.pop("tyden_vsechny", None)        # recomputable from the price history (--dotaz)
            r["vitezove"] = [x if x.get("obstala_oos") else
                             {"podminka": x["podminka"], "rad": x["rad"], "smer": x["smer"],
                              "t_is": x["in_sample"].get("t"), "oos_prumer": x["out_of_sample"].get("prumer"),
                              "oos_t": x["out_of_sample"].get("t"), "robustnost": x["robustnost"]["stav"],
                              "tyden": x["tyden"]} for x in res.get("vitezove", [])]
            q["prediktivni"][tf] = r
        q["fund_tech"] = [x for x in P_.get("fund_tech", []) if x.get("obstalo") or x.get("slabe")]
        pv[pair] = q
    out["pary_vysledky"] = pv
    return _round(out)


def archive(R: dict) -> Path:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    path = ARCHIVE / f"{R['tyden']['label']}.json.gz"
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(slim(R), fh, ensure_ascii=False, default=str)
    ev_path = ARCHIVE / "udalosti.jsonl"
    seen = set()
    if ev_path.exists():
        seen = {json.loads(x)["id"] for x in ev_path.read_text().splitlines() if x.strip()}
    with ev_path.open("a") as fh:
        for e in R.get("udalosti_vse", []):
            eid = f"{e['mena']}|{e['udalost']}|{e['cas']}"
            if eid not in seen and e["vyznam"] in ("High", "Medium"):
                fh.write(json.dumps(_round({**e, "id": eid}), ensure_ascii=False, default=str) + "\n")
    return path


def archived_weeks() -> list[dict]:
    out = []
    for p in sorted(ARCHIVE.glob("*-W*.json.gz")):
        with gzip.open(p, "rt", encoding="utf-8") as fh:
            out.append(json.load(fh))
    return out


def archive_summary(current: dict) -> str:
    """Long-term view over the archived weeks: locked conditions that repeatedly worked or failed."""
    weeks = archived_weeks()
    labels = [w["tyden"]["label"] for w in weeks]
    if current["tyden"]["label"] not in labels:
        weeks.append(current)
    if len(weeks) < 4:
        return (f"Archiv má {len(weeks)} týden(ů). Dlouhodobé závěry („fungovalo posledních 20 týdnů“) budou možné "
                "po několika týdnech; do té doby lze historii každé podmínky dopočítat dotazem "
                "`python scripts/tydenni_analyza.py --dotaz \"<podmínka>\" --par <pár> --tydnu 20` (týdenní výsledky "
                "z historie 2012 →, bez nahlížení dopředu).")
    tally = defaultdict(lambda: [0, 0])
    for w in weeks:
        for pair, P_ in w["pary_vysledky"].items():
            for tf, res in P_.get("prediktivni", {}).items():
                for x in res.get("zamceno_pro_tyden", []):
                    if x["tyden"]["n"] >= 5:
                        tally[(pair, tf, x["podminka"], x["smer"])][0 if x["tyden"]["prumer"] > 0 else 1] += 1
    rows = sorted(tally.items(), key=lambda kv: -(kv[1][0] + kv[1][1]))
    lines = [f"Archiv: {len(weeks)} týdnů. Zamčené podmínky s nejdelší historií (týdny fungovala / selhala):"]
    for (pair, tf, cond, d), (ok, bad) in rows[:15]:
        lines.append(f"- {pair} {tf} {cond} ({'↑' if d > 0 else '↓'}): {ok} / {bad}")
    return "\n".join(lines)


def query(cond_text: str, pair: str, tf: str, weeks: int, regime: str | None) -> int:
    """Weekly results of a condition (or 'A & B & C') on history known at each week (no look-ahead: the
    direction is the sign of the mean over all weeks BEFORE each week)."""
    keys = [k.strip() for k in cond_text.split("&")]
    src = load_sources(pair, need_15m=tf in ("15M", "30M"))
    bars = build_tf(src, tf)
    higher = {h: build_tf(src, h) for h in TF[tf][2]}
    ds = Dataset(pair, tf, bars, higher, daily_regimes())
    rows = []
    for k in keys:
        if k not in ds.keys:
            print(f"neznámá podmínka: {k}")
            return 1
        rows.append(ds.keys.index(k))
    mask = combo_mask(ds, tuple(rows))
    labels = sorted(set(ds.week))[-weeks:]
    print(f"{cond_text} | {pair} {tf} | horizont {HORIZON_CZ[tf]} | výsledek = pohyb nad průměrem páru v daném týdnu ve směru "
          f"signálu" + (f" | režim {regime}" if regime else ""))
    ok = bad = 0
    for wl in labels:
        sel = (ds.week == wl) & mask
        if regime:
            sel &= np.any([lab == regime for lab in ds.regime.values()], axis=0)
        known = ds.t_end <= ds.t[ds.week == wl].min()
        past = known & mask
        if sel.sum() == 0 or past.sum() < 20:
            continue
        d = np.sign(np.mean(ds.fwd[past]) - base_of(ds, known)) or 1
        m = (float(np.mean(ds.fwd[sel])) - base_of(ds, ds.week == wl)) * d
        ok += m > 0
        bad += m <= 0
        print(f"  {wl}: n {int(sel.sum()):3d}, směr {'↑' if d > 0 else '↓'} (z historie před týdnem), výsledek {m:+.4f} %")
    print(f"fungovala {ok} týdnů, selhala {bad} týdnů ({sample_label(ok + bad)} podle počtu týdnů)")
    return 0


# ----------------------------------------------------------------------
# pipeline
# ----------------------------------------------------------------------

def load_sources(pair: str, need_15m: bool = True) -> dict:
    sym = yahoo_symbol(pair)
    raw1 = yahoo(sym, "1h", "730d")
    src = {"raw_1h": raw1, "y1h": dedupe(raw1)}
    if need_15m:
        for iv, key in (("15m", "y15"), ("30m", "y30")):
            try:
                src[f"raw_{iv}"] = yahoo(sym, iv, "60d")
                src[key] = dedupe(src[f"raw_{iv}"])
            except Exception as exc:
                src[key] = None
                src[f"chyba_{iv}"] = f"{type(exc).__name__}"
    src["h1"], src["join"] = history_1h(pair, src["y1h"])
    return src


def build_tf(src: dict, tf: str) -> dict:
    from src.path_archive import trading_date
    if tf == "15M":
        return src["y15"]
    if tf == "30M":
        return src["y30"]
    if tf == "1H":
        return src["h1"]
    if tf == "4H":
        return K.resample(src["h1"], 14400, 3600)
    return K.resample_days(src["h1"], 3600, trading_date)


def technical_state(d1: dict, h1: dict, t0: int, t1: int) -> dict:
    """A few states at the start and the end of the week (daily and hourly), information only."""
    out = {}
    for name, bars in (("1D", d1), ("1H", h1)):
        b = K.Builder(bars)
        k0 = np.searchsorted(bars["close_ts"], t0, side="right") - 1
        k1 = np.searchsorted(bars["close_ts"], t1, side="right") - 1
        if k0 < 0 or k1 < 0:
            continue
        r = b.ind("rsi", 14)
        a = b.ind("adx", 14)[0]
        e20, e50, s200 = b.ind("EMA", 20), b.ind("EMA", 50), b.ind("SMA", 200)
        hist = b.ind("macd", 12, 26, 9)[2]
        c = bars["c"]

        def pos(k):
            return ("nad" if c[k] > e20[k] else "pod") + " EMA20, " + ("nad" if c[k] > e50[k] else "pod") + " EMA50, " \
                + ("nad" if c[k] > s200[k] else "pod") + " SMA200"
        out[f"{name} RSI14"] = f"{r[k0]:.0f} → {r[k1]:.0f}"
        out[f"{name} ADX14"] = f"{a[k0]:.0f} → {a[k1]:.0f}"
        out[f"{name} MACD hist"] = f"{'+' if hist[k0] > 0 else '−'} → {'+' if hist[k1] > 0 else '−'}"
        out[f"{name} cena"] = f"{pos(k0)} → {pos(k1)}"
    return out


def week_regime(R: dict, cross: dict) -> dict:
    labels, keys, info = [], [], {}
    adx_vals, eff = [], []
    for pair, P_ in R["pary_vysledky"].items():
        t = P_.get("technika", {}).get("1D ADX14")
        if t:
            adx_vals.append(float(t.split("→")[1]))
        ws = P_["tyden"]
        if ws["rozsah_pct"] > 0:
            eff.append(abs(ws["zmena_pct"]) / ws["rozsah_pct"])
    if adx_vals:
        m = float(np.mean(adx_vals))
        info["průměrné denní ADX14 na konci týdne"] = f"{m:.0f}"
        info["účinnost pohybu (|změna| / rozsah)"] = f"{np.mean(eff):.2f}"
        if m >= 25 or np.mean(eff) >= 0.6:
            labels.append("TREND"); keys.append("trend")
        elif m <= 20 or np.mean(eff) <= 0.3:
            labels.append("RANGE"); keys.append("range")
    vols = R.get("vol_vs_rok", [])
    if vols:
        v = float(np.median(vols))
        info["volatilita týdne / medián 52 týdnů"] = f"{v:.2f}"
        if v >= 1.25:
            labels.append("HIGH VOLATILITY"); keys.append("vysoká")
        elif v <= 0.8:
            labels.append("LOW VOLATILITY"); keys.append("nízká")
    vix = cross.get("VIX")
    es = cross.get("S&P500_fut")
    if vix is not None and es is not None:
        info["VIX změna týdne"] = f"{vix:+.2f} bodu"
        info["S&P 500 futures"] = f"{es:+.2f} %"
        if vix > 0 and es < 0:
            labels.append("RISK-OFF"); keys.append("risk-off")
        elif vix < 0 and es > 0:
            labels.append("RISK-ON"); keys.append("risk-on")
    dx = cross.get("dolar_index")
    if dx is not None:
        info["dolarový index"] = f"{dx:+.2f} %"
        keys.append("USD roste" if dx > 0 else "USD klesá")
    tnx = cross.get("US10Y")
    if tnx is not None:
        info["US 10Y výnos"] = f"{tnx * 100:+.0f} bp"
        keys.append("výnosy rostou" if tnx > 0 else "výnosy klesají")
    return {"stitky": labels or ["bez výrazného režimu"], "stitky_klice": keys, "podklady": info}


def main(argv: list[str]) -> int:
    from src.instruments import DEFAULT_ACTIVE
    if "--dotaz" in argv:
        g = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d  # noqa: E731
        return query(g("--dotaz"), g("--par", "EUR/USD"), g("--tf", "1H"), int(g("--tydnu", "20")), g("--rezim"))
    now = datetime.now(UTC)
    monday = date.fromisoformat(argv[argv.index("--tyden") + 1]) if "--tyden" in argv else last_completed_monday(now)
    t0, t1 = week_bounds(monday)
    if "--pary" in argv:
        arg = argv[argv.index("--pary") + 1]
        if arg == "vse":
            import fxcm_universe as U
            pairs = list(U.universe_all())
        else:
            pairs = [p.strip() for p in arg.split(",")]
    else:
        pairs = list(DEFAULT_ACTIVE)
    fast = "--rychle" in argv
    started = time.time()
    R = {"tyden": {"label": week_label(monday), "od": utc_str(t0), "do": utc_str(t1), "t0": t0, "t1": t1},
         "vytvoreno": now.strftime("%Y-%m-%d %H:%M"), "pary": pairs, "kvalita": {}, "synchronizace": {},
         "vynechano": [], "pary_vysledky": {}, "vol_vs_rok": []}
    regimes = daily_regimes()
    sources, week15 = {}, {}
    for pair in pairs:
        try:
            src = load_sources(pair)
        except Exception as exc:
            R["vynechano"].append(f"{pair} (data: {type(exc).__name__})")
            continue
        qs = [quality(src["raw_1h"], t0, t1, "Yahoo 1h")]
        for iv in ("15m", "30m"):
            if src.get(f"raw_{iv}") is not None:
                qs.append(quality(src[f"raw_{iv}"], t0, t1, f"Yahoo {iv}"))
            else:
                qs.append({"zdroj": f"Yahoo {iv}", "stav": "CHYBA", "ocekavano": 0, "baru": 0, "chybi": 0, "duplicity": 0,
                           "spatne_ohlc": 0, "nulovy_rozsah": 0, "vikend": 0, "outliery": []})
        R["kvalita"][pair] = qs
        sync = {}
        if src.get("y15") is not None:
            b15h = K.resample(window(src["y15"], t0, t1), 3600, 900)
            sync["yahoo_15m_vs_1h"] = sync_check({"close_ts": b15h["close_ts"], "c": b15h["c"]}, window(src["y1h"], t0, t1), pair)
        fx = {k: src["h1"][k][src["h1"]["ts"] < src["join"]] for k in ("close_ts", "c")}
        sync["yahoo_vs_fxcm"] = sync_check(fx, src["y1h"], pair)
        R["synchronizace"][pair] = sync
        if qs[0]["stav"] == "CHYBA":
            R["vynechano"].append(f"{pair} (hodinová data týdne vadná)")
            continue
        sources[pair] = src
    for pair, src in sources.items():
        print(f"{pair} ...", flush=True)
        b1w = window(src["y1h"], t0, t1)
        ok15 = src.get("y15") is not None and R["kvalita"][pair][1]["stav"] != "CHYBA"
        ok30 = src.get("y30") is not None and R["kvalita"][pair][2]["stav"] != "CHYBA"
        b15w = window(src["y15"], t0, t1) if ok15 else None
        b30w = window(src["y30"], t0, t1) if ok30 else None
        d1 = cut(build_tf(src, "1D"), t1)
        P_ = {"tyden": week_stats(pair, b15w, b30w, b1w, d1),
              "dny": day_stats(pair, b15w if ok15 else b1w, b1w)}
        # weekly realized vol vs the last 52 weeks (hourly closes)
        h1 = src["h1"]
        vols = []
        for k in range(1, 53):
            m = (h1["ts"] >= t0 - k * 7 * 86400) & (h1["ts"] < t1 - k * 7 * 86400)
            if m.sum() > 50:
                vols.append(np.std(np.diff(np.log(h1["c"][m]))))
        cur = np.std(np.diff(np.log(b1w["c"]))) if len(b1w["c"]) > 10 else np.nan
        if vols and np.isfinite(cur):
            R["vol_vs_rok"].append(float(cur / np.median(vols)))
        P_["technika"] = technical_state(d1, cut(h1, t1), t0, t1)
        week15[pair] = b15w if ok15 else None
        # predictive datasets
        P_["prediktivni"] = {}
        P_["atribuce"] = {}
        for tf in ("15M", "30M", "1H", "4H", "1D"):
            if tf == "15M" and not ok15 or tf == "30M" and not ok30:
                P_["prediktivni"][tf] = {"stav": "NEOVĚŘENO (data nejsou)"}
                continue
            bars = cut(build_tf(src, tf), t1)
            higher = {}
            for h in TF[tf][2]:
                hb = build_tf(src, h) if tf in ("1H", "4H") else (
                    K.resample(src["y1h"], 3600, 3600) if h == "1H" else K.resample(src["y1h"], 14400, 3600))
                higher[h] = cut(hb, t1)
            ds = Dataset(pair, tf, bars, higher, regimes)
            P_["prediktivni"][tf] = analyze_dataset(ds, (t0, t1), with_wf=not fast or tf != "15M",
                                                    with_wf_combos=not fast and tf in ("1H", "4H"))
            if tf == "1H":
                P_["atribuce"] = attribution_week(ds, (t0, t1))
            print(f"  {tf}: {len(ds.idx)} vzorků, {time.time() - started:.0f} s", flush=True)
        P_["fund_tech"] = [{**x, "par": pair} for x in event_technical(pair, d1)]
        R["pary_vysledky"][pair] = P_
    # events of the week and reactions
    ccys = {c for p in sources for c in p.split("/")}
    events = week_events(t0, t1, ccys)
    for e in events:
        e["reakce"] = []
        for pair in sources:
            if e["mena"] in pair.split("/") and week15.get(pair) is not None:
                full15 = sources[pair]["y15"]
                e["reakce"].append(reactions(e, pair, full15, sources[pair]["y1h"]))
    R["udalosti_vse"] = events
    fw = []
    for pair, P_ in R["pary_vysledky"].items():
        evs = []
        for e in events:
            if e["mena"] in pair.split("/") and e["vyznam"] in ("High", "Medium"):
                r = next((x for x in e["reakce"] if x["par"] == pair), {})
                evs.append({**{k: v for k, v in e.items() if k != "reakce"}, "reakce_paru": r})
                if r.get("po_60m_pct") is not None and "TIMESTAMP UNVERIFIED" not in " ".join(e["priznaky"]):
                    a1 = P_["tyden"]["atr14_h1_pips"]
                    v = r["po_60m_pct"] * r["smer_meny"]
                    atr_pct = a1 * pip(pair) / P_["tyden"]["close"] * 100 if a1 else None
                    fw.append({"udalost": e["udalost"], "cas": e["cas_text"], "mena": e["mena"], "par": pair,
                               "surprise": e["surprise_trida"], "reakce": v, "atr": v / atr_pct if atr_pct else 0.0})
        P_["udalosti"] = evs
        # big hourly moves of the week with events / cross-asset moves in the same hour
        b1w = window(sources[pair]["y1h"], t0, t1)
        hist = window(sources[pair]["y1h"], t0 - 20 * 86400, t0)
        med = np.median(np.abs(np.diff(np.log(hist["c"])))) * 100 if len(hist["c"]) > 50 else None
        moves = []
        if med:
            mv = (b1w["c"] / b1w["o"] - 1) * 100
            for k in np.argsort(-np.abs(mv))[:5]:
                if abs(mv[k]) < CONFIG["big_move_x"] * med:
                    continue
                ts = int(b1w["ts"][k])
                near = [f"{e['cas_text']} {e['mena']} {e['udalost']} ({e['vyznam']})" for e in events
                        if e["mena"] in pair.split("/") and e["vyznam"] in ("High", "Medium")
                        and ts - 900 <= e["cas"] < ts + 3600]
                moves.append({"cas": utc_str(ts), "pct": float(mv[k]), "udalosti": near, "trhy": []})
        P_["velke_pohyby"] = moves
    R["fund_winners"] = sorted(fw, key=lambda x: -abs(x["atr"]))
    # cross assets, factors, correlations, lead-lag
    cross_week, cross15, cross1h = {}, {}, {}
    for name, sym in CROSS.items():
        try:
            b = dedupe(yahoo(sym, "1h", "60d"))
            w = window(b, t0, t1)
            if len(w["c"]) > 5:
                cross_week[name] = float(w["c"][-1] - w["o"][0]) if name in LEVEL_ASSETS else float((w["c"][-1] / w["o"][0] - 1) * 100)
                cross1h[name] = w
            cross15[name] = dedupe(yahoo(sym, "15m", "60d"))
        except Exception:
            continue
    R["trhy"] = {k: (f"{v * 100:+.0f} bp (výnos)" if k == "US10Y" else f"{v:+.2f} bodu" if k in LEVEL_ASSETS else f"{v:+.2f} %")
                 for k, v in cross_week.items()}
    for pair, P_ in R["pary_vysledky"].items():                # cross-asset co-moves in the big-move hours
        for m in P_["velke_pohyby"]:
            ts = next((int(t) for t in window(sources[pair]["y1h"], t0, t1)["ts"] if utc_str(int(t)) == m["cas"]), None)
            for name, w in cross1h.items():
                k = np.where(w["ts"] == ts)[0] if ts else []
                if len(k):
                    r = np.diff(np.log(w["c"]))
                    sd = np.std(r) if len(r) > 10 else 0
                    x = np.log(w["c"][k[0]] / w["o"][k[0]])
                    if sd > 0 and abs(x) >= 2 * sd:
                        m["trhy"].append(f"{name} {'↑' if x > 0 else '↓'}")
    week1h = {p: window(sources[p]["y1h"], t0, t1) for p in sources}
    if len(week1h) >= 3:
        _, rets = aligned_returns(week1h)
        R["faktory"] = currency_factors(rets)
        R["korelace_tyden"] = correlations(rets)
    full15 = {p: cut(sources[p]["y15"], t1) for p in sources if sources[p].get("y15") is not None}
    full15.update({k: cut(v, t1) for k, v in cross15.items() if len(v["c"]) > 500})
    if len(full15) >= 3:
        R["lead_lag"] = lead_lag(full15, [p for p in sources if p in full15])
    R["rezim"] = week_regime(R, cross_week)
    R["surprise_stats"] = surprise_stats(ARCHIVE / "udalosti.jsonl")
    R["surprise_tech"] = surprise_tech(ARCHIVE / "udalosti.jsonl")
    R["archiv_text"] = archive_summary(R)
    REPORTS.mkdir(parents=True, exist_ok=True)
    report = REPORTS / f"{R['tyden']['label']}.md"
    report.write_text(write_report(R))
    path = archive(R)
    R["surprise_stats"] = surprise_stats(ARCHIVE / "udalosti.jsonl")     # with this week's events
    R["surprise_tech"] = surprise_tech(ARCHIVE / "udalosti.jsonl")
    report.write_text(write_report(R))
    print(f"-> {report} | archiv {path} | {time.time() - started:.0f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
