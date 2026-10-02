"""Data for the research on daily moves (scripts/pohyby_lab.py, scripts/kratke_okno_lab.py).

    python scripts/vyzkum_data.py      # download / refresh the caches in data/research/vyzkum

- FX: daily bars at the New York close and hourly mid bars (profit_lab2.series, FXCM 2012-2026).
- Other markets, Yahoo Finance daily 2012-: gold, silver, WTI and Brent oil, copper, natural gas,
  S&P 500, Euro Stoxx 50, Nikkei 225, VIX, US 10y / 5y / 3m yields, the dollar index. Every close of
  date d is known before the FX close of d (17:00 New York), so the same-day value may be used at
  the decision; predictive tests use it for the NEXT day's FX move only.
- Government yields (fundamentals store, daily closes): USD 2y / 10y, EUR 2y, JPY 2y, GBP 5y,
  CAD 2y, AUD 2y.
- Scheduled news dates: central bank decisions (learning/udalosti_historie.json) and US releases
  from ALFRED: NFP, CPI, GDP, retail sales, personal income / PCE, PPI.
"""

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import profit_lab2 as P  # noqa: E402
from src.sources.http import fetch  # noqa: E402

UTC = timezone.utc
CACHE = PROJECT_ROOT / "data" / "research" / "vyzkum"
MARKETS = {"zlato": "GC=F", "stribro": "SI=F", "ropa_wti": "CL=F", "ropa_brent": "BZ=F", "med": "HG=F",
           "plyn": "NG=F", "sp500": "^GSPC", "stoxx50": "^STOXX50E", "nikkei": "^N225", "vix": "^VIX",
           "us10y": "^TNX", "us5y": "^FVX", "us3m": "^IRX", "dolar_index": "DX-Y.NYB"}
LEVEL_CHANGE = {"vix", "us10y", "us5y", "us3m"}          # change in points, others in %
YIELDS = {"USD": "USD.Y2", "EUR": "EUR.Y2", "JPY": "JPY.Y2", "GBP": "GBP.Y5", "CAD": "CAD.Y2", "AUD": "AUD.Y2"}
US_RELEASES = {"NFP": 50, "CPI": 10, "HDP": 53, "maloobchod": 9, "PCE": 54, "PPI": 46}


def yahoo_daily(symbol: str, refresh: bool = False) -> dict:
    """{date: close} of one Yahoo symbol, 2012 to today (cached)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"yahoo_{symbol.replace('^', '').replace('=', '_')}.json"
    if path.exists() and not refresh:
        return {date.fromisoformat(k): v for k, v in json.loads(path.read_text()).items()}
    _, content, _ = fetch(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d"
                          f"&period1=1325376000&period2={int(datetime.now(UTC).timestamp())}", retries=3)
    r = json.loads(content)["chart"]["result"][0]
    tz = r["meta"].get("exchangeTimezoneName", "America/New_York")
    from zoneinfo import ZoneInfo
    out = {}
    for ts, c in zip(r["timestamp"], r["indicators"]["quote"][0]["close"]):
        if c is not None:
            out[datetime.fromtimestamp(ts, tz=ZoneInfo(tz)).date()] = float(c)
    path.write_text(json.dumps({k.isoformat(): v for k, v in sorted(out.items())}))
    return out


def us_release_dates(refresh: bool = False) -> dict:
    """{name: set of dates} of the US releases (ALFRED release dates)."""
    import re
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / "us_releases.json"
    if path.exists() and not refresh:
        return {k: {date.fromisoformat(d) for d in v} for k, v in json.loads(path.read_text()).items()}
    out = {}
    for name, rid in US_RELEASES.items():
        _, content, _ = fetch(f"https://alfred.stlouisfed.org/release/downloaddates?rid={rid}&ff=txt", retries=3)
        out[name] = sorted(d for d in re.findall(r"^(\d{4}-\d{2}-\d{2})\s*$", content.decode(), re.M) if d >= "2011")
    path.write_text(json.dumps(out))
    return {k: {date.fromisoformat(d) for d in v} for k, v in out.items()}


def cb_dates() -> dict:
    """{bank: set of decision dates} (FED, ECB, BOJ, BOE)."""
    ev = json.loads((PROJECT_ROOT / "learning" / "udalosti_historie.json").read_text())
    return {k: {date.fromisoformat(d) for d in ev.get(k, [])} for k in ("FED", "ECB", "BOJ", "BOE")}


def yields() -> dict:
    """{currency: {date: yield}} daily closes from the fundamentals store."""
    from src.fundamental.store import load_series
    out = {}
    for ccy, sid in YIELDS.items():
        s = load_series(sid)
        out[ccy] = {d: s._value(k, 2 ** 62) for k, d in enumerate(s._dates)}
    return out


def fx(pair: str) -> dict:
    """Daily bars at the New York close + hourly bars of one pair (mid)."""
    s = P.series(pair)
    return {"days": s["days"], "o": s["do"], "h": s["dh"], "l": s["dl"], "c": s["dc"], "first": s["first"],
            "last": s["last"], "ts": s["ts"], "hc": s["c"], "hh": s["h"], "hl": s["l"]}


def aligned(series: dict, days: list, change: str = "pct") -> np.ndarray:
    """Change of a daily series on each FX day (vs. its previous available
    value); NaN where the market had no value that day."""
    keys = sorted(series)
    idx = {d: k for k, d in enumerate(keys)}
    out = np.full(len(days), np.nan)
    for i, d in enumerate(days):
        k = idx.get(d)
        if k is None or k == 0:
            continue
        a, b = series[keys[k - 1]], series[d]
        out[i] = (b / a - 1) * 100 if change == "pct" else b - a
    return out


def main() -> int:
    for name, sym in MARKETS.items():
        s = yahoo_daily(sym, refresh=True)
        print(f"{name:12} {sym:10} {min(s)} - {max(s)} ({len(s)} dni)")
    for name, ds in us_release_dates(refresh=True).items():
        print(f"{name:12} {len(ds)} terminu")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
